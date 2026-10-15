# Live-Penetration Analysis SQL Query Templates (Universal Edition)

## Product Config (query technical parameters only)

> Event names / field calibers / caliber notes single-source from SKILL.md "Data Caliber" table + product-config files, not repeated here.
> Judgment thresholds single-source from `references/judgment-parameters.md`, not repeated here.
> This section keeps only pure query technical parameters. **All `{placeholder}` in SQL templates must be read and substituted from product config; do NOT hardcode.**

| Config item | Source | Note |
|--------|------|------|
| Project ID | product config `project_id` | ae-cli `--project-id {project_id}` |
| Event table | product config `event_table` | Trino/Hive full path |
| User table | product config `user_table` | join key `#user_id` |
| Timezone | product config `tz` | `$part_date` cut by this timezone |

## Shell Escaping Essentials

JSON outer single quotes, SQL string values use `'\''...'\'` escaping, column-name double quotes in JSON use `\"`:

```bash
ae-cli analysis adhoc run --project-id {project_id} --model-type sql \
  --definition '{"sql":"SELECT \"$part_date\", COUNT(DISTINCT \"#user_id\") AS uv FROM {event_table} WHERE \"$part_event\" = '\''{enter_event}'\'' AND \"$part_date\" BETWEEN '\''{start_date}'\'' AND '\''{end_date}'\'' GROUP BY 1 ORDER BY 1"}' \
  2>/dev/null
```

**Save & parse (MUST)**:

1. **Save results with `1> /tmp/xxx.json 2>/dev/null`, do NOT use `2>&1`** — `2>&1` mixes ae-cli's "Update available" banner + "dispatching capability=..." logs into the JSON file header, causing `json.loads` to fail from the first character. stderr is either dropped (`2>/dev/null`) or redirected separately for debugging, never mixed into stdout.

2. **Skip log lines before JSON when parsing**: even if the spec is written correctly, use `raw.find('{')` to find the first `{` before `json.loads`, as one layer of tolerance.

3. **Immediately validate the persisted file after each query command**: `echo "size=$(wc -c < /tmp/xxx.json)"` or `ls -la`, confirm the file exists and is non-empty before the next query. Especially important for parallel multi-command runs — a field test saw "command `echo done` but file never generated" silent loss.

4. **Empty-string comparison escaping**: to judge field null-ness, the SQL empty string `''` inside zsh single-quoted JSON must be written as `'\'''\''`.

## Aggregate Trend Queries

### 1. Primary entry event daily UV

```sql
SELECT "$part_date", COUNT(DISTINCT "#user_id") AS enter_uv
FROM {event_table}
WHERE "$part_event" = '{enter_event}'
  AND "$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1
```

If the primary event has a filter (product config `enter_event_filter`), add `AND {enter_event_filter}`.

### 2. Second entry event entry UV (optional)

```sql
SELECT "$part_date", COUNT(DISTINCT "#user_id") AS enter_uv_2
FROM {event_table}
WHERE "$part_event" = '{enter_event_2}'
  AND {enter_event_2_filter}
  AND "$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1
```

### 3. DAU daily UV

```sql
SELECT "$part_date", COUNT(DISTINCT "#user_id") AS dau
FROM {event_table}
WHERE "$part_event" = '{dau_event}'
  AND "$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1
```

## Multi-Dimension Breakdown Queries

### 4. OS dimension breakdown

> **【MUST·case normalization】** If the product has cross-event OS case inconsistency (e.g., primary event `Android`/`iOS`, DAU event `android`/`ios`), any OS-related join cross drill-down will fail to join and produce a whole column of 0%. Write `LOWER(e."#os")` directly in the SQL to unify before GROUP BY.

```sql
SELECT
  e."$part_date",
  LOWER(e."#os") AS os,   -- unify lowercase, avoid case-inconsistency join failure
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1, 2
ORDER BY 1, 2
```

Note: for DAU split, change `$part_event` to `{dau_event}`.

### 5. New/old user breakdown

> **New-user caliber = registration day** (`{new_user_field} = $part_date`), not "registered within last 7 days".
> **Type note**: if `{new_user_field}` is `timestamp(3)` while `$part_date` is `varchar`, **do NOT use `date_parse(u.{new_user_field}, ...)`** — date_parse requires varchar input and errors on timestamp. Correct approach is `cast(x as date)` to unify both sides to date before comparing.

