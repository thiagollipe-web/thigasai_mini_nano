"""Validação do PWA sem acesso à API de geração de respostas."""
import base64
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib import request, error

os.environ.setdefault('THIGAS_SITE_PASSWORD','senha-de-testes-segura')
from web_cloud import Handler

class PWATests(unittest.TestCase):
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
        cls.thread.join(3)

    def get(self, path, auth=False):
        headers={}
        if auth:
            headers['Authorization']='Basic '+base64.b64encode(b'thigas:senha-de-testes-segura').decode()
        return request.urlopen(request.Request('http://127.0.0.1:'+str(self.server.server_port)+path,headers=headers))

    def test_manifest_is_public_and_installable(self):
        with self.get('/manifest.webmanifest') as response:
            data=json.load(response)
            self.assertIn('application/manifest+json',response.headers['Content-Type'])
        self.assertEqual(data['display'],'standalone')
        self.assertEqual(data['start_url'],'/')
        self.assertEqual(data['scope'],'/')
        self.assertIn('pt-BR',data['lang'])
        self.assertEqual({icon['sizes'] for icon in data['icons']},{'192x192','512x512'})
        self.assertEqual(len(data['shortcuts']),2)

    def test_public_shell_but_protected_chat(self):
        for route in ('/sw.js','/offline.html','/assets/capivara.svg'):
            with self.get(route) as response:
                self.assertEqual(response.status,200)
        with self.assertRaises(error.HTTPError) as err:
            self.get('/')
        self.assertEqual(err.exception.code,401)
        with self.get('/',auth=True) as response:
            html=response.read().decode()
        self.assertIn('rel="manifest"',html)
        self.assertIn("serviceWorker.register('/sw.js'",html)
        self.assertIn('id="install-pwa"',html)

    def test_chat_history_module_requires_login_and_is_not_cached(self):
        with self.assertRaises(error.HTTPError) as auth_error:
            self.get('/history_store.js')
        self.assertEqual(auth_error.exception.code,401)
        with self.get('/history_store.js',auth=True) as response:
            js=response.read().decode()
        self.assertIn('THIGASHistory',js)
        with self.get('/sw.js') as response:
            sw=response.read().decode()
        self.assertNotIn("'/history_store.js'",sw)
        with self.get('/',auth=True) as response:
            html=response.read().decode()
        for token in ('id="history-sidebar"','id="history-search"',
                      'id="history-new"','id="history-clear-all"',
                      '/history_store.js','id="sidebar-toggle"'):
            self.assertIn(token,html)

    def test_service_worker_does_not_cache_secrets(self):
        with self.get('/sw.js') as response:
            js=response.read().decode()
        self.assertIn("req.mode==='navigate'",js)
        self.assertIn("url.pathname.startsWith('/api/')",js)
        self.assertIn('caches.open(CACHE_NAME)',js)
        self.assertNotIn("cache.put('/api",js)
        self.assertNotIn("cache.put('/index",js)

    def test_icons_when_present(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]/'assets'
        for name,size in [('icon-192.png',192),('icon-512.png',512),('icon-maskable-512.png',512),('icon-180.png',180)]:
            p=root/name
            if not p.exists():
                continue  # Gerados pelo workflow de ícones após o primeiro commit
            with self.get('/assets/'+name) as response:
                b=response.read()
                self.assertEqual(b[:8],b'\x89PNG\r\n\x1a\n')
                self.assertEqual(int.from_bytes(b[16:20],'big'),size)
                self.assertEqual(int.from_bytes(b[20:24],'big'),size)
if __name__=='__main__':
    unittest.main()
