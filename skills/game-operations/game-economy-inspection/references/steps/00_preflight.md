# Step 00: Pre-flight Check & Data Validation

> ## ⛔ MANDATORY GATE — read before executing
>
> **Event/property mapping MUST be confirmed by the user via numbered text replies. Do not fabricate user replies, do not skip confirmation nodes.**
> **Mapping not confirmed → MUST NOT proceed to Step 01.**

## Objective

Confirm the runtime environment is ready and complete the "business concept → actual field" mapping: probe event data sources, fuzzy-match event/property names, and write back the config after user confirmation.

## Input

- [../config/project_mapping.md](../config/project_mapping.md) — contains the "Match keywords" column

## Output

- Confirmed project_id
- Written-back event/property mapping (into ../config/project_mapping.md)
- Working directory `/tmp/game-economy-inspection/`

---

## Interaction Protocol

All options use the format `[N] English name — short description`.

**Core principle: all uncertain values (timezone, event names, property names, distinguishing properties) MUST be handed to the user for confirmation — never assume.** Fuzzy matching only narrows the candidate range; the final mapping MUST be approved by the user.

- **Scenario A (exact match)**: `[1] currency_earn — currency earned (exact, 100%)`
- **Scenario B (fuzzy match)**: `[1] gold_earn — gold earned (fuzzy, 80%)` `[2] item_gain — item gained (fuzzy, 70%)`
- **Scenario C (summary confirmation)**: `[1] Confirm & Continue` `[2] Re-adjust`
- **Scenario D (timezone confirmation)**: `[1] UTC+8 — project default timezone` `[2] Manual entry — enter another offset`
- **Scenario E (zero candidates)**: `[1] Manual entry` `[2] Skip`

---

## Execution Steps

### 0.1 Verify ae-cli is available

```bash
ae-cli config current
```

Failure → `STEP_FATAL`, prompt the user to install and configure ae-cli first.

### 0.2 Confirm project_id and timezone

**project_id**:

1. Read the `Project ID` from `../config/project_mapping.md`
2. Already filled → use directly; empty → `ae-cli project info list` to list projects for the user to choose, then write back

**Timezone (do not hardcode — hand to project or user confirmation)**:

1. Read the `Timezone` field from `../config/project_mapping.md`; if filled → use directly
2. Empty → query the project's default timezone:
   ```bash
   ae-cli project info get --project-id <project_id>
   ```
   Read the project default timezone from the returned project config (e.g. the default timezone offset field, `8` = UTC+8)
3. Present to the user for confirmation (Scenario D):

   ```
   Timezone confirmation:
   [1] UTC+8 — project default timezone
   [2] Manual entry — enter another timezone offset
   ```

4. Write back the `Timezone` field in `../config/project_mapping.md`

### 0.3 Probe event data sources

**This is critical — event data has two sources, probe in priority order:**

```bash
# Source 1: system metadata (events actually reported by SDK)
ae-cli analysis-meta event list --project-id <project_id>
```

Judgment:

| Probe result | Meaning | Action |
|--------------|---------|--------|
| Non-empty, has nurturing/economy-related events | Project is instrumented, has actual data | Data source = system metadata, go to 0.4 |
| Empty or key events missing | Possibly not instrumented, or has a tracking plan but not reported | Continue to source 2 |
| Error / no permission | Wrong project_id or no permission | `STEP_FATAL` |

If system metadata is insufficient, query the tracking plan:

```bash
# Source 2: tracking plan (user-planned instrumentation, possibly not actually reported)
ae-cli tracking plan get --project-id <project_id>
```

- Tracking plan non-empty → data source = tracking plan, prompt the user "based on the planned tracking plan, may have no actual data yet"
- Tracking plan also empty → `STEP_FATAL`, prompt: project not yet integrated with TE or not instrumented; instrument the SDK first

### 0.4 Event name matching confirmation

For each `{{event.xxx}}` placeholder in the `../config/project_mapping.md` event table, fuzzy-search using the "Match keywords":

```bash
ae-cli analysis-meta event list --project-id <project_id> --queries '["<keyword>"]'
```

Score candidates: exact name=100%, name contains=80%, description contains=70%, partial=60%. Top-5 candidates per event.

**Grouped confirmation**:
1. Exact matches (≥90%) → list in batch, user confirms all at once
2. Fuzzy matches (60-90%) → confirm one by one (Scenario B)
3. Zero candidates (<60% or no result) → confirm one by one: manual entry or skip (Scenario E)

### 0.5 Property name matching confirmation

For each `{{prop.xxx}}` in the property table, fuzzy-search under its parent event:

```bash
# Event properties
ae-cli analysis-meta property list --project-id <project_id> --table-type event --event-name "<event>" --queries '["<keyword>"]'

# User properties
ae-cli analysis-meta property list --project-id <project_id> --table-type user --queries '["<keyword>"]'
```

Confirm in the same grouped manner.

### 0.6 Event merge scenario confirmation

If the user states "earn and consume are the same event" (or matching reveals multiple concepts hitting the same event), confirm the distinguishing property:

```
Detected that currency_earn and currency_consume may map to the same event.
Please confirm the distinguishing property:
[1] flow_type — flow type (earn/consume)
[2] Other property — manual entry
```

After confirmation, record in the `../config/project_mapping.md` "Distinguishing filter" column, e.g. `flow_type = earn` / `flow_type = consume`.

### 0.7 Summary confirmation + write-back

Present the complete mapping list (Scenario C); after user confirmation, write back the "Actual name" and "Distinguishing filter" columns of `../config/project_mapping.md`.

### 0.8 Create working directory

```bash
rm -rf /tmp/game-economy-inspection && mkdir -p /tmp/game-economy-inspection
```

---

## Acceptance Criteria

- [ ] project_id confirmed (non-empty, validated via `analysis-meta event list`)
- [ ] Timezone confirmed and written back to `project_mapping.md`
- [ ] Every `{{event.xxx}}` / `{{prop.xxx}}` has an actual name written back, or is explicitly skipped by the user
- [ ] Working directory `/tmp/game-economy-inspection/` created

---

## Status Output

- `STEP_SUCCESS` — data source confirmed, event/property mapping written back
- `STEP_FATAL` — ae-cli unavailable / project inaccessible / no event data source / user terminated
