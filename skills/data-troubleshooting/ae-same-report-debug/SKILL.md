---
name: ae-same-report-debug
description: "Diagnoses why the same saved report shows different numbers on its detail page and in a dashboard, or across two dashboards, by comparing effective dashboard settings, the saved report definition, and actual results from both execution surfaces. Trigger when the user reports one of these same-report discrepancies. Do not trigger for comparisons between different reports, cross-model discrepancies, or source tracking correctness."
version: "4.0"
---

# Diagnose Same-Report Discrepancies

> **CRITICAL:** Before executing, the `PROJECT_ID_GATE` must be satisfied (see Step 0).
> **CRITICAL:** Never guess any `project_id`, `dashboard_id`, `report_id`, report name, or dashboard name; they must be obtained through ae-cli queries.
> **CRITICAL:** This Skill is strictly read-only debugging; it does not perform any write operations.

---

## Trigger Conditions

Trigger this Skill when the user asks questions similar to the following:

- "The same report shows different results"
- "The numbers shown for a report inside a dashboard differ from the report detail page"
- "The same report placed in two different dashboards shows different numbers"
- "The dashboard outer layer and the detail page data do not match"

---

## Input Requirements

**Before starting the investigation, clarify the specific scenario with the user (one of the following must be confirmed):**

| Case | Scenario Description | Information to Provide |
|------|----------------------|------------------------|
| **Case 1** | The same report shows inconsistent results between **a dashboard outer layer** and the **report detail page** | Dashboard name or ID, report name or ID, project name or ID |
| **Case 2** | The same report is referenced by **two different dashboards**, and the results shown in the two dashboards are inconsistent | Dashboard A name or ID, Dashboard B name or ID, report name or ID, project name or ID |

If the user has not specified the scenario, ask: "Please confirm: is it that a report's numbers inside a dashboard differ from the detail page, or that the same report placed in two different dashboards shows different numbers?" — wait for the user's answer before continuing.

---

## Output Format Rules (globally applicable, highest priority)

> When the output contains "check items / field comparisons / multi-column results", you must use **GFM Markdown tables**. Plain-text tables aligned with spaces, HTML `<table>` tags, or wrapping the table in a triple-backtick code block are all prohibited.

**Mandatory requirements:**

1. **Tables must NOT be wrapped in a triple-backtick ``` code block.** Markdown inside a code block is not parsed as a table by the frontend and will be displayed as raw characters. The table must appear directly in normal body text.
2. The table must include a header row and a separator row `| --- | --- | ... |`.
3. The number of columns and separator columns must match; cells must not contain unescaped `|` characters (use `\|` if a vertical bar is needed).
4. Cells must not contain line breaks; let the frontend wrap long text automatically.
5. Status is distinguished with emoji prefixes (Markdown tables do not support cell background colors, so emojis are used instead):
   - Match → `✅ Match`
   - Mismatch → `⚠️ Mismatch`
   - Unconfirmed → `❓ Unconfirmed`
   - Not applicable / None → `—`

**Conclusion / summary output format requirements:**

- Do not pile multiple paragraphs as unordered plain text; split into "Root Cause / Recommendation / Unconfirmed" subsections, each starting with a **bold heading**.
- Within each subsection, use ordered numbered lists (`1.` `2.` `3.`); **even if there is only 1 item, use `1.` numbering** to keep the format consistent.
- Keep each conclusion to 1–2 sentences; state the conclusion directly without elaborating on principles.

**Standard header template (Case 1, output directly, do not wrap in a code block):**

| Check Item | Dashboard Outer Layer | Report Inner Layer | Difference |
| --- | --- | --- | --- |
| Actual disputed value | 1,240 (Total / 2026-09-27) | 1,180 (Total / 2026-09-27) | ⚠️ Mismatch |
| Effective time zone | fixed_timezone.enabled=true, zone_offset=8; query=8 | effective_zone_offset=8 | ✅ Match |
| Time range | fixed_time.enabled=true, 2026-09-01 to 2026-09-27 | recent 7 complete days | ⚠️ Mismatch |

---

## Execution Flow

### Step 0: Confirm Project (PROJECT_ID_GATE)

Confirm and record `PROJECT_ID` using the following logic (must not be skipped or guessed):

1. If `project_id` has already been explicitly confirmed by the user in the current session, use it directly without re-querying.
2. Otherwise, call the following command to filter projects by name or ID:
   ```bash
   ae-cli project info list --query "<project_name_or_id>" --limit 50
   ```
3. If the candidate project is unique and its name clearly matches the user's description, adopt it directly; if there are multiple candidates or it cannot be determined, list the candidates for the user to confirm.
4. After the user switches projects, re-execute this step.

---

### Step 1: Get Dashboard Details

**If the user only provided a dashboard name, query the ID first:**

```bash
ae-cli analysis dashboard list \
  --project-id <PROJECT_ID> \
  --queries '["<dashboard_name>"]' \
  --fields '["dashboard_id","dashboard_name"]'
