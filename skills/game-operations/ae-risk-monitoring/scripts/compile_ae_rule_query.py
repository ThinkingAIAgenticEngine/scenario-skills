#!/usr/bin/env python3
"""Compile one safe, batched AE/Trino query for a custom monitoring rule."""

import argparse
import json
import math
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo


ALLOWED_FILTERS = {"eq", "neq", "gt", "gte", "lt", "lte", "contains", "not_contains", "in", "not_in", "is_set", "is_not_set"}
ALLOWED_AGGREGATIONS = {"count", "distinct_users", "sum", "avg", "min", "max"}


def quote_identifier(value):
    value = str(value or "")
    if not value or "\x00" in value:
        raise ValueError("invalid identifier")
    return '"' + value.replace('"', '""') + '"'


def quote_table_ref(value):
    parts = str(value or "").split(".")
    if len(parts) != 3 or any(not re.fullmatch(r"[A-Za-z0-9_]+", part) for part in parts):
        raise ValueError("table_ref must be a verified three-part identifier")
    return ".".join(parts)


def quote_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def numeric_literal(value):
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric filter value: {value}") from exc
    if not math.isfinite(float(number)):
        raise ValueError("numeric filter value must be finite")
    return format(number, "f")


def user_expression(columns):
    if not columns:
        raise ValueError("physical_mapping.user_identifiers is required")
    rendered = []
    for column in columns:
        item = quote_identifier(column)
        rendered.append(f"nullif(cast({item} AS varchar), '')")
    return "coalesce(" + ", ".join(rendered) + ")"


def property_inventory(rule):
    names = list(rule.get("group_by", []))
    for metric in rule.get("metrics", []):
        if metric.get("property"):
            names.append(metric["property"])
        names.extend(item.get("property") for item in metric.get("filters", []) if item.get("property"))
    unique = []
    for name in names:
        name = str(name).strip()
        if name and name not in unique:
            unique.append(name)
    return unique


