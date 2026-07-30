# Data Validation Logic — ae-cli Implementation

> This file is the **single source of data validation logic**, including event list, property list, metric definitions, quality validation rules, and data access examples.
> SKILL.md Step 2 references this file; definitions are not duplicated elsewhere.

---

## 0.5 Manual Data Export Contract (Fallback Only)

> Used only when ae-cli is unavailable and user provides manual CSV/table export. Currently implemented only via ae-cli — no second platform validated.

Required fields in manual export: `user_id`, `episode_number`/`episode_id`, `play_duration`, `event_time`, `episode_duration` (optional).

---

## 0. Authentication Recovery

If any ae-cli command returns `Cannot obtain token` (expired): run `ae-cli auth login --no-browser --no-wait` → user authorizes at returned URL → run `ae-cli auth login --device-code <code>` → verify with `ae-cli auth status`. Do NOT run other commands until auth is restored.

---

## 1. Data Access Flow

Data source: ThinkingData, accessed via ae-cli tool.

### Command Domain Mapping (⚠️ Important — verified against ae-cli 6.x)

ae-cli commands are distributed across different domains. Use the exact
registered domain and subcommand spelling. Analysis metadata lives under
`analysis-meta`, and current subcommands use space-separated names such as
`event list`; do not translate them into underscore-style legacy spellings.

| Purpose | Correct Command | Domain |
|---------|-----------------|--------|
| List projects | `ae-cli team +list-projects` | team |
| List events | `ae-cli analysis-meta event list --project-id <pid>` | analysis-meta |
| Get event detail (properties) | `ae-cli analysis-meta event get --project-id <pid> --event-name <name>` | analysis-meta |
| Load filter candidate values | `ae-cli analysis filter-value list --project-id <pid> --property-name <property> --table-type event --event-name <name>` | analysis |
| Run SQL query (**recommended**) | `ae-cli analysis adhoc run --model-type sql --project-id <pid> --definition '<sql_json>'` | analysis |
| Run event model query (⚠️ fragile) | `ae-cli analysis adhoc run --model-type event --project-id <pid> --definition '<ai_definition_json>'` | analysis |
| Export async (large data) | `ae-cli analysis adhoc export --model-type sql --project-id <pid> --definition '<sql_json>'` | analysis |
| Inspect async run | `ae-cli analysis run inspect --run-id <run_id>` | analysis |
| Download artifact | `ae-cli analysis artifact download --run-id <run_id> --artifact-id <artifact_id>` | analysis |

> **Common errors**:
> - Omitting `--project-id` from `analysis-meta event list`; the project ID is required.
> - `--model-type event` with raw `events`/`group_by` fields → `definition must use AI-facing model fields; do not pass raw QP field: events`. Rewrite the request with the documented event-model fields; use SQL only when the semantic model cannot express the requirement.
> - `--zone-offset 8` on some projects → `PROJECT_TZ_DISABLED`. Omit the flag or use `99`.

### Recommended Query Path: adhoc run with SQL model

Prefer the event/retention/revenue AI models for supported aggregate questions. The SQL model (`ae-cli analysis adhoc run --model-type sql`) is reserved for user-level detail or unsupported logic and requires prior discovery of authorized tables and columns. An error about `events` or `group_by` means raw QP fields were supplied; it is not evidence that the event model itself is unreliable.

> **⚠️ Concurrency limit**: adhoc SQL queries have a concurrent upper bound of ~3-5 per project. When running multiple T1–T5 templates in a batch, execute serially or in small batches of ≤3 to avoid `rate limit` / `too many concurrent queries` errors.

Full parameters:

**⚠️ Standard execution: use heredoc temp file to avoid shell escaping hell.** Do NOT inline `--definition '{...}'` in shell — SQL single quotes + JSON double quotes + shell single quotes create 3-layer nesting that breaks easily.

```bash
# Step 1: write SQL JSON to temp file via heredoc (single-quoted EOF disables variable expansion)
cat > /tmp/ae_query.json <<'EOF'
{"sql":"SELECT \"episode_no\", COUNT(*) AS cnt FROM v_event_1642 WHERE \"$part_date\" = '2026-06-15' AND \"$part_event\" = 'playlet_start' GROUP BY \"episode_no\""}
EOF

# Step 2: pass file content as --definition
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type sql \
  --definition "$(cat /tmp/ae_query.json)" \
  --format json
```

