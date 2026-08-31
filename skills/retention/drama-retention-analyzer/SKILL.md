---
name: drama-retention-analyzer
description: >
  Decomposes short drama retention through a 5-layer funnel (traffic acquisition, opening hook, plot viewing, payment conversion, long-term return) and outputs layered actionable optimization strategies with per-episode churn inflection point diagnosis. Accepts ThinkingData project ID, drama name, and drama type as input via ae-cli. Supports 5 optional drill-down dimensions (segment, time, social, genre comparison, ROI). Use when users need to analyze short drama retention, churn, or per-episode completion rates. Not applicable to long-form dramas, games, e-commerce, or any non-short-drama content.
version: 6.1.3
compatibility: [claude-code, workbuddy]
---

# Short Drama Retention Analysis (5-Layer Funnel + Optional Drill-Down)

> **Applicable industry**: Short drama (vertical short drama, mini-program drama, vertical micro-short drama)
> **Target roles**: Short drama operations manager, data analyst, content producer
> **One-line positioning**: Decompose retention through a 5-layer funnel + layered attribution (traffic / content / product / monetization), precisely locate retention problem inflection points and output actionable strategies. Core conclusions first, drill-down on demand.
> **Data source**: ThinkingData, accessed via ae-cli (command syntax: `ae-cli --help`; verified against ae-cli 6.0.42). Metric SQL templates in `references/sql-templates.md` run via `ae-cli analysis adhoc run --model-type sql` or direct Hive/Presto/Trino access.

## When to Activate

Trigger phrases (any of these should activate this skill):
- short drama retention analysis
- short drama churn analysis
- micro-short drama retention
- short drama max churn episode
- short drama per-episode completion rate
- short drama ROI analysis
- short drama before/after comparison
- short drama funnel analysis
- short drama per-episode dropout rate
- short drama retention benchmark

## Not Applicable (Do NOT Activate)

- Long-form drama / film retention analysis (the 5-layer funnel model and thresholds are calibrated for short dramas only)
- Retention analysis for games, e-commerce repurchase, or other non-short-drama content
- Pure consulting with no ThinkingData/ae-cli data source available and user cannot provide manual data

## Prerequisites

**Required tools:**
- **ae-cli** (6.0.42) — ThinkingData CLI. Install and authenticate before use. Key commands:
  - `ae-cli team +list-projects` — discover project IDs
  - `ae-cli analysis-meta event list --project-id <pid>` — list events
  - `ae-cli analysis-meta event get --project-id <pid> --event-name <name>` — get event properties
  - `ae-cli analysis filter-value list --project-id <pid> --property-name <prop> --table-type event --event-name <name> --search-prefix <keyword>` — search drama name
  - `ae-cli analysis adhoc run --model-type sql --project-id <pid> --definition '<sql_json>'` — run SQL query (recommended path)
  - `ae-cli analysis adhoc export --model-type sql --project-id <pid> --definition '<sql_json>'` — export large data (async)
  - `ae-cli auth status` — check auth status
- **sql-query-interface** (optional) — direct SQL access to `v_event_<pid>` as alternative to ae-cli. Requires: read access to `v_event_<pid>` (partition column `"$part_date"`), Presto/Trino-compatible SQL dialect.

> Full command syntax and auth recovery flow: see `references/data-validation.md §0` and `§1`.

---

## 1. Analysis Model

### 5-Layer Core Funnel (Default Execution)

Check layer by layer: "Acquisition → Opening → Viewing → Payment → Long-term". **Must start from the traffic layer** to avoid misattributing traffic problems as content problems.

| Layer | Name | Core Goal | Key Metrics |
|-------|------|-----------|-------------|
| Layer 1 | Traffic | Determine whether retention issue is traffic or content | Impression CTR, start-play rate, E1 completion rate, D1 retention, **same-day cross-drama viewing rate** (short-drama desensitization metric) |
| Layer 2 | Opening | Validate first-3-episode hook effectiveness | E1 completion rate, E2 completion rate, 3-episode retention |
| Layer 3 | Plot | Precisely locate churn inflection points (most critical) | Per-episode completion rate, per-episode churn rate, segment retention rate (opening / middle / paywall / post-paywall / finale) |
| Layer 4 | Commercialization & Product | Detect non-content retention losses | Paywall trigger position, ad frequency, mid-episode exit rate, crash rate |
| Layer 5 | Long-term | Evaluate single-drama platform long-term value | Full-drama retention, 7-day re-view rate, 30-day revisit rate, 7-day user re-engagement rate, cross-drama conversion rate |

