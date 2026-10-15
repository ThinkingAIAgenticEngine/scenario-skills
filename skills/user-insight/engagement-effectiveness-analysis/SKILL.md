---
name: engagement-effectiveness-analysis
version: "1.12"
description: "Analyzes post-execution effectiveness of marketing touchpoints (push, in-app message, popup, SMS, EDM, phone, journey canvas) across two data modes: (A) native ThinkingData Engage, queried by task_id / flow_id / config_id; (B) third-party or self-built platforms, where the campaign strategy and the tracking events used for result recovery are collected first and a funnel plus event analysis is built from them. Triggered when the user asks about push open rate, click-through rate, touchpoint conversion, delivery funnel, strategy or node comparison, experiment lift, engagement fatigue, or the effectiveness of a campaign sent outside ThinkingData. Returns two local artifacts: a seven-sheet detail workbook (XLSX) holding all retrieved campaign data, and a six-section analysis report explaining how the campaign performed and what to optimize. NOT applicable when no tracking events exist for the campaign (design the tracking plan with ae-generate-tracking-plan first), when the task is creating or editing a campaign (use gift-push-strategy or ae-engage), when the task is diagnosing non-delivery rather than measuring delivered effect, or when future performance must be predicted rather than reviewed. Minimum data: a 3-day window and 1000 targeted users."
agent_created: true
triggers:
  - 触达效果
  - 推送效果
  - 推送数据
  - 打开率
  - 点击率
  - 触达分析
  - 触达转化
  - 触达疲劳
  - 运营效果回收
  - 触达明细数据
  - 第三方触达
  - 自建推送系统
  - 外部运营后台
  - 触达回收事件
  - engagement effectiveness
  - push performance
metadata:
  language: zh-CN
  domain: analytics
  methodology: engagement-effectiveness
  skills:
    - ae-analysis
    - ae-generate-tracking-plan
  tools:
    - Bash
    - Read
    - Write
    - python3
    - openpyxl
---

# Engagement Effectiveness Analysis v1.12

Post-execution review of marketing touchpoints: given a campaign that already
went out, answer whether it worked, why, and what to change.

The distinctive constraint is that the customer may not have sent through
ThinkingData at all. Many accounts run their own push system or a third-party CDP
while ThinkingData only receives the events. Those campaigns have no canvas id and
no platform-side delivery metrics, so the skill collects the campaign description
and the recovery events instead, rebuilds the chain from tracking data, and runs
the **same analysis** over it.

## Use This Skill When

- The user asks how a push / in-app message / SMS / popup / EDM campaign performed
- The user wants open rate, click-through, conversion, or the delivery funnel for a specific send
- The user asks whether an A/B test produced real lift
- The user describes a campaign sent from their own platform and wants it evaluated
- The user is worried about engagement fatigue from repeated sends

## Directory Guide

```
engagement-effectiveness-analysis/
├── SKILL.md
├── references/
│   ├── steps/                        # one file per step: Goal / Input / Output / Flow /
│   │   ├── 00_preflight.md           # decision rules / error-handling table
│   │   ├── 01_intake.md
│   │   ├── 02_fetch.md
│   │   ├── 03_analyze.md
│   │   ├── 04_export_excel.md
│   │   ├── 05_report.md
│   │   └── 06_validate.md
│   ├── engage_command_reference.md      # mode A: commands, parameters, return shapes
│   ├── analysis_command_reference.md    # mode B: builders, qp structure, envelope traps
│   ├── intake_contract.md               # mode B: the 11 questions and how to resolve unknowns
│   ├── metric_definitions.md            # the shared six-stage funnel and rate definitions
│   └── benchmark_thresholds.md          # thresholds and how a bleed point is chosen
├── scripts/
│   ├── _env.py                      # portable tool discovery + dependency bootstrap (no hard-coded paths)
│   ├── _ae.py                       # shared ae-cli helpers (discovery, envelope handling)
│   ├── _cmdtree.py                  # 1.x <-> 6.x command-tree translation
│   ├── _wording.py                  # locale catalog loader for report wording (_L / _F)
│   ├── check_prerequisites.py       # Step 0 gate: interpreter, auth, remote reach, local write permissions
│   ├── selftest_gates.py            # tests the Step 0 gate itself against fixtures (see Gate Self-Test)
│   ├── detect_mode.py               # Step 0 gate: resolve mode A vs B
│   ├── validate_params.py           # Step 0 gate: parameters and window
│   ├── collect_intake.py            # Step 1b: render the mode-B questionnaire
│   ├── resolve_events.py            # Step 1b: fuzzy-search events / properties / audiences
│   ├── validate_intake.py           # Step 1b gate: required answers present
│   ├── fetch_engage_reports.py      # Step 2a: pull native Engage reports
│   ├── fetch_event_analysis.py      # Step 2b: build + run ad-hoc queries, normalize
│   ├── validate_raw_report.py       # Step 2 gate: payload present and non-zero
│   ├── analyze_effectiveness.py     # Step 3: six-dimension analysis (shared by both modes)
│   ├── validate_analysis.py         # Step 3 gate: analysis blocks complete and coherent
│   ├── export_detail_excel.py       # Step 4: seven-sheet workbook (shared by both modes)
│   ├── validate_excel.py            # Step 4 gate: sheets present and populated
│   ├── generate_report.py           # Step 5: six-section report (shared by both modes)
│   ├── validate_report.py           # Step 5 gate: completeness, traceability, hygiene
│   └── validate_outputs.py          # Combined post-flight gate over all three artifacts
└── assets/
    ├── detail_workbook_spec.md          # the seven sheets and their columns
    └── report_template.md               # the six report sections and hard requirements
    └── locale_zh.json                   # report wording catalog (data, not code)
```

**Language rule for this skill.** Report wording lives in
`assets/locale_zh.json` and is reached through `_wording._L(key)` /
`_wording._F(key, **values)`, and comments and docstrings are English; a few
literal section titles in the validators stay Chinese by design and the
self-test pins their ratio (CJK may cover at most 10% of a `.py` file). Chinese
otherwise exists only in the catalog, in the Markdown deliverables and in this
file. Keep it that way — a missing catalog key raises `KeyError` rather than
shipping a blank sentence, so a stray inline literal is not the failure mode you
would notice.

## Portable Deployment

This skill is handed to other people, so it has to work on a machine that has
none of the author's setup. The rule applied throughout: **no hard-coded path,
no pre-installed dependency, no platform assumption.**

### What the target machine needs

| Requirement | Needed for | If missing |
|---|---|---|
| `python3` >= 3.8 | everything | install python - macOS ships one, Windows needs python.org or the Microsoft Store |
| `ae-cli` reachable **and speaking a command tree this skill can drive** | every ae-cli call | install the npm package `@thinkingai/ae-cli` through your team's channel, or point `$AE_CLI_PATH` at the binary. Both 1.x and 6.x work - see the warning below |
| an ae-cli login for the target host | Step 2, both modes | `ae-cli auth login`, or log in through the web UI and run `ae-cli auth set-token <token>` |
| write access to the workspace | `tmp/` and `output/` | run from a writable directory or pass `--workspace` |
| `openpyxl` | Step 4 (XLSX) only | **handled automatically** - see below |

Nothing else is required. There is no API key to obtain and no scope to request:
ae-cli's access model is a session plus project visibility.

> **Both ae-cli generations are supported.**
>
> 1.x and 6.x are not compatible with each other, and both can sit side by side
> on one machine, so which one discovery picks decides whether anything runs at
> all. The difference is structural, not cosmetic: 1.x hard-codes one command per
> backend tool (`engage +task_list`), while 6.x is a thin shell over a
> **capability gateway** whose capability list is fetched from the server
> (`engage-task task list`, or more durably `capability run
> engage-task.task.list`). That is why 6.x `--help` shows a different tree for
> the same operations - and why a 6.x run that is not translated fails every
> step while `--version` and `auth status` still look healthy.
>
> `_cmdtree.py` absorbs the difference in one place. Every script keeps
> describing its call in the 1.x vocabulary; `_ae.run_ae()` translates that into
> the 6.x form and maps the 6.x response back (payload unwrapped from `result`,
> fields renamed from snake_case, row lists found wherever the generation put
> them). No analysis code knows which generation answered - so neither has to be
> rewritten the next time the CLI tree moves.
>
> Step 0 reports which generation it found (`ae_cli_compat`), discovery
> **prefers 6.x**, and a binary matching neither still stops the run with a
> FATAL: a command tree the translation table has never seen cannot be guessed
> at, and guessing shows up as a confusing mid-run failure.
>
> **Ad-hoc analysis runs on the unified 6.x contract.** It is a *single* call
> (`analysis adhoc run --model-type <m> --definition <json>`, with raw QP
> rejected outright, so no intermediate QP ever exists), and the definition is a
> nested object rather than a flag tail, so no per-call argv translation can
> express it. `_ae.adhoc_run()` builds it: callers pass the model, the time
> range and the model's own parameters, and get `{"title", "rows"}` back. Both
> modes are therefore complete and verified end to end on 6.x.
>
> Two measured asymmetries live in that adapter, and both are silent if you get
> them wrong:
>
> * **The time-range keys are pinned to snake_case.** The contract wants
>   `{"mode":"custom","start_time":…,"end_time":…}` and rejects the camelCase
>   form. `TIME_RANGE_KEYS` respells on the way in, so a caller may send either.
> * **The lifecycle id prefix is pinned.** The schema matches
>   `^cli_[0-9a-f]{32}$`. The core is respelled, and an id that cannot be
>   respelled is dropped rather than sent in a form the server refuses (it is
>   optional there).

### Where the login comes from

