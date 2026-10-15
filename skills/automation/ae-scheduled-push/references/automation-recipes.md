# automation Path: SQL Templates, Analysis-Board Data Source, Push Formats, message Templates, Output Templates

## 1. SQL Templates (D0~D7, self-contained rules on the push side; the writing style is an isomorphic reference to the sibling skill metric-alert's sql-templates.md — this package is independently usable without it)

**Core rules** (MUST follow): ① Filter event tables by `$part_date` first (pure user tables are exempt; **with a UNION of multiple branches, every branch must carry it** — the platform only checks whether the whole SQL contains `$part_date`; a branch missing it = full-table scan and silently wrong numbers; the script intercepts per branch with exit 2) ② Multi-timezone: expand both sides by 1 day + a shifted_time subquery ③ `SELECT *` forbidden ④ LIMIT is mandatory (the LIMIT of export / file-section queries must be ≥ the BUILD-phase row-count assessment cap — when actual rows exceed the LIMIT, export is silently truncated; the script emits a run/export dual-path WARN when the returned row count hits the LIMIT) ⑤ `$part_date` compares only with strings (for boundary expansion, convert to a string via `date_format(date(...) ± INTERVAL '1' DAY, '%Y-%m-%d')`) ⑥ **Window-level unconditional COUNT (whole-window count, no CASE WHEN/GROUP BY condition) wraps `NULLIF(count(...), 0)`** (a no-data day returns 1 row of all NULL → uniformly displayed as `-`, same symbol as a SUM null; see D1 — copying D0/D2/D4/D6 applies the same rule; when omitted, the script emits a WARN reminder). **Column aliases are human-readable with units**: `AS "Total Payment Amount"` rather than `AS "metric_value"` — column names go straight into the user's message headers / row sets; a readable alias needs no translation, and carrying the unit (`AS "Pct Change %"`) avoids ambiguity; when the template's `{{aggregate_expr}}` placeholder is replaced, give a readable column name likewise. **Conditional counts are NOT wrapped**: for `count(CASE WHEN ...)` / `count(DISTINCT CASE WHEN ...)` in a window with data, 0 is a true value (e.g. "refund count 0"); wrapping NULLIF would display a true 0 as `-` (no data) — conditional counts keep a bare count.

**Time placeholders** (matched per `content.window_freq`; mixing is an error): `{{date}}` (window attribution day) / `{{window_start}}` / `{{window_end}}` (timestamp-column scenarios, any window — rendered as a string with hours/minutes/seconds, comparable only with timestamp columns; when used for `$part_date` boundary expansion, first take the date part via `substr('{{window_start}}', 1, 10)` before comparing) / `{{week_start}}` / `{{week_end}}` (weekly only) / `{{month_start}}` / `{{month_end}}` (monthly only) — **both weekly and monthly may instead use `{{window_start}}`/`{{window_end}}`** (timestamp-column scenarios; the two guards are symmetric: a weekly/monthly window missing the corresponding placeholder with no window alternative → die 2; a non-weekly/non-monthly window containing week/month placeholders → die 2). Business placeholders (event name / properties / filters) are all replaced during the BUILD phase; a leftover at run time is an immediate error.

### Template D0: Hour Window (hourly)

Single-timezone (natural hour window):
```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" >= date_format(date(substr('{{window_start}}', 1, 10)), '%Y-%m-%d')
  AND "$part_date" <= date_format(date(substr('{{window_end}}', 1, 10)), '%Y-%m-%d')
  AND date_format("#event_time", '%Y-%m-%d %H:%M:%S') >= '{{window_start}}'
  AND date_format("#event_time", '%Y-%m-%d %H:%M:%S') < '{{window_end}}'
  {{filters}}
LIMIT 1
```

Multi-timezone (definition = settlement timezone, $part_date expanded 1 day on both sides + shifted_time subquery conversion):
```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM (
  SELECT
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)),
       date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"),
       "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" >= date_format(date(substr('{{window_start}}', 1, 10)) - INTERVAL '1' DAY, '%Y-%m-%d')
    AND "$part_date" <= date_format(date(substr('{{window_end}}', 1, 10)) + INTERVAL '1' DAY, '%Y-%m-%d')
    {{filters}}
) t
WHERE date_format(shifted_time, '%Y-%m-%d %H:%M:%S') >= '{{window_start}}'
  AND date_format(shifted_time, '%Y-%m-%d %H:%M:%S') < '{{window_end}}'
LIMIT 1
```

