# Data Validation Guide

> **Purpose**: ae-cli command reference, data contract, quality validation, and recovery flows for new-user-analysis.
> **Usage**: Load before any data access. Reference during Step 0 (environment check) and Step 2 (data validation).

---

## 0. ae-cli Environment Verification

### 0.1 Installation Check

```bash
# Check ae-cli is installed and executable
ae-cli --version
# Expected: 6.x.x or compatible

# If not installed:
npm install -g @thinkingdata/ae-cli
# or
brew install ae-cli
```

### 0.2 Auth Status Check

```bash
# Check authentication status
ae-cli auth status

# Expected output:
# {
#   "authenticated": true,
#   "user": "user@example.com",
#   "expires_at": "2026-12-31T23:59:59Z"
# }

# If not authenticated:
ae-cli auth login
# Follow device code flow: visit URL, enter code, authorize
```

### 0.3 Auth Recovery Flow

| Symptom | Cause | Fix |
|---------|-------|-----|
| `auth expired` | Token older than 7 days | `ae-cli auth login` (re-auth) |
| `project not found` | Wrong project ID or no access | `ae-cli team +list-projects` to verify |
| `permission denied` | Insufficient role | Ask admin to grant analyst role |
| `network timeout` | Firewall or VPN required | Check corporate network settings |
| `invalid JSON` | Shell escaping issue | Use Python `json.dump` to generate definition (see §4.1) |

---

## 1. Project Discovery

### 1.1 List Projects

```bash
# List all accessible projects
ae-cli team +list-projects

# Expected output:
# [
#   {"project_id": 1234, "project_name": "game-demo", "status": "active"},
#   {"project_id": 5678, "project_name": "ecommerce-prod", "status": "active"}
# ]
```

### 1.2 Verify Project Access

```bash
# Probe project reachability
ae-cli analysis-meta event list --project-id {project_id} --limit 5

# If fails with "project not found":
# 1. Verify project_id from list-projects
# 2. Check user has access to this project
# 3. Try SQL fallback probe (see §3.2)
```

---

## 2. Data Contract

### 2.1 Event Table Schema

ThinkingData stores events in `v_event_{project_id}`:

| Column | Type | Description | Required for new-user-analysis |
|--------|------|-------------|-------------------------------|
| `#distinct_id` | string | Anonymous user ID (device-level) | ✅ Yes |
| `#account_id` | string | Account ID (login-level) | Recommended |
| `#device_id` | string | Device fingerprint | Recommended |
| `#session_id` | string | Session identifier | Phase 2 |
| `event_name` | string | Event type | ✅ Yes |
| `event_time` | timestamp | Event occurrence time | ✅ Yes |
| `"$part_date"` | date | Partition date (YYYY-MM-DD) | ✅ Yes |
| `duration` | number | Event duration (seconds) | Phase 2 |
| `channel` | string | Acquisition channel | Phase 4/5 |
| `device_model` | string | Device model | Phase 4/5 |
| `region` | string | Geographic region | Phase 4/5 |
| `traffic_source` | string | Organic / paid / etc. | Phase 4/5 |
| `revenue` | number | Purchase amount | Phase 2 |
| `is_success` | string | Success flag ("1"/"0") | Varies by event |

### 2.2 Property Validation Checklist

Before running any analysis, verify these properties exist:

```bash
# List all events in project
ae-cli analysis-meta event list --project-id {project_id}

# Check specific event properties
ae-cli analysis-meta event get --project-id {project_id} --event-name {event_name}

# List USER properties (a dimension absent from event props often lives here)
ae-cli analysis-meta property list --project-id {project_id} --table-type user

# After resolving an exact event property, look up its stored candidate filter values
ae-cli analysis filter-value list --project-id {project_id} --table-type event --event-name {event_name} --property-name {property} --search-prefix {keyword}
```

> **Rule — check BOTH tables before declaring a dimension missing.** `region`/`country`/`traffic_source` are frequently user properties (e.g. `channel@country`, `media_source`, `#vp@region`), not event properties. Always run `property list --table-type user` before concluding "no region dimension".

**Required properties checklist**:

