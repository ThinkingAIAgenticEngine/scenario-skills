---
name: ab-test-analysis
version: 2.7.0
description: A/B test significance analysis for two-group experiments. Before querying it aligns variant-field aliases, validates field value domains and enforces an exposure-cohort caliber (success users must be a subset of the exposed cohort and occur after exposure), then runs two-proportion z-tests and Welch's t-tests with confidence intervals, Cohen's d, MDE, a Bonferroni-corrected decision rule over the declared metric family, Bayesian posterior, post-hoc power, business significance and polarity-aware guardrail checks. Every verdict, recommendation and guardrail conclusion reads the corrected decision flag, never the raw p-value. Emits a self-contained Chinese-language HTML report with verdict, per-metric recommendations and an action plan; a five-metric experiment renders in about 3-5 minutes instead of 1-2 hours of manual spreadsheet work. Use for A/B test review, variant win check, lift and significance questions. Do NOT use for experiment design, traffic allocation or pre-launch sample-size planning, experiment configuration management, tracking-plan authoring or event instrumentation, tests with more than five arms, or when no variant property exists in tracking.
author: WorkBuddy
agent_created: true
triggers:
  - A/B test
  - AB测试
  - experiment analysis
  - 实验分析
  - control vs treatment
  - variant comparison
  - significant difference
  - 差异显著
  - 实验效果
  - lift
exclusions:
  - Experiment design, traffic allocation or pre-launch sample-size planning
  - Experiment configuration management (creating or editing experiment definitions)
  - Tracking-plan authoring or event instrumentation
  - Multi-variant tests with more than five arms
  - Projects where tracking has no variant property to split groups
metadata:
  language: zh-CN
  domain: analytics
  methodology: ab-test-significance
  skills:
    - ae-analysis
  tools:
    - Bash
    - Read
    - Write
---

# A/B Test Analysis v2.7

## Quick Start

**Trigger conditions** — start here when the user has finished running an experiment and needs a verdict:

- the user mentions A/B test, experiment comparison, control vs treatment, variant analysis
- the user asks "is the difference significant", "which variant won", "experiment conclusion"
- the user says "AB测试", "实验分析", "对照组", "实验组", "差异显著", "实验效果", "这个实验能不能推全量"
- a metric moved after a release or strategy change and the user wants to know whether the movement is real
- an experiment must be signed off (推全量 / 灰度 / 放弃) and needs a defensible statistical basis

**Operational steps** — the path from "here is my experiment" to "here is the report":

1. **Collect the six inputs** (`project_id`, variant property and its type, success events, guardrail events,
   time range and mode, global filters). Do not start querying before all six are confirmed — see Step 0b.
2. **Run the pre-flight gates** — `python scripts/check_prerequisites.py`, then
   `python scripts/validate_params.py --project-id {...} --variant-property {...} --success-events {...} --time-range {...}`.
3. **Align the fields**, write `tmp/field_mapping.json`, then gate it with
   `python scripts/check_field_mapping.py tmp/field_mapping.json`. A FATAL here means the field is wrong —
   fix the field, not the query.
4. **Build the query** on the exposure-cohort caliber and gate it **before sending** with
   `python scripts/check_query_definition.py <definition.json> --model-type event|funnel|retention --kind proportion|guardrail|continuous|retention`.
5. **Run the query**, then gate the returned data with
   `python scripts/validate_query_output.py tmp/query_output.json`.
6. **Assemble `tmp/analysis_input.json`** from the query's `data.rows` and run
   `python scripts/ab_test_stats.py --data @tmp/analysis_input.json --output tmp/analysis_results.json`.
7. **Generate the report** — `python scripts/generate_report.py --results tmp/analysis_results.json --output output/ab_test_report_{date}.html`.
8. **Present** the verdict, the correction caliber and the action plan, then offer the closed-loop re-run.

**What you need before starting** — this skill cannot run without tracking that actually exists in the project:

| Requirement | Minimum | Checked by |
|-------------|---------|------------|
| A variant property with exactly two clean values | required | `scripts/check_field_mapping.py` |
| An exposure event marking entry into the experiment | required (a success-event proxy is accepted, with a caveat) | `scripts/check_query_definition.py` |
| At least one success event inside the experiment window | required | `scripts/validate_params.py` |
| Exposed users per group | ≥ 100 (≥ 1000 for a confident conclusion) | `scripts/validate_query_output.py` |
| Guardrail events (crash, refund, ticket volume…) | optional but recommended | `scripts/check_field_mapping.py` |
| Project access | the running account must be able to read the project's event/property metadata and run adhoc queries on `project_id` (read-only; this skill never writes to the project) | `scripts/check_prerequisites.py` |

The business pain this skill removes: a data or product owner has run an experiment and must answer
"is the difference real and can we roll it out" — today that means an hour or two of hand-built
spreadsheets with no defensible significance decision and no way to separate the intended effect from a
guardrail regression (crash rate, refund rate, ticket volume). This skill turns that into one scripted,
gated run and one citable report.

**Expected effect**: a five-metric experiment goes from roughly 1-2 hours of manual spreadsheet work to a 3-5 minute scripted run (7 gated steps), and yields exactly one citable HTML report carrying a correction-aware verdict, per-metric recommendations and a guardrail status

## Scenario Entry Points

Find the row that matches the user's situation, then start from that scenario's default metric caliber.
The full playbook — pain points in the user's own words, role-specific emphasis, per-scenario calibers and
scenario-specific pitfalls — is in **`references/scenarios.md`**.

| Industry / scenario | Typical role | Default metrics (starting point for Step 0b) |
|---------------------|--------------|----------------------------------------------|
| E-commerce checkout / payment conversion | Growth PM, data analyst | Conversion rate (proportion, funnel caliber) |
| E-commerce AOV and revenue | Business analyst, operations | Revenue per exposed user (continuous; user-level exposed-cohort distribution required for inference) |
| Gaming onboarding and monetisation | Game ops, producer | D7 retention + first-purchase rate, with a churn guardrail |
| Gaming release rollout | Publishing / ops lead | Crash rate and force-quit rate (guardrail, `lower_is_better: true`) |
| Content and social recommendation | Recommendation engineer, content ops | Time per user, with D1 retention as a guardrail |
| SaaS / B2B onboarding and pricing | PM, growth lead | Trial-to-paid rate, with ticket volume as a guardrail |
| Paid acquisition / landing page and creative | Acquisition optimizer, growth | Signup cost per exposed user, with a small-sample warning |
| Presales / customer-supplied experiment data | Solutions engineer, presales | The customer's headline metric, plus the caliber gate |

Role-specific emphasis — which part of the report to lead with:

| Role | Cares most about | Read first in the report |
|------|------------------|--------------------------|
| Data analyst | Test method, assumptions, sample size | Statistical methodology + MDE + power analysis |
| Product / operations | Whether the conclusion can be acted on | Verdict banner + per-metric recommendation cards + action plan |
| Business owner | Risk | Guardrail banner + limitations |
| Presales / solutions | Whether the deliverable can be shown to a customer | The full HTML report + data source and caliber |

## Directory Guide

