# ADR-0003 — Prefect 3 como orquestrador no lugar de Airflow

**Data:** 2026-05-07
**Status:** Aceito
**Decisor:** Osney Andrade de Souza Junior

## Contexto

O `docs/source/project.md` §3.1 e §4 prevê **Apache Airflow** como orquestrador de pipelines, com DAGs em `pipelines/dags/`. A escolha pressupunha Airflow rodando em container (ADR-0002 elimina essa premissa).

Sem Docker, Airflow exige: instalação via pip num venv dedicado, configuração manual de scheduler+webserver via `airflow standalone`, banco de metadata separado, gestão de Fernet key, e cuidados com versões de provider packages. Para um piloto com poucos pipelines em uma única máquina, isso é peso desproporcional.

## Decisão

Substituir Airflow por **Prefect 3** em todo o MVP.

- Pipelines vivem em `pipelines/flows/` como funções Python decoradas com `@flow` e `@task`.
- Deployments declarados em `pipelines/deployments/prefect.yaml`.
- Server Prefect roda localmente em `:4200` via `prefect server start`.
- Workers via `prefect worker start --pool default --type process`.

## Justificativa

- Prefect 3 instala como pacote pip único, sem orquestração separada.
- DAGs Python puro: o mesmo arquivo é executável, testável e agendável, sem distinção entre DAG e tarefa de runtime.
- Schedules cron-like, retries e observabilidade nativas, suficientes para o MVP.
- A migração futura para Airflow (ou outro) é viável: a lógica de cada flow está em funções importadas de `climate_esg.*`, o decorador é casca fina.

## Consequências

- Diverge da §3.1 do `project.md`. O documento autoritativo (`project.md`) **não é editado** — a divergência fica documentada aqui.
- Curva de aprendizagem: equipes vindas de Airflow precisam reaprender retry/timeout/scheduling.
- Não há equivalente direto de `XComArg` — passagem de dados entre tasks usa retorno de função normal ou storage no data lake (preferido para volumes grandes).
- Operadores customizados Airflow (`plugins/`) viram funções Python comuns em `climate_esg.utils.*`.

## Alternativas consideradas

- **Airflow standalone nativo:** rejeitado pelo overhead descrito acima.
- **Scripts Python + cron/systemd:** rejeitado por perder retries e UI de observabilidade que serão úteis a partir da F1.
- **Dagster:** mais alinhado com mentalidade software-defined-assets, mas peso de adoção é maior. Reavaliar no GA.

## Revisão

Reavaliar no início da F3 Beta, quando volume de pipelines, dependência inter-equipe e necessidade de SLA mais rígido podem mudar o cálculo.
