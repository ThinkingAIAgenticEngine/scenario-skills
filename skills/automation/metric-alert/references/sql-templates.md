# SQL Template Library

This file lists all SQL templates. In configuration phase step 4B (automation path), select a template based on the business scenario, fill in business parameters, and write it into the `sql_template` field of `alert_rule.json`.

**Core Principles** (must be followed):
1. **Any SQL querying the event table must first filter by `$part_date`** (except SQL that only queries the user table `ta.v_user_*` — the user table has no partition column)
2. **Multi-timezone projects**: widen `$part_date` by 1 day on each side, perform timezone shift in the subquery, and use the shifted time for precise filtering in the outer query
3. **`SELECT *` is forbidden**: event wide tables can have thousands of columns
4. **`LIMIT` is mandatory**: prevents accidental full-table returns
5. **`$part_date` only compares with strings**: `$part_date` is varchar; comparing it directly with `date()` functions or `INTERVAL` expressions raises a type error. To express "widen by 1 day on each side", use `date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d')` to convert to a string first, then compare
6. **List-type monitoring should use the `natural_day` window**: list filtering (Template 12) commonly uses a lookback-N-days definition; the right end of a `today_to_now` window drifts with the trigger time, so the same user triggering at different times yields different lists; only a day-level definition paired with `natural_day` is reproducible

**Placeholder Reference**:

| Placeholder | Description | Filled at Config Phase | Replaced at Runtime |
|--------|------|-------------|-------------|
| `{{project_id}}` | Project ID | Yes | No |
| `{{event_name}}` | Event name | Yes | No |
| `{{metric_prop}}` | Property name | Yes | No |
| `{{aggregate_expr}}` | Aggregate expression (see quick reference at end) | Yes | No |
| `{{settle_tz}}` | Settlement timezone (hour offset) | Yes | No |
| `{{tz_column}}` | Timezone offset column name | Yes | No |
| `{{filters}}` | Event filter conditions (starts with AND, may be empty) | Yes | No |
| `{{numerator_event}}` | Numerator event name (Template 5) | Yes | No |
| `{{denominator_event}}` | Denominator event name (Template 5) | Yes | No |
| `{{new_user_event}}` | New user event name (Templates 8/9) | Yes | No |
| `{{date}}` | Target date (YYYY-MM-DD) | No | Yes |
| `{{window_start}}` | Window start time | No | Yes |
| `{{window_end}}` | Window end time | No | Yes |
| `{{week_start}}` / `{{week_end}}` | Natural week start/end dates (Template 4 and Template 11 custom) | No | Yes |
| `{{base_date}}` | Retention base date (Templates 8/9 only) | No | Yes |
| `{{current_hour}}` | Window hour count (today_to_now) / window end hour (other windows, `HH` two digits) | No | Yes |

**`{{current_hour}}` semantics**: under a today_to_now window it is the number of complete hours covered by the window (from 00:00 of the day to the last full hour; running at 14:35 = `14`; running during 00:00~00:59 which falls back to the entire previous day = `24`); for other windows it is the hour of the window end time (`HH` two-digit string, e.g. natural_hour window 13:00~14:00 = `14`). Used by Template 11 custom SQL (typically for hourly-average calculations like `metric_value / {{current_hour}}`); other templates do not reference it.

**Placeholders that must be resolved at config phase** (all replaced with concrete content before writing into `alert_rule.json`):

| Placeholder | Used in Template | Resolution |
|--------|----------|----------|
| `{{time_filter}}` | 3, 5, 10 | Select from the "Time Filter Placeholders" table at the end based on window type, or leave empty (natural day only) |
| `{{time_filter_shifted}}` | 3, 5, 10 | Same as above, with `#event_time` replaced by `shifted_time` |
| `{{return_event_filter}}` | 8, 9 | If `return_event` is non-empty: `AND "$part_event" = '<return_event>'`; otherwise leave empty |
| `{{retention_days}}` | 8, 9 | Write the number directly, e.g. `1`, `7` |
| `{{retention_days-1}}` / `{{retention_days+1}}` | 8, 9 | Compute and hardcode at config phase; e.g. when retention_days=7, write `6` and `8` |
| `{{group_dimension}}` / `{{group_limit}}` | 10 | Group-by property name / group limit (recommended 1000) |
| `{{result_columns}}` | 12 | Result column names, written as `user_id, account_id, last_active_time` (aliases must match the `result_columns` field; see Template 12 for list ID rules) |
| `{{step1}}` / `{{step2}}` / `{{step3}}` | 6, 7 | Funnel step event names |
| `{{active_event}}` / `{{pay_event}}` | 12 | Activity determination event / payment event name (two events for churn monitoring; see Template 12 "High Spender Definition Confirmation") |
| `{{amount_prop}}` / `{{big_r_threshold}}` / `{{lookback_days}}` | 12 | Payment amount field name / High Spender threshold / payment lookback window days (all are business inputs; do not copy example values verbatim) |
| `{{inactive_days_minus_1}}` | 12 | N-1 of "inactive in the last N days" (fill `6` for last 7 days) |
| `{{big_r_prop}}` | 12b | High Spender determination user property name (discover from user property metadata, confirm with the user) |
| `{{step_window_ab}}` / `{{step_window_bc}}` | 6 | Inter-step window period (fill only if the customer constrains step intervals, otherwise leave empty): fill in the form `AND b.event_time <= date_add('minute', N, a.event_time)`, where N is the constrained minutes; see Template 6 "Window Period Filling" |