| Property | Phase | Validation Method |
|----------|-------|-----------------|
| `#distinct_id` | All | `ae-cli analysis-meta event get` on any event |
| `event_name` | All | `ae-cli analysis-meta event list` |
| `event_time` | All | Implicit in all events |
| `"$part_date"` | All | Partition column, always present |
| `channel` | Phase 4/5 | Check event property or user property |
| `device_model` | Phase 4/5 | Check event property |
| `region` | Phase 4/5 | Check event property or user property |
| `traffic_source` | Phase 4/5 | Check user property (e.g., `#vp@traffic_source`) |

### 2.3 Event Name Variants

Common event name variants for key actions:

| Action | Common Names | Notes |
|--------|-----------|-------|
| App Launch | `launch`, `app_open`, `first_open`, `AppStart`, `app_start`, `ta_app_start` | `ta_app_start` is ThinkingData auto-track |
| Tutorial Start | `tutorial_start`, `ftue_start`, `onboarding_start`, `guide_begin` | |
| Tutorial Complete | `tutorial_complete`, `ftue_complete`, `onboarding_complete`, `guide_finish` | |
| Register | `signup`, `register`, `account_create`, `join`, `Register` | Case-sensitive in some projects |
| Purchase | `purchase`, `payment_complete`, `order_success`, `transaction`, `pay` | |
| Add to Cart | `add_cart`, `cart_add`, `add_to_bag`, `basket_add` | |
| Search | `search`, `query`, `search_submit`, `find` | |
| Like | `like`, `heart`, `upvote`, `favorite`, `thumbs_up` | |
| Follow | `follow`, `subscribe`, `friend_add`, `track` | |
| Share | `share`, `repost`, `forward`, `send_to_friend` | |

**Auto-discovery command**:

```bash
# Search event metadata for candidate event names (for example, tutorial)
ae-cli analysis-meta event list --project-id {project_id} --queries '["tutorial"]'
```

---

## 3. Data Quality Validation

### 3.1 Low-Sample Tiers

| Daily New Users | Tier | Handling | Output |
|-----------------|------|----------|--------|
| **<50/day** | Insufficient | Aggregate to monthly only | Monthly trend + "insufficient daily data" label on all outputs |
| **50-200/day** | Low | Daily granularity with warning | Daily scores + "low sample" flag on every metric |
| **>200/day** | Normal | Full analysis | No warnings |

**Check query** (T5.1 in sql-templates.md):

```sql
SELECT 
  "$part_date" as date,
  COUNT(DISTINCT "#distinct_id") as new_users
FROM v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
  AND event_name IN ({active_event_list})
GROUP BY "$part_date"
ORDER BY "$part_date"
```

### 3.2 Synthetic Data Detection

Run before attribution to catch demo/test data:

| Check | Query Logic | Pass | Fail Action |
|-------|-----------|------|-------------|
| Single device model | `COUNT(DISTINCT device_model) = 1` | >1 | Label "synthetic data suspected", investigate |
| Single region | `COUNT(DISTINCT region) = 1` | >1 | Same as above |
| Single channel | `COUNT(DISTINCT channel) = 1` | >1 | Same as above |
| Round user count | `user_count % 1000 = 0` | Not round | Warn "possible synthetic cohort" |
| Uniform session duration | `STDDEV(duration) < 1` | >1 | Warn "bot-like uniformity" |
| No null properties | `COUNT(null_props) = 0` | Some nulls expected | Warn "overly clean data" |

**Detection query** (T5.2 in sql-templates.md):

```sql
-- Run all checks in one query
SELECT 
  'device_diversity' as check_name,
  COUNT(DISTINCT device_model) as unique_count,
  CASE WHEN COUNT(DISTINCT device_model) > 1 THEN 'PASS' ELSE 'FAIL' END as result
FROM v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
UNION ALL
SELECT 
  'region_diversity',
  COUNT(DISTINCT region),
  CASE WHEN COUNT(DISTINCT region) > 1 THEN 'PASS' ELSE 'FAIL' END
FROM v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
```

### 3.3 Time Range Validation

| Issue | Symptom | Fix |
|-------|---------|-----|
| Timezone mismatch | Data appears shifted by N hours | Use `--zone-offset` flag or adjust dates |
| Incomplete days | First/last day has partial data | Use full days only, or normalize by hours |
| Future dates | `"$part_date"` > today | Check system clock, use `DATE_SUB` |
| Gap in data | Missing dates in sequence | Verify tracking was live, fill gaps with 0 |

