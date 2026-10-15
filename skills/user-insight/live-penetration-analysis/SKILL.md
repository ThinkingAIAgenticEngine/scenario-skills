---
name: live-penetration-analysis
description: Diagnose root causes of live-stream / voice-room / party-room room-entry penetration-rate (entry UV ÷ DAU) declines or trend shifts, product-agnostic. Parameterize the product config first, then run the Part 0-6 workflow (aggregate validation → dimension breakdown → cross drill-down → evidence-backed, confidence-scored root-cause conclusions with High/Medium/Low labels and P0/P1/P2 actions). Use when users report or ask about live penetration, penetration drop, entry UV, entry rate, or entry-rate trend changes. Do NOT use for gift/recharge monetization, pay conversion, product category, short-video, ad, or any other penetration metric.
version: 2.3.1
updated: 2026-09-20
compatibility: claude-code, workbuddy
---

# Live-Stream Penetration Decline / Trend Root-Cause Diagnosis (Universal Edition)

## Preflight: Environment & Execution Gate (MUST)

Before Part 0, verify the execution environment in order:

1. `ae-cli config current` succeeds and the intended account/session is active.
2. `python3`, `scripts/ae_query.sh`, and `scripts/dim_analyzer.py` are available.
3. The confirmed `project_id` is accessible to the current session.
4. **Bash shell required** — scripts use bash syntax (heredoc, `set -uo pipefail`); Windows users need WSL or Git Bash.

> **【MUST·`analysis-meta event list` bug fallback】** On ae-cli ≥6.0.47, `analysis-meta event list` may fail with `INVALID_CAPABILITY_INPUT`. Fallback: `ae-cli capability run metadata.event.list --input '{"project_id":<pid>,"queries":[...],"limit":200}'`. Same for `metadata.event.get` (`--input '{"project_id":<pid>,"event_name":"<name>"}'`, returns `data.event` with `event_props`). Do NOT abort event discovery on the CLI bug.

**If CLI/login/permission/query execution fails at any point:**
- Report the exact failed capability and the available error text to the user.
- Ask the user to restore access or provide the missing input.
- **Do NOT infer, fabricate, or reuse data-backed conclusions for the failed window.**
- Stop at the failed gate; continue only after the failure is resolved.

## Result Management: Multi-Round Progressive Discipline (MUST)

> **Incremental by default; overriding requires explicit authorization.** Before a new analysis round, if a prior round's conclusion exists, re-verify the prior root cause's **suspect dimension** within this round's Part 3/4 mandatory checks. Only when the user says "recompute / redo / overturn" may you do a full rerun. Read prior conclusion from **current conversation context**; no disk persistence.

Two non-negotiable disciplines:

1. **Trend acceleration forces re-verification (MUST)**: if key metric's change magnitude ≥ `TREND_ACCEL_RATIO` (see judgment-parameters.md) the previous window, do NOT reuse prior root-cause type; run the new window's full drill-down. Full rule: `governance.md` HARD RULE #13.
2. **【MUST·incremental recompute all dimensions]**: Incremental does NOT mean "only suspect dimensions + aggregate". In every incremental window, every dimension group's daily series must be fully recomputed and individually run through the trend test. Do NOT run only the aggregate + prior suspect dimension series.

> **"Key metric" definition**: the suspect-dimension metric that entered root-cause attribution in the prior round (e.g., new-user penetration), **NOT the aggregate penetration**. A flat aggregate does NOT mean no acceleration.

---

## Quick Reference (user phrasing → analysis mode)

| User phrasing | Analysis mode | Key default |
|---------|---------|---------|
| "Why did penetration drop" / "entry rate fell" | Standard analysis | Run Part 1 aggregate validation first, then full dimension breakdown |
| "Look at last 7 days" / "supplement on top of this" | **Incremental analysis** | Incremental by default, read prior conclusion, recompute all dimensions |
| "Before/after update comparison" / "did the event work" | **Comparison mode** | See `references/comparison-mode.md` |
| "Which entry is dropping" / "recommend vs follow page" | Funnel entry breakdown | Focus on `{enter_source_field}` |
| "Are streamers not streaming" / "supply problem" | Supply-side analysis | Read `indicators.md` supply side + supply-demand linkage |
| "Is it a version problem" | Version diagnosis | Read `version-diagnosis.md`; do NOT blurt "migration is normal" |
| "Recompute" / "overturn prior conclusion" | Full rerun | The only signal authorizing overwriting history |

