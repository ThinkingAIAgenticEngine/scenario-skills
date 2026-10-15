#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1b helper - help the customer name their events and properties.

Mode B starts from a description, not from an id. A user says "push the lapsed
users last Thursday" and cannot be expected to recall `ops_click` or
`hermes_push_click`. This script turns that description into a shortlist by
fuzzy-searching event names (matched against eventName / eventDesc / aiRemark),
event and user properties, and audience clusters.

The agent then shows the shortlist and asks the user to pick. The user only
needs to understand their own business; the vocabulary is supplied here.

Usage:
    python3 resolve_events.py --project-id 61 --kind events --query push
    python3 resolve_events.py --project-id 61 --kind properties --query strategy
    python3 resolve_events.py --project-id 61 --kind clusters --query recall
    python3 resolve_events.py --project-id 61 --kind all --query push --out tmp/candidates.json

Exit codes:
  0  SUCCESS with candidates, or EMPTY when nothing matched
  1  FATAL (ae-cli error)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402

KINDS = ("events", "properties", "clusters", "tags", "all")

# Event name fragments that ThinkingData customers conventionally use for
# operational touchpoints. Surfaced first because they resolve a mode-B
# campaign far more often than an arbitrary keyword match.
CONVENTIONAL_HINTS = ("ops_view", "ops_click", "push_view", "push_click",
                      "sms", "email_click", "popup", "inapp")


def extract_items(resp):
    """Deprecated shim kept for readability at call sites; delegates to _ae."""
    return _ae.extract_items(resp)


def search(ae, project_id, kind, query, limit):
    # NOTE: ae-cli's help text advertises `aiRemark` as a returnable field for
    # both list_events and list_properties, but the server rejects it with
    # INVALID_FIELDS. Only name + description are requested here.
    if kind == "events":
        args = ["analysis_meta", "+list_events", "-p", str(project_id),
                "--fields", json.dumps(["eventName", "eventDesc"]),
                "--limit", str(limit)]
    elif kind == "properties":
        args = ["analysis_meta", "+list_properties", "-p", str(project_id),
                "--fields", json.dumps(["propName", "propDesc"]),
                "--limit", str(limit)]
    elif kind == "clusters":
        args = ["analysis_audience", "+list_clusters", "-p", str(project_id),
                "--limit", str(limit)]
    elif kind == "tags":
        args = ["analysis_audience", "+list_tags", "-p", str(project_id),
                "--limit", str(limit)]
    else:
        raise ValueError("unknown kind %s" % kind)
    if query:
        args += ["-q", query]
    return _ae.extract_items(_ae.run_ae(args, ae=ae), what=kind)


def normalise(kind, items):
    out = []
    for it in items:
        if kind == "events":
            name = it.get("eventName") or ""
            out.append({
                "event_name": name,
                "display": it.get("eventDesc") or it.get("aiRemark") or "",
                "conventional": any(h in name for h in CONVENTIONAL_HINTS),
            })
        elif kind == "properties":
            name = it.get("propName") or ""
            out.append({
                "property_name": name,
                "display": it.get("propDesc") or it.get("aiRemark") or "",
                "scope": "event" if name.startswith("#") else "user",
            })
        else:
            out.append({
                "audience_name": it.get("clusterName") or "",
                "display": it.get("displayName") or "",
                "type": it.get("clusterType") or "",
                "users": it.get("usersNum"),
            })
    return out


def main():
    ap = argparse.ArgumentParser(description="Fuzzy-search events / properties / audiences")
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--kind", required=True, choices=KINDS)
    ap.add_argument("--query", default=None,
                    help="keyword; matched against name, description and remark")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--out", default=None)
    ap.add_argument("--ae-cli", default=None)
    args = ap.parse_args()

    ae = args.ae_cli or _ae.find_ae_cli()
    kinds = ("events", "properties", "clusters", "tags") if args.kind == "all" else (args.kind,)

    result, fatal = {}, []
    for kind in kinds:
        try:
            items = search(ae, args.project_id, kind, args.query, args.limit)
            result[kind] = normalise(kind, items)
            _ae.log("%s: %d candidate(s)" % (kind, len(result[kind])), prefix="resolve")
        except Exception as e:
            result[kind] = []
            fatal.append("%s: %s" % (kind, str(e)[:200]))
            _ae.log("search failed for %s: %s" % (kind, str(e)[:200]), prefix="resolve")

    total = sum(len(v) for v in result.values())
    # Conventional event names float to the top: they resolve faster.
    if "events" in result:
        result["events"].sort(key=lambda x: (not x["conventional"], x["event_name"]))

    payload = {
        "status": "FATAL" if fatal and total == 0 else ("SUCCESS" if total else "EMPTY"),
        "project_id": str(args.project_id),
        "query": args.query,
        "kind": args.kind,
        "total": total,
        "candidates": result,
        "errors": fatal,
        "hint": ("Present these candidates to the user and ask them to confirm which "
                 "event marks the touchpoint click/open. Do not pick one silently."),
    }

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(1 if payload["status"] == "FATAL" else 0)


if __name__ == "__main__":
    main()