```sql
SELECT
  e."$part_date",
  CASE WHEN cast(u.{new_user_field} as date) = cast(e."$part_date" as date)
       THEN 'new' ELSE 'old' END AS user_type,
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
JOIN {user_table} u ON e."#user_id" = u."#user_id"
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1, 2
ORDER BY 1, 2
```

### 6. Organic/paid breakdown (virtual property)

**Prefer event analysis model for virtual properties** (SQL model cannot GROUP BY virtual properties directly):

```bash
# primary event split by {organic_field}
ae-cli analysis adhoc run --project-id {project_id} --model-type event \
  --definition '{"time_range":{"mode":"previous","unit":"day","value":7},"time_particle_size":"day","metrics":[{"event":"{enter_event}","aggregation":"user_count"}],"groups":[{"field":{"name":"{organic_field}","type":"user_property"}}],"relation":"and"}' \
  2>/dev/null

# DAU split: change event to {dau_event}
# second-event split: change event to {enter_event_2}, add filters [{"field":{"name":"...","type":"event_property"},"operator":"eq","values":["..."]}]
```

#### SQL fallback (CASE WHEN rules, no virtual property)

If the event model is unavailable, and the product's user table has raw channel fields (e.g., `media_source` / `channel_name`), use SQL CASE WHEN fallback (specific rules per product's actual fields):

```sql
SELECT
  e."$part_date",
  CASE WHEN u."media_source" = 'organic' THEN 'organic' ELSE 'paid' END AS user_source,
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
JOIN {user_table} u ON e."#user_id" = u."#user_id"
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1, 2
ORDER BY 1, 2
```

### 7. Channel breakdown (virtual property)

**Prefer event analysis model for virtual properties**:

```bash
ae-cli analysis adhoc run --project-id {project_id} --model-type event \
  --definition '{"time_range":{"mode":"previous","unit":"day","value":7},"time_particle_size":"day","metrics":[{"event":"{enter_event}","aggregation":"user_count"}],"groups":[{"field":{"name":"{channel_field}","type":"user_property"}}],"relation":"and"}' \
  2>/dev/null
```

### 7b. Version dimension breakdown

```sql
SELECT
  e."$part_date",
  e."#app_version",
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1, 2
ORDER BY 1, 2
```

**Do NOT `SUBSTR`/`split`-truncate version numbers to aggregate major versions**. Version numbers are `x.x.xx` three-segment (possibly four-segment hotfix/channel suffix); must GROUP BY `#app_version` original value. Truncation merges dozens of patch versions into fake major versions, masking real generational migration. When there are 100+ patch versions, sort by DAU and take TOP N major versions for intra-group penetration comparison (early rollout versions with denominator <200 have noise-level penetration, exclude them).

> **【MUST·parsing script must implement filtering】** The version dimension full result can return 100+ patch values; when parsing, the script must first `SUM(DAU) GROUP BY version` to get each version's window DAU total, then `ORDER BY total DESC LIMIT TOP 20~30`, and skip "single-day denominator <200" days. **This filtering must be designed at the parsing-script stage.**

### Cross Drill-Down Queries

(Part 4 step 2b; using "version × new/old user" as example; replace dimension names)

```sql
SELECT
  e."$part_date",
  e."#app_version",
  CASE WHEN cast(u.{new_user_field} as date) = cast(e."$part_date" as date)
       THEN 'new' ELSE 'old' END AS user_type,
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
JOIN {user_table} u ON e."#user_id" = u."#user_id"
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN 'start' AND 'end'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
```

> DAU split: change `$part_event` to `{dau_event}` to get the cross-dimension DAU.

> **【MUST·field-order trap】** The cross drill-down SQL return column order is `["$part_date", dimension_value, user_type, uv]` — **dimension value is column 2, new/old is column 3**. When the parsing script deserializes as `rows = [date, d1, d2, uv]`, **d1 = dimension value, d2 = user_type** — the two are easily swapped. Swapping silently produces whole columns of "—" / 0 values. **Iron rule**: before parsing cross drill-down results, `print(rows[:3])` to print the first 3 raw rows and eyeball the column order before writing access code. The default access structure is `date → user_type('new'/'old') → dimension value → uv`.

### 7c. Version-Difference Diagnosis Queries

**Core: new vs old version "same-period" intra-group penetration comparison; do NOT use historical-period old version comparison.**

#### Step zero: same-cohort before/after upgrade comparison (rule out selection bias, highest priority)

