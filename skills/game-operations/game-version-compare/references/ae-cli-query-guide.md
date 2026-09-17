# ae-cli Query Guide (with real-world pitfalls)

Standard commands and verified correct schemas for Step 6 execution. **The commands here have been confirmed working after real-world debugging; do not rewrite key fields from memory.**

## Command Entry Point (important: use the right entry)

The correct query entry is **`ae-cli analysis adhoc run`**, not `capability run analysis.adhoc.run`:

```bash
ae-cli analysis adhoc run -p <PID> --model-type <event|retention|funnel|sql|...> --definition '<JSON>'
```

Other common entry points:
- `ae-cli analysis report list -p <PID>` / `dashboard list`: search for existing reports (check this first before querying)
- `ae-cli analysis report get -p <PID> --report-id <RID>`: verify a report's approach
- `ae-cli analysis report-data run`: directly read data from an existing report
- `ae-cli analysis-meta event list --project-id <PID>`: inspect event metadata when exact event bindings must be confirmed
- `ae-cli analysis-meta property list --project-id <PID> --scope <event|user>`: inspect property metadata
- `ae-cli analysis filter-value list --project-id <PID> --property-name <FIELD> --table-type <event|user>`: retrieve exact version values; add `--event-name <EVENT>` for an event property

## event model definition (verified)

**Time range uses `custom` mode + `start_time`/`end_time`; the field names are `start_time`/`end_time` (not start_date, and not start under custom mode)**:

```json
{
  "metrics": [
    {"event": "login", "aggregation": "user_count"},
    {"event": "login", "aggregation": "total_count"}
  ],
  "time_range": {"mode": "custom", "start_time": "2026-07-08", "end_time": "2026-07-14"},
  "time_particle_size": "total",
  "comparison_time_ranges": [{"mode": "custom", "start_time": "2026-07-01", "end_time": "2026-07-07"}]
}
```

**Key pitfalls**:
- Use `total_count` for the total event count, **not `event_count`** (the latter reports an unknown field)
- `comparison_time_ranges` returns the before/after two-window comparison in one call; no need to run twice
- In time-comparison results, "original time" is the primary window and "comparison time 1" is the comparison window
- Pass `--preview-rows 100`; if the response says `has_more=true`, export the full result rather than treating the preview as complete

## Version-cohort Comparison

After the user confirms the target and baseline values, run the same event definition twice over the same post-launch range. Add only one version filter per query:

```json
{"field":{"name":"<version field>","type":"<event_property|user_property>"},"operator":"eq","values":["<confirmed target value>"]}
```

Use the confirmed baseline value(s) in the second query. Keep metrics, groups, time range, timezone, and all other filters identical. Do not use `neq target` as the baseline because it can include missing and malformed values; quantify those separately.

**groups structure** (drill down by dimension):
```json
"groups": [{"field": {"name": "channel", "type": "event_property"}}]
```

## Common Aggregation Reference

| What to compute | aggregation |
|---------|------------|
| Distinct user count (DAU, etc.) | `user_count` |
| Total event count | `total_count` |
| Property sum (duration / amount) | `sum` + `property` |
| Per-user | `per_user_count` / `avg_per_user` |

## Pitfall: Property Attached to the Wrong Event

The `sum` aggregation must specify the property attached to the correct event. For example, "online duration" may be attached to the `logout` event rather than `login`; attaching it wrong yields `No property matched the input`. **Probe which event the property is on first**.

## SQL Model (fallback for complex queries)

```bash
ae-cli analysis adhoc run -p <PID> --model-type sql --definition '{"sql": "..."}'
```

**Verified key syntax** (Trino):
- Event table name looks like `hive.ta.v_event_<PID>` (use `ae-cli analysis sql-table list -p <PID>` to get the exact table name)
- System columns need double quotes: `"#user_id"` (bigint), `"#event_name"`, `"#event_time"`, `"$part_date"` (varchar, date partition)
- Querying the event table **must carry the `$part_date` partition predicate**, otherwise the backend rejects it
- Add days to a date: `date_add('day', 1, CAST(x AS date))` — three arguments (unit, amount, date), **not two**
- `$part_date` is varchar; to compare dates, use `CAST(... AS date)` or `CAST(date_add(...) AS varchar)` to align types

**Reference SQL for retention-difference calculation** is implemented in `scripts/retention_diff.py`. It compares registration cohorts by whether the target behavior occurred on registration day, then measures D1/DN retention; this prevents later behavior from being used to classify an earlier retention outcome. Its usage example uses the verified Project 7 table/events, while command-line options accept confirmed values for another project. Event and date values use typed SQL parameters, and the table reference is restricted to a safe identifier shape. For another project, discover its authorized table and exact events before running it.

Conceptual query shape:
```sql
WITH reg AS (
  SELECT "#user_id", min("$part_date") AS reg_date
  FROM <authorized_table_ref>
  WHERE ${PartDate:reg_window}
    AND "#event_name" ${Text:reg_event}
  GROUP BY "#user_id"
),
action_events AS (
  SELECT "#user_id", "$part_date" AS action_date
  FROM <authorized_table_ref>
  WHERE ${PartDate:action_window}
    AND "#event_name" ${Text:action_event}
),
ret AS (
  SELECT DISTINCT "#user_id", "$part_date" AS d
  FROM <authorized_table_ref>
  WHERE ${PartDate:return_window}
    AND "#event_name" ${Text:return_event}
)
-- Classify users only by actions on their registration date, then calculate
-- retained-user counts from aligned per-user D1/DN dates; divide by each group's total for rates.
```

## Safe Script Execution

Use argument arrays rather than a shell and typed SQL parameters for values. Check the subprocess exit code and parse the JSON response instead of scraping rows with regular expressions. The samples under `scripts/` follow these rules. The batch example intentionally retains the Project 7 event/property mapping; the retention example exposes the original project/event/table overrides.

Project 7 time-comparison example:

```bash
python scripts/batch_event_compare.py \
  --project-id 7 \
  --post-start 2026-07-09 --post-end 2026-07-15 \
  --pre-start 2026-07-01 --pre-end 2026-07-07
```

Project 7 add-friend retention example:

```bash
python scripts/retention_diff.py \
  --project-id 7 --table hive.ta.v_event_7 \
  --action-event add_friend --reg-event register --return-event login \
  --reg-start 2026-07-08 --reg-end 2026-07-14 --ret-window 7
```

For another project, confirm the event/property mappings and obtain the exact table from `analysis sql-table list`. The batch script still requires code adaptation when those mappings differ; the retention script can receive the confirmed values through its command-line options.

## Environment Issues

If `which ae-cli` finds nothing after an environment reset, report the missing dependency and ask the user before changing the global environment. After approval, use this recovery order:
1. `npm install -g @thinkingai/ae-cli`
2. `ae-cli config set-host <host>`
3. `ae-cli update` (auto-upgrades to the version required by the host + syncs the companion skills)
4. `ae-cli auth login` (device-code authorization)
