# THIGAS AI — Nano 0.3B / Mini 0.6B

## Pesos, parâmetros e contexto

- **Nano ~0.3B:** base HuggingFaceTB/SmolLM2-360M-Instruct, **361,8 milhões de parâmetros**, licença Apache-2.0. GGUF Q4_K_M, contexto configurado e testado de **2.048 tokens**.
- **Mini 0.6B:** base Qwen/Qwen3-0.6B, **aproximadamente 751,6 milhões de parâmetros reais** (o nome da família é 0.6B), licença Apache-2.0. GGUF Q4_K_M, contexto configurado e testado de **4.096 tokens**.

O pipeline usa os modelos-base pré-treinados. Faz **fine-tuning LoRA de identidade e instruções em português**, separa treinamento e validação, mescla os pesos, converte para GGUF e testa geração pelo llama.cpp. Não é treinamento do zero. Foram preparados 67 exemplos; o treinamento é curto e sua qualidade precisa de testes independentes. Janelas longas são herança da arquitetura pré-treinada, **não** resultado de treino em sequências de milhares de tokens.

Os GGUF e os relatórios de treinamento ficam em GitHub Releases **somente se os jobs concluírem com sucesso**:
- Release thigas-nano-03b-v1: THIGAS_AI_nano_03B_Q4_K_M.gguf
- Release thigas-mini-06b-v1: THIGAS_AI_mini_06B_Q4_K_M.gguf

## Windows — arquivo real testado no llama.cpp

Instale llama.cpp com llama-server disponível no PATH. Baixe o script THIGAS_03B_06B_Windows.ps1 desta pasta e execute no PowerShell:

    .\THIGAS_03B_06B_Windows.ps1 -Acao Baixar
    .\THIGAS_03B_06B_Windows.ps1 -Acao Verificar
    .\THIGAS_03B_06B_Windows.ps1 -Acao Iniciar

O script baixa os GGUF das Releases, verifica a integridade SHA-256 de cada arquivo e inicia dois servidores locais:
- Nano: http://127.0.0.1:8091, alias THIGAS_AI_nano_03B, contexto 2048.
- Mini: http://127.0.0.1:8092, alias THIGAS_AI_mini_06B, contexto 4096.

O script solicita um token privado que também precisa ser configurado no Render. Não publique esse token nem envie prints contendo-o.

## Site em Render Free: arquitetura que funciona

O serviço Render Free **não executa os dois GGUF na mesma instância** em memória. É necessário manter o Windows com os dois llama-server ligados, expondo cada um por uma conexão HTTPS segura (por exemplo túnel Cloudflare com domínio estável), ou contratar infraestrutura de inferência.

Para teste provisório, instale cloudflared e abra dois terminais PowerShell:

    cloudflared tunnel --url http://127.0.0.1:8091
    cloudflared tunnel --url http://127.0.0.1:8092

Cada comando produz um endereço HTTPS público temporário. Os subdomínios mudam a cada reinicialização; mantenha os túneis ativos. Os llama-server devem continuar com autenticação de API ativa. Para produção, use um túnel estável com controles adicionais.

Configure no painel Render > Environment, sem enviar chaves ao GitHub:

    THIGAS_NANO_UPSTREAM_URL=https://TUNEL-NANO/v1/chat/completions
    THIGAS_NANO_API_KEY=TOKEN_PRIVADO_DO_WINDOWS
    THIGAS_NANO_MODEL=THIGAS_AI_nano_03B
    THIGAS_NANO_MAX_TOKENS=600

    THIGAS_MINI_UPSTREAM_URL=https://TUNEL-MINI/v1/chat/completions
    THIGAS_MINI_API_KEY=TOKEN_PRIVADO_DO_WINDOWS
    THIGAS_MINI_MODEL=THIGAS_AI_mini_06B

O modo Rápido encaminha perguntas textuais ao Nano, e Equilibrado/Alto ao Mini. As imagens são textualmente processadas pela API de OCR externa já configurada porque os dois modelos locais são text-only. Enquanto essas variáveis não estiverem configuradas, o site mantém o motor externo anterior para conversar, sem alegar que o GGUF próprio já está ligado. Quando o Windows desligar, os modelos próprios deixam de responder.