```sql
-- find users who upgraded from old to new version, compare their entry rate before/after upgrade
WITH upgrade_users AS (
  SELECT
    u."#user_id",
    MIN(CASE WHEN e."#app_version" = '{new_version}' THEN e."$part_date" END) AS upgrade_date
  FROM {user_table} u
  JOIN {event_table} e ON e."#user_id" = u."#user_id"
  WHERE e."$part_event" = '{dau_event}'
  GROUP BY 1
)
SELECT
  u."#user_id",
  u.upgrade_date,
  COUNT(DISTINCT CASE WHEN e."$part_date" > u.upgrade_date
                       AND e."$part_date" <= date_add('day', 7, u.upgrade_date)
                       AND e."$part_event" = '{enter_event}' THEN e."$part_date" END) AS post_enter_days,
  COUNT(DISTINCT CASE WHEN e."$part_date" <= u.upgrade_date
                       AND e."$part_date" > date_add('day', -7, u.upgrade_date)
                       AND e."$part_event" = '{enter_event}' THEN e."$part_date" END) AS pre_enter_days,
  COUNT(DISTINCT CASE WHEN e."$part_date" > u.upgrade_date
                       AND e."$part_date" <= date_add('day', 7, u.upgrade_date)
                       AND e."$part_event" = '{dau_event}' THEN e."$part_date" END) AS post_active_days,
  COUNT(DISTINCT CASE WHEN e."$part_date" <= u.upgrade_date
                       AND e."$part_date" > date_add('day', -7, u.upgrade_date)
                       AND e."$part_event" = '{dau_event}' THEN e."$part_date" END) AS pre_active_days
FROM upgrade_users u
JOIN {event_table} e ON e."#user_id" = u."#user_id"
GROUP BY 1, 2
```

After aggregation, compare: pre-upgrade entry rate = Σpre_enter_days / Σpre_active_days; post-upgrade entry rate = Σpost_enter_days / Σpost_active_days. **If the same cohort's post-upgrade entry rate drops ≥ 2pp → version defect ironclad evidence.**

> Notes:
> - `upgrade_date` is aggregated by `MIN(...)`, already date/timestamp type, **do NOT wrap in `date_parse` again**.
> - `date_add('day', N, ts)`'s third argument requires timestamp; if `upgrade_date` is date, first `CAST(upgrade_date AS TIMESTAMP)`, or use `e."$part_date" <= u.upgrade_date + INTERVAL '7' DAY`.
> - If the user table has no version-change timestamp, switch to the "upgrade event" or approximate the upgrade time by the first date the new version number appears in `#app_version`.

#### Version × entry source (primary event)

```sql
SELECT
  e."$part_date",
  e."#app_version",
  e.{enter_source_field},
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
```

#### Version × OS / Version × new-old user

Same structure; replace column 3 with `LOWER(e."#os")` or the new/old CASE WHEN.

#### DAU split (version + sub-dimension as denominator)

Change `$part_event` to `{dau_event}` in the above queries for the corresponding DAU split.

**Judgment notes**:
- Intra-group penetration = that combination's UV / same combination's DAU, **do NOT use aggregate DAU as denominator**.
- New version vs same-period old version intra-group rate difference ≥ 2pp → version defect; < 2pp and aggregate decline fully explained by share change → pure structural migration.

### 8. Entry-source null-rate check + entry breakdown (primary event only)

**Step 8a: null-rate check** (first judge whether tracking is abnormal):

```sql
SELECT
  e."$part_date",
  COUNT(DISTINCT CASE WHEN e.{enter_source_field} IS NULL OR e.{enter_source_field} = ''
                       THEN e."#user_id" END) AS null_uv,
  COUNT(DISTINCT e."#user_id") AS total_uv
FROM {event_table} e
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1
```

Judgment rule: first/last-day null-rate change ≥3pp = anomaly; does not depend on absolute historical value.

**Step 8b: entry breakdown (MUST, high null-rate ≠ skip)**. If the entry-source field's null-rate is chronically high, but the non-null entries have clear semantics, **high null-rate only means a coverage caveat, not a reason to skip breakdown** — must split the non-null part by entry:

```sql
SELECT
  e."$part_date",
  e.{enter_source_field},
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
WHERE e."$part_event" = '{enter_event}'
  AND e.{enter_source_field} IS NOT NULL
  AND e.{enter_source_field} <> ''
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1, 2
ORDER BY 1, 2
```

