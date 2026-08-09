"""Data-quality runner: executes the rule catalogue, prints a rich scorecard,
writes a JSON report and enforces the critical-severity gate.

Exit codes:
  0  all critical rules passed (pipeline may proceed)
  2  at least one critical rule failed and DQ_FAIL_ON_CRITICAL is set
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from claimsight.config import EXPORTS_DIR, Settings, get_settings
from claimsight.db import get_engine
from claimsight.quality import engine as dq_engine
from claimsight.quality.engine import QualityRun

console = Console()

_SEV_STYLE = {"critical": "bold red", "high": "red", "medium": "yellow", "low": "dim"}


def _report_dict(run: QualityRun) -> dict:
    return {
        "run_id": run.run_id,
        "run_ts": run.run_ts.isoformat(),
        "overall_score": round(run.overall_score(), 2),
        "dimension_scores": {k: round(v, 2) for k, v in run.dimension_scores().items()},
        "table_scores": {k: round(v, 2) for k, v in run.table_scores().items()},
        "critical_failures": [r.rule.id for r in run.critical_failures()],
        "rules": [
            {
                "rule_id": r.rule.id,
                "name": r.rule.name,
                "dimension": r.rule.dimension.value,
                "severity": r.rule.severity.value,
                "table": r.rule.table,
                "column": r.rule.column,
                "rows_checked": r.rows_checked,
                "rows_failed": r.rows_failed,
                "fail_rate": round(r.fail_rate, 6),
                "passed": r.passed,
            }
            for r in run.results
        ],
    }


def _print_scorecard(run: QualityRun) -> None:
    table = Table(title=f"ClaimSight Data-Quality Scorecard (run #{run.run_id})", show_lines=False)
    table.add_column("Rule", style="cyan", no_wrap=True)
    table.add_column("Dimension")
    table.add_column("Sev")
    table.add_column("Checked", justify="right")
    table.add_column("Failed", justify="right")
    table.add_column("Fail %", justify="right")
    table.add_column("Result", justify="center")
    for r in run.results:
        sev = r.rule.severity.value
        result = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(
            r.rule.id,
            r.rule.dimension.value,
            f"[{_SEV_STYLE[sev]}]{sev}[/]",
            f"{r.rows_checked:,}",
            f"{r.rows_failed:,}",
            f"{r.fail_rate * 100:.2f}",
            result,
        )
    console.print(table)

    dim = Table(title="Dimension scores")
    dim.add_column("Dimension")
    dim.add_column("Score", justify="right")
    for d, s in sorted(run.dimension_scores().items()):
        dim.add_row(d, f"{s:.1f}")
    console.print(dim)
    console.print(f"[bold]Overall data-quality score: {run.overall_score():.1f} / 100[/bold]")


def run_quality(settings: Settings | None = None, exports_dir: Path | None = None) -> QualityRun:
    settings = settings or get_settings()
    exports_dir = exports_dir or EXPORTS_DIR
    engine = get_engine(settings)
    run = dq_engine.run(engine, settings.raw_schema)

    _print_scorecard(run)

    exports_dir.mkdir(parents=True, exist_ok=True)
    report_path = exports_dir / "dq_report.json"
    report_path.write_text(json.dumps(_report_dict(run), indent=2), encoding="utf-8")
    console.print(f"Wrote DQ JSON report to [cyan]{report_path}[/cyan]")
    return run


def main() -> int:
    settings = get_settings()
    run = run_quality(settings)
    crit = run.critical_failures()
    if crit:
        console.print(
            f"[bold red]CRITICAL data-quality failures ({len(crit)}): "
            f"{', '.join(r.rule.id for r in crit)}[/bold red]"
        )
        if settings.dq_fail_on_critical:
            console.print("[bold red]Halting pipeline (DQ gate).[/bold red]")
            return 2
    else:
        console.print("[green]No critical failures — pipeline may proceed.[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