**How to assemble `{{filters}}`**: when `metric.filters` is non-empty, the value is a complete condition starting with `AND` (e.g. `AND "channel" = 'AppStore'`), which directly replaces `{{filters}}` in the template; when empty, delete the entire `{{filters}}` line. All business placeholders must be replaced before writing — any residual placeholder detected at runtime causes an immediate error.

**Common multi-timezone structure** (shared by all multi-timezone template versions; see [`timezone-guide.md`](timezone-guide.md) for details):

- The inner subquery performs the timezone shift: `IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time`
- When `"{{tz_column}}"` is NULL or out of the ±30 hour range (dirty value), the IF branch does not apply and `shifted_time` falls back to the original `#event_time` — these rows participate in window filtering under the settlement timezone and are not silently dropped due to a NULL shift result
- The inner `$part_date` filter is widened (extend 1 day on each side of the target date, using `date_format(date(...) ± INTERVAL '1' DAY, '%Y-%m-%d')` to convert to string before comparison); list-type lookback windows (Template 12) are an exception — only the left end is widened; for the right end see the template's own upper-bound constraint
- The outer query uses the shifted `shifted_time` for precise filtering (`date(shifted_time) = date('{{date}}')` + window conditions)
- Single-timezone projects filter directly on `#event_time` without shifting; how to determine whether a project is single/multi-timezone is covered in [`timezone-guide.md`](timezone-guide.md) "Determination Flow"

---

## Template 1: Single Metric + Natural Hour

**Scenario**: hourly DAU, hourly order volume

### Single-Timezone Version

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" = '{{date}}'
  AND "#event_time" >= TIMESTAMP '{{window_start}}'
  AND "#event_time" <  TIMESTAMP '{{window_end}}'
  {{filters}}
LIMIT 1
```

### Multi-Timezone Version

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM (
  SELECT
    "{{metric_prop}}",
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
    {{filters}}
) t
WHERE date(shifted_time) = date('{{date}}')
  AND shifted_time >= TIMESTAMP '{{window_start}}'
  AND shifted_time <  TIMESTAMP '{{window_end}}'
LIMIT 1
```

---

## Template 2: Single Metric + Natural Day

**Scenario**: daily GMV, daily new users

### Single-Timezone Version

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" = '{{date}}'
  {{filters}}
LIMIT 1
```

### Multi-Timezone Version

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM (
  SELECT
    "{{metric_prop}}",
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
    {{filters}}
) t
WHERE date(shifted_time) = date('{{date}}')
LIMIT 1
```

---

## Template 3: Single Metric + Today-to-Now (00:00 to Now)

**Scenario**: today's cumulative payment amount, today's cumulative active users

**Today-to-now window filtering** (the today-to-now row of the "Time Filter Placeholders" table at the end): `>= TIMESTAMP '{{window_start}}'` and `< TIMESTAMP '{{window_end}}'` (both ends are computed by the script based on window type and are always on the hour, ensuring reproducible results across multiple runs on the same day; a run at the 00:00 hour falls back entirely to the previous full day — see [`rule-schema.md`](rule-schema.md) "window sub-item"). The single-timezone version applies to `#event_time`; the multi-timezone version applies to `shifted_time`.

### Single-Timezone Version

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" = '{{date}}'
  {{time_filter}}
  {{filters}}
LIMIT 1
```

### Multi-Timezone Version

(Uses the common multi-timezone structure, with today-to-now window filtering applied in the outer query)

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM (
  SELECT
    "{{metric_prop}}",
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
    {{filters}}
) t
WHERE date(shifted_time) = date('{{date}}')
  {{time_filter_shifted}}
LIMIT 1
```

---

## Template 4: Single Metric + Natural Week

**Scenario**: this week's active users, this week's payment amount

### Single-Timezone Version

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" BETWEEN '{{week_start}}' AND '{{week_end}}'
  {{filters}}
LIMIT 1
```

### Multi-Timezone Version

```sql
SELECT {{aggregate_expr}} AS "metric_value"
FROM (
  SELECT
    "{{metric_prop}}",
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" BETWEEN date_format(date('{{week_start}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{week_end}}') + INTERVAL '1' DAY, '%Y-%m-%d')
    {{filters}}
) t
WHERE date(shifted_time) BETWEEN date('{{week_start}}') AND date('{{week_end}}')
LIMIT 1
```

---

## Template 5: Ratio Metric

**Scenario**: payment success rate = payment success / payment initiated

**Applicable windows**: natural_hour / natural_day / today_to_now. **Do not use this template for natural-week ratio monitoring** (`{{time_filter}}` has no week option; the script rejects it outright) — for week-level ratios, use Template 11 custom SQL with hand-written `{{week_start}}`/`{{week_end}}` placeholders, applying week filtering separately in the numerator and denominator CTEs.

**Shared filter note**: `{{filters}}` is inserted into both the numerator and denominator CTEs — it expresses "common property filtering for the counting definition" (e.g. channel = app store). **Filtering of the events themselves is not in `{{filters}}`**: the numerator and denominator are two different events (`{{numerator_event}}` / `{{denominator_event}}`), each distinguished by its own `$part_event` condition; if the numerator should only count "successful payment initiations" (e.g. `status = 'success'`), such **numerator-only conditions** must also not go into `{{filters}}` (they would incorrectly constrain the denominator) — instead use Template 11 custom SQL and add the condition separately in the numerator CTE.

### Single-Timezone Version

```sql
WITH numerator AS (
  SELECT {{aggregate_expr}} AS val
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{numerator_event}}'
    AND "$part_date" = '{{date}}'
    {{time_filter}}
    {{filters}}
),
denominator AS (
  SELECT {{aggregate_expr}} AS val
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{denominator_event}}'
    AND "$part_date" = '{{date}}'
    {{time_filter}}
    {{filters}}
)
SELECT
  n.val AS numerator_value,
  d.val AS denominator_value,
  CAST(n.val AS DOUBLE) / NULLIF(d.val, 0) AS metric_value
