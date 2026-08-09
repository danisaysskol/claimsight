-- Monthly member summary must only contain positive, sensible aggregates.
select member_month_sk
from {{ ref('fct_monthly_member_summary') }}
where claim_count <= 0
   or billed_amount_pkr < 0
   or paid_amount_pkr < 0
