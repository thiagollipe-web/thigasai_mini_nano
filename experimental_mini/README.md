# THIGAS AI mini — experimento independente
Este branch é **experimental**, não modifica a versão do site Render na branch `main`.

## Atenção à proveniência
Não foi localizado o checkpoint do THIGAS AI Mini já treinado no Termux do usuário.
Este script treina **um modelo novo do zero** utilizando a arquitetura do
nanoGPT (licença MIT). O arquivo gerado NÃO representa o Mini anteriormente
treinado nem deve ser anunciado como uma IA conversacional pronta.

- Arquitetura: GPT-2 (6 camadas, 6 cabeças, embedding 288, 257 tokens byte-level).
- Treinamento demonstrativo com texto educacional curto/repetido em português.
- Saída: `models/THIGAS_AI_mini_experimental-6M-F16.gguf`.
- Verificação de aprendizagem: o job só publica se a loss de validação diminuir.
- O checkpoint PyTorch fica disponível como artefato do job GitHub Actions.

Nenhum arquivo desta branch é usado pelo site Render que roda em `main`.