def compile_filter(condition, column):
    operator = str(condition.get("operator", "")).strip()
    if operator not in ALLOWED_FILTERS:
        raise ValueError(f"unsupported filter operator: {operator}")
    if operator == "is_set":
        return f"{column} IS NOT NULL"
    if operator == "is_not_set":
        return f"{column} IS NULL"
    value = condition.get("value")
    if value in (None, ""):
        raise ValueError(f"filter {operator} requires a value")
    value_type = str(condition.get("value_type") or "string").lower()
    if value_type not in {"string", "number"}:
        raise ValueError(f"unsupported filter value_type: {value_type}")
    if operator in {"gt", "gte", "lt", "lte"}:
        value_type = "number"
    rendered_column = f"try_cast({column} AS double)" if value_type == "number" else f"cast({column} AS varchar)"
    render_value = numeric_literal if value_type == "number" else quote_literal
    if operator in {"eq", "neq", "gt", "gte", "lt", "lte"}:
        symbols = {"eq": "=", "neq": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
        return f"{rendered_column} {symbols[operator]} {render_value(value)}"
    if operator in {"contains", "not_contains"}:
        predicate = f"strpos(cast({column} AS varchar), {quote_literal(value)}) > 0"
        return predicate if operator == "contains" else f"NOT ({predicate})"
    values = [item.strip() for item in str(value).split(",") if item.strip()]
    if not values:
        raise ValueError(f"filter {operator} requires at least one value")
    predicate = f"{rendered_column} IN ({', '.join(render_value(item) for item in values)})"
    return predicate if operator == "in" else f"NOT ({predicate})"


def compile_filters(filters, property_aliases):
    expression = ""
    for index, condition in enumerate(filters or []):
        property_name = str(condition.get("property", "")).strip()
        if property_name not in property_aliases:
            raise ValueError(f"unresolved filter property: {property_name}")
        predicate = compile_filter(condition, f"s.{quote_identifier(property_aliases[property_name])}")
        if index == 0:
            expression = predicate
            continue
        connector = str(condition.get("connector", "AND")).upper()
        if connector not in {"AND", "OR"}:
            raise ValueError("filter connector must be AND or OR")
        expression = f"({expression} {connector} {predicate})"
    return expression


def parse_as_of(value, timezone_name):
    if value:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return datetime.now(ZoneInfo(timezone_name))


def compile_rule_query(config, rule, as_of=None):
    mapping = config["physical_mapping"]
    timezone_name = config.get("timezone", "UTC")
    current = parse_as_of(as_of, timezone_name)
    lateness_seconds = max(0, int(config.get("lateness_seconds", 30)))
    evaluation_end = current - timedelta(seconds=lateness_seconds)
    window_minutes = int(rule.get("window_minutes", 5))
    consecutive_periods = int(rule.get("consecutive_periods", 1))
    if window_minutes < 1 or consecutive_periods < 1 or consecutive_periods > 12:
        raise ValueError("invalid window_minutes or consecutive_periods")
    metrics = rule.get("metrics", [])
    if not metrics:
        raise ValueError("at least one metric is required")
    group_by = [str(item).strip() for item in rule.get("group_by", [])]
    if len(group_by) > 2 or len(set(group_by)) != len(group_by) or any(not item for item in group_by):
        raise ValueError("group_by must contain 0 to 2 unique properties")

    periods = []
    window = timedelta(minutes=window_minutes)
    for index in range(consecutive_periods):
        start = evaluation_end - window * (consecutive_periods - index)
        end = start + window
        periods.append((index, start, end))
    history_start = periods[0][1]

    properties = property_inventory(rule)
    verified = set(mapping.get("verified_properties", properties))
    unresolved = [name for name in properties if name not in verified]
    if unresolved:
        raise ValueError("properties are not metadata-verified: " + ", ".join(unresolved))
    property_aliases = {name: f"property_{index + 1}" for index, name in enumerate(properties)}

    event_names = []
    seen_aliases = set()
    for metric in metrics:
        alias = str(metric.get("alias", "")).strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", alias) or alias in seen_aliases:
            raise ValueError(f"invalid or duplicate metric alias: {alias}")
        seen_aliases.add(alias)
        event_name = str(metric.get("event_name", "")).strip()
        if not event_name:
            raise ValueError(f"metric {alias} requires event_name")
        if event_name not in event_names:
            event_names.append(event_name)

    table = quote_table_ref(mapping["table_ref"])
    event_partition = quote_identifier(mapping["event_partition"])
    date_partition = quote_identifier(mapping["date_partition"])
    event_time = quote_identifier(mapping["event_time"])
    source_columns = [
        f"{event_time} AS event_time",
        f"cast({event_partition} AS varchar) AS event_name",
        f"{user_expression(mapping['user_identifiers'])} AS user_key",
    ]
    source_columns.extend(f"{quote_identifier(name)} AS {quote_identifier(alias)}" for name, alias in property_aliases.items())
    start_sql = history_start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    end_sql = evaluation_end.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    source = (
        "source AS (SELECT " + ", ".join(source_columns)
        + f" FROM {table}"
        + f" WHERE {date_partition} BETWEEN {quote_literal(history_start.strftime('%Y-%m-%d'))} AND {quote_literal(evaluation_end.strftime('%Y-%m-%d'))}"
        + f" AND {event_partition} IN ({', '.join(quote_literal(item) for item in event_names)})"
        + f" AND {event_time} >= TIMESTAMP {quote_literal(start_sql)}"
        + f" AND {event_time} < TIMESTAMP {quote_literal(end_sql)})"
    )
    period_values = ", ".join(
        f"({index}, TIMESTAMP {quote_literal(start.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])}, TIMESTAMP {quote_literal(end.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])})"
        for index, start, end in periods
    )
    periods_cte = f"periods(period_index, period_start, period_end) AS (VALUES {period_values})"

    branches = []
    for metric in metrics:
        alias = str(metric["alias"])
        aggregation = str(metric.get("aggregation", "count"))
        if aggregation not in ALLOWED_AGGREGATIONS:
            raise ValueError(f"unsupported aggregation: {aggregation}")
        property_name = str(metric.get("property", "")).strip()
        if aggregation in {"sum", "avg", "min", "max"} and property_name not in property_aliases:
            raise ValueError(f"metric {alias} requires a verified numeric property")
        if aggregation == "count":
            value_expression = "count(*)"
        elif aggregation == "distinct_users":
            value_expression = "count(DISTINCT s.user_key)"
        else:
            column = f"s.{quote_identifier(property_aliases[property_name])}"
            value_expression = f"{aggregation}(try_cast({column} AS double))"
            if aggregation == "sum":
                value_expression = f"coalesce({value_expression}, 0)"
        filter_sql = compile_filters(metric.get("filters", []), property_aliases)
        where_parts = [f"s.event_name = {quote_literal(metric['event_name'])}"]
        if filter_sql:
            where_parts.append(filter_sql)
        group_columns = [f"s.{quote_identifier(property_aliases[name])}" for name in group_by]
        shown_groups = [f"cast({column} AS varchar) AS group_{index + 1}" for index, column in enumerate(group_columns)]
        shown_groups.extend(f"cast(NULL AS varchar) AS group_{index + 1}" for index in range(len(shown_groups), 2))
        group_clause = ", " + ", ".join(group_columns) if group_columns else ""
        branches.append(
            "SELECT p.period_index, p.period_start, p.period_end, "
            + f"{quote_literal(alias)} AS metric_alias, "
            + ", ".join(shown_groups)
            + f", cast({value_expression} AS double) AS metric_value"
            + ", count(DISTINCT s.user_key) AS affected_users"
            + ", max(s.event_time) AS latest_event_time"
            + ", count(*) AS filtered_event_volume"
            + " FROM periods p JOIN source s ON s.event_time >= p.period_start AND s.event_time < p.period_end"
            + " WHERE " + " AND ".join(f"({item})" for item in where_parts)
            + f" GROUP BY p.period_index, p.period_start, p.period_end{group_clause}"
        )
    sql = "WITH " + source + ", " + periods_cte + " " + " UNION ALL ".join(branches) + " ORDER BY period_index, metric_alias, group_1, group_2"
    return {
        "rule_id": rule.get("id"),
        "evaluation_time": current.isoformat(),
        "watermark": evaluation_end.isoformat(),
        "query_count": 1,
        "period_count": consecutive_periods,
        "metric_count": len(metrics),
        "group_by": group_by,
        "sql": sql,
        "expected_columns": ["period_index", "period_start", "period_end", "metric_alias", "group_1", "group_2", "metric_value", "affected_users", "latest_event_time", "filtered_event_volume"],
    }


def main():
    parser = argparse.ArgumentParser(description="Compile one batched AE custom-rule query")
    parser.add_argument("--config", required=True)
    parser.add_argument("--rule-id", required=True)
    parser.add_argument("--as-of")
    parser.add_argument("--output")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rule = next((item for item in config.get("custom_rules", []) if item.get("id") == args.rule_id), None)
    if not rule:
        raise ValueError(f"rule not found: {args.rule_id}")
    result = compile_rule_query(config, rule, args.as_of)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
