from __future__ import annotations

import io
import zipfile

import pytest

from climate_esg.ingestion import cvm

CNPJ = "84.693.183/0001-68"
CNPJ_DIGITS = "84693183000168"

_DRE_HEADER = "CNPJ_CIA;DENOM_CIA;DT_REFER;ORDEM_EXERC;CD_CONTA;VL_CONTA;ESCALA_MOEDA"
_DFC_HEADER = "CNPJ_CIA;DENOM_CIA;DT_REFER;ORDEM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ESCALA_MOEDA"


def _dre_csv() -> str:
    rows = [
        _DRE_HEADER,
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;3.01;1000;MIL",
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;3.05;200;MIL",
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;3.11;100;MIL",
        f"{CNPJ};SCHULZ S.A.;2024-12-31;PENÚLTIMO;3.01;900;MIL",
        f"{CNPJ};SCHULZ S.A.;2023-12-31;ÚLTIMO;3.01;800;MIL",
    ]
    return "\n".join(rows)


def _dfc_csv() -> str:
    rows = [
        _DFC_HEADER,
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;6.01.01.02;Depreciação e Amortização;50;MIL",
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;6.01.01.02.01;Depreciação;30;MIL",
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;6.01.01.02.02;Amortização;-20;MIL",
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;6.01.01.03;Provisões;15;MIL",
    ]
    return "\n".join(rows)


def _bpa_csv() -> str:
    rows = [
        _DRE_HEADER,
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;1;5000;MIL",
    ]
    return "\n".join(rows)


def _bpp_csv() -> str:
    rows = [
        _DRE_HEADER,
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;2.03;2000;MIL",
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;2.01.04;300;MIL",
        f"{CNPJ};SCHULZ S.A.;2024-12-31;ÚLTIMO;2.02.01;700;MIL",
    ]
    return "\n".join(rows)


def _zip_bytes(members: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text.encode("latin-1"))
    return buf.getvalue()


class _Resp:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class _Client:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def get(self, url: str, timeout: float | None = None) -> _Resp:
        return _Resp(self._content)


@pytest.fixture()
def dfp(monkeypatch):
    content = _zip_bytes(
        {
            "dfp_cia_aberta_DRE_con_2024.csv": _dre_csv(),
            "dfp_cia_aberta_DFC_MI_con_2024.csv": _dfc_csv(),
            "dfp_cia_aberta_BPA_con_2024.csv": _bpa_csv(),
            "dfp_cia_aberta_BPP_con_2024.csv": _bpp_csv(),
        }
    )
    monkeypatch.setattr(cvm, "get_client", lambda: _Client(content))
    return cvm.fetch_dfp_financials(2024)


def test_escala_mil_aplicada(dfp) -> None:
    rec = dfp[CNPJ_DIGITS]
    assert rec["revenue"] == pytest.approx(1_000_000.0)
    assert rec["ebit"] == pytest.approx(200_000.0)
    assert rec["net_income"] == pytest.approx(100_000.0)
    assert rec["total_assets"] == pytest.approx(5_000_000.0)
    assert rec["equity"] == pytest.approx(2_000_000.0)
    assert rec["gross_debt"] == pytest.approx(1_000_000.0)


def test_da_sem_dupla_contagem_de_subtotais(dfp) -> None:
    rec = dfp[CNPJ_DIGITS]
    assert rec["ebitda"] == pytest.approx(200_000.0 + 50_000.0)


def test_usa_exercicio_mais_recente(dfp) -> None:
    rec = dfp[CNPJ_DIGITS]
    assert rec["fiscal_year"] == 2024
    assert rec["revenue"] == pytest.approx(1_000_000.0)


def test_cnpj_normalizado_e_denom(dfp) -> None:
    rec = dfp[CNPJ_DIGITS]
    assert rec["cnpj"] == CNPJ_DIGITS
    assert rec["denom"] == "SCHULZ S.A."
    assert rec["denom_norm"] == "SCHULZ"


def test_normalize_name_remove_acentos_e_stopwords() -> None:
    assert cvm.normalize_name("Döhler S.A.") == "DOHLER"
    assert cvm.normalize_name("Cia. Hering") == "HERING"