`ae-cli auth login` auto-extracts the token from Chrome on macOS, which requires
the *Automation* permission for the calling process (`osascript` otherwise fails
with `权限违例 (-10004)` / `-17404`), and it reads `localStorage.ACCESS_TOKEN`
from a tab already open on the host. When that path is unavailable, log in
through the web UI and hand the token over explicitly:

```bash
# in the browser console on the logged-in AE page
localStorage.getItem('ACCESS_TOKEN')
ae-cli --host https://<host> auth set-token '<token>'   # validates before saving
```

`--host` is a **global** option (`ae-cli --host <url> <command>`), whereas
`ae-cli config` is an interactive TUI and unsuitable for scripts. For a
zero-side-effect validity test, export `TE_TOKEN` - `getToken()` honours it
before touching the credential store, so a stale token can be checked without
overwriting anything.

### How the one dependency is handled

`openpyxl` is the only third-party import in the skill. It is resolved at Step 0
in three stages - the current interpreter, any other interpreter found on the
machine, and finally a private virtualenv built under the user cache directory:

| Platform | Cache location |
|---|---|
| macOS | `~/Library/Caches/ae-skill-cache/` |
| Linux | `$XDG_CACHE_HOME/ae-skill-cache/` (default `~/.cache/`) |
| Windows | `%LOCALAPPDATA%\ae-skill-cache\` |

Override with `$AE_SKILL_CACHE`. The environment is reused on later runs and the
user's own site-packages are never touched - which also sidesteps PEP 668
"externally managed environment" failures on current Linux distributions.
`--no-install` turns the automatic build off and yields a plain install command.

### Tool discovery

`ae-cli` and the interpreter are both found by the same three steps: an explicit
override (argument or environment variable), then `PATH`, then a scan of
conventional prefixes with version directories left as wildcards. `_env.py` owns
this and every other script imports it, so the logic cannot drift into a second,
weaker copy that happens to be the one that runs.

**Rule for anyone editing these scripts**: never add an absolute path that only
exists on your own machine. A failed discovery must list what was searched and
how to override it, not just fail.

## Programmatic Guards

These constraints are enforced by scripts. The agent is not expected to remember
them; the scripts intercept at the decision points.

| Guard | Script | Trigger | Behavior |
|---|---|---|---|
| Environment ready | `scripts/check_prerequisites.py` | Step 0 | ae-cli missing, unauthenticated, `openpyxl` absent, project not visible, credential store unwritable or missing the active host, or `tmp/`/`output/` not writable -> exit 1 |
| Gate trustworthy | `scripts/selftest_gates.py` | before publish, after any `scripts/` edit | any fixture case regresses -> exit 1; do not ship a red self-test |
| Mode resolvable | `scripts/detect_mode.py` | Step 0 | neither a native object id nor an event chain supplied -> exit 1, ask the user |
| Parameters valid | `scripts/validate_params.py` | Step 0 | mode/id mismatch, unparseable date, future end date, or missing click event in mode B -> exit 1 |
| Intake complete | `scripts/validate_intake.py` | Step 1b | any REQUIRED answer missing -> exit 1; a free-text "event" that is really a description -> flagged |
| Payload usable | `scripts/validate_raw_report.py` | Step 2 | no parsable metric block -> exit 1; all metrics zero -> EMPTY, confirm before proceeding |
| Analysis coherent | `scripts/validate_analysis.py` | Step 3 | missing block, bleed point without a benchmark reference, duplicated issue category, empty validation plan -> exit 1 |
| Workbook complete | `scripts/validate_excel.py` | Step 4 | a required sheet absent or blank -> exit 1 |
| Report deliverable | `scripts/validate_report.py` | Step 5 | missing section, absent confidence statement, or leaked credential / internal IP / home path -> exit 1 |
| Combined post-flight | `scripts/validate_outputs.py` | after Step 5 | 16 checks across all three artifacts |

Key behaviors worth knowing, because they exist to stop silent wrongness rather
than to stop errors:

- `validate_raw_report.py` treats an all-zero metric block as `EMPTY`, not
  success. All-zero is equally consistent with "the campaign reached nobody" and
  "the wrong object id was queried", so it must be confirmed.
- `validate_analysis.py` rejects a bleed point that lacks a threshold reference.
  That is the signature of the absolute-drop ranking bug described in Pitfalls.
- `validate_analysis.py` rejects a `validation_plan` with neither indicators nor
  an explicit statement that no baseline could be established.
- `validate_report.py` treats missing data reported as churn language as a
  failure indicator through the confidence-statement and section checks; the
  generator itself already separates the two.

## Gate Self-Test

`check_prerequisites.py` is a gate, so its worth lies entirely in what it
*rejects*. A gate that answers SUCCESS for a broken environment is worse than no
gate, because the failure then lands later with the fetching already paid for.
The gate is therefore itself under test, by a script, and that test is part of
the deliverable rather than a one-off check:

```bash
$PY $S/scripts/selftest_gates.py                      # 149 fixture cases, no network
$PY $S/scripts/selftest_gates.py --smoke              # + 7 end-to-end cases (calls ae-cli)
$PY $S/scripts/selftest_gates.py --out tmp/gate_selftest.json
```

Every case uses a fixture - a stub `ae-cli` executable whose output is driven by
environment variables, and a throwaway credential store in a temp directory. The
real `~/.ae-cli` is never read, written or chmod-ed, and nothing leaves the
machine unless `--smoke` is passed.

| Group | Cases | Pins |
|---|:---:|---|
| `host_stem` | 5 | host URL -> `<host>.enc.json` stem, including the `:` -> `_` port rewrite |
| `auth` | 7 | structured `authenticated:false` is FATAL rather than SUCCESS; `ok:false`, non-zero exit, and the text fallback both ways |
| `credential_store` | 8 | absent, unreadable, empty and read-only stores; a missing active host must name the alternates |
| `output_writable` | 4 | read-only workspace, missing workspace, and that `tmp/`/`output/` are actually created |
| `network` | 2 | no host skips the probe; an unreachable host is ERROR, never FATAL |
| `portability` | 15 | override order (argument beats environment), candidate shape, rejection of `python3-config`-style artefacts on both separators, and that **no other script hard-codes an author-specific path** |
| `task_meta` | 7 | task resolution: a point lookup, a soft `success:false` that must **not** read as a hit, paged scans that reach past page 1, and an end-to-end check that the analysis reads the id from its nested `object` home |
| `meta_contract` | 16 | trigger time precedence and its fallback marker, timezone conversion, crontab humanising, the caveat block being emitted only when two sources actually disagree, and the report/workbook rendering both |
| `cli_compat` | 8 | variant detection from the advertised domains, both generations reporting compatible, an unreadable help output as `None` rather than `False`, and discovery stepping past an incompatible binary listed first |
| `cmdtree` | 14 | 1.x argv -> capability argv (int ids, nested `req`, `-q` -> list), the snake_case column rename, `result` unwrapping, and row-list discovery |
| `adhoc` | 35 | the two ad-hoc protocols: time-range respelling, lifecycle-id prefix, definition regrouping, **funnel column resolution**, "a percentage is not a count", summary-label canonicalisation, and that truncation/unknown columns reach the confidence statement |
| `experiment` | 10 | a missing A/B experiment stays missing (no fabricated control/experiment pair), the two degradation wordings stay distinct, and an insignificant experiment is not reported as a win |
| `verdict` | 6 | the coverage qualifier on the one-line verdict: only a *material* degradation (loss ≠ 「不影响结论」) earns the "observable stages only" hedge, and a clean payload gets none |
| `escaping` | 7 | the escape boundary covers the **whole structure**, not just `meta`: a payload carried by a downstream-assembled field (degradations) cannot reach the report as inline HTML, a `\|` in it cannot split a Markdown table, and legitimate text acquires no escape entities at all |
| `--smoke` | 7 | stdout is valid JSON, exit code agrees with the verdict, check names are unique and entries well-formed |

144 cases run by default (151 with `--smoke`).

The `portability` group is the one that protects this skill's distribution. The
failure it catches is a contributor "fixing" discovery by pasting their own
virtualenv path: that change passes every functional test on their machine and
breaks on every other one, so it is asserted structurally rather than trusted.

The `adhoc` group exists for the same reason one level down: every rule it pins
is mechanical (a key spelling, a column index, a label), and a mechanical mistake
there does not raise. A wrong key is rejected by one generation or the other, and
a wrong column index yields a plausible zero - which is why the cases assert that
the *unknown* is declared rather than silently rendered as `0`.

Run it after touching anything in `scripts/`, and before publishing a new
version. Exit 1 means the gate can no longer be trusted; a red self-test is not
shippable.

The suite deliberately asserts shapes rather than counts: the number of check
entries legitimately varies with the arguments and the auth outcome
(`project_visible` needs `--project-id`, `network_reachable` needs a resolved
host), so a pinned count would break on every legitimate change.

**Three false negatives this suite exists to prevent.** All three were found in
the field, not reasoned about in advance:

1. A logged-out session answers `{"ok": true, "data": {"authenticated": false}}`.
   That payload contains none of the phrases an earlier text-matching check
   looked for, so the gate reported SUCCESS while every call afterwards returned
   HTTP 500. The check now reads the structured verdict first and falls back to
   text matching only when the output is not machine-readable.
2. ae-cli writes its error envelope to **stderr** and leaves stdout empty, so a
   stdout-only read replaced the real reason (`HTTP error: 500 Server Error`
   from the analysis gateway) with a generic "returned empty output".
   `_ae.run_ae` now parses the
   stderr envelope and lets `unwrap_error` shape the message.
3. Task metadata was resolved from *the first page* of `+task_list`. A real
   project holds 500+ tasks and the list is paged, so a valid low id sits past
   any fixed slice: the run declared a live campaign missing and every header
   field in the report - channel, trigger time, conversion indicator - came out
   blank. Compounding it, `+task_detail` answers for an unknown id with a
   **soft** error (`ok: true` while `data.success: false`), so trusting the exit
   status turns "not found" into a false hit. `_ae.find_task` now does a point
   lookup, reads the flag rather than the exit code, and falls back to a full
   paged scan.

## Style Conventions

Not code-enforceable, so they are stated here for the agent to follow.

1. **Ask the mode-B questionnaire in one turn.** Present all 11 items at once.
   Drip-feeding questions across turns loses the user.
2. **Never choose an event name silently.** Search, show the candidates with
   their human descriptions, and let the user confirm.
3. **Name deliverables in the customer's language.** `{strategy}_明细数据_{date}.xlsx`
   and `{strategy}_效果分析报告_{date}.md`, with the date as `YYYYMMDD`.
4. **State the data source mode on the first line of the report.** The two modes
   are not equally precise and the reader must know which they are holding.
5. **Estimate conservatively, then label it.** Precision-loss figures are
   estimates; present them as such rather than as measurements.
6. **Prefer `ae-cli` over any connector or hand-rolled HTTP call** when it
   can do the same thing. The CLI carries the project context, the retry
   envelope and the generation differences described above; a direct call
   has to re-derive all three.
7. **Clean up intermediate files** under `tmp/` when the run finishes. They are
   not deliverables.
8. **Write the report in Chinese for Chinese customers**, keeping the section
   headings from `assets/report_template.md` verbatim so the deliverable is
   consistent across runs.

## Top-Level Flow

Each step has its own file under `references/steps/`, with Goal, Input, Output, Executor,
Validation Gate, Failure Handling, a numbered Flow whose sub-steps carry explicit
`IF … THEN` decision rules, and an error-handling table. **Read the step file before
executing that step** — the table below is the index, and `## Detailed Steps` further
down keeps the measured rationale behind each step.

