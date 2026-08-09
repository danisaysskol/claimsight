select
    {{ surrogate_key(['procedure_code']) }} as procedure_sk,
    procedure_code,
    description,
    category,
    typical_cost_pkr
from {{ ref('stg_procedures') }}
