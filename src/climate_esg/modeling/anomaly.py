from __future__ import annotations

from dataclasses import dataclass

from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from climate_esg.modeling.features import build_company_features

MIN_SAMPLE = 10


@dataclass(frozen=True, slots=True)
class AnomalyResult:
    company_sk: int
    name: str
    score: float
    is_outlier: bool


def detect_anomalies(session: Session, *, contamination: float = 0.1) -> list[AnomalyResult]:
    feats = build_company_features(session)
    if len(feats.company_sks) < MIN_SAMPLE:
        return []
    model = IsolationForest(contamination=contamination, random_state=0)
    model.fit(feats.matrix)
    scores = model.score_samples(feats.matrix)
    preds = model.predict(feats.matrix)
    return [
        AnomalyResult(
            company_sk=sk,
            name=name,
            score=round(float(score), 4),
            is_outlier=bool(pred == -1),
        )
        for sk, name, score, pred in zip(
            feats.company_sks, feats.names, scores, preds, strict=False
        )
    ]


def company_anomaly(session: Session, company_sk: int) -> AnomalyResult | None:
    for result in detect_anomalies(session):
        if result.company_sk == company_sk:
            return result
    return None
