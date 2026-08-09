"""Data-quality engine tests.

Unit tests validate the rule catalogue and the scoring maths with no database.
The integration test ingests a small generated dataset and proves the engine
catches every injected defect class, reconciled against the manifest.
"""

from __future__ import annotations

import pytest

from claimsight.quality.engine import QualityRun, RuleResult
from claimsight.quality.rules import RULES, Dimension, Rule, Severity


# ------------------------------- unit tests -------------------------------- #
def test_rule_catalogue_size_and_coverage():
    assert len(RULES) >= 25
    dims = {r.dimension for r in RULES}
    assert dims == set(Dimension), "every quality dimension must be covered"


def test_rule_ids_unique():
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids))


def test_rules_are_wellformed():
    for r in RULES:
        assert "record_key" in r.failing_sql, f"{r.id} must select a record_key"
        assert "{s}" in r.failing_sql, f"{r.id} must be schema-parameterised"
        assert isinstance(r.severity, Severity)


def _fake_result(sev: Severity, checked: int, failed: int) -> RuleResult:
    rule = Rule(
        id=f"X-{sev.value}", name="x", dimension=Dimension.VALIDITY, severity=sev,
        table="t", description="d",
        failing_sql='SELECT id AS record_key FROM "{s}".t WHERE false',
    )
    return RuleResult(rule=rule, rows_checked=checked, rows_failed=failed, failing_keys=[])


def test_scoring_perfect_is_100():
    run = QualityRun(run_id=1, run_ts=None, results=[_fake_result(Severity.HIGH, 100, 0)])
    assert run.overall_score() == pytest.approx(100.0)


def test_scoring_all_failed_is_0():
    run = QualityRun(run_id=1, run_ts=None, results=[_fake_result(Severity.HIGH, 100, 100)])
    assert run.overall_score() == pytest.approx(0.0)


def test_scoring_is_severity_weighted():
    # A low-severity total failure should hurt less than a critical one.
    low = QualityRun(1, None, [_fake_result(Severity.LOW, 10, 10),
                               _fake_result(Severity.CRITICAL, 10, 0)])
    crit = QualityRun(1, None, [_fake_result(Severity.LOW, 10, 0),
                                _fake_result(Severity.CRITICAL, 10, 10)])
    assert low.overall_score() > crit.overall_score()


# --------------------------- integration test ------------------------------ #
@pytest.fixture(scope="module")
def dq_run_on_small(db_engine, tmp_path_factory):
    """Generate → write CSVs → ingest into an isolated schema → run DQ."""
    from claimsight.config import get_settings
    from claimsight.generate.generate import generate, write_outputs
    from claimsight.ingest.ingest import ingest_all
    from claimsight.quality import engine as dq_engine

    settings = get_settings().model_copy(update={"raw_schema": "raw_test"})
    raw_dir = tmp_path_factory.mktemp("raw")
    result = generate(seed=777, target_lines=4000)
    write_outputs(result, raw_dir)
    ingest_all(settings=settings, raw_dir=raw_dir)
    run = dq_engine.run(db_engine, settings.raw_schema)
    return run, result.manifest["injected_defects"]


def _failed(run, rule_id: int) -> int:
    return next(r.rows_failed for r in run.results if r.rule.id == rule_id)


def test_dq_catches_duplicates(dq_run_on_small):
    run, defects = dq_run_on_small
    injected = defects["duplicate_claims"]
    caught = _failed(run, "U-HDR-BIZDUP")
    # A handful of injected duplicates can have their signature altered by a
    # subsequent orphan/negative-amount injection, so allow a small tolerance.
    assert injected * 0.9 <= caught <= injected + 5


def test_dq_catches_orphans(dq_run_on_small):
    run, defects = dq_run_on_small
    assert _failed(run, "R-HDR-MEMBER-FK") == defects["orphan_fk_member"]
    assert _failed(run, "R-HDR-PROVIDER-FK") == defects["orphan_fk_provider"]


def test_dq_catches_nulls(dq_run_on_small):
    run, defects = dq_run_on_small
    assert _failed(run, "C-HDR-ADJMODE") == defects["null_values"]


def test_dq_catches_impossible_ages(dq_run_on_small):
    run, defects = dq_run_on_small
    assert _failed(run, "V-MBR-AGE") == defects["impossible_ages"]


def test_dq_catches_date_violations(dq_run_on_small):
    run, defects = dq_run_on_small
    assert _failed(run, "K-HDR-DISCHARGE") == defects["date_violations"]


def test_dq_catches_nonpositive(dq_run_on_small):
    run, defects = dq_run_on_small
    assert _failed(run, "A-HDR-NONNEG") == defects["nonpositive_amounts"]


def test_dq_catches_amount_violations(dq_run_on_small):
    run, defects = dq_run_on_small
    # approved>billed also trips on the negative-billed rows, hence >=.
    assert _failed(run, "A-HDR-APPR-BILLED") >= defects["amount_violations"]
    assert _failed(run, "A-HDR-PAID-APPR") >= defects["amount_violations"]


def test_dq_no_critical_failures_on_normal_data(dq_run_on_small):
    run, _ = dq_run_on_small
    assert run.critical_failures() == []


def test_dq_score_is_reasonable(dq_run_on_small):
    run, _ = dq_run_on_small
    # Most rows are clean, so the weighted score should stay high.
    assert 80.0 <= run.overall_score() <= 100.0
