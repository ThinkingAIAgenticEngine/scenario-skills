# TE Metric Alert (alert) Capability Boundaries and Routing Decision

This skill is the unified entry point for customer alerting requirements. For the same "alert" requirement, two underlying implementations may be used:

| Implementation | When to Use | Advantages | Limitations |
|---------|--------|------|------|
| **TE Metric Alert (alert)** | The requirement falls within alert capabilities | Native to the system, stable, free, no Agent required | Strict capability boundaries (see below) |
| **Agent Automation (automation)** | The requirement exceeds alert capability boundaries | Flexible, supports complex logic | Requires an execution Agent + scheduled tasks |

**Decision Principle**: If alert can do it, use alert. Only go to automation when it exceeds the boundaries.

---

## alert Capability Boundaries (verified against production)

### 1. Monitored Object (`alert_event_config`)

**Supported**:
- Single event (`event_name` required)
- Standard metric `type=0`, using `analysis` to select the analysis method
- Formula metric `type=1`, using `custom_event` / `formulation` to write expressions (ratios are supported)

**`analysis` enum** (based on production samples + product documentation):

| Enum | English | Requires quota | Remarks |
|------|------|----------------|------|
| `A100` | Total Count | No | |
| `A101` | Triggering User Count | No | User subject can be switched |
| `A102` | Per User Count | No | Total Count / Triggering User Count |
| `A103` | Sum | Yes (numeric property) | SUM(quota) |
| `A104` | Average | Yes (numeric property) | AVG(quota) |
| `A105` | Minimum | Yes (numeric property) | MIN(quota) |
| `A106` | Maximum | Yes (numeric property) | MAX(quota) |
| `A107+` | Percentile Series | Yes (numeric property) | p25/p50/p75/p90/p95/p99 |

**Not Supported**: Funnel, Retention, Custom SQL, cross-event analysis

**How to write the property name for property aggregation (required reading for A103-A107)**: Property aggregation must place the property name in the `alert_event_config.quota` field (at the same level as `analysis`):

```json
{"event_name": "payment", "event_type": "event", "type": 0, "analysis": "A103", "quota": "recharge_value", "relation": "1", "filts": []}
```

`quota` is the only property binding field that the platform parses (verified against production samples, confirmed by reading back project 5 alert 361). If the property name is placed in any other field (such as `analysis_params`), the platform raises no error but does not parse it either; the metric degrades into an aggregation with no property, and the first calculation fails immediately.

### 2. Monitoring Frequency (`alert_calc_freq`)

Only two values are used:

| Value | English |
|---|------|
| `hour` | By Hour |
| `day` | By Day |

(`minute_5` / `minute_10` / `realtime` are special configurations and are out of scope for this skill)

### 3. Trigger Rules (`alert_rules[].alert_standard`)

**Comparison baseline (`alert_compare_moment_type`)**:

| Value | English | Applicable Frequency |
|---|------|---------|
| `constant` | Fixed Value | hour + day |
| `last_hour` | Previous Hour | hour |
| `hour_of_yesterday` | Same Period Yesterday | hour |
| `avg_24hour` | Average Over the Past 24 Hours | hour |
| `last_day` | Previous Day | day |
| `day_of_last_week` | Same Time Last Week | day |
| `avg_7day` | Average Over the Past 7 Days | day |
| `predict_upper` | Predicted Upper Bound | hour + day |
| `predict_lower` | Predicted Lower Bound | hour + day |

**Comparison type (`alert_compare_type`)**:

| Value | English |
|---|------|
| `more` | Greater than (>) |
| `less` | Less than (<) |
| `more_or_less` | Rise or Fall (deviation) |

**Result type and threshold unit (`alert_result_type` + `calcu_value`)**:

| Value | English | calcu_value Unit (verified against production samples) |
|---|------|-------------------------------|
| `number` | Absolute Value | Same unit as the metric |
| `percent` | Percentage | **0-100**, e.g. for "less than 20%" write `calcu_value: 20` |

**Threshold unit for ratio metrics (important, do not mix up the two paths)**:

| Does the alert config contain `format: percent` | `alert_result_type` to use | How to write `calcu_value` | Example (less than 95%) |
|---|---|---|---|
| **No** (this is the case for all formula metrics created via API - the API whitelist does not accept the `format` field) | `number` | The formula's current value is a decimal in 0~1, so **user percentage / 100** | `calcu_value: 0.95` |
| Yes (only alerts created via the platform UI carry this field) | `percent` | **0-100** | `calcu_value: 95` |

The two forms are fully semantically equivalent (0.95 = 95%). When creating a formula alert via API, follow the first row and write `number` + 0.95; in delivery wording, use the dual notation "0.95 (i.e. 95%)" (the platform UI displays a numeric threshold for alerts without `format`). For the equivalent conversion rule on the automation path, see the `zero_denominator` strategy description in [`rule-schema.md`](rule-schema.md).

### 4. Group Alert (`group_by` + `alert_rules[].groups`)

- Select 1 event property or user property as the grouping dimension
- **Each group value must be written as its own separate rule** (`groups=["Apple"]`, `groups=["Huawei"]`...)
- When the `groups` array of a single rule contains multiple values, they are **aggregated together**, not judged independently
- Monitor at most **100 group values**
- **Group values must be enumerable**: newly appearing group values are not monitored automatically (this is the key limitation)

### 5. Notification Channels (`alert_push_target`)

| Field | Type | Description |
|------|------|------|
| `dd_web_hooks` | string[] | DingTalk bot webhook URL |
| `wx_web_hooks` | string[] | WeCom bot webhook URL |
| `feishu_web_hooks` | string[] | Feishu bot webhook URL |
| `slack_web_hooks` | string[] | Slack webhook URL |
| `third_party_user_ids` | number[] | Third-party recipients |
| `notice_configs` | object[] | Custom notification channels (nested structure) |

### 6. Other Limits

- A single project supports at most 50 alert tasks
- The name is at most 80 characters
- Time zones are supported (`task_zone_offset` + `data_zone_offset`, see "How to Fill Time Zone Fields" below)

### How to Fill Time Zone Fields (required reading, misconfiguration leads directly to alert_fail)

Both time zone fields of an alert are **required**, but what to fill in depends on whether the project **has time zone offset enabled** (`time_zone_enabled`):

| Project Type | `data_zone_offset` (data statistics time zone, i.e. settlement time zone) | `task_zone_offset` (delay setting: when the task initiates calculation) |
|---------|-----------------------------------|--------------------------------------------------|
| Time zone offset enabled (`time_zone_enabled=true`) | Settlement time zone offset value (e.g. `8`) | Server deployment time zone offset (e.g. `8`), or `99` |
| **Time zone offset not enabled (`time_zone_enabled=false`)** | **Must be `99`** (statistics follow the local time of data storage) | System default time zone offset, or `99` |

**Key rules**:

- **`data_zone_offset` is the decisive field**: For a project with time zone offset disabled, filling in any concrete value (including `0`) is rejected by the calculation engine with the error "Time zone for the current project is disabled; time zone configuration is not supported" → `recent_alert_execute_status=alert_fail`. This error is **not reported at creation time**; it appears only during the first calculation round (within 1~5 minutes after creation). At the instant of creation, alert get status is clean - you must wait for the first calculation round and then check the execution status to detect it (see "alert Execution Status Fields" at the end of this document)
- `task_zone_offset` is the "delay setting" (specifying at what time of day/hour the task initiates calculation) and is highly tolerant: for a project with time zone offset disabled, filling in 0/8/13/99 all calculate normally
- **DO NOT treat `default_time_zone_offset=0` as "UTC+0 for a single-time-zone project" and fill it into `data_zone_offset`** - `default_time_zone_offset` is the project default time zone, not a valid value source for the alert time zone field; when time zone offset is disabled, always use `99`
- How to read the system default time zone (server deployment time zone): the `scheduleTimeZone` returned by `ae-cli agent +list-automations` (e.g. `Asia/Shanghai` → offset 8); `project info get` does not provide this information

### 7. URL Back-link

After creation is complete, generate the redirect link; read the host dynamically via a command (**DO NOT hardcode the domain** - the access domain of a customer environment is determined by its deployment; the demo domain is valid only in this environment):

