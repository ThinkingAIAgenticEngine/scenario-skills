# push_spec.json Field Authoritative Definition

> Three-part structure: **data pipeline (queries) × message template (template) × slot filling**.
> data task = the engine deterministically fills slots; report task = the LLM fills slots in two stages (same architecture).
> All RUN phase behavior is governed by this file; for the BUILD phase process see SKILL.md.

## Top-level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `task_name` | string | Yes | Task name |
| `project_id` / `project_name` | int / string | Yes | Primary project; each query of a multi-project task may override it individually |
| `projects` | array | No | Multi-project task: lists all projects (informational; used for Step 2 item-by-item verification, not read at RUN time) |
| `cli_version` | string | No | Measured `ae-cli --version` value at BUILD time; the RUN phase script compares it automatically, drift only triggers a warning |
| `auto_push` | bool | No | Set to true after first-push acceptance (RUN push safeguard; the automation message carries `--push` itself, either one taking effect is enough; **report tasks need not set it** — push authorization rides on the two-stage commands, and a full-run auto_push/--push is rejected by the script) |
| `schedule_hint` | object | No | Non-authoritative snapshot (informational, not consumed at RUN time): the authoritative schedule is the automation scheduling parameters |
| `env` / `cli` | object / string | No | Escape hatch for the ae-cli execution path (`env.ae_cli_path` takes precedence over `cli`; default `"ae-cli"`) |
| `content` | object | Yes | Content section (see below) |
| `delivery` | object | Yes | Delivery section (see below) |
| `timezone` | object | Yes | Timezone section (see below) |

## content Sub-fields (data Task)

