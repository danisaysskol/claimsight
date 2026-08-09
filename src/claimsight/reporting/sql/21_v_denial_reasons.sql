-- Denial reasons ranked by frequency and by value (billed on denied claims).
create or replace view v_denial_reasons as
select
    denial_reason_code,
    count(*)                                as denial_count,
    sum(billed_amount_pkr)                  as denied_billed_pkr,
    rank() over (order by count(*) desc)              as rank_by_frequency,
    rank() over (order by sum(billed_amount_pkr) desc) as rank_by_value
from v_claims_enriched
where status = 'Denied' and denial_reason_code is not null
group by denial_reason_code
order by denial_count desc
