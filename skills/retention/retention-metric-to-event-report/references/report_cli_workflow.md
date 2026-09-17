# Report Viewing and Editing CLI Workflow

> For any step in this skill's workflow that requires "viewing the current report configuration", "locating an existing report", "editing/creating a report", or "post-write verification", **you MUST read this document first** and follow its CLI commands and order; do not call commands or assemble parameters from memory.

## When to Use This Document

| Step | Typical Scenario | Command Chain |
|---|---|---|
| Locate a report | The customer mentions an existing report (retention/event) by name without an ID | `report list` |
| View current report configuration | Creating a metric by referencing an existing retention report (inferring definition/events/granularity); getting the version and existing definition before editing an event report | `report get` |
| Edit an existing report | Appending a retention metric into an existing events analysis report | `report get` → `report update` |
| Create a new report | The customer asks for a new events analysis report to carry the metric | `report create` |
| Post-write verification | Confirming the metric was added successfully and the report can return data | `report get` → `report-data run` → `asset url-get` |

## 1. Locate a Report: report list

```bash
ae-cli analysis report list \
  --project-id <project_id> \
  --queries '["<report name keyword>"]' \
  --model-types '["retention"]' \
  --fields '["report_id","report_name","report_model","version"]'
```

Key points:

1. `--queries`: a JSON array of 1-20 non-empty strings with OR semantics; merge multiple known names into a single call instead of querying one name at a time.
2. `--model-types`: filter by model; use `"retention"` for retention reports and `"event"` for events analysis reports.
3. `--limit` defaults to 50 (1..200); when `has_more=true`, paginate with the returned `next_offset`; stop when `has_more=false`.
4. If multiple or zero results match, confirm with the customer first; do not pick one on your own.

## 2. View the Current Report Configuration: report get (required before referencing/editing)

```bash
ae-cli analysis report get --project-id <project_id> --report-id <report_id>
```

Key `data` fields:

| Field | Purpose |
|---|---|
| `version` | Integer version number, used as `--report-version` in `report update` (optimistic lock). **Fetch it fresh right before use**; do not reuse a stale version from a previous list call or an earlier conversation round |
| `model_type` | Report model (`retention` / `event` / `sql`, etc.); determines the `--model-type` to pass in update |
| `definition` | AI QP definition (raw QP not included). For event reports, look at `metrics[]` + `time_particle_size`; for retention reports, look at the `retention{}` structure |
| `definition.time_particle_size` | Report time granularity: `day` / `week` / `month` / `hour` / `total`, etc.; a missing field means the report has no readable granularity — do not infer it from the number of result rows |

### Inferring Metric Parameters from a Retention Report Definition (reference-based metric creation scenario)

| Retention report definition | Metric-side field | Mapping |
|---|---|---|
| `retention.initial_event` | `type:0` initial event in `metric_events[]` | Reuse the event name as-is |
| `retention.return_event` | `type:1` return event in `metric_events[]` | Reuse the event name as-is |
| `retention.stat_type` + `rtn_rate_or_num` | `retentionType` + `format` | `retention`+`rate` → `RETENTION_RATE`+`percent`; `retention`+`count` → `RETENTION_NUM`+`integer`; `lost`+`rate` → `LOST_RATE`+`percent`; `lost`+`count` → `LOST_NUM`+`integer` |
| `retention.unit_num` | `unitNum` | Day N |
| `time_particle_size` | `timeParticleSize` | `day`↔`T1`, `week`↔`T2`, `month`↔`T3` |
| `retention.initial_filters` / `return_filters` | `filts` of the corresponding event | The structure must be converted to the metric-side TA standard filter structure; if unsure, first create a metric with filters in the UI, then `metric get` to reverse-lookup and copy the exact structure |

Notes:

1. The report configuration is for reference only; before creation you must still confirm the definition and `unitNum` with the customer per `retention_metric_create.md`; do not copy the report by default.
2. If the retention report uses "Simultaneous Display (ROI/LTV/LT)", assemble the A/B metrics and calculation rules per the SIM_STAT template in `retention_metric_create.md`; do not guess from the report definition.
3. `groups` (report grouping dimensions) has no corresponding field on the metric side; ignore it when creating metrics.

## 3. Edit an Existing Report: report update

```bash
ae-cli analysis report update \
  --project-id <project_id> \
  --report-id <report_id> \
  --report-version <version just fetched via report get> \
  --model-type <model_type returned by report get> \
  --definition '<complete new AI QP definition>'
```

Key points:

1. Modifying the definition requires `--model-type` at the same time; when changing only the name/description, pass only `--report-name` / `--report-desc` without the definition.
2. **DO NOT submit raw QP** (`events` / `event_view` / `analysis_query`); always submit the AI QP definition and let the compiler generate the raw QP.
3. Treat the returned `definition` as the base for the update. Preserve its time range, groups, filters, relations, other settings, and every existing `metrics[]` entry; append only the new metric and change granularity only after confirmation. `definition.metrics[]` uses full-replacement semantics, so omitting old entries deletes old metrics.
4. Before writing retention-type metrics, you must run the time granularity pre-check (rules and branches in "Prerequisite 4" of `retention_metric_in_event_report.md`).
5. Fetch the version via `report get` at the moment just before writing; do not fetch it rounds in advance and hold it.
6. `DATA_ALREADY_UPDATED`: the version is stale (the report was updated by another editor). Re-run `report get` to fetch the latest `version` and `definition`, reassemble, and retry; if it still fails, stop and investigate — do not retry blindly.
7. `AI_QP_COMPILE_FAILED`: compilation failed and the report is not modified. Keep the definition unchanged and fix it per the structured error returned (field names and enum values follow the respective references).

## 4. Create a New Report: report create

```bash
ae-cli analysis report create \
  --project-id <project_id> \
  --report-name '<report display name>' \
  --model-type event \
  --definition '<complete AI QP definition>'
```

Key points:

1. When creating a report containing retention-type metrics, `time_particle_size` must be set directly to one of `day|week|month` (consistent with the metric granularity).
2. After a successful creation, keep the returned `report_id` for later verification and linking.

## 5. Post-Write Verification and Report Link (MANDATORY)

1. **Structure verification**: run `report get` again and confirm the metric entry was resolved by the compiler as a metric (that entry in `resolved.metrics[]` has `type == "metric"`).
2. **Data verification**:

```bash
ae-cli analysis report-data run \
  --project-id <project_id> \
  --report-ids '[<report_id>]' \
  --preview-rows 10
```

Add `--start-time` / `--end-time` to cover earlier dates. When all metric columns show `-`, first check whether the observation window is not yet full (see Key Pitfall 3 in `retention_metric_in_event_report.md`).

3. **Report link** (output to the customer after create/update succeeds):

```bash
ae-cli analysis-meta asset url-get \
  --project-id <project_id> \
  --resource-id <report_id> \
  --resource-type report
```

Take the returned `markdown_link` and give it to the customer directly.

## Command Quick Reference

| Purpose | Command |
|---|---|
| Locate a report by name/model | `ae-cli analysis report list` |
| View report configuration (version/model/definition/granularity) | `ae-cli analysis report get` |
| Edit an existing report (optimistic lock) | `ae-cli analysis report update` |
| Create a new report | `ae-cli analysis report create` |
| Run a report query | `ae-cli analysis report-data run` |
| Get a clickable report link | `ae-cli analysis-meta asset url-get` |

## Related Documents

- Metric creation (7 required pieces of information, SIM_STAT template): this skill's `references/retention_metric_create.md`
- Adding retention metrics to events analysis reports (definition structure, granularity pre-check, pitfalls): this skill's `references/retention_metric_in_event_report.md`
- Full contracts for each command: the `ae-analysis` skill's `references/report_list.md`, `report_get.md`, `report_update.md`, `report_create.md`, `report_data_run.md`, `asset_url_get.md`