### 5 Optional Drill-Down Dimensions (Phase 2, On Demand)

After Phase 1 core analysis is complete, expand the following dimensions based on user selection:

| Dimension | Name | Applicable Scenario | Key Metrics |
|-----------|------|---------------------|-------------|
| Dim A | User Segment Depth | "How much do retention differ across user groups?" | Segment 3-episode retention difference, payment-path retention difference |
| Dim B | Time Dynamics | "Fast decay after first-day burst?" | D1→D7→D30 decay curve, update-day vs gap-day retention |
| Dim C | Social / Viral | "Did social sharing drive retention?" | Share→new viewer→3-episode retention funnel, danmaku density correlation |
| Dim D | Same-Genre Comparison | "How does it compare to same-genre dramas?" | Same-genre Top5 benchmark retention curve, genre fit score |
| Dim E | ROI / Commercialization Loop | "What's the ROI of this drama?" | LTV/CAC, full payment funnel, ARPU-retention paradox |

**Root cause rules**: Phase 1 core rules in `references/root-cause-rules.md` (13 Layer 1-5 rules). Phase 2 dimension rules in `references/root-cause-rules-dimensions.md` (18 rules, load on demand when user selects a drill-down).
**Optimization strategy library**: see `references/optimization-playbook.md` (per-layer Quick Fix / System Fix / A/B Test / Monitor + industry benchmarks).

---

## 2. Core Workflow (2 Phases)

### Phase 1 — Core Analysis (Default Execution)

**Goal**: Quickly deliver core conclusions + drill-down options.

#### Step 0 — Verify ae-cli Environment (Prerequisite, Cannot Skip)

Before collecting information, confirm data dependencies are available (full command syntax and recovery flow: `references/data-validation.md §0` and `§1`):

1. Verify ae-cli is installed and executable (version check)
2. Check auth status — if not authenticated, run device code flow login (recovery flow: `data-validation.md §0`)
3. Discover available projects — match the user's drama name against short-drama projects. If no project ID is known, **ask the user**.
4. Probe project reachability AND auto-match event names — list events for the project. If this fails, try SQL fallback probe (full SQL: `data-validation.md §1`). **If it succeeds, immediately auto-match play_start/play_end event names from the returned list using the variant table in `data-validation.md §1` (e.g., `playlet_start`/`playlet_end` vs `EpisodeExpose`/`EpisodeQuit`). Cache the matched names — Step 2 must reuse them, do NOT re-query.** Only confirm with user when no variant matches or multiple candidates are ambiguous.
5. **Any validation failure → try SQL fallback**: If ae-cli event/property metadata APIs are unavailable, use the SQL probe query in `data-validation.md §1` to test directly.
6. **Both unavailable → STOP**: Clearly inform the user "ae-cli not installed / project unreachable", and provide installation or connection guidance. **Do NOT proceed to subsequent steps. Do NOT fabricate analysis results using training data.**
7. **Fallback — manual data export**: If no programmatic data path is available but the user can manually export data conforming to the **manual data export contract** in `references/data-validation.md §0.5` (CSV/table with `user_id`, `episode_number`/`episode_id`, `play_duration`, `event_time`), accept the manual export and proceed with local aggregation. Label the report "data source: manual export". If the user cannot provide data either, STOP.

> **⚠️ Known ae-cli output quirk**: ae-cli prints a `[ae-cli] dispatching...` line before JSON output. Strip non-JSON prefix lines when piping to a JSON parser (find the first line starting with `{` or `[`). See `data-validation.md §1` for full details.
>
> **⚠️ Zone offset**: Some projects reject `--zone-offset` with `PROJECT_TZ_DISABLED`. Omit the flag or pass `99` for local-time mode. See `data-validation.md §1`.

#### Step 1 — Collect Required Information (3 Items)

| Information | Description |
|-------------|-------------|
| **Project ID** | ThinkingData project ID. Via `ae-cli team +list-projects` (look for short-drama projects by name) or provided directly by user |
| **Drama name / Episode ID** | Drama name for report presentation; episode ID for precise data query filtering |
| **Drama type** | Vertical short drama / Mini-program drama / Vertical micro-short drama (parameter differences per type: see `references/drama-type-configs.md`) |

Phase 2 optional information (collected only when user selects drill-down): payment model, update rhythm, distribution channels, core segment dimensions, same-genre benchmarks, social data, ROI data.

