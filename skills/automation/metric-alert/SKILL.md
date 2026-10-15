---
name: metric-alert
version: "2.32"
description: "Create condition-based monitoring tasks that push alert notifications when metrics/clusters/data meet preset conditions. Supports multiple monitoring targets (metric values, cluster lists, data tables, group-by dimensions), multiple judgment logic (value comparison, change-rate comparison, push-on-data, complex rules), and multiple push content types (alert text, user list, data table). Typical scenarios: metric alerting (alert when payment success rate falls below 95%), abnormal user monitoring (High Spender users who have not logged in for 7 consecutive days), data anomaly detection (zero new users today), group monitoring (monitor DAU per channel separately). Trigger words: monitor, alert, warning. Do not trigger for unconditional scheduled push (use the Scheduled Push skill), real-time triggering, or post-hoc anomaly attribution."
metadata:
  requires:
    bins:
      - ae-cli
  verified_cli_version: 6.1.5
---

# Monitoring and Alerts

Create scheduled condition-based monitoring tasks that automatically push alert notifications when the monitored target meets preset conditions.

**Core logic**: compute data -> evaluate condition -> push only when hit

**Difference from [Scheduled Push]**: this skill requires configuring a trigger condition (trigger) and only pushes when the condition is hit; [Scheduled Push] requires no condition and sends on schedule.

**Two implementation approaches**: based on the customer's requirements, this skill selects the most appropriate approach to create the alert:

| Approach | When to use | Description |
|---------|--------|------|
| **TE Metric Alert (alert)** | Requirement is within system capabilities | Directly call `analysis alert create`; native system feature |
| **Agent Automation (automation)** | Requirement exceeds system capability boundaries | Create an Agent + scheduled task that executes custom SQL judgment |

> Before any operation, first read [`references/alert-route.md`](references/alert-route.md) (capability boundaries and routing judgment), [`references/timezone-guide.md`](references/timezone-guide.md), and [`references/sql-templates.md`](references/sql-templates.md).

---

## Supported Monitoring Scenarios

| Scenario Type | Monitoring Target | Judgment Logic | Push Content | Recommended Approach | Persistence Mapping (metric.type / window.type / SQL Template) | Example |
|---------|---------|---------|---------|---------|------|------|
| **Metric Alert** | Single-event metric (count/sum/users/average) | Value comparison | Alert text | alert | `single` / natural_hour, natural_day / Templates 1, 2 | Alert when yesterday's payment amount is below 100k |
| **Group Monitoring** | Metric value (by dimension) | Per-group comparison | Alert text (including hit group list) | alert (group values enumerable) / automation (dynamically added) | `group` / natural_hour, natural_day / Template 10 | Monitor DAU per channel separately |
| **Ratio Monitoring** | Ratio metric (division of two numbers) | Value comparison | Alert text | alert (formula metric) | `ratio` / natural_hour, natural_day / Template 5 | Payment success rate = success/initiated; alert when below 95% |
| **Abnormal User Monitoring** | Cluster list | Push on data | User list | automation | `row_filter` / natural_day / Templates 12, 12b | High Spender users who have not logged in for 7 consecutive days |
| **Data Anomaly Detection** | Metric value (current-day cumulative window) | Value comparison | Alert text | automation | `single` / today_to_now / Template 3 | Zero new users today |
| **Funnel Conversion Monitoring** | Metric value | Value comparison | Alert text | automation | `funnel` / natural_day / Templates 6, 7 | Registration-to-payment Conversion Rate below 20% |
| **Retention Monitoring** | Metric value | Value comparison | Alert text | automation | `retention` / natural_day / Templates 8, 9 | Day-1 Retention Rate below 30% |
| **Custom Monitoring** | Any | Custom | Custom | automation | `custom` / any / Template 11 | User-provided SQL |

**Explicitly out of scope**:
- Real-time triggering (immediate alert on a single large order) -> use real-time computing/CEP
- Alert only after N consecutive periods (debounce) -> not supported in v2
- Intelligent attribution (why it rose/fell) -> analyze in a separate session
- Unconditional scheduled push -> use the [Scheduled Push] skill

---

## Mandatory Principles

