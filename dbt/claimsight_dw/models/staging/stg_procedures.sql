select
    procedure_code,
    description,
    category,
    nullif(typical_cost_pkr, '')::numeric as typical_cost_pkr
from {{ source('raw', 'procedures') }}