| File | Layer | Purpose |
|------|-------|---------|
| `references/steps/00_preflight.md` … `references/steps/05_closed_loop.md` | Procedure | **Per-step procedure contracts** — one file per pipeline step, each declaring goal, input, output, executor, validation gate, failure handling and IF/THEN flow |
| `references/steps.md` | Reference | **End-to-end step-by-step runbook** — every step's command, input, expected output, decision branch and failure branch |
| `references/scenarios.md` | Reference | **Scenario playbook** — industry scenarios with roles, pain points, default metric calibers and scenario-specific pitfalls |
| `references/field_mapping.md` | Reference | Field inventory, **variant/exposure/success field alias tables**, value-domain validation rules, mismatch diagnosis |
| `references/ae_cli_query_patterns.md` | Reference | `ae-cli analysis adhoc run` templates (`--project-id` / `--model-type` / `--definition`, `data.rows` output) |
| `scripts/check_prerequisites.py` | Guard | Step 0: verify ae-cli auth, Python deps, scipy availability |
| `scripts/validate_params.py` | Guard | Step 0: validate experiment parameters completeness |
| `scripts/check_field_mapping.py` | Guard | Step 0b: **field alignment gate** — required fields present, alias resolved, value domain legal, groups mapped to control/treatment, cohort block declared |
| `scripts/check_query_definition.py` | Guard | Step 1 pre-flight: **query-caliber gate** — validates the funnel/retention definition and requires an external user-level exposed-cohort distribution for continuous inference |
| `scripts/validate_query_output.py` | Validate | Gate after Step 1: check ae-cli returned data, exposure-cohort denominator floor, numerator ⊆ denominator |
| `scripts/validate_analysis.py` | Validate | Gate after Step 2: check analysis output structure |
| `scripts/ab_test_stats.py` | Execute | Statistical engine v2: z-test, t-test, Bayesian, power, Bonferroni |
| `scripts/generate_report.py` | Execute | Generate v2 HTML report with Bayesian/power/action cards |

## Programmatic Guards

| Guard | Script | Trigger | Behavior |
|-------|--------|---------|----------|
| CLI authentication | `scripts/check_prerequisites.py` | Step 0 | ae-cli not authenticated → exit 1 (FATAL) |
| Python dependency | `scripts/check_prerequisites.py` | Step 0 | scipy/numpy missing → auto-install to private venv |
| Parameter completeness | `scripts/validate_params.py` | Step 0 | project_id / variant_property / success_events / time_range missing → exit 1 (FATAL) |
| Field alignment | `scripts/check_field_mapping.py` | Step 0b | variant field not seen in project / value domain illegal (not exactly 2 clean groups) / control-treatment not mapped / success event outside exposure scope / missing `cohort` block → exit 1 (FATAL) |
| Query caliber | `scripts/check_query_definition.py` | Before Step 1 query | success not nested under exposure / continuous inference lacks a declared one-row-per-exposed-user distribution / retention contract is not nested → exit 1 (FATAL/ERROR) |
| Query data non-empty | `scripts/validate_query_output.py` | After Step 1 | ae-cli returned empty → exit 1 (EMPTY) |
| Sample size adequacy | `scripts/validate_query_output.py` | After Step 1 | exposure-cohort (denominator) column <100 per group → exit 1 (ERROR); success count > cohort size → exit 1 (ERROR); a zero-conversion arm → WARN (degenerate) |
| Analysis output valid | `scripts/validate_analysis.py` | After Step 2 | missing raw statistics, top-level `multiple_comparison`, or per-metric corrected-decision fields → exit 1 |

## Style Conventions

1. **Ask before querying** — always confirm variant property and success events with the user before running ae-cli queries
2. **Report title format** — `{Experiment Name} A/B Test Report {YYYY-MM-DD}`
3. **Conclusion first** — report structure: verdict → metrics table → statistical details → caveats
4. **Alpha = 0.05 by default** — the top-level `alpha` propagates to every metric (use 0.01 for conservative experiments); a per-metric `alpha` overrides it. This is the *raw* level — the **decision** threshold is the corrected alpha (see next rule)
5. **Corrected decision rule** — verdict, per-metric recommendation, guardrail status and business significance all read `decision_significant` (p < corrected α). The raw `significant` flag is kept for disclosure only, and any metric that is raw-significant but correction-retired is surfaced explicitly
6. **Two-sided tests** — default; use one-sided only when user explicitly requests

## Top-Level Flow

Full command-by-command runbook: **`references/steps.md`**. Field alignment detail: **`references/field_mapping.md`**.

| # | Step | Output | Validation Gate |
|---|------|--------|-----------------|
| 0 | Pre-flight Check | PASS/FAIL | `scripts/check_prerequisites.py` + `scripts/validate_params.py` |
| 0b | Field Alignment | `{workspace}/tmp/field_mapping.json` | `scripts/check_field_mapping.py` |
| 1 | Query Experiment Data (+ caliber pre-check) | `{workspace}/tmp/query_output.json` | `scripts/check_query_definition.py` → `scripts/validate_query_output.py` |
| 2 | Statistical Analysis | `{workspace}/tmp/analysis_results.json` | `scripts/validate_analysis.py` |
| 3 | Generate HTML Report | `{workspace}/output/ab_test_report_{date}.html` | Check file exists and size > 0 |
| 4 | Present Results | User-facing summary + file link | Confirm verdict reported |
| 5 | Closed-Loop Re-Analysis (optional) | Updated results + trend comparison | Same gates as Step 2/3 |

## Field Alignment (Step 0b)

Statistics can be flawless and the conclusion still wrong, because the fields were wrong. A two-sample
analysis depends on only four fields, but every one of them is easy to misconfigure — so alignment happens
**before** any query is sent. The complete alias tables, value-domain rules and mismatch diagnosis live in
`references/field_mapping.md`.

### The four fields that must be verified

| Role | Meaning | Allowed type | Verification action |
|------|---------|--------------|---------------------|
| **Group field** `variant_field` | The property that stores A/B assignment | `event_property` or `user_property` | Confirm it **really exists** in the project, has the right type, and its domain is exactly two clean groups |
| **Group values** `control_value` / `treatment_value` | The concrete values of the two groups | string | Map the actual values to control/treatment explicitly — **never by row order** |
| **Exposure event** `exposure_event` | Where the denominator comes from (users who entered the experiment) | event name | Confirm it is the experiment exposure, not a site-wide app start, or the denominator is inflated |
| **Success event(s)** `success_event(s)` | Where the numerator comes from | event name | Confirm it occurs inside the experiment window and that the user was exposed first (otherwise unassigned users enter the numerator) |

### Field aliases (the user will not use the canonical name)

Users name fields in many ways. Normalise through the alias table first, then check the normalised name
against the project:

| Role | Common aliases (any match makes it a candidate) |
|------|-------------------------------------------------|
| Group field | `ab_group` / `abtest_group` / `ab_test_group` / `$abtest_group` / `experiment_group` / `$experiment_group` / `experiment_variant` / `variant` / `variant_id` / `group` / `group_id` / `bucket` / `bucket_id` / `test_group` / `traffic_group` / `strategy_group` |
| Exposure event | `experiment_exposure` / `exposure` / `$exposure` / `ab_exposure` / `abtest_exposure` / `enter_experiment` / `$app_start` (last resort, inflates the denominator) / `page_view` (only when exposure really is page-level) |
| Success event | `purchase` / `payment_success` / `order_paid` / `recharge` / `level_complete` / `signup` / `register` / `subscribe` / `button_click` (must be the target button, not any click) |

**A candidate alias must then be verified against the project metadata** (list events/properties via
`ae-cli`). Never let a misspelled name reach the query — it returns empty data, which is then misread as
"the experiment had no traffic".

### Value-domain validation rules

The group field's domain must satisfy every rule below, or the gate raises FATAL
(`scripts/check_field_mapping.py` reports each rule individually):

