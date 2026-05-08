"""Score de risco físico por empresa.

Implementação real entra na F1, depois que `fact_climate_indicator`
estiver populado a partir de xclim sobre Zarr regridded.
"""

from __future__ import annotations

from climate_esg.modeling.scoring import ScoreBand


def compute_physical_score(
    company_sk: int,
    scenario_sk: int,
    horizon_year: int,
) -> ScoreBand:
    """Stub. Será substituído por overlay raster × ativos + agregação ponderada."""
    raise NotImplementedError(
        "physical_risk.compute_physical_score: aguardando F1 (ingestão CMIP6 promovida a gold)"
    )
