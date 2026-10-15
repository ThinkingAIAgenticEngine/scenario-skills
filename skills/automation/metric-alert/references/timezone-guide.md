# Time Zone Handling Guide

This file is the single authoritative reference for how the metric-alert skill handles time zones. It must be followed in both the configuration phase and the runtime phase.

---

## Core Concepts

| Concept | Description | Source |
|---------|-------------|--------|
| **Project Time Zone** | `default_time_zone_offset` in the project configuration, e.g. UTC+8 | `ae-cli project info get` |
| **Settlement Time Zone** | The time zone the user uses for business reporting, e.g. Vietnam UTC+7 | **Confirmed by the user**; defaults to the project time zone |
| **Scheduling Time Zone** | The time zone in which the server executes scheduled tasks, e.g. Asia/Shanghai | `scheduleTimeZone` returned by `ae-cli agent +list-automations` |
| **Time Zone Offset Column** | The field in event data that records the time zone each record belongs to; defaults to `#zone_offset` | Project configuration `time_zone_offset_column`; falls back to the default if empty |

---

## Decision Flow

Executed in Step 1 of the configuration phase, "Environment Self-Check and Project Discovery":

```
1. Look up the project configuration
  |
  v
2. time_zone_enabled = false?
  |-- YES -> single time zone project; no need to ask the user for a settlement time zone; use the "single time zone template" in SQL
  `-- NO  -> multi time zone project; continue below
  |
  v
3. Ask the user: which settlement time zone to use? (default: project time zone UTC+X)
  |
  v
4. Look up the scheduling time zone (server time zone)
  |
  v
5. Compute the scheduling time recommendation (see formula below)
  |
  v
6. Use the "multi time zone template" in SQL
```

---

## Single Time Zone Projects

**Characteristics**: `time_zone_enabled = false`

**SQL approach**: Filter directly on `#event_time` without any offset

```sql
SELECT ...
FROM ta.v_event_<PROJECT_ID>
WHERE "$part_event" = '<EVENT>'
  AND "$part_date" = '<DATE>'
  AND "#event_time" >= TIMESTAMP '<DATE> 00:00:00'
  AND "#event_time" <  TIMESTAMP '<DATE+1> 00:00:00'
```

**Example**: To report full-day data for 2026-08-18, write the time filter as `>= TIMESTAMP '2026-08-18 00:00:00' AND < TIMESTAMP '2026-08-19 00:00:00'`.

**Notes**:
- In a single time zone project, `$part_date` and `#event_time` fall on the same calendar date, so direct filtering is sufficient. Data delayed writes are handled by scheduling delay (e.g. `minute=05`); there is no need to widen `$part_date`. Multi time zone projects need to expand by 1 day on both sides because the time zone offset can shift records across day boundaries; this is not a data-loading latency issue
- Use a half-open interval `[start, next day start)` for the time window; do NOT write a closed interval like `< '... 23:59:59'` - that would miss data between 23:59:59 and 24:00

---

## Multi Time Zone Projects

**Characteristics**: `time_zone_enabled = true`

**Core rules**:
1. **Every SQL statement must first filter dates by `$part_date`**, then apply the multi time zone offset
2. **The `$part_date` filter range must cover 1 extra day on each side** of the target date, to prevent records that cross a day boundary after the offset from being dropped
3. **Apply the time zone offset in a subquery**, and use the shifted time in the outer query for precise filtering
4. **`$part_date` is a varchar** and can only be compared against strings in `'YYYY-MM-DD'` format; comparing it directly against a `date()` function or an `INTERVAL` expression will raise a type error. To express "expand by 1 day on each side", first convert with `date_format(date('<DATE>') - INTERVAL '1' DAY, '%Y-%m-%d')` and then compare as a string
5. **`$part_date` is the partition date, not the settlement time zone natural day**: which business natural day an event falls into must be determined by converting to `shifted_time` and then applying `date(shifted_time)`; `$part_date` is only used as a coarse partition filter (rule 2). Filtering a multi time zone project directly by `$part_date` = target date will mis-attribute records that cross a day boundary after the offset

### Time Zone Offset Formula