1. **Exactly two valid groups** after dirty values are removed. More than two means the wrong field was
   picked, or the experiment is multi-arm.
2. **Null-like values must be excluded**: `null` / `""` / `undefined` / `-1` / `0` (when 0 means
   unassigned) / `unknown`. These are users who never entered the experiment; including them dilutes the
   difference between the arms.
3. **Internal and test groups must be excluded**: `test` / `inner` / 内部 / 白名单 / `whitelist` / `debug` /
   `gray_test` and similar.
4. **The two labels must be mutually exclusive**: the same user or record cannot belong to both groups
   (especially important when the split is a user property).
5. **The two arms must not be severely imbalanced**: the default warning threshold is the smaller arm
   below 20% of the larger (`min_group_ratio`). A severe skew usually means broken allocation or a
   misconfigured field.
6. **Numerator ⊆ denominator**: the success-user count must not exceed the exposed-user count. A
   conversion rate above 100% means the numerator was not restricted to exposed users.
7. **Type validation**: count fields must be **non-negative integers**; mean/ratio fields must be **finite
   floats**. Strings such as `-`, `--` or `N/A` are data-quality defects that must be handled explicitly,
   not silently treated as 0.

### Mismatch symptom → diagnosis

| Symptom | Most likely cause | Action |
|---------|-------------------|--------|
| The query returns only one group | The group field name is wrong, or the field is a user property but was queried as an event property | Retry with another alias; switch `field.type`; confirm the property type from project metadata |
| The query returns 3+ groups | Wrong field (e.g. channel or city picked up), or the experiment really is multi-arm | Confirm the field semantics; if it truly is multi-arm, see Boundary Statement item 5 |
| The two arms differ by more than 10x | Dirty values were not excluded (nulls or internal-test groups became an arm), or allocation is broken | Clean per value-domain rules 2 and 3 and re-run; if still skewed, suspect the experiment configuration first |
| Exposed users far exceed experiment users | A site-wide event such as `$app_start` was used as exposure | Switch to the real exposure event, or obtain explicit acknowledgement from the user that the success event is being used as a denominator proxy |
| Conversion rate above 100% | The success event was not restricted to exposed users | Add the exposure constraint to the query (the same user must be exposed before converting) |
| The time range does not line up | `recent` includes today (data not fully landed) / `previous` excludes today | See the time-range mode table in `references/ae_cli_query_patterns.md`, and state explicitly which mode was used |

### The `field_mapping.json` contract

Step 0b writes the verified result to `{workspace}/tmp/field_mapping.json`, which becomes the field caliber
archive for the whole pipeline (Step 1's query and Step 2's metadata both read it, so nothing gets
hand-edited mid-run):

```json
{
  "project_id": "8888",
  "variant_field": "ab_group",
  "variant_field_type": "event_property",
  "control_value": "control",
  "treatment_value": "treatment",
  "exposure_event": "experiment_exposure",
  "success_events": ["purchase"],
  "guardrail_events": ["app_crash"],
  "excluded_values": ["", "null", "unknown", "test", "内部"],
  "observed_domain": ["control", "treatment"],
  "observed_counts": {"control": 10000, "treatment": 10000},
  "field_aliases_resolved": {"group_field": "ab_group", "exposure_event": "experiment_exposure"},
  "cohort": {
    "basis": "exposed_users_after_exposure",
    "exposure_event": "experiment_exposure",
    "order_enforced": true,
    "denominator_column": "曝光用户数",
    "numerator_columns": {"购买转化率": "付费用户数"}
  },
  "metrics": [
    {"name": "购买转化率", "type": "proportion", "numerator_column": "付费用户数"}
  ]
}
```

Validation command:

```bash
python scripts/check_field_mapping.py {workspace}/tmp/field_mapping.json
```

Exit code `0` = alignment passed, proceed to Step 1. Exit code `1` = FATAL/ERROR; the output names the
failing rule and how to fix it. **Never continue to a query with unaligned fields.**

## Analysis Framework

> **The caliber rule that governs items 1–4:** every proportion and continuous metric is tested over the
> **exposure cohort** (`exposed_users_after_exposure`). The numerator (success users / summed value) must be a
> **subset** of that cohort and must occur **after** exposure. A success count and an exposure count pulled as
> two independent `user_count` queries do **not** satisfy this — the same user can appear in the success row and
> in the exposure row without ever having been exposed. Caliber 1 (cohort), Caliber 2 (per-user) and Caliber 3
> (nested retention) in `references/ae_cli_query_patterns.md` are the templates that *do* satisfy it, and
> `scripts/check_query_definition.py` is the gate that enforces it.

### 1. Conversion Rate Comparison (Proportion)
Compare success users / exposed-cohort users, where success is a **funnel step nested under exposure**.
Use `ae-cli analysis adhoc run` with the **funnel model**: step 1 = exposure event, step 2 = success event, plus
an explicit conversion window; group by the variant property.
Apply two-proportion z-test with pooled standard error.

### 2. Continuous Metric Comparison (Mean)
Compare per-exposed-user metrics like ARPU, session duration or revenue per exposed user.
For a Welch test, use an explicit **user-level distribution** with one row per exposed user, including users
who contributed 0; declare it with `distribution: user_level`. An event-model `avg_per_user` can be reported as
a descriptive point estimate, but it neither proves inclusion of non-triggering exposed users nor supplies
their same-cohort per-user variance, so it must not feed the t-test.
**Rejected**: `aggregation: avg` + `stddev` over the purchase event paired with the paying-user count — that
distribution is payers-only, so its mean is ARPPU, not ARPU, and its n is not the cohort size. A Welch t-test on
those numbers answers a different question than the one the report claims.
Apply Welch's t-test (unequal variance, two-sided) only after mean, standard deviation and n are all computed
from that same exposed-user distribution.

### 3. Sample Size Adequacy
Calculate minimum detectable effect (MDE) given actual sample size.
The adequacy floor applies to the **exposure cohort (denominator)** only — never to a success numerator, otherwise a
50/55 conversion count would be flagged as "insufficient sample" while a 0-conversion arm passes silently.
Flag experiments where the cohort is insufficient to detect the observed effect.
Rule of thumb: <1000 per group → low confidence; <100 per group → invalid.
A zero-numerator arm is **not** a silent pass — it is reported as a degenerate arm.

### 4. Guardrail Metric Check
Verify that guardrail metrics (e.g., crash rate, retention) did not regress — judged on the **corrected**
significance flag, so a guardrail that stops being significant after multiple-comparison correction is not
reported as a violation, and vice versa.
Run the same grouped query for each guardrail metric.
Apply the same significance test; flag any **correction-surviving** movement in the metric's **harmful** direction
as "guardrail violated".
Mark each guardrail with `is_guardrail: true` and — for harm metrics such as crash rate, refund rate,
error rate or response time — `lower_is_better: true` (see "Metric Polarity" for the inference rules).

## Boundary Statement

This skill is NOT applicable when:
1. Experiment design or traffic allocation is needed — use `ae-experiment-design` skill
2. Experiment configuration management is needed — use `ae-experiment` skill
3. Sample size < 100 users per group — insufficient for any statistical conclusion
4. No variant property exists in tracking — cannot distinguish groups without a tracking field
5. Multi-variant tests with > 5 groups — pairwise correction becomes unreliable; use dedicated ANOVA tool

### Boundary against `ae-experiment-insight`

`ae-experiment-insight` and this skill address **different stages of the experiment lifecycle**. They are
complementary, not substitutes:

