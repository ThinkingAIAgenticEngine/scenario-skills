#!/usr/bin/env python3
"""
metric-alert runtime executor

Reads alert_rule.json, executes SQL queries, compares trigger conditions, and pushes an alert on a hit.

Environment variables:
  METRIC_ALERT_SPEC: path to alert_rule.json, defaults to ./alert_rule.json
  METRIC_ALERT_DRY_RUN: when set to 1, only query without pushing (dry-run mode); run_result.json additionally
      writes rendered_sql (the rendered SQL of the main/baseline queries) and sample_rows (first 5 sample rows)
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib import request as urlrequest

SPEC_PATH = os.environ.get("METRIC_ALERT_SPEC", "./alert_rule.json")
DRY_RUN = os.environ.get("METRIC_ALERT_DRY_RUN", "0") == "1"
RUN_RESULT_PATH = "./run_result.json"
ALERT_MESSAGE_PATH = "./alert_message.md"

QUERY_TIMEOUT_SECONDS = 300
PREVIEW_ROWS = 1000
SAMPLE_ROWS = 5
MESSAGE_VALUE_KEYS = ("metric_value", "value", "metric")

# metric.type whitelist (shared by evaluate and the message variable mapping; change it in one place)
VALID_METRIC_TYPES = ("single", "ratio", "funnel", "retention", "group", "row_filter", "custom")

# Message variables available for each metric_type (consistent with the "message_template variables" table in rule-schema.md).
# single/ratio/funnel/retention/custom all follow the single-value result path and share the same variable set.
_SINGLE_VALUE_VARS = {"task_name", "window", "project_name", "current_value", "baseline_value"}
MESSAGE_VARS_BY_TYPE = {
    "single": _SINGLE_VALUE_VARS,
    "ratio": _SINGLE_VALUE_VARS,
    "funnel": _SINGLE_VALUE_VARS,
    "retention": _SINGLE_VALUE_VARS,
    "custom": _SINGLE_VALUE_VARS,
    "group": {"task_name", "window", "project_name", "row_count", "total_groups",
              "miss_groups", "data_table"},
    "row_filter": {"task_name", "window", "project_name", "row_count", "user_list"},
}

# ---------- Safety validation ----------
# SQL is executed via `ae-cli analysis adhoc run` (read-only analysis API), so DDL/DML never reaches the storage layer.
# Dangerous-keyword blocking is not applied: word-boundary matching over the whole text would flag legal event names
# or property values such as 'delete' as dangerous statements, blocking normal tasks instead. Here we only validate
# that the query can run correctly and at low cost.

_LIMIT_RE = re.compile(r"\blimit\s+\d+\b", re.IGNORECASE)
_PARTITION_RE = re.compile(
    r'"?\$part_date"?\s*(?:>=|<=|>|<|=|\bBETWEEN\b|\bIN\b)', re.IGNORECASE
)
_PLACEHOLDER_RESIDUE_RE = re.compile(r"\{\{[^{}]+\}\}")
_MESSAGE_VAR_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")


def sql_safety_check(sql: str) -> None:
    """SQL structural validation: LIMIT is required; queries hitting event tables require a $part_date partition predicate"""
    if not _LIMIT_RE.search(sql):
        raise RuntimeError("SQL missing LIMIT clause")
    # User tables (e.g. ta.v_user_11) have no $part_date partition column, so only SQL querying user tables is exempt;
    # event tables (ta.v_event_*) still require the $part_date predicate, otherwise it triggers a full table scan
    if re.search(r"\bv_user_\w+\b", sql, re.IGNORECASE) and \
            not re.search(r"\bv_event_\w+\b", sql, re.IGNORECASE):
        return
    if not _PARTITION_RE.search(sql):
        raise RuntimeError(
            "SQL missing $part_date partition predicate "
            "(must compare $part_date with =/>=/<=/>/</BETWEEN/IN)"
        )


# ---------- DRY_RUN dry-run trace ----------

# Collect rendered SQL and sample rows; populated only under DRY_RUN and persisted with run_result.json
_DRY_RUN_SQL = []
_DRY_RUN_SAMPLE_ROWS = []


def _collect_dry_run(sql: str, rows: list, label: str, window: str) -> None:
    if not DRY_RUN:
        return
    _DRY_RUN_SQL.append({"label": label, "window": window, "sql": sql})
    _DRY_RUN_SAMPLE_ROWS.append(
        {"label": label, "window": window, "sample_rows": rows[:SAMPLE_ROWS]}
    )


# ---------- ae-cli execution ----------

def run_query(sql: str, rule: dict) -> list:
    """Execute the SQL query and return the row list"""
    ae_cli = rule.get("env", {}).get("ae_cli_path", "ae-cli")
    project_id = str(rule["project_id"])

    definition = json.dumps({"sql": sql})
    cmd = [
        ae_cli, "analysis", "adhoc", "run",
        "-p", project_id,
        "--model-type", "sql",
        "--definition", definition,
        "--preview-rows", str(PREVIEW_ROWS),
        "--format", "json",
    ]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=QUERY_TIMEOUT_SECONDS, check=False
        )
    except FileNotFoundError:
        raise RuntimeError(f"ae-cli not found: {ae_cli}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"query timeout after {QUERY_TIMEOUT_SECONDS}s")

    if proc.returncode != 0:
        raise RuntimeError(
            f"ae-cli exited with code {proc.returncode}: {proc.stderr[:300]}"
        )

    # Parse the output (skip a possible dispatching hint line)
    out = proc.stdout
    json_start = out.find('{')
    if json_start < 0:
        raise RuntimeError(f"ae-cli returned non-JSON: {out[:200]}")

    try:
        payload = json.loads(out[json_start:])
    except json.JSONDecodeError:
        raise RuntimeError(f"ae-cli returned invalid JSON: {out[:200]}")

    if not payload.get("ok"):
        error = payload.get("error", {})
        raise RuntimeError(f"query failed: {error.get('message', 'unknown error')}")

    data = payload.get("data", {})
    inner = data.get("data", data)
    if "rows" not in inner:
        raise RuntimeError(f"ae-cli response missing rows field: {str(inner)[:200]}")
    rows = inner.get("rows") or []
    titles = inner.get("title") or []

    # adhoc returns array rows (e.g. [[null,"723187"]]); zip them with the title column-name array into dict rows
    # so group/row_filter/result_column can look up values by column name; if title is missing or its length
    # mismatches, columns cannot be located, so raise an error directly
    if rows and isinstance(rows[0], (list, tuple)):
        if not titles:
            raise RuntimeError(
                "ae-cli response rows are arrays but title (column names) is missing; "
                "cannot locate columns (group/row_filter/result_column need column names)"
            )
        if len(titles) != len(rows[0]):
            raise RuntimeError(
                f"ae-cli response title length {len(titles)} != row length {len(rows[0])}; "
                "cannot map columns"
            )
        rows = [dict(zip(titles, row)) for row in rows]
    return rows


# ---------- Time window computation ----------

def get_now_in_timezone(tz_offset: int) -> datetime:
    """Get the current time in the specified timezone"""
    tz = timezone(timedelta(hours=tz_offset))
    return datetime.now(tz)


def compute_window(rule: dict, offset_periods: int = 0, offset_days: int = 0) -> tuple:
    """
    Compute the time window
    offset_periods: how many periods to go back; the unit follows the window type (natural_hour=hours, natural_week=weeks, otherwise days)
    offset_days: absolute number of days to go back, independent of the window type (used by same_time_yesterday/last_week/history_*)
    Returns (start_datetime, end_datetime, target_date_str)
    """
    window = rule["window"]
    window_type = window["type"]

    # Get the settlement timezone
    tz_config = rule.get("timezone", {})
    settle_tz = tz_config.get("settle_timezone", 8)

    now = get_now_in_timezone(settle_tz)

    # Apply the offset (used for historical baselines)
    if offset_days > 0:
        now = now - timedelta(days=offset_days)
    if offset_periods > 0:
        if window_type == "natural_hour":
            now = now - timedelta(hours=offset_periods)
        elif window_type == "natural_week":
            now = now - timedelta(weeks=offset_periods)
        else:
            now = now - timedelta(days=offset_periods)

    if window_type == "natural_hour":
        # Previous complete hour
        end = now.replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=1)
        target_date = start.strftime("%Y-%m-%d")

    elif window_type == "natural_day":
        # Full day yesterday
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
        target_date = start.strftime("%Y-%m-%d")

    elif window_type == "today_to_now":
        # From 00:00 today to the last complete hour (aligned to the hour so hours are comparable and {{current_hour}} semantics stay consistent)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(minute=0, second=0, microsecond=0)
        if end <= start:
            # Triggered in the 00:00 hour (00:00-00:59): today has no complete hour yet, so fall back to the full previous day,
            # covering the 23:00-24:00 window of the previous day that no hourly run can obtain, avoiding a guaranteed first failure each day
            end = start
            start = start - timedelta(days=1)
        target_date = start.strftime("%Y-%m-%d")

    elif window_type == "natural_week":
        # Previous natural week (Monday to Sunday)
        days_since_monday = now.weekday()
        end = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=7)
        target_date = start.strftime("%Y-%m-%d")

    else:
        raise RuntimeError(f"unknown window type: {window_type}")

    return start, end, target_date


# ---------- SQL rendering ----------

def render_sql(sql_template: str, window_start: datetime, window_end: datetime, target_date: str, rule: dict = None) -> str:
    """
    Render the SQL template, replacing time placeholders
    """
    sql = sql_template

    # A natural_week window combined with a non-week template: {{date}} would be silently rendered to last Monday (counting only 1 day of data), so it must be intercepted here
    if rule and rule.get("window", {}).get("type") == "natural_week" \
            and ("{{week_start}}" not in sql or "{{week_end}}" not in sql):
        raise RuntimeError(
            "natural_week window requires '{{week_start}}'/'{{week_end}}' in sql_template "
            "(use template 4 or template 11 custom SQL with week placeholders)"
        )

    # Format the time
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")
    current_hour = window_end.strftime("%H")
    if rule and rule.get("window", {}).get("type") == "today_to_now":
        # Same-day cumulative: {{current_hour}} is the number of whole hours the window covers (24 when falling back to the full previous day at 00:00);
        # taking the hour of window_end directly would render the fallback case as 00, leaving an empty filter range
        current_hour = str(int((window_end - window_start).total_seconds() // 3600))

    # Replace time placeholders
    sql = sql.replace("{{date}}", target_date)
    sql = sql.replace("{{window_start}}", start_str)
    sql = sql.replace("{{window_end}}", end_str)
    sql = sql.replace("{{current_hour}}", current_hour)

    # Extra placeholders for the natural_week window
    if "{{week_start}}" in sql or "{{week_end}}" in sql:
        sql = sql.replace("{{week_start}}", window_start.strftime("%Y-%m-%d"))
        sql = sql.replace("{{week_end}}", (window_end - timedelta(days=1)).strftime("%Y-%m-%d"))

    # Extra placeholders for the retention window
    retention_days = None
    if "{{base_date}}" in sql:
        base_date = _compute_base_date(rule, target_date)
        sql = sql.replace("{{base_date}}", base_date)
        retention_days = int(rule.get("metric", {}).get("retention_days", 1))

    # Placeholder residue validation: business parameter placeholders must be fully replaced at config stage; any residue means a config error
    residue = _PLACEHOLDER_RESIDUE_RE.search(sql)
    if residue:
        raise RuntimeError(f"SQL template contains unresolved placeholder: {residue.group(0)}")

    # Retention hard validation: the lookback days in templates 8/9 are literals hard-coded at config stage,
    # while the base_date computed by the script from metric.retention_days is a second source of truth; drift
    # would silently produce a wrong retention rate. Anchor on the "date('<base_date>') + INTERVAL '<n>' DAY"
    # boundary pattern and require retention_days to appear in the matched literal set (contains semantics: only
    # catch drift of retention_days itself, not a character-by-character check of the +/-1 partition extension
    # boundary; a boundary literal matched with the same shape as the anchor pattern is normal and not an error);
    # custom retention SQL without that pattern, or SQL not using {{base_date}}, skips validation and needs manual review
    if retention_days is not None and rule.get("metric", {}).get("type") == "retention":
        boundary = re.compile(
            r"date\('" + re.escape(base_date) + r"'\)\s*\+\s*INTERVAL\s+'(\d+)'\s+DAY",
            re.IGNORECASE,
        )
        matched = boundary.findall(sql)
        if matched and str(retention_days) not in matched:
            raise RuntimeError(
                f"retention SQL lookback INTERVAL {matched} does not contain "
                f"metric.retention_days={retention_days}; the SQL lookback literal "
                "(config-stage) and retention_days (rule field) have drifted — "
                "regenerate the SQL from template 8/9 with matching days"
            )

    return sql


def _compute_base_date(rule: dict, target_date: str) -> str:
    """
    Compute the base date of the retention window (new user date)
    base_date = target_date - retention_days days
    """
    retention_days = int(rule.get("metric", {}).get("retention_days", 1))
    base = datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=retention_days)
    return base.strftime("%Y-%m-%d")


def get_sql_from_rule(rule: dict) -> str:
    """Get the SQL template from the alert rule"""
    sql_template = rule.get("sql_template")
    if not sql_template:
        raise RuntimeError("alert_rule.json missing sql_template field")
    return sql_template


# ---------- Trigger condition evaluation ----------

def _check_day_based_baseline(rule: dict, compare_to: str) -> None:
    """
    Day-level offsets (same_time_* / history_*) fall back into the same natural week under a natural_week window
    (baseline = current value), so they must be intercepted; use previous_period for week-level baselines (offset_periods=1, going back a full week)
    """
    window_type = rule.get("window", {}).get("type")
    day_based = compare_to in (
        "same_time_yesterday", "same_time_last_week", "history_avg", "history_max",
    )
    if window_type == "natural_week" and day_based:
        raise RuntimeError(
            f"compare_to={compare_to} shifts by days, which stays inside the same "
            "natural week under window.type=natural_week (baseline would equal "
            "current value). Use compare_to=previous_period for week-over-week"
        )


def _query_metric_rows(rule: dict, label: str, offset_periods: int = 0, offset_days: int = 0) -> list:
    """Run one query with a window offset and return the result row list (traced by label under DRY_RUN)"""
    start, end, target_date = compute_window(rule, offset_periods=offset_periods, offset_days=offset_days)
    sql_template = get_sql_from_rule(rule)
    sql = render_sql(sql_template, start, end, target_date, rule)
    sql_safety_check(sql)
    rows = run_query(sql, rule)
    _collect_dry_run(
        sql, rows, label,
        f"{start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%Y-%m-%d %H:%M')}",
    )
    return rows


def _query_metric(rule: dict, label: str, offset_periods: int = 0, offset_days: int = 0) -> float:
    """Run one single-value metric query with a window offset and return metric_value (None when there is no data)"""
    rows = _query_metric_rows(rule, label, offset_periods=offset_periods, offset_days=offset_days)
    if not rows:
        return None
    return _extract_value(rows[0], rule)


def get_baseline_value(rule: dict) -> float:
    """
    Get the baseline value of a single-value metric, returns float (None when there is no data)
    """
    trigger = rule["trigger"]
    compare_to = trigger["compare_to"]

    if compare_to == "fixed":
        return float(trigger["threshold"])

    _check_day_based_baseline(rule, compare_to)

    # Historical data needs to be queried
    # previous_period goes back one period by window type; same_time_* / history_* always go back by days
    if compare_to == "previous_period":
        return _query_metric(rule, "baseline_query", offset_periods=1)
    elif compare_to == "same_time_yesterday":
        return _query_metric(rule, "baseline_query", offset_days=1)
    elif compare_to == "same_time_last_week":
        return _query_metric(rule, "baseline_query", offset_days=7)
    elif compare_to in ("history_avg", "history_max"):
        # Past N-day average/maximum: per-window queries + Python aggregation (consistent with other monitoring scenarios).
        # A failed single-window query skips that window; all windows failing is a systemic failure, so raise and exit rather than silently not triggering
        history_days = int(trigger.get("history_days", 7))
        values = []
        failed_windows = 0
        last_error = None
        for i in range(1, history_days + 1):
            try:
                val = _query_metric(rule, f"baseline_query (-{i}d)", offset_days=i)
            except Exception as e:
                print(f"WARN: baseline day -{i}d query failed, skipped: {e}", file=sys.stderr)
                failed_windows += 1
                last_error = e
                continue
            if val is not None:
                values.append(val)
        if failed_windows == history_days:
            raise RuntimeError(
                f"baseline query failed for all {history_days} history windows "
                f"(systemic failure, not missing data); last error: {last_error}"
            )
        if not values:
            return None
        return sum(values) / len(values) if compare_to == "history_avg" else max(values)
    else:
        raise RuntimeError(f"unknown compare_to: {compare_to}")


def _group_rows_to_baseline_map(rows: list, window_label: str) -> dict:
    """All-group baseline query result rows -> {group_key: baseline value}.
    Groups whose metric_value is NULL or non-numeric map to None (treated as a missing baseline, without blocking other groups)"""
    baselines = {}
    for row in rows:
        if not isinstance(row, dict) or "group_key" not in row or "metric_value" not in row:
            raise RuntimeError(
                "group baseline query row must be a dict with group_key/metric_value "
                f"columns (row: {row!r})"
            )
        group_key = row["group_key"]
        if group_key is None:
            continue
        value = row["metric_value"]
        if value is not None:
            try:
                value = float(value)
            except (TypeError, ValueError):
                print(
                    f"WARN: baseline metric_value is not numeric for group '{group_key}' "
                    f"in {window_label}, treated as missing baseline: {value!r}",
                    file=sys.stderr,
                )
                value = None
        baselines[group_key] = value
    return baselines


def get_group_baselines(rule: dict) -> dict:
    """Baseline for group monitoring: run one all-group SQL per offset window (isomorphic to the main query, without the group filter),
    returning {group_key: baseline value}. The query count = number of baseline windows (history_avg 7 days = 7 SQLs),
    independent of the number of groups; a failed single-window query affects all groups of that window (the window is skipped), and all windows failing raises and exits"""
    trigger = rule["trigger"]
    compare_to = trigger["compare_to"]

    _check_day_based_baseline(rule, compare_to)

    if compare_to == "previous_period":
        rows = _query_metric_rows(rule, "baseline_query", offset_periods=1)
        return _group_rows_to_baseline_map(rows, "baseline_query")
    elif compare_to == "same_time_yesterday":
        rows = _query_metric_rows(rule, "baseline_query", offset_days=1)
        return _group_rows_to_baseline_map(rows, "baseline_query")
    elif compare_to == "same_time_last_week":
        rows = _query_metric_rows(rule, "baseline_query", offset_days=7)
        return _group_rows_to_baseline_map(rows, "baseline_query")
    elif compare_to in ("history_avg", "history_max"):
        history_days = int(trigger.get("history_days", 7))
        values_by_group = {}
        failed_windows = 0
        last_error = None
        for i in range(1, history_days + 1):
            label = f"baseline_query (-{i}d)"
            try:
                rows = _query_metric_rows(rule, label, offset_days=i)
            except Exception as e:
                print(f"WARN: baseline day -{i}d query failed, skipped (affects all groups): {e}", file=sys.stderr)
                failed_windows += 1
                last_error = e
                continue
            for group_key, value in _group_rows_to_baseline_map(rows, label).items():
                if value is not None:
                    values_by_group.setdefault(group_key, []).append(value)
        if failed_windows == history_days:
            raise RuntimeError(
                f"baseline query failed for all {history_days} history windows "
                f"(systemic failure, not missing data); last error: {last_error}"
            )
        if compare_to == "history_avg":
            return {g: sum(v) / len(v) for g, v in values_by_group.items()}
        return {g: max(v) for g, v in values_by_group.items()}
    else:
        raise RuntimeError(f"unknown compare_to: {compare_to}")


def _extract_value(row, rule: dict = None) -> float:
    """
    Extract the numeric value from the query result.
    Prefer the column specified by metric.result_column; when unspecified, use the whitelist keys
    (metric_value/value/metric);
    a key that exists but whose value is NULL (e.g. NULLIF with a zero denominator) returns None; raise if the numeric column cannot be located.
    """
    if isinstance(row, dict):
        result_column = (rule or {}).get("metric", {}).get("result_column")
        if result_column:
            if result_column not in row:
                raise RuntimeError(
                    f"result_column '{result_column}' not found in row "
                    f"(row keys: {list(row.keys())[:10]})"
                )
            if row[result_column] is None:
                return None
            return float(row[result_column])
        for key in MESSAGE_VALUE_KEYS:
            if key in row:
                if row[key] is None:
                    return None
                return float(row[key])
        raise RuntimeError(
            "cannot extract metric value from row: no key in "
            f"{MESSAGE_VALUE_KEYS} (row keys: {list(row.keys())[:10]})"
        )
    elif isinstance(row, (list, tuple)) and len(row) > 0:
        # Take the last column (usually metric_value)
        if row[-1] is None:
            return None
        return float(row[-1])
    raise RuntimeError(f"cannot extract metric value from row: {row!r}")


def check_trigger(rule: dict, current_value, baseline_value) -> bool:
    """
    Check whether the alert triggers.
    gt/lt/eq: current value vs threshold (absolute threshold)
    pct_change_gt/lt: (current value - baseline value)/|baseline value| vs threshold; no trigger when the baseline is missing
    """
    trigger = rule["trigger"]
    operator = trigger["operator"]
    threshold = float(trigger["threshold"])

    if operator in ("pct_change_gt", "pct_change_lt") and threshold < 0:
        raise RuntimeError(
            f"pct_change threshold must be >= 0 (got {threshold}); "
            "direction is decided by the operator, not the sign of the threshold"
        )

    if current_value is None:
        return False

    if operator == "gt":
        return current_value > threshold
    elif operator == "lt":
        return current_value < threshold
    elif operator == "eq":
        return current_value == threshold
    elif operator in ("pct_change_gt", "pct_change_lt"):
        if baseline_value is None or baseline_value == 0:
            return False
        change = (current_value - baseline_value) / abs(baseline_value)
        return change > threshold if operator == "pct_change_gt" else change < -threshold
    else:
        raise RuntimeError(f"unknown operator: {operator}")


# ---------- Group and list results ----------

def _render_cell(value) -> str:
    if value is None:
        return "-"
    s = str(value)
    # Escape | within Markdown table cells as \| and replace newlines with spaces, so the table structure is not broken
    s = s.replace("|", "\\|").replace("\n", " ")
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return s


def format_user_list(rows: list, columns: list) -> str:
    """Render row-level results as a Markdown list"""
    if not rows:
        return "(no data)"
    lines = []
    for row in rows:
        if isinstance(row, dict):
            parts = []
            for col in columns:
                parts.append(f"{col}={_render_cell(row.get(col))}")
            lines.append("- " + ", ".join(parts))
        elif isinstance(row, (list, tuple)):
            lines.append("- " + ", ".join(_render_cell(v) for v in row))
        else:
            lines.append(f"- {row}")
    return "\n".join(lines)


def format_data_table(rows: list, columns: list) -> str:
    """Render group results as a Markdown table"""
    if not rows:
        return "(no data)"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        if isinstance(row, dict):
            body.append("| " + " | ".join(_render_cell(row.get(c)) for c in columns) + " |")
        elif isinstance(row, (list, tuple)):
            body.append("| " + " | ".join(_render_cell(v) for v in row) + " |")
    return "\n".join([header, sep] + body)


def evaluate_group_rows(rule: dict, rows: list) -> dict:
    """
    Group monitoring: each group is compared against its own baseline (the baseline is pre-fetched by the all-group SQL, see get_group_baselines);
    groups with a missing baseline do not trigger (counted into miss_groups).
    Returns {"hit_groups": [...], "total_groups": N, "miss_groups": N, "with_baseline": bool}
    """
    trigger = rule["trigger"]
    compare_to = trigger["compare_to"]

    # gt/lt/eq are absolute-threshold decisions (consistent with the single-value path metric_alert.py:evaluate);
    # however dynamic compare_to is, no baseline is queried, avoiding wasted baseline SQL and a false systemic failure
    # report when every baseline fails
    need_baseline = compare_to != "fixed" and trigger["operator"] not in ("gt", "lt", "eq")
    baselines = get_group_baselines(rule) if need_baseline else {}

    hit_groups = []
    miss_count = 0
    for row in rows:
        if not isinstance(row, dict) or "group_key" not in row or "metric_value" not in row:
            raise RuntimeError("group monitor requires dict rows with group_key/metric_value columns")
        group_key = row.get("group_key")
        if group_key is None:
            print(f"WARN: group row with NULL group_key skipped: {row!r}", file=sys.stderr)
            miss_count += 1
            continue
        metric_value = row.get("metric_value")
        if metric_value is None:
            miss_count += 1
            continue
        try:
            value = float(metric_value)
        except (TypeError, ValueError):
            # A single dirty group (non-numeric) only skips that group, without failing the whole evaluation
            print(
                f"WARN: group '{group_key}' metric_value is not numeric, group skipped: {metric_value!r}",
                file=sys.stderr,
            )
            miss_count += 1
            continue
        if need_baseline:
            baseline = baselines.get(group_key)
            if baseline is None:
                # A group with a missing baseline cannot be judged for period-over-period change, counted as skipped like NULL values/dirty data
                miss_count += 1
                continue
        else:
            baseline = None
        if check_trigger(rule, value, baseline):
            entry = {"group_key": group_key, "metric_value": value}
            if need_baseline:
                entry["baseline_value"] = baseline
            hit_groups.append(entry)
    return {
        "hit_groups": hit_groups,
        "total_groups": len(rows),
        "miss_groups": miss_count,
        "with_baseline": need_baseline,
    }


# ---------- Alert push ----------

PUSH_MAX_RETRIES = 3  # retry count (excluding the first attempt): 1 + 3 = 4 attempts in total
PUSH_RETRY_BASE_DELAY = 2  # seconds; backoff 2s / 4s / 8s, total wait 14s


def _post_webhook(url: str, data: bytes) -> tuple:
    """A single HTTP POST, returns (status, body, error); a non-empty error means a network-layer failure that can be retried"""
    req = urlrequest.Request(
        url, data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urlrequest.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", "ignore"), None
    except urlrequest.HTTPError as e:
        # 4xx/5xx are deterministic failures: return the status code and body so the caller can judge by status, not treated as a retryable network error
        try:
            err_body = e.read().decode("utf-8", "ignore")
        except Exception:
            err_body = ""
        return e.code, err_body, None
    except Exception as e:
        return None, "", str(e)

def render_message(rule: dict, result: dict) -> str:
    """Generate the alert message, supporting all variables promised by rule-schema"""
    notify = rule["notify"]
    template = notify.get("message_template", "")

    if not template:
        if result.get("metric_type") == "group":
            template = """[Group Alert] {{task_name}}

