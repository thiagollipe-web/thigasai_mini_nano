"""Testes HTTP sem chamadas à Wikipédia e sem consumo de créditos Maritaca."""
import base64
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib import request, error

os.environ.setdefault('THIGAS_SITE_PASSWORD', 'senha-de-testes-segura')

from web_cloud import Handler, CALL_TIMES, RATE_LOCK, mini_conversa, remote_mini_config
from thigas_wiki import THIGASError


class DualModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)

    def setUp(self):
        with RATE_LOCK:
            CALL_TIMES.clear()

    def url(self, endpoint='/'):
        return f'http://127.0.0.1:{self.server.server_port}{endpoint}'

    def headers(self):
        auth = base64.b64encode(b'thigas:senha-de-testes-segura').decode()
        return {'Authorization': 'Basic ' + auth}

    def post(self, obj, headers=None):
        h={**self.headers(), 'Content-Type':'application/json', **(headers or {})}
        return request.urlopen(request.Request(self.url('/api/chat'), method='POST', headers=h,
                                               data=json.dumps(obj).encode('utf-8')))

    def test_health_and_password(self):
        with request.urlopen(self.url('/health')) as r:
            self.assertEqual(r.status, 200)
            self.assertTrue(json.loads(r.read())['ok'])
        for path in ['/', '/mini', '/nano', '/api/status']:
            with self.assertRaises(error.HTTPError) as out:
                request.urlopen(self.url(path))
            self.assertEqual(out.exception.code, 401)

    def test_index_and_tabs(self):
        # Interface v0.8: o seletor é de esforço, sem abas de pensamento.
        for path in ['/', '/mini', '/nano']:
            with request.urlopen(request.Request(self.url(path), headers=self.headers())) as res:
                html=res.read().decode('utf-8')
                for identifier in ('id="plus"', 'id="mic"', 'id="effort"', 'id="quick-menu"',
                                   'id="document-file"', 'id="image-file"', 'id="site-url"'):
                    self.assertIn(identifier, html)
                self.assertIn('data-effort="rapido"', html)
                self.assertIn('data-effort="equilibrado"', html)
                self.assertIn('data-effort="alto"', html)
                self.assertIn('@wikipedia', html)
                self.assertIn('/pesquisar', html)
                self.assertIn('SpeechRecognition', html)
                self.assertNotIn('Maritaca AI', html)
                self.assertNotIn('sabiazinho-4-br-sp', html)
        with patch('web_cloud.ler_config', return_value={'modelo':'sabiazinho-4-br-sp'}):
            with request.urlopen(request.Request(self.url('/api/status'),headers=self.headers())) as r:
                status=json.loads(r.read())
                self.assertEqual(status['modos'], ['nano', 'mini'])
                self.assertTrue(status['wikipedia'])
                self.assertNotIn('api_key', status)
                self.assertNotIn('modelo_api', status)
                self.assertNotIn('mini_motor', status)
                self.assertNotIn('Maritaca', json.dumps(status))

    def test_separate_mini_nano_modes(self):
        cfg={'provedor':'maritaca','modelo':'sabiazinho-4-br-sp','api_key':'fake'}
        with patch('web_cloud.ler_config', return_value=cfg), \
             patch('web_cloud.mini_conversa',return_value={'resposta':'Sou Mini','fontes':[],'modo':'mini'} ) as mini, \
             patch('web_cloud.conversa',return_value={'resposta':'Sou Nano','fontes':[],'aviso':''}) as nano:
            with self.post({'modo':'mini','pergunta':'Olá','historico':[],'wikipedia':True}) as r:
                out=json.loads(r.read())
                self.assertEqual(out['resposta'],'Sou Mini')
            mini.assert_called_once()
            nano.assert_not_called()
            with self.post({'modo':'nano','pergunta':'Einstein','wikipedia':True}) as r:
                out=json.loads(r.read())
                self.assertEqual(out['resposta'],'Sou Nano')
                self.assertEqual(out['modo'], 'nano')
                self.assertNotIn('motor', out)
                self.assertNotIn('modelo_api', out)
            nano.assert_called_once()

    def test_csrf_validation_rate_limit(self):
        with self.assertRaises(error.HTTPError) as out:
            self.post({'modo':'mini','pergunta':'oi'}, {'Origin':'https://externo.example'})
        self.assertEqual(out.exception.code, 403)
        with patch.dict(os.environ, {'THIGAS_MAX_REQUESTS_HOUR':'1'}), \
             patch('web_cloud.ler_config', return_value={'provedor':'maritaca'}), \
             patch('web_cloud.mini_conversa', return_value={'resposta':'oi'}):
            with self.post({'modo':'mini','pergunta':'oi'}) as r:
                self.assertEqual(r.status,200)
            with self.assertRaises(error.HTTPError) as out:
                self.post({'modo':'mini','pergunta':'oi'})
            self.assertEqual(out.exception.code,429)

    def test_invalid_payloads(self):
        for obj in [{'modo':'outro','pergunta':'oi'}, {'modo':'mini','pergunta':''}, {'modo':'mini','pergunta':'oi','historico':'x'}]:
            with self.assertRaises(error.HTTPError) as out:
                self.post(obj)
            self.assertEqual(out.exception.code,400)

    def test_mini_backend_cloud_and_remote(self):
        cfg={'provedor':'maritaca','modelo':'sabiazinho-4-br-sp','api_key':'fake'}
        with patch.dict(os.environ, {'THIGAS_MINI_UPSTREAM_URL':''}), patch('web_cloud.api_chat', return_value='Olá') as api:
            out=mini_conversa('Olá',[],cfg)
            self.assertEqual(out['resposta'],'Olá')
            self.assertEqual(out['modo'], 'mini')
            self.assertNotIn('motor', out)
            self.assertEqual(api.call_args.args[0]['max_tokens'], 1150)
            self.assertIn('profundidade adequada', api.call_args.args[1][0]['content'])
            self.assertEqual(api.call_args.args[0]['modelo'],'sabiazinho-4-br-sp')
        with patch.dict(os.environ, {'THIGAS_MINI_UPSTREAM_URL':'https://exemplo.com/v1/chat/completions',
                                     'THIGAS_MINI_API_KEY':'token-oculto', 'THIGAS_MINI_MODEL':'Thigas-Mini'}), \
             patch('web_cloud.api_chat', return_value='Mini real') as api:
            out=mini_conversa('Olá',[],cfg)
            self.assertEqual(out['modo'], 'mini')
            self.assertNotIn('motor', out)
            self.assertEqual(api.call_args.args[0]['modelo'],'Thigas-Mini')
            self.assertEqual(api.call_args.args[0]['api_key'],'token-oculto')

    def test_nano_is_concise_and_extra_sources_optional(self):
        cfg={'provedor':'maritaca','modelo':'sabiazinho-4-br-sp','api_key':'fake'}
        with patch('web_cloud.ler_config', return_value=cfg), \
             patch('web_cloud.conversa', return_value={'resposta':'Resposta breve','fontes':[], 'aviso':''}) as nano:
            with self.post({'modo':'nano','pergunta':'Olá','wikipedia':False}) as r:
                out=json.loads(r.read())
                self.assertEqual(out['modo'], 'nano')
                self.assertNotIn('motor',out)
            kwargs=nano.call_args
            self.assertEqual(kwargs.kwargs['buscar'],False)
            self.assertEqual(kwargs.args[1]['max_tokens'],500)
            self.assertEqual(kwargs.args[1]['temperatura'],0.25)


    def test_effort_routes_to_quick_or_detailed(self):
        cfg={'provedor':'maritaca','modelo':'sabiazinho-4-br-sp','api_key':'fake'}
        with patch('web_cloud.ler_config',return_value=cfg), \
             patch('web_cloud.mini_conversa',return_value={'resposta':'Detalhado','fontes':[]}) as mini, \
             patch('web_cloud.conversa',return_value={'resposta':'Rápido','fontes':[]}) as nano:
            with self.post({'modo':'mini','esforco':'rapido','pergunta':'Explique isso','wikipedia':False}) as r:
                self.assertEqual(json.load(r)['resposta'],'Rápido')
            nano.assert_called_once()
            with self.post({'modo':'nano','esforco':'alto','pergunta':'Explique isso','wikipedia':False}) as r:
                self.assertEqual(json.load(r)['resposta'],'Detalhado')
            self.assertEqual(mini.call_args.kwargs['esforco'],'alto')

    def test_invalid_effort_and_images(self):
        with self.assertRaises(error.HTTPError) as e:
            self.post({'modo':'mini','pergunta':'Olá','esforco':'nonsense'})
        self.assertEqual(e.exception.code,400)
        with self.assertRaises(error.HTTPError) as e:
            self.post({'modo':'mini','pergunta':'Olá','imagem':{'nome':'falso.png',
                       'dados':'data:image/png;base64,cmFuZG9t'}})
        self.assertEqual(e.exception.code,400)

    def test_valid_image_passed_as_ocr_payload(self):
        from web_cloud import validar_imagem, mensagem_com_imagem
        import base64
        imagem=validar_imagem({
            'nome':'exemplo.jpg',
            'dados':'data:image/jpeg;base64,'+base64.b64encode(b'\xff\xd8\xff' + b'\x00'*50).decode()
        })
        conteudo=mensagem_com_imagem('Leia esse texto',imagem)
        self.assertEqual(conteudo[0]['type'],'text')
        self.assertEqual(conteudo[1]['type'],'image_url')
        self.assertTrue(conteudo[1]['image_url']['url'].startswith('data:image/jpeg;base64,'))

    def test_user_facing_provider_errors_are_generic(self):
        with patch('web_cloud.ler_config',return_value={'provedor':'maritaca'}), \
             patch('web_cloud.mini_conversa',side_effect=THIGASError('Maritaca AI: dados internos')):
            with self.assertRaises(error.HTTPError) as raised:
                self.post({'modo':'mini','pergunta':'Olá'})
            self.assertEqual(raised.exception.code,502)
            msg=raised.exception.read().decode('utf-8')
            self.assertNotIn('Maritaca',msg)
            self.assertNotIn('dados internos',msg)
            self.assertIn('Tente novamente',msg)

    def test_reject_local_or_unauthenticated_mini_upstream(self):
        for url in ['http://127.0.0.1:8090/v1/chat/completions',
                    'https://192.168.1.2/v1/chat/completions',
                    'https://user:pass@host.com/v1/chat/completions',
                    'https://example.com/v1/other']:
            with patch.dict(os.environ, {'THIGAS_MINI_UPSTREAM_URL':url,'THIGAS_MINI_API_KEY':'x'}):
                with self.assertRaises(THIGASError):
                    remote_mini_config()
        with patch.dict(os.environ, {'THIGAS_MINI_UPSTREAM_URL':'https://exemplo.com/v1/chat/completions','THIGAS_MINI_API_KEY':''}):
            with self.assertRaises(THIGASError):
                remote_mini_config()


if __name__=='__main__':
    unittest.main()
