# Alert Rule Field Reference

The alert rule (alert_rule.json) is the final deliverable of the configuration phase and the sole input of the runtime phase.

**ID Conventions (global rules; metric / sql_template / result_columns are all governed by them)**:

- **ID System**: `#user_id` (the user unique identifier mandated by the TE ID system), `#account_id` (the login account ID; the customer's business ID is often reported here), `#distinct_id` (the visitor ID), `#device_id` (the device ID); the customer's business ID may also live on custom properties (e.g. `account_id`, `account`, `role_id`, etc.)
- **Which ID to use for calculation**: When the customer explicitly specifies an ID field (e.g. "calculate by `#account_id`", "deduplicate by role_id"), compute based on the specified property (deduplicated count, grouping, and joins all use it as the source of truth). When the customer has not specified one, confirm first: "Users are calculated by `#user_id`; if you have a designated ID field, please list it." Until confirmed, default to `#user_id`
- **Which IDs to output in lists**: For lists output on a per-user basis (the "users" in the customer's wording), both `#user_id` and `#account_id` columns must be output. `#account_id` tolerates nulls (unlogged-in data only has a visitor ID) — `#user_id` is the system-internal numeric ID that the customer does not recognize; `#account_id` is the login ID by which the customer identifies people. When monitoring other entities such as devices, channels, or orders, both calculation and lists use that entity's ID (devices use `#device_id`; business entities use the corresponding property). Do NOT apply the `#user_id` + `#account_id` dual-ID pattern. If the customer needs to identify people, provide a separate entity-to-user mapping (one device may be associated with multiple users)

---

## Top-Level Fields

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `task_name` | Yes | string | Task name | Payment Success Rate Monitor |
| `note` | No | string | Remarks | Dedicated to major promotion periods |
| `project_id` | Yes | number | Project ID | 2 |
| `project_name` | Yes | string | Project name (for verification) | Card Game DEMO |
| `metric` | Yes | object | Metric definition under monitoring | See below |
| `window` | Yes | object | Time window definition | See below |
| `trigger` | Yes | object | Trigger condition definition | See below |
| `schedule` | Yes | object | Schedule definition | See below |
| `notify` | Yes | object | Notification definition | See below |
| `timezone` | Yes | object | Timezone information (required for all projects; see below) | See below |
| `env` | No | object | Environment information (for record only; scripts do not depend on it to run) | See below |
| `created_at` | No | string | Creation time (for archival; scripts do not read it) | 2026-08-19T10:00:00+08:00 |
| `sql_template` | Yes | string | SQL template (with time placeholders) | See below |

**`sql_template` notes**:
- During the configuration phase, based on the `metric` definition, select a template from [`sql-templates.md`](sql-templates.md) and fill in business parameters (event names, property names, filter conditions, etc.)
- The required time placeholders must be included, chosen by window type (see sql-templates.md for details): `{{date}}` (templates 3/5/10 and single-day templates), `{{window_start}}` / `{{window_end}}` (hourly and today-to-now window filters)
- Conditional placeholders: `{{week_start}}` / `{{week_end}}` (natural_week windows), `{{base_date}}` (retention type)
- Under a natural_week window, `{{date}}` renders as the **Monday** of the previous natural week — week-granularity filtering must use `{{week_start}}` / `{{week_end}}`, not `{{date}}`
- At runtime, `metric_alert.py` replaces the time placeholders and then executes; any unreplaced placeholder left in the SQL causes an immediate error

**Time Placeholder Semantics**:

| Placeholder | Meaning | Example Value |
|--------|------|--------|
| `{{date}}` | Target date (the day the window belongs to) | 2026-08-19 |
| `{{window_start}}` | Window start time | 2026-08-19 00:00:00 |
| `{{window_end}}` | Window end time (exclusive) | 2026-08-19 14:00:00 |
| `{{week_start}}` | Natural week start date (Monday) | 2026-08-10 |
| `{{week_end}}` | Natural week end date (Sunday, inclusive) | 2026-08-16 |
| `{{base_date}}` | Retention base date = date - retention_days | 2026-08-18 |
| `{{current_hour}}` | Number of complete hours covered by the window (today_to_now window; 24 when falling back to the previous full day at midnight); for other windows, the hour of the window end time (two-digit `HH` string; see "Semantics of `{{current_hour}}`" in [`sql-templates.md`](sql-templates.md)) | 14 |

---

## metric Sub-Fields

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `type` | Yes | string | Monitor type; **the value must be one of the seven listed above** (the script validates against a whitelist; unlisted values cause an immediate error) | `single` / `ratio` / `funnel` / `retention` / `group` / `row_filter` / `custom` |
| `event_name` | Conditional | string | Event name (required for single / group) | payment |
| `aggregate` | Conditional | string | Aggregation method (required for single / group) | `SUM` / `COUNT` / `COUNT_DISTINCT` / `AVG` |
| `metric_prop` | Conditional | string | Property name (required for SUM / AVG / COUNT_DISTINCT; optional for COUNT) | amount |
| `filters` | No | string | Event filter condition fragment, starting with `AND` | `AND "channel" = 'AppStore'` |

**How `filters` is applied**: Templates 1-5 and 10 reserve a `{{filters}}` insertion point at the tail of the WHERE clause. When `filters` is non-empty, replace `{{filters}}` in the template with its value (a complete condition starting with `AND`); when empty, delete the entire line containing the `{{filters}}` placeholder. Replacement must be completed before writing into `sql_template`.

### type = ratio (Ratio Metric)

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `numerator_event` | Yes | string | Numerator event | payment_success |
| `denominator_event` | Yes | string | Denominator event | payment_init |
| `zero_denominator` | No | string | Handling when the denominator is 0 | `skip` / `zero` / `hundred`; default `skip` |

**`zero_denominator` strategies** (when the denominator is 0, the SQL returns NULL):
- `skip`: Do not trigger an alert (default) — suitable for "don't bother me when there's no data" scenarios
- `zero`: Treat as 0 and continue with threshold evaluation — suitable for "a payment_init count of 0 is itself anomalous" scenarios (alert with an `lt` threshold)
- `hundred`: Treat as 1.0 (the ratio is on a 0~1 decimal scale, where 1.0 equals 100%) and continue with threshold evaluation — suitable for "a zero denominator is treated as a full value" scenarios (e.g. success-rate metrics configured with `lt` alerts). The threshold uses the same scale as the ratio: 0.95 means 95% (formula-metric thresholds on the alert path use the same scale conversion; see "Threshold Unit for Ratio Metrics" in [`alert-route.md`](alert-route.md))

This field only takes effect when `type = ratio`. For `type = custom` where the SQL computes the ratio itself, this protection does not apply — you must use `NULLIF(denominator, 0)` in the SQL yourself, and accept the default semantics of "denominator is 0 → metric_value is NULL → no trigger" (to make NULL also trigger, use COALESCE in the SQL to fall back to a concrete value).

### type = funnel (Funnel Metric)

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `steps` | Yes | array | List of step events | `["register", "verify", "pay"]` |
| `strict_order` | No | bool | Whether strict ordering is required | true |

**Note**: `steps` / `strict_order` only serve template selection during the configuration phase — `strict_order=true` uses template 6 (strict order), `false` uses template 7 (loose order); the generated SQL bakes the ordering semantics in. The runtime script does not read these two fields, so changing them does not alter execution behavior (to switch between strict and loose ordering, the SQL must be regenerated).

**Note**: `metric_value` is the overall conversion rate (users completing all steps / users completing the first step). To monitor intermediate steps, switch to the `custom` type and write your own SQL. When the denominator (users completing the first step) is 0, the SQL returns NULL; `zero_denominator` does not apply — funnel templates do not have this field, and NULL means no trigger.

### type = retention (Retention Metric)

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `new_user_event` | Yes | string | New user event | register |
| `return_event` | No | string | Return event (empty = any event) | login |
| `retention_days` | Yes | number | N-day retention | 1 |

**Note**: When the denominator (new users on base_date) is 0, the SQL returns NULL; `zero_denominator` does not apply — retention templates do not have this field, and NULL means no trigger.

**Semantics of `base_date`**:
- `base_date` is the "new user date"; retention rate = the proportion of base_date new users who return on base_date + retention_days
- Computed automatically at runtime: `base_date = {{date}} - retention_days`; the calculation reads only `metric.retention_days`
- When the window is `natural_day`, `{{date}}` is yesterday, so base_date is the day before yesterday
- **Dual sources of truth must agree**: The lookback days in the SQL (e.g. the `INTERVAL '1' DAY` in template 9) must equal `metric.retention_days` — the script computes base_date from `metric.retention_days`, while the SQL filters returns by its own literal; any mismatch causes the numerator and denominator to use inconsistent definitions. The script hard-validates the `INTERVAL '<n>' DAY` boundary anchored to `base_date` in the rendered SQL: if `retention_days` does not appear in the matched literal, it errors out directly rather than self-checking or silently computing a wrong result. The validation is "contains" semantics — it only blocks drift of `retention_days` itself and does not verbatim-validate the ±1 boundary of partition expansion; custom retention SQL that does not contain this pattern, or SQL that does not use `{{base_date}}`, skips validation and must be manually reviewed

### type = group (Group Monitoring)

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `group_dimension` | Yes | string | Grouping property name | channel |

**Notes**:
- The SQL uses template 10 and returns two columns: `group_key`, `metric_value`
- Each group is evaluated independently; an alert fires as soon as any group matches. The message includes details of the matched groups. For period-over-period monitoring (`pct_change_*`), the details additionally include each group's baseline value (the `baseline_value` column) to facilitate review of deviation magnitude
- Baselines (`compare_to` != `fixed`) are computed per group: each group is compared against **its own** baseline, without mixing in data from other groups. The baseline query is structurally identical to the main query — the script renders the time placeholders onto the offset window and returns values for all groups, from which each group's own baseline is taken. Groups with missing or non-numeric baselines are automatically skipped (counted in `miss_groups`) and do not block evaluation of other groups. When `operator` is `gt` / `lt` / `eq`, it is an absolute threshold evaluation, consistent with the single-value path, and no baseline is queried
- **Group count gate**: The number of baseline queries equals the number of baseline windows (history_avg over 7 days = 7 queries), independent of the group count, but the number of rows returned by the main query is truncated by the script's `PREVIEW_ROWS` = 1000 — groups beyond the cap will not be monitored. Before configuring, probe the number of groups (`SELECT COUNT(DISTINCT ...)`)**: **> 800 requires user confirmation** (explain the truncation risk and confirm whether to narrow the grouping or shrink the window); **> 1000 is a hard rejection** (beyond monitoring capability; recommend switching to a fixed-threshold monitor on the total, or splitting into multiple rules by business line)
- **Zero-data groups produce no rows**: GROUP BY only returns groups that have data within the window. Zero-data groups do not appear in the query result and their evaluation is vacuous ("below threshold" alerts do not fire for zero-data groups). When "zero-data groups should be treated as 0 and participate in evaluation" is required, it must be confirmed with the user during configuration, and a full set of groups must first be constructed (e.g. DISTINCT values seen in the last N days) followed by a LEFT JOIN to backfill zeros — the trade-off is that values absent for N consecutive days drop out of monitoring, which must be disclosed as well

### type = row_filter (Abnormal User / List Monitoring)

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `result_columns` | Yes | array | List of result column names; see "ID Conventions" below | ["user_id", "account_id", "last_active_time"] |

**Notes**:
- The SQL uses template 12 and returns row-level detail (one user / order etc. per row), not aggregated values
- **Only `compare_to = fixed` is supported** (row counts have no baseline in the "previous period" sense). Use `fixed` + `gt` + `0` for "alert when any row exists", and `fixed` + `gt` + `10` for "alert only when more than 10 rows". `operator` **must be `gt`** — for row counts only "exceeds threshold" is meaningful; `eq` has limited utility, and `lt` would treat "empty list" as an alert. The script errors out directly on the latter two instead of silently computing with the wrong semantics
- Push content: a formatted list (`result_columns` determines which columns are displayed)

**ID Conventions**: Follow the global "ID Conventions" rules at the top of this file — user lists output dual IDs (`user_id` + `account_id`); lists of other entities use the entity ID and do not apply the user dual-ID pattern.

### type = custom (Custom SQL)

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `result_column` | Yes | string | Result column name (the SQL returns the numeric value of this column as the current value) | metric_value |

**Note**: Custom SQL is written directly into the `sql_template` field and must return a **single row and single column numeric value**. When the result column name is not `metric_value`, `metric.result_column` must be configured to specify the actual column name, otherwise value extraction fails.

---

## window Sub-Fields

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `type` | Yes | string | Window type | `natural_hour` / `natural_day` / `today_to_now` / `natural_week` |

**Window Type Descriptions**:

| type | Description | Example (current time 14:35) |
|------|------|------------------------|
| `natural_hour` | Previous complete hour | 13:00 ~ 14:00 |
| `natural_day` | All of yesterday | 2026-08-18 00:00 ~ 24:00 |
| `today_to_now` | From 00:00 today to the previous full hour | 2026-08-19 00:00 ~ 14:00 |
| `natural_week` | Previous natural week | 2026-08-10 ~ 2026-08-16 |

**Notes**:
- The right endpoint of `today_to_now` **always snaps to a full hour** (in the example above, a run at 14:35 takes 14:00, not 14:35), ensuring reproducible results across multiple runs within the same day
- When `today_to_now` runs during 00:00~00:59 (the current day has no complete hour yet), the window **falls back to the entire previous day** (2026-08-18 00:00 ~ 2026-08-19 00:00, with `{{date}}` = the previous day) — this both lets the first daily run produce a result as usual, and covers the 23:00~24:00 hour that any full-hour run would skip
- Regardless of window type, the schedule must leave a buffer for data ingestion: for `minute` use `05` or `10` (not 0), otherwise the data at the full-hour right endpoint of the window may not have landed yet. The only allowed values are multiples of 5 — `05`, `10`, `15`...`55`; the UI does not offer values like `06`, `07`

**Recommended Window x Schedule Frequency Combinations** (automation path):

| Window Type | Recommended freq | Schedule Point | Notes |
|----------|-----------|--------|------|
| `natural_hour` | `hourly` | `minute: 05` | Previous complete hour vs. previous hour / baseline |
| `natural_day` | `daily` | `time: 09:00` (set per business hours) | All of yesterday |
| `natural_week` | `weekly` | `time: 09:00` + `day_of_week: 1` | Previous natural week |
| `today_to_now` | `hourly` | `minute: 05` | Cumulative today; the 00:05 run counts the entire previous day, while runs at other times count from 00:00 today to the previous full hour |

Other combinations are not forbidden, but the semantics must be confirmed case by case: when the window span does not match the schedule frequency (e.g. `natural_hour` with `daily`), only the single complete hour at the scheduled moment is monitored, leaving the other 23 hours of the day unwatched.

---

## trigger Sub-Fields

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `compare_to` | Yes | string | Comparison baseline; **the script errors out directly if missing** (it does not default to fixed). When `operator` is `gt` / `lt` / `eq`, use `fixed` (absolute threshold evaluation, no baseline query); for `pct_change_*`, use a dynamic baseline | `fixed` / `previous_period` / `same_time_yesterday` / `same_time_last_week` / `history_avg` / `history_max` |
| `operator` | Yes | string | Comparison operator | `gt` / `lt` / `eq` / `pct_change_gt` / `pct_change_lt` |
| `threshold` | Yes | number | Threshold (semantics below) | 0.3 |
| `history_days` | Conditional | number | Number of history days (used when compare_to=history_avg/max; **explicitly filling it in is recommended**; the script defaults to 7 days when omitted). **The unit is always "days"** and does not change with window type: under a natural_week window, day-by-day fallback still lands within the same week (the script errors out directly; see baseline limitations below); history_days=7 means "past 7 days", not "past 7 weeks" | 7 |

**`threshold` Semantics** (constant, independent of compare_to):

| operator Usage | threshold Meaning | Example |
|--------------|---------------|------|
| `gt` / `lt` / `eq` | **Absolute threshold**; the current value is compared against it directly | threshold=0.3 means comparing the current value against 0.3 |
| `pct_change_gt` / `pct_change_lt` | **Rate-of-change threshold** | threshold=0.3 means a 30% deviation from baseline |

**Evaluation Rules**:
- `gt`: current value > threshold; `lt`: current value < threshold; `eq`: current value = threshold — independent of compare_to; **the script skips the baseline query** (the `baseline_value` in run_result is null). Example: `compare_to=history_avg` + `operator=lt` + `threshold=0.3` means "current value < 0.3", **not** "30% below the historical average"
- `pct_change_gt`: (current value - baseline) / |baseline| > threshold; `pct_change_lt`: < -threshold. No trigger when the baseline is 0 or the query returns None. Baseline query failure handling (consistent for single-value and group monitoring): `previous_period` / `same_time_*` fail on a single query and exit with an error (exit code 1); `history_*` skips the failed window automatically, and if all windows fail it is a systemic failure and exits with an error (it does not silently evaluate as no-trigger). Under group monitoring, a failure of one baseline window in history affects all groups in that window (that window is skipped); a missing baseline for a single group (that group has no data in the baseline window) only skips that group

**`compare_to` Baseline Windows**:

| compare_to | Baseline Window |
|------------|---------|
| `fixed` | No baseline query; threshold is the reference value |
| `previous_period` | Window shifted back one period: natural_hour = the hour before last, natural_day = the day before yesterday, natural_week = the week before last, today_to_now = yesterday 00:00 to the same time (equivalent to same_time_yesterday under a natural_day window) |
| `same_time_yesterday` | Same-shaped window shifted back 1 day (e.g. natural_hour's same hour yesterday = yesterday 13:00~14:00; today_to_now's same time yesterday = yesterday 00:00 to the same full hour yesterday) |
| `same_time_last_week` | Same-shaped window shifted back 7 days |
| `history_avg` | Average of same-shaped windows day by day over the past `history_days` days; a failed query for a given day is automatically skipped; failure of all days is a systemic failure and exits with an error. Empty-data days for SUM/AVG metrics are counted as 0 in the average (the template's `COALESCE` makes an empty window return 0 instead of NULL; see "Empty Window Semantics" in [`references/sql-templates.md`](sql-templates.md)) |
| `history_max` | Same as above, taking the maximum |

**Baseline Limitations for natural_week Windows**: `same_time_yesterday` / `same_time_last_week` / `history_avg` / `history_max` all fall back by **days**, which under a natural_week window still lands within the same natural week (baseline = current value, period-over-period change is always 0) — the script detects this combination and errors out directly. For natural week monitoring, period-over-period comparisons must use `previous_period` (shift back a full week).

**operator Notes**:

| operator | Evaluation | Applicable compare_to |
|----------|------|-----------------|
| `gt` | current value > threshold | All |
| `lt` | current value < threshold | All |
| `eq` | current value = threshold | All (recommended only for integers; eq on floating-point metrics may never hit) |
| `pct_change_gt` | (current - baseline) / \|baseline\| > threshold | Non-fixed (the script errors when paired with fixed) |
| `pct_change_lt` | (current - baseline) / \|baseline\| < -threshold | Non-fixed (the script errors when paired with fixed) |

---

## schedule Sub-Fields

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `freq` | Yes | string | Frequency | `hourly` / `daily` / `weekly` / `monthly` |
| `minute` | Conditional | number | Minute within the hour (required when freq=hourly, 0-59) | 5 |
| `time` | Conditional | string | Time of day (required when freq=daily/weekly/monthly, HH:MM) | 09:00 |
| `day_of_week` | Conditional | number | Day of week (required when freq=weekly, **0-6, 0=Sunday**, consistent with CLI `--weekday`) | 1 |
| `day_of_month` | Conditional | number | Day of month (required when freq=monthly, 1-28, avoiding the issue of variable month-end lengths) | 1 |

**Note**: The schedule time is interpreted in the server timezone, not the settlement timezone. For conversion methods and the paired dual-timezone echo phrasing, see "Schedule Time Conversion" in [`timezone-guide.md`](timezone-guide.md).

---

## notify Sub-Fields

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `channel` | Yes | string | Notification channel | `wecom` / `dingtalk` / `feishu` / `custom_webhook` |
| `webhook_url` | Yes | string | Webhook URL | https://qyapi.weixin.qq.com/... |
| `message_template` | No | string | Custom message template | See below |

**Note**: The automation path only supports webhook-style channels (`custom_webhook` is the generic exit: Slack and similar incoming-webhook channels all connect through it).

The request body of `custom_webhook` is fixed as `{"text": message}` and only fits endpoints that accept this format (Slack incoming webhooks do); endpoints like Discord / Teams that require a proprietary payload structure are incompatible. For every channel, HTTP 2xx is required; non-2xx is a failure (exit code 3, with the error message including the status code and a response body summary). Deterministic failures are not retried; only network-layer errors such as connection failures and timeouts go through retries (3 attempts with exponential backoff).

Official channels (`wecom` / `dingtalk` / `feishu`) additionally judge the business code in the response body (`errcode` / `code` must be 0 to count as success; a non-JSON response body is treated as failure): for DingTalk bot security settings, choose "Custom Keywords" (the message must contain the keyword) rather than "Sign" — the script sends without a signature, and a signed bot returns `310000` failure.

**message_template Variables**:

| Variable | Description | Applicable Scenarios |
|------|------|---------|
| `{{task_name}}` | Task name | All |
| `{{current_value}}` | Current value | Single-value metrics (metric alert / ratio / funnel / retention / custom) |
| `{{baseline_value}}` | Baseline value | Single-value metrics (metric alert / ratio / funnel / retention / custom) |
| `{{window}}` | Time window | All |
| `{{project_name}}` | Project name | All |
| `{{row_count}}` | Matched row count (row_filter) / matched group count (group) | List monitoring, group monitoring |
| `{{total_groups}}` | Total number of groups returned | Group monitoring |
| `{{miss_groups}}` | Number of skipped groups (returned groups with missing baseline / empty value / dirty data; groups with zero events in the window or absent from the query result are not counted) | Group monitoring |
| `{{user_list}}` | User list (formatted) | List monitoring |
| `{{data_table}}` | Data table (formatted, matched group details) | Group monitoring |

Variables other than the 10 above appearing in the template, or variables not applicable to the `metric.type` (e.g. `{{row_count}}` in a single-value metric template), cause an immediate error at the trial-run stage; blank fields will not be pushed.

**Push Format (IM webhook text messages)**: Text messages from WeCom / DingTalk / Feishu bots **do not render Markdown** — the pipe table of `{{data_table}}` and the list markers of `{{user_list}}` are displayed as-is. The per-line "field=value, field=value" form of `{{user_list}}` is reasonably readable; the table-line form of `{{data_table}}` is poorly readable. When the customer has requirements on the push format (e.g. Feishu cards, rendered tables), first explain that the current push is plain text and confirm acceptability before creating.

---

## timezone Sub-Fields (Required for All Projects)

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `project_tz_enabled` | Yes | bool | Whether the project has multi-timezone enabled (taken from the project info's `time_zone_enabled`) | true |
| `settle_timezone` | Yes | number | Settlement timezone (hour offset). For multi-timezone projects, confirmed by the user; for single-timezone projects, taken from the project info's `default_time_zone_offset`. **The script computes the window date based on this field; when unfilled it defaults to UTC+8** — a non-UTC+8 project with this field missing will compute the wrong window date and the SQL will aggregate the wrong day | 7 |
| `settle_timezone_source` | Yes | string | Source | `user_confirmed` / `default_fallback` |
| `zone_offset_column` | Conditional | string | Timezone offset column name (required for multi-timezone projects; single-timezone projects do not have this column, fill in null) | #zone_offset |
| `schedule_timezone` | Yes | string | Schedule timezone | Asia/Shanghai |
| `schedule_utc_offset` | Yes | number | Schedule UTC offset | 8 |

---

## env Sub-Fields

| Field | Required | Type | Description | Example |
|------|------|------|------|------|
| `ae_cli_version` | No | string | ae-cli version at configuration time (for record) | 6.1.5 |
| `ae_cli_path` | No | string | ae-cli path; when unfilled, the script uses `ae-cli` from PATH | /usr/local/bin/ae-cli |

---

## Complete Examples

### Example 1: Metric Alert

```json
{
  "task_name": "Payment Success Rate Monitor",
  "note": "Dedicated to major promotion periods",
  "project_id": 2,
  "project_name": "Card Game DEMO",
  "metric": {
    "type": "ratio",
    "numerator_event": "payment_success",
    "denominator_event": "payment_init",
    "zero_denominator": "skip"
  },
  "window": {
    "type": "today_to_now"
  },
  "trigger": {
    "compare_to": "same_time_yesterday",
    "operator": "pct_change_lt",
    "threshold": 0.3
  },
  "schedule": {
    "freq": "hourly",
    "minute": 5
  },
  "notify": {
    "channel": "wecom",
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
  },
  "timezone": {
    "project_tz_enabled": true,
    "settle_timezone": 8,
    "settle_timezone_source": "user_confirmed",
    "zone_offset_column": "#zone_offset",
    "schedule_timezone": "Asia/Shanghai",
    "schedule_utc_offset": 8
  },
  "env": {
    "ae_cli_version": "6.1.5",
    "ae_cli_path": "/usr/local/bin/ae-cli"
  },
  "created_at": "2026-08-19T10:00:00+08:00",
  "sql_template": "WITH numerator AS (\n  SELECT COUNT(*) AS val\n  FROM (\n    SELECT\n      \"#user_id\",\n      IF(((\"#zone_offset\" IS NOT NULL) AND (\"#zone_offset\" >= -30) AND (\"#zone_offset\" <= 30)), date_add('second', CAST((8 - \"#zone_offset\") * 3600 AS integer), \"#event_time\"), \"#event_time\") AS shifted_time\n    FROM ta.v_event_2\n    WHERE \"$part_event\" = 'payment_success'\n      AND \"$part_date\" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')\n  ) t\n  WHERE date(shifted_time) = date('{{date}}')\n    AND shifted_time >= TIMESTAMP '{{date}} 00:00:00'\n    AND shifted_time < TIMESTAMP '{{window_end}}'\n),\ndenominator AS (\n  SELECT COUNT(*) AS val\n  FROM (\n    SELECT\n      \"#user_id\",\n      IF(((\"#zone_offset\" IS NOT NULL) AND (\"#zone_offset\" >= -30) AND (\"#zone_offset\" <= 30)), date_add('second', CAST((8 - \"#zone_offset\") * 3600 AS integer), \"#event_time\"), \"#event_time\") AS shifted_time\n    FROM ta.v_event_2\n    WHERE \"$part_event\" = 'payment_init'\n      AND \"$part_date\" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')\n  ) t\n  WHERE date(shifted_time) = date('{{date}}')\n    AND shifted_time >= TIMESTAMP '{{date}} 00:00:00'\n    AND shifted_time < TIMESTAMP '{{window_end}}'\n)\nSELECT\n  n.val AS numerator_value,\n  d.val AS denominator_value,\n  CAST(n.val AS DOUBLE) / NULLIF(d.val, 0) AS metric_value\nFROM numerator n, denominator d\nLIMIT 1"
}
```

### Example 2: Abnormal User Monitoring (List Filtering, Template 12 Semantics)

The SQL structure corresponds to the multi-timezone version of template 12 in sql-templates.md: GROUP BY a single ID column + `MAX(account_id)` output, with churn determination and payment determination each using CASE WHEN keyed by event name. Event names / amount fields / thresholds / lookback windows are all demo values; actual configuration must be confirmed item by item with the user before replacement.

```json
{
  "task_name": "High Spender Churn Alert",
  "note": "High Spenders inactive for the past 7 days. Placeholder values are for demonstration only (active event game_start, payment event payment, amount field pay_amount, threshold 1000, lookback 30 days); actual configuration must be confirmed item by item with the user",
  "project_id": 2,
  "project_name": "Card Game DEMO",
  "metric": {
    "type": "row_filter",
    "result_columns": ["user_id", "account_id", "last_active_time", "total_payment"]
  },
  "window": {
    "type": "natural_day"
  },
  "trigger": {
    "compare_to": "fixed",
    "operator": "gt",
    "threshold": 0
  },
  "schedule": {
    "freq": "daily",
    "time": "09:00"
  },
  "notify": {
    "channel": "wecom",
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
    "message_template": "[High Spender Churn Alert] Found {{row_count}} High Spenders inactive for the past 7 days (cumulative payment over 30-day lookback > 1000)\n\n{{user_list}}\n\nPlease follow up promptly."
  },
  "timezone": {
    "project_tz_enabled": true,
    "settle_timezone": 8,
    "settle_timezone_source": "user_confirmed",
    "zone_offset_column": "#zone_offset",
    "schedule_timezone": "Asia/Shanghai",
    "schedule_utc_offset": 8
  },
  "env": {
    "ae_cli_version": "6.1.5",
    "ae_cli_path": "/usr/local/bin/ae-cli"
  },
  "created_at": "2026-08-19T10:00:00+08:00",
  "sql_template": "SELECT\n  user_id,\n  MAX(account_id) AS account_id,\n  MAX(CASE WHEN event_name = 'game_start' THEN shifted_time END) AS last_active_time,\n  SUM(CASE WHEN event_name = 'payment' THEN CAST(amount_prop AS DOUBLE) ELSE 0 END) AS total_payment\nFROM (\n  SELECT\n    \"#user_id\" AS user_id,\n    \"#account_id\" AS account_id,\n    \"pay_amount\" AS amount_prop,\n    \"$part_event\" AS event_name,\n    IF(((\"#zone_offset\" IS NOT NULL) AND (\"#zone_offset\" >= -30) AND (\"#zone_offset\" <= 30)), date_add('second', CAST((8 - \"#zone_offset\") * 3600 AS integer), \"#event_time\"), \"#event_time\") AS shifted_time\n  FROM ta.v_event_2\n  WHERE \"$part_event\" IN ('game_start', 'payment')\n    AND \"$part_date\" >= date_format(date('{{date}}') - INTERVAL '30' DAY, '%Y-%m-%d')\n    AND \"$part_date\" <= date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')\n) t\nGROUP BY user_id\nHAVING (MAX(CASE WHEN event_name = 'game_start' THEN shifted_time END) IS NULL OR MAX(CASE WHEN event_name = 'game_start' THEN shifted_time END) < TIMESTAMP '{{date}} 00:00:00' - INTERVAL '6' DAY)\n  AND SUM(CASE WHEN event_name = 'payment' THEN CAST(amount_prop AS DOUBLE) ELSE 0 END) > 1000\n  AND MAX(shifted_time) < TIMESTAMP '{{date}} 00:00:00' + INTERVAL '1' DAY\nLIMIT 1000"
}
```
