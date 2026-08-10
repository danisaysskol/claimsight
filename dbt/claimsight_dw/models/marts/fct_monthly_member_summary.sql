-- Member x month grain: feeds PMPM and per-member utilisation metrics.
{{ config(post_hook=[
    "create index if not exists ix_fmms_member_sk on {{ this }} (member_sk)",
    "create index if not exists ix_fmms_month_key on {{ this }} (month_key)"
]) }}
with claims as (
    select
        c.member_id,
        date_trunc('month', c.submission_date)::date as month_start,
        c.billed_amount_pkr,
        c.approved_amount_pkr,
        c.paid_amount_pkr,
        c.member_share_pkr
    from {{ ref('int_claims_cleaned') }} c
    where c.submission_date is not null
),
mbr as (
    select member_id, member_sk, employer_group_id, policy_id
    from {{ ref('dim_member') }}
)
select
    {{ surrogate_key(['claims.member_id', 'claims.month_start']) }} as member_month_sk,
    mbr.member_sk,
    claims.member_id,
    mbr.employer_group_id,
    mbr.policy_id,
    claims.month_start,
    cast(to_char(claims.month_start, 'YYYYMMDD') as int) as month_key,
    count(*)                            as claim_count,
    sum(claims.billed_amount_pkr)       as billed_amount_pkr,
    sum(claims.approved_amount_pkr)     as approved_amount_pkr,
    sum(claims.paid_amount_pkr)         as paid_amount_pkr,
    sum(claims.member_share_pkr)        as member_share_pkr
from claims
inner join mbr on claims.member_id = mbr.member_id
group by 2, 3, 4, 5, 6, 7
