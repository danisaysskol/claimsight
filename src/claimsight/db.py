"""SQLAlchemy engine factory and small schema helpers."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Engine, create_engine, text

from claimsight.config import Settings, get_settings


def get_engine(settings: Settings | None = None, *, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for the configured PostgreSQL database.

    ``pool_pre_ping`` guards against stale connections when the container has
    been idle; ``future=True`` opts into SQLAlchemy 2.0 semantics.
    """
    settings = settings or get_settings()
    return create_engine(
        settings.sqlalchemy_url,
        echo=echo,
        pool_pre_ping=True,
        future=True,
    )


def ensure_schemas(engine: Engine, schemas: Iterable[str]) -> None:
    """Create the given schemas if they do not already exist."""
    with engine.begin() as conn:
        for schema in schemas:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))


def ping(engine: Engine) -> bool:
    """Return True if the database answers ``SELECT 1``."""
    with engine.connect() as conn:
        return conn.execute(text("SELECT 1")).scalar_one() == 1
