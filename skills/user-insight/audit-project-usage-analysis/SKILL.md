---
name: audit-project-usage-analysis
description: Analyze system usage of an AE project explicitly named, translated, or confirmed as "Audit Project". Aggregate per-user tracking-event counts for analysis, engage, and agent modules over a recent time window, assign usage tags (deep usage, viewer, engage task, data export), and assess module value and project activity. Trigger when the target project has already been identified as Audit Project and the user asks who uses which features, for per-user usage statistics, for analysis/engage/agent module usage, or for a system value assessment. Do not use for an unidentified project's generic usage question, dashboard freeze/cleanup actions, unrelated ad-hoc queries, or non-AE platform data.
---

# Audit Project Usage Analysis

Analyze tracking events of the "审计项目" (Audit Project) AE project, count user behavior, tag users, and assess module value. The deliverable is a "per-user statistics + module value assessment" report.

## Customer pain points & scenarios

A customer-success / delivery team deploying an AE project to a client typically faces these questions, which this skill answers in one pass:

1. **Is the system actually being used, and by whom?** — the per-user overview table shows, per account, how much each of analysis / engage / agent is used, with tags distinguishing deep users from passive viewers.
2. **Which features deliver value and which are idle?** — the module value assessment tells whether the engage module (separately purchased) and the agent module (6.0+) are actually adopted, so the team can steer onboarding or upsell.
3. **What business data does each person care about?** — the "attention-data" column maps each user's watched reports to business themes (payment / growth / data-dev / agent usage…), revealing who cares about revenue vs. retention.
4. **Which projects are active and who drives them?** — the project-activity module ranks projects by action volume with their top members and top reports, so the team knows where to focus support.

Scenarios that trigger this skill: a customer-success manager asking "审计项目用得怎么样", or asking "谁用了哪些功能 / 按人统计使用量" after the target has been explicitly confirmed as Audit Project. If the project has not been identified, resolve or confirm it before using this skill. The output is a ready-to-share markdown (and optional Feishu XML) report.

