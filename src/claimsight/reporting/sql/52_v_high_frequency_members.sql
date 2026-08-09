-- Fraud/utilisation signal: members whose claim frequency exceeds the
-- population mean by more than 2 standard deviations.
create or replace view v_high_frequency_members as
with per_member as (
    select member_id, count(*) as claim_count, sum(paid_amount_pkr) as paid_pkr
    from v_claims_enriched
    group by member_id
),
stats as (
    select avg(claim_count) as mean_freq, stddev_pop(claim_count) as sd_freq
    from per_member
)
select
    m.member_id,
    m.claim_count,
    m.paid_pkr,
    s.mean_freq,
    case when s.sd_freq > 0 then (m.claim_count - s.mean_freq) / s.sd_freq end as z_score
from per_member m
cross join stats s
where s.sd_freq > 0 and m.claim_count > s.mean_freq + 2 * s.sd_freq
order by m.claim_count desc
