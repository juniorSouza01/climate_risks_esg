from __future__ import annotations

from collections.abc import Iterator

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from climate_esg.config import get_settings
from climate_esg.db.base import get_session_factory


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = get_settings().api_key
    if expected is None:
        return
    if x_api_key != expected.get_secret_value():
        raise HTTPException(status_code=401, detail="X-API-Key inválida ou ausente")