```sql
IF((("{time_zone_offset_column}" IS NOT NULL) AND ("{time_zone_offset_column}" >= -30) AND ("{time_zone_offset_column}" <= 30)), date_add('second', CAST(({settlement_time_zone} - "{time_zone_offset_column}") * 3600 AS integer), "#event_time"), "#event_time")
```

(Illustrative form; placeholders are for illustration only. When actually generating SQL, use the `{{settle_tz}}` / `{{tz_column}}` versions in each template in [`sql-templates.md`](sql-templates.md).)

Meaning: convert the event time from "the time zone the data belongs to" to "the settlement time zone".

**Fallback for NULL and dirty values**: when the offset column is NULL or clearly outside the business range (the templates use +/-30 hours as the bound), the IF branch does not match and `shifted_time` falls back to the original `#event_time` - these rows still participate in subsequent window filtering under the settlement time zone, and are not silently dropped because the offset result is NULL. When the field contains a few scattered dirty values, results will lean toward the settlement time zone; when the field itself has low credibility, confirm with the user during the configuration phase whether to switch to the single time zone approach.

**Example**: data time zone UTC-5, settlement time zone UTC+8
```
offset seconds = (8 - (-5)) * 3600 = 46800 seconds = 13 hours
shifted time = original time + 13 hours
```

**Daylight Saving Time**: both the settlement time zone and the data time zone are expressed as fixed integer hour offsets; regions that observe daylight saving time (e.g. US Eastern: UTC-4 in summer, UTC-5 in winter) are NOT supported - a 1-hour window misalignment will occur on the transition day. If the business time zone observes DST and is sensitive to boundaries, manually watch the transition week, or configure separate offsets before and after the transition.

### Standard SQL Structure

```sql
SELECT ...
FROM (
  SELECT
   ...,
   IF((("{TZ_COLUMN}" IS NOT NULL) AND ("{TZ_COLUMN}" >= -30) AND ("{TZ_COLUMN}" <= 30)), date_add('second', CAST(({SETTLE_TZ} - "{TZ_COLUMN}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_<PROJECT_ID>
  WHERE "$part_event" = '<EVENT>'
   AND "$part_date" BETWEEN '<DATE-1>' AND '<DATE+1>'  -- expand 1 day on each side
) t
WHERE date(shifted_time) = date('<DATE>')           -- precise filter using the shifted time
  -- subsequent window filtering uses shifted_time
```

**Key points**:
- Inner `$part_date` filter: wide (1 extra day on each side)
- Outer `date(shifted_time)` filter: strict (exactly 1 day)
- Window filtering uses `shifted_time`, not `#event_time`

### Pre-Delivery Boundary Check (Multi Time Zone + Natural Day)

When a list / counting task involves the natural day definition, run a read-only check SQL before delivery to spot-check boundary rows: pick rows from the matched detail whose `shifted_time` falls near the natural day boundary (e.g. within 1 hour before and after 00:00), and verify row by row that the conversion from the original `#event_time` and the offset column value is correct - if boundary rows show "should be in the list but are not / should not be in the list but are", the natural day definition is wrong (the most common cause: treating `$part_date` as the settlement time zone natural day and filtering on it directly). Deliver only after the check passes; the spot check is read-only and does not require creating any platform asset.

---

## Scheduling Time Conversion

**Problem**: when the settlement time zone and the server scheduling time zone differ, when should the scheduled task fire to ensure data completeness?

**Formula**:

```
Earliest time the daily data is complete (server time zone) = 00:00 + (server time zone - settlement time zone) hours

Example 1: settlement time zone UTC+7 (Vietnam), server time zone UTC+8 (Beijing)
  Vietnam 8.18 24:00 = Beijing 8.19 01:00
  Earliest complete time = 00:00 + (8 - 7) = 01:00 (Beijing time)
  -> the scheduled task must fire after 01:00 Beijing time

Example 2: settlement time zone UTC-5 (US Eastern), server time zone UTC+8 (Beijing)
  US Eastern 8.18 24:00 = Beijing 8.19 13:00
  Earliest complete time = 00:00 + (8 - (-5)) = 13:00 (Beijing time)
  -> the scheduled task must fire after 13:00 Beijing time
```

**Adding data latency** (e.g. payment data delayed by 30 minutes):