1. **Data authenticity**: if no data is found, report an error; DO NOT mock or fake success
2. **Prefer system features**: use TE Metric Alert (alert) whenever possible instead of Agent Automation
3. **SQL only via templates**: all queries on the automation path must use the templates in [`references/sql-templates.md`](references/sql-templates.md)
4. **Pre-write gate**: before creating, modifying, enabling/disabling, or deleting any monitoring asset, fully echo the final configuration to the user and execute only after user confirmation. If the echoed configuration **deviates in any way** from the user's original statement (thresholds, metric definitions, filter conditions, dimensions, channels, ID subjects being replaced or omitted), you MUST point out each difference and explain the reason, then wait for user confirmation; when the requested definition **cannot be implemented** in the project (e.g., a property does not exist), explain the reason and propose an alternative definition, again waiting for confirmation — NEVER substitute on your own
5. **Confirm before routing for group monitoring**: "how to handle group values" (enumerate all current values / monitor only specified ones / automatically cover new values) MUST be clarified **before** routing judgment — the answer directly determines routing (enumerate -> alert, auto-cover new values -> automation); do not route before confirmation; when routing to alert, also inform the user of the current group count and the limitation that "newly added group values will not be monitored automatically"
6. **Environment probing before requirement collection**: check the project's time zone configuration first, then decide whether to ask time-zone-related questions
7. **ID definition**: when the customer says "user", it does not necessarily mean `#user_id` (business IDs are often reported to `#account_id` or custom properties). Compute using the ID field specified by the customer; if unspecified, first confirm "users are counted by `#user_id`; if you have a designated ID field, please list it". For the complete rules on list output and entity monitoring, see "ID Definition" in [`references/rule-schema.md`](references/rule-schema.md)
8. **Multi-timezone natural-day definition**: for multi-timezone projects, whether an event falls within a business natural day MUST be determined by row-by-row conversion using the offset field (`shifted_time`); `$part_date` is only a coarse partition filter, not the natural-day definition. For list/count tasks involving natural-day definitions, before delivery spot-check boundary rows per "Pre-delivery Boundary Check" in [`references/timezone-guide.md`](references/timezone-guide.md), and deliver only after passing

---

## Configuration Phase

### Step 1: Environment Self-check and Project Probing

Before collecting requirements, complete environment probing:

```bash
ae-cli --version                                # Confirm version >= 6.1.5
ae-cli project info list                       # List projects, confirm the project exists
ae-cli project info get -p <id>                # Check time zone configuration
```

**Information that MUST be obtained**:

