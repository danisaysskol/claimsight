"""Centralised, typed configuration loaded from the environment / ``.env``.

Uses pydantic-settings so every setting is validated once, at startup, and the
rest of the codebase can rely on correct types instead of re-parsing os.environ.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = three levels up from this file:
# src/claimsight/config.py -> src/claimsight -> src -> <root>
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
# Output dirs are env-overridable so containerised runners (e.g. the Airflow
# image, which runs as a non-root user that can't write git-tracked host dirs)
# can point them at a writable location.
RAW_DATA_DIR = Path(os.environ.get("CLAIMSIGHT_RAW_DIR") or (DATA_DIR / "raw"))
EXPORTS_DIR = Path(os.environ.get("CLAIMSIGHT_EXPORTS_DIR") or (DATA_DIR / "exports"))


class Settings(BaseSettings):
    """Application settings sourced from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- PostgreSQL ---
    postgres_user: str = Field(default="claimsight")
    postgres_password: str = Field(default="claimsight")
    postgres_db: str = Field(default="claimsight")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5433)

    # --- Application ---
    claimsight_seed: int = Field(default=42)
    claimsight_n_claim_lines: int = Field(default=60_000)
    raw_schema: str = Field(default="raw")
    reporting_schema: str = Field(default="reporting")

    # --- Data-quality gate ---
    dq_fail_on_critical: bool = Field(default=True)

    @property
    def sqlalchemy_url(self) -> str:
        """Return a psycopg2 SQLAlchemy URL for the configured database."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (parsed once per process)."""
    return Settings()
