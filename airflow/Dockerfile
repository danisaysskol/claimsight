# Airflow runner for the ClaimSight pipeline (optional Phase 10).
# Airflow's own environment is left untouched: the ClaimSight stack (which needs
# SQLAlchemy 2.x, incompatible with Airflow 2.x) lives in an isolated venv at
# /home/airflow/cs-venv, invoked by the DAG's BashOperators.
FROM apache/airflow:2.10.5-python3.12

USER airflow

# Isolated virtualenv with the pipeline's runtime deps + dbt (no Airflow clash).
RUN python -m venv /home/airflow/cs-venv \
    && /home/airflow/cs-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /home/airflow/cs-venv/bin/pip install --no-cache-dir \
        pandas==2.3.3 numpy==2.2.6 SQLAlchemy==2.0.51 psycopg2-binary==2.9.12 \
        Faker==40.36.0 pydantic==2.13.4 pydantic-settings==2.15.0 \
        python-dotenv==1.2.2 rich==15.0.0 openpyxl==3.1.5 \
        dbt-core==1.12.0 dbt-postgres==1.11.0
