select
    diagnosis_code,
    description,
    chapter
from {{ source('raw', 'diagnoses') }}
