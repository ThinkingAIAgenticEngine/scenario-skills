# Retention Metric Family General Definition

## Suggested File Path

```text
wiki/metrics/retention.md
```

## Applicable Scenarios

This document defines the general calculation definition for retention metrics, suitable for analysis scenarios that use a cohort of users' initial behavior, observe whether they complete a return behavior on the subsequent Nth day/week/month, and calculate the retention rate.

Applicable sub-metrics:

- New-user retention: cohort starts from the register or first-login event; return is the login or active event.
- Payment retention: cohort starts from the first-payment event; return is the login or re-payment event.
- Core-gameplay retention: cohort starts from completing onboarding; return is login or active.
- Social retention: cohort starts from adding friends / joining a guild; return is login or active.

When the company-level knowledge base uses this document, specific project event names, field names, and business filter conditions should be configured as instance configuration, not written into the general definition itself.

## Core Definition

Retention rate is the proportion of users who still complete the return behavior, observed over a specified observation window (e.g., day 7, day 30) for a group of users.

The standard definition includes four required parts:

1. Initial user set: determines the cohort start from the initial event and initial filter conditions.
2. Return event: used to determine whether the user is still active or still paying on the observation day.
3. Observation window: the number of days/weeks/months observed after the initial event day, part of the metric definition.
4. Subject definition: account, device, role, or user unique identifier, which affects dedup and attribution.

## Recommended Machine-Readable Definition

```yaml
metric_family: retention
model: retention
analysis_subject: account_or_user
initial_event: <initial_event_name>
return_event: <return_event_name>
value_aggregation: ratio
value_formula: UNIQUE(return_event_users) / UNIQUE(initial_event_users)
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
  is_metric_definition: true
query_date_range: <runtime_parameter>
granularity: <runtime_parameter>
group_by: <optional_dimension_list>
caveats:
  - The analysis subject must match the project's retention default subject to avoid dedup definition drift
  - The observation window is part of the metric definition; changing the window requires re-confirmation
```

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range.

Metric calculation definitions that need confirmation include:

- How the initial user set is defined (register, first login, first payment, onboarding completion, etc.).
- Whether the return event represents activity or payment, and whether it matches the target behavior.
- Whether the observation window length (7/14/30 days or weeks/months) is part of the metric definition.
- Whether the analysis subject is account, device, role, or another user identifier.
- Whether the cohort start event is unique and whether lifecycle filtering needs to be added.

Items that should NOT be forced as definition conflicts include:

- User's query date range differing from the report default range.
- User's granularity (day/week/month) differing from the report default granularity.
- User adds extra split dimensions without changing the metric calculation method.
- User filters by a business group, and the filter condition can be expressed explicitly.

For the complete caveats and confirmation flow, see the [caveats checklist](../rules/caveats-checklist.md).

## Time-Related Conventions

Two kinds of time need to be distinguished:

- Query date range: which days/weeks/months this analysis should cover, determined by user requirements.
- Metric observation window: how long to observe after the initial behavior day (7/14/30 days, etc.), part of the metric calculation definition.

When the user's requirement differs from the metric observation window (e.g., the report is 7-day retention but the user asks for 30-day retention), confirm the observation window, because this changes the metric calculation definition.

For cohorts within the query date range, ensure that cohort day + observation window ≤ query day; otherwise the latest cohort's window retention rate will be underestimated because observation is incomplete. In trend analysis, only include cohorts that can be fully observed.

## Common Event and Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Initial event | Behavior defining the cohort start | `<register_event>`, `<first_login_event>`, `<first_payment_event>`, `<tutorial_complete_event>` |
| Return event | Behavior determining user return | `<login_event>`, `<active_event>`, `<payment_success_event>` |
| Lifecycle field | Identifies new users, first-day users, or lifecycle tiers | `<lifecycle_field>` |
| User identifier | Used for dedup and attribution | `<account_id>`, `<distinct_id>` |

When instantiating at the project level, map the placeholders to specific event names and property names; the company-level registry keeps only placeholders and field roles. See [Machine-Readable Metric Definition Table Schema](../reference/metric-registry.md).

## Output Requirements

When answering externally, it is recommended to explicitly state:

- The metric definition adopted this time (initial event, return event, observation window, subject).
- The user-specified query date range.
- Whether the default observation window is retained.
- Whether all cohorts can be fully observed, and whether incompletely observed ones are excluded.
- Data conclusions and the verifiable source.
