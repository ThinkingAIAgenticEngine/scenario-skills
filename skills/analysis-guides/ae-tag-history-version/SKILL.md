---
name: ae-tag-history-version
description: Tag history version expert — triggered when users ask about tag history/date versions, want tag values as of a past date, need to backfill/refresh history versions, or ask to build reports referencing history-version tags; explains version logic, completes backfill configuration, and builds reports that select history-version tag modes. Do not trigger for general tag creation, first/Nth-event tag building, new/old user classification, user-level metric aggregation, or retention verification unless the request specifically concerns tag history/date versions.
---

**Response format**: Answer the user's current question using the relevant concepts or workflow results. Adapt headings, tables, examples, and explanations to the scenario, and include verified identifiers, dates, statuses, and results where applicable. Preserve wording and structure only for the explicitly marked fixed question and closing-output templates, translating them into the user's language as instructed. Do not reproduce unrelated sections or internal execution instructions in the reply.

## Language Policy (Highest Priority)

Detect the user's language and use it for **all output**. This skill file is written in English; translate into the user's language when needed. CLI commands, field names, and enum values stay in their original form.


## Execution Prerequisites and Product References

This scenario Skill depends on the `ae-analysis` product Skill for CLI command contracts and AI-facing definitions. Concept-only explanations do not require that dependency.

1. Locate `ae-analysis` in the current client's available Skill catalog and use the directory containing its listed `SKILL.md` as the product Skill root. When working in a confirmed source checkout, that root is `product-skills/ae-analysis` in `te-system-skills` or `skills/ae-analysis` in `te-cli`. Do not assume either repository layout exists in an installed client.
2. Read the located product `SKILL.md` and the references needed for the current operation. All product reference paths below are relative to that product Skill root, not to this scenario package:
   - Tag creation: `references/user_tag_create.md`, `references/user_tag_models.md`, and `references/audience_models.md`.
   - History version listing or refresh: the matching `references/history_tag_list.md`, `references/history_tag_refresh.md`, or `references/history_tag_batch_refresh.md`.
   - Report creation or update: the matching `references/report_create.md` or `references/report_update.md`, plus `references/report_get.md`, `references/ai_models.md`, and the selected model's reference under `references/ai_models/`. For event chart settings, also read `references/event_report_presentation.md`.
3. If `ae-analysis` or a required reference is unavailable, identify the missing dependency and ask the user to make the product Skill available before executing the affected operation. Continue any independent conceptual explanation; do not invent schemas, guess file paths, or claim that an unexecuted operation succeeded.

## Trigger Scenarios

Trigger this skill when any of the following occurs:
1. **Asked about history versions**: The user asks questions related to tag history versions / date versions. For example: "What is a history version?", "What are tag history versions / date versions?", "What is the difference between the latest version and a history version?"
2. **Wants to display tag values as of different points in time**: The user wants to go back to a past point in time and view the tag values at that time. For example: "I want to display users' tag values as of different points in time", "What was a user's tag value at a historical point in time?", "Analyze September data with the tag values from September"
3. **Configuration request**: "Help me backfill the history versions of a tag for a range of dates"
4. **Report building request**: The user asks to build a report or Analysis Board that **references history-version tags** and to select the tag version mode as required. For example: "Build a report with September's historical tag values", "View the report grouped by the tag tiers at that time"

---

# Part One: Introduction to Tag History Versions

## 1. Core Concepts

🟢 User tags: Tags are applied to users based on certain behaviors, but **updating a tag overwrites the old result**, which means that if only the latest value is kept, "the user's tag value at some historical moment" is lost.

🟢 Tag history versions: A tag stores, in the form of "date versions", the user's tag value under that tag on a given date. **Any analysis that "goes back to a past day to view users' tag values at that time" should use history versions.**

## 2. The 3 Version Modes

When a tag is used for filtering/grouping in an analysis, if the tag has multiple date versions, you can specify:

| Version Mode | Calculation Basis |
|---------|---------|
| **Latest Version** | Calculated by the user's **current** tag value |
| **Dynamic Matching** | Calculated by the user's tag value **on the day the event occurred** |
| **History Version** | Calculated by the user's tag value **on a specified date** |

## 3. Example

Take a **first/last-event tag** as an example: the `level` property value at the time the user last triggered the `level_up` event (obtaining the last active level)

User A's behavioral timeline:
- 🟢 August 20: triggered `level_up(level=30)`, then remained silent for a long time
- 🟢 October 1: returned and triggered `level_up(level=50)`

| Version Used | User A's Tag Value | Meaning |
|-----------|:---:|------|
| Latest version (calculated on October 13) | 50 | The current last level |
| September 1 history version | **30** | Reflects the last level **at that time** (as of September 1) |
| August 1 history version | None (not yet triggered at that time) | — |

> **Application value**: When analyzing "the retention performance of paying users in September", if the latest version is used to group by level, User A would be counted in the "level 50" group — but in September they were actually a level-30 silent user, so the conclusion is contaminated by today's tag values. Switching to the **September 1 history version** for grouping restores "the level tier the user belonged to at that time", correctly evaluating the effect of the operational actions targeting the level-30 group back then.

