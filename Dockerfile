# Containerised runner for the ClaimSight pipeline (generate → ingest → DQ →
# dbt → reporting → excel) and tests. Runs the Python 3.12 stack on Linux so it
# behaves identically to CI and is independent of host-side tooling.
FROM python:3.12-slim

WORKDIR /app

# Dependencies first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Application code (overridden by a bind-mount during development runs).
COPY . .

ENV PYTHONPATH=/app/src \
    DBT_PROFILES_DIR=/app/dbt/claimsight_dw

CMD ["python", "-m", "claimsight.pipeline"]
