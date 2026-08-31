# Step 02: Baseline Query

## Objective

Pull 30-day trend data in parallel by domain to establish the baseline for slow-variable judgment.

## Input

- `/tmp/game-economy-inspection/scenario.json` — scenario config (domain + metric list + window)
- [../metric_definitions.md](../metric_definitions.md) — definitions of each metric (§N)

## Output

- `/tmp/game-economy-inspection/baseline_{domain}.json` — baseline data per domain

---

## Execution Steps

### 2.1 Read scenario config

Extract from `scenario.json`:
- Domain list and each domain's metric list
- Time window (start/end)

### 2.2 Parallel query by domain

**Core principle**: one query per metric, execute in parallel grouped by domain. See the adapter layer for tool invocation.

For each metric:
1. Read the corresponding §N six-element definition (Intent/Semantics/Input/Dimension/Judgment/Output) from `../metric_definitions.md`
2. Replace `{{event.xxx}}` / `{{prop.xxx}}` placeholders with actual field names from `../config/project_mapping.md`
3. Construct the query (use `time_particle_size=week` to pull the 30-day trend, about 4 weekly-granularity data points)
4. Execute the query

**Parallel strategy**: queries are mutually independent across domains and across metrics within a domain — fire in one parallel batch.

### 2.3 Persist results

After each domain's queries complete, write results to `/tmp/game-economy-inspection/baseline_{domain}.json`.

Structure:
```json
{
  "domain": "battle",
  "metrics": {
    "pvp_hhi": [
      {"week": "2026-07-20", "value": 0.18},
      {"week": "2026-08-16", "value": 0.33}
    ]
  }
}
```

### 2.4 Data completeness check

For each domain, check:
- Whether there are ≥ 4 data points (one per week, 30 days ≈ 4 weeks)
- Whether data is continuous (no large gaps)
- If a domain's data is insufficient → mark `STEP_EMPTY`, annotate "insufficient data" in the final report

---

## Acceptance Criteria

- [ ] `baseline_{domain}.json` written for every domain in the scenario
- [ ] Every domain has ≥4 weekly data points with no large gaps
- [ ] Insufficient-data domains marked `STEP_EMPTY` for the report

---

## Status Output

- `STEP_SUCCESS` — all domain queries completed, data complete
- `STEP_EMPTY` — some domains have insufficient data (continue, annotate in report)
- `STEP_ERROR` — individual queries failed (continue, annotate "Data Missing" in report)
