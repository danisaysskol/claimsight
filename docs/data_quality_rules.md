# ClaimSight Data-Quality Rules

The engine (`src/claimsight/quality`) runs a declarative catalogue of **39 rules**
across the **six** data-quality dimensions. Each rule declares the SQL that
identifies failing rows; the engine is generic. Results land in `dq.dq_results`
and failing keys in `dq.dq_failed_records`. A composite, **severity-weighted**
score is produced per table, per dimension and overall.

Severity weights: critical=8, high=4, medium=2, low=1.
Score = `100 × Σ(weight × (1 − fail_rate)) / Σ(weight)`.

## The gate

Any **critical**-severity rule that fails halts the pipeline and exits `2`
(configurable via `DQ_FAIL_ON_CRITICAL`). Critical rules are structural
invariants clean data always satisfies (primary-key uniqueness, key presence),
so a normal run proceeds; a genuine breach stops it. Injected defects are
high/medium/low — they are caught, quarantined and reported without halting.

## Rules by dimension

### Completeness (7)
- `C-HDR-ADJMODE` (medium) — adjudication_mode populated → catches injected nulls
- `C-HDR-CLAIMID` / `C-HDR-MEMBERID` / `C-HDR-PROVIDERID` (critical) — keys present
- `C-LINE-CLAIMID` (critical) — line carries parent claim id
- `C-MBR-DOB` / `C-MBR-POLICY` (high) — member DOB / policy present

### Validity (12)
- `V-HDR-STATUS`, `V-HDR-CTYPE` (high) — accepted status / claim-type values
- `V-HDR-ADJMODE` (low) — Auto/Manual when present
- `V-MBR-GENDER` (medium), `V-MBR-REL` (low) — accepted member values
- `V-PRV-NETWORK` (medium), `V-PRV-TYPE` (low) — accepted provider values
- `V-POL-TIER` (low), `V-POL-COPAY` (low) — accepted policy values / copay range
- `V-HDR-DATEPARSE` (medium) — submission date parses (validates mixed-format handling)
- `V-MBR-AGE` (high) — age 0–120 → catches injected impossible ages
- `R-HDR-MEMBER-FK`, `R-HDR-PROVIDER-FK`, `R-LINE-CLAIM-FK` (high) — referential integrity → catches injected orphans

### Consistency (6)
- `K-HDR-DISCHARGE` (high) — discharge ≥ admission → catches injected date violations
- `K-HDR-SUBMIT` (medium) — submission ≥ discharge
- `K-MBR-CITY`, `K-PRV-CITY`, `K-GRP-CITY` (low) — canonical city casing → catches injected casing/whitespace
- `K-HDR-DENIAL` (medium) — denial reason consistent with status

### Uniqueness (5)
- `U-HDR-CLAIMID`, `U-LINE-ID`, `U-MBR-ID`, `U-PRV-ID` (critical) — primary-key uniqueness
- `U-HDR-BIZDUP` (high) — no duplicate business claims → catches injected duplicates

### Accuracy (4)
- `A-HDR-APPR-BILLED` (high) — approved ≤ billed → catches injected amount violations
- `A-HDR-PAID-APPR` (high) — paid ≤ approved
- `A-HDR-NONNEG` (high) — billed > 0 → catches injected negative/zero amounts
- `A-LINE-MATH` (low) — line billed ≈ unit price × quantity

### Timeliness (3)
- `T-HDR-ADJ-LAG` (low) — adjudicated within 60 days of submission
- `T-HDR-PAYMENT` (medium) — payment ≥ adjudication
- `T-HDR-SUBMIT-LAG` (low) — submitted within 30 days of discharge

## Injected-defect → rule mapping (verified by the test-suite)

| Injected defect | Manifest key | Caught by | Match |
|-----------------|--------------|-----------|-------|
| Duplicate claims | `duplicate_claims` | `U-HDR-BIZDUP` | ≥ |
| Null adjudication_mode | `null_values` | `C-HDR-ADJMODE` | = |
| Orphan member FK | `orphan_fk_member` | `R-HDR-MEMBER-FK` | = |
| Orphan provider FK | `orphan_fk_provider` | `R-HDR-PROVIDER-FK` | = |
| Discharge before admission | `date_violations` | `K-HDR-DISCHARGE` | = |
| Approved>billed / paid>approved | `amount_violations` | `A-HDR-APPR-BILLED`, `A-HDR-PAID-APPR` | ≥ |
| Negative/zero amounts | `nonpositive_amounts` | `A-HDR-NONNEG` | = |
| Impossible ages | `impossible_ages` | `V-MBR-AGE` | = |
| City casing/whitespace | `city_casing_variants` | `K-*-CITY` | ≥ |
| Mixed date formats | `mixed_date_format_values` | handled by parser; `V-HDR-DATEPARSE` stays green | n/a |

`tests/test_quality.py` asserts these relationships against the manifest.
