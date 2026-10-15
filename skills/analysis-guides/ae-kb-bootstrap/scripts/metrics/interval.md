# Interval Metric Family General Definition

## Suggested File Path

```text
wiki/metrics/interval.md
```

## Applicable Scenarios

This document defines metrics for the time interval between two events, measuring how quickly users complete key behaviors. It applies to register → first-payment interval, repurchase interval, guide / level completion duration, and similar scenarios.

Applicable sub-metrics:

- Register → first-payment interval: interval from the register event to the first payment event.
- Repurchase interval: interval from first payment to second payment.
- Guide / level completion duration: interval from entering the guide to completing the guide.

When the company-level knowledge base uses this document, specific project event names, observation windows, and aggregation definitions should be configured as instance configuration, not written into the general definition itself.

## Core Definition

Interval analysis takes the initial event as the start point and the return event as the end point, computes the time interval between the two for each user within the window, and then aggregates into mean / median / distribution.

The standard definition includes the following parts:

1. Initial event: the start behavior of the interval calculation.
2. Return event: the end behavior of the interval calculation.
3. Observation window: maximum allowed interval `window`, which is part of the metric definition.
4. Aggregation definition: average interval `avg` / median interval `median` / bucketed distribution.
5. Relation field (optional): association key for the same user / session / order.

## Recommended Machine-Readable Definition

```yaml
metric_family: interval
model: interval
analysis_subject: account_or_user
initial_event: <initial_event_name>
return_event: <return_event_name>
window:
  unit: day
  value: <n>                 # maximum observation interval, part of the metric definition
relation_field: <relation_event_property>   # optional
value_aggregation: avg       # avg|median|distribution
value_formula: AVG(return_event_time - initial_event_time)
filters: []
query_date_range: <runtime_parameter>
granularity: <runtime_parameter>
group_by: <optional_dimension_list>
caveats:
  - Observation window (maximum interval) is part of the metric definition; changing the window requires re-confirmation
```

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range.

Metric calculation definitions that need confirmation include:

- Whether the initial event and return event represent the two target behaviors.
- Observation window (maximum interval) length, which is part of the metric definition.
- Aggregation definition (average, median, or distribution).
- Relation field.

Items that should NOT be forced as definition conflicts include:

- User's query date range differing from the report default range.
- User's granularity (day/week/month) differing from the report default granularity.
- User adds extra split dimensions without changing the metric calculation method.

For the complete caveats and confirmation flow, see the [caveats checklist](../rules/caveats-checklist.md).

## Time-Related Conventions

The observation window (maximum interval) is part of the metric definition; if the user changes the window it must be confirmed. The query date range is determined by user requirements.

## Common Event and Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Initial event | Interval start behavior | `<register_event>`, `<first_payment_event>`, `<tutorial_start_event>` |
| Return event | Interval end behavior | `<first_payment_event>`, `<second_payment_event>`, `<tutorial_complete_event>` |
| Relation field | Association key | `<account_id>`, `<order_id>` |
| User identifier | Used for dedup | `<account_id>` |

When instantiating at the project level, map the placeholders to specific event names and property names; the company-level registry keeps only placeholders and field roles. See [Machine-Readable Metric Definition Table Schema](../reference/metric-registry.md).

## Output Requirements

When answering externally, it is recommended to explicitly state:

- Initial event, return event, observation window, aggregation definition.
- Average / median interval results.
- Whether caveats exist.
- Data conclusions and the verifiable source.
