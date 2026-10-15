# Recipes & ae-cli Commands

Merged command sequence + SQL templates. Single source of truth for building the tag via ae-cli.

---

## Placeholders

| Placeholder | Meaning | How to determine |
|---|---|---|
| `<event_table_ref>` | exact server-authorized event-view table reference | `ae-cli analysis sql-table list -p <project_id> --usage tag_cluster`, select the event-view row and copy its `table_ref` exactly |
| `<event>` | the event(s) to count (can enumerate several) | user-specified, e.g. `payment` / `order_init` / `battle_win` / `attend_arena` |
| `<userID>` | which ID to count by | user-confirmed: `#account_id` / `#user_id` / `#device_id` / `#distinct_id`, or a user-supplied event/user property |
| `<dateParam>` | parameter name in `${PartDate:date1}` | the time param name in the tag editor, default `date1` |

> **`<userID>` cast rule** — wrap `<userID>` in `cast("<userID>" as varchar)` in the `id` column whenever it is numeric; `PARTITION BY` keeps the raw column. Applies to BOTH the Step-1 virtual-property SQL and the Step-3 tag SQL. See Pitfall 10.

---

## `recent_day` time encoding (quick reference)

`part_date` params accept `recent_day` in exactly two forms. Pick per scenario:

| Form | Meaning | Scenario | Example |
|---|---|---|---|
| `"0-x"` | last x days incl. today | Scenario 2 (Recent N) | `"0-30"` = last 30 days incl. today |
| `"1-x"` | past x days excl. today | Scenario 2 (Recent N) | `"1-30"` = past 30 days excl. today |
| `"<date> 00:00:00@@0"` | fixed start → today (end rolls daily, incl. today) | Scenario 1 (Nth, since launch) | `"2022/01/01 00:00:00@@0"` |
| `"<date> 00:00:00@@1"` | fixed start → yesterday (up to yesterday) | Scenario 1 variant | `"2022/01/01 00:00:00@@1"` |

- Date uses `/` separators. `@@0` = incl. today, `@@1` = up to yesterday.
- **Do NOT** use `end_time: "today"` (backend rejects at execution) or `end_time: "2099-12-31"` (static end that never rolls). See Pitfall 9.

---

## Full command sequence (Step 0 → link)

### Step 0 — check for an existing usable entity (avoid duplicates)

```bash
ae-cli project entity list -p <project_id>
```

- Look for a "userID + event name + event time" concatenation entity (column_name like `#vp@xxx`, entity_name containing "event time"/"concat")
- **Usable entity exists → skip Step 1+2**, take its `entity_id` to Step 3
- **None → build via Step 1+2**
- A "account + event time" legacy entity missing the event-name dimension is NOT reusable — build the full triple (Pitfall 8)

### Step 1 — create the virtual event property

```bash
ae-cli analysis-meta virtual-property create --project-id <project_id> \
  --property-name '#vp@id_event_time' --table-type event --select-type string \
  --sql-expression 'cast("<userID>" as varchar)||"#event_name"||cast("#event_time" as varchar)' \
  --sql-event-relation-type relation_default
```

- **`cast("<userID>" as varchar)` is required** when `<userID>` is numeric — the backend validates the type **asynchronously**, so a raw `bigint` breaks silently later. See Pitfall 10.
- Verify: `ae-cli analysis-meta property list -p <project_id> --queries '["id_event_time"]'` → `real_status=REAL_AVAILABLE`, `prop_type=virtual_prop`.

### Step 2 — create the multi-analysis entity

```bash
ae-cli project entity create --project-id <project_id> \
  --entity-name 'user+event+time' --column-name '#vp@id_event_time' --table-type 0
```

- `--table-type 0` = event property, `1` = user property.
- Record the returned `entity_id` — pass it as `--entity-id` in Step 3.

### Step 3 — create the SQL tag

#### 3a. Get the event view table name

```bash
ae-cli analysis sql-table list -p <project_id> --usage tag_cluster
ae-cli analysis sql-table columns -p <project_id> \
  --table-ref '<event_table_ref>' --usage tag_cluster
```

Select the event-view row from the first command and copy its exact `table_ref` into the second command. Reuse that same value as `<event_table_ref>` in the SQL below; do not construct or infer a table name from the project ID.

#### 3b. Write the definition-request JSON (type=sql)

**Scenario 1 (Nth, cumulative since launch, ascending)**:

```json
{
  "type": "sql",
  "sql": "SELECT cast(\"<userID>\" as varchar)||\"#event_name\"||cast(\"#event_time\" as varchar) AS id, row_number() OVER (PARTITION BY \"<userID>\",\"#event_name\" ORDER BY \"#event_time\" ASC) AS rnk FROM <event_table_ref> WHERE \"$part_event\" = '<event>' AND ${PartDate:date1}",
  "params": [{"name": "date1", "type": "part_date", "recent_day": "<launch_date> 00:00:00@@0"}]
}
```

**Scenario 2 (Recent N, last x days, descending)**:

```json
{
  "type": "sql",
  "sql": "SELECT cast(\"<userID>\" as varchar)||\"#event_name\"||cast(\"#event_time\" as varchar) AS id, row_number() OVER (PARTITION BY \"<userID>\",\"#event_name\" ORDER BY \"#event_time\" DESC) AS rowid FROM <event_table_ref> WHERE \"$part_event\" = '<event>' AND ${PartDate:date1}",
  "params": [{"name": "date1", "type": "part_date", "recent_day": "0-30"}]
}
```

