#!/usr/bin/env python3
"""THIGAS mini (modo nuvem) + THIGAS nano/Wikipédia, um único serviço protegido.

Python stdlib; chaves exclusivamente no servidor. O modelo GGUF Mini original NÃO é
executado no Render: sem upstream público, o perfil Mini usa Maritaca como motor.
"""
from __future__ import annotations

import base64
import binascii
import hmac
import ipaddress
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from thigas_wiki import THIGASError, ler_config, conversa, api_chat, validar_url, wikipedia, contexto_de_fontes
from site_tools import ContextError, documento, site, validar_contexto

BASE = Path(__file__).resolve().parent
INDEX = (BASE / 'index.html').read_bytes()
LOCAL_GGUF_JS = (BASE / 'local_gguf.js').read_bytes()
WLLAMA_ROOT = (BASE / 'assets' / 'wllama' / 'esm').resolve()
HISTORY_JS = (BASE / 'history_store.js').read_bytes()
CHAT_FORMAT_JS = (BASE / 'chat_format.js').read_bytes()
CAPIVARA = (BASE / 'assets' / 'capivara.svg').read_bytes()
# Somente recursos estáticos públicos podem ser guardados offline.
# Arquivos de configuração, HTML autenticado e respostas da API nunca são cacheados.
PWA_PUBLIC = {
    '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json; charset=utf-8'),
    '/sw.js': ('sw.js', 'text/javascript; charset=utf-8'),
    '/offline.html': ('offline.html', 'text/html; charset=utf-8'),
    '/assets/capivara.svg': ('assets/capivara.svg', 'image/svg+xml'),
    '/assets/icon-180.png': ('assets/icon-180.png', 'image/png'),
    '/assets/icon-192.png': ('assets/icon-192.png', 'image/png'),
    '/assets/icon-512.png': ('assets/icon-512.png', 'image/png'),
    '/assets/icon-maskable-512.png': ('assets/icon-maskable-512.png', 'image/png'),
}
USER = os.environ.get('THIGAS_SITE_USER', 'thigas')
PASSWORD = os.environ.get('THIGAS_SITE_PASSWORD', '')
RATE_LOCK = threading.Lock()
INFLIGHT = threading.BoundedSemaphore(2)
CALL_TIMES: list[float] = []
TOOL_TIMES: list[float] = []

ALLOWED_EFFORTS = {'rapido', 'equilibrado', 'alto'}
MAX_IMAGE_BYTES = 950_000

