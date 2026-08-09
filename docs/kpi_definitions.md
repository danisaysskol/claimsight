# ClaimSight KPI Definitions

Every KPI below is materialised as a view in the `reporting` schema and consumed
identically by the Streamlit dashboard, the Excel report and Power BI, so there
is exactly one definition per metric. Amounts are in **PKR**.

Base view: **`reporting.v_claims_enriched`** — one row per claim, denormalised
with member, employer, provider, policy and calendar attributes.

---

## Financial

| KPI | Plain-English definition | Formula (SQL) | View |
|-----|--------------------------|---------------|------|
| Total billed | Sum of amounts providers billed | `sum(billed_amount_pkr)` | `v_financial_monthly` |
| Total approved | Sum of adjudicated-approved amounts | `sum(approved_amount_pkr)` | `v_financial_monthly` |
| Total paid | Sum actually paid to providers | `sum(paid_amount_pkr)` | `v_financial_monthly` |
| Approval rate | Share of billed that is approved | `sum(approved)/sum(billed)` | `v_financial_monthly` |
| Savings rate | Share of billed avoided | `sum(billed-approved)/sum(billed)` | `v_financial_monthly` |
| Member cost share | Share of billed borne by members | `sum(member_share)/sum(billed)` | `v_financial_monthly` |
| Loss ratio | Paid claims ÷ earned premium | `sum(paid)/earned_premium` | `v_mlr_by_group` |
| Medical loss ratio (MLR) | Paid ÷ earned premium, per employer group | `sum(paid)/(monthly_premium*24)` | `v_mlr_by_group` |
| PMPM | Paid per member per month | `sum(paid)/member_months` | `v_pmpm` |
| IBNR (estimate) | Incurred-but-not-reported reserve, simple lag-triangle style estimate | see note below | documented |

**IBNR note.** A rigorous IBNR uses a claim-lag development triangle
(incurred month × reporting lag). ClaimSight ships a simplified estimator:
for each incurred month, IBNR ≈ (still-open billed for that month) scaled by the
historical open→paid conversion rate. The ageing view (`v_claims_ageing`) plus
`v_operations_monthly` provide the inputs; the DAX file includes a measure.

---

## Operational

| KPI | Definition | Formula | View |
|-----|-----------|---------|------|
| Claim volume | Count of claims by type/status/month | `count(*)` grouped | `v_operations_monthly` |
| Turnaround time (submit→adjudicate) | Days from submission to adjudication | `adjudication_date - submission_date` | `v_operations_monthly` |
| TAT mean / median / p90 | Central + tail latency | `avg`, `percentile_cont(0.5)`, `percentile_cont(0.9)` | `v_operations_monthly` |
| Auto-adjudication rate | Share adjudicated automatically | `avg((adjudication_mode='Auto')::int)` | `v_operations_monthly` |
| Denial rate | Share of claims denied | `avg((status='Denied')::int)` | `v_operations_monthly` |
| Denial reasons ranked | Denials by frequency and by value | `count(*)`, `sum(billed)` ranked | `v_denial_reasons` |
| Ageing buckets | Open claims by 0-30/31-60/61-90/90+ days | bucketed `days_open` | `v_claims_ageing` |

---

## Clinical & utilisation

| KPI | Definition | Formula | View |
|-----|-----------|---------|------|
| Utilisation per 1,000 members | Claims per 1,000 covered lives | `1000*count(*)/member_count` | `v_utilisation` |
| Average length of stay | Mean LOS for facility claims | `avg(length_of_stay)` | `v_utilisation` |
| Top 10 diagnoses | By line volume and billed cost | `count(*)`, `sum(line_billed)` | `v_top_diagnoses` |
| Top 10 procedures | By line volume and billed cost | `count(*)`, `sum(line_billed)` | `v_top_procedures` |
| Readmission proxy | Same member+chapter within 30 days | self-join ≤ 30 days | `v_readmissions` |

---

## Network

| KPI | Definition | Formula | View |
|-----|-----------|---------|------|
| In vs out-of-network cost | OON premium for the same procedure | `oon_avg / in_avg` per procedure | `v_network_cost_diff` |
| Provider concentration | Top-10 providers' share of spend | cumulative `paid/total` | `v_provider_concentration` |
| Provider scorecard | Volume, spend, denial rate, avg claim value | grouped aggregates | `v_provider_scorecard` |

---

## Risk & fraud signals

| KPI | Definition | Formula | View |
|-----|-----------|---------|------|
| Duplicate claim candidates | Same member/provider/date/amount > once | `group by … having count(*)>1` | `v_duplicate_candidates` |
| Provider billing anomaly | Avg claim value > peer mean + 2σ | z-score vs `provider_type` peers | `v_provider_anomaly` |
| High-frequency members | Claim count > population mean + 2σ | z-score vs member population | `v_high_frequency_members` |
| Upcoding proxy | High-cost procedure mix vs provider type | (documented; `v_provider_anomaly` + procedure category mix) | documented |