### Comparison Mode

When the user mentions "before/after update", "event effect", "this week vs last week", "did the redesign improve", enter comparison mode — full Period A/B procedure in `references/comparison-mode.md`.

---

## Part 0: Product Config + Required Info Collection (Prerequisite, MUST)

**This skill is product-agnostic. Before any analysis, you MUST complete the product config** — pin down the target product's event tables, event names, and field mappings; all subsequent SQL/caliber reads from the config.

### 0.1 Required info collection (first step is to ASK, never self-assume)

> **【MUST·ask before querying】** Confirm 3 items via AskUserQuestion before any query: ① project_id ② time range ③ event caliber (entry/DAU/source field). Do NOT self-list projects, search events, or guess which project is the live one. Only when the user explicitly asks "help me find the project" may you list candidates for the user to choose — do NOT self-select. Full rule: `governance.md` HARD RULE #0.

### 0.2 Product config population

- **Config template**: `references/product-config-template.md` (all config items + fill checklist)
- **Filled example**: `references/product-config-example.md` (LesPark real values, only as "how to fill" reference, **NOT defaults**)

**Config population method**:
1. First use: request config items from the user, or extract from the product's tracking-plan doc, fill into template and **persist as `configs/product-config-<product>.md`**.
2. Subsequent use: read the persisted config and reuse; do not re-request.
3. Multiple products: one config per product; switch product = switch config.

**Config item confirmation (after user provides project ID)**: use `ae-cli analysis-meta event list --project-id <pid>` (or the capability-gateway fallback in Preflight) to list all events, **present entry-event candidates (e.g., `enter_liveroom`/`room_enter`) and DAU-event candidates (e.g., `ta_app_start`/`login`) for the user to confirm**; for the entry-source field, use `ae-cli analysis-meta event get --project-id <pid> --event-name <name>` to inspect event properties then confirm. **Event names are finalized only by user confirmation; do NOT guess.**

> **【MUST·composite entry event — verify behavior filter】** If the entry event has a discriminator field (e.g., `bhv_type`/`behavior_type`/`event_type` distinguishing `exposure`/`click`/`exit`), you MUST `GROUP BY` that field to confirm which value means "enter room", then record it as `enter_event_filter`. Using the whole composite event inflates penetration by orders of magnitude. The field name differs per product — read from event properties, do NOT assume.

> **【MUST·`last_day_count` is PV, not UV】** Do NOT infer penetration magnitude from `metadata.event.list`'s `last_day_count` — it is event-row count (PV), not distinct users. Judge magnitude ONLY by `COUNT(DISTINCT "#user_id")` over the analysis window.

> **【MUST·user skips event-caliber confirmation】** If the user skips the AskUserQuestion on event caliber: ① state your assumed default in plain text + proceed with caveat ("assumed, unconfirmed" label carried into conclusion), or ② stop and wait. Silently substituting your own pick and presenting results as confirmed = violation. Do NOT re-ask in a loop.

**Running analysis without config = violation. Guessing event names = violation.** All `{placeholder}` (`{dau_event}`/`{enter_event}`/`{enter_source_field}` etc.) must be read and substituted from the product config; do NOT default.

---

## Part 1: Aggregate Trend + Data Validation Layer

**Goal**: first eliminate false problems, then judge the inflection shape.

### 1.1 Trend validation

Pull the last 28 days at day granularity: DAU, entry UV, penetration — three lines. Cliff-like drop (1–3 days) → check event-driven factors first; slow decline (2+ weeks) → structural problem. Record the decline start date.

### 1.2 Tracking validation

Compare `{dau_event}`/`{enter_event}` totals vs the same period last week; a drop >30% → check data loss first. Hit → output "false decline" conclusion and stop, with evidence.

### 1.3 User-composition validation

Split penetration by guest (`#account_id` empty) vs registered user; for bot suspicion, filter by black/gray-list fields and recompute. If the drop disappears after excluding abnormal users → false decline.

