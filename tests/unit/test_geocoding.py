from __future__ import annotations

from climate_esg.ingestion.geocoding import (
    build_address_query,
    only_digits,
    parse_brasilapi_cnpj,
    parse_nominatim,
)


def test_only_digits() -> None:
    assert only_digits("84.693.183/0001-68") == "84693183000168"


def test_build_address_query_ignora_vazios() -> None:
    q = build_address_query(municipality="Joinville", state="SC")
    assert q == "Joinville, SC, Brasil"


def test_build_address_query_completa() -> None:
    q = build_address_query(street="Rua X 100", municipality="Joinville", state="SC")
    assert q == "Rua X 100, Joinville, SC, Brasil"


def test_parse_nominatim_vazio() -> None:
    assert parse_nominatim([]) is None


def test_parse_nominatim_pega_primeiro() -> None:
    r = parse_nominatim(
        [
            {"lat": "-26.3", "lon": "-48.84", "display_name": "Joinville"},
            {"lat": "0", "lon": "0", "display_name": "outro"},
        ]
    )
    assert r is not None
    assert r.latitude == -26.3
    assert r.longitude == -48.84
    assert r.display_name == "Joinville"


def test_parse_brasilapi_cnpj() -> None:
    addr = parse_brasilapi_cnpj(
        {
            "cnpj": "84693183000168",
            "razao_social": "Schulz S.A.",
            "descricao_tipo_de_logradouro": "Rua",
            "logradouro": "Dona Francisca",
            "numero": "6901",
            "municipio": "Joinville",
            "uf": "SC",
            "cep": "89219501",
        }
    )
    assert addr.name == "Schulz S.A."
    assert addr.municipality == "Joinville"
    assert addr.state == "SC"
    assert addr.street == "Rua Dona Francisca 6901"
