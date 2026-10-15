# Path Metric Family General Definition

## Suggested File Path

```text
wiki/metrics/path.md
```

## Applicable Scenarios

This document defines metrics for user event flow / behavior sequences within a session, used to analyze the paths before and after key behaviors. It applies to pre-payment paths, behavior paths, key event flows, and similar scenarios.

Applicable sub-metrics:

- Pre-payment path: with the payment event as the endpoint, trace backward what the user did before paying (backward).
- Behavior path: with the launch / entry event as the start point, look forward at the user's subsequent behavior (forward).
- Key event flow: the distribution of adjacent events before and after a key event.

When the company-level knowledge base uses this document, specific project event names, direction, session definition, and included event set should be configured as instance configuration, not written into the general definition itself.

## Core Definition

Path analysis uses the source event as the anchor, and counts the other events a user triggers in sequence within the same session (or within the session interval), forming nodes and flows.

The standard definition includes the following parts:

1. Source event: the start point (forward) or end point (backward) of the path.
2. Direction: forward looks after, backward looks before.
3. Session definition: how long without activity counts as session end (`session_interval` + `session_unit`).
4. Included events: the event set participating in path analysis `included_events`.

## Recommended Machine-Readable Definition

```yaml
metric_family: path
model: path
analysis_subject: account_or_user
source_event: <source_event_name>
direction: forward            # forward|backward
session:
  unit: minute
  value: <n>                  # session timeout, part of the metric definition
included_events:
  - <event1>
  - <event2>
value_aggregation: total_count    # trigger count / user count per node
filters: []
query_date_range: <runtime_parameter>
caveats:
  - Session timeout definition is part of the metric definition; changing the session definition requires re-confirmation
```

## Metric Definition Confirmation Principles

Before running analysis you only need to confirm the metric calculation definition; you do not require the user's requested time range to match the original report's default time range.

Metric calculation definitions that need confirmation include:

- Source event and direction (look before or after).
- Session timeout definition (how long counts as one session).
- The event set included in the path.

Items that should NOT be forced as definition conflicts include:

- User's query date range differing from the report default range.
- Number of displayed nodes or hierarchy depth.

For the complete caveats and confirmation flow, see the [caveats checklist](../rules/caveats-checklist.md).

## Common Event and Field Mapping

The company-level knowledge base does not hard-code specific project field names, but recommended mappings may be recorded:

| Role | Meaning | Example placeholder |
| --- | --- | --- |
| Source event | Path anchor | `<payment_event>`, `<launch_event>` |
| Included event | Events participating in the path | `<launch_event>`, `<register_event>`, `<payment_event>`, `<levelup_event>` |
| User identifier | Used for dedup / session attribution | `<account_id>` |

When instantiating at the project level, map the placeholders to specific event names and property names; the company-level registry keeps only placeholders and field roles. See [Machine-Readable Metric Definition Table Schema](../reference/metric-registry.md).

## Output Requirements

When answering externally, it is recommended to explicitly state:

- Source event, direction, session definition, included events.
- Main flow nodes and the verifiable source.