### 1.4 Aggregate series + inflection judgment

1. Query `{enter_event}` UV, `{enter_event_2}` UV (if configured), `{dau_event}` DAU daily series
2. Compute daily penetration, mark inflections. **Inflection dual threshold**: see `judgment-parameters.md` §1 (sole authority — do NOT copy numbers here). For weekly granularity, aggregate to weekly mean/weekly total
3. Judge whether DAU fluctuation is an illusion (see `judgment-parameters.md` §1 `DAU_FLUCT_THRESHOLD` / `DAU_CONSECUTIVE_DECLINE_DAYS`: below threshold with no consecutive decline → penetration change is mostly numerator-driven; consecutive decline ≥ the day count → mark "downward trend, needs attention")
4. If dual entry events configured, compute the two events' difference to check caliber consistency

SQL/event templates: `references/query-templates.md` "Aggregate trend queries".

### 1.5 Trend-shape judgment (after Part 1, before Part 2)

**Granularity lock (MUST)**: once granularity is confirmed (daily/weekly), it is locked for the whole run — no step may silently down/up-sample. Under daily, do NOT fold back to weekly for trend comparison. Full rule: `governance.md` HARD RULE #14.

| Shape | Judgment (daily) | Judgment (weekly) | Follow-up flow |
|------|---------|---------|---------|
| **A - decline inflection** | Downward inflection (dual threshold), clear downward trend | Weekly decline ≥ `TREND_INFLECTION_PP` (see judgment-parameters.md) | Part 4 "deteriorating-dimension drill-down"; Part 5 types 1-4 |
| **B - no inflection, small fluctuation** | No inflection or single-day noise only | Inflection below `TREND_INFLECTION_PP`, change below it | Part 4 "significant-change dimension drill-down" (bidirectional); Part 5 adds type 5 |
| **C - rise inflection** | Upward inflection, clear upward trend | Rise ≥ `TREND_INFLECTION_PP` | Part 4 "improvement-driver dimension" drill-down; Part 5 type 5 |

**Key distinction (MUST): "between-group difference" ≠ "time-trend fluctuation"**. Between-group difference is a static cross-section feature; only a group's own rate changing over time counts as fluctuation. Inflection/shape/type judgments target only time-trend change. Full rule + falsification steps: `governance.md` HARD RULE #9.

**Shape B/C type 5 (version-iteration transition period)**: only when the aggregate truly has an inflection (A/C) AND the "version-difference diagnosis" has falsified version defect may this conclusion be drawn. **No aggregate inflection (B) → skip type 5 entirely, output "no fluctuation" directly.**

---

## Part 2: Phenomenon Layering + Funnel Breakdown

**Goal**: locate "who, when, where" is dropping; is the bottleneck insufficient reach or poor retention.

### 2.1 Phenomenon layering (four dimensions, take the 2 combinations with the largest drop contribution)

| Dimension | Split key | Data source | Output example |
|------|--------|---------|---------|
| User layering | New (registered ≤30d) / old / returning user | `{new_user_field}` + `{dau_event}` | "80% of the drop is from old users" |
| Channel layering | Registration/source channel | `{channel_field}` | "a paid channel's new-user penetration is low" |
| Time layering | Hour granularity, prime-time vs off-prime | event time + `{enter_event}` | "only prime time dropped" |
| Version layering | APP version | `#app_version` | "new version's penetration is low = version problem" |

**Judgment**: a dimension contributing >50% of the drop may converge the scope early.

### 2.2 Funnel breakdown (exposure → entry → stay → interaction)

The full funnel chart, exposure-stage CTR boundary, supply-side breakdown, environment-layer breakdown, root-cause verification methods, and the high-frequency root-cause library (evidence chain) — **all in `references/indicators.md`**. Core conclusions:

- Entry rate: `{enter_event}` ÷ DAU, split by `{enter_source_field}` to find entry-level differences
- Quick-exit rate rising → "content/matching" problem; entry volume dropping → "reach" problem
- CTR caliber: most products "tap card = enter room", approximate with "exposure → entry" conversion; if there's a "tapped but not entered" intermediate state, add a click event

---

