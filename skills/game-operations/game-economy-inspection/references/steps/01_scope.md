# Step 01: Define Inspection Scope

> ## ⛔ MANDATORY GATE — read before executing
>
> **All confirmations via text replies**: list numbered options, the user enters numbers. Do not fabricate user replies, do not skip confirmation nodes.

## Objective

Determine this inspection's scenario, metric scope, and time window. This is the sole user interaction window.

## Input

- [../config/scenarios.json](../config/scenarios.json) — preset scenario templates
- [../scenario_guide.md](../scenario_guide.md) — custom scenario guide

## Output

- `/tmp/game-economy-inspection/scenario.json` — selected scenario config (including window)

---

## Interaction Protocol

All options use the format `[N] English name — short description`.

---

## Execution Steps

### 1.1 Present preset scenarios

Read `../config/scenarios.json`, list scenarios:

```
Available inspection scenarios:
[1] Currency Silent Devaluation — detect nurturing currency silently devaluing (Card/RPG/SLG)
[2] Equipment Recycle Anomaly — detect abnormally rising recycle/salvage ratio
[3] Custom scenario — define inspection domains and metrics freely
```

User enters a number to select.

### 1.2 Handle selection

- **Selected [1] or [2]**: load the matching scenario config from `../config/scenarios.json`
- **Selected [3] custom**: load `../scenario_guide.md`, guide the user through scenario definition

Resolve every selected metric's required event/property placeholders from `../metric_definitions.md`. If any required mapping was skipped in Step 00, the scenario cannot run: return to Step 00 for explicit mapping confirmation or ask the user to choose another scenario. Optional breakdown properties do not block execution.

Write the scenario config to `/tmp/game-economy-inspection/scenario.json`.

### 1.3 Confirm time window

Default window: past 30 days (start = 30 days ago, end = yesterday).

```
Inspection time window confirmation:
[1] Default past 30 days — confirm
[2] Custom — enter start/end dates manually
```

User enters a number. If custom, ask the user for start/end dates (yyyy-MM-dd).

### 1.4 Confirm thresholds

Read the "Threshold Configuration" in `../config/project_mapping.md`, and present only the thresholds required by the selected scenario. **Thresholds are methodology reference values — different game ecosystems differ, MUST be confirmed or adjusted by the user, never applied blindly. Any required value still marked `[Fill in]` blocks execution until the user supplies it**:

```
Anomaly threshold confirmation (defaults from methodology reference):
- HHI index: attention 0.015/week, alert 0.025/week
- Consumption concentration: attention 0.02/week, alert 0.04/week
- Fragment accumulation: attention 0.03/week, alert 0.05/week
- Bundle conversion: attention drop 1.5%, alert drop 3%
- Equipment recycle-before-use ratio: no universal default — enter project-specific attention and alert slopes

[1] Use all populated methodology thresholds — Confirm (unavailable if any required value is blank)
[2] Adjust some thresholds — enter the items and values to adjust
```

After user confirmation or adjustment, write back `../config/project_mapping.md`.

### 1.5 Inspection plan summary confirmation (final gate)

Present the complete inspection plan, wait for user confirmation:

```
Inspection plan summary:
- Scenario: {scenario_name}
- Data domains: {domain list + metric count}
- Time window: {start} ~ {end} ({N} days)
- Anomaly thresholds: {confirmed thresholds}

[1] Confirm & Continue
[2] Re-adjust
[3] Terminate
```

User enters `1` → merge window and threshold info into `scenario.json`, proceed to Step 02.

---

## Acceptance Criteria

- [ ] Scenario selected and loaded from `scenarios.json` (or a custom scenario fully defined)
- [ ] Every event/property mapping required by the selected metrics is confirmed; skipped required mappings block execution
- [ ] Time window confirmed (default 30 days or custom dates)
- [ ] Thresholds confirmed (default or adjusted), written back to `project_mapping.md`
- [ ] `scenario.json` written to `/tmp/game-economy-inspection/` with window + thresholds merged

---

## Status Output

- `STEP_SUCCESS` — scenario, time window, thresholds confirmed
- `STEP_FATAL` — user terminated / scenario config failed to load
