## Histórico lateral de conversas (v0.9)

No computador, o **histórico aparece à esquerda**, organizado por Hoje, Ontem,
Últimos 7 dias, Últimos 30 dias e Anteriores. No celular, abra ou feche o menu
com o botão ☰ no cabeçalho. Recursos: **Nova conversa**, busca local por título
ou mensagem, reabrir conversas, renomear, excluir individualmente e apagar todo o
histórico com confirmação. Os títulos são gerados a partir da primeira pergunta.

As conversas são persistidas **somente no armazenamento local do navegador/PWA**;
não são sincronizadas com outros aparelhos, não ficam em banco de dados no Render,
e podem desaparecer se os dados do site forem apagados ou o modo privado for usado.
O histórico é armazenado em texto simples no próprio dispositivo e poderá ser
visto por quem usar o mesmo perfil do navegador. Evite inserir dados pessoais
sensíveis, especialmente dados de estudantes. O aplicativo preserva somente
mensagens, links públicos de fontes e preferências de esforço/Wikipédia.
**Arquivos, imagens e textos extraídos de documentos/sites não são persistidos**;
eles precisam ser anexados novamente ao reabrir a conversa. Por espaço e
desempenho, o histórico é limitado às 80 conversas e 70 mensagens mais recentes
por conversa, sujeito à cota de armazenamento do navegador.

## Chat com esforço, microfone, anexos e atalhos (v0.8)

A interface foi redesenhada como uma conversa única. Não há mais abas grandes de
Nano/Mini nem controle de "nível de pensamento"; existe um seletor de **Esforço**
no campo de mensagem:

- **Rápido**: mensagens concisas, perfil Nano.
- **Equilibrado**: explicações em linguagem natural, perfil Mini.
- **Alto**: solicita mais detalhamento, exemplos e ressalvas, com teto de tokens maior.

**Transparência:** o esforço ajusta o formato e o limite das respostas do
modelo configurado, não garante raciocínio interno adicional nem troca
automaticamente o provedor. Respostas longas podem consumir mais créditos.

O botão **+** abre anexos de documento, **imagem PNG/JPEG (OCR de texto)**,
análise de site HTTPS e busca opcional na Wikipédia. O anexo de imagem é
redimensionado no navegador para caber no limite de 950 KB e enviado ao servidor
no momento da pergunta; é encaminhado à API configurada, sem ser salvo no Render.
A leitura de imagem via API extrai sobretudo caracteres legíveis, e **não faz
análise visual completa de fotografias**. Imagens enviadas podem gerar custos
conforme o provedor. O microfone usa a API de reconhecimento de fala do
navegador, pode pedir permissão, pode não existir em todos os dispositivos e
apenas preenche a caixa de texto; nunca envia uma mensagem sem confirmação.

