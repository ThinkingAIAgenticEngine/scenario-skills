# Adding a Retention Metric to an Events Analysis Report (Retention Metric → Event Report)

> When you need to add an "already created retention analysis metric" (a metric-center asset, e.g. N-day LTV / ROI / LT / Retained User Count / Retention Rate) to an "Events Analysis" report (appending to an existing report or creating a new report), **you MUST read this document first** and follow its structure and command templates to build quickly; do not assemble QP from memory.

## Core Mechanism (in one sentence)

Events analysis reports use the **AI QP definition path** (`ae-cli analysis report create/update --definition`). When the compiler parses `metrics[]` in the definition, the `event` field matches not only normal events **but also metric technical names from the metric center**; when a metric is matched, the compiled output has `resolved.metrics[].type == "metric"`, which means the metric was successfully embedded into the report.

**DO NOT** hand-craft raw QP (`events` / `event_view` / `analysis_query`) — always submit the AI definition and let the compiler generate the raw QP.

## Prerequisites (must check)

1. The metric has been created successfully and can be reverse-looked-up via `ae-cli analysis-meta metric get --project-id <id> --metric-id <id>`.
2. **SIM_STAT (Simultaneous Display ROI/LTV/LT) metrics**: the `type:3` (denominator) entry in `metric_events` must carry `"init_date_stat_first": false`. Omitting it causes report queries to throw `TaRetentionQueryVo.getInitDateStatFirst() is null` (NPE).
   - Remedy: perform a **full update** on the metric (`metric update` passing `--metric-name` + `--metric-desc` + `--model-type` + `--metric-events` + `--metric-params` together) to add the field to the type-3 entry. A partial update is ineffective, and patching at the report QP level is also ineffective.
   - It is recommended to include the field in `metric create` from the start, in one step.
3. Remember the metric's **technical name** (`metric_name`, e.g. `ltv_30d`) — it is used in the definition; `metric_desc` (display name, e.g. "30-Day LTV") is used for `display_name`.
4. **Time granularity pre-check (MANDATORY, perform before writing to the report)**: retention-type metrics only support three granularities: **By Day / By Week / By Month** (platform limitation; Total / By 1 Minute / By 5 Minutes / By 10 Minutes / By Hour / By Quarter / By Year, etc. are not supported). After locating the target report, first use `report get` to check the report's time granularity (`definition.time_particle_size`) and compare it with the metric granularity (`metric_params.timeParticleSize`), then handle it per the following two branches:
   - Granularity mapping: AI definition `day` ↔ metric `T1` (By Day); `week` ↔ `T2` (By Week); `month` ↔ `T3` (By Month).
   - Granularities match on both sides → pre-check passed; continue building.
   - **Branch 1: the events analysis report uses "Total" granularity** (`total`, or any granularity other than By Day/By Week/By Month, such as `minute`, `hour`, `quarter`, `year`): retention-type metrics do not support Total (that granularity), and the metric side cannot be changed to match. **Directly inform the customer: retention-type metrics do not support Total**, and ask whether to change the events analysis report to match the retention-type metric; after the customer confirms, change the report's time granularity to match the retention-type metric (in `report update`, set `definition.time_particle_size` to the `day|week|month` corresponding to the metric granularity), then continue building.
   - **Branch 2: both the retention-type metric and the events analysis report use By Day/By Week/By Month, but the two differ**: **inform the customer that they must be aligned**; ask the customer to choose whether to change the events analysis report setting or the retention-type metric setting; after confirmation, modify the chosen side:
     - Change the report: in `report update`, set `definition.time_particle_size` to the target granularity (`day|week|month`);
     - Change the metric: perform a **full** `metric update` on the metric to set `metric_params.timeParticleSize` to the target granularity (only `T1|T2|T3`; other values are rejected by the backend).
   - If the pre-check fails, you must stop building, obtain the customer's confirmation, and complete the alignment; do not write to the report before alignment.

## Quick Build Workflow (5 steps)

