-- Business rule: discharge cannot precede admission.
select claim_id, length_of_stay
from {{ ref('fct_claim_header') }}
where length_of_stay < 0
