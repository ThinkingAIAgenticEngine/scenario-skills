# Step 05: User Segmentation

## Objective

Segment users by ad niche and content consumption. Compare retention and activity across groups.

**Depends on Step 02 baseline.**

## Input / Output

Input: `data_inventory.json`, `core_diagnostics.md`, [../config/project_mapping.md](../config/project_mapping.md)
Output: `{{workspace_dir}}/segmentation_report.md`

### 5.0 Preparation

Read Step 02 results for overall ad distribution and D1 levels baseline. Step 06 will refine intervals.

### 5.1 Ad Niche Segmentation (§12)

#### 5.1.1 Count D1 Ad Distribution

```bash
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "metrics":[{"event":"{{event.ad_impression}}","aggregation":"per_user_count"}]
  }'
```

#### 5.1.2 Create Clusters

```bash
# Zero ad
ae-cli analysis user-cluster create \
  --project-id {{project.id}} \
  --cluster-name "ad_niche_zero" \
  --display-name "Zero Ad Users" \
  --definition-request '{"type":"condition","conditions":{"items":[{"type":"event","event":"{{event.ad_impression}}","operator":"eq","value":0,"aggregation":"count","time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"}}],"relation":"and"}}'

# Light (1 ~ X), Medium (X+1 ~ Y), Heavy (>Y) — intervals from data distribution
ae-cli analysis user-cluster create --project-id {{project.id}} --cluster-name "ad_niche_light" --display-name "Light Ad Users" --definition-request '<condition_definition_request_json>'
ae-cli analysis user-cluster create --project-id {{project.id}} --cluster-name "ad_niche_medium" --display-name "Medium Ad Users" --definition-request '<condition_definition_request_json>'
ae-cli analysis user-cluster create --project-id {{project.id}} --cluster-name "ad_niche_heavy" --display-name "Heavy Ad Users" --definition-request '<condition_definition_request_json>'
```

#### 5.1.3 Compare

For each cluster, compute D2 retention (§1), avg levels (§3), daily login count.

### 5.2 Content Consumption Segmentation (§13)

#### 5.2.1 Count D1 Levels

```bash
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "metrics":[{"event":"{{event.level_complete}}","aggregation":"per_user_count"}]
  }'
```

#### 5.2.2 Create Clusters

Light (≤{{threshold.content_light_max}}), Medium (≤{{threshold.content_medium_max}}), Heavy (≤{{threshold.content_heavy_max}}), Overdraft (>{{threshold.content_heavy_max}}).

#### 5.2.3 Compare

D2, D3 retention, D3-7 daily logins per cluster.

### 5.3 Write

```markdown
# User Segmentation

## Ad Niche
| Segment | Users | Share | D2 | Avg Levels |

## Content Consumption
| Segment | Users | Share | D2 | D3-7 Logins |
```

## Status Output

- `STEP_SUCCESS` — ≥1 dimension fully succeeded
- `STEP_ERROR` — Clusters created but comparison failed
- `STEP_FATAL` — All cluster creations failed
