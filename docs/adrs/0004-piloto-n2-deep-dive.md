# ADR-0004 — Piloto N=2 (Döhler + Schulz) com soma ponderada no lugar de XGBoost no MVP

**Data:** 2026-05-07
**Status:** Aceito
**Decisor:** Osney Andrade de Souza Junior

## Contexto

O `docs/source/project.md` §2.1 dimensiona o MVP em 10 empresas de um único setor. A §8 propõe XGBoost com SHAP para risco de transição, com critério de aceitação `AUC > 0.75 out-of-time, Brier < 0.20`.

O usuário decidiu fazer o piloto com **duas empresas industriais sediadas em Joinville/SC**:

- **Döhler S.A.** — setor têxtil (cama/mesa/banho). Capital fechado (a confirmar formalmente). Implica fontes de dado financeiro/ESG limitadas — sem CVM/B3, dependendo de relatórios voluntários, GHG Protocol BR, CDP (se reportar), CNAE/CNPJ públicos.
- **Schulz S.A.** — compressores e autopeças. Capital aberto (B3: SHUL3/SHUL4). Fontes públicas amplas.

Com N=2, modelos tabulares aprendidos (XGBoost, LightGBM, regressão logística calibrada) são estatisticamente inviáveis: não há amostra suficiente para treino+validação out-of-time, e qualquer cross-validation degenera.

## Decisão

1. **Risco físico:** mantido conforme `project.md` §8. É determinístico (overlay raster × ativo); independe de N.
2. **Risco de transição no MVP:** **substituir XGBoost por soma ponderada calibrada** com bandas de incerteza explícitas. Pesos derivados de literatura (NGFS, TCFD scenarios) e validados contra benchmarks externos (peers do mesmo setor com dados públicos amplos).
3. **Profundidade > largura:** o esforço economizado em ML é redirecionado para análise aprofundada por empresa: mapa de ativos por município de SC, exposição por planta, narrativa por cenário, comparação histórica vs. projetada.
4. **XGBoost reaparece na F3 Beta**, quando a cobertura setorial expandir e N for compatível com a métrica de aceitação original.

## Justificativa

- O próprio `project.md` §2.2 princípio 5 autoriza: "soma ponderada calibrada antes de XGBoost". Estamos exercendo esse princípio, não o violando.
- Bandas de incerteza (princípio §2.2.4) ficam mais honestas em soma ponderada do que num XGBoost com 2 amostras.
- A arquitetura E2E (ingestão → silver/gold → score → API → dashboard) é exercida igualmente; só o componente de aprendizagem é adiado.

## Consequências

- O critério de aceitação `AUC > 0.75 out-of-time, Brier < 0.20` da §8 **não se aplica ao MVP**. Substituído por:
  - **Estabilidade trimestral** do score sob recálculo (variação < 5% sem mudança metodológica).
  - **Coerência de sinal** com eventos materiais conhecidos (ex.: enchente de 2017 em Joinville deve aumentar score físico das duas empresas).
  - **Banda de incerteza** sempre explícita (`score_low`, `score_high`).
- O módulo `climate_esg.modeling.transition_risk` no MVP exporta uma função determinística, não um modelo treinado. Persistência de "model run" continua igual (`dim_model_run`, `run_sk`), com `model_name='weighted_sum'` e versão bumped a cada recalibração de pesos.
- Escolha de Döhler exige lista alternativa de fontes de dado de transição: ver `docs/runbooks/data_sources_dohler.md` (a criar na F1).

## Alternativas consideradas

- **Tentar XGBoost com peers como dados sintéticos:** rejeitado. Inflar amostra com peers de outro perfil setorial (Döhler têxtil + Schulz autopeças não compartilham peers óbvios) é receita para overfit imperceptível.
- **Manter setor único de 10 empresas (agronegócio B3):** rejeitado pela decisão do usuário.
- **Usar regressão logística penalizada com priors fortes:** considerado, mas equivalente conceitual à soma ponderada com complexidade extra que não compensa em N=2.

## Revisão

Reavaliar quando: (a) cobertura subir para N≥30 com diversidade setorial; (b) houver target observável (perda reportada, restatement, evento material) que dê sinal de aprendizagem.