```

- When multiple records are returned, list the candidates for the user to confirm; do not pick one on your own.

**Case 1: Get a single dashboard's details**

```bash
ae-cli analysis dashboard get \
  --project-id <PROJECT_ID> \
  --dashboard-id <DASHBOARD_ID>
```

**Case 2: Get details for both dashboards separately**

```bash
# Dashboard A
ae-cli analysis dashboard get \
  --project-id <PROJECT_ID> \
  --dashboard-id <DASHBOARD_A_ID>

# Dashboard B
ae-cli analysis dashboard get \
  --project-id <PROJECT_ID> \
  --dashboard-id <DASHBOARD_B_ID>
```

The returned structure is a gateway envelope: `{ "ok": true, "data": { ... }, "meta": { ... } }`.

**Read the normalized fields below exactly; do not search for guessed key-name patterns (for Case 2, inspect both dashboards separately):**

| Check Item | Canonical `dashboard get` field | Impact |
|------------|---------------------------------|--------|
| Effective time zone | `effective_settings.fixed_timezone.enabled`, `zone_offset`, `timezone_source` | A fixed dashboard time zone can resolve relative dates differently from the report detail surface |
| Fixed time range | `filter_config.fixed_time.enabled` and `.definition` | The saved dashboard time range can replace the report's own dynamic range |
| Dashboard default filter | `filter_config.dashboard_default.enabled` and `.definition` | Adds the dashboard-wide default filter |
| Dashboard business filter | `filter_config.dashboard_business.enabled` and `.definition` | Adds a mandatory dashboard business filter |
| Space business filter | `filter_config.space_business.enabled` and `.definition` | Adds a mandatory inherited project-space filter |
| Merge relation | `filter_config.merge_relation` | Saved dashboard filters and call-time filters are combined with this relation; the current contract returns `and` |
| Approximate calculation | `effective_settings.approximate_calculation.enabled` | Approximate execution can differ from exact report-detail execution |
| Cache | `effective_settings.cache.applicable`, `value`, `unit`, `source` | Cached dashboard data can lag behind a direct report query |
| Scheduled pre-computation | `effective_settings.scheduled_precompute.enabled`, `schedule_hour`, `zone_offset` | Scheduled results can lag behind real-time report-detail results |

If a saved filter condition has `supported=false`, report that its legacy definition could not be fully mapped. Do not treat it as absent and do not infer its meaning.

---

### Step 2: Get Report Definition

**If the user only provided a report name, query the ID first:**

```bash
ae-cli analysis report list \
  --project-id <PROJECT_ID> \
  --queries '["<report_name>"]' \
  --fields '["report_id","report_name"]'
```

- When multiple records are returned, list the candidates for the user to confirm.

**Get the report definition:**

```bash
ae-cli analysis report get \
  --project-id <PROJECT_ID> \
  --report-id <REPORT_ID>
```

In the returned structure:
- `data.model_type`: model type (`event` / `funnel` / `retention` / `sql`, etc.)
- `data.definition`: AI-readable model definition of the report

**Record only the normalized AI-facing fields actually returned under `data.definition`:**

| Field | Canonical key | Description |
|-------|---------------|-------------|
| Time range | `time_range` | Saved relative or custom report range |
| Comparison periods | `comparison_time_ranges` | Saved comparison ranges when present |
| Time granularity | `time_particle_size` | Saved day/hour/total granularity when present |
| Filter conditions | `filters` and `relation` | Saved report filter leaves/groups and their relation |
| Grouping dimensions | `groups` | Saved grouping dimensions |
| Metric definition | `metrics` | Saved event, property, saved-metric, or formula metrics |
| Analysis entity | root `analysis_entity` | Saved entity selector when supported by the model |

Preserve model-specific fields returned by `report get`. Do not search for raw frontend/QP keys such as `recentDay`, `startTime`, `comparedByTime`, `indicators`, or `subject`; this capability deliberately returns the normalized definition rather than those DTOs. Also record `data.in_dashboards` (when returned) to confirm that the selected report belongs to the dashboard(s) being compared.


---

### Step 3: Reproduce the Difference on Both Execution Surfaces

Configuration differences are hypotheses until the actual saved surfaces have been executed. First run the report directly, without adding overrides:

```bash
ae-cli analysis report-data run \
  --project-id <PROJECT_ID> \
  --report-ids '[<REPORT_ID>]' \
  --preview-rows 100 \
  --timeout-seconds 180
