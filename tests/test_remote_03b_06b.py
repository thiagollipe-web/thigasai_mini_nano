"""Roteamento para GGUF reais sem rede e sem consumo de API."""
import base64
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib import request, error

os.environ.setdefault('THIGAS_SITE_PASSWORD', 'senha-de-testes-segura')
from web_cloud import Handler, CALL_TIMES, RATE_LOCK, remote_nano_config, mini_conversa
from thigas_wiki import THIGASError


class RemoteBackendTests(unittest.TestCase):
    def test_nano_config_requires_https_and_key(self):
        base={
            'THIGAS_NANO_UPSTREAM_URL': 'https://nano.example.net/v1/chat/completions',
            'THIGAS_NANO_API_KEY': 'segredo-interno',
            'THIGAS_NANO_MODEL': 'THIGAS_AI_nano_03B',
        }
        with patch.dict(os.environ,base):
            config=remote_nano_config()
            self.assertEqual(config['modelo'], 'THIGAS_AI_nano_03B')
            self.assertEqual(config['api_key'], 'segredo-interno')
            self.assertEqual(config['provedor'], 'compat')
        for url in (
            'http://127.0.0.1:8091/v1/chat/completions',
            'https://127.0.0.1/v1/chat/completions',
            'https://example.org/models',
            'https://user:pass@example.com/v1/chat/completions',
        ):
            with patch.dict(os.environ,{**base,'THIGAS_NANO_UPSTREAM_URL':url}):
                with self.assertRaises(THIGASError):
                    remote_nano_config()
        with patch.dict(os.environ,{**base,'THIGAS_NANO_API_KEY':''}):
            with self.assertRaises(THIGASError):
                remote_nano_config()

    def test_mini_remote_token_limit_and_fallback_to_ocr(self):
        cloud={'provedor':'maritaca','modelo':'sabiazinho-4-br-sp','api_key':'nuvem'}
        remote={
            'THIGAS_MINI_UPSTREAM_URL':'https://mini.example.net/v1/chat/completions',
            'THIGAS_MINI_API_KEY':'segredo-mini',
            'THIGAS_MINI_MODEL':'THIGAS_AI_mini_06B',
        }
        with patch.dict(os.environ,remote), patch('web_cloud.api_chat',return_value='ok') as chat:
            mini_conversa('Oi',[],cloud,esforco='alto')
            config=chat.call_args.args[0]
            self.assertEqual(config['modelo'],'THIGAS_AI_mini_06B')
            self.assertEqual(config['max_tokens'],1600)
            mini_conversa('Leia',[],cloud,imagem={'data_url':'data:image/png;base64,AAAA'},esforco='equilibrado')
            self.assertEqual(chat.call_args.args[0]['modelo'],'sabiazinho-4-br-sp')

    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0), Handler)
        cls.server.daemon_threads=True
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)

    def test_api_uses_real_remote_nano_when_configured(self):
        with RATE_LOCK:
            CALL_TIMES.clear()
        payload={'modo':'nano','esforco':'rapido','pergunta':'Olá','wikipedia':False}
        auth=base64.b64encode(b'thigas:senha-de-testes-segura').decode()
        remote={'THIGAS_NANO_UPSTREAM_URL':'https://nano.example.net/v1/chat/completions',
                'THIGAS_NANO_API_KEY':'segredo','THIGAS_NANO_MODEL':'THIGAS_AI_nano_03B'}
        with patch.dict(os.environ,remote), \
             patch('web_cloud.ler_config',return_value={'provedor':'maritaca','modelo':'simulado'}), \
             patch('web_cloud.conversa',return_value={'resposta':'Olá do Nano','fontes':[],'aviso':''}) as fn:
            req=request.Request(
                f'http://127.0.0.1:{self.server.server_port}/api/chat',
                data=json.dumps(payload).encode(),method='POST',
                headers={'Content-Type':'application/json','Authorization':'Basic '+auth})
            with request.urlopen(req) as response:
                body=json.load(response)
            self.assertEqual(body['resposta'],'Olá do Nano')
            engine=fn.call_args.args[1]
            self.assertEqual(engine['modelo'],'THIGAS_AI_nano_03B')
            self.assertEqual(engine['max_tokens'],600)
            self.assertNotIn('segredo',json.dumps(body))


if __name__=='__main__':
    unittest.main()
