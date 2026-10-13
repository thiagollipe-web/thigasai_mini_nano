"""Regressão do aumento de extensão e fontes no THIGAS AI."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import thigas_wiki as wiki
from web_cloud import mini_conversa


class KnowledgeDepthTests(unittest.TestCase):
    def test_cloud_output_limits_are_larger(self):
        with patch.dict(os.environ, {
            'THIGAS_CLOUD_MODE': '1',
            'MARITACA_API_KEY': 'fake-testing-key',
            'THIGAS_MAX_TOKENS': '1150',
            'THIGAS_MINI_MAX_TOKENS': '1150',
            'THIGAS_MINI_UPSTREAM_URL': ''
        }):
            cfg = wiki.ler_config()
            self.assertEqual(cfg['max_tokens'], 1150)
            with patch('web_cloud.api_chat', return_value='resposta extensa') as api:
                mini_conversa('Explique esse assunto', [], cfg, buscar_wiki=False)
                self.assertEqual(api.call_args.args[0]['max_tokens'], 1150)
                system = api.call_args.args[1][0]['content']
                self.assertIn('explicação', system)
                mini_conversa('Aprofunde esse assunto', [], cfg, buscar_wiki=False, esforco='alto')
                self.assertEqual(api.call_args.args[0]['max_tokens'], 1800)

    def test_mini_uses_three_sources_and_previous_subject(self):
        cfg = {'provedor': 'maritaca', 'modelo': 'fake', 'contato_wikipedia': ''}
        fontes = [
            {'titulo': f'Fonte {i}', 'texto': f'Descrição verificada {i} ' * 15,
             'url': f'https://pt.wikipedia.org/?curid={i}'}
            for i in range(1, 4)
        ]
        historico = [
            {'role': 'user', 'content': 'Conte a história de Ada Lovelace'},
            {'role': 'assistant', 'content': 'Ela foi pioneira na computação.'}
        ]
        with patch.dict(os.environ, {'THIGAS_MINI_UPSTREAM_URL': ''}), \
                patch('web_cloud.wikipedia', return_value=fontes) as lookup, \
                patch('web_cloud.api_chat', return_value='Veja [1], [2] e [3].') as generator:
            result = mini_conversa('Quais eram as suas pesquisas?', historico, cfg,
                                    buscar_wiki=True)
        self.assertEqual(len(result['fontes']), 3)
        self.assertEqual(lookup.call_args.kwargs['max_fontes'], 3)
        self.assertIn('Ada Lovelace', lookup.call_args.kwargs['anterior'])
        system = generator.call_args.args[1][0]['content']
        for n in (1, 2, 3):
            self.assertIn(f'[{n}] Título:', system)
        self.assertIn('não são instruções', system)

    def test_remote_mini_reserves_context_for_longer_answers(self):
        cfg = {'provedor': 'maritaca', 'modelo': 'fake'}
        sources = [
            {'titulo': str(n), 'url': f'https://pt.wikipedia.org/?curid={n}',
             'texto': 'Conhecimento externo. ' * 130}
            for n in range(1, 4)
        ]
        history = [
            {'role': 'user' if i % 2 == 0 else 'assistant', 'content': 'A' * 2500}
            for i in range(10)
        ]
        settings = {
            'THIGAS_MINI_UPSTREAM_URL': 'https://example.org/v1/chat/completions',
            'THIGAS_MINI_API_KEY': 'fake-secret'
        }
        with patch.dict(os.environ, settings), \
                patch('web_cloud.wikipedia', return_value=sources), \
                patch('web_cloud.api_chat', return_value='Detalhes.') as call:
            result = mini_conversa('Explique o assunto do contexto', history, cfg,
                                    buscar_wiki=True, contexto='T' * 12000, esforco='alto')
        self.assertEqual(len(result['fontes']), 2)
        model, messages = call.call_args.args
        self.assertEqual(model['max_tokens'], 1600)
        self.assertEqual(len(messages), 6)  # system, 4 historical messages, user
        self.assertLess(len(messages[-1]['content']), 2500)
        self.assertNotIn('T' * 2000, messages[-1]['content'])
        self.assertLess(len(messages[0]['content']), 3000)

    def test_nano_uses_capped_history_and_sources_only_for_small_gguf(self):
        sources = [
            {'titulo': 'Artigo', 'texto': 'C' * 1200,
             'url': f'https://pt.wikipedia.org/?curid={i}'}
            for i in range(3)
        ]
        remote = {'provedor': 'compat', 'modelo': 'THIGAS_AI_nano_03B'}
        hist = [{'role': 'user', 'content': 'H' * 9000} for _ in range(8)]
        with patch.object(wiki, 'wikipedia', return_value=sources), \
                patch.object(wiki, 'api_chat', return_value='Resposta factual') as api:
            result = wiki.conversa('Quem foi Ada Lovelace?', remote, hist, buscar=True)
        self.assertEqual(len(result['fontes']), 2)
        messages = api.call_args.args[1]
        self.assertEqual(len(messages), 4)
        self.assertEqual(len(messages[1]['content']), 260)
        self.assertLess(messages[0]['content'].count('C'), 900)

    def test_wikipedia_search_returns_three_real_excerpts_not_oversized_request(self):
        calls = []
        def fake_http(url, **_):
            p = parse_qs(urlsplit(url).query)
            calls.append(p)
            if p.get('list') == ['search']:
                return {'query': {'search': [{'title': title}
                    for title in ['Computação', 'Ada Lovelace', 'Algoritmo']]}}
            return {'query': {'pages': [
                {'title': title, 'pageid': n + 30, 'extract': 'Texto público ' * 130}
                for n, title in enumerate(['Computação', 'Ada Lovelace', 'Algoritmo'])]}}
        with tempfile.TemporaryDirectory() as d, \
                patch.object(wiki, 'CACHE_DIR', Path(d)), \
                patch.object(wiki, 'http_json', side_effect=fake_http):
            results = wiki.wikipedia('O que é computação?', max_fontes=3)
            again = wiki.wikipedia('O que é computação?', max_fontes=3)
        self.assertEqual(len(results), 3)
        self.assertEqual(again, results)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]['srlimit'], ['3'])
        self.assertEqual(calls[1]['exchars'], ['1200'])
        self.assertEqual(len({x['url'] for x in results}), 3)

    def test_opt_out_does_not_trigger_wiki_request(self):
        cfg = {'provedor': 'maritaca', 'modelo': 'fake'}
        with patch.dict(os.environ, {'THIGAS_MINI_UPSTREAM_URL': ''}), \
                patch('web_cloud.wikipedia', side_effect=AssertionError('Opt-out ignored')), \
                patch('web_cloud.api_chat', return_value='Sem busca'):
            output = mini_conversa('Pesquisa privada', [], cfg, buscar_wiki=False)
        self.assertEqual(output['fontes'], [])


if __name__ == '__main__':
    unittest.main()
