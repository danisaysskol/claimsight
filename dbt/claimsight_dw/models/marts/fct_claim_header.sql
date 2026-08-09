-- Claim-grain fact: one row per adjudicated claim, with turnaround-time
-- measures and surrogate keys to the conformed dimensions.
with claims as (
    select * from {{ ref('int_claims_cleaned') }}
),
-- One version per member/provider in the current snapshot, so join on the
-- natural key (no is_current filter) to keep terminated members' claims keyed.
mbr as (
    select member_id, member_sk, employer_group_id, policy_id
    from {{ ref('dim_member') }}
),
prv as (
    select provider_id, provider_sk from {{ ref('dim_provider') }}
),
grp as (select group_id, employer_group_sk from {{ ref('dim_employer_group') }}),
pol as (select policy_id, policy_sk from {{ ref('dim_policy') }})

select
    {{ surrogate_key(['c.claim_id']) }}                      as claim_sk,
    c.claim_id,
    mbr.member_sk,
    prv.provider_sk,
    grp.employer_group_sk,
    pol.policy_sk,
    c.claim_type,
    c.status,
    c.adjudication_mode,
    c.denial_reason_code,
    cast(to_char(c.admission_date, 'YYYYMMDD') as int)      as admission_date_key,
    cast(to_char(c.discharge_date, 'YYYYMMDD') as int)      as discharge_date_key,
    cast(to_char(c.submission_date, 'YYYYMMDD') as int)     as submission_date_key,
    case when c.adjudication_date is not null
         then cast(to_char(c.adjudication_date, 'YYYYMMDD') as int) end as adjudication_date_key,
    case when c.payment_date is not null
         then cast(to_char(c.payment_date, 'YYYYMMDD') as int) end      as payment_date_key,
    -- measures
    c.billed_amount_pkr,
    c.approved_amount_pkr,
    c.paid_amount_pkr,
    c.member_share_pkr,
    (c.billed_amount_pkr - c.approved_amount_pkr)           as savings_pkr,
    c.length_of_stay,
    c.days_submit_to_adjudicate                             as tat_submit_to_adjudicate,
    c.days_adjudicate_to_pay                                as tat_adjudicate_to_pay,
    (c.days_submit_to_adjudicate + coalesce(c.days_adjudicate_to_pay, 0)) as tat_total,
    1                                                       as claim_count
from claims c
left join mbr on c.member_id = mbr.member_id
left join prv on c.provider_id = prv.provider_id
left join grp on mbr.employer_group_id = grp.group_id
left join pol on c.policy_id = pol.policy_id
