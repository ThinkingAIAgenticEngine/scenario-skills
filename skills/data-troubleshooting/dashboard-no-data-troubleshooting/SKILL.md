---
name: dashboard-no-data-troubleshooting
description: "Performs minimal investigation of dashboards showing no data, all zeros, or abnormal drops — checking dashboard config, spot-checking one report, then verifying the event source to quickly determine whether the issue is time range, filter/metric config, or tracking/data ingestion. Use when a dashboard shows no data, all zeros, or an abnormal drop."
---

# Dashboard No-Data Troubleshooting

## Language Policy

**CRITICAL**: Always respond in the user's language.
- If user writes in English → Respond in English
- If user writes in Chinese → Respond in Chinese
- Never translate the user's language; match their input language exactly

## Applicable Scenarios

Use when users report:
- Dashboard shows no data
- Dashboard data is all zeros
- New dashboard returns no data
- Existing dashboard suddenly shows no data
- Data shows an obviously abnormal drop

Goal: **Locate the root cause with the fewest steps. No unnecessary exploration.**

---

## Execution Principles

1. **Check config first, then data.**
2. **Verify one key object at a time.** Check the dashboard first, then spot-check the first report — don't iterate through all reports upfront.
3. **Stop when root cause is found.** Don't continue unrelated checks.
4. **Only use real, available ae-cli commands.** Don't fabricate commands.
5. **Conclusions must be clearly categorized** into one of:
   - Time range error
   - Filter or metric configuration error
   - Event not reported / data source has no data
   - Permission or visibility issue
   - Other configuration error

---

## Minimal Investigation Flow

### Step 1: Get Dashboard Basic Info (must do, once only)

Call in sequence:
- `analysis dashboard list`: find `dashboard_id` by name or keyword
- `analysis dashboard get`: read dashboard details (once only)

Key information to extract:
- `dashboard_id` / `dashboard_name`
- Report list (`report_id`, `report_name`, `model_type`)
- Whether the report count appears abnormal

If the dashboard can't even be found, output directly:

```text
Issue: Configuration Error
Root Cause: Target dashboard does not exist or is not accessible under the current project.
Fix: Verify project ID, dashboard name, and access permissions, then retry.
```

---

### Step 2: Verify Time Range (highest priority)

Determine time range from:
- Info returned by `analysis dashboard get`
- If time config is unclear, call `analysis report get` on the first report
- Execute that report with `analysis report-data run` and an explicitly aligned time range when the command supports the required override

Key checks:
- Is a future time range selected?
- Is the time range too narrow (e.g. only a few minutes/hours)?
- Does the recent period genuinely have no data?
- Could timezone be a factor?
- Is a fixed historical time window being used (e.g. a specific month), causing a mismatch with the user's intended viewing period?

Supplementary rule:
- If the report's default time range is a fixed historical window, even if the final root cause is "event not reported" or "filter config error", add a note: "Current report time range is a fixed historical window and may not be suitable for viewing current-period data."
- This note supplements but does not change the primary conclusion category.

If switching to "last 7 days" shows data while the original config shows none, output:

```text
Issue: Time Range Error
Root Cause: The dashboard or report's time range does not cover the actual data-producing period.
Fix: Adjust the time range to last 7 days, last 30 days, or confirm the actual data cycle and reconfigure.
```

---

### Step 3: Spot-Check One Report's Data (don't iterate all)

Take only the **first report**, call in sequence:
- `analysis report get`
- `analysis dashboard-report-data run` with only that report ID

Judgment:
- **Has data**: The dashboard isn't entirely data-less; more likely specific report config issues
- **No data**: Proceed to Step 4 to check event source

If the first report has data but the user reports "dashboard has no data", output:

```text
Issue: Configuration Error
Root Cause: The dashboard is not entirely data-less — at least one report returns data normally. The issue is more likely concentrated in specific report configurations.
Fix: Target the specific reports showing no data and check their filter conditions, metric definitions, and time ranges. Don't attribute the issue to the entire dashboard or data source.
```

---

### Step 4: Verify Event Source (only when Step 3 confirms the report has no data)

From `analysis report get`, extract:
- Event names used
- Key filter conditions
- Model type (event analysis, funnel, retention, etc.)

Then call in order:
- Construct the smallest semantic AI-facing definition for the report model
- `analysis adhoc run`: let the compiler resolve the event/property names
- If compilation needs clarification, use `analysis-meta event/property list`
  and select an exact candidate
