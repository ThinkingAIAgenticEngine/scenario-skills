---
name: "ae-freeze-inactive-dashboards"
description: "Automatically identifies and freezes inactive dashboards with no visits in the past 30/60/90 days (configurable) using dashboard_search event data from an Audit Project, executed via ae-cli. Use when users need to identify and freeze inactive dashboards to reduce clutter and resource usage."
---

# ae-freeze-inactive-dashboards

> **CRITICAL:** Use `ae-cli` exclusively. No other HTTP endpoints or external tools.
> **CRITICAL:** Satisfy `PROJECT_ID_GATE` before execution.
> **CRITICAL:** Default action is **freeze** (`analysis dashboard freeze`), not delete. Delete only when user explicitly says "delete," confirmed one by one.
> **CRITICAL:** Present freeze candidates and receive explicit user confirmation before any write operation.

---

## Background

This Skill relies on the **Audit Project** — a dedicated TA project that records a `dashboard_search` event each time a user opens a dashboard.

Key `dashboard_search` properties:

| Property | Type | Description |
|---|---|---|
| `dashboard_id` | Number | Dashboard ID |
| `dashboard_name` | String | Dashboard name |
| `project_name` | String | Project the dashboard belongs to (used to filter target project) |
| `login_name` | String | Querying user |

---

## Configurable Parameters

Defaults apply unless the user specifies otherwise:

| Parameter | Default | Description |
|---|---|---|
| `INACTIVE_DAYS` | `30` | Dashboards with fewer than `MIN_QUERY_COUNT` queries in the past N days are inactive candidates |
| `TARGET_PROJECT` | Current conversation project | Target project to analyze |
| `AUDIT_PROJECT` | Ask user to specify, or list all projects and let user identify it | Audit project storing `dashboard_search` tracking data |
| `MIN_QUERY_COUNT` | `1` | Dashboards with query count < this value are inactive candidates |
| `OUTPUT_FORMAT` | `table` | `table / json / csv` |

---

## Execution Flow

### Step 0: Project Confirmation (PROJECT_ID_GATE)

```bash
ae-cli team +list-projects
```

- Match the target project against this returned list; `+list-projects` has no
  server-side `--query` option.
- Target project unspecified → ask the user to select from the returned list
- Audit project not specified → list all projects and ask user to identify which one is the Audit Project
- Audit project not found → **stop immediately** and output the message below; do NOT attempt any workaround (e.g. using `update_time` as a proxy):
  > This Skill relies on the `dashboard_search` event data in the Audit Project to determine dashboard query activity. The Audit Project was not found — cannot continue.
  >
  > Possible causes and next steps:
  > 1. **You do not have access to the Audit Project** → Contact your system administrator to grant your account access to the Audit Project.
  > 2. **The Audit Project has not been deployed** → Contact your CSM to request deployment.
  >
  > Once the Audit Project is deployed and access is granted, re-run this Skill.
- Record: `TARGET_PROJECT_ID`, `TARGET_PROJECT_NAME`, `AUDIT_PROJECT_ID`

---

### Step 1: Retrieve All Dashboards

```bash
ae-cli analysis dashboard list --project-id <TARGET_PROJECT_ID> \
  --fields '["dashboard_id","dashboard_name"]' --limit 50 --offset 0
```

When `has_more=true`, continue with the returned `next_offset`; do not calculate
the offset locally. If empty → output "No dashboards found" and stop.

---

### Step 2: Query Audit Project for Dashboard Activity

> **CRITICAL:** Use the `event` AI-facing definition below. Do not use SQL or raw QP.

```bash
ae-cli analysis adhoc run \
  --project-id <AUDIT_PROJECT_ID> \
  --model-type event \
  --definition '{"time_range":{"mode":"recent","unit":"day","value":<INACTIVE_DAYS>},"time_particle_size":"total","metrics":[{"event":"dashboard_search","aggregation":"total_count"}],"filters":[{"field":{"name":"project_name","type":"event_property"},"operator":"eq","values":["<TARGET_PROJECT_NAME>"]}],"groups":[{"field":{"name":"dashboard_id","type":"event_property"}}]}' \
  --format json
```

Extract `ACTIVE_DASHBOARD_IDS` = IDs with query count ≥ `MIN_QUERY_COUNT`.

If the result is truncated, use `analysis adhoc export`; do not treat a bounded
preview as the complete active-ID set. If the command reports an explicit
project-no-data condition, warn the user and treat all dashboards as inactive
candidates. A generic empty object or failed command is not evidence of no data.

---

### Step 3: Compute Sets

```
INACTIVE_DASHBOARDS = ALL_DASHBOARDS − ACTIVE_DASHBOARD_IDS
DELETED_DASHBOARDS  = audit dashboard_ids − ALL_DASHBOARDS  (historical residue; excluded from all actions)
```

---

### Step 4: Output Results & Confirm Freeze Intent

Output split tables. **Do NOT call `dashboard get` yet.**

**Output format rules (CRITICAL):**
- Output order: ① Inactive candidates table → ② Active summary (count only, no table) → ③ Deleted table
- Inactive candidates table: columns = Dashboard ID, Dashboard Name, Query Count; sorted by Query Count ascending (0 first)
- Active dashboards: output one summary line only — e.g. `🟢 Active dashboards: <n> total (query count ≥ <MIN_QUERY_COUNT>, not listed individually)`; **do NOT list individual active dashboards**
- Deleted table: columns = Dashboard ID, Query Count; sorted by Query Count ascending
- No "Recommended Action" column; table heading conveys the category
- All headers in user's language (English if user writes in English)

