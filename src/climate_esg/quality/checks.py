from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

MAX_SCORE_JUMP = 30.0

INDICATOR_SCHEMA = pa.DataFrameSchema(
    {
        "date_sk": pa.Column(int, pa.Check.in_range(18500101, 21001231), nullable=False),
        "value_mean": pa.Column(float, nullable=False),
    }
)

SCORE_SCHEMA = pa.DataFrameSchema(
    {
        "score_0_100": pa.Column(float, pa.Check.in_range(0.0, 100.0), nullable=False),
        "band_low": pa.Column(float, pa.Check.in_range(0.0, 100.0), nullable=False),
        "band_high": pa.Column(float, pa.Check.in_range(0.0, 100.0), nullable=False),
    },
    checks=[
        pa.Check(lambda df: df["band_low"] <= df["score_0_100"], error="band_low > score"),
        pa.Check(lambda df: df["score_0_100"] <= df["band_high"], error="score > band_high"),
    ],
)


def validate_indicator_rows(rows: list[tuple[int, float]], *, min_rows: int = 1) -> None:
    if len(rows) < min_rows:
        raise ValueError(
            f"validate_indicator_rows: {len(rows)} linhas < min_rows={min_rows} — "
            "validação vazia bloqueada"
        )
    if not rows:
        return
    df = pd.DataFrame(rows, columns=["date_sk", "value_mean"])
    INDICATOR_SCHEMA.validate(df, lazy=True)


def validate_score_rows(rows: list[dict[str, float]], *, min_rows: int = 1) -> None:
    if len(rows) < min_rows:
        raise ValueError(
            f"validate_score_rows: {len(rows)} linhas < min_rows={min_rows} — "
            "validação vazia bloqueada"
        )
    if not rows:
        return
    SCORE_SCHEMA.validate(pd.DataFrame(rows), lazy=True)


def assert_score_jump(previous: float | None, current: float) -> None:
    if previous is not None and abs(current - previous) > MAX_SCORE_JUMP:
        raise ValueError(
            f"salto de score {previous:.1f}→{current:.1f} excede {MAX_SCORE_JUMP:.0f} pts "
            "sem justificativa — bloqueado (§9.2)"
        )
