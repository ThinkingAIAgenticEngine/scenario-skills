# Step 03: Level Deep Dive

## Objective

5-direction deep analysis at the level dimension. **Parallel with Steps 02 and 04.**

## Input / Output

Input: `data_inventory.json`, [../config/project_mapping.md](../config/project_mapping.md)
Output: `{{workspace_dir}}/level_analysis.md`

### 3.0 Get Level ID Values

```bash
ae-cli analysis filter-value list \
  --project-id {{project.id}} \
  --property-name "{{prop.level_id}}" \
  --table-type event
```

### 3.1 First Level Pass Rate (§5)

Two adhoc calls (parallel):

```bash
# Start L1
ae-cli analysis adhoc run --project-id {{project.id}} --model-type event --preview-rows 100 \
  --definition '{"time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},"metrics":[{"event":"{{event.level_start}}","aggregation":"user_count"}],"filters":[{"field":{"name":"{{prop.level_id}}","type":"event_property"},"operator":"eq","values":["1"]}],"relation":"and"}'

# Complete L1
ae-cli analysis adhoc run --project-id {{project.id}} --model-type event --preview-rows 100 \
  --definition '{"time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},"metrics":[{"event":"{{event.level_complete}}","aggregation":"user_count"}],"filters":[{"field":{"name":"{{prop.level_id}}","type":"event_property"},"operator":"eq","values":["1"]}],"relation":"and"}'
```

### 3.2 IPU per 10-Level Stage (§6)

Group by level_id, manually bucket into stages.

```bash
ae-cli analysis adhoc run --project-id {{project.id}} --model-type event --preview-rows 100 \
  --definition '{"time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},"metrics":[{"event":"{{event.ad_impression}}","aggregation":"per_user_count"}],"groups":[{"field":{"name":"{{prop.level_id}}","type":"event_property"}}]}'
```

### 3.3 Per-Level Ad Trigger (§7)

Cross-group by level_id × ad_scene.

### 3.4 Level Retention Curve (§8)

Run one retention query grouped by the confirmed level property, then read the groups for N=10,20,30,40,50,60:

```bash
ae-cli analysis adhoc run --project-id {{project.id}} --model-type retention --preview-rows 100 \
  --definition '{"time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},"retention":{"initial_event":"{{event.level_complete}}","return_event":"{{event.daily_login}}","stat_type":"retention","unit_num":1,"rtn_rate_or_num":"rate","groups":[{"field":{"name":"{{prop.level_id}}","type":"event_property"}}]},"time_particle_size":"day"}'
```

### 3.5 Level Pass Rate Curve (§9)

Group by level_id, compute complete/start ratio per level.

## Status Output

- `STEP_SUCCESS` — ≥3/5 succeeded
- `STEP_ERROR` — 1-2 succeeded
- `STEP_FATAL` — all failed
