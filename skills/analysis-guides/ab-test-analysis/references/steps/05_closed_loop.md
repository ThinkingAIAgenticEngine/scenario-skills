# Step 5 - Closed-Loop Re-Analysis (optional)

> Procedure file for **Step 5** in `SKILL.md`.
> Re-run matrix and comparison guidance: `references/steps.md`, section "Step 5".

## Goal

When the user comes back after acting on the recommendation ("I extended the experiment", "we are at 50%
gradual rollout, how does it look now"), re-measure with **the same caliber** and answer two questions:
was the earlier recommendation borne out, and what comes next?

## Input

| Source | Content |
|--------|---------|
| The previous run's `{ws}/tmp/analysis_results.json` | Used as the comparison baseline |
| The new time range / filters | Extended run, gradual-rollout cohort, or a drill-down by platform or region |
| The previous run's `{ws}/tmp/field_mapping.json` | Reused directly when the fields have not changed |

## Output

- `{ws}/tmp/analysis_results_prev.json` - a backup of the previous run
- A new `{ws}/tmp/analysis_results.json` plus `{ws}/output/ab_test_report_{date}.html`, written as a
  new dated file
- A user-facing comparison: is the effect growing, stable or decaying, and did the guardrails hold

## Executor

Orchestrator: back up, re-run, compare, conclude.

## Validation Gate

All of the Step 1-3 gates apply, and **none may be skipped**:

```bash
python scripts/check_query_definition.py <definition.json> --model-type ... --kind ... --exposure-event ... --variant-field ...
python scripts/validate_query_output.py {ws}/tmp/query_output.json {ws}/tmp/field_mapping.json
python scripts/ab_test_stats.py --data @{ws}/tmp/analysis_input.json --output {ws}/tmp/analysis_results.json
python scripts/validate_analysis.py {ws}/tmp/analysis_results.json
```

Plus one **cross-run** check: the new run's `multiple_comparison.n_comparisons` and `corrected_alpha` must
be comparable with the previous run's. If the metric set changed, the two runs are no longer on the same
scale and their "significance" cannot be read side by side.

## Failure Handling

| Situation | Status | Action |
|-----------|--------|--------|
| The field mapping changed (new event, different group field) | Blocked | Rebuild the mapping in Step 0b and state that the two runs are no longer directly comparable |
| The metric set changed, so the correction family changed | WARN | Still produce a conclusion, but declare that the scale differs |
| The new run has fewer samples than the old one | WARN | Check the filters for a mistake; if they are right, state that confidence has dropped |
| A guardrail is violated in this run | Blocked | Escalate immediately and recommend a rollback or pausing the rollout |

## Flow

1. Back up the previous run: `cp analysis_results.json analysis_results_prev.json`.
2. `IF the field mapping is unchanged -> skip Step 0b; ELSE -> go back to Step 0b and rebuild it`.
3. Re-run Steps 1-3 with the new time range / filters.
4. Compare across runs: is the effect growing, stable or decaying, and did the guardrails hold?
5. State whether the earlier recommendation was borne out.
6. Give the next action from the matrix below.

| Earlier recommendation | Follow-up action | How to re-measure |
|------------------------|------------------|-------------------|
| Ship (full rollout) | Watch for 7-14 days | Re-run with an extended time range |
| Extend the experiment | Keep collecting | Re-run with the updated time range |
| Gradual rollout | Watch the gradual traffic | Re-run with a filter for the gradual-rollout cohort |
| Subgroup drill | Query by platform / region | Re-run with an extra filter |
| Abandon | Design a new variant | Start a fresh A/B test |

## Error Handling Summary

| Check | Passes when | If it fails |
|-------|-------------|-------------|
| Baseline backup | `analysis_results_prev.json` exists | Back up first; never overwrite the baseline |
| Field mapping | Identical to the previous run | Go back to Step 0b and declare the limited comparability |
| Correction family | Identical to the previous run | Produce the conclusion but declare the different scale |
| Guardrails | No new violation | Block and recommend a rollback |

## Notes

- This step is **optional**. If the user does not come back, do not run it - re-running spends query
  resources for nothing.
- A re-measurement must reuse the same caliber and correction configuration, otherwise statements like
  "it went up" or "it went down" are meaningless.
