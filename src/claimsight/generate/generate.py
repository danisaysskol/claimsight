"""Synthetic ClaimSight dataset generator.

Produces a deliberately imperfect, but *signal-rich*, TPA claims dataset in
Pakistani context and writes CSVs to ``data/raw/`` plus a JSON manifest that
records exactly how many defects of each class were injected. The data-quality
engine (Phase 3) and the test-suite (Phase 9) assert against that manifest.

Design:
  1. Generate clean, internally-consistent entities.
  2. Inject a measured number of defects of each class.
  3. Write CSVs + manifest.

Everything is driven by a fixed seed so the dataset is fully reproducible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from claimsight.config import RAW_DATA_DIR, get_settings
from claimsight.generate import reference as ref

# --- Simulation window (fixed for reproducibility; ~24 months) ---
WINDOW_START = date(2024, 7, 1)
WINDOW_END = date(2026, 6, 30)
# A fixed "as of" timestamp so the manifest is reproducible (no wall-clock).
GENERATED_AT = "2026-06-30T00:00:00"

# Scale parameters.
N_MEMBERS = 12_000
N_PROVIDERS = 300
N_EMPLOYER_GROUPS = 40
N_POLICIES = 60
N_ANOMALOUS_PROVIDERS = 5
HEAVY_UTILISER_FRACTION = 0.05

# Defect rates (fraction of claims, unless noted). Recorded in the manifest.
RATE_DUPLICATE = 0.020
RATE_NULLS = 0.015
RATE_ORPHAN_FK = 0.005
RATE_DATE_VIOLATION = 0.008
RATE_AMOUNT_VIOLATION = 0.006
RATE_NONPOSITIVE = 0.003
RATE_IMPOSSIBLE_AGE = 0.004  # fraction of members


@dataclass
class GenerationResult:
    """Container for generated tables plus the defect manifest."""

    tables: dict[str, pd.DataFrame]
    manifest: dict = field(default_factory=dict)


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _random_dates(rng: np.random.Generator, start: date, end: date, n: int) -> list[date]:
    span = (end - start).days
    offsets = rng.integers(0, span + 1, size=n)
    return [start + timedelta(days=int(o)) for o in offsets]


def _masked_cnic(rng: np.random.Generator) -> str:
    """Return a masked, obviously-fake CNIC-style identifier.

    Real CNIC is 5-7-1 digits. We keep the region prefix and check digit but
    mask the personal middle section so no value resembles a real CNIC.
    """
    region = int(rng.integers(10_000, 99_999))
    check = int(rng.integers(0, 10))
    return f"{region}-*******-{check}"


# --------------------------------------------------------------------------- #
# Entity generators
# --------------------------------------------------------------------------- #
def gen_employer_groups(rng: np.random.Generator, fake: Faker) -> pd.DataFrame:
    rows = []
    for i in range(1, N_EMPLOYER_GROUPS + 1):
        prefix = ref.EMPLOYER_PREFIXES[int(rng.integers(0, len(ref.EMPLOYER_PREFIXES)))]
        suffix = ref.EMPLOYER_SUFFIXES[int(rng.integers(0, len(ref.EMPLOYER_SUFFIXES)))]
        city = ref.CITIES[int(rng.choice(len(ref.CITIES), p=ref.CITY_WEIGHTS))]
        lives = int(rng.integers(120, 5_000))
        contract_start = WINDOW_START - timedelta(days=int(rng.integers(0, 365)))
        rows.append(
            {
                "group_id": f"EG{i:04d}",
                "name": f"{prefix} {suffix}",
                "industry": ref.INDUSTRIES[int(rng.integers(0, len(ref.INDUSTRIES)))],
                "city": city,
                "contract_start": contract_start.isoformat(),
                "contract_end": (contract_start + timedelta(days=365 * 3)).isoformat(),
                "lives_covered": lives,
                # Premium scales with lives; ~PKR 1,800-3,500 per life per month.
                "monthly_premium_pkr": int(lives * rng.integers(1_800, 3_500)),
            }
        )
    return pd.DataFrame(rows)


def gen_policies(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(1, N_POLICIES + 1):
        tier = ref.PLAN_TIERS[int(rng.integers(0, len(ref.PLAN_TIERS)))]
        p = ref.PLAN_TIER_PARAMS[tier]
        rows.append(
            {
                "policy_id": f"POL{i:04d}",
                "plan_name": f"{tier} Care {i:02d}",
                "plan_tier": tier,
                "annual_limit_pkr": int(p["annual_limit"]),
                "room_rent_cap_pkr": int(p["room_rent_cap"]),
                "deductible_pkr": int(p["deductible"]),
                "copay_pct": float(p["copay_pct"]),
                "maternity_covered": bool(tier in ("Silver", "Gold", "Platinum")),
                "pre_existing_waiting_months": int({"Bronze": 12, "Silver": 9, "Gold": 6, "Platinum": 3}[tier]),
            }
        )
    return pd.DataFrame(rows)


def gen_providers(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    anomalous_ids = set(
        f"PR{int(x):04d}" for x in rng.choice(range(1, N_PROVIDERS + 1), size=N_ANOMALOUS_PROVIDERS, replace=False)
    )
    for i in range(1, N_PROVIDERS + 1):
        pid = f"PR{i:04d}"
        ptype = ref.PROVIDER_TYPES[int(rng.choice(len(ref.PROVIDER_TYPES), p=ref.PROVIDER_TYPE_WEIGHTS))]
        prefix = ref.HOSPITAL_PREFIXES[int(rng.integers(0, len(ref.HOSPITAL_PREFIXES)))]
        city = ref.CITIES[int(rng.choice(len(ref.CITIES), p=ref.CITY_WEIGHTS))]
        network = "In-Network" if rng.random() < 0.72 else "Out-of-Network"
        panel_since = WINDOW_START - timedelta(days=int(rng.integers(0, 365 * 5)))
        rows.append(
            {
                "provider_id": pid,
                "hospital_name": f"{prefix} {ptype if ptype != 'Hospital' else 'Hospital'}",
                "city": city,
                "provider_type": ptype,
                "network_status": network,
                "tier": ref.PROVIDER_TIERS[int(rng.integers(0, len(ref.PROVIDER_TIERS)))],
                "panel_since": panel_since.isoformat(),
                # Not persisted to CSV as a column the DQ engine checks, but used
                # downstream to drive anomalous billing.
                "_is_anomalous": pid in anomalous_ids,
            }
        )
    return pd.DataFrame(rows)


def gen_members(rng: np.random.Generator, fake: Faker, employer_groups: pd.DataFrame, policies: pd.DataFrame) -> pd.DataFrame:
    group_ids = employer_groups["group_id"].to_numpy()
    policy_ids = policies["policy_id"].to_numpy()
    rows = []
    for i in range(1, N_MEMBERS + 1):
        relationship = ref.RELATIONSHIPS[int(rng.choice(len(ref.RELATIONSHIPS), p=ref.RELATIONSHIP_WEIGHTS))]
        if relationship == "Child":
            age = int(rng.integers(0, 26))
        elif relationship == "Spouse":
            age = int(rng.integers(20, 70))
        else:
            age = int(rng.integers(18, 66))
        dob = WINDOW_END - timedelta(days=age * 365 + int(rng.integers(0, 365)))
        gender = ref.GENDERS[int(rng.integers(0, 2))]
        enrol = WINDOW_START - timedelta(days=int(rng.integers(0, 365 * 2)))
        # ~4% of members terminate during the window.
        terminated = rng.random() < 0.04
        term_date = (enrol + timedelta(days=int(rng.integers(200, 800)))) if terminated else None
        rows.append(
            {
                "member_id": f"MB{i:06d}",
                "masked_cnic": _masked_cnic(rng),
                "name": fake.name_male() if gender == "Male" else fake.name_female(),
                "gender": gender,
                "date_of_birth": dob.isoformat(),
                "city": ref.CITIES[int(rng.choice(len(ref.CITIES), p=ref.CITY_WEIGHTS))],
                "employer_group_id": str(rng.choice(group_ids)),
                "policy_id": str(rng.choice(policy_ids)),
                "enrolment_date": enrol.isoformat(),
                "termination_date": term_date.isoformat() if term_date else "",
                "relationship": relationship,
            }
        )
    return pd.DataFrame(rows)


def gen_diagnoses() -> pd.DataFrame:
    return pd.DataFrame(
        [{"diagnosis_code": c, "description": d, "chapter": ch} for c, d, ch in ref.DIAGNOSES]
    )


def gen_procedures() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"procedure_code": c, "description": d, "category": cat, "typical_cost_pkr": cost}
            for c, d, cat, cost in ref.PROCEDURES
        ]
    )


# --------------------------------------------------------------------------- #
# Claims (the heart of the signal)
# --------------------------------------------------------------------------- #
def _month_volume_weight(d: date) -> float:
    """Higher volume near the policy year end (June) — end-of-year utilisation."""
    # Peaks in May/June, trough just after (July/August).
    month = d.month
    return {7: 0.7, 8: 0.75, 9: 0.85, 10: 0.95, 11: 1.0, 12: 1.1,
            1: 1.15, 2: 1.05, 3: 1.0, 4: 1.05, 5: 1.2, 6: 1.35}[month]


def _pick_claim_type(rng: np.random.Generator) -> str:
    return ref.CLAIM_TYPES[int(rng.choice(len(ref.CLAIM_TYPES), p=ref.CLAIM_TYPE_WEIGHTS))]


def gen_claims(
    rng: np.random.Generator,
    members: pd.DataFrame,
    providers: pd.DataFrame,
    policies: pd.DataFrame,
    diagnoses: pd.DataFrame,
    procedures: pd.DataFrame,
    target_lines: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate claim headers and lines with realistic embedded signal."""
    policy_by_id = policies.set_index("policy_id").to_dict("index")
    member_records = members.to_dict("records")
    provider_records = providers.to_dict("records")

    # Heavy utilisers: 5% of members get a much higher claim propensity.
    n_heavy = int(len(member_records) * HEAVY_UTILISER_FRACTION)
    heavy_idx = set(rng.choice(len(member_records), size=n_heavy, replace=False).tolist())

    # Procedure lookup by category.
    proc_by_cat: dict[str, list[dict]] = {}
    for _, prow in procedures.iterrows():
        proc_by_cat.setdefault(prow["category"], []).append(prow.to_dict())
    diag_by_chapter: dict[str, list[dict]] = {}
    for _, drow in diagnoses.iterrows():
        diag_by_chapter.setdefault(drow["chapter"], []).append(drow.to_dict())

    headers: list[dict] = []
    lines: list[dict] = []
    claim_seq = 0
    line_seq = 0

    while line_seq < target_lines:
        midx = int(rng.integers(0, len(member_records)))
        member = member_records[midx]
        # Heavy utilisers submit more claims: bias re-selection by continuing.
        propensity = 4 if midx in heavy_idx else 1
        n_claims_for_member = int(rng.integers(1, propensity + 1))

        for _ in range(n_claims_for_member):
            if line_seq >= target_lines:
                break
            claim_seq += 1
            claim_id = f"CLM{claim_seq:07d}"
            provider = provider_records[int(rng.integers(0, len(provider_records)))]
            claim_type = _pick_claim_type(rng)

            # Maternity only for female members of childbearing age.
            if claim_type == "Maternity" and member["gender"] != "Female":
                claim_type = "Outpatient"

            # --- Dates with seasonality ---
            # Rejection sampling weighted by month volume.
            for _try in range(5):
                adm = _random_dates(rng, WINDOW_START, WINDOW_END, 1)[0]
                if rng.random() <= _month_volume_weight(adm) / 1.35:
                    break
            if claim_type in ("Inpatient", "Maternity", "Emergency"):
                los = int(rng.integers(1, 12))
            elif claim_type == "Daycare":
                los = 0
            else:
                los = 0
            discharge = adm + timedelta(days=los)
            submission = discharge + timedelta(days=int(rng.integers(1, 20)))
            adjudication_mode = "Auto" if rng.random() < 0.55 else "Manual"
            # Manual adjudication is far slower.
            adj_lag = int(rng.integers(1, 5)) if adjudication_mode == "Auto" else int(rng.integers(7, 40))
            adjudication = submission + timedelta(days=adj_lag)

            # --- Diagnosis & procedures for this claim ---
            chapters = ref.CLAIM_TYPE_TO_DIAG_CHAPTERS[claim_type]
            # Winter respiratory boost.
            if adm.month in (12, 1, 2) and "Respiratory" not in chapters and rng.random() < 0.25:
                chapter = "Respiratory"
            else:
                chapter = chapters[int(rng.integers(0, len(chapters)))]
            diag_pool = diag_by_chapter.get(chapter) or diag_by_chapter[next(iter(diag_by_chapter))]
            diag = diag_pool[int(rng.integers(0, len(diag_pool)))]

            categories = ref.CLAIM_TYPE_TO_PROC_CATEGORIES[claim_type]
            n_lines = 1
            if claim_type in ("Inpatient", "Maternity"):
                n_lines = int(rng.integers(2, 6))
            elif claim_type in ("Emergency", "Diagnostic"):
                n_lines = int(rng.integers(1, 4))
            # Anomalous providers bill many more lines.
            if provider.get("_is_anomalous") and rng.random() < 0.6:
                n_lines += int(rng.integers(3, 8))

            # Out-of-network cost multiplier + anomalous provider inflation.
            oon_mult = 1.6 if provider["network_status"] == "Out-of-Network" else 1.0
            anom_mult = float(rng.uniform(1.8, 3.0)) if provider.get("_is_anomalous") else 1.0

            claim_billed = 0
            claim_lines_buf = []
            for ln in range(1, n_lines + 1):
                cat = categories[int(rng.integers(0, len(categories)))]
                proc_pool = proc_by_cat.get(cat) or proc_by_cat[next(iter(proc_by_cat))]
                proc = proc_pool[int(rng.integers(0, len(proc_pool)))]
                qty = int(rng.integers(1, 3))
                unit = float(proc["typical_cost_pkr"]) * float(rng.uniform(0.85, 1.4)) * oon_mult * anom_mult
                line_billed = round(unit * qty, 2)
                claim_billed += line_billed
                line_seq += 1
                claim_lines_buf.append(
                    {
                        "claim_line_id": f"CL{line_seq:08d}",
                        "claim_id": claim_id,
                        "line_no": ln,
                        "procedure_code": proc["procedure_code"],
                        "diagnosis_code": diag["diagnosis_code"],
                        "quantity": qty,
                        "unit_price_pkr": round(unit, 2),
                        "line_billed_pkr": line_billed,
                        # line_approved filled once we know approval share.
                    }
                )

            # --- Adjudication outcome ---
            policy = policy_by_id[member["policy_id"]]
            tier = policy["plan_tier"]
            approval_base = ref.PLAN_TIER_APPROVAL_BASE[tier]
            denial_base = ref.CLAIM_TYPE_DENIAL_BASE[claim_type]
            # Providers vary; anomalous + OON denied a bit more.
            denial_prob = denial_base
            if provider["network_status"] == "Out-of-Network":
                denial_prob += 0.06
            if provider.get("_is_anomalous"):
                denial_prob += 0.05

            roll = rng.random()
            if roll < denial_prob:
                status = "Denied"
            elif roll < denial_prob + 0.05:
                status = "Pending"
            elif roll < denial_prob + 0.09:
                status = "In Review"
            elif roll < denial_prob + 0.20:
                status = "Partially Paid"
            else:
                status = "Paid"

            copay = float(policy["copay_pct"])
            deductible = float(policy["deductible_pkr"])

            if status == "Denied":
                approved = 0.0
                paid = 0.0
                member_share = 0.0
                denial_code = list(ref.DENIAL_REASON_CODES)[int(rng.integers(0, len(ref.DENIAL_REASON_CODES)))]
                payment_date = ""
            else:
                share = approval_base * float(rng.uniform(0.9, 1.05))
                if status == "Partially Paid":
                    share *= float(rng.uniform(0.5, 0.8))
                share = min(share, 1.0)
                approved = round(claim_billed * share, 2)
                member_share = round(min(approved, deductible + approved * copay), 2)
                paid = round(approved - member_share, 2)
                denial_code = ""
                if status in ("Pending", "In Review"):
                    payment_date = ""
                    approved = approved if status == "In Review" else 0.0
                    paid = 0.0
                    member_share = 0.0 if status == "Pending" else member_share
                else:
                    payment_date = (adjudication + timedelta(days=int(rng.integers(1, 30)))).isoformat()

            # Distribute approved across lines proportionally.
            approved_share_of_billed = (approved / claim_billed) if claim_billed > 0 else 0.0
            for lb in claim_lines_buf:
                lb["line_approved_pkr"] = round(lb["line_billed_pkr"] * approved_share_of_billed, 2)
                lines.append(lb)

            headers.append(
                {
                    "claim_id": claim_id,
                    "member_id": member["member_id"],
                    "provider_id": provider["provider_id"],
                    "policy_id": member["policy_id"],
                    "claim_type": claim_type,
                    "admission_date": adm.isoformat(),
                    "discharge_date": discharge.isoformat(),
                    "submission_date": submission.isoformat(),
                    "adjudication_date": adjudication.isoformat() if status not in ("Pending",) else "",
                    "payment_date": payment_date,
                    "status": status,
                    "denial_reason_code": denial_code,
                    "billed_amount_pkr": round(claim_billed, 2),
                    "approved_amount_pkr": round(approved, 2),
                    "paid_amount_pkr": round(paid, 2),
                    "member_share_pkr": round(member_share, 2),
                    "adjudication_mode": adjudication_mode,
                }
            )

    return pd.DataFrame(headers), pd.DataFrame(lines)


