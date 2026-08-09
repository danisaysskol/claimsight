-- Base analytical view: one row per claim, fully denormalised with dimension
-- attributes and the submission calendar date. Every other reporting view (and
-- the Streamlit / Power BI filters) builds on this.
create or replace view v_claims_enriched as
select
    f.claim_id,
    f.claim_sk,
    d.date_day                      as claim_date,
    d.year_month,
    d.month_number,
    d.month_name_short,
    d.calendar_year,
    d.fiscal_year,
    -- member
    m.member_id,
    m.gender,
    m.age_band,
    m.city                          as member_city,
    m.relationship,
    -- employer
    g.group_id                      as employer_group_id,
    g.employer_name,
    g.industry,
    g.monthly_premium_pkr,
    g.lives_covered,
    -- provider
    p.provider_id,
    p.hospital_name,
    p.city                          as provider_city,
    p.provider_type,
    p.network_status,
    p.tier                          as provider_tier,
    -- policy
    pol.plan_tier,
    -- claim descriptors
    f.claim_type,
    f.status,
    f.adjudication_mode,
    f.denial_reason_code,
    -- measures
    f.billed_amount_pkr,
    f.approved_amount_pkr,
    f.paid_amount_pkr,
    f.member_share_pkr,
    f.savings_pkr,
    f.length_of_stay,
    f.tat_submit_to_adjudicate,
    f.tat_adjudicate_to_pay,
    f.tat_total,
    (f.status = 'Denied')::int      as is_denied,
    (f.adjudication_mode = 'Auto')::int as is_auto
from marts.fct_claim_header f
left join marts.dim_member m         on f.member_sk = m.member_sk
left join marts.dim_provider p       on f.provider_sk = p.provider_sk
left join marts.dim_employer_group g on f.employer_group_sk = g.employer_group_sk
left join marts.dim_policy pol       on f.policy_sk = pol.policy_sk
left join marts.dim_date d           on f.submission_date_key = d.date_key