```
① Confirm the target report → ② report get to fetch the version and existing definition, and run the time granularity pre-check → ③ assemble the new definition (preserve old entries + append the metric entry) → ④ report update / create → ⑤ verify (resolved + report-data)
```

- User asks to "add to an existing report": follow ①~⑤ (update).
- User asks to "create a new report": skip the preservation logic in ②, follow ①③④ (create) ⑤; the new report's `time_particle_size` must be set directly to one of `day|week|month`.
- If the target is unclear, **ask the user first**: which existing report to add to, or whether to create a new report.
- If the granularity pre-check in ② fails: handle per "Prerequisite 4" before continuing.

### ① Confirm the Target Report

- The user gave a report name: use `ae-cli analysis report list` (fuzzy search by name via `--queries`) to find the `reportId`, and confirm the unique match with the user.
- New report: confirm the report name with the user.

### ② Reverse-Lookup the Existing Report (required on the update path)

```bash
ae-cli analysis report get --project-id <project_id> --report-id <report_id>
```

Record three values:

- `version` (integer) → used as `--report-version` in the next step (optimistic lock).
- Complete `definition` → use it as the base for the update. Preserve its time range, groups, filters, relations, other settings, and every existing `metrics[]` entry; then append the metric entry. The `metrics` array uses full-replacement semantics; omitting old entries deletes old metrics.
- `definition.time_particle_size` (current time granularity) → run the granularity pre-check per "Prerequisite 4"; do not assemble and write before confirmation and alignment are complete.

### ③ Assemble the New Definition

Top-level structure of an events analysis AI definition:

```json
{
  "metrics": [ ... ],
  "time_particle_size": "day | total",
  "time_range": { "mode": "...", "unit": "day", "value": N }
}
```

#### metrics[] Entry Structure

**A. Normal event entry** (existing report metrics are usually this kind):

```json
{"property":"","formula":"","aggregation":"total_count","event":"login","display_name":"Login Event.Total Count"}
```

Field notes: `event`=event name; `aggregation`=aggregation method (`total_count` Total Count / `user_count` User Count, etc.); `property`=the property used in aggregation (leave empty for count-type); `formula`=formula (leave empty if none); `display_name`=column display name (convention: "Event Name.Aggregation Name").

**B. Metric-center metric entry** (the core of this document):

```json
{"event":"ltv_30d","aggregation":"total_count","display_name":"30-Day LTV"}
```

Field notes:

| Field | Value | Notes |
|---|---|---|
| `event` | **metric technical name** (`metric_name`) | The compiler resolves it in the metric center; do not write the display name |
| `aggregation` | `"total_count"` | **Mandatory placeholder**; omitting it causes `AGGREGATION_REQUIRED`; the metric's actual aggregation comes from its own definition, and this value does not change the calculation |
| `display_name` | metric display name (e.g. "30-Day LTV") | Report column name |

Note: self-invented fields like `metric` / `metric_name` are ignored by the compiler; **only the `event` field takes effect**.

#### time_range.mode Values

| mode | Meaning |
|---|---|
| `previous` | Past N days (excluding today, up to yesterday) |
| `recent` | Recent N days (including today) |
| `start_to_today` / `start_to_yesterday` | From the start date to today/yesterday (value ignored) |
| `custom` | Custom (additional start/end date fields) |

`time_particle_size`: `day`=split columns By Day, `week`=By Week, `month`=By Month, `total`=Total. **When adding retention-type metrics it can only be `day`/`week`/`month`, and must match the metric granularity (see "Prerequisite 4").**

#### Complete Example (login count report + 30-Day LTV, past 7 days by day)

For an existing report, this example is illustrative only. Start from the complete `definition` returned by `report get` so any additional groups, filters, relations, or other saved settings remain intact.

```json
{
  "metrics": [
    {"property":"","formula":"","aggregation":"total_count","event":"login","display_name":"Login Event.Total Count"},
    {"event":"ltv_30d","aggregation":"total_count","display_name":"30-Day LTV"}
  ],
  "time_particle_size": "day",
  "time_range": {"mode":"previous","unit":"day","value":7}
}
```

