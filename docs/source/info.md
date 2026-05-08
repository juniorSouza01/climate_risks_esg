# Documento Técnico

## Plataforma de Análise de Riscos Climáticos para ESG

**Arquitetura de IA híbrida para suporte à decisão de investimento**

Versão 1.0 — Proposta de arquitetura técnica
Autor: Osney Andrade de Souza Junior

---

## 1. Sumário executivo

Este documento descreve a arquitetura técnica de uma plataforma de análise de riscos climáticos voltada a investidores e acionistas, com foco em decisões ESG (Environmental, Social, Governance). O sistema combina dados climáticos, geoespaciais, financeiros e regulatórios para produzir, por empresa e por região, um mapa de riscos físicos e de transição que apoia o julgamento sobre alocação de capital.

A pergunta central feita por quem inicia um projeto deste tipo costuma ser: *"qual modelo eu uso, uma LLM, uma SLM ou uma rede neural?"*. A resposta tratada aqui é que nenhuma escolha única dá conta do problema. Trata-se de uma arquitetura híbrida em que cada componente é escolhido pelo tipo de dado e pela natureza da pergunta: modelos de séries temporais para projeções climáticas, modelos de gradient boosting para scoring tabular, modelos geoespaciais para exposição física, e LLMs para extração de informação não estruturada e geração de relatórios. A integração é o que entrega valor, não um modelo isolado.

O documento cobre escopo, taxonomia de riscos, fontes de dados, arquitetura de modelos, pipeline de engenharia, governança, métricas de avaliação e roadmap de implementação. O produto final entregue ao acionista é um painel interativo com scores de risco, cenários e justificativas auditáveis.

---

## 2. Contexto e escopo do problema

### 2.1. Motivação

Reguladores como a TCFD, ISSB (IFRS S2), CDP e SEC vêm exigindo que empresas listadas reportem riscos climáticos materiais. Investidores institucionais incorporam esses riscos em modelos de precificação e em mandatos ESG. O problema, do ponto de vista do acionista, é que esses dados estão dispersos, são heterogêneos, e raramente chegam de forma comparável entre empresas e regiões.

A plataforma proposta consolida essas informações e produz, para cada ativo investível, uma visão integrada de exposição climática, capacidade de adaptação e impacto financeiro projetado.

### 2.2. Personas e casos de uso

- **Acionista institucional**: avalia risco climático de carteira e compara empresas dentro de um setor.
- **Analista ESG**: investiga drivers de risco específicos de uma empresa ou região e produz teses de investimento.
- **Comitê de risco**: monitora exposição agregada e simula cenários (NGFS, IPCC SSP).
- **Gestor de relacionamento com investidores da empresa investida**: usa o output como insumo para diálogo de engajamento.

### 2.3. Taxonomia de riscos cobertos

A literatura padrão da TCFD divide riscos climáticos em duas grandes famílias, e a plataforma trata ambas explicitamente:

| Categoria | Subtipos | Exemplos de impacto |
|---|---|---|
| Risco físico agudo | Enchentes, ciclones, ondas de calor, incêndios florestais | Interrupção operacional, perda de ativos, ruptura de cadeia |
| Risco físico crônico | Aumento do nível do mar, estresse hídrico, mudanças de temperatura média | Queda de produtividade agrícola, custos de adaptação, realocação |
| Risco de transição: política | Precificação de carbono, banimento de combustíveis, exigências de reporte | Aumento de custo, compliance, stranded assets |
| Risco de transição: tecnológico | Substituição por renováveis, eletrificação, eficiência energética | Obsolescência, capex de adaptação, perda de market share |
| Risco de transição: mercado e reputação | Mudança de preferência de consumidor, exclusão de índices, litígio climático | Queda de receita, custo de capital, perda de licença social |

---

## 3. Arquitetura técnica de alto nível

A arquitetura é organizada em cinco camadas, do dado bruto até a entrega ao acionista. Cada camada tem responsabilidades isoladas, o que permite trocar implementações sem refazer o sistema.

### 3.1. Visão em camadas

