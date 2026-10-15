# Distribution Metric Family General Definition

## Suggested File Path

```text
wiki/metrics/distribution.md
```

## Applicable Scenarios

This document defines how users or events distribute over a numeric / property dimension, bucketing to count the number of users or the aggregated value per interval. It applies to duration distribution, level distribution, payment amount tiering, and similar scenarios.

Applicable sub-metrics:

- Duration distribution: user online duration / per-session duration bucketing.
- Level distribution: bucketing users by level and counting them.
- Payment amount tiering: bucketing by payment amount intervals and counting payers or amounts.
- Event property distribution: distribution over arbitrary event property values.

When the company-level knowledge base uses this document, specific project event names, distribution properties, and bucketing strategies should be configured as instance configuration, not written into the general definition itself.

## Core Definition

Distribution analysis buckets the values of a property on an event (or user) and returns the user count / event count or aggregated value per bucket.

The standard definition includes the following parts:

1. Statistical event and aggregation: event + aggregation method (without a property use `user_count` / `total_count`; numeric properties may use `sum` / `avg` / `max` / `min` / `median` / `percentile`).
2. Distribution property: the numeric or string property being bucketed.
3. Bucketing strategy: auto buckets `def` / custom intervals `user_defined` / discrete values `discrete`.
4. Analysis subject and filters.

## Recommended Machine-Readable Definition

```yaml
metric_family: distribution
model: distribution
analysis_subject: account_or_user
event: <stat_event_name>
property: <distribution_property>       # optional aggregation for numeric properties; string properties only support distinct distribution
value_aggregation: user_count           # user_count|total_count|sum|avg|max|min|median|percentile
bucket:
  strategy: def                         # def|user_defined|discrete
  boundaries: []                        # fill [100,1000,10000] when user_defined
filters: []
query_date_range: <runtime_parameter>
granularity: <runtime_parameter>
group_by: <optional_dimension_list>
caveats:
  - Bucketing strategy and interval boundaries are part of the metric definition; changing buckets requires re-confirmation
```

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range.

Metric calculation definitions that need confirmation include:

- Distribution property and bucketing strategy (auto / custom interval boundaries).
- Aggregation definition (user count, event count, or amount).
- Numeric property semantics (e.g., whether payment amount is actual paid or original price).

Items that should NOT be forced as definition conflicts include:

- User's query date range differing from the report default range.
- User's granularity (day/week/month) differing from the report default granularity.
- User adds extra split dimensions without changing the metric calculation method.

For the complete caveats and confirmation flow, see the [caveats checklist](../rules/caveats-checklist.md).

## Common Event and Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Statistical event | The behavior carrying the distribution | `<login_event>`, `<payment_event>`, `<levelup_event>` |
| Distribution property | The property being bucketed | `<duration_field>`, `<level_field>`, `<payment_amount_field>` |
| User identifier | Used for dedup | `<account_id>` |

When instantiating at the project level, map the placeholders to specific event names and property names; the company-level registry keeps only placeholders and field roles. See [Machine-Readable Metric Definition Table Schema](../reference/metric-registry.md).

## Output Requirements

When answering externally, it is recommended to explicitly state:

- Distribution property, bucketing strategy, aggregation definition.
- Each bucket's value and the verifiable source.