> **Language note:** the report **output** is in Chinese (the customer's business language), including labels such as 深度使用/查看者/运营任务/数据导出 and event display names. The instruction below describes the report structure in English; Chinese strings are runtime output values maintained directly in `scripts/generate_report.py`, not documentation text.

## Entry & Dependencies

This skill queries data through `ae-cli` only. Before running commands, load the `ae-analysis` skill for its conventions (command syntax, AI-facing definition contract, export/run routing). All queries use `ae-cli analysis adhoc export` — do NOT construct QP by hand or bypass ae-cli.

> **Trigger phrases (Chinese)**: 审计项目使用分析 / 审计项目用得怎么样. After the target is confirmed as Audit Project, contextual requests such as XX 用户用了哪些功能 / 分析、运营、agent 模块使用情况 / 系统价值评估 / 按人统计使用量 also apply.

Data processing and report generation use `scripts/generate_report.py` (built-in event classification, metric filtering, tagging logic, report template, and Chinese locale strings).

## Prerequisites (which modules to count)

The three modules have different availability. Judge each before counting; **modules that are not provisioned are simply omitted from the report**:

1. **Analysis module**: baseline feature, present for every customer, always counted.
2. **Engage module**: separately purchased, may be absent. Check total `engage_*` events; if 0 over 15 days (not provisioned), the report **completely omits the engage module** (no overview column, no TOP board, no "not provisioned" note) to keep the report clean.
3. **Agent module**: available by default after upgrading to 6.0, tied to version. First query `ta_version` to determine the version: count the agent module only when ≥ 6.0; below 6.0, omit it like engage.

Version check: `ta_version` is a system version field (e.g. `6.1`), preset on every event. Group any high-frequency event (e.g. `report_search`) by `ta_version` in the event model to read the current version. `fe_version` (frontend) and `common_service_deploy_version` (business component) are auxiliary.

### Cross-customer usage (project ID / tenant prefix resolved dynamically)

This skill targets any customer's project named "审计项目". The following identifiers are **never hardcoded**:

- **Project ID**: resolved dynamically by name via `ae-cli project info list --query "审计"`. Different customers have different IDs; no code change needed and no need to know the numeric ID.
- **System bare-account prefix**: `detect_system_account()` auto-detects it (an account starting with `ta-` and containing no `_` is the tenant prefix itself), used to exclude the bare account and build display-name fallbacks — different customers have different prefixes and there is no hardcoded fallback.

**Depends on AE platform standard event names and field names** (portable across projects, but gated by version/purchase):

- Events: analysis events (`report_search`/`dashboard_search`/`metric_sql`…), `engage_*` (requires purchase), agent events (requires 6.0+) — when a target project lacks a class of events, the corresponding module is automatically omitted (see prerequisites above).
- Fields: `#account_id`, `user_name`, `project_name`, `report_name`, `ta_version`, `sql_query_system_refresh` are AE platform preset fields.

If a target project's event/field names differ (custom tracking renames), verify against `references/event_classification.md` and sync the script dictionaries.

## Workflow

### Step 1: Confirm project and version

1. Resolve the project ID via `ae-cli project info list --query "审计"`.
2. Query `ta_version` to decide whether to count the agent module.
   - **Checkpoint**: record the resolved project ID and version; abort with a clarifying question if the query returns multiple projects or no 审计项目.

### Step 2: Export data (6 exports)

Use `ae-cli analysis adhoc export` (`--artifact-format jsonl --output <file> --force`), grouped by `#account_id`, counting `total_count` per event, time range "recent 15 days" = `{"mode":"recent","unit":"day","value":15}` (includes today).

Event lists and grouping dimensions are in `references/event_classification.md`; export definitions are generated by `scripts/generate_report.py --prepare`:

- **Analysis + dashboard** (one export): all analysis events + all dashboard events; for `metric_sql`, add filter `sql_query_system_refresh is_false` (exclude scheduled refresh).
- **Engage**: all `engage_*` events (`*_model` page-browse events are excluded inside the script; still exported for completeness).
- **Agent**: all agent events (agent_* plus tool-call events; `--prepare` generates the full list).
- **Account × project** (project dimension): group `report_search`/`dashboard_search`/`dashboard_create`/`report_save`/`report_edit`/`export_data`/`model_search` by `#account_id` + `project_name` (`def_account_project.json`). Feeds the "active projects TOP3" column and the "project activity" module. Note: agent events carry no project field, so they are excluded from the project dimension.
- **Report interest** (business attention): group `report_search` by `#account_id` + `project_name` + `report_name` (`def_report_interest.json`). Report names are the business theme; feeds the "business attention" module and the "top report" column of the project table.

**Concurrency control**: submit the 6 exports in **two parallel batches of 3** (`&` background + `wait`). Submitting all 6 at once triggers backend concurrency limits (`Concurrency limit exceeded`). If one export reports that error, wait for active queries to finish and retry it alone. `--output` blocks until completion.

**Resume / idempotency**: if the flow is interrupted midway (e.g. token expiry), before re-running check whether each `--output` target file already exists and is non-empty — skip exports that are already complete, only re-run the missing ones. The 6 exports have no inter-dependency.

### Step 3: Build account → display-name mapping

`#account_id` is the unified account identifier (present on all three event families); `user_name` is the operator display name (a user property) — present on analysis/engage events but empty on agent events.

Group `report_search` and `model_search` by `#account_id` + `user_name` (`def_mapping.json`) — one row per account, far fewer rows than a detail export. For accounts not mapped (pure-agent users), strip the "system bare-account prefix + `_`" from `#account_id` as the display name (prefix auto-detected; see "Key metrics rationale").

### Step 4: Run the script to generate the report

```bash
python3 scripts/generate_report.py \
  --analysis analysis_by_account.jsonl.gz \
  --engage engage_by_account.jsonl.gz \
  --agent agent_by_account.jsonl.gz \
  --mapping-raw mapping_by_account.jsonl.gz \
  --account-project account_project.jsonl.gz \
  --report-interest report_interest.jsonl.gz \
  --top-n 20            # 20 during debug; full output = omit or pass 0
  --out-json 审计项目_按人统计_细分.json   # full detail dump (optional)
  --feishu-xml report.xml                 # also emit Feishu doc XML (optional)
```

The script does: parse, exclude the system bare account, drop automated tasks, tag users, render the report (markdown + optional Feishu XML from a single shared conclusion/data layer).

**Report format is fixed in the script** (markdown output + `--feishu-xml` one-shot Feishu XML; the two share the same structure, no manual transcription needed):

- markdown is standard (tables; multi-value cells use `<br>` line breaks), pasteable/importable into Feishu, Yuque, Notion, or any markdown environment.
- the XML from `--feishu-xml` can be created with `lark-cli docs +create --content @report.xml`, or overwritten with `lark-cli docs +update --command overwrite --content @report.xml`; multi-value cells are split into multiple `<p>` lines per Feishu rules. **Caution: `overwrite` wipes and rewrites the existing doc, dropping its images and comments — confirm with the user before overwriting, or use `docs +create` to create a new doc instead.**

## Key metrics rationale (why it is handled this way)

1. **Accounts unified on `#account_id`** (user property): `user_name` is missing on agent events; only `#account_id` spans all three event families; `user_name` is display-only.
2. **Exclude the system bare account**: it is the pure tenant prefix in `#account_id` with no username suffix, carrying automated tracking like engage `*_model` page-browse, and does not represent a real person. The script auto-detects the prefix (`ta-`-prefixed, no `_`) without a hardcoded fallback. When no bare-account row is present, it leaves the account set unchanged and retains full account IDs as display-name fallbacks.
3. **Drop automated tasks as much as possible**:
   - `metric_sql` (all queries) contains heavy internal SQL; filter scheduled refresh with `sql_query_system_refresh is_false` (bool field — operator must be `is_true`/`is_false`/`exists` only).
   - `metric_task` (task execution) and `metric_interface` (metric interface) are low-level automated executions, not counted as "analysis actions".
   - Engage `*_model` events (`engage_task_model`/`engage_activity_model`/`engage_channel_model`/`engage_task_instance_model`) are page-browse auto tracking, not counted as "engage actions".
   - the agent tool-call event's `call_source` distinguishes `te-agent` (automated) / `customer` (user-initiated) / `ae-cli`; all three count into the tool-call total, no proactive/reactive split (these are backend channels and normal usage).
4. **Dashboards merged into analysis actions**: the overview table has only 分析/运营/agent columns; dashboards are part of the analysis product, merged into analysis; but "create dashboard" still independently drives the deep-usage tag.

## Tag rules

Tag each user's per-person detail:

- **Deep usage** (深度使用): `build report > 0` or `data export > 0` or `create dashboard > 0`. Judged by: build report (`report_save`/`report_edit`/`chart_save`/`report_del`), data export (`export_data`/`download_data`), create dashboard (`dashboard_create`). Data export and create dashboard carry equal weight.
- **Viewer** (查看者): no deep-usage behavior, but some view behavior (`view report`/`view dashboard`/`model analysis`/`dashboard management` any > 0).
- **Engage task** (运营任务): engage active actions > 0 (stackable with other tags).
- **Data export** (数据导出): `data export > 0` (stackable; since "data export" is itself a deep-usage criterion, users with this tag always also carry "deep usage").

"Deep usage" and "viewer" are mutually exclusive; "engage task" and "data export" are stackable. Users with no tag (pure-agent usage or SQL-only) show `-`.

Note: **agent behavior does not drive the deep-usage tag** (the deep-usage definition targets analysis-side behavior only). If requirements change to fold agent deep usage in, adjust the script's `is_deep` logic.

## Report structure

Output strictly follows this template (markdown; built into `generate_report.py`), in this module order:

### Section 1: Module usage & value assessment (first)

1. **Value conclusions** (first; 3–5 items generated dynamically by the script; Engage and Agent conclusions appear only when those modules appear in the report):
   1. Analysis is the foundation;
   2. Dashboards are mainly for viewing — do not infer "depth" from few creations (mature projects mostly view existing dashboards, which is normal);
   3. Engage module — describe data objectively, do **not** make judgments like "value depression" (auto tasks configured on mature projects produce no new tracking, so the numbers only reflect recent new actions);
   4. Agent is conversation-centric — contrast "usage" (conversations, tool calls) vs "building" (create Agent, Skill management);
   5. Users form a pyramid (deep usage / viewer / no tag).

2. **Usage overview** (table: module / active accounts / action volume; only provisioned modules appear).

3. **Per-module feature distribution** (module name as bold heading + sub-table "feature category | count"; use tables, not pie charts).

### Section 2: Per-user statistics

1. **Overview table** (single table; column order: rank / account / attention-data / tags / active-projects(TOP3) / top-reports / data-export / analysis-actions / engage-actions / agent-actions).
   - "attention-data": the script maps the user's **all** watched reports (not only TOP3) to business themes via keyword rules (Agent usage / payment-revenue / data-dev / data-resource-usage / user-growth-activity / user-profile-segmentation / ops-monitoring / base-data), deduped, at most 6 themes, comma-separated.
   - "tags": multiple tags, one per line in the cell.
   - "active-projects(TOP3)": the user's top-3 projects by action volume, format `project（count）`, one per line.
   - "top-reports": the user's top-3 most-viewed reports, format `name（count）`, one per line.
   - "data-export": export count within the time window (`export_data`/`download_data`).
   - Debug stage shows top 20; full output shows all (with a "N users summary" line).
   - "analysis-actions" = analysis + dashboard combined; "engage-actions"/"agent-actions" columns appear only when the module exists.

2. **Three-module TOP boards** (table: rank + one column per behavior category, cell = `name count`; TOP5 per category, empty cells when fewer than 5; a whole module is omitted when not provisioned).

### Section 3: Project activity

- Table: rank / project name / active users / view reports / view dashboards / model analysis / create dashboards / build reports / data export / total actions / top members (TOP3, comma-separated) / top report (the project's TOP1 report, `report: name（count）`).
- Sorted by total actions descending; agent behavior excluded (no project field); note the metric rationale and project count at the top.

## Verification & self-check (before delivering the report)

**Data volume threshold (prerequisite)**: if the analysis export yields zero accounts or the total action volume is 0, stop and investigate (likely a field-name mismatch) instead of emitting an empty report. The script prints a warning to stderr when a data file exists but all its event columns read 0.

**Result verification (step checkpoints)**: after each export, confirm the file exists, is non-empty, and its `row` count is plausibly > 0 (e.g. analysis export should have dozens of accounts). After running the script, spot-check: (1) the total-user count matches the overview-table row count; (2) conclusion numbers (e.g. "N/M users") match the computed totals in the same report; (3) markdown and Feishu XML conclusions are identical (they share one `build_conclusions` source).

**Output self-check (consistency + retry)**: before delivering, re-check that (1) tag categories sum to the total user count; (2) the "active projects" and "top reports" cells are line-broken per item; (3) no `null`/`(null)` leaked into user-visible cells. If an export failed with a concurrency error, retry it once after the current batch; if a field seems all-zero, re-verify the export column names against the script's `col_value` candidates before trusting the output.

## Output rules

- Debug/conversation stage: overview table top 20.
- Full skill output: overview table full, with the full detail also dumped to JSON (`审计项目_按人统计_细分.json`).
- The report header states the time range (recent 15 days, includes today) and the metric rationale (account basis, auto-task exclusion, engage omission when not provisioned, agent version gate, project dimension covers analysis/dashboard only).
- The report is standard markdown (tables, `<br>` line breaks in cells are universal syntax), pasteable/importable into Feishu, Yuque, Notion, or any markdown environment — not bound to any single platform.
