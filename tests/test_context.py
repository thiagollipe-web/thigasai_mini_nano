"""Testes offline: arquivos, URL pública e integração HTTP autenticada."""
import base64
import json
import os
import unittest
from unittest.mock import patch
from urllib import request, error

os.environ.setdefault("THIGAS_SITE_PASSWORD", "senha-de-testes-segura")

import site_tools
from web_cloud import Handler
from http.server import ThreadingHTTPServer
import threading


class ContextTests(unittest.TestCase):
    def test_txt(self):
        out = site_tools.documento("material.txt", "A educação e a tecnologia ajudam os estudantes a aprender.".encode())
        self.assertEqual(out["tipo"], "documento")
        self.assertIn("educação", out["texto"])

    def test_file_limits(self):
        for nome in ("malware.exe", "../../foto.png"):
            with self.assertRaises(site_tools.ContextError):
                site_tools.documento(nome, "Arquivo de texto aleatório".encode("utf-8"))
        with self.assertRaises(site_tools.ContextError):
            site_tools.documento("documento.txt", b"A" * (site_tools.MAX_FILE + 1))
        with self.assertRaises(site_tools.ContextError):
            site_tools.documento("arquivo.pdf", b"PDF mas sem assinatura")

    def test_docx(self):
        from docx import Document
        import io
        d = Document()
        d.add_paragraph("Os biomas brasileiros incluem florestas, campos e cerrados.")
        b = io.BytesIO()
        d.save(b)
        out = site_tools.documento("biomas.docx", b.getvalue())
        self.assertIn("biomas", out["texto"])

    def test_dns_private_blocked(self):
        for url in ("http://example.com", "https://127.0.0.1", "https://localhost", "https://example.com:8000"):
            with self.assertRaises(site_tools.ContextError):
                site_tools._host_publico(url)
        with patch("site_tools.socket.getaddrinfo", return_value=[(None, None, None, None, ("10.2.3.4", 443))]):
            with self.assertRaises(site_tools.ContextError):
                site_tools._host_publico("https://teste-publico.example.com")

    def test_context_is_not_instruction(self):
        c = site_tools.validar_contexto({"tipo": "documento", "titulo": "Ensino", "texto": "Resumo de um documento fornecido pelo usuário."})
        self.assertIn("nunca instrução", c)
        with self.assertRaises(site_tools.ContextError):
            site_tools.validar_contexto({"tipo": "site", "titulo": "X", "texto": "Y" * (site_tools.MAX_CHARS + 1)})


class ContextHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)

    def url(self, suffix):
        return "http://127.0.0.1:" + str(self.server.server_port) + suffix

    def auth(self):
        return {"Authorization": "Basic " + base64.b64encode(b"thigas:senha-de-testes-segura").decode()}

    def post(self, path, payload, auth=True):
        headers = {"Content-Type": "application/json"}
        if auth:
            headers.update(self.auth())
        return request.urlopen(request.Request(self.url(path), data=json.dumps(payload).encode(), headers=headers, method="POST"))

    def test_logo_served_protected(self):
        with self.assertRaises(error.HTTPError) as e:
            request.urlopen(self.url("/assets/capivara.svg"))
        self.assertEqual(e.exception.code, 401)
        with request.urlopen(request.Request(self.url("/assets/capivara.svg"), headers=self.auth())) as r:
            self.assertIn(b"<svg", r.read())
            self.assertIn("image/svg+xml", r.headers["Content-Type"])

    def test_upload_document(self):
        b64 = base64.b64encode("Texto sobre a história da educação paulista.".encode()).decode()
        with self.post("/api/documento", {"nome": "aula.txt", "base64": b64}) as r:
            out = json.load(r)
        self.assertEqual(out["tipo"], "documento")
        self.assertIn("educação", out["texto"])

    def test_site_invalid_url(self):
        with self.assertRaises(error.HTTPError) as raised:
            self.post("/api/site", {"url": "http://localhost/admin"})
        self.assertEqual(raised.exception.code, 422)

    def test_mode_receives_context(self):
        from web_cloud import CALL_TIMES, TOOL_TIMES, RATE_LOCK
        with RATE_LOCK:
            CALL_TIMES.clear()
            TOOL_TIMES.clear()
        with patch("web_cloud.ler_config", return_value={"provedor": "maritaca", "modelo": "falso"}), \
             patch("web_cloud.mini_conversa", return_value={"resposta": "analisado"}) as mini:
            with self.post("/api/chat", {
                "modo": "mini", "pergunta": "Resuma", "contexto": {
                    "tipo": "documento", "titulo": "Aula", "texto": "Conteúdo de história colonial brasileira."
                }
            }) as r:
                self.assertEqual(json.load(r)["resposta"], "analisado")
            self.assertIn("DOCUMENTO EXTERNO", mini.call_args.kwargs["contexto"])

if __name__ == "__main__":
    unittest.main()
