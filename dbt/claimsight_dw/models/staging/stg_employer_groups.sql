-- Employer groups: type casting + canonical city (trim + title-case).
select
    group_id,
    name,
    industry,
    initcap(btrim(city))                     as city,
    {{ parse_date('contract_start') }}       as contract_start,
    {{ parse_date('contract_end') }}         as contract_end,
    nullif(lives_covered, '')::int           as lives_covered,
    nullif(monthly_premium_pkr, '')::numeric as monthly_premium_pkr
from {{ source('raw', 'employer_groups') }}