```json
{
  "content": {
    "kind": "data",
    "window_freq": "daily",
    "queries": [ ... ],
    "message": { "template": "builtin:plain" },
    "file": { "name_template": "detail_rows_{date}.csv", "detail_query": "detail_rows" },
    "on_empty": "push",
    "max_message_kb": 8
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | string | Yes | `data` (engine fills slots) / `report` (LLM fills slots, see the report section) |
| `window_freq` | string | Yes | **Data window frequency (authoritative)**: `daily` / `weekly` / `hourly` / `monthly` / `rolling:N` (N=2~90, the last N complete days up to yesterday, excluding today — for scenarios like "push the last 7 days every day"). Window = see the "Window Semantics" section. For daily/weekly/hourly/monthly windows the BUILD phase must match the automation `--schedule-kind` (a mismatch silently computes the wrong window); `rolling:N` is decoupled from the schedule frequency (the window is computed as "yesterday going back N days" from the trigger moment, daily scheduling means the window rolls forward each day, weekly scheduling also works). The SQL query of a rolling task **MUST** contain `{{window_start}}`/`{{window_end}}` (static validation) |
| `queries` | array | Yes | Query list (at least 1), see below |
| `message` | object | Conditional | Message shape section: `{template: <string|object>, preview_rows?: int}`, see "Message Template". **Mandatory for data tasks; optional for report tasks but the type must be an object** (report only consumes `preview_rows`/`max_message_kb`, `template` is not consumed, see "Report Scenario" — a string/number shape → exit code 2, to prevent a bare exception at render time) |
| `file` | object | No | Presence = this task attaches a CSV file (detail rows + file / pure file shape). `name_template` supports `{date}` (= **window start date** YYYYMMDD — daily = yesterday, weekly = last Monday, monthly = the 1st of last month, aligned with the data window; weekly/monthly interval data lands on the window start point); **only the single placeholder `{date}` is supported**, any other text is kept literally. The value must be a leaf filename in the task working directory: absolute paths, path separators, `.`/`..`, and symlink escapes are rejected. `detail_query` **MUST point to a mode=rows query** (that query produces the full file, fetch defaults to export). The file section of a report task is only valid for the HTML template and only consumes `name_template` (attachment naming, no detail_query needed) — text/card reports produce no attachment, configuring a file section is rejected by static validation (exit code 2). File export is **NOT truncated by the message size guardrail** — data completeness is bounded by the SQL LIMIT (when the LIMIT is hit, an "first N rows metric definition" completeness note is appended to the message, see the R4 size truncation section), export failure is fail-loud |
| `on_empty` | string | No | One value configured per section (field granularity). **A single section with skip + 0 rows still renders the "No data this period" placeholder**; skip only suppresses the entire push when **all sections have 0 rows and skip** |
| `max_message_kb` | int | No | Message size guardrail in KB, default 8 (R4 tiered truncation trigger line; only for text/rich text shapes — card size is controlled by preview_rows) |
| `title_template` | string | No | Report title template, vocabulary `{{task_name}}`/`{{date}}`/`{{window_range}}` (for weekly/monthly windows `"[Report]{{task_name}} {{window_range}}"` is recommended — interval dates prevent misreading as a single day), the default built-in title already uses the interval. **Only consumed when kind=report** — for data tasks filling it does not error but has no effect (the rendered title is fixed as "[Push]...") |
| `report` | object | Conditional | Mandatory when kind=report (`{outline, template}`, see the "Report Scenario" section); not configured for kind=data |

## queries[] Sub-fields

| Field | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Section name (template placeholders reference it, e.g. `{{q.payment_amount.rows}}`) |
| `mode` | string | No | `value` (**default**, produces numbers: single row with multiple columns, one number per column) / `rows` (produces row sets: TopN / lists / detail rows) |
| `source` | string | No | `sql` (default, uses sql_template) / `dashboard_report` (uses dashboard_id+report_ids). **The file section's detail_query only supports sql** (file export goes through the SQL engine) |
| `sql_template` | string | Conditional | Mandatory when source=sql. Time placeholders: `{{date}}` / `{{window_start}}` / `{{window_end}}` (timestamp-column scenarios, only comparable with timestamp columns; before comparing with `$part_date` you must first truncate to a date string via `substr('{{window_start}}', 1, 10)` — comparing the original string with hours/minutes/seconds directly errors) / `{{week_start}}` / `{{week_end}}` (weekly only) / `{{month_start}}` / `{{month_end}}` (monthly only). **Both weekly and monthly may instead use `{{window_start}}`/`{{window_end}}`** (timestamp-column scenarios, with hours/minutes/seconds) (the two guards are symmetric). Week/month placeholders have bidirectional guards: a weekly/monthly window missing the corresponding placeholder with no window alternative errors; a non-weekly/non-monthly window containing week/month placeholders also errors (to prevent silently wrong windows). Business placeholders are all replaced during the BUILD phase; a leftover at run time is an immediate error |
| `dashboard_id` | int | Conditional | Mandatory when source=dashboard_report |
| `report_ids` | array | Conditional | **When source=dashboard_report and mode=value, it must be explicitly specified with exactly 1 entry (static validation exit code 2)** — not specifying it reads the entire Analysis Board merging multiple Reports, and `v.<column>` takes the first row of the merged result = picking up wrong data. Merging multiple Reports in a rows query is legitimate usage (concatenating structurally identical Reports, column structures must be consistent). `--report-ids` takes a **JSON array**; **the run pipeline result is always capped at 100 rows per Report**; above the cap that query goes through export (the fallback path strips total rows marked by the first column — Overview/Total/total/summary; export artifacts have no row_metadata, scope=total cannot be determined. Business data rows whose first-column value happens to be exactly these four words are also stripped — rare; when a test run finds fewer rows than expected, check the stderr "stripped N total rows" log) |
| `fetch` | string | No | Data fetching pipeline (locked during the BUILD phase per user scenario, independent of source): `run` (synchronous bounded — bounded message body scenarios) / `export` (asynchronous full volume — detail-row export / large tables / csv file section). Default inference: file section detail_query → export, everything else → run. RUN phase fallback: a query locked to run that hits has_more / repeated timeouts (QUERY_TIMEOUT retried 2 times) automatically switches to export. See the "Data Fetching Pipeline" section |
| `summary` | array | No | **Detail aggregation declaration** (how decision point a lands): `[{column, agg, name}]`, `agg ∈ sum | count | count_distinct`. The engine computes aggregations over the full detail rows (same batch of rows → the aggregate and the detail rows are naturally consistent in metric definition); aggregated values are referenced by templates via `{{agg.<name>}}`. `column` is the detail column name (**validated at run time**: row set non-empty but column missing → that section is treated as a fetch failure, exit code 1 — fail-loud, to prevent silently wrong numbers); for `agg: count` column may be omitted (= row count). Aggregation names are globally unique (same name across queries → exit code 2). value queries do not need summary (they produce numbers themselves). **When 0 rows, the aggregation yields null → displayed as `-`** (unified symbol with empty data, to prevent mixing "no data" with "true zero"); when sum encounters an unparseable value (currency symbols/units and other dirty values) → **that section is treated as a fetch failure (exit code 1)** — silently ignoring it would push an undersized total into the customer group, fail-loud; when a section's fetch fails, `{{agg.*}}` renders a `[Fetch Failed]` placeholder |
| `on_empty` | string | No | When this section has 0 rows: `push` (default, pushes the "No data this period" placeholder) / `skip` (a single section with skip + 0 rows still renders the placeholder; only when all sections have 0 rows and skip does the whole push not happen). value queries should be **aggregations without GROUP BY** (normally always 1 row; on a no-data day an all-NULL row displayed as `-`); with GROUP BY or an empty Analysis Board window, 0 rows are legitimately produced — then `v.<column>` also renders `-` (an empty window is not a fault, do not refuse to push) |
| `project_id` | int | No | Multi-project task: each query specifies its own; defaults to the top-level project_id |
| `chart` | string | No | Chart type: `line` (line chart, default) / `bar` (bar chart). **Scope of effect**: ① report task mode=rows queries — the HTML template generates an inline SVG chart from the first 2 columns of the query result as "label column + value column"; the card template generates a VChart chart component — the long table's first column serves as the X axis and each remaining numeric column becomes a line (multiple lines possible), long table field names are fixed as `date` (first column) / `metric` (column name) / `value` (numeric), VChart xField/yField/seriesField follow this; ② data task mode=rows queries under the `builtin:card_chart` template — each rows section renders a VChart chart per its `chart` (default line; sections in the same card may each be line/bar). **No effect**: value queries (they go through the KPI branch/summary row, no chart), data task plain/rich/card_table templates (the message has no chart) — configuring it there is silently ignored, do not configure it. The chart type of an inline custom VChart template is written in its own chart_spec and does not go through this field |

## Message Template (message.template)

Two shapes, pick one:

1. **Reference a built-in template name** (string, e.g. `"builtin:card_table"`) — the factory reference templates for the five shapes, see the "Built-in Template Library" catalog in delivery-mechanisms.md. Common scenarios are a one-line configuration (`builtin:rich` is recommended only for im_cli — on webhook channels markdown symbols enter the text as-is).
2. **Inline custom template** (object) — the message/card skeleton finalized through BUILD phase exploration is locked into the spec as-is. The exploration path (test delivery → read errors → iterate → accept) is in "BUILD Phase Shape Probing Methodology" in delivery-mechanisms.md.

| Field | Type | Required | Description |
|---|---|---|---|
| `template` | string \| object | Yes | Built-in template name / inline template skeleton |
| `preview_rows` | int | No | Row-set display cap inside the message, default **100** (shared by inline tables, table components, file preview; above the cap, an "X rows total + first N rows" annotation is shown). It is a display-layer truncation, not a data truncation |

### Inline Template Skeleton

- Text types (plain/rich text): a string skeleton, placeholders embedded directly in the text
- Card types: `{"kind": "card_2.0", "header": {...}, "body": {"elements": [...]}}` — Feishu card 2.0 structure; element types and how to write them are in "Card Reference Patterns" in delivery-mechanisms.md (VChart chart / table / markdown components)
- Placeholder positions: embedded in text (in any string); **structured whole-value placeholders only in object value positions** (e.g. `"rows": "{{q.detail_rows.rows}}"` — a list element position does not parse whole-value placeholders, it degrades to a text hint)

### Placeholder Vocabulary (engine-supported data bindings, closed set)

| Placeholder | Product | Description |
|---|---|---|
| `{{task_name}}` | string | Task name |
| `{{date}}` | string | Window attribution date (YYYY-MM-DD; title/body metric definition — window start date; for weekly/monthly windows the window start date) |
| `{{window_range}}` | string | Window interval display string: daily = single day (same as `{{date}}`); weekly/monthly = `start~end` (e.g. `2026-09-21~2026-09-27`, end = the last day inside the window); hourly = hour window (`2026-10-05 09:00~10:00`). For weekly/monthly window titles **prefer this** (writing only the start date would be misread as based on single-day data); the built-in template title and the statistics-window row already carry it by default |
| `{{window_start}}` / `{{window_end}}` | string | Window start/end (with hours/minutes/seconds, timestamp-column scenarios) |
| `{{q.<label>.rows}}` | row set | The row list of that rows query (each row a "column name → value" dict, **key = the query's original column name**; directly usable as Feishu table component rows, columns[].name written with the actual column names). **Only usable in card template fields** — appearing in a text skeleton degrades to a "(first N items of the row-set data...)" hint sentence and the rows are not expanded. **Row-set cell values pass through as-is (no thousands separators)** — phone numbers/order numbers/IDs stay copyable and consistent with the CSV attachment; thousands separators are only used for value-section numbers and `{{agg.*}}` |
| `{{q.<label>.long}}` | long table | The rows query's wide table converted to a VChart long table (`date/metric/value` fields — directly usable as the chart component's `data[].values`). Only usable in card template fields |
| `{{q.<label>.n}}` | int | Row count returned by that query (a failed-fetch section renders a short `[Fetch Failed]` placeholder instead of a number — the technical raw text only lands in run_result/stderr, R1) |
| `{{q.<label>.v.<column>}}` | single value | The value of a column of that value query (single row, multiple columns). Column names are validated at RUN time (row exists but column does not → exit code 2 config typo; query returns 0 rows → renders `-` empty-window symbol) |
| `{{agg.<name>}}` | numeric | The aggregation product declared in summary |

> `{{week_start}}` / `{{week_end}}` / `{{month_start}}` / `{{month_end}}` are **only usable in SQL templates** (see the bidirectional guard on the `sql_template` row) — appearing in message templates or title_template is rejected by static validation (out-of-vocabulary placeholder).

> Business placeholders in SQL templates such as `{{event_name}}` / `{{aggregate_expr}}` are fully replaced by the BUILD phase Agent (sql_template row description) and do not belong to this vocabulary — the table only lists the bindings the engine supports at run time.

> Closed-surface statement: the placeholder vocabulary = the set of data transformations the engine supports (row set/long table/aggregation/single value). **The template structure dimension is fully open** (any component combination and layout may be locked); adding a new data transformation = modifying the script. This is the necessary price of RUN determinism — the engine must predictably transform the data before filling it into the template.

### Static Validation (RUN phase, exit code 2)

- A label / aggregation name referenced by a template placeholder does not exist in the spec → invalid configuration (**static validation**, `--check-spec` can trigger it standalone)
- A report inline HTML template's `{{slot:<section_id>}}` references a non-existent outline section, or `{{data:<label>}}` references a non-existent query-section label → invalid configuration (**static validation**, die 2 — symmetric with data task placeholder validation; previously such typos only landed a `[Unmatched Slot]` + WARN in the rendered artifact, now BUILD phase `--check-spec` intercepts them. Reference comparison is an exact match of the raw text — **no whitespace allowed after the colon**, a reference with whitespace also dies with 2, same treatment as render-time behavior) |
- Message template / title_template contains an **out-of-vocabulary placeholder** (a `{{...}}` token outside the closed vocabulary, e.g. `{{week_start}}` — week/month placeholders are only usable in SQL templates, `title_template` vocabulary is `{{task_name}}`/`{{date}}`/`{{window_range}}`) → invalid configuration (to prevent literal pass-through into the group at RUN time) |
| `v.<column>` column-level references and summary-referenced columns: **validated at RUN time** — column names are only known once the query result comes out; a missing column found at render/aggregation time is handled per the table above (v.column → exit code 2; summary column → section-level failure exit code 1)
- `file.detail_query` is not a mode=rows query → invalid configuration
- `queries[].chart` is not `line`/`bar` → invalid configuration (exit code 2)
- When `window_freq` is `rolling:N` (N=2~90), an sql-source query missing either `{{window_start}}`/`{{window_end}}` → invalid configuration (exit code 2 — misusing `{{date}}` only counts the single day of the window start); week/month placeholders are blocked by the week/month guard as usual under rolling
- The `mechanisms[].as` field is deprecated; its presence is invalid configuration (exit code 2) — the sending identity follows the mechanism (im_cli = user identity always user, webhook = bot identity), not configured separately
- Card templates (`builtin:card_*` / inline `card_2.0`) require the spec to configure at least one **card-capable mechanism** (im_cli in lark-cli default form or feishu webhook) — command-template mechanisms only cover text+file and do not support cards; a card task configured with pure template mechanisms is rejected by static validation (switch to a text shape during BUILD, do not register an undeliverable card template as an automation)
- Command templates (`send_template`/`send_file_template`) being in string form / out of placeholder vocabulary (including near-miss typos like `{Text}`) / violating sub-template subsets / `success` structurally invalid or appearing alone (no template configured at all) → invalid configuration (exit code 2); `success` is consumed together with `send_template` or `send_file_template`
- HTML reports (template=daily/weekly/monthly/inline HTML) require at least one `file_ok` mechanism — the attachment is always produced, and static validation rejects otherwise (`text`/`card` reports produce no attachment and are not subject to this; configuring a `content.file` section on either is a config typo, rejected by static validation)
- **SQL template placeholder vocabulary is closed (static validation)**: `sql_template` containing any `{{...}}` other than `{{date}}/{{window_start}}/{{window_end}}/{{month_start}}/{{month_end}}/{{week_start}}/{{week_end}}` (e.g. unreplaced recipe template variables `{{aggregate_expr}}`/`{{project_id}}`) → exit 2 — a missed replacement left to RUN time means a daily no-op run; the week/month guards / leftover detection run at RUN time in `render_sql` (exit 2), and BUILD phase test delivery always truly executes the SQL rendering
- Intercepted before `render_sql` executes: SQL containing `SELECT *` or an event table (`ta.v_event_*`) query missing a `$part_date` predicate → exit code 2; no LIMIT → WARN (script-level backstop for the recipes core rules — $part_date filtering / no SELECT * / mandatory LIMIT). **UNION per-branch interception**: the platform only checks whether the whole SQL contains `$part_date` (verified on the platform), so every branch of a top-level UNION containing an event table must carry its own `$part_date` predicate; a single branch missing it → exit code 2 (a missing predicate causes a full table scan and silently wrong numbers); containing a `COUNT` aggregate without `NULLIF` wrapping → WARN (rule ⑥ heuristic reminder)
- A field in the spec not registered in the script (outside the reconciliation checklist) → stderr WARN (field reconciliation mechanism, to prevent doc-script drift)
- Channel feasibility is **NOT validated here** (no hard-coded matrix) — rely on the BUILD phase primary mechanism passing a test delivery with the final template (see delivery-mechanisms.md)

## delivery Sub-fields

| Field | Type | Required | Description |
|---|---|---|---|
| `mechanisms` | array | Yes | Ordered mechanism list. For the **same delivery target**, the first success wins (the rest = backups; on primary failure, switch in order); **different targets are each delivered independently (broadcast)**. Target determination: the `group` field takes precedence (same `group` = a cross-channel primary-backup group — e.g. "if Feishu fails, send via WeCom": two mechanisms share one group; without a group, targets are determined by each mechanism itself, and cross-channel is always different targets = broadcast double-send). Any target ultimately undelivered → exit code 3 |
| `mechanisms[].mechanism` | string | Yes | `im_cli` / `webhook` |
| `mechanisms[].tool` | string | Conditional | Mandatory for im_cli: a bare PATH-resolved channel CLI executable name ending in `-cli` (for example `lark-cli`). Paths, shells, interpreters, and generic executables are rejected. Without `send_template`, only `lark-cli` is accepted and invoked with its built-in argument form; other channel CLIs must configure a `send_template` command template or static validation exits 2. |
| `mechanisms[].send_template` | array\<string\> | No | **Command template (custom channel CLI direct-send adapter)**: an argv array of arguments element by element (shell strings forbidden — concatenation has an injection surface and messages containing spaces/newlines would shatter). The first element must be exactly `{tool}`, so the locked channel CLI is the only executable. Closed placeholder vocabulary: `{tool}`/`{target_id}`/`{target_type}`/`{text}` (an unknown token or `{file}` appearing here → exit 2). BUILD phase probes the CLI argument form (`--help`) → draft the template → test delivery → user acceptance → lock. rich text and text share this template (channel rendering quality is adjudicated by test delivery); cards are not supported (cards only via lark-cli default form / Feishu webhook) |
| `mechanisms[].send_file_template` | array\<string\> | No | File delivery command template (same rules as above; `{file}` = relative file name, `{display_name}` = display name, execution cwd = the file's directory). A mechanism with `send_template` configured for a file task must have this template to count as file-capable |
| `mechanisms[].success` | object | No | Success determination rule for command templates (consumed together with `send_template` or `send_file_template`; appearing alone with neither configured → exit 2). `{"type": "exit_code", "value": 0}` (default — exit code equal to value means success, value defaults to 0) or `{"type": "stdout_json", "field": "errcode", "value": 0}` (exit code 0 AND the specified field of stdout JSON equals value; **for the stdout_json type both field and value are mandatory** — with a default value, a missing field would falsely judge success on None==None; value type must match the CLI output field, number to number, string to string). If a CLI envelope is identified during the BUILD phase, lock the more reliable rule; timeouts count as network-class retries, other failures are not retried |
| `mechanisms[].target` | object | Conditional | Mandatory for im_cli: `{type: chat|user, id: oc_xxx or ou_xxx}` |
| `mechanisms[].group` | string | No | Cross-channel primary-backup group identifier (non-empty string; leading/trailing whitespace is normalized at lock time — if " g1 " and "g1" were not normalized they would silently become two groups = broadcast double-send). Mechanisms sharing one group share the delivery-target semantics: first success wins, failure switches in order (e.g. "Feishu im + WeCom webhook configured with group=backup1" = cross-channel fallback, not broadcast double-send). When not configured, targets are grouped by each mechanism itself — cross-channel = different targets = broadcast |
| `mechanisms[].webhook_url` | string | Conditional | Mandatory for webhook (kind is recognized from the URL domain: qyapi.weixin.qq.com→wecom / open.feishu.cn→feishu / oapi.dingtalk.com→dingtalk, anything else custom_webhook) |
| `mechanisms[].webhook_kind` | string | Conditional | Mandatory for webhook: `wecom` / `dingtalk` / `feishu` / `custom_webhook` |
| `mechanisms[].file_ok` | bool | No | File delivery of this mechanism passed BUILD phase real testing (default false). When false, RUN phase file tasks skip this mechanism with a warning |
| `mechanisms[].form_ok` | bool | No | The mechanism's **final shape (template) test delivery** passed BUILD phase real testing (channel × shape feasibility relies on measured flags, not a hard-coded matrix). The primary mechanism must be true to lock. **Not consumed at RUN time** (pure BUILD phase record) — degradation semantics see R5 |
| `file_name` | string | No | Legacy field, superseded by `content.file.name_template` (kept for compatibility reads — only the report HTML attachment naming falls back to it, see "Report Scenario"). It follows the same leaf-filename restriction and cannot contain a path. |

> Email is not supported on the automation automation path (neither mechanism class has email capability) — when email is needed, route to the Analysis Board push path and clearly inform the user during the BUILD phase.

## timezone Sub-fields

```json
{ "multi_tz": true, "offset": 8, "offset_source": "user", "zone_offset_column": "#zone_offset" }

