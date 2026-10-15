# Attribution Metric Family General Definition

## Suggested File Path

```text
wiki/metrics/attribution.md
```

## Applicable Scenarios

This document defines metrics that attribute conversion credit to touchpoint events that occurred before the conversion, used to evaluate the contribution of each touchpoint to the conversion. It applies to ad / channel touchpoint attribution, feature-usage attribution, conversion contribution analysis, and similar scenarios.

Applicable sub-metrics:

- Touchpoint attribution: contribution of ad clicks / impressions and other touchpoints reached before conversion.
- Behavioral attribution: contribution of features / content and other behavioral touchpoints used before conversion.
- Conversion contribution / TGI: share and contribution of each touchpoint in terms of converted user count.

When the company-level knowledge base uses this document, specific project event names, attribution models, and lookback windows should be configured as instance configuration, not written into the general definition itself.

## Core Definition

Attribution analysis takes the target conversion event as the endpoint, looks back over the touchpoint events within the window before the conversion, and assigns conversion credit to touchpoints according to the attribution model.

The standard definition includes the following parts:

1. Target event: the conversion behavior being attributed (e.g., payment).
2. Touchpoint events: the candidate touchpoint event list `attribution_events`.
3. Attribution model: first touch `first` / last touch `last` / equal credit `linear`.
4. Lookback window: how far back to look before the conversion `window`, which is part of the metric definition.
5. Target aggregation: total count `total_count` or `sum` over a numeric field.

## Recommended Machine-Readable Definition

```yaml
metric_family: attribution
model: attribution
analysis_subject: account_or_user
target_event: <conversion_event_name>
attribution_events:
  - <touchpoint_event1>
  - <touchpoint_event2>
attribution_model: last        # first|last|linear
window:
  unit: day
  value: <n>                   # lookback window, part of the metric definition
target_aggregation: total_count   # total_count|sum(<field>)
filters: []
query_date_range: <runtime_parameter>
caveats:
  - Attribution model and lookback window are part of the metric definition; changing the definition requires re-confirmation
```

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range.

Metric calculation definitions that need confirmation include:

- Target conversion event and touchpoint event definitions.
- Attribution model (first / last / linear), which is part of the metric definition.
- Lookback window length, which is part of the metric definition.

Items that should NOT be forced as definition conflicts include:

- User's query date range differing from the report default range.
- Display dimensions.

For the complete caveats and confirmation flow, see the [caveats checklist](../rules/caveats-checklist.md).

## Time-Related Conventions

The lookback window is part of the metric definition; if the user changes the window it must be confirmed. The query date range is determined by user requirements.

## Common Event and Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Target event | Conversion being attributed | `<payment_event>` |
| Touchpoint event | Reached before conversion | `<ad_click_event>`, `<feature_use_event>`, `<content_view_event>` |
| User identifier | Used for dedup / attribution | `<account_id>` |

When instantiating at the project level, map the placeholders to specific event names and property names; the company-level registry keeps only placeholders and field roles. See [Machine-Readable Metric Definition Table Schema](../reference/metric-registry.md).

## Output Requirements

When answering externally, it is recommended to explicitly state:

- Target event, touchpoint events, attribution model, lookback window.
- Each touchpoint's contribution and the verifiable source.