| Information | Purpose |
|------|------|
| `time_zone_enabled` | Determines whether to ask about "settlement time zone" in Step 2; **on the alert path it also determines how to fill the time zone field** (when time zone offset is not enabled, `data_zone_offset` MUST be `99`; see "Time Zone Field Filling" in [`references/alert-route.md`](references/alert-route.md)) |
| `default_time_zone_offset` | Fallback settlement time zone for multi-timezone projects (**NOT** the source of the alert time zone field value); **for single-timezone projects, the settlement time zone takes this value** (written into the rule's `timezone.settle_timezone`) |
| `time_zone_offset_column` | Time zone offset field name for multi-timezone projects |
| Project name + Project ID | Echo for confirmation |
| Target event exists + has data in the last 7 days | Rule out invalid configurations such as "event name typo" or "no data" |

**`settle_timezone` MUST always be written into alert_rule.json (automation path)**: the script uses it to compute window dates; for multi-timezone projects take the user-confirmed value, for single-timezone projects take `default_time_zone_offset`. If omitted, the script defaults to UTC+8, and non-UTC+8 projects will compute wrong days (see "timezone sub-item" in [`references/rule-schema.md`](references/rule-schema.md)).

**Echo example**: "Will configure the alert on project 'Card Games DEMO' (id=2); the project has multi-timezone enabled, default time zone UTC+8"

### Step 2: Collect Requirements

Ask the user in natural language and fill the answers into the table below. **If required fields are missing, ask follow-up questions; DO NOT guess**.

| Field | Required | Description | Example |
|------|------|------|------|
| Task name | Yes | Monitoring task name | Payment success rate monitoring |
| What to monitor | Yes | Monitoring target + definition | Sum of amount of the payment event / abnormal user filter conditions |
| ID definition | Conditional | Required when monitoring involves "users" or the customer mentions an ID: for complete rules and confirmation wording see "ID Definition" in [`references/rule-schema.md`](references/rule-schema.md) | `#user_id` (default) |
| Monitoring type | Yes | Metric alert / ratio / group / abnormal user monitoring / data anomaly detection / funnel / retention / custom (for the corresponding metric.type see the "Persistence Mapping" column in the scenario table above) | Metric alert |
| Time window | Yes | Hourly / daily / current-day cumulative (up to the last whole hour) / natural week | From 00:00 today to now |
| Judgment condition | Yes | Compare with what + how to judge | Alert if 30% lower than the same time yesterday / push whenever abnormal users exist |
| Check frequency | Yes | Hourly / daily / weekly / monthly | Hourly |
| Notification target | Yes | WeCom / DingTalk / Feishu / custom webhook (for Slack use custom_webhook with an incoming webhook). When the user only gives a group name without an address, prompt how to obtain it: WeCom group bot webhook = group settings -> add group bot -> copy the Webhook address (same for DingTalk/Feishu; add a bot in group settings to obtain it) | https://qyapi.weixin.qq.com/... |
| Push content | Conditional | Alert text / user list / data table (required for abnormal user monitoring) | User list |
| Remarks | No | Task description | For promotion period only |

**Channel notes** (determine whether pushes can actually be delivered):
- For **DingTalk bots**, select "Custom Keywords" in security settings and ensure the message template contains that keyword (the script sends without a signature; signature mode returns `310000` failure)
- The request body of **custom_webhook** is fixed as `{"text": message}` and only fits endpoints that accept this format (Slack incoming webhook works; Discord / Teams do not)

**Conditional follow-up questions** (based on the probing results from Step 1):

| Condition | Follow-up Question |
|------|---------|
| `time_zone_enabled=true` | "Which settlement time zone should be used? Default is the project time zone UTC+X" |
| `time_zone_enabled=false` | Do not ask time-zone-related questions (to avoid information noise); `settle_timezone` directly takes the project's `default_time_zone_offset` |
| Monitoring type = metric alert/group AND aggregation = SUM/AVG | "When there is zero data in the window (no events or data not yet ingested), it is counted as 0, which will trigger 'below threshold' alerts; confirm whether zero-data days should be treated as 0 (default: yes)" |
| Monitoring type = group monitoring | "Group by which property?" + "How to handle group values? Enumerate all current values / monitor only specified ones / automatically cover new values" |
| Monitoring involves "users" but the customer has not specified an ID field | "Users are counted by `#user_id`; if you have a designated ID field (such as `#account_id`, role_id, or other business IDs), please list it" (for complete ID definition rules see "ID Definition" in [`references/rule-schema.md`](references/rule-schema.md)) |
| Monitoring target is another entity such as device/channel/order | "Which property does the entity ID correspond to?" (for complete ID definition rules see "ID Definition" in [`references/rule-schema.md`](references/rule-schema.md)) |
| Monitoring type = retention monitoring | "Which return-visit definition: return on **any day** within N days after registration (general default), or return **on day N exactly**?" (the two definitions produce significantly different results; see the selection rationale for Templates 8/9 in [`references/sql-templates.md`](references/sql-templates.md)) |
| Monitoring type = retention monitoring AND the return window includes "today" | "When the right end of the return window is today, today's data is not yet complete (e.g., at 10:30 only data up to 10:30 is counted) — should the comparison baseline be shifted back by one day as a whole (using a fully complete day), or should the schedule be moved to after 00:30 the next day?" (if unconfirmed, default to shifting the baseline back to avoid reading truncated values every day) |

### Step 3: Routing Judgment

Based on requirement characteristics, decide whether to use **TE Metric Alert (alert)** or **Agent Automation (automation)**. For the complete judgment table (including the rationale for each route), see "Routing Judgment Table" in [`references/alert-route.md`](references/alert-route.md).

**Quick reference**:

| Requirement Characteristic | Route To |
|---------|--------|
| Single event + supported comparison baseline + by hour/by day | **alert** |
| Group values enumerable (<=100) | **alert** |
| Ratio (A/B) + by-hour/by-day window | **alert** (formula metric); ratios with current-day cumulative/natural week windows go to automation |
| Funnel / retention / custom SQL / cross-event | **automation** |
| Group values not enumerable / need dynamic coverage of new values | **automation** |
| Need to return user list / data table push | **automation** |
| From 00:00 today to now / natural week window | **automation** |
| Fully custom webhook payload | **automation** |
| Slack notification | **Either works**: alert uses `slack_web_hooks`; automation uses custom_webhook with a Slack incoming webhook — determine routing by other requirement characteristics |

**Hard prerequisite for group monitoring** (before routing judgment; do not route before confirmation): first ask "How to handle group values? Enumerate all current values / monitor only specified ones / automatically cover new values" — the answer directly determines routing (enumerate -> alert, auto-cover -> automation). For the complete probing and notification flow, see "Special Notes for Group Alerts" in [`references/alert-route.md`](references/alert-route.md). When routing to alert: first probe current group values (`SELECT DISTINCT ... LIMIT 100`), inform the customer of the group count and the limitation that "newly added group values will not be monitored automatically"; if the customer wants to "automatically cover new values", switch routing to automation.

**Routing result echo**: "Based on your requirements, I will use [TE Metric Alert / Agent Automation] to implement this alert task, because ..." — the reason MUST be specific (point out the requirement characteristic that determined the route, e.g., "a user list push is needed, and alert only supports text"), not just "more suitable".

**Weekday values for weekly tasks are opposite on the two paths** (match accordingly when configuring):

| Path | Field | Values |
|------|------|------|
| alert | `alert_hour_intervals[].week_day` | `1`~`7`, `1` = Monday ... `7` = Sunday |
| automation | `schedule.day_of_week` / `--weekday` | `0`~`6`, `0` = Sunday |

Example: "every Sunday" is written as `7` on the alert path and `0` on the automation path. Do not carry over the value from the other path.

### Step 4A: Create TE Metric Alert (alert path)

If routing judgment is **alert**:

1. **Capacity pre-check**: `ae-cli analysis alert list -p <project_id>` to check the current alert count in the project. Each project has a limit of 50; when full, inform the user to clean up old tasks on the platform first (or switch to the automation path) — do not create blindly
2. **Build the alert definition**: refer to the JSON skeleton and config examples in [`references/alert-route.md`](references/alert-route.md)
3. **Preview the configuration**: show the user the key parameters
   - Monitoring target (event + analysis method)
   - Judgment condition (comparison baseline + threshold + comparison method)
   - Notification method (channel + webhook)
   - Group value list (if group monitoring)
   - Any discrepancies between the preview and the user's original statement (thresholds, definitions, property substitutions, etc.); point them out one by one with reasons and wait for user confirmation
4. **Create after user confirmation**: `ae-cli analysis alert create -p <project_id> --definition-request '<json>'`
5. **Read-back verification (two-stage, both mandatory)** — for complete status field descriptions, polling cadence, and fail handling, see "Alert Execution Status Fields" in [`references/alert-route.md`](references/alert-route.md):
   - **Immediately**: use `ae-cli analysis alert list -p <project_id> --format json` to pull back the alert's definition and compare field by field with the previewed promise: event (including the formula metric's events and aggregation codes), analysis method (the property name bound to `quota` when aggregating by property), group value list, threshold (for ratio metrics see "Threshold Units for Ratio Metrics" in [`references/alert-route.md`](references/alert-route.md)), frequency, notification channel, and time zone. **Creation success != correct configuration** (the platform silently tolerates unknown fields); if any field differs from the preview, fix it immediately or inform the user — do not gloss over it as "verification passed"
   - **After the first calculation round**: the platform runs the first calculation round for a newly created alert within 1~5 minutes (regardless of the scheduled time, even for daily tasks); configuration errors only surface after the first calculation round. Use `ae-cli analysis alert get` to check `recent_alert_execute_status`; when it is `alert_fail`, read `fail_msg` to locate the cause and fix it; if the result is not available within the session, do not block delivery waiting — attach the self-check command in the delivery checklist