Project: {{project_name}}
Window: {{window}}
Triggered groups: {{row_count}} / {{total_groups}} (skipped {{miss_groups}} groups: missing baseline / empty value / dirty data; groups with zero events in the window that do not appear in the result are not counted)
Details:
{{data_table}}"""
        elif result.get("metric_type") == "row_filter":
            template = """[List Alert] {{task_name}}

Project: {{project_name}}
Window: {{window}}
Matched rows: {{row_count}}
List:
{{user_list}}"""
        else:
            template = """[Metric Alert] {{task_name}}

Project: {{project_name}}
Window: {{window}}
Current value: {{current_value}}
Baseline value: {{baseline_value}}
Verdict: alert triggered"""

    allowed_vars = MESSAGE_VARS_BY_TYPE.get(result.get("metric_type"))
    if allowed_vars is not None:
        not_applicable = sorted(set(_MESSAGE_VAR_RE.findall(template)) - allowed_vars)
        if not_applicable:
            raise RuntimeError(
                f"message template variable not applicable to "
                f"metric_type={result.get('metric_type')}: {', '.join(not_applicable)}; "
                f"allowed: {', '.join(sorted(allowed_vars))}"
            )

    msg = template
    msg = msg.replace("{{task_name}}", str(rule["task_name"]))
    msg = msg.replace("{{project_name}}", str(rule.get("project_name", "")))
    msg = msg.replace("{{window}}", str(result.get("window", "")))
    msg = msg.replace("{{current_value}}", _render_cell(result.get("current_value")))
    msg = msg.replace("{{baseline_value}}", _render_cell(result.get("baseline_value")))
    msg = msg.replace("{{row_count}}", str(result.get("row_count", "")))
    msg = msg.replace("{{total_groups}}", str(result.get("total_groups", "")))
    msg = msg.replace("{{miss_groups}}", str(result.get("miss_groups", "")))
    msg = msg.replace("{{user_list}}", result.get("user_list", "(no data)"))
    msg = msg.replace("{{data_table}}", result.get("data_table", "(no data)"))

    residue = _PLACEHOLDER_RESIDUE_RE.search(msg)
    if residue:
        raise RuntimeError(f"message template contains unknown variable: {residue.group(0)}")

    return msg


def push_alert(rule: dict, message: str) -> dict:
    """Push the alert. Channels: wecom / dingtalk / feishu / custom_webhook"""
    notify = rule["notify"]
    channel = notify["channel"]

    if channel in ("wecom", "dingtalk", "feishu", "custom_webhook"):
        webhook_url = notify["webhook_url"]

        if channel in ("wecom", "dingtalk"):
            payload = {"msgtype": "text", "text": {"content": message}}
        elif channel == "feishu":
            payload = {"msg_type": "text", "content": {"text": message}}
        else:
            payload = {"text": message}

        data = json.dumps(payload).encode("utf-8")

        # Network-layer failures (connection refused/timeout/read interrupted) are retried up to PUSH_MAX_RETRIES times with exponential backoff
        # (first attempt + 3 retries = 4 attempts, backoff 2s/4s/8s);
        # business-layer rejections (non-zero errcode/code) are deterministic failures and are not retried
        status, body, err = None, "", None
        attempt = 0
        while True:
            attempt += 1
            status, body, err = _post_webhook(webhook_url, data)
            if err is None:
                break
            if attempt <= PUSH_MAX_RETRIES:
                delay = PUSH_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                print(
                    f"WARN: push attempt {attempt}/{PUSH_MAX_RETRIES + 1} failed ({err}), "
                    f"retrying in {delay}s",
                    file=sys.stderr,
                )
                time.sleep(delay)
            else:
                break
        if err is not None:
            return {"status": "error", "error": f"push failed after {PUSH_MAX_RETRIES + 1} attempts: {err}"}

        # HTTP 2xx is required for every channel. Official channels additionally return a business code:
        # WeCom/DingTalk use errcode and Feishu uses code; any non-zero value is a business failure.
        # Official channels (wecom/dingtalk/feishu) must return a JSON body, and a successful response must contain a business code
        # (errcode or code) equal to 0 to count as success -- a response missing the business code (rewritten by a gateway / returned by an
        # abnormal proxy) is treated as failure; non-JSON content such as an HTML error page is likewise treated as failure;
        # custom_webhook is a user-defined endpoint whose response body format is out of our control, so only the HTTP status is used
        # and the body is recorded as-is in run_result for manual review
        if status is None or not 200 <= status < 300:
            return {"status": "error", "error": f"webhook returned HTTP {status}: {body[:300]}"}
        if channel == "custom_webhook":
            return {"status": status, "body": body}
        try:
            resp_json = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return {"status": "error", "error": f"webhook returned non-JSON body: {body[:300]}"}
        if not isinstance(resp_json, dict):
            return {"status": "error", "error": f"webhook returned non-dict JSON body: {body[:300]}"}
        biz_code = resp_json.get("errcode", resp_json.get("code"))
        if biz_code != 0:
            return {"status": "error", "error": f"webhook rejected: {body[:300]}"}
        return {"status": status, "body": body}

    else:
        return {"status": "error", "error": f"unknown channel: {channel}"}


# ---------- Main flow ----------

def evaluate(rule: dict) -> dict:
    """Run the alert evaluation (single-value / group / list)"""
    if "type" not in rule.get("metric", {}):
        raise RuntimeError("alert_rule.json missing metric.type field")
    metric_type = rule["metric"]["type"]
    if metric_type not in VALID_METRIC_TYPES:
        raise RuntimeError(
            f"unknown metric.type: {metric_type} (valid: {', '.join(VALID_METRIC_TYPES)})"
        )
    trigger = rule["trigger"]
    if "compare_to" not in trigger:
        raise RuntimeError("alert_rule.json missing trigger.compare_to field")
    if trigger["operator"] in ("pct_change_gt", "pct_change_lt") and trigger["compare_to"] == "fixed":
        raise RuntimeError(
            f"operator {trigger['operator']} compares against a dynamic baseline; "
            "trigger.compare_to must not be fixed (use previous_period/same_time_yesterday/"
            "same_time_last_week/history_avg/history_max)"
        )
    start, end, target_date = compute_window(rule)
    window_str = f"{start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%Y-%m-%d %H:%M')}"

    sql_template = get_sql_from_rule(rule)
    sql = render_sql(sql_template, start, end, target_date, rule)
    sql_safety_check(sql)
    rows = run_query(sql, rule)
    _collect_dry_run(sql, rows, "main_query", window_str)

    if metric_type == "group":
        # Group monitoring: judged group by group; any hit triggers the alert
        if len(rows) >= PREVIEW_ROWS:
            print(
                f"WARN: main query returned {len(rows)} rows (PREVIEW_ROWS cap reached); "
                "groups beyond the cap are not monitored",
                file=sys.stderr,
            )
        group_result = evaluate_group_rows(rule, rows)
        hit = len(group_result["hit_groups"]) > 0
        result = {
            "task_name": rule["task_name"],
            "window": window_str,
            "target_date": target_date,
            "metric_type": metric_type,
            "total_groups": group_result["total_groups"],
            "hit_groups": group_result["hit_groups"],
            "miss_groups": group_result["miss_groups"],
            "row_count": len(group_result["hit_groups"]),
            "hit": hit,
            "dry_run": DRY_RUN,
        }
        if hit:
            columns = ["group_key", "metric_value"]
            if group_result.get("with_baseline"):
                columns.append("baseline_value")
            result["data_table"] = format_data_table(group_result["hit_groups"], columns)
        return result

    if metric_type == "row_filter":
        # List monitoring: row count > threshold (default 0) triggers; only a fixed baseline is supported
        compare_to = trigger["compare_to"]
        if compare_to != "fixed":
            raise RuntimeError(
                f"row_filter only supports compare_to=fixed, got: {compare_to}"
            )
        if trigger.get("operator") != "gt":
            raise RuntimeError(
                f"row_filter only supports operator=gt, got: {trigger.get('operator')} "
                "(for row counts only 'exceeds threshold' is meaningful; eq is of limited use, and lt would treat an empty list as an alert)"
            )
        row_count = len(rows)
        truncated = row_count >= PREVIEW_ROWS
        if truncated:
            print(
                f"WARN: main query returned {row_count} rows (PREVIEW_ROWS cap reached); "
                "user list is truncated",
                file=sys.stderr,
            )
        hit = check_trigger(rule, float(row_count), None)
        result_columns = rule.get("metric", {}).get("result_columns") or []
        result = {
            "task_name": rule["task_name"],
            "window": window_str,
            "target_date": target_date,
            "metric_type": metric_type,
            "row_count": row_count,
            "hit": hit,
            "dry_run": DRY_RUN,
        }
        if hit:
            user_list = format_user_list(rows, result_columns)
            if truncated:
                user_list += f"\n(matched rows reached the {PREVIEW_ROWS} cap, showing only the first {PREVIEW_ROWS} rows)"
            result["user_list"] = user_list
        return result

    # Single-value metric
    metric_cfg = rule.get("metric", {})
    current_value = _extract_value(rows[0], rule) if rows else None

    # Handling policy when the ratio metric denominator is 0 (metric_value is NULL)
    if current_value is None and rows and metric_cfg.get("type") == "ratio":
        policy = metric_cfg.get("zero_denominator", "skip")
        if policy == "zero":
            current_value = 0.0
        elif policy == "hundred":
            current_value = 1.0
        # skip: keep None, no trigger

    # gt/lt/eq are independent of compare_to (absolute-threshold decisions), so the baseline query is skipped;
    # only pct_change_* needs a baseline
    if rule["trigger"]["operator"] in ("gt", "lt", "eq"):
        baseline_value = None
    else:
        baseline_value = get_baseline_value(rule)
    hit = check_trigger(rule, current_value, baseline_value)
    result = {
        "task_name": rule["task_name"],
        "window": window_str,
        "target_date": target_date,
        "metric_type": metric_type,
        "current_value": current_value,
        "baseline_value": baseline_value,
        "hit": hit,
        "dry_run": DRY_RUN,
    }
    return result


def main():
    if not os.path.exists(SPEC_PATH):
        print(f"alert rule not found: {SPEC_PATH}", file=sys.stderr)
        sys.exit(2)

    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        rule = json.load(f)

    try:
        result = evaluate(rule)
    except Exception as e:
        # On a mid-run failure during the dry-run, also persist the collected rendered_sql/sample_rows,
        # so the config stage can show the user "how far execution got"
        result = {"error": str(e), "hit": False}
        if DRY_RUN:
            result["rendered_sql"] = _DRY_RUN_SQL
            result["sample_rows"] = _DRY_RUN_SAMPLE_ROWS
        with open(RUN_RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Write the result; under DRY_RUN attach the rendered SQL and sample rows (to show dry-run details to the user at config stage)
    if DRY_RUN:
        result["rendered_sql"] = _DRY_RUN_SQL
        result["sample_rows"] = _DRY_RUN_SAMPLE_ROWS
    with open(RUN_RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Output the result
    print(f"Window: {result['window']}")
    if result.get("metric_type") == "group":
        print(f"Groups: {result['total_groups']}, triggered: {result['row_count']}")
    elif result.get("metric_type") == "row_filter":
        print(f"Matched rows: {result['row_count']}")
    else:
        print(f"Current value: {result['current_value']}")
        print(f"Baseline value: {result['baseline_value']}")
    print(f"Verdict: {'alert triggered' if result['hit'] else 'not triggered'}")

    if result["hit"]:
        # On a hit, render the message: the dry-run (DRY_RUN) also renders once to validate the message_template variables,
        # moving template errors left to the config stage so the real run does not traceback right when it hits and drop this alert
        try:
            message = render_message(rule, result)
        except Exception as e:
            result["error"] = f"render message failed: {e}"
            with open(RUN_RESULT_PATH, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"ERROR: render message failed: {e}", file=sys.stderr)
            sys.exit(1)

        if not DRY_RUN:
            with open(ALERT_MESSAGE_PATH, "w", encoding="utf-8") as f:
                f.write(message)

            push_result = push_alert(rule, message)
            result["push"] = push_result
            with open(RUN_RESULT_PATH, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            if push_result.get("status") == "error":
                print(f"PUSH FAILED: {push_result.get('error')}", file=sys.stderr)
                sys.exit(3)
            print(f"Alert pushed: {push_result.get('status')}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
