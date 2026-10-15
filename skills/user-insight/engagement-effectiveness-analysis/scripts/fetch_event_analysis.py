#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 2b -- mode B data fetch (client-hosted operations backend / third-party channels)

When the client sends campaigns from their own operations backend there is no
canvas ID and no task ID, so the effect has to be reconstructed from a "strategy
description + retrieval events". This script **normalises the generic analysis
endpoint's response into a structure isomorphic to mode A**:

    raw_overview.json       <- users per funnel stage ({"data":{"dataList":[...]}})
    raw_detail_time.json    <- day-by-day event trend ({"data":{"data":{"x":[],"y":[]}}})
    raw_event_meta.json     <- mode B metadata (event chain / attribution window /
                               data availability / truncation flags)

Once normalised, Steps 3-5 (analysis -> detail Excel -> report) are reused with
no branching at all, which is exactly how the "two sources, one analysis"
architecture lands.

The ad-hoc protocol is absorbed by _ae.adhoc_run(): 6.x runs one call
("analysis adhoc run --definition") and explicitly refuses a raw QP. This
script only declares the model, the time range and the parameters. The first
row of the result is the platform's summary row, captioned in the caller's
language (`Overview` or a localised stage-summary caption).
Normalisation relabels it to the downstream token `total`; see canonical_label().

Usage:
    python3 fetch_event_analysis.py --project-id 61 \
        --steps '[{"event":"ops_view","role":"view"},{"event":"ops_click","role":"click"},{"event":"shop_buy","role":"main"}]' \
        --time-range '{"mode":"custom","startTime":"2026-08-01","endTime":"2026-09-14"}' \
        --window-value 24 --window-unit hour --out-dir tmp

`--time-range` accepts either spelling of the start and end keys
(`startTime`/`endTime` or `start_time`/`end_time`) and re-spells them for the
target generation before sending.

role values and the platform metric keys they map to:
    view  -> impression     click -> click        main -> conversion
    (plan / actualTrigger / trigger are unavailable on the mode B side and are
     degraded away automatically)
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wording import _L, _F  # noqa: E402
import _ae  # noqa: E402
import _cmdtree  # noqa: E402
import _env  # noqa: E402

ROLE_TO_METRIC = {
    "view": "view",
    "click": "click",
    "main": "main",
    "plan": "plan",
    "trigger": "trigger",
    "actualTrigger": "actualTrigger",
}


def log(msg):
    print(f"[fetch-b] {msg}", file=sys.stderr)


# ae-cli discovery, invocation and request-id generation all live in _ae, which
# in turn delegates discovery to _env. Keeping a second copy here is how a skill
# ends up working on the author's machine and nowhere else: the two copies drift,
# and the weaker one (no stderr fallback, no soft-error handling) silently wins.
#
# Fetching an ad-hoc analysis happens in _ae.adhoc_run(), which builds the
# unified 6.x call: an AI-facing definition, with raw QP refused (one call).
# That protocol detail belongs to the CLI contract, not to this script, so
# nothing here branches on it.


def canonical_label(index, label):
    """Row 0 of an analysis result is the platform's summary row.

    The platform renders that caption in the caller's language - `Overview` on the
    1.x path, a localised stage-summary caption on the 6.x one - so the text is not
    a stable identifier. Downstream readers (parse_time_series, timeline_days)
    recognise the summary by name and would score a localised caption as an ordinary
    data point: one phantom day in the trend, and a total row masquerading as a date.
    Position is the contract that actually holds, so row 0 is relabelled to the
    canonical token those readers already know.
    """
    return "total" if index == 0 else str(label)


# ---------------------------------------------------------------- normalisation

# The funnel result interleaves a conversion column after every step but the
# first:  [Totals, Step1, Step2, Conv2, Step3, Conv3, ...]
# so a step's count is NOT at index i+1. Reading it positionally lands the third
# step on the second step's conversion percentage - `int("85.99%")` fails and
# the step reports 0, a headline "no conversions" that looks like a finding.
# Confirmed for 2..5 steps against a real project (title length == 2 * steps).
STEP_MARKER_RE = re.compile(_L("fe.001"), re.I)