## Part 3: Multi-Dimension Breakdown (at confirmed granularity, not first/last comparison)

Split numerator UV and denominator DAU by dimension for the analysis window. **Each dimension must query the full window's daily data; do NOT query only first and last days.**

> **Full-breakdown hard requirement (MUST)**: all dimensions (including entry-source) must be **queried all at once, completely** before entering Part 4. The phrase "all/every dimension" may only be used after every dimension has been queried and passed anomaly judgment. Full rule: `governance.md` HARD RULE #16.

Dimension split field table: `references/indicators.md` "Dimension breakdown fields".

**Key requirements**:
- **Complete definition of "entry-source breakdown done" (MUST)**: satisfy both (a) **tracking check** (null-rate changes ≥ `NULL_RATE_DELTA_THRESHOLD` day over day, see judgment-parameters.md); (b) **business breakdown** (non-null part: each entry's **daily penetration series + trend inflection judgment**). TOP volume distribution alone ≠ done (it's a static cross-section, not a daily trend).
- Entry-source dimension penetration uses **aggregate DAU as denominator** (DAU has no such property).

**Execution checklist (AMA-3)**: output the "all-dimension breakdown status table" verbatim after Part 3 queries (table + ✓/✗ rule + Part 4 pre-gate) — full template in `references/output-templates.md` §1.

**Anomaly-dimension judgment checklist (AMA-2)**: write all three checks explicitly as "checked ✓: <explanation>" — full template in `references/output-templates.md` §2.

> **【MUST·anomaly-dimension candidate list — carry suspect-level distinction】** Distinguish: ① **True trend change (suspect)**: intra-group rate deviates from aggregate/other groups (magnitude ~2×+, opposite direction, cliff jump); ② **Follows aggregate (non-suspect)**: all groups same-direction, comparable magnitude (±~1pp), passive result of denominator dilution. A single group underperforming aggregate by ≥ `SUSPECT_DEVIATION_THRESHOLD` (see judgment-parameters.md) → suspect bucket.

SQL/event templates: `references/query-templates.md` "Multi-dimension breakdown queries".

---

## Part 4: Anomaly-Dimension Cross Drill-Down

**Step 1: single-dimension horizontal comparison + anomaly judgment (uniform, no per-dimension exception)**

Judge each Part 3 dimension independently; the standard is uniform across all dimensions, exactly one:

> **Anomaly judgment: does the intra-group rate have "time-trend change".** Look at the full N-day series movement (daily inflection / consecutive rise or fall / V-shape / inverted-U), **not between-group difference, not first/last difference**. Threshold is **uniform** using the dual threshold. For each dimension output "anomalous" or "normal", list anomalous dimensions → step 2. Between-group difference does NOT enter anomaly judgment. Full rule: `governance.md` HARD RULE #9.

> **【MUST·anomaly judgment must carry sample-size confidence】** Label judgment confidence per `judgment-parameters.md` §2 (sample-size tiers `SAMPLE_CONFIDENCE_TIERS`). Low/Very Low anomalies labeled "pending verification", cannot be root cause; Very Low listed as data only.

**Step 2: cross drill-down on every anomalous dimension (no fixed combination, full traversal)**

Every anomalous dimension found in step 1 is a "suspect bucket" — **each must be drilled**, not just the one with the largest change.

**Drill-down combination generation rule (no preset mapping)**: for each suspect dimension X, candidates = `X × {all other still-splittable dimensions}` — the **full set**, listed and executed one by one, no preset default direction.

> **Mandatory artifact instruction (AMA-4)**: in step 2a, when quoting scope you MUST explicitly list the full candidate-combination list + combination count; after execution report back item by item ("executed" or "user reduced"). **Do NOT do a subset while implying the full set.**

**Drill-down is recursive (MUST)**: each "changed sub-combination" whose intra-group rate still shows significant trend becomes a new suspect bucket to continue drilling, until the intra-group rate no longer diverges or an atomic dimension is reached. Do NOT conclude after a single level. Full stop conditions: `governance.md` HARD RULE #11.

#### Step 2a: main agent confirms drill-down scope with the user (MUST, do NOT delegate to sub-agent)

