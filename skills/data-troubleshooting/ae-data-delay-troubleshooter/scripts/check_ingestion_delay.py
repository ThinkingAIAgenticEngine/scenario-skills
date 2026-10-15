#!/usr/bin/env python3
"""Read-only AE ingestion-delay checker (SQL path).

Queries event data through `ae-cli analysis adhoc run --model-type sql`
with a mandatory $part_date predicate and a $part_event predicate only for
event-scoped runs and aggregates per-date lag statistics in SQL
(approx_percentile):

- authentication and direct SQL execution are the only required capabilities
- a single-partition probe SQL tests data-query permission by execution,
  checks #dw_create_time resolvability, and estimates scan cost before the
  full-window measurement runs
- event time is normalized from #zone_offset to the server time zone before
  upload and end-to-end lag are calculated
- #server_time and #dw_create_time use a user-confirmed
  --server-zone-offset; the checker never guesses the deployment time zone
- rows without #zone_offset are excluded unless the user confirms their
  actual offset with --missing-zone-offset
- windows above 31 days or an estimated scan above the row budget stop with
  a blocked verdict unless --allow-large-scan is passed
- #server_time constancy detection (not a row-level receive time)
- the expected threshold is user-confirmed and configurable; positive
  durations above it determine delay wording, while >=1 hour is a separate
  long-delay observation line
- platform warehouse uses all rows with receive and warehouse timestamps;
  upload and end-to-end use rows covered by valid or user-confirmed time-zone metadata

Never uploads events or mutates project configuration.
Exit codes: 0 = measurement completed, 3 = inconclusive,
2 = blocked/invalid arguments.
"""

from __future__ import annotations

import argparse
from concurrent.futures import Future, ThreadPoolExecutor
import json
import math
import os
import shutil
import subprocess
import time
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from report_model import enrich_result

UPLOAD_SEGMENT = "event_to_receive"
WAREHOUSE_SEGMENT = "receive_to_warehouse"
END_TO_END_SEGMENT = "event_to_warehouse"
MIN_PRECISE_SAMPLES = 20
AE_CLI_NAME = "ae-cli"
MAX_WINDOW_DAYS = 31
# Rough scan-cost ceiling for the full-window measurement, estimated from the
# single-partition probe. Exceeding it requires --allow-large-scan.
SCAN_ROW_BUDGET = 500_000_000
PERMISSION_HINTS = (
    "permission",
    "denied",
    "not authorized",
    "unauthorized",
    "forbidden",
    "access denied",
    "insufficient privilege",
)
DEFAULT_EXPECTED_SECONDS = 300
OUTPUT_PATH: Path | None = None
HOST_COMPAT_NOTICES: list[str] = []
REQUIRED_EVENT_COLUMNS = {"$part_date", "$part_event", "#event_time", "#server_time", "#zone_offset"}

# Current 45-column measurement schema: min, p50, p95, max, negative,
# first positive bucket, sample count. Upload sample count is derived from
# timezone coverage instead of a dedicated SQL column.
SEGMENT_COLUMNS = {
    UPLOAD_SEGMENT: (7, 8, 9, 10, 11, 12, None),
    WAREHOUSE_SEGMENT: (19, 20, 21, 22, 23, 24, 31),
    END_TO_END_SEGMENT: (32, 33, 34, 35, 43, 36, 44),
}


class DiagnosticError(RuntimeError):
    pass


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    attach_host_compat_notice(payload)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if OUTPUT_PATH is not None:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{OUTPUT_PATH.name}.", suffix=".tmp", dir=OUTPUT_PATH.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, OUTPUT_PATH)
        except BaseException:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise
    else:
        print(rendered, end="")
    raise SystemExit(exit_code)


# ---------------------------------------------------------------- ae-cli I/O

AE_CLI_EXECUTABLE = AE_CLI_NAME


def resolve_ae_cli() -> str:
    """Resolve ae-cli from PATH, as required by the skill setup contract."""
    return shutil.which(AE_CLI_NAME) or ""


def ae_cli_command(command: list[str], host: str | None) -> list[str]:
    """Full argv for one ae-cli invocation; the executable is resolved once in main()."""
    full_command = [AE_CLI_EXECUTABLE, *command]
    if host:
        full_command += ["--host", host]
    return full_command + ["--format", "json"]