Digite \`@\` para buscar **@wikipedia, @arquivo, @imagem, @site** e \`/\` para
**/resumir, /explicar, /pesquisar, /codigo, /limpar, /ajuda**. Os comandos
aparecem em um menu de sugestões operável pelo toque ou teclado. O histórico
da conversa fica somente na aba atual, e a escolha de esforço é salva no
navegador. Nada de conteúdo privado entra no cache offline do PWA.

# THIGAS AI — Nano rápido + Mini elaborado | Render

Portal web protegido por senha, com dois **estilos de resposta** sob a identidade THIGAS AI:

- **THIGAS nano:** respostas curtas, diretas e objetivas; consulta à Wikipédia em português disponível opcionalmente.
- **THIGAS mini:** explicações mais elaboradas, com contexto, exemplos e etapas quando necessário.

Ao entrar pela primeira vez em `/`, o visitante escolhe: **"Você prefere respostas rápidas ou mais elaboradas?"**. O modo pode ser alterado a qualquer momento pelos botões superiores. Somente essa escolha de estilo fica salva no navegador; o histórico da conversa não persiste após recarregar a página.

## Documentos e análise de sites (v0.7)

No chat, após escolher Nano ou Mini, use **Anexar documento** ou **Analisar site**.
São aceitos PDFs textuais (até 25 páginas), DOCX, TXT, Markdown e CSV, com
**limite de 1,5 MB por arquivo**. A extração utiliza até **12 mil caracteres**.
PDFs digitalizados/escaneados não dispõem de OCR. Para páginas online, são
aceitas URLs **HTTPS públicas** em HTML ou texto; sites que exigem login, fazem
carregamento por JavaScript ou bloqueiam robôs podem não funcionar.

Cada modo mantém somente **um contexto ativo por vez**, guardado na memória do
navegador durante a sessão. Trocar o anexo substitui o anterior; **Remover anexo**
apaga o contexto selecionado. Não há biblioteca persistente de documentos.

**Privacidade:** o servidor extrai o texto e o devolve ao navegador. Quando você
envia uma pergunta com um documento ou site anexado, o trecho utilizado é enviado
à API de geração de respostas configurada pelo administrador. Não envie documentos
sigilosos nem dados de alunos sem autorização e base legal adequada. As consultas
à Wikipédia continuam independentes.

**Marca:** o arquivo SVG em assets/capivara.svg é uma adaptação vetorial criada a
partir da referência visual da capivara. Para reproduzir o desenho PNG original
exatamente, será necessário adicioná-lo ao repositório e ajustar o caminho no HTML.

## Instalar como aplicativo PWA (Android e iPhone)

O THIGAS AI funciona como um **Progressive Web App**. Abra
https://thigas-mini-nano.onrender.com em um navegador e faça login.

- Android (Chrome/Brave): toque em **Instalar app** quando aparecer ou use
  o menu do navegador **Instalar app / Adicionar à tela inicial**.
- iPhone (Safari): use **Compartilhar > Adicionar à Tela de Início**.
- Depois da instalação, um ícone com a capivara abrirá o THIGAS AI em janela
  independente, sem a barra de endereço do navegador.

O PWA precisa de **internet para conversar**. Em falhas de conexão, exibe
uma página offline que convida a reconectar. Por segurança, não cacheia
a interface HTML autenticada, respostas, documentos, anexos, tokens ou
chaves. O login HTTP Basic pode ser solicitado ao abrir a versão instalada.

Ícones PNG de 180, 192 e 512 px e variante maskable são gerados
automaticamente de `assets/capivara.svg` por
`.github/workflows/pwa-icons.yml`. Não expor credenciais no manifesto.

## Informação técnica para o administrador

O nome do provedor de IA e o identificador do modelo **não aparecem na interface**, na API pública de status nem nas mensagens de erro apresentadas pelo site. A chave de acesso nunca é enviada ao navegador. Ainda assim, a arquitetura deve ser descrita com transparência se houver uma pergunta técnica direta.

Por padrão, **ambos os estilos usam a mesma API externa da Maritaca AI**, com `sabiazinho-4-br-sp`: são perfis de resposta distintos, **não dois modelos locais GGUF diferentes**. O Nano reduz o limite de tokens de saída, enquanto o Mini usa limite maior e orientações para detalhar. O usuário pode escolher a extensão e o propósito da resposta, sem garantia contratual de tempo de resposta. O Mini pode ser ligado a um backend próprio somente quando um servidor remoto autenticado estiver disponível. O Render gratuito não executa automaticamente os arquivos GGUF produzidos no Termux. Uma API paga continua consumindo créditos quando utilizada.

## Publicar no Render (sem computador)

1. Utilize o repositório existente [thiagollipe-web/thigasai_mini_nano](https://github.com/thiagollipe-web/thigasai_mini_nano). **Ele é público**: nunca envie chaves, senhas nem `config.local.json`. O projeto já inclui os arquivos na raiz, incluindo `render.yaml`, `web_cloud.py`, `index.html`, `requirements.txt` e `thigas_wiki.py`.
2. Em <https://dashboard.render.com/>, escolha **New > Blueprint**. Autorize o acesso ao repositório e selecione o plano **Free**.
3. Defina no Render as variáveis privadas `MARITACA_API_KEY` (a sua chave) e `THIGAS_SITE_PASSWORD` (senha **diferente** da chave, com pelo menos 12 caracteres). Elas não devem estar no GitHub. **Nunca copie `config.local.json` para o repositório.**
4. Quando o serviço estiver ativo, entre no endereço HTTPS fornecido pelo Render, com usuário `thigas` e a senha `THIGAS_SITE_PASSWORD`.
5. Na tela inicial, escolha **THIGAS nano — respostas rápidas** ou **THIGAS mini — respostas elaboradas**.

O nome do endereço público será definido pelo Render. Não presuma que um subdomínio esteja livre.

### Usando Termux para enviar os arquivos

Baixe `THIGAS_AI_Mini_Nano_Respostas_v06.zip` para Downloads e execute **fora do Ubuntu PRoot**:

```bash
pkg install -y git gh unzip python
termux-setup-storage
mkdir -p ~/thigas-site-render
unzip -o ~/storage/downloads/THIGAS_AI_Mini_Nano_Respostas_v06.zip -d ~/thigas-site-render
cd ~/thigas-site-render
python3 -m unittest discover -s tests -q
gh auth login
git init
git branch -M main
git add .
git commit -m "THIGAS AI nano rapido e mini detalhado"
git remote add origin https://github.com/thiagollipe-web/thigasai_mini_nano.git
git push -u origin main
```

Se o comando `git commit` solicitar identidade, configure `git config --global user.name` e `git config --global user.email`. Se o repositório remoto já tiver commits, faça `git clone` primeiro em vez de `git init`, para evitar histórico divergente. Novas alterações devem ser enviadas por commit/push normalmente.

## Configuração manual do Web Service (alternativa ao Blueprint)

- Runtime: **Python**, versão especificada em `.python-version`.
- Comando de build: `pip install -r requirements.txt`
- Comando de inicialização: `python3 web_cloud.py`
- Health check: `/health`
- Environment obrigatórias: `THIGAS_CLOUD_MODE=1`, `MARITACA_API_KEY`, `THIGAS_SITE_PASSWORD`.
- Environment opcionais: `MARITACA_MODEL=sabiazinho-4-br-sp`, `THIGAS_SITE_USER=thigas`, `THIGAS_MAX_REQUESTS_HOUR=20`, `THIGAS_NANO_MAX_TOKENS=220`, `THIGAS_MINI_MAX_TOKENS=800`, `THIGAS_WIKI_CONTACT`.

### Backend Mini próprio (opcional)

Se hospedar o GGUF do seu Mini em **outro servidor público HTTPS com autenticação**, configure:

```text
THIGAS_MINI_UPSTREAM_URL=https://seu-servidor/v1/chat/completions
THIGAS_MINI_API_KEY=token-do-servidor-remoto
THIGAS_MINI_MODEL=THIGAS_AI_mini
```

O localhost (`127.0.0.1`) do seu Termux não é acessível ao Render. **Nunca exponha um llama-server doméstico sem autenticação e HTTPS.** Sem endpoint remoto, o Mini usa o serviço externo configurado, com o estilo elaborado.

## Segurança, custos e limitações

- Autenticação HTTP Basic em todo o conteúdo e na API de chat. Use somente HTTPS no acesso remoto.
- O limite global padrão é 20 perguntas por hora e até duas chamadas simultâneas, mantidas em memória. Reinícios limpam o contador; não é um limite financeiro confiável. Defina limites de gasto no painel da sua API, caso disponíveis.
- Não divulgue credenciais em conversas, prints ou repositórios. Para alunos e terceiros, considere autenticação individual e controle de cotas no futuro.
- Históricos são mantidos apenas na página aberta. Pesquisas feitas no modo Nano podem consultar a Wikipédia online. O conteúdo da Wikipédia serve como fonte, não como instrução.
- O modo Nano costuma ser mais sucinto, mas uma pesquisa externa pode torná-lo mais lento do que o Mini.
- Render Free pode suspender a aplicação ociosa; o primeiro acesso após inatividade pode demorar.
- O modelo THIGAS AI nano v0.2 treinado do zero e seu GGUF **não são alterados** por este aplicativo.

## Teste local

```bash
python3 -m unittest discover -s tests -v
THIGAS_CLOUD_MODE=1 THIGAS_SITE_PASSWORD='senha-de-testes-forte' MARITACA_API_KEY='ficticia' PORT=8173 python3 web_cloud.py
```

Abra `http://127.0.0.1:8173` para visualizar a tela (o chat com chave fictícia não responderá). Os testes usam respostas simuladas e **não consomem créditos**.

## Documentação de referência

- <https://render.com/docs/free>
- <https://render.com/docs/blueprint-spec>
- <https://docs.maritaca.ai/pt/api/openai-compatibilidade>
