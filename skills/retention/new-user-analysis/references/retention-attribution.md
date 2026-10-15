# Retention Attribution Guide (留存归因)

> **Purpose**: Phase 4 methodology — answer which dimensions and which first-day behaviors drive new-user retention. This is the single source of truth for lift thresholds, the behavior×retention split method, and cross-dimension localization.
> **Usage**: Load before Phase 4 (L3). Do NOT restate these thresholds in SKILL.md.

**Terminology (same as SKILL.md §2 anchor)**: `D0` = `首日` = `first-day` = the register day itself. `D1` = the next day (次日). Throughout this file, "did X on D0" means "did X on the register day", and is interchangeable with "首日做了 X".

---

## 1. Lift Thresholds & Sample-Size Tiers

### 1.1 Lift tiers (absolute percentage-point as PRIMARY, relative as SECONDARY)

| Tier | Absolute lift | Label | Operational meaning |
|------|--------------|-------|---------------------|
| 🔴 Critical | **≥ +10pt** | 关键行为 | Push to D0, prioritize onboarding |
| 🟡 Effective | **+5 ~ +10pt** | 有效行为 | Worth optimizing, add to funnel |
| ⚪ Weak / neutral | **< +5pt** | 弱/无关 | Do not prioritize, avoid resource waste |
| ⚫ Negative | **< 0** | 损害留存 | Investigate for friction / UX bug |

**Why absolute pt is primary**: retention baselines sit at 20–50%, so a relative-only metric misfires — a 20%-baseline dimension with +25% relative is only +5pt, not a real signal. Use absolute pt to rank; report relative lift as a second column for context.

### 1.2 Sample-size tiers (apply before any lift is trusted)

| Group sample | Handling |
|-------------|----------|
| **≥100 / group** | Trustworthy, judge normally |
| **50–100 / group** | Flag "low sample", state conclusion cautiously |
| **<50 / group** | Aggregate to monthly; suppress lift entirely |

**Minimum viable split**: each behavior split ("did X" vs "did NOT do X") must have ≥50 users per arm before a lift is reported. Otherwise output "insufficient sample" and do not rank the behavior.

---

## 2. First-Day Behavior × Retention Split Method

This is the core query pattern the rest of the skill did not previously have: joining a D0 behavior with a retention label to compute lift.

### 2.1 Steps

1. From Phase 3, take the user-confirmed key first-day events (5–8 events).
2. For each event X, split the new-user cohort into two arms:
   - **Did X on D0**: users whose `register` and first `X` fall on the same day (or within the D0 window confirmed in Gate A).
   - **Did NOT do X on D0**: the rest of the register cohort.
3. For each arm, compute retention at the confirmed windows (D1/D3/D7).
4. Lift = retention(did X) − retention(did NOT do X). Report absolute pt (primary) + relative (secondary).
5. Rank events by lift; apply §1 thresholds and sample-size tiers.

**Observation-window completeness**: report a D(n) lift only for cohorts whose entire D(n) return day has finished and whose return-event data has arrived. If "last 7 days" includes today:
- D1 is incomplete for today's register cohort; exclude that cohort from D1.
- D3 is incomplete for cohorts registered in the last 3 calendar days; exclude them from D3.
- D7 is incomplete for every cohort in that seven-day window; use an older cohort window for D7.

For each D(n), set the latest eligible register date using the project's reporting timezone and the last fully ingested event date. Keep the same eligible cohort window in both the "did X" and "did NOT do X" arms. Never treat an unfinished return day as non-retention.

### 2.2 Isolation caveat (must honor)

If the split cannot be isolated to the **new-user cohort's D0** (e.g. the behavior is also done by returning users), do NOT issue a lift — output "not new-user-isolated" and fall back to correlation-level notes. Same rule as Phase 2's first-day isolation gate.

### 2.3 Query pattern

**✅ Verified (2026-09-16, project 2)**: the retention model natively supports `filters` inside the `retention` object — you can split retention by ANY property (user_property or event_property) with a single query, no post-processing join needed.

```json
{
  "time_range": {"mode": "custom", "start_time": "...", "end_time": "..."},
  "retention": {
    "initial_event": "register",
    "return_event": "login",
    "unit_num": 1,
    "filters": [
      {"field": {"name": "media_source", "type": "user_property"}, "operator": "eq", "values": ["Organic"]}
    ]
  }
}
```

- `filters` goes INSIDE the `retention` object (NOT under metrics — retention model has no metrics).
- The filter scopes to the `initial_event` cohort. To split by dimension D, run one retention query per D value (e.g. one per channel, one per media_source).
- Result rows: `[阶段值, cohort_size, 留存人数/率, 当日, 1日, ...]` — the first two rows are the aggregate (count + rate).

**Behavior × retention lift** (verified 2026-09-17, CORRECTED): the correct method is a **SQL CTE with date-aligned join** — NOT a retention `filters` flag. The retention model's `relative_event_time` operator does NOT work on datetime user properties (validate passes, runtime returns `PARAMETER_ERROR`). So for "did X on the register day", write SQL: build the cohort from the **register EVENT** (`#event_name='register'`, `MIN("#event_time")`), join the behavior X on the SAME day, then left-join the return event one day later. Full verified pattern in `references/data-validation.md` §4.3.5.

Key gotchas (verified 2026-09-17):
1. Join identity = `#distinct_id`, all within `v_event_N`. Do NOT cross event-table ↔ user-table by identity.
2. **Cohort date = register EVENT's `#event_time`, NOT user-table `#reg_time`** — `#reg_time` skews retention ~10x (D1 collapses from 43% to 3.5%).
3. `#account_id` + register-event date also over-counts (5,342 vs correct).

---

## 3. Cross-Dimension Localization (only when a low-retention cohort fires or the user asks)

Minimal two-way cross to localize the specific low-retention population. Run ONLY after §2 or a dimension×retention split (Phase 4 step 2) has surfaced a low-retention segment.

### 3.1 Templates

| Cross | Template | Output |
|-------|----------|--------|
| Dimension × Dimension | Split cohort by `dimA × dimB`, compute retention per cell | Low-retention cell (e.g. "region=R × channel=C, D1 15%") |
| Dimension × Key behavior | Split by `dimA × (did X on D0)`, compute retention per cell | Which segment fails to convert the key behavior |
| Channel × First-day behavior | Split by `channel × (did X on D0)` | Channel whose users skip the high-lift behavior |

### 3.2 Rules

- Only cross 2 dimensions at a time; a 3-way cross explodes cell counts and breaches §1.2 sample tiers.
- Report only cells with ≥50 users; suppress sparser cells.
- Confirm the field placeholders (`{region}` / `{channel}` / `{traffic_source}`) with the user before querying — never guess the field name.

---

## 4. Output Contract (Phase 4 deliverable)

1. **Retention-attribution dashboard**: key behaviors ranked by lift (with sample-size flags) + low-retention dimensions + cross localization.
2. **One-line root cause** per low-retention cohort.
3. **Recommended focus**: the 1–2 highest-lift behaviors to push into D0, and the 1 lowest-retention dimension to intervene on.
4. **Re-check window**: e.g. "re-run Phase 4 in 14 days and compare lift stability".

---

*File version: 1.1.0 | Last updated: 2026-09-17 | Thresholds user-confirmed: D1/D3/D7 all three; lift default critical ≥+10pt, effective +5~+10pt. Behavior×retention SQL method verified (register-event date, NOT #reg_time); observation-window completeness rule added.*
