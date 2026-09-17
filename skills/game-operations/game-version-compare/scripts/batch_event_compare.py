#!/usr/bin/env python3
"""
Batch comparison of core metrics before/after a version: pulls activity / social / duration metrics for "pre-launch vs post-launch" in one call.

Purpose: core query for Step 6 of version comparison (event model + comparison_time_ranges).

Usage:
    python batch_event_compare.py --project-id 7 \
        --post-start 2026-07-08 --post-end 2026-07-14 \
        --pre-start 2026-07-01 --pre-end 2026-07-07

This Project 7 example covers activity/login/register/add_friend/del_friend/online duration.
Confirm and adapt the event/property mappings before using it with another project.
Calls ae-cli via Python subprocess and returns structured pre/post comparison results.
"""

import argparse
import json
import subprocess
import sys


def run_adhoc(ae_cli, project_id, definition, model="event"):
    cmd = [ae_cli, "analysis", "adhoc", "run", "-p", str(project_id),
           "--model-type", model, "--definition", json.dumps(definition),
           "--preview-rows", "100", "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown ae-cli error"
        raise RuntimeError(detail)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ae-cli returned invalid JSON") from exc


def extract_rows(payload):
    data = payload.get("data", payload)
    if data.get("has_more"):
        print("WARNING: preview is truncated; use analysis adhoc export for full results",
              file=sys.stderr)
    return json.dumps(data.get("rows", []), ensure_ascii=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project-id", type=int, required=True)
    p.add_argument("--post-start", required=True)
    p.add_argument("--post-end", required=True)
    p.add_argument("--pre-start", required=True)
    p.add_argument("--pre-end", required=True)
    p.add_argument("--ae-cli", default="ae-cli")
    args = p.parse_args()

    post = {"mode": "custom", "start_time": args.post_start, "end_time": args.post_end}
    pre = {"mode": "custom", "start_time": args.pre_start, "end_time": args.pre_end}

    # Default metrics for the Project 7 example: activity / login count / register / add friend / delete friend
    def1 = {
        "metrics": [
            {"event": "login", "aggregation": "user_count"},
            {"event": "login", "aggregation": "total_count"},
            {"event": "register", "aggregation": "user_count"},
            {"event": "add_friend", "aggregation": "user_count"},
            {"event": "del_friend", "aggregation": "user_count"},
        ],
        "time_range": post,
        "time_particle_size": "total",
        "comparison_time_ranges": [pre],
    }
    print("### Activity / Social metrics: pre vs post ###")
    print(extract_rows(run_adhoc(args.ae_cli, args.project_id, def1)))
    print()

    # Online duration (attached to the logout event)
    def2 = {
        "metrics": [{"event": "logout", "aggregation": "sum", "property": "online_time"}],
        "time_range": post,
        "time_particle_size": "total",
        "comparison_time_ranges": [pre],
    }
    print("### Online duration (logout.online_time sum): pre vs post ###")
    print(extract_rows(run_adhoc(args.ae_cli, args.project_id, def2)))
    print()

    # Channel drill-down (add_friend grouped by channel)
    def3 = {
        "metrics": [{"event": "add_friend", "aggregation": "user_count"}],
        "groups": [{"field": {"name": "channel", "type": "event_property"}}],
        "time_range": post,
        "time_particle_size": "total",
        "comparison_time_ranges": [pre],
    }
    print("### Channel drill-down (add_friend by channel): pre vs post ###")
    print(extract_rows(run_adhoc(args.ae_cli, args.project_id, def3)))


if __name__ == "__main__":
    main()
