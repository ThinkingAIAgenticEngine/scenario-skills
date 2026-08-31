# Step 02: Core Diagnostics

## Objective

Execute 4 core diagnostics in parallel: retention decay, play duration, level progress, ad behavior.

## Input

- `{{workspace_dir}}/data_inventory.json`
- [../config/project_mapping.md](../config/project_mapping.md)

## Output

Write to `{{workspace_dir}}/core_diagnostics.md`

## Execution Steps

### 2.1 Retention Decay (§1)

D2, D3, D7 retention analysis using `{{event.daily_login}}` as initial + return.

```bash
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type retention \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "retention":{"initial_event":"{{event.daily_login}}","return_event":"{{event.daily_login}}","stat_type":"retention","unit_num":1,"rtn_rate_or_num":"rate"},
    "time_particle_size":"day"
  }'
```

> Run 3 times with `unit_num=1,3,7` (parallel). Calculate decay ratios from daily results.

### 2.2 Play Duration (§2)

Per-user average of `{{prop.session_duration}}` from `{{event.session_end}}`, grouped by day.

```bash
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "metrics":[{"event":"{{event.session_end}}","aggregation":"avg","property":"{{prop.session_duration}}"}],
    "time_particle_size":"day"
  }'
```

Judgment: D1/D2 > `{{threshold.duration_overdraft_ratio}}` → overdraft risk.

### 2.3 Levels Completed per User (§3)

```bash
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "metrics":[{"event":"{{event.level_complete}}","aggregation":"per_user_count"}],
    "time_particle_size":"day"
  }'
```

Judgment: D1 > `{{threshold.overdraft_warning}}` → too fast.

### 2.4 Ad Placement Breakdown (§4)

Two independent group-by analyses on `{{event.ad_impression}}`:

```bash
# By ad type
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "metrics":[{"event":"{{event.ad_impression}}","aggregation":"total_count"}],
    "groups":[{"field":{"name":"{{prop.ad_type}}","type":"event_property"}}]
  }'

# By ad scene
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "metrics":[{"event":"{{event.ad_impression}}","aggregation":"total_count"}],
    "groups":[{"field":{"name":"{{prop.ad_scene}}","type":"event_property"}}]
  }'
```

### 2.5 Aggregate and Write

```markdown
# Core Diagnostics Results

## Retention Decay
| Metric | Value |
| Avg D2 Retention | XX% |
| D2→D3 Decay | XX% |
| D3→D7 Decay | XX% |
| Judgment | Normal / Mid-term Fracture |

## Play Duration
| Metric | D1 | D2 | D3-7 |
| Avg Duration (min) | XX | XX | XX |

## Levels Completed
| Metric | D1 | D2 | D3-7 |
| Avg Levels | XX | XX | XX |

## Ad Placement
| Ad Type | Impressions | Share |
```

## Parallel Strategy

All 4 sub-analyses independent. Batch 1: fire all `adhoc run` calls in parallel. Batch 2: aggregate.

## Status Output

- `STEP_SUCCESS` — ≥3/4 succeeded
- `STEP_ERROR` — 1-2 succeeded
- `STEP_FATAL` — all failed