**Timezone handling**:

```bash
# Some projects reject --zone-offset with PROJECT_TZ_DISABLED
# Omit flag or pass 99 for local-time mode
ae-cli analysis adhoc run --project-id {pid} --model-type sql --definition '...' --zone-offset 99
```

---

## 4. ae-cli Query Execution

### 4.1 Definition JSON Generation (Mandatory)

**Never hand-write multi-line JSON in shell commands.** Use Python to generate:

```bash
python3 - <<'PY'
import json

definition = {
    "time_range": {
        "mode": "custom",
        "start_time": "2026-09-01 00:00:00",
        "end_time": "2026-09-07 23:59:59"
    },
    "time_particle_size": "day",
    "metrics": [
        {
            "event": "注册",
            "aggregation": "user_count",
            "filters": [
                {"field": {"name": "is_success", "type": "event_property"}, "operator": "eq", "values": ["1"]}
            ]
        }
    ],
    "groups": [
        {"field": {"name": "channel", "type": "user_property"}}
    ]
}

with open("definition.json", "w") as f:
    json.dump(definition, f, ensure_ascii=False)
PY

DEF=$(cat definition.json)
ae-cli analysis adhoc run --project-id {pid} --model-type event --definition "$DEF"
```

### 4.2 Run vs Export

| Command | Use Case | Limit | Async? |
|---------|---------|-------|--------|
| `ae-cli analysis adhoc run` | Quick preview, small result | 100 rows (`has_more=true`) | No |
| `ae-cli analysis adhoc export` | Full data download | No row limit | Yes |

**Export workflow**:

```bash
# 1. Submit export
ae-cli analysis adhoc export --project-id {pid} --model-type sql --definition "$DEF"
# Output: {"run_id": "abc123"}

# 2. Poll status
ae-cli analysis adhoc run inspect --project-id {pid} --run-id abc123
# Wait for "status": "SUCCEEDED" or "artifact_status": "COMPLETED"

# 3. Download artifact
ae-cli analysis adhoc artifact download --project-id {pid} --run-id abc123 --output ./data.jsonl.gz
```

### 4.3 Model Type Definition Formats (Verified via Live Test)

ae-cli supports multiple model types. **Each has a unique definition structure**. Using the wrong structure returns `INVALID_CAPABILITY_INPUT` or `unknown field` errors.

#### 4.3.1 Event Model (`--model-type event`) ✅ Verified

**Use for**: Phase 1 caliber data-quality verification (event existence/coverage), Phase 2 feature adoption, Phase 4/5 channel distribution.

**Structure**:
```json
{
  "time_range": {"mode": "custom", "start_time": "...", "end_time": "..."},
  "time_particle_size": "day",
  "metrics": [
    {"event": "event_name", "aggregation": "user_count", "filters": [...]}
  ],
  "groups": [
    {"field": {"name": "property_name", "type": "user_property|event_property"}}
  ]
}
```

**Verified example** (MMO demo, 2026-09-07):
```json
{
  "time_range": {"mode": "custom", "start_time": "2026-09-07 00:00:00", "end_time": "2026-09-07 23:59:59"},
  "time_particle_size": "day",
  "metrics": [
    {"event": "login", "aggregation": "user_count"},
    {"event": "create_role", "aggregation": "user_count"},
    {"event": "register", "aggregation": "user_count"},
    {"event": "payment", "aggregation": "user_count"}
  ]
}
```

**Notes**:
- `groups` is optional. Omit for simple counts.
- `filters` inside metrics is optional.
- Supports multiple metrics in one query.
- Returns `title` (column names) and `rows` (data arrays).

#### 4.3.2 Path Model (`--model-type path`) ✅ Verified

**Use for**: Phase 3 behavior sequence analysis, path distribution.

**Structure**:
```json
{
  "time_range": {"mode": "custom", "start_time": "...", "end_time": "..."},
  "path": {
    "source_event": "event_name",
    "included_events": ["event1", "event2", ...],
    "session_interval": 24,
    "session_unit": "hour"
  }
}
```

