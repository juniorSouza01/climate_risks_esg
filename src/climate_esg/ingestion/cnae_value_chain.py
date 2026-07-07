from __future__ import annotations

from typing import Any

from climate_esg.modeling.climate_financial import sector_profile

# Cadeia de valor setorial (divisão CNAE → montante/jusante). Metodologia estática
# estilo matriz insumo-produto simplificada — NÃO são contrapartes reais da empresa.
_VALUE_CHAIN: dict[str, dict[str, list[dict[str, Any]]]] = {
    "01": {
        "upstream": [
            {"division": "20", "label": "Fertilizantes e defensivos"},
            {"division": "28", "label": "Máquinas agrícolas"},
        ],
        "downstream": [
            {"division": "10", "label": "Indústria de alimentos"},
            {"division": "46", "label": "Atacado / trading"},
            {"division": "49", "label": "Logística e exportação"},
        ],
    },
    "02": {
        "upstream": [
            {"division": "28", "label": "Máquinas florestais"},
            {"division": "20", "label": "Insumos químicos"},
        ],
        "downstream": [
            {"division": "17", "label": "Celulose e papel"},
            {"division": "16", "label": "Madeira"},
        ],
    },
    "03": {
        "upstream": [
            {"division": "10", "label": "Rações e insumos"},
            {"division": "28", "label": "Equipamentos"},
        ],
        "downstream": [
            {"division": "10", "label": "Processamento de pescado"},
            {"division": "47", "label": "Varejo"},
        ],
    },
    "05": {
        "upstream": [
            {"division": "28", "label": "Equipamentos de mineração"},
            {"division": "35", "label": "Energia"},
        ],
        "downstream": [
            {"division": "35", "label": "Termelétricas"},
            {"division": "24", "label": "Siderurgia"},
        ],
    },
    "06": {
        "upstream": [
            {"division": "28", "label": "Equipamentos"},
            {"division": "42", "label": "Infraestrutura/dutos"},
        ],
        "downstream": [
            {"division": "19", "label": "Refino"},
            {"division": "35", "label": "Termelétricas"},
            {"division": "20", "label": "Petroquímica"},
        ],
    },
    "07": {
        "upstream": [
            {"division": "35", "label": "Energia"},
            {"division": "28", "label": "Equipamentos"},
            {"division": "20", "label": "Explosivos/química"},
        ],
        "downstream": [
            {"division": "24", "label": "Siderurgia"},
            {"division": "23", "label": "Cimento"},
            {"division": "49", "label": "Ferrovias/portos (exportação)"},
        ],
    },
    "08": {
        "upstream": [
            {"division": "35", "label": "Energia"},
            {"division": "28", "label": "Equipamentos"},
        ],
        "downstream": [
            {"division": "23", "label": "Cimento/materiais"},
            {"division": "41", "label": "Construção"},
        ],
    },
    "10": {
        "upstream": [
            {"division": "01", "label": "Agropecuária"},
            {"division": "20", "label": "Embalagens/aditivos"},
        ],
        "downstream": [
            {"division": "47", "label": "Varejo"},
            {"division": "55", "label": "Food service"},
            {"division": "46", "label": "Atacado"},
        ],
    },
    "11": {
        "upstream": [
            {"division": "01", "label": "Agropecuária (insumos)"},
            {"division": "20", "label": "Embalagens"},
        ],
        "downstream": [
            {"division": "47", "label": "Varejo"},
            {"division": "56", "label": "Bares e restaurantes"},
        ],
    },
    "13": {
        "upstream": [
            {"division": "01", "label": "Agricultura (algodão/fibras)"},
            {"division": "20", "label": "Química (fibras sintéticas/corantes)"},
            {"division": "35", "label": "Energia"},
        ],
        "downstream": [
            {"division": "14", "label": "Confecção/vestuário"},
            {"division": "47", "label": "Varejo"},
            {"division": "31", "label": "Móveis/estofados"},
        ],
    },
    "14": {
        "upstream": [
            {"division": "13", "label": "Têxtil (tecidos)"},
            {"division": "46", "label": "Atacado de insumos"},
        ],
        "downstream": [
            {"division": "47", "label": "Varejo de moda"},
            {"division": None, "label": "Consumidor final"},
        ],
    },
    "16": {
        "upstream": [{"division": "02", "label": "Produção florestal"}],
        "downstream": [
            {"division": "31", "label": "Móveis"},
            {"division": "41", "label": "Construção"},
        ],
    },
    "17": {
        "upstream": [
            {"division": "02", "label": "Produção florestal"},
            {"division": "20", "label": "Químicos"},
            {"division": "35", "label": "Energia"},
        ],
        "downstream": [
            {"division": "18", "label": "Impressão/embalagem"},
            {"division": "46", "label": "Atacado"},
        ],
    },
    "21": {
        "upstream": [{"division": "20", "label": "Química fina (princípios ativos)"}],
        "downstream": [
            {"division": "86", "label": "Saúde"},
            {"division": "47", "label": "Farmácias/varejo"},
        ],
    },
    "22": {
        "upstream": [{"division": "20", "label": "Petroquímica (resinas)"}],
        "downstream": [
            {"division": "10", "label": "Alimentos (embalagens)"},
            {"division": "29", "label": "Automotivo"},
            {"division": "41", "label": "Construção"},
        ],
    },
    "19": {
        "upstream": [{"division": "06", "label": "Petróleo e gás"}],
        "downstream": [
            {"division": "49", "label": "Transporte/distribuição"},
            {"division": "20", "label": "Petroquímica"},
            {"division": "47", "label": "Postos/varejo"},
        ],
    },
    "20": {
        "upstream": [
            {"division": "19", "label": "Petroquímica básica"},
            {"division": "06", "label": "Gás natural"},
        ],
        "downstream": [
            {"division": "01", "label": "Agro (fertilizantes)"},
            {"division": "22", "label": "Plásticos/borracha"},
            {"division": "21", "label": "Farmacêutica"},
        ],
    },
    "23": {
        "upstream": [
            {"division": "08", "label": "Mineração (calcário)"},
            {"division": "35", "label": "Energia"},
        ],
        "downstream": [
            {"division": "41", "label": "Construção"},
            {"division": "42", "label": "Infraestrutura"},
        ],
    },
    "24": {
        "upstream": [
            {"division": "07", "label": "Mineração (minério de ferro)"},
            {"division": "35", "label": "Energia"},
        ],
        "downstream": [
            {"division": "25", "label": "Metalurgia/produtos de metal"},
            {"division": "29", "label": "Automotivo"},
            {"division": "41", "label": "Construção"},
        ],
    },
    "25": {
        "upstream": [
            {"division": "24", "label": "Siderurgia (aço)"},
            {"division": "35", "label": "Energia"},
        ],
        "downstream": [
            {"division": "28", "label": "Máquinas"},
            {"division": "41", "label": "Construção"},
            {"division": "29", "label": "Automotivo"},
        ],
    },
    "26": {
        "upstream": [
            {"division": "27", "label": "Componentes elétricos"},
            {"division": "46", "label": "Importação de componentes"},
        ],
        "downstream": [
            {"division": "62", "label": "Tecnologia"},
            {"division": "47", "label": "Varejo"},
        ],
    },
    "27": {
        "upstream": [
            {"division": "24", "label": "Metais (cobre/aço)"},
            {"division": "22", "label": "Plásticos"},
        ],
        "downstream": [
            {"division": "35", "label": "Energia elétrica"},
            {"division": "41", "label": "Construção"},
            {"division": "28", "label": "Máquinas"},
        ],
    },
    "28": {
        "upstream": [
            {"division": "24", "label": "Siderurgia (aço/fundidos)"},
            {"division": "25", "label": "Produtos de metal"},
            {"division": "27", "label": "Componentes elétricos"},
        ],
        "downstream": [
            {"division": "01", "label": "Agroindústria"},
            {"division": "07", "label": "Mineração"},
            {"division": "29", "label": "Automotivo"},
            {"division": "41", "label": "Construção"},
        ],
    },
    "29": {
        "upstream": [
            {"division": "24", "label": "Aço"},
            {"division": "22", "label": "Plásticos/borracha"},
            {"division": "27", "label": "Componentes elétricos"},
        ],
        "downstream": [
            {"division": "45", "label": "Concessionárias"},
            {"division": None, "label": "Consumidor final / frotas"},
        ],
    },
    "31": {
        "upstream": [
            {"division": "16", "label": "Madeira"},
            {"division": "13", "label": "Têxtil (estofados)"},
        ],
        "downstream": [
            {"division": "47", "label": "Varejo"},
            {"division": None, "label": "Consumidor final"},
        ],
    },
    "35": {
        "upstream": [
            {"division": "06", "label": "Gás natural"},
            {"division": "28", "label": "Equipamentos/turbinas"},
        ],
        "downstream": [
            {"division": None, "label": "Indústria, comércio e residências (consumidores)"}
        ],
    },
    "36": {
        "upstream": [
            {"division": "20", "label": "Química (tratamento)"},
            {"division": "35", "label": "Energia"},
        ],
        "downstream": [{"division": None, "label": "População / concessões municipais"}],
    },
    "41": {
        "upstream": [
            {"division": "23", "label": "Cimento/materiais"},
            {"division": "24", "label": "Aço"},
            {"division": "47", "label": "Materiais de construção"},
        ],
        "downstream": [
            {"division": "68", "label": "Imobiliário"},
            {"division": "84", "label": "Setor público (obras)"},
        ],
    },
    "42": {
        "upstream": [{"division": "23", "label": "Materiais"}, {"division": "24", "label": "Aço"}],
        "downstream": [
            {"division": "84", "label": "Setor público / concessões"},
            {"division": "35", "label": "Utilities"},
        ],
    },
    "45": {
        "upstream": [{"division": "29", "label": "Montadoras"}],
        "downstream": [{"division": None, "label": "Consumidor final / frotas"}],
    },
    "46": {
        "upstream": [
            {"division": "10", "label": "Indústria"},
            {"division": "20", "label": "Química"},
        ],
        "downstream": [
            {"division": "47", "label": "Varejo"},
            {"division": "55", "label": "Food service"},
        ],
    },
    "47": {
        "upstream": [
            {"division": "10", "label": "Alimentos"},
            {"division": "46", "label": "Atacado"},
            {"division": "13", "label": "Vestuário/indústria"},
        ],
        "downstream": [{"division": None, "label": "Consumidor final"}],
    },
    "49": {
        "upstream": [
            {"division": "19", "label": "Combustíveis"},
            {"division": "29", "label": "Veículos"},
        ],
        "downstream": [{"division": None, "label": "Embarcadores (indústria e comércio)"}],
    },
    "50": {
        "upstream": [
            {"division": "19", "label": "Combustíveis"},
            {"division": "30", "label": "Construção naval"},
        ],
        "downstream": [
            {"division": "07", "label": "Mineração (exportação)"},
            {"division": None, "label": "Comércio exterior"},
        ],
    },
    "51": {
        "upstream": [
            {"division": "19", "label": "Querosene de aviação"},
            {"division": "30", "label": "Aeronaves"},
        ],
        "downstream": [{"division": None, "label": "Passageiros e cargas"}],
    },
    "55": {
        "upstream": [
            {"division": "10", "label": "Alimentos"},
            {"division": "46", "label": "Atacado"},
        ],
        "downstream": [{"division": None, "label": "Turistas / hóspedes"}],
    },
    "58": {
        "upstream": [
            {"division": "62", "label": "Tecnologia"},
            {"division": "17", "label": "Papel/impressão"},
        ],
        "downstream": [{"division": None, "label": "Assinantes / anunciantes"}],
    },
    "61": {
        "upstream": [
            {"division": "26", "label": "Equipamentos de telecom"},
            {"division": "35", "label": "Energia"},
        ],
        "downstream": [{"division": None, "label": "Assinantes (pessoas e empresas)"}],
    },
    "62": {
        "upstream": [
            {"division": "61", "label": "Telecom/infraestrutura"},
            {"division": "26", "label": "Hardware"},
        ],
        "downstream": [{"division": None, "label": "Empresas (B2B), diversos setores"}],
    },
    "63": {
        "upstream": [
            {"division": "61", "label": "Telecom"},
            {"division": "62", "label": "Software"},
        ],
        "downstream": [{"division": None, "label": "Empresas e usuários"}],
    },
    "64": {
        "upstream": [
            {"division": "62", "label": "Tecnologia"},
            {"division": "63", "label": "Serviços de informação"},
        ],
        "downstream": [{"division": None, "label": "Empresas e pessoas (crédito/investimento)"}],
    },
    "65": {
        "upstream": [
            {"division": "66", "label": "Corretagem"},
            {"division": "62", "label": "Tecnologia"},
        ],
        "downstream": [{"division": None, "label": "Segurados (pessoas e empresas)"}],
    },
    "66": {
        "upstream": [
            {"division": "64", "label": "Bancos"},
            {"division": "62", "label": "Tecnologia"},
        ],
        "downstream": [{"division": "64", "label": "Instituições financeiras"}],
    },
    "68": {
        "upstream": [{"division": "41", "label": "Construção"}],
        "downstream": [{"division": None, "label": "Locatários e compradores"}],
    },
    "85": {
        "upstream": [
            {"division": "58", "label": "Editorial/conteúdo"},
            {"division": "62", "label": "Tecnologia"},
        ],
        "downstream": [{"division": None, "label": "Alunos e famílias"}],
    },
    "86": {
        "upstream": [
            {"division": "21", "label": "Farmacêutica"},
            {"division": "26", "label": "Equipamentos médicos"},
        ],
        "downstream": [{"division": None, "label": "Pacientes / operadoras de saúde"}],
    },
}

_GENERIC = {
    "upstream": [{"division": None, "label": "Fornecedores de insumos e serviços"}],
    "downstream": [{"division": None, "label": "Clientes do setor"}],
}


def value_chain(cnae_code: Any) -> dict[str, Any] | None:
    if cnae_code is None:
        return None
    prof = sector_profile(cnae_code)
    division = prof.get("division")
    entry = _VALUE_CHAIN.get(division or "")
    assumed = entry is None
    entry = entry or _GENERIC
    return {
        "cnae_codigo": str(cnae_code),
        "division": division,
        "archetype": prof["archetype"],
        "assumed": assumed or bool(prof.get("assumed")),
        "upstream": entry["upstream"],
        "downstream": entry["downstream"],
        "methodology": (
            "Mapa setorial estático (divisão CNAE → cadeia, estilo insumo-produto "
            "simplificado). NÃO são fornecedores/clientes reais da empresa."
        ),
        "seal": "inferido",
        "source": "cnae_value_chain_map",
    }
