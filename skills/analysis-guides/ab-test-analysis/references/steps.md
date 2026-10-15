# Runbook: End-to-End Steps

Step-by-step execution guide for `ab-test-analysis`. SKILL.md gives the *what*; this file gives the
*how* — the exact command, the expected output, the decision branch, and the failure branch for
every step.

**Conventions used below**

- `{ws}` = the current workspace directory. All intermediate files live under `{ws}/tmp/`, the
  deliverable under `{ws}/output/`.
- `python` = whichever interpreter the pre-flight check resolved (see Step 0.3). On a machine
  without scipy, use `$(cat scripts/.resolved_python)`.
- Every gate prints a JSON object with a `status` field and **exits non-zero on failure**. Read the
  exit code; do not assume success from the printed text.

**Pipeline at a glance**

```
Step 0  Pre-flight ──────────► check_prerequisites.py + validate_params.py
   │  (PASS)
Step 0b Field alignment ─────► check_field_mapping.py      → tmp/field_mapping.json
   │  (PASS)
Step 1  Query experiment ────► check_query_definition.py   (query caliber, before the query)
   │                              │
   │                              └─► validate_query_output.py  → tmp/query_output.json
   │  (PASS)
Step 2  Statistical analysis ► validate_analysis.py        → tmp/analysis_results.json
   │  (PASS)                     (decision chain: decision_significant, not significant)
Step 3  Generate report ─────► file exists && size > 0     → output/ab_test_report_{date}.html
   │
Step 4  Present results ─────► user-facing summary + action plan
   │
Step 5  Closed-loop re-run ──► (optional, when the user acts on the recommendation)
```

---

## Step 0 — Pre-flight Check

**Executor**: orchestrator (shell). **Duration**: seconds. **Blocks**: everything.

### 0.1 Verify environment

```bash
python scripts/check_prerequisites.py
```

Checks three things and returns one aggregated `status`:

| check | meaning | on failure |
|-------|---------|-----------|
| `ae_cli_auth` | ae-cli is logged in | FATAL → tell the user to run the ae-cli login flow, then stop |
| `ae_cli_capability` | local `ae-cli analysis adhoc run` command exposes `--project-id`, `--model-type` and `--definition` | FATAL → the CLI version may predate the curated command; stop and report |
| `python_deps` | scipy / numpy importable | WARN → auto-installs scipy+numpy into a private venv and writes `scripts/.resolved_python`; the engine then auto-loads that venv and degrades to normal approximation if it still cannot import |

Exit `0` = SUCCESS or WARN (WARN is survivable — the analysis still runs, on the fallback engine).
Exit `1` = FATAL → **stop**, report which check failed.

### 0.2 Validate parameters

```bash
python scripts/validate_params.py \
  --project-id {project_id} \
  --variant-property {variant_property} \
  --success-events {comma_separated_events} \
  --time-range "{time_range}" \
  [--guardrail-events {comma_separated_events}] \
  [--filters "{filter_expression}"]
```

