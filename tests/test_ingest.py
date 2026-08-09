"""Ingestion tests: dirt-preservation (unit) and row-count reconciliation (integration)."""

from __future__ import annotations

import pandas as pd

from claimsight.ingest.ingest import load_csv_as_text


def test_load_csv_preserves_dirt(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text(
        "a,b,c\n"
        "1,,karachi \n"          # empty middle, trailing space preserved
        "2,3.5,KARACHI\n",
        encoding="utf-8",
    )
    df = load_csv_as_text(csv)
    # Everything is text; nothing coerced to NaN/float.
    assert list(df.columns) == ["a", "b", "c"]
    assert df.loc[0, "b"] == ""            # empty preserved as ''
    assert df.loc[0, "c"] == "karachi "    # trailing whitespace preserved
    assert df["a"].dtype == object


def test_ingest_reconciles_counts(db_engine, tmp_path):
    from claimsight.config import get_settings
    from claimsight.generate.generate import generate, write_outputs
    from claimsight.ingest.ingest import ingest_all

    settings = get_settings().model_copy(update={"raw_schema": "raw_test_ingest"})
    result = generate(seed=55, target_lines=1200)
    write_outputs(result, tmp_path)
    counts = ingest_all(settings=settings, raw_dir=tmp_path)

    for name, df in result.tables.items():
        assert counts[name] == len(df)

    # And the data really landed.
    with db_engine.connect() as conn:
        n = pd.read_sql(
            f'SELECT count(*) AS n FROM "{settings.raw_schema}".claims_header', conn
        )["n"].iloc[0]
    assert n == len(result.tables["claims_header"])
