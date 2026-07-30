# SQL Templates — Short Drama Retention Metrics

> **Recommended query path.** These SQL templates work both via `ae-cli analysis adhoc run --model-type sql` and via direct Hive/Presto/Trino access.
> This file is the **single source of data retrieval SQL**. All metric queries use these templates; do not hand-write ad-hoc SQL.
> SQL dialect: Presto/Trino. Adapt function names if running on other engines.
>
> **⚠️ Field name portability**: Templates use the field names verified on the ThinkingData short-drama demo project (ae-cli SQL model). When using direct Hive access, the event-name column is `"#event_name"` (not `"$part_event"`). When using ae-cli SQL model, it is `"$part_event"`. User ID via ae-cli is `"#account_id"` / `"#distinct_id"`; via direct Hive it may be `"#user_id"`. Always run §0.1 discovery queries first to confirm field names per environment.

---

## 0. Conventions & Placeholders

All templates use these placeholders — replace before execution:

| Placeholder | Meaning | Example |
|-------------|---------|---------|
| `<pid>` | ThinkingData project ID | `1234` |
| `<start>` / `<end>` | Analysis date range (inclusive, `yyyy-MM-dd`) | `2026-06-10` / `2026-07-10` |
| `<drama_filter>` | Complete AND clause for drama scoping (include table alias if query uses aliases). Never wrap in outer quotes — paste directly into WHERE. | `AND t."playlet_id"='playlet_1006'` or `AND "video_name" LIKE '%厉总%'` |
| `<drama>` | Drama name pattern for LIKE matching | `%厉总%` |
| `<ep>` | Episode number | `3` |
| `<n>` | Episode count threshold | `3` / `7` |
| `<paywall_ep>` | First paid episode number (from drama-type-configs.md paywall range) | `30` |
| `<finale_ep>` | Last episode number (= total episode count) | `80` |
| `<last_free_ep>` | Last free episode (= `<paywall_ep>` - 1) | `29` |

**Table & field conventions:**
- Event table: `v_event_<pid>` (via `ae-cli analysis adhoc run --model-type sql`). When using direct Hive/Presto/Trino access (not ae-cli), the full path is `v_event_<pid>`.
- Partition column: `"$part_date"` — **mandatory** in every query (full-table scans are rejected)
- Event name column: `"$part_event"` (via ae-cli SQL model). When using direct Hive access, the column is `"$part_event"`.
- User column: `"#account_id"` (logged-in users) or `"#distinct_id"` (device-level, includes anonymous). Use `"#distinct_id"` for UV counting when login rate is low.
- Event time: `"#event_time"`
- Play-start/play-end event names: **must be discovered via §0.1 first — never hardcode.** Common pairs include `playlet_start`/`playlet_end` (programmatic), `EpisodeExpose`/`EpisodeQuit` (demo projects), `watch_episode`/`watch_end`. The auto-match table is in `data-validation.md §1`. Substitute the discovered names into all `"$part_event" = '<event_name>'` filters below.
- Episode number column defaults to `episode_no`; alternatives: `episode_number`. Confirm via §0.1.
- Watch time column: `watch_time` (cumulative) or `play_duration` (single-session). Confirm semantics — see `data-validation.md §4`.
- Video duration column: `video_duration`.
- Drama name column: `video_name`; drama ID column: `video_id`. Filter using `video_id` for precision, or `video_name LIKE '%<keyword>%'` for fuzzy matching.
- Filters referencing the outer table use alias `t.`; inner subqueries use their own aliases — keep the `<drama_filter>` alias consistent with the query it's pasted into.
- **Type casting**: TA stores most properties as strings — always `CAST(... AS INTEGER/DOUBLE)` before arithmetic. Guard division with `NULLIF`.
- **Identifier delimiting**: Column names containing `#`, `$`, `@`, spaces, or punctuation MUST be wrapped in double quotes: `"#account_id"`, `"$part_date"`, `"$part_event"`. Single quotes are string literals: `'EpisodeQuit'`.

### 0.1 Discovery Queries (run first, every new project)