FROM numerator n, denominator d
LIMIT 1
```

### Multi-Timezone Version

```sql
WITH numerator AS (
  SELECT {{aggregate_expr}} AS val
  FROM (
    SELECT
      "{{metric_prop}}",
      IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
    FROM ta.v_event_{{project_id}}
    WHERE "$part_event" = '{{numerator_event}}'
      AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
      {{filters}}
  ) t
  WHERE date(shifted_time) = date('{{date}}')
    {{time_filter_shifted}}
),
denominator AS (
  SELECT {{aggregate_expr}} AS val
  FROM (
    SELECT
      "{{metric_prop}}",
      IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
    FROM ta.v_event_{{project_id}}
    WHERE "$part_event" = '{{denominator_event}}'
      AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
      {{filters}}
  ) t
  WHERE date(shifted_time) = date('{{date}}')
    {{time_filter_shifted}}
)
SELECT
  n.val AS numerator_value,
  d.val AS denominator_value,
  CAST(n.val AS DOUBLE) / NULLIF(d.val, 0) AS metric_value
FROM numerator n, denominator d
LIMIT 1
```

---
## Template 6: Funnel (Strict Order, Completed Within the Same Day)

**Scenario**: register → identity verification → payment, must occur in order, completed within the same day

**Determination semantics**: the user has an ordered event subsequence A < B < C (determined by event time; each step is not required to be its "first occurrence"). For example, if a user's behavior that day is B A C B A C — the first B precedes the first A, but there exists an A2 < B2 < C2 subsequence, so it still counts as completed.

**Step count**: the template is written for 3 steps. When the business has only 2 steps, delete the `c_events` section, the `JOIN c_events` and `{{step_window_bc}}` in `completed`, and the step3 count column, and change metric_value to `ab_users / step1`; for more than 3 steps, extend following the `x_events` + `JOIN x_events x ON ... x.event_time > previous event time` pattern, with metric_value always being the last step divided by the first step.

**Inter-step window period**: by default there is no interval constraint (steps only need to occur in order within the same day). Fill `{{step_window_ab}}` / `{{step_window_bc}}` only if the customer constrains step intervals (e.g. "complete within 30 minutes"); otherwise leave empty.

**Business filtering not yet supported**: the template has no `{{filters}}` insertion point and cannot filter step events by property; when filtering is needed, use Template 11 custom SQL instead.

### Single-Timezone Version

```sql
WITH step_events AS (
  SELECT
    "#user_id" AS user_id,
    "$part_event" AS event_name,
    "#event_time" AS event_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" IN ('{{step1}}', '{{step2}}', '{{step3}}')
    AND "$part_date" = '{{date}}'
),
a_events AS (
  SELECT user_id, event_time FROM step_events WHERE event_name = '{{step1}}'
),
b_events AS (
  SELECT user_id, event_time FROM step_events WHERE event_name = '{{step2}}'
),
c_events AS (
  SELECT user_id, event_time FROM step_events WHERE event_name = '{{step3}}'
),
ab_users AS (
  SELECT DISTINCT a.user_id
  FROM a_events a
  JOIN b_events b ON a.user_id = b.user_id AND b.event_time > a.event_time
    {{step_window_ab}}
),
completed AS (
  SELECT DISTINCT a.user_id
  FROM a_events a
  JOIN b_events b ON a.user_id = b.user_id AND b.event_time > a.event_time
    {{step_window_ab}}
  JOIN c_events c ON a.user_id = c.user_id AND c.event_time > b.event_time
    {{step_window_bc}}
)
SELECT
  COUNT(DISTINCT a.user_id) AS step1_users,
  (SELECT COUNT(*) FROM ab_users) AS step2_users,
  (SELECT COUNT(*) FROM completed) AS step3_users,
  CAST((SELECT COUNT(*) FROM completed) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.user_id), 0) AS metric_value
FROM a_events a
LIMIT 1
```

### Multi-Timezone Version

```sql
WITH step_events AS (
  SELECT
    "#user_id" AS user_id,
    "$part_event" AS event_name,
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" IN ('{{step1}}', '{{step2}}', '{{step3}}')
    AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
),
filtered_events AS (
  SELECT user_id, event_name, shifted_time FROM step_events
  WHERE date(shifted_time) = date('{{date}}')
),
a_events AS (
  SELECT user_id, shifted_time AS event_time FROM filtered_events WHERE event_name = '{{step1}}'
),
b_events AS (
  SELECT user_id, shifted_time AS event_time FROM filtered_events WHERE event_name = '{{step2}}'
),
c_events AS (
  SELECT user_id, shifted_time AS event_time FROM filtered_events WHERE event_name = '{{step3}}'
),
ab_users AS (
  SELECT DISTINCT a.user_id
  FROM a_events a
  JOIN b_events b ON a.user_id = b.user_id AND b.event_time > a.event_time
    {{step_window_ab}}
),
completed AS (
  SELECT DISTINCT a.user_id
  FROM a_events a
  JOIN b_events b ON a.user_id = b.user_id AND b.event_time > a.event_time
    {{step_window_ab}}
  JOIN c_events c ON a.user_id = c.user_id AND c.event_time > b.event_time
    {{step_window_bc}}
)
SELECT
  COUNT(DISTINCT a.user_id) AS step1_users,
  (SELECT COUNT(*) FROM ab_users) AS step2_users,
  (SELECT COUNT(*) FROM completed) AS step3_users,
  CAST((SELECT COUNT(*) FROM completed) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.user_id), 0) AS metric_value