**Verified example** (MMO demo, 2026-09-07):
```json
{
  "time_range": {"mode": "custom", "start_time": "2026-09-07 00:00:00", "end_time": "2026-09-07 23:59:59"},
  "path": {
    "source_event": "login",
    "included_events": ["login", "create_role", "enter_dungeon", "dungeon_result", "level_up", "payment"],
    "session_interval": 24,
    "session_unit": "hour"
  }
}
```

**Critical rules**:
- `source_event` must be included in `included_events` list (error: `SOURCE_EVENT_NOT_IN_LIST`).
- `session_unit` only accepts `second` (1..999), `minute` (1..999), or `hour` (1..24). **Do not use `day`** — express 1 day as `session_interval=24` + `session_unit=hour`.
- `included_events` and `source_event` are **strings**, not objects.
- Returns node-link structure (Sankey-ready): `nodes` array of arrays, each inner array = one step's events with `times` (count) and `id` (step_eventname).

**Status**: ✅ Verified on MMO demo (2026-09-14). Result showed login→enter_dungeon (6,623 users), login→login (3,825), etc.

#### 4.3.3 Funnel Model (`--model-type funnel`) ✅ Verified (Partial)

**Use for**: Phase 3 sequential funnel drop-off analysis.

**Structure**:
```json
{
  "time_range": {"mode": "custom", "start_time": "...", "end_time": "..."},
  "funnel": {
    "steps": [
      {"event": "event1", "filters": []},
      {"event": "event2", "filters": []}
    ],
    "window": {"unit": "day|hour", "value": 1}
  }
}
```

**Verified example** (MMO demo, 2026-09-07):
```json
{
  "time_range": {"mode": "custom", "start_time": "2026-09-07 00:00:00", "end_time": "2026-09-07 23:59:59"},
  "funnel": {
    "steps": [
      {"event": "login", "filters": []},
      {"event": "create_role", "filters": []},
      {"event": "enter_dungeon", "filters": []},
      {"event": "payment", "filters": []}
    ],
    "window": {"unit": "day", "value": 1}
  }
}
```

**Critical rules**:
- `steps` must be objects with `event` (string) and `filters` (array, can be empty). `filters` is **required** on each step — omitting it causes `unknown field funnel` error.
- `window` must be an object `{"unit": "...", "value": N}`, not an integer.
- Do NOT add `name` to steps (error: `unknown field name`).
- Do NOT add `metrics` anywhere (error: `unknown field metrics`).
- Returns `title` (step names + conversion columns) and `rows` (single row with counts and conversion %).

**Known issue**: With `window={"unit":"day","value":1}` and 1-day time range, all steps after Step 1 returned 0% conversion despite event model showing non-zero counts for the same events. This suggests the funnel window logic may require events to occur within the same calendar day, or the window semantics differ from expectations. **Workaround**: Use event model to compute step counts independently, or use SQL model for precise funnel control. Needs further investigation.

**Status**: ⚠️ Format verified, but conversion semantics need clarification. Use with caution.

#### 4.3.4 Retention Model (`--model-type retention`) ✅ Verified

**Use for**: Phase 2 D1 retention signal, cohort retention curves.

**Structure**:
```json
{
  "time_range": {"mode": "custom", "start_time": "...", "end_time": "..."},
  "retention": {
    "initial_event": "event_name",
    "return_event": "event_name",
    "unit_num": 1
  }
}
```

**Verified example** (MMO demo, 2026-09-01 to 2026-09-07):
```json
{
  "time_range": {"mode": "custom", "start_time": "2026-09-01 00:00:00", "end_time": "2026-09-07 23:59:59"},
  "retention": {
    "initial_event": "create_role",
    "return_event": "login",
    "unit_num": 1
  }
}
```

**Critical rules**:
- `initial_event` and `return_event` are **strings**, not objects.
- `unit_num` is required (integer, retention period count). Use 1 / 3 / 7 for D1 / D3 / D7 curves.
- Do NOT include `retention_type` (error: `unknown field retention_type`).
- **`filters` is supported INSIDE the `retention` object** (verified 2026-09-16, project 2). It scopes to the initial_event cohort, so you can split retention by any property (user_property or event_property) with one query per value. Do NOT put filters under metrics — retention has no metrics.
- Returns `title` (date, initial users, metric, current, D1) and `rows` (paired rows: retention count and retention rate per cohort date).