Key points of the heredoc pattern:
- `<<'EOF'` (single-quoted EOF) → variable expansion disabled, so JSON `\"` and SQL `'` work as-is
- SQL single quotes (string literals like `'2026-06-15'`) need NO escaping
- JSON double quotes around column names need `\"` only because they're inside the JSON string value
- `--definition "$(cat /tmp/file.json)"` reads file content as the parameter value

**Output parsing template** (ae-cli prints a `[ae-cli] dispatching...` prefix line before JSON):

```bash
# Pipe to python, find first line starting with { or [
# ⚠️ Assumes ae-cli 6.x JSON output format (data.data.rows). If using other versions,
# verify the JSON path with: ae-cli ... | python3 -c "import sys,json; print(json.dumps(json.loads(sys.stdin.read().split('{',1)[1].rsplit('}',1)[0].join(['{','}'])))  # fallback: inspect raw structure
ae-cli ... 2>&1 | python3 -c "
import sys, json
lines = sys.stdin.read().split('\n')
start = next(i for i, l in enumerate(lines) if l.strip().startswith(('{', '[')))
data = json.loads('\n'.join(lines[start:]))
print(json.dumps(data['data']['rows'], indent=2, ensure_ascii=False))
"
```

**Inline alternative** (only for very short queries, not recommended):
```
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type sql \
  --definition '{"sql":"SELECT ... FROM v_event_<pid> WHERE \"$part_date\" BETWEEN '\''<start>'\'' AND '\''<end>'\'' ... "}' \
  --limit 1000 \
  --timeout-seconds 180 \
  --format json
```

**Key parameter notes:**

- `--project-id` / `-p`: Numeric project ID
- `--definition`: JSON object with `sql` key. The SQL string must:
  - Use `v_event_<pid>` (NOT `hive.ta.v_event_<pid>`) as the table name
  - Use `"$part_event"` (NOT `"#event_name"`) for event name filtering
  - Use `"$part_date"` for date partition filtering (mandatory — queries without it are rejected)
  - Use `"#account_id"` / `"#distinct_id"` for user identifiers (quote with double quotes — `#` requires delimiting)
  - With heredoc pattern: SQL single quotes need no escaping; with inline pattern: must be `'\''`
- `--limit`: Max 1000 inline rows. For larger data, use `ae-cli analysis adhoc export` (async gzip artifact)
- `--timeout-seconds`: Max 180
- `--zone-offset`: **Omit by default**. Some projects reject it with `PROJECT_TZ_DISABLED`. If needed, use `99` for local-time mode.

**⚠️ Output parsing**: ae-cli prints a `[ae-cli] dispatching capability=... request_id=...` line before JSON. Strip non-JSON lines when piping to a parser — see the parsing template above.

**Drama name discovery**: Before writing SQL filters, confirm the drama's exact stored name and ID:
```
ae-cli analysis filter-value list --project-id <pid> --property-name "video_name" --table-type event --event-name <event> --search-prefix "<drama_name_keyword>"
```
This returns candidate values like `1765:实习生菜菜` (format: `video_id:video_name`). Use the `video_id` value in SQL filters: `AND "video_id" = '1765'` or `AND "video_name" LIKE '%实习生菜菜%'`.

### ⚠️ Property List Must Be Fully Paginated

The event `get` command returns ALL event properties in one call (no pagination needed). However, when listing events via `analysis-meta event list`, results may paginate — check the total count.

**Correct command for properties**: `ae-cli analysis-meta event get --project-id <pid> --event-name <name>` → returns `event_props` array with all properties.

**Known case**: The short-drama demo project's EpisodeExpose event has 47+ properties including `episode_no`, `is_vip_episode`, `video_id`, `video_name`, `watch_time`, `video_duration`. These are all returned in a single `event get` call.

### Event Name Auto-Matching

Different projects use different event names (e.g., "play" may be called `EpisodeExpose`/`watch_episode`/`play_start`). **Prioritize auto-matching common naming patterns**; only confirm with user when no match is found:

| Standard Event | Common Naming Variants |
|----------------|----------------------|
| play_start (start play) | `playlet_start`, `episode_start`, `watch_episode`, `play_start`, `EpisodeExpose` |
| play_end (exit/end) | `playlet_end`, `episode_end`, `play_end`, `watch_end`, `EpisodeQuit` |
| Completion | `playlet_actual_end`, `episode_complete`, `play_complete` |
| Paywall display | `pay_wall_show`, `paywall_show`, `paywall_display` |
| Paywall click | `pay_wall_click`, `paywall_click` |
| Recommend impression | `recommend_show`, `recommend_display`, `impression` |
| Recommend click | `recommend_click`, `click` |

