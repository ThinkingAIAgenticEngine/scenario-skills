---
name: game-version-compare
description: Game version data comparison analysis. Use when the user needs to evaluate a new version's launch effect, compare old vs new version data, or review a version iteration. Supports different game types (casual / hardcore / card / SLG, etc.) and different business goals (new feature validation, retention, monetization, performance, balance, overall health), producing structured conclusions through a combined approach of version-number segmentation plus before/after comparison. Triggered when the user says "compare version A and version B", "did this update have any effect", "before/after patch comparison", or "correlate the retention board and payment board for comparison".
version: "1.4"
---

# Game Version Data Comparison Analysis

> One-line positioning: starting from the "business goal", define the comparison approach and select metrics, query data with ae-cli, quantify the differences between the old and new versions (or across multiple boards), then perform root-cause attribution with a confidence-level label (heuristic inference, not causal proof), and output actionable tiered recommendations.

## Responsibility Boundary

This skill does exactly one thing: **answer "did this version change have any effect, where is the problem, and do we need to act"**. It takes the following three things as input and produces structured conclusions:

| Input | Source |
|------|------|
| The core change in this version (what changed) | User statement |
| Version field + version number + launch date | User statement (all must be clarified, none can be missing, see Step 2) |
| Quantified differences between old and new versions | ae-cli query |

**In scope**: define the comparison approach, select metrics, query data, compare, infer root cause, produce a report.
**Out of scope**:
- Single campaign effect analysis (use the campaign analysis skill)
- Long-term lifecycle / monthly review (use the business review skill)
- Pure "build a board / produce a report" requests (hand off to ae-analysis)

## Trigger Scenarios

Triggered when any of the following applies:
- The user says "compare version A and version B", "did this update/revamp have any effect", "before/after patch comparison"
- The user wants to "correlate the retention board and payment board to see the version impact"
- A new feature / campaign / balance / performance change has launched and needs a data review

**Pre-interception**: if another skill (e.g. ae-analysis) is currently running, first determine whether the user's current message is an "analysis request" or a "query parameter / supplementary parameter"; the latter should be intercepted and returned to the original skill to avoid stepping on its toes.

## Execution Steps (8 steps, do not skip)

### Step 1: Identify the Business Goal (mandatory)

First confirm with the user the core change in this version, map it to the table below, and decide the comparison approach and metric priority. When the user is unclear, use AskUserQuestion to offer options.

| Business Goal | Typical Version Change | Core Question |
|---------|------------|---------|
| A. New feature / gameplay acceptance | New system, new gameplay, new level, new hero | Did users adopt it? Did they stay after using it? |
| B. Retention optimization | New user tutorial, recall mechanism, check-in / quests, push | Did the churn point improve? Did the retention curve lift? |
| C. Monetization / payment | Gift pack, first purchase, gacha, store, pricing | Did payment rate / ARPPU improve? Did it squeeze the overall base? |
| D. Performance / stability | Engine upgrade, package optimization, crash fix, lag optimization | Did crashes / lag drop? Did it affect retention? |
| E. Balance / numeric tuning | Difficulty, output / consumption, matchmaking | Did the bottleneck ease? Is the economy out of balance? |
| F. Overall health routine review | Routine iteration, content update | Are DAU / duration / retention stable? Any abnormal fluctuation? |

Multiple goals are allowed, but the user must rank a **primary goal**, which determines the core conclusion of the report.

When presenting the business-goal options via AskUserQuestion, list them in the fixed order A/B/C/D/E/F shown above — do not reorder or shuffle them.

### Step 2: Confirm Version Field, Version Number, and Launch Date (mandatory, interactive confirmation)

Before writing any query, **confirm the following three things with the user — none can be silently assumed or auto-detected**. The most frequent omissions are (a) confirming the version number without confirming which field identifies it, and (b) skipping the launch date (版本更新时间).

1. **Version identification field (版本识别字段)**: ask the user which metadata field actually records the version number in this project.
   - Ask in plain text and let the user type the exact field name freely — **do NOT present candidate options (e.g. `app_version` / `version` / `client_ver` / `build` / `#app_version`) as a multiple-choice list**; the user knows their own field naming better than any guessed list.
   - Explicitly tell the user: "if the target project has no version identification field, reply '无版本字段' to skip". When the user skips, only time comparison is possible (cohort / updated-vs-not-updated comparison is not possible), which must be stated in the report.
2. **Version values (版本号取值)**: the exact target-version value and the exact baseline-version value(s).
   - After the field is confirmed, use `ae-cli analysis filter-value list --project-id <PID> --property-name <FIELD> --table-type <event|user>` (add `--event-name <EVENT>` for an event property) to retrieve candidate values.
   - Ask the user to identify the target version and baseline version(s) from those returned values. Do not guess, and do not define the baseline as `!= target`: missing or malformed values are not a valid not-updated cohort.
3. **Launch date (版本更新时间 / 上线日期)**: the date the version officially launched (the boundary day for time comparison). Let the user type it.

Ask these in plain text (free input, no multiple-choice options), and proceed to Step 3 only after getting clear answers. If the user provides only some of them, proactively ask for the missing ones. When the user replies "no version field", skip items 1–2 and confirm only the launch date.

### Step 3: Confirm Data Feasibility (mandatory)

Before writing queries, first probe the project metadata with ae-cli and confirm three things:
1. **Version-number property**: whether event/user properties contain a version field (name varies by project). If absent → fall back to time windows to distinguish old vs new, but this **only supports time comparison, not "updated vs not-updated" cohort comparison**, which must be stated in the report.
2. **Core behavior events**: whether key events such as launch / login / level / payment are complete.
3. **Payment event / amount property** (needed for monetization goals).

