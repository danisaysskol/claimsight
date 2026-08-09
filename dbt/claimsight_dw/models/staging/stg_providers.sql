-- Providers: canonical city, date casting.
select
    provider_id,
    hospital_name,
    initcap(btrim(city))              as city,
    provider_type,
    network_status,
    tier,
    {{ parse_date('panel_since') }}   as panel_since
from {{ source('raw', 'providers') }}
