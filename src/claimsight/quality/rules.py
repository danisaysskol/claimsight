"""Declarative data-quality rule model and rule catalogue.

Each rule is a small, self-describing pydantic object carrying the SQL needed to
(a) count the rows checked and (b) identify the rows that fail. The engine
(``engine.py``) is generic — it knows nothing about individual rules, it just
executes whatever SQL the catalogue declares. Adding a rule = adding a Rule().

SQL uses ``{s}`` as a placeholder for the raw schema name and the helper
function ``cs_parse_date(text)`` (created by the engine) to cope with the mixed
date formats deliberately planted in the source data.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# The fixed end of the simulation window; used for age sanity checks.
WINDOW_END_SQL = "DATE '2026-06-30'"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Dimension(StrEnum):
    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    UNIQUENESS = "uniqueness"
    ACCURACY = "accuracy"
    TIMELINESS = "timeliness"


SEVERITY_WEIGHT: dict[Severity, int] = {
    Severity.CRITICAL: 8,
    Severity.HIGH: 4,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
}


class Rule(BaseModel):
    """A single declarative data-quality check."""

    id: str
    name: str
    dimension: Dimension
    severity: Severity
    table: str
    column: str | None = None
    description: str
    # Max acceptable failure rate for the rule to be considered "passing".
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    # SQL returning failing rows, each exposing a `record_key` column. {s}=schema.
    failing_sql: str
    # SQL returning a single integer = rows checked. Defaults to count(*).
    checked_sql: str | None = None

    def resolved_checked_sql(self, schema: str) -> str:
        sql = self.checked_sql or f'SELECT count(*) FROM "{{s}}"."{self.table}"'
        return sql.replace("{s}", schema)

    def resolved_failing_sql(self, schema: str) -> str:
        return self.failing_sql.replace("{s}", schema)


def _num(col: str) -> str:
    """Cast a text column to numeric, treating '' as NULL."""
    return f"NULLIF({col}, '')::numeric"


# --------------------------------------------------------------------------- #
# Rule catalogue (39 rules across all six dimensions)
# --------------------------------------------------------------------------- #
RULES: list[Rule] = [
    # ----------------------------- COMPLETENESS ---------------------------- #
    Rule(
        id="C-HDR-ADJMODE", name="Adjudication mode is populated",
        dimension=Dimension.COMPLETENESS, severity=Severity.MEDIUM,
        table="claims_header", column="adjudication_mode",
        description="Every claim must record how it was adjudicated (Auto/Manual).",
        failing_sql='SELECT claim_id AS record_key FROM "{s}".claims_header '
                    "WHERE adjudication_mode IS NULL OR adjudication_mode = ''",
    ),
    Rule(
        id="C-HDR-CLAIMID", name="Claim id is present",
        dimension=Dimension.COMPLETENESS, severity=Severity.CRITICAL,
        table="claims_header", column="claim_id",
        description="Claim id is the primary key and can never be missing.",
        failing_sql='SELECT claim_id AS record_key FROM "{s}".claims_header '
                    "WHERE claim_id IS NULL OR claim_id = ''",
    ),
    Rule(
        id="C-HDR-MEMBERID", name="Member id is present on claim",
        dimension=Dimension.COMPLETENESS, severity=Severity.CRITICAL,
        table="claims_header", column="member_id",
        description="A claim must always be attributable to a member.",
        failing_sql='SELECT claim_id AS record_key FROM "{s}".claims_header '
                    "WHERE member_id IS NULL OR member_id = ''",
    ),
    Rule(
        id="C-HDR-PROVIDERID", name="Provider id is present on claim",
        dimension=Dimension.COMPLETENESS, severity=Severity.CRITICAL,
        table="claims_header", column="provider_id",
        description="A claim must always name the servicing provider.",
        failing_sql='SELECT claim_id AS record_key FROM "{s}".claims_header '
                    "WHERE provider_id IS NULL OR provider_id = ''",
    ),
    Rule(
        id="C-LINE-CLAIMID", name="Claim line references a claim",
        dimension=Dimension.COMPLETENESS, severity=Severity.CRITICAL,
        table="claims_lines", column="claim_id",
        description="Every claim line must carry its parent claim id.",
        failing_sql='SELECT claim_line_id AS record_key FROM "{s}".claims_lines '
                    "WHERE claim_id IS NULL OR claim_id = ''",
    ),
    Rule(
        id="C-MBR-DOB", name="Member date of birth is present",
        dimension=Dimension.COMPLETENESS, severity=Severity.HIGH,
        table="members", column="date_of_birth",
        description="Date of birth is required for age and eligibility logic.",
        failing_sql='SELECT member_id AS record_key FROM "{s}".members '
                    "WHERE date_of_birth IS NULL OR date_of_birth = ''",
    ),
    Rule(
        id="C-MBR-POLICY", name="Member policy id is present",
        dimension=Dimension.COMPLETENESS, severity=Severity.HIGH,
        table="members", column="policy_id",
        description="A member must be linked to a policy.",
        failing_sql='SELECT member_id AS record_key FROM "{s}".members '
                    "WHERE policy_id IS NULL OR policy_id = ''",
    ),
    # ------------------------------- VALIDITY ------------------------------ #
    Rule(
        id="V-HDR-STATUS", name="Claim status is a known value",
        dimension=Dimension.VALIDITY, severity=Severity.HIGH,
        table="claims_header", column="status",
        description="Status must be one of the accepted adjudication states.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE status NOT IN ('Paid','Denied','Pending','Partially Paid','In Review')",
    ),
    Rule(
        id="V-HDR-CTYPE", name="Claim type is a known value",
        dimension=Dimension.VALIDITY, severity=Severity.HIGH,
        table="claims_header", column="claim_type",
        description="Claim type must be one of the accepted categories.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE claim_type NOT IN "
                    "('Inpatient','Outpatient','Daycare','Pharmacy','Diagnostic','Maternity','Emergency')",
    ),
    Rule(
        id="V-HDR-ADJMODE", name="Adjudication mode value is valid",
        dimension=Dimension.VALIDITY, severity=Severity.LOW,
        table="claims_header", column="adjudication_mode",
        description="When present, adjudication mode must be Auto or Manual.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE adjudication_mode <> '' AND adjudication_mode IS NOT NULL "
                    "AND adjudication_mode NOT IN ('Auto','Manual')",
    ),
    Rule(
        id="V-MBR-GENDER", name="Member gender is valid",
        dimension=Dimension.VALIDITY, severity=Severity.MEDIUM,
        table="members", column="gender",
        description="Gender must be Male or Female.",
        failing_sql="SELECT member_id AS record_key FROM \"{s}\".members "
                    "WHERE gender NOT IN ('Male','Female')",
    ),
    Rule(
        id="V-MBR-REL", name="Member relationship is valid",
        dimension=Dimension.VALIDITY, severity=Severity.LOW,
        table="members", column="relationship",
        description="Relationship must be Self, Spouse or Child.",
        failing_sql="SELECT member_id AS record_key FROM \"{s}\".members "
                    "WHERE relationship NOT IN ('Self','Spouse','Child')",
    ),
    Rule(
        id="V-PRV-NETWORK", name="Provider network status is valid",
        dimension=Dimension.VALIDITY, severity=Severity.MEDIUM,
        table="providers", column="network_status",
        description="Network status must be In-Network or Out-of-Network.",
        failing_sql="SELECT provider_id AS record_key FROM \"{s}\".providers "
                    "WHERE network_status NOT IN ('In-Network','Out-of-Network')",
    ),
    Rule(
        id="V-PRV-TYPE", name="Provider type is valid",
        dimension=Dimension.VALIDITY, severity=Severity.LOW,
        table="providers", column="provider_type",
        description="Provider type must be a known category.",
        failing_sql="SELECT provider_id AS record_key FROM \"{s}\".providers "
                    "WHERE provider_type NOT IN ('Hospital','Clinic','Diagnostic','Pharmacy')",
    ),
    Rule(
        id="V-POL-TIER", name="Plan tier is valid",
        dimension=Dimension.VALIDITY, severity=Severity.LOW,
        table="policies", column="plan_tier",
        description="Plan tier must be Bronze/Silver/Gold/Platinum.",
        failing_sql="SELECT policy_id AS record_key FROM \"{s}\".policies "
                    "WHERE plan_tier NOT IN ('Bronze','Silver','Gold','Platinum')",
    ),
    Rule(
        id="V-POL-COPAY", name="Copay percentage in range",
        dimension=Dimension.VALIDITY, severity=Severity.LOW,
        table="policies", column="copay_pct",
        description="Copay percentage must be between 0 and 1.",
        failing_sql=f"SELECT policy_id AS record_key FROM \"{{s}}\".policies "
                    f"WHERE {_num('copay_pct')} < 0 OR {_num('copay_pct')} > 1",
    ),
    Rule(
        id="V-HDR-DATEPARSE", name="Submission date is parseable",
        dimension=Dimension.VALIDITY, severity=Severity.MEDIUM,
        table="claims_header", column="submission_date",
        description="Submission date must parse under a known date format.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE submission_date <> '' AND cs_parse_date(submission_date) IS NULL",
    ),
    Rule(
        id="V-MBR-AGE", name="Member age is plausible",
        dimension=Dimension.VALIDITY, severity=Severity.HIGH,
        table="members", column="date_of_birth",
        description="Age derived from DOB must be between 0 and 120 years.",
        failing_sql="SELECT member_id AS record_key FROM \"{s}\".members "
                    "WHERE cs_parse_date(date_of_birth) IS NULL "
                    f"OR cs_parse_date(date_of_birth) > {WINDOW_END_SQL} "
                    f"OR ({WINDOW_END_SQL} - cs_parse_date(date_of_birth)) > 120*365",
    ),
    # ----------------------------- CONSISTENCY ----------------------------- #
    Rule(
        id="K-HDR-DISCHARGE", name="Discharge is not before admission",
        dimension=Dimension.CONSISTENCY, severity=Severity.HIGH,
        table="claims_header", column="discharge_date",
        description="Discharge date must be on or after the admission date.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE cs_parse_date(discharge_date) < cs_parse_date(admission_date)",
    ),
    Rule(
        id="K-HDR-SUBMIT", name="Submission is not before discharge",
        dimension=Dimension.CONSISTENCY, severity=Severity.MEDIUM,
        table="claims_header", column="submission_date",
        description="A claim cannot be submitted before the patient is discharged.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE submission_date <> '' AND discharge_date <> '' "
                    "AND cs_parse_date(submission_date) < cs_parse_date(discharge_date)",
    ),
    Rule(
        id="K-MBR-CITY", name="Member city is canonical",
        dimension=Dimension.CONSISTENCY, severity=Severity.LOW,
        table="members", column="city",
        description="City must have no stray casing/whitespace (canonical form).",
        failing_sql="SELECT member_id AS record_key FROM \"{s}\".members "
                    "WHERE city <> initcap(btrim(city)) OR city <> btrim(city)",
    ),
    Rule(
        id="K-PRV-CITY", name="Provider city is canonical",
        dimension=Dimension.CONSISTENCY, severity=Severity.LOW,
        table="providers", column="city",
        description="City must have no stray casing/whitespace (canonical form).",
        failing_sql="SELECT provider_id AS record_key FROM \"{s}\".providers "
                    "WHERE city <> initcap(btrim(city)) OR city <> btrim(city)",
    ),
    Rule(
        id="K-GRP-CITY", name="Employer city is canonical",
        dimension=Dimension.CONSISTENCY, severity=Severity.LOW,
        table="employer_groups", column="city",
        description="City must have no stray casing/whitespace (canonical form).",
        failing_sql="SELECT group_id AS record_key FROM \"{s}\".employer_groups "
                    "WHERE city <> initcap(btrim(city)) OR city <> btrim(city)",
    ),
    Rule(
        id="K-HDR-DENIAL", name="Denial reason consistent with status",
        dimension=Dimension.CONSISTENCY, severity=Severity.MEDIUM,
        table="claims_header", column="denial_reason_code",
        description="Denied claims must carry a denial reason; others must not.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE (status = 'Denied' AND (denial_reason_code IS NULL OR denial_reason_code = '')) "
                    "OR (status <> 'Denied' AND denial_reason_code <> '' AND denial_reason_code IS NOT NULL)",
    ),
    # ------------------------------ UNIQUENESS ----------------------------- #
    Rule(
        id="U-HDR-CLAIMID", name="Claim id is unique",
        dimension=Dimension.UNIQUENESS, severity=Severity.CRITICAL,
        table="claims_header", column="claim_id",
        description="The claim primary key must be unique.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "GROUP BY claim_id HAVING count(*) > 1",
    ),
    Rule(
        id="U-LINE-ID", name="Claim line id is unique",
        dimension=Dimension.UNIQUENESS, severity=Severity.CRITICAL,
        table="claims_lines", column="claim_line_id",
        description="The claim-line primary key must be unique.",
        failing_sql="SELECT claim_line_id AS record_key FROM \"{s}\".claims_lines "
                    "GROUP BY claim_line_id HAVING count(*) > 1",
    ),
    Rule(
        id="U-MBR-ID", name="Member id is unique",
        dimension=Dimension.UNIQUENESS, severity=Severity.CRITICAL,
        table="members", column="member_id",
        description="The member primary key must be unique.",
        failing_sql="SELECT member_id AS record_key FROM \"{s}\".members "
                    "GROUP BY member_id HAVING count(*) > 1",
    ),
    Rule(
        id="U-PRV-ID", name="Provider id is unique",
        dimension=Dimension.UNIQUENESS, severity=Severity.CRITICAL,
        table="providers", column="provider_id",
        description="The provider primary key must be unique.",
        failing_sql="SELECT provider_id AS record_key FROM \"{s}\".providers "
                    "GROUP BY provider_id HAVING count(*) > 1",
    ),
    Rule(
        id="U-HDR-BIZDUP", name="No duplicate business claims",
        dimension=Dimension.UNIQUENESS, severity=Severity.HIGH,
        table="claims_header", column=None,
        description="Same member/provider/admission/amount should not recur (duplicate submission).",
        failing_sql="SELECT record_key FROM ("
                    "  SELECT claim_id AS record_key, row_number() OVER ("
                    "    PARTITION BY member_id, provider_id, admission_date, billed_amount_pkr "
                    "    ORDER BY claim_id) AS rn "
                    "  FROM \"{s}\".claims_header) d WHERE rn > 1",
    ),
    # ------------------------------- ACCURACY ------------------------------ #
    Rule(
        id="A-HDR-APPR-BILLED", name="Approved not greater than billed",
        dimension=Dimension.ACCURACY, severity=Severity.HIGH,
        table="claims_header", column="approved_amount_pkr",
        description="Approved amount cannot exceed the billed amount.",
        failing_sql=f"SELECT claim_id AS record_key FROM \"{{s}}\".claims_header "
                    f"WHERE {_num('approved_amount_pkr')} > {_num('billed_amount_pkr')}",
    ),
    Rule(
        id="A-HDR-PAID-APPR", name="Paid not greater than approved",
        dimension=Dimension.ACCURACY, severity=Severity.HIGH,
        table="claims_header", column="paid_amount_pkr",
        description="Paid amount cannot exceed the approved amount.",
        failing_sql=f"SELECT claim_id AS record_key FROM \"{{s}}\".claims_header "
                    f"WHERE {_num('paid_amount_pkr')} > {_num('approved_amount_pkr')}",
    ),
    Rule(
        id="A-HDR-NONNEG", name="Billed amount is positive",
        dimension=Dimension.ACCURACY, severity=Severity.HIGH,
        table="claims_header", column="billed_amount_pkr",
        description="Billed amount must be strictly positive (no zero/negative).",
        failing_sql=f"SELECT claim_id AS record_key FROM \"{{s}}\".claims_header "
                    f"WHERE {_num('billed_amount_pkr')} <= 0",
    ),
    Rule(
        id="A-LINE-MATH", name="Line billed equals price x quantity",
        dimension=Dimension.ACCURACY, severity=Severity.LOW,
        table="claims_lines", column="line_billed_pkr",
        description="Line billed should equal unit price times quantity (± rounding).",
        failing_sql=f"SELECT claim_line_id AS record_key FROM \"{{s}}\".claims_lines "
                    f"WHERE abs({_num('line_billed_pkr')} - {_num('unit_price_pkr')} * "
                    f"{_num('quantity')}) > 1.0",
    ),
    # ------------------------------ TIMELINESS ----------------------------- #
    Rule(
        id="T-HDR-ADJ-LAG", name="Adjudication within SLA",
        dimension=Dimension.TIMELINESS, severity=Severity.LOW,
        table="claims_header", column="adjudication_date",
        description="Claims should be adjudicated within 60 days of submission.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE adjudication_date <> '' AND submission_date <> '' "
                    "AND (cs_parse_date(adjudication_date) - cs_parse_date(submission_date)) > 60",
    ),
    Rule(
        id="T-HDR-PAYMENT", name="Payment after adjudication",
        dimension=Dimension.TIMELINESS, severity=Severity.MEDIUM,
        table="claims_header", column="payment_date",
        description="Payment cannot precede adjudication.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE payment_date <> '' AND adjudication_date <> '' "
                    "AND cs_parse_date(payment_date) < cs_parse_date(adjudication_date)",
    ),
    Rule(
        id="T-HDR-SUBMIT-LAG", name="Submission within filing limit",
        dimension=Dimension.TIMELINESS, severity=Severity.LOW,
        table="claims_header", column="submission_date",
        description="Claims should be submitted within 30 days of discharge.",
        failing_sql="SELECT claim_id AS record_key FROM \"{s}\".claims_header "
                    "WHERE submission_date <> '' AND discharge_date <> '' "
                    "AND (cs_parse_date(submission_date) - cs_parse_date(discharge_date)) > 30",
    ),
    # --------------------------- REFERENTIAL (validity) -------------------- #
    Rule(
        id="R-HDR-MEMBER-FK", name="Claim member exists",
        dimension=Dimension.VALIDITY, severity=Severity.HIGH,
        table="claims_header", column="member_id",
        description="Every claim's member_id must exist in the members table.",
        failing_sql="SELECT h.claim_id AS record_key FROM \"{s}\".claims_header h "
                    "LEFT JOIN \"{s}\".members m ON h.member_id = m.member_id "
                    "WHERE m.member_id IS NULL",
    ),
    Rule(
        id="R-HDR-PROVIDER-FK", name="Claim provider exists",
        dimension=Dimension.VALIDITY, severity=Severity.HIGH,
        table="claims_header", column="provider_id",
        description="Every claim's provider_id must exist in the providers table.",
        failing_sql="SELECT h.claim_id AS record_key FROM \"{s}\".claims_header h "
                    "LEFT JOIN \"{s}\".providers p ON h.provider_id = p.provider_id "
                    "WHERE p.provider_id IS NULL",
    ),
    Rule(
        id="R-LINE-CLAIM-FK", name="Claim line parent exists",
        dimension=Dimension.VALIDITY, severity=Severity.HIGH,
        table="claims_lines", column="claim_id",
        description="Every claim line's claim_id must exist in claims_header.",
        failing_sql="SELECT l.claim_line_id AS record_key FROM \"{s}\".claims_lines l "
                    "LEFT JOIN \"{s}\".claims_header h ON l.claim_id = h.claim_id "
                    "WHERE h.claim_id IS NULL",
    ),
]


def rules_by_dimension() -> dict[Dimension, list[Rule]]:
    out: dict[Dimension, list[Rule]] = {d: [] for d in Dimension}
    for r in RULES:
        out[r.dimension].append(r)
    return out
