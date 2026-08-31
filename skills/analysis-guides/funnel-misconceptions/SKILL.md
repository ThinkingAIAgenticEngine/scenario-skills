---
name: funnel-misconceptions
description: "Diagnoses funnel counting rules, explains common pitfalls, and helps troubleshoot funnel or conversion rate anomalies. Use when users report that funnel conversion counts look wrong, users are missing from funnel results, or conversion rates seem inconsistent with event data."
---

## Language Policy (Highest Priority — Execute Before Any Output)

**Before generating a single word of output**, detect the user's language.
- Detect the language from the user's question and use that language for **all output** — titles, section headers, table column names, rule names, body text, conclusions, everything.
- This skill file is written in English for reference only. Translate all content into the user's language before outputting.
- Never mix languages. Technical terms may optionally include English in parentheses.

---

## Tool Priority

**ae-cli is the PRIMARY tool.** All data queries go through `ae-cli` commands. The commands below are verified against ae-cli 6.0.42 and use kebab-case CLI flags with snake_case AI-facing definition keys.

**A connected analysis connector is FALLBACK ONLY.** Use it only when:
- ae-cli has no matching command for the required operation, OR
- ae-cli repeatedly fails for confirmed non-parameter reasons

Always read the matching `references/<tool_name>.md` in the ae-analysis skill directory before composing ae-cli commands. Never guess command names, flags, JSON payloads, project_id, resource IDs, or parameter formats.

### Critical ae-cli Conventions

| Rule | Example |
|------|---------|
| CLI flags use kebab-case | `--project-id`, `--model-type`, `--request-id`, `--zone-offset` |
| AI-facing definition keys use snake_case | `start_time`, `end_time`, `time_particle_size` |
| Wrap JSON in single quotes | `'{"mode":"custom","start_time":"2026-06-01","end_time":"2026-06-07"}'` |
| `--request-id` is optional | Omit it and ae-cli generates `cli_<32 lowercase hex>` |
| `--zone-offset` belongs to query execution | Pass it to `adhoc run`; the resulting context preserves the same scope for drilldown |
| Raw QP is forbidden | Pass only the documented AI-facing `--definition` |

---

## ⛔ Output Prohibitions (Always Apply)

1. **No process narration**: Never output expressions like "Let me check...", "I found...", "Based on what I just viewed...", or any description of searching, looking up, or browsing.
2. **No fabricating rules**: All rule explanations must strictly follow the Output Template below.
3. **No listing report metadata**: Do not output report IDs, dashboard names, reportModel values, etc.

---

## ⚠️ Mandatory Output Requirement

When this skill is invoked, **regardless of what specific question the user asks**, the following Part One rules must be output as the beginning part of the response, followed by any diagnosis or explanation content.

---

## Part One: Five Core Rules of Funnel Analysis

When analyzing user conversion paths, the funnel analysis model follows five core rules. Understanding these rules is the prerequisite for correctly using funnel analysis.

### Rule 1: Sequencing

**Core Principle**: Must strictly follow [step order] triggering, timestamps must be increasing; skipping steps, out-of-order, or simultaneous triggering are all considered invalid

**Typical Cases**:
- ✅ Register(10:00) → Login(10:05) → Payment(10:10)
- ❌ Register(10:00) → Payment(10:10) [Skipped login]
- ❌ Register(10:00:00.000) → Login(10:00:00.000) [Simultaneous triggering]

### Rule 2: Time Window

**Core Principle**: All steps must be completed within the window period, calculated from the trigger time of step 1; timeout results in conversion failure

**Typical Cases** (7-day window):
- ✅ Register(1/1) → Login(1/2) → Payment(1/5) [Completed in 5 days]
- ❌ Register(1/1) → Login(1/2) → Payment(1/10) [9 days timeout]

### Rule 3: Global Filtering

**Core Principle**: Each step must satisfy global filter conditions; if any step doesn't meet them, conversion fails

