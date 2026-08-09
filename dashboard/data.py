"""Cached data access for the Streamlit dashboard.

All queries read from the ``reporting`` schema views so the dashboard, Excel and
Power BI share one definition of every metric.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make the ``claimsight`` package importable when run via ``streamlit run``.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from claimsight.config import get_settings  # noqa: E402
from claimsight.db import get_engine  # noqa: E402


@st.cache_resource
def _engine():
    return get_engine(get_settings())


@st.cache_data(ttl=600)
def load_view(name: str) -> pd.DataFrame:
    """Load a reporting view into a DataFrame (cached for 10 minutes)."""
    settings = get_settings()
    with _engine().connect() as conn:
        return pd.read_sql(f'SELECT * FROM "{settings.reporting_schema}"."{name}"', conn)


@st.cache_data(ttl=600)
def load_dq_latest() -> pd.DataFrame:
    """Load the most recent data-quality run's rule results."""
    with _engine().connect() as conn:
        return pd.read_sql(
            "SELECT * FROM dq.dq_results WHERE run_id = "
            "(SELECT max(run_id) FROM dq.dq_results) ORDER BY severity, rule_id",
            conn,
        )


@st.cache_data(ttl=600)
def load_dq_trend() -> pd.DataFrame:
    with _engine().connect() as conn:
        return pd.read_sql(
            "SELECT run_id, avg(fail_rate) as avg_fail_rate, "
            "sum(rows_failed) as total_failed FROM dq.dq_results GROUP BY run_id ORDER BY run_id",
            conn,
        )


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply the sidebar filters to the enriched claims frame."""
    out = df
    if filters.get("date_range") and "claim_date" in out.columns:
        start, end = filters["date_range"]
        cd = pd.to_datetime(out["claim_date"])
        out = out[(cd >= pd.Timestamp(start)) & (cd <= pd.Timestamp(end))]
    for col, key in [
        ("employer_name", "employer"),
        ("claim_type", "claim_type"),
        ("member_city", "city"),
        ("network_status", "network"),
    ]:
        vals = filters.get(key)
        if vals and col in out.columns:
            out = out[out[col].isin(vals)]
    return out
