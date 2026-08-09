-- Top diagnoses by volume and by billed cost (line grain -> diagnosis).
create or replace view v_top_diagnoses as
select
    dx.diagnosis_code,
    dx.description,
    dx.chapter,
    count(*)                        as line_count,
    sum(l.line_billed_pkr)          as billed_pkr,
    sum(l.line_approved_pkr)        as approved_pkr
from marts.fct_claim_line l
join marts.dim_diagnosis dx on l.diagnosis_sk = dx.diagnosis_sk
group by dx.diagnosis_code, dx.description, dx.chapter
order by line_count desc
