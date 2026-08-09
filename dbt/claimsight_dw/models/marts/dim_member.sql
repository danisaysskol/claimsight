-- Member dimension with Type-2 SCD scaffolding. The source is a single snapshot
-- so each member currently has one active version; the model is written so that
-- if enrolment history were supplied it would version correctly. valid_from /
-- valid_to / is_current give BI tools point-in-time join capability.
with members as (
    select * from {{ ref('int_members_cleaned') }}
)
select
    {{ surrogate_key(['member_id', 'enrolment_date']) }} as member_sk,
    member_id,
    masked_cnic,
    name,
    gender,
    date_of_birth,
    age_years,
    case
        when age_years < 18 then '0-17'
        when age_years < 30 then '18-29'
        when age_years < 45 then '30-44'
        when age_years < 60 then '45-59'
        else '60+'
    end                                                  as age_band,
    city,
    employer_group_id,
    policy_id,
    relationship,
    enrolment_date,
    termination_date,
    -- SCD2 validity window
    enrolment_date                                       as valid_from,
    coalesce(termination_date, date '9999-12-31')        as valid_to,
    (termination_date is null)                           as is_current
from members
