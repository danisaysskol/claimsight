-- Utilisation and length-of-stay by claim type. Utilisation per 1,000 members
-- uses the distinct member count as the exposed population.
create or replace view v_utilisation as
with pop as (select count(*) as member_count from marts.dim_member where is_current)
select
    c.claim_type,
    count(*)                                                as claim_count,
    1000.0 * count(*) / nullif((select member_count from pop), 0) as claims_per_1000_members,
    avg(case when c.claim_type in ('Inpatient', 'Maternity', 'Emergency')
             then c.length_of_stay end)                     as avg_length_of_stay,
    sum(c.paid_amount_pkr)                                  as paid_pkr
from v_claims_enriched c
group by c.claim_type
order by claim_count desc
