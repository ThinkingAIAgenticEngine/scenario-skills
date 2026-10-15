# LTV Metric General Definition

## Suggested File Path

```text
wiki/metrics/ltv.md
```

## Applicable Scenarios

This document defines the general calculation definition for revenue-type LTV metrics, suitable for analysis scenarios that use a cohort of users' initial behavior, observe subsequent payment behavior, and aggregate revenue.

When the company-level knowledge base uses this document, specific projects, reports, tag fields, and business filter conditions should be configured as instance configuration, not written into the general definition itself.

## Core Definition

LTV is a value metric that takes a group of users as the analysis subject, counts the revenue they subsequently generate within a specified observation window, and normalizes by user count or sums directly.

The standard definition includes four required parts:

1. Initial user set: determined by the initial event and initial filter conditions.
2. Return or conversion event: used to capture the user's subsequent payment or value behavior.
3. Value field and aggregation method: usually the sum of the payment amount field.
4. User count definition: used for the denominator or cohort size description, usually the unique user count.

## Recommended Machine-Readable Definition

```yaml
metric_family: ltv
model: retention
analysis_subject: account_or_user
initial_event: <initial_event_name>
return_event: <payment_success_event>
value_field: <payment_amount_field>
value_aggregation: sum
value_formula: SUM(<payment_amount_field>)
denominator:
  metric: USER_COUNT
  mode: unique
initial_filters:
  - field: <lifecycle_or_new_user_field>
    operator: eq
    value: <new_user_value>
observation_window:
  unit: day
  length: <n>
query_date_range: <runtime_parameter>
granularity: <runtime_parameter>
group_by: <optional_dimension_list>
caveats: []
```

> **Implementation notes**: ThinkingEngine has no standalone `retention_ltv` model. LTV is implemented with the retention model — `return_event` is the payment event, the amount aggregation is placed in `simultaneous_metrics` (e.g., `sum(<payment_amount_field>)`), and the cohort size is carried by the same group's `user_count`. The project-level registry provides the specific simultaneous_metrics configuration.

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range.

Metric calculation definitions that need confirmation include:

- How the initial user set is defined.
- Whether to look only at new users or first-day users.
- Whether the return or conversion event represents revenue recognition.
- Whether the revenue field is the actual payment amount.
- Whether the aggregation method is summation, per-user average, or another derived calculation.
- Whether the analysis subject is account, device, role, or another user identifier.
- Whether the observation window is part of the metric definition, e.g., 7-day LTV, 14-day LTV.

Items that should NOT be forced as definition conflicts include:

- The user's requested query date range differing from the report default date range.
- The user's requested granularity differing from the report default granularity.
- The user requests extra split dimensions without changing the metric calculation method itself.
- The user requests filtering by a business group, and the filter condition can be expressed explicitly.

## Time-Related Conventions

Two kinds of time need to be distinguished:

- Query date range: which days, weeks, or months this analysis should cover, usually determined by user requirements.
- Metric observation window: how long to observe after the initial behavior in the LTV model, e.g., 7 days, 14 days, 30 days. This is part of the metric calculation definition.

When the user's requirement differs from the report's default query date range, follow the user's requirement.

When the user's requirement differs from the metric observation window, e.g., the report is 7-day LTV but the user asks for 30-day LTV, confirm the observation window, because this changes the metric calculation definition.

## Common Event and Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Initial event | Behavior defining the cohort start | `<register_event>`, `<login_event>`, `anyEvent` |
| Return event | Subsequent behavior generating revenue or value | `<payment_success_event>` |
| Amount field | Numeric field used for revenue aggregation | `<payment_amount_field>` |
| Lifecycle field | Identifies new users, first-day users, or lifecycle tiers | `<lifecycle_field>` |
| User identifier | Used for dedup and attribution | `<account_id>`, `<distinct_id>` |

## Output Requirements

When answering externally, it is recommended to explicitly state:

- The metric definition adopted this time.
- The user-specified query date range.
- Whether the default observation window is retained.
- Whether caveats exist.
- Data conclusions and the verifiable source.