Note: entry penetration uses **aggregate DAU** as denominator (DAU has no entry-source property); declare the coverage caveat when interpreting.

### 9. Country/region dimension breakdown

Join user table for `{locale_field}`, split UV and DAU by country/region:

```sql
SELECT
  e."$part_date",
  u.{locale_field},
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
JOIN {user_table} u ON e."#user_id" = u."#user_id"
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1, 2
ORDER BY 1, 2
```

Note: for DAU split, change `$part_event` to `{dau_event}`.

### 10. Second-event entry-source breakdown (virtual property)

If the second entry event + virtual-property entry source is configured, **prefer event analysis model for virtual properties** (SQL model cannot GROUP BY virtual properties directly).

```bash
# split by {enter_source_vp}
ae-cli analysis adhoc run --project-id {project_id} --model-type event \
  --definition '{"time_range":{"mode":"previous","unit":"day","value":7},"time_particle_size":"day","metrics":[{"event":"{enter_event_2}","aggregation":"user_count"}],"groups":[{"field":{"name":"{enter_source_vp}","type":"event_property"}}],"filters":[{"field":{"name":"...","type":"event_property"},"operator":"eq","values":["..."]}],"relation":"and"}' \
  2>/dev/null
```

Event-model definition field notes:
- `time_range`: `{"mode":"previous|recent|custom","unit":"day","value":N}`, previous excludes today, recent includes today; custom needs `start_time`/`end_time`. **For fixed N-day windows, prefer `previous`+`value`; `custom`'s `end_time` boundary semantics are error-prone. `previous` mode returns an extra `["phase summary", <dim value>, <total>]` row — skip it when parsing**
- `time_particle_size`: `"day"` day granularity
- `metrics`: `[{"event":"event name","aggregation":"user_count"}]`
- `groups`: `[{"field":{"name":"property name","type":"event_property or user_property"}}]`, virtual properties use `event_property`
- `filters`: `[{"field":{"name":"property name","type":"event_property"},"operator":"eq","values":["value"]}]`
- `relation`: `"and"`

