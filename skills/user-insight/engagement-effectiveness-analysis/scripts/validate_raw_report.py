#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 2 gate - validate raw report payloads before analysis.

Catches the failure that matters most at this stage: a fetch that "succeeded"
but returned an empty envelope. Left unchecked it flows into the analysis and
surfaces as a confident report about nothing.

Usage:
    python3 validate_raw_report.py --raw-dir tmp --mode A
    python3 validate_raw_report.py --raw-dir tmp_b --mode B

Exit codes:
  0  SUCCESS (analysable data present)
  0  EMPTY   (payload exists but no metric values - run continues in degraded mode)
  1  FATAL   (no usable payload at all)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402

OVERVIEW_METRICS = ("plan", "actualTrigger", "trigger", "view", "click", "main")


def load(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def overview_metrics(raw):
    """Accept both the flat {dataList:[...]} shape and a nested variant."""
    if not raw:
        return {}
    node = raw.get("data") or {}
    dl = node.get("dataList")
    if not dl and isinstance(node.get("data"), dict):
        dl = node["data"].get("dataList")
    out = {}
    for item in dl or []:
        try:
            out[item["key"]] = int(float(item.get("value") or 0))
        except (KeyError, TypeError, ValueError):
            continue
    return out


SUMMARY_LABELS = ("total", "合计", "Total", "Overview", "overview")


def timeline_days(raw):
    """Count real date rows, excluding the summary row the platform prepends."""
    if not raw:
        return 0
    node = (raw.get("data") or {}).get("data") or {}
    return sum(1 for x in (node.get("x") or []) if str(x) not in SUMMARY_LABELS)


def main():
    ap = argparse.ArgumentParser(description="Step 2 gate")
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--mode", required=True, choices=["A", "B"])
    args = ap.parse_args()

    checks = []
    rd = args.raw_dir

    def add(name, status, message):
        checks.append({"check": name, "status": status, "message": message})

    # --- overview block: mandatory in both modes -------------------------
    ov_path = os.path.join(rd, "raw_overview.json")
    ov = load(ov_path)
    if ov is None:
        add("overview_present", "FATAL", "raw_overview.json missing at %s" % ov_path)
        metrics = {}
    else:
        metrics = overview_metrics(ov)
        add("overview_present", "SUCCESS", "raw_overview.json present")
        add("overview_parsable", "SUCCESS" if metrics else "FATAL",
            "%d metric(s) parsed: %s" % (len(metrics), sorted(metrics)))
        non_zero = {k: v for k, v in metrics.items() if v > 0}
        if not metrics:
            pass
        elif not non_zero:
            add("overview_non_zero", "EMPTY",
                "every metric is 0 - either the campaign genuinely reached nobody "
                "or the object id / event chain is wrong; confirm before proceeding")
        else:
            add("overview_non_zero", "SUCCESS",
                "%d metric(s) above zero" % len(non_zero))

    # --- timeline block: recommended -------------------------------------
    tl_path = os.path.join(rd, "raw_detail_time.json")
    tl = load(tl_path)
    if tl is None:
        add("timeline_present", "EMPTY",
            "raw_detail_time.json missing - trend and fatigue analysis will be skipped")
    else:
        days = timeline_days(tl)
        add("timeline_present", "SUCCESS", "timeline present")
        add("timeline_days", "SUCCESS" if days >= 3 else "EMPTY",
            "%d day row(s); >= 3 recommended" % days)

    # --- per-mode extras --------------------------------------------------
    if args.mode == "A":
        if load(os.path.join(rd, "raw_tasklist.json")) is not None:
            add("task_meta_present", "SUCCESS", "raw_tasklist.json present")
        else:
            add("task_meta_present", "EMPTY",
                "raw_tasklist.json missing - channel / trigger time / conversion "
                "indicators will be blank in the report header")
        if load(os.path.join(rd, "raw_exp_overview.json")) is not None:
            add("experiment_present", "SUCCESS", "experiment report present")
        else:
            add("experiment_present", "EMPTY",
                "no experiment report - lift will fall back to a quasi-experiment")
    else:
        em = load(os.path.join(rd, "raw_event_meta.json"))
        if em is None:
            add("event_meta_present", "FATAL",
                "raw_event_meta.json missing - mode B cannot report which events were used")
        else:
            add("event_meta_present", "SUCCESS",
                "event chain: %s" % " -> ".join(em.get("event_chain") or []))
            if not em.get("funnel_has_data"):
                add("event_funnel_data", "EMPTY",
                    "the funnel returned no rows for this event chain and window. "
                    "Check: event name correctness, whether the campaign ran in the "
                    "window, and whether the client is still reporting.")
            else:
                add("event_funnel_data", "SUCCESS", "funnel returned rows")

            # A stage whose column could not be resolved was written as 0, which
            # is indistinguishable from "nobody reached it". Stop the run here
            # rather than let that zero be read as a finding.
            unmapped = em.get("unmapped_steps") or []
            if unmapped:
                add("event_funnel_columns", "EMPTY",
                    "the funnel's column layout did not match the expected shape, "
                    "so stage(s) %s were written as 0 - this is NOT evidence of no "
                    "conversion" % ", ".join(map(str, unmapped)))
            else:
                add("event_funnel_columns", "SUCCESS",
                    "every funnel stage resolved to a column")

            # Truncation: the rows returned are valid, they are just not all of
            # them, so any trend conclusion drawn from them is short.
            truncated = em.get("truncated") or []
            if truncated:
                add("event_result_complete", "EMPTY",
                    "the platform truncated the result (%s); shorten the window or "
                    "use the export capability before drawing conclusions"
                    % ", ".join(map(str, truncated)))
            else:
                add("event_result_complete", "SUCCESS", "result not truncated")

    fatals = [c for c in checks if c["status"] == "FATAL"]
    empties = [c for c in checks if c["status"] == "EMPTY"]
    status = "FATAL" if fatals else ("EMPTY" if empties else "SUCCESS")
    print(json.dumps({"status": status, "mode": args.mode,
                      "metrics": metrics, "checks": checks},
                     ensure_ascii=False, indent=2))
    sys.exit(1 if fatals else 0)


if __name__ == "__main__":
    main()
