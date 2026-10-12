"""Comprova entrega segura do runtime WASM e consulta de fontes para GGUF local."""
import base64
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib import request,error

os.environ.setdefault('THIGAS_SITE_PASSWORD','senha-de-testes-segura')
from web_cloud import Handler

class BrowserGGUFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.server.daemon_threads=True
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(4)

    def url(self,path):
        return 'http://127.0.0.1:'+str(self.server.server_port)+path

    def get(self,path,auth=True):
        headers={}
        if auth:
            headers['Authorization']='Basic '+base64.b64encode(b'thigas:senha-de-testes-segura').decode()
        return request.urlopen(request.Request(self.url(path),headers=headers),timeout=20)

    def test_local_js_and_wasm_require_login(self):
        for route in ['/local_gguf.js','/assets/wllama/esm/index.js','/assets/wllama/esm/wasm/wllama.wasm']:
            with self.assertRaises(error.HTTPError) as raised:
                self.get(route,auth=False)
            self.assertEqual(raised.exception.code,401)
            with self.get(route) as response:
                self.assertEqual(response.status,200)
                data=response.read(12)
                self.assertTrue(data)
                self.assertEqual(response.headers['Cross-Origin-Opener-Policy'],'same-origin')
                self.assertEqual(response.headers['Cross-Origin-Embedder-Policy'],'require-corp')
        with self.get('/assets/wllama/esm/wasm/wllama.wasm') as response:
            self.assertIn('application/wasm',response.headers['Content-Type'])

    def test_wasm_csp_allows_wasm_but_not_javascript_eval(self):
        with self.get('/') as response:
            csp=response.headers['Content-Security-Policy']
        self.assertIn("'wasm-unsafe-eval'", csp)
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertIn("worker-src 'self' blob:",csp)

    def test_unknown_static_path_is_not_exposed(self):
        for path in ('/assets/wllama/esm/../../web_cloud.py','/assets/wllama/esm/.env'):
            with self.assertRaises(error.HTTPError) as raised:
                self.get(path)
            self.assertEqual(raised.exception.code,404)

    def test_wikipedia_requires_login_and_only_returns_sources(self):
        with self.assertRaises(error.HTTPError) as raised:
            self.get('/api/wiki?q=Einstein',auth=False)
        self.assertEqual(raised.exception.code,401)
        with self.assertRaises(error.HTTPError) as raised:
            self.get('/api/wiki?q=')
        self.assertEqual(raised.exception.code,400)
        example=[{'titulo':'Teste','texto':'Dados públicos','url':'https://pt.wikipedia.org/wiki/Teste'}]
        with patch('web_cloud.ler_config',return_value={'contato_wikipedia':''}),patch('web_cloud.wikipedia',return_value=example):
            with self.get('/api/wiki?q=Einstein') as response:
                payload=json.load(response)
        self.assertEqual(payload['fontes'],example)

if __name__=='__main__':
    unittest.main()