| # | Step | Mode | Step file | Scripts | Output | Validation Gate |
|---|---|:---:|---|---|---|---|
| 0 | Pre-flight, mode detection, parameter check | A/B | `references/steps/00_preflight.md` | `check_prerequisites.py`, `detect_mode.py`, `validate_params.py` | `tmp/mode.json` | all three scripts must exit 0 |
| 1a | Identify the campaign object | A | `references/steps/01_intake.md` | inline (`engage +task_list`) | `tmp/target.json` | object must carry `hasPushRecord=true` |
| 1b | Collect strategy and recovery events | B | `references/steps/01_intake.md` | `collect_intake.py`, `resolve_events.py` | `tmp/intake.json` | `validate_intake.py` |
| 2a | Fetch native Engage reports | A | `references/steps/02_fetch.md` | `fetch_engage_reports.py` | `tmp/raw_*.json` | `validate_raw_report.py --mode A` |
| 2b | Build and run ad-hoc analysis | B | `references/steps/02_fetch.md` | `fetch_event_analysis.py` | `tmp/raw_*.json` | `validate_raw_report.py --mode B` |
| 3 | Six-dimension analysis (shared) | A/B | `references/steps/03_analyze.md` | `analyze_effectiveness.py` | `tmp/analysis.json` | `validate_analysis.py` |
| 4 | Export the detail workbook (shared) | A/B | `references/steps/04_export_excel.md` | `export_detail_excel.py` | `output/{strategy}_明细数据_{date}.xlsx` | `validate_excel.py` |
| 5 | Generate the analysis report (shared) | A/B | `references/steps/05_report.md` | `generate_report.py` | `output/{strategy}_效果分析报告_{date}.md` | `validate_report.py`, then `validate_outputs.py` |
| 6 | Post-flight cross-check | A/B | `references/steps/06_validate.md` | `validate_outputs.py` | — | the two deliverables must agree |

**The architecture in one line: Step 2 forks, Steps 3 to 6 do not.** Mode
differences are confined to the fetch layer. `fetch_event_analysis.py` normalizes
ad-hoc query output into the exact shape mode A produces, so the analysis,
workbook and report carry no mode branching at all. This is not a design
intention; it was verified end to end.

## Analysis Framework

Six dimensions. The first three are always attempted; the last three degrade when
their inputs are unavailable.

### 1. Delivery chain funnel
Walk target audience -> flow entry -> dispatch -> impression -> click ->
conversion, computing the stage-to-stage drop at each step.
Fields: `plan`, `actualTrigger`, `trigger`, `view`, `click`, `main`.
Mode A reads them from `engage +task_data_overview`; mode B reconstructs the
chain from events. First, and always: identify whether the chain is *truncated*
(not measured) or *churning* (measurably losing users). These two look identical
in a raw table and mean opposite things.

### 2. Strategy, node and group comparison
Compare campaigns against each other, or canvas nodes against each other, or
A/B groups against each other. Mode A uses `engage +config_item_strategy_comparison`
and `+flow_node_overview_report`; mode B groups by the discriminating property.
Read this second: it explains *which* variant caused the funnel shape found in
dimension 1.

### 3. Experiment judgment
Read the platform's own lift, confidence interval and significance rather than
recomputing them. Mode A uses `engage +task_experiment_report`; mode B uses a
group property when the customer tracked one. Read third: it answers whether the
observed difference is real, which changes whether dimension 5 should recommend
scaling or abandoning.

### 4. Trend and frequency
Plot the metric trend across the window to find the fatigue inflection - the
point where a repeat send starts costing more unsubscribes than it earns clicks.
Fields: per-day series from `detail_type=time` (mode A) or
`--time_particle_size day` (mode B). Read after the funnel: fatigue only matters
if the campaign is otherwise performing.

### 5. Audience response segmentation
Break response down by activity level, payment tier, lifecycle stage or new vs
returning, to separate the segment that responds from the segment being wasted on.
Mode A rarely exposes this; mode B gets it from `--groups`. Read fifth: it
converts a general "improve targeting" into a specific segment to include or drop.

### 6. Value accounting and prioritised actions
Convert the funnel into recoverable headcount per stage and rank the actions by
expected impact. Every recommendation carries an expected effect. Read last,
because it depends on everything above.

Dimension priorities when the run is short on time:
`funnel integrity > benchmark miss > experiment verdict > content and timing > segmentation`.

## Who Reads What (Client Roles)

The two deliverables serve four different readers, and each one opens a specific
part first. Knowing this changes what must never be omitted — a number without its
caveat is fine for the analyst and actively misleading for the decision maker.

| Role | What they read first | What they decide | What must therefore never be missing |
|---|---|---|---|
| **Campaign owner / 运营** | 优化建议, then 人群 / 通道 / 内容 / 承接 in the attribution section | which node to change next and for whom | at least one concrete next action, with the affected audience named — "no anomaly" is not "no advice" |
| **Data analyst / 数据分析师** | 链路漏斗 in the report, Sheets 2-4 in the workbook | whether the funnel is complete and whether the rates are computed on the right denominators | the data-source mode, every degradation, and the raw rows behind each figure |
| **Solution engineer / 交付·售前** | 数据来源与置信度 line, then the funnel | whether this result is safe to put in front of the customer, and what to fix in the tracking plan first | the confidence statement, the precision-loss estimates, and an explicit list of what was unobservable |
| **Decision maker / 客户负责人** | 结论先行 (one line), then 问题定位 | whether to keep investing in this campaign or in this channel | the verdict must state which stages were unobservable, or "found no problem" reads as "no problem" |

Two rules follow from the table and are enforced by the renderer:

1. **The mode and confidence statement sit above the fold.** A mode B number is
   materially less precise than a mode A number; the reader must learn which they
   are holding before reading any figure.
2. **A caveat travels with its number.** `field_caveats` and `degradations` are
   rendered next to the affected metric, not collected in an appendix nobody opens.
   An analyst will find the appendix; a decision maker will not.

## Boundary Statement

This skill is NOT applicable when:

1. **The campaign must be created or edited** - use `gift-push-strategy` or
   `ae-engage`.
2. **The problem is that nothing was delivered** - diagnosing non-delivery
   (deliverability, channel throttling, token validity) is a different
   investigation from measuring delivered effect, and is out of scope here.
3. **A tracking plan must be designed** - use `ae-generate-tracking-plan`.
4. **Future performance must be predicted** - this skill reviews what already
   happened; it does not forecast. A campaign that has not run has nothing to
   measure.
5. **Mode B and no touchpoint events are tracked at all** - there is no data
   foundation. Close the tracking gap first (design the missing events with
   `ae-generate-tracking-plan`, then implement the instrumentation),
   then return.
6. **The customer will not describe the campaign or name the recovery events** -
   the intake contract is a hard gate in mode B. Without it there is nothing to
   query, and guessing would produce a plausible but wrong report.
7. **Fewer than 1000 users or a window shorter than 3 days** - the sample cannot
   support a decision-grade conclusion. The skill still runs and labels the
   result accordingly, but it must not be presented as decision-grade.
8. **The question is about non-touchpoint behaviour** - retention curves,
   monetisation modelling and acquisition attribution belong to other skills.

## Degradation Strategy

### Mode A

| Missing | Substitute | Precision loss |
|---|---|---|
| No A/B experiment configured | Before/after comparison or a matched-cohort quasi-experiment | ~20% |
| `+task_experiment_report` unusable | `+task_data_overview` plus a manually defined control group | ~25% |
| `view` not returned by the platform | Click-through uses `trigger` as denominator; flagged `degraded` | ~25% |
| No conversion event tracked | Click rate and next-day retention stand in | ~15% |
| Canvas node report returns `dataList: null` | `+flow_process_report` for an aggregate estimate | ~30% |
| `metricMap` empty on the task | Read the goal from `completionIndicatorDef` instead | none |

### Mode B