| Camada | Função | Tecnologias sugeridas |
|---|---|---|
| 1. Ingestão | Coleta de fontes climáticas, geoespaciais, financeiras, regulatórias e de mídia | Airflow, Kafka, conectores REST e SFTP, scrapers controlados |
| 2. Armazenamento | Camadas bronze (raw), prata (limpo) e ouro (modelado), dados vetoriais e raster | Data lake (S3/GCS), Delta Lake, PostGIS, banco vetorial (pgvector, Weaviate) |
| 3. Modelagem | Modelos especializados por subproblema (ver seção 4) | PyTorch, XGBoost/LightGBM, Prophet/N-BEATS, Hugging Face, scikit-learn |
| 4. Orquestração de IA | LLM como camada de raciocínio, RAG para fundamentar respostas, agregação de scores | LangChain/LlamaIndex, modelo grande (LLM) + modelos pequenos (SLM) locais |
| 5. Apresentação | Dashboard, relatórios, API para integração com sistemas dos investidores | React, Mapbox/Deck.gl, FastAPI, exportação PDF/XLSX |

### 3.2. Princípio de design: modelos especializados orquestrados por LLM

O ponto mais importante da arquitetura: **a LLM não calcula o risco. Ela orquestra, interpreta e comunica.** O cálculo numérico fica com modelos especializados (séries temporais, gradient boosting, modelos geoespaciais), que são auditáveis, baratos de operar e bem entendidos por reguladores.

A LLM atua em três pontos: extração de informação não estruturada (relatórios anuais, notícias, regulamentações), composição de explicações em linguagem natural sobre por que um score é o que é, e como interface conversacional para o acionista fazer perguntas sobre a carteira. Esse desenho evita o erro comum de pedir à LLM para "calcular" risco, o que produz respostas plausíveis e erradas.

---

## 4. Escolha de modelos: LLM, SLM ou rede neural?

Esta é a pergunta-chave do projeto. A resposta direta é: **todos, mas para problemas distintos**. A tabela abaixo mapeia subproblemas a famílias de modelos, com justificativa técnica.

| Subproblema | Modelo recomendado | Por quê | Alternativas |
|---|---|---|---|
| Projeção climática local (temperatura, precipitação, vento) | Downscaling de modelos climáticos (CMIP6) + redes neurais convolucionais 3D ou modelos foundation climáticos (ex.: ClimaX, Pangu-Weather, GraphCast) | Dado raster, alta dimensionalidade, padrões espaço-temporais | LSTM, Transformers temporais |
| Risco físico de um ativo (planta, fazenda, loja) | Modelos de hazard físico + análise geoespacial (overlay raster x localização) | Problema espacial determinístico, não precisa de IA pesada | Random Forest geoespacial |
| Score de risco de transição da empresa | Gradient Boosting (XGBoost, LightGBM, CatBoost) sobre features tabulares | Dados tabulares mistos, alta interpretabilidade exigida (SHAP) | Regressão logística regularizada, redes tabulares (TabNet) |
| Extração de metas, emissões e compromissos de relatórios anuais e ESG | LLM com RAG e prompts estruturados (saída em JSON) | Texto livre, alta variabilidade, ganho de generalização da LLM | SLM fine-tuned (Phi, Llama 3 8B) para reduzir custo |
| Classificação de notícias e sinais de mídia (sentimento ESG, controvérsias) | SLM fine-tuned (BERT-like, FinBERT, ClimateBERT) | Volume alto, latência baixa, tarefa bem definida | LLM em zero-shot quando volume é menor |
| Projeção de impacto financeiro de cenários | Modelos econométricos (DCF ajustado, value-at-risk climático) + simulação Monte Carlo | Auditável, alinhado a NGFS e a métodos de finanças | Bayesian networks para incerteza |
| Geração de explicações e relatórios para o acionista | LLM + RAG fundamentando em dados internos | Geração de linguagem natural com citação de fonte | Templates determinísticos para casos críticos |
| Q&A conversacional do acionista sobre a carteira | LLM com agente que invoca ferramentas (consultas SQL, modelos de risco) | Interface natural, raciocínio multi-passo | BI tradicional (Looker, Tableau) |

### 4.1. Quando faz sentido SLM em vez de LLM

