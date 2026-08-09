"""ClaimSight — Streamlit analytics dashboard.

Five pages (Executive Summary, Claims Operations, Financial Performance,
Provider Network, Data Quality) reading from the ``reporting`` schema views.
Charts use a colourblind-safe palette and always pair colour with a label.

Run with:  streamlit run dashboard/app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import apply_filters, load_dq_latest, load_dq_trend, load_view
from theme import NETWORK_COLORS, OKABE_ITO, STATUS_COLORS, apply_plotly_layout, pkr

st.set_page_config(page_title="ClaimSight", page_icon="🩺", layout="wide")


# --------------------------------------------------------------------------- #
# Data + filters
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=600)
def get_claims() -> pd.DataFrame:
    df = load_view("v_claims_enriched")
    if not df.empty:
        df["claim_date"] = pd.to_datetime(df["claim_date"])
    return df


def sidebar_filters(claims: pd.DataFrame) -> dict:
    st.sidebar.title("🩺 ClaimSight")
    st.sidebar.caption("TPA Claims Analytics — synthetic Pakistani data")
    filters: dict = {}
    if claims.empty:
        return filters
    valid_dates = claims["claim_date"].dropna()
    if not valid_dates.empty:
        dmin, dmax = valid_dates.min().date(), valid_dates.max().date()
        filters["date_range"] = st.sidebar.date_input(
            "Submission date range", value=(dmin, dmax), min_value=dmin, max_value=dmax
        )
    filters["employer"] = st.sidebar.multiselect(
        "Employer group", sorted(claims["employer_name"].dropna().unique())
    )
    filters["claim_type"] = st.sidebar.multiselect(
        "Claim type", sorted(claims["claim_type"].dropna().unique())
    )
    filters["city"] = st.sidebar.multiselect(
        "Member city", sorted(claims["member_city"].dropna().unique())
    )
    filters["network"] = st.sidebar.multiselect(
        "Network status", sorted(claims["network_status"].dropna().unique())
    )
    return filters


def kpi_delta(series_by_month: pd.Series) -> float | None:
    """Return the period-over-period % change of the last two months."""
    if len(series_by_month) < 2:
        return None
    prev, curr = series_by_month.iloc[-2], series_by_month.iloc[-1]
    if prev == 0:
        return None
    return (curr - prev) / prev * 100.0


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_executive(claims: pd.DataFrame) -> None:
    st.header("Executive Summary")
    if claims.empty:
        st.warning("No data. Run the pipeline (generate → ingest → dbt build → reporting) first.")
        return

    monthly = claims.groupby("year_month").agg(
        billed=("billed_amount_pkr", "sum"),
        paid=("paid_amount_pkr", "sum"),
        claims=("claim_id", "count"),
        denied=("is_denied", "sum"),
    )
    total_billed = claims["billed_amount_pkr"].sum()
    total_paid = claims["paid_amount_pkr"].sum()
    denial_rate = claims["is_denied"].mean() * 100
    savings_rate = claims["savings_pkr"].sum() / total_billed * 100 if total_billed else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Claims", f"{len(claims):,}", f"{kpi_delta(monthly['claims']):+.1f}%" if kpi_delta(monthly['claims']) is not None else None)
    c2.metric("Billed", pkr(total_billed), f"{kpi_delta(monthly['billed']):+.1f}%" if kpi_delta(monthly['billed']) is not None else None)
    c3.metric("Paid", pkr(total_paid), f"{kpi_delta(monthly['paid']):+.1f}%" if kpi_delta(monthly['paid']) is not None else None)
    c4.metric("Denial rate", f"{denial_rate:.1f}%")
    c5.metric("Savings rate", f"{savings_rate:.1f}%")

    left, right = st.columns(2)
    with left:
        st.subheader("Paid vs billed by month")
        m = monthly.reset_index()
        fig = go.Figure()
        fig.add_bar(x=m["year_month"], y=m["billed"], name="Billed", marker_color=OKABE_ITO[0])
        fig.add_bar(x=m["year_month"], y=m["paid"], name="Paid", marker_color=OKABE_ITO[2])
        fig.update_layout(barmode="group")
        st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)
    with right:
        st.subheader("Claim status mix")
        status = claims["status"].value_counts().reset_index()
        status.columns = ["status", "count"]
        fig = px.bar(
            status, x="count", y="status", orientation="h", text="count",
            color="status", color_discrete_map=STATUS_COLORS,
        )
        st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)

    st.subheader("Spend by city")
    city = claims.groupby("member_city")["paid_amount_pkr"].sum().reset_index()
    fig = px.bar(city.sort_values("paid_amount_pkr"), x="paid_amount_pkr", y="member_city",
                 orientation="h", text_auto=".2s")
    st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def page_operations(claims: pd.DataFrame) -> None:
    st.header("Claims Operations")
    if claims.empty:
        st.warning("No data available.")
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Auto-adjudication rate", f"{claims['is_auto'].mean() * 100:.1f}%")
    c2.metric("Mean TAT (submit→adj)", f"{claims['tat_submit_to_adjudicate'].mean():.1f} days")
    c3.metric("Median TAT (submit→adj)", f"{claims['tat_submit_to_adjudicate'].median():.1f} days")
    c4.metric("90th pct TAT", f"{claims['tat_submit_to_adjudicate'].quantile(0.9):.0f} days")

    left, right = st.columns(2)
    with left:
        st.subheader("Claim volume by type")
        vol = claims["claim_type"].value_counts().reset_index()
        vol.columns = ["claim_type", "count"]
        fig = px.bar(vol, x="claim_type", y="count", text="count", color="claim_type",
                     color_discrete_sequence=OKABE_ITO)
        st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)
    with right:
        st.subheader("Turnaround time distribution")
        fig = px.histogram(claims, x="tat_submit_to_adjudicate", nbins=40,
                           color="adjudication_mode", color_discrete_sequence=OKABE_ITO,
                           barmode="overlay")
        st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)

    st.subheader("Adjudication funnel")
    order = ["In Review", "Pending", "Partially Paid", "Denied", "Paid"]
    counts = claims["status"].value_counts()
    funnel = go.Figure(go.Funnel(
        y=order, x=[int(counts.get(s, 0)) for s in order],
        marker=dict(color=[STATUS_COLORS[s] for s in order]),
    ))
    st.plotly_chart(apply_plotly_layout(funnel), use_container_width=True)

    st.subheader("Denial reasons")
    denials = load_view("v_denial_reasons")
    if not denials.empty:
        st.dataframe(denials, use_container_width=True, hide_index=True)


def page_financial(claims: pd.DataFrame) -> None:
    st.header("Financial Performance")
    if claims.empty:
        st.warning("No data available.")
        return
    fin = load_view("v_financial_monthly")
    if not fin.empty:
        fig = go.Figure()
        for col, name, color in [
            ("billed_pkr", "Billed", OKABE_ITO[0]),
            ("approved_pkr", "Approved", OKABE_ITO[1]),
            ("paid_pkr", "Paid", OKABE_ITO[2]),
        ]:
            fig.add_trace(go.Scatter(x=fin["year_month"], y=fin[col], name=name,
                                     mode="lines+markers", line=dict(color=color, width=3)))
        st.subheader("Billed / approved / paid trend")
        st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Medical loss ratio by employer (top 15)")
        mlr = load_view("v_mlr_by_group").head(15)
        if not mlr.empty:
            fig = px.bar(mlr.sort_values("medical_loss_ratio"),
                         x="medical_loss_ratio", y="employer_name", orientation="h",
                         color_discrete_sequence=[OKABE_ITO[5]])
            st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)
    with right:
        st.subheader("PMPM (paid per member per month)")
        pmpm = load_view("v_pmpm")
        if not pmpm.empty:
            fig = px.line(pmpm, x="year_month", y="pmpm_paid_pkr", markers=True,
                          color_discrete_sequence=[OKABE_ITO[2]])
            st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def page_network(claims: pd.DataFrame) -> None:
    st.header("Provider Network")
    scorecard = load_view("v_provider_scorecard")
    conc = load_view("v_provider_concentration")
    diff = load_view("v_network_cost_diff")
    anomaly = load_view("v_provider_anomaly")

    if not conc.empty:
        top10_share = conc.head(10)["spend_share"].sum() * 100
        st.metric("Top-10 provider spend concentration", f"{top10_share:.1f}%")

    left, right = st.columns(2)
    with left:
        st.subheader("In-network vs out-of-network cost (same procedure)")
        if not diff.empty:
            d = diff.dropna(subset=["oon_cost_multiple"]).head(15)
            fig = px.bar(d, x="oon_cost_multiple", y="description", orientation="h",
                         color_discrete_sequence=[NETWORK_COLORS["Out-of-Network"]])
            fig.add_vline(x=1.0, line_dash="dash")
            st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)
    with right:
        st.subheader("Anomalous providers (avg claim value > peer +2σ)")
        if not anomaly.empty:
            flagged = anomaly[anomaly["is_anomalous"]]
            st.metric("Flagged providers", f"{len(flagged)}")
            st.dataframe(
                anomaly.head(15)[["hospital_name", "provider_type", "avg_claim_value", "z_score", "is_anomalous"]],
                use_container_width=True, hide_index=True,
            )

    st.subheader("Provider scorecard")
    if not scorecard.empty:
        st.dataframe(scorecard.head(50), use_container_width=True, hide_index=True)


def page_data_quality() -> None:
    st.header("Data Quality")
    dq = load_dq_latest()
    if dq.empty:
        st.warning("No data-quality runs found. Run the quality engine first.")
        return
    passed = int(dq["passed"].sum())
    total = len(dq)
    total_failed_rows = int(dq["rows_failed"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Rules passing", f"{passed}/{total}")
    c2.metric("Total failing rows", f"{total_failed_rows:,}")
    c3.metric("Critical failures", f"{int(((dq['severity'] == 'critical') & (~dq['passed'])).sum())}")

    st.subheader("Rule results")
    view = dq[["rule_id", "rule_name", "dimension", "severity", "rows_checked",
               "rows_failed", "fail_rate", "passed"]].copy()
    view["fail_rate"] = (view["fail_rate"] * 100).round(2)
    st.dataframe(view, use_container_width=True, hide_index=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Failing rows by dimension")
        by_dim = dq.groupby("dimension")["rows_failed"].sum().reset_index()
        fig = px.bar(by_dim, x="dimension", y="rows_failed", color="dimension",
                     color_discrete_sequence=OKABE_ITO)
        st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)
    with right:
        st.subheader("Quality trend across runs")
        trend = load_dq_trend()
        if not trend.empty:
            fig = px.line(trend, x="run_id", y="total_failed", markers=True,
                          color_discrete_sequence=[OKABE_ITO[5]])
            st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
def main() -> None:
    try:
        claims_all = get_claims()
    except Exception as exc:  # noqa: BLE001
        st.error(
            "Could not load data from the reporting schema. Is PostgreSQL up and the "
            f"pipeline built?\n\n{exc}"
        )
        claims_all = pd.DataFrame()

    filters = sidebar_filters(claims_all)
    claims = apply_filters(claims_all, filters) if not claims_all.empty else claims_all

    page = st.sidebar.radio(
        "Page",
        ["Executive Summary", "Claims Operations", "Financial Performance",
         "Provider Network", "Data Quality"],
    )
    if not claims_all.empty:
        st.sidebar.caption(f"Showing {len(claims):,} of {len(claims_all):,} claims")

    if page == "Executive Summary":
        page_executive(claims)
    elif page == "Claims Operations":
        page_operations(claims)
    elif page == "Financial Performance":
        page_financial(claims)
    elif page == "Provider Network":
        page_network(claims)
    else:
        page_data_quality()


main()
