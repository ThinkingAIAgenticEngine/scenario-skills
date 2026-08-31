# AE query patterns

These are logical templates, not copy-paste queries. Resolve and quote the physical table, event, and property identifiers first. Every event-table scan must include a `"$part_date"` predicate.

## Contents

- [Metric-level filters](#metric-level-filters)
- [Shared grouping](#shared-grouping)
- [IP account burst](#ip-account-burst)
- [Login silence and comparable baseline](#login-silence-and-comparable-baseline)
- [Withdrawal activity](#withdrawal-activity)

For custom rules, prefer `scripts/compile_ae_rule_query.py` after metadata verification. It returns all metrics, grouping tuples, and consecutive periods for one rule in a single AE round trip. This reduces CLI/network overhead and keeps period watermarks consistent.

## Metric-level filters

Compile each custom metric's `filters` only after resolving its property names from AE metadata. Map the allow-listed operators to SQL predicates; quote physical identifiers and bind or safely quote literal values. Never paste the submitted filter expression into SQL.

```sql
AND (
  <verified_property_1> = <quoted_value_1>
  AND <verified_property_2> IN (<quoted_value_2>, <quoted_value_3>)
)
```

Preserve the submitted left-to-right connector semantics by nesting predicates as they are compiled. Treat `is_set` as `IS NOT NULL`, `is_not_set` as `IS NULL`, and require numeric metadata for `gt`, `gte`, `lt`, and `lte`.

## Shared grouping

Apply the rule-level `group_by` tuple identically to every metric query. Validate that each grouping property is available for every participating event, quote it as a physical identifier, and join metric aggregates on the complete grouping tuple.

```sql
SELECT
  <verified_group_property_1> AS group_1,
  <verified_group_property_2> AS group_2,
  <metric_aggregate> AS metric_value
FROM <event_table>
WHERE "$part_date" BETWEEN '<start_date>' AND '<end_date>'
  AND "$part_event" = '<verified_event>'
  AND <compiled_metric_filters>
GROUP BY 1, 2
```

Build the union of group tuples across metrics. Fill missing `count`, `distinct_users`, and `sum` values with zero; skip and diagnose groups missing a required `avg`, `min`, or `max`. Cap the evaluated set by filtered event volume before formula evaluation, then retain at most the five strongest matching groups for external delivery.

## IP account burst

```sql
SELECT
  date_trunc('minute', "#event_time") AS bucket,
  <ip_property> AS ip,
  count(DISTINCT "#account_id") AS distinct_accounts,
  count(DISTINCT <device_property>) AS distinct_devices,
  count(*) AS events
FROM <event_table>
WHERE "$part_date" BETWEEN '<start_date>' AND '<end_date>'
  AND "$part_event" IN ('<login_event>', '<register_event>')
  AND "#event_time" >= TIMESTAMP '<window_start>'
  AND "#event_time" < TIMESTAMP '<window_end>'
  AND <success_filter>
  AND <ip_property> IS NOT NULL
GROUP BY 1, 2
HAVING count(DISTINCT "#account_id") >= <threshold>
ORDER BY distinct_accounts DESC
```

For exact rolling windows, query the bounded raw interval and evaluate sliding windows in the bundled evaluator or a verified AE model that supports them.

## Login silence and comparable baseline

```sql
SELECT
  date_trunc('minute', "#event_time") AS bucket,
  count(DISTINCT "#account_id") AS login_users,
  count(*) AS login_events,
  max("#server_time") AS latest_server_time
FROM <event_table>
WHERE "$part_date" BETWEEN '<start_date>' AND '<end_date>'
  AND "$part_event" = '<login_event>'
  AND "#event_time" >= TIMESTAMP '<history_start>'
  AND "#event_time" < TIMESTAMP '<window_end>'
  AND <success_filter>
GROUP BY 1
ORDER BY 1
```

Generate the full time-bucket series outside the event table or with a supported sequence function so missing buckets are represented as zero. Compare current buckets with a median of comparable historical buckets.

Run a separate freshness query over heartbeat or all expected events:

```sql
SELECT max("#server_time") AS latest_server_time,
       max("#event_time") AS latest_event_time,
       count(*) AS recent_events
FROM <event_table>
WHERE "$part_date" BETWEEN '<start_date>' AND '<end_date>'
  AND "#server_time" >= TIMESTAMP '<freshness_start>'
```

## Withdrawal activity

```sql
SELECT
  "#event_time" AS event_time,
  "#account_id" AS account_id,
  <ip_property> AS ip,
  <device_property> AS device_id,
  <transaction_property> AS transaction_id,
  <amount_property> AS amount,
  <currency_property> AS currency,
  <status_property> AS status
FROM <event_table>
WHERE "$part_date" BETWEEN '<start_date>' AND '<end_date>'
  AND "$part_event" = '<withdrawal_event>'
  AND "#event_time" >= TIMESTAMP '<window_start>'
  AND "#event_time" < TIMESTAMP '<window_end>'
  AND <verified_success_filter>
ORDER BY "#event_time" DESC
```

Normalize currency before applying a cross-currency amount threshold. Query by immutable transaction ID to prevent duplicate alerts.
