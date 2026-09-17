---
name: retention-metric-to-event-report
description: Create retention analysis metrics and merge them into event analysis reports. Use when a customer asks how to create a retention metric or asks to merge the retention analysis model into the events analysis model. Do not use for retention data verification, retention trend or churn diagnosis, analysis model selection, or pure data or report queries.
---

# Retention Metric to Event Report

## Purpose

Guide the customer through two related workflows:

1. Create a metric in Retention Analysis.
2. Merge a retention analysis model into an Events Analysis report by creating the retention metric and then adding it to an event report.

## When to Use

Trigger this skill when the customer asks:

- How to create a retention metric.
- How to merge the retention analysis model into the events analysis model.
- How to configure a retention metric the same as an existing retention report.

## When Not to Use

Do not use this skill for:

- Verifying whether retention data is correct or diagnosing retention versus event analysis data discrepancies.
- Retention trend, churn, or LTV analysis.
- Choosing which analysis model to use.
- Simple data queries or report viewing without creating or modifying retention metrics.

## Mandatory References

Read the referenced file before the corresponding step. The files are the source of truth for exact fields, enum values, and command templates.

| Step | Required reference |
|---|---|
| Create a retention metric | references/retention_metric_create.md |
| Locate or inspect reports | references/report_cli_workflow.md |
| Add a retention metric to an event report | references/retention_metric_in_event_report.md |

## Workflow

### Step 1: Route the scenario

- Scenario A: The customer only needs to create a retention metric. Go to Step 2; do not add anything to a report.
- Scenario B: The customer asks to merge the retention analysis model into the events analysis model. Complete Step 2 and Step 3. The workflow is complete only after the metric is added to an event report.

If the requested scenario is unclear, ask the customer to choose between creating only a metric and merging it into an event report.

### Step 2: Create the retention metric

1. Read references/retention_metric_create.md before doing anything else.
2. Confirm with the customer and do not use defaults for:
   - Metric definition: Simultaneous Display (ROI/LTV/LT), Retained User Count, Retention Rate, Churn Rate, or Churned User Count.
   - Day-N calculation: `unitNum`, for example 3, 7, or 30.
3. Verify project-specific inputs:
   - Confirm the project ID.
   - Confirm the initial event and return event names from the actual project metadata. Do not invent event names.
   - Confirm or reverse-lookup the analysis subject object. `#user_id` is the preset subject, but the full `taIdMeasureVo` object must match the project's analysis subject.
4. If the customer asks to create a metric based on an existing retention report:
   - Read references/report_cli_workflow.md.
   - Use `report list` to locate the report and `report get` to inspect its current configuration.
   - Map the retention report definition to metric fields using the table in references/report_cli_workflow.md.
   - Still confirm the metric definition and `unitNum` with the customer before creation.
5. Create the metric with ae-cli only. Use the exact template in references/retention_metric_create.md. The command shape is:

```bash
ae-cli analysis-meta metric create --project-id <project_id> --metric-name <metric_name> --metric-desc '<metric_display_name>' --model-type retention --metric-events '<metric_events_definition>' --metric-params '<metric_params_definition>'
```

6. Verify persistence with:

```bash
ae-cli analysis-meta metric get --project-id <project_id> --metric-id <metric_id>
```

If the customer only needed the metric, output the closing message described below and stop here.

### Step 3: Add the metric to an Events Analysis report

Before executing, confirm with the customer whether to add the metric to an existing report or create a new report. Wait for confirmation.

Also perform the time-granularity pre-check before writing:

- Retention metrics support only By Day, By Week, or By Month.
- If the target report uses Total or another unsupported granularity, stop and explain that the metric cannot use that granularity. Ask whether to change the report to the metric's supported granularity; do not offer to change the metric to Total or another unsupported value.
- If both sides use supported granularities but differ, ask whether to align the report or the metric. Change the chosen side only after confirmation.
- Do not write to the report before alignment.

Then:

1. Read references/retention_metric_in_event_report.md and references/report_cli_workflow.md. Treat them as the source of truth; do not assemble the report definition from memory.
2. For an existing report:
   - Use `report list` to locate the report by name and confirm a unique match.
   - Use `report get` to fetch the current `version`, `model_type`, `definition`, and `time_particle_size`.
   - Copy the complete `definition` returned by `report get`, including its time range, groups, filters, relations, and other settings. Preserve every existing `metrics[]` entry, then append the retention metric entry. Change `time_particle_size` only when the customer approved a granularity adjustment.
   - The metric entry uses the metric technical name as `event`, `total_count` as the placeholder `aggregation`, and the metric display name as `display_name`.
3. For a new report, confirm the report name and set `time_particle_size` directly to `day`, `week`, or `month`, matching the metric granularity.
4. Write the report with ae-cli only:
   - Existing report: use `report update` with the fresh `--report-version`.
   - New report: use `report create`.
5. Verify after writing:
   - Run `report get` and confirm the appended metric entry is resolved as a metric.
   - Run `report-data run` with a bounded preview. If all metric columns show `-`, first check whether the selected observation window is complete.
   - Get the report link with `asset url-get` and include the returned Markdown link in the response.

## Closing Message

Only when Step 2 completed metric creation alone and the metric was not added to an event report, make the last sentence of the reply a Markdown blockquote:

> The <metric_display_name> metric has been created. If you want to add it to a report in Events Analysis, just tell me the report name or ask me to create a new report.

Replace `<metric_display_name>` with the actual display name.

If the metric was successfully added to an event report, do not output this closing message. End with the report verification result and report link.

## Key Constraints

- Use ae-cli for all platform operations. Do not use any other tool channel.
- Do not submit raw QP definitions. Submit only the AI-facing definition documented in the references and let the compiler generate raw QP.
- Do not invent event names, property names, metric fields, enum values, or command flags.
- For `report update`, use optimistic locking: fetch the version immediately before writing and preserve the complete existing definition, including all `metrics[]` entries; omission can change or remove existing report settings.
- For SIM_STAT metrics, include `init_date_stat_first: false` on the type-3 entry at creation time.
- If ae-cli is unavailable or returns a permission or capability error, stop and report the failure. Do not fabricate a completed result.

## Degradation and Recovery

- Missing project ID, event names, or analysis subject: ask the customer; do not guess.
- Granularity mismatch: stop the report write, align the report or metric after customer confirmation, then retry.
- `DATA_ALREADY_UPDATED`: re-run `report get` to fetch the latest version and definition, reassemble, then retry once. If it still fails, stop and investigate.
- All metric columns show `-`: verify the query succeeded, then check the observation window. N-day metrics can be empty when the project does not yet have enough history.
- Temporary verification assets: delete them only with explicit customer confirmation, using the delete commands documented in references/retention_metric_in_event_report.md.

## Self-Check Before Final Output

- Was the metric created and verified with `metric get`?
- If a report was written, did `report get` confirm the metric resolved as a metric and did `report-data run` succeed?
- Were all consequential writes and deletions confirmed by the customer?
- Is the closing message present only for metric-only completion and not after a successful report write?
- Does the response use the same language as the customer?

## Language Constraint

Respond in the exact same language as the customer. If the customer writes in Chinese, respond entirely in Chinese; if in English, respond in English. Do not mix languages unless translating a specific term.