**Fixed closing output (mandatory)**: When you have answered the user's question (concept/method introduction) per Part One and have not yet entered the backfill execution flow, you MUST append the following "Next Step" guidance paragraph at the end of Part One, **reproduced verbatim** (only translation into the language of the user's question is allowed; the format and structure must remain unchanged); do not rewrite, reorganize, add to, or remove it, and do not replace it with a self-written "follow-up actions" section. Once the user provides the information above, proceed to the Part Two backfill flow:

---

## Next Step: How to make the tag you created support switching time

To view tag data by different dates, you must first generate (backfill) the history versions of that tag for the corresponding dates.

💬 If the tag has already been created, please provide the following information to backfill history tags:
1. `project_id` (Project ID)
2. Tag name or keyword
3. Dates to backfill: a single day or a date range (e.g., 2026-09-01 ~ 2026-09-30)
---

# Part Two: Updating History Versions Based on Customer Needs

## Scenario Limitation Note

**Only when the customer explicitly mentions the Composition Analysis model** (e.g., asks to add/use history-version tags in Composition Analysis), output the following note; when answering conceptual questions or questions involving other analysis models, **do not proactively quote this section**:

> Model support scope: Events Analysis, Retention Analysis, Funnel Analysis, Distribution Analysis, Flows Analysis, and Interval Analysis support selecting tag versions; Composition Analysis can only use the latest version.

## Tag Pre-check (mandatory before entering the history version update flow)

1. **The customer has provided a tag** (gave a tag name or keyword): go directly to **Step 0** of the history version update flow.
2. **The customer has not provided a tag** (only described the business need, with no usable tag yet): first read `references/tag-creation.md`, follow the process in it to have the customer describe the need in natural language (confirm with the customer only when the core analysis metric and analysis period are missing; the analysis period must be dynamic time), have the Agent determine and list the tag configuration, complete the tag creation (after verifying `progress=100` and the returned `users_num`), then return to Step 0 to continue the history version update flow.

## Step 0: Pre-confirmation (mandatory)

1. **Confirm `project_id`**: if the user has not provided it, ask first; do not guess.
2. **Discover the exact `tag_name`** (fabrication is prohibited; display_name cannot be used directly as a parameter):

```bash
ae-cli analysis user-tag list --project-id <project_id> --query <keyword> --limit 50
```

3. **Confirm the requirement elements with the customer**: which dates to backfill (a single day or a date range).

## Step 1: View existing history versions

```bash
ae-cli analysis history-tag list --project-id <project_id> --tag-name <tag_name>
```

- `items[]`: `tag_date` (yyyyMMdd integer), `history_tag_status` (`normal` = version data already exists, `miss` = that date was not calculated).
- Only report dates with `normal` as "history versions already exist"; existing dates do not need to be backfilled again (unless the customer requests recalculation).

## Step 2: Backfill history versions

Use the customer-confirmed dates. Skip dates already marked `normal` unless the customer explicitly requested recalculation. For a mixed date range, keep the existing normal versions and backfill only missing or abnormal versions.

**Single-day backfill**:

```bash
ae-cli analysis history-tag refresh --project-id <project_id> --tag-name <tag_name> \
  --refresh-date 2026-09-01
```

**Date range batch backfill**:

```bash
ae-cli analysis history-tag batch-refresh --project-id <project_id> --tag-name <tag_name> \
  --refresh-request '{"start_time":"2026-09-01","end_time":"2026-09-30","only_abnormal":true}'
```

- `start_time`/`end_time`: required, **closed interval**, `yyyy-MM-dd`; substitute the customer-confirmed dates for the example dates.
- **Set `only_abnormal:true` for ordinary backfill** so existing normal versions are not recalculated. Set it to `false` only when the customer explicitly requests recalculation of existing versions within that date range; do not widen the requested range.
- **Strict snake_case**: do not pass camelCase names or aliases such as `startDate`/`endDate`; the backend will reject them.

## Step 3: Verify and interpret

1. **Successful submission is not the same as completed calculation**: a successful return from a refresh command only means the task has been submitted. Poll the `history-tag list` from Step 1 until the status of the target `tag_date` becomes `normal` before reporting completion.
2. **Polling cadence**: once every 10–30 seconds, for at most several minutes; if it is still incomplete, tell the customer the task has been submitted and to check again later.
3. After the backfill is complete, the customer can select the corresponding history version of the tag in Events/Retention/Funnel/Distribution/Flows/Interval Analysis for filtering or grouping.

## ⛔ Prohibitions

1. DO NOT fabricate `tag_name`, dates, or calculation results; everything is subject to the actual command output.
2. DO NOT report "task submitted" as "version generated"; you must verify `history_tag_status=normal`.
3. When answering concept/rule questions, cite the knowledge sources (AE Product Manual · User Tags / TE Product FAQ · System Configuration and Limitations).

## Command Quick Reference

