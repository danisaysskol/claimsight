-- Drop members with impossible ages (future DOB or age > 120). These are the
-- deliberately-injected accuracy defects; excluding them keeps dim_member clean
-- and keeps downstream claims referentially valid (claims are filtered to this
-- set in int_claims_cleaned).
with src as (
    select * from {{ ref('stg_members') }}
)
select *
from src
where date_of_birth is not null
  and date_of_birth <= date '{{ var("window_end") }}'
  and age_years between 0 and 120