def string_leaves(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        values: list[str] = []
        for child in value.values():
            values.extend(string_leaves(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(string_leaves(child))
        return values
    return []


def record_host_compat_notice(payload: dict[str, Any], stderr: str) -> None:
    notice = payload.get("_notice")
    candidates = (
        string_leaves(notice.get("host_compat"))
        if isinstance(notice, dict) and notice.get("host_compat") is not None
        else []
    )
    stderr_lower = stderr.lower()
    markers = (
        "host_compat", "host compatibility", "cli version incompatible",
        "version compatibility", "版本不兼容", "版本兼容",
    )
    if any(marker in stderr_lower for marker in markers):
        candidates.extend(line.strip() for line in stderr.splitlines() if line.strip())
    for candidate in candidates:
        if candidate not in HOST_COMPAT_NOTICES:
            HOST_COMPAT_NOTICES.append(candidate)


def attach_host_compat_notice(payload: dict[str, Any]) -> None:
    if not HOST_COMPAT_NOTICES:
        return
    notice = payload.setdefault("_notice", {})
    if not isinstance(notice, dict):
        notice = {}
        payload["_notice"] = notice
    notice["host_compat"] = list(HOST_COMPAT_NOTICES)


def run_ae(command: list[str], host: str | None, timeout_seconds: int) -> dict[str, Any]:
    full_command = ae_cli_command(command, host)
    try:
        completed = subprocess.run(
            full_command, check=False, capture_output=True, text=True, timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired as exc:
        raise DiagnosticError(f"ae-cli process timed out after {timeout_seconds}s") from exc
    except FileNotFoundError as exc:
        raise DiagnosticError(f"could not execute ae-cli at {AE_CLI_EXECUTABLE}") from exc
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DiagnosticError(
            f"ae-cli did not return JSON (exit={completed.returncode}, stderr={completed.stderr.strip()[:500]!r})"
        ) from exc
    record_host_compat_notice(payload, completed.stderr)
    if completed.returncode != 0 or payload.get("ok") is False:
        raise DiagnosticError(json.dumps(payload, ensure_ascii=False)[:2000])
    return payload


def find_value(node: Any, key: str) -> Any | None:
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = find_value(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = find_value(value, key)
            if found is not None:
                return found
    return None


def page_items(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool, int]:
    items = find_value(payload, "items")
    if not isinstance(items, list):
        raise DiagnosticError("AE response did not contain an items list")
    has_more = find_value(payload, "has_more")
    if has_more is None:
        has_more = find_value(payload, "hasMore")
    next_offset = find_value(payload, "next_offset")
    if next_offset is None:
        next_offset = find_value(payload, "nextOffset")
    return items, bool(has_more), int(next_offset or 0)


def table_columns(
    project_id: int,
    table_ref: str,
    host: str | None,
    timeout: int,
) -> tuple[str, set[str]]:
    payload = run_ae(
        [
            "analysis", "sql-table", "columns",
            "--project-id", str(project_id),
            "--table-ref", table_ref,
            "--usage", "analysis",
        ],
        host,
        timeout,
    )
    columns = find_value(payload, "columns")
    if not isinstance(columns, list):
        raise DiagnosticError(f"SQL table {table_ref!r} did not return a columns list")
    sql_reference = find_value(payload, "sql_reference")
    if not isinstance(sql_reference, str) or not sql_reference:
        raise DiagnosticError(f"SQL table {table_ref!r} did not return a normalized sql_reference")
    names: set[str] = set()
    for column in columns:
        if isinstance(column, str):
            names.add(column)
        elif isinstance(column, dict):
            name = column.get("column_name") or column.get("name") or column.get("field_name")
            if isinstance(name, str):
                names.add(name)
    return sql_reference, names


def discover_event_table(
    project_id: int,
    requested_ref: str | None,
    host: str | None,
    timeout: int,
) -> tuple[str, set[str]]:
    if requested_ref:
        resolved_ref, columns = table_columns(project_id, requested_ref, host, timeout)
        missing = sorted(REQUIRED_EVENT_COLUMNS - columns)
        if missing:
            raise DiagnosticError(
                f"authorized SQL table {requested_ref!r} is missing required columns: {', '.join(missing)}"
            )
        return resolved_ref, columns

    offset = 0
    candidates: list[dict[str, Any]] = []
    while True:
        payload = run_ae(
            [
                "analysis", "sql-table", "list",
                "--project-id", str(project_id),
                "--limit", "200",
                "--offset", str(offset),
                "--usage", "analysis",
            ],
            host,
            timeout,
        )
        items, has_more, next_offset = page_items(payload)
        candidates.extend(items)
        if not has_more:
            break
        offset = next_offset

    matches: dict[str, set[str]] = {}
    for candidate in candidates:
        table_ref = candidate.get("sql_reference") or candidate.get("table_ref")
        if not isinstance(table_ref, str) or not table_ref:
            continue
        table_type = str(candidate.get("table_type") or "").lower()
        table_name = str(candidate.get("table") or "").lower()
        if "event" not in table_type and not table_name.startswith("v_event_"):
            continue
        try:
            resolved_ref, columns = table_columns(project_id, table_ref, host, timeout)
        except DiagnosticError:
            continue
        if REQUIRED_EVENT_COLUMNS <= columns:
            matches[resolved_ref] = columns
    if not matches:
        raise DiagnosticError(
            "no server-authorized analysis table contains the required event fields; "
            "inspect `analysis sql-table list/columns` or pass an exact authorized --table-ref"
        )
    if len(matches) > 1:
        refs = ", ".join(list(matches)[:5])
        raise DiagnosticError(
            f"multiple authorized event tables match ({refs}); rerun with the intended --table-ref"
        )
    return next(iter(matches.items()))


# ------------------------------------------------------------- SQL building


def build_main_sql(
    table_ref: str,
    event_name: str | None,
    start_date: str,
    end_date: str,
    include_dw: bool,
    expected_seconds: int,
    server_zone_offset: float,
    missing_zone_offset: float | None = None,
) -> str:
    """Main measurement SQL.

    The per-date rows and OVERALL row use GROUPING SETS so the event table is
    aggregated once. Event time is shifted from its row-level #zone_offset to
    the server time zone before upload and end-to-end subtraction. Missing
    event offsets remain excluded unless the caller supplies their actual value.
    """
    event_filter = f'where "$part_event" in (\'{event_name}\')\n    and ' if event_name else "where "
    dw_select = ', "#dw_create_time" as "dw"' if include_dw else ""
    offset_expr = f'coalesce("zo", {missing_zone_offset:g})' if missing_zone_offset is not None else '"zo"'
    zo_gate = f'{offset_expr} is not null and {offset_expr} >= -12 and {offset_expr} <= 14'
    event_in_server_zone = (
        f'date_add(\'minute\', cast(({server_zone_offset:g} - {offset_expr}) * 60 as bigint), "et")'
    )
    diff_expr = (
        f'case when {zo_gate} then date_diff(\'second\', {event_in_server_zone}, "st") end as "diff"'
    )
    dw_calc = ""
    if include_dw:
        e2e_cond = f'"dw" is not null and {zo_gate}'
        dw_calc = (
            ', case when "dw" is not null then date_diff(\'second\', "st", "dw") end as "wh"'
            f', case when {e2e_cond} then date_diff(\'second\', {event_in_server_zone}, "dw") end as "e2e"'
        )
    dw_stats = ""
    if include_dw:
        dw_stats = (
            f', min("wh") as "wh_min"'
            f', approx_percentile("wh", 0.5) as "wh_p50"'
            f', approx_percentile("wh", 0.95) as "wh_p95"'
            f', max("wh") as "wh_max"'
            f', count_if("wh" < 0) as "wh_neg"'
            f', count_if("wh" >= 0 and "wh" <= {expected_seconds}) as "wh_b1"'
            f', count_if("wh" > {expected_seconds} and "wh" < 600) as "wh_b2"'
            f', count_if("wh" >= 600 and "wh" < 1800) as "wh_b3"'
            f', count_if("wh" >= 1800 and "wh" < 3600) as "wh_b4"'
            f', count_if("wh" >= 3600 and "wh" < 10800) as "wh_b5"'
            f', count_if("wh" >= 10800 and "wh" < 86400) as "wh_b6"'
            f', count_if("wh" >= 86400) as "wh_b7"'
            f', count_if("wh" is not null) as "wh_n"'
            f', min("e2e") as "e2e_min"'
            f', approx_percentile("e2e", 0.5) as "e2e_p50"'
            f', approx_percentile("e2e", 0.95) as "e2e_p95"'
            f', max("e2e") as "e2e_max"'
            f', count_if("e2e" >= 0 and "e2e" <= {expected_seconds}) as "e2e_b1"'
            f', count_if("e2e" > {expected_seconds} and "e2e" < 600) as "e2e_b2"'
            f', count_if("e2e" >= 600 and "e2e" < 1800) as "e2e_b3"'
            f', count_if("e2e" >= 1800 and "e2e" < 3600) as "e2e_b4"'
            f', count_if("e2e" >= 3600 and "e2e" < 10800) as "e2e_b5"'
            f', count_if("e2e" >= 10800 and "e2e" < 86400) as "e2e_b6"'
            f', count_if("e2e" >= 86400) as "e2e_b7"'
            f', count_if("e2e" < 0) as "e2e_neg"'
            f', count_if("e2e" is not null) as "e2e_n"'
        )
    return f"""
with raw as (
  select "$part_date" as "d", "#event_time" as "et", "#server_time" as "st", "#zone_offset" as "zo"{dw_select}
  from {table_ref}
  {event_filter}"$part_date" between '{start_date}' and '{end_date}'
),
calc as (
  select "d", "et", "st", "zo",
    {diff_expr}{dw_calc}
  from raw
)
select
  case when grouping("d") = 1 then 'OVERALL' else cast("d" as varchar) end as "d",
  count(*) as "n",
  count_if("zo" is null) as "zo_missing",
  count_if("zo" is not null and ("zo" < -12 or "zo" > 14)) as "zo_invalid",
  approx_distinct("st") as "st_distinct",
  max("et") as "et_max",
  max("st") as "st_max",
  min("diff") as "up_min",
  approx_percentile("diff", 0.5) as "up_p50",
  approx_percentile("diff", 0.95) as "up_p95",
  max("diff") as "up_max",
  count_if("diff" < 0) as "up_neg",
  count_if("diff" >= 0 and "diff" <= {expected_seconds}) as "up_b1",
  count_if("diff" > {expected_seconds} and "diff" < 600) as "up_b2",
  count_if("diff" >= 600 and "diff" < 1800) as "up_b3",
  count_if("diff" >= 1800 and "diff" < 3600) as "up_b4",
  count_if("diff" >= 3600 and "diff" < 10800) as "up_b5",
  count_if("diff" >= 10800 and "diff" < 86400) as "up_b6",
  count_if("diff" >= 86400) as "up_b7"{dw_stats}
from calc
group by grouping sets (("d"), ())
limit 200
""".strip()


def build_probe_sql(
    table_ref: str,
    probe_date: str,
    include_dw: bool,
    event_name: str | None = None,
) -> str:
    """One-partition lightweight probe.

    Run before the full-window measurement. A single cheap query that
    simultaneously answers three questions: is the event table readable at
    all (data-query permission), is #dw_create_time resolvable on this
    deployment (warehouse capability), and roughly how large is one day of
    data (scan-cost estimate). Never scans more than one partition.
    """
    dw_col = ', count_if("#dw_create_time" is not null) as "dw_n"' if include_dw else ""
    event_filter = f' and "$part_event" in (\'{event_name}\')' if event_name else ""
    return f"""
select count(*) as "n"{dw_col}
from {table_ref}
where "$part_date" = '{probe_date}'{event_filter}
limit 1
""".strip()


def build_offset_sql(table_ref: str, event_name: str | None, start_date: str, end_date: str) -> str:
    event_filter = f'where "$part_event" in (\'{event_name}\')\n  and ' if event_name else "where "
    return f"""
select "$part_date" as "d", "#zone_offset" as "zo", count(*) as "c"
from {table_ref}
{event_filter}"$part_date" between '{start_date}' and '{end_date}'
group by "$part_date", "#zone_offset"
order by "d", "zo"
limit 500
""".strip()


def build_top_events_sql(
    table_ref: str,
    start_date: str,
    end_date: str,
    server_zone_offset: float,
    limit: int = 15,
    missing_zone_offset: float | None = None,
) -> str:
    offset_expr = f'coalesce("#zone_offset", {missing_zone_offset:g})' if missing_zone_offset is not None else '"#zone_offset"'
    zo_gate = f'{offset_expr} is not null and {offset_expr} >= -12 and {offset_expr} <= 14'
    event_in_server_zone = (
        f'date_add(\'minute\', cast(({server_zone_offset:g} - {offset_expr}) * 60 as bigint), "#event_time")'
    )
    return f"""
with event_source as (
  select
    "$part_event" as "e",
    coalesce(cast("#data_source" as varchar), '未记录') as "source",
    case when {zo_gate}
      then date_diff('second', {event_in_server_zone}, "#server_time") end as "up",
    case when "#dw_create_time" is not null
      then date_diff('second', "#server_time", "#dw_create_time") end as "wh",
    case when "#dw_create_time" is not null
      and {zo_gate}
      then date_diff('second', {event_in_server_zone}, "#dw_create_time") end as "e2e"
  from {table_ref}
  where "$part_date" between '{start_date}' and '{end_date}'
)
select
  "e", "source",
  count_if("up" is not null) as "up_n",
  count_if("up" >= 3600) as "up_ge_1h",
  count_if("wh" is not null) as "wh_n",
  count_if("wh" >= 3600) as "wh_ge_1h",
  count_if("e2e" is not null) as "e2e_n",
  approx_percentile("e2e", 0.5) as "e2e_p50",
  approx_percentile("e2e", 0.95) as "e2e_p95",
  count_if("e2e" >= 3600) as "e2e_ge_1h"
from event_source
group by "e", "source"
order by "e2e_ge_1h" desc, "e2e_p95" desc
limit {limit}
""".strip()


def sql_definition(sql: str) -> str:
    return json.dumps({"sql": sql}, ensure_ascii=False)


def run_sql_query(
    project_id: int,
    event_name: str | None,
    sql: str,
    host: str | None,
    timeout: int,
) -> list[list[Any]]:
    request_id = f"cli_{uuid.uuid4().hex}"
    try:
        payload = run_ae(
            [
                "analysis", "adhoc", "run",
                "--project-id", str(project_id),
                "--model-type", "sql",
                "--definition", sql_definition(sql),
                "--use-cache", "false",
                "--request-id", request_id,
                "--timeout-seconds", str(timeout),
            ],
            host, timeout + 15,
        )
    except DiagnosticError as exc:
        raise DiagnosticError(f"{exc} (request_id={request_id})") from exc
    if find_value(payload, "success") is False:
        raise DiagnosticError(
            json.dumps(
                {
                    "reason": find_value(payload, "message") or "AE query failed",
                    "errorCode": find_value(payload, "errorCode"),
                    "request_id": request_id,
                },
                ensure_ascii=False,
            )[:2000]
        )
    rows = extract_sql_rows(payload)
    if rows is None:
        raise DiagnosticError(f"unexpected response shape; no data.rows (request_id={request_id})")
    return rows


def extract_sql_rows(payload: Any) -> list[list[Any]] | None:
    """Find tabular rows in the current gateway envelope or a legacy saved fixture."""
    if isinstance(payload, dict):
        rows = payload.get("rows")
        if isinstance(rows, list) and (
            isinstance(payload.get("title"), list)
            or "returned_rows" in payload
            or "column_metadata" in payload
        ):
            return rows
        outer = payload.get("data")
        if isinstance(outer, dict):
            inner = outer.get("data")
            if isinstance(inner, dict) and isinstance(inner.get("rows"), list):
                return inner["rows"]
        for value in payload.values():
            found = extract_sql_rows(value)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = extract_sql_rows(value)
            if found is not None:
                return found
    return None


# -------------------------------------------------------------- aggregation


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def fmt(value: Any, decimals: int = 0) -> Any:
    number = to_float(value)
    if number is None:
        return None
    return round(number, decimals)


def segment_summary(values_with_n: dict[str, Any], decimals: int | None = None) -> dict[str, Any]:
    sample_count = int(to_float(values_with_n.get("n")) or 0)
    if sample_count < 1:
        return {"status": "unavailable", "sample_count": 0}
    decimals = (3 if sample_count >= MIN_PRECISE_SAMPLES else 0) if decimals is None else decimals
    bucket_total = 7 if "b7" in values_with_n else 6
    dist = {f"b{i}": int(to_float(values_with_n.get(f"b{i}")) or 0) for i in range(1, bucket_total + 1)}
    neg_raw = values_with_n.get("neg")
    neg = int(to_float(neg_raw) or 0) if neg_raw is not None else None
    out: dict[str, Any] = {
        "status": "measured",
        "sample_count": sample_count,
        "seconds": {
            "min": fmt(values_with_n.get("min"), decimals),
            "p50": fmt(values_with_n.get("p50"), decimals),
            "p95": fmt(values_with_n.get("p95"), decimals),
            "max": fmt(values_with_n.get("max"), decimals),
        },
        "distribution": dist,
    }
    if neg is not None:
        out["negative_count"] = neg
        out["distribution"]["negative"] = neg
    return out


def segment_from_row(
    row: list[Any],
    segment: str,
    *,
    sample_count: int | None = None,
    decimals: int | None = None,
) -> dict[str, Any]:
    """Parse one segment using the single current measurement-column map."""
    min_i, p50_i, p95_i, max_i, neg_i, bucket_i, count_i = SEGMENT_COLUMNS[segment]
    count = sample_count if sample_count is not None else int(to_float(row[count_i]) or 0)
    return segment_summary(
        {
            "n": count,
            "min": row[min_i],
            "p50": row[p50_i],
            "p95": row[p95_i],
            "max": row[max_i],
            "neg": row[neg_i],
            **{f"b{i}": row[bucket_i + i - 1] for i in range(1, 8)},
        },
        decimals=decimals,
    )


def per_date_segment(summary: dict[str, Any]) -> dict[str, Any]:
    """Keep the established compact per-date JSON shape."""
    if summary.get("status") != "measured":
        return {"status": "not_measured", "sample_count": 0}
    seconds = summary["seconds"]
    return {
        "status": "measured",
        "sample_count": summary["sample_count"],
        "p50": seconds["p50"],
        "p95": seconds["p95"],
        "max": seconds["max"],
        "distribution": summary["distribution"],
    }


def summarize(
    main_rows: list[list[Any]],
    offset_rows: list[list[Any]],
    include_dw: bool,
    observed_at: str,
    expected_seconds: int,
    server_zone_offset: float,
    top_event_rows: list[list[Any]] | None = None,
    missing_zone_offset: float | None = None,
) -> dict[str, Any]:
    """Parse the current measurement schema (one parser, no legacy path).

    Positive buckets are: <=expected threshold, threshold-10m, 10-30m, 30-60m, 1-3h,
    3-24h and >=24h. Upload/end-to-end use valid event-time rows;
    warehouse uses every row with a warehouse timestamp. Rows are 19
    columns without warehouse data and 45 columns with it; any other
    width is rejected with an explicit message instead of being parsed
    with shifted column meanings.
    """
    widths = {len(row) for row in main_rows if row}
    expected = {19} if not include_dw else {45}
    unexpected = widths - expected
    if unexpected:
        other = {45} if not include_dw else {19}
        if unexpected <= other:
            reason = (
                f"row width {sorted(unexpected)} does not match the selected mode; "
                + (
                    "this payload carries warehouse columns - drop --no-warehouse to parse it"
                    if include_dw
                    else "this payload has no warehouse columns - add --no-warehouse to parse it"
                )
            )
        else:
            reason = (
                f"row width {sorted(unexpected)} does not match the current measurement "
                f"schema (expected {sorted(expected)} columns); saved results from older "
                "skill versions are no longer parseable - re-run the measurement"
            )
        return {
            "verdict": "inconclusive",
            "reason": reason,
            "time_basis": "timezone_normalized",
            "warnings": [],
        }
    overall: list[Any] | None = None
    per_rows: list[list[Any]] = []
    for row in main_rows:
        if not row or len(row) < 19:
            continue
        if str(row[0]) == "OVERALL":
            overall = row
        else:
            per_rows.append(row)
    if overall is None:
        return {
            "verdict": "inconclusive",
            "reason": "no OVERALL aggregate row in query result",
            "time_basis": "timezone_normalized",
            "warnings": ["query result missing the OVERALL aggregate row"],
        }

    n_total = int(to_float(overall[1]) or 0)
    zo_missing = int(to_float(overall[2]) or 0)
    zo_invalid = int(to_float(overall[3]) or 0)
    st_distinct = int(to_float(overall[4]) or 0)
    newest_et = str(overall[5]) if overall[5] else None
    newest_st = str(overall[6]) if overall[6] else None
    up_neg = int(to_float(overall[11]) or 0)
    confirmed_missing = zo_missing if missing_zone_offset is not None else 0
    valid_upload = max(0, n_total - zo_invalid - (0 if missing_zone_offset is not None else zo_missing))
    server_time_constant = st_distinct == 1 and n_total > 1

    per_date: list[dict[str, Any]] = []
    for row in per_rows:
        if len(row) < (45 if include_dw else 19):
            continue
        n = int(to_float(row[1]) or 0)
        d_miss = int(to_float(row[2]) or 0)
        d_inv = int(to_float(row[3]) or 0)
        day_valid = max(0, n - d_inv - (0 if missing_zone_offset is not None else d_miss))
        day: dict[str, Any] = {
            "event_date": str(row[0]),
            "row_count": n,
            "zone_offset_missing": d_miss,
            "zone_offset_invalid": d_inv,
            "server_time_distinct": int(to_float(row[4]) or 0),
            "newest_event_time": str(row[5]) if row[5] else None,
            "newest_server_time": str(row[6]) if row[6] else None,
        }
        if day_valid > 0 and not server_time_constant:
            day["upload_lag"] = per_date_segment(
                segment_from_row(row, UPLOAD_SEGMENT, sample_count=day_valid, decimals=0)
            )
        else:
            day["upload_lag"] = {"status": "not_measured", "sample_count": 0}
        if include_dw:
            warehouse_day = segment_from_row(row, WAREHOUSE_SEGMENT, decimals=0)
            if warehouse_day.get("status") == "measured":
                day["warehouse_lag"] = per_date_segment(warehouse_day)
            end_to_end_day = segment_from_row(row, END_TO_END_SEGMENT, decimals=0)
            if end_to_end_day.get("status") == "measured":
                day["end_to_end_lag"] = per_date_segment(end_to_end_day)
        per_date.append(day)

    offset_map: dict[str, dict[str, int]] = {}
    for row in offset_rows:
        if not row or len(row) < 3:
            continue
        d, zo, count = str(row[0]), row[1], int(to_float(row[2]) or 0)
        label = "null" if zo is None else f"{to_float(zo):+g}"
        bucket = offset_map.setdefault(d, {})
        bucket[label] = bucket.get(label, 0) + count
    if offset_rows:
        for day in per_date:
            day["zone_offset_distribution"] = offset_map.get(day["event_date"], {})

    warnings: list[str] = []
    if n_total == 0:
        warnings.append("所选时间内没有查到数据, 请确认时间范围和事件名")
    if missing_zone_offset is not None and zo_missing > 0:
        warnings.append(
            f"{zo_missing:,} 条 #zone_offset 为空的数据按用户提供值 UTC{missing_zone_offset:+g} 纳入统计; "
            f"事件时间先统一到服务器时区 UTC{server_zone_offset:+g} 再计算延迟"
        )
    if n_total > 0 and valid_upload == 0:
        warnings.append(
            f"共 {n_total:,} 条数据没有有效时区信息, 上报段和总延迟无法测算; 平台入库段仍使用全部可测数据"
        )
    elif (zo_missing - confirmed_missing) + zo_invalid > 0:
        excluded = (zo_missing - confirmed_missing) + zo_invalid
        covered = valid_upload / n_total * 100 if n_total else 0.0
        warnings.append(
            f"{excluded:,}/{n_total:,} 条数据没有有效时区信息, 未纳入上报段和总延迟统计; "
            f"有效覆盖占 {covered:.2f}%, 平台入库段不受此限制"
        )

    all_rows_anomalous = valid_upload > 0 and up_neg >= valid_upload
    receive_time_not_row_level = server_time_constant or all_rows_anomalous
    if server_time_constant:
        warnings.append(f"该项目的接收时间不是逐条记录的 (全部 {n_total} 条相同), 上报段数值无意义")
    elif all_rows_anomalous:
        warnings.append(f"{up_neg:,} 条数据的事件时间全部晚于接收时间, 当前接收时间不能支持逐条上报延迟测算")

    if valid_upload > 0 and not receive_time_not_row_level:
        upload_summary = segment_from_row(overall, UPLOAD_SEGMENT, sample_count=valid_upload)
    else:
        upload_summary = {
            "status": (
                "not_measured_server_time_constant" if server_time_constant
                else "not_measured_receive_time_not_row_level" if all_rows_anomalous
                else "not_measured_zone_offset_missing"
            ),
            "sample_count": valid_upload if all_rows_anomalous else 0,
        }
        if all_rows_anomalous:
            upload_summary.update({"negative_count": up_neg, "distribution": {"negative": up_neg}})

    warehouse_summary: dict[str, Any] = {"status": "not_available_on_this_deployment", "sample_count": 0}
    e2e_summary: dict[str, Any] | None = None
    if include_dw and len(overall) >= 45:
        parsed_warehouse = segment_from_row(overall, WAREHOUSE_SEGMENT)
        if parsed_warehouse.get("status") == "measured":
            warehouse_summary = parsed_warehouse
        parsed_end_to_end = segment_from_row(overall, END_TO_END_SEGMENT)
        if parsed_end_to_end.get("status") == "measured":
            e2e_summary = parsed_end_to_end

    segments: dict[str, Any] = {
        UPLOAD_SEGMENT: upload_summary,
        WAREHOUSE_SEGMENT: warehouse_summary,
    }
    if e2e_summary is not None:
        segments[END_TO_END_SEGMENT] = e2e_summary
        if e2e_summary.get("negative_count", 0) > 0:
            warnings.append(
                f"{e2e_summary['negative_count']:,} 行数据事件时间晚于入库时间, 单独列为时间异常, 不计入正向延迟"
            )

    top_events: list[dict[str, Any]] = []
    for row in top_event_rows or []:
        if not row or len(row) < 10:
            continue
        top_events.append({
            "event": str(row[0]),
            "data_source": str(row[1]) if row[1] not in (None, "") else "未记录",
            "upload_sample_count": int(to_float(row[2]) or 0),
            "upload_ge_1h_count": int(to_float(row[3]) or 0),
            "warehouse_sample_count": int(to_float(row[4]) or 0),
            "warehouse_ge_1h_count": int(to_float(row[5]) or 0),
            "end_to_end_sample_count": int(to_float(row[6]) or 0),
            "end_to_end_p50_seconds": fmt(row[7]),
            "end_to_end_p95_seconds": fmt(row[8]),
            "end_to_end_ge_1h_count": int(to_float(row[9]) or 0),
        })

    reference = e2e_summary or (warehouse_summary if warehouse_summary.get("status") == "measured" else upload_summary)
    reference_dist = reference.get("distribution") or {}
    delayed_count = sum(int(reference_dist.get(f"b{i}", 0) or 0) for i in range(2, 8))
    ge_1h_count = sum(int(reference_dist.get(key, 0) or 0) for key in ("b5", "b6", "b7"))
    verdict = "delay_observed" if delayed_count > 0 else (
        "no_delay_observed" if reference.get("status") == "measured" else "inconclusive"
    )
    result: dict[str, Any] = {
        "measurement_schema": "2.0",
        "verdict": verdict,
        "verdict_basis": "event_time_covered_end_to_end" if e2e_summary else "available_segment",
        "time_basis": "timezone_normalized",
        "timestamp_zones": {
            "event_time": {
                "source": "#zone_offset",
                "missing_offset": missing_zone_offset,
                "missing_policy": "user_provided" if missing_zone_offset is not None else "excluded",
            },
            "server_time": {
                "offset": server_zone_offset,
                "source": "user_provided",
            },
            "dw_create_time": {
                "offset": server_zone_offset,
                "source": "user_provided",
            },
        },
        "decision_policy": {"expected_seconds": expected_seconds},
        "long_delay_observation": {"threshold_seconds": 3600, "count": ge_1h_count},
        "total_rows": n_total,
        "per_date": per_date,
        "delay_segments": segments,
        "timezone_quality": {
            "valid_count": max(0, n_total - zo_missing - zo_invalid),
            "missing_count": zo_missing,
            "invalid_count": zo_invalid,
            "confirmed_missing_count": confirmed_missing,
            "confirmed_missing_offset": missing_zone_offset,
            "covered_count": valid_upload,
            "all_null_or_invalid": n_total > 0 and valid_upload == 0,
        },
        "server_time_semantics": "constant" if server_time_constant else "row_level",
        "sample_coverage": {
            "total_rows": n_total,
            "zone_covered_rows": valid_upload,
            "zone_covered_share": (valid_upload / n_total) if n_total else 0.0,
            "warehouse_rows": int(warehouse_summary.get("sample_count") or 0),
            "end_to_end_rows": int((e2e_summary or {}).get("sample_count") or 0),
        },
        "warnings": warnings,
        "freshness": {
            "observed_at": observed_at,
            "newest_event_time": newest_et,
            "newest_server_time": newest_st,
        },
    }
    if top_events:
        result["top_slow_events"] = top_events
    return result


# --------------------------------------------------------------------- main


# --------------------------------------------------------------------- output


def finish(payload: dict[str, Any], exit_code: int) -> None:
    """Emit the checker contract as JSON; presentation belongs to render_report.py."""
    emit(payload, exit_code)
def diagnosis_exit_code(result: dict[str, Any]) -> int:
    judgements = ((result.get("diagnosis") or {}).get("segments") or {})
    if any(
        (judgements.get(key) or {}).get("code") not in {None, "not_measured", "legacy_threshold_unavailable"}
        for key in ("end_to_end", "warehouse", "upload")
    ):
        return 0
    return 3


def choose_probe_date(start_date: str, end_date: str) -> str:
    """Prefer a complete partition when the requested window ends today."""
    today = datetime.now().date()
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    if end == today and start < end:
        return (end - timedelta(days=1)).isoformat()
    return end.isoformat()


def resolve_window(
    days: int,
    start_date: str | None,
    end_date: str | None,
    *,
    today: datetime | None = None,
) -> tuple[str, str, int]:
    """Resolve an inclusive partition window, anchoring --days to --end-date."""
    anchor = (today or datetime.now()).date()

    def parse(value: str, label: str) -> datetime:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"{label} must be YYYY-MM-DD") from exc
        if parsed.strftime("%Y-%m-%d") != value:
            raise ValueError(f"{label} must be YYYY-MM-DD")
        return parsed

    end = parse(end_date, "--end-date") if end_date else datetime.combine(anchor, datetime.min.time())
    start = parse(start_date, "--start-date") if start_date else end - timedelta(days=days - 1)
    window_days = (end.date() - start.date()).days + 1
    if window_days < 1:
        raise ValueError("start date is after end date")
    return start.date().isoformat(), end.date().isoformat(), window_days


def is_missing_dw_column_error(message: str) -> bool:
    """Recognize common engine wording for an unavailable warehouse column."""
    lowered = message.lower()
    return "#dw_create_time" in lowered and any(
        marker in lowered
        for marker in ("cannot be resolved", "not found", "unknown column", "does not exist", "unresolved")
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-id", type=int)
    parser.add_argument("--project-name", help="Confirmed project display name for the report")
    parser.add_argument("--event-name", help="Event name; omit to check ALL events in the project")
    parser.add_argument(
        "--table-ref",
        help="Exact server-authorized event table from analysis sql-table list; normally auto-discovered",
    )
    parser.add_argument("--host")
    parser.add_argument("--days", type=int, default=7, help=f"Window length ending today (local date); >{MAX_WINDOW_DAYS} requires --allow-large-scan")
    parser.add_argument("--start-date", help="YYYY-MM-DD (partition date window start)")
    parser.add_argument("--end-date", help="YYYY-MM-DD (partition date window end)")
    parser.add_argument("--missing-zone-offset", type=float,
                        help="User-provided UTC offset for rows where #zone_offset is NULL")
    parser.add_argument("--server-zone-offset", type=float,
                        help="User-confirmed server UTC offset used by #server_time and #dw_create_time")
    parser.add_argument("--expected-seconds", type=int,
                        help="User-confirmed expected-delay threshold in seconds; must be 1..599")
    parser.add_argument("--allow-large-scan", action="store_true",
                        help="Override the window-length and estimated scan-row protections")
    parser.add_argument("--timeout-seconds", type=int, default=180, help="Gateway timeout per ae-cli call (10..180 seconds)")
    parser.add_argument("--no-warehouse", action="store_true", help="Skip the #dw_create_time segment entirely")
    parser.add_argument("--include-zone-offset-detail", action="store_true",
                        help="Run the optional per-date exact zone-offset distribution query")
    parser.add_argument("--serial-queries", action="store_true",
                        help="Run independent full-window queries serially instead of the default two-worker plan")
    parser.add_argument("--json", action="store_true", help="Compatibility flag; checker output is always JSON")
    parser.add_argument("--output", help="Atomically write JSON to this path")
    parser.add_argument("--dry-run", action="store_true", help="Print planned SQL without executing anything")
    return parser


def build_query_specs(
    args: argparse.Namespace,
    table_ref: str,
    start_date: str,
    end_date: str,
    include_dw: bool,
    server_zone_offset: float,
) -> dict[str, tuple[str | None, str]]:
    """Build the full-window query plan shared by dry-run and execution."""
    specs = {
        "main": (
            args.event_name,
            build_main_sql(
                table_ref,
                args.event_name,
                start_date,
                end_date,
                include_dw,
                args.expected_seconds,
                server_zone_offset,
                args.missing_zone_offset,
            ),
        )
    }
    if not args.event_name and include_dw:
        specs["top_events"] = (
            None,
            build_top_events_sql(
                table_ref,
                start_date,
                end_date,
                server_zone_offset,
                missing_zone_offset=args.missing_zone_offset,
            ),
        )
    if args.include_zone_offset_detail:
        specs["zone_offset_detail"] = (
            args.event_name,
            build_offset_sql(table_ref, args.event_name, start_date, end_date),
        )
    return specs


def build_dry_run_plan(
    args: argparse.Namespace,
    start_date: str,
    end_date: str,
    server_zone_offset: float,
) -> dict[str, Any]:
    """Build the complete execution plan without making network calls."""
    probe_date = choose_probe_date(start_date, end_date)
    table_ref = args.table_ref or "<authorized-event-table-from-analysis-sql-table-list>"
    queries: list[tuple[str, str | None, str]] = [
        (
            "single-partition probe",
            args.event_name,
            build_probe_sql(table_ref, probe_date, not args.no_warehouse, args.event_name),
        ),
    ]
    labels = {
        "main": "main measurement (single-scan compact plan)",
        "top_events": "slowest events ranking",
        "zone_offset_detail": "zone_offset detail (optional)",
    }
    for name, (required_event, sql) in build_query_specs(
        args, table_ref, start_date, end_date, not args.no_warehouse, server_zone_offset
    ).items():
        queries.append((labels[name], required_event, sql))

    return {
        "dry_run": True,
        "executable": AE_CLI_EXECUTABLE,
        "time_basis": "timezone_normalized",
        "expected_seconds": args.expected_seconds,
        "missing_zone_offset": args.missing_zone_offset,
        "server_zone_offset": server_zone_offset,
        "server_zone_offset_source": "user_provided",
        "auth_command": ae_cli_command(["auth", "status"], args.host),
        "queries": [
            {"label": label, "required_event": required_event, "sql": sql}
            for label, required_event, sql in queries
        ],
        "notes": [
            "the single-partition probe tests data access, #dw_create_time, and estimated scan cost",
            "the compact main query uses GROUPING SETS for per-day and overall results",
            "upload and end-to-end exclude invalid time-zone rows; warehouse uses all measurable rows",
            "exact zone-offset distribution is optional",
            "independent full-window queries use two workers unless --serial-queries is set",
            f"windows above {MAX_WINDOW_DAYS} days or about {SCAN_ROW_BUDGET:,} rows require --allow-large-scan",
            "synchronous failures retain their request id; only asynchronous run_ids are cancelable",
        ],
    }


def main() -> None:
    global AE_CLI_EXECUTABLE, OUTPUT_PATH

    args = build_parser().parse_args()
    OUTPUT_PATH = Path(args.output).expanduser().resolve() if args.output else None
    server_zone_offset = args.server_zone_offset
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")

    if args.server_zone_offset is None:
        finish({"verdict": "invalid_arguments", "reason": "--server-zone-offset requires a user-confirmed value"}, 2)
    if args.expected_seconds is None:
        finish({"verdict": "invalid_arguments", "reason": "--expected-seconds requires a user-confirmed value"}, 2)
    if args.days < 1 and not args.start_date:
        finish({"verdict": "invalid_arguments", "reason": "--days must be at least 1"}, 2)
    if not 10 <= args.timeout_seconds <= 180:
        finish({"verdict": "invalid_arguments", "reason": "--timeout-seconds must be between 10 and 180"}, 2)
    if not 1 <= args.expected_seconds < 600:
        finish({"verdict": "invalid_arguments", "reason": "--expected-seconds must be between 1 and 599"}, 2)
    if args.missing_zone_offset is not None and not -12 <= args.missing_zone_offset <= 14:
        finish({"verdict": "invalid_arguments", "reason": "--missing-zone-offset must be between -12 and +14"}, 2)
    if not -12 <= server_zone_offset <= 14:
        finish({"verdict": "invalid_arguments", "reason": "--server-zone-offset must be between -12 and +14"}, 2)

    if args.event_name and ("'" in args.event_name or "\\" in args.event_name):
        finish(
            {"verdict": "invalid_arguments", "reason": "event name must not contain quotes or backslashes"},
            2,
        )

    try:
        start_date, end_date, window_days = resolve_window(args.days, args.start_date, args.end_date)
    except ValueError as exc:
        finish({"verdict": "invalid_arguments", "reason": str(exc)}, 2)
    if window_days > MAX_WINDOW_DAYS and not args.allow_large_scan:
        finish(
            {
                "verdict": "invalid_arguments",
                "reason": (
                    f"window is {window_days} days, above the {MAX_WINDOW_DAYS}-day protection limit; "
                    "narrow the window or pass --allow-large-scan"
                ),
            },
            2,
        )

    if not args.project_id:
        finish({"verdict": "invalid_arguments", "reason": "--project-id is required"}, 2)

    AE_CLI_EXECUTABLE = resolve_ae_cli()
    if not AE_CLI_EXECUTABLE:
        finish(
            {
                "verdict": "blocked",
                "reason": (
                    "ae-cli was not found on PATH. Install it using the platform's supported "
                    "method, then verify with `ae-cli --version`."
                ),
            },
            2,
        )

    host = args.host
    timeout = args.timeout_seconds

    if args.dry_run:
        emit(
            build_dry_run_plan(
                args,
                start_date,
                end_date,
                server_zone_offset,
            ),
            0,
        )

    # Authentication and direct SQL execution are the only required capabilities.
    capabilities: dict[str, Any] = {}

    probe_date = choose_probe_date(start_date, end_date)
    try:
        auth = run_ae(["auth", "status"], host, timeout)
        if find_value(auth, "authenticated") is not True:
            raise DiagnosticError("ae-cli is not authenticated; run ae-cli auth login")
    except DiagnosticError as exc:
        finish({"verdict": "blocked", "reason": str(exc)}, 2)
    capabilities["authentication"] = {"available": True}

    try:
        table_ref, available_columns = discover_event_table(
            args.project_id, args.table_ref, host, timeout
        )
    except DiagnosticError as exc:
        finish({"verdict": "blocked", "reason": str(exc), "capabilities": capabilities}, 2)
    capabilities["sql_table_discovery"] = {
        "available": True,
        "table_ref": table_ref,
    }

    # Project and event scope are confirmed by the caller before execution;
    # the probe SQL below is the authoritative access check.
    project_name = args.project_name
    event_display = args.event_name
    # Data access, warehouse capability and scan cost are probed together by
    # executing one lightweight SQL against the newest partition. A returned
    # result row is direct evidence that data queries are permitted.
    dw_available = not args.no_warehouse
    dw_note = "skipped by --no-warehouse" if args.no_warehouse else "probe succeeded"
    probe_rows: list[list[Any]] | None = None
    message = ""
    try:
        probe_rows = run_sql_query(
            args.project_id,
            args.event_name,
            build_probe_sql(table_ref, probe_date, dw_available, args.event_name),
            host,
            timeout,
        )
    except DiagnosticError as exc:
        message = str(exc)
        if dw_available and is_missing_dw_column_error(message):
            dw_available = False
            dw_note = "column #dw_create_time cannot be resolved on this project"
            try:
                probe_rows = run_sql_query(
                    args.project_id,
                    args.event_name,
                    build_probe_sql(table_ref, probe_date, False, args.event_name),
                    host,
                    timeout,
                )
            except DiagnosticError as exc2:
                message = str(exc2)
    if probe_rows is None:
        lowered = message.lower()
        reason = (
            f"data queries are not permitted with this account: {message[:400]}"
            if any(hint in lowered for hint in PERMISSION_HINTS)
            else message[:600]
        )
        finish(
            {
                "verdict": "blocked",
                "reason": reason,
                "note": f"the server-authorized table {table_ref!r} was selected through SQL table discovery",
                "capabilities": capabilities,
            },
            2,
        )
    capabilities["data_query"] = {"available": True, "evidence": "probe SQL returned a result row"}

    # Scan-cost protection: estimate the full window from the probe day and
    # stop before an expensive scan unless explicitly overridden.
    probe_day_rows = int(to_float(probe_rows[0][0]) or 0) if probe_rows and probe_rows[0] else 0
    estimated_rows = probe_day_rows * window_days
    scan_protection = {
        "probe_date": probe_date,
        "probe_day_rows": probe_day_rows,
        "window_days": window_days,
        "estimated_window_rows": estimated_rows,
        "row_budget": SCAN_ROW_BUDGET,
    }
    if estimated_rows > SCAN_ROW_BUDGET and not args.allow_large_scan:
        finish(
            {
                "verdict": "blocked",
                "reason": (
                    f"estimated scan is about {estimated_rows:,} rows "
                    f"({probe_day_rows:,} on {probe_date} x {window_days} days), above the "
                    f"{SCAN_ROW_BUDGET:,}-row protection budget; narrow the window, pass "
                    "--event-name, or pass --allow-large-scan"
                ),
                "scan_protection": scan_protection,
                "capabilities": capabilities,
            },
            2,
        )

    # Compact full-window plan. The main query includes per-day and overall
    # distributions in one aggregation. Independent optional
    # queries share a two-worker pool by default, reducing wall time without
    # changing their individual timeout guarantees.
    measurement_started = time.monotonic()
    query_specs = build_query_specs(args, table_ref, start_date, end_date, dw_available, server_zone_offset)

    worker_count = 1 if args.serial_queries else min(2, len(query_specs))
    futures: dict[str, Future[Any]] = {}
    query_outcomes: dict[str, list[list[Any]] | DiagnosticError] = {}
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        for name, (required_event, query_sql) in query_specs.items():
            futures[name] = pool.submit(
                run_sql_query,
                args.project_id,
                required_event,
                query_sql,
                host,
                timeout,
            )
        for name, future in futures.items():
            try:
                query_outcomes[name] = future.result()
            except DiagnosticError as exc:
                query_outcomes[name] = exc
            except Exception as exc:  # keep worker failures structured
                query_outcomes[name] = DiagnosticError(
                    f"{name} query worker failed: {type(exc).__name__}: {str(exc)[:300]}"
                )

    main_outcome = query_outcomes["main"]
    if isinstance(main_outcome, DiagnosticError):
        finish({"verdict": "inconclusive", "reason": str(main_outcome)}, 3)
    main_rows = main_outcome

    offset_rows: list[list[Any]] = []
    optional_query_notes: list[str] = []
    offset_outcome = query_outcomes.get("zone_offset_detail")
    if isinstance(offset_outcome, list):
        offset_rows = offset_outcome
    elif isinstance(offset_outcome, DiagnosticError):
        optional_query_notes.append(f"zone-offset detail failed: {str(offset_outcome)[:300]}")

    top_event_rows: list[list[Any]] = []
    top_event_note: str | None = None
    top_outcome = query_outcomes.get("top_events")
    if isinstance(top_outcome, list):
        top_event_rows = top_outcome
    elif isinstance(top_outcome, DiagnosticError):
        top_event_note = f"the slowest-events ranking query failed: {str(top_outcome)[:300]}"
    elif not args.event_name and not dw_available:
        top_event_note = "the slowest-events ranking is unavailable because warehouse timing is unavailable"

    execution = {
        "query_plan": "compact_v1",
        "scope_source": "caller_confirmed",
        "parallel_full_window_queries": worker_count > 1,
        "full_window_query_count": len(query_specs),
        "zone_offset_detail": args.include_zone_offset_detail,
        "measurement_wall_seconds": round(time.monotonic() - measurement_started, 3),
    }
    if optional_query_notes:
        execution["optional_query_notes"] = optional_query_notes

    result = summarize(
        main_rows,
        offset_rows,
        dw_available,
        observed_at,
        args.expected_seconds,
        server_zone_offset,
        top_event_rows,
        args.missing_zone_offset,
    )
    result.update(
        {
            "project_id": args.project_id,
            "project_name": project_name or str(args.project_id),
            "event_name": event_display or "全部事件",
            "host": host or find_value(auth, "host"),
            "window": {"start_date": start_date, "end_date": end_date},
            "warehouse_capability": {"available": dw_available, "note": dw_note},
            "capabilities": capabilities,
            "scan_protection": scan_protection,
            "execution": execution,
        }
    )
    if top_event_note:
        result["top_slow_events_note"] = top_event_note
    result = enrich_result(result)
    exit_code = diagnosis_exit_code(result)
    finish(result, exit_code)


if __name__ == "__main__":
    main()