FROM a_events a
LIMIT 1
```

**Window period filling** (fill only if the customer constrains step intervals; otherwise leave the entire line empty; N is the number of minutes given by the customer, written directly as a number, e.g. `30`):

| Position | When left empty | When constrained |
|------|--------|---------|
| `{{step_window_ab}}` | (empty line) | `AND b.event_time <= date_add('minute', N, a.event_time)` |
| `{{step_window_bc}}` | (empty line) | `AND c.event_time <= date_add('minute', N, b.event_time)` |

(Note the window anchor — `ab` constrains B to be within N minutes after A, and `bc` constrains C to be within N minutes after B. If the customer's definition is "the entire funnel completes within N minutes", anchor both to a: `AND b.event_time <= date_add('minute', N, a.event_time)` / `AND c.event_time <= date_add('minute', N, a.event_time)`; confirm the definition with the customer before filling.)

---

## Template 7: Funnel (Loose Order, Completed Within the Same Day)

**Scenario**: completed both A and B, order not required

**Business filtering not yet supported**: the template has no `{{filters}}` insertion point and cannot filter step events by property; when filtering is needed, use Template 11 custom SQL instead.

### Single-Timezone Version

```sql
WITH user_events AS (
  SELECT DISTINCT
    "#user_id" AS user_id,
    "$part_event" AS event_name
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" IN ('{{step1}}', '{{step2}}', '{{step3}}')
    AND "$part_date" = '{{date}}'
),
user_step_count AS (
  SELECT
    user_id,
    MAX(CASE WHEN event_name = '{{step1}}' THEN 1 ELSE 0 END) AS has_step1,
    MAX(CASE WHEN event_name = '{{step2}}' THEN 1 ELSE 0 END) AS has_step2,
    MAX(CASE WHEN event_name = '{{step3}}' THEN 1 ELSE 0 END) AS has_step3
  FROM user_events
  GROUP BY user_id
)
SELECT
  SUM(has_step1) AS step1_users,
  SUM(has_step1 * has_step2) AS completed_1_2,
  SUM(has_step1 * has_step2 * has_step3) AS completed_all,
  CAST(SUM(has_step1 * has_step2 * has_step3) AS DOUBLE) / NULLIF(SUM(has_step1), 0) AS metric_value
FROM user_step_count
LIMIT 1
```

### Multi-Timezone Version

```sql
WITH user_events AS (
  SELECT DISTINCT
    "#user_id" AS user_id,
    "$part_event" AS event_name,
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" IN ('{{step1}}', '{{step2}}', '{{step3}}')
    AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
),
filtered_events AS (
  SELECT user_id, event_name FROM user_events
  WHERE date(shifted_time) = date('{{date}}')
),
user_step_count AS (
  SELECT
    user_id,
    MAX(CASE WHEN event_name = '{{step1}}' THEN 1 ELSE 0 END) AS has_step1,
    MAX(CASE WHEN event_name = '{{step2}}' THEN 1 ELSE 0 END) AS has_step2,
    MAX(CASE WHEN event_name = '{{step3}}' THEN 1 ELSE 0 END) AS has_step3
  FROM filtered_events
  GROUP BY user_id
)
SELECT
  SUM(has_step1) AS step1_users,
  SUM(has_step1 * has_step2) AS completed_1_2,
  SUM(has_step1 * has_step2 * has_step3) AS completed_all,
  CAST(SUM(has_step1 * has_step2 * has_step3) AS DOUBLE) / NULLIF(SUM(has_step1), 0) AS metric_value
FROM user_step_count
LIMIT 1
```

---

## Template 8: N-Day Retention (Same-Day Basis)

**Scenario**: next-day retention rate = proportion of new users from the day before yesterday who returned yesterday (`{{base_date}}` = target date - N days, return date = target date)

**Selection basis**: use this template only when the customer's definition is "return **on day N itself**" — the return date must fall exactly on `base_date + N`. If the customer says "return within N days / on any day", use Template 9. **The two definitions differ significantly** (return on day 7 itself 6.5% vs return on any day within 7 days is higher); when configuring retention-type requirements, confirm the definition with the customer first — do not default to either one.

**Business filtering not yet supported**: the template has no `{{filters}}` insertion point and cannot filter new-user or return events by property; when filtering is needed, use Template 11 custom SQL instead.

### Single-Timezone Version

```sql
WITH new_users AS (
  SELECT DISTINCT "#user_id" AS user_id
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{new_user_event}}'
    AND "$part_date" = '{{base_date}}'
),
return_users AS (
  SELECT DISTINCT "#user_id" AS user_id
  FROM ta.v_event_{{project_id}}
  WHERE "$part_date" = date_format(date('{{base_date}}') + INTERVAL '{{retention_days}}' DAY, '%Y-%m-%d')
    AND "#user_id" IN (SELECT user_id FROM new_users)
    {{return_event_filter}}
)
SELECT
  (SELECT COUNT(*) FROM new_users) AS new_user_count,
  (SELECT COUNT(*) FROM return_users) AS return_user_count,
  CAST((SELECT COUNT(*) FROM return_users) AS DOUBLE) / NULLIF((SELECT COUNT(*) FROM new_users), 0) AS metric_value
