select
    {{ surrogate_key(['policy_id']) }} as policy_sk,
    policy_id,
    plan_name,
    plan_tier,
    annual_limit_pkr,
    room_rent_cap_pkr,
    deductible_pkr,
    copay_pct,
    maternity_covered,
    pre_existing_waiting_months
from {{ ref('stg_policies') }}
