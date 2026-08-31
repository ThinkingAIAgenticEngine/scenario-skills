#!/usr/bin/env python3
"""Evaluate normalized AE events against reusable monitoring rules."""

import argparse
import ast
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


SEVERITY_ORDER = {"HEALTHY": 0, "INFO": 1, "WARNING": 2, "DATA_PIPELINE_SUSPECTED": 3, "CRITICAL": 4}
SUPPORTED_NOTIFICATION_LANGUAGES = {"zh-CN", "en-US"}

MESSAGES = {
    "en-US": {
        "alert_tag": "AE Risk Alert",
        "project": "Project",
        "window": "Window",
        "anomaly": "Anomaly",
        "data_status": "Data status",
        "recommendation": "Recommendation",
        "dedup_key": "Deduplication key",
        "batch_dedup_key": "Batch deduplication key",
        "anomalous_groups": "Anomalous groups",
        "not_set": "(not set)",
        "group": "group",
        "custom_alert": "Custom Alert",
        "count": "event count",
        "distinct_users": "distinct users",
        "sum": "sum",
        "avg": "average",
        "min": "minimum",
        "max": "maximum",
        "filters_applied": " ({count} filter(s) applied)",
        "field_separator": ": ",
    },
    "zh-CN": {
        "alert_tag": "AE \u98ce\u9669\u9884\u8b66",
        "project": "\u9879\u76ee",
        "window": "\u65f6\u95f4\u7a97",
        "anomaly": "\u5f02\u5e38",
        "data_status": "\u6570\u636e\u72b6\u6001",
        "recommendation": "\u5efa\u8bae",
        "dedup_key": "\u53bb\u91cd\u952e",
        "batch_dedup_key": "\u6279\u6b21\u53bb\u91cd\u952e",
        "anomalous_groups": "\u5f02\u5e38\u5206\u7ec4",
        "not_set": "(\u672a\u8bbe\u7f6e)",
        "group": "\u5206\u7ec4",
        "custom_alert": "\u81ea\u5b9a\u4e49\u9884\u8b66",
        "count": "\u4e8b\u4ef6\u6b21\u6570",
        "distinct_users": "\u53bb\u91cd\u7528\u6237\u6570",
        "sum": "\u5408\u8ba1",
        "avg": "\u5e73\u5747\u503c",
        "min": "\u6700\u5c0f\u503c",
        "max": "\u6700\u5927\u503c",
        "filters_applied": " (\u5df2\u5e94\u7528{count}\u6761\u7b5b\u9009)",
        "field_separator": "\uff1a",
    },
}


def notification_language(config):
    language = str(config.get("notification_language", "zh-CN"))
    if language not in SUPPORTED_NOTIFICATION_LANGUAGES:
        raise ValueError("notification_language must be zh-CN or en-US")
    return language


def message(language, key, **values):
    return MESSAGES[language][key].format(**values)


def field(language, key, value):
    return f"{message(language, key)}{message(language, 'field_separator')}{value}"


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate AE risk-monitoring rules")
    parser.add_argument("--input", required=True, help="Normalized event CSV")
    parser.add_argument("--config", required=True, help="Monitoring config JSON")
    parser.add_argument("--output", required=True, help="Output alert JSON")
    parser.add_argument("--state", help="Persistent deduplication state JSON")
    parser.add_argument("--fail-on-alert", action="store_true")
    return parser.parse_args()


def parse_time(value):
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def mask_identifier(value):
    value = str(value or "")
    if not value:
        return ""
    if "." in value and all(part.isdigit() for part in value.split(".") if part):
        parts = value.split(".")
        return ".".join(parts[:3] + ["*"]) if len(parts) == 4 else "***"
    if len(value) <= 4:
        return value[0] + "***"
    return value[:2] + "***" + value[-2:]


def normalize_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"event_time", "event_name", "account_id"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Missing required CSV columns: " + ", ".join(sorted(missing)))
        for line_no, raw in enumerate(reader, start=2):
            try:
                event_time = parse_time(raw["event_time"])
            except Exception as exc:
                raise ValueError(f"Invalid event_time at line {line_no}: {raw.get('event_time')}") from exc
            amount_raw = (raw.get("amount") or "").strip()
            amount = float(amount_raw) if amount_raw else None
            rows.append(
                {
                    "event_time": event_time,
                    "event_name": (raw.get("event_name") or "").strip(),
                    "account_id": (raw.get("account_id") or "").strip(),
                    "ip": (raw.get("ip") or "").strip(),
                    "device_id": (raw.get("device_id") or "").strip(),
                    "amount": amount,
                    "transaction_id": (raw.get("transaction_id") or "").strip(),
                    "status": (raw.get("status") or "").strip().lower(),
                    "properties": {key: (value or "").strip() for key, value in raw.items()},
                }
            )
    return rows


def in_window(row, start, end):
    return start <= row["event_time"] < end


def dedup_key(rule_id, project_id, dimensions, start):
    raw = json.dumps([rule_id, project_id, dimensions, start.isoformat()], sort_keys=True)
    return f"{rule_id}|" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def dedup_group(rule_id, project_id, dimensions):
    raw = json.dumps([rule_id, project_id, dimensions], sort_keys=True)
    return f"{rule_id}|" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def notification(language, severity, title, project, start, end, anomaly, freshness, suggestion, key):
    return "\n".join(
        [
            f"[{severity}][{message(language, 'alert_tag')}] {title}",
            field(language, "project", f"{project['name']} ({project['id']})"),
            field(language, "window", f"{start.isoformat()} – {end.isoformat()}"),
            field(language, "anomaly", anomaly),
            field(language, "data_status", freshness),
            field(language, "recommendation", suggestion),
            field(language, "dedup_key", key),
        ]
    )