(Window = the previous full hour; `{{window_start}}`/`{{window_end}}` are rendered by the script per the window. **Keep the `$part_date` predicate** (core rule ①; the multi-timezone version expands $part_date by 1 day on both sides, the single-timezone version = the window's own day boundary without expansion); the precise window is filtered by the timestamp column. **Use `#event_time` for the timestamp column** — the `$ts` column does not exist in event tables (measured); `{{window_*}}` renders as a string with hours/minutes/seconds; for boundary expansion take the date part with `substr('{{window_start}}', 1, 10)` then `date()` (`date()` cannot take a string with hours/minutes/seconds — measured). Multi-timezone `{{settle_tz}}` = the spec.timezone.offset number, `{{tz_column}}` = the project info's `time_zone_offset_column`, replaced at BUILD time.)

> The multi-timezone generic skeleton (shifted_time subquery conversion + outer precise filtering) is an isomorphic reference to the sibling skill; the complete multi-timezone writing of each template in this skill is already inlined (D0/D1/D4/D6) — independently usable.

### Template D1: Single-Value Metric (daily-report value segment, most used)

Single-timezone (natural-day window):
```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" = '{{date}}'
  {{filters}}
LIMIT 1
```

(Multiple metrics can be one query with multiple columns: `{{aggregate_expr}}` = comma-separated columns. **Window-level unconditional COUNT wraps `NULLIF(count(...), 0)`** — on a no-data day, empty aggregation returns 1 row of `SUM=NULL / COUNT=0`; unwrapped, the message renders `Total Payment Amount: - / Paying Users: 0`, two symbols for one state (one state, two faces); a whole-window count of 0 occurs only when the window has no records, and wrapped with NULL it becomes null like SUM, uniformly displayed as `-` — the rendering layer's NULL→`-` behavior already exists. A conditional count's (count(CASE WHEN...)) 0 is a true value — do not wrap. Example:
```sql
SELECT sum("pay_amount") AS "Total Payment Amount",
       NULLIF(count(DISTINCT "#account_id"), 0) AS "Paying Users"
FROM ... WHERE ...
LIMIT 1
```
)

Multi-timezone (complete writing, self-contained in this skill — `{{settle_tz}}` = spec.timezone.offset, `{{tz_column}}` = the project info's `time_zone_offset_column`, replaced at BUILD time):
```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM (
  SELECT
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)),
       date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"),
       "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" >= date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d')
    AND "$part_date" <= date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
    {{filters}}
) t
WHERE date(shifted_time) = date('{{date}}')
LIMIT 1
```
(The skeleton is isomorphic to the D0/D4 multi-timezone versions — subquery conversion + $part_date expanded 1 day on both sides + outer precise window. A complete runnable example of the same shape is also in scripts/push_spec.example.json.)

**Derived metrics (period-over-period, etc.) are pre-computed inside the SQL into a final single-column value**; the message layer renders only the single value:
```sql
SELECT ROUND((a.v - b.v) * 100.0 / NULLIF(b.v, 0), 1) AS "Pct Change %"   -- column name carries the unit; the message renders "Pct Change %: 12.5", self-readable by the user
FROM (SELECT ...) a, (SELECT ...) b   -- a = current period, b = previous period; each queried first, then computed
LIMIT 1
```

### Template D2: TopN (rows mode)

```sql
SELECT "{{group_dimension}}" AS "group_key", {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" = '{{date}}'
  {{filters}}
GROUP BY "{{group_dimension}}"
ORDER BY metric_value DESC
LIMIT {{top_n}}
```

### Template D3: List (rows mode, ID two-column rule)

```sql
SELECT "#user_id", "#account_id", {{extra_columns}}
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" BETWEEN '{{date}}' AND '{{date}}'  -- per the metric definition this can be a lookback of N days
  {{filters}}
GROUP BY "#user_id", "#account_id"
LIMIT {{limit_n}}
```

(Weekly list: replace `{{date}}` with `{{week_start}}`/`{{week_end}}` BETWEEN — the week guard requires a week window to use week placeholders or the window alternative (timestamp-column scenarios); a bare `{{date}}` is intercepted with die 2.)

### Template D4: Weekly Report (natural_week window, at least one of `{{week_start}}`/`{{week_end}}` or `{{window_start}}`/`{{window_end}}`)

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" BETWEEN '{{week_start}}' AND '{{week_end}}'
  {{filters}}
LIMIT 1
```
Multi-timezone (definition = settlement timezone — a week window likewise needs conversion; applying the single-timezone version directly yields a wrong window / missed rows):
```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM (
  SELECT
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)),
       date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"),
       "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" BETWEEN date_format(date('{{week_start}}') - INTERVAL '1' DAY, '%Y-%m-%d')
                        AND date_format(date('{{week_end}}') + INTERVAL '1' DAY, '%Y-%m-%d')
    {{filters}}
) t
WHERE date(shifted_time) BETWEEN date('{{week_start}}') AND date('{{week_end}}')
LIMIT 1
```
(Skeleton same as the D0 multi-timezone version: subquery conversion + $part_date expanded 1 day on both sides + outer precise window.)

### Template D5: Multi-Project Merge (cross-project UNION ALL)

**Few metrics, many projects** (one row per project, no UNION needed): one query per metric, each carrying `queries[].project_id` pointing to its project.

**Cross-project list / TopN merge** (combined into one table):
```sql
SELECT 'Project A' AS "project", "#user_id", "#account_id", {{extra_columns}}
FROM ta.v_event_1
WHERE "$part_event" = '{{event_name}}' AND "$part_date" = '{{date}}' {{filters}}
UNION ALL
SELECT 'Project B' AS "project", "#user_id", "#account_id", {{extra_columns}}
FROM ta.v_event_2
WHERE "$part_event" = '{{event_name}}' AND "$part_date" = '{{date}}' {{filters}}
LIMIT {{limit_n}}
```
(Aggregation definitions must be consistent across branches; `ta.v_event_<project_id>` / `ta.v_user_<project_id>` query cross-project tables directly. The csv file section supports only a single SQL — multi-project csv splits into multiple tasks or drops the file section.)

### Template D6: Monthly Report (monthly window, `{{month_start}}`/`{{month_end}}`)

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" BETWEEN '{{month_start}}' AND '{{month_end}}'
  {{filters}}
LIMIT 1
```

Multi-timezone (definition = settlement timezone — a month window likewise needs conversion): shifted_time subquery + `$part_date` expanded 1 day on both sides (`date_format(date('{{month_start}}') - INTERVAL '1' DAY, '%Y-%m-%d')` / `date_format(date('{{month_end}}') + INTERVAL '1' DAY, '%Y-%m-%d')`) + outer `date(shifted_time) BETWEEN date('{{month_start}}') AND date('{{month_end}}')` — the complete skeleton is the same as the D4 multi-timezone version, with the placeholders swapped to the month pair.

