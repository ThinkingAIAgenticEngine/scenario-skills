#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 0/1 gate - parameter and window validation.

This is the guard that stops the run before it spends API calls on an
underspecified request. Everything in here is a rule an agent could forget:
mode/id consistency, date format, minimum window length, required B-mode
events. Keeping it in code means the answer is always the same.

Usage:
    python3 validate_params.py --project-id 61 --mode A --task-id 0822
    python3 validate_params.py --project-id 61 --mode B \\
        --click-event ops_click --start-time 2026-08-01 --end-time 2026-09-14 \\
        --out tmp/params.json

Exit codes:
  0  SUCCESS / EMPTY (soft warnings only)
  1  FATAL   (a required parameter is missing or malformed)
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402

MIN_WINDOW_DAYS = 3
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def parse_date(value):
    if not value:
        return None
    s = _ae.norm_date(value)
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description="Validate skill parameters")
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--mode", required=True, choices=["A", "B"])
    ap.add_argument("--task-id", default=None)
    ap.add_argument("--flow-id", default=None)
    ap.add_argument("--config-id", default=None)
    ap.add_argument("--click-event", default=None)
    ap.add_argument("--anchor-event", default=None)
    ap.add_argument("--conversion-event", default=None)
    ap.add_argument("--start-time", default=None)
    ap.add_argument("--end-time", default=None)
    ap.add_argument("--window-value", type=int, default=24)
    ap.add_argument("--window-unit", default="hour",
                    choices=["hour", "day", "minute"])
    ap.add_argument("--strategy-name", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    checks = []
    fatal, warn = [], []

    def add(name, ok, message, soft=False):
        status = "SUCCESS" if ok else ("EMPTY" if soft else "FATAL")
        checks.append({"check": name, "status": status, "message": message})
        if not ok:
            (warn if soft else fatal).append(name)

    # --- project id -------------------------------------------------------
    add("project_id", bool(PROJECT_ID_RE.match(str(args.project_id))),
        "project_id=%s" % args.project_id if PROJECT_ID_RE.match(str(args.project_id))
        else "project_id '%s' is not a valid identifier" % args.project_id)

    # --- mode / object consistency ---------------------------------------
    ids = [k for k, v in (("task_id", args.task_id), ("flow_id", args.flow_id),
                          ("config_id", args.config_id)) if v]
    if args.mode == "A":
        add("native_object", len(ids) == 1,
            "exactly one of task_id/flow_id/config_id required for mode A (got %s)" % (ids or "none"))
    else:
        add("no_native_object", not ids,
            "mode B must not carry a native object id (got %s)" % ids if ids
            else "mode B carries no native object id", soft=True)
        add("click_event", bool(args.click_event),
            "click/open event name is required for mode B: without it the "
            "conversion path cannot be observed")

    # --- date window ------------------------------------------------------
    start, end = parse_date(args.start_time), parse_date(args.end_time)
    if args.start_time and start is None:
        add("start_time_format", False,
            "start_time '%s' is not parseable (use yyyy-MM-dd)" % args.start_time)
    if args.end_time and end is None:
        add("end_time_format", False,
            "end_time '%s' is not parseable (use yyyy-MM-dd)" % args.end_time)
    if start and end:
        if end < start:
            add("window_order", False, "end_time %s precedes start_time %s" % (end, start))
        else:
            days = (end - start).days + 1
            add("window_length", days >= MIN_WINDOW_DAYS,
                "window spans %d day(s)" % days,
                soft=(days < MIN_WINDOW_DAYS))
            if days < MIN_WINDOW_DAYS:
                checks[-1]["message"] += (" - below the %d-day minimum; "
                                          "conclusions will be unreliable"
                                          % MIN_WINDOW_DAYS)
        if end > date.today():
            add("window_future", False,
                "end_time %s is in the future; metrics beyond today are always "
                "zero and will be misread as churn" % end)
    else:
        add("window_present", False,
            "start_time and end_time are required (default last 7 days is "
            "acceptable only when the campaign dates are genuinely unknown)",
            soft=True)

    # --- attribution window ----------------------------------------------
    add("attribution_window", args.window_value > 0,
        "attribution window = %d %s" % (args.window_value, args.window_unit))

    # --- strategy name ----------------------------------------------------
    add("strategy_name", bool(args.strategy_name),
        "strategy name = %s" % args.strategy_name if args.strategy_name
        else "strategy_name missing - deliverables will be named generically",
        soft=True)

    status = "FATAL" if fatal else ("EMPTY" if warn else "SUCCESS")
    payload = {
        "status": status,
        "mode": args.mode,
        "project_id": str(args.project_id),
        "window": {"start": str(start) if start else None,
                   "end": str(end) if end else None,
                   "days": ((end - start).days + 1) if (start and end) else None},
        "attribution_window": {"value": args.window_value, "unit": args.window_unit},
        "checks": checks,
        "fatal": fatal,
        "warnings": warn,
    }

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(1 if fatal else 0)


if __name__ == "__main__":
    main()
