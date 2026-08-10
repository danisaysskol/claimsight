"""Load raw CSVs into the PostgreSQL ``raw`` schema.

The golden rule of this layer: **preserve the dirt exactly as generated**. Every
column is loaded as text so that mixed date formats, out-of-range values and
inconsistent casing survive untouched for the data-quality engine and the dbt
staging layer to deal with. No cleaning happens here.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from claimsight.config import RAW_DATA_DIR, Settings, get_settings
from claimsight.db import get_engine

# Order matters only for readability; there are no FKs in the raw schema.
RAW_TABLES: list[str] = [
    "employer_groups",
    "policies",
    "providers",
    "members",
    "diagnoses",
    "procedures",
    "claims_header",
    "claims_lines",
]

CHUNK_SIZE = 5_000


def load_csv_as_text(path: Path) -> pd.DataFrame:
    """Read a CSV with every column as text (preserve raw values verbatim)."""
    # keep_default_na=False so empty strings stay '' rather than becoming NaN,
    # except we still want injected NaNs to read as empty — the DQ engine treats
    # empty string / NULL uniformly for completeness checks.
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[])


def ingest_table(engine: Engine, schema: str, name: str, raw_dir: Path) -> int:
    """Load one CSV into ``schema.name`` (replace). Returns row count."""
    path = raw_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Expected raw CSV not found: {path}")
    df = load_csv_as_text(path)
    df.to_sql(
        name,
        engine,
        schema=schema,
        if_exists="replace",
        index=False,
        chunksize=CHUNK_SIZE,
        method="multi",
    )
    return len(df)


def ingest_all(settings: Settings | None = None, raw_dir: Path | None = None) -> dict[str, int]:
    """Ingest every raw table. Returns a name -> row-count map."""
    settings = settings or get_settings()
    raw_dir = raw_dir or RAW_DATA_DIR
    engine = get_engine(settings)

    # Rebuild the landing zone cleanly. Dropping the schema CASCADE removes any
    # downstream objects that depend on the raw tables from a previous run (dbt
    # staging views, reporting.v_duplicate_candidates) — otherwise pandas'
    # to_sql(if_exists="replace") DROP TABLE fails with DependentObjectsStillExist.
    # dbt build and the reporting step recreate those objects afterwards.
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{settings.raw_schema}" CASCADE'))
        conn.execute(text(f'CREATE SCHEMA "{settings.raw_schema}"'))

    counts: dict[str, int] = {}
    for name in RAW_TABLES:
        n = ingest_table(engine, settings.raw_schema, name, raw_dir)
        counts[name] = n
        print(f"  loaded raw.{name:20s} {n:>8,} rows")

    # Record ingest run in a small audit table.
    with engine.begin() as conn:
        conn.execute(
            text(
                f'CREATE TABLE IF NOT EXISTS "{settings.raw_schema}"._ingest_audit '
                "(table_name text, row_count integer, loaded_at timestamptz default now())"
            )
        )
        conn.execute(text(f'TRUNCATE "{settings.raw_schema}"._ingest_audit'))
        for name, n in counts.items():
            conn.execute(
                text(
                    f'INSERT INTO "{settings.raw_schema}"._ingest_audit (table_name, row_count) '
                    "VALUES (:t, :n)"
                ),
                {"t": name, "n": n},
            )
    return counts


def main() -> None:
    print("Ingesting raw CSVs into PostgreSQL ...")
    counts = ingest_all()
    total = sum(counts.values())
    print(f"Ingested {len(counts)} tables, {total:,} total rows into the raw schema.")


if __name__ == "__main__":
    main()
