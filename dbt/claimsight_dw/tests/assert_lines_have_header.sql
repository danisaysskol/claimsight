-- Referential integrity: every claim line's claim must exist in the header fact.
select l.claim_line_id
from {{ ref('fct_claim_line') }} l
left join {{ ref('fct_claim_header') }} h on l.claim_id = h.claim_id
where h.claim_id is null
