"""Execution engine for the declarative data-quality rules.

Generic: it executes whatever SQL each :class:`~claimsight.quality.rules.Rule`
declares, records the outcome in ``dq.dq_results``, quarantines failing row keys
in ``dq.dq_failed_records`` and computes severity-weighted quality scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from claimsight.quality.rules import (
    RULES,
    SEVERITY_WEIGHT,
    Dimension,
    Rule,
    Severity,
)

DQ_SCHEMA = "dq"

_PARSE_DATE_FN = """
CREATE OR REPLACE FUNCTION cs_parse_date(s text) RETURNS date AS $$
  SELECT CASE
    WHEN s IS NULL OR s = '' THEN NULL
    WHEN s ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN to_date(substr(s, 1, 10), 'YYYY-MM-DD')
    WHEN s ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' THEN to_date(s, 'DD/MM/YYYY')
    WHEN s ~ '^[0-9]{2}-[0-9]{2}-[0-9]{4}$' THEN to_date(s, 'DD-MM-YYYY')
    ELSE NULL
  END
$$ LANGUAGE sql IMMUTABLE;
"""


@dataclass
class RuleResult:
    rule: Rule
    rows_checked: int
    rows_failed: int
    failing_keys: list[str]

    @property
    def fail_rate(self) -> float:
        return (self.rows_failed / self.rows_checked) if self.rows_checked else 0.0

    @property
    def passed(self) -> bool:
        return self.fail_rate <= self.rule.threshold


@dataclass
class QualityRun:
    run_id: int
    run_ts: datetime
    results: list[RuleResult]

    # --- scores ---
    def table_scores(self) -> dict[str, float]:
        scores: dict[str, dict[str, float]] = {}
        for r in self.results:
            w = SEVERITY_WEIGHT[r.rule.severity]
            acc = scores.setdefault(r.rule.table, {"num": 0.0, "den": 0.0})
            acc["num"] += w * (1.0 - r.fail_rate)
            acc["den"] += w
        return {t: 100.0 * (a["num"] / a["den"]) if a["den"] else 100.0 for t, a in scores.items()}

    def overall_score(self) -> float:
        num = sum(SEVERITY_WEIGHT[r.rule.severity] * (1.0 - r.fail_rate) for r in self.results)
        den = sum(SEVERITY_WEIGHT[r.rule.severity] for r in self.results)
        return 100.0 * (num / den) if den else 100.0

    def dimension_scores(self) -> dict[str, float]:
        scores: dict[Dimension, dict[str, float]] = {}
        for r in self.results:
            w = SEVERITY_WEIGHT[r.rule.severity]
            acc = scores.setdefault(r.rule.dimension, {"num": 0.0, "den": 0.0})
            acc["num"] += w * (1.0 - r.fail_rate)
            acc["den"] += w
        return {d.value: 100.0 * (a["num"] / a["den"]) if a["den"] else 100.0 for d, a in scores.items()}

    def critical_failures(self) -> list[RuleResult]:
        return [r for r in self.results if r.rule.severity == Severity.CRITICAL and not r.passed]


def setup(engine: Engine) -> None:
    """Create the DQ schema, helper function and result tables."""
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DQ_SCHEMA}"'))
        conn.execute(text(_PARSE_DATE_FN))
        conn.execute(
            text(
                f'CREATE TABLE IF NOT EXISTS "{DQ_SCHEMA}".dq_results ('
                "run_id integer, run_ts timestamptz, rule_id text, rule_name text, "
                "dimension text, severity text, table_name text, column_name text, "
                "rows_checked bigint, rows_failed bigint, fail_rate numeric, "
                "threshold numeric, passed boolean)"
            )
        )
        conn.execute(
            text(
                f'CREATE TABLE IF NOT EXISTS "{DQ_SCHEMA}".dq_failed_records ('
                "run_id integer, rule_id text, table_name text, record_key text, "
                "captured_at timestamptz DEFAULT now())"
            )
        )


def _next_run_id(engine: Engine) -> int:
    with engine.connect() as conn:
        val = conn.execute(
            text(f'SELECT COALESCE(max(run_id), 0) + 1 FROM "{DQ_SCHEMA}".dq_results')
        ).scalar_one()
    return int(val)


def run(engine: Engine, schema: str, rules: list[Rule] | None = None) -> QualityRun:
    """Execute all rules against ``schema`` and persist the outcome."""
    rules = rules if rules is not None else RULES
    setup(engine)
    run_id = _next_run_id(engine)
    run_ts = datetime.now(UTC)

    results: list[RuleResult] = []
    with engine.connect() as conn:
        for rule in rules:
            checked = int(conn.execute(text(rule.resolved_checked_sql(schema))).scalar_one())
            rows = conn.execute(text(rule.resolved_failing_sql(schema))).fetchall()
            keys = [str(r[0]) for r in rows]
            results.append(
                RuleResult(rule=rule, rows_checked=checked, rows_failed=len(keys), failing_keys=keys)
            )

    # Persist results + quarantine.
    with engine.begin() as conn:
        for res in results:
            conn.execute(
                text(
                    f'INSERT INTO "{DQ_SCHEMA}".dq_results '
                    "(run_id, run_ts, rule_id, rule_name, dimension, severity, table_name, "
                    "column_name, rows_checked, rows_failed, fail_rate, threshold, passed) VALUES "
                    "(:run_id, :run_ts, :rule_id, :rule_name, :dimension, :severity, :table_name, "
                    ":column_name, :rows_checked, :rows_failed, :fail_rate, :threshold, :passed)"
                ),
                {
                    "run_id": run_id,
                    "run_ts": run_ts,
                    "rule_id": res.rule.id,
                    "rule_name": res.rule.name,
                    "dimension": res.rule.dimension.value,
                    "severity": res.rule.severity.value,
                    "table_name": res.rule.table,
                    "column_name": res.rule.column,
                    "rows_checked": res.rows_checked,
                    "rows_failed": res.rows_failed,
                    "fail_rate": res.fail_rate,
                    "threshold": res.rule.threshold,
                    "passed": res.passed,
                },
            )
            if res.failing_keys:
                conn.execute(
                    text(
                        f'INSERT INTO "{DQ_SCHEMA}".dq_failed_records '
                        "(run_id, rule_id, table_name, record_key) VALUES "
                        "(:run_id, :rule_id, :table_name, :record_key)"
                    ),
                    [
                        {
                            "run_id": run_id,
                            "rule_id": res.rule.id,
                            "table_name": res.rule.table,
                            "record_key": k,
                        }
                        for k in res.failing_keys
                    ],
                )

    return QualityRun(run_id=run_id, run_ts=run_ts, results=results)
