-- The cleaning core. Removes every injected defect class so the marts are
-- trustworthy:
--   * de-duplicates business duplicates (keep first per natural signature)
--   * drops orphan member / provider foreign keys
--   * drops non-positive, and internally-inconsistent (approved>billed,
--     paid>approved) amounts
--   * drops date violations (discharge before admission)
--   * drops rows missing adjudication mode (completeness defect)
with deduped as (
    select
        *,
        row_number() over (
            partition by member_id, provider_id, admission_date, billed_amount_pkr
            order by claim_id
        ) as _dup_rn
    from {{ ref('stg_claims_header') }}
),
valid_members as (select member_id from {{ ref('int_members_cleaned') }}),
valid_providers as (select provider_id from {{ ref('stg_providers') }})

select
    claim_id,
    member_id,
    provider_id,
    policy_id,
    claim_type,
    admission_date,
    discharge_date,
    submission_date,
    adjudication_date,
    payment_date,
    status,
    denial_reason_code,
    billed_amount_pkr,
    approved_amount_pkr,
    paid_amount_pkr,
    member_share_pkr,
    adjudication_mode,
    -- turnaround-time measures (in days)
    (submission_date - discharge_date)      as days_discharge_to_submit,
    (adjudication_date - submission_date)    as days_submit_to_adjudicate,
    (payment_date - adjudication_date)       as days_adjudicate_to_pay,
    (discharge_date - admission_date)        as length_of_stay
from deduped
where _dup_rn = 1
  and member_id in (select member_id from valid_members)
  and provider_id in (select provider_id from valid_providers)
  and adjudication_mode is not null
  and billed_amount_pkr > 0
  and approved_amount_pkr >= 0
  and paid_amount_pkr >= 0
  and approved_amount_pkr <= billed_amount_pkr
  and paid_amount_pkr <= approved_amount_pkr
  and discharge_date >= admission_date
