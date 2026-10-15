# Metric Definition Caveats Checklist

## Recommended file path

```text
wiki/rules/caveats-checklist.md
```

## Purpose

This document helps the Agent, before querying data with KB metric definitions, quickly identify which information affects metric calculation and which is merely query parameter differences.

The company-level knowledge base should include this checklist as metric definition confirmation rules reused by all projects.

## Caveats that must be confirmed

The following items change the metric calculation definition and must be confirmed with the user (or have a default choice stated explicitly) before querying data.

| Type | Check item | Impact |
| --- | --- | --- |
| Analysis subject | Whether account, device, role, and user are consistent | Affects deduplication and attribution |
| Initial event | Whether the cohort starting event is unique | Affects the population entering the calculation |
| Return event | Whether the conversion, payment, or retention event represents the target behavior | Affects the numerator and attribution |
| Amount field | Whether the revenue field is actual paid amount, net revenue, or order amount | Affects revenue scale |
| Aggregation method | Whether sum, per-user, mean, or ratio is explicit | Affects metric interpretation |
| New-user definition | Whether first-day, new registration, first login, or lifecycle field definitions are explicit | Affects the user set |
| Metric observation window | Whether windows such as 7-day, 14-day, or 30-day are part of the metric definition | Affects LTV, retention, and similar metrics |
| Filter conditions | Whether filters such as tag, channel, platform, or server affect the target population | Affects result comparability |
| Denominator definition | Whether denominators such as user count, active count, or paying-user count are explicit | Affects per-user and conversion metrics |
| Business context / data availability boundary | Whether the project has business events (bans, version releases, migrations) that make certain date ranges incomparable | Affects result comparability and time range validity |

## Differences that should not require mandatory confirmation

The following are usually query parameters or display parameters; user requirements may override report default configurations.

| Type | Description |
| --- | --- |
| Query date range | When the user asks for this week, this month, or a specific date, follow the user's request |
| Display granularity | Day, week, or month granularity can be switched per the user's request |
| Sort order | Does not change the metric calculation formula |
| Display fields | Only affect result presentation, not the metric definition |
| Extra group by | If the dimension exists and does not change the population definition, execute directly |
| Report default time | The report's default query date is not a metric definition the user's request has to align with |

## Special note: time windows

Time-related information needs to be split into two categories:

| Type | Is metric definition | Example |
| --- | --- | --- |
| Query date range | No | Users queried from 2026-08-01 to 2026-08-07 |
| Metric observation window | Yes | Computing 7-day LTV, 14-day retention, 30-day payback |

When the user's query date range differs from the report's default date range, there is no need to require them to match.

When the observation window requested by the user differs from the matched metric definition, confirmation is needed, because this changes the metric itself.

## Common risk patterns

### Name implies a config that does not match

The report name contains words such as platform, channel, segment, or version, but the configuration has no corresponding `group_by` or filter conditions.

Handling: point out the discrepancy between name and configuration, and query only by the configured metric definition, unless the user explicitly asks to add dimensions or filters.

### Special tag filtering

The metric depends on a business tag, a segmentation field, or a temporary list filter.

Handling: explain that this filter affects the target population; the company-level KB keeps only the filter type, not project-private tag names.

### Empty report or no readable configuration

The KB contains a dashboard or report reference, but no readable model configuration.

Handling: never guess the metric definition from the name; fall back to available metadata, report details, or user confirmation.

### Inconsistent analysis subject

The same business metric uses account, device, or role as the analysis subject in different reports.

Handling: treat as a strong caveat; confirm the subject before querying data.

### Unclear amount field semantics

The payment amount field may represent original price, actual paid, pre-tax, post-tax, post-refund net amount, or currency-converted amount.

Handling: unless the KB clarifies the field semantics, confirm before querying data.

### Data gaps caused by business events

The project has business events such as bans, version launches, or channel migrations that make certain date ranges incomparable.

Handling: before querying, read the "data availability boundary" in the project-level `context.md` to determine whether the target date range falls within a valid interval; incomparable periods must be excluded or explicitly noted.

## Agent execution guidance

```text
1. First match candidate metrics from the machine-readable registry.
2. Determine whether caveats is empty.
3. Determine whether the user is changing the metric calculation definition or query/display parameters.
4. Only initiate confirmation for the parts that change the calculation definition.
5. For overridden items such as query date range, granularity, and display dimensions, just note them in the result.
6. If uniquely matched and caveats is empty, state the metric definition and query data directly in the same reply.
```

## Recommended reply templates

Uniquely matched with no caveats:

```text
I will execute with the following metric definition: <metric definition summary>. The query range uses <date range> per your request, not the report's default date. Querying data directly below.
```

Caveats exist that affect the calculation:

```text
This metric has a metric definition point that affects the calculation and needs confirmation: <caveat>. After you confirm, I will query the data.
```

Only query parameters differ:

```text
The report's default time differs from this request, but this is only the query date range and does not affect the metric calculation definition. I will query using the time range you specified.
```
