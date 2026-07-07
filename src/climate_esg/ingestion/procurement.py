from __future__ import annotations

from typing import Any

import httpx

from climate_esg.ingestion.geocoding import only_digits
from climate_esg.ingestion.http import request_json

GOV_SUPPLIER_URL = "https://dadosabertos.compras.gov.br/modulo-fornecedor/1_consultarFornecedor"


def fetch_gov_supplier(cnpj: str, *, timeout: float | None = None) -> dict[str, Any] | None:
    """Consulta o cadastro de fornecedor do Executivo Federal (Compras.gov, sem auth).

    Retorna None em erro/ausência de rede; {found: False} quando o CNPJ não consta;
    o cadastro factual quando consta.
    """
    digits = only_digits(cnpj)
    if len(digits) != 14:
        return None
    try:
        payload = request_json(
            "compras_gov",
            GOV_SUPPLIER_URL,
            params={"cnpj": digits, "ativo": "true"},
            timeout=timeout,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise
    if payload is None:
        return None
    results = payload.get("resultado") or []
    base = {"seal": "factual", "source": "compras.gov.br"}
    if not results:
        return {"found": False, **base}
    it = results[0]
    return {
        "found": True,
        "habilitado_licitar": it.get("habilitadoLicitar"),
        "ativo": it.get("ativo"),
        "razao_social": it.get("nomeRazaoSocialFornecedor"),
        "cnae_codigo": it.get("codigoCnae"),
        "cnae_nome": it.get("nomeCnae"),
        "natureza_juridica": it.get("naturezaJuridicaNome"),
        "porte": it.get("porteEmpresaNome"),
        "municipio": it.get("nomeMunicipio"),
        "uf": it.get("ufSigla"),
        "note": "Cadastro de fornecedor do Executivo Federal; habilitado a licitar não implica contrato ativo.",
        **base,
    }