> **Fine-grained source-field trap**: if the second entry-source virtual property is a fine-grained position bit (e.g., SPM's C segment), value drift is high (same entry may change label); first/last-segment comparison shows "first segment 0 → last segment appears" fake growth, needing recognition of "new content position launched / label renamed" vs real growth.

#### SQL fallback (event-level property only, no virtual property)

If the product's entry source is an event-level property (not virtual), SQL model can query directly:

```sql
SELECT
  e."$part_date",
  e.{enter_source_field_2},
  COUNT(DISTINCT e."#user_id") AS uv
FROM {event_table} e
WHERE e."$part_event" = '{enter_event_2}'
  AND {enter_event_2_filter}
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1, 2
ORDER BY 1, 2
```

## Supply-Side Queries

### 11. Streaming start/end events

```sql
-- active streamers / streaming rooms
SELECT
  e."$part_date",
  COUNT(DISTINCT e."#user_id") AS active_hosts,
  COUNT(DISTINCT e.{room_id_field}) AS active_rooms
FROM {event_table} e
WHERE e."$part_event" = '{live_start_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1

-- prime-time streaming rooms (20:00-23:59)
SELECT
  e."$part_date",
  COUNT(DISTINCT e.{room_id_field}) AS golden_rooms
FROM {event_table} e
WHERE e."$part_event" = '{live_start_event}'
  AND HOUR(e."$part_time") >= 20
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1
```

### 12. Valid-streaming-duration share

```sql
SELECT
  e."$part_date",
  COUNT(DISTINCT CASE WHEN e.{live_duration_field} >= 60 THEN e.{room_id_field} END) AS valid_lives,
  COUNT(DISTINCT e.{room_id_field}) AS total_lives
FROM {event_table} e
WHERE e."$part_event" = '{live_end_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1
```

## Funnel Queries

### 13. Exposure event (optional)

```sql
SELECT
  e."$part_date",
  COUNT(*) AS exposure_pv,
  COUNT(DISTINCT e."#user_id") AS exposure_uv
FROM {event_table} e
WHERE e."$part_event" = '{exposure_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1
```

To split by scene/entry: add `e.{exposure_scene_field}` to GROUP BY.

### 14. Quick-exit rate / avg watch time

```sql
SELECT
  e."$part_date",
  COUNT(DISTINCT CASE WHEN e.{stay_duration_field} < 30 THEN e."#user_id" END) AS quick_exit_uv,
  COUNT(DISTINCT e."#user_id") AS total_enter_uv,
  SUM(e.{stay_duration_field}) AS total_stay
FROM {event_table} e
WHERE e."$part_event" = '{enter_event}'
  AND e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
GROUP BY 1
ORDER BY 1
```

## Common Query Traps

1. **Event-name case**: SQL exact match, event names are case-sensitive
2. **OS case inconsistency**: `#os` may be case-inconsistent across events; `LOWER()` normalize in cross drill-down
3. **Virtual property needs event model**: `#vp@`-prefixed properties are TE backend virtual properties, SQL model cannot query directly; **prefer event analysis model** (`--model-type event`)
4. **Event-model definition format**: `field`'s `type` depends on property ownership — event-level property uses `event_property`, user-level uses `user_property`; wrong type returns empty results
5. **Row limit**: SQL model defaults to 100 rows max; event model defaults to 1000 rows, results truncated when dimension values >20 (`has_more=true`). **Do NOT try to add any row-limit parameter.** When over-limit, use SQL `WHERE` to filter TOP dimension values, or pre-aggregate SQL
6. **Dimension breakdown must query daily data**: do NOT query only first/last two days. SQL uses `BETWEEN 'start' AND 'end'`, event model uses `"time_range":{"mode":"custom","start_time":"...","end_time":"..."}`
7. **Event-model large-result handling**: querying virtual-property dimensions may return very large results (50-120KB); pipe to a Python script to extract key dates and TOP N dimension values

   > **【MUST·truncation ≠ lost series】** When event model truncates at 1000 rows (`has_more=true`), **do NOT rush to re-query**; judge in this order:
   > 1. Take the returned rows, `set(r[0] for r in rows)` to check whether the **date dimension covers the full window**. Data is sorted by `(date, dim value)`; truncation usually only cuts the trailing "phase summary" row and **tiny tail dimension values**; **main entries' (high-UV dimension values) daily series are often complete**.
   > 2. If dates are complete → main entries' daily penetration trend is directly usable, **no SQL re-query needed**.
   > 3. **Skip the `phase summary` row when parsing**, otherwise totals are double-counted.
8. **Do NOT truncate version numbers**: `#app_version` split by original value, do NOT `SUBSTR` into fake major version. Truncation merges dozens of patch versions into fake major versions, masking generational migration
9. **【concurrency limit】** ae-cli has a per-host query concurrency cap; **firing multiple SQL queries in parallel within one command triggers `CONCURRENCY_LIMIT_EXCEEDED`**. Correct approach: **SQL queries serial** (one command one SQL, or `&&`-chain + `sleep 1~2` buffer in between); event-model queries `sleep 2` in between suffices; if concurrency error still occasionally occurs → retry the single query, do NOT resend the whole batch
10. **【event-model `previous` mode returns one extra day】** `--model-type event` with `"time_range":{"mode":"previous","unit":"day","value":31}` returns the **last 31 days up to yesterday**, i.e., **one extra first day** vs SQL `BETWEEN` window. **Iron rule**: event-model parsing must **explicitly filter the date range** (`if dt < start or dt > end: continue`); SQL-model and event-model time windows must align to the same `[start, end]` closed interval before computing
11. **【parsing-script Python traps】** two high-frequency bugs when writing parsing scripts:
    - **setdefault chained assignment**: `d.setdefault(k, {})[kk] = v` throws `KeyError` when `k` exists but the inner dict isn't initialized. **Canonical form**: write `d.setdefault(k, {})` on its own line, then `d[k][kk] = v` on the next line
    - **tuple cannot be a JSON key**: using `{(date, dim1): ...}` tuple keys in a dict, then `json.dump` throws `TypeError`. Before persisting JSON, **convert tuple keys to nested dicts** (`date → dim1 → dim2 → uv`)
12. **【dimension value may be None / empty string】** grouping fields (`country`, `#app_version`, `channel`, etc.) frequently return `None` or `''`. When parsing, normalize with `v or 'NULL'` before using as a dict key — otherwise `int += str` style arithmetic throws `TypeError`, and the None group silently vanishes from totals. Decide explicitly whether to keep the NULL group or drop it; do not let it disappear by accident.
13. **【metadata `last_day_count` is PV not UV】** event-metadata `last_day_count` is event-row count (repeat firing), not distinct users. Do NOT use it to judge penetration magnitude or compare two events' UV scale — pull `COUNT(DISTINCT "#user_id")` instead.
