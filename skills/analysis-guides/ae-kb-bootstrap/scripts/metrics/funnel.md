# Funnel Metric Family General Definition

## Suggested File Path

```text
wiki/metrics/funnel.md
```

## Applicable Scenarios

This document defines the general calculation definition for multi-step conversion metrics, observing the proportion of users who complete a sequence of behaviors in order within a conversion window. It applies to registration conversion, payment conversion, onboarding, repurchase / re-engagement, and similar scenarios.

Applicable sub-metrics:

- Registration conversion: enter → register → create role → complete onboarding.
- First-payment conversion: register → first payment.
- Repurchase conversion: first payment → second payment (or re-engagement login → payment).
- Onboarding conversion: guide launch → each step completed → final completion.

When the company-level knowledge base uses this document, specific project event names, step order, conversion window, and business filters should be configured as instance configuration, not written into the general definition itself.

## Core Definition

Funnel conversion rate is the proportion of users who complete each step in order within the conversion window.

The standard definition includes the following parts:

1. Step sequence: ordered event list `steps`; each step may carry step-level filters.
2. Conversion window: maximum allowed time `window` between adjacent steps (or relative to the first step), which is part of the metric definition.
3. Relation field: the association field determining that multiple steps belong to the same user / session / entity (e.g., account, order ID).
4. Analysis subject and filters: overall population definition and top-level filters.

## Recommended Machine-Readable Definition

```yaml
metric_family: funnel
model: funnel
analysis_subject: account_or_user
steps:
  - event: <step1_event>
  - event: <step2_event>
  - event: <step3_event>
window:
  unit: day
  value: <n>                 # conversion window, part of the metric definition
relation_field: <relation_event_property>   # optional relation property
value_aggregation: ratio
value_formula: UNIQUE(users_completed_stepN) / UNIQUE(users_entered_step1)
filters: []
query_date_range: <runtime_parameter>
granularity: <runtime_parameter>
group_by: <optional_dimension_list>
caveats:
  - Conversion window is part of the metric definition; changing the window requires re-confirmation
```

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range.

Metric calculation definitions that need confirmation include:

- Whether the step order and each step's event match the business funnel.
- Conversion window length (completed within the same day / within 7 days, etc.), which is part of the metric definition.
- Relation field (same user vs same order / session).
- Step-level filters (e.g., a step only counts paid channels or a specific version).

Items that should NOT be forced as definition conflicts include:

- User's query date range differing from the report default range.
- User's granularity (day/week/month) differing from the report default granularity.
- User adds extra split dimensions without changing the metric calculation method.

For the complete caveats and confirmation flow, see the [caveats checklist](../rules/caveats-checklist.md).

## Time-Related Conventions

The conversion window is part of the metric definition (same day, 7 days, etc.); if the user changes the window it must be confirmed. The query date range is determined by user requirements. In trend analysis, the latest date segment whose funnel has not fully elapsed within the window will be underestimated; dates without complete observation should be excluded.

## Common Event and Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Step event | Behavior at each funnel step | `<launch_event>`, `<register_event>`, `<create_role_event>`, `<tutorial_complete_event>`, `<payment_event>` |
| Relation field | Multi-step association key | `<account_id>`, `<order_id>` |
| User identifier | Used for dedup | `<account_id>` |

When instantiating at the project level, map the placeholders to specific event names and property names; the company-level registry keeps only placeholders and field roles. See [Machine-Readable Metric Definition Table Schema](../reference/metric-registry.md).

## Output Requirements

When answering externally, it is recommended to explicitly state:

- Step sequence, conversion window, relation field.
- Overall conversion rate and step-by-step conversion rate.
- The user-specified query date range.
- Whether caveats exist.
- Data conclusions and the verifiable source.
