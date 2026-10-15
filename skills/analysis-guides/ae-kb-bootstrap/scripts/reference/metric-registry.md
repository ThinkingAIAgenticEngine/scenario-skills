# Machine-readable Metric Definition Table Schema

## Purpose

This document defines a company-level, reusable machine-readable metric definition table format, so that an Agent can reliably identify metric definitions before querying data and reduce free-text interpretation drift.

This schema is meant to live in the company-level knowledge base; each project should maintain an instantiated registry in the project knowledge base.

## Recommended file path

```text
wiki/reference/metric-registry.md
```

## Top-level structure

```yaml
schema_version: "1.0"
scope: company_standard
metric_registry_type: analysis_metric_registry
owner_team: <team_name>
updated_at: <YYYY-MM-DD>
common_metric_rules:
  - <rule>
field_definitions:
  <field_or_placeholder>:
    role: <field_role>
    description: <description>
metrics:
  - metric_id: <stable_metric_id>
    metric_name: <display_name>
    metric_family: <ltv|retention|event|funnel|distribution|interval|path|attribution|prop|revenue|conversion|custom>
    model: <analysis_model>
    analysis_subject: <account|user|device|role|account_or_user|other>
    initial_event: <event_name_or_placeholder>
    return_event: <event_name_or_placeholder>
    value_field: <field_name_or_placeholder>
    value_aggregation: <sum|count|unique_count|avg|ratio|custom>
    value_formula: <formula>
    denominator:
      metric: <optional_denominator_metric>
      mode: <optional_denominator_mode>
    filters:
      - field: <field_name_or_placeholder>
        operator: <eq|neq|in|not_in|gte|lte|exists|not_exists|custom>
        value: <value_or_placeholder>
    observation_window:
      unit: <day|week|month|none>
      length: <number_or_runtime_parameter>
      is_metric_definition: true
    default_query_date_range:
      type: <recent|fixed|runtime_parameter>
      value: <value>
      is_metric_definition: false
    granularity: <day|week|month|runtime_parameter>
    group_by:
      - <dimension>
    caveats:
      - <caveat>
    source_examples:
      - <optional_source_reference>
```

## Field descriptions

| Field | Required | Description |
| --- | --- | --- |
| `metric_id` | Yes | Stable machine identifier; should not change when the display name changes |
| `metric_name` | Yes | Human-readable metric name |
| `metric_family` | Yes | Metric family, used to quickly route to the analysis model |
| `model` | Yes | Analysis model, e.g. retention |
| `analysis_subject` | Yes | Analysis subject; must be explicit about whether it is account, device, user, or role |
| `initial_event` | Conditionally required | Cohort starting event; may be empty for non-cohort metrics and should be noted |
| `return_event` | Conditionally required | Return, conversion, or revenue event |
| `value_field` | Conditionally required | Amount or value field |
| `value_aggregation` | Yes | Aggregation method for the amount/value field, e.g. sum |
| `value_formula` | Yes | Executable or explainable calculation formula |
| `denominator` | No | Denominator definition for metrics such as per-user and conversion rate |
| `filters` | No | Filter conditions that affect metric calculation |
| `observation_window` | No | Metric observation window; if it affects the metric definition, `is_metric_definition` is true |
| `default_query_date_range` | No | Default query date range; must not be treated as a metric definition the user's request has to match |
| `granularity` | No | Default granularity; may be overridden by the user's request |
| `group_by` | No | Default breakdown dimension |
| `caveats` | No | Risks, gaps, and items pending confirmation |
| `source_examples` | No | Example sources; do not write sensitive project IDs |

## Metric definition confirmation rules

When using this table, the Agent follows these rules:

1. If a metric is uniquely matched and `caveats` is empty, state the metric definition and query data directly in the same reply.
2. If a metric is uniquely matched but `caveats` is non-empty, first show the caveats and confirm the parts that affect calculation.
3. If multiple metric candidates match, ask the user to choose the metric calculation definition.
4. A difference between the user's query date range and the default query date range does not constitute a metric definition conflict.
5. If the user requests changing the observation window and that window is part of the metric definition, confirm before querying.
6. If the user only changes granularity, date range, or display dimensions without changing the calculation formula, execute directly and note the overridden items in the result.

## Example

```yaml
schema_version: "1.0"
scope: company_standard
metric_registry_type: analysis_metric_registry
owner_team: data
updated_at: "2026-08-11"
metrics:
  - metric_id: ltv_new_user_payment_success_sum
    metric_name: New User Payment LTV
    metric_family: ltv
    model: retention
    analysis_subject: account
    initial_event: <register_or_login_event>
    return_event: <payment_success_event>
    value_field: <payment_amount_field>
    value_aggregation: sum
    value_formula: SUM(<payment_amount_field>)
    denominator:
      metric: USER_COUNT
      mode: unique
    filters:
      - field: <lifecycle_field>
        operator: eq
        value: <new_user_value>
    observation_window:
      unit: day
      length: 7
      is_metric_definition: true
    default_query_date_range:
      type: runtime_parameter
      value: user_request
      is_metric_definition: false
    granularity: runtime_parameter
    group_by: []
    caveats: []
```

## Maintenance requirements

- Field names must be mappable to real events or properties in the data assets.
- The same metric's `metric_id` must not be reused for different calculation formulas.
- Project-private report IDs, dashboard IDs, and tag IDs should stay in the project-level registry, not the company-level schema.
- Every change to the calculation formula, analysis subject, core events, or filter conditions should update `updated_at` and record the reason for the change.
