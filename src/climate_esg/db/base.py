"""Engine SQLAlchemy + sessão. Importado por models.py e por código de runtime."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from climate_esg.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa única para todo o ORM."""


def make_engine() -> Engine:  # type: ignore[name-defined]  # noqa: F821
    """Cria engine novo a partir das settings. Não cacheado."""
    from sqlalchemy.engine import Engine  # local para evitar import top-level pesado

    settings = get_settings()
    engine: Engine = create_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        future=True,
    )
    return engine


_SessionFactory: sessionmaker[Session] | None = None


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=make_engine(), expire_on_commit=False)
    return _SessionFactory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager com commit/rollback automático."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