6. **Delivery checklist** (all items required):
   - Task completion status (task name + alert ID + **execution status**: `recent_alert_execute_status` confirmed as calculation succeeded, or note "first calculation round not yet reached" and attach the `alert get` self-check command; see "Alert Execution Status Fields" in [`references/alert-route.md`](references/alert-route.md))
   - Platform jump link: first read the current deployment's access domain via `ae-cli config current --jq '.activeHost'` (**NEVER hardcode any domain**; the domain of the customer's environment is determined by their deployment), then append `/#/alert/detail?id=<project_id>_<alert_id>&currentProjectId=<project_id>`
   - Advise the user to manually trigger a preview/calculation on the platform to confirm the data is normal
   - When a formula alert's config has no `format` field (the norm for API-created alerts), state the threshold in the delivery wording in dual form such as "0.95 (i.e., 95%)", and explain that the platform UI will display a numeric threshold (e.g., "below fixed value 0.95 (numeric)"), to prevent the user from misjudging the configuration as wrong after seeing the UI

**Not needed on the alert path**: writing SQL, dry runs, creating an Agent, creating a scheduled task.

### Step 4B: Create Agent Automation (automation path)

If routing judgment is **automation**:

1. **Write the execution script to disk**: read `scripts/metric_alert.py` from the Skill script assets and write it to the current directory (command: `ae-cli agent +read-skill-script --id <skill_id> --path metric_alert.py --output ./metric_alert.py` — `--path` is relative to the skill's script asset directory; just give the file name, do not include the `scripts/` prefix; the returned JSON envelope's body is what `--output` writes to disk; use it for both dry runs and the run phase. `<skill_id>` is this skill's platform ID — obtain it from the current session's Skill metadata; do not guess)