**⚠️ Handling rules when required information is missing:**
- When user does not provide drama name / episode ID or drama type, **must use AskUserQuestion to ask the user**. Do NOT autonomously browse or list in-project drama lists as a substitute.
- Do NOT proactively query drama lists unless user explicitly requests "list in-project drama list".
- Time range is also required — if user does not provide it, must ask in the same prompt.

#### Step 2 — Data Access and Validation

> Detailed validation logic: see `references/data-validation.md` (manual export contract §0.5 + ae-cli implementation §1-§6).
> Metric SQL templates: see `references/sql-templates.md` (discovery queries + T1–T5 layer metric templates against `v_event_<pid>` — run via `ae-cli analysis adhoc run --model-type sql` or direct Hive access).
> This skill uses ae-cli as the default data adapter. Manual CSV export is a fallback (see §0.5).

Core flow:
1. Confirm drama type → load corresponding threshold parameters from `drama-type-configs.md`
2. Reuse the event names auto-matched in Step 0.4 (do NOT re-query the event list). Confirm required properties via `ae-cli analysis-meta event get` using the matched event names. If using SQL adapter: run discovery queries (`sql-templates.md §0.1`) instead. **If Step 0.4 did not match (event list returned but no variant matched), resolve with the user here before proceeding.**
3. Validate required properties (`episode_no`, `watch_time`/`play_duration`, `video_duration`, `#account_id`/`#distinct_id`, `video_name`/`video_id`) — check semantics of watch_time (cumulative vs single-session, see `data-validation.md §4`)
4. Execute data quality validation (incl. §5.1 low-sample check and §5.2 synthetic-data sanity check), record data gaps, label affected analysis layers
5. Prefer an ae-cli AI-facing analysis model when the requested aggregate can be expressed semantically. Use the SQL model only for user-level detail or logic the AI models cannot express, after discovering authorized tables and columns. Full command syntax and parameters: see `references/data-validation.md §1` and `references/sql-templates.md`.
6. **Cross-validate drama type**: After querying episode count and per-episode duration, cross-check against the Quick Lookup Table in `drama-type-configs.md`. If the data suggests a different type than the user provided (e.g., user said "vertical short" but data shows 15 episodes × 2min = micro-short), flag the discrepancy and ask the user to confirm before proceeding with threshold calibration.

> **⚠️ SQL Safety**: When interpolating user-provided values (drama name, video_id, episode number) into SQL templates, always use single-quoted string literals and escape any embedded single quotes by doubling them (`''`). Never concatenate raw user input directly into SQL without escaping — this prevents SQL injection through the `--definition` JSON payload.

#### Step 3 — Execute 5-Layer Core Analysis

Execute 5 layers in sequence (**must start from traffic layer**):

1. **Traffic Layer (L1)** → Determine if retention issue is a traffic problem (includes D1 desensitization check, see drama-type-configs.md §Vertical Micro-Short Drama)
2. **Opening Layer (L2)** → Determine if first-3-episode hooks are adequate
3. **Plot Layer (L3)** → Per-episode churn inflection points + segment retention
4. **Commercialization & Product Layer (L4)** → Detect non-content losses
5. **Long-term Layer (L5)** → Evaluate long-term platform value

**Dynamic rule loading strategy**: Do NOT load all 13 rules from `root-cause-rules.md` upfront. Instead:
1. After querying each layer's metrics, compare against thresholds in `drama-type-configs.md`
2. Only load the rule sections whose Trigger conditions match the observed anomalies (e.g., if L1 start-play rate and D1 are both normal, skip R1-1 through R1-4)
3. For layers with no anomaly detected, mark as "healthy" and move to the next layer without loading that layer's rules
4. Cross-layer rules (e.g., R2-3/R4-1) are loaded only when both affected layers show anomalies

This reduces average context load from 13 rules to 3-5 rules per analysis session.

Root cause attribution: see `references/root-cause-rules.md`, sorted by layer priority. When multiple rules match, execute compound diagnosis.

#### Step 4 — Output Phase 1 Core Report

Report format: see `references/report-templates.md` (Phase 1 core report template).

**1-page core report**, including:
- Core TOP5 metric dashboard (start-play rate / E1 completion / 3-episode retention / max churn episode / full-drama retention)
- Drama health label (Top hit / Short-term cash-cow / Opening failure / Post-paywall attrition; definitions in `references/episode_churn_table.md`)
- Max churn episodes Top3 (churn rate + churn contribution + severity badge + attribution label)
- One-line conclusion

