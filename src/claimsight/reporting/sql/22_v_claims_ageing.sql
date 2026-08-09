-- Ageing of still-open claims (Pending / In Review) into 0-30/31-60/61-90/90+
-- day buckets, measured from submission to the end of the window.
create or replace view v_claims_ageing as
with open_claims as (
    select
        claim_id,
        (date '2026-06-30' - claim_date) as days_open,
        billed_amount_pkr
    from v_claims_enriched
    where status in ('Pending', 'In Review') and claim_date is not null
)
select
    case
        when days_open <= 30 then '0-30'
        when days_open <= 60 then '31-60'
        when days_open <= 90 then '61-90'
        else '90+'
    end                            as ageing_bucket,
    count(*)                       as open_claim_count,
    sum(billed_amount_pkr)         as open_billed_pkr
from open_claims
group by 1
order by 1
