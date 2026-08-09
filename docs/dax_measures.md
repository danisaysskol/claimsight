# ClaimSight — Power BI DAX Measures

Paste these into Power BI Desktop against the imported star schema. `dim_date`
must be marked as the date table (see `powerbi_guide.md`). Facts:
`fct_claim_header` (claim grain), `fct_claim_line` (line grain),
`fct_monthly_member_summary` (member×month). Relationships join each
`*_date_key` to `dim_date[date_key]` (the submission-date relationship is the
active one on `fct_claim_header`).

> 40+ measures. Create a dedicated `_Measures` table to hold them.

## Core financial

```DAX
Total Billed = SUM(fct_claim_header[billed_amount_pkr])
```
Sum of billed amounts.

```DAX
Total Approved = SUM(fct_claim_header[approved_amount_pkr])
```
Sum of approved amounts.

```DAX
Total Paid = SUM(fct_claim_header[paid_amount_pkr])
```
Sum of paid amounts.

```DAX
Total Member Share = SUM(fct_claim_header[member_share_pkr])
```
Sum members paid out of pocket.

```DAX
Total Savings = SUM(fct_claim_header[savings_pkr])
```
Billed minus approved (avoided cost).

```DAX
Claim Count = COUNTROWS(fct_claim_header)
```
Number of claims in context.

```DAX
Approval Rate = DIVIDE([Total Approved], [Total Billed])
```
Approved as a share of billed.

```DAX
Savings Rate = DIVIDE([Total Savings], [Total Billed])
```
Savings as a share of billed.

```DAX
Member Cost Share = DIVIDE([Total Member Share], [Total Billed])
```
Member burden as a share of billed.

```DAX
Avg Claim Value = DIVIDE([Total Billed], [Claim Count])
```
Mean billed value per claim.

## Premium, loss ratio, PMPM

```DAX
Earned Premium =
SUMX(VALUES(dim_employer_group[group_id]),
     CALCULATE(MAX(dim_employer_group[monthly_premium_pkr])) * 24)
```
Monthly premium × 24 months, summed over groups in context.

```DAX
Loss Ratio = DIVIDE([Total Paid], [Earned Premium])
```
Paid claims ÷ earned premium.

```DAX
Medical Loss Ratio = DIVIDE([Total Paid], [Earned Premium])
```
Loss ratio, sliced by employer group on a page.

```DAX
Member Months = COUNTROWS(fct_monthly_member_summary)
```
Distinct member-month rows with activity.

```DAX
PMPM Paid = DIVIDE([Total Paid], [Member Months])
```
Paid per member per month.

```DAX
PMPM Billed = DIVIDE([Total Billed], [Member Months])
```
Billed per member per month.

## Operational

```DAX
Denied Claims = CALCULATE([Claim Count], fct_claim_header[status] = "Denied")
```
Count of denied claims.

```DAX
Denial Rate = DIVIDE([Denied Claims], [Claim Count])
```
Share of claims denied.

```DAX
Auto Adjudicated = CALCULATE([Claim Count], fct_claim_header[adjudication_mode] = "Auto")
```
Count auto-adjudicated.

```DAX
Auto Adjudication Rate = DIVIDE([Auto Adjudicated], [Claim Count])
```
Share auto-adjudicated.

```DAX
Avg TAT Submit to Adjudicate = AVERAGE(fct_claim_header[tat_submit_to_adjudicate])
```
Mean days submission→adjudication.

```DAX
Median TAT = MEDIAN(fct_claim_header[tat_submit_to_adjudicate])
```
Median turnaround.

```DAX
P90 TAT =
PERCENTILE.INC(fct_claim_header[tat_submit_to_adjudicate], 0.9)
```
90th-percentile turnaround.

```DAX
Avg TAT Adjudicate to Pay = AVERAGE(fct_claim_header[tat_adjudicate_to_pay])
```
Mean days adjudication→payment.

```DAX
Open Claims = CALCULATE([Claim Count], fct_claim_header[status] IN {"Pending","In Review"})
```
Claims still in progress.

