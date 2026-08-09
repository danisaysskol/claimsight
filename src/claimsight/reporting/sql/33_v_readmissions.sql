-- Readmission proxy: same member admitted for the same diagnosis chapter within
-- 30 days of a prior inpatient claim's admission.
create or replace view v_readmissions as
with inpatient as (
    select
        f.claim_id,
        f.member_sk,
        dx.chapter,
        d.date_day as admit_day
    from marts.fct_claim_header f
    join marts.dim_date d on f.admission_date_key = d.date_key
    join lateral (
        select dl.diagnosis_sk
        from marts.fct_claim_line dl
        where dl.claim_id = f.claim_id
        limit 1
    ) fl on true
    join marts.dim_diagnosis dx on fl.diagnosis_sk = dx.diagnosis_sk
    where f.claim_type in ('Inpatient', 'Emergency', 'Maternity')
)
select
    a.member_sk,
    a.chapter,
    a.claim_id           as index_claim_id,
    b.claim_id           as readmit_claim_id,
    (b.admit_day - a.admit_day) as days_between
from inpatient a
join inpatient b
  on a.member_sk = b.member_sk
 and a.chapter = b.chapter
 and b.admit_day > a.admit_day
 and (b.admit_day - a.admit_day) <= 30
