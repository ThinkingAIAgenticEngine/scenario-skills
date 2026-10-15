# Step 6: Post-Flight Self-Check

## Goal

Confirm, after the run, that the two deliverables are internally consistent, that
every claim in the report is traceable, and that nothing was delivered with a
silently dropped caveat.

This is the orchestrator-side companion to `validate_outputs.py`: the gate checks
that the artifacts **exist and are complete**; this step checks that they **agree**.

## Input

- `tmp/analysis.json`
- `output/{strategy}_明细数据_{YYYYMMDD}.xlsx`
- `output/{strategy}_效果分析报告_{YYYYMMDD}.md`

## Output

No new file. A short consistency statement in the reply to the user.

## Executor

Orchestrator. Read-only — this step must not modify a deliverable to make it pass.

## Flow

### Sub-step 6.1 — Re-run the combined gate

```bash
$PY $S/scripts/validate_outputs.py --analysis tmp/analysis.json \
      --excel <xlsx> --report <md>
```

**Decision:** exit 1 → **FATAL**, report the failing item. Never repair a
deliverable silently.

### Sub-step 6.2 — Cross-check the two deliverables against each other

| Check | Pass condition | If it fails |
|---|---|---|
| Trigger time | the report's date and the workbook's date are identical, source label included | the `trigger_time` fallback to `startDate` broke — FATAL |
| Funnel numbers | the report's per-stage counts equal the workbook's, sheet by sheet | one of them is reading a different block — FATAL |
| Plan volume | if `plan` and `planNum` differ, a `field_caveats` note is present in the report | the caveat was dropped — FATAL |
| Experiment | when `expConfig.enableExp` is false, neither artifact claims lift | a phantom experiment — FATAL |
| Degradations | every entry in `analysis.json`'s `degradations` appears in the report's confidence statement | confidence is overstated — FATAL |

### Sub-step 6.3 — Confirm the honesty conditions

- Every stage excluded from judgement is named as **unobservable**, not as zero.
- The data break and its downstream stages are excluded from bleed-point ranking,
  and the report says so.
- Mode B's missing platform-side fields (`plan`, `actualTrigger`, `trigger`) are
  described as unavailable rather than as zero.
- A truncated fetch is reported as a completeness caveat, not as a smaller campaign.
- When data was too thin to judge a stage, the verdict says so instead of defaulting
  to "on target".

**Decision:**

- **IF every condition holds** → the run is complete. State the two deliverable paths.
- **IF any condition fails** → **FATAL**. Fix the analysis (Step 3) and re-run
  Steps 4-5; do not patch the rendered Markdown.

---

**Run complete.**

## Error Handling Summary

| Scenario | Action | Status |
|---|---|---|
| All checks pass | Report both artifact paths | SUCCESS |
| Gate exit 1 | Report the failing item, stop | FATAL |
| Cross-check mismatch | Fix Step 3 and re-run Steps 4-5 | FATAL |
| Missing degradation in the report | Fix Step 3 and re-run Steps 4-5 | FATAL |
| Thin data silently judged | Fix Step 3 and re-run Steps 4-5 | FATAL |

## Notes

- This step never edits a deliverable. A deliverable that only passes after being
  hand-edited cannot be re-derived, and the next run will disagree with it.
- The cross-checks exist because the report and the workbook are rendered from the
  same `analysis.json` by two different scripts — divergence means one of them is
  reading a field the other is not.