```sql
-- Event names in project (confirm play-start / play-end / paywall event names)
-- ae-cli: ae-cli analysis adhoc run --model-type sql -p <pid> --definition '{"sql":"..."}'
SELECT "$part_event", COUNT(*) AS cnt
FROM v_event_<pid>
WHERE "$part_date" BETWEEN '<start>' AND '<end>'
GROUP BY "$part_event"
ORDER BY cnt DESC
LIMIT 100;

-- Property names on the play-start event (confirm episode-number / drama-id column names)
SELECT *
FROM v_event_<pid>
WHERE "$part_date" = '<end>'
  AND "$part_event" = 'EpisodeExpose'
LIMIT 5;
```

> Match discovered names against the auto-match table in `data-validation.md §1`, then substitute into all templates below.
>
> **Drama name discovery via ae-cli** (faster than SQL scan):
> ```
> ae-cli analysis filter-value list --project-id <pid> --property-name "video_name" --table-type event --event-name EpisodeExpose --search-prefix "<keyword>"
> ```
> Returns values like `1765:实习生菜菜`. Use `video_id` in SQL filters for precision.

---

## 1. Layer 1 — Traffic

### T1.1 Day0 New Viewers (base cohort)

```sql
-- Day0 new viewers: users whose FIRST play-start of this drama falls within the range
WITH first_touch AS (
  SELECT "#distinct_id", DATE(MIN("#event_time")) AS d0
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY "#distinct_id"
)
SELECT d0, COUNT(*) AS new_uv
FROM first_touch
GROUP BY d0
ORDER BY d0;
```

### T1.2 D1 Retention (self-join on per-user first-touch date)

```sql
-- D1 retention: Day0 users who return on Day1
WITH d0 AS (
  SELECT "#distinct_id", DATE(MIN("#event_time")) AS d0
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY "#distinct_id"
)
SELECT
  COUNT(DISTINCT d0."#distinct_id") AS d0_uv,
  COUNT(DISTINCT t."#distinct_id") AS d1_uv,
  COUNT(DISTINCT t."#distinct_id") * 1.0 / COUNT(DISTINCT d0."#distinct_id") AS d1_rate
FROM d0
LEFT JOIN v_event_<pid> t
  ON t."#distinct_id" = d0."#distinct_id"
  AND DATE(t."#event_time") = d0.d0 + INTERVAL '1' DAY
  AND t."$part_event" = 'EpisodeExpose'
  AND <drama_filter>;
```

> D7 / D30 retention: copy T1.2 and change `INTERVAL '1' DAY` to `'7'` / `'30'`.

### T1.3 Same-Day Cross-Drama Viewing Rate (micro-short desensitization metric)

```sql
-- Share of Day0 completers who also watched OTHER short dramas on the same day.
-- ≥15% means D1 is structurally suppressed (see drama-type-configs.md §Vertical Micro-Short Drama).
WITH d0 AS (
  SELECT "#distinct_id", DATE(MIN("#event_time")) AS d0
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY "#distinct_id"
),
same_day AS (
  SELECT u."#distinct_id", u.d0,
    MAX(CASE WHEN t."video_name" NOT LIKE '<drama>' THEN 1 ELSE 0 END) AS other
  FROM d0 u
  LEFT JOIN v_event_<pid> t
    ON t."#distinct_id" = u."#distinct_id"
    AND DATE(t."#event_time") = u.d0
    AND t."$part_event" = 'EpisodeExpose'
  GROUP BY u."#distinct_id", u.d0
)
SELECT
  COUNT(*) AS d0_uv,
  SUM(CASE WHEN other > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS cross_rate
FROM same_day;
```

### T1.4 Per-Channel Start-Play & D1 (channel quality stratification)

```sql
-- Per-channel start-play UV + D1 retention (requires channel/source property)
WITH d0 AS (
  SELECT "#distinct_id",
         DATE(MIN("#event_time")) AS d0,
         arbitrary("channel") AS channel
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY "#distinct_id"
)
SELECT
  d0.channel,
  COUNT(DISTINCT d0."#distinct_id") AS d0_uv,
  COUNT(DISTINCT t."#distinct_id") * 1.0 / COUNT(DISTINCT d0."#distinct_id") AS d1_rate
FROM d0
LEFT JOIN v_event_<pid> t
  ON t."#distinct_id" = d0."#distinct_id"
  AND DATE(t."#event_time") = d0.d0 + INTERVAL '1' DAY
  AND t."$part_event" = 'EpisodeExpose'
  AND <drama_filter>
GROUP BY d0.channel
ORDER BY d0_uv DESC;
```

---