The timezone is UTC-offset semantics (not an IANA timezone name) — DST regions have a 1-hour offset during the transition period and need manual adjustment; non-DST regions are unaffected.
```

| Field | Type | Required | Description |
|---|---|---|---|
| `multi_tz` | bool | Yes | Gate = `project info get → time_zone_enabled` (probed during BUILD) |
| `offset` | number | Conditional | The single numeric field is branched by the gate: **true** = data settlement timezone (user-confirmed; if unconfirmed, the project default `default_time_zone_offset` is used, driving the SQL shifted_time conversion + window day-cutting + title date); **false** = this field is not stored (treat as no timezone concept — the window cuts days by the server calendar, data is queried directly by `$part_date`, never mention timezone to the user) |
| `offset_source` | string | No | `"user"` / `"project_default"` (informational; example in the timezone code block above) |
| `zone_offset_column` | string | Conditional | The conversion column when multi_tz=true and the source is SQL (probed from project info `time_zone_offset_column`) |
| `server_tz` | number | No | **Locked during BUILD when multi_tz=false**: the server timezone's hour offset (converted from `+list-automations → serverUtcOffset`, in the form "UTC+08:00") — the RUN phase window day-cutting uses the spec value directly, not a run-time read (a failed read silently falls back to +8, which would give a wrong window on overseas deployments); old specs without this field go through the run-time read for compatibility |

**The schedule timezone does not go into the spec** (registration is completed during BUILD): non-multi-timezone projects = the user's moment is registered as-is (exception: only explain the conversion when the user proactively mentions timezone); multi-timezone projects = after confirming the stated timezone, convert to the server timezone for registration (the server timezone is read from `+list-automations → serverUtcOffset`; **the sandbox `date` is the container clock, forbidden as a basis**).

The settlement timezone of Analysis Board sources / Analysis Board pushes = **the Analysis Board's own timezone setting** (decoupled from the spec offset, which only governs the title date) — the BUILD phase compares the expected settlement timezone vs the Analysis Board's current timezone; if unequal the user picks one of three: modify the Analysis Board (a write operation) / save a copy / accept the current metric definition (details in "Analysis Board Data Source" in automation-recipes.md).

---

## Data Fetching Pipeline (two-layer structure, RUN phase script behavior is authoritative)

**The BUILD phase locks `queries[].fetch` per user scenario** (independent of the data source):

| User scenario | fetch | Rationale |
|---|---|---|
| Metric summaries, TopN lists, report aggregate data (bounded message body) | `run` | Synchronous, stdout JSON, immediate success/failure judgment — best for automation loops |
| Exporting tens of thousands of detail rows, explicitly large tables, csv file shape | `export` | Result volume large/unknown; no need to run first and then switch |
| Existing Analysis Board Reports available | Unrestricted (run or export by volume) | Analysis Board source preferred over rewriting SQL — the user tunes the metric definition by editing the Analysis Board directly, the task only takes the IDs |

**RUN phase fallback (queries locked to run)**:

```
run done & has_more=false  → data complete, use directly (WARN on suspected truncation when returned rows == SQL LIMIT — symmetric across the run/export dual paths)
run done & has_more=true   → switch to export for full-volume fetch (do not retry with a larger request row count — the synchronous cap is a cluster configuration, differs per customer)
run QUERY_TIMEOUT          → retry (2 times total) → still timing out → switch to export (the async pipeline has no synchronous timeout limit)
Deterministic failure (syntax / table not found) → placeholder + exit code 1 (do not switch to export — switching would be pointless)
```

**export execution** (both sources share one pipeline): submit → `--wait --wait-timeout-seconds 300` (short window, not enlarged — to avoid delaying failure discovery) → complete → download and deliver; **wait timeout (ASYNC_WAIT_TIMEOUT) is NOT a failure** (the remote task is not canceled) → `analysis run wait --run-id` continues, polling in short windows until a terminal state (up to 20 rounds); a real failure → placeholder + exit code 1, the message carries the run_id for manual follow-up.

**Pipeline capability boundaries (measured)**:
- run (adhoc): `--preview-rows` is a request parameter, returned = min(request, cluster synchronous cap, actual row count); the synchronous cap is a **cluster configuration value, different per customer** (without the parameter the cluster default is used); synchronous timeout 120/180s (timeout error code QUERY_TIMEOUT, CLI exit code 1)
- run (dashboard): the result is **always capped at 100 rows per Report** (regardless of request parameters); for a multi-Report Analysis Board, has_more is **judged per Report**; total rows (Overview/total) are automatically stripped
- export: **the pipeline has no row-count cap** (but a LIMIT in the SQL truncates the export — LIMIT must be ≥ the BUILD phase row-count assessment cap, the script WARNs when it is hit); remote runtime cap 6 hours; the artifact is gzip (magic-number sniffing decompression; adhoc=CSV / dashboard=JSONL routed parsing; a corrupted JSONL line is fail-loud section-level failure)

## Window Semantics (key difference between the push side and the alert side)

Window = **the last complete period** (what is pushed at the scheduled moment is the period that just ended, not the current one):

| window_freq | Window |
|---|---|
| `daily` | All of yesterday (natural_day) |
| `weekly` | The last natural week (natural_week, Monday~Sunday) |
| `hourly` | The last full clock hour |
| `monthly` | The last natural month (the 1st of last month ~ month end) |
| `rolling:N` | The N complete days up to yesterday (an interval like 09-30~10-06, excluding today; decoupled from the schedule frequency, daily scheduling = rolling daily) |

There is no `today_to_now` (that is alert-side semantics). Weekly/monthly report SQL uses `{{week_*}}`/`{{month_*}}`, or substitutes `{{window_start}}`/`{{window_end}}` (timestamp-column scenarios, the two guards are symmetric) — the script guards bidirectionally. **rolling:N is the special case**: the SQL MUST use `{{window_start}}`/`{{window_end}}` (static validation enforces this — under rolling, `{{date}}` = the window start date (N days ago); mistaking it for a single-day filter would count N days as 1 day); week/month placeholders are unusable under rolling (the guards block them as usual). Display of the window interval in the title/statistics-window row: weekly/monthly/rolling show the full "start~end" interval, daily/hourly show a single day/hour window — rolling tasks carry this interval display by default, users do not need to infer the range from the task name.

## Row-count and Size Gates (RUN phase semantics, authoritative table)

| Shape | Behavior | Message |
|---|---|---|
| In-message row set (inline table / table component / preview) | Render the first `preview_rows` rows (default 100) + annotation; **plain-text inline tables show only the first 6 columns per row** (the text row set serves as a summary — the full column set goes to the card table component or the CSV attachment) | `X rows total, showing the first N rows` |
| File export (csv) | Not truncated by the message guardrail (data completeness is bounded by the SQL LIMIT — when the row count hits the LIMIT, the message appends a completeness note + a run_result record); data rows counted excluding the header; file name `{date}` = window start date | `X rows total, file xxx.csv generated` (with a ⚠ completeness hint line when the cap is hit) |
| 0 data rows | Each section's `on_empty` (field granularity, default push placeholder); also applies to csv empty data | `No data this period` |
| Fetch failure | fail-loud: placeholder + exit code 1 (export failure carries the run_id for manual follow-up) | Fixed plain-language placeholder (`[Fetch Failed]` short marker / R3 whole-message copy) |

## Execution Semantics of Design Decisions (RUN phase script behavior, numbered R1~R5)

- **R1 Partial push**: when any query fails (including export pipeline failure), the remaining sections render and push normally, the failed section shows a short `[Fetch Failed]` marker (the technical raw text only lands in run_result's `queries[].error`/`error_detail` and stderr, never enters the customer group), overall **exit code 1** (visible as an automation failure mark). Built-in and inline templates share the same contract — when an inline template references a failed section, `{{q.*}}`/`{{agg.*}}` render failure placeholders (empty row-set slot + WARN); only "referencing a section/aggregation name that does not exist in the spec" gives exit code 2
- **R2 No data**: each section's `on_empty` (field granularity, effective at section level for non-skip); default push placeholder (the principle: silence of a push task = failure); all sections skip with 0 rows → no push
- **R3 Fetch failure**: all queries fail → the whole message becomes a "fetch failed" placeholder + exit code 1 (visible in the group + automation failure mark, dual channel)
- **R4 Size truncation**: when the rendered message > max_message_kb: row-set sections are truncated first (keep the first M rows + annotation), number sections preserved as much as possible; if still over, row-set sections degrade to a truncation annotation; ultimate row-level trimming as the last resort (**structural tail protection**: summary rows / the "file generated" row / footnotes are never trimmed — only row-set sections are trimmed). **Only text/rich text shapes** — for card shapes the size is controlled by `preview_rows` (over-limit data is truncated at the display layer), not the KB guardrail. **Truncation does not change section semantics** — a failed section is still `[Fetch Failed]`, an empty-data section is still "No data this period"
- **Data completeness annotation**: when the query row count hits the SQL LIMIT (both run/export paths), the message body appends "⚠ Data completeness hint: section 'X' row count hit the SQL cap N (this period's detail/summary uses the first-N-rows metric definition)" and records run_result `limit_note` — the old convention of the hit determination only landing in stderr is deprecated (users cannot see it); it does not block the push and the exit code is unchanged
- **R5 Push retry and degradation**: network-class failures (including **HTTP 429/500/502/503/504** — rate limiting / gateway jitter / upstream overload are transient failures) retry 3 times with exponential backoff (2/4/8s); deterministic failures (any other HTTP non-2xx, non-zero business code, CLI not found, unparseable response) are **not retried**. Degradation happens **within the channel**: when the card shape cannot be sent → the same mechanism degrades to a plain-text summary + WARNING (delivery first); primary mechanism failure → switch to backup mechanisms for the same target in order (a cross-channel backup requires both mechanisms to share the same `group`, e.g. "if Feishu fails, send via WeCom" — cross-channel mechanisms without a group are a broadcast double-send; backup mechanisms are configured only on explicit user request); all failed → exit code 3

## Report Scenario (kind=report, LLM slot filling)

`content.report`: `{outline, template}` — an outline (section_id bound to data sections) + a layout template (built-in or inline HTML). RUN two stages: `--stage data` (engine fetches data → data.json) → the Agent writes analysis text section by section per the outline → analysis_slots.json (**the LLM only produces text**: data, metric definitions, outline, and layout all come from the spec) → `--stage render` (slot keys validated against the locked outline, missing/extra → exit code 2; the entry point additionally validates that the spec `queries` label set matches the data.json sections, mismatch → exit code 2 — for dual-spec dual-shape, the two specs' queries must be completely identical, label drift silently drops sections) → render → deliver).

**outline entry structure** (one object per section, the script strongly validates section_id/title):

| Field | Type | Required | Description |
|---|---|---|---|
| `section_id` | string | Yes | Section identifier (slot key; analysis_slots.json aligns on it) |
| `title` | string | Yes | Section title (rendered into the report) |
| `points` | array | No | Analysis point hints for this section (at RUN time the LLM interprets around these directions) |
| `data_labels` | array | No | The list of data-section labels bound to this section (at render time the corresponding data table's first 5 rows are attached under the section). **Referencing a non-existent label → static validation exit code 2**; section_id is globally unique (duplicate → exit code 2) — typos are caught during BUILD, not waiting for a silently missing table at render time |

**Report template id vocabulary**: `text` (text report, default) / `card` (report card) / `daily` / `weekly` (monthly = alias of weekly) or an inline HTML template starting with `<` (a body fragment or a complete document both work); **must be a string** — non-string (dict/int) is rejected by static validation (exit code 2). An invalid id string → exit code 2.

**Report card template (`card`)**: the message body = a Feishu card 2.0 direct send into the group, **no attachment** — value queries render a KPI row (each column as **label**: value), rows+`chart` queries render a VChart chart component (long table), rows queries without `chart` render a table component (`preview_rows` display-layer truncation + X rows total), and the slot analysis text is rendered section by section as markdown paragraphs in outline order. Data sections render in the declared order of queries, failed sections marked `[Fetch Failed]`. Card delivery requires **at least one im_cli or feishu webhook mechanism** (static validation intercepts — cards are not implemented for other channels); when the card cannot be sent, the delivery layer degrades to a full text report for delivery (R5 delivery first). Keep the layout simple (no KPI card grid / risk-section color scheme and the like — layout customization belongs to the inline HTML template domain). Naturally composes with dual-spec dual-shape (card + HTML delivered separately on two channels). In dry-run (`--stage render` without `--push`), what stdout prints is the degraded text preview; the card structure itself is recorded in the `card` field of `run_result.json` in the same directory — check that file to verify the card structure during BUILD.

**Analysis-text number observation**: `--stage render` loosely compares the numbers in the slot text against the value set of data.json (thousands separators / percentages / rounding / wan-notation forms all count as hits; value pool = row-set numbers + summary aggregate values); a miss → stderr WARN + run_result `unmatched_numbers` — the observation surface for LLM transcription hallucinations (does not block: legitimately derived numbers such as period-over-period deltas are also not in the original value set). **Both text and HTML reports are compared** (the analysis numbers in the HTML attachment are what the user actually reads). A query section's SQL hitting the LIMIT (recorded in the data.json section's `limit_hit`) → a forewarning line / a "⚠ Data completeness hint" appended at the end of the report message. A failed section's slot text lacking the failure placeholder → a "⚠ Data anomaly hint" is automatically appended at the end of the message (user-visible, does not die). Chinese numerals / scientific notation are not in the observation surface (the writing standard requires thousands-separated Arabic numerals).

**The real use of `content.message` in report tasks**: `preview_rows` controls the display-layer truncation of HTML data tables and card detail tables; `max_message_kb` controls the message truncation of the text report (`report.template = "text"`) shape and of its role as the card's degraded text; `message.template` is **not consumed** in report tasks (the message layout is decided by `report.template` — do not write this field in examples). **HTML templates (daily/weekly/monthly/inline HTML) always produce an attachment** (regardless of whether `content.file` exists; pure text / card reports produce no HTML attachment): the naming fallback chain = `content.file.name_template` → `delivery.file_name` (legacy compatibility read) → `{task_name}_{date}.html`. HTML report attachments always produced → **static validation requires at least one file_ok mechanism** (the same gate as file tasks); the card template produces no attachment and is not subject to the file_ok gate (but subject to the card mechanism gate, see above).

**data.json size guardrail**: on disk, rows are truncated to 200 per section (`total_rows`/`rows_truncated_to` recorded per section, summary fully preserved; sections whose SQL hits the LIMIT also record `limit_hit` — the analysis text must state the "first-N-rows metric definition") — the RUN phase execution Agent must read data.json in full to write the analysis; a large row set would overflow the context or allow only a partial read; a rows query with LIMIT > 5000 gets a static WARN (the root fix is to write aggregations — AI analysis relies on aggregate results, not piles of detail rows). **Nature of the numbers**: 200 rows and 5000 are heuristic guardrails (engineering-reasoned values, not measured — the intents are respectively preventing RUN Agent context overflow and steering toward aggregation-style writing); 200 rows is hard script behavior (truncation happens, the annotation is transparent), 5000 only WARNs without blocking; another related number, "no take above 30k rows" (the SKILL applicability boundary), is a measured reference line of the demo environment's cluster synchronous cap, differs per customer environment, and is a routing recommendation, not a script gate.

**First-push convention**: a report task's BUILD full-flow test run (without `--stage`) only produces a "real data + placeholder analysis text" preview, no push; the first real push must go through the two stages — a full flow + `--push` is rejected by the script, preventing placeholder text from being pushed into a real group. Report layout templates are in report-templates.md.

## Exit Codes

| Code | Semantics |
|---|---|
| 0 | Normal (including empty-data skip sections, all sections skip with no push) |
| 1 | Fetch failure (see run_result when the placeholder was pushed or the push itself also failed; a data task BUILD test run failing entirely also exits 1 — Step 5 user confirmation is the gate, does not block registration). Note: the ae-cli executable not existing (a RUN phase environment-level fault) also exits 1 — at that point no artifact has been generated and run_result.json does not exist; the technical raw text is in the stderr `[FATAL]` line, distinguished from a fetch failure) |
| 2 | spec missing / field missing / placeholder reference validation failure / report slot validation failure / report first-push wrong posture / invalid template id / placeholder guard triggered; a BUILD full-flow test run (report task) with all queries failing (blocking registration) also uses 2 |
| 3 | Push failure (an undelivered delivery target remains) |

*Linkage with R1/R3: a fetch failure always exits 1 (even if the placeholder push succeeded) — so the failure is observable on the automation side, and the placeholder makes it observable on the group side. The placeholder copy contains only plain language and action guidance ("see the task execution log (run_result.json) for details; the next cycle retries automatically; if it recurs, contact the task owner"); the technical error raw text only lands in run_result `error_detail` and stderr, never entering the customer group.

### Backfill (missed run / failure recovery)

`python3 push_deliver.py <spec> --push --window-date YYYY-MM-DD` — recomputes "the last complete period" from the anchor date's 00:00 perspective (backfilling yesterday's daily report is sent today). daily/hourly are always available (hourly = 23:00~24:00 of the day before the anchor date — backfilling the last period of last night is sent today, the same mental model as daily; other hour slots cannot anchor at day granularity, the message title will truthfully show the hour window); weekly/monthly/rolling are back-computed by the same rule from the anchor date. `--window-date` and `--stage render` cannot be combined (render reads the window from data.json — a report task backfill runs the full two stages from `--stage data`).

## Example

See `scripts/push_spec.example.json` (a minimal example of a summary + detail-rows file task — **the project ID / event names / group IDs in it are measured values of the demo environment; replace them with your environment's actual values when copying to start**, disclaimer details at the head of the "spec Variant Examples" section in automation-recipes.md); for the complete variants of the five shapes (including a custom card template), see "spec Variant Examples" in automation-recipes.md.
