# AE-CLI Adapter Layer

> ⚠️ **This file is the tool adapter layer** — it centralizes command patterns verified against ae-cli 6.0.42. The Skill remains compatible with the supported 6.0 and 6.1 cluster lines.
> Orchestration files may link here for command syntax; methodology and metric definitions remain tool-agnostic.
>
> **Command format**: gateway commands use `ae-cli <domain> <resource> <action> --project-id <id>` (kebab-case flags). Ad-hoc analysis uses one unified `analysis adhoc run` with an AI-facing model definition — there is no separate builder step.

---

## 1. General Conventions

### Global rules

- **PROJECT_ID_GATE**: before any data query, validate the project with `ae-cli analysis-meta event list --project-id <id>`. Reuse verified context within the same session.
- **QUERY_EXISTING_FIRST**: before ad-hoc queries, search existing reports with `ae-cli analysis report list --project-id <id> --queries '["<keyword>"]'`.
- **Ad-hoc one-step**: `analysis adhoc run` compiles metadata and executes in one step. Do not handcraft QP or use removed builder commands.
- **Post-write link loop**: after a write returns a resource ID, call `ae-cli analysis-meta asset url-get` to generate the link.

### request-id

`analysis adhoc run`, `drilldown-* run` accept an optional `--request-id cli_<32 lowercase hex>` (auto-generated and printed when omitted). Use it to cancel or correlate a run.

### Empty results

Empty result set = query succeeded but no matching data. Treat as normal, do not retry.

---

## 2. Metadata Discovery (Step 00)

### List events (system metadata — actually reported)
```bash
ae-cli analysis-meta event list --project-id <project_id>
ae-cli analysis-meta event list --project-id <project_id> --queries '["<keyword>"]'
```

### List properties
```bash
# Event properties
ae-cli analysis-meta property list --project-id <project_id> --table-type event --event-name "<event_name>" --queries '["<keyword>"]'

# User properties
ae-cli analysis-meta property list --project-id <project_id> --table-type user --queries '["<keyword>"]'
```

### Query tracking plan (planned but possibly unreported)
```bash
ae-cli tracking plan get --project-id <project_id>
```

> **Data source probing order** (used in Step 00): first `analysis-meta event list` (system metadata); if empty, `tracking plan get` (tracking plan); if both empty → project not yet integrated with TE, guide the user to instrument first.

---

## 3. Project Config (Step 00)

### List accessible projects
```bash
ae-cli project info list
```

### Get project configuration (timezone, etc.)
```bash
ae-cli project info get --project-id <project_id>
```

> Read the project default timezone from the returned `default_time_zone_offset` (or the project timezone field); never hardcode it.

---

## 4. Ad-hoc Analysis (Steps 02-04)

### Key: one unified step

`analysis adhoc run` takes an **AI-facing model definition** and both resolves metadata and executes. There is no separate builder → query step.

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type <model_type> \
  --definition '<ai_facing_definition_json>' \
  --preview-rows 100
```

- `--definition` is the AI-facing model definition, NOT raw QP / events / event_view. The compiler resolves event and property names from project metadata.
- Omit `--preview-rows` to use the cluster synchronous limit; agents should normally pass `100`.
- If the result exceeds the synchronous limit, use `ae-cli analysis adhoc export` for full data.
- If metadata resolution needs clarification, the command fails with `AI_QP_COMPILE_FAILED`; inspect `meta.compile_status`, `meta.errors[]`, `meta.resolved`, `meta.warnings` and ask the user — never guess from display text.

### Model type registry

| Model | Purpose |
|-------|---------|
| event | event analysis (trends, grouping, filters) |
| retention | retained/lost users between two events |
| funnel | ordered conversion steps |
| distribution | value distribution buckets |
| attribution | conversion credit attribution |
| interval | elapsed time between two events |
| path | behavior paths before/after a source event |
| prop_analysis | user-property metrics |
| sql | SQL analysis |
| heat_map | 2D heat map (scenario model) |
| rank_list | ranking (scenario model) |
| revenue | revenue cohort metrics (scenario model) |

### Event analysis (trend line, core of slow-variable inspection)

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --definition '{"time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},"time_particle_size":"week","metrics":[{"event":"{{event.battle_start}}","aggregation":"total_count"}],"groups":[{"field":{"name":"{{prop.hero_id}}","type":"event_property"}}]}' \
  --preview-rows 100
```

Event metric aggregations (semantic spelling): without property use `total_count`, `user_count`, `per_user_count`; with a numeric property use `sum`, `avg`, `avg_per_user`, `max`, `min`, `distinct_count`, `median`, `percentile`, `variance`, `stddev`; string/date properties use `distinct_count`; boolean properties use `true_count`, `false_count`, `not_empty_count`, `empty_count`, `distinct_count`.

### Equipment recycle-before-use ratio (§11)

Query weekly distinct `{{prop.equipment_instance_id}}` counts for `{{event.equipment_recycle}}` filtered to `{{prop.was_used_before}} = false`, and for `{{event.equipment_first_use}}`, then calculate the ratio defined in §11 locally. Use only compiler-validated event definitions following the event-analysis pattern above.

Before division, verify that each equipment instance is classified once and the two sets are mutually exclusive. If `{{prop.was_used_before}}` is absent, use only a project-validated lifecycle sequence or SQL model. Otherwise mark §11 "Data Missing"; do not approximate it with raw recycle event count, recycle material amount, or `§7` holding change.