| Missing | Substitute | Precision loss |
|---|---|---|
| **No discriminating property** | Approximate the audience from the time window only | ~20% |
| No impression event | Start the funnel at the click; impression-to-click CTR unavailable | ~25% |
| No group property | Before/after quasi-experiment instead of a real A/B | ~25% |
| No conversion event | Click rate and next-day retention as proxies | ~20% |
| Overlapping campaigns in the same window | Isolate a second time by channel property, otherwise attribution is confounded | ~30% |
| Delivery and impression live only on the customer's side | The dimension is labelled "not visible from this data source" and skipped | no effect on conclusions |

The workbook never drops a sheet for a degradation. It records which dimension is
unavailable and why, so the deliverable is complete and readable rather than
apparently buggy.

### Minimum viable data

- **Mode A**: `project_id` + one of `task_id` / `flow_id` / `config_id` + a 3-day window
- **Mode B**: `project_id` + `click_event` + a 3-day window (+ `discriminator` for full precision)

If neither minimum is met, report `INSUFFICIENT_DATA` with the specific missing
item rather than producing a partial report.

## Field Type Validation

Every value entering the analysis crosses a trust boundary: it comes from the
platform's JSON envelope, from a third-party backend, or from a file a human filled
in by hand. The rule applied throughout is **guard at the boundary, once** — the
analysis layer may assume its inputs are well-typed.

The declared type of each field, and what happens when reality disagrees:

| Field | Declared type | Observed deviation | Handling |
|---|---|---|---|
| reporting envelope | `dict` | `list` / `str` / `None` after an upstream shape change | coerced to `{}` by `as_dict()`; a bare `.get()` would raise, and `(v or {})` does not help because a non-empty list is truthy |
| `dataList` | `list[dict]` | absent, `null`, or a dict instead of a list | non-list → treated as empty; a non-dict entry is skipped and logged, never raised — one bad record must not stop the report |
| entry `key` / `value` | `str` / numeric | missing key, `null` value | entry skipped and logged |
| numeric metric | `int` / `float` / numeric `str` | `None`, `""`, `"N/A"`, `NaN`, `Inf` | normalized to `0`; non-finite values are non-computable, not zero-loss |
| numeric metric (overflow) | `int` | `inf` persisted by a Python `json.dump` upstream | `OverflowError` is caught **explicitly** — `int(float('inf'))` raises that, not `ValueError`, and a missing branch tracebacks the whole run on its last step |
| timestamp | `int` (ms) or `int` (s) | string digits, seconds instead of ms | magnitude heuristic; an unparsable value returns `None` and the caller degrades to a dash — a date is never guessed |
| `tzOffset` | `int` hours | absent, string | absent → `None` → unparsable timestamp; never silently assumed to be UTC |
| `completionIndicatorDef` | `dict` | a JSON-encoded **string** | decoded before use |
| `expConfig` | `dict` | a JSON-encoded string, `null` | decoded; `enableExp` absent → treated as "no experiment" and no lift is claimed |
| `rate` | `float` in `[0, 1]` | ratio above `1.0` | impossible by construction (numerator ⊂ denominator) → reported as a missing-denominator anomaly, **not** as excellent performance |
| denominator | `int`/`float` > 0 | `0` or `null` | safe division returns `None`; the rate is omitted rather than printed as `inf` |
| `plan` / `planNum` | `int` | two units for one quantity across interfaces | both kept, and a `field_caveats` note is emitted **only when the values disagree** |
| `plan` / `actualTrigger` / `trigger` (mode B) | `int` | **unobtainable**, not zero | excluded from judgement; `.get(..., 0)` here is the single most misleading bug this skill can ship |
| `discriminator` | `str` | absent | run continues with a recorded precision loss; a query filter is never faked for 1.x, which would silently ignore it |
| `strategy_name` | `str` | empty, or a path separator | gate rejects; the value reaches a filename, so it is validated before use |

Two invariants hold the scheme together:

- **`None` and `0` are different answers.** `None` means "not observable"; `0` means
  "observed to be zero". Collapsing the two is what turns a missing event into a
  fabricated loss, so the analysis keeps them distinct and only the presentation
  layer renders `None` as a dash.
- **A guard never raises.** Except at the Step 0 gate, bad input degrades the result
  and is logged; it does not abort the run. A report that says "this dimension could
  not be measured" is worth more than no report.

`scripts/validate_intake.py` and the Step 0 gate enforce the same contract on the
human-supplied inputs; `scripts/validate_analysis.py` re-checks the shape of the
analysis after the fact, so a silently dropped block is caught rather than rendered
as an empty section.

## Verification

### Thresholds

| Metric | Threshold | Direction | Action |
|---|---|:---:|---|
| Dispatch success | 0.90 | below | red - channel configuration |
| Click-through | 0.03 | below | amber - content or timing |
| Unsubscribe rate | 0.02 | above | amber - frequency control |
| Experiment lift | 0.05 | below | amber - no significant effect |
| Experiment significance | 0.05 | above | amber - inconclusive |

### How a bleed point is chosen

For every rate below its benchmark, `recoverable = (benchmark - actual) * denominator`.
The stage with the largest recoverable headcount becomes the bleed point. Stages
downstream of a data break are excluded, and a campaign that clears every
benchmark is reported as having no bleed point rather than being assigned one.

### Priority order for issues

`broken data chain > benchmark miss > inconclusive experiment > content and timing > segment mismatch`

### Validation steps after an optimization

1. Record the baseline metrics from this run.
2. Re-run the same strategy with the same audience definition and window.
3. Compare the core metrics; treat a change above 5% with adequate sample as real.
4. Where a strict answer is needed, run a fresh A/B with the original strategy as the control.

When no baseline could be computed because nothing was returned, the report says
so and the first step becomes closing the data gap.

## Long-Term Monitoring Metrics

A single run answers "did this campaign work". It cannot answer "is this channel
getting worse", because that is a question about a *sequence* of runs. When the
customer asks for ongoing monitoring, this is what to track and what each movement
means.

### Cadence

| Cadence | Scope | Question it answers |
|---|---|---|
| **Per campaign** | the campaign just sent | did this one work, and what to change |
| **Weekly** | all campaigns sent in the window | is the channel's baseline drifting, and is fatigue appearing |
| **Monthly** | by channel and by audience segment | which channel or segment is decaying, and which is improving |

### The metric set

Track these five continuously. They are the same quantities the per-run report
already computes, so no new instrumentation is needed — only persistence.

| # | Metric | Definition | Watch for |
|---|---|---|---|
| 1 | **Delivery success rate** | dispatched / targeted | a step change downward is a channel or token-config problem, not a content problem |
| 2 | **Impression rate** | impression / dispatched | a falling impression rate with a stable dispatch rate points at the client-side receive path |
| 3 | **Click-through rate** | click / impression (degraded: click / dispatched) | the main fatigue signal; compare like-for-like denominators across runs |
| 4 | **Conversion rate** | conversion / click | the business-outcome signal; a click rate that holds while conversion falls points at the landing step, not the message |
| 5 | **Unsubscribe rate** | unsubscribes / dispatched | the frequency-control alarm; a sustained rise means the send cadence is too high for this audience |

Two derived indicators matter as much as the five raw ones:

- **Campaign-over-campaign delta** against the channel's own trailing baseline, not
  against a global average. A channel that always delivers 92% is not "under the
  95% benchmark" — it is stable, and calling it a problem trains the reader to
  ignore the alert.
- **Fatigue slope**: click-through rate regressed over the last 6-8 sends to the same
  segment. A negative slope with a stable content type is the earliest usable
  warning, and it is visible well before a single campaign looks bad.

### Reading the trend

| Pattern | Most likely cause | First check |
|---|---|---|
| Delivery flat, impression falling | client-side receive path, OS-level restrictions | the SDK version and platform mix between the two periods |
| Impression flat, click falling | content, send time, or genuine fatigue | compare by send hour and by content type before concluding fatigue |
| Click flat, conversion falling | landing page, offer, or price | the landing funnel, not the message |
| Everything falling together | audience quality, or a broader event-tracking gap | whether tracking itself degraded — check event volume independently |
| Unsubscribe rising with clicks holding | cadence too high | the number of sends per user per week |

### Guardrails

1. **Only compare runs that share a definition.** Event names, denominator,
   attribution window and audience definition must match, or the delta is a
   definition change wearing a performance costume.
2. **A mode B run and a mode A run are not a time series.** Their precision differs,
   so mixing them into one trend line makes mode switching look like performance
   movement. Track mode as a dimension.
3. **Never interpolate across a degraded run.** If a period's impression data was
   unobservable, that point is missing, not zero.
4. **Record the degraded periods.** A trend that silently drops its worst-data weeks
   is worse than one that shows the gaps.

## Global Conventions

### File layout

| Path | Purpose | Delivered |
|---|---|:---:|
| `{workspace}/tmp/` | intermediate JSON for every step | no |
| `{workspace}/output/` | the two final artifacts | yes |

### Status codes

`SUCCESS` continue. `EMPTY` continue but label the result as not measured.
`ERROR` attempt a documented degradation. `FATAL` stop and report the specific
missing item. Script exit codes: `0` for SUCCESS, `1` for FATAL.

Every gate prints `{"status": ..., "checks": [...]}` so the agent can branch on
structure rather than parsing prose.

### Language

Script output and reports are written in Chinese for the customer-facing
deliverable. This document and everything under `references/` are in English.

## Detailed Steps

Execution order — every step consumes the previous step's output, and a failing
gate stops the run at that point:

1. **Step 0 — pre-flight, mode detection, parameter freeze.** **IF any check exits 1 → FATAL**, report the named check and stop; **IF all exit 0 → proceed to Step 1**.
2. **Step 1 (a/b) — resolve the campaign object.** **IF no object carries send records → FATAL**, ask the user to disambiguate; **IF resolved → proceed to Step 2**.
3. **Step 2 (a/b) — fetch the raw reports.** **IF the overview block is missing → FATAL**; **IF only an optional block is missing → record a degradation and continue** to Step 3.
4. **Step 3 — six-dimension analysis.** **IF the gate exits 1 → FATAL**, fix the analysis before exporting; **IF exit 0 → proceed to Step 4**.
5. **Step 4 — export the workbook.** **IF the gate exits 1 → FATAL**; a thin sheet is labelled EMPTY and kept, never dropped.
6. **Step 5 — generate the report.** **IF the gate exits 1 → FATAL**; a `no_sensitive_leakage` failure must be fixed before delivery, never shipped with a note.
7. **Step 6 — post-flight cross-check.** **IF the two deliverables disagree → return to Step 3**; **IF they agree → the run is complete**.

### Step 0: Pre-flight, mode detection, parameters

> Procedure: `references/steps/00_preflight.md`

**Input:** `project_id` plus either a native object id or the campaign's event names
**Output:** `tmp/prereq.json`, `tmp/mode.json`, `tmp/params.json`
**Executor:** Orchestrator running scripts
**Validation gate:** three scripts, all must exit 0
**Failure handling:** any exit 1 -> FATAL, stop and report the failing check

**Interpreter**: any `python3` >= 3.8 can run every script here. Only one step
needs a third-party package - `export_detail_excel.py` needs `openpyxl` - and you
should not solve that by hard-coding a path to a virtualenv, because that path
exists on exactly one machine. Let the gate resolve it:

1. Run `check_prerequisites.py` with whatever `python3` is on `PATH`.
2. Read `context.resolved_python` from its output, or from the JSON it persists
   with `--out` (the step-0 command below writes `tmp/prereq.json`).
3. Use **that** path as `PY` for every later step, Step 4 in particular.

`check_prerequisites.py` resolves `openpyxl` in three stages: the current
interpreter, then any other interpreter it can find, and finally a **private
virtualenv it builds itself** under the user cache directory. A machine with
nothing but `python3` therefore still works - the skill installs its own
dependency rather than asking the user to fix their environment. Pass
`--no-install` to forbid that and receive a plain install command instead.

A running script cannot switch its own interpreter, so `PY` must be resolved
before the script is invoked.

**What Step 0 actually checks**, in two groups. The first group is about remote
authority and the interpreter; the second is about *local* permissions, and it
exists because both failure modes used to surface only after the data had
already been fetched:

| # | Check | Group | Fails as |
|---|---|---|---|
| 1 | `python_version` >= 3.8 | interpreter | FATAL |
| 2 | `ae_cli_binary` discoverable | interpreter | FATAL |
| 3 | `ae_cli_compat` - the binary is a 1.x or 6.x ae-cli | **capability** | FATAL || 4 | `ae_cli_auth` authenticated, reports active host | remote authority | FATAL |
| 5 | `ae_cli_roundtrip` - `+list_projects` answers | remote authority | ERROR |
| 6 | `openpyxl` reachable, bootstrapped when absent | interpreter | FATAL |
| 7 | `project_visible` - target id in the active host's list | remote authority | FATAL |
| 8 | `credential_store` - store writable **and** holds a credential for the active host | **local permission** | FATAL |
| 9 | `output_writable` - `tmp/` and `output/` creatable under `--workspace` | **local permission** | FATAL |
| 10 | `network_reachable` - probe against the active host | local network | ERROR |

Check 3 deserves its own note. The two generations advertise **disjoint top-level
domains**, and that is what makes the check honest: 1.x offers `engage` +
`analysis_common`, 6.x offers `capability` + `engage-task` + `analysis-meta`. So
a binary can answer `--version` and `auth status` perfectly while failing
literally every step, and a version *string* is not evidence either - the 6.x
binary on the author's machine reports `6.0.36` while the host expects
`6.1-agent-review-workflow.4`, and it drives the skill correctly all the same.
Two majors also coexist on real machines, and picking by path order alone lands
on the wrong one - so discovery prefers a binary whose domain list matches, this
check reports which generation it found, and it fails loudly when neither
matches, naming a compatible binary when one is present and `AE_CLI_PATH` as the
override.

Two details behind checks 8 and 9:

- ae-cli stores one encrypted credential per host under
  `<home>/.ae-cli/secure-tokens/<host>.enc.json`, with the port separator
  rewritten as `_` (so `http://ta.example.com:8993` becomes
  `ta.example.com_8993.enc.json`). `auth status` only speaks for the *active*
  host, so
  a project living on a host this machine never logged into passes check 3 and
  fails at fetch time. Check 7 closes that gap, and check 6 names the same
  possibility in its error text when other hosts have credentials. Switch host
  with `ae-cli config` - note that `auth login` does **not** accept `--host`;
  `--host` is a global option (`ae-cli --host <url> auth login`).
- The credential store must stay **writable**, not merely readable: the access
  token refreshes roughly every 2h and the refresh is what writes back. A
  read-only store (wrong ownership, restored backup, container bind-mount)
  produces a 401 partway through a long run. On Windows the writability probe is
  advisory rather than authoritative, since `os.access` cannot see NTFS ACLs;
  the real test happens when the store is first written to.

```bash
PY=<resolved interpreter>; S=<skill_dir>

$PY $S/scripts/check_prerequisites.py --project-id <PID> --workspace <WD> \
      --out tmp/prereq.json                                                # 10 checks, see below
$PY $S/scripts/detect_mode.py  --project-id <PID> \
      [--task-id <TID> | --flow-id <FID> | --config-id <CID>] \
      [--anchor-event <E>] [--click-event <E>] --out tmp/mode.json
$PY $S/scripts/validate_params.py --project-id <PID> --mode <A|B> \
      [--task-id <TID>] [--click-event <E>] --start-time <S> --end-time <E> \
      --strategy-name "<name>" --out tmp/params.json
```

Then branch: mode A continues to Step 1a, mode B to Step 1b.

### Step 1a: Identify the campaign object (mode A)

> Procedure: `references/steps/01_intake.md`

**Input:** `project_id`, optionally a campaign name rather than an id
**Output:** `tmp/target.json`
**Executor:** Orchestrator
**Validation gate:** the chosen object must carry `hasPushRecord=true`
**Failure handling:** no object with send records -> FATAL, report that the named campaign has never sent

```bash
ae-cli engage +task_list -p <PID> --req '{"pageNum":1,"pageSize":200}'
```

Filter on `hasPushRecord`. Read `completionIndicatorDef` to learn which event the
platform counts as the conversion goal, and `expConfig.enableExp` to learn whether
there is an experiment. Present candidate tasks to the user when the name is
ambiguous; do not pick one.

### Step 1b: Collect strategy and recovery events (mode B)

> Procedure: `references/steps/01_intake.md`

**Input:** whatever the user said about the campaign
**Output:** `tmp/intake.json`, `tmp/candidates.json`
**Executor:** Orchestrator, with script-assisted search
**Validation gate:** `scripts/validate_intake.py tmp/intake.json`
**Failure handling:** missing REQUIRED answer -> FATAL, ask the user for exactly
those items; missing `discriminator` -> continue and record the degradation

```bash
$PY $S/scripts/collect_intake.py --show --strategy-name "<name>"
$PY $S/scripts/resolve_events.py --project-id <PID> --kind events     --query push
$PY $S/scripts/resolve_events.py --project-id <PID> --kind properties --query strategy
$PY $S/scripts/resolve_events.py --project-id <PID> --kind clusters   --query <keyword>
# fill tmp/intake.json from the answers, then:
$PY $S/scripts/validate_intake.py tmp/intake.json
```

When the user cannot name an event, search and show candidates with their
descriptions. `references/intake_contract.md` has the question wording and the
resolution playbook.

### Step 2a: Fetch native Engage reports (mode A)

> Procedure: `references/steps/02_fetch.md`

**Input:** `tmp/mode.json`, `tmp/params.json`
**Output:** `tmp/raw_overview.json`, `tmp/raw_detail_time.json`, `tmp/raw_detail_instance.json`, `tmp/raw_exp_*.json`, `tmp/raw_tasklist.json`, `tmp/raw_meta.json`
**Executor:** Orchestrator running the script
**Validation gate:** `scripts/validate_raw_report.py --raw-dir tmp --mode A`
**Failure handling:** a missing optional block is recorded as a degradation and
the run continues; a missing overview block is FATAL

```bash
$PY $S/scripts/fetch_engage_reports.py --project-id <PID> --task-id <TID> \
      --start-time <S> --end-time <E> --out-dir tmp
```

### Step 2b: Build and run ad-hoc analysis (mode B)

> Procedure: `references/steps/02_fetch.md`

**Input:** `tmp/intake.json`
**Output:** `tmp/raw_overview.json`, `tmp/raw_detail_time.json`, `tmp/raw_event_meta.json`, `tmp/raw_event_rows.json`
**Executor:** Orchestrator running the script
**Validation gate:** `scripts/validate_raw_report.py --raw-dir tmp --mode B`
**Failure handling:** empty funnel rows -> EMPTY, confirm the event name and window
with the user before concluding that the campaign had no effect

```bash
$PY $S/scripts/fetch_event_analysis.py --project-id <PID> \
      --steps '[{"event":"ops_view","role":"view"},{"event":"ops_click","role":"click"},{"event":"shop_buy","role":"main"}]' \
      --time-range '{"mode":"custom","startTime":"<S>","endTime":"<E>"}' \
      --window-value 24 --window-unit hour --out-dir tmp
```

`--time-range` accepts either spelling of the start/end keys
(`startTime`/`endTime` or `start_time`/`end_time`) and is respelled for whichever
generation is installed - 1.x rejects the snake_case form and 6.x rejects the
camelCase one, so the choice is not ours to make.