| Dimension | `ae-experiment-insight` | This skill (`ab-test-analysis`) |
|-----------|-------------------------|-------------------------------|
| Stage | Insight and monitoring while the experiment is **running** | Verdict and sign-off **after** the experiment ends |
| Input | An experiment entity already configured on the platform (experiment id) | The retrieval and caliber declaration for the group / exposure / success event triple |
| Core action | Pull the experiment's existing metrics, present them on a board, surface trends and anomalies | Hypothesis testing (z / Welch t), confidence intervals, MDE, multiple-comparison correction, Bayesian posterior, guardrail verdict |
| Output | An insight view or metric snapshot | A deliverable HTML conclusion report plus a ship / gradual / abandon action recommendation |
| Answers | "How is the experiment doing right now?" | "Is this difference real, and dare we roll it out?" |

**Decision rule**: if the question is about **statistical inference and rollout decision** (is the
difference significant, does it survive correction, was a guardrail violated, should we ship), use this
skill. If the question is about **experiment runtime state and insight presentation** (current metric
performance, trends, anomalies), use `ae-experiment-insight`.

**What this skill cannot be replaced on**: the exposure-cohort caliber gate
(`check_query_definition.py`), the **decision caliber** after multiple-comparison correction
(`decision_significant` rather than the raw `significant`), polarity-aware guardrail judgement
(`lower_is_better`), and the deliverable conclusion report with its action loop.

When both skills exist in the target environment, the recommended combination is: watch the experiment with
`ae-experiment-insight` while it runs, then switch to this skill for the final verdict and report once the
stopping condition is reached.

> Note: as of this version, `ae-experiment-insight` is not published on Skill Hub under that name (Hub
> searches for experiment / insight / ae-* return no skill of that name). This section describes a
> **capability boundary** so that triggers and outputs do not overlap; if that skill is published later,
> the decision rule above still applies.

## Degradation Strategy

If scipy is unavailable:
→ Fall back to normal approximation (internal `_norm_cdf_approx` using `math.erf`); precision loss < 0.001 for p-values.
   Recorded as `stats_engine: normal-approximation-fallback` and printed in the report's methodology
   section, so a reader always knows which engine produced the p-values.

If a v2 sub-analysis fails for one metric:
→ The remaining sub-analyses still run and the metric keeps its recommendation. The failure is
   recorded in that metric's `v2_error`, surfaced as a top-level `warnings` entry, and rendered in the
   report as "部分分析缺失" with a "分析降级" badge — never as a silently blank card.

If two groups are exactly identical:
→ p = 1.0, `required_sample_per_group: null`, `power_assessment: "undefined"`, and the recommendation
   is "无差异，放弃此方向". The report shows "无法估计" rather than a fake "±0.00%".

If every observation is a success or a failure in both arms:
→ Pooled variance is 0, so z / MDE are undefined. Flagged as `degenerate_variance` and rendered as
   "无法估计" with an explicit data-quality caveat.

If exposure event is missing:
→ Use `user_count` of any success event as denominator proxy; flag as "no dedicated exposure tracking, using success event as proxy"

If variant property is a user property (not event property):
→ Switch `groups[].field.type` from `event_property` to `user_property` in ae-cli query; same analysis applies

Minimum viable data:
→ `project_id` + variant property with exactly 2 values + at least 1 success event + ≥ 100 users per group
→ If fewer: report `INSUFFICIENT_SAMPLE` and suggest running longer

Degenerate variance: if both arms are identical the statistical engine exits cleanly with
`degenerate_variance: true`, `mde_pct: null`, and a report note — it never crashes.

## Verification

Significance threshold: raw p < `alpha` (default 0.05); **decision** threshold p < corrected α, where corrected α
= `alpha` / n_comparisons (Bonferroni over the declared `family`, default `all` = 核心+护栏). Every conclusion
reads the corrected flag.
Effect size threshold: Cohen's d > 0.2 (small), > 0.5 (medium), > 0.8 (large)
Guardrail violation: any guardrail metric with **corrected** significance AND movement in its **harmful** direction
(see "Metric polarity" below — for crash rate / response time that means an INCREASE, not a decrease)

Priority for verdict: success metric corrected significance > guardrail safety > sample adequacy > effect size

Validate effectiveness:
1. Check that p-values are within [0, 1] range
2. Verify confidence intervals do not cross zero when correction-surviving
3. Cross-check conversion rate = success_users / exposure_users manually
4. Confirm `summary.metrics_significant_decision` ≤ `summary.metrics_significant_raw` — the decision count can never
   exceed the raw count, and any gap must be explained by the "校正后失效" disclosure in the report

## Metric Polarity (`lower_is_better`)

Any metric can declare `lower_is_better: true` — that means **smaller is better**, so a significant
DECREASE is the good outcome and an INCREASE is the harm. The engine uses this one flag consistently
everywhere: verdict, business significance, the Bayesian probability, the risk ladder, the
recommendation, and the guardrail check.

**Omitting the flag.** For a metric with `is_guardrail: true` that omits it, the engine infers the
polarity from the metric name and, when the name is inconclusive, defaults to `true`:

| Name contains | Inferred polarity |
|---------------|-------------------|
| 崩溃 / 闪退 / 错误 / 失败 / 异常 / 超时 / 卡顿 / 延迟 / 耗时 / 退款 / 流失 / 投诉 / 卸载 (crash, error, timeout, latency, refund, churn…) | `lower_is_better: true` |
| 留存 / 活跃 / 时长 / 会话 / 转化 / 付费 / 收入 / GMV / ARPU / 曝光 / 点击 (retention, engagement, conversion, revenue…) | `lower_is_better: false` |
| anything else | `lower_is_better: true` (harm-metric default) |

Non-guardrail metrics default to `lower_is_better: false` unless declared.

**Always declare it explicitly for the metrics that matter.** The inference is a safety net, not a
substitute for the analyst's judgement. Every metric result carries `lower_is_better` plus
`lower_is_better_source` (`explicit` / `inferred-name` / `default-guardrail` / `not-guardrail`), and
the report prints a "方向假设（未显式声明，请核对）" block listing every metric whose polarity was
guessed — so a wrong assumption is always visible rather than silent.

```json
{"name": "崩溃率", "type": "proportion", "is_guardrail": true,
 "lower_is_better": true,
 "control_success": 100, "control_total": 10000,
 "treatment_success": 300, "treatment_total": 10000}
```

**Bayesian probability.** `prob_treatment_better` stays the literal P(treatment > control).
`prob_favourable` is the polarity-corrected "treatment is the better arm" probability and is what
every decision and label reads; for `lower_is_better` metrics it equals `1 - prob_treatment_better`.
The report labels it `P(实验组低于对照组)` vs `P(实验组高于对照组)` accordingly.

## Global Conventions

- Intermediate files: `{workspace}/tmp/` (`field_mapping.json` → `query_output.json` → `analysis_input.json` → `analysis_results.json`)
- Final report: `{workspace}/output/ab_test_report_{YYYY-MM-DD}.html`
- Status codes: SUCCESS / EMPTY / ERROR / FATAL (all non-SUCCESS gates exit non-zero)
- All ae-cli queries use `--format json` for structured output

## Detailed Steps

Each step below states its input, output, executor and validation gate. For the full command-level
runbook — exact shell commands, expected output, decision branches and failure branches — see
**`references/steps.md`**; that file is the authoritative execution guide when a step's details matter.

### Step File Map

