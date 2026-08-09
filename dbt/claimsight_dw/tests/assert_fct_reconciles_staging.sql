-- Reconciliation: cleaning may only remove rows, never invent them. The header
-- fact row count must not exceed the raw staging row count.
with fct as (select count(*) as n from {{ ref('fct_claim_header') }}),
     stg as (select count(*) as n from {{ ref('stg_claims_header') }})
select fct.n as fct_rows, stg.n as stg_rows
from fct, stg
where fct.n > stg.n
