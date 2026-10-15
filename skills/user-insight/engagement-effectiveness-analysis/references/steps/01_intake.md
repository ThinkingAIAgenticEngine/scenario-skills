# Step 1: Identify the Campaign (1a mode A / 1b mode B)

## Goal

Pin down *which* campaign is being reviewed and, for mode B, collect the campaign
description plus the recovery events that stand in for the missing platform-side
delivery metrics.

The two modes diverge here and re-converge at Step 2. Run exactly one of 1a / 1b —
the branch was already decided by `tmp/mode.json` in Step 0.

## Input

- `tmp/mode.json` (from Step 0)
- Mode A: `project_id`, optionally a campaign name instead of an id
- Mode B: whatever the user has said about the campaign, plus `project_id`

## Output

- Mode A: `tmp/target.json`
- Mode B: `tmp/intake.json`, `tmp/candidates.json`

## Executor

Orchestrator. Mode B uses script-assisted search.

---

## 1a — Identify the campaign object (mode A)

### Validation Gate

The chosen object **must** carry `hasPushRecord=true`. A campaign that never sent
has no effectiveness to review.

### Failure Handling

No object with send records → **FATAL**, and say plainly that the named campaign has
never sent. Do not fall back to a "similar" campaign.

### Flow

```bash
ae-cli engage +task_list -p <PID> --req '{"pageNum":1,"pageSize":200}'
```

**Sub-step 1a.1 — Filter candidates.**

Keep only rows with `hasPushRecord=true`.

**Sub-step 1a.2 — Read the conversion contract off the object.**

- `completionIndicatorDef` → which event the platform counts as the conversion goal.
  This is the *platform's* definition, and it is what the analysis must use.
- `expConfig.enableExp` → whether an experiment ran. When false, skip every
  experiment judgement downstream rather than reporting "no lift".

**Sub-step 1a.3 — Resolve ambiguity with the user.**

**Decision:**

- **IF exactly one candidate matches the name** → write `tmp/target.json`, proceed to Step 2a.
- **IF several match** → present the candidates (name, id, send time, audience size)
  and **ask**. Do not pick one.
- **IF none match** → **FATAL**.

### Error Handling Summary

| Scenario | Action | Status |
|---|---|---|
| One object, `hasPushRecord=true` | Write `target.json`, go to Step 2a | SUCCESS |
| Several objects match the name | Present candidates, ask the user | ASK |
| No object has send records | Report "never sent", stop | FATAL |
| Task list call fails | Re-run Step 0 auth checks, stop | FATAL |

---

## 1b — Collect the campaign description and recovery events (mode B)

### Validation Gate

`scripts/validate_intake.py tmp/intake.json`

### Failure Handling

- Missing a **REQUIRED** answer → **FATAL**, and ask for exactly those items.
- Missing `discriminator` → continue, and record the degradation. Do **not** treat
  it as fatal: it costs precision, not correctness.

### Flow

**Sub-step 1b.1 — Render the questionnaire.**

```bash
$PY $S/scripts/collect_intake.py --show --strategy-name "<name>"
```

The 11 questions and their exact wording live in `references/intake_contract.md`.
Ask them as written — the wording is what makes the answers machine-checkable.

**Sub-step 1b.2 — Resolve unknown names by search.**

```bash
$PY $S/scripts/resolve_events.py --project-id <PID> --kind events     --query push
$PY $S/scripts/resolve_events.py --project-id <PID> --kind properties --query strategy
$PY $S/scripts/resolve_events.py --project-id <PID> --kind clusters   --query <keyword>
```

`--kind` accepts `events`, `properties`, `clusters`, `tags`, `all`. When the user
cannot name an event, show the candidates **with their descriptions** and let them
choose. Never silently substitute a similarly-named event.

**Sub-step 1b.3 — Write and validate the intake.**

Fill `tmp/intake.json` from the answers, then:

```bash
$PY $S/scripts/validate_intake.py tmp/intake.json
```

**Decision based on exit code:**

- **IF exit 0** → intake complete. Proceed to Step 2b.
- **IF exit 1 (missing REQUIRED)** → ask the user for exactly the named items. Stop.
- **IF exit 1 (schema/type problem)** → **FATAL**, quote the offending field.

### Error Handling Summary

| Scenario | Action | Status |
|---|---|---|
| Intake validates, discriminator present | Proceed to Step 2b | SUCCESS |
| Intake validates, discriminator absent | Proceed, record a precision degradation | WARN |
| Required answer missing | Ask for those items, stop | ASK |
| Event name unresolvable | Show search candidates, ask | ASK |
| Intake file malformed | Report the field, stop | FATAL |

## Notes

- Mode B has no canvas id and no platform-side delivery metrics. The funnel is
  rebuilt from tracking events, which is why the event chain must be named exactly.
- `plan` / `actualTrigger` / `trigger` are **unavailable** in mode B. Their absence
  means unobservable, never zero — Step 3 relies on this distinction.
- A discriminator is the only thing that separates this campaign's events from other
  campaigns' events inside the same time window. Its absence is a real precision
  loss and is reported as such in the final report.
