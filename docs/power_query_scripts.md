# Power Query (M) scripts — connect Excel to the ClaimSight `reporting` views

Paste these into Excel via **Data → Get Data → Launch Power Query Editor →
New Source → Blank Query → Advanced Editor**. They connect directly to the
PostgreSQL `reporting` schema so the workbook refreshes live.

> Requires the **Npgsql** provider installed on Windows 11 (same as Power BI).
> Connection: server `localhost:5433`, database `claimsight`.

## Parameters (create these first as Power Query parameters)

- `PgServer` (Text) → `localhost:5433`
- `PgDatabase` (Text) → `claimsight`
- `DateFrom` (Date) → e.g. `2024-07-01`
- `DateTo` (Date) → e.g. `2026-06-30`

## Query: Claims (enriched, with a parameterised date filter)

```m
let
    Source = PostgreSQL.Database(PgServer, PgDatabase),
    View   = Source{[Schema="reporting", Item="v_claims_enriched"]}[Data],
    Filtered = Table.SelectRows(
        View,
        each [claim_date] <> null
            and [claim_date] >= DateFrom
            and [claim_date] <= DateTo
    ),
    Typed = Table.TransformColumnTypes(Filtered, {
        {"billed_amount_pkr", type number},
        {"approved_amount_pkr", type number},
        {"paid_amount_pkr", type number},
        {"claim_date", type date}
    })
in
    Typed
```

## Query: Financial monthly

```m
let
    Source = PostgreSQL.Database(PgServer, PgDatabase),
    Data   = Source{[Schema="reporting", Item="v_financial_monthly"]}[Data]
in
    Data
```

## Query: Provider scorecard

```m
let
    Source = PostgreSQL.Database(PgServer, PgDatabase),
    Data   = Source{[Schema="reporting", Item="v_provider_scorecard"]}[Data],
    Sorted = Table.Sort(Data, {{"billed_pkr", Order.Descending}})
in
    Sorted
```

## Query: Data-quality latest run

```m
let
    Source = PostgreSQL.Database(PgServer, PgDatabase),
    Q = Value.NativeQuery(
        Source,
        "SELECT * FROM dq.dq_results WHERE run_id = (SELECT max(run_id) FROM dq.dq_results)"
    )
in
    Q
```

## Refreshing

Data → Refresh All. Change `DateFrom` / `DateTo` (Queries & Connections →
right-click a parameter → Edit) and refresh to re-scope every query at once.
