---
name: ae-scheduled-push
description: |-
  Create time-driven periodic push tasks: push at the scheduled time, no trigger conditions needed. Route from user scenarios - periodic business data, TopN/list/detail-row export, periodic analysis reports (data + LLM generated per a locked outline). BUILD phase aligns the metric definition and locks the push_spec (data pipeline x message template); RUN phase executes deterministically; five message forms (text / rich text / chart card / table card / detail rows + file, plus an HTML report) + a closed-loop exploration path for custom templates; supports multi-project merging, row-count gate, and delivery mechanism probed during BUILD phase + test delivery. Trigger words: scheduled push, daily push, weekly push, daily report, weekly report, scheduled sending. Does NOT trigger: condition-triggered alerts (use metric-alert), one-off manual sending, real-time push.
version: "1.2"
---

# Scheduled Push (scheduled-push)

**Product model**: Scheduled Push = what content + what time rule + who to send to.
**User scenario**: The user has a recurring piece of information consumption/distribution/delivery work - checking core metrics daily, sending an operations list weekly, producing an analysis report periodically - that they originally had to do manually on schedule. This skill turns it into a task that is **built once and then executes deterministically many times**: BUILD phase aligns the metric definition and locks the `push_spec`; RUN phase reads only the spec and executes on schedule, with no re-reasoning.

**Scope boundary**: This skill runs on the TE/ThinkingData analysis platform (event model `ta.v_event_*`, ae-cli, platform automation, and the sandbox IM CLI are prerequisite dependencies); time zones use UTC-offset semantics (not IANA time zone names) - DST regions have a 1-hour window shift around transition periods that requires manual adjustment, while non-DST regions are unaffected. "Deterministic execution" refers to the metric definition, computation, layout, and delivery - the analysis text of report tasks is generated per period by an LLM following a locked outline (content is not reproduced verbatim, but the metric definition is constrained by the outline).

**Core logic**: Scheduled time arrives → fetch data / take screenshots → push unconditionally

## Terminology Quick Reference

| Term | Meaning |
|---|---|
| BUILD / RUN | Build phase (align with the user and lock the configuration) / execution phase (scheduled trigger, zero interaction) |
| push_spec | The locked configuration produced by BUILD and the sole input of RUN (field definitions in push-spec-schema.md) |
| Two paths | Analysis Board push (platform analysis board subscription push, dashboard_daily_report) / automation (the scheduled-task + script-execution "Automation" module; routing diagram and user-facing shorthand both say "Automation") |
| D0~D7 | SQL template numbers for the automation path (hourly window / single value / TopN / list / weekly report / multi-project UNION / monthly report / rolling window) |
| run / export | The two data-fetch pipelines (synchronous bounded / asynchronous full); BUILD phase locks `queries[].fetch` per the user scenario |
| R1~R5 | RUN-phase design decision numbers (partial push / no data / fetch failure / size truncation / push retry and fallback), see the schema |
| Template | The message-form skeleton: a built-in template name (factory reference for the five forms) or an inline custom template finalized through BUILD-phase exploration |
| Placeholder | Data binding markers in templates (`{{q.<label>.rows}}`, `{{agg.<name>}}`, etc.; closed vocabulary, see the schema) |
| Slot | The sectioned analysis text of report tasks (analysis_slots.json, key = outline section_id) - the data-task engine fills slots, the report-task LLM fills slots; identical architecture |
| file_ok / form_ok | BUILD-phase test-delivery flags for the file / final-form capability of the delivery mechanism (file_ok participates in the file delivery gate - shared by file tasks and HTML reports; form_ok is recorded in BUILD and not consumed in RUN) |
| Window | The data statistics interval = the last complete period (yesterday / last week / the previous hour / last month) or a rolling interval (rolling:N = the last N complete days up to yesterday), authoritatively determined by content.window_freq |
| Sender identity | Whose name the message enters the group under: im_cli = user identity (the bound account holder), webhook = bot identity (the group bot) - an inherent property of the mechanism enum; it follows the mechanism and is not configured separately |

**Division of labor with the sibling skill metric-alert** (metric-alert has a corresponding note on its side):

| | metric-alert | scheduled-push (this skill) |
|---|---|---|
| Driver | Condition-driven: push only when a threshold / year-over-year / period-over-period condition is hit | Time-driven: push when the scheduled time arrives |
| Routing dimension | Whether the system can compute it | What the user wants (scenario routing) |
| Push failure | That alert is lost (manual re-push) | Push a "fetch failure" placeholder (fail-loud dual channel) |


## I. Routing (user scenario → implementation path)

Routing starts from **what the user wants**; the implementation path is the routing conclusion - confirmed with the user during BUILD and locked into `push_spec`.

### 1.1 Information Gathering (two layers; ask for whatever is missing)

