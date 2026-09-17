---
name: new-old-user-define
description: "Trigger when the user asks how to create or define a new/old user property or field, how to distinguish or filter new vs old users in analysis when tracking does not report such a field, or how to implement a 24-hour vs calendar-day new/old rule. The Skill first performs prerequisite checks on registration time reporting and #zone_offset timezone identification grouped by #data_source, then guides the user to confirm the new/old definition or a user tag fallback, and creates a virtual event property using DATE_DIFF SQL so the property can be used in analysis models. Do not trigger when tracking already directly reports a usable new/old classification field and the user only needs to query that field, or for unrelated virtual property creation."
---

# New/Old User Virtual Property Creation Guide

## Purpose

Use this Skill when a customer's tracking does not report a "new/old user" classification field, but the customer needs to filter or group users as new vs old in Events Analysis, Funnel, Retention, Distribution, or similar models. The Skill builds a virtual event property based on reported registration time, or falls back to a first/last user tag when registration time is not available. It does not analyze the resulting new/old distribution beyond confirming the property was created.

## Trigger Scenarios

Trigger when the user mentions:

- "How do I create a new/old user property or obtain a new/old user field?"
- Tracking or event properties do not report a new/old user classification field, but analysis requires new-user/old-user filtering.
- The user asks how the definition of new/old users, such as 24-hour rule vs calendar-day rule, can be implemented in TE.
- The user wants to filter or group by new/old users, but the corresponding property is missing.
- The user wants an approximate new/old user solution through a user tag when registration time is not reported, or is reported in local time.

Do not trigger when:

- Tracking already reports a directly usable new/old classification field and the user only wants to query or use that field.
- The request is ordinary virtual property creation unrelated to new/old users.

## Business Problem

The customer needs a reusable new/old user classification asset. Without it, every analysis model must manually reconstruct the rule, and definitions may become inconsistent. This Skill produces one virtual event property such as `#vp@user_type_24h`, so analysts can consistently filter the same definition across models.

## Inputs and Data Requirements

Required inputs or discoverable facts:

- Project ID selected in the current session.
- Whether user property metadata contains a registration-time-like field.
- The actual event table reference for the project.
- `#zone_offset` behavior grouped by `#data_source`.

Minimum useful data conditions:

- The event table must have analyzable event data; if no event data exists, the virtual property cannot be verified.
- Either a reported registration time user property must exist, or a sufficient registration/account-creation event must exist for a tag fallback.

Degradation path:

- If a registration time user property does not exist but a registration-like event exists and the user accepts lower tag timeliness, use the first/last tag branch.
- If neither exists, stop and tell the user that registration time must be reported first, or a new/old field must be reported directly.
- If registration time is reported in local time and timezone handling is inconsistent with event reporting, precise data cannot be created. Offer the user either fixing tracking or using the tag fallback.

## Core Method

1. Obtain the project ID, preferring the session-selected project.
2. Check whether registration time is reported as a user property.
3. Identify timezone behavior for each data source using `#zone_offset` grouped by `#data_source`.
4. Confirm three points with the user at once: new/old classification rule, registration time reporting timezone, and whether the identified data-source timezone behavior matches reality.
5. Decide whether timezone conversion is required.
6. Build the virtual property SQL using `DATE_DIFF` between event time aligned to the registration time timezone and registration time.
7. Create the virtual property and reply with one concise completion sentence.

## Questioning Discipline

Ask the user to confirm only these three points, all at once:

1. New/old classification rule: 24-hour rule or calendar-day rule.
2. Which timezone the registration time user property is reported in.
3. Whether the identified timezone behavior for each data source matches the actual reporting situation.

Do not ask the user to discover metadata that can be queried directly, such as whether a field exists, the `#zone_offset` distribution, or the event-table name. Do not ask whether tracking can directly report a new/old field unless the customer proactively says such a field already exists.

## Workflow

### Step 0: Obtain the Project ID

Prefer the project already selected in the UI and injected into the session environment.

```bash
printenv TE_AGENT_CURRENT_SESSION_SELECTION_JSON
```

Parse `projectIds` from the returned JSON. Example: `{"projectIds":["9"]}` means project_id is `9`. If `projectIds` already has a value, do not call a full project enumeration API.

