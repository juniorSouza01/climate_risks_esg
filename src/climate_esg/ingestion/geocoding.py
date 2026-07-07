from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from climate_esg.ingestion.http import request_json

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

NOMINATIM_MIN_INTERVAL_S = 1.0

_nominatim_lock = threading.Lock()
_nominatim_last_call = 0.0


def _throttle_nominatim() -> None:
    global _nominatim_last_call
    with _nominatim_lock:
        wait_s = _nominatim_last_call + NOMINATIM_MIN_INTERVAL_S - time.monotonic()
        if wait_s > 0:
            time.sleep(wait_s)
        _nominatim_last_call = time.monotonic()


@dataclass(frozen=True, slots=True)
class GeocodeResult:
    latitude: float
    longitude: float
    display_name: str


@dataclass(frozen=True, slots=True)
class CompanyAddress:
    cnpj: str
    name: str
    street: str | None
    municipality: str | None
    state: str | None
    cep: str | None


def only_digits(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def build_address_query(
    *,
    name: str | None = None,
    street: str | None = None,
    municipality: str | None = None,
    state: str | None = None,
    country: str = "Brasil",
) -> str:
    parts = [p for p in (name, street, municipality, state, country) if p]
    return ", ".join(parts)


def parse_nominatim(payload: list[dict[str, Any]]) -> GeocodeResult | None:
    if not payload:
        return None
    top = payload[0]
    return GeocodeResult(
        latitude=float(top["lat"]),
        longitude=float(top["lon"]),
        display_name=str(top.get("display_name", "")),
    )


def parse_brasilapi_cnpj(payload: dict[str, Any]) -> CompanyAddress:
    street_parts = [
        str(payload.get(k))
        for k in ("descricao_tipo_de_logradouro", "logradouro", "numero")
        if payload.get(k)
    ]
    return CompanyAddress(
        cnpj=str(payload.get("cnpj", "")),
        name=str(payload.get("razao_social") or payload.get("nome_fantasia") or ""),
        street=" ".join(street_parts) or None,
        municipality=payload.get("municipio"),
        state=payload.get("uf"),
        cep=payload.get("cep"),
    )


def geocode(query: str, *, timeout: float | None = None) -> GeocodeResult | None:
    _throttle_nominatim()
    payload = request_json(
        "nominatim",
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1, "countrycodes": "br"},
        timeout=timeout,
    )
    return parse_nominatim(payload or [])


def cnpj_to_address(cnpj: str, *, timeout: float | None = None) -> CompanyAddress | None:
    try:
        payload = request_json(
            "brasilapi", BRASILAPI_CNPJ_URL.format(cnpj=only_digits(cnpj)), timeout=timeout
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise
    if payload is None:
        return None
    return parse_brasilapi_cnpj(payload)


def geocode_cnpj(cnpj: str, *, timeout: float | None = None) -> GeocodeResult | None:
    address = cnpj_to_address(cnpj, timeout=timeout)
    if address is None:
        return None
    query = build_address_query(
        street=address.street,
        municipality=address.municipality,
        state=address.state,
    )
    return geocode(query, timeout=timeout)