**Prerequisite information** (needed for routing decisions; do not ask about anything readable from the user's request; ask for everything missing in one round, do not split into multiple rounds):

| Information | Purpose |
|---|---|
| Whether there is a trigger condition | "Only notify when the change is significant" = condition-driven → hand off to metric-alert and explicitly inform the user |
| Nature of the content | Metric data / list · detail rows · TopN / analysis report → scenario branch (1.2) |
| Frequency | Path availability decision (1.3) + data window frequency |
| Delivery target | Group / individual / email → delivery path and mechanism (1.4) |
| Projects involved | Single / multi-project affects the plan (1.2 cross-cutting) |

**In-route follow-up questions** (ask only after routing is decided; do not front-load them):
- ① Metrics line: **first check existing analysis boards in the project** (list the ones matching the requested metrics; if any exist, present them for the user to choose - the user may have forgotten they have a ready-made board); decide the data source per the 1.2 ① metric-definition complexity criteria (SQL / analysis board); a standalone report must be attached to an analysis board first - the analysis-board push path recognizes boards only, not standalone reports
- ② List / detail-rows line: row-count magnitude (decides in-message table / file / combination / file-only)
- ③ Report line: analysis outline, layout preference, data source (SQL / analysis-board report)
- Delivery: webhook URL provided, IM CLI probe result confirmed

### 1.2 Scenario Routing Tree

```
User scenario (first dimension)
① Periodic business data ("send me XX metrics on a schedule")
   First cut: metric-definition complexity (data source leaning)
   ├─ Simple definition (all criteria met) → Automation · direct SQL query
   │    Form stays as-is: a few numbers → text / rich text; multi-day / multi-group → chart card + summary
   └─ Complex definition (any criterion met) → Analysis Board first
        ├─ A suitable board exists → use it as the data source
        ├─ None → guide the user to create a board (definition = report configuration, user can self-audit and self-adjust) → same as above once built
        └─ Refuses to create → Automation · SQL (state frankly: adjusting the definition later requires reconfiguring the task)
   (Data source ≠ push path: after the board is built, still choose the path per 1.3 - inside the grid use board push; monthly-level or LLM-requiring goes through automation reading board reports)
② List / detail rows / TopN / ranking ("periodically get a batch of rows")
   ├─ ≤100 rows → Automation · table card displayed directly
   ├─ >100 rows → Automation · first 100 rows preview + full table file as attachment
   └─ Full detail rows / large list → Automation · one message (X rows total + optional summary) + full file as attachment
③ Analysis report ("periodically get a report with interpretation")
   → Automation · data (SQL or analysis-board report query) + LLM writes the analysis per a locked outline → chart card in the group / HTML / text report

Cross-cutting dimensions
- Multi-project (①③): boards can only be built per single project - few metrics and a simple definition → SQL merging cross-project tables;
  many metrics → build a board per project + automation reads each board's results, merges, and pushes
- Data source (①③ and multi-project multi-metric): SQL query vs analysis-board report data (dashboard_report) - criteria table in the recipes "Analysis Board Data Source" section
- Email: the automation path has no email capability → if email is needed, guide the user to the analysis-board push path
```

**Metric-definition complexity criteria** (soft reference, no hard gate; the Agent judges by these and can review them afterwards):

| Dimension | SQL suitable | Analysis Board suitable |
|---|---|---|
| Metric count | About ≤5 | More, or the user expects to keep adding metrics |
| Event/property span | A single event family (one event producing multiple numbers, e.g. payment amount / payer count / transaction count) | Across multiple events, many properties |
| Definition form | Single-layer aggregation such as sum / dedup | Composite definitions like grouped comparison, retention, LTV, multi-window trends |
| Maintenance expectation | Definition basically frozen | The user wants to adjust the definition themselves later |

**Analysis-board script iron rules** (recommended stance: user-auditable / user-maintainable first):
- When going with SQL, you MUST say: "No board was built this time; we push numbers directly. If you later want a board version you can adjust yourself, I can build one for you."
- When going with a board, you MUST say: "The metric definitions are all in the board's reports; you can adjust them on the board yourself later, and the push will automatically follow, no need to come to me."

**The routing rationale must be explained clearly to the user** (inherited sibling principle): "Based on your requirements, I will take [path], because [specific requirement characteristics]."

### 1.3 Frequency and Path Availability

The analysis-board push frequency grid: **Monday~Sunday (multi-select) × on-the-hour times 0~23 (multi-select, comma-separated multiple values)**.

| Frequency | Analysis-board push path | Automation path |
|---|---|---|
| Inside the grid (any combination of daily / weekly / on-the-hour hourly) | ✅ | ✅ |
| Off-the-hour times (e.g. 09:30) | ❌ | ✅ (must explicitly tell the user "this frequency can only go through automation") |
| Every N minutes / multiple times per hour | ❌ | ❌ (the finest granularity of a single automation task is hourly - multiple time points must be split into multiple automations, and this must be stated explicitly) |
| Monthly (the 1st~28th of each month) | ❌ | ✅ (monthly window = the last calendar month, `--schedule-kind monthly` + `--day-of-month` 1-28 - month-end / the 30th / 31st are not supported by automation) |
| "Last N days" rolling (push the last N days of data daily/weekly) | Managed by the board report itself | ✅ (`window_freq: rolling:N` + the corresponding schedule - SQL uses `{{window_start}}`/`{{window_end}}`, and the statistics window / title automatically shows the full interval; see the schema "Window Semantics") |

**Time zone model (two time zones, one gate; the sole standard throughout)**:

- **Scheduling time zone**: the rule registered with automation - **non-multi-time-zone project = the user's local time registered as-is** (never mention the words "time zone" throughout; exception: explain the conversion only if the user proactively brings up time zones); multi-time-zone project = confirm the time zone the user stated, convert it to the **server time zone**, and register that (read via `ae-cli agent +list-automations → serverUtcOffset` (shaped like "UTC+08:00", the offset read directly by the platform; `scheduleTimeZone` is the IANA time zone name (Asia/Shanghai, etc.) corresponding to the serverUtcOffset numeric offset - fall back to its static mapping if serverUtcOffset is unavailable); **the sandbox `date` is the container clock and MUST NEVER be used as a basis**)
- **Data settlement time zone**: exists only for multi-time-zone projects. The gate = `ae-cli project info get -p <id>` → `time_zone_enabled`:
  - **false**: behave as if the concept of "time zone" does not exist - query the data directly via `$part_date`, with the window cutting days on the server calendar (during BUILD, read the server time zone **once and lock it into `spec.timezone.server_tz`** (read it the same way as scheduleTimeZone above, converted to an hour offset); RUN uses the spec value directly and never reads at runtime - to avoid a silent fallback to the wrong window when the read fails), **never mention time zones to the user throughout** (the customer's business context has no multi-time-zone concept; bringing it up only adds confusion; internal configuration actions aligned with the board/project defaults do not count as "mentioning to the user" - the rule is not to throw time-zone decisions at the user or force the user to pick a time zone, not to avoid the words themselves; the sole exception = the day-cut confirmation in Step 0 when serverUtcOffset cannot be read - what is asked there is a technical parameter of the server calendar, which does not violate this rule)
  - **true**: ask the user for the settlement time zone; if unconfirmed, use the project default (`default_time_zone_offset`). Application diverges by source: SQL source → convert inside the SQL yourself (expand 1 day on both sides of $part_date + shifted_time); board source / board push → **compare** the desired settlement time zone vs the board's current time zone; if they differ, the user picks one of three (change the board / save a copy / accept the current definition) - details in the recipes "Analysis Board Data Source"

### 1.4 Delivery Mechanisms (automation path)

Two mechanism classes, selected by "**BUILD-phase probing + first-run test delivery**": probe the mechanisms available in the sandbox → test-deliver with the **final form (template)** → lock the validated mechanism + parameters into `spec.delivery.mechanisms` (including the `file_ok`/`form_ok` test flags).

The mechanism list executes in order, with semantics grouped by target: for the **same delivery target**, the first success takes effect (later entries for the same target = fallback - configured only per explicit user request, e.g. "if Feishu fails, send via WeCom"; **cross-channel fallback requires the primary and fallback mechanisms to share the same `mechanisms[].group`** - without a group, cross-channel = broadcast to both); **different targets are each delivered independently (broadcast)**. Fallback happens **within a channel** (card cannot be sent → fall back to plain text + WARNING in the same channel, delivery first - which channel to push is fixed during BUILD, no cross-channel jumps). If any target is ultimately not delivered → exit code 3.

| Mechanism | Identity | Capability | Evidence |
|---|---|---|
| IM CLI direct send | **User identity** (sent in the name of the bound account; the group sees the user themselves) | Direct send via the channel CLIs installed in the sandbox: Feishu lark-cli works with zero configuration (all forms tested in practice); other channel CLIs connect via command templates (text / rich text / file; see the "Command Templates" section of delivery-mechanisms) | Feishu lark-cli, all forms tested in practice |
| webhook | **Bot identity** (sent in the name of the group bot; the group sees the bot) | Group-bot URL provided by the user, HTTP POST; text reliable, cards tested per channel, file capability tested during BUILD | WeCom upload_media tested in practice |

**Sender identity = an inherent property of the mechanism enum** (identity is not configured separately; it follows the mechanism): users do perceive "in whose name the message is sent" - if they care that the message comes from themselves (e.g. a detail-rows file entering the group under the user's identity is more credible), choose im_cli; if they do not care or there is no CLI environment, choose webhook. When choosing a mechanism, identity is one of the semantic dimensions, presented alongside form capability and delivery target.

Do NOT make negative conclusions about untested channels; all validated approaches are **references and examples, not the sole standard** - forms outside the menu are explored per the "BUILD-phase form-probing methodology" in delivery-mechanisms (test-delivery sample → read the error → iterate → user acceptance → finalize and lock the template). See [`references/delivery-mechanisms.md`](references/delivery-mechanisms.md). The analysis-board push path channels (email / WeCom / DingTalk / Feishu / KIM / Slack) manage themselves in [`references/dashboard-daily-report.md`](references/dashboard-daily-report.md).


## II. Scope

**In scope**: three scenario classes (①②③) × two paths; any combination inside the frequency grid (both paths) + off-the-hour frequencies (automation) + monthly level (automation); multi-project (SQL merging / board merging); five message forms + custom templates; BUILD-RUN spec locking; lifecycle management (change the definition / change the frequency / switch delivery / pause).

**Out of scope**:
- Condition-triggered push → metric-alert (gray areas: always ask, always hand off)
- Real-time triggering / N-period debouncing / intelligent attribution (the sibling does not do these either)
- One-off non-periodic sending ("send it to me tomorrow morning" is not scheduled push)
- Large-scale data movement (extremely large row counts; the agreed reference line is 30,000+ rows - the synchronous upper bound tested in practice in the demo environment is exactly 30,000; cluster configuration varies per customer, so this is a routing reference, not a hard gate) → recommend the platform's native export
- DataOps route (paid module; this skill is a general preset skill and must be usable by all customers)


## III. Hard Rules (must not be bypassed)

1. **Missing tool = terminate immediately** - ae-cli does not exist, query/report commands are unavailable, SQL validation fails → immediately terminate with an error and report truthfully (a dry run means it was not pushed). No mocks / no fake success.
2. **RUN does not re-reason the metric definition** - BUILD may reason and cross-check; RUN executes only per the locked `push_spec`; parameters / projects / SQL / mechanisms are all taken from the spec. Report-scenario LLM boundary: in RUN the LLM only produces analysis text; data, metric definition, outline, and layout all come from the spec.
3. **Confirm before write operations** - before creating/modifying/pausing a push task, the first real push, or **modifying the user's platform assets (report/board configuration)**, you MUST echo the final configuration in full to the user (including a comparison of asset changes) and get confirmation; point out every echo deviation one by one, wait for the user's verdict, and never substitute your own.
4. **Mandatory read-back after creation** - analysis-board push path: after update, read back with get and compare field by field (read-back key names are transformed; use the mapping table in dashboard-daily-report.md); automation path: script dry run + user confirmation of sample data.
5. **Fail loud on both channels** - fetch failure pushes a placeholder message + exit code 1 (visible in the group + automation marks the failure); push-pipeline failure is exit code 3.
6. **If uncertain, say you did not find it** - for unverified platform/external facts (tool existence, channel capability, platform mechanisms), only say "I could not find it" or "not tested in practice"; do NOT declare "it does not exist / there is only one way"; once the user corrects you, update the fact chain immediately.


## IV. BUILD Workflow (automation path)

> The analysis-board push path BUILD is in [`references/dashboard-daily-report.md`](references/dashboard-daily-report.md) (CLI capability, all verified boundaries). This section is the automation path; the report scenario (③) adds Step 3R.

### Step 0 Environment self-check + routing

`ae-cli --version` (write the tested version into `spec.cli_version` - the RUN-phase script auto-compares and only warns on drift); `ae-cli team +list-projects` to verify projects; `ae-cli agent +list-automations` to read `serverUtcOffset` (the server time zone, shaped like "UTC+08:00" - during BUILD, convert it to an hour offset and **lock it into `spec.timezone.server_tz`**; do this even for non-multi-time-zone projects: RUN uses the spec value for window day-cutting and does not depend on a runtime read - if the lock is missed, RUN falls back to a runtime read, and if that read fails it falls back to +8, which silently produces the wrong window in overseas deployments. **In a new customer environment the automation list is usually empty and serverUtcOffset cannot be read - in that case do NOT silently assume +8; confirm with the user before locking** (this is the sole exception to "never mention time zones for non-multi-time-zone projects": ask only when it cannot be read and cannot be inferred from project/board configuration; what is asked is not for the user to pick a time zone but a technical parameter of the server calendar day-cut - phrase it in terms of business consequences: "Which region's calendar do you use to cut 'yesterday'? By default we use Beijing time; if you are deployed in another time zone, please let us know." Do not use a question like "Is UTC+8 correct?" that the user can only blindly answer "yes" to.). Gather prerequisite information per 1.1 → route per 1.2 → explain the routing rationale thoroughly. (The automation path must first persist the Skill script into the current session working directory: `ae-cli agent +read-skill-script --id <skill id> --path push_deliver.py --output ./push_deliver.py` - find the skill id via `ae-cli agent +list-skills` under the skill's actual scope (personal for the personal edition / company for the company preset edition).)

### Step 1 Requirement structuring (ask for anything missing; guessing is forbidden)

| Field | Required | Notes |
|---|---|---|
| `task_name` | Yes | Task name |
| `project` / `projects` | Yes | Project name/ID (for multi-project tasks list all; verify one by one in Step 2) |
| `content` | Yes | Scenario definition: metric list / TopN · list conditions / report requirements |
| `window_freq` | Yes | Data window frequency: daily / weekly / hourly / monthly (determines the statistics window; consistent with the scheduling frequency) |
| `schedule` | Yes | freq + time (used when registering the automation; does not go into push_spec; off-the-hour frequencies must be explicitly flagged automation-only) |
| `delivery` | Yes | Delivery target (group/individual); mechanism locked after Step 4 probing |
| `on_empty` | No | 0 rows pushes a "no data this period" placeholder (default push) / skip (skip the whole message only when every segment has 0 rows) |

(timezone is not asked separately in the structuring checklist - follow the 1.3 gate: never mention it for non-multi-time-zone projects; ask for the settlement time zone in Step 2 for multi-time-zone projects.)

### Step 2 Fact verification + row-count magnitude assessment + form confirmation

List projects and verify project_id (one by one for multi-project); `project info get` to probe `time_zone_enabled` (for multi-time-zone projects, ask for the settlement time zone here); `analysis sql-table list/columns` + `analysis-meta event/property list` for targeted schema probing; targeted SQL to verify events/properties exist and have data.

**Row-count magnitude assessment** (mandatory for rows-type queries): count probe → report the magnitude to the user → simultaneously decide the output form and the **data-fetch pipeline** (`queries[].fetch`, independent of the data source):
- ≤100 rows: in-message table / table card → run
- >100 rows / full detail rows: first-100-rows preview + full file combination, or file-only → file-segment detail_query → export (explicitly: large tables need not run `run` first - lock export directly during BUILD)
- Extremely large magnitude (agreed reference line 30,000+ rows - the value tested in practice in the demo environment; varies per customer; a routing reference, not a hard gate): recommend the platform's native export, do not take it on
- Report-scenario rows queries expected to exceed a thousand rows → guide the user toward an aggregation-style rewrite (AI analysis relies on aggregated results, not piles of detail rows - fixes the root cause)

**Form confirmation (must ask; do not guess)** - present the candidate form menu per the 1.2 scenario (single-day numbers → text / rich text; multi-day multi-group → chart card + summary; TopN ≤100 rows → table card; detail rows → message + attachment; **report scenario → in-group chart card / text / HTML report**). **Form vocabulary must not enter the user conversation** - describe options in plain language about "what the push looks like" (e.g. "a card message with the chart laid out directly in the group" or "an HTML file - open it to see the full report"); the test-delivery sample is the final verdict (channel × form combination capability differs per customer environment; do not hard-code a matrix - what the user's environment can send is decided by BUILD-phase probing + test delivery). **After the user chooses, lock** `message.template` (built-in name or inline template) / for the report scenario lock `report.template` (`text` / `card` in-group chart card / `daily`/`weekly`/`monthly` HTML / inline HTML); when a chart card is chosen, tell the user "the built-in chart defaults to the first column as the X axis, with each remaining numeric column becoming a line (line/bar per `queries[].chart`, defaulting to line)" - only deviate to an inline custom template, and ask about axes/line columns in detail at that point, if this does not match the user's expectation (they want to specify axis/line columns); forms outside the menu follow the "form-probing methodology" in delivery-mechanisms.md. Template A's form row source = **the user's choice**. **Key-column whitelist for detail-row previews**: when there are many fields (>5~6 columns), the message preview shows only the subset of key columns the user cares about (confirm with the user and write it into the template - **the whitelist is implemented via an inline custom template**; the built-in template's card table shows all columns / plain text shows the first 6 columns, fixed and not selectable), annotated with "full fields in the attachment" - the "all fields" semantics = all fields go into the file, not all into the preview.

**Push form catalog** (full list of rendered artifacts - produced inside our sandbox, capability can be promised; channel capability is **not in this table**, decided by BUILD-phase test delivery):

| Scenario | What the push looks like | spec lock |
|---|---|---|
| ① Single-day numbers / few metrics | One plain-text or rich text message | data task `message.template: builtin:plain/rich` |
| ① Multi-day multi-group | Chart card: VChart line/bar (`queries[].chart`, default line) + summary numbers | data task `builtin:card_chart` |
| ② TopN / leaderboard ≤100 rows | Table inside a card, displayed directly | data task `builtin:card_table` |
| ② Detail rows / list | Message summary + full table file as attachment | data task file segment (detail_query+export) |
| ③ Analysis report · charts in the group | Card: KPI row + chart + detail table + sectioned analysis text | report task `template: "card"` |
| ③ Analysis report · full report | HTML file (KPI card grid + charts + collapsible detail rows + sections) | report task `template: daily/weekly/inline` |
| ③ Analysis report · plain text | One long text (sections + data summary) | report task `template: "text"` |

**Channel test-in-practice reference** (verified facts only, not a universal matrix): Feishu lark-cli all forms (text / rich text / card / file); Feishu webhook text + card + VChart; DingTalk webhook text; WeCom webhook text + file (upload_media two-step delivery). Any channel × combination not mentioned = untested; decided by BUILD-phase probing + test delivery.

### Step 3 Draft queries + echo for confirmation

Draft per the templates in [`references/automation-recipes.md`](references/automation-recipes.md) (D1 single value / D2 TopN / D3 list / D4 weekly report / D5 multi-project UNION / D0 hourly window / D6 monthly report / D7 rolling window); when the data source is an analysis-board report, follow the "Analysis Board Data Source" section of that file (**data-source stance = user-auditable first**: prefer an existing board report as the board source - the user adjusts the definition by editing the board and the task stays untouched; when definition/window do not match, present A/B options to the user with the board side as the default recommendation; do not decide for the user). Echo the SQL + a plain-language explanation of the metric definition and wait for user confirmation. SQL conventions: LIMIT is mandatory; event tables must have a `$part_date` predicate; `SELECT *` is forbidden; a trailing semicolon is forbidden; unconditional COUNT at window level wraps `NULLIF(count(...), 0)` (no-data days and SUM nulls both display `-` uniformly); the 0 of conditional counts (count(CASE WHEN...)) is a true value and is not wrapped.

When summary numbers inside the message are needed (detail-rows + summary form): the `summary` aggregation declaration attaches to the detail query (columns + aggregation method + names), and **the engine computes over the full rows of the detail result - the same batch of rows is inherently consistent in definition**; do not write a separate summary SQL.

### Step 3R Report-scenario sub-steps (outline + layout locking)

- **Metric definition**: queries locked (`source` can be `sql` / `dashboard_report`)
- **Analysis outline**: agree with the user on the report sections (e.g. Overview / Trends / Top changes / Risk signals), each section bound to a data segment and analysis points → `spec.content.report.outline`
- **Layout**: choose a built-in template ([`references/report-templates.md`](references/report-templates.md): `card` in-group chart card / `daily`/`weekly` HTML - dark banner + KPI cards + chart cards + collapsible detail rows + sectioned interpretation cards / `text` plain text); for "charts laid out directly in the group" choose card, for a full report choose HTML; if requirements are not met → modify per user request → finalize the inline version into `spec.content.report.template` (a body fragment or a complete HTML document both work; complex charts may be rendered by an in-page script - same-source data table + graceful no-JS degradation required; see the report-templates "HTML Delivery Specification")
- **Dry-run sample**: render a sample with real data + placeholder analysis text; lock after user confirmation

### Step 4 Delivery probing + test delivery (first step of two-step authorization)

Per [`references/delivery-mechanisms.md`](references/delivery-mechanisms.md): ask for the delivery target → probe available mechanisms (IM CLI existence/auth / webhook URL domain identifies the kind, refresh and echo it; **for channel CLIs other than lark-cli, draft the `send_template` per the "Command Templates" section of that file and test-deliver it together**) → **tell the user before sending**: "I will now send a test message to <target>; please confirm the form when you receive it" (the test delivery is the first step of two-step authorization - the target was provided by the user, the content is explicitly labeled test copy) → **test-deliver one message with the final form (template)** (real channel, recognizable test copy; file-form tasks include the file in the test; card tasks send a card) → user accepts the received form → lock the validated mechanism + parameters into `spec.delivery.mechanisms` (including `file_ok`/`form_ok` test results, the command template, and its success criteria); fallback mechanisms must also be test-delivered (explain the fallback semantics to the user when form capability is insufficient). The webhook URL will appear in plaintext in the automation trigger records; remind the user to confirm it is safe to expose before creation.

After all test-delivery validations pass, **write the finalized push_spec into `./push_spec.json`** (the root of the current session working directory; the authoritative field definitions are in [`references/push-spec-schema.md`](references/push-spec-schema.md)) - subsequent Steps 5/6 and the RUN phase all take this file as input.

### Step 5 Dry run (no push)

```bash
SCHEDULED_PUSH_DRY_RUN=1 python3 ./push_deliver.py ./push_spec.json
```

Real queries, no push (`SCHEDULED_PUSH_DRY_RUN=1` suppresses every real push, including auto_push/--push). Output: the full message preview (stdout) + per-segment detail (run_result.json: the rendered SQL / row count / first 5-row sample / aggregate values; report-scenario detail in data.json. Sample rows are retained with the session records inside the platform - take care with sensitive data). Any failed segment is presented with an R1 partial annotation, and the exit code is 1 (a dry run uses the same code as a real run — not pushing does not change failure semantics). The user confirms the numbers.

### Step 6 First real push (second step of two-step authorization)

- **Normal tasks**: `python3 ./push_deliver.py ./push_spec.json --push` performs one end-to-end real push → acceptance (the user confirms receipt in the group) → `spec.auto_push = true`
- **Report tasks**: use the two-stage real first push - `--stage data --push` → write the real analysis text per the outline into `analysis_slots.json` → `--stage render --push` → acceptance (running the full pipeline + `--push` together will be rejected by the script, to prevent placeholder text from entering a real group; report tasks need not set auto_push=true - the RUN message template's execution command must explicitly carry the `--stage data --push` / `--stage render --push` flags; push authorization does not rely on auto_push). The two stages report exit codes independently (a data-stage failure exits 1 without affecting the render stage's own exit code - when called serially, check the exit code per stage; do not infer one stage's result from the other's)

### Step 7 Register the schedule

`ae-cli agent +create-automation`, with the message embedding the locked spec per the template (normal edition / report edition, see recipes; the template carries `--push` - push authorization was already completed in the two-step authorization). **Before registering, make sure the execution Agent exists**: the automation must be bound to a dedicated execution Agent mounting this skill (reuse one found by checking skillIds; if none, create it with `+create-agent`, passing `--agent-id` explicitly - omitting it implicitly binds the current session's Agent, whose execution behavior is uncontrollable). When creating the execution Agent you **MUST pass `--instructions @-`** (write the system prompt to a temp file first and pipe it via stdin; the full text and command template are in the recipes "Key Points for the Creation Command") - omitting it creates a hollow Agent with systemPrompt=null, leaving the execution Agent's improvisation gate unguarded (measured consequence). **Judge automation creation success solely by the returned envelope's `ok` field; do not guess the key name holding the task; before creating, run `+list-automations` to check for a same-name task — if one exists, ask the user to choose (in-place `--message` update, or rename and create new) instead of registering a duplicate; after creation, read back and confirm exactly one task of the same name before delivering** (the platform has no delete command; duplicate tasks can only be disabled). Register the schedule time per the 1.3 time zone model. Deliver the three-piece set: task name + automation ID, jump link (`ae-cli config current --jq '.activeHost'` to read the domain dynamically and append `/agent/automations/<id>`; if the read-back host is an intranet address, replace it with the current deployment's standard access domain — the same convention as the analysis-board push path delivery), and the first-run tip (recommend manually triggering the task once on the platform's "Automation" page to verify - the page has a run-now entry; include the execution Agent's name).

**One dataset, two forms, delivered to two channels** (e.g. Feishu receives the HTML report + DingTalk receives the text report): one automation's message embeds two push_specs (distinguished by filename; queries and outline kept identical, only template and delivery differ); the step orchestration = first spec `--stage data` → write the slots → both specs in turn `--stage render --push` (the two specs MUST land in the same directory - the script looks for data.json / analysis_slots.json in the spec file's directory; landing the second one elsewhere exits with code 2 for missing data files; numeric consistency is guaranteed by the shared files) - the skeleton and message template are in the recipes "Dual Spec, Dual Form".


## V. RUN - Execution flow (a fresh sandbox triggered by automation)

**Data tasks (engine fills slots)**:
1. Parse `push_spec` in the message (missing fields → exit code 2)
2. Persist `push_deliver.py` from the Skill's `scripts/` (`+read-skill-script --output`)
3. Write `./push_spec.json` (identical to the message; must not rewrite it)
4. Execute `python3 ./push_deliver.py ./push_spec.json --push` (the message template carries --push; `spec.auto_push` is the BUILD-phase default safety net). Inside the script: static validation (labels/aggregate names referenced by placeholders exist; report-template slot/data references - whitespace after the colon is not allowed, whitespace present likewise exits 2; the placeholder vocabulary is closed - tokens outside the vocabulary are rejected, anything illegal exits with code 2; column-level references are validated in RUN, a missing column errors with exit code 2; a UNION branch's event table missing `$part_date` likewise exits 2, and a UNION inside a comment is not mis-split) → window computed per `window_freq` (hourly = the previous on-the-hour hour, rolling with the run time) → execute the queries (run/export pipelines + fallback switching) → summary aggregation computed live (a missing referenced column or an unparseable dirty value in sum both count as segment-level failure) → **the fill engine fills the artifacts into the template** → deliver per mechanisms (text and file attempted independently, no mutual guilt; every target that received text must actually get the file, otherwise record failure with exit code 3; file/form flags and fallback semantics per R5, cross-channel fallback per group - leading/trailing whitespace in a group is normalized at lock time)
5. Zero interaction, zero parameter changes throughout: no SQL edits, no project swaps, no follow-up questions, no mocks

**Report tasks (LLM fills slots, two stages)**:
1~3 same as above
4. `python3 ./push_deliver.py ./push_spec.json --stage data --push` → execute the queries → `./data.json` (deterministic data fetch; if everything fails, push the placeholder + exit code 1 and stop)
5. The Agent reads `data.json`, writes the analysis text section by section per `spec.content.report.outline` → `./analysis_slots.json` (**the LLM only produces text**: data, metric definition, outline, and layout all come from the spec and must not be altered)
6. `python3 ./push_deliver.py ./push_spec.json --stage render --push` → validate that the slot keys = the locked outline (missing/extra → exit code 2) + that the spec's `queries` label set matches the data.json segments (mismatch → exit code 2; the two specs' queries must be completely identical in the dual-spec setup) → render → deliver

**Exit code semantics** (authoritative table in push-spec-schema.md): **0** normal (including empty-data skip) / **1** fetch failure (placeholder already pushed) / **2** spec missing, placeholder-reference validation failure, or slot validation failure / **3** push failure (a target was ultimately not delivered)


## VI. Row-count and size gates (summary; authoritative table in push-spec-schema.md)

- **In-message row set** (in-message table / table component / preview): presentation-layer truncation - `preview_rows` rows before rendering (default 100) + an "X rows total" annotation; it is a presentation truncation, not a data truncation
- **File export (csv)**: not truncated by the message guardrail (data completeness is bounded by the SQL LIMIT - when the row count reaches the LIMIT, an "first N rows definition" completeness note is appended to the message and run_result records `limit_note`); export failure is fail-loud (placeholder + exit code 1); the message contains the first-N-rows data preview + summary aggregate values (subject to the size guardrail)
- **Message size guardrail**: when `max_message_kb` is exceeded (default 8KB), the row-set segment shrinks first while number segments are preserved as much as possible (R4); truncation does not change segment semantics
- **Query failure**: partial failure gets a segment-level annotation (R1); total failure replaces the whole message with a placeholder (R3); both exit code 1


## VII. Lifecycle Management

| Change | How |
|---|---|
| Change definition / SQL / outline | Re-run BUILD Steps 2~6 → new spec → `+update-automation --message` in-place update (**DRY_RUN first, then update**) |
| Change frequency | **Change both places in sync**: the automation schedule (`--schedule-kind/--time`) + `content.window_freq` in the spec inside the message - changing only the schedule without the spec silently computes the wrong data window |
| Switch delivery / recipients / form | Modify the spec's mechanism/template fields, test-deliver, then update; analysis-board push path: update + get read-back |
| Pause / resume | automation: `+update-automation` enabled; board push: update `enable_send` |
| Board-source definition drift | The board's time zone/definition is changed by the user → the pushed numbers change accordingly (a board source's definition = the board's settings); when numbers shift abnormally, check the board first |
| **Missed-run / failure re-push** | `python3 ./push_deliver.py ./push_spec.json --push --window-date YYYY-MM-DD` - anchored to "the 00:00 perspective of that day", recomputes the last complete period (to backfill yesterday's daily report, pass today; an hourly task backfills that day's previous-day 23:00~24:00 - other hourly slots cannot be anchored at day granularity; report tasks run both full stages from `--stage data`, and `--window-date` is mutually exclusive with `--stage render`). **Do NOT blindly re-run the next day** - without an anchor it pushes the "most recent period's" data, not the missed period (the group would see data with the wrong date). For self-service paths when numbers are wrong / nothing is received, see the seven ops items in Template C |


## VIII. Output templates (fixed format; improvised rewriting is forbidden)

Template A (parameter table for confirmation, **no time-zone row for non-multi-time-zone projects**) / Template B (dry-run results + confirmation) / Template C (delivery summary) - structure aligned with the sibling skill, all in the user's language, fixed confirmation questions; the report scenario's Template B attaches a rendered sample. Template bodies are in [`references/automation-recipes.md`](references/automation-recipes.md).


## References

- [`references/push-spec-schema.md`](references/push-spec-schema.md) - authoritative field definitions of push_spec.json (three-part structure of data pipeline x template x slots + placeholder vocabulary + gate semantics + R1~R5 decision semantics + exit codes)
- [`references/dashboard-daily-report.md`](references/dashboard-daily-report.md) - the analysis-board push path, fully tested boundaries (6 channels / placeholders / host_url pitfalls / frequency grid / read-back key-name transformations)
- [`references/automation-recipes.md`](references/automation-recipes.md) - the automation path's SQL templates (D0~D7), analysis-board data source (including the definition-mismatch branch and time-zone comparison), message templates (normal + report editions), output templates, spec variant examples
- [`references/delivery-mechanisms.md`](references/delivery-mechanisms.md) - delivery mechanisms: probing and test-delivery flow, the **form-probing methodology**, the built-in template library catalog, card reference implementations (VChart/table pitfalls, all recorded), webhook details
- [`references/report-templates.md`](references/report-templates.md) - analysis report layout templates (daily-report type / weekly-report type), slot specification, HTML delivery specification

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