**Guard conservatism note (week/month symmetric)**: the window guard requires "the month pair (`{{month_start}}`+`{{month_end}}`) or the window pair to appear as a pair" — **single-boundary writing (e.g. only `{{month_end}}` for a month-end snapshot) is intercepted with die 2**. This is deliberately conservative: silently wrong numbers from a missing boundary (no upper bound = full scan) cost more than the mistaken interception of rare single-boundary needs. Month-end single-day snapshot needs should be rewritten as: `{{window_start}}`/`{{window_end}}` (timestamp-column scenario, with hours/minutes/seconds precise to the day boundary) or registered as a day window.

### Template D7: Rolling Window (`window_freq: rolling:N`, the last N complete days up to yesterday)

Scenarios like "push the active-user count of the last 7 days daily" — the window rolls with the schedule; the statistical window/title automatically shows the full range `2026-09-30~2026-10-06` (the user does not guess the range from the task name).

```sql
SELECT {{date_expr}} AS "date", {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" BETWEEN substr('{{window_start}}', 1, 10)
                      AND date_format(date(substr('{{window_end}}', 1, 10)) - INTERVAL '1' DAY, '%Y-%m-%d')
  {{filters}}
GROUP BY {{date_expr}}
LIMIT {{top_n}}
```

Key points: ① `{{window_start}}`/`{{window_end}}` **must be paired** (rolling static guard — misusing `{{date}}` counts only the window-start day, N days silently become 1 day); `{{window_end}}` is an exclusive bound (next day 00:00 with hours/minutes/seconds); the `$part_date` comparison takes the date part with `substr` then subtracts 1 day (same as the D0/D4 timestamp-column writing) ② `{{date}}` under rolling = the window-start day (N days ago) — informational only, never a filter condition ③ N = 2~90 (longer spans use monthly aggregation) ④ schedule frequency and window are decoupled — a daily schedule rolls daily; a weekly schedule pushes "the last N days from last Thursday's perspective" (usually paired with daily) ⑤ multi-timezone: shifted_time subquery skeleton same as D1/D4; the outer precise filter is written `date(shifted_time) BETWEEN date(substr('{{window_start}}',1,10)) AND date(date(substr('{{window_end}}',1,10)) - INTERVAL '1' DAY)` (the `$part_date` side, same as D0, takes the date part with `substr` then converts to a string with `date_format` for comparison).

## 2. Analysis-Board Data Source (queries[].source = dashboard_report)

Multi-project multi-metric merging / report data sources can read analysis-board reports instead of raw SQL.

**Recommended stance: user-auditable first** — most users can read analysis-board report configs but not SQL, so put the metric-definition asset on the side the user can self-inspect and self-adjust: with a simple definition (criteria in SKILL.md 1.2, roughly ≤5 metrics / single event family / single-layer aggregation), direct SQL is fine; many metrics, spanning multiple event properties, compound definitions (grouping/retention/LTV/multi-window trends), or the user wanting to adjust the definition later → analysis-board source (or guide them to build a board). Explicit cases where SQL is kept: ① cross-window computation (period-over-period etc., which board reports cannot produce from a single window) ② the data source involves only aggregate-granularity reports that would be stripped empty (see below) ③ the user explicitly does not want to create/modify platform assets.

```bash
# run pipeline (synchronous and bounded — results are hard-capped at 100 rows/report, independent of --preview-rows)
ae-cli analysis dashboard-report-data run -p <project_id> \
  --dashboard-id <id> --report-ids '[<id>,<id>]' --format json

# export pipeline (asynchronous full gzip JSONL — when data beyond 100 rows/report is needed)
ae-cli analysis dashboard-report-data export -p <project_id> \
  --dashboard-id <id> --report-ids '[<id>,<id>]' --wait --wait-timeout-seconds 300 --output <path> --force
```