```
Recommended schedule time = earliest complete time + data latency
                 = 01:00 + 00:30 = 01:30 (Beijing time)
```

**Configuration phase script** (echo both time zones as a pair; neither can be omitted):

```
Agent: Confirmed settlement time zone is UTC+7.

     Server scheduling time zone is Asia/Shanghai (UTC+8).
     Daily data closes at 24:00 Vietnam time, which converts to 01:00 Beijing time.

     Recommended schedule time: after 01:00 every day (Beijing time).
     That is: the task will fire at 01:30 in server time zone UTC+8, and the data is day-bucketed by settlement time zone UTC+7.
     If you need to reserve time for data latency, please tell me the latency in minutes (e.g. 30 minutes).
```

**Paired echo template** (use this sentence pattern whenever mentioning trigger time and reporting definition):

> The task will fire at <HH:MM> in **server time zone <X>**; data is day-bucketed / hour-bucketed by **settlement time zone <Y>**.

Whenever the schedule time is mentioned in any delivery, confirmation, or summary, both the server time zone and the settlement time zone must be given together; mentioning only one side is not allowed - saying only "fires at 01:00 every day" without stating which time zone it refers to leaves the user unable to verify whether the reporting definition is correct.

---

## Difference Between Schedule Time and Window Time

| Concept | Description | Example |
|---------|-------------|---------|
| **Schedule Time** | When the scheduled task fires | Every day at 09:00 (Beijing time) |
| **Window Time** | Which time period of data to report | Full previous day (Vietnam time 00:00-24:00) |

**The two are independent**:
- Schedule time is determined by the cron expression of the automation and is interpreted in the server time zone
- Window time is determined by the time filter conditions in the SQL and is interpreted in the settlement time zone

**Statements must be paired**: when reporting the trigger time to the user, the server time zone and the settlement time zone must both appear (see the paired echo template above).

**Example**: settlement time zone UTC+7, schedule time 09:00 Beijing time
- 09:00 Beijing time = 08:00 Vietnam time
- If the window is "full previous day", the SQL reports data for Vietnam time 8.17 00:00-24:00
- If the window is "today so far", the SQL reports data for Vietnam time 8.18 00:00-08:00

---

## Time Zone Offset Column Name

**Default**: `#zone_offset`

**Custom**: when the project configuration `time_zone_offset_column` is non-empty, use the customer-specified column name.

**Must check during the configuration phase**:

```bash
ae-cli project info get -p <PROJECT_ID> --format json
```

Fields to read:
- `time_zone_offset_column`: if empty use `#zone_offset`; if non-empty use the specified column name
- `default_time_zone_offset`: the project default time zone
- `time_zone_enabled`: whether multi time zone is enabled

---

## Common Mistakes

| Mistake | Consequence | Correct Approach |
|---------|-------------|------------------|
| Filter directly on `#event_time` without applying an offset | Multi time zone project data is attributed to the wrong date | Apply the offset first, then filter on `shifted_time` |
| Treat `$part_date` as the settlement time zone natural day and filter by it = target date | Rows that cross a day boundary after the offset are attributed to the wrong date (rows that should / should not be in the list are misclassified) | Use `$part_date` only as a coarse partition filter expanded by 1 day on each side; determine the natural day with `date(shifted_time)` |
| Filter `$part_date` to only the single target date | Records that cross a day boundary after the offset are dropped | Expand `$part_date` by 1 extra day on each side |
| Compare `$part_date` directly against `date()` / `INTERVAL` | Type mismatch between varchar and date; SQL raises an error | Convert to a string first with `date_format(date(...) +/- INTERVAL 'n' DAY, '%Y-%m-%d')` and then compare |
| Write the time window as a closed interval `< '... 23:59:59'` | Misses data between 23:59:59 and 24:00 | Use a half-open interval `[start, next day start)` |
| Use `AT TIME ZONE` for conversion in SQL | Double offset; results are wrong | Use `date_add` to apply the offset manually |
| Configure the schedule time in the settlement time zone | The server does not recognize it; the trigger time is wrong | The schedule time must be configured in the server time zone |
| Confuse window time with schedule time | The reported period is wrong | Window time follows the settlement time zone; schedule time follows the server time zone |