Modelos pequenos especializados (SLMs) entregam custo previsível, latência baixa e privacidade ao rodarem on-premise. São a escolha certa para tarefas de alto volume e bem delimitadas: classificação de notícias, NER em relatórios, detecção de tópicos. Modelos como ClimateBERT, FinBERT, ou variantes fine-tuned de Phi-3 ou Llama 3 8B costumam superar LLMs grandes nessas tarefas com fração do custo. A LLM grande fica reservada para tarefas abertas: síntese, raciocínio em múltiplos documentos, geração de relatório executivo.

### 4.2. Quando NÃO usar IA

Boa parte do problema é resolvido sem aprendizado de máquina: cálculo de exposição geográfica é álgebra de raster, scoring de transição pode ser uma soma ponderada calibrada, e cenários NGFS já vêm prontos como séries macroeconômicas. Uma armadilha comum nesses projetos é introduzir redes neurais onde uma planilha bem feita já resolve. A regra prática é: **comece com a abordagem mais simples que funciona, e só suba na complexidade quando houver ganho mensurável**.

---

## 5. Fontes de dados

A qualidade da plataforma depende mais dos dados do que dos modelos. As fontes abaixo são as referências canônicas no setor.

| Tipo | Fontes | Granularidade típica |
|---|---|---|
| Clima histórico | ERA5 (Copernicus), NOAA, INMET, NASA POWER | Grid 0.25°, horária ou diária |
| Projeções climáticas | CMIP6 (IPCC), CORDEX para downscaling regional | Cenários SSP1-2.6 a SSP5-8.5 |
| Cenários macro-financeiros | NGFS (Network for Greening the Financial System) | País / setor |
| Eventos extremos | EM-DAT, GDACS, Cemaden (Brasil), NOAA Storm Events | Ponto / polígono, datado |
| Hazard maps | Aqueduct (WRI), JBA, Munich Re, Climate Impact Explorer | Raster, retorno de período |
| Dados de empresa | CDP, Refinitiv, MSCI ESG, Sustainalytics, S&P Trucost, B3 ESG | Empresa / ano |
| Localização de ativos | OpenStreetMap, GLEIF, dados próprios da empresa investida | Ponto geográfico |
| Texto não estruturado | Relatórios anuais, formulários CDP, GRI, ISSB, notícias, mídia social | Documento / artigo |
| Regulação | CVM, SEC, ESMA, taxonomia europeia, planos NDC dos países | Jurisdição |

### 5.1. Cuidados de qualidade

- Reanálise climática (ERA5) tem viés conhecido em regiões tropicais, exigindo correção via observação local.
- Dados ESG auto-reportados pelas empresas são heterogêneos; é necessário cruzar com fontes independentes.
- Dados de localização de ativos raramente vêm completos e precisam de geocodificação inferida.
- Cenários climáticos têm incertezas estruturais; o sistema deve apresentar bandas de confiança e nunca um único número "correto".

---

## 6. Pipeline de dados e MLOps

### 6.1. Fluxo de processamento

O pipeline segue um padrão medalhão (bronze, prata, ouro), com pontos de validação automática a cada transição:

- **Bronze**: dados brutos versionados, sem transformação. Permite reprocessamento histórico.
- **Prata**: dados limpos, padronizados, com chave canônica de empresa (LEI, CNPJ) e geometria validada.
- **Ouro**: features prontas para modelo, agregadas por empresa, ativo, região e cenário.
- **Camada de feature store**: features compartilhadas entre treino e inferência, com versionamento.
- **Camada vetorial**: embeddings de documentos para RAG.

### 6.2. Treinamento e versionamento

- Experimentos rastreados em MLflow ou Weights & Biases.
- Modelos versionados em registry com metadados de dados, hiperparâmetros e métricas.
- CI/CD com testes de qualidade de dados (Great Expectations) e de regressão de modelo.
- Reprodutibilidade: dados, código e ambiente sempre congelados em conjunto (DVC, contêineres).

### 6.3. Inferência e atualização

- Cálculo diário de scores físicos e de mercado, com cache para chamadas pontuais.
- Reprocessamento mensal de scores de transição.
- Reprocessamento anual de cenários climáticos longos.
- Trigger por evento extremo: alerta automático quando hazard atinge ativo monitorado.

