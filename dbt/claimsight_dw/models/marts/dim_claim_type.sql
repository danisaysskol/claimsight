-- Small conformed dimension for claim type with a care-setting grouping.
select
    {{ surrogate_key(['claim_type']) }} as claim_type_sk,
    claim_type,
    care_setting
from (
    values
        ('Inpatient',  'Facility'),
        ('Daycare',    'Facility'),
        ('Maternity',  'Facility'),
        ('Emergency',  'Facility'),
        ('Outpatient', 'Ambulatory'),
        ('Diagnostic', 'Ambulatory'),
        ('Pharmacy',   'Ambulatory')
) as t(claim_type, care_setting)
