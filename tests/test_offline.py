import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import thigas_wiki as t

class TestTHIGASOffline(unittest.TestCase):
    def test_search_cleaning(self):
        self.assertEqual(t.consulta_resumida('Quem foi Albert Einstein?'), 'Albert Einstein')
        self.assertEqual(t.consulta_resumida('Como funciona o sistema solar?'), 'sistema solar')

    def test_followup_uses_subject(self):
        self.assertIn('Einstein', t.consulta_resumida('E quando nasceu?', 'Quem foi Albert Einstein?'))

    def test_wiki_cache_and_two_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(t, 'CACHE_DIR', Path(temp)):
                call_list = []
                def fake_http(url, **_):
                    call_list.append(url)
                    if 'list=search' in url:
                        return {'query': {'search':[{'title':'Albert Einstein'}]}}
                    return {'query': {'pages': [{'title':'Albert Einstein', 'pageid': 12,
                                'extract':'Físico teórico alemão.'}]}}
                with patch.object(t, 'http_json', side_effect=fake_http):
                    fontes = t.wikipedia('Quem foi Albert Einstein?')
                    self.assertEqual(fontes[0]['url'], 'https://pt.wikipedia.org/?curid=12')
                    self.assertEqual(len(call_list), 2)
                    fontes2 = t.wikipedia('Quem foi Albert Einstein?')
                    self.assertEqual(fontes2, fontes)
                    self.assertEqual(len(call_list), 2)

    def test_no_source_lookup_on_greeting(self):
        with patch.object(t, 'wikipedia', side_effect=AssertionError('não deveria pesquisar')):
            with patch.object(t, 'api_chat', return_value='Olá!') as fake_api:
                r = t.conversa('Oi', {'provedor':'local','modelo':'thigas-local'})
                self.assertEqual(r['resposta'], 'Olá!')
                self.assertEqual(r['fontes'], [])
                self.assertIn('system', fake_api.call_args.args[1][0]['role'])

    def test_source_citation_input(self):
        f = [{'titulo':'Exemplo','texto':'Texto da enciclopédia','url':'https://pt.wikipedia.org/?curid=1'}]
        with patch.object(t, 'wikipedia', return_value=f):
            with patch.object(t, 'api_chat', return_value='Segundo a fonte [1], ...') as fake_api:
                r = t.conversa('Exemplo?', {'provedor':'local','modelo':'thigas-local'})
                self.assertEqual(len(r['fontes']), 1)
                self.assertIn('Texto da enciclopédia', fake_api.call_args.args[1][0]['content'])

    def test_remote_key_only_to_provider(self):
        cfg = {'provedor': 'openrouter', 'modelo':'test/model', 'api_key':'FAKE-SECRET'}
        res = {'choices':[{'message':{'content':'Tudo certo.'}}]}
        with patch.object(t, 'http_json', return_value=res) as fake:
            resposta = t.api_chat(cfg, [{'role':'system','content':'teste'},
                                        {'role':'user','content':'oi'}])
            self.assertEqual(resposta, 'Tudo certo.')
            self.assertEqual(fake.call_args.kwargs['headers']['Authorization'], 'Bearer FAKE-SECRET')
            self.assertNotIn('FAKE-SECRET', str(fake.call_args.args))


    def test_maritaca_sabia4_endpoint_and_auth(self):
        """Não faz requisições reais nem usa créditos; testa a configuração de saída."""
        cfg = {'provedor':'maritaca', 'modelo':'sabia-4', 'api_key':'CHAVE-FICTICIA'}
        fake_result = {'choices':[{'message':{'content':'Conexão estabelecida.'}}]}
        with patch.object(t, 'http_json', return_value=fake_result) as mock_http:
            texto = t.api_chat(cfg, [{'role':'system','content':'Responda em português.'},
                                     {'role':'user','content':'Olá'}])
        self.assertEqual(texto, 'Conexão estabelecida.')
        self.assertEqual(mock_http.call_args.args[0],
                         'https://chat.maritaca.ai/api/chat/completions')
        self.assertEqual(mock_http.call_args.kwargs['headers']['Authorization'],
                         'Bearer CHAVE-FICTICIA')
        self.assertEqual(mock_http.call_args.kwargs['data']['model'], 'sabia-4')

    def test_maritaca_missing_key(self):
        with patch.dict('os.environ', {'THIGAS_API_KEY': ''}):
            with self.assertRaises(t.THIGASError):
                t.api_chat({'provedor':'maritaca','modelo':'sabia-4'},
                           [{'role':'user','content':'Olá'}])

    def test_gemini_native(self):
        cfg = {'provedor':'gemini','modelo':'gemini-test','api_key':'FAKE-SECRET'}
        result = {'candidates':[{'content':{'parts':[{'text':'Olá do Gemini'}]}}]}
        with patch.object(t, 'http_json', return_value=result) as fake:
            resp = t.api_chat(cfg, [{'role':'system','content':'Siga instruções'},
                                    {'role':'user','content':'Oi'}])
            self.assertEqual(resp, 'Olá do Gemini')
            self.assertIn('systemInstruction', fake.call_args.kwargs['data'])
            self.assertEqual(fake.call_args.kwargs['headers']['x-goog-api-key'], 'FAKE-SECRET')

    def test_insecure_remote_endpoint_rejected(self):
        with self.assertRaises(t.THIGASError):
            t.validar_url('http://outro-servidor.com/api/v1/chat/completions')
        self.assertEqual(t.validar_url('http://127.0.0.1:8092/v1/chat/completions'),
                         'http://127.0.0.1:8092/v1/chat/completions')

    def test_wiki_down_allows_answer_with_warning(self):
        with patch.object(t, 'wikipedia', side_effect=t.THIGASError('offline')):
            with patch.object(t, 'api_chat', return_value='Não pude verificar fontes.'):
                r = t.conversa('Quem foi Ada Lovelace?',{'provedor':'local','modelo':'thigas-local'})
                self.assertIn('offline', r['aviso'])
                self.assertEqual(r['fontes'], [])

if __name__ == '__main__':
    unittest.main()
