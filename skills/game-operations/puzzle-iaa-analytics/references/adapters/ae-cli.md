# AE-CLI Adapter Layer

> ⚠️ **This document is an optional tool adapter** — only load when the runtime environment provides `ae-cli`.
> The SKILL.md and references body MUST NOT reference this document. To switch BI tools, replace this file only.

---

## 1. General Conventions

### Global Rules

Before any ae-cli command, observe the mandatory constraints from the `ae-analysis` skill:

- **PROJECT_ID_GATE**: Verify `project_id` via `ae-cli analysis-meta event list --project-id <id>` before any data query. Reuse verified project context within the same session.
- **QUERY_EXISTING_FIRST**: Before ad-hoc queries, search existing reports with `ae-cli analysis report list --project-id <id> --queries '["<keyword>"]'`.
- **Write Post-link**: After successful writes that return `resource_id`, generate a clickable link.

### requestId / context

Each `ae-cli analysis adhoc run` call returns a `query_context_id` for follow-up queries (drilldown, result clusters).

### Empty Results

An empty result set means the query succeeded but matched no data — treat as a normal result, do not retry.

---

## 2. Metadata Discovery (Step 01)

### List Events
```bash
ae-cli analysis-meta event list --project-id <project_id> --queries '["<keyword>"]'
```

### List Properties
```bash
# Event properties
ae-cli analysis-meta property list --project-id <project_id> --table-type event --event-name "<event_name>" --queries '["<keyword>"]'

# User properties
ae-cli analysis-meta property list --project-id <project_id> --table-type user --queries '["<keyword>"]'
```

---

## 3. Ad-Hoc Analysis (Steps 02-06)

All model analysis uses the unified `ae-cli analysis adhoc run` command. No separate builder step needed — the `--definition` JSON contains the complete AI-facing model definition.

### Supported model_type values

`event`, `retention`, `funnel`, `distribution`, `attribution`, `interval`, `path`, `prop_analysis`, `sql`, `heat_map`, `rank_list`, `revenue`

### Event Analysis
```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range": {"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "metrics": [
      {"event":"{{event.level_complete}}","aggregation":"user_count"}
    ],
    "groups": [
      {"field":{"name":"{{prop.level_id}}","type":"event_property"}}
    ]
  }'
```

### Retention Analysis
```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type retention \
  --preview-rows 100 \
  --definition '{
    "time_range": {"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "retention": {
      "initial_event":"{{event.daily_login}}",
      "return_event":"{{event.daily_login}}",
      "stat_type":"retention",
      "unit_num":1,
      "rtn_rate_or_num":"rate"
    },
    "time_particle_size":"day"
  }'
```

### Funnel Analysis
```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type funnel \
  --preview-rows 100 \
  --definition '{
    "time_range": {"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "funnel": {
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

> For totals: do not pass `time_particle_size=total`. Omit the field and read the overall figure from the result.

---

## 4. Filter Value Lookup

```bash
ae-cli analysis filter-value list \
  --project-id <project_id> \
  --property-name "{{prop.level_id}}" \
  --table-type event
```

---

## 5. User Drilldown

### Get User/Entity List
```bash
ae-cli analysis drilldown-entities run \
  --project-id <project_id> \
  --query-context-id "<query_context_id>" \
  --source '<source_selector_json>' \
  --coordinate '<coordinate_json>' \
  --preview-rows 100
```

Parameters:
- `query_context_id`: from the original synchronous `analysis adhoc run` result.
- `source`: select only from `sources[].drilldown` returned by that preview.
- `coordinate`: assemble only from `analysis query-context get` row, column, and metric options; never guess a date, step, or target ID.

### Get User Event Sequences
```bash
ae-cli analysis drilldown-user-events run \
  --project-id <project_id> \
  --drilldown-context-id "<drilldown_context_id>" \
  --user-id "<user_id>" \
  --event-name-filter "<optional_event_name_filter>" \
  --preview-rows 100
```

---

## 6. User Clusters and Tags

### List Clusters
```bash
ae-cli analysis user-cluster list --project-id <project_id> --queries '["<keyword>"]'
```

### Create Cluster
```bash
ae-cli analysis user-cluster create \
  --project-id <project_id> \
  --cluster-name "ad_niche_zero" \
  --display-name "Zero Ad Users" \
  --definition-request '{"type":"condition","conditions":{"relation":"and","items":[{"type":"event","event":"{{event.ad_impression}}","operator":"eq","value":0,"aggregation":"count","time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"}}]}}'
```

### Create Cluster from Analysis Result
```bash
ae-cli analysis query create-result-cluster \
  --project-id <project_id> \
  --query-context-id "<query_context_id>" \
  --source '<source_selector_json>' \
  --coordinate '<coordinate_json>' \
  --cluster-name "churned_users" \
  --display-name "Churned Users"
```

### List Tags
```bash
ae-cli analysis user-tag list --project-id <project_id> --queries '["<keyword>"]'
```

### Create Tag (Metric Type)
```bash
ae-cli analysis user-tag create \
  --project-id <project_id> \
  --tag-name "d1_ad_count" \
  --display-name "Day 1 Ad Count" \
  --definition-request '{"type":"metric","metric":{"event":"{{event.ad_impression}}","aggregation":"count","time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"}}}'
```

---

## 7. Common Filter Operators

| operator | meaning |
|----------|---------|
| `eq` | equals |
| `neq` | not equals |
| `gt` / `gte` | greater than / greater than or equal |
| `lt` / `lte` | less than / less than or equal |
| `contains` / `not_contains` | contains / does not contain |
| `exists` / `not_exists` | has value / no value |
| `between` | between |
| `is_true` / `is_false` | boolean |
| `in_cluster` / `not_in_cluster` | in cluster / not in cluster |

---

## 8. Time Range Modes

| mode | meaning |
|------|---------|
| `recent` | most recent N units (including today) |
| `previous` | past N units (excluding today) |
| `custom` | explicit start/end dates |

Do NOT use `mode=relative`, `relativeTime`, `begin`, or `end`.

---

## 9. Parallel Invocation Convention

All independent `ae-cli analysis adhoc run` calls fire in one batch, wait for all, then aggregate:

```
Batch 1: adhoc run × N (parallel, each with different model_type + definition)
  ↓ all returned
Batch 2: drilldown-entities × N (parallel, each with different query_context_id)
  ↓ all returned, aggregate results
```