2. **Generate the SQL template**
   - Select a template per [`references/sql-templates.md`](references/sql-templates.md)
   - Fill in business parameters (replace all configuration-phase placeholders such as `{{project_id}}`, `{{event_name}}`, `{{aggregate_expr}}`, `{{filters}}` with concrete content)
   - **Keep run-phase time placeholders**: `{{date}}`, `{{window_start}}`, `{{window_end}}` (conditional: `{{week_start}}`/`{{week_end}}`, `{{base_date}}`)

3. **Write the alert rule file**: `./alert_rule.json`
   - Write the generated SQL into the `sql_template` field (for field definitions see [`references/rule-schema.md`](references/rule-schema.md))

4. **SQL dry run**
   - Execute: `METRIC_ALERT_DRY_RUN=1 METRIC_ALERT_SPEC=./alert_rule.json python3 ./metric_alert.py`
   - The script replaces time placeholders, executes queries, and computes baseline values; dry run details are in `./run_result.json` in the `rendered_sql` field (rendered SQL of the main query and baseline queries, each annotated with its window; multiple baseline queries of history_avg/max are distinguished by offset days, e.g., `baseline_query (-1d)` denotes the window offset by 1 day) and the `sample_rows` field (first 5 sample rows of each query segment; labels correspond one-to-one with rendered_sql)
   - When the trigger condition is hit, the script still renders the message template once for variable validation (without pushing): unknown variables in the template, or variables not applicable to this monitoring type (e.g., writing `{{row_count}}` for a single-value metric), will cause an immediate error exit at the dry run stage (exit code 1) instead of being deferred to the formal run
   - Show the user **four things**:
     1. **Full SQL** (the actual SQL after placeholder replacement in `rendered_sql`; show both the main query and baseline queries; for group monitoring the baseline query is structurally identical to the main query, differing only in time window)
     2. **Judgment result**: for single-value metrics show the current value and baseline value (absolute-threshold judgments `gt`/`lt`/`eq` have no baseline value; an empty baseline column is normal — the terminal prints `None` and `run_result.json` records `null`); for group monitoring show the number of triggered groups (hit groups / total groups / skipped groups); for list monitoring show the number of hit rows
     3. **First 5 rows of data samples** (`sample_rows`, so the user can visually verify the definition is correct)
     4. **Review hint**: "You can review this yourself on the platform using the same SQL" (attach the main query SQL)
   - When the user questions the numbers, first self-check the definition (time window, filter conditions, dedup logic), then align with the user; do not merely repeat the script output