def validar_imagem(imagem):
    """Aceita somente JPEG/PNG pequeno. Nada é salvo em disco ou log."""
    if imagem is None:
        return None
    if not isinstance(imagem, dict):
        raise ValueError('Imagem inválida.')
    url = imagem.get('dados', '')
    nome = imagem.get('nome', 'imagem')
    if not isinstance(nome, str) or len(nome) > 120 or not isinstance(url, str):
        raise ValueError('Imagem inválida.')
    tipos = {'data:image/jpeg;base64,': 'jpeg', 'data:image/png;base64,': 'png'}
    prefixo = next((p for p in tipos if url.startswith(p)), None)
    if not prefixo or len(url) > 1_360_000:
        raise ValueError('Use imagem PNG ou JPEG de até 950 KB.')
    try:
        raw = base64.b64decode(url[len(prefixo):], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError('Imagem codificada incorretamente.') from exc
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError('A imagem deve ter no máximo 950 KB.')
    if prefixo.startswith('data:image/jpeg') and not raw.startswith(b'\xff\xd8\xff'):
        raise ValueError('O arquivo não é um JPEG válido.')
    if prefixo.startswith('data:image/png') and raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('O arquivo não é um PNG válido.')
    return {'data_url': url, 'nome': nome}

def mensagem_com_imagem(pergunta, imagem):
    """Estrutura oficial image_url da Maritaca: imagem é processada como OCR."""
    if not imagem:
        return pergunta
    return [
        {'type': 'text', 'text': pergunta + '\nSe a imagem tiver texto legível, use o OCR. '
         'Não afirme enxergar objetos, expressões ou detalhes visuais que o OCR não fornece.'},
        {'type': 'image_url', 'image_url': {'url': imagem['data_url']}},
    ]

MINI_SYSTEM = (
    'Você é o THIGAS mini, modo de respostas elaboradas do projeto THIGAS AI. '
    'Responda em português brasileiro, com profundidade e precisão, explicando etapas, '
    'exemplos e contexto quando forem úteis. Para programação e educação, ofereça '
    'soluções concretas e ressalvas necessárias. Não seja prolixo sem necessidade. '
    'Não afirme que está executando um modelo GGUF local quando a inferência for remota. '
    'Não divulgue segredos ou detalhes internos espontaneamente; quando perguntado '
    'diretamente sobre a tecnologia usada, responda com transparência.'
)


def get_rate_limit() -> int:
    try:
        return min(100, max(1, int(os.getenv('THIGAS_MAX_REQUESTS_HOUR', '20'))))
    except ValueError:
        return 20


def remote_mini_config() -> dict | None:
    """Ativa o verdadeiro backend Mini SOMENTE se URL HTTPS e token forem informados.

    O endpoint precisa terminar em /chat/completions. Render não pode acessar
    http://127.0.0.1 do aparelho Android do usuário.
    """
    url = os.getenv('THIGAS_MINI_UPSTREAM_URL', '').strip()
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise THIGASError('THIGAS_MINI_UPSTREAM_URL deve ser HTTPS público e sem dados na URL.')
    if not parsed.path.rstrip('/').endswith('/chat/completions'):
        raise THIGASError('A URL do Mini deve apontar para .../chat/completions.')
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        ip = None
    if ip and not ip.is_global:
        raise THIGASError('O servidor remoto Mini precisa ter endereço público HTTPS.')
    # Uma URL definida pelo administrador, nunca vinda de uma pergunta do usuário.
    key = os.getenv('THIGAS_MINI_API_KEY', '').strip()
    if not key:
        raise THIGASError('Configure THIGAS_MINI_API_KEY para autenticar o backend Mini.')
    return {
        'provedor': 'compat', 'modelo': os.getenv('THIGAS_MINI_MODEL', 'thigas-mini'),
        'api_url': validar_url(url), 'api_key': key,
        'temperatura': 0.4, 'max_tokens': 420,
    }



def remote_nano_config() -> dict | None:
    """Backend GGUF Nano autenticado, com HTTPS. Nunca aceita URL enviada por usuário."""
    url = os.getenv('THIGAS_NANO_UPSTREAM_URL', '').strip()
    if not url:
        return None
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or not parsed.path.rstrip('/').endswith('/chat/completions')):
        raise THIGASError('THIGAS_NANO_UPSTREAM_URL deve ser uma URL HTTPS pública /chat/completions.')
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise THIGASError('Servidor Nano deve usar um domínio HTTPS público.')
    secret = os.getenv('THIGAS_NANO_API_KEY', '').strip()
    if not secret:
        raise THIGASError('Configure THIGAS_NANO_API_KEY no Render.')
    return {
        'provedor': 'compat',
        'modelo': os.getenv('THIGAS_NANO_MODEL', 'THIGAS_AI_nano_03B'),
        'api_url': validar_url(url),
        'api_key': secret,
        'temperatura': 0.25,
        'max_tokens': 600,
    }