### ④ Write to the Report

**Update an existing report** (with the optimistic-lock version number):

```bash
ae-cli analysis report update \
  --project-id <project_id> \
  --report-id <report_id> \
  --report-version <version fetched in the previous step> \
  --model-type event \
  --definition '<complete JSON assembled in ③>'
```

**Create a new report**:

```bash
ae-cli analysis report create \
  --project-id <project_id> \
  --report-name '<report display name>' \
  --model-type event \
  --definition '<complete JSON assembled in ③>'
```

### ⑤ Verify (MANDATORY)

1. **Structure verification**: run `report get` again and confirm the new metric entry in `resolved.metrics[]` has `type == "metric"` (instead of `type == "event"`), which means the compiler resolved it as a metric successfully.
2. **Data verification**:

   ```bash
   ae-cli analysis report-data run --project-id <project_id> --report-ids '[<report_id>]' --preview-rows 10
   ```

   Add `--start-time` / `--end-time` to cover earlier dates. Confirm the query succeeds and the metric columns have values.
3. **Value spot-check** (recommended): the metric column values should match the same-definition values in the original retention analysis report (you can use `ae-cli analysis report-data run --project-id <project_id> --report-ids '[<source_retention_report_id>]'` to read the source retention report for comparison). When a metric column shows `-`, first check "Key Pitfalls".

## Compiled raw QP Storage Structure (for understanding only; do not hand-write)

After the AI definition is submitted, the compiler generates an entry like the following in the raw QP's `events[]` for the metric (visible via reverse-lookup):

```json
{
  "eventName": "ltv_30d",
  "metricName": "ltv_30d",
  "metric": {
    "metricMode": 1,
    "metricName": "ltv_30d",
    "metricDesc": "30-Day LTV",
    "depEvents": ["login", "payment"],
    "quotaProperties": ["payment_amount"],
    "depAggregates": ["STAGE_ACC", "TRIG_USER_NUM"],
    "format": "FORMAT_FLOAT",
    "timeParticle": "T1"
  },
  "format": "FORMAT_FLOAT"
}
```

`metricMode:1` = retention-type metric. This structure is automatically injected by the compiler from the metric center; maintaining the definition manually is sufficient.

## Key Pitfalls (ordered by frequency)

1. **`metric_particle_not_match` (time granularity mismatch)**: a `report-data` query fails with `error.op.parameter_error.metric_particle_not_match`, meaning the retention metric granularity does not match the report's `time_particle_size` (typical scenario: the report is `total` while the metric is By Day). **Do not blindly retry or repeatedly change the metric**; stop and handle it per the two branches of "Prerequisite 4" (when the report uses Total/By Minute/By Hour, etc., the metric side cannot match — the only option is to change the report granularity). Encountering this error at query time means the granularity pre-check was skipped before writing.
2. **`DATA_ALREADY_UPDATED`**: `--report-version` is stale (the report was updated by another editor). Re-run `report get` to fetch the latest `version` and `definition`, reassemble, and retry.
3. **All metric columns show `-`**: first confirm it is not a query failure, then check the date window — an N-day metric showing `-` when its observation window is not yet full is normal business behavior (e.g. the project has only 7 days of data, so all 30-day metrics show `-`).

## Cleaning Up Temporary Verification Assets

If temporary metrics/reports were created during verification (e.g. using a short 7-day-period metric for a value spot-check), delete them after verification is complete:

```bash
ae-cli analysis-meta metric delete --project-id <id> --metric-id <id> --yes
ae-cli analysis report delete --project-id <id> --report-ids '[<id>]' --yes
```

Both are high-risk write operations; user confirmation is required before deletion (or, for temporary assets you created yourself, proactively clean them up and inform the user).

## Related Documents

- Metric creation: this skill's `references/retention_metric_create.md` (7 required fields, SIM_STAT template, `init_date_stat_first` constraint)
- Metric reverse-lookup: `ae-cli analysis-meta metric get`
- Report definition reverse-lookup: `ae-cli analysis report get` (AI definition + version + resolved)
