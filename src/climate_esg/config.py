"""Configuração central via variáveis de ambiente (.env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Settings carregadas de .env e variáveis de ambiente.

    Paths default apontam para o filesystem local do repo, refletindo a
    decisão de não usar MinIO no MVP (ver ADR-0002).
    """

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Postgres ---
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "climate_esg"
    pg_password: SecretStr = SecretStr("changeme_local_only")
    pg_db: str = "climate_esg"
    database_url: PostgresDsn | None = None

    # --- Data lake local ---
    data_bronze: Path = Field(default=REPO_ROOT / "data" / "bronze")
    data_silver: Path = Field(default=REPO_ROOT / "data" / "silver")
    data_gold: Path = Field(default=REPO_ROOT / "data" / "gold")

    # --- Prefect / MLflow ---
    prefect_api_url: str = "http://127.0.0.1:4200/api"
    mlflow_tracking_uri: str = str(REPO_ROOT / "mlruns")

    # --- ESGF ---
    esgf_openid: str = ""
    esgf_password: str = ""

    # --- Fontes corporativas ---
    brapi_token: SecretStr = SecretStr("")
    portal_transparencia_token: str = ""

    # --- Pool de conexões DB ---
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # --- Cache ---
    dossier_cache_ttl_s: int = 3600

    # --- Qualidade ---
    min_companies_scored: int = 1

    # --- API ---
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:4173",
            "http://127.0.0.1:5173",
        ]
    )
    api_key: SecretStr | None = None

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def sqlalchemy_url(self) -> str:
        """URL pronta para SQLAlchemy/Alembic."""
        if self.database_url:
            return str(self.database_url)
        return (
            f"postgresql+psycopg://{self.pg_user}:{self.pg_password.get_secret_value()}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — settings nunca mudam dentro de um processo."""
    return Settings()