def mini_conversa(pergunta: str, historico: list, cloud_cfg: dict, contexto: str = '',
                  buscar_wiki: bool = False, imagem=None, esforco: str = 'equilibrado') -> dict:
    base = remote_mini_config() if imagem is None else None
    # Imagens ainda exigem o serviço de OCR; sem endpoint remoto: perfil Mini usa Sabiázinho, NÃO o GGUF original.
    cfg = (base if base else cloud_cfg).copy()
    # O Mini prioriza explicações e exemplos. Isso controla o estilo e o tamanho,
    # não transforma o serviço em um segundo modelo treinado localmente.
    try:
        limite_mini = int(os.getenv('THIGAS_MINI_MAX_TOKENS', '800'))
    except ValueError:
        limite_mini = 800
    teto = 520 if esforco != 'alto' else 1100
    if base:
        # Os 4096 tokens são janela total do llama-server; saída fica abaixo desse limite.
        cfg['max_tokens'] = 1500 if esforco == 'alto' else 850
    else:
        cfg['max_tokens'] = max(250, min(1200, limite_mini, teto)) if esforco != 'alto' else max(900, min(1200, limite_mini + 300))
    cfg['temperatura'] = 0.4
    historico = historico if isinstance(historico, list) else []
    instrucao = MINI_SYSTEM
    if esforco == 'alto':
        instrucao += ' Esforço de elaboração alto: estrutura a resposta de forma completa, compare alternativas e inclua ressalvas quando úteis.'
    else:
        instrucao += ' Esforço equilibrado: seja claro e completo sem alongar desnecessariamente.'
    fontes = []
    aviso = ''
    if buscar_wiki and pergunta.casefold() not in {'oi', 'olá', 'ola'}:
        try:
            fontes = wikipedia(pergunta, contato=str(cloud_cfg.get('contato_wikipedia') or ''))
            if fontes:
                instrucao += '\n\nMaterial da Wikipédia para citar quando pertinente:\n' + contexto_de_fontes(fontes)
        except THIGASError:
            aviso = 'A Wikipédia não respondeu nesta consulta.'
    messages = [{'role': 'system', 'content': instrucao}]
    for h in historico[-8:]:
        if isinstance(h, dict) and h.get('role') in ('user', 'assistant'):
            messages.append({'role': h['role'], 'content': str(h.get('content', ''))[:2200]})
    messages.append({'role': 'user', 'content': mensagem_com_imagem(pergunta[:1600] + contexto, imagem)})
    resposta = api_chat(cfg, messages)
    return {'resposta': resposta, 'fontes': fontes, 'aviso': aviso, 'modo': 'mini'}


