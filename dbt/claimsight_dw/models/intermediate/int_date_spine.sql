-- Dense daily calendar covering the full simulation window (plus margin).
select generate_series(
    date '2024-01-01',
    date '2027-12-31',
    interval '1 day'
)::date as date_day
