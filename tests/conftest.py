"""Shared pytest fixtures.

Unit tests run with no external dependencies. Integration tests that need a live
PostgreSQL are skipped automatically when the database is unreachable, so the
suite is green both locally-without-Docker and in CI-with-Postgres.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from claimsight.config import get_settings  # noqa: E402


@pytest.fixture(scope="session")
def small_dataset():
    """A small but structurally-complete generated dataset (fast)."""
    from claimsight.generate.generate import generate

    return generate(seed=123, target_lines=3000)


@pytest.fixture(scope="session")
def db_engine():
    """A live engine, or skip the test if PostgreSQL is unreachable."""
    from sqlalchemy.exc import SQLAlchemyError

    from claimsight.db import get_engine, ping

    engine = get_engine(get_settings())
    try:
        if not ping(engine):
            pytest.skip("PostgreSQL not reachable")
    except SQLAlchemyError:
        pytest.skip("PostgreSQL not reachable")
    return engine
