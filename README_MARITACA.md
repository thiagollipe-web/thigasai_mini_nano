# THIGAS AI nano + Maritaca AI (v0.3.1)

Integração ao projeto **THIGAS AI nano** para conversar em português consultando artigos da Wikipédia.

O modelo de resposta é o Sabiá da Maritaca AI **na nuvem**; o nanoGPT v0.2 continua separado e não é treinado por essas conversas. Não existe chave de API incluída no pacote.

## Instalação (Termux normal, não Ubuntu/PRoot)

1. Baixe `THIGAS_AI_nano_Wikipedia_Maritaca_v03_1.zip` para Downloads.
2. Execute no Termux:

```bash
pkg install -y python unzip
mkdir -p ~/THIGAS_AI_nano_wikipedia
unzip -o ~/storage/downloads/THIGAS_AI_nano_Wikipedia_Maritaca_v03_1.zip -d ~/THIGAS_AI_nano_wikipedia
cd ~/THIGAS_AI_nano_wikipedia
python3 configurar.py
```

Se o Termux ainda não tiver acesso ao armazenamento, execute `termux-setup-storage` e aceite a permissão. A atualização não inclui `config.local.json` e não remove a configuração anterior, mas reconfigure-a para a Maritaca.

Escolha **6. Maritaca AI**, mantenha o modelo `sabia-4` ou digite o modelo disponível na sua conta, e informe a chave **somente no prompt do Termux**. A URL é preenchida automaticamente: `https://chat.maritaca.ai/api/chat/completions`.

O configurador oculta a digitação e salva `config.local.json` com permissão 0600. A chave é armazenada como texto simples no dispositivo e enviada apenas à API da Maritaca. Não publique o arquivo ou seu conteúdo.

## Testes

```bash
bash teste_wiki.sh
bash teste_api.sh
bash iniciar.sh --pergunta 'Quem foi Ada Lovelace?'
bash abrir_web.sh
```

O teste da Wikipédia não chama a API paga. Os outros podem consumir seus créditos da Maritaca. Ao iniciar a interface, abra `http://127.0.0.1:8173` no navegador do mesmo celular.

Se desejar testar sem consulta à Wikipédia: `bash iniciar.sh --sem-wiki --pergunta 'Diga olá em português.'`.

## Problemas comuns

- **HTTP 401/403:** chave inválida, inativa ou sem permissão.
- **HTTP 400/404:** modelo digitado incorretamente ou parâmetros incompatíveis. Experimente `sabia-4`, se disponível.
- **HTTP 402/429:** verifique créditos, restrições e limites da conta.
- **Erro Wikipédia:** a resposta ainda pode ser gerada, mas sem comprovação pela fonte consultada. Confira conexão e `User-Agent`.
- **Não abre 127.0.0.1:8173:** mantenha `bash abrir_web.sh` rodando numa sessão do Termux.

## Segurança e custos

A API recebe sua pergunta, histórico recente e trechos dos artigos; a Wikipédia recebe o texto da busca. Não envie dados pessoais de alunos nem segredos. O custo depende do plano, dos tokens e do modelo selecionado. Para mais informações, consulte as [instruções oficiais da Maritaca](https://docs.maritaca.ai/pt/api/openai-compatibilidade).