## 2. Layer 2 — Opening

### T2.1 Per-Episode Start & Completion (E1–E3 focus)

```sql
-- Per-episode start UV, completion UV, completion rate.
-- Completion = exit event with watch_time ≥ video_duration × 80% (or watch_time ≥ video_duration if cumulative)
-- (see data-validation.md §4 for threshold confirmation).
WITH exits AS (
  SELECT
    "#distinct_id",
    CAST("episode_no" AS INTEGER) AS ep,
    MAX(CASE
          WHEN CAST("watch_time" AS DOUBLE) >= CAST("video_duration" AS DOUBLE) * 0.8
          THEN 1 ELSE 0 END) AS completed
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeQuit'
    AND <drama_filter>
  GROUP BY "#distinct_id", CAST("episode_no" AS INTEGER)
)
SELECT
  ep,
  COUNT(*) AS start_uv,
  SUM(completed) AS complete_uv,
  SUM(completed) * 1.0 / COUNT(*) AS completion_rate
FROM exits
GROUP BY ep
ORDER BY ep;
```

> If no exit event exists, approximate completion from the start event's `play_duration` property directly (same formula, `"$part_event"='EpisodeExpose'`).

#### T2.1-Fallback: end_type-based completion (when play_duration/watch_time is null)

> Use this version when data-validation.md §5 matrix shows `play_duration`/`watch_time` all null but `end_type`/`exit_type` enum exists on play_end event. Precision is lower than the standard definition — label report accordingly.

```sql
-- end_type-based completion proxy: next/manual_next = completed, exit = hard-exit
-- ⚠️ Replace "episode_no" with the discovered field name from §0.1 if different
WITH exits AS (
  SELECT
    "#distinct_id",
    CAST("episode_no" AS INTEGER) AS ep,
    MAX(CASE
          WHEN "end_type" IN ('next', 'manual_next', 'auto_next')
          THEN 1 ELSE 0 END) AS completed,
    MAX(CASE WHEN "end_type" = 'exit' THEN 1 ELSE 0 END) AS hard_exit
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = '<play_end_event>'
    AND <drama_filter>
  GROUP BY "#distinct_id", CAST("episode_no" AS INTEGER)
)
SELECT
  ep,
  COUNT(*) AS start_uv,
  SUM(completed) AS complete_uv,
  SUM(completed) * 1.0 / COUNT(*) AS completion_rate,
  SUM(hard_exit) AS hard_exit_uv,
  SUM(hard_exit) * 1.0 / COUNT(*) AS hard_exit_rate
FROM exits
GROUP BY ep
ORDER BY ep;
```

### T2.2 3-Episode / 7-Episode Retention (industry golden metric)

```sql
-- Users who completed ≥<n> episodes / Day0 new viewers
WITH d0 AS (
  SELECT "#distinct_id", DATE(MIN("#event_time")) AS d0
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY "#distinct_id"
),
completed_eps AS (
  SELECT t."#distinct_id", COUNT(DISTINCT CAST(t."episode_no" AS INTEGER)) AS eps_done
  FROM d0
  JOIN v_event_<pid> t
    ON t."#distinct_id" = d0."#distinct_id"
    AND t."$part_event" = 'EpisodeQuit'
    AND <drama_filter>
    AND CAST(t."watch_time" AS DOUBLE) >= CAST(t."video_duration" AS DOUBLE) * 0.8
  GROUP BY t."#distinct_id"
)
SELECT
  (SELECT COUNT(*) FROM d0) AS d0_uv,
  COUNT(*) AS retained_uv,
  COUNT(*) * 1.0 / (SELECT COUNT(*) FROM d0) AS retention_rate
FROM completed_eps
WHERE eps_done >= <n>;
```

> `<n>` = 3 for 3-episode retention (free→paid dividing line), 7 for 7-episode retention (paying user core).

---

## 3. Layer 3 — Plot

### T3.1 Per-Episode Churn (viewers of ep N who never reach ep N+1)

```sql
-- Per-episode churn rate: completed ep N but never started ep N+1
WITH ep_users AS (
  SELECT DISTINCT "#distinct_id", CAST("episode_no" AS INTEGER) AS ep
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
),
churn AS (
  SELECT a.ep,
    COUNT(*) AS viewers,
    COUNT(b."#distinct_id") AS continued
  FROM ep_users a
  LEFT JOIN ep_users b
    ON b."#distinct_id" = a."#distinct_id" AND b.ep = a.ep + 1
  GROUP BY a.ep
)
SELECT
  ep,
  viewers,
  continued,
  (viewers - continued) * 1.0 / viewers AS churn_rate
FROM churn
ORDER BY ep;
```

