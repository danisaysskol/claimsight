-- Top procedures by volume and by billed cost.
create or replace view v_top_procedures as
select
    pr.procedure_code,
    pr.description,
    pr.category,
    count(*)                        as line_count,
    sum(l.quantity)                 as total_quantity,
    sum(l.line_billed_pkr)          as billed_pkr,
    sum(l.line_approved_pkr)        as approved_pkr
from marts.fct_claim_line l
join marts.dim_procedure pr on l.procedure_sk = pr.procedure_sk
group by pr.procedure_code, pr.description, pr.category
order by billed_pkr desc
