from __future__ import annotations

from dataclasses import dataclass

from sklearn.neighbors import NearestNeighbors
from sqlalchemy.orm import Session

from climate_esg.modeling.features import build_company_features


@dataclass(frozen=True, slots=True)
class Peer:
    company_sk: int
    name: str
    distance: float


def nearest_peers(session: Session, company_sk: int, *, k: int = 5) -> list[Peer]:
    feats = build_company_features(session)
    if company_sk not in feats.company_sks or len(feats.company_sks) < 2:
        return []
    idx = feats.company_sks.index(company_sk)
    n = min(k + 1, len(feats.company_sks))
    nn = NearestNeighbors(n_neighbors=n, metric="cosine").fit(feats.matrix)
    distances, indices = nn.kneighbors(feats.matrix[idx : idx + 1])

    peers: list[Peer] = []
    for dist, i in zip(distances[0], indices[0], strict=False):
        if int(i) == idx:
            continue
        peers.append(
            Peer(
                company_sk=feats.company_sks[int(i)],
                name=feats.names[int(i)],
                distance=round(float(dist), 4),
            )
        )
    return peers[:k]
