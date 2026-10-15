# Step 2: Fetch the Data (2a native reports / 2b ad-hoc funnel + events)

## Goal

Retrieve the raw campaign data and write it as `tmp/raw_*.json` in a shape that is
**identical for both modes**, so Steps 3-5 need no branching at all.

That convergence is the whole point of the "two sources, one analysis" design. Run
exactly one of 2a / 2b.

## Input

- `tmp/mode.json`, `tmp/params.json` (from Step 0)
- Mode A: `tmp/target.json` (from Step 1a)
- Mode B: `tmp/intake.json` (from Step 1b)

## Output

- Both modes: `tmp/raw_overview.json`, `tmp/raw_detail_time.json`, `tmp/raw_meta.json`
- Mode A additionally: `tmp/raw_detail_instance.json`, `tmp/raw_exp_overview.json`,
  `tmp/raw_exp_detail.json`, `tmp/raw_tasklist.json`
- Mode B additionally: `tmp/raw_event_meta.json`, `tmp/raw_event_rows.json`

## Executor

Orchestrator running the script.

## Validation Gate

`scripts/validate_raw_report.py --raw-dir tmp --mode <A|B>`

---

## 2a — Fetch native Engage reports

### Failure Handling

- A missing **optional** block is recorded as a degradation and the run continues.
- A missing **overview** block is **FATAL** — without it there is no funnel and
  nothing downstream can be computed.

### Flow

```bash
$PY $S/scripts/fetch_engage_reports.py --project-id <PID> --task-id <TID> \
      --start-time <S> --end-time <E> --out-dir tmp
```

**Decision based on exit code:**

- **IF exit 0** → proceed to the gate.
- **IF exit 1 (overview missing)** → **FATAL**.
- **IF exit 1 (auth / project)** → re-run Step 0, then stop.

---

## 2b — Build and run ad-hoc analysis

### Failure Handling

Empty funnel rows → **EMPTY**, not FATAL. Confirm the event name and the attribution
window with the user before concluding the campaign had no effect — an empty funnel
far more often means a mis-typed event than a genuinely dead campaign.

### Flow

```bash
$PY $S/scripts/fetch_event_analysis.py --project-id <PID> \
      --steps '[{"event":"ops_view","role":"view"},{"event":"ops_click","role":"click"},{"event":"shop_buy","role":"main"}]' \
      --time-range '{"mode":"custom","startTime":"<S>","endTime":"<E>"}' \
      --window-value 24 --window-unit hour --out-dir tmp
```

`--time-range` accepts either spelling of the start/end keys
(`startTime`/`endTime` or `start_time`/`end_time`) and is respelled for whichever
generation is installed — 1.x rejects the snake_case form and 6.x rejects the
camelCase one, so the choice is not ours to make.

`role` maps to the platform metric keys: `view` → impression, `click` → click,
`main` → conversion.

**Three properties of the ad-hoc result are handled inside the script.** Each is a
place where a careless read produces a confident wrong number:

| Trap | Why it bites | How it is handled |
|---|---|---|
| **Funnel step columns are not `index + 1`** | the engine interleaves a conversion column after every step but the first — `[Totals, Step1, Step2, Conv2, Step3, Conv3]` — so a 3-step funnel's third count sits at column **4**, and reading column 3 lands on `"85.99%"` | `resolve_step_columns()` reads the parenthesised step marker in the header, falls back to the `len(title) == 2 * steps` layout, and reports the step as *unknown* when neither reading agrees instead of reading a neighbour |
| **The summary row is identified by position, not caption** | the platform renders the caption in the caller's language — `Overview` on one call, a localized stage-summary caption on the next, same host, same credentials | `canonical_label()` relabels row 0 to the `total` token the downstream parsers already know |
| **A truncated result is not a complete one** | 6.x sets `has_more` on the synchronous preview, whose row budget is fixed; every row returned is valid, they are simply not all of them | recorded in `meta.truncated` and surfaced as a completeness degradation in the final report |

**Decision based on exit code:**

- **IF exit 0 with non-empty funnel rows** → proceed to the gate.
- **IF exit 0 with empty funnel rows** → **EMPTY**. Confirm the event names and
  window with the user before concluding "no effect".
- **IF exit 1** → **FATAL**, and quote the failing step.

---

## Gate — validate the raw payload

```bash
$PY $S/scripts/validate_raw_report.py --raw-dir tmp --mode <A|B>
```

**Decision based on exit code:**

- **IF exit 0** → proceed to Step 3.
- **IF exit 1** → report which block is missing or zero, and stop.

## Error Handling Summary

| Scenario | Action | Status |
|---|---|---|
| Gate exit 0 | Proceed to Step 3 | SUCCESS |
| Optional block missing | Record degradation, continue | WARN |
| Overview block missing (A) | Report, stop | FATAL |
| Truncated result (`has_more`) | Record completeness degradation, continue | WARN |
| Empty funnel rows (B) | Confirm events with the user | EMPTY |
| Gate exit 1 | Report the failing block, stop | FATAL |

## Notes

- Mode B's whole value is that it normalizes ad-hoc output into the mode A shape.
  Nothing after this step knows which mode produced the numbers.
- `meta.truncated` must survive into the report. A silently truncated funnel reads
  as a smaller campaign, not as an incomplete fetch.