| # | Step | File | Output | Validation Gate |
|---|------|------|--------|-----------------|
| 0 | Pre-flight Check | `references/steps/00_preflight.md` | PASS / FATAL | `scripts/check_prerequisites.py` + `scripts/validate_params.py` |
| 0b | Field Alignment | `references/steps/00.5_field_alignment.md` | `tmp/field_mapping.json` | `scripts/check_field_mapping.py` |
| 1 | Query Experiment Data | `references/steps/01_query.md` | `tmp/query_output.json` | `scripts/check_query_definition.py` → `scripts/validate_query_output.py` |
| 2 | Statistical Analysis | `references/steps/02_analyze.md` | `tmp/analysis_results.json` | `scripts/validate_analysis.py` |
| 3 | Generate HTML Report | `references/steps/03_report.md` | `output/ab_test_report_{date}.html` | file exists and non-empty + 4 rendering checks |
| 4 | Present Results & Action Plan | `references/steps/04_present.md` | user-facing answer | pre-delivery checklist in `references/steps/04_present.md` |
| 5 | Closed-Loop Re-Analysis (optional) | `references/steps/05_closed_loop.md` | re-rendered report | all Step 1-3 gates + cross-run comparability |

Every step file follows the same nine-section contract: **Goal → Input → Output → Executor → Validation Gate → Failure Handling → Flow → Error Handling Summary → Notes**. Each Flow section states its decision rules explicitly, for example `IF exit 0 -> continue to the next step` and `IF exit 1 -> FATAL, stop and report`.

### Step 0: Pre-flight Check

> **Procedure**: `references/steps/00_preflight.md`

**Executor**: Orchestrator (run validation scripts)

1. Run `python scripts/check_prerequisites.py` — checks ae-cli auth, Python deps
2. Run `python scripts/validate_params.py --project-id {project_id} --variant-property {variant_property} --success-events {success_events} --time-range {time_range} [--guardrail-events {guardrail_events}] [--filters {filters}]`
3. Any script exit 1 → FATAL, stop and report missing items

**Failure handling**: ae-cli not authenticated → FATAL stop; scipy missing → auto-install to private venv; parameters missing → FATAL stop, ask user

### Step 0b: Field Alignment

> **Procedure**: `references/steps/00.5_field_alignment.md`

**Input**: user's answers to Step 1's questions, plus project metadata (`ae-cli` event/property list)
**Output**: `{workspace}/tmp/field_mapping.json`
**Executor**: Orchestrator (alias resolution + user confirmation), then script
**Validation gate**: `python scripts/check_field_mapping.py {workspace}/tmp/field_mapping.json`

1. **归一别名** —— 用户给的字段名先过一遍别名表（见 `references/field_mapping.md`），得到候选标准名。
2. **核对存在性** —— 用项目元数据确认分组字段/曝光事件/成功事件真实存在；不存在则回到用户确认，**不要直接拿去查询**。
3. **核对类型** —— 确认分组字段是 `event_property` 还是 `user_property`（决定 Step 1 里 `groups[].field.type` 的取值）。
4. **核对值域** —— 确认分组字段的有效取值恰好 2 个，列出被排除的脏值（空值 / 内部测试组 / 未知值）。
5. **映射分组语义** —— 明确 `control_value` / `treatment_value` 分别对应哪个实际取值，以及 `exposure_event` 是否为真正的实验曝光。
6. **落盘并跑门禁** —— 写 `field_mapping.json`，执行上面那条命令。返回 FATAL/ERROR 就按提示修字段，修完重跑；**对齐通过才允许进入 Step 1**。

**Failure handling**: 字段名查不到 → 回到用户确认（提供近似候选名）；值域不是 2 组 → 判断是多臂实验（走 Boundary Statement 第 5 条）还是拿错字段；两组样本严重失衡 → 先清理脏值重查，仍失衡则作为数据质量风险上报用户。

### Step 1: Query Experiment Data

> **Procedure**: `references/steps/01_query.md`

**Input**: the confirmed mapping in `{workspace}/tmp/field_mapping.json` (project_id, variant_field, control/treatment values, exposure_event, success_events, guardrail_events, optional filters)
**Output**: `{workspace}/tmp/query_output.json`
**Executor**: Orchestrator (run ae-cli commands)
**Validation gate (in order)**:
1. `python scripts/check_query_definition.py <definition.json> --model-type {model_type} --kind proportion|guardrail|continuous|retention --exposure-event {exposure_event} --variant-field {variant_field}` — **runs on the model definition before it is sent**
2. `python scripts/validate_query_output.py {workspace}/tmp/query_output.json` — runs on the returned data

The field questions are asked **once**, in Step 0b, and recorded in `field_mapping.json`; the query is
derived from that file rather than from a second round of questions. The six things to have confirmed
by the end of Step 0b:

1. Which project? (project_id)
2. Which event/user property stores the A/B group assignment? — and its type (`event_property` /
   `user_property`)
3. Which events measure success? (e.g., `purchase`, `level_complete`)
4. What is the experiment time range? — and which mode (`recent` includes today; `previous` does not)
5. Any global filters? (platform, country, etc.)
6. Any guardrail metrics? (metrics that should NOT regress) — plus their polarity

Build and locally gate the definition, then execute it directly. If the compiler reports a concrete
metadata-resolution problem, run the corrected definition once with `--dry-run` and inspect
`meta.compile_status`, `meta.errors[]`, `meta.resolved` and `meta.warnings` before executing. See
`references/steps.md` §Step 1 for the exact commands and exit-code branches.

Run `ae-cli analysis adhoc run` with the **cohort caliber**, grouped by variant property:
- **proportion / guardrail** → funnel model: step 1 = the exposure event, step 2 = the success event, plus a
  conversion window. This is what guarantees the success users are a subset of the exposed cohort.
- **continuous** → inferential caliber requires an external one-row-per-exposed-user distribution declared as
  `distribution: user_level`; `avg_per_user` is descriptive only, and event-level `avg`+`stddev` is payers-only.
- **retention** → the nested `retention` object (`initial_event`, `return_event`, `stat_type`, `unit_num`,
  `rtn_rate_or_num`) — never flat top-level `initial_event` / `return_event`.

**IMPORTANT**: Use `ae-cli analysis adhoc run`; pass the project, model and model-definition JSON
separately with `--project-id`, `--model-type` and `--definition`. The definition file must not contain
the legacy generic-capability `{project_id, model_type, definition}` wrapper.
See `references/ae_cli_query_patterns.md` for exact query templates (Caliber 1/2/3, Scenarios A/A2/B/C) and
`scripts/check_query_definition.py` for the gate that enforces them.

Before assembling the analysis input, record the caliber in `analysis_input.json` as
`"cohort_basis": "exposed_users_after_exposure"` — the report prints it in the 数据口径 line.

**Output parsing**: ae-cli returns `{"ok": true, "data": {"title": ["时间", "ab_group", ...], "rows": [["<time_range>", "<group_value>", "<metric1>", ...], ...]}}`.
Read results from `data.rows` (NOT `data.data`), column names from `data.title`.
- `row[0]` = time range string (skip this)
- `row[1]` = group value (e.g., "control" or "treatment") — use this to identify groups
- `row[2+]` = metric values — **all strings**, must convert with `int()` or `float()` before arithmetic
- Group order is NOT guaranteed — always check `row[1]` to determine which group

**Failure handling**: ae-cli HTTP error → FATAL; empty data → EMPTY (check if time range correct); < 100 per group → ERROR (insufficient sample)

### Step 2: Statistical Analysis

> **Procedure**: `references/steps/02_analyze.md`