> Use `ae-cli analysis-meta event list --project-id <pid>` to query the full event list, then auto-match per the table above. Only confirm with user when multiple candidates match.
>
> **Drama name discovery**: After identifying the play-start/play-end event, search for the target drama's `video_id` and exact `video_name` stored value:
> ```
> ae-cli analysis filter-value list --project-id <pid> --property-name "video_name" --table-type event --event-name <event_name> --search-prefix "<keyword>"
> ```
> Returns values like `1765:实习生菜菜` (format: `video_id:video_name`). Use `video_id` in SQL filters for precision.

---

## 2. Required Event List

| Event | Trigger Timing | Analysis Purpose | Required |
|-------|---------------|-----------------|----------|
| `click` / `impression` / `recommend_show` | User sees ad/cover and clicks | Layer 1: Impression CTR | Optional |
| `play_start` (see §1 event name auto-match) | User clicks play button | Layer 1: Start-play rate; All layers: Day0 baseline | **Required** |
| `play_end` (see §1 event name auto-match) | User stops/exits playback (includes play_duration) | All layers: Completion rate, per-episode retention, churn rate | **Required** |

**Confirmation step**: Query with `ae-cli analysis-meta event list --project-id <pid>`, then map per §1 event name auto-match table. Only confirm with user when all common naming variants fail to match.

---

## 3. Event Property List

### Core Properties (Required)

| Property | Description | Missing Handling |
|----------|-------------|-----------------|
| `episode_no` | Episode number, basis for per-episode analysis | **Blocking**: Cannot perform per-episode analysis, downgrade to overall trend |
| `watch_time` / `play_duration` | Watch time in seconds (⚠️ check semantics: cumulative vs single-session) | **Conditional Degradable**: Check for `end_type`/`exit_type` enum on play_end event — if present, degrade to end_type-based completion proxy (see §4 fallback). If no end_type either, then **Blocking**: downgrade to start-play rate + retention trend |
| `end_type` / `exit_type` | Exit type enum on play_end event (values: `next`, `manual_next`, `auto_next`, `exit`) | **Conditional**: Not required when `play_duration` exists. Used as completion proxy when `play_duration`/`watch_time` absent (see §4 fallback definition) |
| `video_duration` / `episode_duration` | Total episode duration in seconds | **Blocking**: Cannot calculate completion rate |
| `#account_id` / `#distinct_id` | User/device identifier | **Blocking**: Cannot perform retention analysis |
| `video_name` / `video_id` | Drama name/ID for filtering | **Blocking**: Cannot filter to specific drama |

### Commercialization Properties (Optional)

| Property | Description | Missing Handling |
|----------|-------------|-----------------|
| `is_paid` / `is_locked` | Whether this episode is a paid episode | Skip Layer 4 paywall analysis |
| `ad_shown` | Whether ad was displayed | Skip Layer 4 ad frequency analysis |
| `is_vip_user` | Whether user is a paid member | Skip paid vs free segment comparison |

### Traffic Properties (Optional)

| Property | Description | Missing Handling |
|----------|-------------|-----------------|
| `channel` / `source` | Traffic source channel | Skip Layer 1 per-channel analysis |

### Drill-Down Properties (Phase 2, On Demand)

| Property | Description | Corresponding Dimension |
|----------|-------------|------------------------|
| `user_source` / `user_segment` | User source / segment tag | Dim A Segment |
| `share_action` | Share behavior event | Dim C Social |
| `danmaku_count` | Danmaku count | Dim C Social |
| `genre_tag` | Genre tag | Dim D Genre Comparison |

---

## 4. Metric Calculation Definitions