**Bilingual header reference:**

| English | Chinese |
|---|---|
| Dashboard ID | 看板ID |
| Dashboard Name | 看板名称 |
| Query Count | 查询次数 |
| Creator | 创建人 |
| Create Time | 创建时间 |

**Example output:**

```
=== Target Project: <NAME> (ID: <ID>) | Period: Past <N> days | Active threshold: ≥ <MIN_QUERY_COUNT> queries ===
Total dashboards: <total> | Active: <active> | Inactive candidates: <inactive> | Deleted: <deleted>

━━━ 🔴 Inactive Candidate Dashboards (<inactive> total, query count < <MIN_QUERY_COUNT> in past <N> days) ━━━
┌──────────────┬────────────────────┬─────────────┐
│ Dashboard ID │ Dashboard Name     │ Query Count │
├──────────────┼────────────────────┼─────────────┤
│ 12345        │ Dashboard A        │ 0           │
│ 67890        │ Dashboard B        │ 2           │
└──────────────┴────────────────────┴─────────────┘

🟢 Active dashboards: <active> total (query count ≥ <MIN_QUERY_COUNT>, not listed individually)

━━━ ⚫ Deleted Dashboards (<deleted> total, found in audit history but no longer exist in project — excluded from freeze) ━━━
┌──────────────┬─────────────┐
│ Dashboard ID │ Query Count │
...
└──────────────┴─────────────┘

💡 Please confirm: freeze all inactive candidate dashboards, or specify a subset?
```

**Wait for explicit user confirmation before proceeding.**

---

### Step 5: Pre-freeze Status Check & Final Confirmation

Once user confirms the target set:

**1. Call `dashboard get` for each dashboard in the confirmed target only:**

```bash
ae-cli analysis dashboard get --project-id <TARGET_PROJECT_ID> --dashboard-id <id>
```

Extract `settings.dashboard_status`, `creator.user_name`, `create_time`.

**2. Split:**
- `dashboard_status == "freeze"` → `ALREADY_FROZEN` (skip, no action)
- otherwise → `FREEZE_CANDIDATES`

**3. Output final tables and ask for final confirmation:**

```
━━━ 🔴 Dashboards to Freeze (<n> total) ━━━
┌──────────────┬────────────────────┬─────────────┬─────────┬─────────────────────┐
│ Dashboard ID │ Dashboard Name     │ Query Count │ Creator │ Create Time         │
...
└──────────────┴────────────────────┴─────────────┴─────────┴─────────────────────┘

━━━ ⚠️ Already Frozen (<n> total, excluded from this operation) ━━━
┌──────────────┬────────────────────┬─────────────┐
│ Dashboard ID │ Dashboard Name     │ Query Count │
...
└──────────────┴────────────────────┴─────────────┘

Please confirm: freeze the <n> dashboards listed above?
```

If `FREEZE_CANDIDATES` is empty:
```
✅ All confirmed dashboards are already frozen — no action needed.
```

---

### Step 6: Execute Freeze

After final user confirmation:

```bash
ae-cli analysis dashboard freeze \
  --project-id <TARGET_PROJECT_ID> \
  --dashboard-ids '[<id1>, <id2>, ...]' \
  --freeze true
```

- Never include `ALREADY_FROZEN` or `DELETED_DASHBOARDS`
- Report result per dashboard; surface errors explicitly — do not silently skip

---

## Follow-up Options

1. **Freeze (default):** `analysis dashboard freeze` after confirmation
2. **Export:** Output as JSON/CSV; no write operations
3. **Delete (only when user explicitly says "delete"):** Individual confirmation per dashboard required

> Action priority: Freeze > Export > Delete. "Handle" or "freeze" → execute freeze, never delete.

---

## Boundary & Exception Handling

| Scenario | Action |
|---|---|
| Target project not found | Stop; ask user to verify name/ID |
| Audit project not found | Stop immediately; output structured message: distinguish "no permission" (contact admin) vs "not deployed" (contact CSM); never use `update_time` or any proxy |
| No dashboards in target project | Output message and stop |
| Audit project has no `dashboard_search` data | Warn; treat all as inactive candidates |
| `dashboard_id` in audit not found in project | Mark as deleted; exclude from all actions |
| `dashboard_status = "freeze"` at Step 5 check | Mark already frozen; exclude from freeze |
| `dashboard get` call fails | Note "Status Unknown"; still include in output |
| Dashboard count > 50 | Paginate and merge all pages before processing |
| `project_name` mismatch | Prompt user to verify exact name (case-sensitive) |
| `INACTIVE_DAYS` exceeds audit data history | Warn about data range limitation |

---

## Constraints

- Never guess `project_id`, `dashboard_id`, or `project_name` — always retrieve via API
- Analytical queries must run in the **Audit Project**, not the target project
- **`dashboard get` is called lazily** — only after user confirms freeze target (Step 5), not upfront for all inactive dashboards
- Output format: separate tables by category; no single merged table; no charts; no "Recommended Action" column
- Before any write operation, present candidates and receive explicit confirmation

---

## Language Policy

Always respond in the user's language.