Fall back to enumeration only when the environment variable does not exist or `projectIds` is empty. In the fallback, use `--jq` to fetch only key fields such as `projectId` and `projectName`. If multiple projects are returned, confirm which one to use with the user.

### Step 1: Check Whether Registration Time Is Reported

Query user property metadata:

```bash
ae-cli analysis-meta property list --project-id <project_id> --scope user --queries '["registration","time","install","register","signup","creation time"]'
```

If a registration-time-like user property exists, for example `install_time`, `#reg_time`, or a property named "registration time", spot-check recent event data to confirm it has values and is being reported continuously. If confirmed, proceed to Step 2.

If no such user property exists, or the spot-check shows all values empty, treat registration time as not reported and go to the Step 6 tag solution branch.

### Step 2: Identify Timezone Behavior by Data Source

First obtain the real event table reference. Do not guess the table name.

```bash
ae-cli analysis sql-table list --project-id <project_id> --queries '["event"]'
```

Then run ad-hoc SQL to inspect `#zone_offset` grouped by `#data_source`. Event table SQL must include the `"$part_date"` partition condition.

```sql
SELECT "#data_source", "#zone_offset", COUNT(*) AS cnt
FROM <event_table_table_ref>
WHERE "$part_date" = '<yesterday_date yyyy-MM-dd>'
GROUP BY 1, 2
ORDER BY 1, cnt DESC
```

If yesterday has no data, first probe the data date range:

```sql
SELECT MIN("$part_date"), MAX("$part_date")
FROM <event_table_table_ref>
WHERE "$part_date" BETWEEN '1970-01-01' AND '<today_date yyyy-MM-dd>'
```

Then switch to a partition range that has data. Every event-table query, including a date-range probe, must contain a `"$part_date"` predicate. The broad probe may scan many partitions; narrow it if a reliable project start date is available.

Determine each `#data_source` separately:

- `#zone_offset` is always the same fixed value: this data source reports in a fixed timezone.
- `#zone_offset` shows multiple different values: this data source reports in multiple timezones, meaning local time.
- Some null and some values: determine behavior from the specific values found. Do not assume null rows have the same offset; use a fallback only when the reporting timezone for those rows is confirmed.
- All null: ask the user for that data source's actual reporting timezone. After receiving it, treat it as fixed-timezone reporting. SQL can use `COALESCE("#zone_offset", <confirmed_timezone_value>)` only if that fallback applies to every null row used by the expression.

If `#data_source` cannot be resolved or is unavailable, use another available source identifier such as `#lib`. If none exists, determine from the overall `#zone_offset` distribution and show the identification result for user confirmation in Step 3.

### Step 3: Confirm Three Points with the User

Ask all three points at once and do not add extra questions:

1. **New/old classification rule**
   - A. 24-hour rule: a full 24 hours makes an old user. Example: registered Sep 1 15:00, triggers an event Sep 2 00:01: still new; triggers Sep 2 15:01: old.
   - B. Calendar-day rule: crossing a calendar day makes an old user. Example: registered Sep 1 15:00, triggers an event Sep 2 00:01: old.
   - If the user is unsure, explain the difference using these examples. Do not choose a default on the user's behalf.

2. **Registration time reporting timezone**
   - Ask whether the registration time user property is reported as a fixed timezone value, such as UTC+8 = `8`, or as local time that varies by device.

3. **Data source timezone behavior confirmation**
   - Show the Step 2 result for each `#data_source`: fixed timezone or multiple timezones/local time, and ask whether it matches actual reporting.

### Step 4: Decide Timezone Handling

Based on Steps 2 and 3:

- If the registration time user property has a confirmed fixed UTC offset, compare that numeric offset with every event row's `#zone_offset`, across all data sources. Use the timezone-consistent SQL in Step 5 only if they are equal for every relevant row. Fixed reporting by itself is insufficient: registration time at UTC+8 and events at UTC+0 require conversion.
- If any event row has a different offset, use the timezone-conversion SQL in Step 5. For null offsets, use a confirmed fallback for the affected data source; if the null rows cannot be assigned a reliable offset, stop rather than silently classify them.
- If the registration time user property is reported in local time that varies by user, do not assume it shares an event's timezone. The event's `#zone_offset` describes the event, not necessarily the user's timezone at registration. This workflow cannot classify it precisely without a reliable registration-time offset for each user. Offer the customer two choices:
  1. Fix tracking so registration time is reported in a fixed timezone, then reprocess. This run ends.
  2. Use the Step 6 tag creation method to approximate new/old users.

