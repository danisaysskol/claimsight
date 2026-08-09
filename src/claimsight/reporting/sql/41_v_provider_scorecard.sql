-- Provider scorecard: volume, spend, denial behaviour and average claim value.
create or replace view v_provider_scorecard as
select
    provider_id,
    hospital_name,
    provider_city,
    provider_type,
    network_status,
    provider_tier,
    count(*)                                   as claim_count,
    sum(billed_amount_pkr)                     as billed_pkr,
    sum(paid_amount_pkr)                        as paid_pkr,
    avg(billed_amount_pkr)                      as avg_claim_value_pkr,
    avg(is_denied::numeric)                     as denial_rate,
    sum(savings_pkr)                            as savings_pkr
from v_claims_enriched
group by provider_id, hospital_name, provider_city, provider_type, network_status, provider_tier
order by billed_pkr desc
