"""Rodízio seguro de credenciais Maritaca/Groq para THIGAS AI.

- Intercala provedores por requisição e credenciais dentro de cada provedor.
- Não expõe valores ou nomes de chaves em respostas HTTP e logs.
- 429 bloqueia temporariamente o PROVEDOR, pois quotas podem ser da organização.
- Não repete chamadas após resposta 200 malformada (pode ter gerado cobrança).
- Imagens (OCR) são encaminhadas somente ao provedor com suporte existente.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from urllib import error as urlerror
from typing import Callable, Mapping, Any

from thigas_wiki import THIGASError

PROVIDERS = ("maritaca", "groq")
# Ex.: GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY2,
#      GROQ_API_KEY_BACKUP, MARITACA_API_KEY_3.
_KEY_NAME = re.compile(
    r"^(MARITACA|GROQ)_API_KEY(?:_?\d+|_(?:BACKUP|SECONDARY|TERTIARY|ALT|EXTRA)(?:_\d+)?)?$"
)
# Variáveis alternativas opcionais: GROQ_API_KEYS / MARITACA_API_KEYS
_KEY_LIST_NAME = re.compile(r"^(MARITACA|GROQ)_API_KEYS$")


@dataclass(frozen=True)
class Credential:
    provider: str
    secret: str = field(repr=False)
    identifier: str = field(repr=False)

    def __repr__(self) -> str:
        return f"Credential(provider={self.provider!r}, secret=[REDACTED])"


_LOCK = threading.RLock()
_PROVIDER_TURN = 0
_KEY_TURNS: dict[str, int] = {"maritaca": 0, "groq": 0}
_KEY_COOLDOWN: dict[str, float] = {}
_PROVIDER_COOLDOWN: dict[str, float] = {}


def _safe_secret_items(value: str) -> list[str]:
    value = str(value or "").strip()
    if not value:
        return []
    if value.startswith("["):
        try:
            result = json.loads(value)
            if isinstance(result, list):
                return [str(item).strip() for item in result if isinstance(item, str) and item.strip()]
        except (ValueError, TypeError):
            return []
    return [item.strip() for item in re.split(r"[,;\n]+", value) if item.strip()]


def discover_credentials(env: Mapping[str, str] | None = None) -> dict[str, list[Credential]]:
    env = os.environ if env is None else env
    result: dict[str, list[Credential]] = {p: [] for p in PROVIDERS}
    seen: dict[str, set[str]] = {p: set() for p in PROVIDERS}

    def add(provider: str, secret: str) -> None:
        secret = secret.strip()
        if not secret:
            return
        unique = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        if unique in seen[provider]:
            return
        seen[provider].add(unique)
        result[provider].append(Credential(provider, secret, provider + ":" + unique))

    # Ordenação reprodutível: variável base, numéricas e depois backups nomeados.
    for name in sorted(env, key=lambda item: (
        0 if item.endswith("_API_KEY") else 1,
        int(re.search(r"(\d+)$", item).group(1)) if re.search(r"(\d+)$", item) else 0,
        item,
    )):
        match = _KEY_NAME.fullmatch(name)
        if match:
            value = env.get(name, "")
            if isinstance(value, str):
                add(match.group(1).lower(), value)
        else:
            listed = _KEY_LIST_NAME.fullmatch(name)
            if listed:
                for secret in _safe_secret_items(env.get(name, "")):
                    add(listed.group(1).lower(), secret)
    return result


def public_status(env: Mapping[str, str] | None = None) -> dict[str, object]:
    discovered = discover_credentials(env)
    counts = {provider: len(slots) for provider, slots in discovered.items()}
    return {
        "rotacao_ativa": sum(counts.values()) > 1,
        "credenciais_configuradas": sum(counts.values()),
        "provedores_ativos": [p for p, n in counts.items() if n],
    }


def _choose_candidates(*, image: bool) -> list[Credential]:
    """Distribuição justa entre provedores e, dentro deles, entre chaves."""
    global _PROVIDER_TURN
    groups = discover_credentials()
    enabled = [p for p in PROVIDERS if groups[p] and (not image or p == "maritaca")]
    if not enabled:
        return []
    with _LOCK:
        turn = _PROVIDER_TURN % len(enabled)
        _PROVIDER_TURN += 1
        providers = enabled[turn:] + enabled[:turn]
        ordered: dict[str, list[Credential]] = {}
        for provider in providers:
            secrets = groups[provider]
            idx = _KEY_TURNS[provider] % len(secrets)
            _KEY_TURNS[provider] += 1
            ordered[provider] = secrets[idx:] + secrets[:idx]
    # Primeira tentativa: uma chave de cada provedor.
    # Somente após isso considerar outras chaves do mesmo provedor.
    return [
        ordered[p][index]
        for index in range(max(len(ordered[p]) for p in providers))
        for p in providers
        if index < len(ordered[p])
    ]


def _available(slot: Credential) -> bool:
    now = time.monotonic()
    with _LOCK:
        return (now >= _PROVIDER_COOLDOWN.get(slot.provider, 0)
                and now >= _KEY_COOLDOWN.get(slot.identifier, 0))


def _cooldown(slot: Credential, *, provider: bool, seconds: float) -> None:
    until = time.monotonic() + max(1, min(900, seconds))
    with _LOCK:
        target = _PROVIDER_COOLDOWN if provider else _KEY_COOLDOWN
        key = slot.provider if provider else slot.identifier
        target[key] = max(target.get(key, 0), until)


def _http_error(exc: THIGASError) -> urlerror.HTTPError | None:
    cause = exc.__cause__
    return cause if isinstance(cause, urlerror.HTTPError) else None


def _retry_after(http_exc: urlerror.HTTPError) -> float:
    value = getattr(http_exc, "headers", None)
    raw = value.get("Retry-After", "") if value else ""
    try:
        return max(10.0, min(180.0, float(raw)))
    except (TypeError, ValueError):
        return 45.0


def rotate_chat(config: dict[str, Any], messages: list[dict[str, Any]],
                single_chat: Callable[[dict[str, Any], list[dict[str, Any]]], str]) -> str:
    """Alterna por chamada; tenta outra credencial em falhas definitivas/429.

    Esta camada só atua quando config['rotate_keys'] é True. Nenhum texto,
    imagem, nome de chave ou token é salvo em estado global.
    """
    has_image = any(
        isinstance(m, dict) and isinstance(m.get("content"), list)
        for m in messages
    )
    candidates = _choose_candidates(image=has_image)
    if not candidates:
        if has_image:
            raise THIGASError("Nenhum provedor configurado suporta OCR de imagem.")
        raise THIGASError("Nenhuma credencial de IA configurada no servidor.")

    attempted = 0
    for slot in candidates:
        if not _available(slot):
            continue
        attempted += 1
        selected = dict(config)
        selected["rotate_keys"] = False
        selected["provedor"] = slot.provider
        selected["api_key"] = slot.secret
        if slot.provider == "groq":
            selected["modelo"] = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
        else:
            selected["modelo"] = os.environ.get("MARITACA_MODEL", "sabiazinho-4-br-sp").strip() or "sabiazinho-4-br-sp"
        try:
            return single_chat(selected, messages)
        except THIGASError as exc:
            http_exc = _http_error(exc)
            if http_exc is None:
                # Um corpo 200 inválido pode já ter sido cobrado: não repetir.
                # Uma falha de conexão também pode acontecer após o servidor responder.
                raise
            status = http_exc.code
            if status == 401:
                _cooldown(slot, provider=False, seconds=600)
                continue
            if status == 429:
                # Groq limita por organização, não por chave; outras chaves do
                # mesmo provedor também entram em cooldown.
                _cooldown(slot, provider=True, seconds=_retry_after(http_exc))
                continue
            if status in (402, 403, 400, 404, 422):
                # Conta sem saldo, modelo indisponível, erro de permissão ou payload.
                # Outra chave na mesma organização provavelmente não resolverá.
                _cooldown(slot, provider=True, seconds=180)
                continue
            if status in (408, 500, 502, 503, 504):
                _cooldown(slot, provider=True, seconds=20)
                continue
            raise

    if attempted == 0:
        raise THIGASError("Credenciais de IA temporariamente em espera.")
    raise THIGASError("Nenhum provedor disponível nesta tentativa.")


def _reset_for_tests() -> None:
    global _PROVIDER_TURN
    with _LOCK:
        _PROVIDER_TURN = 0
        _KEY_TURNS.update({"maritaca": 0, "groq": 0})
        _KEY_COOLDOWN.clear()
        _PROVIDER_COOLDOWN.clear()
