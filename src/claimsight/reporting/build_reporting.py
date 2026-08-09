"""Create the ``reporting`` schema views from ``.sql`` files.

Each ``sql/*.sql`` file contains a single ``create or replace view`` statement.
Files are executed in filename order (numeric prefixes control dependencies),
so a base view can be referenced by later ones.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from claimsight.config import Settings, get_settings
from claimsight.db import ensure_schemas, get_engine

SQL_DIR = Path(__file__).resolve().parent / "sql"


def build_reporting(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    engine = get_engine(settings)
    ensure_schemas(engine, [settings.reporting_schema])

    files = sorted(SQL_DIR.glob("*.sql"))
    count = 0
    with engine.begin() as conn:
        conn.execute(text(f"SET search_path TO {settings.reporting_schema}, marts, public"))
        for f in files:
            sql = f.read_text(encoding="utf-8")
            conn.execute(text(sql))
            count += 1
    return count


def main() -> None:
    n = build_reporting()
    print(f"Built {n} reporting views.")


if __name__ == "__main__":
    main()