**Drill-down options menu at end of report:**
```
📋 Core analysis complete — Select next drill-down:

1. Churn episode deep-dive → Diagnose churn causes for episode {X}
2. Traffic layer deep-dive → Per-channel retention comparison
3. Payment deep-dive → Payment conversion rate and blocking points
4. Long-term layer deep-dive → 7-day re-view / 30-day revisit / cross-drama conversion
5. Segment deep-dive → New/returning/paid/channel segment retention differences
6. Time dynamics → D1→D7→D30 lifecycle decay
7. Social viral → Share→new viewer→retention funnel
8. Genre comparison → Compare with same-genre benchmark
9. ROI loop → LTV/CAC + full payment funnel
10. Comparison mode → Before/after comparison
11. End → Reply: end
```

> Drill-down options that cannot be executed due to data gaps should be labeled "⚠️ Data unavailable" in the menu.

#### Example Walkthrough

> User: "分析项目 1234 中短剧《厉总的替仵作》的留存，竖屏短剧，最近 7 天"

1. **Step 0**: `ae-cli --version` → 6.0.42 ✓ | `ae-cli auth status` → authenticated ✓ | `ae-cli team +list-projects` → found pid=1234 "短剧demo" | `ae-cli analysis-meta event list --project-id 1234` → returns events incl. EpisodeExpose, EpisodeQuit ✓
2. **Step 1**: drama_name="厉总的替仵作", drama_type="vertical short drama", time_range="2026-07-10 to 2026-07-17"
3. **Step 2**: Load thresholds from drama-type-configs.md §1 (start-play ≥40%, E1 ≥70%, 3-ep ≥35%, etc.) | Auto-match events (EpisodeExpose=play_start, EpisodeQuit=play_end) via data-validation.md §1 table | Run T1.1–T5.2 SQL templates from sql-templates.md | Cross-validate type: data shows 80 eps × 5min → confirms "vertical short" ✓ | Validate properties: episode_no ✓, watch_time ✓, video_duration ✓, #distinct_id ✓ | Run §5.1 low-sample check: new_uv=3200 (>100, pass) | Run §5.2 synthetic-data sanity check: no synthetic signatures (pass)
4. **Step 3**: L1 start-play=42% (pass), D1=18% (below 20% threshold) → load R1-3 | L2 E1 completion=58% (below 70%) → load R2-1 (Opening Hook Failure) | L3 max churn at E12 (32% churn rate, 18% contribution) → load R3-2 (Episode Content Quality Collapse) | L4 paywall at E29, paywall pass=42% (pass) | L5 finale retention=14% (pass)
5. **Step 4**: Output Phase 1 report (report-templates.md format) with health label="Opening failure" (low paywall reach + severe first-3-episode dropout), churn Top3=[E12 🔴 P0, E1 🟠 P1, E29 🔒 🟡 P2], one-line conclusion="Opening hook ineffective (E1 comp 58% <70%), traffic quality marginal (D1 18% <20%); content quality collapse at E12.", drill-down menu

---

### Phase 2 — Optional Drill-Down (Execute After User Selection)

After user selects from Phase 1 drill-down menu, reuse existing 5-layer analysis data and only query incremental data for the selected dimension:

| User Selection | Additional Info Needed | Execution | Report Template |
|----------------|----------------------|-----------|-----------------|
| Churn episode deep-dive | Narrative structure annotation data (if available) | Per-episode confidence interval + root cause inference + narrative deviation analysis | report-templates.md Phase 2 full version |
| Segment deep-dive | Core segment dimensions (new/returning/paid/channel) | Dim A full expansion | Same |
| Time dynamics | Update rhythm (daily / full-release / weekly) | Dim B full expansion (incl. three-tier basis) | Same |
| Social viral | Share data / danmaku data / UGC data | Dim C full expansion | Same |
| Genre comparison | Same-genre benchmark data / genre tags | Dim D full expansion | Same |
| ROI loop | LTV/CAC / payback period / eCPM | Dim E full expansion | Same |
| Comparison mode | Version A/B time ranges + change elements | 2-period full 5-layer comparison | report-templates.md Comparison Mode section |

**Phase 2 report**: see `references/report-templates.md` (Phase 2 full report template).

---

## 3. Execution Notes

