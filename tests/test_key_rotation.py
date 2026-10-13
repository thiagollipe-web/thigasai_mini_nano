"""Testes de alternância e segurança das credenciais, sem consumir APIs pagas."""
import io
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import key_rotation as rotation
from thigas_wiki import THIGASError, ler_config, api_chat


class PoolTests(unittest.TestCase):
    def setUp(self):
        rotation._reset_for_tests()

    def test_detects_names_numbers_lists_deduplicates_and_redacts(self):
        env = {
            "MARITACA_API_KEY": "maritaca-secret-1",
            "MARITACA_API_KEY_2": "maritaca-secret-2",
            "GROQ_API_KEY": "groq-secret-1",
            "GROQ_API_KEY2": "groq-secret-2",
            "GROQ_API_KEY_BACKUP": "groq-secret-2",
            "GROQ_API_KEYS": '["groq-secret-3", "groq-secret-1"]',
            "GROQ_MODEL": "openai/gpt-oss-20b",
            "GROQ_API_KEY_HELP": "text-not-a-secret",
        }
        result = rotation.discover_credentials(env)
        self.assertEqual(len(result["maritaca"]), 2)
        self.assertEqual(len(result["groq"]), 3)
        self.assertFalse("groq-secret-1" in repr(result["groq"][0]))
        status = rotation.public_status(env)
        self.assertEqual(status["credenciais_configuradas"], 5)
        self.assertTrue(status["rotacao_ativa"])
        self.assertNotIn("secret", repr(status))

    def test_alternates_providers_and_keys_deterministically(self):
        env = {
            "MARITACA_API_KEY": "maritaca-one",
            "GROQ_API_KEY": "groq-one",
            "GROQ_API_KEY_2": "groq-two",
            "GROQ_MODEL": "openai/gpt-oss-20b",
        }
        attempted = []
        def fake(config, _):
            attempted.append((config["provedor"], config["api_key"], config["modelo"]))
            return "ok"
        with patch.dict(os.environ, env, clear=True):
            cfg = {"provedor": "maritaca", "rotate_keys": True, "max_tokens": 500}
            for _ in range(4):
                self.assertEqual(rotation.rotate_chat(cfg, [{"role": "user", "content": "Olá"}], fake), "ok")
        self.assertEqual([(p, k) for p, k, _ in attempted], [
            ("maritaca", "maritaca-one"),
            ("groq", "groq-one"),
            ("maritaca", "maritaca-one"),
            ("groq", "groq-two"),
        ])
        self.assertEqual(attempted[1][2], "openai/gpt-oss-20b")
        self.assertNotEqual(cfg.get("api_key"), "groq-two")

    def test_429_is_provider_wide_not_key_bypass(self):
        env = {
            "MARITACA_API_KEY": "maritaca-one",
            "GROQ_API_KEY": "groq-one",
            "GROQ_API_KEY_2": "groq-two",
        }
        visited = []
        def fail_groq(config, _):
            visited.append((config["provedor"], config["api_key"]))
            if config["provedor"] == "groq":
                status = HTTPError(
                    "https://api.groq.com/openai/v1/chat/completions", 429,
                    "Too Many Requests", {"Retry-After": "90"}, io.BytesIO(b"")
                )
                raise THIGASError("Limite do provedor.") from status
            return "Maritaca respondeu."
        with patch.dict(os.environ, env, clear=True):
            cfg = {"provedor": "maritaca", "rotate_keys": True}
            rotation.rotate_chat(cfg, [{"role": "user", "content": "Primeira"}], fail_groq)
            self.assertEqual(
                rotation.rotate_chat(cfg, [{"role": "user", "content": "Segunda"}], fail_groq),
                "Maritaca respondeu."
            )
            self.assertEqual(
                rotation.rotate_chat(cfg, [{"role": "user", "content": "Terceira"}], fail_groq),
                "Maritaca respondeu."
            )
        self.assertEqual([p for p, _ in visited], ["maritaca", "groq", "maritaca", "maritaca"])
        self.assertTrue(all(k != "groq-two" for _, k in visited))

    def test_invalid_credential_401_falls_back_to_next_key(self):
        env = {"GROQ_API_KEY": "groq-bad", "GROQ_API_KEY_2": "groq-good"}
        called = []
        def fake(cfg, _):
            called.append(cfg["api_key"])
            if cfg["api_key"] == "groq-bad":
                status = HTTPError("https://api.groq.com", 401, "Unauthorized", {}, io.BytesIO(b""))
                raise THIGASError("Chave recusada.") from status
            return "Retorno confiável"
        with patch.dict(os.environ, env, clear=True):
            cfg = {"provedor": "groq", "rotate_keys": True}
            self.assertEqual(rotation.rotate_chat(cfg, [{"role": "user", "content": "Olá"}], fake), "Retorno confiável")
        self.assertEqual(called, ["groq-bad", "groq-good"])
        self.assertNotIn("groq-bad", str(cfg))

    def test_billing_or_model_error_skips_entire_provider(self):
        env = {
            "GROQ_API_KEY": "groq-one", "GROQ_API_KEY_2": "groq-two",
            "MARITACA_API_KEY": "maritaca-one",
        }
        seq=[]
        def fake(cfg, _):
            seq.append(cfg["provedor"])
            if cfg["provedor"] == "groq":
                raise THIGASError("Model not found") from HTTPError(
                    "https://api.groq.com", 400, "Bad Request", {}, io.BytesIO(b""))
            return "ok"
        with patch.dict(os.environ, env, clear=True):
            cfg = {"provedor": "groq", "rotate_keys": True}
            rotation.rotate_chat(cfg, [{"role": "user", "content": "A"}], fake)
            rotation.rotate_chat(cfg, [{"role": "user", "content": "B"}], fake)
        self.assertEqual(seq.count("groq"), 1)

    def test_no_retry_if_successful_http_answer_is_malformed(self):
        env={"GROQ_API_KEY": "one", "GROQ_API_KEY_2": "two"}
        calls=[]
        def fail(cfg,_):
            calls.append(cfg["api_key"])
            raise THIGASError("Resposta HTTP 200 sem texto")
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(THIGASError):
                rotation.rotate_chat({"rotate_keys": True}, [{"role":"user","content":"Olá"}], fail)
        self.assertEqual(calls, ["one"], "Não repetir requisição possivelmente faturada")

    def test_images_only_use_provider_with_ocr(self):
        env={"MARITACA_API_KEY": "m-one", "GROQ_API_KEY": "g-one"}
        records=[]
        with patch.dict(os.environ, env, clear=True):
            for _ in range(3):
                rotation.rotate_chat({"rotate_keys": True}, [
                    {"role": "user", "content": [
                        {"type": "text", "text": "Leia"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,aGVsbG8="}}
                    ]}
                ], lambda cfg, _: records.append(cfg["provedor"]) or "ok")
        self.assertEqual(records, ["maritaca"] * 3)
        rotation._reset_for_tests()
        with patch.dict(os.environ, {"GROQ_API_KEY": "g-one"}, clear=True):
            with self.assertRaisesRegex(THIGASError, "OCR"):
                rotation.rotate_chat({"rotate_keys": True}, [
                    {"role": "user", "content": [{"type": "image_url"}]}
                ], lambda *_: "ok")

    def test_groq_only_starts_cloud_without_maridaca(self):
        with patch.dict(os.environ, {
            "THIGAS_CLOUD_MODE": "1",
            "GROQ_API_KEY": "only-groq",
            "THIGAS_MAX_TOKENS": "950",
            "GROQ_MODEL": "openai/gpt-oss-20b",
        }, clear=True):
            cfg=ler_config()
        self.assertEqual(cfg["provedor"], "groq")
        self.assertEqual(cfg["api_key"], "only-groq")
        self.assertEqual(cfg["max_tokens"], 950)
        self.assertTrue(cfg["rotate_keys"])

    def test_groq_request_parameters_protect_reasoning_and_secret(self):
        cfg = {
            "provedor":"groq", "modelo":"openai/gpt-oss-20b", "api_key":"key-selected",
            "max_tokens": 1150, "temperatura": 0.35, "esforco": "alto"
        }
        request=[]
        def fake_http(url, **kwargs):
            request.append((url, kwargs))
            return {"choices":[{"message":{"content":"O resultado final é claro."}}]}
        with patch.dict(os.environ, {"THIGAS_API_KEY":"legacy-should-not-override"}, clear=True), \
             patch("thigas_wiki.http_json", side_effect=fake_http):
            result=api_chat(cfg,[{"role":"user","content":"Explique um conceito."}])
        self.assertEqual(result,"O resultado final é claro.")
        url,opts=request[0]
        self.assertEqual(url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(opts["headers"]["Authorization"], "Bearer key-selected")
        payload=opts["data"]
        self.assertEqual(payload["model"],"openai/gpt-oss-20b")
        self.assertEqual(payload["reasoning_effort"],"medium")
        self.assertFalse(payload["include_reasoning"])
        self.assertEqual(payload["max_completion_tokens"],1790)
        self.assertNotIn("max_tokens",payload)
        self.assertNotIn("key-selected",str(payload))


if __name__ == "__main__":
    unittest.main()
