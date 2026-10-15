# Step 3: Six-Dimension Analysis

## Goal

Turn `tmp/raw_*.json` into `tmp/analysis.json` — the single intermediate that both
deliverables are rendered from. Everything the report asserts and every number the
workbook prints comes from here, so a wrong field here is wrong twice.

## Input

- `tmp/raw_*.json` (from Step 2)
- `references/metric_definitions.md` — the shared six-stage funnel and rate definitions
- `references/benchmark_thresholds.md` — thresholds and how a bleed point is chosen

## Output

- `tmp/analysis.json`

## Executor

Orchestrator running the script.

## Validation Gate

`scripts/validate_analysis.py tmp/analysis.json`

## Failure Handling

- Gate exit 1 → **FATAL**. Fix the analysis before generating deliverables; do not
  render a report from a failed analysis.
- Every metric zero → continue, but the report must state that nothing was
  measurable.

## Flow

### Sub-step 3.1 — Run the analysis

```bash
$PY $S/scripts/analyze_effectiveness.py --raw-dir tmp --out tmp/analysis.json \
      --mode <A|B> [--task-id <TID>] --strategy-name "<name>"
```

**Decision based on exit code:**

- **IF exit 0** → proceed to 3.2.
- **IF exit 1** → **FATAL**, quote the failing assertion.

### Sub-step 3.2 — Check the required blocks

`analysis.json` must carry all of:

`meta`, `metrics`, `funnel`, `rates`, `max_bleed`, `data_break`, `timeline`,
`experiment`, `issues`, `recommendations`, `validation_plan`, `degradations`,
`field_caveats`.

**Decision:**

- **IF all present** → proceed to 3.3.
- **IF a block is absent** → **FATAL**. A missing block is not an empty block.

### Sub-step 3.3 — Confirm the two cross-deliverable invariants

Two fields in `meta` exist specifically so the report and the workbook cannot
disagree about the same campaign. Both must survive any future refactor of this
step.

**Invariant 1 — trigger time.** `trigger_time` + `trigger_time_source` +
`trigger_time_label`.

`triggerTime` is empty whenever a campaign is cron-driven, so the value falls back
to `startDate`, converted with the campaign's own `tzOffset`, and is labelled as the
task start date. Reading `triggerTime` alone made the report print a date while the
workbook printed a dash — the same campaign, two deliverables, two answers.

**Invariant 2 — field caveats.** `field_caveats`.

The same business quantity can carry two units across interfaces:
`task_list.planNum` counts **sends**, `task_data_overview.plan` counts **users**.
Both are correct. Printing them side by side with no caveat reads as a ~100×
discrepancy. A caveat is emitted **only when the values actually disagree**, so an
honest agreement does not generate noise.

### Sub-step 3.4 — Confirm the judgement calls were made, not assumed

| Question | Correct handling | Wrong handling |
|---|---|---|
| Is a zero-valued stage a data break or real churn? | the first stage whose value is 0 **and whose every downstream stage is also 0** is the data break; it is excluded from bleed-point ranking | treating it as churn and reporting a "loss" that is really a missing event |
| Which stage is the bleeding point? | only a stage whose **rate is below its benchmark**, ranked by recoverable users = `(benchmark - actual) × denominator` | ranking by largest absolute drop-off, which always points at impression→click (that stage always loses >95%) |
| Is a ratio above 100% real? | impossible; the numerator is a subset of the denominator, so it signals a missing denominator event | judging it "normal" against the benchmark, which reads missing events as excellent performance |
| Is mode B's `plan` / `actualTrigger` / `trigger` zero? | **unobservable**, excluded from judgement | `.get(..., 0)` narrating null as zero and inventing "the audience was filtered out" |

**Decision:**

- **IF the data break, bleed points and priority order are populated as above** →
  proceed to Step 4.
- **IF any judgement rests on an `.get(..., 0)` default over mode B's
  platform-side fields** → **FATAL**. That is the single most misleading bug this
  skill can ship.

---

**After completion, proceed to Step 4 (`steps/04_export_excel.md`).**

## Error Handling Summary

| Scenario | Action | Status |
|---|---|---|
| Gate exit 0, all blocks present | Proceed to Step 4 | SUCCESS |
| Gate exit 1 | Report the failing assertion, stop | FATAL |
| A required block absent | Stop; an absent block is not an empty one | FATAL |
| Every metric zero | Continue; the report states nothing was measurable | WARN |
| Degradations recorded | Continue; they must reach the report | WARN |
| Mode B platform-side fields defaulted to 0 | Stop and fix | FATAL |

## Notes

- The analysis is the only place where the "unobservable ≠ zero" rule can be
  enforced. By the time the report is rendered, the distinction is already lost.
- `degradations` is an input to the report's confidence statement, not a debug log.
  Dropping one silently raises the apparent confidence of the whole report.
- `field_caveats` fires on disagreement only. Making it unconditional would train
  readers to ignore it.
