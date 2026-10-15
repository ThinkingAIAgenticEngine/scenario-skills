#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1b gate - validate a filled mode-B intake file.

Hard rule encoded here: a run may not start until every REQUIRED field of the
contract is present. The critical field (discriminating property) does not
block the run, but its absence is reported loudly because it costs precision.

Usage:
    python3 validate_intake.py tmp/intake.json

Exit codes:
  0  SUCCESS (all required present, critical present)
  0  EMPTY   (all required present, critical missing -> degraded, warn loudly)
  1  FATAL   (a required field is missing -> ask the user, do not proceed)
Output: {"status":..., "checks":[...], "missing_required":[...], "degradations":[...]}
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402
from collect_intake import CONTRACT, REQUIRED, CRITICAL  # noqa: E402

MIN_WINDOW_DAYS = 3


def present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(present(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    return True


def main():
    ap = argparse.ArgumentParser(description="Validate mode-B intake contract")
    ap.add_argument("intake", help="path to intake.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if not os.path.exists(args.intake):
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "intake_file", "status": "FATAL",
                             "message": "intake file not found: %s" % args.intake}]})

    try:
        with open(args.intake, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "intake_parse", "status": "FATAL",
                             "message": "cannot parse intake json: %s" % e}]})

    checks, missing_required, degradations = [], [], []

    for key, level, label, _q, _how in CONTRACT:
        ok = present(data.get(key))
        status = "SUCCESS" if ok else ("FATAL" if level == "required" else "EMPTY")
        checks.append({"check": key, "level": level, "status": status,
                       "message": "%s %s" % (label, "present" if ok else "MISSING")})
        if not ok and level == "required":
            missing_required.append(key)
        elif not ok and level == "critical":
            degradations.append({
                "item": "discriminating property",
                "impact": "the exact send cannot be isolated; the audience is approximated "
                          "by the time window and overlapping campaigns may contaminate it",
                "loss": "~20%",
            })
        elif not ok and level == "optional":
            degradations.append({
                "item": label,
                "impact": "corresponding analysis block is skipped",
                "loss": {"grouping": "~25%", "view_event": "~25%",
                         "conversion_event": "~20%", "exclusions": "~5%"}.get(key, "~10%"),
            })

    # Event names are machine identifiers (snake_case, ASCII). A natural-language
    # phrase here means the user described the action but nobody resolved it to a
    # real event yet - running with it returns an empty funnel that looks like
    # "no engagement" instead of "wrong name".
    def looks_like_description(value):
        if not isinstance(value, str):
            return False
        s = value.strip()
        if not s:
            return False
        if any("\u4e00" <= ch <= "\u9fff" for ch in s):
            return True
        if " " in s or "，" in s or "," in s:
            return True
        return not re.match(r"^[A-Za-z_#][A-Za-z0-9_.#:\[\]-]*$", s)

    for key in ("click_event", "view_event", "conversion_event"):
        v = data.get(key)
        if present(v) and looks_like_description(v):
            checks.append({"check": "%s_resolved" % key, "status": "EMPTY",
                           "message": "%s looks like a description ('%s'), not a resolved "
                                      "event name; search candidates and confirm with the "
                                      "user first" % (key, v)})
            if key == "click_event":
                degradations.append({
                    "item": "click event name",
                    "impact": "an unresolved name returns an empty funnel, which reads as "
                              "'nobody engaged' rather than 'wrong event'",
                    "loss": "~100%",
                })

    # Window sanity.
    tw = data.get("time_window") or {}
    start, end = _ae.norm_date(tw.get("start")), _ae.norm_date(tw.get("end"))
    if start and end:
        try:
            d0 = datetime.strptime(start, "%Y-%m-%d").date()
            d1 = datetime.strptime(end, "%Y-%m-%d").date()
            days = (d1 - d0).days + 1
            if days < MIN_WINDOW_DAYS:
                checks.append({"check": "time_window_length", "status": "EMPTY",
                               "message": "window spans %d day(s), minimum %d"
                                          % (days, MIN_WINDOW_DAYS)})
                degradations.append({"item": "short window",
                                     "impact": "too few observations for a stable rate",
                                     "loss": "~15%"})
            else:
                checks.append({"check": "time_window_length", "status": "SUCCESS",
                               "message": "window spans %d day(s)" % days})
        except ValueError:
            pass

    fatals = [c for c in checks if c["status"] == "FATAL"]
    status = "FATAL" if fatals else ("EMPTY" if degradations else "SUCCESS")

    payload = {
        "status": status,
        "checks": checks,
        "missing_required": missing_required,
        "degradations": degradations,
        "required_fields": REQUIRED,
        "critical_fields": CRITICAL,
        "strategy_name": data.get("strategy_name"),
    }
    if missing_required:
        payload["next_action"] = (
            "Ask the user for: %s. Do not start the analysis until these are "
            "answered - a guessed value produces a plausible but wrong report."
            % ", ".join(missing_required)
        )
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(1 if fatals else 0)


if __name__ == "__main__":
    main()