### Step 5: Build the SQL Expression

Replace `install_time` with the real registration time user property. The user property reference format is `ta_u."field_name"`. System fields containing `#` must also be double-quoted, such as `ta_u."#reg_time"`.

If a user tag is used after Step 6, the reference format is `ta_tag."tag_machine_name"`, such as `ta_tag."first_register_time"`. Do not write `ta_t."..."`, `ta_u."#tag_..."`, or any other form. The `ta_tag` and `ta_u` aliases work only during virtual property SQL compilation; ad-hoc SQL cannot resolve them, so do not verify this syntax with `analysis adhoc run`.

Identifiers containing special characters such as `#` and `@` must be wrapped in double quotes in Trino SQL.

#### Timezone-consistent version

Rule A, 24-hour rule:

```sql
DATE_DIFF('day', ta_u."install_time", "#event_time")
```

Rule B, calendar-day rule:

```sql
DATE_DIFF('day', date(ta_u."install_time"), date("#event_time"))
```

#### Timezone-conversion version

The example uses `-7` only as a placeholder. Replace it with the real registration-time reporting timezone. Use `8` for UTC+8.

If `#zone_offset` is null, replace it with a confirmed fallback for those rows. When null rows from different data sources require different offsets, select the fallback by `#data_source` (or the confirmed source identifier); do not use one global `COALESCE` value.

Rule A, 24-hour rule:

```sql
DATE_DIFF(
    'day',
    ta_u."install_time",
    DATE_ADD('minute', CAST((-7 - "#zone_offset") * 60 AS INTEGER), "#event_time")
)
```

Rule B, calendar-day rule:

```sql
DATE_DIFF(
    'day',
    date(ta_u."install_time"),
    date(DATE_ADD('minute', CAST((-7 - "#zone_offset") * 60 AS INTEGER), "#event_time"))
)
```

The result is a difference in days and is numeric. Use `number` for `--select-type`.

### Step 6: Tag Solution Branch

Use this branch when:

- Registration time is not reported as a user property; or
- Registration time is reported in local time and precise data cannot be created, and the customer chooses the tag method instead of fixing tracking.

First explain the tradeoff and ask for acceptance:

- Because registration time is unavailable or imprecise, a user tag based on registration behavior can approximate new/old users.
- Configure a daily refresh for this tag. Newly registered users may remain unclassified until the next completed refresh. Once their registration timestamp is in the tag, the virtual property's new/old result follows each event's time. Without a refresh schedule, the tag does not update automatically.

If the customer accepts, create a first/last tag with these confirmed settings:

- **Tag type**: first/last tag, taking the first occurrence.
- **Tag name**: any business-meaningful name such as "First Registration Time". Record the tag machine name because Step 5 must reference it.
- **Timezone**: confirm a numeric offset supported by the project; UTC+8 is only an example. Use the confirmed value in Step 5.
- **Analysis time range**: from the project's first reporting date through today. Verify the first reporting date before entering it; do not guess.
  - Query the earliest event partition with:

```sql
SELECT MIN("$part_date") AS first_date
FROM <event_table_table_ref>
WHERE "$part_date" BETWEEN '1970-01-01' AND '<today_date yyyy-MM-dd>'
```

- **Analysis metric**: `#event_time` of the first account registration event. Confirm the registration event name from metadata, such as `register`, `sign_up`, or "registration". Do not fabricate it.

Create the tag with the confirmed event, first reporting date, and timezone. Choose a daily refresh time in the tag timezone:

```bash
ae-cli analysis user-tag create \
  --project-id <project_id> \
  --tag-name first_register_time \
  --display-name 'First Registration Time' \
  --zone-offset <confirmed_numeric_offset> \
  --definition-request '{"type":"first_last","first_last":{"event":"<confirmed_registration_event>","occurrence":"first","calculation":"specific_time","time_range":{"mode":"start_to_today","start_time":"<first_date>"}}}' \
  --auto-refresh-schedule '{"frequency":"daily","time":"02:30"}'
```