def to_count(value):
    """A step count, or None when the value is not one.

    Counts arrive as ints under 6.x and strings under 1.x. Anything that is not
    a number returns None rather than being coerced to zero - in particular a
    conversion percentage, which is exactly what a mis-resolved column yields.
    Reporting "0 users reached this step" and "we read the wrong column" as the
    same value is how a layout change becomes a business conclusion.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(float(str(value).strip().replace(",", "")))
    except (TypeError, ValueError):
        return None


def resolve_step_columns(title, n_steps):
    """Map each funnel step to the result column holding its count.

    Two independent readings, because neither is guaranteed:
      * the header carries a parenthesised step marker - a real structural
        signal, but rendered in the caller's language and observed to switch
        between calls on the same host;
      * `len(title) == 2 * n_steps` means the interleaved layout above, which
        is what the engine emits today but is an implementation detail.

    Nothing is returned for a step whose column cannot be agreed on, so the
    caller reports it rather than reading a neighbour as if it were the answer.
    """
    by_marker = {}
    for col, name in enumerate(title or []):
        found = STEP_MARKER_RE.search(str(name))
        if found:
            by_marker[int(found.group(1)) - 1] = col
    if len(by_marker) == n_steps:
        return by_marker
    if title and len(title) == 2 * n_steps:
        # step 1 -> column 1; step k -> 2k, because a conversion column sits
        # between every later pair.
        return {k: (1 if k == 0 else 2 * k) for k in range(n_steps)}
    return {}


def normalize_funnel(adhoc, steps):
    """Normalise a funnel result into mode A's raw_overview structure."""
    title = adhoc.get("title") or []
    rows = adhoc.get("rows") or []
    row = rows[0] if rows else None
    columns = resolve_step_columns(title, len(steps))

    metrics, unmapped = {}, []
    for i, step in enumerate(steps):
        metric_key = ROLE_TO_METRIC.get(step.get("role"), step.get("event"))
        col = columns.get(i)
        value = to_count(row[col]) if (row and col is not None and col < len(row)) else None
        if value is None:
            # Either the column could not be identified, or what is in it is
            # not a count. Both mean "unknown", which is not the same as zero.
            unmapped.append(step.get("event") or metric_key)
            value = 0
        metrics[metric_key] = value
    return {
        "data": {
            "dataList": [{"key": k, "value": str(v)} for k, v in metrics.items()],
            "resultGenerateTime": None,
        },
        "_source": {
            "model": "funnel",
            "title": title,
            "rows": rows,
            "has_data": bool(rows),
            "unmapped_steps": unmapped,
        },
    }


