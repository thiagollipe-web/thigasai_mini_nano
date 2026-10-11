#!/usr/bin/env python3
"""Interface web mobile para THIGAS AI nano, apenas em localhost."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from thigas_wiki import ler_config, conversa, THIGASError

HERE = Path(__file__).resolve().parent
HTML = (HERE / 'index.html').read_bytes()

class Handler(BaseHTTPRequestHandler):
    def responder(self, status, content, mime='application/json; charset=utf-8'):
        if isinstance(content, (dict, list)):
            content = json.dumps(content, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'none'; connect-src 'self'; form-action 'none'")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path in ['/', '/index.html']:
            return self.responder(200, HTML, 'text/html; charset=utf-8')
        if self.path == '/api/status':
            try:
                cfg = ler_config()
                return self.responder(200, {'provedor': cfg.get('provedor'),
                                            'modelo': cfg.get('modelo'), 'ok': True})
            except THIGASError as exc:
                return self.responder(400, {'erro': str(exc), 'ok': False})
        return self.responder(404, {'erro': 'Não encontrado'})

    def do_POST(self):
        if self.path != '/api/chat':
            return self.responder(404, {'erro': 'Não encontrado'})
        try:
            size = int(self.headers.get('Content-Length') or 0)
            if not (1 <= size <= 24000):
                return self.responder(413, {'erro': 'Mensagem muito grande ou vazia.'})
            dados = json.loads(self.rfile.read(size).decode('utf-8'))
            pergunta = dados.get('pergunta', '')
            if not isinstance(pergunta, str) or not pergunta.strip():
                return self.responder(400, {'erro': 'Digite sua pergunta.'})
            historico = dados.get('historico', [])
            if not isinstance(historico, list):
                historico = []
            wiki = bool(dados.get('wikipedia', True))
            saida = conversa(pergunta, ler_config(), historico, buscar=wiki)
            return self.responder(200, saida)
        except (ValueError, UnicodeError, TypeError):
            return self.responder(400, {'erro': 'JSON inválido.'})
        except THIGASError as exc:
            return self.responder(502, {'erro': str(exc)})

    def log_message(self, format, *args):
        # Não registrar perguntas nem nomes de arquivos sensíveis.
        pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--porta', type=int, default=8173)
    args = ap.parse_args()
    ler_config()  # exige configurar antes
    if not (1024 <= args.porta <= 65535):
        ap.error('A porta precisa ficar entre 1024 e 65535.')
    server = ThreadingHTTPServer(('127.0.0.1', args.porta), Handler)
    print(f'THIGAS AI nano — abra no celular: http://127.0.0.1:{args.porta}', flush=True)
    print('O servidor fica disponível apenas neste aparelho. Ctrl+C para parar.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nEncerrando.')
    finally:
        server.server_close()

if __name__ == '__main__':
    try:
        main()
    except THIGASError as exc:
        print('Erro:', exc)
        raise SystemExit(1)
