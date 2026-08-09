-- Claim headers: parse mixed-format dates, cast amounts. No business logic and
-- no cleaning here — defect rows are preserved for the intermediate layer to
-- deal with, exactly as they arrived.
select
    claim_id,
    member_id,
    provider_id,
    policy_id,
    claim_type,
    {{ parse_date('admission_date') }}         as admission_date,
    {{ parse_date('discharge_date') }}         as discharge_date,
    {{ parse_date('submission_date') }}        as submission_date,
    {{ parse_date('adjudication_date') }}      as adjudication_date,
    {{ parse_date('payment_date') }}           as payment_date,
    status,
    nullif(denial_reason_code, '')             as denial_reason_code,
    nullif(billed_amount_pkr, '')::numeric     as billed_amount_pkr,
    nullif(approved_amount_pkr, '')::numeric   as approved_amount_pkr,
    nullif(paid_amount_pkr, '')::numeric       as paid_amount_pkr,
    nullif(member_share_pkr, '')::numeric      as member_share_pkr,
    nullif(adjudication_mode, '')              as adjudication_mode
from {{ source('raw', 'claims_header') }}
