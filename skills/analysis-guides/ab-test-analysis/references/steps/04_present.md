# Step 4 - Present Results & Action Plan

> Procedure file for **Step 4** in `SKILL.md`.
> Phrasing rules and the full presentation order: `references/steps.md`, section "Step 4".

## Goal

Translate the numbers in the report into **a conclusion the user can act on**, and state plainly whether
they can ship now and what to do next. This step changes no number. It only relays, and the relay must
agree with `decision_significant`.

## Input

| Source | Content |
|--------|---------|
| `{ws}/tmp/analysis_results.json` | Read `verdict`, `overall_recommendation`, `guardrail_status`, `multiple_comparison` and the per-metric decision fields |
| `{ws}/output/ab_test_report_{date}.html` | Handed to the user to open |

## Output

One user-facing answer, with no file artifact. The delivery order is fixed at 10 items:

1. One-sentence verdict - which arm won and by how much
2. Key metrics table - control vs treatment, lift, p-value, and **whether it survives correction**
3. Correction caliber - raw alpha, correction family, corrected alpha, and the metrics that were retired
4. Bayesian probability - posterior probability that treatment is better, per metric
5. Post-hoc power - was this experiment adequately powered?
6. Business significance - is the effect worth acting on?
7. Guardrail status - when violated, say which direction is the harmful one
8. Per-metric recommendation (ship / extend / gradual / subgroup drill / abandon)
9. Overall action plan, numbered
10. Closed-loop guidance - how to re-test after acting on the recommendation

## Executor

Orchestrator, writing the final answer.

## Validation Gate

A per-item checklist before delivery (no script):

- Every use of "significant" corresponds to `decision_significant: true`; `significant: true` may
  **not** stand in for it
- When `downgraded_from` is present, the downgrade must be stated and the original action must not be quoted
- Direction wording for `lower_is_better` metrics is correct
- A degraded `stats_engine`, a `lower_is_better_source` other than `explicit`, and a non-empty `warnings`
  list must each be disclosed on your own initiative

## Failure Handling

| Situation | Status | Action |
|-----------|--------|--------|
| The conclusion contradicts `decision_significant` | Blocked | Stop delivery; go back to Step 2/3 and fix the decision caliber |
| The report is missing or empty | Blocked | Re-render in Step 3 |
| The user disputes a polarity | Blocked | Go back to Step 0b, change the `lower_is_better` declaration and re-run the whole chain |
| The user wants numbers only, no recommendation | Degraded | Items 1-3 and 7 are still required; the recommendation may be condensed but the guardrail status may not be dropped |

## Flow

1. Read `verdict.status` to choose the opening: `treatment_wins` / `inconclusive` / anything else relayed
   as written in the report.
2. `IF verdict == treatment_wins AND a winning metric has decision_significant -> report "significant win";`
   `ELSE IF no metric survives correction -> report "insufficient statistical evidence" and name the metrics
   that were retired by correction`.
3. When relaying each metric, apply the phrasing rules: **still significant after correction (p < corrected
   alpha)** or **significant before correction but below the corrected threshold (not enough to ship)**.
4. Guardrails: `IF safe -> one sentence; IF violated -> name the harmful direction; IF watch -> explain that
   it was significant before correction and is being kept under observation`.
5. Give the overall action plan and the closed-loop guidance, then hand the report file to the user to open.

## Error Handling Summary

| Relay point | Allowed phrasing | Forbidden phrasing |
|-------------|------------------|--------------------|
| Significant after correction | "still significant after correction" | - |
| Significant only before correction | "significant before correction, but below the corrected threshold" | "significant win" |
| Recommendation downgraded | "the overall recommendation was downgraded from X to Y" | Quoting X directly |
| A lower-is-better metric | "decreased 12.5% (lower is better)" | "decreased 12.5%", or calling it a regression |
| Degraded engine | "this run used the normal approximation" | Staying silent about it |

## Notes

- The user's real question is "which arm won, and can I ship it". The answer must address both head-on
  before adding detail.
- If the report contains a "direction assumed (not explicitly declared, please confirm)" block, it must be
  read out and confirmed before the user acts on it.
