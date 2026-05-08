# ADR-0001 — Monorepo único, repositório privado, licenciamento proprietário

**Data:** 2026-05-07
**Status:** Aceito
**Decisor:** Osney Andrade de Souza Junior

## Contexto

A proposta original (`docs/source/project.md` §4.1) recomenda monorepo na fase inicial, sem definir o regime de licenciamento. A §13 deixa essa definição como decisão pendente.

## Decisão

1. O projeto é um **monorepo** Python+R+TypeScript em um único repositório git.
2. O repositório é **privado** desde o dia 1.
3. Todo o código é **proprietário** — sem licença open-source. Não há `LICENSE` no formato OSI; apenas aviso `All Rights Reserved` no `README.md` e em headers de fonte se for julgado necessário.
4. Documentação e ADRs **não são publicados externamente**.

## Justificativa

- Monorepo reduz fricção em fase inicial (CI única, refactors atravessando módulos sem coordenação).
- Licenciamento fechado preserva o diferencial competitivo dos modelos e fórmulas de score, que são parte do valor entregue ao cliente.
- A decisão pode ser revertida em uma direção (parte da infra virar Apache 2.0) com facilidade; o caminho contrário (publicar e depois fechar) é virtualmente impossível.

## Consequências

- Sem benefício de "vitrine open-source" (atração de colaboradores, credibilidade junto a reguladores que valorizam código auditável).
- Necessidade de mecanismos próprios para auditabilidade externa quando exigida por clientes (provisão de model cards, relatórios de validação).
- Headers proprietários nos arquivos fonte ficam **opcionais por enquanto** — adicionar no momento de onboarding do primeiro cliente externo.

## Alternativas consideradas

- **Híbrido (Apache 2.0 infra + proprietária modelos):** rejeitado por gerar ambiguidade sobre o que é "infra" vs. "modelo" e por exigir disciplina de fronteira entre módulos que ainda não temos.
- **Tudo open (Apache 2.0):** rejeitado pelo motivo de competitividade acima.

## Revisão

Reavaliar quando: (a) houver demanda de cliente regulado por código auditável aberto; (b) o pipeline F0/F1 estiver suficientemente maduro a ponto de a infra ser separável dos modelos com baixo custo.
