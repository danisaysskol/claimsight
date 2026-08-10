"""ClaimSight end-to-end pipeline as an Airflow DAG (optional Phase 10).

Orchestrates: generate -> ingest -> quality gate -> dbt build -> reporting ->
excel. Each step runs in the isolated ClaimSight venv (``CS_PYTHON``) so Airflow's
own dependencies are never touched. The quality gate task fails (non-zero exit)
if a critical data-quality rule fails, halting the run — exactly like the CLI
pipeline.
"""

from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

CS_PY = os.environ.get("CS_PYTHON", "/home/airflow/cs-venv/bin/python")
CS_DBT = os.environ.get("CS_DBT", "/home/airflow/cs-venv/bin/dbt")
PROJ = os.environ.get("CS_PROJECT", "/opt/airflow/project")
DBT_DIR = f"{PROJ}/dbt/claimsight_dw"
SRC = f"{PROJ}/src"


def _py(module: str) -> str:
    return f"cd {PROJ} && PYTHONPATH={SRC} {CS_PY} -m {module}"


with DAG(
    dag_id="claimsight_pipeline",
    description="generate -> ingest -> DQ gate -> dbt build -> reporting -> excel",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
    tags=["claimsight"],
) as dag:
    generate = BashOperator(
        task_id="generate", bash_command=_py("claimsight.generate.generate")
    )
    ingest = BashOperator(
        task_id="ingest", bash_command=_py("claimsight.ingest.ingest")
    )
    # Exits non-zero on a critical DQ failure -> task fails -> pipeline halts.
    quality_gate = BashOperator(
        task_id="quality_gate", bash_command=_py("claimsight.quality.run_quality")
    )
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {DBT_DIR} && DBT_TARGET_PATH=${{DBT_TARGET_PATH:-/tmp/dbt_target}} {CS_DBT} build",
    )
    reporting = BashOperator(
        task_id="reporting", bash_command=_py("claimsight.reporting.build_reporting")
    )
    excel = BashOperator(
        task_id="excel", bash_command=_py("claimsight.export.excel_report")
    )

    generate >> ingest >> quality_gate >> dbt_build >> reporting >> excel