Sub-agents cannot call AskUserQuestion. **Execution order (irreversible; three steps in one reply)**: ① print candidate-combination list (numbered + count) → ② print MUST phrasing → ③ call AskUserQuestion. List format, MUST phrasing template, AskUserQuestion constraints: **AMA-5** (`governance.md`); `multiSelect: true`. Do NOT ask "which suspect dimension to drill" (decided in step 1b).

#### Step 2b: execute cross drill-down queries (may delegate to sub-agent)

Cross drill-down SQL templates: `references/query-templates.md` "Cross drill-down queries" (generic two-dimension GROUP BY, replace dimension names; no suspect-dimension-specific SQL).

**Cross drill-down judgment logic (stop on match)**:
1. **Whole-dimension problem**: all groups within the suspect bucket have low intra-group rates (below mean ≥ `VERSION_DEFECT_THRESHOLD`) → the dimension is a whole-dimension problem.
2. **Single-subgroup problem**: only a few groups significantly low (below mean ≥ `SUBGROUP_DEFECT_THRESHOLD`) → root cause concentrated in these subgroups, **continue drilling**.
3. **Structural dilution**: each group's penetration unchanged, but low-penetration groups' DAU share rose.

> **【MUST·whole-dimension early convergence】** May converge early if suspect dimension shows "all groups in sync" across the required orthogonal-split count AND (no subgroup opposite-direction or over-magnitude; tracking anomaly ruled out). Do NOT skip on grounds of "aggregate flat". Full rule: `governance.md` HARD RULE #11.

> **【MUST·convergence has granularity boundary】** Early convergence is only valid within the prior round's time window; do NOT inherit across windows. If an incremental round's shorter window shows single-day big jump or first/last ≥ `VERSION_DEFECT_THRESHOLD` (see judgment-parameters.md) on the suspect dimension, re-run suspect × remaining dimensions cross drill-down (at minimum suspect × version and suspect × country).

> **Final judgment of structural migration vs version defect converges to `references/version-diagnosis.md`.** This step is only responsible for "locate anomaly dimension + full-traversal cross drill-down + identify changed sub-combination"; no final characterization.

**Notes**:
- Cross drill-down only needs the primary event
- Cross drill-down DAU split: change `$part_event` to `{dau_event}`
- **As long as step 1 has any anomaly dimension, you MUST drill down**, do NOT skip on grounds of "aggregate flat"

**First-round no-anomaly proactive drill-down exit (MUST)**: if step 1 confirms "no dimension's intra-group rate has time-trend change", **do NOT close directly with "no fluctuation"**; first present the first-round full-dimension detail to the user and proactively ask:

> "The first round found no intra-group time-trend change in any dimension. Do you still want to cross-drill by some dimension (e.g., in a business direction you care about)? Or end here and record the conclusion as 'no fluctuation'?"
>
> Candidates specified by the user or checked from all splittable dimensions, **no preset, no recommendation**. Continue → step 2b; end → Part 5 closing as "no fluctuation".

---

## Part 5: Root-Cause Judgment

### 5.1 Tracking fault vs real business (types 1-5)

| Type | Judgment condition |
|------|----------|
| 1. Real business fluctuation | Both events drop in sync, DAU stable, a dimension's penetration systematically low and expanding/replacing |
| 2. Second-event tracking problem | Second event vs primary event difference jumps suddenly, single event anomaly |
| 3. Primary-event property anomaly | UV normal but property null-rate jumps (`{enter_source_field}` first/last-day null-rate change ≥`NULL_RATE_DELTA_THRESHOLD`) |
| 4. Structural dilution | Low-penetration group share rises but each group's penetration did not worsen. Subtypes 4a low-penetration share up / 4b early-bird → full rollout dilution / 4c high-penetration shrink |
| 5. Healthy fluctuation / version-iteration transition | No tracking anomaly, both events in sync, a dimension in new-old handover rollout, each group's penetration regressing to mean as rollout progresses (shape B/C only). **Only after version-difference diagnosis falsifies version defect; otherwise switch to version defect** |

**Residual-signal check (MUST, before 5.1 judgment)**: re-verify the suspect dimension's intra-group rate by the next un-split dimension, confirming no "opposite direction / far-exceeding-magnitude" subgroup. If present, attribution is invalid — return to Part 4. "Aggregate rate flat" ≠ "intra-group rates flat". Full rule: `governance.md` HARD RULE #12.

