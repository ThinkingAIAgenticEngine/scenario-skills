# AE-CLI Adapter Layer

> ⚠️ This file is the tool adapter layer — load it only when the runtime environment provides `ae-cli`.
> SKILL.md and the references body do not embed ae-cli command details outside this file; when switching BI tools only this file needs to be replaced.
> The `--definition` field format follows `references/ai_models.md` of the ae-analysis skill (snake_case).

---

## 1. Global Conventions

- **Project gate**: verify project_id via `ae-cli analysis-meta event list --project-id <project_id>` before data queries; reuse the verified project context within the same session.
- **Empty result**: `ok:true` with empty data = query succeeded but no matching data; treat as a normal result, do not retry.
- **Request id**: `--request-id cli_<32 lowercase hex>` (when omitted, ae-cli auto-generates it and prints it to stderr).

---

## 2. Metadata Discovery (Step 01)

```bash
# Event catalog
ae-cli analysis-meta event list --project-id <project_id>

# Property catalog
ae-cli analysis-meta property list --project-id <project_id>
```

---

## 3. Property Candidate Values (Step 01 drama-identifier detection / Step 02 episode list)

```bash
ae-cli analysis filter-value list \
  --project-id <project_id> \
  --property-name <property name> \
  --table-type event \
  --event-name <event name>
```

---

## 4. Ad-Hoc Analysis (Step 02)

All model analyses uniformly use `ae-cli analysis adhoc run`; `--definition` is the complete AI-facing JSON (snake_case). There is no separate builder step.

Supported model_type values: `event`, `retention`, `funnel` (the three used by this skill).

### event

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range": {"mode": "custom", "start_time": "...", "end_time": "..."},
    "metrics": [{"event": "...", "aggregation": "user_count"}],
    "groups": [{"field": {"name": "...", "type": "event_property"}}]
  }'
```

### funnel

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type funnel \
  --preview-rows 100 \
  --definition '{
    "time_range": {"mode": "custom", "start_time": "...", "end_time": "..."},
    "funnel": {
      "steps": [
        {"event": "...", "filters": [{"event_property_name": "...", "operator": "eq", "values": ["1"]}]},
        {"event": "..."}
      ],
      "window": {"value": 5, "unit": "minute"}
    }
  }'
```

> Funnel step filters use `event_property_name` (a plain string), NOT a `field` object. (Event metric-level / top-level filters DO use `field` objects — see the event example above.)

### retention

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type retention \
  --preview-rows 100 \
  --definition '{
    "time_range": {"mode": "custom", "start_time": "...", "end_time": "..."},
    "retention": {
      "initial_event": "...",
      "initial_filters": [{"event_property_name": "...", "operator": "eq", "values": ["..."]}],
      "initial_filter_relation": "and",
      "return_event": "...",
      "return_filters": [{"event_property_name": "...", "operator": "eq", "values": ["..."]}],
      "return_filter_relation": "and",
      "stat_type": "retention",
      "unit_num": 1,
      "rtn_rate_or_num": "rate"
    }
  }'
```

> Retention supports event-property filters on the initial/return events via `initial_filters` / `return_filters`. Use `event_property_name` (a plain string), NOT a `field` object; do not use top-level `filters` or `retention.filters`. Omit the filter keys entirely when no event-level filter is needed.

---

## 5. Playback Detail (Dimension 3 pacing / Dimension 6 binge / churn location)

```bash
ae-cli analysis event-detail export \
  --project-id <project_id> \
  --definition '{
    "event": "...",
    "time_range": {"mode": "absolute", "start_time": "... 00:00:00", "end_time": "... 23:59:59"},
    "filters": {"relation": "and", "items": [
      {"field": {"name": "...", "type": "event_property"}, "operator": "eq", "values": ["..."]}
    ]},
    "properties": ["#user_id", {"name": "...", "type": "event_property"}, "#event_time"],
    "sort": [{"field": "#event_time", "order": "asc"}]
  }' \
  --artifact-format csv --output <temp file>
```

> Event-detail uses `mode: absolute` (NOT `custom`) for a fixed window, or `mode: relative` with `relative_date_range`. Its optional `filters` is a wrapper object `{"relation": "...", "items": [...]}`, not a bare array. `--output <file>` implies waiting for the async artifact; alternatively poll with `analysis run inspect` and download with `analysis artifact download`.

---

## 6. Result and Error Handling

| Result | Meaning | Handling |
|------|------|------|
| `ok:true` with data | Success | Read `rows` / `result` |
| `ok:true` with empty data | Success but no matching data | Inform the user, do not retry |
| `AI_QP_COMPILE_FAILED` | Metadata resolution failed | Check `meta.errors` / `meta.resolved` and follow the ae-analysis metadata_resolution flow |
| `ok:false` | Failure | Keep `error.code` / `error.message`, do not guess parameters and retry |

Query times out or full results needed → switch to `ae-cli analysis adhoc export` (async, returns an artifact).

---

## 7. Common filter Operators

`eq` / `neq` / `gt` / `gte` / `lt` / `lte` / `contains` / `not_contains` / `exists` / `not_exists` / `between` / `is_true` / `is_false`

### Filter shape by position (verified against ae-cli 6.1.x)

| Position | Shape |
|------|------|
| event metric `filters` / top-level `filters` | `{"field": {"name": "...", "type": "event_property"}, "operator": "eq", "values": ["..."]}` |
| funnel step `filters` | `{"event_property_name": "...", "operator": "eq", "values": ["..."]}` |
| retention `initial_filters` / `return_filters` | `{"event_property_name": "...", "operator": "eq", "values": ["..."]}` |
| event-detail `filters` | `{"relation": "and", "items": [{"field": {"name": "...", "type": "event_property"}, "operator": "eq", "values": ["..."]}]}` |

Do NOT mix `field` objects into funnel steps / retention filters, and do NOT mix `event_property_name` into event metric filters.

---

## 8. Time Range modes

Ad-hoc model (`analysis adhoc run/export`) modes:

| mode | Meaning |
|------|------|
| `recent` | Last N units (including today) |
| `previous` | Past N units (excluding today) |
| `custom` | Explicit start_time / end_time |
| `start_to_today` | From a fixed start_time through today |
| `start_to_yesterday` | From a fixed start_time through yesterday |

Do not use `mode=relative`, `relativeTime`, `begin`, or `end` for ad-hoc models.

Event-detail (`analysis event-detail run/export`) uses a different contract:

| mode | Meaning |
|------|------|
| `absolute` | Explicit start_time / end_time (format `yyyy-MM-dd HH:mm:ss`) |
| `relative` | Relative window via `relative_date_range` (e.g. `"0-7"`) |

Do not pass `mode: custom` to event-detail.

---

## 9. Parallelism Convention

All independent `ae-cli analysis adhoc run` calls are issued in parallel within the same batch, waiting for all to return before aggregating; never serialize.