# --------------------------------------------------------------------------- #
# Defect injection
# --------------------------------------------------------------------------- #
def inject_defects(
    rng: np.random.Generator,
    tables: dict[str, pd.DataFrame],
) -> dict[str, int]:
    """Mutate tables in place to plant measured defects. Returns counts."""
    manifest: dict[str, int] = {}
    headers = tables["claims_header"]
    members = tables["members"]
    providers = tables["providers"]
    groups = tables["employer_groups"]

    n_claims = len(headers)

    # 1) Duplicate claim rows: same member/provider/date/amount, new claim_id.
    n_dup = int(n_claims * RATE_DUPLICATE)
    dup_src = headers.sample(n=n_dup, random_state=int(rng.integers(0, 1_000_000)))
    dups = dup_src.copy()
    dups["claim_id"] = [f"CLMDUP{i:06d}" for i in range(n_dup)]
    tables["claims_header"] = pd.concat([headers, dups], ignore_index=True)
    headers = tables["claims_header"]
    manifest["duplicate_claims"] = n_dup

    # 2) Null values in a non-critical but always-populated column.
    #    Concentrated in adjudication_mode so the completeness rule catches an
    #    exact, assertable count (denial_reason_code / payment_date are
    #    legitimately empty on many rows and would be ambiguous).
    n_null = int(len(headers) * RATE_NULLS)
    idx = rng.choice(len(headers), size=n_null, replace=False)
    col = headers.columns.get_loc("adjudication_mode")
    for i in idx:
        headers.iat[int(i), col] = np.nan
    manifest["null_values"] = n_null

    # 3) Orphan foreign keys (member / provider references that do not exist).
    n_orphan = int(len(headers) * RATE_ORPHAN_FK)
    idx = rng.choice(len(headers), size=n_orphan, replace=False)
    half = n_orphan // 2
    for j, i in enumerate(idx):
        if j < half:
            headers.iat[int(i), headers.columns.get_loc("member_id")] = "MB999999"
        else:
            headers.iat[int(i), headers.columns.get_loc("provider_id")] = "PR9999"
    manifest["orphan_fk_member"] = half
    manifest["orphan_fk_provider"] = n_orphan - half

    # 4) Date violations: discharge before admission OR submission before discharge.
    n_date = int(len(headers) * RATE_DATE_VIOLATION)
    idx = rng.choice(len(headers), size=n_date, replace=False)
    for i in idx:
        adm = pd.to_datetime(headers.iat[int(i), headers.columns.get_loc("admission_date")])
        bad_discharge = (adm - timedelta(days=int(rng.integers(1, 5)))).date().isoformat()
        headers.iat[int(i), headers.columns.get_loc("discharge_date")] = bad_discharge
    manifest["date_violations"] = n_date

    # 5) Amount violations: paid > approved OR approved > billed.
    n_amt = int(len(headers) * RATE_AMOUNT_VIOLATION)
    idx = rng.choice(len(headers), size=n_amt, replace=False)
    for i in idx:
        billed = float(headers.iat[int(i), headers.columns.get_loc("billed_amount_pkr")] or 0)
        headers.iat[int(i), headers.columns.get_loc("approved_amount_pkr")] = round(billed * 1.2, 2)
        headers.iat[int(i), headers.columns.get_loc("paid_amount_pkr")] = round(billed * 1.3, 2)
    manifest["amount_violations"] = n_amt

    # 6) Negative or zero amounts.
    n_neg = int(len(headers) * RATE_NONPOSITIVE)
    idx = rng.choice(len(headers), size=n_neg, replace=False)
    for i in idx:
        headers.iat[int(i), headers.columns.get_loc("billed_amount_pkr")] = round(
            -abs(float(rng.uniform(1, 5000))), 2
        )
    manifest["nonpositive_amounts"] = n_neg

    # 7) Impossible ages: DOB in the future or age > 120.
    n_age = int(len(members) * RATE_IMPOSSIBLE_AGE)
    idx = rng.choice(len(members), size=n_age, replace=False)
    half = n_age // 2
    for j, i in enumerate(idx):
        if j < half:
            future = (WINDOW_END + timedelta(days=int(rng.integers(30, 500)))).isoformat()
            members.iat[int(i), members.columns.get_loc("date_of_birth")] = future
        else:
            ancient = (WINDOW_END - timedelta(days=125 * 365)).isoformat()
            members.iat[int(i), members.columns.get_loc("date_of_birth")] = ancient
    manifest["impossible_ages"] = n_age

    # 8) Inconsistent city casing / whitespace across member, provider, group.
    variants = {
        "Karachi": ["karachi ", "KARACHI", " Karachi", "karachi"],
        "Lahore": ["lahore", "LAHORE ", " lahore "],
        "Islamabad": ["islamabad ", "ISLAMABAD"],
    }
    casing_count = 0
    for tbl in (members, providers, groups):
        col = "city"
        cidx = rng.choice(len(tbl), size=max(1, int(len(tbl) * 0.05)), replace=False)
        for i in cidx:
            city = tbl.iat[int(i), tbl.columns.get_loc(col)]
            if city in variants:
                v = variants[city][int(rng.integers(0, len(variants[city])))]
                tbl.iat[int(i), tbl.columns.get_loc(col)] = v
                casing_count += 1
    manifest["city_casing_variants"] = casing_count

    # 9) Mixed date formats in two source CSVs:
    #    members.enrolment_date -> DD-MM-YYYY for ~50%
    #    claims_header.submission_date -> DD/MM/YYYY for ~50%
    def _to_ddmmyyyy(s: str, sep: str) -> str:
        try:
            d = datetime.fromisoformat(s).date()
            return d.strftime(f"%d{sep}%m{sep}%Y")
        except (ValueError, TypeError):
            return s

    mixed = 0
    midx = rng.choice(len(members), size=len(members) // 2, replace=False)
    col = members.columns.get_loc("enrolment_date")
    for i in midx:
        members.iat[int(i), col] = _to_ddmmyyyy(str(members.iat[int(i), col]), "-")
        mixed += 1
    hidx = rng.choice(len(headers), size=len(headers) // 2, replace=False)
    col = headers.columns.get_loc("submission_date")
    for i in hidx:
        headers.iat[int(i), col] = _to_ddmmyyyy(str(headers.iat[int(i), col]), "/")
        mixed += 1
    manifest["mixed_date_format_values"] = mixed

    return manifest


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def generate(seed: int, target_lines: int) -> GenerationResult:
    """Generate the full dataset (clean entities + injected defects)."""
    rng = _rng(seed)
    fake = Faker("en_US")  # names only; context comes from our reference lists
    Faker.seed(seed)

    employer_groups = gen_employer_groups(rng, fake)
    policies = gen_policies(rng)
    providers = gen_providers(rng)
    members = gen_members(rng, fake, employer_groups, policies)
    diagnoses = gen_diagnoses()
    procedures = gen_procedures()
    claims_header, claims_lines = gen_claims(
        rng, members, providers, policies, diagnoses, procedures, target_lines
    )

    # Drop the internal helper column before persistence.
    providers_out = providers.drop(columns=["_is_anomalous"])

    tables: dict[str, pd.DataFrame] = {
        "employer_groups": employer_groups,
        "policies": policies,
        "providers": providers_out,
        "members": members,
        "diagnoses": diagnoses,
        "procedures": procedures,
        "claims_header": claims_header,
        "claims_lines": claims_lines,
    }

    defects = inject_defects(rng, tables)

    manifest = {
        "seed": seed,
        "generated_at": GENERATED_AT,
        "window_start": WINDOW_START.isoformat(),
        "window_end": WINDOW_END.isoformat(),
        "row_counts": {name: int(len(df)) for name, df in tables.items()},
        "injected_defects": defects,
        "anomalous_provider_count": N_ANOMALOUS_PROVIDERS,
    }
    return GenerationResult(tables=tables, manifest=manifest)


def write_outputs(result: GenerationResult, raw_dir: Path) -> None:
    """Write all tables to CSV plus the manifest JSON."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, df in result.tables.items():
        df.to_csv(raw_dir / f"{name}.csv", index=False)
    (raw_dir / "manifest.json").write_text(json.dumps(result.manifest, indent=2), encoding="utf-8")


def main() -> None:
    settings = get_settings()
    print(f"Generating synthetic dataset (seed={settings.claimsight_seed}, "
          f"target_lines={settings.claimsight_n_claim_lines}) ...")
    result = generate(settings.claimsight_seed, settings.claimsight_n_claim_lines)
    write_outputs(result, RAW_DATA_DIR)
    print("Row counts:")
    for name, n in result.manifest["row_counts"].items():
        print(f"  {name:20s} {n:>8,}")
    print("Injected defects:")
    for name, n in result.manifest["injected_defects"].items():
        print(f"  {name:26s} {n:>6,}")
    print(f"Wrote CSVs + manifest to {RAW_DATA_DIR}")


if __name__ == "__main__":
    main()