**"No fluctuation" precondition (MUST)**: only when Part 4 confirms "no dimension's intra-group rate has time-trend change" AND the user has explicitly waived, may you output "no fluctuation".

### 5.2 Supply side + environment layer + root-cause library

Supply-side breakdown, environment-layer breakdown, root-cause verification methods, and **the high-frequency root-cause library (evidence-chain judgment, none missing)** — all in `references/indicators.md`.

> **【MUST·root-cause library evidence chain (HARD RULE #18)】** Must hit **all** indicators in `indicators.md` "high-frequency root-cause library" evidence combination. Judging "supply shrinking" from just "online room count dropped" = violation.

> **【MUST·root-cause confidence labeling】** Label confidence (High/Medium/Low) per `judgment-parameters.md` §2.2, format `supply shrinking [High] + algorithm match failure [Medium]`.

### 5.3 Version-difference diagnosis

When Part 4 locates "version" as a suspect dimension, or the trend shape points to "version handover", **read `references/version-diagnosis.md`** to distinguish "structural migration" vs "version defect". Do NOT directly output "version migration is normal".

---

## Part 6: Conclusion & Recommendations

This part outputs the analysis conclusion with five fixed elements:

1. **Inflection location**: date + decline magnitude
2. **Root-cause judgment**: one of types 1-5 or mixed (see Part 5)
3. **Confirmed caliber**: key calibers used this round (events, dimensions, thresholds, control group, product config), for next-round incremental reuse
4. **Prioritized actions**: P0/P1/P2
5. **Remaining to-do**: unqueried fields, assumptions to verify, info needed from user

Write the conclusion directly in the reply; no need to persist. In multi-round progression, obey the "Result Management" iron rule: incremental by default, override requires explicit authorization.

> **【MUST·update report on incremental rounds】** If a prior round delivered an HTML report, sync the new window's dimension-breakdown results into it (add/update cards). Check item-by-item that every dimension has a corresponding card.

### Conclusion ending fixed format (proactively guide next step)

After each conclusion, append the fixed next-step prompt — full template in `references/output-templates.md` §4.

---

## Output Spec

Default text/Markdown output. **When the user explicitly asks "output report / generate report / html report", read `references/report-spec.md` to generate HTML.**

> **Complete-output iron rule (MUST)**: every detail table queried must be **fully output item-by-item** with full-window daily/weekly columns (matching query granularity). Do NOT compress into first/last summary. "Queried but not output" = violation. Full rule: `governance.md` HARD RULE #17.

Detail table template + Do/Don't examples + color conventions (up = red, down = green): `references/output-templates.md` §5.

---

## Script Resources

- `scripts/ae_query.sh`: ae-cli query + persisted-file validation. Usage `./ae_query.sh sql <output.json> <<'SQL' ... SQL` (SQL via heredoc/stdin/file); event model `./ae_query.sh evt <output.json> <definition.json>` (definition JSON object written to a file first, validated before run). **project-id read from env var `AE_PROJECT_ID` (export first)**.
- `scripts/dim_analyzer.py`: dimension/cross drill-down analyzer. `overview` (aggregate three series) / `dim` (single dimension, `--os-normalize`/`--top N`/`--min-dau`) / `cross` (cross drill-down, `--dim1`). Auto-computes intra-group rate daily series + ★ dual-threshold anomaly mark and separately prints a net-trend `hint` (first-half vs second-half displacement vs day-over-day noise σ, per `judgment-parameters.md` §1). The ★ is a mechanical threshold result only — the main agent confirms the full daily-series shape (consecutive decline / V-shape / inversion) for the final anomaly judgment.

## References

| File | Purpose | When to read |
|------|---------|-------------|
| `references/product-config-template.md` | Product config template | First time configuring a product (Part 0) |
| `references/product-config-example.md` | Filled example (LesPark, reference only) | Part 0, "how to fill" reference |
| `configs/product-config-<product>.md` | Persisted product configs (generated at runtime by you, NOT shipped in this package) | Reuse on subsequent analysis for same product |
| `references/query-templates.md` | SQL/event model query templates + query traps | Every query step (Part 1/3/4/5) |
| `references/indicators.md` | Metric calibers + funnel + supply side + environment layer + root-cause library | Part 2/5 |
| `references/comparison-mode.md` | Comparison mode Period A/B procedure | When user says "before/after update" / "this week vs last week" |
| `references/judgment-parameters.md` | Thresholds (sole authority) + confidence tiers + root-cause confidence labeling | Before any threshold/confidence-based judgment (Part 4/5) |
| `references/version-diagnosis.md` | Version-difference diagnosis flow | Part 5.3, when "version" is a suspect |
| `references/governance.md` | HARD RULES + AMA + sub-agent delegation rules | Any time a MUST rule is in doubt; before delegating queries |
| `references/output-templates.md` | Fixed output artifacts (status table, checklists, conclusion format, detail table template) | Part 3/4/6 + Output Spec, when a template is needed |
| `references/validation-checklist.md` | Output self-check list | Before delivering any conclusion |
| `references/report-spec.md` | HTML report spec | Only when user asks for an HTML report |

---

## Prohibited Constraints

> **【权威声明】** The 7 bottom lines below are a condensed quick-glance summary. `references/governance.md` is the **sole authority** for the full 18 HARD RULES + 5 AMA + delegation rules. On any conflict, governance.md wins; do NOT treat this summary as a substitute.
>
> Seven bottom lines invalidate the conclusion if violated: (1) running without product config; (2) first/last-only dimension breakdown; (3) treating between-group difference as time-trend fluctuation; (4) concluding after a single drill-down; (5) confirmatory conclusion without residual-signal check; (6) incomplete "all dimensions" claim; (7) "query but not output". Full HARD RULES (0-18) + AMA (AMA-1~5) + delegation rules: `references/governance.md`. Thresholds + confidence tiers: `references/judgment-parameters.md`. Output self-check: `references/validation-checklist.md`.

---

## Boundary Statement

This skill is NOT applicable when:
1. The target metric is NOT a live/voice-room room-entry penetration (entry UV ÷ DAU) — e.g., gift/recharge monetization, pay conversion, product-category, short-video, or ad penetration use other skills.
2. The product has NO entry event tracked — room-entry UV cannot be computed; only DAU and revenue-side signals exist.
3. Data volume is insufficient — aggregate DAU below ~1,000/day makes sub-dimension breakdowns statistically unreliable (Low/Very Low confidence per `references/judgment-parameters.md` §2); use a longer window or merge groups instead.
4. The user wants penetration **prediction** rather than decline **diagnosis** — this skill locates root causes of observed declines, it does not forecast future penetration.

## Degradation Strategy

If ideal conditions are not met, degrade rather than error out:

- **Dual entry event missing** → run single-entry analysis; skip the two-event caliber-consistency check in Part 1.4 (precision: lose the cross-validation signal only).
- **No `{exposure_event}`** → skip the funnel exposure stage; estimate CTR via "entry-source distribution" instead of "exposure → entry" conversion (precision: cannot separate reach from conversion).
- **No `{stay_duration_field}`** → skip quick-exit rate / avg watch time; rely on entry rate + retention (T+1/T+3) to separate "reach" from "retention".
- **No `{new_user_field}`** → skip new/old split; use channel + version as the primary segmentation alternatives.
- **Virtual properties (`#vp@...`) unavailable in SQL** → use event model, or fall back to raw user-table fields via SQL CASE WHEN (see `query-templates.md` §6/§7).
- **Sub-dimension group sample too small (n < 100)** → merge groups or extend the window; label Low/Very Low per `references/judgment-parameters.md` §2, never use as root cause.

## Verification

- Penetration drop ≥ `TREND_INFLECTION_PP` (weekly) or a dual-threshold daily inflection triggers the diagnosis flow (see judgment-parameters.md §1).
- Priority: first validate tracking (Part 1.2) → then locate the anomalous dimension (Part 3/4) → then evidence-chain the root cause (Part 5).
- Validate effectiveness by comparing penetration trend before vs after corrective action (30-day window recommended), confirming the drop halts or reverts.