---

## 7. Modelo de scoring entregue ao acionista

O acionista não consome modelos, consome decisões. A camada de scoring traduz saídas técnicas em uma estrutura interpretável e comparável.

### 7.1. Estrutura do score

Cada empresa recebe um score composto por três pilares e um índice agregado, todos em escala 0–100, com cenários:

| Pilar | Composição | Peso típico |
|---|---|---|
| Risco físico | Exposição agregada de ativos a hazards (enchente, calor, vento, fogo, água) ponderada por receita ou capex | 35% |
| Risco de transição | Intensidade de carbono, alinhamento de metas (SBTi), capex em descarbonização, exposição setorial | 40% |
| Capacidade de adaptação | Governança ESG, qualidade de reporte, controvérsias, diversificação geográfica | 25% |

### 7.2. Score regional (ESG de localidade)

Em paralelo ao score por empresa, a plataforma produz um score por região, útil para decidir em qual jurisdição expandir, alocar capex ou desinvestir. Combina exposição climática agregada, qualidade institucional, infraestrutura e densidade de regulamentação ESG. Permite ao acionista responder à pergunta *"vale investir nessa região"*, e não apenas *"vale investir nessa empresa"*.

### 7.3. Cenários obrigatórios

- NGFS Net Zero 2050 — transição ordenada.
- NGFS Delayed Transition — transição desordenada.
- NGFS Current Policies — hot house world.
- IPCC SSP2-4.5 e SSP5-8.5 para riscos físicos.

Cada score é entregue para cada cenário e horizonte (2030, 2040, 2050), permitindo análise de sensibilidade explícita.

---

## 8. Interface do acionista

A camada de apresentação é o que diferencia uma boa plataforma técnica de uma plataforma realmente usada. O design parte de três telas principais:

### 8.1. Visão de carteira

- Heatmap de empresas por pilar e cenário.
- Distribuição de exposição setorial e geográfica.
- Alertas de eventos recentes que afetam empresas da carteira.

### 8.2. Drill-down por empresa

- Mapa de ativos com sobreposição de hazards.
- Decomposição do score com SHAP values e narrativa gerada por LLM com citação de fonte.
- Linha do tempo de eventos, controvérsias e compromissos.
- Comparação com pares do setor.

### 8.3. Análise regional

- Mapa coroplético com score regional por cenário.
- Decomposição do risco regional em fatores climáticos, regulatórios e socioeconômicos.

### 8.4. Conversa com o agente

Um agente conversacional baseado em LLM permite ao acionista perguntar em linguagem natural: *"qual empresa da minha carteira tem maior exposição a estresse hídrico em 2040 sob SSP5-8.5?"*. O agente decompõe a pergunta, consulta o banco analítico via ferramentas, e responde citando os dados que utilizou. Este é o ponto onde a LLM agrega valor mais visível, mas a resposta numérica vem dos modelos especializados.

---

## 9. Governança, ética e auditoria

### 9.1. Explicabilidade

Acionista institucional não aceita caixa-preta. Todo score precisa ter atribuição clara: SHAP em modelos tabulares, attention maps em modelos espaciais, citação de documento em respostas de LLM. A regra é que nenhuma decisão pode ser apresentada sem que o usuário consiga clicar e ver a evidência subjacente.

### 9.2. Risco de alucinação da LLM

- LLM nunca produz números finais; apenas extrai, resume e narra.
- RAG com base de conhecimento curada e citações obrigatórias.
- Validação automática de outputs estruturados via JSON Schema.
- Eval contínua com conjunto dourado de perguntas-respostas.

### 9.3. Bias e fairness

Dados ESG têm viés conhecido para empresas grandes em mercados desenvolvidos. O sistema documenta cobertura e disponibilidade de dado por empresa, evitando penalizar pequenas empresas em mercados emergentes simplesmente porque reportam menos. Quando o dado está ausente, o sistema sinaliza explicitamente em vez de imputar valores otimistas ou pessimistas.

### 9.4. Conformidade regulatória

- Alinhamento metodológico com TCFD e ISSB IFRS S2.
- Trilha de auditoria completa: linhagem de dado, versão de modelo, parâmetros.
- Documentação de modelo no padrão Model Cards.
- LGPD / GDPR para dados pessoais eventualmente coletados via mídia.

