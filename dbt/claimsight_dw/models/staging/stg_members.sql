-- Members: canonical city, mixed-format date parsing, derived age.
select
    member_id,
    masked_cnic,
    name,
    gender,
    {{ parse_date('date_of_birth') }}                                   as date_of_birth,
    initcap(btrim(city))                                                as city,
    employer_group_id,
    policy_id,
    {{ parse_date('enrolment_date') }}                                  as enrolment_date,
    {{ parse_date('termination_date') }}                                as termination_date,
    relationship,
    (date '{{ var("window_end") }}' - {{ parse_date('date_of_birth') }}) / 365 as age_years
from {{ source('raw', 'members') }}
