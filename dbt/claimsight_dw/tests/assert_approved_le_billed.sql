-- Business rule: approved amount can never exceed billed amount.
select claim_id, approved_amount_pkr, billed_amount_pkr
from {{ ref('fct_claim_header') }}
where approved_amount_pkr > billed_amount_pkr