### Distribution analysis (consumption distribution, holding distribution)

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type distribution \
  --definition '{"time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},"distribution_metrics":[{"event":"{{event.currency_consume}}","aggregation":"sum","property":"{{prop.consume_amount}}"}],"groups":[{"field":{"name":"{{prop.hero_id}}","type":"event_property"}}]}' \
  --preview-rows 100
```

> Distribution filters MUST be attached to the matching `distribution_metrics[].filters` — do not use top-level `filters` or `relation`.

### Funnel analysis (nurturing bundle conversion)

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type funnel \
  --definition '{"time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},"time_particle_size":"week","funnel":{"steps":[{"event":"{{event.shop_view}}"},{"event":"{{event.purchase_complete}}"}],"window":{"value":7,"unit":"day"}}}' \
  --preview-rows 100
```

> Step-level filters use the same field-reference shape as global filters: `{"filters":[{"field":{"name":"{{prop.shop_category}}","type":"event_property"},"operator":"eq","values":["nurturing"]}]}`. If the compiler rejects a field name, follow `meta.errors[]` feedback.

### Retention analysis (nurturing-active vs stagnant user comparison)

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type retention \
  --definition '{"time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},"time_particle_size":"week","retention":{"initial_event":"{{event.currency_consume}}","return_event":"{{event.daily_login}}","stat_type":"retention","unit_num":7,"rtn_rate_or_num":"rate"}}' \
  --preview-rows 100
```

> For totals, omit `time_particle_size` and read the overall figure from the result.

### Resolve an exact stored value

```bash
ae-cli analysis filter-value list \
  --project-id <project_id> \
  --property-name <property_name> \
  --table-type <event|user> \
  [--event-name <event_name>]
```

---

## 5. User Drilldown (Step 04 attribution)

The drilldown flow is context-driven; coordinates come only from the returned preview.

```bash
# 1) adhoc run returns query_context_id + sources[].drilldown
# 2) read the coordinate options lazily
ae-cli analysis query-context get --project-id <project_id> --query-context-id <query_context_id> --source '<source_selector_json>'

# 3) drill into users/entities behind one cell
ae-cli analysis drilldown-entities run \
  --project-id <project_id> \
  --query-context-id <query_context_id> \
  --source '<source_selector_json>' \
  --coordinate '<coordinate_json>' \
  --preview-rows 100

# 4) follow one user's event sequence (only when step 3 returns drilldown_context_id + canonical user_id)
ae-cli analysis drilldown-user-events run \
  --project-id <project_id> \
  --drilldown-context-id <drilldown_context_id> \
  --user-id <canonical_user_id> \
  --preview-rows 100
```

Rules:
- The selectable population is exactly the returned preview after `--preview-rows`; never invent coordinates.
- Assemble `--coordinate` only from `row_options` / `column_options` / `metric_options` fragments returned by `query-context get`; never pass `target_id`, raw QP, or inferred values.
- `drilldown-entities run` returns canonical `user_id` (and `drilldown_context_id` when user-event follow-up is allowed). Never substitute another identity field.
- Exports never create a drilldown context.

---

## 6. Report Persistence (Step 05 optional)

### List existing reports
```bash
ae-cli analysis report list --project-id <project_id> --queries '["<keyword>"]'
```

### Save inspection query as report
```bash
ae-cli analysis report create \
  --project-id <project_id> \
  --report-name "Economy Ecology Inspection - HHI Trend" \
  --model-type event \
  --definition '<ai_facing_definition_json>'
```

> `--definition` is the same AI-facing model definition shape as `adhoc run`.

---

## 7. Alert Configuration (Step 05 optional)

### Create threshold alert
```bash
ae-cli analysis alert create \
  --project-id <project_id> \
  --definition-request '<alert_definition_request_json>'
```

> `--definition-request` is a structured alert definition JSON using snake_case field names.

---

## 8. Resource Links (post-write)

### Get a clickable resource link
```bash
ae-cli analysis-meta asset url-get --project-id <project_id> --resource-type dashboard --resource-id <id>
```

> After creating a report / alert / dashboard, call this to return the clickable link.

---

## 9. Common Filter Operators

| Operator | Meaning |
|----------|---------|
| `eq` | Equals |
| `neq` | Not equals |
| `gt` / `gte` | Greater than / greater than or equal |
| `lt` / `lte` | Less than / less than or equal |
| `contains` / `not_contains` | Contains / does not contain |
| `exists` / `not_exists` | Has value / no value |
| `between` | Between (exactly two values) |
| `in_cluster` / `not_in_cluster` | In cluster / not in cluster |

---

## 10. Time Range Modes

| Mode | Meaning |
|------|---------|
| `recent` | Most recent N units (including today/current unit) |
| `previous` | Past N units (excluding today/current unit) |
| `custom` | Explicit `start_time` / `end_time` |
| `start_to_today` | From a fixed `start_time` through today |
| `start_to_yesterday` | From a fixed `start_time` through yesterday |

Do NOT use `mode=relative`, `relativeTime`, `begin`, or `end`.

---

## 11. Parallel Invocation Convention

Fire all independent `adhoc run` calls in one parallel batch; aggregate after all return:

```
Batch 1: adhoc run × N (parallel, one per domain/metric)
  ↓ all returned
Batch 2: query-context get → drilldown-entities run × N (parallel, per anomaly signal)
  ↓ all returned, aggregate results
```