def numeric_property(row, property_name):
    value = row.get(property_name)
    if value is None:
        value = row.get("properties", {}).get(property_name)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_property(row, property_name):
    value = row.get(property_name)
    if value is None:
        value = row.get("properties", {}).get(property_name)
    return value


def numeric_filter_value(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare_filter(actual, condition):
    operator = str(condition.get("operator", "")).strip()
    expected = condition.get("value")
    allowed = {"eq", "neq", "gt", "gte", "lt", "lte", "contains", "not_contains", "in", "not_in", "is_set", "is_not_set"}
    if operator not in allowed:
        raise ValueError(f"unsupported filter operator: {operator}")
    is_set = actual not in (None, "")
    if operator == "is_set":
        return is_set
    if operator == "is_not_set":
        return not is_set
    if not is_set or expected in (None, ""):
        return False
    actual_text = str(actual)
    expected_text = str(expected)
    if operator in {"eq", "neq"}:
        value_type = str(condition.get("value_type") or "string").lower()
        if value_type == "number":
            actual_number = numeric_filter_value(actual)
            expected_number = numeric_filter_value(expected)
            if actual_number is None or expected_number is None:
                raise ValueError("numeric equality filter requires numeric values")
            equal = actual_number == expected_number
        elif value_type == "string":
            equal = actual_text == expected_text
        else:
            raise ValueError(f"unsupported filter value_type: {value_type}")
        return equal if operator == "eq" else not equal
    if operator in {"contains", "not_contains"}:
        contains = expected_text in actual_text
        return contains if operator == "contains" else not contains
    if operator in {"in", "not_in"}:
        options = [item.strip() for item in expected_text.split(",") if item.strip()]
        included = any(
            compare_filter(actual, {"operator": "eq", "value": option, "value_type": condition.get("value_type")})
            for option in options
        )
        return included if operator == "in" else not included
    actual_number = numeric_filter_value(actual)
    expected_number = numeric_filter_value(expected)
    if actual_number is None or expected_number is None:
        raise ValueError(f"filter operator {operator} requires numeric values")
    comparisons = {
        "gt": actual_number > expected_number,
        "gte": actual_number >= expected_number,
        "lt": actual_number < expected_number,
        "lte": actual_number <= expected_number,
    }
    return comparisons[operator]


def matches_metric_filters(row, filters):
    result = None
    for index, condition in enumerate(filters or []):
        property_name = str(condition.get("property", "")).strip()
        if not property_name:
            raise ValueError("every metric filter requires a property")
        connector = "AND" if index == 0 else str(condition.get("connector", "AND")).upper()
        if connector not in {"AND", "OR"}:
            raise ValueError("metric filter connector must be AND or OR")
        matched = compare_filter(metric_property(row, property_name), condition)
        result = matched if result is None else (result and matched if connector == "AND" else result or matched)
    return True if result is None else result


def metric_group_key(row, group_by):
    return tuple(None if metric_property(row, name) in (None, "") else str(metric_property(row, name)) for name in group_by)


def select_metric_rows(rows, metric, start, end, group_by=None, group_key=None):
    event_name = str(metric.get("event_name", "")).strip()
    if not event_name:
        raise ValueError("metric event_name is required")
    selected = [
        row
        for row in rows
        if row["event_name"] == event_name
        and in_window(row, start, end)
        and matches_metric_filters(row, metric.get("filters", []))
    ]
    if group_by:
        selected = [row for row in selected if metric_group_key(row, group_by) == group_key]
    return selected


def aggregate_metric(rows, metric, start, end, group_by=None, group_key=None, empty_sum_zero=False):
    event_name = str(metric.get("event_name", "")).strip()
    selected = select_metric_rows(rows, metric, start, end, group_by, group_key)
    aggregation = metric.get("aggregation", "count")
    if aggregation == "count":
        return float(len(selected)), selected
    if aggregation == "distinct_users":
        return float(len({row["account_id"] for row in selected if row["account_id"]})), selected
    if aggregation not in {"sum", "avg", "min", "max"}:
        raise ValueError(f"unsupported aggregation: {aggregation}")
    property_name = str(metric.get("property", "")).strip()
    if not property_name:
        raise ValueError(f"property is required for {aggregation}")
    values = [numeric_property(row, property_name) for row in selected]
    values = [value for value in values if value is not None]
    if not values:
        if aggregation == "sum" and empty_sum_zero:
            return 0.0, selected
        raise ValueError(f"no numeric values for {event_name}.{property_name}")
    if aggregation == "sum":
        return float(sum(values)), selected
    if aggregation == "avg":
        return float(statistics.fmean(values)), selected
    if aggregation == "min":
        return float(min(values)), selected
    return float(max(values)), selected


def evaluate_formula(expression, values):
    operators = {
        ast.Add: lambda left, right: left + right,
        ast.Sub: lambda left, right: left - right,
        ast.Mult: lambda left, right: left * right,
        ast.Div: lambda left, right: left / right,
    }

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return operators[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.Name) and node.id in values:
            return float(values[node.id])
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("formula may contain only metric aliases, numbers, parentheses, and + - * /")

    try:
        return float(visit(ast.parse(expression, mode="eval")))
    except ZeroDivisionError as exc:
        raise ValueError("formula division by zero") from exc
    except SyntaxError as exc:
        raise ValueError("invalid formula syntax") from exc


def compare_value(value, comparator, threshold):
    comparisons = {
        ">": lambda left, right: left > right,
        ">=": lambda left, right: left >= right,
        "<": lambda left, right: left < right,
        "<=": lambda left, right: left <= right,
        "==": lambda left, right: left == right,
        "!=": lambda left, right: left != right,
    }
    if comparator not in comparisons:
        raise ValueError(f"unsupported comparator: {comparator}")
    return comparisons[comparator](value, threshold)


def metric_business_label(metric, language):
    event_name = str(metric.get("event_name", "")).strip()
    aggregation = str(metric.get("aggregation", "count")).strip()
    property_name = str(metric.get("property", "")).strip()
    labels = {key: message(language, key) for key in ("count", "distinct_users", "sum", "avg", "min", "max")}
    suffix = labels.get(aggregation, aggregation)
    subject = f"{event_name}.{property_name}" if property_name else event_name
    filter_count = len(metric.get("filters", []) or [])
    filter_label = message(language, "filters_applied", count=filter_count) if filter_count else ""
    return f"{subject} {suffix}{filter_label}".strip()


def custom_rule_anomaly(rule, metric_values, expression_value, period_results=None, language="zh-CN"):
    title = str(rule.get("name") or rule.get("id") or message(language, "custom_alert"))
    window_minutes = int(rule.get("window_minutes", 5))
    comparator = str(rule.get("comparator", ">="))
    threshold = float(rule.get("threshold"))
    comparator_text = {">=": "≥", "<=": "≤", "==": "=", "!=": "≠"}.get(comparator, comparator)
    metrics = rule.get("metrics", [])
    details = []
    for metric in metrics:
        alias = str(metric.get("alias", "")).strip()
        if alias in metric_values:
            if language == "zh-CN":
                details.append(f"{metric_business_label(metric, language)}\u4e3a {metric_values[alias]:g}")
            else:
                details.append(f"{metric_business_label(metric, language)} was {metric_values[alias]:g}")
    detail_text = ("\uff0c" if language == "zh-CN" else ", ").join(details)
    expression = str(rule.get("expression", "")).strip()
    consecutive_periods = int(rule.get("consecutive_periods", 1))
    if consecutive_periods > 1 and period_results:
        values_text = ("\u3001" if language == "zh-CN" else ", ").join(f"{period['value']:g}" for period in period_results)
        if len(metrics) == 1 and expression == str(metrics[0].get("alias", "")).strip():
            if language == "zh-CN":
                return f"\u5ba2\u6237\u89c4\u5219\u201c{title}\u201d\u89e6\u53d1\uff1a\u8fde\u7eed{consecutive_periods}\u4e2a{window_minutes}\u5206\u949f\u5468\u671f\u5185 {metric_business_label(metrics[0], language)}\u5747\u6ee1\u8db3\u9884\u8b66\u6761\u4ef6 {comparator_text} {threshold:g}\uff08\u5404\u5468\u671f\uff1a{values_text}\uff09"
            return f"Customer rule \"{title}\" triggered: {metric_business_label(metrics[0], language)} met the alert condition {comparator_text} {threshold:g} in {consecutive_periods} consecutive {window_minutes}-minute periods (period values: {values_text})"
        if language == "zh-CN":
            return f"\u5ba2\u6237\u89c4\u5219\u201c{title}\u201d\u89e6\u53d1\uff1a\u8fde\u7eed{consecutive_periods}\u4e2a{window_minutes}\u5206\u949f\u5468\u671f\u7684\u7ec4\u5408\u8ba1\u7b97\u7ed3\u679c\u5747\u6ee1\u8db3\u9884\u8b66\u6761\u4ef6 {comparator_text} {threshold:g}\uff08\u5404\u5468\u671f\uff1a{values_text}\uff1b\u6700\u65b0\u5468\u671f {detail_text}\uff09"
        return f"Customer rule \"{title}\" triggered: the combined result met the alert condition {comparator_text} {threshold:g} in {consecutive_periods} consecutive {window_minutes}-minute periods (period values: {values_text}; latest period: {detail_text})"
    if len(metrics) == 1 and expression == str(metrics[0].get("alias", "")).strip():
        if language == "zh-CN":
            return f"\u5ba2\u6237\u89c4\u5219\u201c{title}\u201d\u89e6\u53d1\uff1a{window_minutes}\u5206\u949f\u5185 {detail_text}\uff0c\u9884\u8b66\u6761\u4ef6 {comparator_text} {threshold:g}"
        return f"Customer rule \"{title}\" triggered: within {window_minutes} minutes, {detail_text}; alert condition {comparator_text} {threshold:g}"
    if language == "zh-CN":
        return f"\u5ba2\u6237\u89c4\u5219\u201c{title}\u201d\u89e6\u53d1\uff1a{window_minutes}\u5206\u949f\u5185 {detail_text}\uff1b\u7ec4\u5408\u8ba1\u7b97\u7ed3\u679c\u4e3a {expression_value:g}\uff0c\u9884\u8b66\u6761\u4ef6 {comparator_text} {threshold:g}"
    return f"Customer rule \"{title}\" triggered: within {window_minutes} minutes, {detail_text}; combined result was {expression_value:g}; alert condition {comparator_text} {threshold:g}"


def add_ip_burst_alerts(rows, config, project, as_of, alerts, diagnostics, privacy, language):
    rule = config.get("rules", {}).get("ip_account_burst", {})
    if not rule.get("enabled", False):
        return
    window = timedelta(minutes=int(rule.get("window_minutes", 5)))
    start = as_of - window
    threshold = int(rule.get("distinct_accounts", 10))
    critical = int(rule.get("critical_accounts", 25))
    cooldown = int(rule.get("cooldown_minutes", 30))
    event_names = config.get("event_names", {})
    for group in rule.get("event_groups", ["login", "register"]):
        names = set(event_names.get(group, []))
        if not names:
            diagnostics.append(f"ip_account_burst skipped group {group}: no event names configured")
            continue
        grouped = defaultdict(list)
        for row in rows:
            if row["event_name"] in names and row["ip"] and in_window(row, start, as_of):
                grouped[row["ip"]].append(row)
        for ip, found in grouped.items():
            accounts = sorted({row["account_id"] for row in found if row["account_id"]})
            if len(accounts) < threshold:
                continue
            devices = {row["device_id"] for row in found if row["device_id"]}
            severity = "CRITICAL" if len(accounts) >= critical else "WARNING"
            shown_ip = mask_identifier(ip) if privacy else ip
            dimensions = {"ip": shown_ip, "event_group": group}
            key = dedup_key("ip_account_burst", project["id"], dimensions, start)
            if language == "zh-CN":
                title = "\u540cIP\u591a\u8d26\u53f7\u6ce8\u518c" if group == "register" else "\u540cIP\u591a\u8d26\u53f7\u767b\u5f55"
                anomaly = f"IP {shown_ip} \u5173\u8054 {len(accounts)} \u4e2a\u8d26\u53f7\u3001{len(devices)} \u53f0\u8bbe\u5907\uff1b\u9608\u503c >={threshold}"
                freshness = "\u4e8b\u4ef6\u6837\u672c\u53ef\u7528\uff1b\u4ecd\u9700\u7ed3\u5408 AE \u63a5\u5165\u76d1\u63a7\u786e\u8ba4\u94fe\u8def\u65b0\u9c9c\u5ea6"
                suggestion = "\u6838\u67e5\u9a8c\u8bc1\u7801\u3001\u8bbe\u5907\u6307\u7eb9\u3001\u6e20\u9053\u4e0eIP\u767d\u540d\u5355\uff1b\u6682\u4e0d\u81ea\u52a8\u5c01\u7981"
            else:
                title = "Multi-account Registration from One IP" if group == "register" else "Multi-account Login from One IP"
                anomaly = f"IP {shown_ip} was associated with {len(accounts)} accounts across {len(devices)} devices; threshold >={threshold}"
                freshness = "Event samples are available; confirm ingestion freshness with AE integration monitoring"
                suggestion = "Investigate CAPTCHA results, device fingerprints, channels, and the IP allowlist; do not automatically block accounts"
            alerts.append(
                {
                    "rule_id": "ip_account_burst",
                    "severity": severity,
                    "title": title,
                    "window": {"start": start.isoformat(), "end": as_of.isoformat()},
                    "observed": {"distinct_accounts": len(accounts), "distinct_devices": len(devices)},
                    "threshold": {"distinct_accounts": threshold, "critical_accounts": critical},
                    "dimensions": dimensions,
                    "sample_accounts": [mask_identifier(item) if privacy else item for item in accounts[:5]],
                    "dedup_key": key,
                    "dedup_group": dedup_group("ip_account_burst", project["id"], dimensions),
                    "cooldown_minutes": cooldown,
                    "notification": notification(
                        language,
                        severity,
                        title,
                        project,
                        start,
                        as_of,
                        anomaly,
                        freshness,
                        suggestion,
                        key,
                    ),
                }
            )


def add_login_drop_alert(rows, config, project, as_of, alerts, diagnostics, language):
    rule = config.get("rules", {}).get("login_silence_or_drop", {})
    if not rule.get("enabled", False):
        return
    names = set(config.get("event_names", {}).get("login", []))
    if not names:
        diagnostics.append("login_silence_or_drop skipped: no login event names configured")
        return
    minutes = int(rule.get("window_minutes", 5))
    baseline_windows = int(rule.get("baseline_windows", 12))
    consecutive = max(1, int(rule.get("consecutive_windows", 2)))
    window = timedelta(minutes=minutes)
    current_start = as_of - window * consecutive
    current_counts = []
    for index in reversed(range(consecutive)):
        start = as_of - window * (index + 1)
        end = as_of - window * index
        current_counts.append(len({r["account_id"] for r in rows if r["event_name"] in names and in_window(r, start, end)}))
    baseline_counts = []
    for index in range(baseline_windows):
        end = current_start - window * index
        start = end - window
        baseline_counts.append(len({r["account_id"] for r in rows if r["event_name"] in names and in_window(r, start, end)}))
    baseline = statistics.median(baseline_counts) if baseline_counts else 0
    current = statistics.fmean(current_counts)
    minimum = float(rule.get("minimum_baseline", 20))
    drop_threshold = float(rule.get("drop_ratio", 0.7))
    cooldown = int(rule.get("cooldown_minutes", 20))
    drop_ratio = 1.0 - current / max(baseline, 1)
    if baseline < minimum or not (all(value == 0 for value in current_counts) or drop_ratio >= drop_threshold):
        return
    recent_any = any(in_window(row, current_start, as_of) for row in rows)
    pipeline_suspected = not recent_any
    severity = "DATA_PIPELINE_SUSPECTED" if pipeline_suspected else ("CRITICAL" if all(value == 0 for value in current_counts) else "WARNING")
    dimensions = {"scope": "all"}
    key = dedup_key("login_silence_or_drop", project["id"], dimensions, current_start)
    if language == "zh-CN":
        title = "\u767b\u5f55\u91cf\u5f52\u96f6\u6216\u65ad\u5d16\u4e0b\u964d"
        anomaly = f"\u5f53\u524d\u6bcf\u7a97\u5e73\u5747 {current:.1f} \u4e2a\u767b\u5f55\u8d26\u53f7\uff0c\u57fa\u7ebf\u4e2d\u4f4d\u6570 {baseline:.1f}\uff0c\u4e0b\u964d {drop_ratio:.1%}"
        freshness = "\u5f53\u524d\u7a97\u53e3\u5168\u90e8\u4e8b\u4ef6\u4e3a\u7a7a\uff0c\u7591\u4f3c\u6570\u636e\u94fe\u8def\u4e2d\u65ad" if pipeline_suspected else "\u5176\u4ed6\u4e8b\u4ef6\u4ecd\u6709\u6570\u636e\uff0c\u767b\u5f55\u94fe\u8def\u5f02\u5e38\u53ef\u80fd\u6027\u8f83\u9ad8"
        suggestion = "\u5148\u68c0\u67e5\u63a5\u5165\u5ef6\u8fdf\u548c\u767b\u5f55\u670d\u52a1\uff0c\u518d\u6309\u6e20\u9053\u3001\u5730\u533a\u3001\u7248\u672c\u4e0b\u94bb"
    else:
        title = "Login Volume Reached Zero or Dropped Sharply"
        anomaly = f"Current average was {current:.1f} login accounts per window versus a baseline median of {baseline:.1f}, a {drop_ratio:.1%} decrease"
        freshness = "All events are absent from the current window; a data pipeline interruption is suspected" if pipeline_suspected else "Other events are still present; a login-path anomaly is more likely"
        suggestion = "Check ingestion lag and the login service first, then drill down by channel, region, and version"
    alerts.append(
        {
            "rule_id": "login_silence_or_drop",
            "severity": severity,
            "title": title,
            "window": {"start": current_start.isoformat(), "end": as_of.isoformat()},
            "observed": {"current_average": current, "current_windows": current_counts, "drop_ratio": drop_ratio},
            "threshold": {"baseline_median": baseline, "minimum_baseline": minimum, "drop_ratio": drop_threshold},
            "dimensions": dimensions,
            "sample_accounts": [],
            "dedup_key": key,
            "dedup_group": dedup_group("login_silence_or_drop", project["id"], dimensions),
            "cooldown_minutes": cooldown,
            "notification": notification(
                language,
                severity,
                title,
                project,
                current_start,
                as_of,
                anomaly,
                freshness,
                suggestion,
                key,
            ),
        }
    )


def add_withdrawal_alerts(rows, config, project, as_of, alerts, diagnostics, privacy, language):
    rule = config.get("rules", {}).get("withdrawal_activity", {})
    if not rule.get("enabled", False):
        return
    names = set(config.get("event_names", {}).get("withdrawal", []))
    if not names:
        diagnostics.append("withdrawal_activity skipped: no withdrawal event names configured")
        return
    start = as_of - timedelta(minutes=int(rule.get("window_minutes", 10)))
    success = {str(item).lower() for item in rule.get("success_statuses", ["success"])}
    found = [r for r in rows if r["event_name"] in names and in_window(r, start, as_of) and (not success or r["status"] in success)]
    if not found:
        return
    high_amount = float(rule.get("high_amount", 1000))
    account_frequency = int(rule.get("account_frequency", 3))
    shared_threshold = int(rule.get("shared_origin_accounts", 3))
    cooldown = int(rule.get("cooldown_minutes", 10))
    by_account = defaultdict(list)
    by_origin = defaultdict(set)
    for row in found:
        by_account[row["account_id"]].append(row)
        origin = row["device_id"] or row["ip"]
        if origin:
            by_origin[origin].add(row["account_id"])
    max_amount = max((r["amount"] or 0.0) for r in found)
    max_frequency = max(len(items) for items in by_account.values())
    max_shared = max((len(items) for items in by_origin.values()), default=0)
    critical = max_amount >= high_amount or max_frequency >= account_frequency or max_shared >= shared_threshold
    if not rule.get("notify_any", True) and not critical:
        return
    severity = "CRITICAL" if critical else "WARNING"
    unique_transactions = {r["transaction_id"] for r in found if r["transaction_id"]}
    dimensions = {"scope": "withdrawal"}
    key_basis = sorted(unique_transactions) if unique_transactions else [start.isoformat(), str(len(found))]
    key = "withdrawal_activity|" + hashlib.sha256(json.dumps(key_basis).encode()).hexdigest()[:16]
    accounts = sorted(by_account)
    if language == "zh-CN":
        title = "\u63d0\u73b0\u64cd\u4f5c\u9884\u8b66"
        anomaly = f"\u68c0\u6d4b\u5230 {len(found)} \u7b14\u6210\u529f\u63d0\u73b0\u3001{len(accounts)} \u4e2a\u8d26\u53f7\uff1b\u6700\u9ad8\u91d1\u989d {max_amount:g}\uff1b\u5355\u8d26\u53f7\u6700\u9ad8 {max_frequency} \u7b14"
        freshness = "\u63d0\u73b0\u4e8b\u4ef6\u6570\u636e\u53ef\u7528\uff1b\u9700\u7ed3\u5408 AE \u63a5\u5165\u76d1\u63a7\u786e\u8ba4\u5b8c\u6574\u6027"
        suggestion = "\u6838\u5bf9\u4ea4\u6613\u72b6\u6001\u3001\u8d26\u53f7\u5386\u53f2\u3001\u8bbe\u5907/IP\u5173\u8054\u548c\u98ce\u63a7\u5ba1\u6279\uff1b\u4e0d\u81ea\u52a8\u51bb\u7ed3\u6216\u62d2\u7edd"
    else:
        title = "Withdrawal Activity Alert"
        anomaly = f"Detected {len(found)} successful withdrawals across {len(accounts)} accounts; maximum amount {max_amount:g}; maximum {max_frequency} withdrawals for one account"
        freshness = "Withdrawal event data is available; confirm completeness with AE integration monitoring"
        suggestion = "Review transaction status, account history, device/IP relationships, and risk approvals; do not automatically freeze or reject transactions"
    alerts.append(
        {
            "rule_id": "withdrawal_activity",
            "severity": severity,
            "title": title,
            "window": {"start": start.isoformat(), "end": as_of.isoformat()},
            "observed": {"transactions": len(found), "accounts": len(accounts), "max_amount": max_amount, "max_account_frequency": max_frequency, "max_shared_origin_accounts": max_shared},
            "threshold": {"high_amount": high_amount, "account_frequency": account_frequency, "shared_origin_accounts": shared_threshold},
            "dimensions": dimensions,
            "sample_accounts": [mask_identifier(item) if privacy else item for item in accounts[:5]],
            "dedup_key": key,
            "dedup_group": key,
            "cooldown_minutes": cooldown,
            "notification": notification(
                language,
                severity,
                title,
                project,
                start,
                as_of,
                anomaly,
                freshness,
                suggestion,
                key,
            ),
        }
    )


def add_custom_rule_alerts(rows, config, project, as_of, alerts, diagnostics, privacy, language):
    for index, rule in enumerate(config.get("custom_rules", []), start=1):
        if not rule.get("enabled", True):
            continue
        rule_id = str(rule.get("id") or f"custom_rule_{index}")
        title = str(rule.get("name") or rule_id)
        try:
            window_minutes = int(rule.get("window_minutes", 5))
            if window_minutes <= 0:
                raise ValueError("window_minutes must be positive")
            consecutive_periods = int(rule.get("consecutive_periods", 1))
            if consecutive_periods < 1 or consecutive_periods > 12:
                raise ValueError("consecutive_periods must be between 1 and 12")
            window = timedelta(minutes=window_minutes)
            start = as_of - window * consecutive_periods
            expression = str(rule.get("expression", "")).strip()
            comparator = str(rule.get("comparator", ">="))
            threshold = float(rule.get("threshold"))
            metrics = rule.get("metrics", [])
            aliases = []
            for metric in metrics:
                alias = str(metric.get("alias", "")).strip()
                if not alias or not alias.isidentifier():
                    raise ValueError("every metric requires a valid alias")
                if alias in aliases:
                    raise ValueError(f"duplicate metric alias: {alias}")
                aliases.append(alias)
            if not metrics:
                raise ValueError("at least one metric is required")
            evaluate_formula(expression, {alias: 1.0 for alias in aliases})
            group_by = [str(item).strip() for item in rule.get("group_by", [])]
            if any(not item for item in group_by) or len(group_by) > 2 or len(set(group_by)) != len(group_by):
                raise ValueError("group_by must contain 0 to 2 unique non-empty properties")
            max_groups = int(rule.get("max_groups", 50))
            notification_group_limit = int(rule.get("notification_group_limit", 5))
            if max_groups < 1 or max_groups > 200:
                raise ValueError("max_groups must be between 1 and 200")
            if notification_group_limit < 1 or notification_group_limit > 5:
                raise ValueError("notification_group_limit must be between 1 and 5")
            severity = str(rule.get("severity", "WARNING")).upper()
            if severity not in SEVERITY_ORDER or severity == "HEALTHY":
                raise ValueError(f"unsupported severity: {severity}")
            cooldown = int(rule.get("cooldown_minutes", config.get("default_cooldown_minutes", 30)))
        except (TypeError, ValueError) as exc:
            diagnostics.append(f"custom rule {rule_id} skipped: {exc}")
            continue

        if group_by:
            group_counts = defaultdict(int)
            for period_offset in reversed(range(consecutive_periods)):
                period_start = as_of - window * (period_offset + 1)
                period_end = as_of - window * period_offset
                for metric in metrics:
                    for row in select_metric_rows(rows, metric, period_start, period_end):
                        group_counts[metric_group_key(row, group_by)] += 1
            ordered_groups = sorted(group_counts, key=lambda item: (-group_counts[item], tuple("" if value is None else value for value in item)))
            if len(ordered_groups) > max_groups:
                diagnostics.append(f"custom rule {rule_id}: limited {len(ordered_groups)} groups to top {max_groups} by filtered event volume")
            group_keys = ordered_groups[:max_groups]
        else:
            group_keys = [()]

        matched_groups = []
        for group_key in group_keys:
            matched_rows = []
            period_results = []
            try:
                for period_offset in reversed(range(consecutive_periods)):
                    period_start = as_of - window * (period_offset + 1)
                    period_end = as_of - window * period_offset
                    period_metric_values = {}
                    for metric in metrics:
                        alias = str(metric.get("alias", "")).strip()
                        value, selected = aggregate_metric(rows, metric, period_start, period_end, group_by, group_key, empty_sum_zero=bool(group_by))
                        period_metric_values[alias] = value
                        matched_rows.extend(selected)
                    period_value = evaluate_formula(expression, period_metric_values)
                    period_results.append(
                        {
                            "start": period_start.isoformat(),
                            "end": period_end.isoformat(),
                            "metrics": period_metric_values,
                            "value": period_value,
                            "matched": compare_value(period_value, comparator, threshold),
                        }
                    )
            except (TypeError, ValueError) as exc:
                diagnostics.append(f"custom rule {rule_id} group {dict(zip(group_by, group_key))} skipped: {exc}")
                continue
            if all(period["matched"] for period in period_results):
                matched_groups.append(
                    {
                        "group_key": group_key,
                        "matched_rows": matched_rows,
                        "period_results": period_results,
                        "metric_values": period_results[-1]["metrics"],
                        "expression_value": period_results[-1]["value"],
                        "violation_score": abs(period_results[-1]["value"] - threshold),
                    }
                )

        matched_groups.sort(key=lambda item: (-item["violation_score"], tuple("" if value is None else value for value in item["group_key"])))
        total_matched_groups = len(matched_groups)
        if group_by and total_matched_groups > notification_group_limit:
            diagnostics.append(f"custom rule {rule_id}: limited {total_matched_groups} matched groups to {notification_group_limit} notifications")
        shown_groups = matched_groups[:notification_group_limit] if group_by else matched_groups
        for rank, candidate in enumerate(shown_groups, start=1):
            raw_dimensions = {"custom_rule": rule_id, **dict(zip(group_by, candidate["group_key"]))}
            shown_dimensions = {"custom_rule": rule_id}
            for property_name, value in zip(group_by, candidate["group_key"]):
                text_value = message(language, "not_set") if value is None else str(value)
                sensitive = any(token in property_name.lower() for token in ("ip", "account", "user", "device", "bank", "card"))
                shown_dimensions[property_name] = mask_identifier(text_value) if privacy and sensitive else text_value
            key = dedup_key(rule_id, project["id"], raw_dimensions, start)
            accounts = sorted({row["account_id"] for row in candidate["matched_rows"] if row["account_id"]})
            anomaly = custom_rule_anomaly(rule, candidate["metric_values"], candidate["expression_value"], candidate["period_results"], language)
            if group_by:
                separator = "\uff0c" if language == "zh-CN" else ", "
                anomaly += ("\uff1b" if language == "zh-CN" else "; ") + field(language, "group", separator.join(f"{name}={shown_dimensions[name]}" for name in group_by))
            if language == "zh-CN":
                freshness = "\u81ea\u5b9a\u4e49\u89c4\u5219\u6240\u9700\u4e8b\u4ef6\u6837\u672c\u53ef\u7528\uff1b\u4ecd\u9700\u7ed3\u5408\u63a5\u5165\u76d1\u63a7\u786e\u8ba4\u5b8c\u6574\u6027"
                suggestion = "\u6838\u67e5\u5f02\u5e38\u5206\u7ec4\u3001\u7ec4\u6210\u6307\u6807\u53ca\u76f8\u5173\u4e8b\u4ef6\u660e\u7ec6\uff1b\u4e0d\u81ea\u52a8\u6267\u884c\u5904\u7f6e"
            else:
                freshness = "The custom rule's event samples are available; confirm completeness with integration monitoring"
                suggestion = "Investigate the anomalous group, component metrics, and related event details; do not take automatic action"
            alerts.append(
                {
                    "rule_id": rule_id,
                    "severity": severity,
                    "title": title,
                    "window": {"start": start.isoformat(), "end": as_of.isoformat()},
                    "observed": {
                        "metrics": candidate["metric_values"],
                        "expression": expression,
                        "value": candidate["expression_value"],
                        "consecutive_periods": consecutive_periods,
                        "period_results": candidate["period_results"],
                        "group_rank": rank,
                        "matched_group_count": total_matched_groups,
                    },
                    "threshold": {"comparator": comparator, "value": threshold},
                    "dimensions": shown_dimensions,
                    "sample_accounts": [mask_identifier(item) if privacy else item for item in accounts[:5]],
                    "dedup_key": key,
                    "dedup_group": dedup_group(rule_id, project["id"], raw_dimensions),
                    "cooldown_minutes": cooldown,
                    "notification": notification(
                        language,
                        severity,
                        title,
                        project,
                        start,
                        as_of,
                        anomaly,
                        freshness,
                        suggestion,
                        key,
                    ),
                }
            )


def apply_deduplication(alerts, state_path, as_of):
    if not state_path:
        return alerts, []
    path = Path(state_path)
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        state = {"version": 1, "records": {}}
    records = state.setdefault("records", {})
    emitted, suppressed = [], []
    for alert in alerts:
        group = alert["dedup_group"]
        previous = records.get(group)
        suppress = False
        reason = None
        if previous:
            last_sent = parse_time(previous["sent_at"])
            elapsed = as_of - last_sent
            cooldown = timedelta(minutes=int(alert.get("cooldown_minutes", 0)))
            previous_rank = SEVERITY_ORDER.get(previous.get("severity"), 0)
            current_rank = SEVERITY_ORDER.get(alert.get("severity"), 0)
            if elapsed < cooldown and current_rank <= previous_rank:
                suppress = True
                reason = "within_cooldown_without_severity_escalation"
        if suppress:
            suppressed.append({**alert, "suppression_reason": reason})
            continue
        emitted.append(alert)
        records[group] = {
            "dedup_key": alert["dedup_key"],
            "severity": alert["severity"],
            "sent_at": as_of.isoformat(),
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return emitted, suppressed


def build_notification_batches(alerts, project, language):
    """Batch same-rule group alerts while preserving per-group deduplication."""
    grouped = defaultdict(list)
    for alert in alerts:
        key = (
            alert["rule_id"],
            alert["severity"],
            alert["title"],
            alert["window"]["start"],
            alert["window"]["end"],
        )
        grouped[key].append(alert)
    batches = []
    for (rule_id, severity, title, start, end), items in grouped.items():
        if len(items) == 1:
            rendered_notification = items[0]["notification"]
        else:
            anomaly_lines = []
            anomaly_prefix = message(language, "anomaly") + message(language, "field_separator")
            for index, item in enumerate(items[:5], start=1):
                anomaly = next(
                    (line.removeprefix(anomaly_prefix) for line in item["notification"].splitlines() if line.startswith(anomaly_prefix)),
                    item["title"],
                )
                anomaly_lines.append(f"{index}. {anomaly}")
            batch_key = "batch|" + hashlib.sha256(
                json.dumps(sorted(item["dedup_key"] for item in items), ensure_ascii=False).encode()
            ).hexdigest()[:16]
            if language == "zh-CN":
                batch_title = f"{title} ({len(items)}\u4e2a\u5f02\u5e38\u5206\u7ec4)"
                freshness = "\u5206\u7ec4\u89c4\u5219\u6240\u9700\u4e8b\u4ef6\u6837\u672c\u53ef\u7528\uff1b\u4ecd\u9700\u7ed3\u5408\u63a5\u5165\u76d1\u63a7\u786e\u8ba4\u5b8c\u6574\u6027"
                suggestion = "\u4f18\u5148\u6838\u67e5\u6700\u4e25\u91cd\u5206\u7ec4\u53ca\u76f8\u5173\u4e8b\u4ef6\u660e\u7ec6\uff1b\u4e0d\u81ea\u52a8\u6267\u884c\u5904\u7f6e"
            else:
                batch_title = f"{title} ({len(items)} anomalous groups)"
                freshness = "Grouped-rule event samples are available; confirm completeness with integration monitoring"
                suggestion = "Investigate the most severe groups and related event details first; do not take automatic action"
            message_text = [
                f"[{severity}][{message(language, 'alert_tag')}] {batch_title}",
                field(language, "project", f"{project['name']} ({project['id']})"),
                field(language, "window", f"{start} – {end}"),
                field(language, "anomalous_groups", ""),
                *anomaly_lines,
                field(language, "data_status", freshness),
                field(language, "recommendation", suggestion),
                field(language, "batch_dedup_key", batch_key),
            ]
            rendered_notification = "\n".join(message_text)
        batches.append(
            {
                "rule_id": rule_id,
                "severity": severity,
                "alert_count": len(items),
                "alert_dedup_keys": [item["dedup_key"] for item in items],
                "notification": rendered_notification,
            }
        )
    return sorted(batches, key=lambda item: (-SEVERITY_ORDER[item["severity"]], item["rule_id"]))


def main():
    args = parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rows = normalize_rows(args.input)
    if not rows:
        raise ValueError("Input CSV contains no events")
    as_of = parse_time(config["as_of"]) if config.get("as_of") else max(row["event_time"] for row in rows)
    project = {"id": config.get("project_id"), "name": config.get("project_name", "Unknown")}
    privacy = config.get("privacy", {}).get("mask_identifiers", True)
    language = notification_language(config)
    alerts, diagnostics = [], []
    add_ip_burst_alerts(rows, config, project, as_of, alerts, diagnostics, privacy, language)
    add_login_drop_alert(rows, config, project, as_of, alerts, diagnostics, language)
    add_withdrawal_alerts(rows, config, project, as_of, alerts, diagnostics, privacy, language)
    add_custom_rule_alerts(rows, config, project, as_of, alerts, diagnostics, privacy, language)
    alerts.sort(key=lambda item: (-SEVERITY_ORDER[item["severity"]], item["rule_id"], item["dedup_key"]))
    candidate_alerts = len(alerts)
    candidate_status = max((item["severity"] for item in alerts), key=lambda item: SEVERITY_ORDER[item], default="HEALTHY")
    alerts, suppressed = apply_deduplication(alerts, args.state, as_of)
    status = candidate_status
    result = {
        "status": status,
        "evaluated_at": as_of.isoformat(),
        "project": project,
        "notification_language": language,
        "input_events": len(rows),
        "candidate_alerts": candidate_alerts,
        "alerts": alerts,
        "notification_batches": build_notification_batches(alerts, project, language),
        "suppressed": suppressed,
        "diagnostics": diagnostics,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "alerts": len(alerts), "suppressed": len(suppressed), "diagnostics": len(diagnostics)}, ensure_ascii=False))
    if args.fail_on_alert and alerts:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
