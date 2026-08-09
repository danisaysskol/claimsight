"""Tests for the synthetic data generator, asserting against the defect manifest."""

from __future__ import annotations

import pandas as pd

from claimsight.generate.generate import (
    N_EMPLOYER_GROUPS,
    N_MEMBERS,
    N_POLICIES,
    N_PROVIDERS,
    generate,
)

EXPECTED_TABLES = {
    "employer_groups", "policies", "providers", "members",
    "diagnoses", "procedures", "claims_header", "claims_lines",
}
DEFECT_KEYS = {
    "duplicate_claims", "null_values", "orphan_fk_member", "orphan_fk_provider",
    "date_violations", "amount_violations", "nonpositive_amounts",
    "impossible_ages", "city_casing_variants", "mixed_date_format_values",
}


def test_tables_present(small_dataset):
    assert set(small_dataset.tables) == EXPECTED_TABLES


def test_dimension_row_counts(small_dataset):
    t = small_dataset.tables
    # dims are fixed-size; claims_header includes injected duplicates.
    assert len(t["members"]) == N_MEMBERS
    assert len(t["providers"]) == N_PROVIDERS
    assert len(t["employer_groups"]) == N_EMPLOYER_GROUPS
    assert len(t["policies"]) == N_POLICIES


def test_line_target_met(small_dataset):
    assert len(small_dataset.tables["claims_lines"]) >= 3000


def test_manifest_has_all_defect_classes(small_dataset):
    defects = small_dataset.manifest["injected_defects"]
    assert DEFECT_KEYS.issubset(defects)
    for key in DEFECT_KEYS:
        assert defects[key] > 0, f"expected some {key}"


def test_duplicates_actually_injected(small_dataset):
    headers = small_dataset.tables["claims_header"]
    n_dup = small_dataset.manifest["injected_defects"]["duplicate_claims"]
    dup_rows = headers["claim_id"].astype(str).str.startswith("CLMDUP").sum()
    assert dup_rows == n_dup


def test_orphan_fks_present(small_dataset):
    headers = small_dataset.tables["claims_header"]
    assert (headers["member_id"] == "MB999999").sum() >= 1
    assert (headers["provider_id"] == "PR9999").sum() >= 1


def test_nonpositive_amounts_present(small_dataset):
    headers = small_dataset.tables["claims_header"]
    billed = pd.to_numeric(headers["billed_amount_pkr"], errors="coerce")
    assert (billed <= 0).sum() >= 1


def test_mixed_date_formats_present(small_dataset):
    members = small_dataset.tables["members"]
    # Some enrolment dates should be in DD-MM-YYYY (contain a non-ISO layout).
    ddmm = members["enrolment_date"].astype(str).str.match(r"^\d{2}-\d{2}-\d{4}$")
    iso = members["enrolment_date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}")
    assert ddmm.sum() > 0 and iso.sum() > 0


def test_reproducible_with_same_seed():
    a = generate(seed=999, target_lines=1500)
    b = generate(seed=999, target_lines=1500)
    assert a.manifest["injected_defects"] == b.manifest["injected_defects"]
    assert a.manifest["row_counts"] == b.manifest["row_counts"]
    # Content identical too.
    pd.testing.assert_frame_equal(a.tables["claims_header"], b.tables["claims_header"])


def test_masked_cnic_is_masked(small_dataset):
    members = small_dataset.tables["members"]
    # No CNIC should look like a full 13-digit real identifier.
    assert members["masked_cnic"].str.contains(r"\*").all()
