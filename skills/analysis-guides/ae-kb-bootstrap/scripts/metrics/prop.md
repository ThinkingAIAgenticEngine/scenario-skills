# Property Metric Family General Definition

## Suggested File Path

```text
wiki/metrics/prop.md
```

## Applicable Scenarios

This document defines profile / composition metrics based on user properties (rather than events), counting the number of users satisfying a property condition or the aggregated value of a property. It applies to user composition, level profile, active / paying user profile, and similar scenarios.

Applicable sub-metrics:

- User composition: group by a user property (platform / channel / level / lifecycle) and count users and share.
- Level / lifecycle profile: count users by level or lifecycle tier.
- Paying / active user profile: distribution of a user property within the paying or active population.

When the company-level knowledge base uses this document, specific project user properties, grouping dimensions, and filters should be configured as instance configuration, not written into the general definition itself.

## Core Definition

Property analysis uses user properties as dimensions, counting users per group (`user_count`) or numerically aggregating a property. Unlike event analysis, property analysis is based on the user property table snapshot and usually has no time range.

The standard definition includes the following parts:

1. Statistical metric: without a property use `user_count`; numeric properties may use `sum` / `avg` / `max` / `min` / `distinct_count`.
2. Grouping dimensions: user property / tag / cluster, only `user_property` / `cluster` / `tag` are supported.
3. Filters: only user property / tag / cluster are supported; event properties are not supported.
4. Analysis subject.

## Recommended Machine-Readable Definition

```yaml
metric_family: prop
model: prop_analysis
analysis_subject: account_or_user
metric:
  aggregation: user_count      # user_count, or sum/avg/max/min/distinct_count for numeric properties
  property: <numeric_user_property>   # required for numeric aggregation
groups:
  - field: <user_property_or_tag>
filters: []
query_date_range: none          # property analysis is based on the user property snapshot and usually has no time range
caveats:
  - Property value snapshot definition (current value vs historical value) must be confirmed
```

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range (property analysis usually has no time range).

Metric calculation definitions that need confirmation include:

- Grouping property and statistical metric (user count or numeric aggregation).
- Property semantics (definition of level / lifecycle / channel).
- Snapshot definition of property values (current value or historical value).

Items that should NOT be forced as definition conflicts include:

- Display dimensions (property analysis is itself primarily grouping-based).
- Result sorting method.

For the complete caveats and confirmation flow, see the [caveats checklist](../rules/caveats-checklist.md).

## Common Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Grouping property | Profile dimension | `<platform_field>`, `<channel_field>`, `<level_field>`, `<lifecycle_field>` |
| Numeric property | Aggregation field | `<balance_field>`, `<spend_field>` |
| User identifier | Used for dedup | `<account_id>` |

When instantiating at the project level, map the placeholders to specific user property names; the company-level registry keeps only placeholders and field roles. See [Machine-Readable Metric Definition Table Schema](../reference/metric-registry.md).

## Output Requirements

When answering externally, it is recommended to explicitly state:

- Grouping property, statistical metric.
- User count and share per group.
- Whether caveats exist.
- Data conclusions and the verifiable source.
