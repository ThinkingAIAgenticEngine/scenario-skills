# Step 5: Generate the Analysis Report

## Goal

Render `tmp/analysis.json` into the six-section Markdown report and pass the final
combined gate over all three artifacts.

The six sections are the report's contract: **conclusion first / effect overview /
attribution analysis / problem localisation / optimisation advice / verification
plan**. None is optional.

## Input

- `tmp/analysis.json` (from Step 3)
- `assets/report_template.md` — the six sections and their hard requirements
- The workbook's filename (from Step 4), so the report can reference it

## Output

- `output/{strategy}_效果分析报告_{YYYYMMDD}.md`

## Executor

Orchestrator running the script.

## Validation Gate

`scripts/validate_report.py <md>`, then `scripts/validate_outputs.py`.

## Failure Handling

- Gate exit 1 → **FATAL**.
- A `no_sensitive_leakage` failure must be **fixed**, never delivered with a note.

## Flow

### Sub-step 5.1 — Render the report

```bash
$PY $S/scripts/generate_report.py --analysis tmp/analysis.json --out-dir output \
      --strategy-name "<name>" --excel-name "<workbook filename>"
```

**Decision based on exit code:**

- **IF exit 0** → proceed to 5.2.
- **IF exit 1** → **FATAL**, quote the error.

### Sub-step 5.2 — Validate the report on its own

```bash
$PY $S/scripts/validate_report.py <md>
```

Checks completeness, traceability and hygiene; the minimum size is 1200 bytes.

**Decision based on exit code:**

- **IF exit 0** → proceed to 5.3.
- **IF exit 1 (`no_sensitive_leakage`)** → **FATAL**. Some external text — a strategy
  name, a channel, an event name, a discriminator property, a client-defined field —
  carried credential-shaped material, an internal address or a machine-local path
  into the report. Fix the source value or the escaping; do not ship with a caveat.
- **IF exit 1 (other)** → report the failing check and stop.

### Sub-step 5.3 — Run the combined gate over all three artifacts

```bash
$PY $S/scripts/validate_outputs.py --analysis tmp/analysis.json \
      --excel <xlsx> --report <md>
```

This is the last gate before delivery. It re-checks the analysis blocks, the seven
worksheets, and the report's six sections **together**, so an artifact that passed in
isolation but disagrees with its siblings is still caught.

**Decision based on exit code:**

- **IF exit 0** → deliverables are complete. Report both paths to the user.
- **IF exit 1** → **FATAL**, quote the failing item.

### Sub-step 5.4 — Confirm the section-level requirements

| Section | Must contain |
|---|---|
| Conclusion first | the one-line verdict, **plus** an explicit statement of which stages were unobservable — otherwise "found no problem" reads as "no problem" |
| Effect overview | funnel, per-stage rates against benchmark, and the data-source mode |
| Attribution analysis | audience / channel / content / landing, with mode B's missing platform-side fields named as unobservable rather than zero |
| Problem localisation | ordered by priority: data consistency > data break > bleed point > channel > invalid experiment > content and timing |
| Optimisation advice | at least one concrete next action even when nothing is wrong — "no anomaly" is not "no advice" |
| Verification plan | a baseline for each proposed change; when no metric is computable, state explicitly that no baseline could be established instead of emitting an empty plan |

---

**After completion, deliver both artifacts and proceed to `steps/06_validate.md`
for the post-flight self-check.**

## Error Handling Summary

| Scenario | Action | Status |
|---|---|---|
| Render exit 0, both gates exit 0 | Deliver both artifacts | SUCCESS |
| `validate_report.py` exit 1 (leakage) | Fix the input or the escaping, stop | FATAL |
| `validate_report.py` exit 1 (other) | Report the failing check, stop | FATAL |
| `validate_outputs.py` exit 1 | Report the failing item, stop | FATAL |
| Report under 1200 bytes | Treat as a failed render | FATAL |
| A degradation missing from the confidence statement | Stop and fix | FATAL |

## Notes

- The renderer HTML-escapes the whole analysis payload, because external text reaches
  the Markdown tables through `degradations` and `issues`, not only through `meta`.
  A raw `|` there silently stretches a 3-column table into 4.
- Deliverable filenames are taken from the raw `meta`, bypassing the escaping, so a
  filename and its in-file mention can legitimately differ in encoding.
- Both artifacts carry the run date, so a workbook and a report from the same run pair
  up visually.
