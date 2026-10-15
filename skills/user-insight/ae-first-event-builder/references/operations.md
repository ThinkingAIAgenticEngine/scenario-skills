# Operations Manual (references/operations.md)

Execute the following operations strictly per their parameters; do not adjust on your own. Four placeholder classes:
- **Template variables**: `{{EVENT}}`, `{{PROP}}`, `{{TAG_NAME}}`, `{{VALUE_COL}}`, `{{ENTITY_ID_COL}}`, `{{PROJECT_ID}}`, `{{START_DATE}}`, `{{YESTERDAY}}` (definitions in each operation's inline notes and variable table; replace before use)
- **CLI placeholders**: angle-bracket placeholders in commands such as `<id>`, `<event>`, `<tag_name>`, replaced in place at execution time
- **params macros**: `${PartDate:*}` is a macro specific to the tag definition-request params system; declarations appear in each operation's params array
- **Naming prefixes**: `#vp@` virtual event property, `ta@` virtual event, `ta_tag.` the tag reference alias inside virtual event property definitions (rewritable by the engine only; adhoc SQL cannot reference it directly — see Operation 2's notes)

All command and SQL templates are complete structures; replace the placeholders and execute directly.

> The templates below depend on several platform behavior assertions; re-verify them first after platform upgrades: table-name forms, timezone offset behavior, the interval model's pairing rules, `recent_day` window semantics, and CLI switch support for auto backup (see Operation 3 and Step 5 of the main file).

## Tag Snapshot Table Structure (referenced by Operation 1)

Tag computation results are written to `ta.user_result_cluster_{{PROJECT_ID}}` (the current snapshot table, with no version-date column):

| Column | Type | Description |
|---|---|---|
| `#user_id` | bigint | User subject ID (preset subject) |
| `#varchar_id` | varchar | String-type custom subject ID |
| `#double_id` | double | Numeric custom subject ID |
| `tag_value` | varchar | String value |
| `tag_value_num` | double | Numeric value |
| `tag_value_tm` | timestamp(3) | Time value |
| `tag_value_bool` | boolean | Boolean value |
| `tag_value_array_varchar` | array(varchar) | String array value |
| `cluster_name` | varchar | Tag name |

Each row has a value only in the ID column corresponding to its subject type; the other ID columns are NULL; the tag value is written to the value column matching its value type (the SQL output column alias is uniformly `tag_value`; the platform routes it to the matching physical column on write).

## Operation 1: Create a Lifecycle First-Value Tag

One tag records one value of the user's first occurrence of the "target event" (`{{PROP}}` is an event property field name, or `#event_time` for the first time — time is also a field of the event, so both share the same template). Creation is always two steps: full initialization → switch to incremental. `{{TAG_NAME}}` follows the main SKILL.md "Asset naming convention summary": when `{{PROP}}` = `#event_time`, use `first_<event>_time` (display name "First <event display name> Time"); for a business property, use `first_<event>_<property>` (display name "First <event display name> <property display name>"). `{{EVENT}}` is the event's English name; `{{PROJECT_ID}}` is the numeric project ID.

#### Variable Table

| Variable | Description |
|---|---|
| `{{PROP}}` | Value field: an event property field name, or `#event_time` (the first time) |
| `{{VALUE_COL}}` | Snapshot table value column: string→`tag_value`, numeric→`tag_value_num`, time→`tag_value_tm`, boolean→`tag_value_bool`, string array→`tag_value_array_varchar` |
| `{{ENTITY_ID_COL}}` | Snapshot table subject column: user subject→`#user_id`, string-type custom subject→`#varchar_id`, number-type custom subject→`#double_id` (a subject's select_type is queried via `ae-cli project entity list`) |
| `{{TAG_NAME}}` | See the naming convention summary |

#### Custom Analysis Subject (skip this section when the default user subject applies)

1. Event-table side: `"#user_id"` → the subject column (e.g., `"#device_id"`), replacing in SELECT, PARTITION BY / GROUP BY, and JOIN keys in sync; `#user_id` references inside output expressions such as COALESCE (e.g., the incremental SQL's `COALESCE(h."#user_id", i."#user_id")`) are replaced likewise
2. Add `--entity-id <ID>` to the create command (looked up via `ae-cli project entity list`)
3. The incremental SQL's hist side and JOIN keys: `"#user_id"` → `{{ENTITY_ID_COL}}`; **the SELECT output subject-column alias in both the full and incremental SQL is also uniformly written as `{{ENTITY_ID_COL}}`** (the tag value's subject slot in the snapshot table is routed by that column; writing an event-table column name such as `#device_id` lands in the wrong slot)

The full initialization SQL, the incremental SQL, and every verification SQL all apply the above replacements.

### Step 1: Full initialization (start date → yesterday, no backup)

The start date (`{{START_DATE}}`) is the data start date given by the user in Step 1.

Before executing, use `ae-cli analysis sql-table list --project-id <id> --usage tag_cluster` to check the authorized table list; **the table-name forms of the event/snapshot tables in the SQL follow the returned `sql_reference`** (this template writes `ta.v_event_{{PROJECT_ID}}` / `ta.user_result_cluster_{{PROJECT_ID}}`; some clusters require a catalog prefix — copy the returned `sql_reference` verbatim (a form like `"hive"."ta"."v_event_{{PROJECT_ID}}"`, each segment double-quoted); the `tag_cluster` authorized table set differs from ordinary analysis SQL — do not mix them up).

```sql
SELECT "#user_id", "{{PROP}}" AS tag_value
FROM (
  SELECT "#user_id", "{{PROP}}",
    row_number() OVER (PARTITION BY "#user_id" ORDER BY "#event_time" ASC, "#server_time" ASC) AS rn
  FROM ta.v_event_{{PROJECT_ID}}
  WHERE ${PartDate:partdate}
    AND "$part_event" = '{{EVENT}}'
    AND "{{PROP}}" IS NOT NULL
) t
WHERE rn = 1
```

Create command (with `--zone-offset <project timezone; remove this parameter if timezone is disabled>`, using the project's default timezone offset):

```bash
ae-cli analysis user-tag create --project-id <id> \
  --tag-name <tag_name> \
  --display-name "<display name>" \
  --zone-offset <project timezone; remove this parameter if timezone is disabled> \
  --definition-request '{"type":"sql","sql":"<the SQL above>","params":[{"name":"partdate","type":"part_date","start_time":"{{START_DATE}}","end_time":"{{YESTERDAY}}"}]}'
```

- Create reports "object quantity limit reached" (`EXCESS_QUANTITY`) → handle per the main file's Step 4 "Quota-limit contingency" (list candidates for user confirmation; two-phase deletion or quota expansion; never delete existing assets on your own)
- `{{YESTERDAY}}` = yesterday (**not today**; does not overlap the incremental window)
- **Do not enable backup**: lifecycle first needs no historical versions; the platform default is no backup — keep the default
- The tag value type is auto-detected (datetime/string/number); no need to specify
- Wait for that full computation to finish before moving to step 2 — submission triggers the first full computation automatically; there is no need (and no way) to trigger it manually. Just use step 4's status-polling command to confirm `computation.status=succeeded`; poll every 60 seconds for at most 30 minutes (long runtimes are normal for full computation on large tables). On timeout, tell the user "the full computation is still queuing/running" and pause the workflow — do not wait indefinitely; when the user returns, resend the same polling command and continue to step 2 only after confirming succeeded (a pause over 2 days triggers the next interval constraint — handle it per its rules)
- **Full → incremental interval constraint**: the full run's `end_time` is the creation day's yesterday D-1, and the first incremental window is the most recent 3 days after the switch; steps 1–3 should complete within 2 days of creation (a full-computation queue timeout or the user delaying confirmation both widen the gap). If the incremental-switch day is **more than 3 days** past the full run's `end_time`, a gap that neither side covers appears — in that case do not switch to incremental; **instead use `user-tag update` to resubmit step 1's full SQL** (definition-request identical to step 1; the params `end_time` updated to the current yesterday; strictly never run `user-tag create` again — a same-name rerun creates a duplicate tag with a suffix). Record the pre-update `refresh_time`, follow the update response's `computation.triggered_automatically` / `next_action`, and poll `user-tag get` until `progress=100` and `refresh_time` advances; do not call `user-tag refresh` after a definition update. Then continue to step 2
- When `{{PROP}}` = `#event_time` (time type), it can be simplified to the aggregate form `SELECT "#user_id", min("#event_time") AS tag_value ... GROUP BY "#user_id"`; the window form is steadier, deciding a unique row by `#server_time` when identical timestamps tie
- **Caliber note**: `IS NOT NULL` makes this solution take the "first non-null property value"; if the property is empty on the user's first event, the value taken is from a later non-null event. Explain this caliber when confirming requirements with the user; a strict "the value on the first event itself (including empty)" requires separate customization
- **Timezone caliber**: this operation takes the first occurrence by ordering on raw `#event_time` (`ORDER BY "#event_time"`), and the tag value stores the raw time. In projects with timezone enabled, for multi-timezone users (with differing `#zone_offset`), the "first" chosen here may differ from Operation 3's first_last tag (which orders by the project timezone) — a known caliber difference between the two routes; simply state it honestly
- Value-type note: the SQL output column alias is uniformly written `tag_value`; the platform routes it on write to the physical column matching the value type (see "Tag snapshot table structure" above); the incremental SQL's hist side reads the corresponding physical column via `{{VALUE_COL}}`, matching the write routing

### Step 2: Switch to the incremental SQL (daily scan of the "last 3 days" window + merge with the current tag snapshot)

The source of historical values is the tag's own **current snapshot table** `ta.user_result_cluster_{{PROJECT_ID}}`. Before writing the incremental SQL, confirm that table is authorized for query (reuse step 1's `sql-table list` check result; run the check only if not done before). If the authorized list lacks the snapshot table (platform version below 6.0, or the `tag_cluster` authorization not enabled) → the incremental route is unavailable: stop this operation, tell the user honestly that the lifecycle incremental solution depends on platform 6.0+ and snapshot-table authorization, and continue only after the platform enables it; do not rewrite the template as a workaround.

```sql
WITH hist AS (
  SELECT "#user_id", "{{VALUE_COL}}" AS val
  FROM ta.user_result_cluster_{{PROJECT_ID}}
  WHERE "cluster_name" = '{{TAG_NAME}}'
),
inc AS (
  SELECT "#user_id", "{{PROP}}" AS val
  FROM (
    SELECT "#user_id", "{{PROP}}",
      row_number() OVER (PARTITION BY "#user_id" ORDER BY "#event_time" ASC, "#server_time" ASC) AS rn
    FROM ta.v_event_{{PROJECT_ID}}
    WHERE "$part_event" = '{{EVENT}}'
      AND ${PartDate:date1}
      AND "{{PROP}}" IS NOT NULL
  ) t
  WHERE rn = 1
)
SELECT COALESCE(h."#user_id", i."#user_id") AS "#user_id",
       COALESCE(h.val, i.val) AS tag_value
FROM hist h
FULL OUTER JOIN inc i ON h."#user_id" = i."#user_id"
WHERE COALESCE(h.val, i.val) IS NOT NULL
```

Switch command:

```bash
ae-cli analysis user-tag update --project-id <id> \
  --tag-name <tag_name> \
  --definition-request '{"type":"sql","sql":"<incremental SQL>","params":[{"name":"date1","type":"part_date","recent_day":"0-3"}]}'
```

Before submitting the update, record the current `refresh_time`. A changed `--definition-request` automatically starts recomputation; **do not call `user-tag refresh` afterward**. Follow the returned `computation.triggered_automatically` and `next_action`, then poll `user-tag get` every 60 seconds for at most 30 minutes until `progress=100` and `refresh_time` advances. On timeout, pause per step 1's rules. This automatically triggered recomputation also serves as **same-day verification of the incremental SQL** (snapshot-table permissions, column names, and JOIN errors all surface here). If the update unexpectedly reports `not_triggered`, stop and inspect whether the normalized definition actually changed; do not compensate with an unplanned refresh.

- `recent_day: "0-3"` = **the most recent 3 days (including today)**. The window must include today: the daily 01:01 auto update computes today's current value, and a window without today cannot compute it; today's data fully enters the tag only at the next day's update. This operation does not enable backup (no historical versions); the window also provides 2 days of late-data tolerance
- **Merge rule `COALESCE(h.val, i.val)` (history first)**: uniform template, deterministic first values that never drift, stable downstream analysis. Uncovered edges: ① late-arriving data (event time earlier than the stored historical value) never rewrites the historical value; ② a new user whose first event lands later than the incremental window's look-back date range — the partition is outside the window and that user's first is missed — both are accepted edges, with no special-case handling
- `ORDER BY "#event_time" ASC, "#server_time" ASC` = when event times tie, compare ingestion time and take the earliest ingested
- **Gap self-healing**: the incremental window only tolerates late data within the window, not scheduling interruptions. If the tag's auto update fails for several consecutive days (check via step 4's polling command's `refresh_time` and computation fields), events get permanently missed — upon discovering a gap, record the current `refresh_time`, then use `user-tag update` to resubmit step 1's full SQL (`end_time` updated to the current yesterday; strictly never create again). The changed definition automatically starts recomputation; follow `next_action` and poll until `progress=100` and `refresh_time` advances, then redo step 2's incremental switch (the full recomputation overwrites the snapshot; idempotent and safe). Do not call `user-tag refresh` after either definition update

### Step 3: Enable auto update (off by default after creation; must be enabled separately)

```bash
ae-cli analysis user-tag update --project-id <id> \
  --tag-name <tag_name> \
  --enable-auto-refresh true \
  --auto-refresh-schedule '{"frequency":"daily","time":"01:01"}'
```

- Any time within the day works; default 01:01 (early-morning off-peak)
- (Operation 3's create command can carry `--enable-auto-refresh true` directly; this operation enables auto update after the incremental switch, because it runs full first then switches to incremental)

### Step 4: Verification (must do)

```bash
# Status polling: progress=100 and refresh_time has advanced from the pre-update value
ae-cli analysis user-tag get --project-id <id> --tag-names '["<tag_name>"]'
# Sample cross-validation: user-tag-member list 10 users ↔ independently compute first values on the event-table side
ae-cli analysis user-tag-member list --project-id <id> --tag-name <tag_name> --preview-rows 10
```

**Independently compute the sampled users' first values on the event-table side** (verification command; check each sampled user; IDs taken from the previous step's user-tag-member return, with quotes added for string-type IDs):

```bash
ae-cli analysis adhoc run -p <id> --zone-offset <project timezone; remove this parameter if timezone is disabled> --model-type sql \
  --definition '{"sql":"SELECT \"#user_id\", \"{{PROP}}\" AS tag_value FROM (SELECT \"#user_id\", \"{{PROP}}\", row_number() OVER (PARTITION BY \"#user_id\" ORDER BY \"#event_time\" ASC, \"#server_time\" ASC) AS rn FROM ta.v_event_{{PROJECT_ID}} WHERE \"$part_date\" BETWEEN '\''{{START_DATE}}'\'' AND '\''{{YESTERDAY}}'\'' AND \"$part_event\" = '\''{{EVENT}}'\'' AND \"{{PROP}}\" IS NOT NULL AND \"#user_id\" IN (<sampled user ID list>)) t WHERE rn = 1"}'
```

(This is the inner layer of step 1's full SQL, with the partition condition changed to a literal date range plus the sampled-user filter; table-name forms same as step 1, following the `sql_reference` returned by `sql-table list`. For custom subjects, replace `#user_id` per the subject adaptation above.)

Verification caliber notes (must be followed, or the numbers will not match):
- **For tags whose definition was changed via update**: record `refresh_time` before the update, confirm the response reports `computation.triggered_automatically=true`, follow its `next_action`, and require `progress=100` plus an advanced `refresh_time` before using `users_num` or querying members. Do not call `user-tag refresh` after the definition update
- Always carry `--zone-offset <project timezone; remove this parameter if timezone is disabled>` on adhoc queries (rules and exceptions: see the main SKILL.md "Global rules")
- Check per sample that the tag value equals the user's actual first-event value; mismatched samples are a real problem — troubleshoot the SQL and window before continuing
- The cross-check SQL's comparison range ends at yesterday, while users whose first occurred today (after the incremental switch) have already entered the tag — such sampled users having no comparison row is an expected difference, not a failure (the range end may be temporarily relaxed to today for re-checking)

## Operation 2: Create the Virtual Event Property (Lifecycle Version)

```bash
ae-cli analysis-meta virtual-property create --project-id <id> \
  --property-name '#vp@is_first_<event>' \
  --property-desc 'Is first <event display name>' \
  --table-type event \
  --select-type bool \
  --sql-expression '"#event_time" = ta_tag."first_<event>_time"' \
  --sql-event-relation-type relation_by_setting \
  --related-events '[{"eventName": "<event>"}]'
```

The lifecycle-version tag has no historical versions; the `ta_tag` reference is the current snapshot, so no tag date policy is needed.

**Stored-state read-back (must do after creation)**: `ae-cli analysis-meta property get -p <id> --table-type event --prop-name '#vp@is_first_<event>'` — check that the returned `vir_prop_column_rule` matches the submitted `--sql-expression` (a rename after a same-name conflict without synced replacement surfaces here); if inconsistent, fix per the rename-propagation rule and rebuild; for deletion see the main file's Step 5 "Mid-run cancellation".

**Timezone caliber**: the SQL tag stores raw `#event_time` (Operation 1's SQL directly SELECTs the raw column), so both sides of the equation share the same caliber and the equality holds directly. Whether timezone is enabled does not change this form (unlike Operation 4 — see its notes).

**Verification method (must do)** — Events Analysis model, past 30 days (when no first occurred in the last 30 days, rerun once with a custom range: replace `"time_range"` with `{"mode":"custom","start_time":"{{START_DATE}}","end_time":"<yesterday>"}`), total granularity, grouped by the virtual event property, checking **true-row event count = triggering user count** (the property is bool; true is the first marker; at most one per user):

```bash
ae-cli analysis adhoc run -p <id> --zone-offset <project timezone; remove this parameter if timezone is disabled> --model-type event \
  --definition '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"total","metrics":[{"event":"<event display name>","aggregation":"total_count"},{"event":"<event display name>","aggregation":"user_count"}],"groups":[{"field":{"name":"#vp@is_first_<event>","type":"event_property"}}]}'
```

- Pass = the first-value row's event count equals the triggering user count; event count > user count → first check identical-timestamp ties per the notes below; rule them out before troubleshooting the virtual event property definition; a completely missing true row in the verification result = no first occurred in the range — verify the range and state it honestly; do not judge failure
- The tag's users_num (returned by `user-tag get`) as reference: **true-row user count > users_num → the virtual event property definition is wrong** (marking events true even for users without the tag) — troubleshoot the definition; true-row user count ≤ users_num with a gap → some users first occurred outside the 30-day window, which is normal
- When event/property names conflict with same-named metrics, disambiguate using **display names**
- Custom analysis subject: append `"analysis_entity": {"id": <entity_id>}` to the verification command's definition (entity_id looked up via `project entity list` matched by `column_name`); the judgment is at subject granularity (at most one true per subject)

**Notes**:
- adhoc SQL **cannot reference `ta_tag."<tag>"` directly** (errors with Column cannot be resolved); `ta_tag` is rewritten by the engine only inside virtual event property definitions; to query tag data itself from adhoc you must explicitly JOIN the snapshot table (written like the incremental SQL's hist side). Verification must go through the `#vp@` property column itself (Events Analysis model grouping, or SQL referencing the `#vp@` column)
- **Identical-timestamp tied events**: the equality match `"#event_time" = ta_tag."first_<event>_time"` marks both rows true when a user's two earliest events have completely identical `#event_time`, breaking the "event count = user count" caliber. If verification finds event count > user count, first check identical-timestamp duplicates — reuse step 4's verification command shell (`--model-type sql`) with the SQL replaced by:

```bash
ae-cli analysis adhoc run -p <id> --zone-offset <project timezone; remove this parameter if timezone is disabled> --model-type sql \
  --definition '{"sql":"SELECT \"#user_id\", \"#event_time\" FROM ta.v_event_{{PROJECT_ID}} WHERE \"$part_date\" BETWEEN '\''<verification window start date>'\'' AND '\''<yesterday>'\'' AND \"$part_event\" = '\''<event>'\'' GROUP BY \"#user_id\", \"#event_time\" HAVING count(*) > 1"}'
```

(Event-table data queries must carry a `"$part_date"` partition predicate; metadata-level queries aggregating only the partition column, like `min("$part_date")`, can run without a predicate — see the main file's Step 1 fallback command; table-name forms follow the `sql_reference` returned by `sql-table list`); identical-timestamp ties are a rare edge — confirm with the user whether to accept, or rely on the user_count caliber in downstream analysis
- **Rename propagation**: after the tag is renamed due to a same-name conflict, the `ta_tag."first_<event>_time"` inside `--sql-expression` must be replaced in sync with the actually created name (rule: see the main SKILL.md "Same-name asset handling")

## Operation 3: Create the Daily First/Last Tag (first_last)

Fill parameters per the **target value**: when the value = `#event_time` (the first time), fill `calculation: "specific_time"`; when the value = a business property, fill `property: "<property field name>"`. Exactly one of the two is required per case; a missing one is rejected. Tag name and display name follow the naming convention summary (`daily_first_<event>_time` / "Daily First <event display name> Time"; `daily_first_<event>_<property>` / "Daily First <event display name> <property display name>").

Template for value = `#event_time`:

```bash
ae-cli analysis user-tag create --project-id <id> \
  --tag-name daily_first_<event>_time \
  --display-name "Daily First <event display name> Time" \
  --zone-offset <project timezone; remove this parameter if timezone is disabled> \
  --enable-auto-refresh true \
  --auto-refresh-schedule '{"frequency":"daily","time":"01:01"}' \
  --definition-request '{
    "type": "first_last",
    "first_last": {
      "event": "<event>",
      "occurrence": "first",
      "calculation": "specific_time",
      "time_range": {"mode": "recent", "unit": "day", "value": 1}
    }
  }'
```

When the value = a business property, replace the `first_last` block with:

```json
{"type": "first_last", "first_last": {
  "event": "<event>", "occurrence": "first",
  "property": "<target property field name>",
  "time_range": {"mode": "recent", "unit": "day", "value": 1}
}}
```

- Analysis period = today (`recent day 1`)
- **Pre-existing same-name tag**: **read-only, do not touch**; name-conflict/reuse/resume-run checking rules: see the main file's "Same-name asset handling" and "Pre-existing tags with the same name"
- **The tag timezone must be explicit**: for projects with timezone enabled, create must carry `--zone-offset` (the project default timezone or the user-specified one per the global rules) — if omitted, the tag value falls into the "local time" caliber, inconsistent with the project timezone
- **NULL-caliber difference**: the Operation 1 lifecycle route takes the "first non-null property value" (`IS NOT NULL`; see its caliber note); this operation's first_last route takes "the property value as recorded on the day's first event" — empty when that record is empty, without skipping to the next non-null value. The two routes differ on NULL handling for the same request; explain the difference when the customer cares
- **Custom analysis subject**: the create command likewise adds `--entity-id <ID>` (looked up via `ae-cli project entity list`); the backfill parameters are unchanged
- **Auto backup (branch by CLI capability)**: the daily tag's current value represents only the "today" version; the tag auto-updates once per day, not in real time — today's real-time data cannot enter the tag — so viewing day-by-day/historical data requires retaining one version per day, which is exactly what auto backup does. After the tag is created, first probe whether the CLI supports the backup switch: check whether backup-related parameters (backup / version-style naming) appear in the output of `ae-cli analysis user-tag create --help` and `ae-cli analysis user-tag update --help` (probe once per session; reuse the result throughout) —
  - **Supported** → enable auto backup for the tag with `user-tag update` using the parameter semantics annotated in help; when the parameter semantics are uncertain, do not guess — fall back to the manual-reminder path in the next item. The main file's Step 5 delivery phrasing correspondingly changes to telling the user "Auto Backup has been enabled"
  - **Not supported** → keep the status quo: **remind the user at the main file's Step 5 delivery to enable it manually on the tag settings page** (the only manual step in the operation chain); without it, auto updates from tomorrow on retain no new versions
- **Historical-version backfill** (start date = the historical query start date given by the user in Step 1): the platform requires the tag to have **≥2 date versions** for the "dynamic matching" option to appear when configuring a virtual event property (Operation 4) or reports; a freshly created tag has only 1 version (the current value) — without backfill you must wait until the next day's auto update + backup. Therefore **backfill immediately after creation** — backfill to the given start date if the user provides one, otherwise backfill 1 day (yesterday):

```bash
ae-cli analysis history-tag batch-refresh --project-id <id> \
  --tag-name <tag_name> \
  --refresh-request '{"start_time": "<start date (user-required or yesterday)>", "end_time": "<yesterday>", "only_abnormal": false, "use_user_table_type": "user_table"}'
```

(`--tag-name` takes the corresponding tag per the naming convention summary: time value `daily_first_<event>_time`; property value `daily_first_<event>_<property>`)

(`use_user_table_type` is fixed as `"user_table"`; it also applies to custom-subject tags)

**Verification (must do)**: `ae-cli analysis user-tag get --project-id <id> --tag-names '["<tag_name>"]'` — check the `definition_request` (event name, occurrence, calculation/property either-or), that `cluster_zone_offset` matches the create-time `--zone-offset`, that `entity_id` is correct, and that `computation.status=succeeded`. A×daily has no later operation as a safety net; this step is the only pre-delivery check.

**Wait rules after backfill submission (two cases by follow-up operation)**:
1. **Operation 4 follows** (B×daily, C×daily start chain, etc.): actively poll `ae-cli analysis history-tag list --project-id <id> --tag-name <tag_name>`, every 60 seconds for at most 30 minutes; once a historical date version with history_tag_status=normal appears (the first historical version ready), the dynamic-matching configuration condition is satisfied (the return also has a numeric task_status field — not a readiness criterion; do not mix them up) — continue to Operation 4; for long backfill ranges (e.g., a year) there is no need to wait for everything to finish — the remaining backfill continues in the background. On timeout, tell the user "the backfill is still running in the background" and pause the workflow — do not wait indefinitely; when the user returns later, resend the polling command and continue to Operation 4 after confirming the first historical version is ready.
2. **A×daily (no subsequent Operation 4/5)**: after submitting the backfill, **do not poll or wait** — go straight to the unified report and note that the backfill proceeds in the background.

## Operation 4: Create the Virtual Event Property (Daily Version, Dynamic Matching)

**Prerequisite: Operation 3's first historical version backfilled and ready** (`history-tag list` shows a historical date version with history_tag_status=normal).

```bash
ae-cli analysis-meta virtual-property create --project-id <id> \
  --property-name '#vp@daily_is_first_<event>' \
  --property-desc 'Is first <event display name> of the day' \
  --table-type event \
  --select-type bool \
  --sql-expression 'date_add('\''second'\'', cast((<project timezone> - "#zone_offset")*3600 AS integer), "#event_time") = ta_tag."daily_first_<event>_time"' \
  --sql-event-relation-type relation_by_setting \
  --related-events '[{"eventName": "<event>"}]' \
  --tag-date-policies '[{"tagName": "daily_first_<event>_time", "clusterDatePolicy": "AUTO"}]'
```

(This is the template for projects with timezone enabled; **projects with timezone disabled use the raw equality form** `'"#event_time" = ta_tag."daily_first_<event>_time"'`, with the other parameters unchanged.)

**Stored-state read-back (must do after creation)**: `ae-cli analysis-meta property get -p <id> --table-type event --prop-name '#vp@daily_is_first_<event>'` — check that the returned `vir_prop_column_rule` matches the submitted `--sql-expression` (including the timezone formula and the tag name; a rename without synced replacement surfaces here); if inconsistent, fix per the rename-propagation rule and rebuild; for deletion see the main file's Step 5 "Mid-run cancellation".

**The equality form's timezone caliber (important)**: the first_last tag computes the tag value by the timezone parameter at tag creation (`--zone-offset`) — for projects with timezone enabled, the tag value is each user's local time (recorded per their `#zone_offset`) uniformly shifted into the project timezone, no longer the raw `#event_time`. Therefore the event time on the left of the equation must be shifted by the same offset before comparing (`<project timezone>` is the project's `default_time_zone_offset`, e.g., 8 for UTC+8; the template above is written accordingly. **When the user explicitly specifies another timezone**: the `--zone-offset` for Operation 3's tag creation and the `<project timezone>` in this formula both change to the user-specified timezone, and the verification query's display timezone changes likewise — all three stay on the same timezone). **Projects with timezone disabled**: do not pass `--zone-offset` when creating the tag; the tag value is the raw `#event_time`, and the equality form is written directly as `'"#event_time" = ta_tag."daily_first_<event>_time"'`.

**Tag date policy (`--tag-date-policies`, a JSON array, one entry per tag referenced by the SQL; this interface's fields use camelCase (tagName/clusterDatePolicy), unlike the snake_case of history-tag and other interfaces — fill it per the template verbatim)**:

| Matching mode | Form | Behavior |
|---|---|---|
| Latest version (default; this applies when the parameter is omitted) | `{"tagName":"<tag name>","clusterDatePolicy":"LATEST"}` | All dates use the current snapshot; only the current day's events can match |
| **Dynamic matching** | `{"tagName":"<tag name>","clusterDatePolicy":"AUTO"}` | At query time, joins the day's tag version automatically by each event row's date; at most 1 true per user per day |
| Historical version | `{"tagName":"<tag name>","clusterDatePolicy":"SPECIFIED","specifiedClusterDate":"2026-09-20"}` | All event rows match against the specified date's version; true appears only on that date |

**Verification method (must do)** — Events Analysis model, past 7 days (change to past 2 days when only 1 day was backfilled; for long backfill ranges, additionally spot-check the first and last ready dates of the range), by day, grouped by the virtual event property, checking day by day that **true-row event count = triggering user count** (the property is bool; at most one first per user per day). The verification query's display timezone is chosen to match the tag's (i.e., the `--zone-offset` used at tag creation; the default for timezone-disabled projects), so event grouping and tag values are in the same timezone frame and cross-day deviation is eliminated:

```bash
ae-cli analysis adhoc run -p <id> --zone-offset <project timezone; remove this parameter if timezone is disabled> --model-type event \
  --definition '{"time_range":{"mode":"previous","unit":"day","value":7},"time_particle_size":"day","metrics":[{"event":"<event display name>","aggregation":"total_count"},{"event":"<event display name>","aggregation":"user_count"}],"groups":[{"field":{"name":"#vp@daily_is_first_<event>","type":"event_property"}}]}'
```

- Dates already backfilled and ready: true-row event count = triggering user count; dates whose backfill is not yet complete having true = 0 is normal — just wait for the background backfill to finish
- Dates in the window with **no version** (e.g., earlier dates in the window when only 1 day was backfilled) having true = 0 is normal; no action needed — do not re-backfill them
- When a historical date's backfill is complete but true = 0, re-backfill that date (`history-tag batch-refresh`) and re-check

- When event/property names conflict with same-named metrics, disambiguate using **display names**
- Custom analysis subject: append `"analysis_entity": {"id": <entity_id>}` to the verification command's definition (entity_id looked up via `project entity list` matched by `column_name`); the judgment is at subject granularity (at most one true per subject per day)
- Event rows with an empty `#zone_offset` yield an empty shift result and the equality fails (such rows are not marked); when verification finds the true total clearly below expectation, first check the event side's `#zone_offset` NULL share
- **Identical-timestamp tied events** (same as Operation 2's notes): when a user's two earliest events of the day have completely identical `#event_time`, both get marked true, breaking the per-day "event count = user count" — first check that date's identical-timestamp duplicates (troubleshooting SQL same as Operation 2's notes, with `"$part_date"` constrained to that date), and confirm with the user whether to accept
- **Rename propagation**: after the tag is renamed due to a same-name conflict, the `ta_tag."daily_first_<event>_time"` inside `--sql-expression` and the `tagName` in `--tag-date-policies` must be replaced in sync with the actually created name

## Operation 5: Create the Virtual Event (Scenario B deliverable / Scenario C start-point asset)

Lifecycle version (filtering Operation 2's virtual event property), event name `ta@first_<event>`, description "First <event display name>":

```bash
ae-cli analysis-meta virtual-event create --project-id <id> \
  --event-name "ta@first_<event>" \
  --event-desc "First <event display name>" \
  --events '[{"event_name":"<event>","filter":{"relation":"and","items":[{"field":{"name":"#vp@is_first_<event>","type":"event_property"},"operator":"is_true"}]}}]'
```

Daily version: replace `field.name` with `#vp@daily_is_first_<event>` (Operation 4's dynamic-matching property); event name `ta@daily_first_<event>`, description "Daily First <event display name>".

**Scenario C's object switch**: when Scenario C builds a start virtual event, the wrapped object is the **start event XX itself** (not the target event) — `--event-name` still follows the naming convention (`ta@first_<XX>` / `ta@daily_first_<XX>`), and `--events`'s `event_name` is filled with the XX event's own name.

**Start virtual event caliber**: build a start virtual event only when the start point is a "(daily) first XX" and the event itself has no usable ready-made "is first" property; when the event itself has a usable property, skip this operation and filter directly on the start side in the interval model at computation time (see Operation 6's "start-event filter").

- Virtual events are logical definitions with no physical partitions; an adhoc SQL query for `"$part_event" = 'ta@first_<event>'` returning 0 is normal; the virtual event itself gets no independent verification — its correctness is guaranteed upstream (lifecycle version → Operation 2's verification; daily version → Operation 4's verification)
- **Rename propagation**: after the `#vp@` virtual event property or the virtual event itself is renamed due to a same-name conflict, the filter's `field.name` and `--event-name` must be replaced in sync with the actually created name
- **Stored-state read-back (must do after creation)**: `ae-cli analysis-meta virtual-event get -p <id> --v-event-id <event_id>` (event_id looked up from event list by name) — check that `rule.events`' wrapped event name and filter fields are correct (Scenario C wraps the XX event's own name); the filter's stored state is the platform's normalized form (`ta_filters`) — checking that field names/values/operator semantics match suffices, no verbatim match required; if inconsistent, fix per the rename-propagation rule and rebuild; for deletion see the main file's Step 5 "Mid-run cancellation"

## Operation 6: Interval Analysis Computation (Scenario C's execution method)

**How to compute depends on the start point**: the start-point three-way branch (one-time event / count every occurrence / "(daily) first XX" — with a usable ready-made property on the event itself, compute directly with the start-event filter; otherwise build the start virtual event first) and the start-point asset chain are in the main file's Step 4 Type C; this operation covers only the interval computation itself.

**The model's pairing rule (shortest-interval principle)**: each start event is paired with the **first** target event that occurs **after** it to compute the interval; when a user has consecutive repeated start events, only the **last** start counts. Therefore the target side needs no preprocessing — what the model pairs is precisely the first target event after the start point

**Execution** (once the start event is ready; fill the calibers confirmed in the main file's Step 3 for the analysis window and maximum interval):

```bash
ae-cli analysis adhoc run -p <id> --zone-offset <project timezone; remove this parameter if timezone is disabled> --model-type interval \
  --definition '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day",
  "interval":{"initial_event":"<start event or virtual event name>","return_event":"<target event English name>","window":{"value":7,"unit":"day"}}}'
```

- Fill `time_range` (the analysis window) and `window` (the maximum allowed interval) per the calibers confirmed in Step 3; the two default tiers offered at plan confirmation:
  - One-time / lifecycle start point (e.g., "how long after registration until the first payment", time to first payment): analysis window past 30 days, maximum interval 7 days (the template is this tier; enlarge the interval for long-cycle ice-breaking cases)
  - Daily-first start point (e.g., "how long after the daily first login until payment"): analysis window past 7 days, maximum interval 1 day (change the template's `time_range` `value` to 7 and `window`'s `value` to 1)
  - Users whose first behavior occurs outside the window are silently excluded; adjust the window per the user's needs
- `initial_event` takes the start event or virtual event name (virtual events like `ta@first_pay` / `ta@daily_first_pay`); `return_event` takes the target event's English name
- **Start-event filter (when the start point is a "(daily) first XX" and the event itself has a usable ready-made "is first" property — compute directly without building a start virtual event)**: fill `initial_event` directly with XX's English name and add an `initial_filters` array inside `interval` — constraining the start event only (the target-side counterpart is `return_filters`; **do not use the un-prefixed `filters`** — that is a global filter constraining both start and target; using it for one-sided start filtering computes 0 over the whole table):

  ```json
  "initial_filters": [{"event_property_name": "<ready-made property name>", "operator": "is_true"}]
  ```

  For boolean, use `is_true` with no `values`; for 0/1 or yes/no style encodings, use `eq` with the confirmed "first" value — `values` elements are always strings (numeric values filled as `"1"`; string values quoted). When the property name conflicts with a same-named virtual property, disambiguate using display names (same rule as Operations 2/4). "Daily first XX" start points likewise apply (the property semantics must match the time range)
- Custom analysis subject: add `"analysis_entity": {"id": <entity_id>}` to the definition (entity_id looked up via `ae-cli project entity list -p <id>` matched by `column_name`); intervals are then paired at the selected subject's granularity; without the field, the default is the user subject (the UI-side interval analysis likewise supports selecting the analysis subject)
- After delivering the result, attach the UI configuration path (the Interval Analysis model, start/target event selection as above; when computing directly with the start-event filter, select XX itself as the start event and add the first-marker filter) for the user's self-service reuse