```

Then run the same report through each selected dashboard. Case 1 runs this once; Case 2 runs it once for Dashboard A and once for Dashboard B:

```bash
ae-cli analysis dashboard-report-data run \
  --project-id <PROJECT_ID> \
  --dashboard-id <DASHBOARD_ID> \
  --report-ids '[<REPORT_ID>]' \
  --preview-rows 100 \
  --timeout-seconds 180
```

For every result:

1. Compare the same metric, group, period, and total/date row; never compare cells with different coordinates.
2. Record returned effective timezone information, actual query-cluster scope/source, warnings, partial failures, and `has_more` when present. Do not guess a value that was not returned.
3. Dashboard queries already apply `filter_config` and effective dashboard settings. Do not copy those filters into `--filters`, which would apply them twice.
4. SQL reports ignore generic dashboard time/filter overrides; preserve and report any `OVERRIDE_IGNORED_FOR_MODEL` warning.
5. If the bounded response is truncated or does not contain the disputed cell, use the corresponding export command or narrow the requested scope before concluding.
6. An empty result is a successful query with no rows, not an execution failure.

Classify the evidence before continuing:

- **Observed discrepancy**: the dashboard and direct report executions reproduce different values for the same coordinate.
- **Configuration risk only**: a setting differs, but the queried values currently match.
- **Not reproduced**: settings and queried values match; report cache timing, a midnight boundary, or a user-specific UI state remains a hypothesis, not a confirmed root cause.

---

### Step 4: Case Determination and Investigation

---

#### Case 1: Dashboard Outer Layer vs Report Detail Page — Inconsistent Results

Compare the dashboard override field values found in Step 1 with the report inner-layer definition from Step 2 item by item, and output using the template below.

> **Output rules:**
> - Fill each column with the actual value; if the corresponding field is absent, fill "Not found"; if an execution field is optional and not returned, fill "Not returned"
> - The Difference column uses emoji prefixes: `✅ Match` / `⚠️ Mismatch` / `❓ Unconfirmed` / `—`
> - Keep conclusions to within 2 lines; do not elaborate on causes or recommendations
> - **You must use a GFM Markdown table, and the table must NOT be wrapped in a triple-backtick code block** (otherwise the frontend will not render it)

Output template (output exactly like this; do not wrap the outer layer in a code block):

=== Case 1 Investigation Results ===
Dashboard: <DASHBOARD_NAME> (ID: <DASHBOARD_ID>)
Report: <REPORT_NAME> (ID: <REPORT_ID>)

| Check Item | Dashboard Outer Layer | Report Inner Layer | Difference |
| --- | --- | --- | --- |
| Actual disputed value | <dashboard-report-data value + coordinate> | <report-data value + coordinate> | <✅ Match / ⚠️ Mismatch / ❓ Unconfirmed> |
| Effective time zone | effective_settings.fixed_timezone=<actual value>; query=<returned value / Not returned> | report-data effective_zone_offset=<actual value / Not returned> | <✅ Match / ⚠️ Mismatch / ❓ Unconfirmed> |
| Time range | filter_config.fixed_time=<actual value / disabled> | definition.time_range=<actual value> | <✅ Match / ⚠️ Mismatch> |
| Dashboard default filter | filter_config.dashboard_default=<actual value / disabled> | — | <⚠️ Mismatch / —> |
| Dashboard business filter | filter_config.dashboard_business=<actual value / disabled> | — | <⚠️ Mismatch / —> |
| Space business filter | filter_config.space_business=<actual value / disabled> | — | <⚠️ Mismatch / —> |
| Approximate calculation | effective_settings.approximate_calculation.enabled=<true / false> | — | — |
| Cache | effective_settings.cache=<actual value> | — | — |
| Scheduled pre-computation | effective_settings.scheduled_precompute=<actual value> | — | — |
| Query route / warnings | <actual scope, source, warnings> | <actual scope, source, warnings> | <✅ Match / ⚠️ Mismatch / ❓ Unconfirmed> |

Pending user confirmation is required only for a material setting that the current CLI response does not expose. Name the exact UI setting and do not include a fixed confirmation checklist when CLI evidence is already sufficient.

[If custom cache or scheduled pre-computation is enabled, append the following notice:]
⚠️ The dashboard has enabled <Custom cache / Scheduled pre-computation>; data may be non-real-time. It is recommended to manually refresh the dashboard before comparing with the report detail page.

Conclusion: <1 sentence explaining the root cause; if there are unconfirmed items, state "Root cause can be located after the user confirms item X">
Recommendation: <1 sentence>

---

#### Case 2: The Same Report Shows Inconsistent Results in Two Different Dashboards

Compare the override configurations of the two dashboards from Step 1 side by side to find the differing items:

> **Output rules:**
> - Fill each column with the actual value; if the corresponding field is absent, fill "Not found"; if an execution field is optional and not returned, fill "Not returned"
> - The Difference column uses emoji prefixes: `✅ Match` / `⚠️ Mismatch` / `❓ Unconfirmed` / `—`
> - Keep conclusions to within 2 lines; do not elaborate on causes or recommendations
> - **You must use a GFM Markdown table, and the table must NOT be wrapped in a triple-backtick code block**

Output template (output exactly like this; do not wrap the outer layer in a code block):

=== Case 2 Investigation Results ===
Report: <REPORT_NAME> (ID: <REPORT_ID>)
Dashboard A: <DASHBOARD_A_NAME> (ID: <DASHBOARD_A_ID>)
Dashboard B: <DASHBOARD_B_NAME> (ID: <DASHBOARD_B_ID>)

| Check Item | Dashboard A | Dashboard B | Difference |
| --- | --- | --- | --- |
| Actual disputed value | <dashboard A value + coordinate> | <dashboard B value + coordinate> | <✅ Match / ⚠️ Mismatch / ❓ Unconfirmed> |
| Effective time zone | <effective_settings.fixed_timezone + returned query value> | <effective_settings.fixed_timezone + returned query value> | <✅ Match / ⚠️ Mismatch / ❓ Unconfirmed> |
| Fixed time range | <filter_config.fixed_time> | <filter_config.fixed_time> | <✅ Match / ⚠️ Mismatch> |
| Dashboard default filter | <filter_config.dashboard_default> | <filter_config.dashboard_default> | <✅ Match / ⚠️ Mismatch> |
| Dashboard business filter | <filter_config.dashboard_business> | <filter_config.dashboard_business> | <✅ Match / ⚠️ Mismatch> |
| Space business filter | <filter_config.space_business> | <filter_config.space_business> | <✅ Match / ⚠️ Mismatch> |
| Approximate calculation | <effective_settings.approximate_calculation.enabled> | <effective_settings.approximate_calculation.enabled> | <✅ Match / ⚠️ Mismatch> |
| Cache | <effective_settings.cache> | <effective_settings.cache> | <✅ Match / ⚠️ Mismatch> |
| Scheduled pre-computation | <effective_settings.scheduled_precompute> | <effective_settings.scheduled_precompute> | <✅ Match / ⚠️ Mismatch> |
| Query route / warnings | <actual scope, source, warnings> | <actual scope, source, warnings> | <✅ Match / ⚠️ Mismatch / ❓ Unconfirmed> |

Report inner layer (shared by both dashboards):
- Time range: <definition.time_range actual value>
- Comparison periods: <definition.comparison_time_ranges actual value / none>

Pending user confirmation is required only for a material setting that the current CLI response does not expose.

Conclusion: <1 sentence explaining the root cause or differing items; if no differing item, explain possible causes (cache / crossing midnight); if there are unconfirmed items, note them>
Recommendation: <1 sentence>

---

### Step 5: Summary Output Conclusion

> The investigation summary uses a structured format: split into "Root Cause / Recommendation / Pending User Confirmation" subsections, each starting with a bold heading, with ordered numbered lists inside. **Do not pile multiple paragraphs as unordered plain text.**
> Keep each conclusion to 1–2 sentences; state the conclusion directly without elaborating on principles.
> When the root cause can be located, omit the "Pending User Confirmation" subsection; when there is no recommendation, omit the "Recommendation" subsection; but the Root Cause subsection is always retained.

Output template (output exactly like this; do not wrap the outer layer in a code block):

### Investigation Summary

**Root Cause**

1. <Root cause description: directly state which configuration item caused the inconsistency; if not located, write "All queryable configurations are consistent; the root cause will be located after the user confirms item X">
2. <If there are multiple root causes, continue listing as 2. 3.; if only one root cause, only write 1.>

**Recommendation**

1. <Recommendation 1: executable action corresponding to root cause 1>
2. <Recommendation 2: corresponding to root cause 2 or follow-up; if none, omit the entire subsection>

**Pending User Confirmation** (omit this subsection if the root cause has been located)

1. <Confirmation item 1: a material setting not exposed by the CLI; name its exact UI location>
2. <Confirmation item 2, up to 3 items>

**Common root causes and recommendations mapping:**

| Root Cause | Applicable Case | Recommendation |
|------------|-----------------|----------------|
| Dashboard fixed time range overrides the report range | Case 1 / Case 2 | Disable or align `filter_config.fixed_time`, then rerun both execution surfaces |
| Dashboard fixed time zone differs from direct report execution | Case 1 / Case 2 | Align `effective_settings.fixed_timezone` with the intended report execution timezone, then rerun both surfaces |
| Dashboard adds default, business, or space filters | Case 1 / Case 2 | Confirm whether each enabled `filter_config` source is intended; remove or align it if not needed |
| Approximate calculation is enabled | Case 1 / Case 2 | Turn off approximate calculation and re-compare; if the data volume makes the error acceptable, explain the situation |
| Custom cache or scheduled pre-computation is enabled | Case 1 / Case 2 | Manually refresh the dashboard before comparing with the report detail page; if still inconsistent, investigate other root causes |
| The two dashboards have different override configurations | Case 2 | Align the override parameters of the two dashboards |
| Dynamic time range crosses midnight during rendering | Case 1 / Case 2 | Explain that this is normal behavior for dynamic time; if consistency is needed, switch to a fixed time range |

---

### Step 6: Delivery Self-Check

Before presenting a root cause, verify all of the following:

1. The project, dashboard(s), and report were resolved to exact IDs without guessing.
2. `dashboard get` was called once for each selected dashboard and only canonical `effective_settings` / `filter_config` paths were interpreted.
3. `report get` confirmed the report model, normalized definition, and dashboard membership when available.
4. The disputed report was executed through both `report-data run` and every relevant `dashboard-report-data run` surface.
5. Compared values use the same metric, group, period, and row coordinate; truncation, warnings, partial failures, routes, and effective timezone evidence are disclosed.
6. A root cause is labeled confirmed only when the observed value difference and the responsible effective setting are supported by returned evidence. Otherwise label it a hypothesis or pending UI confirmation.

---

## Constraints

- Never guess any resource ID or name; must be obtained through ae-cli queries
- All command parameters use kebab-case (`--project-id`, `--dashboard-id`, `--report-id`); do not use underscore form
- The return structure is always a gateway envelope (`ok/data/meta`); always take business fields from `data`; `ok: true` with empty `data` is treated as success, not failure
- Field names are subject to the actual API return; do not infer field values from patterns; if a field does not exist, record "Not found" instead of assuming a value
- Read dashboard timezone behavior from `effective_settings.fixed_timezone`; use the effective timezone returned by data execution when present. If a required UI-specific setting is not exposed, state that exact limitation instead of claiming that all timezone information is unavailable.
- If sufficient information cannot be obtained via ae-cli (e.g. missing fields), clearly tell the user which configuration items need to be manually checked in the UI
- This Skill is strictly read-only debugging; it does not perform any write operations
- **Investigation result tables must use GFM Markdown tables and must NOT be wrapped in triple-backtick code blocks**; violating this rule causes the frontend to display the table as raw characters
- **The investigation summary must use a structured format**: Root Cause / Recommendation / Pending User Confirmation subsections, each with a bold heading + ordered numbered list; piling multiple paragraphs as unordered plain text is prohibited
- The status column uses unified emoji prefixes: `✅ Match` / `⚠️ Mismatch` / `❓ Unconfirmed` / `—`

## Language Policy
Always respond in the user's language.