**Key discipline**: when a key field is missing, clearly tell the user "this analysis is limited by the missing XX and can only achieve YY", **do not force it**. The most common pitfall in this step is "the pre-launch window has no data at all" — always confirm both sides of the comparison window have data before continuing (see references/data-feasibility.md).

### Step 4: Define the Comparison Approach (choose by goal)

**Universal dual approach; recommended to run both and cross-validate for any goal**:

```
Approach 1 (time comparison): N days after launch vs N days before launch (same window length)
Approach 2 (cohort comparison): updated users vs not-updated users (within the same time period)
```

- Approach 1 is simple but mixes in overall natural fluctuation, holidays, and campaigns
- Approach 2 is cleaner but requires version-number tracking and a sufficient number of not-updated users
- Both agree → trustworthy; they conflict → drill down to find the cause (usually channel-mix change or selection bias)

**Default time window**: exclude launch day D. Compare D+1 through D+7 with D-7 through D-1. If fewer than 7 complete post-launch days are available, use the same number of complete days on each side. Include D only when the user explicitly requests launch-day analysis. D7 retention requires a complete observation period for every included cohort.

### Step 5: Confirm Metrics and Drill-down Dimensions (interactive confirmation)

Based on the primary goal, select 3-5 core metrics + 1-3 drill-down dimensions. **After generating the suggested list, you MUST ask the user to confirm; do not execute directly.**

- Universal base: activity (DAU / new users / returning users), duration (per-user duration / launch count), retention (D1 / D3 / D7)
- Add metrics by goal (see references/metrics-and-dimensions.md)
- Channel dimension is mandatory by default, unless the user explicitly says not to look at channel

### Step 6: Execute Queries and Multi-dimensional Breakdown (with ae-cli)

**Query order**: first check whether an existing report with a consistent approach exists (reuse its numbers directly if so) → otherwise fall back to adhoc.

- Existing report: search with `analysis report list` / `dashboard list` → verify the approach with `report get` → if consistent, read numbers with `report-data run` passing version A/B windows
- adhoc: `analysis adhoc run -p <PID> --model-type event/sql --definition '{...}'`
- Correct schema and pitfalls are recorded in references/ae-cli-query-guide.md. The scripts under `scripts/` retain the verified Project 7 examples: `batch_event_compare.py` uses its event/property mapping as an example, while `retention_diff.py` accepts confirmed project, event, and table overrides. Do not reuse Project 7 mappings unchanged in a project with different tracking.

For the dual approach, execute both paths with identical metric definitions:

1. **Time comparison**: use the post-launch range as `time_range` and the aligned pre-launch range in `comparison_time_ranges`.
2. **Version cohort comparison**: run the same definition twice over the same post-launch range. Filter one query with the confirmed target version and the other with the confirmed baseline value(s). Keep metrics, dimensions, timezone, and all non-version filters identical. Report missing-version users separately; never silently include them in the baseline.

Use `analysis filter-value list` to resolve exact version values. Pass `--preview-rows 100` for bounded synchronous queries and parse the JSON envelope; if `has_more=true`, use `analysis adhoc export` instead of treating the preview as complete.

### Step 7: Root-cause Diagnosis (confidence-level label)

After getting the differences, infer which version change drove the change. **This is heuristic inference, not causal proof** — label the reliability with "confidence level" and honestly note confounding factors.

> ⚠️ "Confidence level" refers to the reliability of the inference, **NOT statistical confidence/significance** (not a p-value, not a confidence interval); it is only a subjective grading of how well the inference holds up.

Confidence-level grading (based on two negative conditions: whether it is singular and clear + whether confounding factors exist):
- **High**: a single clear change matches the difference, and there are no confounding factors → can act on it
- **Medium**: there is a reasonable association or slight confounding → verify before acting
- **Low**: the signal is weak/ambiguous → do qualitative research or extend the observation period

Inference rule table is in references/root-cause-rules.md.

### Step 8: Output the Report

Strictly follow the structure and standards in references/report-template.md (结论速览 → comparison table → charts → drill-down → root cause → risks → tiered recommendations). Core dashboard spirit:

- **Conclusion first**: the 结论速览 (Summary) must stand alone independently
- **Data must be compared**: there must be an old-version or not-updated control; never list only new-version data
- **Beware false causality**: proactively check channel-mix change, campaigns, and holiday interference
- **Honestly mark uncertainty**: insufficient observation period, small sample, missing fields, low confidence level — all must be stated

## Output Standards (summary)

See references/output-standards.md for details. Key points:

- Red/green color follows the A-share convention: **up = red 🔴, down = green 🟢** (opposite of Western convention, unless the user explicitly requests otherwise)
- Amount/currency defaults to **¥ (CNY)**
- Root-cause diagnosis uses "confidence level" (high/medium/low), not "statistical confidence"
- Recommendation tiers: P0 immediate / P1 within this week / P2 within this month / monitor

## Common Pitfalls (self-check list)

- [ ] Confirmed the version identification field, the version number, and the launch date (not missing the version field, not missing the launch date)?
- [ ] Checked not-updated users as a control?
- [ ] Time windows aligned (same length for old and new)?
- [ ] Avoided the launch-day spike?
- [ ] Retention observation period sufficient?
- [ ] Distinguished "version effect" from "channel-mix / campaign" interference?
- [ ] For monetization, looked at both payment rate and ARPPU (to guard against squeeze)?
- [ ] Considered selection bias (users who proactively update are inherently more active)?
- [ ] Labeled confidence level on root-cause? Low confidence level prompts further verification?
- [ ] Checked for an existing report with a consistent approach before querying, and verified its approach before reusing?

## Language Constraint

Respond in the exact same language as the user's input. If the user writes in Chinese, respond entirely in Chinese; if in English, respond entirely in English. Do not mix languages unless translating terms.
