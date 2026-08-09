-- Operational KPIs by month: volume, denial rate, auto-adjudication rate and
-- turnaround-time statistics (mean, median, 90th percentile).
create or replace view v_operations_monthly as
select
    year_month,
    count(*)                                                    as claim_count,
    sum(is_denied)                                              as denied_count,
    avg(is_denied::numeric)                                     as denial_rate,
    avg(is_auto::numeric)                                       as auto_adjudication_rate,
    avg(tat_submit_to_adjudicate)                               as tat_adj_mean,
    percentile_cont(0.5) within group (order by tat_submit_to_adjudicate) as tat_adj_median,
    percentile_cont(0.9) within group (order by tat_submit_to_adjudicate) as tat_adj_p90,
    avg(tat_total)                                              as tat_total_mean,
    percentile_cont(0.9) within group (order by tat_total)      as tat_total_p90
from v_claims_enriched
where year_month is not null
group by year_month
order by year_month
