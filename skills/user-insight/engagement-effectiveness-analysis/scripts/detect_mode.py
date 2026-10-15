#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 0 gate - data source mode detection (A vs B).

The whole skill is built on one idea: two very different data sources, one
shared analysis pipeline. This script is the fork point, and it is a script
rather than prose because guessing the mode wrong sends the run down a path
that either returns nothing or, worse, returns something plausible-but-wrong.

Usage:
    python3 detect_mode.py --project-id 61 [--task-id 0822] [--flow-id 0306]
                           [--config-id abc] [--click-event push_click]
                           [--out tmp/mode.json]

Decision rules (first match wins):
  A  when any native object id is supplied AND it resolves inside Engage
  B  when a click/open event name is supplied instead
  B  when no native object id is given but project_id + event chain is present
  UNKNOWN otherwise -> exit 1, the caller must go back and ask the user

Exit codes:
  0  mode resolved (status SUCCESS)
  1  mode could not be resolved (status UNKNOWN) - ask the user
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402

NATIVE_KEYS = ("task_id", "flow_id", "config_id")


def probe_native(ae, project_id, task_id, flow_id, config_id):
    """Return (found: bool, detail: str) for whichever native id was supplied."""
    if task_id:
        # A single page of +task_list is not a membership proof: projects hold
        # hundreds of tasks and the list is paged, so a valid low id sits past
        # any first slice. _ae.find_task does a point lookup, then a full scan.
        t = _ae.find_task(ae, project_id, task_id)
        if t:
            return True, ("task %s (%s), status=%s, hasPushRecord=%s"
                          % (task_id, t.get("taskName"), t.get("statusName"),
                             t.get("hasPushRecord")))
        return False, ("task %s not found in project %s after scanning the full "
                       "task list" % (task_id, project_id))

    if flow_id:
        resp = _ae.run_ae(["engage", "+flow_list", "--project_id", str(project_id)], ae=ae)
        flows = _ae.as_list(resp)
        hit = [f for f in flows if str(f.get("flowId")) == str(flow_id)]
        if hit:
            f = hit[0]
            return True, ("flow %s (%s), hasData=%s"
                          % (flow_id, f.get("flowName"), f.get("hasData")))
        return False, "flow %s not found in project %s" % (flow_id, project_id)

    if config_id:
        resp = _ae.run_ae(["engage", "+config_item_list", "--project_id", str(project_id)],
                          ae=ae)
        items = _as_list(resp.get("data"))
        hit = [c for c in items if str(c.get("configId")) == str(config_id)]
        if hit:
            return True, "config_item %s (%s)" % (config_id, hit[0].get("configName"))
        return False, "config_item %s not found in project %s" % (config_id, project_id)

    return False, "no native object id supplied"


def _as_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("dataList", "items", "list", "configItemDTOS"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def main():
    ap = argparse.ArgumentParser(description="Detect data source mode A/B")
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--task-id", default=None)
    ap.add_argument("--flow-id", default=None)
    ap.add_argument("--config-id", default=None)
    ap.add_argument("--click-event", default=None,
                    help="click/open event name - presence implies mode B")
    ap.add_argument("--anchor-event", default=None,
                    help="funnel entry event name for mode B")
    ap.add_argument("--out", default=None, help="write mode.json here")
    ap.add_argument("--ae-cli", default=None)
    args = ap.parse_args()

    ae = args.ae_cli or _ae.find_ae_cli()
    checks = []
    mode, reason, detail = None, "", ""

    has_native = any([args.task_id, args.flow_id, args.config_id])
    has_events = bool(args.click_event or args.anchor_event)

    if has_native and has_events:
        # Explicit native object wins: its metrics are platform-defined, which
        # is strictly better than a reconstructed event funnel.
        mode = "A"
        reason = "native object id supplied together with event names; native wins"
    elif has_native:
        try:
            found, detail = probe_native(ae, args.project_id, args.task_id,
                                         args.flow_id, args.config_id)
        except Exception as e:
            found, detail = False, "probe failed: %s" % str(e)[:200]
        if found:
            mode = "A"
            reason = "native object id resolved inside Engage"
        else:
            mode = "UNKNOWN"
            reason = ("native object id was supplied but could not be resolved; "
                      "confirm the id or switch to mode B by supplying event names")
    elif has_events:
        mode = "B"
        reason = "no native object id; event chain supplied instead"

    checks.append({"check": "mode_resolved", "status": "SUCCESS" if mode in ("A", "B") else "FATAL",
                   "message": "mode=%s (%s)" % (mode, reason)})
    if detail:
        checks.append({"check": "native_probe", "status": "SUCCESS", "message": detail})

    payload = {
        "status": "SUCCESS" if mode in ("A", "B") else "UNKNOWN",
        "mode": mode,
        "mode_label": {
            "A": "ThinkingData Engage native (task/flow/config)",
            "B": "third-party or self-built platform (event recovery)",
        }.get(mode),
        "reason": reason,
        "project_id": str(args.project_id),
        "object": {"task_id": args.task_id, "flow_id": args.flow_id,
                   "config_id": args.config_id},
        "events": {"anchor": args.anchor_event, "click": args.click_event},
        "checks": checks,
    }

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload["status"] != "SUCCESS":
        _ae.log("mode not resolved - ask the user for either a native object id "
                "or the campaign's click/open event name", prefix="detect")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
