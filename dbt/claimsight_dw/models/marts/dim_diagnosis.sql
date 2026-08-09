select
    {{ surrogate_key(['diagnosis_code']) }} as diagnosis_sk,
    diagnosis_code,
    description,
    chapter
from {{ ref('stg_diagnoses') }}
