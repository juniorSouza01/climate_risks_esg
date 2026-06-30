from __future__ import annotations

import unicodedata
from functools import lru_cache
from typing import Any

from climate_esg.ingestion.http import get_client

MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def _norm(text: str) -> str:
    base = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return base.upper().strip()


def _uf_sigla(municipio: dict[str, Any]) -> str | None:
    try:
        return str(municipio["microrregiao"]["mesorregiao"]["UF"]["sigla"])
    except (KeyError, TypeError):
        regiao = municipio.get("regiao-imediata") or {}
        try:
            return str(regiao["regiao-intermediaria"]["UF"]["sigla"])
        except (KeyError, TypeError):
            return None


@lru_cache(maxsize=1)
def _municipality_index() -> dict[tuple[str, str], str]:
    resp = get_client().get(MUNICIPIOS_URL, timeout=90.0)
    resp.raise_for_status()
    index: dict[tuple[str, str], str] = {}
    for m in resp.json():
        uf = _uf_sigla(m)
        nome = m.get("nome")
        if uf and nome:
            index[(_norm(nome), uf.upper())] = str(m["id"])
    return index


def resolve_ibge_code(municipality: str, uf: str) -> str | None:
    if not municipality or not uf:
        return None
    return _municipality_index().get((_norm(municipality), uf.upper()))