LIMIT 1
```

### Multi-Timezone Version

```sql
WITH new_users AS (
  SELECT DISTINCT "#user_id" AS user_id
  FROM (
    SELECT
      "#user_id",
      IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
    FROM ta.v_event_{{project_id}}
    WHERE "$part_event" = '{{new_user_event}}'
      AND "$part_date" BETWEEN date_format(date('{{base_date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{base_date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
  ) t
  WHERE date(shifted_time) = date('{{base_date}}')
),
return_users AS (
  SELECT DISTINCT "#user_id" AS user_id
  FROM (
    SELECT
      "#user_id",
      IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
    FROM ta.v_event_{{project_id}}
    WHERE "$part_date" BETWEEN date_format(date('{{base_date}}') + INTERVAL '{{retention_days-1}}' DAY, '%Y-%m-%d') AND date_format(date('{{base_date}}') + INTERVAL '{{retention_days+1}}' DAY, '%Y-%m-%d')
      AND "#user_id" IN (SELECT user_id FROM new_users)
      {{return_event_filter}}
  ) t
  WHERE date(shifted_time) = date('{{base_date}}') + INTERVAL '{{retention_days}}' DAY
)
SELECT
  (SELECT COUNT(*) FROM new_users) AS new_user_count,
  (SELECT COUNT(*) FROM return_users) AS return_user_count,
  CAST((SELECT COUNT(*) FROM return_users) AS DOUBLE) / NULLIF((SELECT COUNT(*) FROM new_users), 0) AS metric_value
LIMIT 1
```

---

## Template 9: N-Day Retention (Cross-Day Basis)

**Scenario**: 7-day retention = return on any day within 7 days after registration (`{{base_date}}` = target date - N days)

**Selection basis**: use this template when the customer's definition is "return on **any day** within N days" (BETWEEN base+1 ~ base+N) — the common default for retention semantics. If the customer explicitly says "return on day N itself", use Template 8. When in doubt, ask first; the two definitions produce significantly different results.

**Business filtering not yet supported**: the template has no `{{filters}}` insertion point and cannot filter new-user or return events by property; when filtering is needed, use Template 11 custom SQL instead.

**`retention_days` conversion example** (mental cross-check at config phase to prevent off-by-one): when retention_days=7 (7-day retention), write `7` for `{{retention_days}}` and `6` for `{{retention_days-1}}` in Template 8; write `7` for the BETWEEN right end `{{retention_days}}` in Template 9, and `8` for `{{retention_days+1}}` in the multi-timezone version. After writing, self-check whether "base_date + N equals the target date" (Template 8) and "whether the right end = base_date + N" (Template 9); if they do not match, the conversion is wrong.

### Single-Timezone Version

```sql
WITH new_users AS (
  SELECT DISTINCT "#user_id" AS user_id
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{new_user_event}}'
    AND "$part_date" = '{{base_date}}'
),
return_users AS (
  SELECT DISTINCT "#user_id" AS user_id
  FROM ta.v_event_{{project_id}}
  WHERE "$part_date" BETWEEN date_format(date('{{base_date}}') + INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{base_date}}') + INTERVAL '{{retention_days}}' DAY, '%Y-%m-%d')
    AND "#user_id" IN (SELECT user_id FROM new_users)
    {{return_event_filter}}
)
SELECT
  (SELECT COUNT(*) FROM new_users) AS new_user_count,
  (SELECT COUNT(*) FROM return_users) AS return_user_count,
  CAST((SELECT COUNT(*) FROM return_users) AS DOUBLE) / NULLIF((SELECT COUNT(*) FROM new_users), 0) AS metric_value
LIMIT 1
```

### Multi-Timezone Version

```sql
WITH new_users AS (
  SELECT DISTINCT "#user_id" AS user_id
  FROM (
    SELECT
      "#user_id",
      IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
    FROM ta.v_event_{{project_id}}
    WHERE "$part_event" = '{{new_user_event}}'
      AND "$part_date" BETWEEN date_format(date('{{base_date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{base_date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
  ) t
  WHERE date(shifted_time) = date('{{base_date}}')
),
return_users AS (
  SELECT DISTINCT "#user_id" AS user_id
  FROM (
    SELECT
      "#user_id",
      IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
    FROM ta.v_event_{{project_id}}
    WHERE "$part_date" BETWEEN date_format(date('{{base_date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{base_date}}') + INTERVAL '{{retention_days+1}}' DAY, '%Y-%m-%d')
      AND "#user_id" IN (SELECT user_id FROM new_users)
      {{return_event_filter}}
  ) t
  WHERE date(shifted_time) BETWEEN date('{{base_date}}') + INTERVAL '1' DAY AND date('{{base_date}}') + INTERVAL '{{retention_days}}' DAY
)
SELECT
  (SELECT COUNT(*) FROM new_users) AS new_user_count,
  (SELECT COUNT(*) FROM return_users) AS return_user_count,
  CAST((SELECT COUNT(*) FROM return_users) AS DOUBLE) / NULLIF((SELECT COUNT(*) FROM new_users), 0) AS metric_value
LIMIT 1
```

---

## Template 10: Group Monitoring

**Scenario**: monitor DAU per channel separately, judge group by group (each group is compared against its own baseline; data from other groups is not mixed in)

**Notes**:
- Do not add `ORDER BY metric_value DESC` — sort-then-truncate would squeeze out small-value groups via LIMIT, while the script must judge every returned group individually. `{{group_limit}}` is only a safety cap (recommended 1000, consistent with the script's `PREVIEW_ROWS`)
- The main query and the baseline query use the same SQL: the script only renders time placeholders into shifted windows; the baseline query likewise returns `group_key, metric_value` for all groups, and the script takes each group's own baseline value from the results — do not write any single-group filter conditions in sql_template
- `{{total_groups}}` comes from the number of rows returned by the main query, subject to truncation by `{{group_limit}}` (script cap `PREVIEW_ROWS` = 1000): when the group count exceeds the cap, it only reflects returned row count, not the true total number of groups. Probe the group count before configuring (`SELECT COUNT(DISTINCT ...)`): confirm with the user if > 800, reject if > 1000 (see rule-schema "type = group")
- Result column names are fixed as `group_key` and `metric_value`

### Single-Timezone Version

```sql
SELECT
  "{{group_dimension}}" AS group_key,
  {{aggregate_expr}} AS metric_value
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" = '{{date}}'
  {{time_filter}}
  {{filters}}
GROUP BY "{{group_dimension}}"
LIMIT {{group_limit}}
```

### Multi-Timezone Version

```sql
SELECT
  "{{group_dimension}}" AS group_key,
  {{aggregate_expr}} AS metric_value
FROM (
  SELECT
    "{{group_dimension}}",
    "{{metric_prop}}",
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
    {{filters}}
) t
WHERE date(shifted_time) = date('{{date}}')
  {{time_filter_shifted}}
GROUP BY "{{group_dimension}}"
LIMIT {{group_limit}}
```

---

## Template 11: Custom SQL

**Scenario**: user-provided SQL or LLM-written SQL

**Constraints**:
- Single-value monitoring returns a single numeric column (recommended column name `metric_value`; other column names require `metric.result_column` to specify); group monitoring returns two columns `group_key, metric_value`
- Must include `$part_date` filtering (`$part_date` is varchar; only compare with `'YYYY-MM-DD'` strings, do not connect directly with `date()`/`INTERVAL` expressions)
- Must include `LIMIT`
- Multi-timezone projects must use a subquery for timezone shifting

**Examples**:

```sql
-- Single timezone
SELECT COUNT(DISTINCT "#user_id") AS metric_value
FROM ta.v_event_{{project_id}}
WHERE "$part_event" = '{{event_name}}'
  AND "$part_date" = '{{date}}'
LIMIT 1

-- Multi timezone
SELECT COUNT(DISTINCT "#user_id") AS metric_value
FROM (
  SELECT
    "#user_id",
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" = '{{event_name}}'
    AND "$part_date" BETWEEN date_format(date('{{date}}') - INTERVAL '1' DAY, '%Y-%m-%d') AND date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
) t
WHERE date(shifted_time) = date('{{date}}')
LIMIT 1
```

---

## Template 12: List Filtering (Abnormal Users / Order Details)

**Scenario**: High Spender users inactive in the last N days, abnormal orders exceeding an amount threshold — the SQL returns row-level details and the script judges alerting by row count

**Constraints**:
- Returns row-level data, one user / order per row; column names are the `result_columns` (displayed by column name when pushing the list)
- For lists output on a user basis, `result_columns` must include dual IDs (`user_id` + `account_id`); when monitoring other entities such as devices/orders, use the entity ID as the primary column — see "List ID Rules" at the end
- Must include `$part_date` filtering and `LIMIT` (cap 1000, consistent with the script's `PREVIEW_ROWS`)
- Window determination logic is expressed by the SQL itself (`HAVING` / `WHERE`); the script only counts rows

**High Spender definition confirmation** (must ask at config phase; do not copy example values verbatim):

| Business Input | Description |
|---------|------|
| Determination method | Choose one of two: **payment event calculation method** (this template, SUM of payment event amounts > threshold, lookback window selectable) or **user property method** (Template 12b, direct WHERE user property > threshold, suitable for projects with properties like VIP level / cumulative payment amount) |
| `{{big_r_threshold}}` | High Spender threshold (amount), given by the business |
| `{{lookback_days}}` | Payment lookback window days, given by the business (e.g. 30/90) |
| `{{amount_prop}}` | Payment event amount field name, varies by project; confirm from event property metadata |
| `{{active_event}}` | Activity determination event (which event determines "inactive", e.g. `login` / `game_start` — when the customer says "has not logged in to play", use the real login event, not literally `login`) |
| `{{pay_event}}` | Payment event name |
| `{{inactive_days_minus_1}}` | N-1 of "inactive in the last N days" (e.g. fill `6` for inactive in last 7 days) |

**Churn determination semantics**: `MAX(CASE WHEN ... THEN ... END)` only applies to `{{active_event}}` — it determines "no active event occurred in the last N days"; payment behavior does not lift the churn determination (users who paid but did not log in remain on the list). If the customer's definition is "neither logged in nor paid" (any activity excludes), replace `{{active_event}}` with a list of activity events (`"$part_event" IN (...)` combined with CASE WHEN judging the IN list).

**Inherent limitation**: users with no active events at all within the lookback window produce no rows (users whose MAX is NULL only appear when they have payment event rows) — pure churned users (neither active nor paying) inherently cannot be found. The `IS NULL` branch also treats "never had an active event within the window" as inactive — if the active event's collection pipeline fails on a given day (data entirely missing), all paying users would be misjudged as inactive and the list would explode. Before running this template, probe the current day's active event row count once (`SELECT COUNT(*) ... WHERE "$part_event" = '{{active_event}}' AND "$part_date" = ...`); if it is 0, abort configuration and confirm the data pipeline with the user — do not deliver the list directly. The list scope is constrained by `{{lookback_days}}`; historical behavior beyond the lookback window is invisible; when longer tracing is needed, enlarge the lookback window (at the cost of scan volume).

**Definition confirmation table** (must ask at config phase, including Template 12's payment definition):

| Business Input | Must-Ask Content |
|---------|---------|
| `{{pay_event}}` / `{{active_event}}` | Whether event names match the customer's definition (customer saying "payment" is not necessarily payment, saying "active" is not necessarily login) |
| Whether payment lifts churn | Does payment behavior count as "active"? If yes → the activity event list must include the payment event; if no → use this template's default definition |

**User tag/cluster determination**: directly querying tags via SQL is not verified as supported. When the customer's definition depends on tags/clusters, prefer guiding them to express it with equivalent user properties (Template 12b), or use the platform's cluster feature to select users by cluster.

**Mixed scenario of High Spender determination via property + churn determination via event**: the High Spender condition uses Template 12b's property table (`ta.v_user_{{project_id}}`); the inactivity determination still needs to go back to the event table for MAX (the user table has no last_active_time-type fields); the two tables are joined on `#user_id`.

**How to write `{{result_columns}}`** (aligned with `metric.result_columns`): the two versions must correspond one-to-one — the single-timezone version uses original column names, the multi-timezone version uses subquery alias columns.

| Scenario | result_columns |
|------|---------------|
| Single-timezone version | Use original columns + aggregation directly, e.g. `"#user_id" AS user_id, MAX("#account_id") AS account_id, MAX(CASE WHEN "$part_event" = '{{active_event}}' THEN "#event_time" END) AS last_active_time, SUM(CASE WHEN "$part_event" = '{{pay_event}}' THEN CAST("{{amount_prop}}" AS DOUBLE) ELSE 0 END) AS total_payment` |
| Multi-timezone version | Use subquery alias columns, e.g. `user_id, MAX(account_id) AS account_id, MAX(CASE WHEN event_name = '{{active_event}}' THEN shifted_time END) AS last_active_time, SUM(CASE WHEN event_name = '{{pay_event}}' THEN CAST(amount_prop AS DOUBLE) ELSE 0 END) AS total_payment` |

### Single-Timezone Version (example: High Spender users inactive in the last 7 days)

```sql
SELECT
  {{result_columns}}
FROM ta.v_event_{{project_id}}
WHERE "$part_event" IN ('{{active_event}}', '{{pay_event}}')
  AND "$part_date" >= date_format(date('{{date}}') - INTERVAL '{{lookback_days}}' DAY, '%Y-%m-%d')
  AND "$part_date" <= '{{date}}'
GROUP BY "#user_id"
HAVING (MAX(CASE WHEN "$part_event" = '{{active_event}}' THEN "#event_time" END) IS NULL
        OR MAX(CASE WHEN "$part_event" = '{{active_event}}' THEN "#event_time" END) < TIMESTAMP '{{date}} 00:00:00' - INTERVAL '{{inactive_days_minus_1}}' DAY)
  AND SUM(CASE WHEN "$part_event" = '{{pay_event}}' THEN CAST("{{amount_prop}}" AS DOUBLE) ELSE 0 END) > {{big_r_threshold}}
LIMIT 1000
```

`"$part_date" <= '{{date}}'` is the right-end upper bound of the lookback window (`{{date}}` is the window attribution date, which naturally excludes data after the window date) — without it, partition data later than the attribution date would leak into the SUM, and the same rule triggered at different times would yield different lists.

### Multi-Timezone Version

```sql
SELECT
  {{result_columns}}
FROM (
  SELECT
    "#user_id" AS user_id,
    "#account_id" AS account_id,
    "{{amount_prop}}" AS amount_prop,
    "$part_event" AS event_name,
    IF((("{{tz_column}}" IS NOT NULL) AND ("{{tz_column}}" >= -30) AND ("{{tz_column}}" <= 30)), date_add('second', CAST(({{settle_tz}} - "{{tz_column}}") * 3600 AS integer), "#event_time"), "#event_time") AS shifted_time
  FROM ta.v_event_{{project_id}}
  WHERE "$part_event" IN ('{{active_event}}', '{{pay_event}}')
    AND "$part_date" >= date_format(date('{{date}}') - INTERVAL '{{lookback_days}}' DAY, '%Y-%m-%d')
    AND "$part_date" <= date_format(date('{{date}}') + INTERVAL '1' DAY, '%Y-%m-%d')
) t
GROUP BY user_id
HAVING (MAX(CASE WHEN event_name = '{{active_event}}' THEN shifted_time END) IS NULL
        OR MAX(CASE WHEN event_name = '{{active_event}}' THEN shifted_time END) < TIMESTAMP '{{date}} 00:00:00' - INTERVAL '{{inactive_days_minus_1}}' DAY)
  AND SUM(CASE WHEN event_name = '{{pay_event}}' THEN CAST(amount_prop AS DOUBLE) ELSE 0 END) > {{big_r_threshold}}
  AND MAX(shifted_time) < TIMESTAMP '{{date}} 00:00:00' + INTERVAL '1' DAY
LIMIT 1000
```

The multi-timezone version has two layers of right ends: the inner `$part_date` takes a widened upper bound (+1 day, consistent with the widening principle of the common structure), and the outer `MAX(shifted_time) < 00:00:00 of the day after the window attribution date` is the precise right end (it blocks the extra 1 day of data).

## Template 12b: List Filtering - User Property Method (High Spender Determined by User Property)

**Scenario**: High Spender determination is based on user properties (VIP level, cumulative payment amount, etc.) rather than event calculation. Discover properties via `ae-cli analysis-meta property list -p <pid> --table-type user` and confirm with the user.

```sql
SELECT
  {{result_columns}}
FROM ta.v_user_{{project_id}}
WHERE "{{big_r_prop}}" > {{big_r_threshold}}
LIMIT 1000
```

**Constraints**:
- `{{big_r_prop}}`: user property name (e.g. `total_pay_amount`, with double quotes in SQL), filled in after confirmation with the user
- The property table has no `$part_date` partition — no date filtering needed; it contains no event timezones — multi-timezone projects involve no shifting either; the syntax is identical for single/multi-timezone projects (the script exempts SQL that only queries the user table and contains no event table from `$part_date` validation)
- The dual-ID rule for user lists is the same as Template 12; `{{result_columns}}` e.g. `"#user_id" AS user_id, "#account_id" AS account_id, "{{big_r_prop}}" AS big_r_value`
- Property values are "as of now" snapshots (e.g. cumulative payment), with no lookback window concept; when a windowed definition like "paid X in the past N days" is needed, use Template 12's event method

**List ID Rules**:

- **Business definition** (which ID counts as "user", which IDs the list outputs, how entity lists are handled): see the "ID Definition" global rules at the top of [`rule-schema.md`](rule-schema.md)
- **Group by a single ID column only** (technical rule of this file): GROUP BY always uses a single computed ID column (default `#user_id` / subquery alias column); `account_id` serves only as an output column, extracted via `MAX(account_id) AS account_id` aggregation, and does not participate in GROUP BY. Reason: if some of a user's events report `#account_id` and some do not, grouping by both columns would split one person into a NULL row and a non-NULL row, duplicating the list and fragmenting aggregate values. The same `#user_id` never corresponds to multiple non-NULL `#account_id` values, so taking MAX yields the accurate value

---

## Aggregate Expression Quick Reference

| aggregate | SQL Expression |
|-----------|-----------|
| `SUM` | `COALESCE(SUM(CAST("{{metric_prop}}" AS DOUBLE)), 0)` |
| `COUNT` | `COUNT(*)` |
| `COUNT_DISTINCT` | `COUNT(DISTINCT "{{metric_prop}}")` |
| `AVG` | `COALESCE(AVG(CAST("{{metric_prop}}" AS DOUBLE)), 0)` |

**Empty-window semantics for SUM/AVG**: when there are zero events in the window (including data not yet ingested), `SUM`/`AVG` returns NULL; `COALESCE(..., 0)` uniformly treats empty windows as 0, so "below threshold" alerts still fire on zero-data days and are not silently swallowed. At config phase, confirm with the user whether a zero-data day is treated as 0 (default is yes); `COUNT`/`COUNT_DISTINCT` inherently returns 0 for empty windows and needs no COALESCE. If the user explicitly does not want zero treatment, remove `COALESCE(..., 0)` from `{{aggregate_expr}}` — in that case the metric is NULL on zero-data days, `lt`-type alerts do not fire that day, and this consequence must be communicated to the user at config phase. Note this semantics also applies to the baseline query (which shares the same SQL template as the main query): the average/maximum of `history_avg`/`history_max` counts empty-data days as 0.

**COUNT + multi-timezone**: the multi-timezone template's subquery SELECT contains `"{{metric_prop}}"`; when the aggregation is `COUNT` (expression `COUNT(*)`, which references no property column), the `"{{metric_prop}}"` in the subquery should be replaced with `"#user_id"` (or another existing column) — otherwise the subquery SELECTs a placeholder property column that nobody uses, and a misconfigured property name directly causes a query error.

---

## Time Filter Placeholders

At config phase, use this table to replace `{{time_filter}}` in Templates 3/5/10 with concrete content:

| Window Type | Replace `{{time_filter}}` with |
|----------|------------------------|
| natural_hour | `AND "#event_time" >= TIMESTAMP '{{window_start}}' AND "#event_time" < TIMESTAMP '{{window_end}}'` |
| natural_day | (leave empty) |
| today_to_now | `AND "#event_time" >= TIMESTAMP '{{window_start}}' AND "#event_time" < TIMESTAMP '{{window_end}}'` |
| natural_week | Not supported (Templates 3/5/10 paired with natural_week are rejected outright by the script; for natural week monitoring use Template 4 or Template 11) |

**`{{time_filter_shifted}}`**: same as above, with `#event_time` replaced by `shifted_time`.

Note: the replaced content still contains runtime placeholders such as `{{window_start}}` — this is normal; they are replaced a second time at runtime.

**Template adaptation constraint for natural_week windows**: when the window type is natural_week, the SQL template must contain the `{{week_start}}` / `{{week_end}}` placeholders (Template 4 is the only ready-made one; for other structures use Template 11 custom SQL with hand-written week placeholders). The script validates: natural_week window + template without week placeholders → direct error with a prompt to switch to Template 4 or 11, rather than silently computing with a wrong definition — Templates 1/2/3/5/10 all express time via `{{date}}`, and when paired with a natural_week window, `{{date}}` would be rendered as the Monday of the previous natural week (only 1 day of data), which is why the script forbids it. For custom SQL (Template 11) under a natural_week window, if both `{{week_start}}` and `{{date}}` are written, `{{date}}` renders as the Monday of the previous natural week — it is for informational display only; week filtering always uses `{{week_start}}`/`{{week_end}}`.
