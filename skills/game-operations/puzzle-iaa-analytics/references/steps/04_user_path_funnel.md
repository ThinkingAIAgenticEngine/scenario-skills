# Step 04: User Path and Churn Points

## Objective

Funnel analysis and churned user behavior tracing. **Parallel with Steps 02 and 03.**

## Input / Output

Input: `data_inventory.json`, [../config/project_mapping.md](../config/project_mapping.md)
Output: `{{workspace_dir}}/user_path_analysis.md`

### 4.1 Register → First 10 Levels Funnel (§10)

6-step funnel, 7-day window:

```bash
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type funnel \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "funnel":{
      "steps":[
        {"event":"{{event.register}}"},
        {"event":"{{event.level_start}}","filters":[{"field":{"name":"{{prop.level_id}}","type":"event_property"},"operator":"eq","values":["1"]}]},
        {"event":"{{event.level_complete}}","filters":[{"field":{"name":"{{prop.level_id}}","type":"event_property"},"operator":"eq","values":["1"]}]},
        {"event":"{{event.ad_impression}}"},
        {"event":"{{event.level_complete}}","filters":[{"field":{"name":"{{prop.level_id}}","type":"event_property"},"operator":"eq","values":["5"]}]},
        {"event":"{{event.level_complete}}","filters":[{"field":{"name":"{{prop.level_id}}","type":"event_property"},"operator":"eq","values":["10"]}]}
      ],
      "window":{"unit":"day","value":7}
    }
  }'
```

Judgment: 1→2 = tech, 3→4 = ad deterrence, 4→5 = weak content.

### 4.2 Churned User Behavior Trace (§11)

#### 4.2.1 Identify churned users

Retention analysis, lost side, `unit_num={{threshold.churn_definition_days}}`:

```bash
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type retention \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "retention":{"initial_event":"{{event.daily_login}}","return_event":"{{event.daily_login}}","unit_num":{{threshold.churn_definition_days}},"rtn_rate_or_num":"rate","stat_type":"lost"},
    "time_particle_size":"day"
  }'
```

Save the `query_context_id` and the matching `sources[].drilldown` selector from the synchronous result. Run `ae-cli analysis query-context get --project-id {{project.id}} --query-context-id <query_context_id> --source '<source_selector_json>'`, then choose one coordinate only from its returned row, column, and metric options.

#### 4.2.2 Drilldown churned user list

```bash
ae-cli analysis drilldown-entities run \
  --project-id {{project.id}} \
  --query-context-id "<query_context_id>" \
  --source '<source_selector_json>' \
  --coordinate '<coordinate_json>' \
  --preview-rows 50
```

Sample 30-50 users from results. Preserve the returned canonical `user_id` and `drilldown_context_id`; do not substitute another identifier.

#### 4.2.3 Query user behavior sequences (max 5 concurrent)

```bash
ae-cli analysis drilldown-user-events run \
  --project-id {{project.id}} \
  --drilldown-context-id "<drilldown_context_id>" \
  --user-id "<user_id>" \
  --event-name-filter "<optional_event_name_filter>" \
  --preview-rows 100
```

#### 4.2.4 Aggregate

Compute: stuck-level distribution, fail-ad-fail pattern, frustration exit rate, no-ad exit rate.

### 4.3 Write

See [../templates/churn_analysis.md](../templates/churn_analysis.md) for output format.

## Status Output

- `STEP_SUCCESS` — Funnel + ≥20 user traces succeeded
- `STEP_ERROR` — Only funnel succeeded
- `STEP_EMPTY` — No funnel data
- `STEP_FATAL` — Prerequisites missing