```bash
ae-cli config current --jq '.activeHost'
```

It returns something like `{"ok": true, "data": "https://xxx.example.com"}`; take the value of `data` and build the link:

```
<activeHost>/#/alert/detail?id=<project_id>_<alert_id>&currentProjectId=<project_id>
```

---

## Routing Decision Table

| Customer Requirement Characteristics | Route | Rationale |
|-------------|------|------|
| Single event + fixed value / previous period / same period / average / predicted value + By Hour/By Day | **alert** | Fully within alert capabilities |
| Single event + **enumerable grouping dimension** (<=100 values) + independent rule per group | **alert** | group_by + one rule per group |
| Ratio (A/B) + hourly/daily window | **alert** | Use a formula metric `type=1`; ratios for same-day cumulative or calendar-week windows go to automation (the window model is not supported by alert) |
| **Slack notification** | **Either works** | alert natively supports it via `slack_web_hooks`; automation uses custom_webhook to connect to a Slack incoming webhook - decide the route by the requirement's other characteristics |
| Funnel / Retention / Custom SQL / cross-event | **automation** | Not supported by alert |
| **Group dimension values are not enumerable** (e.g. user_id, dynamically added new channels) | **automation** | alert group values must be enumerable |
| Need to push a **user list / data table** | **automation** | alert pushes text only |
| **Same day from 0:00 to now / calendar week** window (including ratios under that window) | **automation** | The alert window model is different |
| Need a **fully custom webhook payload** | **automation** | The alert format is fixed |

---

## Special Notes on Group Alerts

When a customer says "monitor every channel", you must first investigate:

1. How many group values are there right now? (Investigate with SQL, e.g. `SELECT DISTINCT channel FROM ...`)
2. Tell the customer the current value list and the implementation approach:
   - "I detected 8 channels at present: app store, Huawei App Store, Tencent MyApp..."
   - "A separate rule will be created for each channel, 8 rules in total, sharing 1 alert task"
   - "**Note**: if a 9th channel is added tomorrow, alert will not monitor it automatically; the rule must be added manually"
3. Create only after the customer confirms

If group values > 100, or the customer explicitly requires "automatically cover new values", route to automation.

---

## JSON Structure for Creating an alert

### Common Skeleton (shared by all alerts)

```json
{
  "alert_name": "<task name, at most 80 characters>",
  "alert_event_config": { ... fill in per the config examples below ... },
  "group_by": [],
  "alert_calc_freq": "day",
  "alert_hour_intervals": [
    {"start_hour":"0","end_hour":"24","week_day":"1"},
    {"start_hour":"0","end_hour":"24","week_day":"2"},
    {"start_hour":"0","end_hour":"24","week_day":"3"},
    {"start_hour":"0","end_hour":"24","week_day":"4"},
    {"start_hour":"0","end_hour":"24","week_day":"5"},
    {"start_hour":"0","end_hour":"24","week_day":"6"},
    {"start_hour":"0","end_hour":"24","week_day":"7"}
  ],
  "alert_rules": [ ... fill in per the config examples below ... ],
  "alert_push_target": {
    "feishu_web_hooks": ["https://open.feishu.cn/open-apis/bot/v2/hook/xxx"]
  },
  "task_zone_offset": 8,
  "data_zone_offset": 8,
  "delay": 0
}
```

**Skeleton notes**:
- `alert_hour_intervals`: for full-week monitoring use the 7 entries above; for weekdays only, delete the two entries for week_day 6/7. `week_day` takes values `1`~`7`, where `1` = Monday ... `7` = Sunday (note this differs from the `day_of_week` convention in rule-schema, where `0` = Sunday)
- `task_zone_offset` / `data_zone_offset`: fill in per the classification rules in "How to Fill Time Zone Fields" above (for a project with time zone offset disabled, `data_zone_offset` must be `99`; the `8/8` in the skeleton applies only to a project with time zone offset enabled and a settlement time zone of UTC+8)
- The config examples below give only the two differing parts, `alert_event_config` and `alert_rules`; copy the remaining fields from the skeleton

### config Example 1: Single-Metric Fixed-Value Alert (DAU below 1000)

