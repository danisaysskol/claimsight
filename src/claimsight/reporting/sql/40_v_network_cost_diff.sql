-- In-network vs out-of-network cost for the SAME procedure. Shows the OON
-- premium buyers pay for identical services.
create or replace view v_network_cost_diff as
with by_net as (
    select
        pr.procedure_code,
        pr.description,
        p.network_status,
        avg(l.unit_price_pkr) as avg_unit_price_pkr,
        count(*)              as line_count
    from marts.fct_claim_line l
    join marts.dim_procedure pr on l.procedure_sk = pr.procedure_sk
    join marts.dim_provider p   on l.provider_sk = p.provider_sk
    group by pr.procedure_code, pr.description, p.network_status
)
select
    procedure_code,
    description,
    max(case when network_status = 'In-Network' then avg_unit_price_pkr end)     as in_network_avg_pkr,
    max(case when network_status = 'Out-of-Network' then avg_unit_price_pkr end)  as out_network_avg_pkr,
    case
        when max(case when network_status = 'In-Network' then avg_unit_price_pkr end) > 0
        then max(case when network_status = 'Out-of-Network' then avg_unit_price_pkr end)
           / max(case when network_status = 'In-Network' then avg_unit_price_pkr end)
    end as oon_cost_multiple
from by_net
group by procedure_code, description
having max(case when network_status = 'In-Network' then avg_unit_price_pkr end) is not null
   and max(case when network_status = 'Out-of-Network' then avg_unit_price_pkr end) is not null
order by oon_cost_multiple desc nulls last
