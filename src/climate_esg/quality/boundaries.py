from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandera.pandas as pa
from pydantic import BaseModel, Field

MAX_PLAUSIBLE_MARKET_CAP = 1e15

ADAPTABRASIL_SCHEMA = pa.DataFrameSchema(
    {
        "ibge_code": pa.Column(str, pa.Check.str_length(min_value=1), nullable=False),
        "value": pa.Column(float, pa.Check.in_range(0.0, 1.0), nullable=False),
    }
)


def validate_adaptabrasil_rows(
    rows: Sequence[tuple[str, float, str]], *, indicator: int
) -> None:
    if not indicator:
        raise ValueError("payload AdaptaBrasil sem indicador associado")
    if not rows:
        return
    df = pd.DataFrame(
        [(ibge, value) for ibge, value, _ in rows], columns=["ibge_code", "value"]
    )
    ADAPTABRASIL_SCHEMA.validate(df, lazy=True)


class BrapiQuoteBoundary(BaseModel):
    ticker: str = Field(min_length=1)
    price: float | None = Field(default=None, gt=0.0)
    market_cap: float | None = Field(default=None, gt=0.0, lt=MAX_PLAUSIBLE_MARKET_CAP)


def validate_brapi_quote(
    ticker: str, price: float | None, market_cap: float | None
) -> None:
    BrapiQuoteBoundary(ticker=ticker, price=price, market_cap=market_cap)