Key points (both scenarios):
- `id` column is an **inline concatenation expression**, not a virtual-property reference (the selected event view has no `#vp@` columns).
- `cast("<userID>" as varchar)` in the `id` column when `<userID>` is numeric — see Pitfall 10.
- `<userID>` must be the same in SELECT and PARTITION.
- PARTITION is always `"<userID>","#event_name"` double grouping — multiple events count independently.
- Enumerate multiple events: `"$part_event" in ('a','b')`.
- **Neither scenario hardcodes N** — numbering runs `1..K`; the `rowid <= N` / `rnk = N` cutoff is applied at analysis time, not in the tag.

#### 3c. Create the tag

```bash
ae-cli analysis user-tag create --project-id <project_id> \
  --tag-name <snake_case_name> --display-name "<human name>" \
  --entity-id <Step2_entity_id> --zone-offset <offset> \
  --enable-auto-refresh true \
  --auto-refresh-schedule '{"frequency":"daily","time":"<HH:MM>"}' \
  --definition-request '{"type":"sql",...}'
```

- **Must pass `--entity-id`** — otherwise the tag defaults to the "user" entity, wrong granularity.
- **Must pass `--zone-offset`** — otherwise `cluster_zone_offset` falls to 99 (unbound) and the window slices by raw `#event_time` (Pitfall 7).
- **Tag the caliber in `--display-name`** — append the ID and (for Scenario 2) the window, e.g. `Roguelike最近N次结算(user)` / `商城购买第几次(device)`. Same entity + event can yield several tags differing only by caliber/window; a bare display name forces the user to click in to tell them apart.
- **Enable auto-refresh at create (ae-cli ≥ 6.0.49)** — `--enable-auto-refresh true` + `--auto-refresh-schedule '{"frequency":"daily","time":"<HH:MM>"}'` (or `--auto-refresh-cron`). **Confirm the frequency + time with the user; do NOT hardcode `01:01`.** Omit `--enable-auto-refresh` and the tag is created with auto-refresh OFF. On older ae-cli (no such flags), enable it later via UI (Step 5).

#### 3d. Wait for computation

```bash
ae-cli analysis user-tag get --project-id <project_id> --tag-names '["<tag_name>"]'
```

Follow the exact `next_action`, `next_capability_id`, and `next_input` returned by the command. After creation, wait until `progress=100` and `refresh_time` is present before treating `users_num` as complete; `select_type=number` is auto-inferred.

**Polling best practice** (large projects can take 5–10+ min):
- Poll in modest non-blocking steps (`sleep 20` → get → `sleep 30` → get …), not one giant `sleep 120+` — a single long `sleep` can get killed by the shell timeout and waste the elapsed time.
- When `progress` plateaus early (e.g. at `2`), that can be normal for a big scan. Continue only when `next_action=poll_get`, using the returned capability and input; do not assume it is stuck and re-submit.
- On the get call, inspect `progress`, `refresh_time`, `users_num`, `next_action`, `next_capability_id`, and `next_input`; the JSON is large and the useful fields are nested.

### Get the tag link

```bash
ae-cli analysis-meta asset url-get -p <project_id> --resource-type tag --resource-id <tag_id>
```

- `--resource-type` must be `tag`, not `user_tag`.
- Returns `raw_url` like `https://<host>/#/tag/tagdetail/<tag_id>?currentProjectId=<project_id>`.

---

## SQL templates (bare, for the manual path)

### Scenario 1: Nth occurrence (cumulative since launch)

```sql
SELECT cast("<userID>" as varchar)||"#event_name"||cast("#event_time" as varchar) "id"
, row_number() over(partition by "<userID>","#event_name" order by "#event_time" asc) rnk
FROM <event_table_ref>
WHERE "$part_event" in ('<event>') AND
${PartDate:date1}
```

- `asc` → rnk=1 is the first occurrence.
- Time: anchored `recent_day: "<launch_date> 00:00:00@@0"`.

### Scenario 2: Recent N (last x days)

```sql
SELECT cast("<userID>" as varchar)||"#event_name"||cast("#event_time" as varchar) "id"
, row_number() over(partition by "<userID>","#event_name" order by "#event_time" desc) rowid
FROM <event_table_ref>
WHERE "$part_event" in ('<event>') AND
${PartDate:date1}
```

- `desc` → rowid=1 is the most recent occurrence.
- Time: relative `recent_day: "0-x"` (e.g. `0-30` = last 30 days).

### Quick comparison

| Dimension | Scenario 1 (Nth) | Scenario 2 (Recent N) |
|---|---|---|
| Ordering | `asc` | `desc` |
| PARTITION | `"<userID>","#event_name"` | `"<userID>","#event_name"` |
| Event filter | `$part_event in (...)` | `$part_event in (...)` |
| Time policy | anchored (launch → today) | relative (last x days) |
| Numbering meaning | cumulative Nth (1 = first) | recency (1 = latest) |
| Tag value change | only grows | rolls daily |

---

## Verified pitfalls log

| # | Observation | Conclusion |
|---|---|---|
| 1 | the selected event view has no `#vp@` virtual-property column | write the `id` column as an inline concatenation, don't reference a virtual-property column name |
| 2 | dry-run passes without `--entity-id` | but the tag defaults to the "user" entity, wrong granularity. **Must pass `--entity-id`** |
| 3 | `select_type` needs no explicit setting | rowid/rnk is numeric, backend auto-infers `number` |
| 4 | guessing an event-view name can select a nonexistent or unauthorized table | copy the exact `table_ref` returned by `analysis sql-table list --usage tag_cluster` |
| 5 | `cluster_zone_offset=99` when `--zone-offset` omitted | 99 = unbound-timezone sentinel; window slices by raw `#event_time`. **Must pass `--zone-offset`** |
| 6 | existing entity may use a different ID than the one requested | `entity 87074` was built on `#user_id`; a `#distinct_id` request needs a fresh property+entity, not reuse — verify the bound virtual property's `vir_prop_column_rule` before reusing |
