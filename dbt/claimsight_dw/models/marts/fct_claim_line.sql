-- Line-grain atomic fact: one row per line of one claim.
with lines as (
    select * from {{ ref('int_claim_lines_cleaned') }}
),
hdr as (
    select
        claim_id, member_id, provider_id, submission_date, claim_type, status
    from {{ ref('int_claims_cleaned') }}
),
mbr as (select member_id, member_sk from {{ ref('dim_member') }}),
prv as (select provider_id, provider_sk from {{ ref('dim_provider') }}),
dia as (select diagnosis_code, diagnosis_sk from {{ ref('dim_diagnosis') }}),
prc as (select procedure_code, procedure_sk from {{ ref('dim_procedure') }})

select
    {{ surrogate_key(['l.claim_line_id']) }}                as claim_line_sk,
    l.claim_line_id,
    l.claim_id,
    l.line_no,
    mbr.member_sk,
    prv.provider_sk,
    dia.diagnosis_sk,
    prc.procedure_sk,
    cast(to_char(h.submission_date, 'YYYYMMDD') as int)     as submission_date_key,
    h.claim_type,
    h.status,
    l.procedure_code,
    l.diagnosis_code,
    l.quantity,
    l.unit_price_pkr,
    l.line_billed_pkr,
    l.line_approved_pkr,
    (l.line_billed_pkr - l.line_approved_pkr)               as line_savings_pkr
from lines l
inner join hdr h on l.claim_id = h.claim_id
left join mbr on h.member_id = mbr.member_id
left join prv on h.provider_id = prv.provider_id
left join dia on l.diagnosis_code = dia.diagnosis_code
left join prc on l.procedure_code = prc.procedure_code
