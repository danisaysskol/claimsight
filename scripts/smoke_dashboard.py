"""Smoke test for the dashboard data contract.

Confirms every reporting view and DQ table the Streamlit pages read is present
and returns rows. Run: ``python scripts/smoke_dashboard.py`` (needs the warehouse
built). Exits non-zero if any query fails or a critical view is empty.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text  # noqa: E402

from claimsight.config import get_settings  # noqa: E402
from claimsight.db import get_engine  # noqa: E402

VIEWS = [
    "v_claims_enriched", "v_financial_monthly", "v_mlr_by_group", "v_pmpm",
    "v_operations_monthly", "v_denial_reasons", "v_claims_ageing",
    "v_top_diagnoses", "v_top_procedures", "v_utilisation", "v_readmissions",
    "v_network_cost_diff", "v_provider_scorecard", "v_provider_concentration",
    "v_provider_anomaly", "v_duplicate_candidates", "v_high_frequency_members",
]
# Views that must not be empty for the dashboard to be meaningful.
MUST_HAVE_ROWS = {"v_claims_enriched", "v_financial_monthly", "v_provider_scorecard"}


def main() -> int:
    settings = get_settings()
    engine = get_engine(settings)
    ok = True
    with engine.connect() as conn:
        for v in VIEWS:
            n = conn.execute(
                text(f'SELECT count(*) FROM "{settings.reporting_schema}"."{v}"')
            ).scalar_one()
            flag = "OK" if (n > 0 or v not in MUST_HAVE_ROWS) else "EMPTY!"
            if flag == "EMPTY!":
                ok = False
            print(f"  reporting.{v:28s} {n:>7,} rows  [{flag}]")
        for t in ("dq.dq_results", "dq.dq_failed_records"):
            n = conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
            print(f"  {t:38s} {n:>7,} rows")
    print("DATA-LAYER SMOKE OK" if ok else "DATA-LAYER SMOKE FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
