# Detail Workbook Specification

Deliverable 1 of 2, produced by `scripts/export_detail_excel.py`.

**Purpose: land everything that was retrieved, at the finest granularity
available, without filtering or premature aggregation.** The workbook is for the
customer's own follow-up analysis, so it must be more complete than the report
and less opinionated.

## Hard rules

1. **Never delete a sheet because data was unavailable.** Write a row explaining
   which dimension is not visible from this data source and why. A missing sheet
   looks like a bug; an explained empty sheet is an answer.
2. **Keep column names byte-identical to the platform's or the customer's own
   vocabulary.** Renaming for tidiness makes a later comparison ambiguous.
3. **Generate through the script, never by hand.** Column misalignment is the
   most common failure in this kind of deliverable and is invisible without
   checking.
4. **Land the finest grain available.** Per-day, per-node, per-metric for mode A;
   per-day and per-property-group for mode B.

## The seven sheets

### `1-策略概览`
Campaign identity and the reading instructions for the rest of the workbook.

| Column | Content |
|---|---|
| strategy / campaign name | as supplied by the user |
| object id | task / flow / config id (mode A), `-` for mode B |
| channel | push / in-app / SMS / ... |
| time window | start - end |
| target audience | the described audience, plus cluster or tag name when known |
| discriminating property | property and value, or `-` |
| recovery events | the event chain actually queried, with roles |
| attribution window | value + unit |
| data source mode | A: Engage native / B: third-party event recovery |
| trigger time | actual trigger time; falls back to the campaign start date with a `（任务起始日）` marker when the platform left `triggerTime` empty |
| trigger rule | the platform's cron expression, restated in plain words when recognizable |
| confidence statement | the degradation table, reproduced here so the workbook stands alone |
| field caveats | same-name metrics that carry different definitions in different interfaces, with both values and the reason |
| generated at | timestamp |

### `2-链路漏斗`
Stage, user count, stage-to-stage conversion, cumulative conversion, drop count,
drop rate, note. Stages that could not be measured are present with a `-` and a
note saying why, never omitted.

### `3-维度明细`
Cross-tabulation by whatever dimension the source supports - channel, platform,
language, node, or a property group. Mode B builds this from `--groups`.

### `4-时序趋势`
One row per period: date plus every metric. Daily when the window is short,
hourly when enough data exists. The summary row is excluded from this sheet and
recorded in sheet 1 instead.

### `5-人群分层`
Response broken down by activity level, payment tier, lifecycle stage, or new vs
returning. Empty with an explanation when neither mode can produce a
segmentation - this is the sheet most often unavailable in mode A.

### `6-策略与分组对比`
Multi-strategy comparison and A/B group comparison. When the platform supplied
lift and significance, those are reported as-is; when the comparison is a
quasi-experiment the sheet says so in the header row.

### `7-原始数据`
The interface response flattened and preserved, so any figure in the workbook can
be traced back to what the platform actually returned. Include the request
parameters alongside the payload.

## Mode-specific coverage

| Sheet | Mode A | Mode B |
|---|---|---|
| 1 策略概览 | full | full |
| 2 链路漏斗 | full chain | from the earliest tracked event |
| 3 维度明细 | node / channel / language | property groups |
| 4 时序趋势 | daily + per-instance | daily |
| 5 人群分层 | usually unavailable | via `--groups` |
| 6 策略与分组对比 | native experiment report | requires a group property |
| 7 原始数据 | engage payloads | qp + adhoc payloads |

## Naming

```
output/{strategy_name}_明细数据_{YYYYMMDD}.xlsx
```

The report references this exact filename, so the two deliverables travel
together.