### T3.2 In-Episode Viewing Progress (content appeal per episode)

```sql
-- Average viewing progress per episode (0~1); low progress + high churn = content problem
SELECT
  CAST("episode_no" AS INTEGER) AS ep,
  COUNT(*) AS uv,
  AVG(CAST("watch_time" AS DOUBLE) / CAST("video_duration" AS DOUBLE)) AS avg_progress,
  approx_percentile(CAST("watch_time" AS DOUBLE) / CAST("video_duration" AS DOUBLE), 0.5) AS median_progress
FROM v_event_<pid>
WHERE "$part_date" BETWEEN '<start>' AND '<end>'
  AND "$part_event" = 'EpisodeQuit'
  AND <drama_filter>
  AND CAST("video_duration" AS DOUBLE) > 0
GROUP BY CAST("episode_no" AS INTEGER)
ORDER BY ep;
```

#### T3.2-Fallback: end_type-based exit analysis (when play_duration/watch_time is null)

> Use when play_duration/watch_time all null but end_type exists. Replaces progress-based analysis with exit-type distribution per episode.

```sql
-- Per-episode end_type distribution; high exit ratio = content problem (same signal as low progress)
-- ⚠️ Replace "episode_no" with the discovered field name from §0.1 if different
SELECT
  CAST("episode_no" AS INTEGER) AS ep,
  COUNT(*) AS uv,
  SUM(CASE WHEN "end_type" IN ('next','manual_next','auto_next') THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS continue_rate,
  SUM(CASE WHEN "end_type" = 'exit' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS hard_exit_rate
FROM v_event_<pid>
WHERE "$part_date" BETWEEN '<start>' AND '<end>'
  AND "$part_event" = '<play_end_event>'
  AND <drama_filter>
GROUP BY CAST("episode_no" AS INTEGER)
ORDER BY ep;
```

```sql
-- Segment retention: users reaching each segment / Day0 users.
-- Segment boundaries from drama-type-configs.md (paywall position varies by drama).
WITH d0 AS (
  SELECT "#distinct_id"
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY "#distinct_id"
),
max_ep AS (
  SELECT t."#distinct_id", MAX(CAST(t."episode_no" AS INTEGER)) AS max_ep
  FROM d0
  JOIN v_event_<pid> t
    ON t."#distinct_id" = d0."#distinct_id"
    AND t."$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY t."#distinct_id"
)
SELECT
  COUNT(*) AS d0_uv,
  SUM(CASE WHEN max_ep >= 4 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pass_opening,     -- E1-E3 → E4
  SUM(CASE WHEN max_ep >= <paywall_ep> THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS reach_paywall,
  SUM(CASE WHEN max_ep >= <paywall_ep> + 5 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pass_paywall,
  SUM(CASE WHEN max_ep >= <finale_ep> THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS reach_finale
FROM max_ep;
```

---

## 4. Layer 4 — Commercialization

### T4.1 Paywall Conversion (free→paid at paywall boundary)

```sql
-- Paywall blocking: viewers of last free ep vs viewers of first paid ep
WITH ep_users AS (
  SELECT DISTINCT "#distinct_id", CAST("episode_no" AS INTEGER) AS ep
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
)
SELECT
  SUM(CASE WHEN ep = <last_free_ep> THEN 1 ELSE 0 END) AS free_ep_uv,
  SUM(CASE WHEN ep = <last_free_ep> + 1 THEN 1 ELSE 0 END) AS paid_ep_uv,
  SUM(CASE WHEN ep = <last_free_ep> + 1 THEN 1 ELSE 0 END) * 1.0
    / NULLIF(SUM(CASE WHEN ep = <last_free_ep> THEN 1 ELSE 0 END), 0) AS paywall_pass_rate
FROM ep_users
WHERE ep IN (<last_free_ep>, <last_free_ep> + 1);
```

### T4.2 Mid-Episode Exit Rate (non-content loss detector)

