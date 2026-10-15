# Execution steps and SQL templates

## 1. Confirm inputs

Resolve project id/name, host, absolute dates, event scope, user-confirmed expected threshold, user-confirmed server time-zone offset, and whether the user supplied an offset for null `#zone_offset` rows. Stop when the server offset or threshold is unknown; never invent either value.

Output: a fixed, user-visible analysis scope. Do not silently change the project, host, dates, event scope, threshold, or offsets later.

## 2. Authenticate and preflight

Confirm `ae-cli auth status`, then verify the project and required timestamp columns through the checker's probe. Stop and report the exact blocker if authentication, project resolution, or required-column checks fail.

Output: authenticated access and a compatible event table.

## 3. Apply partition and scan guards

`$part_date` is mandatory for every event-table query. `$part_event` is mandatory only for a specific-event query. All-events analysis intentionally omits `$part_event` and relies on the scan guard.

Run `check_ingestion_delay.py --dry-run` when reviewing generated SQL or estimating scope. Windows over 31 days or scans over the configured row budget require explicit authorization through `--allow-large-scan`.

Output: bounded SQL with an approved scan size.

## 4. Measure

Run `check_ingestion_delay.py` with `--output result.json`. The checker probes one partition, executes compact aggregation SQL, and atomically writes the canonical JSON. Exit code `0` means completed, `3` means inconclusive, and `2` means blocked or invalid. Stop on any nonzero exit.

Output: `result.json`.

## 5. Validate the measurement before rendering

```bash
python3 scripts/validate_output.py result.json
```

This independent gate checks schema versions, completion status, row and coverage bounds, segment samples, percentile presence, distributions, diagnosis, and warnings. Stop if it exits nonzero or returns `"ok": false`.

Output: a validated measurement result.

## 6. Render the deliverables

```bash
python3 scripts/render_charts.py result.json --out delay_charts.svg
python3 scripts/render_report.py result.json --out report.md --summary-out report-summary.json --chart-ref delay_charts.svg
```

Output: `delay_charts.svg`, `report.md`, and `report-summary.json`.

## 7. Validate rendered artifacts

```bash
python3 scripts/validate_output.py result.json \
  --report report.md \
  --summary report-summary.json \
  --chart delay_charts.svg
```

This gate verifies that the report belongs to the measured project, the chart is a nonempty SVG, and the summary contract and row count agree with the canonical result. Stop if validation fails.

Output: a delivery-ready artifact set.

## 8. Deliver

Present the chart plus a concise conclusion. State the affected segment, delayed share, one-hour-or-more share, key percentiles, time-zone coverage, assumed server offset, excluded rows, and limitations. Treat optional ranking failure as an attribution limitation, not a failed core measurement.

## SQL template

```sql
with raw as (
  select
    "$part_date" as d,
    "#event_time" as et,
    "#server_time" as st,
    "#zone_offset" as zo,
    "#dw_create_time" as dw
  from <server_authorized_event_table>
  where "$part_date" between '<start>' and '<end>'
  -- Specific event only:
  -- and "$part_event" in ('<event>')
), calc as (
  select *,
    case when <zone_gate> then date_diff('second', <event_in_server_zone>, st) end as upload_seconds,
    case when dw is not null then date_diff('second', st, dw) end as warehouse_seconds,
    case when dw is not null and <zone_gate>
      then date_diff('second', <event_in_server_zone>, dw) end as end_to_end_seconds
  from raw
)
select ...
from calc
group by grouping sets ((d), ());
```

Without a confirmed fallback, `<zone_gate>` is `zo is not null and zo between -12 and 14`. With a user-confirmed value, it is `coalesce(zo, <confirmed>) between -12 and 14`.

`<event_in_server_zone>` is `date_add('minute', cast((<server_offset> - <event_offset>) * 60 as bigint), et)`, where `<event_offset>` is `zo` or `coalesce(zo, <provided_missing_offset>)`.

Resolve the table first with `analysis sql-table list`, verify its columns with `analysis sql-table columns`, and preserve the returned `sql_reference`. Use `--use-cache false` and a unique `cli_<32 lowercase hex>` request ID with `ae-cli analysis adhoc run --model-type sql --definition '{"sql":"..."}'`. Prefer the bundled checker, which handles compact aggregation, scan limits, and atomic JSON output. Synchronous requests cannot be cancelled by request ID; cancel only asynchronous work with its returned `run_id`.