| Command | Purpose | Key Parameters |
|------|------|---------|
| `analysis user-tag list` | Discover the exact tag_name | `--project-id` `--query` |
| `analysis user-tag get` | View tag definition/status | `--tag-names '["..."]'` |
| `analysis history-tag list` | History version list and status | `--tag-name` |
| `analysis history-tag refresh` | Backfill a single-day version | `--refresh-date` |
| `analysis history-tag batch-refresh` | Batch backfill a date range | `--refresh-request '{"start_time","end_time","only_abnormal?"}'` |

**Fixed closing output (mandatory)**: After completing the backfill per Part Two and verifying `history_tag_status=normal`, you MUST append the following "Next Step" guidance paragraph at the end of Part Two, **reproduced verbatim** (only translation into the language of the user's question is allowed; the format and structure must remain unchanged); do not rewrite, reorganize, add to, or remove it, and do not replace it with a self-written "follow-up actions" section. Once the user provides the information above, proceed to the Part Three report building flow:

---

## Next Step: Do you need me to build a report referencing this tag for you

If you need me to build a report or Analysis Board referencing this tag for you, please tell me the specific scenario requirement;
for example: "See how users' payment performance was in September, grouped by the login tiers at that time".

---

# Part Three: Building Reports That Reference Tags

## Trigger Scenario

The user asks to build/create an analysis report or Analysis Board containing tags, referencing tags as required and selecting the tag history version mode.

## Step 1: Confirm report elements (mandatory)

1. **Analysis model**: Events Analysis, Retention Analysis, Funnel Analysis, Distribution Analysis, Flows Analysis, Interval Analysis, etc. (Composition Analysis can only use the latest version; see the Scenario Limitation Note in Part Two).
2. **Metrics and grouping/filtering**: which metrics the report displays, whether the tag is used as a filter or for grouping, and whether other grouping dimensions are added.
3. **Tag**: discover the exact `tag_name` (same method as Part Two Step 0; fabrication is prohibited).
4. **Tag version mode**: selected according to the user's needs (see Step 2); it must be confirmed with the user and must not be defaulted on the user's behalf.
5. **Time range and granularity**: the time range and time granularity of the report query.

## Step 2: Tag version mode selection

The mapping between the tag history version modes (Part One) and the `cluster_date_policy` parameter for tag filtering/grouping in report definitions:

| Version Mode | User Need Characteristics | Corresponding Parameter Value |
|---------|---------|---------|
| **Latest Version** | Calculated by the user's current tag value | `cluster_date_policy=LATEST` (default) |
| **Dynamic Matching** | Calculated by the tag value on the day the event occurred; automatically corresponds when the time range is switched | `cluster_date_policy=AUTO` |
| **History Version** | Calculated from the tag snapshot on a specified date | `cluster_date_policy=SPECIFIED` + `specified_cluster_date` (yyyy-MM-dd) |

- Prefer `AUTO` when the user asks to "display the tag data at that time as the time range switches"; use `SPECIFIED` when the user asks for a "fixed snapshot of a specific day".
- Before choosing `AUTO` or `SPECIFIED`, first confirm that the history versions for the target dates have been calculated (`history_tag_status=normal`); if the status is `miss`, backfill per Part Two first, then build the report.

## Step 3: Create the report

```bash
ae-cli analysis report create --project-id <project_id> \
  --report-name "<report name>" \
  --model-type <model: event|retention|funnel|distribution|path|interval etc.> \
  --definition '<AI QP model definition JSON, with cluster_date_policy included in tag filtering/grouping>'
```

- Tags are written into the corresponding model definition as filters/grouping; do not pass low-level fields such as raw QP / events / event_view.
- To save report data for the tag itself, use `--model-type tag` and pass a tag report intent as the definition, e.g., `{"tag":{"tag_name":"vip_users","time_range":{"mode":"recent","unit":"day","value":7}}}`.
- To mount an Analysis Board: pass `--dashboard-ids '[<Analysis Board ID>]'` at creation, or use `ae-cli analysis dashboard create` to create an Analysis Board based on saved reports.
- **For `--model-type event` only**, optionally use `--presentation` to set the chart type (line/combo/bar/stacked/cumulative/pie) and table layout according to the resolved product references `references/report_create.md` and `references/event_report_presentation.md`. Check the selected chart's grouping, time-granularity, and series requirements. Omit `--presentation` for all other report models.

## Step 4: Verify and deliver

1. After successful creation, use `ae-cli analysis report get` to confirm the report definition, tag references, and version mode are correct.
2. Explain to the user: the tag used, the version mode (and the specified date), and the report location or entry point.
3. When the user later adjusts the version mode or date, use `ae-cli analysis report update` to update the definition.

## ⛔ Prohibitions

1. DO NOT fabricate `tag_name`, report IDs, or Analysis Board IDs; everything is subject to the actual command output.
2. DO NOT default to LATEST when the user explicitly requests history versions/dynamic matching; the version mode must be written into the definition according to the user's confirmed need.
3. When the history version status of the target date is `miss`, first backfill per Part Two and verify `normal`, then build the report.

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
