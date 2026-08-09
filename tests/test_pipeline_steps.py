"""Integration tests for the reporting-view builder and the DQ runner/gate.

These depend on the warehouse already being built (raw ingested, marts present),
which is the state during a full pipeline run and in CI (step order guarantees
it). They skip cleanly otherwise.
"""

from __future__ import annotations

import pytest
import sqlalchemy


def _has_table(engine, schema: str, table: str) -> bool:
    q = sqlalchemy.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = :s AND table_name = :t"
    )
    with engine.connect() as conn:
        return conn.execute(q, {"s": schema, "t": table}).first() is not None


def test_build_reporting_creates_views(db_engine):
    from claimsight.reporting.build_reporting import build_reporting

    if not _has_table(db_engine, "marts", "fct_claim_header"):
        pytest.skip("marts not built yet")
    n = build_reporting()
    assert n >= 15
    with db_engine.connect() as conn:
        row = conn.execute(
            sqlalchemy.text("SELECT count(*) FROM reporting.v_claims_enriched")
        ).scalar_one()
    assert row > 0


def test_run_quality_runner_and_gate(db_engine, tmp_path):
    from claimsight.config import get_settings
    from claimsight.quality.run_quality import main, run_quality

    settings = get_settings()
    if not _has_table(db_engine, settings.raw_schema, "claims_header"):
        pytest.skip("raw schema not ingested yet")

    run = run_quality(settings=settings, exports_dir=tmp_path)
    assert run.results
    assert 0 <= run.overall_score() <= 100
    assert (tmp_path / "dq_report.json").exists()
    # No critical failures on the standard dataset, so the gate returns 0.
    assert main() == 0