`alert_event_config`:
```json
{
  "event_name": "login",
  "event_type": "event",
  "type": 0,
  "analysis": "A101",
  "relation": "1",
  "filts": []
}
```

`alert_rules`:
```json
[
  {
    "alert_standard": {
      "alert_result_type": "number",
      "calcu_value": 1000,
      "alert_compare_moment_type": "constant",
      "alert_compare_type": "less"
    },
    "groups": []
  }
]
```

### config Example 2: Group Alert (Paying Users per channel > 1000)

`alert_event_config`: same as config Example 1 (with the event changed to payment).

`group_by` (replacing the empty array in the skeleton):
```json
[
  {
    "column_name": "channel",
    "column_desc": "Source Channel",
    "column_type": "varchar",
    "select_type": "string",
    "table_type": "0"
  }
]
```

`alert_rules` (one rule per group value):
```json
[
  {"alert_standard":{"alert_result_type":"number","calcu_value":1000,"alert_compare_moment_type":"constant","alert_compare_type":"more"},"groups":["app store"]},
  {"alert_standard":{"alert_result_type":"number","calcu_value":1000,"alert_compare_moment_type":"constant","alert_compare_type":"more"},"groups":["Huawei App Store"]}
]
```

### config Example 2b: Group Property-Sum Alert (Total payment amount per channel < 10000)

How to write config Example 2 when the monitored object is changed to a property sum (A103 + quota):

`alert_event_config` (note that the `quota` field binds the summed property, see "How to write the property name for property aggregation" above):
```json
{
  "event_name": "payment",
  "event_type": "event",
  "type": 0,
  "analysis": "A103",
  "quota": "pay_amount",
  "relation": "1",
  "filts": []
}
```

`group_by`: same as config Example 2 (with the grouping property changed to a business property such as channel).

`alert_rules` (one per group, with the threshold changed to the amount):
```json
[
  {"alert_standard":{"alert_result_type":"number","calcu_value":10000,"alert_compare_moment_type":"constant","alert_compare_type":"less"},"groups":["app store"]},
  {"alert_standard":{"alert_result_type":"number","calcu_value":10000,"alert_compare_moment_type":"constant","alert_compare_type":"less"},"groups":["Huawei App Store"]}
]
```

### config Example 3: Formula Metric (Payment Success Rate = successful users / initiated users, alert below 95%)

The structure is consistent with the production sample actually measured (`custom_event` is written as `numerator event.aggregation code/denominator event.aggregation code`, `event_type` is joined with commas per operand, and `quota_entities` has one entry per operand). **Omit the `format` field when creating via API** (the API whitelist does not accept it), in which case write the threshold as `number` + percentage/100 (see "Threshold unit for ratio metrics" above); the `format: "percent"` in the config below is the verbatim structure of the platform UI sample and is provided for reference and comparison only:
**`quota_entities[].ta_id_measure.entity_id` is a project-specific user entity ID** (the example value `4` comes from one specific project) and must be replaced according to the user entity metadata of the target project - copying it into another project binds to the wrong entity, and no error is raised at creation time; it only surfaces during the first calculation round. Likewise, `column_name` must be aligned with the user ID field of the target project.