| Metric | Default Definition | Notes | Items Requiring User Confirmation |
|--------|-------------------|-------|----------------------------------|
| Completion rate | `play_duration ≥ episode_duration × 80%` | Default ≥80% is completion. **⚠️ Watch-time semantics matter**: some projects' `watch_time`/`play_duration` records **cumulative** viewing time (including replays/re-watches), not single-session progress. If watch_time values frequently exceed video_duration (e.g., ratios >100% are common, not rare outliers), the standard progress-based completion rate cannot be computed. In this case, fall back to: `watch_time ≥ video_duration` (cumulative coverage = at least one full viewing of the episode). Label the report with the alternative definition used. **⚠️ Field-absent fallback**: if `play_duration`/`watch_time`/`play_progress` are ALL null/missing (common when tracking is not implemented), check for an `end_type`/`exit_type` enum field on the play_end event. If present, use: completion ≈ `(end_type IN ('next','manual_next','auto_next')) / total` (user continued to next episode = implicit completion); mid-episode exit rate ≈ `end_type = 'exit' / total`. Label report: "⚠️ Field degraded: play_duration absent, using end_type as proxy — precision lower than standard definition." | Completion threshold (some teams use 70% or 90%); watch_time semantics (single-session vs cumulative) |
| Valid view | `watch_time ≥ 30s OR watch_time ≥ video_duration × 30%` | Either condition | Threshold standard |
| Start-play rate | `play_start / click` or `play_start / impression` | Base is click or impression | **Must confirm**; when no click/impression data, use play_start UV as Day0 baseline, label "start-play rate unavailable, using Day0 UV as substitute" |
| Per-episode retention | Relative to E1: `Users who completed Ei / Users who completed E1` | E1 = 100% baseline | Base is E1 or Day0 total |
| D1 retention | `Day0 first play_start, then Day1 has play_start` | First = first playback in this drama | Day0 definition (calendar day or 24h after install) |
| Same-day cross-drama viewing rate | `Day0 finished this drama + same-day other drama play_start` / Day0 total | Short-drama mandatory check: ≥15% means D1 may be distorted | — |
| Non-completer D1 retention | D1 excluding Day0 full-completion users | Vertical micro-short drama desensitization-specific metric | — |
| 7-day user re-engagement rate | `Any play_start during D1-D7` / Day0 total | Layer 5 long-term metric | — |

---

## 4.5 Empty Result Set Handling

An ae-cli query can **succeed yet return 0 rows** — the most common real-world anomaly. Never interpret an empty result as "retention = 0%" or any other metric value.

**When a query returns 0 rows:**

1. **Verify query parameters first** — in this order:
   - Time range: is `start_time`/`end_time` correct and within the data availability window? (`relative_date_range` returns empty data in some projects — always use absolute times, see §1)
   - Episode/drama filter: does the `episode_id`/`playlet_id` value actually exist? (e.g., filter value typo, wrong format `playlet_1006` vs `1006`)
   - Event name: is the queried event the correctly auto-matched one (see §1 event name auto-match table)?
2. **Re-probe with a wider net**: remove filters and query the same event for a recent 7-day window. If data appears, the issue was parameter-level; if still empty, the event itself has no data in this project.
3. **Confirm with the user** before proceeding: report exactly which query returned empty, what was verified, and ask for corrected parameters (time range / drama ID / event name).
4. **Hard constraint**: NEVER run root-cause attribution on an empty result set. An empty result means "no data retrieved", not "metric is zero". Every downstream metric derived from an empty query must be labeled "data unavailable".

---

## 5. Data Quality Validation Matrix

Before executing analysis, check each validation item and record results:

| Check Item | Pass Standard | Missing Handling | Affected Analysis Layers |
|------------|--------------|-----------------|------------------------|
| `episode_no` exists | Any field has values | **Blocking**: Downgrade to overall trend analysis | L2/L3/L4 all downgraded |
| `play_duration`/`watch_time` exists | Field has values and >0 | **Conditional Degradeable**: (1) Check for `end_type`/`exit_type` enum field on play_end event — if present, degrade to end_type-based completion proxy (see §4 completion rate fallback definition). (2) If no end_type either, then **Blocking**: downgrade to start-play rate + retention trend. All completion rate metrics labeled with degradation method used. | All completion rate metrics degraded or unavailable |
| `play_duration`/`watch_time` semantics | Check if watch_time exceeds video_duration frequently (ratio >100%). If yes, watch_time is cumulative (incl. replays), not single-session progress. | Label as "cumulative watch time"; fall back to `watch_time ≥ video_duration` for completion; flag that standard 80% progress completion rate is unavailable | L3 completion rate degraded |
| `user_id` exists | Field has values | **Blocking**: Cannot perform retention calculation | L1-L5 all blocked |
| Sample size ≥ 100 | play_start UV ≥ 100 during analysis period | **Degrade** (see §5.1 Low-Sample Degradation Path) | All layers labeled "⚠️ low sample" |
| `channel` exists | Field has values | Skip per-channel analysis, label | L1 partial functionality unavailable |
| `is_paid`/`is_locked`/`is_vip_episode` exists | Any field has values | Skip paywall analysis, label | L4 paywall analysis unavailable |
| `ad_shown` exists | Field has values | Skip ad frequency analysis, label | L4 ad analysis unavailable |
| `is_vip_user`/`user_status` exists | Field has values | Skip paid vs free segment comparison, label | L4/Dim A partially unavailable |

