#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1b - render the mode-B intake questionnaire.

The intake contract is 11 questions. This script emits it as a template file
so the agent fills it in one pass instead of drip-feeding questions, and so the
customer can see up front what will be asked.

Usage:
    python3 collect_intake.py --out tmp/intake.json --strategy-name "lapsed user recall"
    python3 collect_intake.py --show          # print the questionnaire only

Exit codes: 0 always (this script only prepares input; validate_intake.py gates).
"""
import argparse
import json
import os
import sys

# (key, required, label, question, how_to_resolve)
CONTRACT = [
    ("strategy_name", "required", "Strategy identity",
     "What is this campaign / strategy called, and does it have an id?",
     "Free text. Used for the report title and to keep data isolated."),
    ("channel", "required", "Channel",
     "Which channel did it go out on - push / in-app message / popup / SMS / EDM / phone / mixed?",
     "Enum. Determines which benchmarks apply."),
    ("time_window", "required", "Time window",
     "When was it sent? Start and end date.",
     "yyyy-MM-dd pair. Must span >= 3 days."),
    ("target_audience", "required", "Target audience",
     "Who received it - all users / a tag / a cluster?",
     "Free text. Searchable via analysis_audience +list_clusters / +list_tags."),
    ("discriminator", "critical", "Discriminating property",
     "Is there a property that marks this specific send, e.g. strategy_id, campaign, channel?",
     "MANDATORY to ask. Search via analysis_meta +list_properties -q strategy. "
     "Without it the audience is approximated by the time window and precision drops ~20%."),
    ("grouping", "optional", "Experiment grouping",
     "Was there an A/B split? What is the group property name?",
     "Search via analysis_meta +list_properties. Enables real lift instead of a quasi-experiment."),
    ("view_event", "optional", "Impression event",
     "Which event means the message was displayed?",
     "Search via analysis_meta +list_events -q push / popup. Conventionally ops_view."),
    ("click_event", "required", "Click / open event",
     "Which event means the user clicked or opened it?",
     "Search via analysis_meta +list_events. Conventionally ops_click. "
     "Without this there is no observable conversion path."),
    ("conversion_event", "optional", "Conversion event",
     "Which event means the goal was achieved - payment, reward claimed, return visit?",
     "Search via analysis_meta +list_events. Without it, click rate and next-day retention "
     "are used as proxies."),
    ("attribution_window", "required", "Attribution window",
     "How long after the click still counts as credit for this send?",
     "Defaults to 24 hours. Maps to the funnel window field."),
    ("exclusions", "optional", "Exclusions",
     "Any audience to exclude - already paid, unsubscribed, internal test accounts?",
     "Property filter."),
]

REQUIRED = [k for k, r, *_ in CONTRACT if r == "required"]
CRITICAL = [k for k, r, *_ in CONTRACT if r == "critical"]


def render_text():
    lines = ["Mode B intake contract - fill every REQUIRED field before running.",
             "=" * 68]
    for i, (key, req, label, question, how) in enumerate(CONTRACT, 1):
        tag = {"required": "[REQUIRED]", "critical": "[CRITICAL]",
               "optional": "[optional]"}[req]
        lines.append("")
        lines.append("%2d. %s %s - %s" % (i, tag, label, question))
        lines.append("    %s" % how)
    return "\n".join(lines)


def template():
    t = {}
    for key, _req, _label, _q, _how in CONTRACT:
        if key == "time_window":
            t[key] = {"start": None, "end": None}
        elif key == "discriminator":
            t[key] = {"property": None, "value": None}
        elif key == "grouping":
            t[key] = {"property": None}
        elif key == "attribution_window":
            t[key] = {"value": 24, "unit": "hour"}
        else:
            t[key] = None
    return t


def main():
    ap = argparse.ArgumentParser(description="Render the mode-B intake questionnaire")
    ap.add_argument("--out", default=None, help="write an intake template JSON here")
    ap.add_argument("--strategy-name", default=None, help="pre-fill the strategy name")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    payload = {
        "status": "SUCCESS",
        "required_fields": REQUIRED,
        "critical_fields": CRITICAL,
        "contract": [{"key": k, "level": r, "label": l, "question": q, "how": h}
                     for k, r, l, q, h in CONTRACT],
        "template": template(),
        "text": render_text(),
    }
    if args.strategy_name:
        payload["template"]["strategy_name"] = args.strategy_name

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload["template"], f, ensure_ascii=False, indent=1)
        payload["written"] = os.path.abspath(args.out)

    if args.show or not args.out:
        print(payload["text"])
    print(json.dumps({k: v for k, v in payload.items() if k != "text"},
                     ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