`alert_event_config`:
```json
{
  "event_name": "Payment Success Rate",
  "event_type": "event,event",
  "type": 1,
  "analysis": "",
  "relation": "1",
  "filts": [],
  "custom_event": "payment_success.A101/payment_init.A101",
  "quota_entities": [
    {
      "ta_id_measure": {
        "entity_type": "PRIMARY",
        "custom": false,
        "is_preset": true,
        "csv_size": 0,
        "table_type": "0",
        "has_deleted": false,
        "entity_name": "User",
        "rule_type": 0,
        "has_hide": false,
        "select_type": "number",
        "column_desc": "User ID",
        "column_name": "#user_id",
        "has_upper_case": false,
        "primary": true,
        "primary_bigint_type": false,
        "entity_id": 4
      },
      "index": 0
    },
    {
      "ta_id_measure": {
        "entity_type": "PRIMARY",
        "custom": false,
        "is_preset": true,
        "csv_size": 0,
        "table_type": "0",
        "has_deleted": false,
        "entity_name": "User",
        "rule_type": 0,
        "has_hide": false,
        "select_type": "number",
        "column_desc": "User ID",
        "column_name": "#user_id",
        "has_upper_case": false,
        "primary": true,
        "primary_bigint_type": false,
        "entity_id": 4
      },
      "index": 1
    }
  ],
  "formulation": {
    "formulation_deps": [
      {
        "quota": {"quota_desc": "Triggering User Count", "quota_name": "A101"},
        "property": {"has_deleted": false, "rule_type": 0, "is_preset": false, "has_hide": false, "csv_size": 0, "has_upper_case": false},
        "event": {"event_desc": "Payment Success", "event_name": "payment_success", "event_type": "event", "real_available": false}
      },
      {
        "quota": {"quota_desc": "Triggering User Count", "quota_name": "A101"},
        "property": {"has_deleted": false, "rule_type": 0, "is_preset": false, "has_hide": false, "csv_size": 0, "has_upper_case": false},
        "event": {"event_desc": "Payment Initiated", "event_name": "payment_init", "event_type": "event", "real_available": false}
      }
    ]
  }
}
```

`alert_rules` (write per the "Threshold unit for ratio metrics" rule above. A formula alert created via API has no `format` field, so use `number` + percentage/100; the `percent` + 0-100 form below is used only when the config carries `format: percent`):
```json
[
  {
    "alert_standard": {
      "alert_result_type": "number",
      "calcu_value": 0.95,
      "alert_compare_moment_type": "constant",
      "alert_compare_type": "less"
    },
    "groups": []
  }
]
```

(The combination of `format: percent` + `alert_result_type: "percent"` + `calcu_value: 95` is available only when creating via the platform UI - the API whitelist does not accept the `format` field.)

**Formula quick reference** (all verified against production samples; the `format` column is the display format carried by the sample itself, and that field is not passed when creating via API):

| Requirement | custom_event | event_type | format |
|------|-------------|------------|--------|
| Users of event A / Users of event B | `payment.A101/login.A101` | `event,event` | `percent` |
| Ratio of filtered property sums | `payment.#vp@currency_type__pay_amount__USD.A103/payment.pay_amount.A103` | `event,event` | `float` |
| Formula applied to a single event | `login.A100/100` | `event` | `float` |
| Single-event aggregation | `anyEvent.A100` | `event` | `integer` |

**Recommendation before creation**: first run `ae-cli analysis alert list -p <id> --format json` to inspect existing formula alert samples in the project, and construct against those fields to reduce the chance of structural errors.

**Caliber feasibility check**: before constructing the JSON, verify each event and property used in the requirement against the project (using metadata commands or SQL probes, e.g. `SELECT DISTINCT` to inspect property values). If the requirement mentions a property that does not exist in the project (e.g. the payment event has no status property), **DO NOT change the caliber on your own** - tell the user "there is no X property under this event; the existing properties are a/b/c; should we substitute a, or switch to event Y", and construct only after the user confirms.

---

## alert Execution Status Fields (for post-creation verification)

The response body of `ae-cli analysis alert get -p <pid> --alert-id <id>` contains a set of execution status fields. After creation, the read-back verification must do more than compare the definition: it must also wait for the first calculation round and check the execution status:

| Field | Meaning | Values |
|------|------|------|
| `recent_alert_execute_status` | Result of the most recent calculation round | `alert_none`=calculation succeeded but not triggered / `alert_trigger`=calculation succeeded and triggered / `alert_fail`=calculation failed |
| `fail_msg` | Failure reason (non-empty when `alert_fail`) | e.g. "Time zone for the current project is disabled; time zone configuration is not supported; switched to statistics based on local time" |
| `current_value` | Metric value calculated in the most recent round | numeric value or null |
| `task_status` | Task start/stop status | running / stopped |

**Timing points**: The platform runs the first calculation round for a newly created alert **within 1~5 minutes** (without waiting for the scheduled time, and this holds for daily tasks too). At the instant of creation, `recent_alert_execute_status` is clean, and configuration errors (such as an illegal time zone field) only surface as `alert_fail` after the first calculation round - therefore "creation succeeded" cannot be used as the basis for delivery; you must check the execution status once after the first calculation round.
