-- Full calendar dimension with Pakistani fiscal year (Jul–Jun).
with spine as (
    select date_day from {{ ref('int_date_spine') }}
)
select
    cast(to_char(date_day, 'YYYYMMDD') as int)            as date_key,
    date_day,
    extract(year from date_day)::int                      as calendar_year,
    extract(quarter from date_day)::int                   as calendar_quarter,
    extract(month from date_day)::int                     as month_number,
    to_char(date_day, 'Mon')                              as month_name_short,
    to_char(date_day, 'Month')                            as month_name,
    to_char(date_day, 'YYYY-MM')                          as year_month,
    extract(day from date_day)::int                       as day_of_month,
    extract(isodow from date_day)::int                    as iso_day_of_week,
    (extract(isodow from date_day) in (6, 7))             as is_weekend,
    (date_day = (date_trunc('month', date_day)
        + interval '1 month - 1 day')::date)              as is_month_end,
    -- Pakistani fiscal year runs July -> June.
    case when extract(month from date_day) >= 7
         then extract(year from date_day)::int + 1
         else extract(year from date_day)::int end        as fiscal_year,
    case
        when extract(month from date_day) in (7, 8, 9)    then 1
        when extract(month from date_day) in (10, 11, 12) then 2
        when extract(month from date_day) in (1, 2, 3)    then 3
        else 4 end                                        as fiscal_quarter
from spine
