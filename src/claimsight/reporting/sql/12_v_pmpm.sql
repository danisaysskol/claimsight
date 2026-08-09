-- PMPM (per member per month) = total paid / member-months, from the member x
-- month fact. Member-months = distinct (member, month) rows with activity.
create or replace view v_pmpm as
with agg as (
    select
        month_start,
        to_char(month_start, 'YYYY-MM')  as year_month,
        count(*)                          as member_months,
        sum(paid_amount_pkr)              as paid_pkr,
        sum(billed_amount_pkr)            as billed_pkr
    from marts.fct_monthly_member_summary
    group by month_start
)
select
    year_month,
    member_months,
    paid_pkr,
    billed_pkr,
    case when member_months > 0 then paid_pkr / member_months end   as pmpm_paid_pkr,
    case when member_months > 0 then billed_pkr / member_months end as pmpm_billed_pkr
from agg
order by year_month