---

## 10. Avaliação e métricas

Métricas técnicas separadas por tipo de modelo e métricas de produto separadas por valor entregue ao acionista.

| Componente | Métrica primária | Limiar mínimo aceitável |
|---|---|---|
| Projeção climática local | RMSE e CRPS contra observações retidas | RMSE < 1,5°C para temperatura mensal |
| Modelo de transição (XGBoost) | AUC, calibração de Brier, estabilidade | AUC > 0,75 em validação out-of-time |
| Extração via LLM/SLM | Precision/Recall em conjunto anotado | F1 > 0,85 em campos críticos |
| Agente conversacional | Faithfulness e answer relevance (RAGAS) | Faithfulness > 0,9 com citação obrigatória |
| Score composto | Estabilidade temporal, correlação com retornos ajustados a risco | Variação trimestral controlada (sem saltos espúrios) |
| Produto | Adoção, perguntas por sessão, decisões registradas, NPS | Definir baseline pós-piloto |

---

## 11. Roadmap de implementação

Sugestão de divisão em fases curtas, com entregáveis incrementais que permitem validar a tese antes de investir em infraestrutura pesada.

| Fase | Duração | Escopo | Entregável |
|---|---|---|---|
| 0 — Discovery | 4 semanas | Entrevistas com acionistas, mapeamento de fontes, decisão de stack | Relatório de requisitos e arquitetura validada |
| 1 — MVP | 3 meses | 10 empresas piloto, score físico e de transição básico, dashboard estático | MVP demonstrável internamente |
| 2 — Beta | 3 meses | Cobertura setorial ampliada, cenários NGFS, RAG sobre relatórios anuais | Beta privado para investidor parceiro |
| 3 — GA | 4 meses | Agente conversacional, score regional, API de integração | Lançamento comercial |
| 4 — Evolução | Contínuo | Modelos foundation climáticos, fine-tuning de SLM próprio, expansão geográfica | Releases trimestrais |

---

## 12. Equipe mínima recomendada

- 1 arquiteto de dados / ML (líder técnico).
- 2 engenheiros de dados (pipeline, geoespacial).
- 2 cientistas de dados (séries temporais, tabular, NLP).
- 1 especialista em ML/LLM ops.
- 1 especialista de domínio em finanças sustentáveis (ESG/TCFD).
- 1 climatologista consultor (parcial).
- 1 designer de produto e 1 frontend para dashboard.
- 1 PM com background em finanças ou risco.

---

## 13. Principais riscos do projeto

- Subestimação do esforço de engenharia de dados — historicamente 60% do trabalho real está aqui, não nos modelos.
- Excesso de confiança em saídas de LLM em tarefas que exigem precisão numérica auditável.
- Falta de cobertura ESG para empresas pequenas e de mercados emergentes, gerando vieses no score.
- Mudanças regulatórias (ISSB, taxonomia local) que exigem reajuste metodológico.
- Custo de inferência de LLM em produção, mitigado por cache e uso de SLM em tarefas repetitivas.

---

## 14. Conclusão

O projeto descrito não é um "projeto de LLM" nem um "projeto de rede neural", e essa é a observação mais importante. É um sistema de suporte à decisão financeira em que a IA aparece em três papéis claros: modelos especializados que produzem scores auditáveis, modelos de linguagem pequenos para tarefas repetitivas de NLP, e LLMs como camada de raciocínio e comunicação. Cada componente é a melhor ferramenta para o seu subproblema.

Para o acionista, o entregável final é simples: um painel que diz, com evidência rastreável, qual o risco climático de cada empresa e região da carteira sob diferentes cenários. Para a equipe técnica, o entregável é uma plataforma de dados e modelos com governança suficiente para sobreviver a auditoria regulatória, e flexível o bastante para incorporar novas fontes e novos modelos à medida que a ciência climática e a IA evoluem.

Recomenda-se começar pequeno: dez empresas, dois cenários, um setor. Esse MVP, bem feito, é mais convincente para investidores e patrocinadores internos do que uma arquitetura completa em PowerPoint.