0. **Data Authenticity Hard Constraint (CRITICAL)**: All retention numbers must come from real ae-cli queries. On any ae-cli call failure (not installed / timeout / error / no return / insufficient permissions), truthfully inform the user of the failure reason and stop that analysis item. **NEVER use training data, memory, or experience to fabricate retention rates, completion rates, churn episodes, or any data.** Prefer labeling "data unavailable" over outputting fabricated numbers.
1. **5-layer attribution order cannot be skipped**: Attribution analysis must start from the traffic layer to avoid misattributing traffic problems as content problems. Data retrieval can be parallel — fetch all layers' data in one batch, then perform attribution analysis in layer order.
2. **Progressive analysis**: Phase 1 delivers core conclusions first; Phase 2 drills down per user selection — do NOT expand everything at once.
3. **Phase 2 data reuse**: When entering drill-down, prioritize reusing Phase 1 queried data; only query incremental data.
4. **Drama type parameters first**: Before Step 2, first check `drama-type-configs.md` to load the corresponding drama type's thresholds and rules.
5. **Data quality first**: When per-episode viewers <100, conclusions are unreliable — must warn the user AND follow the degradation path in `data-validation.md §5.1` (skip per-episode churn ranking, force Insufficient-data health label, aggregate to drama-level). Also run the Demo/synthetic data sanity check in `data-validation.md §5.2` before attribution.
6. **Paywall context**: Paid episodes must be analyzed separately for free vs paid users.
7. **Avoid over-inference**: Root cause analysis is inference-based; label as "requires further validation."
8. **Language strategy**: Report language follows the user's question language. Provide bilingual metric labels when the question is in Chinese.

---

## 4. File Index

| File | Purpose | Phase |
|------|---------|-------|
| `references/drama-type-configs.md` | Drama type thresholds, D1 desensitization, segment definitions, paywall ranges | Phase 1 |
| `references/data-validation.md` | Data contract, ae-cli commands, metric definitions, quality validation, low-sample/synthetic-data handling | Phase 1 |
| `references/sql-templates.md` | Metric SQL templates (T1-T5) for ae-cli SQL model or direct Hive | Phase 1 |
| `references/root-cause-rules.md` | **Core rules** — Layer 1-5, 13 rules for Phase 1 attribution | Phase 1 |
| `references/root-cause-rules-dimensions.md` | **Dimension rules** — RA-RE, 18 rules for Phase 2 drill-down. Load only when user selects a drill-down. | Phase 2 |
| `references/optimization-playbook.md` | Per-layer optimization strategies + consolidated monitoring metrics + industry benchmarks + post-implementation verification loop | Phase 1+2 |
| `references/report-templates.md` | Phase 1 core report + Phase 2 full report + comparison mode incremental rules | Phase 1+2 |
| `references/episode_churn_table.md` | Churn episode table format + health label definitions | Phase 1 |

---

## 5. FAQ

**Q: What if ae-cli is not installed or the project is unreachable?**
A: Stop immediately. Do not fabricate results. Follow Step 0 fallback: try SQL probe → if both ae-cli and SQL fail, ask the user to manually export data conforming to the data-validation.md §0.5 manual export contract (CSV with user_id, episode_number, play_duration, event_time). If no data is available, stop.

**Q: What if the drama name cannot be found in the project?**
A: Use `ae-cli analysis filter-value list` with `--search-prefix` to search by keyword. If still no match, ask the user to provide the exact drama name or video_id. Do not auto-browse the full drama list unless the user explicitly requests it.

**Q: What if per-episode UV is below 100?**
A: Trigger the low-sample degradation path (data-validation.md §5.1): skip per-episode churn ranking, force the "Insufficient data" health label, aggregate to drama-level metrics. Every number carries a "low-sample" warning. Suggest expanding the time range first.

**Q: What if watch_time looks cumulative (values exceed video_duration)?**
A: Switch completion rate definition from `watch_time ≥ video_duration × 80%` to `watch_time ≥ video_duration` (cumulative coverage). Label the report with the alternative definition. See data-validation.md §4.

**Q: What if D1 retention is very low for a micro-short drama?**
A: Do not judge immediately. Micro-short dramas are binge-completable same-day — check the same-day cross-drama viewing rate first. If ≥15%, D1 is structurally suppressed by consumption completion, not churn. Use non-completer D1 retention as the traffic quality basis. See drama-type-configs.md §3.

**Q: How do I verify if an optimization actually worked?**
A: Follow the Post-Implementation Verification Loop in optimization-playbook.md: wait the recommended period, re-run Phase 1 core analysis, compare the key metric before vs after. If improvement is below the threshold, escalate to the next fix level.
