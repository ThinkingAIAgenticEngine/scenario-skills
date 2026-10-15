# Step 2 - Statistical Analysis

> Procedure file for **Step 2** in `SKILL.md`.
> Field-by-field interpretation of the engine output: `references/steps.md`, section "Step 2".

## Goal

Turn group counts / means into a result JSON that carries the **correction-aware decision caliber**:
every metric reports both the raw `significant` and the authoritative `decision_significant`, and the
multiple-comparison configuration, the propagation of the top-level alpha, and the data caliber are all
written into the artifact so Step 3 can render them and Step 4 can read them.

## Input

| Source | Content |
|--------|---------|
| `{ws}/tmp/query_output.json` (produced by Step 1) | The grouped counts and means |
| `field_mapping.json` | Each metric's role (core / guardrail) and its polarity declaration |
| The user | The cohort caliber declared in Step 0b, carried through as `cohort_basis` |

## Output

| Artifact | Meaning |
|----------|---------|
| `{ws}/tmp/analysis_input.json` | The structured input assembled in 2a (metric list + alpha + multiple_comparison) |
| `{ws}/tmp/analysis_results.json` | The engine output: per-metric statistics + verdict + guardrail status + overall recommendation |

## Executor

Orchestrator. 2a is assembled by the orchestrator (not by a script); 2b invokes the engine script.

## Validation Gate

```bash
# 2b: run the engine
python scripts/ab_test_stats.py \
  --data @{ws}/tmp/analysis_input.json \
  --output {ws}/tmp/analysis_results.json

# 2c: check the artifact structure
python scripts/validate_analysis.py {ws}/tmp/analysis_results.json
```

The gate proves the artifact is **structurally complete**: raw statistics, top-level
`multiple_comparison`, and every metric's `decision_significant`, `decision_alpha`, `decision_basis`
and `n_comparisons` must be present and well formed. It does **not** judge whether the business
conclusion is right - that is the job of the 2d field checklist, read by a human.

## Failure Handling

| Situation | Status | Action |
|-----------|--------|--------|
| The input JSON is malformed | FATAL | Fix the assembly in 2a; never patch the engine |
| Zero metrics, or none analysable | FATAL | Stop; re-check Step 1's data and the field mapping |
| A single metric fails | Partial | The engine exits `0` and records the failure in `warnings`; it must be named at delivery |
| `alpha` is invalid (0, 0.9, `"abc"`) | WARN | The engine forces 0.05 and warns; tell the user about the fallback |
| A `v2` sub-block (Bayesian / power / business) fails | Degraded | `metrics_degraded` rises and the report shows an "analysis degraded" badge |
| `scipy` unavailable | Degraded | `stats_engine: normal-approximation-fallback`, which must be declared at delivery |

## Flow

1. **2a assembly**: convert `data.rows` into counts per proportion metric, using `row[1]` to identify the
   group. For continuous inference, compute mean, standard deviation and n from the same external
   one-row-per-exposed-user distribution, including zero contributors; do not synthesize them from an
   aggregate query row.
2. Write `cohort_basis: exposed_users_after_exposure`; when guardrails exist, declare their polarity
   (`lower_is_better`).
3. **2b run the engine**: `IF exit 0 -> go to 2c; ELSE -> read the FATAL/ERROR payload and stop`.
4. **2c pass the gate**: `IF exit 0 -> go to 2d; ELSE -> back to 2b and read warnings / per-metric error`.
5. **2d read the caliber** (table below). Anything abnormal must be stated at delivery.
6. Proceed to Step 3.

## Error Handling Summary

| Field | Expected | If abnormal |
|-------|----------|-------------|
| `stats_engine` | `scipy` | If fallback -> declare the degradation in the report and the answer |
| `warnings` | empty | If non-empty -> relay each item (alpha fallback, failed metrics, degraded sub-blocks) |
| `metrics_failed` / `metrics_degraded` | `0` | If non-zero -> name the specific metrics |
| `multiple_comparison` | `{method, family, n_comparisons, corrected_alpha, applied}` | If missing -> check whether the input was trimmed |
| Per-metric `decision_significant` | Consistent with `p < corrected_alpha` | If inconsistent -> engine regression; stop delivery |
| `overall_recommendation.downgraded_from` | Scenario-dependent | If present -> say the recommendation was downgraded; never quote the original action |
| `guardrail_status.status` | `safe` / `violated` / `no_guardrails` | A `watch` flag must also be relayed |
| `lower_is_better_source` | `explicit` | Any other value -> the polarity was guessed; confirm with the user before delivery |

## Notes

- **`decision_significant` is the only authoritative decision caliber.** `significant: true` together
  with `decision_significant: false` means "significant before correction" - it must be disclosed, but
  never acted upon.
- The top-level `alpha` propagates to every per-metric test and can be overridden per metric. Critical
  values come from Acklam's inverse-normal approximation, so any alpha works.
- When no metric survives correction, the overall recommendation is **force-downgraded** to
  `inconclusive` (`downgrade_reason: no_metric_significant_after_correction`).
