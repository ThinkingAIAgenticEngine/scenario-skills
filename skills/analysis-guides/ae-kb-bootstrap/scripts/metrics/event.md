# Event Metric Family General Definition

## Suggested File Path

```text
wiki/metrics/event.md
```

## Applicable Scenarios

This document defines core metrics based on counting a single event (or a small number of events): activity, new users, payment scale, per-user counts, and ratio metrics derived from these. It applies to observing user volume, event counts, amounts, and derived ratios by day/week/month.

Applicable sub-metrics:

- Core activity metrics: DAU / WAU / MAU (triggered user count of the login or active event), new users (triggered user count of the register event).
- Counts and per-user averages: average logins per user, average payments per user, average duration per user (sum of an event numeric property divided by user count).
- Amount scale: payment amount (sum of the payment event amount field).
- Derived ratios / per-user amount: ARPU (payment amount / active users), ARPPU (payment amount / paying users), pay rate (paying users / active users).

When the company-level knowledge base uses this document, specific project event names, field names, and business filter conditions should be configured as instance configuration, not written into the general definition itself.

## Core Definition

Event-type metrics count or numerically aggregate one or more events, then normalize by user count or sum directly.

The standard definition includes the following parts:

1. Statistical event: the behavior carrying the metric (login, register, payment, etc.).
2. Aggregation method: total count `total_count`, triggered user count `user_count`, per-user count `per_user_count`, or `sum` / `avg` / `max` / `min` / `distinct_count` over a numeric field.
3. Value field (conditionally required): the amount or numeric field needed by numeric aggregations such as `sum` / `avg`.
4. Denominator (conditionally required): the denominator definition for ratio metrics such as ARPU / ARPPU / pay rate.
5. Analysis subject: account, device, role, or user unique identifier, which affects dedup.

## Recommended Machine-Readable Definition

```yaml
metric_family: event
model: event
analysis_subject: account_or_user
event: <stat_event_name>
value_field: <numeric_field_name>        # required for sum/avg; leave empty for count types
value_aggregation: user_count            # total_count|user_count|per_user_count|sum|avg|max|min|distinct_count
value_formula: UNIQUE(users)             # or SUM(<field>), SUM(<field>)/UNIQUE(users)
denominator:
  metric: USER_COUNT                     # used by ratio metrics such as ARPU/ARPPU/pay rate
  mode: unique
filters: []
query_date_range: <runtime_parameter>
granularity: <runtime_parameter>
group_by: <optional_dimension_list>
caveats: []
```

> **Implementation notes**: Ratio metrics such as ARPU, ARPPU, and pay rate have no standalone model; they are still implemented with the `event` model — use multiple metrics or `denominator` to carry the numerator and denominator (e.g., payment amount `sum` / active users `user_count`). The project-level registry provides the specific numerator/denominator metric configuration.

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range.

Metric calculation definitions that need confirmation include:

- Whether the statistical event represents the target behavior (activity, new user, or payment).
- Whether the aggregation method is counting, per-user average, or amount summation.
- Amount field semantics (actual paid, net amount, pre-tax, or after currency conversion).
- Denominator definition of ratio metrics (active users, paying users, or all users).
- Whether the analysis subject is account, device, role, or another user identifier.

Items that should NOT be forced as definition conflicts include:

- User's query date range differing from the report default range.
- User's granularity (day/week/month) differing from the report default granularity.
- User adds extra split dimensions without changing the metric calculation method.
- Display fields or sorting.

For the complete caveats and confirmation flow, see the [caveats checklist](../rules/caveats-checklist.md).

## Time-Related Conventions

Event-type metrics usually have no independent observation window (unlike retention / LTV, which have a cohort observation window); the query date range is determined by user requirements and is not part of the metric definition. However, "new users" requires attention to date attribution (attributed by registration date / first login date).

## Common Event and Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Statistical event | The behavior carrying the metric | `<login_event>`, `<register_event>`, `<payment_event>` |
| Value field | Numeric field for sum/avg aggregation | `<payment_amount_field>`, `<duration_field>` |
| Denominator | Denominator of ratio metrics | active users `<login_event>`, paying users `<payment_event>` |
| User identifier | Used for dedup and attribution | `<account_id>`, `<distinct_id>` |

When instantiating at the project level, map the placeholders to specific event names and property names; the company-level registry keeps only placeholders and field roles. See [Machine-Readable Metric Definition Table Schema](../reference/metric-registry.md).

## Output Requirements

When answering externally, it is recommended to explicitly state:

- The metric definition adopted this time (statistical event, aggregation method, value field, denominator).
- The user-specified query date range and granularity.
- Whether caveats exist.
- Data conclusions and the verifiable source.
