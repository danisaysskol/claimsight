-- No duplicate business claims (same member/provider/admission/amount) remain
-- after de-duplication in the intermediate layer.
select member_sk, provider_sk, admission_date_key, billed_amount_pkr, count(*) as n
from {{ ref('fct_claim_header') }}
group by member_sk, provider_sk, admission_date_key, billed_amount_pkr
having count(*) > 1