- `analysis project timezone get`: confirm timezone only when boundaries matter

Execution requirements:
- Keep the adhoc query as simple as possible — strip complex filters
- Only keep essential events and a basic time range
- Don't try to replicate the entire report definition

Judgment:
- **Event exists and adhoc has data** → Data source is normal; issue is in report config (filters, metrics, grouping, funnel steps, etc.)
- **Event exists but adhoc has no data** → Event has no recent data; issue is in tracking/data ingestion
- **Event doesn't exist** → Dashboard/report references a non-existent or renamed event
- If the report's default time range is a fixed historical window at this point, add a note in the conclusion: "Current report time range is a fixed historical window. If the user wants to view current-period data, the time range should be adjusted accordingly, then recheck."

Output example:

```text
Issue: Event Not Reported
Root Cause: The event the report depends on has no valid data in the last 7 days.
Fix: Check whether tracking is still reporting, whether the event name has changed, and whether the data ingestion pipeline is functioning.
```

Or:

```text
Issue: Filter or Metric Configuration Error
Root Cause: The event source has data, but the report query returns empty — the issue is in the report's own configuration, not tracking.
Fix: Remove filter conditions and re-query; restore filters one by one. Also check metric definitions, grouping fields, and funnel step configuration.
```

---

## Scenario-Based Priority

### Scenario A: New Dashboard Has No Data
Suspect first:
1. Time range doesn't cover the data period
2. Wrong event name selected
3. Report filter conditions too strict
4. Metric or grouping configuration error

Recommended actions:
- Check time range first
- Spot-check the first report
- Use adhoc to verify the event has raw data

### Scenario B: Existing Dashboard Suddenly Has No Data
Suspect first:
1. Event stopped reporting
2. Event name or property definition changed
3. Report filter references an invalid property value
4. Time range was modified

Recommended actions:
- First check if the first report still has data for last 7 days
- If no data, verify the event source

### Scenario C: Some Users See Data, Some Don't
Suspect first:
1. Permission differences
2. Different row-level visibility
3. Different personal filter settings

Output for this type:

```text
Issue: Permission or Visibility Issue
Root Cause: The same dashboard returns different results for different users; suspect permission, sharing scope, or data visibility configuration differences.
Fix: Compare dashboard access permissions, report sharing scopes, and row-level permission settings between users who see data and those who don't.
```

---

## Common Root Causes Quick Reference

| Symptom | Most Likely Cause | Minimal Verification |
|---------|-------------------|---------------------|
| New dashboard no data | Time range excludes data period | Switch to last 7 days |
| New dashboard no data | Wrong or non-existent event | `analysis-meta event list` |
| Existing dashboard suddenly no data | Event stopped reporting | `analysis adhoc run` for last 7 days event count |
| Data is zero but not blank | Filter too strict | Remove filters and re-query |
| Only some users see no data | Permission or visibility differs | Compare user permissions and sharing |
| Single report no data, others OK | Report config error | Check only that report's definition |

---

## Tool Usage Constraints

### Required Tools
- `analysis dashboard list/get`
- `analysis report get`
- `analysis dashboard-report-data run`
- `analysis-meta event list`
- `analysis project timezone get`
- `analysis adhoc run` with an AI-facing definition

### Prohibited Behaviors
- Don't fabricate CLI commands
- Don't iterate through all reports without confirming necessity
- Don't expand the investigation scope after finding the root cause
- Don't equate "dashboard no data" directly with "tracking is broken"

---

## Standard Output Format

```text
Issue: [Time Range Error | Filter or Metric Config Error | Event Not Reported | Permission or Visibility Issue | Configuration Error]
Root Cause: <one-line explanation>
Fix: <most direct next step only>
Additional Notes: <only when needed; if the report uses a fixed historical time window, explicitly note that the current time range may not be suitable for viewing current-period data>
```

---

## Recommended Response Style

- Give the conclusion first, then the evidence
- Only include information relevant to the root cause
- Don't list irrelevant checks
- If the root cause isn't yet identified, clearly state "next step is to check only X"

Example:

```text
Issue: Filter or Metric Configuration Error
Root Cause: The spot-checked first report has data at the event source level but returns empty results, indicating the issue is at the report configuration layer.
Fix: Remove the report's filter conditions and re-query; if data returns, restore filters one by one to identify the specific conflicting condition.
```