Creation starts the initial computation but does not mean its value is ready. Poll `ae-cli analysis user-tag get --project-id <project_id> --tag-names '["first_register_time"]'` until `progress=100` and `refresh_time` is present; confirm `enable_auto_refresh=1` and the saved schedule. If computation fails, resolve it before creating the virtual property.

After the tag is ready, continue with the Step 5 SQL using the classification rule confirmed in Step 3. Use the confirmed tag timezone in conversion and replace the registration time field with the first/last tag using `ta_tag."tag_machine_name"`. Example for calendar-day rule with tag machine name `first_register_time` and confirmed UTC+8 timezone:

```sql
DATE_DIFF(
    'day',
    date(ta_tag."first_register_time"),
    date(DATE_ADD('minute', CAST((8 - "#zone_offset") * 60 AS INTEGER), "#event_time"))
)
```

If the customer does not accept the tag solution, inform them that the technical tracking side must first report registration time in a fixed timezone as a user property, or directly report a new/old classification field. Related data can only be viewed after that reporting is complete. End this run.

### Step 7: Create the Virtual Property

Before creating, show the user a confirmation table:

| Item | Value |
|---|---|
| Property name | `#vp@user_type_24h` or another valid `#vp@...` machine name |
| Display name | Recommended to include the rule, such as "New/Old User_24h Rule" |
| Source field | Real registration time field or tag machine name |
| SQL expression | SQL built in Step 5 |
| Report timezone | Numeric timezone used in conversion, if applicable |
| Classification rule | 24-hour rule or calendar-day rule |

After user confirmation, execute:

```bash
ae-cli analysis-meta virtual-property create \
  --project-id <project_id> \
  --property-name '#vp@user_type_24h' \
  --property-desc 'New/Old User_24h Rule' \
  --table-type event \
  --select-type number \
  --sql-expression '<SQL built in Step 5>' \
  --sql-event-relation-type relation_default
```

Equivalent UI path: Event Management → Event Properties → Virtual Event Properties.

After successful creation and the verification below, reply with only one sentence and end the workflow:

> Created virtual property "New/Old User_24h Rule" (`#vp@user_type_24h`): filter this property < 1 for new users, >= 1 for old users.

Do not add trial distribution calculations, percentages, charts, summary reports, UI path suggestions, or other content after that sentence.

## Verification and Self-Check

Before confirming the virtual property is ready:

- Confirm every field name in SQL exists in real metadata and matches the intended type.
- Confirm the registration time or tag field was not fabricated.
- Confirm timezone conversion direction is `(registration-time reporting timezone - #zone_offset)`, not reversed.
- Confirm the tag reference is `ta_tag."tag_machine_name"`, not a user property or event property alias.
- Confirm the classification rule selected by the user is the one encoded in SQL.
- After creation, verify the property can be used in one analysis model query, such as Events Analysis grouped by this virtual property. If the model compiles and returns data normally, the property is usable.

## Exception Handling

- **Registration time field not found**: re-query with synonyms such as `signup`, `create`, `registration`, or "creation time". If still not found, use the Step 6 tag branch.
- **Customer does not know the registration time reporting timezone**: ask the customer to confirm with the technical team. Do not guess the timezone value. Explain that a wrong timezone shifts the entire new/old classification.
- **Creation fails**: check whether field names match metadata, whether special characters are double-quoted, and whether the report timezone is numeric.
- **Creation fails with "Event property ta_xxx.field has been hidden or deleted"**: the reference alias was not recognized. User tags must use `ta_tag."tag_machine_name"`; user properties must use `ta_u."property_name"`. Forms such as `ta_t."..."` and `ta_u."#tag_..."` do not work.
- **Ad-hoc SQL cannot resolve `ta_tag`/`ta_u` aliases**: this is expected. Verify through an analysis model, not ad-hoc SQL.
- **Abnormal result percentages**: first check timezone conversion direction and registration time field definition.
- **No event data available**: stop and report that the virtual property cannot be verified until event tracking exists.
