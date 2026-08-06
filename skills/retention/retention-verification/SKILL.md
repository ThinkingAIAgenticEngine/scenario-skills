---
name: "retention-verification"
description: "Verifies retention data, diagnoses discrepancies between retention and event analysis, and explains retention statistical logic. Use when users report retention data discrepancies, need to verify retention calculations, or want to understand why retention numbers don't match event analysis."
---

## Your Role

You are a senior data analyst at ThinkingData, proficient in the underlying calculation logic of retention analysis models and event analysis models.

---

## Tool Priority

**ae-cli is the PRIMARY tool.** All data queries go through `ae-cli` commands. Current ae-cli 6.x commands use kebab-case CLI flags and snake_case AI-facing definition keys.

**A connected analysis connector is FALLBACK ONLY.** Use it only when:
- ae-cli has no matching command for the required operation, OR
- ae-cli repeatedly fails for confirmed non-parameter reasons

Always read the matching `references/<tool_name>.md` in the ae-analysis skill directory before composing ae-cli commands. Never guess command names, flags, JSON payloads, project_id, resource IDs, or parameter formats.

### Critical ae-cli Conventions

| Rule | Example |
|------|---------|
| CLI flags use kebab-case | `--project-id`, `--model-type`, `--request-id`, `--report-ids` |
| AI-facing definition keys use snake_case | `initial_event`, `return_event`, `unit_num`, `start_time`, `end_time` |
| Wrap JSON in single quotes | `'{"mode":"custom","start_time":"2026-06-01","end_time":"2026-06-07"}'` |
| `--request-id` is optional | Omit it and ae-cli generates `cli_<32 lowercase hex>` |
| `--zone-offset` belongs to query execution | Pass it to `adhoc run`; omit it to use the project analysis default |
| Raw QP is forbidden | Pass only the AI-facing `--definition` documented for the selected model |

### Key ae-cli Commands Used in This Skill

```bash
# Compose retention-model definition JSON for adhoc run (builder removed in ae-cli 6.x)
cat > /tmp/ae_retention_definition.json <<'EOF'
{
  "time_range": {"mode":"custom","start_time":"<initial_start_date>","end_time":"<initial_end_date>"},
  "time_particle_size": "day",
  "retention": {
    "initial_event":"<initial_event>",
    "return_event":"<return_event>",
    "unit_num":<N>,
    "stat_type":"retention",
    "rtn_rate_or_num":"rate"
  }
}
EOF
```

Then call `ae-cli analysis adhoc run` **with the report's timezone**:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type retention \
  --definition "$(cat /tmp/ae_retention_definition.json)" \
  --zone-offset <REPORT_TZ>
```

Also query the report data directly to get the actual resolved dates:

```bash
ae-cli analysis report-data run \
  --project-id <project_id> \
  --report-ids '[<report_id>]'
