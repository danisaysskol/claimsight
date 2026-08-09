-- Policies: type casting + boolean parsing.
select
    policy_id,
    plan_name,
    plan_tier,
    nullif(annual_limit_pkr, '')::numeric        as annual_limit_pkr,
    nullif(room_rent_cap_pkr, '')::numeric       as room_rent_cap_pkr,
    nullif(deductible_pkr, '')::numeric          as deductible_pkr,
    nullif(copay_pct, '')::numeric               as copay_pct,
    (lower(maternity_covered) = 'true')          as maternity_covered,
    nullif(pre_existing_waiting_months, '')::int as pre_existing_waiting_months
from {{ source('raw', 'policies') }}
