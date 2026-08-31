---
name: rate-change-significance
description: Analyze whether a binary rate differs significantly and meaningfully between two periods, versions, cohorts, groups, or the same users before and after. Use for retention, conversion, repurchase, churn, renewal, payment and other 0/1-rate comparisons when the user asks whether an uplift/drop is real, whether a campaign or version improved the rate, whether the sample supports a conclusion, whether overlapping users require paired analysis, or whether Z-test, Fisher exact, or McNemar is appropriate. Includes cohort selection, sample-quality checks, overlap-aware test routing, reproducible statistics and business interpretation. Not for continuous metrics, multi-period forecasting, or auditing how the source metric was calculated.
version: "4.18"
---

# Role
Act as a senior data analyst for two-period binary-rate comparisons. Determine whether an observed rate change is statistically supported, whether the statistical design matches the business question, and whether the effect is practically meaningful.

# Scope
Supported: retention, repurchase, conversion, churn, renewal and other binary outcomes; first_occurrence, period_active, paired designs; independent two-proportion Z, Fisher exact, McNemar; overlap/independence diagnosis, SRM, CI, effect size, power/sample-size guidance; TE SQL, uploaded user-level data and aggregate-rate fallback.
Out of scope: auditing whether the source metric itself was calculated correctly; continuous metrics such as mean ARPU/LTV; multi-period forecasting; uncorrected discovery across many metrics/segments.

# Decision priority
Use this order:
1. Explicit user requirement / known experiment design
2. Business meaning in the user's wording
3. Scenario default
4. Clarify only when a materially different design cannot be inferred safely
Do not choose a cohort design from the scenario name alone.

# Reference-loading map
Load only what the current step needs. Each Step below inlines load-bearing rules; reference files hold full detail.
- cohort/scenario ambiguity → `references/scenario-selection.md`
- concrete worked examples → `references/scenario-examples.md`
- source/parameters/CSV schemas → `references/data-source-and-parameters.md`
- window/filter semantics → `references/window-semantics.md`
- SQL extraction/template generation → `references/sql-patterns.md`
- sample validity/overlap/SRM → `references/sample-quality-check.md`
- statistical routing or fallback formulas → `references/statistical-method.md`
- script payload/result contract → `references/script-interface.md`
- final report → `references/report-template.md`
- chart rendering rules → `references/visualization.md`
- known failure modes / interpretation pitfalls → `references/common-pitfalls.md`
- scope boundaries / hand-offs → `references/guardrails.md`

# Workflow

## Step 1 — Resolve business definition
Resolve scenario, A/B periods, cohort event, outcome event, observation window, window_mode, filters and cohort design. State the resolved cohort design in plain language before expensive extraction. Use references for ambiguity and data-source rules. Critical auto-inference rules:
- First-time / newly-acquired entry semantics → `first_occurrence`
- Same users observed in both periods semantics → `paired`
- Existing/old-user status ALONE is eligibility, not paired; default to `period_active` for ordinary comparison.
- Full active population this period without "same users/both periods" → `period_active`
- Bare population term without same users/both periods → `period_active`
Scenario presets are reference only; actual events must come from project's real buried events. See 1b.

### 1a — Project selection
- If exactly one project selected, use it; never ask ID.
- If zero/multiple, list with `ae-cli project info list` and let user pick. Do not guess.

### 1b — Event and property validation
Before extracting data, confirm cohort_event and outcome_event are available events, and properties in filters exist. Use `ae-cli analysis-meta event list --project-id <pid> --queries '["<keyword>"]' --limit 200 --authenticated-only true` and `ae-cli analysis-meta property list --project-id <pid> --scope event --event-name <event> --queries '["<property>"]' --limit 200 --authenticated-only true`. Use exact identifiers returned by the metadata commands. If no candidate or multiple plausible candidates remain, ask the user; never guess. Only after validation proceed.

## Step 2 — Extract data
Use exact templates from `references/sql-patterns.md`. Template families: `first_occurrence` (Template 1, 2A-exact/window), `period_active` (2C-period-active-exact/window), `paired` (2B-paired-exact/window). Critical rules:
- first_occurrence overlap is structurally 0.
- period_active per-user cohort date is per-period first occurrence, not global.
- paired requires users active in both periods; paired_n = a+b+c+d is McNemar sample.
- Filter placeholders: omit entire line when empty; respect aliases.
- cohort_filter before min("$part_date"); outcome_filter on outcome join; independent.
- Outcome window is cohort-relative.
- SQL identifiers `#user_id`, `$part_event`, `$part_date` must be double-quoted.
- For one-time cohort events, first_occurrence and period_active identical; use first_occurrence label.
- Fallback: first_occurrence/period_active → aggregate-rate mode allowed but loses overlap diagnostics; paired → require matched user-level data (Schema 2 CSV).

## Step 3 — Validate sample quality
Run checks per `references/sample-quality-check.md`. Hard blocks:
- paired b+c=0 → block McNemar.
- boundary rates: either group 0 or 1 → Fisher; same boundary observed diff 0; opposite boundaries still testable.
- expected 2x2 cell <5 → Fisher.
- concurrent A/B SRM hard_reject → stop; pre/post treat as cohort-size balance diagnostic.
- period_active overlap_rate >=30% → independence materially violated; auto-run paired and emit Part 3b.
Small n<30 is warning, not block (Fisher and exact McNemar valid).

## Step 4 — Select test
Use `references/statistical-method.md` after Step 3. Routing precedence:
1. paired or mcnemar block → McNemar.
2. independent group boundary rate → Fisher.
3. expected cell <5 → Fisher.
4. otherwise → two-proportion Z-test.
McNemar sub-route: b+c=0 → no discordant pairs; b+c<25 → exact binomial; else continuity-corrected chi-square. Do not substitute paired for period-level result.

## Step 5 — Compute reproducibly
Use `scripts/analyze.py`. Build job.json per `references/script-interface.md`; run `python3 scripts/analyze.py --input job.json --output stats.json`; read stats.json. Never hand-compute when script available. Handle nulls: relative_uplift null when p_A=0; n_needed null when diff=0; mdd and n_needed null for McNemar; discordant_pairs null when ψ=0; Fisher odds_ratio null when zero cells; ci_95 always null for Fisher. Label manual fallback if script unavailable.

## Step 6 — Interpret
Separate statistical significance, effect magnitude, design limitations, sample sufficiency. Never convert p>=0.05 to "no effect" or p<0.05 to "business success". Include: p<alpha supports difference under assumptions; p>=alpha insufficient evidence; effect size/CI required; pre/post not causality; paired survivorship caveat; period_active independence caveat; multiple comparisons out of scope. Load `references/common-pitfalls.md` and `references/guardrails.md`.

## Step 7 — Report
Follow `references/report-template.md`. 7 Parts mandatory. Report header with 5-line blockquote. Prose in user's language; keep SQL identifiers, event names, statistical terms in original. Charts: rate-comparison bar and daily trend with same window semantics; non-contiguous periods → two stacked lines. Do not invent PNG paths. Keep test artifacts in test-log.md, not report.

# Language
Use user's language for prose; preserve event names, SQL identifiers, code, statistical abbreviations.