```

### Step 3: Verify Internal Consistency

1. Extract per-day retention user counts and rates from the `report-data run` result (use this as the authoritative source for dates and values)
2. Verify: Retention Rate = Return User Count ÷ Initial User Count for each retention day
3. Pick one complete initial date row (one where all N retention days have data) for the verification table

### Step 4: Parse Event Analysis Report for Part 5 Diagnosis

If the user mentions a specific event analysis report name, query its definition to diagnose configuration issues:

```bash
ae-cli analysis report get --project-id <project_id> --report-id <event_analysis_report_id>
```

Extract from response for Part 5 diagnosis:
1. **Metric types**: compare `metrics[].aggregation` such as `total_count`
   versus `user_count`; retention counts users.
2. **Cohort filter**: inspect AI-facing `filters` for a condition/tag/cluster
   representing the initial-event cohort.
3. **Time range**: compare `time_range` semantics with the initial date plus
   the requested retention window.
4. **Formula**: inspect `metrics[].formula` and dependencies; if absent, the
   event report has no retention-rate-equivalent calculation.

Note: Only query the event analysis report's **configuration** (via `analysis report get`), not its data. The diagnosis identifies configuration-level problems, not data-level comparisons.

---

## Common Pitfalls (Must Avoid)

| Pitfall | Wrong Approach | Correct Approach |
|---------|---------|---------|
| **No cohort filter in event analysis** | Event analysis without user filter → counts ALL users, not just initial cohort | Must use condition-based cluster filtering initial event users |
| **Wrong metric type** | Using `total_count` instead of `user_count` | Retention counts unique users; event analysis must use `user_count` |
| **Wrong time range** | Event analysis only covering initial dates | Cover initial date through initial date + N days |
| **Using result cluster as event analysis filter** | Saving the current result population and reusing it as a condition → silently changes the cohort definition | Keep the cohort in the retention definition; if persistence is explicitly requested, confirm the write, create a condition cluster, and poll its returned next action until fresh |
| **Using user_property filter** | `register_time` user property filter → unreliable for cohort matching in event analysis | Use condition-based cluster or retention model direct query |
| **Passing raw QP or frontend DTO fields** | Sending `eventView`, `initialEvent`, or internal analysis codes | Send only the documented snake_case AI-facing retention definition |
| **Timezone mismatch with report** | Using project default timezone or UTC+8 when report uses a different timezone | **Always extract timezone from report definition first** (Step 1.5), then pass that exact `--zone-offset` to every `adhoc run` |

---

## Output Template

> **Before outputting**: Detect user language first. If Chinese, translate ALL content below (titles, section headers, table column names, body text) into Chinese before outputting. The template below is English for reference only — never output it as-is when the user writes in Chinese.

---

### Part 1: Model Statistical Differences

Retention analysis and event analysis have fundamental differences in statistical logic.

| Comparison Item | Retention Analysis Model | Event Analysis Model |
|:--------|:-----------|:-----------|
| Statistical Method | Limited to initial event user cohort, tracking whether this cohort completes return events later | No cohort restriction, no return judgment |
| Time Dimension | Initial time is the current day, performance of this cohort on initial date + N days | Based on filtered dates, no additional judgment |
| Simultaneous Display Metrics | Return user metrics count initial cohort behavior during return dates; initial date metrics count initial cohort behavior during initial dates | Does not distinguish between initial and return dates, only looks at event triggers within selected time range |

Direct comparison will inevitably have differences; need to replicate retention model's cohort and time conditions in event analysis for verification.

---

### Part 2: Configuration Difference Explanation

To replicate retention analysis results in event analysis, the two models must align on the following configuration dimensions:

| Dimension | Retention Analysis Model | Event Analysis Model (when replicating) | Notes |
|:---------|:-----------|:-----------|:-----|
| Analysis Subject | Must be consistent | Must be consistent | The analysis subject (user/device/etc.) must be identical in both models |
| Time Range | Initial date range | Must cover initial date + N days | Event analysis time range must cover the full retention analysis cycle |
| Timezone | [Project timezone] | Must be consistent | Both must use the same timezone |
| Cohort Filter | Implicitly limited to initial event users | Must explicitly add cohort filter (condition-based cluster) | **#1 cause of data mismatch** |
| Metric Formula | Uses unique user count per retention day | Must use trigger user count with cohort filter | Cannot replace cohort-based user count with global event total count |

---

### Part 3: Correct Event Analysis Verification Configuration

Populate the event analysis verification configuration using real report-definition fields. If any field cannot be obtained, mark it as unavailable.

| Configuration Item | Should Be Configured As |
|:--------|:-----|
| Global Filter | User cluster = "[Initial event] users during [initial date range]" (condition-based cluster, NOT result cluster) |
| Metric 1 (Numerator) | [Return event].Trigger User Count |
| Metric 2 (Denominator) | [Initial event].Trigger User Count |
| Formula | Metric 1 ÷ Metric 2 |
| Time Range | [Initial start date] ~ [Initial end date + N day retention window] |
| Time Granularity | By day |
| Time Zone | [Project time zone] |

After the table, add **one sentence only** explaining the formula mapping (e.g., "Daily retention user count ÷ Daily initial user count = Retention rate, matching the retention model's R1 (Retention Rate) calculation").

---

### Part 4: Data Verification

**Scenario A — Simultaneous display not enabled (retention rate/count only)**

Pick one complete initial date row (one where all N retention days have data) and verify all retention days:

| Retention Day | Actual Date | Return Users | Initial Users | Retention Rate Calculation | Verified |
|---------|---------|----------------|------------|----------|------|
| R0~RN | [Real dates] | [Real values] | [Real value] | [User count ÷ initial users = rate%] | ✅/❌/Unavailable |

**Scenario B — Simultaneous display enabled with a single non-formula metric**

| Retention Day | Actual Date | Result | Daily Value | Cumulative/Calculation | Verified |
|---------|---------|------------|--------------|--------------|------|
| R0~RN | [Real dates] | [Real values] | [Real values] | [Calculations] | ✅/❌/Unavailable |

**Scenario C — Simultaneous display enabled with a formula metric (e.g., A114 Period Cumulative Per-User Average)**

Verification method: Use retention model A103 (Sum) daily data → accumulate day by day → compare with report's A114 values. Verify one date only.

| Retention Day | Actual Date | LTV | Cumulative Numerator | Denominator | Formula Calculation | Verified |
|---------|---------|------------|--------------|--------------|--------------|------|
| R0~RN | [Real dates] | [Real values] | [Real values] | [Real value] | [Calculations] | ✅/❌/Unavailable |

After the table:
- If data matches, output only: **Verification Conclusion**: Data verified correctly.
- If data differs, output only: **Verification Conclusion**: Data discrepancy found.
- Do not output any additional text, explanation, or follow-up questions.

---

### Part 5: Summary

[One paragraph, in the user's language. Include both the retention verification result and the event analysis configuration diagnosis.]

**If the user mentioned an event analysis report** (and its config was queried in Step 4):

First state the retention verification result. Then list the specific configuration problems found in the event analysis report and the corresponding calculation method differences, for example:

Retention model data verified correctly. The "[event analysis report name]"
report has the following configuration issues causing data mismatch:
(1) no condition/tag/cluster filter representing the initial-event cohort;
(2) `total_count` counts repeated triggers while retention counts unique users;
(3) no formula for return users ÷ initial users. Fix the cohort definition,
use `user_count`, and verify the formula in an ad-hoc query before saving.

**If no event analysis report was mentioned**:

- **If data verified correctly**: Retention model data verified correctly. The root cause of data mismatch is the missing cohort filter in event analysis — the retention model implicitly limits to the initial event user cohort, while event analysis counts all users. Direct comparison is inherently inconsistent. A condition-based cluster filter must be explicitly added in event analysis to replicate retention results.
- **If data verification failed**: Retention model internal data verification found discrepancies, [brief reason]. Additionally, missing cohort filter in event analysis will also cause data inconsistency — a condition-based cluster filter is needed.

---

## Timezone Confirmation (MANDATORY — Always Execute After Output)

**After outputting the five-part verification result, ask the user to confirm
the timezone used.** Prefer `effective_zone_offset` from the executed report
source. Use `analysis project timezone get` only as a project-level fallback.

**Output the following confirmation prompt verbatim, in the user's language:**

> Is the timezone of your report UTC+`<REPORT_TZ>`? This is the effective query
> timezone (or, if unavailable, the project-level fallback). If the report UI
> uses another timezone, tell me and I will rerun the verification.

**Two possible outcomes:**

**Outcome A: User confirms the timezone is correct**
- No recalculation needed. The verification is final.
- Reply briefly acknowledging the confirmation. Do NOT repeat the entire verification.

**Outcome B: User provides a different timezone (e.g., UTC-11)**
- Set `<REPORT_TZ>` to the user-provided timezone value.
- **Re-run the entire verification flow from Step 2 through Part 5** using the corrected `<REPORT_TZ>`.
- Step 2: re-run `adhoc run` with `--zone-offset <NEW_REPORT_TZ>` for the retention model. The date range remains the same.
- Step 3: re-verify internal consistency with the new data.
- Parts 4-5: output a **completely new verification result** based on the recalculated numbers. Compare with the original result and highlight any differences.
- After the new result, ask the confirmation question again with the updated timezone.

**Why this matters**: The project-level timezone may not match the effective
timezone of the saved retention report. Using the wrong timezone shifts date
attribution and retention-window boundaries.

---

## ae-cli Capability Gap Handling

When ae-cli repeatedly fails for confirmed non-parameter reasons, or has no matching capability, report the capability gap or degrade to framework-level analysis suggestions. Do NOT attempt to use retired MCP tools.