**Validation results** should be noted in Phase 1 report's "Data Source" row. Unavailable drill-down options in the menu should be labeled "⚠️ Data unavailable".

### 5.1 Low-Sample Degradation Path (UV < 100)

When play_start UV < 100 during the analysis period, a bare "⚠️ low sample" warning is NOT enough — per-episode metrics become statistically meaningless and MUST be actively degraded:

| Analysis Item | Degradation Rule |
|---------------|------------------|
| Per-episode churn ranking (Top3) | **Skip entirely**. With UV<100, a single user = 2+ percentage points; churn "inflection points" are noise. Report only drama-level aggregate churn. |
| Health label | **Force `Insufficient data`** (see `references/episode_churn_table.md`). Do NOT fire any of the 4 diagnostic labels regardless of metric values. |
| Per-episode completion / retention | **Aggregate to drama-level** coarse granularity (start-play rate, overall D1, rough 3-episode retention). No per-episode curves. |
| Root-cause rules | **Do NOT fire any rule** whose trigger relies on per-episode metrics (R2-x, R3-x, R3-Sx, R4-1...). Layer 1 traffic rules on aggregate metrics may still fire with ⚠️ label. |
| All reported metrics | Every number carries the ⚠️ low-sample label plus the actual UV: "⚠️ UV=49, directionally indicative only". |

**Escalation**: always suggest expanding the time range first. Only degrade if the user confirms the range cannot be expanded (e.g., drama launched recently).

### 5.2 Data Authenticity Sanity Check (Demo / Synthetic Data Detection)

Demo projects and synthetic datasets produce data that passes field-level validation but does NOT reflect real business shapes. Attributing churn causes from such data produces garbage conclusions. Before Phase 1 analysis, run these checks on the retrieved data:

| # | Check | Synthetic/Demo Signature | Real-World Expectation |
|---|-------|--------------------------|------------------------|
| 1 | Episode numbering monotonicity | `episode_no` scattered non-contiguous (e.g., 48 distinct values spread randomly across 1–143) | Real dramas: episodes numbered contiguously 1..N; per-episode UV decays monotonically-ish with episode number |
| 2 | VIP/paywall marker position | `is_vip_episode` flagged on episode 1, or on ALL episodes, or randomly | Paywall starts mid-drama (typically ep 8–30); episodes before paywall are uniformly free |
| 3 | Funnel ordering | Recharge funnel has click ≈ exposure, or later stage > earlier stage (inverted funnel) | Real funnels strictly decrease: exposure > click > success |
| 4 | Failure event ratio | `EpisodeRequestFail` / error events >10% of play events | Real products: request failure typically <2%; >10% suggests synthetic error injection |
| 5 | User behavior diversity | All users show identical watch patterns (same episodes, same durations) | Real users show heterogeneous paths |

**Handling when ≥2 checks fire:**
1. **STOP attribution** — do NOT run root-cause rules on this data
2. Report to the user: "Data shows synthetic/demo signatures (list which checks fired). Analysis conclusions would not reflect real business performance."
3. Offer two paths: (a) user confirms it IS a demo environment → proceed with explicit "demo data" disclaimer on every conclusion, treating output as pipeline validation only; (b) user believes data is real → investigate tracking/ETL issues first.

**1 check firing alone** → label the anomaly in the report's Data Source row and proceed with caution; do not stop.

### ⚠️ Property Validation Prerequisite

Before executing the above validation matrix, you must complete the **full pagination query** of the property list (see §1). If you only check the first page (limit=50) and then judge "property does not exist", you will get false negatives — core properties (e.g., episode_no, is_vip_episode) may be on the second page or later.

---

## 6. Data Gap Report Format

When data validation discovers gaps, use the following format in the report:

```
⚠️ Data Gap Description:
- Missing field: {field_name}
- Skipped analysis: {Layer X / Drill-down dimension} — {reason}
- Downgrade plan: {alternative analysis method, or "this layer cannot be analyzed"}
```