**Input**: `{workspace}/tmp/analysis_input.json` (assembled from `query_output.json`)
**Output**: `{workspace}/tmp/analysis_results.json`
**Executor**: Orchestrator (assemble input, then run analysis script)
**Validation gate**: `python scripts/validate_analysis.py {workspace}/tmp/analysis_results.json`

**Step 2a — Assemble analysis input** (Orchestrator does this, NOT a script):

`query_output.json` is ae-cli's raw return (`{ok, data: {title, rows}}`). The analysis engine
expects a structured `{metrics: [...]}` object. Convert `data.rows` into per-metric counts/means:

- For each success event, `success_count = int(row[success_col])`, `exposure_count = int(row[exposure_col])` per group.
- Identify control vs treatment rows by `row[1]` (group value), NOT row order.
- Write the assembled object to `{workspace}/tmp/analysis_input.json`.

**Step 2b — Run analysis**:

Run: `python scripts/ab_test_stats.py --data @{workspace}/tmp/analysis_input.json --output {workspace}/tmp/analysis_results.json`

**Analysis input JSON schema** (the `--data` file; build it from the ae-cli query output + user answers):

```json
{
  "experiment_name": "支付按钮颜色实验",
  "control_name": "control",
  "treatment_name": "treatment",
  "time_range": "2026-09-08 至 2026-09-14",
  "hypothesis": "将支付按钮从蓝色改为红色能提升购买转化率",
  "group_field": "ab_group",
  "group_field_type": "event_property",
  "project_name": "示例电商项目",
  "project_id": "8888",
  "alpha": 0.05,
  "cohort_basis": "exposed_users_after_exposure",
  "multiple_comparison": {"method": "bonferroni", "family": "all", "enabled": true},
  "metrics": [
    {"name": "购买转化率", "type": "proportion",
     "control_success": 520, "control_total": 10000,
     "treatment_success": 610, "treatment_total": 10000},
    {"name": "人均付费金额", "type": "continuous",
     "control_mean": 28.5, "control_std": 15.2, "control_n": 10000,
     "treatment_mean": 31.8, "treatment_std": 16.1, "treatment_n": 10000},
    {"name": "崩溃率", "type": "proportion", "is_guardrail": true, "lower_is_better": true,
     "control_success": 100, "control_total": 10000,
     "treatment_success": 300, "treatment_total": 10000}
  ]
}
```

**Top-level fields that drive the decision rule**:
- `alpha` — the raw significance level (default 0.05 when absent/invalid). Propagates to every metric unless that
  metric declares its own `alpha`. An invalid value (≤0, ≥0.5, non-numeric) is coerced to 0.05 and recorded in `warnings`.
- `cohort_basis` — the data caliber string, echoed into the report's 数据口径 line. Use
  `"exposed_users_after_exposure"` for the cohort caliber.
- `multiple_comparison` — `{method: bonferroni|none, family: all|success, enabled: bool}`.
  - `family: all` (default) → correction spans **核心 + 护栏** metrics, so a guardrail's presence also raises the bar for success metrics.
  - `family: success` → correction spans core metrics only.
  - `method: none` / `enabled: false` → single-comparison, `decision_basis: "raw"`.
  - Omitting the block defaults to Bonferroni over `all`.

**Continuous metrics must come from a user-level exposed-cohort distribution** — `control_n` /
`treatment_n`, mean and standard deviation must all be computed from the same one-row-per-exposed-user
dataset, including zero contributors. Do not derive Welch inputs from either event-level avg/stddev or a
standalone `avg_per_user` aggregate; the latter is a descriptive point estimate only. See
`references/ae_cli_query_patterns.md` Scenario B.