This script is the fork's other half: it normalizes ad-hoc output into the mode-A
shape, which is what allows Steps 3 to 5 to run unmodified.

Three properties of the ad-hoc result are handled there, and each is a place
where a careless read produces a confident wrong number:

* **The funnel's step columns are not `index + 1`.** The engine interleaves a
  conversion column after every step but the first -
  `[Totals, Step1, Step2, Conv2, Step3, Conv3]` - so a 3-step funnel's third
  count sits at column **4**, and reading column 3 lands on `"85.99%"`. Measured
  for 2..5 steps; `resolve_step_columns()` reads the parenthesised step marker in
  the header, falls back to the `len(title) == 2 * steps` layout, and reports the
  step as *unknown* when neither reading agrees rather than reading a neighbour.
* **The summary row is identified by position, not by its caption.** The platform
  renders it in the caller's language - `Overview` on one call, `阶段汇总` on the
  next, on the same host with the same credentials - so `canonical_label()`
  relabels row 0 to the `total` token the downstream parsers already know.
* **A truncated result is not a complete one.** 6.x sets `has_more` on the
  synchronous preview, whose row budget is fixed. Every row returned is valid,
  they are simply not all of them, so it is recorded in `meta.truncated` and
  surfaces as a `结果完整性` degradation.

### Step 3: Six-dimension analysis

> Procedure: `references/steps/03_analyze.md`

**Input:** `tmp/raw_*.json` + `references/metric_definitions.md` + `references/benchmark_thresholds.md`
**Output:** `tmp/analysis.json`
**Executor:** Orchestrator running the script
**Validation gate:** `scripts/validate_analysis.py tmp/analysis.json`
**Failure handling:** gate exit 1 -> FATAL, fix the analysis before generating
deliverables; every metric zero -> continue but the report states that nothing
was measurable

```bash
$PY $S/scripts/analyze_effectiveness.py --raw-dir tmp --out tmp/analysis.json \
      --mode <A|B> [--task-id <TID>] --strategy-name "<name>"
```

`analysis.json` carries: `meta`, `metrics`, `funnel`, `rates`, `max_bleed`,
`data_break`, `timeline`, `experiment`, `issues`, `recommendations`,
`validation_plan`, `degradations`, `field_caveats`.

Two fields in `meta` exist so the two deliverables cannot disagree about the same
campaign, and both must survive any refactor of this step:

- `trigger_time` + `trigger_time_source` + `trigger_time_label`. `triggerTime` is
  empty whenever a campaign is cron-driven, so the value falls back to
  `startDate` (converted with the campaign's own `tzOffset`) and is labelled
  `（任务起始日）`. Reading `triggerTime` alone made the report print a date while
  the workbook printed a dash.
- `field_caveats`. The same business quantity can carry two units across
  interfaces - `task_list.planNum` counts sends, `task_data_overview.plan` counts
  users - and both are correct. Printing them side by side with no caveat reads
  as a ~100x discrepancy. A caveat is emitted only when the values actually
  disagree.

### Step 4: Export the detail workbook

> Procedure: `references/steps/04_export_excel.md`

**Input:** `tmp/analysis.json`, `tmp/raw_*.json`, `assets/detail_workbook_spec.md`
**Output:** `output/{strategy}_明细数据_{YYYYMMDD}.xlsx`
**Executor:** Orchestrator running the script
**Validation gate:** `scripts/validate_excel.py <xlsx>`
**Failure handling:** gate exit 1 -> FATAL; a thin sheet is EMPTY and is labelled
rather than dropped

```bash
$PY $S/scripts/export_detail_excel.py --analysis tmp/analysis.json --raw-dir tmp \
      --out-dir output --strategy-name "<name>"
```

### Step 5: Generate the analysis report

> Procedure: `references/steps/05_report.md`

**Input:** `tmp/analysis.json`, `assets/report_template.md`
**Output:** `output/{strategy}_效果分析报告_{YYYYMMDD}.md`
**Executor:** Orchestrator running the script
**Validation gate:** `scripts/validate_report.py <md>`, then `scripts/validate_outputs.py`
**Failure handling:** gate exit 1 -> FATAL; a `no_sensitive_leakage` failure must
be fixed before delivery, never delivered with a note

```bash
$PY $S/scripts/generate_report.py --analysis tmp/analysis.json --out-dir output \
      --strategy-name "<name>" --excel-name "<workbook filename>"
$PY $S/scripts/validate_outputs.py --analysis tmp/analysis.json \
      --excel <xlsx> --report <md>
```

### Step 6: Post-flight cross-check

> Procedure: `references/steps/06_validate.md`

Runs the combined gate once more and cross-checks the report against the workbook on trigger time, funnel numbers, plan volume, experiment claims and degradations. It is read-only by design: a deliverable that only passes after being hand-edited cannot be re-derived, so a mismatch sends the run back to Step 3 rather than patching the rendered Markdown.

## Output Contract

### Deliverable 1 - detail workbook

`output/{strategy}_明细数据_{YYYYMMDD}.xlsx`, seven sheets:

| # | Sheet | Content |
|---|---|---|
| 1 | 策略概览 | campaign identity, source mode, recovery events, attribution window, trigger time / rule, confidence statement, field caveats |
| 2 | 链路漏斗 | stage, count, stage conversion, cumulative conversion, drop count, drop rate, note |
| 3 | 维度明细 | cross-tabulation by channel / platform / language / node / property group |
| 4 | 时序趋势 | one row per period with every metric |
| 5 | 人群分层 | response by activity / payment tier / lifecycle / new vs returning |
| 6 | 策略与分组对比 | multi-strategy and A/B comparison, lift and significance as reported |
| 7 | 原始数据 | the flattened interface response plus the request parameters |

Positioning: land everything retrieved, at the finest available grain, without
filtering or premature aggregation. An unavailable dimension becomes an explained
row, never a deleted sheet.

### Deliverable 2 - analysis report

`output/{strategy}_效果分析报告_{YYYYMMDD}.md`, six sections:

| # | Section | Content |
|---|---|---|
| 1 | 结论先行 | verdict line, three ranked findings, recommended actions |
| 2 | 效果总览 | funnel table plus benchmark comparison with red/amber/green flags |
| 3 | 归因分析 | why the result is what it is - audience, content, timing, frequency, channel |
| 4 | 问题定位 | prioritised issues, each citing the sheet that evidences it |
| 5 | 优化建议 | one action per issue, each with a stated expected impact |
| 6 | 验证方案 | indicators with baseline and target, plus execution steps |

Hard requirements: the header states the data source mode; the confidence
statement lists every degradation with its estimated precision loss; every
conclusion cites a workbook sheet.

A confidence statement and a field caveat are different obligations and both are
mandatory when they apply. A degradation says *a measurement is weaker than it
looks*; a caveat says *two correct numbers are not comparable*. Neither errors
out on its own - the reader simply concludes something wrong - so the header
carries the caveat block whenever `analysis.json.field_caveats` is non-empty,
and it is never folded into the degradation table.

### Intermediate files

`tmp/` holds `mode.json`, `params.json`, `intake.json`, `candidates.json`,
`raw_*.json`, `analysis.json`. Not delivered. Remove after the run.

## 自我检查（引用 self-check skill）

> The shared `self-check` skill holds the general three-phase checklist; in
> this skill every automatable check below is implemented as a script under
> `scripts/`. Run the scripts rather than reading this as a manual list.

### Pre-flight

- #1 ae-cli installed and authenticated - `scripts/check_prerequisites.py`
- #3 `openpyxl` present, python >= 3.8 - `scripts/check_prerequisites.py`
- #5 `project_id` visible to the account - `scripts/check_prerequisites.py`
- #5 `~/.ae-cli` writable and holding a credential for the active host - `scripts/check_prerequisites.py`
- #5 `tmp/` and `output/` writable under the workspace - `scripts/check_prerequisites.py`
- #5 parameters complete and self-consistent - `scripts/validate_params.py`
- #6 the gate itself still rejects what it claims to - `scripts/selftest_gates.py`
- The check result is persisted to `tmp/prereq.json`, so the verdict can be audited after the run
- FAIL handling: red FAIL stops the run and reports the specific missing item

### Mid-flight

- #1 each intermediate file non-empty - the per-step gate scripts
- #2 payload carries at least one non-zero metric - `scripts/validate_raw_report.py`
- #2 window spans at least 3 days - `scripts/validate_raw_report.py`, `scripts/validate_intake.py`
- #6 analysis blocks coherent and bleed point benchmark-referenced - `scripts/validate_analysis.py`
- #6 workbook sheets present and populated - `scripts/validate_excel.py`
- FAIL handling: red FAIL is fixed before continuing; amber WARN is labelled and the run continues

### Post-flight

- #1 both artifacts exist and are non-trivial - `scripts/validate_report.py`, `scripts/validate_excel.py`
- #4 all six report sections and all seven sheets present - same gates
- #6 the report states its data source mode and confidence statement - `scripts/validate_report.py`
- #8 no credential, internal IP or absolute home path leaked - `scripts/validate_report.py`
- FAIL handling: fix before delivery; a hygiene failure is never delivered with a caveat

## 异常处理 / Fallback

| Situation | Handling |
|---|---|
| `ae-cli` not found | FATAL. The message lists every location searched. Install it, or pass `--ae-cli <path>` / set `$AE_CLI_PATH` to skip discovery |
| `openpyxl` missing | Normally self-healing: the gate builds a private virtualenv. FATAL only when that fails too (offline, no `venv` module, externally managed python) - the message then carries a platform-correct install command. Re-run Step 0 after fixing and use `context.resolved_python` as `PY` |
| credential store not writable | FATAL. Token refresh cannot persist; a long run dies with a 401 mid-fetch. Report the failure - do not try to chmod someone's home directory |
| Active host has no credential | FATAL. `auth status` only vouches for the active host. Either the project lives elsewhere (switch with `ae-cli config`) or that host was never logged in here (`ae-cli auth login`) |
| `tmp/` or `output/` not writable | FATAL. The workspace is read-only. This is caught at Step 0 on purpose - otherwise it surfaces at Step 4 with every fetch already spent |
| Not authenticated | FATAL. Triggered by a structured `authenticated: false`, not by matching log text, so a dead session cannot pass. The user runs `ae-cli auth login`; the skill does not attempt to log in |
| `project_id` invisible | FATAL. List accessible projects so the user can correct the id |
| Mode B intake incomplete | Ask for exactly the missing REQUIRED items, one consolidated question, then stop |
| Mode B finds no rows for the event chain | EMPTY. Check the event name, the window, and whether the client is still reporting, in that order. Do not report "no engagement" |
| Canvas report returns `dataList: null` | Treated as EMPTY, not an error. Recurs on sandbox projects where canvas records were never generated |
| Experiment report unavailable | Degrade to before/after and state the ~20% loss |
| All metrics zero | EMPTY. Report that nothing was measurable; do not present zero as poor performance |
| Report gate flags a leaked path | Rewrite the offending content before delivery |

Default tool priority: `ae-cli` first. A connector or a hand-rolled HTTP
call is a last resort, and only for an operation `ae-cli` cannot perform.

## 坑记录

| # | Pitfall | Impact | Resolution |
|---|---|---|---|
| 1 | Ranking the bleed point by absolute drop | Always points at impression-to-click, which loses 95%+ by nature of funnels, and is noise rather than insight | Rank by `(benchmark - actual) * denominator`; report no bleed point when everything clears the benchmark |
| 2 | Treating missing data as churn | A campaign whose platform never returned `view` reads as "100% of users churned at the impression stage" and would be reported as a catastrophe | `find_data_break()` identifies the first all-zero stage whose downstream is also all-zero, excludes it and its downstream from bleed ranking, and labels it "not returned" |
| 3 | Reporting the same problem twice | "Benchmark miss: dispatch success 80%" and "Channel issue: low dispatch success" appear as two issues | Categories already covered by the bleed point or the data break are skipped |
| 4 | Silently degrading when a parameter is missing | The report header shows blank channel, trigger time and conversion indicators with no warning | Read `tmp/raw_meta.json` as a fallback and warn explicitly; mode A only, since mode B has no platform object |
| 5 | `--fields` rejecting `aiRemark` | `analysis_meta +list_events --fields '["eventName","eventDesc","aiRemark"]'` fails even though `--help` advertises the field | Request only `eventName` and `eventDesc` (or `propName` and `propDesc`) |
| 6 | Soft errors hidden behind `ok: true` | List endpoints return `{"ok": true, "data": {"success": false}}` for a rejected query, so a naive check reads it as "no results" | `_ae.extract_items()` raises when `success` is false |
| 7 | Using `--flow_id` for canvas reports | Raises a NullPointerException | Use `--flow_uuid` (`<flowId>_<suffix>` from `+flow_list`) |
| 8 | Passing a compact or datetime date | `20260701` and `2026-07-01 00:00` are both rejected | Normalise to `yyyy-MM-dd`; `_ae.norm_date()` does it |
| 9 | Counting the summary row as a date | `detail_type=time` and the event builder both prepend a summary row, which inflates the day count and pollutes the trend sheet | The summary row is separated from the series and reported in sheet 1 instead. **Identify it by position, never by its caption**: the platform renders that caption in the caller's language and switches between calls on the same host (`Overview` / `阶段汇总`), so `canonical_label()` relabels row 0 to the `total` token the parsers know |
| 10 | `--request_id` treated as an async handle | Unnecessary polling logic gets built around it | `mcp_` + 32 lowercase hex, one call returns the result |
| 11 | Omitting `aggregation` in the event builder | Build fails | `aggregation` is required and only `user_count` is accepted; `count`, `uv` and `event_count` are rejected |
| 12 | Empty `--groups` and `--limit` argument mixing | `analysis_audience` takes `--limit`, while `analysis_meta` accepts `-l` | Use the long form for audience endpoints |
| 13 | Hand-assembling the workbook | Misaligned columns, undetectable without checking | Always generate through `export_detail_excel.py` |
| 14 | Reading the auth verdict from text | `auth status` reports a dead session as `{"authenticated": false}`, a payload containing none of the phrases a text match looks for, so the gate said SUCCESS while every later call returned HTTP 500 | Parse `data.authenticated` first; keep the text match only as a fallback for non-JSON output. Pinned by `selftest_gates.py` case `auth.authenticated_false_is_fatal` |
| 15 | Reading only stdout from ae-cli | On failure ae-cli writes its error envelope to stderr and leaves stdout empty, so the real reason (`HTTP error: 500 Server Error` from the analysis
gateway) is replaced by "returned empty output" | `_ae.run_ae()` falls back to parsing the stderr envelope; `unwrap_error()` then shapes the message |
| 16 | Assuming one host per machine | `auth status` only vouches for the *active* host, and credentials are stored per host, so a project on another host looks identical to a project that does not exist | `credential_store` checks for a credential of the active host; `project_visible` names the other known hosts when it fails |
| 17 | Treating a still-valid-looking gate as trustworthy | A gate is only as good as the cases it rejects, and both false negatives above shipped silently | `selftest_gates.py` pins the reject behaviour with fixtures; run it before publishing |
| 18 | Hard-coding the author's virtualenv as the interpreter | Works on exactly one machine. On any other, the check fails and names a path the recipient does not have - a FATAL that looks like a broken skill rather than a wrong assumption | Discover generically and report `context.resolved_python`; `_env.resolve_package()` even builds a private venv when nothing has openpyxl. Pinned by selftest case `port.no_author_specific_paths` |
| 19 | Two copies of the tool-discovery logic | `fetch_event_analysis.py` carried its own `find_ae_cli`/`run_ae`/`new_request_id`. The weaker copy - no stderr fallback, no soft-error handling - was the one that ran in mode B, and only one copy would get fixed | Discovery lives in `_env.py`, envelope handling in `_ae.py`; every other script imports them |
| 20 | Proving a task exists from the first page of `+task_list` | Projects hold 500+ tasks and the list is paged, so a valid low id sits past any fixed slice. A live campaign was reported as missing, and channel / trigger time / conversion indicator came out blank in the report | `_ae.find_task()` does a point lookup and then a **full paged scan**; `_ae.iter_tasks()` follows the cursor instead of stopping at page 1. Pinned by the `taskmeta.*` cases |
| 21 | Trusting an exit status for a *soft* error | `+task_detail` answers an unknown id with `ok: true` **and** `data.success: false`. Reading only the exit code turns "not found" into a false hit and sends the run down a path with no data | Read `data.success` before accepting a payload - the same rule the auth check applies to `authenticated` |
| 22 | Two scripts disagreeing on where the id lives | Step 2 writes `raw_meta.json` with the id nested under `object`; Step 3 read only the top level. The id was silently taken as absent and every header field came out blank - with a warning that blamed a file which existed and was correct | `analyze_effectiveness.py` accepts both shapes; pinned end to end by `taskmeta.analysis_reads_nested_object_id` |
| 23 | Assuming any `ae-cli` on the machine will do | The two generations advertise disjoint domain trees (`engage` + `analysis_common` vs `capability` + `engage-task` + `analysis-meta`), so a binary can pass `--version` and `auth status` and then fail every single step. Both coexist on real machines, so picking by path order lands on the wrong one - and a version *string* is no help either | `_env.detect_variant()` reads the advertised domains; `_ae.run_ae()` translates to whichever generation is present; discovery prefers a compatible binary and `check_prerequisites` reports `ae_cli_compat` FATAL when neither matches. Pinned by the `cli_compat` and `cmdtree` cases |
| 24 | A bare `ImportError` as the failure mode for a missing dependency | On a fresh machine the message is `ModuleNotFoundError: No module named 'openpyxl'`, which points nowhere - the package usually exists, just not for the interpreter that was started | `_env.die_missing_package()` names the interpreter in use, the one to use instead, and the install command |
| 25 | Reading `triggerTime` and nothing else | It is empty for every cron-driven campaign, and the two scripts disagreed about the same campaign: the report fell back to the range start and printed a date, the workbook printed `—`. A reader cannot tell "no trigger time" from "not read" | `parse_trigger_time()` falls back to `startDate` converted with the campaign's own `tzOffset`, and labels the value `（任务起始日）`; both renderers read `meta.trigger_time`, never the raw field. Pinned by the `meta.*` cases |
| 26 | Printing two correct numbers that count different units | `task_list.planNum` (sends) beside `task_data_overview.plan` (users) reads as a ~100x error, and nothing warns - the reader just concludes the data is broken | `build_field_caveats()` compares the two interfaces and emits a caveat block into both deliverables. A caveat is not a degradation: degradations say a measurement is weak, caveats say two measurements are not comparable, and the report keeps them in separate blocks |
| 27 | Reading funnel steps as `index + 1` | The result interleaves a conversion column after every step but the first (`[Totals, Step1, Step2, Conv2, Step3, Conv3]`), so a 4-step funnel's 4th count sits at column 6. The old code read `"85.99%"`, `int()` threw, and the stage silently reported **0** - a headline "nobody converted" that matched nothing in the data. Present on both generations, so no v6 comparison would have found it | `resolve_step_columns()` locates the steps from the header's parenthesised step marker, falls back to the `len(title) == 2 * steps` layout, and leaves a step *unknown* rather than reading a neighbour. Verified against a real project for 2..5 steps; pinned by `adhoc.funnel_reads_step3_count` |
| 28 | Sending one spelling of a shared field to both generations | The ad-hoc time range is camelCase for 1.x and snake_case for 6.x, and **neither accepts the other's** - the request is rejected, not normalised. The lifecycle id has the same shape problem: 1.x issues `mcp_<32 hex>` while 6.x matches `^cli_[0-9a-f]{32}$` | `_cmdtree.time_range_for()` respells per target and accepts either on the way in; `v6_request_id()` reprefixes, and drops an id it cannot respell (it is optional on 6.x) rather than sending a form the server refuses |
| 29 | Letting a truncated or unreadable result look complete | 6.x answers with `has_more` on the synchronous preview, and every row it does return is valid - so a short curve reads as a real drop in volume. The same goes for a column that cannot be resolved: "0 users" and "we could not read it" support opposite conclusions and must not share a value | `meta.truncated` and `meta.unmapped_steps` are recorded at fetch time and turned into `结果完整性` / `漏斗环节取值` degradations, so they land in the confidence statement on the same page as the conclusion |
| 30 | Reading an unavailable platform metric as `0` | Mode B has no `plan` / `actualTrigger` / `trigger` - those are platform-side delivery counts the customer's own backend never sends. `generate_report.py` read them with `.get('plan', 0)`, so the attribution section narrated "目标人群 0 人" and "通道层是主要损耗来源" - two conclusions with nothing behind them, and they contradicted the rate table two sections up, which correctly printed "数据不足" | The attribution layers guard on `is not None`: a missing delivery metric prints "不可得（客户后台侧，数数不可见）" instead of manufacturing a zero. This is the same unavailable-vs-zero distinction #29 makes for funnel columns |
| 31 | Dropping intake fields on the way to the report | Step 2b's contract says its input is `intake.json`, but `fetch_event_analysis.py` only consumed `--steps` / `--time-range`, so `channel` / `target_audience` / `discriminator` never reached `analysis.json` and the report header printed "触达渠道：—" for a channel the customer had told us | `fetch_event_analysis.py` reads `--intake` and copies those fields into `raw_event_meta.json`; `analyze_effectiveness.py` falls back to `event_meta.channel` / `event_meta.project_id` when the platform task metadata is absent (which is always the case in mode B) |
| 32 | Letting directory sort order pick the ae-cli generation | `find_ae_cli()` ranked candidates with `sorted()`, so `ae-cli-v1` sorted ahead of `workspace` under the managed runtime and discovery picked 1.x - contradicting the documented "prefers 6.x". Which generation runs decides whether anything works at all (#23) | Discovery now prefers a compatible binary, then breaks ties toward `detect_variant() == "v6"`. Pinned by the discovery self-test |
| 33 | Translating a command and dropping its pagination flags | The `CLI_FALLBACK` path forwarded only the command name and threw away `--offset` / `--limit`, so `+list_projects` returned page 1 (50 of 300) and any project past it was reported as "not visible" - a fake FATAL on a project that existed | The translation preserves pagination flags (both `--offset 50` and `--offset=50`) and `project_visible` / `ae_cli_roundtrip` now report the page count honestly (`page 1 of 300`) instead of implying the list is complete |
| 34 | Recording the discriminator without applying it | The intake's `discriminator` (`strategy_id` / `campaign`) was only copied into `raw_event_meta.json` for display, never turned into a query filter - so overlapping sends in the same window contaminated each other and the ~20% precision loss the contract promises to remove stayed in the result. Measured: injecting a second campaign's events raised the unfiltered funnel from 12000/240/48 to 12500/340/68, while the filter kept it at 12000/240/48 | `_cmdtree.discriminator_filter(disc, variant)` builds a 6.x global `FilterRequest` (`field` + `operator:"eq"` + `values`) and `fetch_event_analysis.py` injects it into `funnel.filters` and the event model's top-level `filters`. 1.x *silently ignores* `filters` (its QP uses `filts`), so the function returns `None` there and the run records `discriminator_applied: false` + a "not applied" note instead of fake-filtering. `analyze_effectiveness.build_degradations` now states a missing or unapplied discriminator as a ~20% degradation, and the report header prints the isolation status |
| 35 | A campaign with no A/B experiment had no self-test coverage | The no-experiment path (Engage task without a group split) *was* implemented - `task_experiment_report` is optional and non-fatal, `parse_experiment` returns `None` when both overview and detail are empty, `build_degradations` records an "AB 实验组" ~20% degradation, and the report skips the experiment section - but none of it was pinned in `selftest_gates.py`, so a regression that fabricated a control/experiment comparison (or silently dropped the degradation) would have shipped green | `t_experiment()` pins 10 cases: `parse_experiment` returns `None` on empty payload; roles map 1=control/2=experiment; verdict derives from lift+significance+win; a missing experiment is a mode-A-worded "AB 实验组" degradation; a present-but-insignificant one is the lighter "实验显著性数据" degradation (not "AB 实验组"); a present-and-significant one is silent. Reverse-verified: faking an empty dict and corrupting the wording each turn their cases red |
| 36 | A "pass" verdict read as covering the whole link when it only saw the observable part | `overall_verdict` graded on `issues` alone, which only holds stages that *have* data - in mode B the audience/channel layers are unobservable, so a run whose real fault was "the push never got delivered" would still print "🟡 基本达标" with the misleading word "链路完整", and a busy reader scanning only 结论先行 sees "good enough, tweak the copy" while the true problem sits upstream | `_material_degradations()` (loss ≠ 「不影响结论」) gates a coverage hedge: when real degradations exist, `overall_verdict` appends "本判定仅覆盖可观测环节，未观测项（…）不参与判定，无法排除其掩盖问题的可能" and drops the misleading "链路完整". `t_verdict()` pins 6 cases, reverse-verified (treating every degradation as material, and dropping the qualifier, each turn their cases red) |
| 37 | Parsing external JSON with bare `.get()` and direct indexing | Every `raw_*.json` comes from an API response or a hand-prepared file, so the parse layer is the one place a malformed payload actually lands. 26 of 73 crash-harness fixtures produced a Python traceback instead of a diagnosis - `'list' object has no attribute 'get'`, `KeyError: 'key'`, `OverflowError: cannot convert float infinity to integer` - and a traceback is not a report: the reader sees a stack dump and cannot tell a data problem from a tool problem | Type guards at every level: `as_dict()` normalises non-dict to `{}`, `parse_overview` / `parse_time_series` / `parse_instances` / `parse_experiment` / `parse_conversion_indicators` / `get_task_meta` check `isinstance` before descending and skip (with a log) a record they cannot read, and `to_int()` catches `OverflowError` alongside `TypeError`/`ValueError` (it is `int(float('inf'))` that raises it, not `ValueError`). Result: 0 CRASH / 0 WRONG across the 73-case dual-mode harness |
| 38 | Computing a whole-person count with `int()` | `int((0.03 - 0.02) * 12000)` is `int(119.999… )` = **119**, so a headline "可挽回人数" was silently one short of the arithmetic the same sentence just showed the reader | `round()` instead of `int()`. Caught only because the semantic harness recomputed the expectation independently instead of re-using the script's own output |
| 39 | A physically impossible rate read as a healthy one | `click=500 / view=100` is a 500% click-through rate - it means the **denominator event was never reported**. Nothing in the pipeline objected: the rate table graded it `🟢 正常`, and `overall_verdict` printed "✅ 效果良好，各环节均在基准线内". An upstream tracking gap was thus presented as "the content performed superbly", and every downstream conclusion inherited it | `build_rates` flags `val > 1.0` as `🔴 数据异常（比率超过 100%）`, `build_diagnosis` raises a priority-1 「数据一致性」issue explaining the likely missing denominator event, and `overall_verdict` short-circuits to "⚠️ 需观察（数据可信度不足）". Pinned by the `boundary.impossible_ratio.*` cases; reverse-verified (removing the issue flips the verdict back to 效果良好) |
| 40 | A benchmark entry with no implementation behind it | `BENCHMARKS` declared 退订率 but `RATE_DEFS` never produced that rate, so the guard could never fire - a dead configuration that reads as "we check unsubscribe rate" while checking nothing | Removed the entry and commented that the two lists must stay in sync. The semantic harness now asserts no `BENCHMARKS` name is absent from `RATE_DEFS` (`polarity.no_dead_benchmark_entry`), so the next dead entry fails the suite |
| 41 | Escaping the field you thought carried external text, not every field that does | Only `meta` was HTML-escaped, on the assumption that external strings (strategy name / channel / event name / discriminator) live there. They do not: the analysis layer interpolates `discriminator.property` into the **degradations** wording, which is emitted as a Markdown table row. Feeding `<img src=x onerror=alert(1)>\|evil` as that property put live inline HTML into the delivered report **and** split the 3-column confidence table into 4 columns - the second half is invisible in raw review because the row still "looks" fine | `render()` now runs `esc_deep()` over the whole analysis structure (which is what "every field" means) and a `tcell()` helper escapes `\|` / newlines on every table-cell emission (funnel, rates, experiment groups, degradations, issues, validation indicators). `esc()` also covers `&`. The filename path still reads the raw meta so filenames stay clean. Verified: 0 raw `<` in an injected report, and every table's logical column count is unchanged; normal reports contain 0 escape entities, i.e. the escape is a no-op on legitimate text |
| 42 | Leaving language mixed in a Chinese deliverable | The report shipped `7 个 sheet`, `其它 campaign 的事件`, and the validation table header `indicators` - readable to the author, off-key for the customer receiving it, and easy to miss because each instance is one word inside a sentence | `7 个工作表` / `其它投放活动` / `基线指标表`. The same sweep removed the copy that said the bleed point twice (核心发现 already stated it, the 异常 list repeated it) and turned the internal comparison operators into Chinese (`低于基准`, `超过 5%`, full-width `＞`) - which also avoids emitting `&lt;` into the Markdown source now that #41 escapes everything |
