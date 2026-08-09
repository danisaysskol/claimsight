-- Medical loss ratio (MLR) by employer group = paid claims / earned premium.
-- Earned premium is the monthly premium over the 24-month simulation window.
create or replace view v_mlr_by_group as
with paid as (
    select employer_group_id, sum(paid_amount_pkr) as paid_pkr, count(*) as claim_count
    from v_claims_enriched
    group by employer_group_id
)
select
    g.group_id                                        as employer_group_id,
    g.employer_name,
    g.industry,
    g.lives_covered,
    g.monthly_premium_pkr,
    (g.monthly_premium_pkr * 24)                      as earned_premium_pkr,
    coalesce(p.paid_pkr, 0)                           as paid_pkr,
    coalesce(p.claim_count, 0)                        as claim_count,
    case when g.monthly_premium_pkr > 0
         then coalesce(p.paid_pkr, 0) / (g.monthly_premium_pkr * 24) end as medical_loss_ratio
from marts.dim_employer_group g
left join paid p on g.group_id = p.employer_group_id
order by medical_loss_ratio desc nulls last