class Handler(BaseHTTPRequestHandler):
    def send_body(self, status: int, body, mime='application/json; charset=utf-8', cache_public=False) -> None:
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'public, max-age=31536000, immutable' if cache_public else 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; img-src 'self'; connect-src 'self'; worker-src 'self' blob:; manifest-src 'self'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self) -> bool:
        header = self.headers.get('Authorization', '')
        if not header.startswith('Basic '):
            return False
        try:
            received = base64.b64decode(header[6:], validate=True)
        except (ValueError, binascii.Error):
            return False
        expected = f'{USER}:{PASSWORD}'.encode('utf-8')
        return hmac.compare_digest(received, expected)

    def ask_login(self):
        msg = b'THIGAS AI: acesso protegido. Informe usuario e senha do site.'
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="THIGAS AI", charset="UTF-8"')
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/health':
            return self.send_body(200, {'ok': True})
        if path in PWA_PUBLIC:
            relative, mime = PWA_PUBLIC[path]
            try:
                resource = (BASE / relative).read_bytes()
            except OSError:
                return self.send_body(404, {'erro': 'Recurso não encontrado.'})
            return self.send_body(200, resource, mime)
        if not self.authorized():
            return self.ask_login()
        if path == '/local_gguf.js':
            return self.send_body(200, LOCAL_GGUF_JS, 'text/javascript; charset=utf-8')
        if path.startswith('/assets/wllama/esm/'):
            item = path[len('/assets/wllama/esm/'):]
            target = (WLLAMA_ROOT / item).resolve()
            if not target.is_relative_to(WLLAMA_ROOT) or not target.is_file():
                return self.send_body(404, {'erro': 'Arquivo não encontrado.'})
            mimetypes = {'.js': 'text/javascript; charset=utf-8',
                         '.mjs': 'text/javascript; charset=utf-8',
                         '.wasm': 'application/wasm'}
            mime = mimetypes.get(target.suffix)
            if not mime or target.stat().st_size > 60_000_000:
                return self.send_body(404, {'erro': 'Recurso não permitido.'})
            return self.send_body(200, target.read_bytes(), mime, cache_public=True)
        if path == '/api/wiki':
            queries = parse_qs(urlsplit(self.path).query)
            term = (queries.get('q') or [''])[0].strip()
            if not term or len(term) > 220:
                return self.send_body(400, {'erro': 'Consulta inválida.'})
            with RATE_LOCK:
                now = time.monotonic()
                TOOL_TIMES[:] = [t for t in TOOL_TIMES if now-t < 3600]
                if len(TOOL_TIMES) >= 20:
                    return self.send_body(429, {'erro': 'Limite de consultas atingido.'})
                TOOL_TIMES.append(now)
            try:
                contato = str(ler_config().get('contato_wikipedia', ''))
                return self.send_body(200, {'fontes': wikipedia(term, contato=contato)})
            except THIGASError:
                return self.send_body(502, {'erro': 'Wikipédia indisponível agora.'})
        if path in ('/', '/index.html', '/mini', '/nano'):
            return self.send_body(200, INDEX, 'text/html; charset=utf-8')
        if path == '/history_store.js':
            return self.send_body(200, HISTORY_JS, 'text/javascript; charset=utf-8')
        if path == '/chat_format.js':
            return self.send_body(200, CHAT_FORMAT_JS, 'text/javascript; charset=utf-8')
        if path == '/assets/capivara.svg':
            return self.send_body(200, CAPIVARA, 'image/svg+xml; charset=utf-8')
        if path == '/api/status':
            return self.send_body(200, {
                'ok': True, 'modos': ['nano', 'mini'],
                'wikipedia': True,
            })
        return self.send_body(404, {'erro': 'Página não encontrada.'})

    def do_POST(self):
        if not self.authorized():
            return self.ask_login()
        if self.path not in ('/api/chat', '/api/documento', '/api/site'):
            return self.send_body(404, {'erro': 'Rota inexistente.'})
        origin = self.headers.get('Origin', '')
        if origin:
            p = urlsplit(origin)
            if p.scheme not in ('http', 'https') or p.netloc.lower() != self.headers.get('Host', '').lower():
                return self.send_body(403, {'erro': 'Origem recusada.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            limite = 2_100_000 if self.path == '/api/documento' else (1_400_000 if self.path == '/api/chat' else 32_000)
            if not 1 <= length <= limite:
                return self.send_body(413, {'erro': 'Requisição muito grande ou vazia.'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('O corpo deve ser um objeto JSON.')
            if self.path in ('/api/documento', '/api/site'):
                with RATE_LOCK:
                    agora = time.monotonic()
                    TOOL_TIMES[:] = [t for t in TOOL_TIMES if agora - t < 3600]
                    if len(TOOL_TIMES) >= 20:
                        return self.send_body(429, {'erro': 'Limite de análises por hora atingido.'})
                    if not INFLIGHT.acquire(blocking=False):
                        return self.send_body(503, {'erro': 'Servidor ocupado. Tente novamente.'})
                    TOOL_TIMES.append(agora)
                try:
                    if self.path == '/api/documento':
                        arquivo = data.get('base64', '')
                        if not isinstance(arquivo, str) or len(arquivo) > 2_050_000:
                            raise ContextError('Documento grande demais.')
                        conteudo = base64.b64decode(arquivo, validate=True)
                        resultado = documento(data.get('nome', ''), conteudo)
                    else:
                        resultado = site(data.get('url', ''))
                    return self.send_body(200, resultado)
                except (ContextError, ValueError, binascii.Error) as exc:
                    mensagem = str(exc) if isinstance(exc, ContextError) else 'Arquivo inválido.'
                    return self.send_body(422, {'erro': mensagem})
                except Exception:
                    return self.send_body(502, {'erro': 'Não foi possível analisar o conteúdo agora.'})
                finally:
                    INFLIGHT.release()
            pergunta = data.get('pergunta')
            if not isinstance(pergunta, str) or not pergunta.strip() or len(pergunta) > 1600:
                return self.send_body(400, {'erro': 'Pergunta vazia ou com mais de 1600 caracteres.'})
            modo = data.get('modo', 'nano')
            esforco = data.get('esforco')
            if esforco is not None:
                if esforco not in ALLOWED_EFFORTS:
                    return self.send_body(400, {'erro': 'Esforço inválido.'})
                modo = 'nano' if esforco == 'rapido' else 'mini'
            if modo not in ('mini', 'nano'):
                return self.send_body(400, {'erro': 'Modo desconhecido.'})
            historico = data.get('historico', [])
            if not isinstance(historico, list):
                return self.send_body(400, {'erro': 'Histórico inválido.'})
            usar_wiki = data.get('wikipedia', True) is True
            try:
                contexto = validar_contexto(data.get('contexto'))
            except ContextError as exc:
                return self.send_body(400, {'erro': str(exc)})
            try:
                imagem = validar_imagem(data.get('imagem'))
            except ValueError as exc:
                return self.send_body(400, {'erro': str(exc)})
        except (ValueError, UnicodeError, TypeError, OverflowError):
            return self.send_body(400, {'erro': 'JSON inválido.'})

        # Contabiliza antes da requisição externa, para limitar tentativas concorrentes.
        with RATE_LOCK:
            now = time.monotonic()
            CALL_TIMES[:] = [t for t in CALL_TIMES if now-t < 3600]
            if len(CALL_TIMES) >= get_rate_limit():
                return self.send_body(429, {'erro': 'Limite de perguntas por hora atingido.'})
            if not INFLIGHT.acquire(blocking=False):
                return self.send_body(503, {'erro': 'Duas respostas já estão em andamento. Aguarde.'})
            CALL_TIMES.append(now)
        try:
            cfg = ler_config()
            if modo == 'mini':
                extras = {}
                if contexto:
                    extras['contexto'] = contexto
                if usar_wiki:
                    extras['buscar_wiki'] = True
                if imagem:
                    extras['imagem'] = imagem
                if esforco:
                    extras['esforco'] = esforco
                result = mini_conversa(pergunta, historico, cfg, **extras)
            else:
                # Respostas curtas por padrão; a pesquisa é opcional.
                base_nano = remote_nano_config() if imagem is None else None
                cfg = (base_nano or cfg).copy()
                try:
                    limite_nano = int(os.getenv('THIGAS_NANO_MAX_TOKENS', '600' if base_nano else '220'))
                except ValueError:
                    limite_nano = 220
                cfg['max_tokens'] = max(60, min(800 if base_nano else 400, limite_nano))
                cfg['temperatura'] = 0.25
                extra_nano = {'contexto': contexto} if contexto else {}
                if imagem:
                    extra_nano['imagem'] = imagem
                result = conversa(pergunta, cfg, historico, buscar=usar_wiki, **extra_nano)
                result['modo'] = 'nano'
            return self.send_body(200, result)
        except THIGASError:
            # Não refletir erros do provedor ou seus nomes/detalhes na interface pública.
            return self.send_body(502, {'erro': 'Não foi possível gerar uma resposta agora. Tente novamente em instantes.'})
        except Exception:
            # Exceções imprevistas são ocultadas do usuário (evitar vazamento de credenciais).
            return self.send_body(500, {'erro': 'Falha interna. Consulte os logs protegidos do servidor.'})
        finally:
            INFLIGHT.release()

    def log_message(self, *_):
        # Não registrar perguntas nem URLs sensíveis.
        return


def main():
    if len(PASSWORD) < 12:
        raise SystemExit('Defina THIGAS_SITE_PASSWORD (no mínimo 12 caracteres) no Render.')
    os.environ['THIGAS_CLOUD_MODE'] = '1'
    try:
        ler_config()
        remote_mini_config()
        remote_nano_config()
    except THIGASError as exc:
        raise SystemExit(f'Configuração inválida: {exc}') from exc
    try:
        port = int(os.getenv('PORT', '10000'))
    except ValueError:
        raise SystemExit('PORT inválida.')
    if port < 1024 or port > 65535:
        raise SystemExit('PORT fora do intervalo permitido.')
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'THIGAS mini + nano online na porta {port} | acesso protegido.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