5. **Ensure the execution Agent exists**: see [`references/agent-setup.md`](references/agent-setup.md)

6. **Create the scheduled task**: `ae-cli agent +create-automation` (MUST include `--reuse-conversation true`; see [`references/agent-setup.md`](references/agent-setup.md))
   - For multi-timezone projects, convert the schedule time according to the settlement time zone (for the conversion formula and paired echo wording, see "Schedule Time Conversion" in [`references/timezone-guide.md`](references/timezone-guide.md))
   - The scheduled task's message carries the complete `alert_rule.json` content
   - **Schedule self-check (mechanically execute before submission)**: pair window types with schedule frequencies per the recommended combinations — `natural_hour`+`hourly`, `natural_day`+`daily`, `natural_week`+`weekly`, `today_to_now`+`hourly` (for the combination table see "window sub-item" in [`references/rule-schema.md`](references/rule-schema.md)). For hourly, set `minute` to `05` or `10` to leave a buffer for data ingestion; do not use 0 (allowed values are multiples of 5: 05, 10, 15...55)

7. **Delivery trio** (all items required; see [`references/agent-setup.md`](references/agent-setup.md)):
   - Task completion status (task name + automation ID)
   - Platform jump link: `<activeHost>/agent/automations/<automation_id>` (read the host dynamically via `ae-cli config current --jq '.activeHost'`; **NEVER hardcode the domain**; for the concatenation rule see "Delivery Trio" in [`references/agent-setup.md`](references/agent-setup.md))
   - **First-run hint**: advise the user to manually trigger the automation once (the platform supports immediate runs) to confirm the first run succeeds — issues such as insufficient quota or Agent misconfiguration only surface in a real run

---

## Run Phase (automation path only)

After the scheduled task triggers, the execution Agent mechanically follows the message template: write the script to disk -> write alert_rule.json -> run -> check the exit code. For the complete message template and exit code semantics, see "Message Template" in [`references/agent-setup.md`](references/agent-setup.md).

**Forbidden during the run phase**: modifying SQL, changing the project, changing thresholds, asking the user follow-up questions, mocking data, manual pushing.

---

## Modification and Deletion (existing monitoring tasks)

- **alert path**: use `ae-cli analysis alert update` to modify configuration, `ae-cli analysis alert delete` to delete, `ae-cli analysis alert start` / `ae-cli analysis alert stop` to enable/disable (these can also be done on the platform's alert page). After adjusting thresholds / definitions, also perform the two-stage read-back verification from Step 4A
- **automation path**:
  - **Adjustment (threshold / definition / SQL / schedule)**: assemble the new `alert_rule.json` content into the message and use `ae-cli agent +update-automation --id <automation_id> --message '<new content>'` to **update in place** (schedule and enable/disable use the same command: `--cron` / `--time` / `--minute` / `--enabled`). Before updating, run a DRY_RUN with the same new rule first; update only after the dry run passes, to avoid pushing a broken configuration to the run side
  - **Permanent deletion**: the CLI has no command to delete an automation; delete it on the platform's automation list page
- Before any create, modify, enable/disable, or delete action, still fully echo the final configuration to the user for confirmation per Mandatory Principle 4

---

## Appendix

- [`references/alert-route.md`](references/alert-route.md) — TE Metric Alert capability boundaries and routing judgment
- [`references/rule-schema.md`](references/rule-schema.md) — Complete field table for alert rules (automation path)
- [`references/sql-templates.md`](references/sql-templates.md) — SQL template library (13 in total: Templates 1~12 plus 12b, including single/multi-timezone versions)
- [`references/timezone-guide.md`](references/timezone-guide.md) — Dedicated guide to time zone handling
- [`references/agent-setup.md`](references/agent-setup.md) — Agent detection and creation
- [`scripts/metric_alert.py`](scripts/metric_alert.py) — Run-phase executor (automation path)

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
