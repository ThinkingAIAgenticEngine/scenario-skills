#!/usr/bin/env python3
"""
Retention-difference calculation script: computes the D1/D7 retention difference between two groups of users who "hit a behavior vs did not hit it".

Purpose: verify whether a new feature / behavior correlates with retention (the A/B-goal core gameplay of version comparison).

Usage:
    python retention_diff.py --project-id 7 --action-event add_friend \
        --reg-start 2026-07-08 --reg-end 2026-07-14 \
        --ret-window 7 --table hive.ta.v_event_7

Notes:
    - Calls ae-cli via Python subprocess to avoid shell escaping of SQL.
    - The reg event defaults to register and the return event defaults to login; both can be overridden via parameters.
    - ACTION means the behavior occurred on the user's registration day, avoiding later behavior leaking into earlier retention labels.
    - Outputs two groups: ACTION (hit) and NO_ACTION (not hit) with total/d1/d7.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date, timedelta


TABLE_REF = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_$]*(?:\.[A-Za-z_][A-Za-z0-9_$]*){0,2}$"
)


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def run_sql(ae_cli, project_id, definition):
    cmd = [ae_cli, "analysis", "adhoc", "run", "-p", str(project_id),
           "--model-type", "sql", "--definition", json.dumps(definition),
           "--preview-rows", "100", "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown ae-cli error"
        raise RuntimeError(detail)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ae-cli returned invalid JSON") from exc
    data = payload.get("data", payload)
    if data.get("has_more"):
        print("WARNING: preview is truncated; use analysis adhoc export for full results",
              file=sys.stderr)
    return data.get("rows", [])


def text_param(name, value):
    return {"name": name, "type": "text", "operator": "eq", "value": value}


def date_param(name, start, end):
    return {
        "name": name,
        "type": "part_date",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "use_timezone": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project-id", type=int, required=True)
    p.add_argument("--action-event", required=True,
                   help="Target behavior event name, e.g. add_friend")
    p.add_argument("--reg-start", type=parse_date, required=True,
                   help="Registration window start YYYY-MM-DD")
    p.add_argument("--reg-end", type=parse_date, required=True,
                   help="Registration window end YYYY-MM-DD")
    p.add_argument("--reg-event", default="register", help="Registration event name, default register")
    p.add_argument("--return-event", default="login", help="Return event name, default login")
    p.add_argument("--ret-window", type=int, default=7, help="Maximum retention days, default 7")
    p.add_argument("--table", default=None, help="Event table, default hive.ta.v_event_<pid>")
    p.add_argument("--ae-cli", default="ae-cli", help="ae-cli executable path")
    args = p.parse_args()

    if args.project_id <= 0:
        p.error("--project-id must be positive")
    if args.reg_start > args.reg_end:
        p.error("--reg-start must be on or before --reg-end")
    if not 2 <= args.ret_window <= 90:
        p.error("--ret-window must be between 2 and 90")
    table = args.table or f"hive.ta.v_event_{args.project_id}"
    if not TABLE_REF.fullmatch(table):
        p.error("--table must be an exact safe table_ref")

    return_start = args.reg_start + timedelta(days=1)
    return_end = args.reg_end + timedelta(days=args.ret_window)
    sql = f'''WITH reg AS (
  SELECT "#user_id", min("$part_date") AS reg_date
  FROM {table}
  WHERE ${{PartDate:reg_window}}
    AND "#event_name" ${{Text:reg_event}}
  GROUP BY "#user_id"
),
action_events AS (
  SELECT "#user_id", "$part_date" AS action_date
  FROM {table}
  WHERE ${{PartDate:action_window}}
    AND "#event_name" ${{Text:action_event}}
),
action_users AS (
  SELECT DISTINCT r."#user_id"
  FROM reg r
  JOIN action_events a ON r."#user_id" = a."#user_id"
  WHERE a.action_date = r.reg_date
),
ret AS (
  SELECT DISTINCT "#user_id", "$part_date" AS d
  FROM {table}
  WHERE ${{PartDate:return_window}}
    AND "#event_name" ${{Text:return_event}}
)
SELECT
  CASE WHEN a."#user_id" IS NOT NULL THEN 'ACTION' ELSE 'NO_ACTION' END AS grp,
  count(DISTINCT r."#user_id") AS total,
  count(DISTINCT CASE WHEN ret.d = CAST(date_add('day', 1, CAST(r.reg_date AS date)) AS varchar) THEN ret."#user_id" END) AS d1,
  count(DISTINCT CASE WHEN ret.d = CAST(date_add('day', {args.ret_window}, CAST(r.reg_date AS date)) AS varchar) THEN ret."#user_id" END) AS d{args.ret_window}
FROM reg r
LEFT JOIN action_users a ON r."#user_id" = a."#user_id"
LEFT JOIN ret ON r."#user_id" = ret."#user_id"
GROUP BY 1'''
    definition = {
        "sql": sql,
        "params": [
            date_param("reg_window", args.reg_start, args.reg_end),
            date_param("action_window", args.reg_start, args.reg_end),
            date_param("return_window", return_start, return_end),
            text_param("reg_event", args.reg_event),
            text_param("action_event", args.action_event),
            text_param("return_event", args.return_event),
        ],
    }
    try:
        rows = run_sql(args.ae_cli, args.project_id, definition)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
