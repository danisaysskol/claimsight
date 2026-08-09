select
    claim_line_id,
    claim_id,
    nullif(line_no, '')::int              as line_no,
    procedure_code,
    diagnosis_code,
    nullif(quantity, '')::numeric         as quantity,
    nullif(unit_price_pkr, '')::numeric   as unit_price_pkr,
    nullif(line_billed_pkr, '')::numeric  as line_billed_pkr,
    nullif(line_approved_pkr, '')::numeric as line_approved_pkr
from {{ source('raw', 'claims_lines') }}
