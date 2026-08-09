"""End-to-end pipeline orchestrator.

Runs the full ClaimSight flow in order and stops at the data-quality gate if a
critical rule fails, mirroring a real adjudication data pipeline:

    generate -> ingest -> quality gate -> dbt build -> reporting views -> excel

dbt is invoked as a subprocess; if dbt is not importable in this interpreter the
step is reported as skipped (with guidance) rather than crashing the pipeline,
so the Python-only portion still demonstrates end to end.
"""

from __future__ import annotations

import subprocess
import sys

from claimsight.config import PROJECT_ROOT, RAW_DATA_DIR, get_settings

DBT_PROJECT_DIR = PROJECT_ROOT / "dbt" / "claimsight_dw"


def step_generate() -> None:
    from claimsight.generate.generate import generate, write_outputs

    settings = get_settings()
    print("[1/6] Generating synthetic dataset ...")
    result = generate(settings.claimsight_seed, settings.claimsight_n_claim_lines)
    write_outputs(result, RAW_DATA_DIR)
    print(f"      wrote {sum(result.manifest['row_counts'].values()):,} rows to {RAW_DATA_DIR}")


def step_ingest() -> None:
    from claimsight.ingest.ingest import ingest_all

    print("[2/6] Ingesting into raw schema ...")
    counts = ingest_all()
    print(f"      ingested {sum(counts.values()):,} rows")


def step_quality() -> int:
    from claimsight.quality.run_quality import main as quality_main

    print("[3/6] Running data-quality gate ...")
    return quality_main()


def _run_dbt(args: list[str]) -> int:
    """Try to run dbt in this interpreter; return exit code (127 if unavailable)."""
    try:
        import dbt  # noqa: F401
    except ImportError:
        print("      dbt is not installed in this interpreter — skipping dbt build.")
        print("      Install with `pip install dbt-postgres` or run dbt via Docker.")
        return 127
    proc = subprocess.run(
        [sys.executable, "-m", "dbt", *args],
        cwd=DBT_PROJECT_DIR,
    )
    return proc.returncode


def step_dbt() -> int:
    print("[4/6] Building dbt warehouse ...")
    return _run_dbt(["build"])


def step_reporting() -> None:
    from claimsight.reporting.build_reporting import build_reporting

    print("[5/6] Building reporting views ...")
    n = build_reporting()
    print(f"      created/updated {n} reporting views")


def step_excel() -> None:
    from claimsight.export.excel_report import build_workbook

    print("[6/6] Building Excel executive report ...")
    path = build_workbook()
    print(f"      wrote {path}")


def main(skip_dbt: bool = False) -> int:
    step_generate()
    step_ingest()
    rc = step_quality()
    if rc != 0:
        print(f"Pipeline halted by data-quality gate (exit {rc}).")
        return rc
    if not skip_dbt:
        rc = step_dbt()
        if rc not in (0, 127):
            print(f"dbt build failed (exit {rc}).")
            return rc
        if rc == 0:
            step_reporting()
    step_excel()
    print("Pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(skip_dbt="--skip-dbt" in sys.argv))
