# Create a Retention Model Metric (Create Retention Metric)

Use this skill when the user asks to create a metric under the "Retention Analysis" model. Five definitions are supported: Retention Rate, Retained User Count, Churn Rate, Churned User Count, and Simultaneous Display (ROI/LTV/LT).

## Required Information (7 categories, none may be omitted)

Creating a retention metric requires all 7 categories of information below:

| # | Information | Storage Location | Notes |
|---|------|----------|------|
| 1 | Metric definition | `metric_params.retentionType` | 5 definitions; values and mappings in the table under "Must confirm with the user before creation" |
| 2 | Metric calculation | `metric_params.unitNum` | Day-N retention / statistics days (3-day retention=3, 7-day retention=7, 7-day ROI=7) |
| 3 | Display format | `metric_params.format` | `percent`/`integer`/`float`; mapping to definitions in the table under "Must confirm with the user before creation" |
| 4 | Analysis Subject | `metric_params.taIdMeasureVo` | Defaults to `#user_id` (preset; must be written in full) |
| 5 | Initial Event | `type:0` in `metric_events[]` | The retention starting event |
| 6 | Return Event | `type:1` in `metric_events[]` | The return event |
| 7 | Global Filter | `metric_params.filts` + `relation` | Global user filter; syntax in "Global Filter (filts)" |

## Must Confirm with the User Before Creation (do not use defaults)

1. **Metric definition**: have the user explicitly choose among "Simultaneous Display / Retained User Count / Retention Rate / Churn Rate / Churned User Count", with the following mapping:

   | Definition | `retentionType` | `format` |
   |------|-----------------|----------|
   | Retention Rate | `RETENTION_RATE` | `percent` |
   | Retained User Count | `RETENTION_NUM` | `integer` |
   | Churn Rate | `LOST_RATE` | `percent` |
   | Churned User Count | `LOST_NUM` | `integer` |
   | Simultaneous Display (ROI/LTV/LT) | `SIM_STAT` | `float` |

2. **Metric calculation**: retention/statistics for which day-N (i.e. `unitNum`, e.g. 3, 7, 30).

## Key Rules

1. `--model-type retention` (corresponds to backend `metric_mode=1`).
2. `metric_events` uses snake_case fields: `event_name` / `event_desc` / `event_type` / `type` / `filts` / `relation` / `relation_user`.
3. `metric_params` uses camelCase fields: `retentionType` / `unitNum` / `format` / `timeParticleSize` / `filts` / `relation` / `taIdMeasureVo`.
4. The `type` field distinguishes event roles: `0`=Initial Event, `1`=Return Event, `2`=A metric (numerator), `3`=B metric (denominator); a `type:3` entry must carry `init_date_stat_first:false` (consequences and fix in the `init_date_stat_first` item under "Key Pitfalls").
5. `timeParticleSize:"T1"` = statistics By Day.
6. `relation:"1"` = AND logic.
7. When any event slot is set to "Any Event", the syntax is fixed: `event_name:"anyEvent"`, and `event_type` must be omitted (see "Any Event (anyEvent) Syntax").

## Any Event (anyEvent) Syntax

When creating a metric, any event slot that needs to be set to "Any Event" (e.g. the Initial Event `type:0`, the Return Event `type:1`) uses the same fixed syntax:

```json
{"event_name":"anyEvent","event_desc":"Any Event","type":<0|1>,"filts":[],"relation":"1","relation_user":"1"}
```

Key points:

1. The event name is fixed as **`anyEvent`** and the display name is fixed as "Any Event"; **do NOT write `$any`** (it will be rejected by the backend; see "Key Pitfalls").
2. **Do not include the `event_type` field** (in contrast: a normal event must carry `"event_type":"event"`).
3. `type` still takes its normal value by event role (`0`/`1`, etc.); it does not change for Any Event.
4. The stored form seen via `metric get` reverse-lookup is `{"eventName":"anyEvent","eventDesc":"Any Event","type":0}`, which likewise has no `eventType`; do not misjudge it as a missing field during verification.

## Command Template: Retention Rate / Retained User Count / Churn Rate / Churned User Count

These four definitions share the same structure; only `retentionType` and `format` change:

```bash
ae-cli analysis-meta metric create \
  --project-id <project_id> \
  --metric-name <technical_name> \
  --metric-desc '<display_name>' \
  --model-type retention \
  --metric-events '[{"event_name":"<initial_event>","event_desc":"<initial_event_display_name>","event_type":"event","type":0,"filts":[],"relation":"1","relation_user":"1"},{"event_name":"<return_event>","event_desc":"<return_event_display_name>","event_type":"event","type":1,"filts":[],"relation":"1","relation_user":"1"}]' \
  --metric-params '{"retentionType":"<RETENTION_RATE|RETENTION_NUM|LOST_RATE|LOST_NUM>","unitNum":<N>,"format":"<percent|integer>","timeParticleSize":"T1","filts":[],"relation":"1","taIdMeasureVo":<analysis_subject_object>}'
```

## Analysis Subject taIdMeasureVo (defaults to #user_id)