```sql
-- Mid-episode exits: exit events with progress between 20%~80%
-- High rate on episodes without plot turning points → ads/crash/product issues (R4-2)
SELECT
  CAST("episode_no" AS INTEGER) AS ep,
  COUNT(*) AS exits,
  SUM(CASE
        WHEN CAST("watch_time" AS DOUBLE) / CAST("video_duration" AS DOUBLE)
             BETWEEN 0.2 AND 0.8
        THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS mid_exit_rate
FROM v_event_<pid>
WHERE "$part_date" BETWEEN '<start>' AND '<end>'
  AND "$part_event" = 'EpisodeQuit'
  AND <drama_filter>
  AND CAST("video_duration" AS DOUBLE) > 0
GROUP BY CAST("episode_no" AS INTEGER)
ORDER BY ep;
```

#### T4.2-Fallback: end_type-based exit rate (when play_duration/watch_time is null)

> Use when play_duration/watch_time all null. Replaces progress-based mid-exit with end_type='exit' ratio.

```sql
-- Hard exit rate via end_type: exit = user left mid-episode without continuing
-- High rate on episodes without plot turning points → ads/crash/product issues (R4-2)
-- ⚠️ Replace "episode_no" with the discovered field name from §0.1 if different
SELECT
  CAST("episode_no" AS INTEGER) AS ep,
  COUNT(*) AS exits,
  SUM(CASE WHEN "end_type" = 'exit' THEN 1 ELSE 0 END) AS hard_exit,
  SUM(CASE WHEN "end_type" = 'exit' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS hard_exit_rate
FROM v_event_<pid>
WHERE "$part_date" BETWEEN '<start>' AND '<end>'
  AND "$part_event" = '<play_end_event>'
  AND <drama_filter>
GROUP BY CAST("episode_no" AS INTEGER)
ORDER BY ep;
```

---

## 5. Layer 5 — Long-term

### T5.1 Full-Drama Retention

```sql
-- Users who completed the finale / Day0 new viewers
WITH d0 AS (
  SELECT "#distinct_id"
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY "#distinct_id"
)
SELECT
  (SELECT COUNT(*) FROM d0) AS d0_uv,
  COUNT(DISTINCT t."#distinct_id") AS finale_uv,
  COUNT(DISTINCT t."#distinct_id") * 1.0 / (SELECT COUNT(*) FROM d0) AS full_drama_retention
FROM v_event_<pid> t
WHERE t."$part_date" BETWEEN '<start>' AND '<end>'
  AND t."$part_event" = 'EpisodeQuit'
  AND <drama_filter>
  AND CAST(t."episode_no" AS INTEGER) = <finale_ep>
  AND CAST(t."watch_time" AS DOUBLE) >= CAST(t."video_duration" AS DOUBLE) * 0.8
  AND t."#distinct_id" IN (SELECT "#distinct_id" FROM d0);
```

### T5.2 Average Episodes Watched / Abandonment Rate

```sql
-- Composite efficiency metrics
WITH d0 AS (
  SELECT "#distinct_id"
  FROM v_event_<pid>
  WHERE "$part_date" BETWEEN '<start>' AND '<end>'
    AND "$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY "#distinct_id"
),
per_user AS (
  SELECT t."#distinct_id", COUNT(DISTINCT CAST(t."episode_no" AS INTEGER)) AS eps
  FROM d0
  JOIN v_event_<pid> t
    ON t."#distinct_id" = d0."#distinct_id"
    AND t."$part_event" = 'EpisodeExpose'
    AND <drama_filter>
  GROUP BY t."#distinct_id"
)
SELECT
  COUNT(*) AS d0_uv,
  AVG(eps) AS avg_episodes,
  SUM(CASE WHEN eps < <finale_ep> THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS abandonment_rate
FROM per_user;
```

---

## 6. Execution Notes

1. **Always filter `"$part_date"`** — full-table scans are rejected. **Always `CAST(... AS INTEGER/DOUBLE)`** before arithmetic; guard division with `NULLIF`.
2. **Validate before full run**: run once with `LIMIT 100` to confirm fields and results are non-empty, then run the full query.
3. **Property name variance**: `episode_no`/`watch_time`/`video_duration`/`video_name`/`video_id`/`channel` names vary by project — confirm via §0.1 first. Watch-time semantics differ (`watch_time` cumulative vs `play_duration` single-session, see `data-validation.md §4`).
