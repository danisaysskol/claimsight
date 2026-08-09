-- Fraud/waste signal: duplicate claim candidates surfaced from the raw feed
-- (same member/provider/admission/amount appearing more than once). These are
-- exactly the rows the data-quality engine quarantines.
create or replace view v_duplicate_candidates as
select
    member_id,
    provider_id,
    admission_date,
    billed_amount_pkr,
    count(*)                          as occurrence_count,
    array_agg(claim_id order by claim_id) as claim_ids
from raw.claims_header
group by member_id, provider_id, admission_date, billed_amount_pkr
having count(*) > 1
order by occurrence_count desc, billed_amount_pkr desc