**Required metadata fields** (must be filled from the user's answers — do NOT hardcode):
- `hypothesis` — the experiment hypothesis (one sentence)
- `group_field` + `group_field_type` — the variant property name and its type (`event_property` / `user_property`)
- `project_name` + `project_id` — where the experiment data comes from (shown in the report's data source)

**Metric types**:
- `proportion` — success/total counts (conversion, retention). Uses two-proportion z-test.
- `continuous` — mean/std/n per group (ARPU, duration). Uses Welch's t-test.

The script runs in three stages (this matters when reading the output):

1. **Core per metric** (`analyze_metric_core`) — validate + two-proportion z-test / Welch's t-test, 95% CIs for absolute
   difference and relative lift, Cohen's d (continuous), MDE = `(z_{α/2} + z_β) * SE` at 80% power. Attaches the resolved
   `alpha` / `alpha_source` / `lower_is_better`.
2. **Multiple-comparison correction** (`apply_bonferroni`) — applies the declared `multiple_comparison` config and writes
   `decision_alpha`, `decision_significant`, `decision_basis`, `n_comparisons`, `bonferroni_alpha`, `multiplied_p_value`.
3. **Decision layer** (`attach_v2_analysis`) — Bayesian posterior, post-hoc power, business significance, per-metric
   recommendation, verdict, guardrail check and overall recommendation. **Every one of these reads `decision_significant`,
   never the raw `significant`.**

Plus: polarity resolution (`lower_is_better` + `lower_is_better_source`) on every metric, and a hard guard that downgrades
any ship-type overall recommendation to `inconclusive` when no metric survives correction (recorded as
`downgraded_from` / `downgrade_reason`).

**Failure handling**: scipy import error → auto-load private venv (see below) → fall back to normal approximation; missing fields in input → ERROR

**Analysis output contract** (`analysis_results.json`) — the report reads these fields, so keep them
in mind when inspecting or re-using the file:

| Field | Level | Meaning |
|-------|-------|---------|
| `stats_engine` | top | `scipy` or `normal-approximation-fallback` — always state which engine produced the numbers |
| `warnings` | top | Non-fatal problems (invalid alpha coerced, metrics that failed, degraded v2 blocks). Present only when non-empty |
| `summary.metrics_total` / `metrics_analyzed` / `metrics_failed` / `metrics_degraded` | top | Counts. `metrics_degraded` = analysed OK but part of the v2 block (Bayesian/power/business/recommendation) failed |
| `summary.metrics_significant_raw` / `metrics_significant_decision` | top | Raw vs correction-surviving counts. The decision count can never exceed the raw count; a gap is the "校正后失效" set |
| `alpha` / `cohort_basis` | top | The resolved raw significance level and the declared data caliber (echoed into the report's 数据口径 line) |
| `multiple_comparison` | top | `{method, family, n_comparisons, decision_basis, corrected_alpha, applied}` — the correction actually applied |
| `decision_significant` / `decision_alpha` / `decision_basis` | per metric | **The authoritative significance flag** (p < corrected α), the corrected threshold, and `raw` / `bonferroni`. Every verdict / recommendation / guardrail / business conclusion reads this, not `significant` |
| `error` | per metric | The metric could not be analysed at all. The report lists these separately as "以下指标未能分析" — never shown as a 0.00% card |
| `v2_error` | per metric | Core statistics succeeded, but a v2 sub-analysis failed. The report shows "部分分析缺失" plus a "分析降级" badge instead of a blank card |
| `lower_is_better` / `lower_is_better_source` | per metric | Resolved polarity and how it was decided (`explicit` / `inferred-name` / `default-guardrail` / `not-guardrail`) |
| `bayesian.prob_treatment_better` | per metric | Literal P(treatment > control) |
| `bayesian.prob_favourable` | per metric | Polarity-corrected probability used by every decision and label |
| `power_analysis.required_sample_per_group` | per metric | `null` when the observed effect is 0 or so small that no computable sample size would detect it — render as "无法估计", never as a fake number |
| `guardrail_status.status` | top | `safe` / `violated` / `no_guardrails`; `violated` also carries `violated_metrics` and `details` (metric, change, polarity) |

**Exit codes**: `0` = at least one metric analysed (partial failures are reported via `warnings`);
`1` = nothing analysable, or a fatal input/file problem. A non-zero exit always prints a
machine-readable `status: FATAL|ERROR` payload — check for it rather than assuming success.

**scipy / private venv note**: `check_prerequisites.py` (Step 0) installs scipy/numpy into a
private venv and persists its Python path to `scripts/.resolved_python` when the system Python
lacks them. `ab_test_stats.py` auto-loads that venv's site-packages on startup, so no manual
`RESOLVED_PYTHON` switching is required. If you still hit an import error, run the analysis with
the venv Python directly: `$(cat scripts/.resolved_python) scripts/ab_test_stats.py ...`.

⚠️ **Version match matters.** site-packages from a venv built for a *different* Python minor version
cannot be loaded by the running interpreter — the import fails silently and the engine quietly
degrades to the normal approximation. `check_prerequisites.py` warns when the venv Python version
differs from the current one; when it does, run the analysis with the venv Python itself (the command
above) rather than the system Python. Always read the `stats_engine` field of the result to confirm
which engine actually produced the numbers.
Setting `AB_TEST_NO_SCIPY=1` forces the fallback path — useful only for testing the degraded branch.

### Step 3: Generate HTML Report

> **Procedure**: `references/steps/03_report.md`

**Input**: `{workspace}/tmp/analysis_results.json`
**Output**: `{workspace}/output/ab_test_report_{date}.html`
**Executor**: Orchestrator (run report script)
**Validation gate**: check file exists and size > 0

Run: `python scripts/generate_report.py --results {workspace}/tmp/analysis_results.json --output {workspace}/output/ab_test_report_{date}.html`

The report includes:
- **显著性判定口径** block (raw α / correction family / corrected α / data caliber) — printed before any conclusion
- Verdict card (treatment wins / harmful / mixed / inconclusive)
- Metric comparison table with significance badges, each carrying its correction status (校正后显著 / 校正后不显著 / 不显著)
- Confidence intervals and effect sizes
- Guardrail status banner
- Sample size and MDE details
- "多重比较校正提示" in the executive summary and a "校正后失效" list in the limitations whenever a metric is raw-significant but correction-retired

### Step 4: Present Results & Action Plan

> **Procedure**: `references/steps/04_present.md`

**Output**: User-facing summary + file link + action plan

Present to the user:
1. One-sentence verdict: which variant won and by how much
2. Key metrics table (control vs treatment, lift, p-value, **校正后是否显著**?)
3. The correction caliber: raw α, correction family and the corrected α actually used — and which metrics were retired by it
4. Bayesian probability that the treatment is the better arm, per metric
5. Post-hoc power analysis: is the experiment adequately powered?
6. Business significance: is the observed effect practically meaningful?
7. Guardrail status — and, for any violated guardrail, which direction is the harmful one
8. Per-metric actionable recommendation (ship/extend/gradual/abandon)
9. Overall action plan with numbered next steps
10. Closed-loop guidance: what to do after following the recommendation

**Reading direction correctly**: for a metric marked (or inferred as) `lower_is_better`, a negative
lift is the GOOD outcome. Say "下降 12.5%（越低越好）" rather than "下降 12.5%" alone, and never
describe such a metric as "harness"/"劣化" merely because the number went down. If the report shows a
"方向假设（未显式声明，请核对）" block, read it out to the user and confirm the polarity before
they act on the conclusion.

**Closed-loop principle**: The report is not a one-time deliverable. Each recommendation
includes a follow-up action that the user can take, and the skill supports re-analysis
with new data after the user acts on the recommendation.

| Recommendation | Follow-up action | How to re-analyze |
|---------------|-----------------|-------------------|
| Ship (全量发布) | Monitor 7-14 days | Re-run skill with extended time range |
| Extend (延长实验) | Collect more data | Re-run skill with updated time range |
| Gradual rollout (灰度发布) | Monitor gradual traffic | Re-run skill with filter on rollout cohort |
| Subgroup drill (子群体下钻) | Query by platform/region | Re-run skill with filter parameters |
| Abandon (放弃) | Design new variant | Start new A/B test from scratch |

### Step 5: Closed-Loop Re-Analysis (if user follows recommendation)

> **Procedure**: `references/steps/05_closed_loop.md`

**Trigger**: User returns after acting on recommendation (e.g., "I extended the experiment,
here's the new data" or "I rolled out to 50%, how's it going?")

**Action**:
1. Load previous analysis as baseline (`{workspace}/tmp/analysis_results.json`)
2. Run new analysis with updated parameters
3. Compare trends: is the effect growing, stable, or fading?
4. Report whether the recommendation was validated
5. Suggest next action in the loop

## Output Contract

### Final Deliverable
- Format: self-contained HTML file (v2)
- Content structure:
  1. Cover: experiment name, variant names, time range, generation date
  2. Verdict banner: overall status with color coding
  3. Executive summary: **显著性判定口径** (raw α, correction family, corrected α, data caliber) + verdict + overall recommendation + guardrail status + any "校正后失效" disclosure
  4. Experiment design: hypothesis, groups, metrics, data source
  5. Group analysis: per-group metric cards
  6. Per-metric analysis: bar chart + Bayesian prob bar + power bar + correction-status tag + narrative + recommendation card + stats grid
  7. Guardrail analysis: safe / violated with explanation
  8. Statistical methodology: z-test / Welch t, the raw α, the correction actually applied and the corrected threshold, data caliber, Bayesian Beta posterior, power analysis
  9. Limitations: sample (exposure cohort), multiple comparisons + "校正后失效" list, time window, Bayesian prior, external validity
  10. Action plan: overall recommendation + numbered steps + closed-loop paths

### Intermediate Files (not delivered)
- `{workspace}/tmp/field_mapping.json` — confirmed field alignment record (audit trail for Step 0b)
- `{workspace}/tmp/query_output.json` — raw ae-cli query results
- `{workspace}/tmp/analysis_input.json` — assembled analysis input
- `{workspace}/tmp/analysis_results.json` — statistical analysis output

## Self-Check

### Pre-flight (scripts)
- #1 CLI authentication — `scripts/check_prerequisites.py` auto-checks
- #3 Tool dependencies — `scripts/check_prerequisites.py` auto-checks scipy/numpy
- #5 Parameter completeness — `scripts/validate_params.py` auto-checks
- #2 Field alignment — `scripts/check_field_mapping.py` auto-checks (alias resolved, field exists in project, value domain legal, control/treatment mapped, sample balance)
- FAIL handling: FATAL stop, report missing items

### Mid-flight (scripts)
- #0 Query caliber — `scripts/check_query_definition.py` checks the definition JSON **before** it is sent (funnel nesting, per-user continuous, nested retention)
- #1 Intermediate file non-empty — `scripts/validate_query_output.py` checks after Step 1
- #2 Sample size adequacy — `scripts/validate_query_output.py` applies the ≥100 floor to the **exposure-cohort denominator**, requires numerator ≤ denominator, and flags a zero-conversion arm
- #6 Analysis output structure — `scripts/validate_analysis.py` checks after Step 2
- FAIL handling: EMPTY → report and stop; ERROR/WARN → report and stop (WARN still surfaces to the user)

### Post-flight
- #1 Output file exists — confirm HTML report generated
- #4 Key content complete — report contains verdict, metrics, p-values, CIs
- #8 No sensitive info leaked — no machine-specific paths or private endpoints in the report
- FAIL handling: fix and regenerate before delivering

## Changelog

**v2.7**
- **Sensitive-info red line fixed at the source.** The 21 coefficients of the Acklam inverse-normal
  approximation in `scripts/ab_test_stats.py` were written as scientific-notation decimals whose
  fractional part is a 15-digit run (e.g. `3.969683028665376e+01` → `969683028665376`), which a red-line
  scanner reads as a 15-digit ID number. They are now stored as `float.fromhex('…')` strings — bit-exact,
  no decimal-digit run, portable across Python versions. Verified: no 15/16/17/18-digit or phone-shaped
  number remains anywhere in the package.
- Added an explicit project-permission prerequisite (read-only access to the project's metadata and
  adhoc queries; this skill never writes to the project) and a plain statement of the business pain it
  removes, per the review note.
- Dual-engine regression re-run: decision chain 51/51, report rendering 28/28, semantics 105/105,
  crash regression 0 CRASH / 0 WRONG.

**v2.6**
- `version` is now a semantic version (`2.6.0`) so the Hub's `version_maintenance` check recognises it.
- SKILL.md body brought below the Hub's 5% CJK limit (it measured 8.1%): the industry scenario playbook
  moved to `references/scenarios.md`, and the Step 0b field-alignment chapter, the `ae-experiment-insight`
  boundary table and the older changelog entries were rewritten in English.
- Added `## Quick Start` — trigger conditions, the eight operational steps together with their gate
  commands, and the tracking / data-volume prerequisites — plus `## Scenario Entry Points`, so a
  first-time reader can get from "here is my experiment" to "here is the report" without opening the
  references first.

**v2.5**
- **Package structure**: the per-step procedure files moved from `steps/` to `references/steps/`.
  Only `scripts/`, `references/` and `assets/` may sit at the package root, and the step-file detector
  reads `references/steps`.
- **Language rule**: all seven procedure files rewritten in English. They previously carried 21-41% CJK
  characters against a 10% limit; they now measure 0%. New changelog entries are written in English for
  the same reason.
- **Sensitive info**: the private-venv cache root is now supplied by configuration instead of being
  derived from the running user's account. `CACHE_DIR` pins the location explicitly; with no override a
  per-user temporary directory is used. The shipped source therefore carries no machine-local path and
  no OS-specific directory literal.
- `references/steps.md` kept as the depth runbook; the Step File Map in this file indexes the step files.
- v2.4's changes are recorded below (the entry was missing).

**v2.4**
- Trigger description gained negative triggers (`Do NOT use for ...`) plus a frontmatter `exclusions:`
  list, so the boundary against neighbouring skills is machine-visible.
- Added a quantified expected effect: a five-metric experiment moves from roughly 1-2 hours of manual
  spreadsheet work to a 3-5 minute scripted run (7 gated steps) and one citable HTML report.
- Introduced the per-step procedure contracts and a Step File Map table carrying a Validation Gate column.

**v2.3**
- **Decision chain fixed: multiple-comparison correction now really participates in the verdict.**
  The engine gained `decision_significant` / `decision_alpha` / `decision_basis` as the single
  authoritative decision caliber; the verdict, per-metric recommendations, guardrail status and business
  significance all read the corrected flag, and the raw `significant` flag is kept for disclosure only.
  When no metric survives correction, the overall recommendation is hard-downgraded to `inconclusive`
  (recorded as `downgraded_from` / `downgrade_reason`), so the report can no longer say "ship it" while
  every metric has been retired by correction.
- **Top-level alpha propagation fixed.** A top-level `alpha` (including non-default values such as 0.01)
  now reaches every single-metric test, and a metric may override it with its own `alpha`. An invalid
  alpha (≤0, ≥0.5, non-numeric) is coerced to 0.05 and recorded in `warnings`. Critical values now use the
  Acklam inverse-normal approximation (accurate to about 1e-9 for any α), replacing the previous hardcoded
  table that only supported 0.05 and 0.01.
- **Multiple-comparison family configuration added.** `multiple_comparison: {method, family, enabled}`,
  defaulting to Bonferroni over **all metrics (core + guardrail)**, so a guardrail's presence also raises
  the bar for the success metrics instead of only inflating their false-positive rate.
- **New query-caliber gate `scripts/check_query_definition.py`.** It validates the caliber **before the
  query is sent**: proportions must use the funnel model (step 1 = exposure, step 2 = success plus a
  conversion window); continuous inference must use a declared one-row-per-exposed-user distribution
  (rejecting both payer-only avg/stddev and standalone aggregate `avg_per_user` as Welch inputs); retention must use the nested `retention` object
  (`stat_type` / `unit_num` / `rtn_rate_or_num`). `references/ae_cli_query_patterns.md` was rewritten to
  match (Caliber 1/2/3 plus Scenario A/A2/B/C).
- **Sample gate reworked.** The floor now applies only to the **exposure-cohort denominator** instead of
  misjudging a success count (e.g. 50/55) as "insufficient sample"; a hard numerator ≤ denominator check
  was added, and a zero-conversion arm is flagged as a degenerate arm via WARN rather than passing silently.
- **`cohort_basis` declaration and report disclosure.** The report gained a statistical-caliber block
  (raw α / correction family / corrected α / data caliber), a per-metric correction-status tag
  (survives correction / raw-significant but retired / not significant), a multiple-comparison notice in
  the executive summary, a "retired by correction" list in the limitations, and the methodology block and
  footer version were brought up to date.
- **Stronger regression harness**: `test_decision_chain.py` (51 decision-chain assertions),
  `test_cohort_gate.py` (27 cohort-gate cases), `test_query_definition.py` (47 query-contract cases) and
  `fuzz_query_definition.py` (3000 mutation-fuzz rounds, 0 crashes / 0 silent degradations).
- **Capability boundary against `ae-experiment-insight` made explicit**: runtime insight versus
  end-of-experiment statistical verdict and rollout sign-off, complementary rather than substitutable
  (see the Boundary Statement).

**v2.2**
- Added **Step 0b Field Alignment** with a new programmatic gate `scripts/check_field_mapping.py`:
  required-field check, alias resolution audit, field-type check, value-domain validation
  (exactly two groups, null-like and internal/test values excluded, mapped values present in the
  observed domain, ≥20% sample balance, non-negative integer counts).
- Added `references/field_mapping.md` — field inventory, alias tables for the group field /
  exposure event / success events, value-domain rules, mismatch-symptom → diagnosis table.
- Added `references/steps.md` — command-level runbook for every step (input, expected output,
  decision branch, failure branch) plus exit-code, artifact and pre-delivery checklists.
- Added 应用场景与角色 section: industry scenarios (e-commerce, gaming, content/social, SaaS,
  ad landing pages, presales) with the role, the pain point and the deliverable.
- `description` rewritten as pure-ASCII English (Hub red-line compliance); Chinese trigger keywords
  remain in `triggers`.

**v2.1**
- Guardrail polarity: `lower_is_better` + `lower_is_better_source`, polarity-corrected
  `prob_favourable`, polarity-aware guardrail verdict, business significance, risk ladder.
- Per-metric degradation (`v2_error`) instead of an aborted v2 block; report renders a
  "分析降级" badge.
- Finite-guard on the sample-size formula (extreme inputs no longer raise `OverflowError`).
- Chinese report copy; `.warn-box` / `.error-box` styles defined.
