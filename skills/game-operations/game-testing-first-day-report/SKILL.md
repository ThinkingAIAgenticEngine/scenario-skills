---
name: game-testing-first-day-report
description: Generate a first-day game testing report from TE data, covering acquisition, monetization, progression, and data quality. Trigger when the user wants to review or analyze first-day game test/launch performance data, including first-day metrics, ROI, or post-launch day-one results. For game projects only; confirm data model compatibility for non-game projects.
---

# Game Testing First-Day Data Report Skill

> **[CRITICAL] Output Language Rule**: The report MUST be generated in the **same language the user uses** to interact with you. If the user speaks Chinese, output the full report in Chinese. If the user speaks English, output in English. Only data field names and technical identifiers remain in their original form.

## 1. Prerequisites

- TE analysis APIs are available (`ae-cli analysis adhoc run` / `event-detail run` / `event-detail export`)
- If APIs are not configured, prompt the user to configure them first

## 2. Trigger Identification

Extract from user input:
- **Project ID** (required, defaults to current session default project)
- **First-day date** (required, defaults to yesterday, calculated using CLAUDE.md's `currentDate`)
- **Game type identifier** (optional)
- **Channel info** (optional)

After confirmation, present the analysis scope to the user in a single confirmation (date, whether social features are enabled, whether channel data exists). Do not split into multiple rounds of questions.

## 3. Pre-flight Checks

### 3.1 One-time Project Metadata Retrieval

The main Agent initiates **2 parallel Bash calls in a single message**:

1. `ae-cli project info get --project-id <pid> --format json` — project name, timezone (`default_time_zone_offset`)
2. Run the complete metadata exports in parallel: `ae-cli analysis-meta event export -p <pid> --output /tmp/events.json` and `ae-cli analysis-meta property export -p <pid> --output /tmp/props.json`. These commands return the full accessible event and property inventories without requiring search keywords.

**DO NOT use `project entity-event list`**; it returns only entity columns. **DO NOT loop through events one by one.** Use `analysis-meta catalog list` only for bounded keyword search, and always provide both `--queries '["<keyword>"]'` and `--resource-types`; it is not a full-catalog command in ae-cli 6.0.42.

The export commands write complete JSON arrays to the requested `.json` files. Treat an incomplete or unreadable export as a blocking metadata error rather than silently falling back to guessed fields.

**Do NOT use `--jq`** on this call; known issue returning `rows: null`. Use `--format json` and parse with Python.

### 3.2 Metadata Extraction Rules

From the `event export` and `property export` files:

**Event name matching** (grouped by business domain):
- General: register / login / logout / online / payment
- Tutorial/Battle: guide_completed / battle_start / battle_win / battle_lost
- Progression: level_up
- Gacha/Shop: draw_card / shop_buy
- Gameplay Modes: tower_challenge / attend_arena
- Social: add_guild / guild_activity / **add_friend / friend_add / send_friend_request / accept_friend / remove_friend**
- Tech: crash / anr / login_fail / **ta_app_end**
- Economy (**fuzzy match — naming varies by project**):
  - Diamond-type: diamond_get / diamond_consume / diamond_add / diamond_use
  - Gold-type: gold_get / gold_consume / coin_get / coin_spend
  - Generic currency: currency_get / currency_consume / money_get / money_spend
  - Item-type: item_get / item_use
  - **Match rule**: event name contains `diamond|coin|gold|currency|money|item` AND contains `get|acquire|gain|add|consume|spend|cost|use|lose`

**Property name matching**:
- Payment: pay_amount / payment_name
- Online time: online_time / **#duration** (ta_app_end event)
- Battle/Tutorial: battle_id / guide_step
- Level: level / role_level / player_level / user_level (`hero_level` is typically hero/card level, not for user level distribution)
- **Economy change amount**: change_amount / amount / quantity / count / delta / `<event_name>_amount` pattern
- **Economy change reason**: change_reason / reason / source / channel / action / way

**Preset properties**: #os / #device_model / #ip / #app_version / #network / #resolution

**Virtual properties**: #vp@online_time_1d (if present)

**User entity properties**:
- Current level: role_level / level / player_level / user_level / vip_level
- Account creation time: create_time / register_time
- Cumulative payment: total_pay_amount / pay_total
- Cumulative online time: total_online_time

### 3.3 Confirmation Checklist

> When generating checklist, also perform project type check: verify whether events contain game-characteristic events (at least 2 of register, battle_start, draw_card, level_up). If not, append "Project type check" line.

```
[Game Testing First-Day Report Pre-flight Confirmation]
- Project: {{projectName}} (id={{pid}}) | First Day: {{YYYY-MM-DD}} | Timezone: UTC+{{offset}}
- Register event: register ✅
- Login event: login ✅
- Logout event: logout ✅ (online_time)
- App exit event: ta_app_end ✅ (#duration, alternative online-time source)
- Payment event: payment ✅ (amount property pay_amount)
- Tutorial event: guide_completed ✅ (step property guide_step)
- Battle events: battle_start / battle_win / battle_lost ✅ (stage property battle_id)
- Level-up event: level_up ✅ (level property {{level/role_level}})
- User entity level field: {{role_level/level/none}} {{✅/❌}}
- Social events: add_guild / guild_activity / add_friend {{✅/❌}}
- Economy events: {{diamond_get/diamond_consume/gold_get/gold_consume/...}} {{✅/❌}}
  - Change amount property: {{change_amount/amount/...}}
  - Change reason property: {{change_reason/reason/...}}
- Channel field: channel {{✅/❌}}
- Tech events: crash / anr / login_fail {{✅/❌}}
{{If < 2 game-characteristic events:}}
- Project type check: ⚠️ Non-game project (missing characteristic events such as battle_start/draw_card), report structure may not be fully applicable
{{/If}}

Reply "confirm" to proceed.
```

### 3.4 Termination Condition Check

If register, login, and payment — all three core events — are **all** ❌, terminate and output:

> ⚠️ Core events (register/login/payment) are all not configured. Cannot perform effective first-day data analysis. Please complete the following tracking integration and retry:
> - register: user registration event
> - login: user login event
> - payment: payment event

If only some missing, continue and mark missing modules as "Not Reported."

## 4. Query Execution

> **Key change**: Main Agent directly runs parallel Bash commands. **Do NOT use `--jq`** (known to return `rows: null` on SQL payloads). Keep `/tmp/qN-definition.json` for the definition and `/tmp/qN.out` for the command envelope; parse from the first output line beginning with `{` or `[` so diagnostic prefixes do not corrupt JSON parsing.

### 4.0 SQL Definition Input Format

`ae-cli analysis adhoc run --model-type sql --definition <JSON>` requires a JSON object `{"sql":"<SQL text>"}`, not raw SQL.

Use file-based pattern:
1. Write SQL-JSON to `/tmp/qN-definition.json`: `{"sql":"SELECT ..."}`
2. Run: `definition_json=$(cat /tmp/qN-definition.json); ae-cli analysis adhoc run --project-id <pid> --zone-offset <offset> --model-type sql --definition "$definition_json" --preview-rows 1000 --format json > /tmp/qN.out 2>&1`

**Date column types**:
- Event table `v_event_<pid>`: `"$part_date"` is VARCHAR → `BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`
- User entity table `v_user_<pid>`: `register_time` is TIMESTAMP → `>= TIMESTAMP 'YYYY-MM-DD 00:00:00' AND <= TIMESTAMP 'YYYY-MM-DD 23:59:59'`

**Identifier quoting**: Trino identifiers with `#`, `$`, `@`, spaces, or reserved words must be double-quoted. String literals use single quotes.

**Required partition predicate**: Event-table SQL must include `"$part_date"` predicate.

### 4.1 Unified Context

```
- projectId: <pid>
- First-day date: YYYY-MM-DD
- Timezone: --zone-offset <offset>
- Event mapping: (as identified in §3.2)
- User entity: v_user_<pid>
```

### 4.2 Online Time Analysis Strategy

> **Important**: Sum by `#user_id` before creating distribution.
> **Source detection**: Probe with SQL:
> ```sql
> SELECT
>   COUNT(*) FILTER (WHERE "$part_event"='logout' AND online_time IS NOT NULL) AS logout_cnt,
>   COUNT(*) FILTER (WHERE "$part_event"='ta_app_end' AND "#duration" IS NOT NULL) AS app_end_cnt
> FROM v_event_<pid> WHERE "$part_date" BETWEEN '<date>' AND '<date>'
> ```

**Data source priority**:
1. **Primary A**: logout.online_time
2. **Secondary B**: ta_app_end.#duration
3. **Fallback C**: Virtual property `#vp@online_time_1d` (if exists; skip per-user sum)
4. **Last resort D**: Interval model (from_event=login, to_event=login, window=1day)

**SQL implementation**:
```sql
SELECT
  CASE
    WHEN total_sec < 300 THEN '0-5min'
    WHEN total_sec < 900 THEN '5-15min'
    WHEN total_sec < 1800 THEN '15-30min'
    WHEN total_sec < 3600 THEN '30-60min'
    WHEN total_sec < 5400 THEN '60-90min'
    WHEN total_sec < 7200 THEN '90-120min'
    WHEN total_sec < 10800 THEN '120-180min'
    ELSE '180min+'
  END AS bucket,
  COUNT(*) AS user_count
FROM (
  SELECT "#user_id", SUM(CAST(online_time AS BIGINT)) AS total_sec
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<date>' AND '<date>'
    AND "$part_event" = 'logout'
    AND online_time IS NOT NULL
  GROUP BY "#user_id"
)
GROUP BY 1
ORDER BY 1
```

### 4.3 Level Distribution Analysis Strategy

**Data source priority**:
1. **Primary A**: User entity table `v_user_<pid>` role_level/level (actual current level)
2. **Secondary B**: Latest record from level_up event via window function (use user level fields, not hero_level)

### 4.4 SQL-First Strategy

> Use SQL for all queries. AI-facing models have unstable schemas. Do NOT retry on failure unless a clear type error.

### 4.5 Parallel Query Batches

Each query must include the complete 6.0.42 contract: `definition_json=$(cat /tmp/qN-definition.json); ae-cli analysis adhoc run --project-id <pid> --zone-offset <offset> --model-type <model_type> --definition "$definition_json" --preview-rows 1000 --format json > /tmp/qN.out 2>&1`. Keep the definition input file separate from the output file, then parse the JSON envelope from `/tmp/qN.out`.

#### Batch 1

| # | Model | Description |
|---|-------|-------------|
| Q1 | sql | New users/login/payment users+amount/DAU via SQL. Cross-validate register event count vs v_user_<pid>. |
| Q2 | event | Register user count by hour |
| Q3 | event | Login user count by hour |
| Q4 | sql | Funnel via SQL: COUNT(DISTINCT #user_id) per step |
| Q5 | distribution / sql | Online-time distribution (per-user sum) |
| Q6 | distribution / sql | Payment tier distribution (per-user sum) |
| Q7 | event | Gameplay event participation counts (total) |
| Q8 | event | Register by #os |
| Q9 | event | Register by channel |
| Q10 | sql | Payment item amount TOP 20 |

#### Batch 2

| # | Model | Description |
|---|-------|-------------|
| Q11 | sql | Stage pass/fail rate via SQL |
| Q12 | sql | Level distribution (user entity or level_up window) |
| Q13 | sql | Diamond gain TOP reasons |
| Q14 | sql | Diamond spend TOP reasons |
| Q15 | sql | Gold gain/spend TOP reasons |
| Q16 | sql | Payment top spenders Top 20 |

#### Batch 3 (large volume export only)

- Same-IP batch registration detection via SQL.

### 4.6 Execution Discipline

- Do not spawn sub-Agents.
- Do not output intermediate results.
- Do not return raw JSON.
- Do not retry failed queries.
- Always use SQL first.

## 5. Aggregation and Report Generation

### Step 1: Cross-validation
- Q1 register count vs Q2 hourly total vs Q4 funnel step 1
- Q1 login count vs Q3 hourly total
- Q1 payment sum vs Q10 payment_name aggregate
- Validate payment users ≤ DAU and ≤ register
- Funnel cross-validation
- Online-time total users ≤ login users

### Step 2: Anomaly Scan (business anomalies only)

Flag only if:
- Conversion cliff: adjacent funnel steps >15% difference
- Hourly new-user cliff: >80% difference
- Stage fail-rate spike: >10pp difference between adjacent stages
- Abnormal concentration: single level/stage user share >40%
- Payment concentration: Top 5% users >50% revenue
- Gameplay penetration anomaly: related event penetration difference >30pp
- Economy anomaly: paid currency spend top-1 reason share >60%

Anomaly table: 🔴 High Priority (max 3), 🟡 Medium Priority (max 3). Never include infra issues.

### Step 3: Data Quality Scan

Consolidate infra issues into 📝 Data Quality table:
- Properties all NULL
- Events not configured
- Name conflicts
- Truncation
- Table not exist
- Missing fields
- Economy event missing properties

### Step 4: Generate Charts

Embed charts using ` ```chart ` code fence:
- New-user hourly (Q2) → line
- DAU hourly (Q3) → line
- Online-time (Q5) → bar
- Payment tier (Q6) → bar
- Payment item TOP (Q10) → bar
- Stage pass/fail rate Top 30 (Q11) → line dual-series
- Device OS (Q8) → pie
- Channel (Q9) → pie
- Level (Q12) → bar
- Diamond spend TOP (Q14) → bar
- Gold spend TOP (Q15) → bar

### Step 5: Populate Template

Use `references/report-template.md`. Strictly separate anomalies from data quality.

### Step 6: Final Checks
- Anomaly table contains no infra issues
- Data quality table contains no business anomalies
- Each module ends with `> **Module Summary**:`
- Charts embedded via code fence; no standalone files
- Cross-validation passed or deviations noted
- Failed queries marked
- Online time per-user sum before distribution
- Level distribution prefers user entity table, then level_up window
- Economy module has output/spend totals + TOP reasons

### Step 7: Incomplete Report Review

Count modules with all key metrics marked ⚠️. If ≥3, prompt user:
> ⚠️ Note: This report has N modules with incomplete data (...). Results are for reference only. Still output full report?

If user declines, present summary:
```
## First-Day Report Summary (Incomplete)
- User Acquisition: ...
- Core Funnel: ...
- Payment: ...
- ⚠️ Online Time: data not reported
- ⚠️ Social: social events not reported
```

## 6. Report Output Template

The report template is located at `references/report-template.md`. Read it during execution, then populate placeholders.

Template structure: Anomaly Findings → Basic Data Overview → User Acquisition → Online Time → Core Funnel → Payment → Game Progression → Game Bottlenecks → Economy System → Social → Tech Quality → User Profile → Anomaly Monitoring → Report Summary → Data Quality Table

## 7. Edge Cases

| Scenario | Handling |
|----------|----------|
| Project ID not provided | Use session default; do not ask |
| No date specified | Default to yesterday, inform once |
| Core events missing | Mark module as "Event not reported", write to Data Quality |
| logout has no online_time | Try ta_app_end.#duration, then #vp@online_time_1d, then interval model |
| ta_app_end has no #duration | Fallback to #vp@online_time_1d or interval model |
| Online time requires per-user sum | SQL: SUM(online_time) GROUP BY #user_id then bucket |
| Level distribution has no user entity field | Fallback to level_up ROW_NUMBER window function |
| level_up level property type wrong | Mark "⚠️ Level property type is non-numeric" |
| Economy event has no change_amount | Use project's actual amount field, approximate with user_count if missing |
| Economy event has no change_reason | Only tally totals, do not analyze destinations |
| payment name conflict | Switch directly to SQL `"$part_event"='payment'` |
| event-detail 1000-row truncation | Top details switch to SQL + LIMIT 20 |
| SQL table name does not exist | Use `v_event_<pid>` / `v_user_<pid>` |
| AI-facing funnel/distribution unsupported | Fix window/property placement; retry once; fallback to SQL |
| Sample size <100 | Mark "Sample size insufficient, for reference only" |
| Query timeout | Mark as failed; do not retry |
| Social events not reported | Mark "⚠️ Not Reported"; do not block other modules |
| `--jq` returns `rows: null` | Drop `--jq`; use file + Python parsing |
| SQL definition input format | Must be JSON `{"sql":"..."}`; use file-based pattern |
| `register_time` is TIMESTAMP | Use TIMESTAMP literals, not VARCHAR BETWEEN |
| Register event re-fired by returning users | Cross-check vs v_user_<pid>.register_time; if >2x, flag and use v_user_<pid> count |
| Metadata inventory is large | Use the complete event/property export files; do not substitute bounded catalog search |

## 8. Important Constraints

1. **Strictly separate anomalies from data quality**
2. **Every module must have a summary**: end with `> **Module Summary**:` quoting specific values
3. **Do not fabricate data**: mark as "Not Reported / No Data" when not queried
4. **Charts embedded directly**: use ` ```chart ` code fence; no standalone files
5. **Main Agent runs parallel Bash directly**; no sub-Agents
6. **Silent execution**: output final report directly
7. **Explicit timezone**: all queries add `--zone-offset <offset>`
8. **TE metadata retrieved once** via complete `analysis-meta event/property export`
9. **Online time: multi-source + per-user sum + probe first**
10. **Level distribution: multi-source**; no hero_level
11. **SQL-first + cross-validation**
12. **Economy module must be analyzed**: paid currency spend TOP reasons mandatory
13. **Social module is optional**
14. **Large data volumes use SQL LIMIT**
15. **Strictly control anomaly count**: 🔴 max 3, 🟡 max 3

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