**Verified filter example** (split D1 by media_source, 2026-09-16):
```json
{
  "time_range": {"mode": "custom", "start_time": "2026-09-02 00:00:00", "end_time": "2026-09-15 23:59:59"},
  "retention": {
    "initial_event": "register",
    "return_event": "login",
    "unit_num": 1,
    "filters": [
      {"field": {"name": "media_source", "type": "user_property"}, "operator": "eq", "values": ["Organic"]}
    ]
  }
}
```

**Sample output**:
```json
{"title": ["初始事件发生时间", "创建角色用户数", "指标", "当日", "1日"],
 "rows": [
   ["阶段值", "4888", "留存人数", "4888", "2962"],
   ["阶段值", "4888", "留存率", "100%", "60.6%"],
   ["2026-09-07(一)", "615", "留存人数", "615", "358"],
   ["2026-09-07(一)", "615", "留存率", "100%", "58.21%"]
 ]}
```

**Status**: ✅ Verified on MMO demo (2026-09-14). D1 retention for create_role→login: 60.6% overall, 58.21% for 9/7 cohort.

#### 4.3.5 SQL Model (`--model-type sql`) ✅ Verified (2026-09-16)

**Correct structure** — `definition` is JUST `{"sql": "..."}`. Do NOT wrap in `model_type`/`definition`, do NOT add `time_range` (write it into SQL's `"$part_date"` predicate):

```json
{"sql": "SELECT COUNT(DISTINCT \"#account_id\") AS cnt FROM hive.ta.v_event_2 WHERE \"#event_name\" = 'register' AND \"$part_date\" >= '2026-09-09' AND \"$part_date\" <= '2026-09-15'"}
```

**Table naming (Trino engine, project N)**:
- Event table: `hive.ta.v_event_N`
- User table: `hive.ta.v_user_N`
- User daily-snapshot table: `hive.ta.user_day_serial_N`
- Discover real table names: `ae-cli analysis sql-table list --project-id N` (read `table_ref`).
- Discover columns: `ae-cli analysis-meta datatable columns-get --project-id N --table-ref "hive.ta.v_event_N"`.

**Column naming**:
- Event table uses `#event_name` (NOT `event_name`), `#event_time` (timestamp), `#account_id` / `#distinct_id` / `#user_id`, and partition columns `$part_date` / `$part_event`.
- Identifiers containing `#`/`$`/`@`/spaces MUST be double-quoted: `"#event_name"`, `"$part_date"`.
- **Event-table SQL MUST include a `"$part_date"` predicate**, or the backend rejects it.

**Use case (the key one for this skill)**: cross-event time alignment that `retention` cannot express natively — e.g. "registered AND drew card on the SAME day". This is exactly L3 retention attribution's behavior×retention. The `relative_event_time` operator does NOT work on datetime user properties (validate passes but runtime returns `PARAMETER_ERROR`), so use SQL with date-aligned CTEs instead.

**Verified "注册当天抽卡 → D1 留存" pattern** (project 2, 2026-09-17 — CORRECTED):

> ⚠️ **CRITICAL — do NOT use user-table `#reg_time` to build the cohort.** The `#reg_time` user-property is NOT date-aligned with the register event's `#event_time` (timezone / delayed-write skew). Building the cohort from `#reg_time` makes D1 retention collapse to ~3.5% when the true value is ~43%. **Always build the cohort from the register EVENT itself** (`#event_name='register'`, `MIN("#event_time")`), then align the target behavior to the same day.

```sql
-- cohort = register event; behavior X on the SAME day as register; D1 = login on reg_date+1
WITH reg AS (
  SELECT "#distinct_id" AS did, CAST(MIN("#event_time") AS DATE) AS reg_date
  FROM hive.ta.v_event_2
  WHERE "#event_name" = 'register' AND "$part_date" >= '2026-09-10' AND "$part_date" <= '2026-09-16'
  GROUP BY "#distinct_id"
),
bhv AS (
  SELECT "#distinct_id" AS did, CAST(MIN("#event_time") AS DATE) AS bhv_date
  FROM hive.ta.v_event_2
  WHERE "#event_name" = 'draw_card' AND "$part_date" >= '2026-09-10' AND "$part_date" <= '2026-09-16'
  GROUP BY "#distinct_id"
),
did_x AS (
  SELECT r.did, r.reg_date FROM reg r JOIN bhv b ON r.did = b.did AND b.bhv_date = r.reg_date
),
d1 AS (
  SELECT "#distinct_id" AS did, CAST("#event_time" AS DATE) AS login_date
  FROM hive.ta.v_event_2
  WHERE "#event_name" = 'login' AND "$part_date" >= '2026-09-10' AND "$part_date" <= '2026-09-17'
)
SELECT COUNT(DISTINCT x.did) AS did_total,
       COUNT(DISTINCT CASE WHEN d.did IS NOT NULL THEN x.did END) AS did_ret
FROM did_x x LEFT JOIN d1 d ON x.did = d.did AND d.login_date = DATE_ADD('day', 1, x.reg_date)
```

**Result (project 2, near-7-days)**: drew card on register day → D1 50.0%; did NOT draw → 29.8%; lift **+20.2pt** (critical behavior). battle_start → +22.1pt but "not-done" arm only 322 users (low sample, per lift thresholds).

**Critical gotchas (all verified 2026-09-17)**:
1. **Join identity = `#distinct_id`**, all within `v_event_N` (never cross event-table ↔ user-table by identity for retention — the two tables' identity values don't line up).
2. **Cohort date = register EVENT's `#event_time`**, never user-table `#reg_time` (skew corrupts retention ~10x).
3. If you MUST reproduce a saved report that uses `#reg_time` (report engine semantics), run it via `report-data run --report-ids`, not ad-hoc SQL — the report engine applies its own time alignment that ad-hoc SQL cannot replicate by copying the filter.

### 4.3.6 Model Type Selection Guide

| Phase | Recommended Model | Reason | Verified? |
|-------|-----------------|--------|-----------|
| **Phase 1** Caliber data-quality check | `event` | Verify caliber event exists + property coverage | ✅ Yes |
| **Phase 2** Feature adoption | `event` | Group by event, count users | ✅ Yes |
| **Phase 2** Retention signal | `retention` | D1 retention needs retention model | ✅ Yes |
| **Phase 3** Path analysis | `path` | Designed for behavior sequences | ✅ Yes |
| **Phase 3** Funnel drop-off | `funnel` | Sequential conversion | ⚠️ Format OK, semantics need validation |
| **Phase 3** Funnel drop-off (fallback) | `event` + manual computation | Compute step counts independently, calculate conversion in post-processing | ✅ Yes |
| **Phase 5** Channel mix | `event` + `groups` | Distribution by channel | ✅ Yes |
| **Phase 5** Geo concentration | `event` + `groups` | Distribution by region | ✅ Yes |
| **L3** Behavior × retention lift | `sql` | Cross-event time alignment (did X on register day) via date-aligned CTE join | ✅ Yes (2026-09-16) |

**Recommendation**: All models are now verified except funnel semantics. For Phase 3 funnel analysis, prefer the `event` model fallback (query each step's user count independently, compute conversion rates in post-processing) until funnel window semantics are clarified. For L3 behavior×retention, use the SQL model (§4.3.5) — the retention `relative_event_time` operator is a dead end.

---

## 5. Common Errors and Fixes

### 5.1 `need_clarification` Error

**Symptom**: `ae-cli` returns `{"error": "need_clarification", "candidates": ["Register", "register"]}`

**Cause**: Event name matches multiple variants (case-sensitive or prefix match).

**Fix**: Use exact display name (often Chinese) or fully qualified name:

```bash
# Instead of: --event-name Register
# Use: --event-name "注册"  (exact display name)
```

### 5.2 `PROJECT_TZ_DISABLED` Error

**Symptom**: `{"error": "PROJECT_TZ_DISABLED", "message": "zone offset not supported"}`

**Fix**: Omit `--zone-offset` flag or pass `99` for local-time mode.

### 5.3 `has_more=true` Truncation

**Symptom**: Result shows `has_more: true` but only 100 rows returned.

**Fix**: Use `export` instead of `run` for full result sets.

### 5.4 Empty Result Set

| Possible Cause | Check |
|---------------|-------|
| Wrong date range | Verify `"$part_date"` values exist in range |
| Wrong event name | Run `event list` to confirm exact name |
| Wrong property name | Run `event get` to confirm property exists |
| Property type mismatch | `is_success = "1"` (string) vs `is_success = 1` (number) |
| Filter too restrictive | Remove filters one by one to isolate |

### 5.5 `Invalid JSON` Error

**Symptom**: `{"error": "Invalid JSON", "message": "unexpected character"}`

**Cause**: Shell escaping breaks JSON quotes, or Chinese characters truncated.

**Fix**: Use Python `json.dump` to write definition to file, then `$(cat file)` to pass.

### 5.6 `INVALID_CAPABILITY_INPUT` / `unknown field` Error

**Symptom**: `{"error": "unknown field metrics", "missing required field attribution", ...}`

**Cause**: Using wrong definition structure for the model type. Each model type has a unique schema.

**Fix**: Consult §4.3 Model Type Definition Formats. Key differences:
- `event` model: `time_range` + `metrics` + `groups`
- `path` model: `time_range` + `path` (with `source_event`, `included_events`, `session_interval`)
- `funnel` model: `time_range` + `funnel` (with `steps`, `window` as object)
- `retention` model: `time_range` + `retention` (with `initial_event` as string, `return_event`)
- `sql` model: `{"sql": "SELECT ..."}` — a single raw-SQL string, NOT structured fields. See §4.3.5 for the exact format and table naming.

### 5.7 `FILTER_OPERATOR_TYPE_INVALID` Error (bool property)

**Symptom**: `request.metrics[N].filters[0].operator: Operator eq is not supported for property type bool; allowed operators: exists, not_exists, is_true, is_false`

**Cause**: Filtering a `bool`-type property (e.g. `is_first_pay`, `is_success`) with `eq`/`ne` and string values.

**Fix**: For bool properties use `is_true` / `is_false` (or `exists` / `not_exists`), with an empty `values` array:

```json
{"field": {"name": "is_first_pay", "type": "event_property"}, "operator": "is_true", "values": []}
```

### 5.8 `CAPABILITY_PERMISSION_DENIED` Error (user-property group)

**Symptom**: `{"error": {"type": "permission", "code": "CAPABILITY_PERMISSION_DENIED", "message": "The current user cannot access project-scoped capabilities for project_id: N"}}` when grouping by a user property.

**Cause**: The current account lacks permission to group by `user_property` in this project. This is a **permission gap, not missing data** — the field exists but you cannot query it.

**Diagnosis (must run before concluding)**: run a control test with a field that exists in BOTH tables (e.g. `channel`):
1. Group by `channel` as `event_property` → succeeds (proves event-property grouping works).
2. Group by `channel` as `user_property` → returns `CAPABILITY_PERMISSION_DENIED` (proves user-property grouping is blocked project-wide).

If BOTH fail → broader capability denial. If only #2 fails → user-property grouping blocked; you cannot split by ANY user property.

**Fix / degrade**: mark the affected dimensions "无权限 (permission denied)" and skip them; do NOT fabricate. Recommend the user grant user-property grouping permission or re-run with an account that has it. Never claim "dimension has no data" — the correct label is "dimension queryable but no permission".

### 5.9 `QUERY_TIMEOUT` Error

**Symptom**: `{"ok": false, "error": {"type": "api", "code": "QUERY_TIMEOUT", "message": "Query timed out"}}` (live-tested 2026-09-17 on project_id=9, retention model over a 7-day window).

**Cause**: Demo/shared environments have heavy ad-hoc load; a retention/path/funnel model scan can exceed the engine timeout even on small windows. This is environmental, not a schema error — the definition is usually correct.

**Fix**:
1. **Retry once** — timeouts are often transient load spikes; a second run on the same definition frequently succeeds.
2. **Narrow the window** — halve the time range, or run cohort-by-cohort instead of one wide sweep.
3. **Fall back to the SQL model** — hand-write the equivalent retention as a self-join on `v_event_{N}` (cohort `register` LEFT JOIN return `login` on `#account_id` + date offset). SQL scans one partition at a time and is far less likely to time out. Verified working: see the D1-retention self-join pattern in §4.3.5.
4. Do NOT interpret `QUERY_TIMEOUT` as "no data" — it means the query did not finish. Retry/narrow/fallback before declaring a metric unavailable.

### 5.10 Missing `$part_date` partition predicate

**Symptom**: `{"code": "QUERY_FAILED", "message": "...When querying the event table [v_event_N], please bring the date partition field with the where condition: $part_date..."}` (live-tested 2026-09-17 on project_id=9).

**Cause**: The Trino engine requires every event-table SQL query to filter on `"$part_date"`; a bare `SELECT * ... WHERE "#event_name"='register'` without a partition predicate is rejected to prevent full-table scans.

**Fix**: Always add `AND "$part_date" >= '{start}' AND "$part_date" <= '{end}'` to event-table SQL. This is already mandated by §6.2 Partition Pruning — treat a missing-predicate rejection as a reminder to comply, not a schema error.

---

## 6. Performance Optimization

### 6.1 Parallel Query Submission

Submit multiple independent queries in one Bash block:

```bash
# Submit all exports in parallel
ae-cli analysis adhoc export --project-id {pid} --model-type sql --definition "$DEF1" | grep run_id > run1.txt &
ae-cli analysis adhoc export --project-id {pid} --model-type sql --definition "$DEF2" | grep run_id > run2.txt &
ae-cli analysis adhoc export --project-id {pid} --model-type sql --definition "$DEF3" | grep run_id > run3.txt &
wait

# Poll all to completion
for run in $(cat run*.txt); do
  ae-cli analysis adhoc run inspect --project-id {pid} --run-id $run
done
```

### 6.2 Partition Pruning

Always include `"$part_date"` in WHERE clause:

```sql
-- Good: uses partition pruning
WHERE "$part_date" BETWEEN '2026-09-01' AND '2026-09-07'

-- Bad: full table scan
WHERE event_time BETWEEN '2026-09-01 00:00:00' AND '2026-09-07 23:59:59'
```

### 6.3 Approximate Functions for Large Data

```sql
-- Use approximate distinct for large datasets (faster, ~2% error)
APPROX_DISTINCT("#distinct_id")

-- Use approximate percentile
APPROX_PERCENTILE(duration, 0.5)
```

---

*File version: 1.4.0 | Last updated: 2026-09-17 | Live-tested on MMO Game Demo (project_id=7) + Social Demo (project_id=8) + 卡牌游戏DEMO (project_id=2) + 游戏DEMO (project_id=9). SQL model verified; retention filters + relative-current-time dead-end documented; bool operator is_true/is_false; CAPABILITY_PERMISSION_DENIED diagnosis; QUERY_TIMEOUT + missing-partition-predicate added; §5.6 sql-model description corrected to raw SQL.*

---

## 7. Degradation Strategy (single source of truth)

When data doesn't meet the ideal conditions, degrade gracefully instead of failing. `SKILL.md` §5 links here.

| Missing / inadequate | Degrade to | Precision impact |
|----------------------|-----------|------------------|
| No dedicated `register` event | Use `first_launch` / `app_open` as the new-user proxy | Over-counts (reinstalls/emulators); ~15-25% inflation |
| No launch event at all | Use earliest event timestamp per `#distinct_id` as first-active proxy | Coarse; may miss true first session |
| No `payment` event | Use `paywall_view` / `store_open` as monetization-readiness proxy | Under-counts actual purchase intent; ~10% |
| No tutorial/feature events | Drop Feature Adoption dimension, renormalize weights to remaining 3 | Composite score less comparable |
| No `channel` property | Skip channel drill-down; note "channel data unavailable" | Phase 5 channel detection not possible |
| No first-day isolation property | Phase 2/3 metrics include returning users; flag "not new-user-isolated" | Blends cohorts, inflates feature adoption |
| Funnel model semantics unclear | Use event model + manual conversion computation (see §4.3.6) | No precision loss, just extra steps |
| Low sample (<50/day) | Aggregate to monthly; suppress daily scores (see §3.1) | Wider confidence intervals |

**Minimum viable data**: one new-user signal event + one identity field (`#account_id` or `#distinct_id`) + `event_time`. Without these, stop and ask the user to confirm the caliber.
