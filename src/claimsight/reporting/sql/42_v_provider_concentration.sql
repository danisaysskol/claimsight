-- Provider concentration: each provider's share of total spend, with a running
-- cumulative share to read off the top-10 concentration.
create or replace view v_provider_concentration as
with spend as (
    select provider_id, hospital_name, sum(paid_amount_pkr) as paid_pkr
    from v_claims_enriched
    group by provider_id, hospital_name
),
total as (select sum(paid_pkr) as total_paid from spend)
select
    s.provider_id,
    s.hospital_name,
    s.paid_pkr,
    s.paid_pkr / nullif((select total_paid from total), 0)                       as spend_share,
    row_number() over (order by s.paid_pkr desc)                                 as spend_rank,
    sum(s.paid_pkr) over (order by s.paid_pkr desc rows between unbounded preceding and current row)
        / nullif((select total_paid from total), 0)                             as cumulative_share
from spend s
order by s.paid_pkr desc
