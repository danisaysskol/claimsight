-- Fraud signal: providers whose average claim value exceeds their peer-group
-- (same provider_type) mean by more than 2 standard deviations.
create or replace view v_provider_anomaly as
with prov as (
    select
        provider_id, hospital_name, provider_type, network_status,
        count(*)              as claim_count,
        avg(billed_amount_pkr) as avg_claim_value
    from v_claims_enriched
    group by provider_id, hospital_name, provider_type, network_status
),
peer as (
    select
        provider_type,
        avg(avg_claim_value)          as peer_mean,
        stddev_pop(avg_claim_value)   as peer_sd
    from prov
    group by provider_type
)
select
    p.provider_id,
    p.hospital_name,
    p.provider_type,
    p.network_status,
    p.claim_count,
    p.avg_claim_value,
    peer.peer_mean,
    peer.peer_sd,
    case when peer.peer_sd > 0
         then (p.avg_claim_value - peer.peer_mean) / peer.peer_sd end as z_score,
    (peer.peer_sd > 0 and p.avg_claim_value > peer.peer_mean + 2 * peer.peer_sd) as is_anomalous
from prov p
join peer on p.provider_type = peer.provider_type
order by z_score desc nulls last