- exit `0` → SUCCESS (a WARN for missing `guardrail_events` is fine — it just means the guardrail
  check will be skipped; say so in the report's limitations)
- exit `1` → FATAL, listing each missing/invalid parameter. **Ask the user for exactly those items**,
  then re-run. Do not substitute a default.

### 0.3 Resolve the interpreter

If `check_prerequisites.py` reported a scipy version mismatch, use the venv interpreter for every
subsequent script:

```bash
PY="$(cat scripts/.resolved_python 2>/dev/null)"
[ -z "$PY" ] && PY=python
```

`ab_test_stats.py` also self-loads the venv on startup, so this is a belt-and-braces measure — but
when the venv's Python *minor version* differs from the system one, site-packages silently fails to
load and the engine degrades without an error. Always confirm the engine at the end by reading
`stats_engine` from the results file.

---

## Step 0b — Field Alignment

**Executor**: orchestrator (alias resolution + user Q&A) then script (gate).
**Produces**: `{ws}/tmp/field_mapping.json`. **Detail**: `references/field_mapping.md`.

### 0b.1 Collect the five field facts

Ask the user, resolving business language to field names using the alias tables in
`references/field_mapping.md`:

1. Which project does the experiment live in? → `project_id`
2. Which property records the group assignment? → `variant_field` (+ is it an event property or a
   user property? → `variant_field_type`)
3. What are the two stored values? Which one is the control? → `control_value` / `treatment_value`
4. Which event marks "user entered the experiment"? → `exposure_event`
5. Which events measure success (and which are guardrails)? → `success_events` / `guardrail_events`

### 0b.1b Declare the cohort block (required)

Besides the five facts, the mapping must carry a **`cohort` block** — it is what makes the success
numerator a subset of the exposed cohort rather than an independent count:

```json
"cohort": {
  "basis": "exposed_users_after_exposure",
  "order_enforced": true,
  "exposure_event": "<same as the top-level exposure_event>",
  "denominator_column": "<the column that carries the exposed-cohort user count>",
  "numerator_columns": ["<success count column(s)>"]
}
```

- `basis` must be exactly `exposed_users_after_exposure` — anything else is a FATAL.
- `order_enforced: true` asserts the success event is constrained to occur **after** exposure (the funnel
  window does this on the platform side).
- `denominator_column` must be an unambiguous user-count column; if several candidates match,
  `validate_query_output.py` raises an ERROR rather than guessing.

For continuous inference, declare both `basis: "per_user_over_exposed_cohort"` and
`distribution: "user_level"`. Mean, standard deviation and n must come from one row per exposed user,
including zero contributors; an aggregate `avg_per_user` is descriptive only.

### 0b.2 Verify the fields exist in the project

Query project metadata (`ae-cli` event/property listing) and confirm each name appears. Do **not**
skip this for "obvious" names: a typo does not raise an error, it returns zero rows, and zero rows
will later look like "the experiment had no traffic".

If a name is not found, offer the closest metadata matches to the user and re-confirm.

### 0b.3 Confirm the value domain

Look at the field's actual values and decide the `observed_domain` (after exclusions) and
`excluded_values`. The rules (null-like values, internal/test groups, exactly-two-groups,
balance ≥ 20%, non-negative integer counts) are listed in
`references/field_mapping.md` §3.

### 0b.4 Write and run the gate

Write `{ws}/tmp/field_mapping.json` (schema in `references/field_mapping.md` §5), then:

```bash
python scripts/check_field_mapping.py {ws}/tmp/field_mapping.json
```

| exit | status | action |
|------|--------|--------|
| `0` | SUCCESS / WARN | proceed to Step 1; echo any WARN to the user |
| `1` | FATAL / ERROR | read the failing rule in the JSON, fix the mapping, re-run. **Do not proceed on a failed gate.** |

Take the `resolved_mapping` block from the output forward — Step 1's query and Step 2's
`group_field` / `control_name` / `treatment_name` must all come from it, so the two ends cannot
drift apart.

**Failure branch**: 3+ groups → confirm whether the experiment is genuinely multi-arm (then stop, per
Boundary Statement §5) or the wrong field was picked. Severely imbalanced arms → clean the dirty
values, re-query, and if still imbalanced, report it as an experiment-configuration risk rather than
analysing it as-is.

---

## Step 1 — Query Experiment Data

**Executor**: orchestrator (shell). **Produces**: `{ws}/tmp/query_output.json`.

### 1.1 Build the query

The caliber is not a style choice — it decides whether the p-value answers the question the report claims.
Use the templates in `references/ae_cli_query_patterns.md` (Caliber 1/2/3):

| Metric kind | Scenario | ae-cli shape |
|-------------|----------|--------------|
| Proportion (conversion) | A — **funnel** | `model_type: funnel`, step 1 = exposure event, step 2 = success event, + conversion window |
| Guardrail rate | A2 — **funnel** | same funnel shape, plus `is_guardrail` / `lower_is_better` on the metric definition |
| Continuous (ARPU, duration) | B — **user-level exposed cohort** | external one-row-per-exposed-user distribution with `distribution: user_level`; aggregate `avg_per_user` is descriptive only |
| Retention | C — **nested retention object** | `model_type: retention`, with nested `retention: {initial_event, return_event, stat_type, unit_num, rtn_rate_or_num}` |

`groups[].field` must be `{name: <variant_field>, type: <variant_field_type>}` — the two values come
from `field_mapping.json`, verbatim.

**Rejected shapes** (the gate will fail them, and they produce a wrong answer rather than an error message
downstream — see Caliber 1/2):

- Two independent `user_count` queries (exposure and success pulled separately) — the success users are then not
  guaranteed to be a subset of the exposed cohort, nor to have succeeded after exposure.
- Continuous inference built from event aggregates: `avg` + `stddev` is payers-only, while standalone
  `avg_per_user` neither proves inclusion of non-triggering exposed users as zero nor supplies the same-cohort
  variance. Mean/std/n must come from the same one-row-per-exposed-user dataset.
- Retention declared as flat top-level `initial_event` / `return_event` — the current AE retention model expects a
  **nested** `retention` object with `stat_type`, `unit_num` and `rtn_rate_or_num`.

### 1.2 Query-caliber gate (before spending a query)

```bash
python scripts/check_query_definition.py <definition.json> \
  --model-type event|funnel|retention \
  --kind proportion|guardrail|continuous|retention \
  --exposure-event <exposure_event> \
  --variant-field <variant_field> \
  [--distribution user_level]
```

| exit | status | meaning |
|------|--------|---------|
| `0` | SUCCESS / WARN | caliber satisfied — WARN means the gate accepted it but wants you to double-check something (e.g. no conversion window declared) |
| `1` | ERROR / FATAL | the query shape cannot support the test it will feed — fix the query, do **not** proceed |

The gate is cheap and runs on the local JSON, so it costs nothing to run it on every metric before 1.3.

### 1.3 Conditional compiler preflight

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type <model_type> \
  --definition '<DEFINITION_JSON>' \
  --dry-run
```

Do not routinely dry-run a complete definition whose fields are already confirmed. Use this preflight
once when a concrete compiler or metadata-resolution uncertainty remains. On
`AI_QP_COMPILE_FAILED`, inspect `meta.compile_status`, `meta.errors[]`, `meta.resolved` and
`meta.warnings`; correct the reported paths and keep all other confirmed inputs unchanged. If the
resolved bindings do not match the mapping, stop and fix the definition.

### 1.4 Execute

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type <model_type> \
  --definition '<DEFINITION_JSON>' \
  --preview-rows 100 \
  --format json \
  > {ws}/tmp/query_output.json
```

Repeat once per metric group (one query per success event + one per guardrail event, or one query
with several metrics if they share the same event scope).

### 1.5 Gate

```bash
python scripts/validate_query_output.py {ws}/tmp/query_output.json
```

| exit | status | meaning | action |
|------|--------|---------|--------|
| `0` | SUCCESS | rows present, ≥2 groups, exposure-cohort sample OK, numerator ≤ denominator | proceed |
| `1` | EMPTY | `data.rows` empty or absent | wrong time range or wrong event names → re-check with the user, then re-query |
| `1` | ERROR | exposure cohort <100 users per group, 1 or 3+ groups, negative counts, **success numerator > cohort denominator** | insufficient sample → stop and suggest running longer; numerator > denominator → the caliber is wrong (success users are not a subset of the cohort) → back to 1.1/1.2 |
| `1` | FATAL | `ok: false`, unreadable file, bad JSON, ambiguous or missing denominator column | surface ae-cli's message; a timeout/auth problem belongs to Step 0 |
| `0` | WARN | **a zero-numerator (degenerate) arm** | not a silent pass — tell the user that arm had zero conversions before drawing any conclusion |

The gate returns `denominator_column` and `cohort_basis` too, and `detected_groups` + `metric_columns`.
**Use `detected_groups` to confirm the control/treatment labels again** — the query is where a wrong
mapping would finally show up.

> The denominator floor only applies to the column identified as the exposed cohort (via the explicit
> `cohort.denominator_column`, or the single name that looks like a user count). Success numerators are
> deliberately *not* floored — a 50/55 conversion count is a small numerator, not a small sample.


---

## Step 2 — Statistical Analysis

**Executor**: orchestrator (assemble input) then script (analyse). **Produces**:
`{ws}/tmp/analysis_results.json`.

### 2a — Assemble the analysis input

`ab_test_stats.py` does not read ae-cli output directly. Convert `data.rows` into a
`{metrics: [...]}` object:

```python
# proportion: row = [time, group, exposure_user_count, success_user_count]  — all strings
for row in rows:
    group = row[1]                      # never infer from row order
    exposure, success = int(row[2]), int(row[3])
    if group == control_value:
        control_total, control_success = exposure, success
    else:
        treatment_total, treatment_success = exposure, success
```

For a continuous metric, do **not** read mean/std/n from an aggregate ae-cli row. Start from the
declared external user-level dataset, verify exactly one row per exposed user and an explicit zero for
non-contributors, split by the confirmed group value, then compute each arm's mean, sample standard
deviation and n from those same rows.

Every metric entry carries its flags:

| flag | when | effect |
|------|------|--------|
| `type` | always — `proportion` or `continuous` | selects z-test vs Welch's t-test |
| `is_guardrail` | metric must not regress | included in the correction family when `family: all`; drives the guardrail verdict |
| `lower_is_better` | smaller value = better (crash/refund/error/latency); `false` for retention/GMV/exposure | flips verdict, business significance, Bayesian probability, the risk ladder and the guardrail check |
| `alpha` (per metric, optional) | this metric needs a different level than the top-level one | overrides the top-level `alpha` for this metric only |

For continuous metrics, `control_mean`, `control_std` and `control_n` (and their treatment counterparts)
must all come from the same user-level exposed cohort — never from a payer-only event distribution or a
standalone aggregate.

Top-level fields that must also be set:

| field | value | why it matters |
|-------|-------|----------------|
| `alpha` | 0.05 default (0.01 for conservative runs) | propagates to every metric; an invalid value (≤0, ≥0.5, non-numeric) is coerced to 0.05 and written to `warnings` |
| `cohort_basis` | `"exposed_users_after_exposure"` | echoed into the report's 数据口径 line |
| `multiple_comparison` | `{"method": "bonferroni", "family": "all", "enabled": true}` | `family: all` corrects over 核心 + 护栏 (default); `family: success` over core only; `method: none`/`enabled: false` → `decision_basis: "raw"` |

Fill the metadata too (`experiment_name`, `control_name`, `treatment_name`, `time_range`,
`hypothesis`, `group_field`, `group_field_type`, `project_name`, `project_id`) — it is used verbatim
in the report, and `hypothesis` / `group_field` / `project_name` must come from the user's answers,
never hardcoded. Write the result to `{ws}/tmp/analysis_input.json`.

### 2b — Run the engine

```bash
python scripts/ab_test_stats.py \
  --data @{ws}/tmp/analysis_input.json \
  --output {ws}/tmp/analysis_results.json
```

Exit `0` = at least one metric analysed (per-metric failures are reported in `warnings`).
Exit `1` = nothing analysable or a fatal input problem — read the `status: FATAL|ERROR` payload.

The engine runs in three stages; the split matters when reading the output:

1. `analyze_metric_core` — validate + test, attaches the resolved `alpha` / `alpha_source` / `lower_is_better`
2. `apply_bonferroni` — writes `decision_alpha` / `decision_significant` / `decision_basis` / `n_comparisons` /
   `bonferroni_alpha` / `multiplied_p_value`
3. `attach_v2_analysis` — Bayesian / power / business / recommendation / verdict / guardrails, **all reading
   `decision_significant`**, plus a hard guard that downgrades any ship-type overall recommendation to
   `inconclusive` when nothing survives correction

### 2c — Gate

```bash
python scripts/validate_analysis.py {ws}/tmp/analysis_results.json
```

Exit `0` → proceed. Exit `1` → the output is missing raw statistics, the top-level
`multiple_comparison` contract, or a per-metric corrected-decision field
(`decision_significant`, `decision_alpha`, `decision_basis`, `n_comparisons`); re-run 2b and inspect
`warnings` / per-metric `error`.

### 2d — Read the caveats before believing the numbers

| field | what to check |
|-------|---------------|
| `stats_engine` | `scipy` or `normal-approximation-fallback`. If it degraded, state that in the report/answer |
| `warnings` | invalid alpha coerced, metrics that failed, degraded v2 blocks |
| `metrics_failed` / `metrics_degraded` | failed = not analysed at all; degraded = core stats OK but part of the v2 block failed |
| `alpha` | the resolved top-level level. If the user asked for 0.01 and this says 0.05, the input was invalid — check `warnings` |
| `multiple_comparison` | `method` / `family` / `n_comparisons` / `corrected_alpha` / `decision_basis`. **Read this before quoting any p-value** — it tells you which threshold the verdict used |
| `summary.metrics_significant_raw` vs `metrics_significant_decision` | a gap = the "校正后失效" set. Never present those metrics as wins |
| `decision_significant` (per metric) | the authoritative flag. `significant: true` with `decision_significant: false` means raw-significant only — disclose it, do not act on it |
| `overall_recommendation.downgraded_from` | present when a ship-type recommendation was forced down to `inconclusive` by the correction guard. Say so explicitly |
| `guardrail_status.status` | `safe` / `violated` / `no_guardrails`. A guardrail can also be `watch`-flagged when it is raw-significant but correction-retired |
| `lower_is_better_source` | `explicit` / `inferred-name` / `default-guardrail` / `not-guardrail`. Any value other than `explicit` means the polarity was guessed — surface it to the user before they act |

---

## Step 3 — Generate the HTML Report

**Executor**: orchestrator (shell). **Produces**: `{ws}/output/ab_test_report_{YYYY-MM-DD}.html`.

```bash
mkdir -p {ws}/output
python scripts/generate_report.py \
  --results {ws}/tmp/analysis_results.json \
  --output  {ws}/output/ab_test_report_{date}.html
```

**Gate** (no script — check yourself):

```bash
test -s {ws}/output/ab_test_report_{date}.html && echo "ok"
```

Expected sections: cover → verdict banner → executive summary (**显著性判定口径** block + correction
advisory + verdict + overall recommendation) → experiment design → group analysis → per-metric analysis
(bar chart + Bayesian bar + power bar + correction-status tag + narrative + recommendation + stats grid)
→ guardrail analysis → statistical methodology (raw α + correction actually applied + corrected α + data
caliber) → limitations (incl. "校正后失效" list) → action plan.

Rendering to look for before delivering:

- **显著性判定口径** must be present in the executive summary and must match `multiple_comparison` in the
  results. If the report says `未启用多重比较校正` while the results say `applied: true`, something is wrong.
- A metric with `significant: true` but `decision_significant: false` must carry the
  `校正后不显著（校正前 p < α）` tag and appear in the "多重比较校正提示" paragraph — never as a win.
- `overall_recommendation.downgraded_from` present → the "总体建议已由 … 下调为 …" line must be rendered.
- Degradation rendering: a metric whose analysis failed appears under "以下指标未能分析" (never as a `0.00%`
  card); a metric with `v2_error` shows "部分分析缺失" with a "分析降级" badge. If you see the badge, mention
  the missing sub-analysis when presenting.

---

## Step 4 — Present Results & Action Plan

**Executor**: orchestrator (writing the final answer). **Produces**: the user-facing summary.

Present, in this order:

1. One-sentence verdict — which arm won and by how much
2. Key metrics table — control vs treatment, lift, p-value, **校正后是否显著**
3. The correction caliber — raw α, correction family, corrected α, and which metrics it retired
4. Bayesian probability that the treatment is the better arm, per metric
5. Post-hoc power — was the experiment adequately powered?
6. Business significance — is the effect practically meaningful?
7. Guardrail status — and, for any violation, which direction is the harmful one
8. Per-metric recommendation (ship / extend / gradual / subgroup / abandon)
9. Overall action plan, numbered
10. Closed-loop guidance — what to do after acting on the recommendation

**Correction language.** Never write "显著" for a metric whose `decision_significant` is false. The two legal
phrasings are: "校正后仍显著（p < 校正 α）" and "校正前显著，但未通过校正后阈值（不足以支撑上线）". If the overall
recommendation carries `downgraded_from`, say the downgrade out loud rather than quoting the original action.

**Direction language.** For a `lower_is_better` metric, a negative lift is the *good* outcome. Write
"下降 12.5%（越低越好）", never "下降 12.5%" alone, and never call such a change a degradation. If the
report shows the "方向假设（未显式声明，请核对）" block, read it out and get confirmation before the
user acts on the conclusion.

Then hand over the file so the user can open it.

---

## Step 5 — Closed-Loop Re-Analysis (optional)

**Trigger**: the user comes back after acting on the recommendation ("I extended the experiment",
"we rolled out to 50%, how is it doing?").

1. Back up the previous run: copy `{ws}/tmp/analysis_results.json` to
   `{ws}/tmp/analysis_results_prev.json`
2. Re-run Steps 1–3 with the updated time range / filter (Step 0b can be skipped only if the field
   mapping is unchanged — normally it is)
3. Compare: is the effect growing, stable, or fading? Did the guardrail hold?
4. State whether the earlier recommendation was validated
5. Suggest the next action in the loop

| Earlier recommendation | Follow-up action | How to re-analyse |
|------------------------|------------------|-------------------|
| Ship (全量发布) | monitor 7–14 days | re-run with an extended time range |
| Extend (延长实验) | keep collecting | re-run with the updated range |
| Gradual rollout (灰度发布) | watch gradual traffic | re-run with a filter on the rollout cohort |
| Subgroup drill (子群体下钻) | query by platform/region | re-run with filter parameters |
| Abandon (放弃) | design a new variant | start a new A/B test |

---

## Appendix A — Exit-code contract

| Code | Status | Meaning | Orchestrator action |
|------|--------|---------|---------------------|
| `0` | SUCCESS | gate passed | continue |
| `0` | WARN | passed with caveats (missing guardrails, dependency fallback, degenerate zero-numerator arm, retention without conversion window) | continue, **echo the caveat to the user** |
| `1` | EMPTY | query returned no rows | fix time range / event names, re-query |
| `1` | ERROR | recovered-but-invalid data (small cohort sample, wrong group count, numerator > denominator, query caliber unsatisfiable) | stop; report to user |
| `1` | FATAL | cannot proceed (auth, missing params, unreadable file, bad JSON, malformed retention/funnel contract) | stop; fix the cause |

All non-SUCCESS statuses exit non-zero. **Never treat a printed JSON blob as success without checking
the exit code.** A WARN is not a pass you may ignore silently — it exists because the case is legal but
needs the user's eyes.

## Appendix B — Artifact contract

| Path | Step | Delivered? |
|------|------|-----------|
| `{ws}/tmp/field_mapping.json` | 0b | no — audit record |
| _(definition JSON)_ | 1.1/1.2 | no — validated in place by `check_query_definition.py` |
| `{ws}/tmp/query_output.json` | 1.4 | no |
| `{ws}/tmp/analysis_input.json` | 2a | no |
| `{ws}/tmp/analysis_results.json` | 2b | no |
| `{ws}/output/ab_test_report_{date}.html` | 3 | **yes** — the final deliverable |

## Appendix C — Pre-delivery checklist

- [ ] Step 0 gate passed (or its WARN was explicitly acknowledged)
- [ ] Step 0b gate passed; `lower_is_better_source` is `explicit` for every metric that drives a decision
- [ ] Query caliber gate passed for **every** metric kind (proportion / guardrail / continuous / retention)
- [ ] Step 1 gate passed; `detected_groups` matches the mapping in `field_mapping.json`; `cohort_basis` recorded
- [ ] Step 2 exit `0`; `stats_engine` read and, if degraded, disclosed
- [ ] `multiple_comparison` read: correction family, `n_comparisons`, `corrected_alpha`
- [ ] Every "显著" claim in the answer maps to `decision_significant: true` (not merely `significant: true`)
- [ ] `overall_recommendation.downgraded_from` checked; any downgrade stated out loud
- [ ] Step 3 report exists and is non-empty; the 显著性判定口径 block matches `multiple_comparison`
- [ ] Verdict answers the user's actual question (which arm won, and can they ship it)
- [ ] Any "方向假设" / "分析降级" / "校正后失效" block was read out to the user
- [ ] No sensitive info leaked into the report (no machine-specific paths, no private endpoints)
