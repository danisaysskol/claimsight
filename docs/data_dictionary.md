# ClaimSight Data Dictionary

Synthetic data — **no real patient information**. Amounts in PKR. Identifiers are
fabricated; CNICs are masked (`NNNNN-*******-N`).

## Source / `raw` tables (loaded as text, dirt preserved)

### members
| Column | Type | Notes |
|--------|------|-------|
| member_id | text | PK, `MB######` |
| masked_cnic | text | Masked, fake |
| name | text | Faker-generated |
| gender | text | Male / Female |
| date_of_birth | date* | Mixed ISO/`DD-MM-YYYY`; ~0.4% impossible ages injected |
| city | text | Pakistani city; inconsistent casing injected |
| employer_group_id | text | FK → employer_groups |
| policy_id | text | FK → policies |
| enrolment_date | date* | **Mixed date formats** |
| termination_date | date* | Mostly empty |
| relationship | text | Self / Spouse / Child |

### employer_groups
group_id (PK), name, industry, city, contract_start, contract_end, lives_covered, monthly_premium_pkr.

### policies
policy_id (PK), plan_name, plan_tier (Bronze/Silver/Gold/Platinum), annual_limit_pkr, room_rent_cap_pkr, deductible_pkr, copay_pct, maternity_covered, pre_existing_waiting_months.

### providers
provider_id (PK), hospital_name, city, provider_type (Hospital/Clinic/Diagnostic/Pharmacy), network_status (In-Network/Out-of-Network), tier (A/B/C), panel_since.

### diagnoses
diagnosis_code (PK, ICD-10-style), description, chapter.

### procedures
procedure_code (PK, CPT-style), description, category, typical_cost_pkr.

### claims_header
| Column | Type | Notes |
|--------|------|-------|
| claim_id | text | PK, `CLM#######` (`CLMDUP*` = injected duplicate) |
| member_id | text | FK; ~0.5%/2 orphaned (`MB999999`) |
| provider_id | text | FK; ~0.5%/2 orphaned (`PR9999`) |
| policy_id | text | FK |
| claim_type | text | Inpatient/Outpatient/Daycare/Pharmacy/Diagnostic/Maternity/Emergency |
| admission_date / discharge_date | date* | ~0.8% discharge<admission injected |
| submission_date | date* | **Mixed date formats**; ≥ discharge |
| adjudication_date / payment_date | date* | May be empty for open claims |
| status | text | Paid/Denied/Pending/Partially Paid/In Review |
| denial_reason_code | text | Present only for denials (DR01–DR10) |
| billed_amount_pkr | numeric | ~0.3% negative/zero injected |
| approved_amount_pkr | numeric | ~0.6% approved>billed injected |
| paid_amount_pkr | numeric | ~0.6% paid>approved injected |
| member_share_pkr | numeric | Deductible + copay |
| adjudication_mode | text | Auto/Manual; ~1.5% nulled |

### claims_lines
claim_line_id (PK), claim_id (FK), line_no, procedure_code (FK), diagnosis_code (FK), quantity, unit_price_pkr, line_billed_pkr, line_approved_pkr.

\* Stored as **text** in `raw`; parsed to real `date` in dbt staging.

## `marts` star schema

- **Dimensions:** `dim_date`, `dim_member` (SCD2), `dim_provider` (SCD2),
  `dim_employer_group`, `dim_policy`, `dim_diagnosis`, `dim_procedure`,
  `dim_claim_status`, `dim_claim_type`. Each has a surrogate `*_sk` key.
- **Facts:** `fct_claim_line` (line grain), `fct_claim_header` (claim grain, with
  turnaround-time measures), `fct_monthly_member_summary` (member×month).

Full column-level docs live in the dbt `schema.yml` files and `dbt docs generate`.

## `reporting` views
See `kpi_definitions.md` for the 17 KPI views and their formulas.

## `dq` schema
- `dq_results` — one row per rule per run (rows_checked, rows_failed, fail_rate, passed).
- `dq_failed_records` — quarantined failing record keys per rule per run.
