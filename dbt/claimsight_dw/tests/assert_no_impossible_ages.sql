-- Business rule: no impossible member ages survive into dim_member.
select member_id, age_years
from {{ ref('dim_member') }}
where age_years < 0 or age_years > 120 or date_of_birth > date '{{ var("window_end") }}'