- `--report-ids` takes a **JSON array** (`'[13299523,13299524]'`; a comma string is rejected by the CLI as Invalid JSON)
- run return envelope: `data.report_data_list[]` nested per report, each element containing `report_id/report_name/data(rows)/return_code` — **each query is advised to specify report_ids explicitly** (a single report failure errors at the return_code segment level, not silently; has_more is judged per report)
- **the run pipeline hard-caps results at 100 rows/report** (measured: passing --preview-rows 1000 still returns only 100 rows + has_more) — for needs beyond 100 rows/report, `queries[].fetch=export`
- Total rows (Overview/total marker rows) are stripped automatically by the script and never mixed into the data — **pure aggregate-granularity reports (producing only total rows) get stripped empty and cannot serve as a data source**; such needs go through SQL or switch to detail-granularity reports
- **Probe the value shape before configuring summary on a board source**: report values often carry formatting ("12.5%" and the like) — sum treats unparseable values as a segment-level failure (fail-loud). During the BUILD phase, run the board source's summary-referenced column once to see actual values; if the formatted values (percent/currency signs) cannot be changed on the board side, switch to a SQL source or drop the summary
- Synchronous run pipeline: SQL reports ignore filters/time override and list the ignored items in `data.warnings` (CLI help statement; no actual sample obtained — watch that field when reading; if present, relay it faithfully)
- Multi-project: one query per project's board (`queries[].project_id` pointing to the board's project); the script executes each in turn and merges
- **the file section's detail_query does not support the dashboard_report source** (file export goes through the SQL engine)
- **when a board report's definition/window does not match the need** (e.g. a fixed historical window, mismatched rolling semantics): lay out the options for the user (the comparison dimensions include **definition-maintenance ownership** — whether future definition changes are made by the user on the board, or by re-running BUILD for the task); **default recommendation is the board side** —
  - A. Direct SQL: the definition is locked into the spec; changing it requires re-running BUILD (fits: cross-window computation / aggregate-granularity report stripped empty / the user won't touch platform assets)
  - B. Modify the report (a write operation; the change points must be listed for confirmation): e.g. change a fixed window to rolling "yesterday" — the platform's relative-time writing `{"mode": "previous", "unit": "day", "value": 1}` (reference: existing reports in the project); after the change the task's definition follows the board, and the user adjusts the definition by touching only the board
  - C. Save a "push edition" copy of the board (`ae-cli analysis dashboard-definition export` + `import`): the original board untouched, the new board's reports get new windows (measured: payment overview 2719587 → monthly-report edition 2719610, 8 reports switched to "previous natural month" landed); after changing windows on LTV/retention-type reports, run the data to confirm the semantics — never infer from config alone
  - Before modifying a report, measure the current state first (a fixed window may have no data — report honestly "without the change, a daily push would have no data")
- **Board-source definition annotation**: for board-source tasks, the **data window / metric definition follows the board report's own settings** and is a separate ledger from the spec's `window_freq`/schedule frequency — after the user changes the report window, the data definition changes accordingly, but the message title's "statistical window" does not follow. When locking a board source at BUILD time, read the report's actual window semantics (fixed/rolling); when inconsistent with the push frequency, state it honestly and annotate in template A "data definition = board report window (not the push window)"; the definition asset lives on the board side (user self-inspectable/self-adjustable), and drift is normal operations (see the lifecycle table's "board-source definition drift" entry).
- **Board-source timezone**: the data definition follows the board's own timezone settings (decoupled from spec.timezone.offset; offset only governs the message title date). For multi-timezone projects, at BUILD time **compare** the expected settlement timezone vs the board's current timezone (read: `ae-cli analysis dashboard get` → `data.effective_settings.fixed_timezone` (enabled/zone_offset/timezone_source — the authoritative read of the configured state; note board queries have a ~10-minute cache, so a read-back right after a config change may return the old value); the report query's returned `effective_zone_offset` is **unreliable** — it is affected by the executor's sandbox timezone identity and serves only as corroboration). When they differ, give the user three choices: change the board timezone (write operation) / save a copy of the board with a different timezone (`ae-cli analysis dashboard-definition export` + `import`, verified feasible — the monthly-report-edition board copy + 8 reports with new windows landed) / accept the board's current definition (annotate the message definition honestly)

## 3. automation message Templates (locked execution at RUN time)

### Standard Edition (data tasks)

```text
MODE: RUN
Skill: scheduled-push (skill id: <platform ID — fill from the current session's Skill metadata at creation time: `ae-cli agent +list-skills` per the skill's actual scope (personal edition `--scope personal` / company preset `--scope company`); the one mounted in this session is its real id — do not guess>)
Instructions: This automation session is the sole workspace.
1) Read scripts/push_deliver.py from the Skill script assets (ae-cli agent +read-skill-script --id <skill id> --path push_deliver.py --output ./push_deliver.py) and write it to this session's root as ./push_deliver.py;
2) Write the push_spec below verbatim into ./push_spec.json (no rewriting);
3) Execute: python3 ./push_deliver.py ./push_spec.json --push (push authorization was completed in the two-step BUILD-phase authorization; spec.auto_push is the BUILD-phase safeguard — either one is enough to push);
4) Verify the exit code: 0 = normal (including empty-data skip); 1 = fetch failure (placeholder already pushed); 2 = spec missing / placeholder reference validation failure; 3 = push failure; note: exit code 1 may also mean the ae-cli executable does not exist (at that point no artifact has been produced, run_result.json does not exist, and the technical text is in stderr's `[FATAL]` line — an environment-level fault). On nonzero, output stderr and the run_result.json contents (skip if the file does not exist, e.g. static validation failed before generation), then stop.
Rewriting SQL is forbidden / switching projects is forbidden / asking follow-up questions is forbidden / mocking is forbidden.

push_spec:
<The full push_spec.json locked at BUILD time, embedded verbatim>
```

### Report Edition (kind=report, two-stage)

```text
MODE: RUN
Skill: scheduled-push (skill id: <platform ID>)
Instructions: This automation session is the sole workspace. This task is an analysis report (two-stage execution).
1) Read scripts/push_deliver.py from the Skill script assets (ae-cli agent +read-skill-script --id <skill id> --path push_deliver.py --output ./push_deliver.py) and write it to this session's root as ./push_deliver.py;
2) Write the push_spec below verbatim into ./push_spec.json (no rewriting);
3) Execute: python3 ./push_deliver.py ./push_spec.json --stage data --push (produces ./data.json). Exit code 1 = all queries failed (placeholder already pushed; stop; do not execute the following steps); with partial query failures the exit code is 0, the segment in data.json carries an error field, and step 4 proceeds as normal (failed sections get placeholder text);
4) Read data.json and write the analysis text section by section, strictly following push_spec.content.report.outline, into ./analysis_slots.json in the format {"slots": {"<section_id>": "<analysis text>", ...}} — the keys must exactly match each outline section's section_id, no additions or omissions.
   Writing rules: each section uses "• " bullet short sentences (one point per line, no more than 6 points per section), each point a complete conclusion sentence; numbers must always cite actual values from data.json (thousands-separated readable format); fabricating is forbidden (at render time the script compares the slot text's numbers against the data.json value set; a miss records a WARN + run_result — transcription must be accurate); when a segment contains rows_truncated_to, honestly state "based on the first N rows" (that segment's detail rows were truncated on disk); when a segment contains limit_hit, honestly state "first-N-rows definition" (that segment's SQL hit the LIMIT; the data is not full); give directional attribution for trends/changes/anomalies — when the data cannot support a causal judgment, speculative tone is mandatory (may / possibly / suspected); never present speculation as a definitive conclusion, and describe phenomena first; no long-form prose paragraphs; for a section whose data fetch failed, write the placeholder text "[Data fetch failed: <summary>]" (the summary is a plain short sentence, e.g. "Data fetch failed; will retry automatically next period" — **copying the technical text of the data.json segment's error field is forbidden**; if omitted, a data-anomaly notice is automatically appended to the message tail).
5) Execute: python3 ./push_deliver.py ./push_spec.json --stage render --push (slot validation → rendering → delivery);
6) Verify the exit code: 0 = normal; 1 = fetch failure; 2 = spec/slot validation failure; 3 = push failure; note: exit code 1 may also mean the ae-cli executable does not exist (at that point no artifact has been produced, run_result.json does not exist, and the technical text is in stderr's `[FATAL]` line — an environment-level fault; report and stop). On nonzero, output stderr and the run_result.json contents (skip if the file does not exist). **When the exit code is 2 and the error is "slot validation failed: missing/extra", it means analysis_slots.json's keys do not match the outline — fix the slots file per the missing/extra key names in the error, then retry step 5 once** (this is the only retryable error: align key names only; do not change the analysis content or data); if the retry still fails or the code is another nonzero → stop and report faithfully.
Data, metric definitions, outline, and layout are all governed by the spec; rewriting SQL/data is forbidden; adding/removing sections is forbidden; mocking is forbidden.

push_spec:
<The full push_spec.json locked at BUILD time, embedded verbatim>
```

### Dual-spec Dual-form (one data set, two forms, delivered to two channels)

Need shape: the same data and analysis text delivered in two forms to two channels (e.g. a Feishu group receives the HTML report + a DingTalk group receives the text report — a natural need arising from channel capability differences). **One automation**, with the message embedding two push_specs sharing the fetch and the slots (number consistency is guaranteed by the shared file, no second fetch):

```text
MODE: RUN
Skill: scheduled-push (skill id: <platform ID>)
Instructions: This automation session is the sole workspace. This task is a dual-channel analysis report: <channel A> receives <form A>, <channel B> receives <form B>. The two specs live in the same directory and share the same data.json and analysis_slots.json.
1) Read scripts/push_deliver.py from the Skill script assets (ae-cli agent +read-skill-script --id <skill id> --path push_deliver.py --output ./push_deliver.py) and write it to this session's root as ./push_deliver.py;
2) Write the two push_specs below verbatim into ./push_spec_a.json and ./push_spec_b.json respectively (no rewriting);
3) Execute: python3 ./push_deliver.py ./push_spec_a.json --stage data --push (produces ./data.json). Exit code 1 = all queries failed (placeholder already pushed to channel A; still continue the following steps so channel B also receives a failure-annotated report); with partial query failures the exit code is 0; proceed to step 4 as normal;
4) Read data.json and write the analysis text section by section, strictly following the spec's content.report.outline, into ./analysis_slots.json (writing rules same as the report-edition template; the two specs' outlines are identical and share one slot file);
5) Execute: python3 ./push_deliver.py ./push_spec_a.json --stage render --push (<channel A> <form A>);
6) Execute: python3 ./push_deliver.py ./push_spec_b.json --stage render --push (<channel B> <form B>, reusing the same directory's data.json and analysis_slots.json);
7) Verify the exit code at each step (semantics same as the report edition). On any nonzero, output that step's stderr and run_result.json contents, then stop.
Data, metric definitions, outline, and layout are all governed by the spec; rewriting SQL/data is forbidden; switching projects is forbidden; adding/removing sections is forbidden; mocking is forbidden.

push_spec_a:
<The full push_spec of form A (e.g. Feishu HTML report: template daily/weekly/monthly or inlined HTML)>

push_spec_b:
<The full push_spec of form B (e.g. DingTalk text report: template text; when the channel cannot take files, use the text template without a file section — the form degradation is explained to the user honestly)>
```

Key points: the two specs' `queries` and `report.outline` are **completely identical** (same section_ids are what allows sharing the slot file); only `report.template`, `file`, and `delivery` differ; `--stage data` runs only the first spec (the second's render reuses data.json — no second fetch); the two specs must land in the same directory (template step 2 writes both to the session root `./`) — the script looks for data.json / analysis_slots.json in the directory of the spec file being rendered; if the second lands elsewhere, it exits with code 2 for missing data files; form degradation of the same data across channels (HTML→text) is a channel capability difference — explain honestly to the user which form each channel receives.

### Creation Command Key Points

**Execution Agent (before create-automation)**: the automation must be bound to a dedicated execution Agent with this skill mounted — an omitted `--agent-id` implicitly binds the current session's Agent (binding quality uncontrollable). Flow: ① `ae-cli agent +list-agents`, then `+get-agent --id <id>` for each, checking whether `skillIds` contains this skill's id; ② found → confirm with the user "found the execution Agent '<name>' already bound to this skill — reuse it?"; ③ not found → write the prompt to a temp file first, then pipe it in via stdin to create (`printf '%s\n' '<execution Agent system prompt>' > /tmp/sp_agent_prompt.txt && ae-cli agent +create-agent --name "scheduled-push execution assistant" --description "Execution Agent for the scheduled-push skill; executes the push flow per the message instructions when scheduled tasks trigger" --instructions @- --skill-ids '[<this skill id>]' --scope personal < /tmp/sp_agent_prompt.txt`; scope follows the skill's actual ownership — a personal skill creates personal, a company preset creates company for team-wide reuse) — **`--instructions @-` must not be omitted**; omitting it creates a hollow Agent with systemPrompt=null (measured consequence: an execution Agent without a prompt improvises and lets value-pool WARNs through); ④ after creation, read back with `+get-agent` to confirm systemPrompt is non-empty; ⑤ `+create-automation` explicitly carries `--agent-id <execution Agent id>`. Re-binding an existing task requires delete-and-recreate (update-automation does not support changing the agent).

**Success judgment and duplicate prevention**: whether `+create-automation` succeeded is judged solely by the return envelope's `ok` field — **do not guess the task entity's key name** (the envelope's task key is `data.automation`, different from `+list-automations`'s `data.items`; measured: a hand-written parser guessing `data.item` got all nulls → wrongly judged as failure and retried → duplicate same-name tasks, and the platform has no delete command, only disable). Before creating, run `+list-automations` to check for a same-name task — if one exists, ask the user to choose (in-place update of `--message`, or rename and create new); do not register twice; after creation, read back to confirm only one same-name task exists before delivering.

Execution Agent system prompt (use verbatim at creation):

```text
You are the execution Agent for the scheduled-push skill. When a scheduled task triggers, execute the message steps: mechanical operations — running the script, reading/writing files, checking exit codes — strictly per the message; no follow-up questions, no parameter changes, no mocking, no invented steps; text generation explicitly required by the message (e.g. writing analysis text per the outline for report tasks) proceeds as normal — follow the writing rules inside the message, always cite actual values from the data file, never fabricate. When the script exits nonzero, output stderr and the run_result.json contents and stop.
```

`--schedule-kind` hourly/daily/weekly/monthly (weekly registration suggests Monday~Saturday — "the previous complete natural week" when triggered on Sunday is the week before last (the current week is not yet over), which matches the window definition but is counterintuitive; Sunday registration must explicitly state the actual statistical window to the user; hourly uses `--minute`, suggesting 05/10, multiples of 5 — buffer for on-the-hour data latency; weekly `--weekday` is **0-6 (0=Sunday)**; monthly `--day-of-month` 1-28); `--time` schedule-time registration rule: **non-multi-timezone project = register the user's time as-is** (never mention timezones; exception: only explain the conversion when the user brings it up); **multi-timezone project = after confirming the user's stated timezone, convert to the server timezone for registration**. Read the server timezone from `ae-cli agent +list-automations → serverUtcOffset` (the platform reads the offset directly, in the form "UTC+08:00"; **the sandbox's `date` is a container clock — forbidden as a basis**). Sessions start fresh by default (do not pass `--reuse-conversation`); each execution is isolated and non-polluting. **The webhook URL appears in plaintext in automation trigger records** — remind the user before creation to confirm the URL may be exposed. **Multi-time pushes**: the analysis-board push path's send_time supports comma-separated multiple values (e.g. "09:00,18:00"); the automation side's `--time` is single-valued — for multiple times, create multiple automations.

## 4. Output Templates (user-visible; fixed format, rewriting forbidden)

### Template A — Parameters Pending Confirmation

```text
## Parameters Pending Confirmation

| Parameter | Value | Source |
|------|----|------|
| Task name | {task_name} | user/suggested |
| Project | {project_name} (id={project_id}) | verified |
| Scenario / form | {scenario: periodic data / list details / analysis report} / {plain-language description of what the push looks like (a text message / a card with chart+table / a message + full table file / an HTML report ...)} | user choice (Step 2 form confirmation — plain language, no form jargon) |
| Window frequency | {plain language, e.g. "daily, pushing all of yesterday" / "every Monday, pushing last week" / "daily, pushing the last 7 days"} (consistent with the schedule) | user choice |
| Push content | {natural-language summary of metrics/fields / summary of the report section outline} | user specified |
| Schedule | {send time, e.g. "daily 09:00" / "Monday 09:30"} | user choice |
| Delivery | {target (plain-language group/individual name) + primary-backup relation in plain language ("prefer group A; if A fails, send to group B" / "one copy to group A and one to group B") + **sending identity in plain language**: marked "sent as <login account> personally" / "sent as the group robot"} | verified by Step 4 probing |
| No-data handling | {plain language: default "push an explanatory note even with no data"; if skip was chosen, "no push on a data-less day"} | former by default |
| Timezone | {appears only for multi-timezone projects: settlement timezone (e.g. UTC+8, user-confirmed/project default)} | user choice / project config |

If everything is correct, reply "confirm" and I will start a real-data test run (dry-run, no push).
```

(Non-multi-timezone projects **never show the timezone row** — the concept does not exist in the customer's business context, and mentioning it only adds confusion.)

**Plain-language rules**: template A is the sole basis for the user confirming the metric definition — the value column uses the user's language ("the total recharge amount for all of yesterday", not "SUM(pay_amount) over $part_date direct query"); internal codenames **never enter the parameter table**: SQL template numbers (D1~D7), `$part_date`, run/export, fetch, spec field names like `window_freq`/`on_empty`/`kind`/`mechanisms`, `im_cli`/`webhook`/ae-cli command names — when implementation differences must be distinguished, state only the plain-language difference ("computed directly by one query / data taken from an analysis-board report"); the platform object is uniformly called an "automation task" (aligned with the product page's naming) — do not mix in loose alternate names for the automation feature, and never let an English task-ID phrasing appear user-facing ("Task ID: xxx" is fine; "automation id" is not).

### Template B — Test-Run Result + Write-Operation Confirmation

```text
## Test-Run Result (real data, not pushed)

Window {window}

| Segment | Value / rows | Status |
|----|---------|------|
| {label} | {value or N rows} | ok / fetch failed / empty data / truncated |
(details in run_result.json: rendered SQL, per-segment row counts, first-5-row samples)

Message preview ({x} KB, {form name}):
{full rendered message or card structure}

(report scenarios attach: the full rendered sample)

After confirming the content is correct, reply "create automation" and I will formally create this scheduled task (if there is no dedicated execution assistant yet, one will be created along the way — it only executes per config on schedule, changes no parameters itself, and the creation step will also be confirmed with you).
```

**Message-copy principles**: a parenthetical or short clause describing summary/placeholder/anomaly behavior must **sit right next to the thing it describes** — "summary count of 0 means no data" must follow the summary row, not after "see attachment" (the reader would think it describes the attachment); read the test-run preview once yourself to eliminate copy ambiguity.

### Template C — Delivery Summary

Reuse template A's table and append: **automation task** (name + task ID), **execution Agent (name + id, dedicated to this skill)**, schedule (plain-language description of the window frequency, e.g. "daily at 9 a.m., pushing all of yesterday"), next expected execution time, jump link (activeHost read dynamically), **builder** (the user who originally configured this push — the "find the builder" item among the seven ops notes refers to this person), first-run tip (recommend manually triggering once on the platform's "Automation" page to verify), and the seven ops notes (plain language):

1. Numbers look wrong → first check the source analysis board (board-source tasks' definitions follow the board), or ask the builder to verify the definition
2. Push not received → check the task's execution status on the platform's "Automation" page; for a same-day miss, the builder can manually trigger once on the page (a rerun pushes the previous period); **if the miss is noticed days later, do not rerun directly on the page** — the re-push will fetch the "most recent period" (not the missed one; the group will see data with the wrong date); tell the Agent which period to backfill, and the Agent will anchor by date and push it
3. Want to change what is pushed → have the Agent re-run the configuration flow; the task is updated in place afterwards
4. Want to change the push time → the schedule time and the task config's window frequency must change together (the Agent handles it — remind it not to miss one)
5. Switch group / switch sending method → tell the Agent; after the change it sends a test message first, then updates
6. Don't want to receive it for now → pause on the platform's "Automation" page; resumes afterwards
7. Platform upgrade / script update → does not affect task config; no action needed

## 5. spec Variant Examples

> The project IDs / event names / group IDs in the examples are demo-environment measured values — replace them with your environment's actual values when starting from a copy.

### Form 4 Full Example: Summary + Detail File (recharge details daily report)

```json
{
  "task_name": "Daily Recharge Details",
  "project_id": 2, "project_name": "Card Game DEMO",
  "cli_version": "6.1.25",
  "content": {
    "kind": "data",
    "window_freq": "daily",
    "queries": [
      { "label": "Recharge Details", "mode": "rows", "source": "sql",
        "sql_template": "... (the sole source of a complete runnable SQL = scripts/push_spec.example.json, the official example of this same task — complete multi-timezone writing, columns with AS aliases \"User ID\", \"Recharge Amount\")",
        "fetch": "export",
        "summary": [
          {"column": "Recharge Amount", "agg": "sum", "name": "Total Payment Amount"},
          {"column": "User ID", "agg": "count_distinct", "name": "Total Paying Users"},
          {"agg": "count", "name": "Payment Count"}
        ] }
    ],
    "message": { "template": "builtin:plain", "preview_rows": 100 },
    "file": { "name_template": "recharge_details_{date}.csv", "detail_query": "Recharge Details" },
    "on_empty": "push"
  },
  "delivery": { "mechanisms": [
    { "mechanism": "im_cli", "tool": "lark-cli",
      "target": { "type": "user", "id": "ou_xxx" }, "file_ok": true }
  ] },
  "timezone": { "multi_tz": true, "offset": 8, "offset_source": "project_default", "zone_offset_column": "#zone_offset" }
}
```

(Message = "Total Payment Amount: 223,466 / Total Paying Users: 2,055 / Payment Count: 4,634 + X rows total + first 100 rows preview"; the CSV attachment is an independent file message. The summary is computed by the engine over the full detail rows — same batch of rows, naturally consistent in definition. **The sole source of a complete runnable SQL = `scripts/push_spec.example.json` (the official example of this same task — do not copy one into this file; two copies will drift)**: with multi_tz=true, $part_date expands 1 day on both sides + shifted_time converts to the settlement timezone via `8 - #zone_offset` (offset and zone_offset_column replaced per project info measured values), columns carry `AS` aliases, summary references them by alias; single-timezone projects (multi_tz=false) use `"$part_date" = '{{date}}'` directly — no conversion, no aliases. File name `{date}` = the window attribution day YYYYMMDD. **Preview column whitelist**: with many fields (>5~6 columns), the message preview carries only the key column subset confirmed with the user (template references reflect the whitelist), annotated "full fields in the attachment" — the user wanting "all fields" = all fields into the CSV, not all into the preview.)

### Form 2 Full Example: Chart Card (last 7 days, dual metrics)

```json
{
  "task_name": "Card DEMO Core Metrics Daily Report",
  "project_id": 2, "project_name": "Card Game DEMO",
  "content": {
    "kind": "data",
    "window_freq": "daily",
    "queries": [
      { "label": "last_7_days", "mode": "rows", "source": "dashboard_report",
        "dashboard_id": 2719326, "report_ids": [13299934],
        "fetch": "run" }
    ],
    "message": { "template": "builtin:card_chart" }
  },
  "delivery": { "mechanisms": [
    { "mechanism": "webhook", "webhook_kind": "feishu",
      "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx", "form_ok": true }
  ] },
  "timezone": { "multi_tz": true, "offset": 8 }
}
```

(The engine converts the report's wide table into a long table to fill the VChart `data[].values`; `seriesField` automatically splits the dual lines + legend; the card's tail appends the yesterday-value summary.)

### Custom Card Template Example (inlined writing for forms outside the menu)

```json
"message": {
  "template": {
    "kind": "card_2.0",
    "schema": "2.0",
    "header": {"title": {"tag": "plain_text", "content": "[Daily Report] {{task_name}} {{window_range}}"}},
    "body": {"direction": "vertical", "elements": [
      {"tag": "markdown", "content": "**Yesterday recharge**: count {{agg.payment_count}} / amount {{agg.total_payment_amount}}"},
      {"tag": "table",
       "columns": [{"name": "level", "display_name": "Level"}, {"name": "metric_value", "display_name": "Recharge Amount"}],
       "rows": "{{q.recharge_details.rows}}"}
    ]}
  }
}
```

(The skeleton finalized by BUILD-phase exploration is locked into the spec as-is; placeholder vocabulary in push-spec-schema.md. `kind: "card_2.0"` is the script's validation marker (mandatory); before sending, the script auto-normalizes — strips kind, fills in `schema: "2.0"` (it still sends if omitted). Write `columns[].name` per the query's actual column names (rows keys get no display mapping). For weekly/monthly windows, title with `{{window_range}}` (full range) and place a "Statistical window: {{window_range}}" row as the first body element — built-in templates carry it by default; custom templates follow suit (test delivery shares the source with the final form; the window annotation is ever-present).)

### Report (kind=report, two-stage)

Minimal report spec skeleton (`content.report` + queries with new fields):

```json
{
  "task_name": "Weekly Operations Report",
  "project_id": 2, "project_name": "Card Game DEMO",
  "cli_version": "6.1.25",
  "content": {
    "kind": "report",
    "window_freq": "weekly",
    "queries": [
      { "label": "core_metrics", "mode": "value", "source": "sql",
        "sql_template": "SELECT {{aggregate_expr}} AS \"metric_value\" FROM ta.v_event_{{project_id}} WHERE \"$part_event\" = '{{event_name}}' AND \"$part_date\" BETWEEN '{{week_start}}' AND '{{week_end}}' LIMIT 1" },
      { "label": "daily_trend", "mode": "rows", "source": "sql", "chart": "line",
        "sql_template": "SELECT \"$part_date\", SUM(\"pay_amount\") AS \"pay_amount\" FROM ta.v_event_2 WHERE \"$part_event\" = '{{event_name}}' AND \"$part_date\" BETWEEN '{{week_start}}' AND '{{week_end}}' GROUP BY \"$part_date\" ORDER BY \"$part_date\" LIMIT 7" },
      { "label": "detail_rows", "mode": "rows", "source": "sql",
        "sql_template": "SELECT \"#user_id\", \"pay_amount\" FROM ta.v_event_2 WHERE \"$part_date\" BETWEEN '{{week_start}}' AND '{{week_end}}' LIMIT 1000" }
    ],
    "report": {
      "outline": [
        { "section_id": "overview", "title": "Overview", "points": ["Core metrics period-over-period", "Overall trend"], "data_labels": ["core_metrics", "daily_trend"] },
        { "section_id": "detail", "title": "Payment Details Interpretation", "points": ["Top-user characteristics"], "data_labels": ["detail_rows"] }
      ],
      "template": "weekly"
    },
    "message": { "preview_rows": 100 },
    "file": { "name_template": "weekly_report_{date}.html" }
  },
  "delivery": { "mechanisms": [
    { "mechanism": "im_cli", "tool": "lark-cli", "target": { "type": "chat", "id": "oc_xxx" }, "file_ok": true }
  ] },
  "timezone": { "multi_tz": false }
}
```

(Report task template ids: `text` / `card` (in-group chart card) / `daily` / `weekly` / `monthly` (= the weekly layout) or inlined HTML starting with `<`; the outline entry structure is in push-spec-schema.md's "report scenario"; `file.name_template` names the HTML attachment — no detail_query needed (card/text templates produce no attachment). The `chart` field is **consumed only on mode=rows queries** (first 2 columns label+value produce the trend chart — HTML via inline SVG, card via the VChart component) — value queries take the KPI branch; configuring `chart` has no effect there.)

**Report card form example** (`template: "card"` — monthly-report-type "charts in the group" scenarios; skeleton and degradation semantics in report-templates' "report card form" section):

```json
{
  "task_name": "Payment Monthly Report", "project_id": 2, "project_name": "Card Game DEMO", "cli_version": "6.1.25",
  "content": {
    "kind": "report", "window_freq": "monthly",
    "queries": [
      { "label": "core_metrics", "mode": "value", "source": "sql",
        "sql_template": "SELECT round(sum(pay_amount)) AS \"Total Payment Amount\", NULLIF(count(DISTINCT \"#user_id\"),0) AS \"Paying Users\" FROM (…) t WHERE date(st) BETWEEN date('{{month_start}}') AND last_day_of_month(date('{{month_start}}')) LIMIT 1" },
      { "label": "daily_trend", "mode": "rows", "source": "sql", "chart": "line",
        "sql_template": "SELECT date_format(date(st),'%m-%d') AS \"date\", round(sum(pay_amount)) AS \"Payment Amount\" FROM (…) t WHERE … GROUP BY 1 ORDER BY 1 LIMIT 31" },
      { "label": "daily_detail", "mode": "rows", "source": "sql",
        "sql_template": "SELECT date_format(date(st),'%m-%d') AS \"date\", round(sum(pay_amount)) AS \"Payment Amount\", NULLIF(count(DISTINCT \"#user_id\"),0) AS \"Paying Users\" FROM (…) t WHERE … GROUP BY 1 ORDER BY 1 LIMIT 31" }
    ],
    "report": {
      "outline": [
        { "section_id": "overview", "title": "Overall Performance", "points": ["Total / users / period-over-period"], "data_labels": ["core_metrics"] },
        { "section_id": "risk", "title": "Risk Notes", "points": ["Activity-payment divergence signals"] },
        { "section_id": "advice", "title": "Recommendations", "points": ["3 actionable recommendations"] }
      ],
      "template": "card"
    },
    "message": { "preview_rows": 100 }
  },
  "delivery": { "mechanisms": [
    { "mechanism": "webhook", "webhook_url": "<Feishu group-robot URL>", "webhook_kind": "feishu", "form_ok": true }
  ]},
  "timezone": { "multi_tz": true, "offset": 8, "offset_source": "project_default", "zone_offset_column": "#zone_offset" }
}
```

(The SQL inner subquery = the D-template multi-timezone writing; the complete version is in D4/D6; card delivery requires an im_cli or feishu webhook mechanism — cards are not implemented on other channels; when a card cannot be sent, it automatically degrades to the full text report for delivery.)