**Typical Cases** (Global filter platform=iOS):
- ✅ Register(Android) → Login(iOS) → Payment(iOS)
- ❌ Register(iOS) → Login(Android) → Payment(iOS) [Step 2 doesn't satisfy]

### Rule 4: Associated Property Consistency

**Core Principle**: When associated properties are enabled, all steps must have identical associated property values to track the complete conversion path of the same object

**Typical Cases** (Associated property channel ID):
- ✅ Register(channel_id=A001) → Login(channel_id=A001) → Payment(channel_id=A001)
- ❌ Register(channel_id=A001) → Login(channel_id=A002) → Payment(channel_id=A002) [Inconsistent]

### Rule 5: Timezone Consistency

**Core Principle**: Query timezone must match funnel configuration timezone; otherwise, it will cause errors in event date attribution and window period calculation

**Typical Cases** (1-day window, event UTC time Register(1/1 23:00) → Login(1/2 01:00)):
- ✅ UTC+0 is considered cross-day but within window period
- ✅ UTC+8 is considered same day
- ❌ Inconsistent timezone will cause statistical errors

---

## Part Two: Diagnosing User ID Issues in Feedback

When users report that a specific account ID was not counted in conversion, follow this process to precisely locate the issue. If the user has not provided account information, ask for a user ID first.

### Step 1: Obtain Report Configuration

**Must call** `ae-cli analysis report get` to obtain the funnel report configuration.

```bash
ae-cli analysis report get --project-id <project_id> --report-id <report_id>
```

Extract from response:
- Steps (event names, event filters), window period, global filters, associated properties
- Time range type: check whether the report uses a **relative period** (e.g., "Last 7 Days", "Last 30 Days") or a **fixed date range**

### Step 1.5: Extract and Lock Funnel Timezone (CRITICAL)

**Must do this before any data queries.** The funnel report's timezone determines how event timestamps are attributed to dates, how the window period boundaries are calculated, and whether conversion is counted within the correct window. Using a different timezone will cause incorrect date attribution and wrong diagnostic conclusions.

```bash
ae-cli project timezone get --project-id <project_id>
```

Prefer the saved report execution's `effective_zone_offset` as `<FUNNEL_TZ>`.
If it is unavailable, use the project timezone response as a fallback. Every
new `adhoc run` or `event-detail run` query must use that value.
Context-based drilldown inherits the original query scope and must not be given
an invented timezone override.

### Step 1.6: Determine Actual Date Range

**Must complete before calling Step 2.**

- If the report uses a **custom date range**: use `time_range.start_time` and
  `time_range.end_time` from the report definition.
- If the report uses a **relative period**: preserve its `time_range.mode`,
  `unit`, and `value`; do not reinterpret "recent" as "previous".
  - Example: today is 2026-05-19, report is "Last 7 Days" → targetDates = 2026-05-12 through 2026-05-18
  - Example: today is 2026-05-19, report is "Last 30 Days" → targetDates = 2026-04-19 through 2026-05-18

### Step 2: Direct Filter — Check if User Triggered Step 1

**Primary approach: compose an AI-facing `--definition` and use `ae-cli analysis adhoc run` with a direct `#user_id` filter. This is the most efficient method — the database filters by user ID at the index level, returning only matching rows.**

**Compose definition JSON:**

```bash
# Compose event-model AI definition JSON for adhoc run
cat > /tmp/ae_event_definition.json <<'EOF'
{
  "time_range": {"mode":"custom","start_time":"yyyy-MM-dd","end_time":"yyyy-MM-dd"},
  "metrics": [{"event":"<step1_event_name>","aggregation":"user_count"}],
  "filters": [{"field":{"name":"#user_id"},"operator":"eq","values":["<target_user_id>"]}]
}
EOF
```

**CRITICAL: `type` must be `"event_property"`, NOT `"user_property"`.**
- `"type": "event_property"` → generates `tableType:"0"` → correctly filters at the event level → ✅ works
- `"type": "user_property"` → generates `tableType:"1"` → filters at user property level → ❌ silently returns 0

Then call `ae-cli analysis adhoc run` **with the funnel report's timezone**:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --definition "$(cat /tmp/ae_event_definition.json)" \
  --zone-offset <FUNNEL_TZ>
```

**Branch A: Returns 0**
- The user did NOT trigger step 1 during the analysis window.
- Skip to diagnostic: the user violates Rule 1 (Sequencing) — never entered the funnel.

**Branch B: Returns ≥ 1**
- The user triggered step 1 during the analysis window.
- Proceed to Step 3.

### Step 3: Direct Filter — Check if User Triggered Step 2

Use the same approach as Step 2 for the second event. To verify the conversion
window separately, run an explicitly aligned custom `time_range` that includes
the required window and state why the scope differs.

**Compose definition JSON:**

```bash
# Compose event-model AI definition JSON for adhoc run
cat > /tmp/ae_event_definition.json <<'EOF'
{
  "time_range": {"mode":"custom","start_time":"<report_start_date>","end_time":"<report_end_date + window_days>"},
  "metrics": [{"event":"<step2_event_name>","aggregation":"user_count"}],
  "filters": [{"field":{"name":"#user_id"},"operator":"eq","values":["<target_user_id>"]}]
}
EOF
```

Then call `ae-cli analysis adhoc run` **with the funnel report's timezone**:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --definition "$(cat /tmp/ae_event_definition.json)" \
  --zone-offset <FUNNEL_TZ>
```

**Branch C: Returns ≥ 1**
- The user triggered step 2. Whether they converted or not depends on the timing (within window? correct order?). Proceed to Step 4 for precise timeline verification.

**Branch D: Returns 0**
- The user triggered step 1 but did NOT trigger step 2 at all.
- Proceed to Step 4 to verify with user-level data and confirm the diagnosis.

### Step 4: Precise Verification — Query User's Complete Event Sequence

Use the drilldown context returned by the synchronous Step 2 or Step 3 query. Never invent a user ID or drilldown coordinate.

```bash
# Select a returned USER_LIST coordinate advertised by sources[].drilldown.
ae-cli analysis drilldown-entities run \
  --project-id <project_id> \
  --query-context-id <query_context_id> \
  --coordinate '<merged_returned_coordinate>' \
  --preview-rows 100

# Continue only when the previous result returns subject.type=user,
# drilldown_context_id, and the matching canonical user_id.
ae-cli analysis drilldown-user-events run \
  --project-id <project_id> \
  --drilldown-context-id <drilldown_context_id> \
  --user-id <canonical_user_id> \
  --event-name-filter '<funnel_event_filter>' \
  --sort-order asc \
  --preview-rows 1000
```

**Key parameter notes**:
- `query_context_id`, source, and coordinate must all come from the same synchronous preview.
- Select only a coordinate whose advertised action includes entity drilldown.
- `canonical_user_id` must come from that entity response; do not substitute account ID or visitor ID.
- The drilldown context preserves the originating query's time scope and timezone.
- If the result is truncated, use the matching export command instead of inventing pagination.

**Must obtain real data via ae-cli; placeholders or assumed data are not allowed.**

Also check user properties from the drilldown result:
- `first_pay_time`: if null → user has NEVER completed step 2
- `register_time` / `#reg_time`: the actual first registration timestamp

### Step 4.5 (Fallback): Broad Search When Direct Filter Is Inconclusive

Only use this approach when Steps 2–3 return unexpected results (e.g., Step 2 says 0 but you have reason to believe the user has events).

If the aggregate query does not expose a compatible drilldown action, query each funnel event directly with the current event-detail capability:

```bash
ae-cli analysis event-detail run \
  --project-id <project_id> \
  --definition '{
    "event":"<event_name>",
    "time_range":{"mode":"absolute","start_time":"yyyy-MM-dd HH:mm:ss","end_time":"yyyy-MM-dd HH:mm:ss"},
    "filters":{"relation":"and","items":[{"field":{"name":"#user_id"},"operator":"eq","values":["<target_user_id>"]}]},
    "properties":["#event_time","#account_id","#distinct_id"],
    "sort":[{"field":"#event_time","order":"asc"}]
  }' \
  --zone-offset <FUNNEL_TZ> \
  --preview-rows 1000
```

Run this bounded query for each funnel step event, then merge the returned rows by event time. Use `event-detail export` when the requested sequence cannot fit within 1000 rows.

### Step 5: Output Diagnostic Conclusion

**User ID**: [User-reported ID]

**Behavior Details**:

All event times below are returned from the drilldown in the server's stored format. "Adjusted Time" is calculated by adding `<FUNNEL_TZ>` hours to the raw event time — this is the timestamp the funnel report uses for date attribution and window calculation.

| Event Name | Event Time (raw) | Funnel TZ | Adjusted Time | Associated Property | Global Filter Prop | Notes |
|:--------|:--------|:--------|:--------|:----------|:-------------|:-----|
| Step 1 Event | ... | UTC+`<FUNNEL_TZ>` | ... | ... | ... | Step 1 |
| Step 2 Event | ... | UTC+`<FUNNEL_TZ>` | ... | ... | ... | Step 2 (or "does not exist") |

**User Properties** (from drilldown or event details):

| Property | Value |
|:---|:---|
| first_pay_time | ... or null |
| register_time | ... |
| channel / other relevant props | ... |

**Diagnostic Result**: ❌ Should be counted as - Not converted

**Cause Analysis**:

This user violated **[Rule Name]**:

- **Specific Issue**: [Detailed description]
- **Data Evidence**: [Quote specific data from behavior details]

> **Conclusion**: "This user failed to meet the funnel conversion conditions due to [specific reason], and therefore was not counted in conversion data. This is the correct result in accordance with funnel analysis rules."

---

### Step 6: Timezone Confirmation (MANDATORY — Always Execute)

**After outputting the diagnostic conclusion, ask the user to confirm the
timezone used.** Prefer the executed query source's `effective_zone_offset`.
If no query result exposes it, use `analysis project timezone get` as a
project-level fallback; it may differ from the report UI.

**Output the following confirmation prompt verbatim, in the user's language:**

> Is the timezone of your report UTC+`<FUNNEL_TZ>`? This is the effective query
> timezone (or, if unavailable, the project-level timezone). If the report UI
> uses another timezone, tell me and I will rerun the query.

**Two possible outcomes:**

**Outcome A: User confirms the timezone is correct**
- No recalculation needed. The diagnosis is final.
- Reply briefly acknowledging the confirmation. Do NOT repeat the entire diagnosis.

**Outcome B: User provides a different timezone (e.g., UTC-11)**
- Set `<FUNNEL_TZ>` to the user-provided timezone value.
- **Re-run the entire diagnostic flow from Step 2 through Step 5** using the corrected `<FUNNEL_TZ>`.
- Steps 2–3: re-run `ae-cli analysis adhoc run` with `--zone-offset <NEW_FUNNEL_TZ>`. Note that the analysis window date range itself does NOT change — only the timezone offset for query execution changes.
- Step 4: discard the old query/drilldown contexts, rerun the source `adhoc run` with `--zone-offset <NEW_FUNNEL_TZ>`, and obtain fresh drilldown contexts from that result.
- Step 5: output a **completely new diagnostic conclusion** based on the recalculated results. Compare with the original conclusion and highlight any differences.
- After the new conclusion, ask the confirmation question again with the updated timezone.

**Why this matters**: The project-level timezone may not match the effective
timezone of the saved report execution. Using the wrong timezone changes date
attribution and window boundaries.

---

## Step-by-Step Query Flow Diagram

```
1. ae-cli analysis report get → extract config
2. ae-cli project timezone get → extract & lock <FUNNEL_TZ>
3. Calculate actual date range (relative → absolute)

4. ae-cli analysis adhoc run --zone-offset <FUNNEL_TZ> --model-type event --definition <ai_definition_json>
   filter: #user_id (let the compiler resolve its field type), event: step1
   ↓
   ├─ Returns 0 → Rule 1 violation (never entered funnel) → DIAGNOSIS DONE
   └─ Returns ≥1 → user triggered step1

5. ae-cli analysis adhoc run --zone-offset <FUNNEL_TZ> --model-type event --definition <ai_definition_json>
   filter: #user_id (let the compiler resolve its field type), event: step2
   timeRange extended by window period
   ↓
   ├─ Returns ≥1 → user triggered step2 (proceed to Step 6 for timing check)
   └─ Returns 0 → user did NOT trigger step2 (proceed to Step 6)

6. analysis drilldown-entities run → analysis drilldown-user-events run
   (use only returned context IDs, coordinates, and canonical user_id)
   ↓
7. Analyze complete timeline (with <FUNNEL_TZ> adjusted times) + user properties
   ↓
   ├─ step2 within window, correct order → Should be converted (check filters/associated props)
   ├─ step2 outside window → Rule 2 violation
   ├─ step2 before step1 → Rule 1 violation (out-of-order)
   └─ step2 does not exist → Rule 1 violation (incomplete sequence)

8. Output diagnostic conclusion with rule reference and data evidence

9. Step 6: Ask user to confirm timezone
   "Is the timezone of your report UTC+<FUNNEL_TZ>?"
   ↓
   ├─ User confirms → Diagnosis final. Done.
   └─ User provides different TZ → Set <FUNNEL_TZ> = user value → Re-run Steps 2–8
```
