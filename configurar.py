#!/usr/bin/env python3
"""Assistente de configuração segura: armazena a chave em JSON local (modo 0600)."""
import getpass
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / 'config.local.json'
SERVICOS = {
    '1': ('openrouter', 'openai/gpt-4o-mini'),
    '2': ('openai', 'gpt-4o-mini'),
    '3': ('gemini', 'gemini-2.5-flash'),
    '4': ('compat', ''),
    '5': ('local', 'thigas-local'),
    '6': ('maritaca', 'sabia-4'),
}

def pedir(campo, padrao):
    valor = input(f'{campo} [{padrao}]: ').strip()
    return valor or padrao

def main():
    print('\nTHIGAS AI nano — configurar conversa + Wikipédia')
    print('1. OpenRouter (API paga)\n2. OpenAI (API paga)\n3. Gemini (API paga)')
    print('4. Outra API compatível com OpenAI\n5. llama.cpp LOCAL (sem pagar API)')
    print('6. Maritaca AI (modelo Sabiá; API paga)')
    opcao = input('Selecione 1-6: ').strip()
    if opcao not in SERVICOS:
        print('Opção inválida. Execute novamente.'); return
    provedor, exemplo_modelo = SERVICOS[opcao]
    if provedor == 'maritaca':
        print('Endpoint oficial: https://chat.maritaca.ai/api/chat/completions')
        print('Sugestão: sabia-4 (conversa geral); sabia-4-thinking (raciocínio).')
    modelo = pedir('Nome EXATO do modelo habilitado na sua conta', exemplo_modelo)
    if not modelo:
        print('O nome do modelo é obrigatório.'); return
    url = ''
    if provedor == 'compat':
        url = input('URL COMPLETA do endpoint /chat/completions (HTTPS): ').strip()
    elif provedor == 'local':
        url = pedir('URL completa do seu llama-server', 'http://127.0.0.1:8092/v1/chat/completions')
    from thigas_wiki import validar_url, THIGASError
    if url:
        try:
            validar_url(url)
        except THIGASError as exc:
            print(exc); return
    chave = ''
    if provedor != 'local':
        print('Sua chave ficará SOMENTE em config.local.json neste dispositivo.')
        chave = getpass.getpass('Chave da API (não aparece na tela): ').strip()
        if not chave:
            print('Você pode configurar a chave depois, definindo THIGAS_API_KEY no ambiente.')
    contato = input('E-mail/URL de contato para User-Agent da Wikipédia (opcional): ').strip()[:100]
    cfg = {'provedor': provedor, 'modelo': modelo, 'api_url': url,
           'api_key': chave, 'contato_wikipedia': contato,
           'temperatura': 0.35, 'max_tokens': 400}
    fd = os.open(str(CONFIG), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.chmod(CONFIG, 0o600)
    print('\nConfiguração salva. NÃO compartilhe config.local.json.')
    print('Próximos comandos:')
    print('python3 thigas_wiki.py --wiki "Albert Einstein"')
    print('python3 thigas_wiki.py --teste-api  # pode gerar custo')
    print('python3 thigas_wiki.py')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nCancelado.')
