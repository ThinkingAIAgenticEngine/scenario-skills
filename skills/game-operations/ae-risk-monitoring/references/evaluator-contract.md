# Evaluator contract

Use `scripts/evaluate_rules.py` for local backtests and recurring external monitoring. AE remains a read-only data source; never use AE native alert tasks.

## Contents

- [Input CSV](#input-csv)
- [Configuration JSON](#configuration-json)
- [Output JSON](#output-json)

## Input CSV

Required normalized columns:

```text
event_time,event_name,account_id,ip,device_id,amount,transaction_id,status
```

Only `event_time`, `event_name`, and `account_id` are globally required. A rule is skipped with a diagnostic when its required fields are absent. Use ISO-8601 timestamps with timezone offsets whenever possible.

Custom rules may reference any additional numeric CSV column returned from the verified AE query. Preserve its physical property name as the CSV header.

## Configuration JSON

```json
{
  "project_id": 123,
  "project_name": "Example",
  "notification_language": "zh-CN",
  "as_of": "2026-08-19T14:05:00+08:00",
  "event_names": {
    "login": ["login_success"],
    "register": ["register_success"],
    "withdrawal": ["withdraw_success"]
  },
  "rules": {
    "ip_account_burst": {
      "enabled": true,
      "window_minutes": 5,
      "cooldown_minutes": 30,
      "distinct_accounts": 10,
      "critical_accounts": 25,
      "event_groups": ["login", "register"]
    },
    "login_silence_or_drop": {
      "enabled": true,
      "window_minutes": 5,
      "cooldown_minutes": 20,
      "baseline_windows": 12,
      "minimum_baseline": 20,
      "drop_ratio": 0.7,
      "consecutive_windows": 2
    },
    "withdrawal_activity": {
      "enabled": true,
      "window_minutes": 10,
      "cooldown_minutes": 10,
      "notify_any": true,
      "high_amount": 1000,
      "account_frequency": 3,
      "shared_origin_accounts": 3,
      "success_statuses": ["success"]
    }
  },
  "custom_rules": [
    {
      "id": "payment_failure_rate",
      "name": "High Payment Failure Rate",
      "enabled": true,
      "window_minutes": 10,
      "consecutive_periods": 2,
      "cooldown_minutes": 30,
      "group_by": ["channel", "platform"],
      "max_groups": 50,
      "notification_group_limit": 5,
      "metrics": [
        {
          "alias": "A",
          "event_name": "payment_failed",
          "aggregation": "count",
          "filters": [
            {"connector": "AND", "property": "platform", "operator": "eq", "value": "iOS"},
            {"connector": "AND", "property": "error_code", "operator": "in", "value": "1001,1002"}
          ]
        },
        {"alias": "B", "event_name": "payment_attempt", "aggregation": "count", "filters": []}
      ],
      "expression": "A / B * 100",
      "comparator": ">=",
      "threshold": 20,
      "severity": "CRITICAL"
    },
    {
      "id": "currency_net_output",
      "name": "High Net Virtual Currency Output",
      "enabled": true,
      "window_minutes": 60,
      "metrics": [
        {"alias": "A", "event_name": "currency_gain", "aggregation": "sum", "property": "amount"},
        {"alias": "B", "event_name": "currency_spend", "aggregation": "sum", "property": "amount"}
      ],
      "expression": "A - B",
      "comparator": ">",
      "threshold": 100000,
      "severity": "WARNING"
    }
  ],
  "privacy": {
    "mask_identifiers": true
  }
}
```

`as_of` defaults to the latest event time. For reliable scheduled monitoring, pass the scheduler's timezone-aware evaluation time.

Supported aggregations are `count`, `distinct_users`, `sum`, `avg`, `min`, and `max`. The last four require a numeric `property`. Formulas accept declared aliases, numeric constants, parentheses, and `+ - * /` only. Comparators are `>`, `>=`, `<`, `<=`, `==`, and `!=`.

`notification_language` controls customer-facing notification text. Supported values are `zh-CN` and `en-US`; it defaults to `zh-CN` when omitted. Diagnostics, JSON keys, and technical evidence remain in English for stable automation contracts.

Each metric may include up to 10 `filters`. Supported operators are `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `contains`, `not_contains`, `in`, `not_in`, `is_set`, and `is_not_set`. The first connector is treated as `AND`; subsequent connectors may be `AND` or `OR` and are evaluated left to right. `in` and `not_in` accept comma-separated values. `is_set` and `is_not_set` use `null` as their value. Resolve every filter property against AE metadata before building a query, allow-list the operator, and safely quote the physical identifier and literal.

Set each filter's optional `value_type` from resolved metadata: `number` for numeric properties and `string` otherwise. Equality is exact string equality by default, so identifiers such as `001` and `1` remain distinct. Numeric comparators always require numeric values.

Metric aliases are internal. Customer-facing notification text must render each alias as its event and aggregation label, such as `ta_pageview distinct users`, and lead with the configured rule name. Keep the raw expression and alias-value map only in structured evidence for diagnostics.

`consecutive_periods` is an integer from 1 through 12 and defaults to 1 for backward compatibility. Evaluate adjacent, non-overlapping windows ending at `as_of`. Trigger only when all required windows satisfy the comparator. Include each period's start, end, metric values, expression value, and match result in structured evidence.

`group_by` is optional and contains at most two unique property names shared by every metric. Resolve each name against every participating event before querying. Evaluate formulas independently for each group tuple and require the same tuple to satisfy every consecutive period. `max_groups` defaults to 50 and caps groups by filtered event volume; `notification_group_limit` defaults to 5 and may not exceed 5. Each emitted group alert receives its own deduplication scope. Mask IP, account, user, device, bank, and card-like group values in customer-facing output.

## Output JSON

```json
{
  "status": "CRITICAL",
  "evaluated_at": "...",
  "project": {"id": 123, "name": "Example"},
  "notification_language": "zh-CN",
  "alerts": [
    {
      "rule_id": "ip_account_burst",
      "severity": "CRITICAL",
      "title": "Multi-account Registration from One IP",
      "window": {"start": "...", "end": "..."},
      "observed": {"distinct_accounts": 27},
      "threshold": {"distinct_accounts": 10},
      "dimensions": {"ip": "203.0.113.*"},
      "sample_accounts": ["ab***89"],
      "dedup_key": "...",
      "notification": "..."
    }
  ],
  "suppressed": [],
  "diagnostics": []
}
```

Pass `--state monitor-state.json` in recurring runs. The state file records the last emitted severity, deduplication key, and timestamp for each rule scope. Repeated alerts inside the cooldown are placed in `suppressed`; a severity escalation bypasses cooldown.

Top-level `status` reflects all current candidate alerts, including alerts suppressed by cooldown. `HEALTHY` therefore means no rule currently matched, not merely that no duplicate notification was sent.

`notification_batches` contains the delivery-ready messages. Multiple same-rule group alerts are combined into one message, capped at five groups, while `alerts` preserves per-group evidence and deduplication keys.

The evaluator generates notifications but does not send them. Deliver `alerts` through an explicitly approved messaging connector or caller-owned webhook. Never deliver `suppressed` entries and never use AE native notice configuration.
