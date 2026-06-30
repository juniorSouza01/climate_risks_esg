from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from climate_esg.ingestion.http import get_client

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

_ESG_TERMS = (
    "climate",
    "clima",
    "emission",
    "emiss",
    "pollut",
    "polui",
    "lawsuit",
    "processo",
    "fine",
    "multa",
    "scandal",
    "escândalo",
    "fraud",
    "fraude",
    "spill",
    "vazamento",
    "deforest",
    "desmatamento",
    "layoff",
    "strike",
    "greve",
)


@dataclass(frozen=True, slots=True)
class Article:
    title: str
    url: str
    domain: str
    seendate: str
    language: str


def parse_gdelt(payload: dict[str, Any]) -> list[Article]:
    out: list[Article] = []
    for a in payload.get("articles") or []:
        out.append(
            Article(
                title=str(a.get("title", "")),
                url=str(a.get("url", "")),
                domain=str(a.get("domain", "")),
                seendate=str(a.get("seendate", "")),
                language=str(a.get("language", "")),
            )
        )
    return out


def controversy_ratio(articles: list[Article]) -> float:
    if not articles:
        return 0.0
    flagged = sum(1 for a in articles if any(term in a.title.lower() for term in _ESG_TERMS))
    return round(flagged / len(articles), 4)


def fetch_news(query: str, *, max_records: int = 25, timeout: float = 20.0) -> list[Article]:
    params = {
        "query": f'"{query}"',
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "sort": "DateDesc",
    }
    resp = get_client().get(GDELT_DOC_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    try:
        payload = resp.json()
    except ValueError:
        return []
    return parse_gdelt(payload)
