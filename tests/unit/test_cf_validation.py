"""Testes da validação de faixas físicas plausíveis (CF)."""

from __future__ import annotations

import pytest

from climate_esg.ingestion.cf_validation import PLAUSIBLE_RANGES, check_value_range


def test_tasmin_dentro_da_faixa_passa() -> None:
    # ~ -10 °C a 35 °C em Kelvin.
    check_value_range("tasmin", 263.15, 308.15)


def test_tasmin_abaixo_do_minimo_falha() -> None:
    with pytest.raises(ValueError, match="tasmin"):
        check_value_range("tasmin", 100.0, 300.0)


def test_tasmax_acima_do_maximo_falha() -> None:
    with pytest.raises(ValueError, match="tasmax"):
        check_value_range("tasmax", 280.0, 400.0)


def test_pr_negativa_falha() -> None:
    with pytest.raises(ValueError, match="pr"):
        check_value_range("pr", -0.001, 0.005)


def test_variavel_desconhecida_nao_bloqueia() -> None:
    # Variável fora do catálogo: passa sem erro (não trava o pipeline).
    check_value_range("xpto", -1e9, 1e9)


def test_faixas_sao_coerentes() -> None:
    for var, (lo, hi) in PLAUSIBLE_RANGES.items():
        assert lo < hi, f"faixa inválida para {var}: {lo} >= {hi}"
