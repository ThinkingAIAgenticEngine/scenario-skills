# Step 3 - Generate the HTML Report

> Procedure file for **Step 3** in `SKILL.md`.
> Expected section list and rendering checks: `references/steps.md`, section "Step 3".

## Goal

Render the result JSON into a **self-contained** HTML report that needs no external resource and opens
with a double click. The report must state its decision caliber prominently: the reader has to be able to
see at a glance which alpha was used, which correction was applied and what the data caliber was, rather
than only seeing a conclusion.

## Input

| Source | Content |
|--------|---------|
| `{ws}/tmp/analysis_results.json` (produced by Step 2) | Includes `multiple_comparison`, `cohort_basis` and the per-metric decision fields |
| - | Nothing else; all report copy and styling is inlined |

## Output

`{ws}/output/ab_test_report_{YYYY-MM-DD}.html` - the only deliverable of this skill.

## Executor

Orchestrator. Run the rendering script from the shell.

## Validation Gate

```bash
mkdir -p {ws}/output
python scripts/generate_report.py \
  --results {ws}/tmp/analysis_results.json \
  --output  {ws}/output/ab_test_report_{date}.html

test -s {ws}/output/ab_test_report_{date}.html && echo ok
```

There is no separate validator script: the gate is **the file exists and is non-empty**, plus the four
rendering self-checks in Flow item 3 below.

## Failure Handling

| Situation | Status | Action |
|-----------|--------|--------|
| A missing field in the result JSON breaks rendering | FATAL | Stop; repair the artifact in Step 2 rather than adding a fallback to the report template |
| A 0-byte file is produced | ERROR | Re-run once; if it is still 0 bytes, stop and report |
| The decision-caliber block disagrees with `multiple_comparison` | ERROR | Stop: the engine and the report versions do not match; re-run Step 2 |
| A metric carries `v2_error` | Degraded | Continue; the report shows "part of the analysis is missing", which must be named at delivery |
| A metric failed entirely | Degraded | Continue; the metric belongs under "metrics that could not be analysed" and must **not** be rendered as a `0.00%` card |

## Flow

1. Create the directory and render: `IF the script exits 0 -> continue; ELSE -> read the error and go back to Step 2`.
2. Confirm the file is non-empty: `IF -s holds -> continue; ELSE -> re-run once, then stop`.
3. Four rendering self-checks (none may be skipped before delivery):
   - The **decision caliber** block exists and agrees with `multiple_comparison` (a report claiming
     "no correction applied" while the result says `applied: true` is wrong).
   - A metric with `significant: true` but `decision_significant: false` carries the
     "not significant after correction (raw p < alpha)" tag and appears in the
     "multiple-comparison correction notice" paragraph - it must **never** appear in a winning conclusion.
   - When `overall_recommendation.downgraded_from` exists, the report must render
     "the overall recommendation was downgraded from ... to ...".
   - Direction wording for `lower_is_better` metrics is correct (when lower is better, "decreased" is the
     good outcome).
4. `IF all four pass -> proceed to Step 4; ELSE -> fix the rendering and re-run`.

## Error Handling Summary

| Check | Passes when | If it fails |
|-------|-------------|-------------|
| Script exit code | `0` | Read stderr, then go back to Step 2 |
| File non-empty | byte count > 0 | Re-run once |
| Decision-caliber block | Present and consistent with `multiple_comparison` | ERROR, stop |
| Correction-status tags | Every "significant before correction" metric has one | Fix the rendering and re-run |
| Downgrade notice | A notice exists whenever `downgraded_from` exists | Fix the rendering and re-run |

## Notes

- The report is **self-contained**: styling and charts are inlined, with no CDN reference and no external
  link, so it stays readable offline and can be forwarded.
- The footer records the version number, so a later reader can tell which rule set produced the conclusion.
- Do not delete the disclosure blocks (decision caliber / correction notice / degradation badge) for the
  sake of appearance. They are the core artifacts of this revision.
