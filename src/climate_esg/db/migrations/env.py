"""Ambiente Alembic.

A URL do banco vem de ``climate_esg.config.get_settings()`` (que lê ``.env`` /
``DATABASE_URL``), não do ``alembic.ini`` — assim migrations locais e CI usam a
mesma fonte de configuração que o runtime.

Importa ``climate_esg.db.models`` para popular ``Base.metadata`` (necessário
para ``--autogenerate``).
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from climate_esg.config import get_settings
from climate_esg.db.base import Base
from climate_esg.db import models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Injeta a URL real (escapando %, que o ConfigParser interpreta).
config.set_main_option("sqlalchemy.url", get_settings().sqlalchemy_url.replace("%", "%%"))

target_metadata = Base.metadata

# Tabelas/extensões gerenciadas pelo PostGIS — Alembic não deve tentar criar,
# alterar ou dropar nenhuma delas no autogenerate.
_POSTGIS_TABLES = {
    "spatial_ref_sys",
    "geometry_columns",
    "geography_columns",
    "raster_columns",
    "raster_overviews",
    "topology",
    "layer",
}


def include_object(obj, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    return not (type_ == "table" and name in _POSTGIS_TABLES)


def run_migrations_offline() -> None:
    """Gera SQL sem conectar (modo --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica migrations conectando ao banco."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
