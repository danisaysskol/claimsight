-- Business rule: paid amount can never exceed approved amount.
select claim_id, paid_amount_pkr, approved_amount_pkr
from {{ ref('fct_claim_header') }}
where paid_amount_pkr > approved_amount_pkr