```DAX
Backlog Billed = CALCULATE([Total Billed], fct_claim_header[status] IN {"Pending","In Review"})
```
Billed value of the backlog.

## Clinical & utilisation

```DAX
Distinct Members = DISTINCTCOUNT(fct_claim_header[member_sk])
```
Members with activity in context.

```DAX
Utilisation per 1000 =
DIVIDE([Claim Count], DISTINCTCOUNT(dim_member[member_sk])) * 1000
```
Claims per 1,000 covered members.

```DAX
Avg Length of Stay =
AVERAGEX(FILTER(fct_claim_header, fct_claim_header[claim_type] IN {"Inpatient","Maternity","Emergency"}),
         fct_claim_header[length_of_stay])
```
Mean LOS for facility claims.

```DAX
Line Count = COUNTROWS(fct_claim_line)
```
Number of claim lines.

```DAX
Line Billed = SUM(fct_claim_line[line_billed_pkr])
```
Sum of line-level billed.

## Network & fraud

```DAX
OON Paid = CALCULATE([Total Paid], dim_provider[network_status] = "Out-of-Network")
```
Paid to out-of-network providers.

```DAX
OON Share = DIVIDE([OON Paid], [Total Paid])
```
Out-of-network share of spend.

```DAX
Top10 Provider Spend =
VAR t = TOPN(10, VALUES(dim_provider[provider_id]), [Total Paid], DESC)
RETURN CALCULATE([Total Paid], KEEPFILTERS(t))
```
Paid captured by the 10 highest-spend providers.

```DAX
Provider Concentration = DIVIDE([Top10 Provider Spend], [Total Paid])
```
Top-10 provider share of total spend.

```DAX
Duplicate Claim Flag =
IF(COUNTROWS(RELATEDTABLE(fct_claim_header)) > 1, 1, 0)
```
Marks a duplicate business signature (used in a table visual grouped by signature).

## Time intelligence (require dim_date marked as the date table)

```DAX
Paid YTD = TOTALYTD([Total Paid], dim_date[date_day])
```
Year-to-date paid.

```DAX
Paid PY = CALCULATE([Total Paid], SAMEPERIODLASTYEAR(dim_date[date_day]))
```
Prior-year paid (same period).

```DAX
Paid YoY % = DIVIDE([Total Paid] - [Paid PY], [Paid PY])
```
Year-over-year growth in paid.

```DAX
Billed YTD = TOTALYTD([Total Billed], dim_date[date_day])
```
Year-to-date billed.

```DAX
Paid Rolling 3M =
CALCULATE([Total Paid],
    DATESINPERIOD(dim_date[date_day], MAX(dim_date[date_day]), -3, MONTH))
```
Rolling 3-month paid total.

```DAX
Claim Count PY = CALCULATE([Claim Count], SAMEPERIODLASTYEAR(dim_date[date_day]))
```
Prior-year claim count.

```DAX
Denial Rate PY = CALCULATE([Denial Rate], SAMEPERIODLASTYEAR(dim_date[date_day]))
```
Prior-year denial rate.

```DAX
Paid Fiscal YTD =
TOTALYTD([Total Paid], dim_date[date_day], "06-30")
```
Year-to-date paid on the Pakistani fiscal year (ends 30 June).

```DAX
PMPM Rolling 3M =
DIVIDE(
    CALCULATE([Total Paid], DATESINPERIOD(dim_date[date_day], MAX(dim_date[date_day]), -3, MONTH)),
    CALCULATE([Member Months], DATESINPERIOD(dim_date[date_day], MAX(dim_date[date_day]), -3, MONTH))
)
```
Rolling 3-month PMPM.

## IBNR (simplified)

```DAX
IBNR Estimate =
VAR OpenBilled = [Backlog Billed]
VAR ConvRate = DIVIDE([Total Paid], [Total Approved])
RETURN OpenBilled * ConvRate
```
Rough incurred-but-not-reported reserve: open billed scaled by the paid/approved conversion.
```
