-- Business rule: no negative monetary amounts survive into the fact.
select claim_id
from {{ ref('fct_claim_header') }}
where billed_amount_pkr < 0
   or approved_amount_pkr < 0
   or paid_amount_pkr < 0
   or member_share_pkr < 0
