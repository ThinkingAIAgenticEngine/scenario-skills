# Step 01: Data Validation

> ## ⛔ Mandatory Gate — Read Before Starting
>
> **All output MUST NOT be written to disk until user confirms via 1.8 Summary Confirmation.**
> **Step 01 not confirmed → MUST NOT proceed to Steps 02-06.**
>
> ### Confirmation Method
> All confirmations via **text replies**: you list numbered options, user enters numbers.
> Do NOT fabricate user replies. Do NOT skip confirmation checkpoints.

## Objective

Confirm the project has all needed events and properties. Generate a data inventory via standardized interaction protocol.

## Input

- [../config/project_mapping.md](../config/project_mapping.md)

## Output

Write to `{{workspace_dir}}/data_inventory.json` (after 1.8 confirmation).

---

## Interaction Protocol

All options MUST be bilingual: `[N] English name — Chinese meaning`. Do NOT provide single-language options.

**Scenario A (fuzzy match)**: `[1] level_fail — 关卡失败 (exact, 100%)` `[2] round_lose — 回合失败 (fuzzy, 80%)`
**Scenario B (config missing)**: Prompt user to enter value directly.
**Scenario C (summary)**: `[1] Confirm & Continue — 确认` `[2] Re-adjust — 调整` `[3] Terminate — 终止`
**Scenario D (timezone)**: `[1] Confirm UTC+8 — 确认` `[2] Manual — 手动修改`
**Scenario E (zero candidates)**: `[1] Manual entry — 手动输入` `[2] Skip — 跳过` (core events: only [1])
**Scenario F (missing items)**: `[1] Confirm & Continue — 确认` `[2] Go back — 返回补充`

---

## Field Priority

### Event Tiers

| Tier | Placeholders | Missing |
|------|-------------|---------|
| 🔴 Core | `register`, `daily_login`, `level_start`, `level_complete`, `ad_impression` | Cannot skip |
| 🟡 Important | `level_fail`, `session_end` | Can skip, impacts precision |
| 🟢 Optional | `ad_click` | Can skip, auxiliary only |

### Property Tiers

| Tier | Placeholders | Parent Events |
|------|-------------|---------------|
| 🔴 Core | `level_id`, `ad_type`, `ad_scene` | Level / Ad events |
| 🟡 Important | `pass_result`, `session_duration` | Level / Session |
| 🟢 Optional | `move_count`, `attempt_count`, `register_date` | Level / Register |

---

## Execution Steps

### 1.1 Read and Validate Basic Config

Read `../config/project_mapping.md`. Check: project_id (must be numeric), time window (yyy-MM-dd, ≤90d), game name, version, timezone.

Time window empty → show Scenario B. Version skipped → use date as substitute.

### 1.2 Verify Project Existence

Query project metadata:

```bash
ae-cli analysis-meta event list --project-id {{project.id}} --limit 1
```

Success = project valid. Failure → FATAL.

### 1.3 Verify Event Existence

For each event placeholder, fuzzy search with business keywords:

| Event | Keywords |
|-------|----------|
| `register` | ta_app_install, register, sign_up, create_account, signup, new_user |
| `daily_login` | ta_app_login, login, app_launch, app_open, session_start, daily_login |
| `level_start` | level_start, round_begin, stage_enter, game_start |
| `level_complete` | level_complete, round_win, stage_clear, level_pass |
| `level_fail` | level_fail, round_lose, stage_fail, game_over, level_end |
| `ad_impression` | ad_show, ad_impression, ad_display, ad_view, reward_ad |
| `ad_click` | ad_click, ad_tap |
| `session_end` | session_end, app_background, app_pause, app_exit |

```bash
ae-cli analysis-meta event list --project-id {{project.id}} --queries '["<keyword>"]'
```

Score candidates: exact name=100%, name contains=80%, desc contains=70%, partial=60%. Top-5 per event.

### 1.3.4 Batch Confirm Event Mappings

Display complete checklist in 3 groups (Exact/Fuzzy/Not Found). Confirm group 1 batch → group 2 one-by-one → group 3 one-by-one. All ⚠️ processed → exit.

### 1.4 Verify Property Existence

Search under associated events first, then global user properties:

```bash
# Event properties
ae-cli analysis-meta property list --project-id {{project.id}} --table-type event --event-name "<event>" --queries '["<keyword>"]'

# User properties
ae-cli analysis-meta property list --project-id {{project.id}} --table-type user --queries '["<keyword>"]'
```

### 1.5-1.8 Generate Inventory, Check, Sync, Confirm

Generate `data_inventory.json`, check completeness (5/5 core → READY), display summary (Scenario C). Only write files after user enters `1`.

## Status Output

- `STEP_SUCCESS` — All core events ready, user confirmed
- `STEP_EMPTY` — Core ready but ≥50% important/optional skipped
- `STEP_ERROR` — Warnings but user chose continue
- `STEP_FATAL` — Project inaccessible / core unsolvable / user terminated
