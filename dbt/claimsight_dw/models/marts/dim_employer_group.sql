select
    {{ surrogate_key(['group_id']) }} as employer_group_sk,
    group_id,
    name                              as employer_name,
    industry,
    city,
    contract_start,
    contract_end,
    lives_covered,
    monthly_premium_pkr
from {{ ref('stg_employer_groups') }}