def normalize_event_timeline(adhoc, steps):
    """Normalise an event result into mode A's raw_detail_time structure (x + y)."""
    title = adhoc.get("title") or []
    rows = adhoc.get("rows") or []

    xs, series = [], {}
    for step in steps:
        metric_key = ROLE_TO_METRIC.get(step.get("role"), step.get("event"))
        series[metric_key] = []

    for idx, r in enumerate(rows):
        if not r:
            continue
        # r[0] is a caption, not data - see canonical_label().
        xs.append(canonical_label(idx, r[0]))
        for i, step in enumerate(steps):
            col = i + 1
            metric_key = ROLE_TO_METRIC.get(step.get("role"), step.get("event"))
            value = to_count(r[col]) if col < len(r) else None
            series[metric_key].append(value or 0)

    y = [{k: [{"values": v}]} for k, v in series.items()]
    return {
        "data": {
            "data": {"result_generate_time": None, "x": xs, "y": y, "z": None, "xtag": None},
        },
        "_source": {"model": "event", "title": title, "rows": rows, "has_data": bool(rows)},
    }


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=_L("fe.002"))
    ap.add_argument("--ae-cli", default=None)
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--steps", required=True,
                    help=_L("fe.003"))
    ap.add_argument("--time-range", required=True, help=_L("fe.004"))
    ap.add_argument("--window-value", type=int, default=24, help=_L("fe.005"))
    ap.add_argument("--window-unit", default="hour", choices=["hour", "day", "minute"])
    ap.add_argument("--out-dir", default="tmp")
    ap.add_argument("--intake", default=None,
                    help=_L("fe.006"))
    args = ap.parse_args()

    # The intake.json fields that are irrelevant to fetching but still shown in the
    # report (channel / discriminator property / target audience) used to be thrown
    # away. Step 2b's contract states that its input is intake.json, so it is read
    # here and passed through Step 3 verbatim, instead of the report header showing
    # an empty channel.
    intake = {}
    if args.intake and os.path.exists(args.intake):
        try:
            with open(args.intake, encoding="utf-8") as f:
                intake = json.load(f)
        except Exception as e:
            log(_F("fe.t001", a1=e))

    ae = args.ae_cli or _ae.find_ae_cli()
    steps = json.loads(args.steps)
    if len(steps) < 2:
        log(_L("fe.007"))
        sys.exit(2)

    os.makedirs(args.out_dir, exist_ok=True)
    # The time range may use either spelling of the start/end keys; adhoc_run
    # respells it for whichever CLI generation is installed.
    time_range = json.loads(args.time_range)
    window = {"value": args.window_value, "unit": args.window_unit}

    # A discriminator (strategy_id / campaign / channel) becomes a query filter,
    # isolating this campaign's events from events belonging to other campaigns in
    # the same time window. That is the only meaningful use of a discriminator:
    # writing it into meta for display only, without filtering, leaves that ~20%
    # precision loss sitting in the result. FilterRequest is the 6.x contract; 1.x
    # silently ignores filters (a fake filter), so None is returned here and the
    # "not applied" state is recorded in meta instead.
    variant = _env.detect_variant(ae)
    discriminator = (intake or {}).get("discriminator")
    filt = _cmdtree.discriminator_filter(discriminator, variant)

    # ---- (1) Funnel model: users per stage (each user completes the stages in order)
    funnel_params = {
        "funnel": {"steps": [{"event": s["event"]} for s in steps],
                   "window": window},
    }
    if filt:
        funnel_params["funnel"]["filters"] = [filt]
    log(_L("fe.008") % (
        len(steps), window["value"], window["unit"],
        _L("fe.009") % (filt["field"]["name"], filt["values"][0]) if filt else ""))
    funnel_adhoc = _ae.adhoc_run(ae, args.project_id, "funnel", time_range,
                                 funnel_params, request_id=_ae.new_request_id())
    raw_overview = normalize_funnel(funnel_adhoc, steps)

    # ---- (2) Event model: day-by-day trend
    event_params = {
        "metrics": [{"event": s["event"], "aggregation": "user_count"}
                    for s in steps],
        "time_particle_size": "day",
    }
    if filt:
        event_params["filters"] = [filt]
    log(_L("fe.010"))
    try:
        event_adhoc = _ae.adhoc_run(ae, args.project_id, "event", time_range,
                                    event_params, request_id=_ae.new_request_id())
        raw_timeline = normalize_event_timeline(event_adhoc, steps)
    except Exception as e:
        log(_F("fe.t002", a1=e))
        event_adhoc = None
        raw_timeline = None

    # ---- (3) metadata
    has_data = raw_overview["_source"]["has_data"]
    meta = {
        "mode": "B",
        "project_id": args.project_id,
        "time_range": time_range,
        "attribution_window": window,
        "steps": steps,
        "channel": (intake or {}).get("channel"),
        "target_audience": (intake or {}).get("target_audience"),
        "discriminator": discriminator,
        "discriminator_applied": filt is not None,
        "event_chain": [s["event"] for s in steps],
        "funnel_title": funnel_adhoc.get("title"),
        "funnel_has_data": has_data,
        "timeline_has_data": raw_timeline["_source"]["has_data"] if raw_timeline else False,
        "truncated": [],
        "unmapped_steps": list(raw_overview["_source"].get("unmapped_steps") or []),
        "notes": [],
    }
    if not has_data:
        meta["notes"].append(
            _L("fe.011")
        )
    if discriminator and filt is None:
        meta["notes"].append(
            _L("fe.012")
            % str(discriminator.get("property"))
        )
    meta["notes"].append(
        _L("fe.013")
    )

    # A truncated result is indistinguishable from a complete one at the call
    # site: every row that came back is valid, they are just not all of them.
    # 6.x reports this as `has_more` on the synchronous preview, whose row budget
    # is fixed; 1.x never sets it. Recorded here so Step 3 can put it in the
    # confidence statement instead of letting a short curve read as a real drop
    # in volume.
    for label, payload in (("funnel", funnel_adhoc), ("event", event_adhoc)):
        if payload and payload.get("hasMore"):
            meta["truncated"].append(label)
    if meta["truncated"]:
        meta["notes"].append(
            _L("fe.014")
            % "、".join(meta["truncated"])
        )
    if meta["unmapped_steps"]:
        meta["notes"].append(
            _L("fe.015")
            % "、".join(meta["unmapped_steps"])
        )

    def dump(name, obj):
        obj = {k: v for k, v in obj.items() if k != "_source"} if obj else obj
        p = os.path.join(args.out_dir, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        return p

    p1 = dump("raw_overview.json", raw_overview)
    p2 = dump("raw_detail_time.json", raw_timeline)
    p3 = os.path.join(args.out_dir, "raw_event_meta.json")
    with open(p3, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    # Keep the raw response on file so Sheet 7 stays traceable
    p4 = os.path.join(args.out_dir, "raw_event_rows.json")
    with open(p4, "w", encoding="utf-8") as f:
        json.dump({"funnel": funnel_adhoc, "event": (event_adhoc if raw_timeline else None)},
                  f, ensure_ascii=False, indent=1)

    log(_F("fe.t003", a1=args.out_dir))
    log(_F("fe.t004", a1=has_data, a2=meta['timeline_has_data']))
    log(_F("fe.t005", a1={i['key']: i['value'] for i in raw_overview['data']['dataList']}))
    print(p1)


if __name__ == "__main__":
    main()
