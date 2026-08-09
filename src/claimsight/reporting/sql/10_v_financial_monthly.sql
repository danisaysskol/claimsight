-- Financial performance by month: billed / approved / paid, savings & approval
-- rates, and member cost share.
create or replace view v_financial_monthly as
select
    year_month,
    fiscal_year,
    count(*)                                              as claim_count,
    sum(billed_amount_pkr)                                as billed_pkr,
    sum(approved_amount_pkr)                              as approved_pkr,
    sum(paid_amount_pkr)                                  as paid_pkr,
    sum(member_share_pkr)                                 as member_share_pkr,
    sum(savings_pkr)                                      as savings_pkr,
    case when sum(billed_amount_pkr) > 0
         then sum(approved_amount_pkr) / sum(billed_amount_pkr) end as approval_rate,
    case when sum(billed_amount_pkr) > 0
         then sum(savings_pkr) / sum(billed_amount_pkr) end         as savings_rate,
    case when sum(billed_amount_pkr) > 0
         then sum(member_share_pkr) / sum(billed_amount_pkr) end    as member_cost_share
from v_claims_enriched
where year_month is not null
group by year_month, fiscal_year
order by year_month
