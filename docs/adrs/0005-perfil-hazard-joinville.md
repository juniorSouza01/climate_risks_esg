# ADR-0005 — Perfil de hazard centrado em Joinville/SC; expansão de variáveis CMIP6

**Data:** 2026-05-07
**Status:** Aceito
**Decisor:** Osney Andrade de Souza Junior

## Contexto

A escolha de Döhler e Schulz (ADR-0004) concentra os ativos do MVP em **Joinville/SC** e municípios da região norte de Santa Catarina. O perfil de hazard climático dessa região é distinto do agronegócio brasileiro originalmente sugerido pelo `project.md` §13.

Os 10 scripts wget gerados no MetaGrid ESGF e arquivados em `data/manifests/cmip6_wget/` cobrem variáveis genéricas do EC-Earth3 historical: `tasmin`, `rsdt`, `hurs`, `huss`, `prsn`, `uo`, `sivol`. Algumas dessas variáveis (`prsn`, `sivol`, `uo`) são pouco relevantes para hazards industriais em SC.

## Decisão

### Hazards prioritários

| # | Hazard | Justificativa para Joinville/SC |
|---|---|---|
| 1 | **Enchentes** | Histórico forte de cheias do rio Cachoeira e bacia do Itapocu (2008, 2011, 2017). Ativos industriais em zonas baixas têm exposição direta. |
| 2 | **Deslizamentos** | Encostas com ocupação próxima a parques fabris; chuva intensa é o gatilho. Acoplado ao hazard 1. |
| 3 | **Ventos extremos** | Ciclones extratropicais e episódios convectivos severos crescentes. |
| 4 | **Calor extremo urbano** | Tendência de aumento de dias acima de 32°C em zonas industriais, afetando produtividade laboral e custos de resfriamento. |
| 5 | Estresse hídrico | Menor prioridade; SC industrial é raramente water-stressed em sentido agronômico. |

### Variáveis CMIP6 a usar / a obter

| Variável CF | Frequência | Prioridade | Já temos? |
|---|---|---|---|
| `pr` | day, Amon | **Crítica** (enchentes, deslizamentos) | **Não** — a baixar |
| `tasmax` | day, Amon | **Crítica** (calor extremo) | **Não** — a baixar |
| `tasmin` | day, Amon | Alta (extremos noturnos urbanos) | Sim (Amon historical) |
| `sfcWindmax` | day | Alta (ventos extremos) | **Não** — a baixar |
| `huss` / `hurs` | Amon | Média (estresse térmico) | Sim |
| `rsdt` | Amon | Baixa (uso indireto) | Sim |
| `prsn`, `sivol`, `uo` | qualquer | **Não usar** | Sim (manter em bronze, não promover) |

### Cenários CMIP6 a obter

A coleção atual cobre apenas `historical`. Para projeção de score em horizontes 2030/2040/2050 conforme `project.md` §2.1, precisamos:

- `historical` (calibração baseline) — temos.
- `ssp245` (intermediário) — **a baixar**.
- `ssp585` (alto) — **a baixar**.

### Membros / modelos

Manter EC-Earth3 como modelo principal. Considerar adicionar **MPI-ESM1-2-HR** ou **CMCC-ESM2** como modelo secundário para análise de incerteza inter-modelo (multi-model ensemble pequeno) na F2.

### Plano de execução

1. **F0 (agora):** smoke test bronze→silver→gold com `tasmin` historical já baixado. Suficiente para validar pipeline E2E sem depender de novos downloads.
2. **F0 → F1 (paralelo):** gerar nova requisição MetaGrid ESGF cobrindo `pr`, `tasmax`, `sfcWindmax` × `historical+ssp245+ssp585` × `EC-Earth3`. Arquivar em `data/manifests/cmip6_wget/` com prefixo `v2_`.
3. **F1:** ingestão da v2 + cálculo dos índices xclim relevantes (Rx5day, R99pTOT, TX90p, WSDI).
4. **F1+:** `fact_climate_indicator` populado com indicadores priorizados; índices de exposição por ativo de Döhler/Schulz.

### Dados auxiliares específicos para SC

Catalogar (não baixar tudo agora — só listar fontes a serem implementadas em F1):

- **ANA** — séries hidrológicas estações da bacia do Itapocu/Cachoeira.
- **CEMADEN** — alertas históricos de chuva e deslizamento em municípios de SC.
- **Defesa Civil SC** — registros oficiais de eventos (S2iD).
- **CPRM** — cartas de suscetibilidade a deslizamento para Joinville.
- **IBGE** — malha municipal, censo industrial, cadastro de empresas.
- **INMET** — estações automáticas para validação de regridding CMIP6 → grade local.

## Justificativa

- Sem variáveis adequadas, score físico fica pobre (não captura enchente nem calor extremo, que são os dois hazards dominantes da região).
- Cenários SSP são essenciais para os horizontes 2030/2040/2050; sem eles, só dá para fazer análise retrospectiva.
- O custo de ingerir uma segunda rodada de wget é baixo (algumas dezenas de GB extras); o benefício metodológico é grande.

## Consequências

- F0 pode prosseguir com dados atuais. Bom — não bloqueia início de código.
- F1 fica dependente da nova requisição ESGF. Risco de espera se o nó ESGF estiver instável; mitigado por baixar de múltiplos nós (Globus alternativo conforme `project.md` §7.4).
- O parser `esgf_client.py` precisa funcionar para qualquer wget script válido, não só os 10 atuais. Já está nesse desenho.

## Alternativas consideradas

- **Usar reanálise ERA5 no lugar de CMIP6 historical:** ERA5 é melhor calibrado historicamente, mas não dá projeção. Manter CMIP6 + considerar ERA5 como benchmark de validação na F1.
- **Pular projeção SSP, usar só historical:** rejeitado — contraria o escopo MVP da §2.1.

## Revisão

Reavaliar perfil de hazard se o piloto expandir para outras geografias (ADR específico por região quando isso ocorrer).
