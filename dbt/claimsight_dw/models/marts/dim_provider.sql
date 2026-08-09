-- Provider dimension with Type-2 SCD scaffolding on network_status (the field
-- that genuinely changes as providers join/leave the panel). One active version
-- per provider from the current snapshot; is_current flags it.
with providers as (
    select * from {{ ref('stg_providers') }}
)
select
    {{ surrogate_key(['provider_id', 'panel_since']) }} as provider_sk,
    provider_id,
    hospital_name,
    city,
    provider_type,
    network_status,
    tier,
    panel_since,
    panel_since                                         as valid_from,
    date '9999-12-31'                                   as valid_to,
    true                                                as is_current
from providers
