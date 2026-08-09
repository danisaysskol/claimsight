-- Keep only lines whose parent claim survived cleaning, with sane amounts.
select l.*
from {{ ref('stg_claims_lines') }} l
inner join {{ ref('int_claims_cleaned') }} c on l.claim_id = c.claim_id
where l.line_billed_pkr >= 0
  and l.line_approved_pkr >= 0
  and l.quantity > 0
