# THIGAS AI — Dossiê de projetos e plano de lançamento comercial
**Versão:** 1.0 — 11/10/2026  
**Status:** documento preparatório; não é certificado de registro, parecer jurídico ou comprovação definitiva de autoria.

## 1. Identificação e escopo
**Marca guarda-chuva proposta:** THIGAS AI / ThigasAI (disponibilidade no INPI ainda não confirmada).  
**Responsáveis informados:** Thiago Fillipe Soares e sua esposa, cuja conta GitHub é `mayracanellasoares-bot`. A identificação civil e a titularidade patrimonial de cada contribuição devem ser confirmadas documentalmente.  
**Objetivo:** organizar o inventário de ativos, identificar obrigações e lançar produtos de IA e música com monetização lícita no Brasil.

### Inventário
| Produto | Repositório | Situação técnica observada |
|---|---|---|
| THIGAS AI mini | https://github.com/thiagollipe-web/thigasai_mini_nano | Perfil de respostas detalhadas na aplicação web; por padrão API Maritaca. Modelo treinado separadamente requer evidências próprias. |
| THIGAS AI nano | mesmo repositório | Perfil de respostas curtas na aplicação web; o README menciona modelo nano v0.2 treinado do zero, distinto do serviço web. |
| THIGAS AI | https://github.com/mayracanellasoares-bot/ThigasAI | Gateway Flask/PWA e serviços de documentos, programação e links; inferência por provedores externos. |
| THIGAS Music | https://github.com/mayracanellasoares-bot/thigas_music | Aplicativo Flutter derivado do Musify, com identidade visual e modo foco. Licença GPL-3.0 incluída. |

**Atenção:** a existência dos repositórios demonstra publicações de código, não prova por si só titularidade exclusiva, disponibilidade de marca ou existência de pesos originais para cada nome comercial. Separar aplicativo, modelo-base, treinamento, pesos e API externa em toda comunicação.

## 2. Declaração preliminar de autoria e contribuições
Os envolvidos declaram, sujeitos à conferência e assinatura, que contribuíram para o desenvolvimento dos projetos identificados acima. As contribuições concretas, datas, fontes do código, colaboradores e licenças de terceiros serão discriminadas em anexo. Esta declaração não atribui automaticamente a Thiago os direitos patrimoniais dos repositórios mantidos na conta de sua esposa, nem transfere direitos de terceiros.

**Campos a preencher:** nome completo e CPF dos participantes (somente na versão privada); projeto; módulos criados; datas e commits; materiais de terceiros; autoria e titularidade; permissões de exploração; assinatura e data. Não inserir CPFs em repositórios públicos.

## 3. Checklist de provas
- Arquivar uma versão por tag/release, commit SHA, histórico de commits, READMEs, capturas de tela datadas e backups.
- Fazer inventário SBOM de dependências, marcas, modelos-base e datasets.
- Guardar provas de treinamento (scripts, checkpoints, configuração, origens dos dados e licença).
- Registrar hashes SHA-256 dos artefatos originais em uma ata privada assinada.
- Celebrar acordo escrito entre colaboradores sobre titularidade, licença comercial, divisão de receita, suporte e eventual saída da sociedade.
- Não publicar credenciais, dados pessoais, pesos restritos ou material protegido sem autorização.

## 4. Auditoria de licenças antes da venda
### THIGAS AI mini/nano
README indica que os perfis web Nano/Mini usam normalmente o modelo `sabiazinho-4-br-sp` via Maritaca; perfil de resposta não equivale a LLM independente. Confirmar contrato e custos da API. Verificar separadamente origem e licenciamento dos modelos próprios, arquivos GGUF, dados e treinamento.

### THIGAS AI
README identifica gateway Maritaca/Groq e PWA, não LLM autônoma. Divulgação precisa identificar que a plataforma usa infraestrutura e modelos de terceiros quando aplicável. Implementar proteção de chaves, limites por usuário, autenticação, rate limiting, faturamento e transparência de privacidade antes de cobrar. A documentação diz que a rota /chat é pública.

### THIGAS Music
README atribui o código-base ao Musify, desenvolvido por Valeri Gokadze e colaboradores. Repositório inclui texto GPL-3.0, que exige obrigações ao distribuir binários, entre elas disponibilizar o código-fonte correspondente sob os termos aplicáveis e preservar avisos. O README alerta para divergência entre restrição comercial mencionada pelo upstream e o texto GPL: esclarecer procedência e permissões antes da monetização. Investigar direitos de música, streaming, letras, capa e downloads; não confundir licença do software com licença do conteúdo musical.