```json
{"columnDesc":"User ID","columnName":"#user_id","columnType":"bigint","csvSize":0,"custom":false,"entityId":86103,"entityName":"user","entityType":"PRIMARY","hasDeleted":false,"hasHide":false,"hasUpperCase":false,"isPreset":true,"primary":true,"primaryBigintType":true,"ruleType":0,"selectType":"number","tableType":"0"}
```

Note: `entityId` / `entityName` depend on the project's Analysis Subject (the example is the `user` subject of project 1656). For a different project, first reverse-lookup that project's preset `#user_id` Analysis Subject, or manually create a metric in the UI and then `metric get` to reverse-lookup it.

## Command Template: Simultaneous Display (SIM_STAT, LTV example)

Simultaneous Display requires all of: the Initial Event, the Return Event, plus the **A metric (numerator), the B metric (denominator), and the calculation rule between them**.

- `type 0`: Initial Event
- `type 1`: Return Event
- `type 2`: **A metric (numerator)**, must carry `analysis` (aggregation) + `quota` (amount property)
- `type 3`: **B metric (denominator)**, must carry `analysis` (aggregation) + `final_operator` (calculation rule) + `final_format` (result format) + **`init_date_stat_first: false` (mandatory)**

The calculation rule is written on the B metric (type 3):
- `final_operator`: how A and B are combined; `DIVIDE`=division (A÷B, commonly used for ROI/LTV)
- `final_format`: result display format, e.g. `float`
- `init_date_stat_first`: fixed to `false` (mandatory; consequences of omission and the fix in the `init_date_stat_first` item under "Key Pitfalls")

CLI input `metric_events` (snake_case, verified in practice, 30-day LTV example):

```json
[
  {"event_name":"login","event_desc":"Login Event","event_type":"event","type":0,"filts":[],"relation":"1","relation_user":"1"},
  {"event_name":"payment","event_desc":"","event_type":"event","type":1,"filts":[],"relation":"1","relation_user":"1"},
  {"event_name":"payment","event_desc":"","event_type":"event","type":2,"filts":[],"relation":"1","relation_user":"1","quota":"payment_amount","analysis":"A113"},
  {"event_name":"login","event_desc":"Login Event","event_type":"event","type":3,"filts":[],"relation":"1","relation_user":"1","analysis":"A101","final_operator":"DIVIDE","final_format":"float","init_date_stat_first":false}
]
```

```bash
--metric-params '{"retentionType":"SIM_STAT","unitNum":30,"format":"float","timeParticleSize":"T1","filts":[],"relation":"1","taIdMeasureVo":<analysis_subject>}'
```

Backend storage structure (camelCase, as seen via `metric get` reverse-lookup):

```json
[
  {"eventName":"create_role","type":0},
  {"eventName":"ad_revenue","type":1},
  {"eventName":"ad_revenue","type":2,"analysis":"A113","quota":"pay_amount"},
  {"eventName":"create_role","type":3,"analysis":"A100","finalFormat":"float","finalOperator":"DIVIDE","initDateStatFirst":false}
]
```

Common aggregation codes (`analysis`): `A100`=Total Count, `A101`=User Count, `A113`=Period Cumulative Sum (amount property).

## Global Filter (filts)

- Location: `metric_params.filts` (array) + `metric_params.relation` (logic, `"1"`=AND / `"0"`=OR).
- No global filter: `"filts":[]` and `"relation":"1"` (must be written; cannot be omitted).
- When a global filter is needed, fill `filts` with the TA standard filter structure (`filterDim` + `filterType` + `values`). A non-empty structure must strictly match the backend; it is recommended to first create a metric with a global filter in the UI, then `metric get` to reverse-lookup the exact structure and copy it.

## Key Pitfalls

1. If `taIdMeasureVo` is patched via `metric update`, it must be a "full update" (passing `--metric-name` + `--metric-desc` + `--model-type` + `--metric-events` + `--metric-params` together); a partial update passing only `--metric-params` will have `taIdMeasureVo` discarded by the backend.
2. `metric create` with `taIdMeasureVo` fully included in one step persists it directly (recommended).
3. Retention Rate / Retained User Count / Churn Rate / Churned User Count only need `type 0/1`; `type 2/3` and `final_operator` are required only for SIM_STAT.
4. `retentionType` and `format` must match; see the mapping table under "Must confirm with the user before creation".
5. **A SIM_STAT `type 3` entry missing `init_date_stat_first:false`**: metric creation shows no error, but as soon as the metric is added to an events analysis report, the query throws `TaRetentionQueryVo.getInitDateStatFirst() is null` (NPE). The fix requires a full `metric update` on the metric to add the field (patching at the report level is ineffective). Always include it in one step at creation.
6. **Writing "Any Event" as `$any`**: `metric create` directly fails with `Event $any has been hidden or deleted, please reset the condition.` The correct syntax for "Any Event" is fixed as `event_name:"anyEvent"` without `event_type` (see "Any Event (anyEvent) Syntax").

## Related Documents

- Adding metrics to events analysis reports: this skill's `references/retention_metric_in_event_report.md` (AI definition structure, command templates, verification and pitfalls)
- `ae-analysis` skill: `references/metric_create.md`, `references/metric_update.md`, `references/metric_get.md`
- Reverse-lookup of real structures: `ae-cli analysis-meta metric get --project-id <id> --metric-id <id>`

