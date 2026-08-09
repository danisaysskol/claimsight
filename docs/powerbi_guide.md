# ClaimSight — Power BI Build Guide

This project produces the warehouse and a complete DAX reference; the `.pbix`
itself is a proprietary binary you build in Power BI Desktop. Follow the steps
below against the `marts` / `reporting` schemas.

## 1. Connect Power BI Desktop to PostgreSQL (Windows 11)

1. Install the **Npgsql** provider (Power BI's PostgreSQL connector needs it):
   download Npgsql from nuget.org / the Npgsql site and install the GAC-enabled
   MSI, then restart Power BI Desktop.
2. **Home → Get Data → PostgreSQL database.**
3. Server: `localhost:5433` (the Docker-mapped port). Database: `claimsight`.
4. Data Connectivity mode: **Import**.
5. Credentials: Database → user `claimsight` / password `claimsight`
   (from `.env`). For a real deployment use a read-only role.

## 2. Which objects to import

Import the **marts** tables (they are physical tables, fast to import):

- `marts.dim_date`, `marts.dim_member`, `marts.dim_provider`,
  `marts.dim_employer_group`, `marts.dim_policy`, `marts.dim_diagnosis`,
  `marts.dim_procedure`, `marts.dim_claim_status`, `marts.dim_claim_type`
- `marts.fct_claim_header`, `marts.fct_claim_line`,
  `marts.fct_monthly_member_summary`

Leave the `reporting.*` views for ad-hoc/Excel/Streamlit use — do **not** import
them into the model (they would duplicate grain). Optionally import
`reporting.v_provider_scorecard` as a convenience table for a detail page.

## 3. Relationships (create in Model view)

| From (many) | To (one) | Key | Cardinality | Cross-filter |
|-------------|----------|-----|-------------|--------------|
| fct_claim_header[member_sk] | dim_member[member_sk] | member_sk | many-to-one | single |
| fct_claim_header[provider_sk] | dim_provider[provider_sk] | provider_sk | many-to-one | single |
| fct_claim_header[employer_group_sk] | dim_employer_group[employer_group_sk] | | many-to-one | single |
| fct_claim_header[policy_sk] | dim_policy[policy_sk] | | many-to-one | single |
| fct_claim_header[submission_date_key] | dim_date[date_key] | | many-to-one | single (**active**) |
| fct_claim_header[admission_date_key] | dim_date[date_key] | | many-to-one | single (inactive) |
| fct_claim_line[claim_line_sk→claim_id] | fct_claim_header[claim_id] | claim_id | many-to-one | single |
| fct_claim_line[procedure_sk] | dim_procedure[procedure_sk] | | many-to-one | single |
| fct_claim_line[diagnosis_sk] | dim_diagnosis[diagnosis_sk] | | many-to-one | single |
| fct_monthly_member_summary[member_sk] | dim_member[member_sk] | | many-to-one | single |

Only one relationship to `dim_date` can be active — keep **submission_date_key**
active; use `USERELATIONSHIP` in a measure if you need admission-date analysis.

## 4. Mark the date table

Model view → select `dim_date` → **Mark as date table** → date column
`date_day`. This enables the time-intelligence measures in `dax_measures.md`.

## 5. Page-by-page layout

**Page 1 — Executive Summary**
- KPI cards row: `Total Billed`, `Total Paid`, `Approval Rate`, `Denial Rate`, `PMPM Paid`.
- Line chart: `Total Billed` & `Total Paid` by `dim_date[year_month]`.
- Stacked bar: `Claim Count` by `dim_claim_type[claim_type]` and `status`.
- Map/bar: `Total Paid` by `dim_member[city]`.

**Page 2 — Claims Operations**
- Cards: `Auto Adjudication Rate`, `Median TAT`, `P90 TAT`, `Open Claims`.
- Histogram: `tat_submit_to_adjudicate` (binned) by `adjudication_mode`.
- Funnel: `Claim Count` by `status` (In Review→Pending→Partially Paid→Denied→Paid).
- Table: denial reasons with `Claim Count` and `Total Billed`.

**Page 3 — Financial Performance**
- Cards: `Loss Ratio`, `Savings Rate`, `Member Cost Share`, `Paid YoY %`.
- Line: `Paid Rolling 3M`.
- Bar: `Medical Loss Ratio` by `employer_name` (top 15).

**Page 4 — Provider Network**
- Cards: `Provider Concentration`, `OON Share`.
- Scatter: provider `Avg Claim Value` vs `Claim Count`, coloured by `network_status`.
- Bar: OON vs in-network avg unit price by procedure (from `v_network_cost_diff`).

**Page 5 — Risk & Data Quality**
- Table: anomalous providers (z-score).
- Table: duplicate candidates.
- DQ scorecard sourced from `dq.dq_results` (import that table too).

## 6. Theme

Import `docs/powerbi_theme.json` (Home → View → Themes → Browse for themes). It
uses the Okabe–Ito colourblind-safe palette with high contrast on light and dark
report backgrounds.

## 7. Bookmarks & drill-through

- Create a hidden **Provider Detail** page filtered by `dim_provider[provider_id]`;
  enable **Drill-through** on `provider_id`. Right-click a provider on Page 4 →
  Drill through → Provider Detail.
- Repeat a **Member Detail** drill-through on `dim_member[member_id]`.
- Add Bookmarks for "Denied only" and "Out-of-network only" filter states and a
  Selection-pane button to toggle them.

## 8. Row-level security (filter by employer group)

1. Modeling → **Manage roles** → New role `EmployerGroup`.
2. Table `dim_employer_group`, DAX filter:
   `[group_id] = LOOKUPVALUE(UserGroups[group_id], UserGroups[email], USERPRINCIPALNAME())`
   (map users→groups via a small `UserGroups` table), or for a single-group
   viewer: `[group_id] = "EG0001"`.
3. **View as role** to verify the fact tables filter down through the
   relationships.

## 9. Saving & screenshots

- Save the file as `powerbi/ClaimSight.pbix`.
- Export page screenshots (File → Export → or Win+Shift+S) into
  `docs/screenshots/` as `executive.png`, `operations.png`, `financial.png`,
  `network.png`, `data_quality.png`, then reference them in the README.