## 5. Marca, empresa e proteção
1. Pesquisar gratuitamente THIGAS AI, ThigasAI e THIGAS Music e sinais similares na base do INPI; avaliar classes de serviços (especialmente 42), software baixável (9) e outras classes realmente pertinentes.
2. Marca requer pedido e taxa no INPI; a pesquisa e o uso de uma expressão não equivalem a registro nem garantem exclusividade. Pessoa física também pode requerer, observadas condições legais.
3. O direito autoral do código surge sem depósito, mas o registro de programa no INPI pode ajudar a provar autoria/titularidade; registro eletrônico é pago (portal federal atualmente informa R$ 210 para código 730).
4. Nome empresarial na Junta Comercial, domínio de internet e registro de marca são instrumentos distintos.
5. Lançamento beta gratuito geralmente não exige CNPJ. Para faturamento habitual, emissão de notas e contratação comercial, escolher enquadramento formal com contador. Verificar elegibilidade ao MEI, CNAEs de software e serviços, impostos e vínculo funcional do fundador antes da abertura.
6. Documentar políticas de privacidade, LGPD, termos do serviço, relação com provedores, direitos dos consumidores e tratamento de incidentes.

Fontes oficiais: https://www.gov.br/inpi/pt-br ; https://www.gov.br/pt-br/servicos/solicitar-o-registro-de-programa-de-computador ; https://www.gov.br/empresas-e-negocios/pt-br/redesim

## 6. Estratégia comercial inicial
**Proposta de valor:** assistente em português para programação, educação e documentos, com opção futura de uso de modelos locais; aplicativos complementares sob a marca.

**Oferta piloto:**
- Gratuito: demonstração pública com limitação por usuário, consentimento e políticas visíveis.
- Individual (preços a testar, não anunciados): assinatura com cota clara de mensagens/documentos e política de excedentes.
- Escolas e pequenas equipes: demonstrações e contratos específicos com requisitos LGPD, suporte, faturamento e controle de uso.
- THIGAS Music: validar licenciamento do projeto upstream e direitos de conteúdo antes de venda, publicidade ou assinatura; não incluir músicas protegidas sem autorização.

**Fórmula de preço:** custo variável por interação (tokens + anexos + OCR + operações) + hospedagem + atendimento + tributos + taxas de pagamento + margem. Definir teto de consumo e margens reais antes de criar checkout. Não prometer uso ilimitado se a inferência é faturada por terceiros.

**Canais:** landing page GitHub Pages, versão beta web PWA, demonstrações para professores e desenvolvedores, listas de interesse e conteúdo educativo. Não coletar dados de estudantes em testes sem fundamentação adequada.

## 7. Roteiro de 30 dias
**Dias 1–7:** preservar releases, inventariar autores/licenças, pesquisar marca, redigir acordo de colaboração, inspecionar credenciais e dependências.
**Dias 8–14:** termos de uso e política de privacidade, autenticação e limitação de custos, landing page e formulário de interesse.
**Dias 15–21:** beta com usuários adultos voluntários, métricas de uso, avaliações de qualidade e custo por sessão, testes de segurança.
**Dias 22–30:** validar pacote comercial e termos; decidir enquadramento empresarial/tributário e meios de cobrança; lançamento pago apenas com licenças, infraestrutura e condições regulares.

## 8. Critérios obrigatórios antes de cobrar
- [ ] Identificar titular de cada código, modelo e marca, com autorização escrita da esposa e demais colaboradores.
- [ ] Resolver licenças de modelos-base, datasets, provedores e do Musify.
- [ ] Implantar controle de custos e acesso, logs adequados e segurança.
- [ ] Publicar termos, privacidade, contato e política de cancelamento/reembolso.
- [ ] Definir formalização fiscal, emissão de nota e meio de pagamento.
- [ ] Confirmar que a oferta não confunde gateway com modelo próprio.
- [ ] Revisar marca no INPI e orçamento para registro futuro.

## 9. Declaração de limitações
Este documento foi elaborado a partir de arquivos README e licença disponíveis em 11/10/2026 e informações dos responsáveis; não constitui auditoria completa de código, perícia de autoria, clearance de marca, autorização para comercialização de músicas nem aconselhamento jurídico individual. Um profissional habilitado deve revisar contratos e tributos antes do lançamento pago.
