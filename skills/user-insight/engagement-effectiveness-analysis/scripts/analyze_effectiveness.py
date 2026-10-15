#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 3 -- multi-dimensional effectiveness analysis (shared by both modes).

Reads the raw report JSON produced by Step 2 (modes A / B already normalised)
and writes a uniformly structured analysis.json. Modes A and B share this
script; they differ only in which blocks are present in the input.

Usage:
    python3 analyze_effectiveness.py --raw-dir tmp --out tmp/analysis.json \
        --task-id 0822 --mode A --strategy-name "shiyan"

Input (under --raw-dir; a missing block degrades automatically and is recorded
in `degradations`):
    raw_overview.json          required  funnel metrics {dataList:[{key,value}]}
    raw_detail_time.json       optional  day-by-day series {x:[],y:[{k:[{values:[]}]}]}
    raw_detail_instance.json   optional  per-instance series {x:[],y:[],z:[]}
    raw_exp_overview.json      optional  AB experiment overview {overviewData:[]}
    raw_exp_detail.json        optional  AB experiment detail {detailData:{...}}
    raw_tasklist.json          optional  task metadata (completionIndicatorDef / expConfig)
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wording import _L, _F  # noqa: E402

# ---------------------------------------------------------------- constants

# Campaign funnel stages (order is the funnel order)
FUNNEL_STAGES = [
    ("plan",          _L("an.001"), _L("an.002")),
    ("actualTrigger", _L("an.003"), _L("an.004")),
    ("trigger",       _L("an.005"), _L("an.006")),
    ("view",          _L("an.007"), _L("an.008")),
    ("click",         _L("an.009"),     _L("an.010")),
    ("main",          _L("an.011"),     _L("an.012")),
]

# Stage-to-stage rate definitions: (metric name, numerator key, denominator key, label)
RATE_DEFS = [
    (_L("an.013"),     "actualTrigger", "plan",   _L("an.014")),
    (_L("an.015"), "trigger",       "actualTrigger", _L("an.016")),
    (_L("an.017"),     "view",          "trigger", _L("an.018")),
    (_L("an.019"),     "click",         "view",   _L("an.020")),
    (_L("an.021"),     "main",          "click",  _L("an.022")),
]

# Industry benchmark thresholds (see assets/benchmark_thresholds.md).
# Entry names must map one-to-one onto the metrics in RATE_DEFS -- an entry that
# exists here but not in RATE_DEFS can never fire (dead config) and merely makes
# people believe the metric is being monitored.
# One entry, "unsubscribe rate > 2% frequency-cap warning", was dead for a long
# while: FUNNEL_STAGES has no unsubscribe stage, so no matching RATE_DEFS entry
# exists either. If an unsubscribe event is ever added, both places must change.
BENCHMARKS = [
    (_L("an.015"), 0.90, "lt", "🔴", _L("an.023")),
    (_L("an.019"),     0.03, "lt", "🟠", _L("an.024")),
]

# Metric key -> label (report and Excel headers both align with the platform wording)
METRIC_LABELS = {k: lbl for k, lbl, _ in FUNNEL_STAGES}

# Key of the primary metric (conversion) inside the detail payload
MAIN_METRIC_KEYS = ["main"]


# ---------------------------------------------------------------- helpers

def log(msg):
    print(f"[analyze] {msg}", file=sys.stderr)


def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(_F("an.t001", a1=path, a2=e))
        return None


def safe_div(a, b):
    """Safe division; None means not computable."""
    try:
        if b in (None, 0):
            return None
        return a / b
    except (TypeError, ZeroDivisionError):
        return None


def as_dict(v):
    """Accept dict and nothing else -- anything else becomes an empty dict.

    This is the single guard for external data entering the parsing layer.
    Each file under --raw-dir can turn into a list / str / None because upstream
    changed its response shape, or because mode B data was prepared by hand. A bare
    `.get()` raises AttributeError, and `(v or {})` does not rescue it either: a
    non-empty list is truthy, so `.get` still lands on a list.
    """
    return v if isinstance(v, dict) else {}


def to_int(v):
    """str / float / int -> int; unparsable or non-finite (NaN/Inf) becomes 0.

    OverflowError has to be caught explicitly: `int(float('inf'))` raises that, not
    ValueError. If upstream ever persisted an inf with Python's json.dump (the
    product of a ratio divided by zero), one missing exception type here makes the
    whole analysis traceback on its very last step.
    """
    try:
        return int(float(v))
    except (TypeError, ValueError, OverflowError):
        return 0


def parse_embedded(v):
    """completionIndicatorDef / expConfig and friends may arrive as JSON strings."""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s or s in ("null", "{}", "[]"):
            return None
        try:
            return json.loads(s)
        except Exception:
            return None
    return None


def ms_to_local_date(v, tz_offset):
    """Millisecond (or second) timestamp -> `YYYY-MM-DD` in the task's timezone.

    tz_offset is the platform's `tzOffset` field, in hours. Any parse failure returns
    None and the caller decides to degrade to an em dash; a date is never guessed.
    """
    try:
        ts = float(v)
    except (TypeError, ValueError):
        return None
    if ts > 1e11:                       # 毫秒用 1e11 而不是 1e12 作分界，
        ts = ts / 1000.0                # 秒级时间戳到 3000 年也到不了 1e11
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=int(tz_offset or 0))
    except (OverflowError, OSError, ValueError):
        return None
    return dt.strftime("%Y-%m-%d")


def humanize_crontab(expr):
    """Render common crontab / quartz expressions in plain words; pass through if unknown.

    Only the "fixed moment every day" shape is translated -- it is by far the most
    common driver for campaign sends. Everything else is passed through verbatim, so
    an unrecognised expression is never translated wrongly.
    """
    if not expr:
        return None
    parts = str(expr).split()
    minute = hour = None
    if len(parts) == 6:                 # 秒 分 时 日 月 周（quartz）
        _, minute, hour, dom, month, dow = parts
    elif len(parts) == 5:               # 分 时 日 月 周（cron）
        minute, hour, dom, month, dow = parts
        dow = dow if dow != "*" else "?"
    else:
        return str(expr)
    if dom == "*" and month == "*" and dow in ("?", "*") \
            and re.fullmatch(r"\d+", minute or "") and re.fullmatch(r"\d+", hour or ""):
        return _F("an.t002", a1=int(hour), a2=int(minute), a3=expr)
    return str(expr)


def parse_trigger_time(task_meta):
    """Resolve the send time; returns (value, source field, display string).

    The platform's `triggerTime` (actual trigger time) is often empty -- the task is
    driven by crontab, or the scheduled job has not persisted the field yet. It must
    then fall back to `startDate` (task start date): otherwise the report reads a
    value while the Excel reads an empty one, and the same campaign shows two
    contradictory trigger times across two deliverables, leaving the reader unable to
    tell missing data from a genuinely absent trigger time.
    The display string names its source, so the reader knows whether the date is the
    actual trigger or the planned start date.
    """
    tm = task_meta or {}
    tz = tm.get("tzOffset")
    raw = tm.get("triggerTime")
    if raw not in (None, "", "null"):
        txt = str(raw).strip()
        if re.fullmatch(r"\d{10,13}", txt):     # 裸时间戳
            txt = ms_to_local_date(txt, tz) or txt
        return txt, "triggerTime", txt
    d = ms_to_local_date(tm.get("startDate"), tz)
    if d:
        return d, "startDate", _F("an.t003", a1=d)
    return None, None, None


def build_field_caveats(task_meta, metrics):
    """List the fields where one business volume is measured differently per endpoint.

    The platform task list (`task_list`) and the result retrieval endpoint
    (`task_data_overview`) each define "planned reach" their own way: `planNum`
    counts sends, `plan` counts people. Both are correct, but placing them side by
    side yields the wrong conclusion that they differ by nearly a hundred times. A
    discrepancy like this raises no error and only makes the reader miscalculate, so
    it must be stated outright rather than left for the reader to spot from the
    field names.
    """
    tm = task_meta or {}
    out = []
    plan = to_int((metrics or {}).get("plan"))

    pn = to_int(tm.get("planNum"))
    if plan and pn and pn != plan:
        out.append({
            "field": "planNum",
            "source": _L("an.025"),
            "value": pn,
            "counterpart": _F("an.t004", a1=plan),
            "note": _L("an.026"),
        })

    cu = to_int(tm.get("clusterUserNum"))
    if plan and cu and cu != plan:
        out.append({
            "field": "clusterUserNum",
            "source": _L("an.025"),
            "value": cu,
            "counterpart": f"plan = {plan}（task_data_overview）",
            "note": _L("an.027"),
        })
    return out


# ---------------------------------------------------------------- block parsers

def parse_overview(raw):
    """{dataList:[{key,value}]} -> {metric: value}

    External data, guarded level by level: a non-dict top level, a non-list
    dataList, or a single entry that is not a dict or lacks a key is skipped rather
    than raised. One bad record should not stop the whole report from being
    produced; skipped entries are logged.
    """
    if not isinstance(raw, dict):
        return None
    dl = as_dict(raw.get("data")).get("dataList")
    if not isinstance(dl, list):
        return None
    out = {}
    for item in dl:
        if not isinstance(item, dict):
            log(_L("an.028") % (item,))
            continue
        key = item.get("key")
        if key is None:
            log(_L("an.029") % (item,))
            continue
        out[str(key)] = to_int(item.get("value"))
    return out or None


def parse_time_series(raw):
    """detail_type=time -> [{date, metric: value}, ...] (the total row comes back separately)"""
    if not isinstance(raw, dict):
        return None, None
    d = as_dict(raw.get("data")).get("data")
    if not isinstance(d, dict) or not d.get("x"):
        return None, None
    xs = d.get("x")
    if not isinstance(xs, list):
        return None, None
    series = {}
    for item in d.get("y") or []:
        if not isinstance(item, dict):
            log(_L("an.030") % (item,))
            continue
        for k, v in item.items():
            # The shape is [{values:[...]}]; v[0] can be of any type too, so without a guard
            # `.get` would land on an int or a str.
            if isinstance(v, list) and v and isinstance(v[0], dict):
                series[k] = v[0].get("values") or []
            else:
                series[k] = []
    rows = []
    total_row = None
    for i, date in enumerate(xs):
        row = {"date": date}
        for k, vals in series.items():
            row[k] = to_int(vals[i]) if i < len(vals) else 0
        if date in ("total", _L("an.031"), "Total", "Overview", "overview"):
            total_row = row
        else:
            rows.append(row)
    return rows, total_row


def parse_instances(raw):
    """detail_type=instance -> [{instance_id, metric: value}, ...]"""
    if not isinstance(raw, dict):
        return None
    d = as_dict(raw.get("data")).get("data")
    if not isinstance(d, dict) or not d.get("z"):
        return None
    zs = d.get("z") or []
    if not isinstance(zs, list):
        # When z is a string, enumerate splits it into characters and emits fake instance rows
        log(_L("an.032") % type(zs).__name__)
        return None
    series = {}
    for item in d.get("y") or []:
        if not isinstance(item, dict):
            log(_L("an.033") % (item,))
            continue
        for k, v in item.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                series[k] = v[0].get("values") or []
            else:
                series[k] = []
    rows = []
    for i, inst in enumerate(zs):
        row = {"instance_id": inst}

        def pick(vals):
            return to_int(vals[i]) if i < len(vals) else 0

        for k, vals in series.items():
            row[k] = pick(vals)
        rows.append(row)
    return rows or None


def get_task_meta(raw_tasklist, task_id):
    """Pull the target task's metadata out of the task_list response."""
    if not isinstance(raw_tasklist, dict):
        return None
    ts = as_dict(raw_tasklist.get("data")).get("operationTaskDTOS") or []
    if not isinstance(ts, list):
        return None
    for t in ts:
        if isinstance(t, dict) and str(t.get("taskId")) == str(task_id):
            return t
    return None


def parse_conversion_indicators(task_meta):
    """Extract the conversion metric definition from completionIndicatorDef."""
    if not isinstance(task_meta, dict):
        return []
    d = parse_embedded(task_meta.get("completionIndicatorDef"))
    if not isinstance(d, dict):
        return []
    items = d.get("completionIndicators")
    if not isinstance(items, list):
        return []
    out = []
    for ci in items:
        if not isinstance(ci, dict):
            log(_L("an.034") % (ci,))
            continue
        ev = as_dict(ci.get("event"))
        unit_map = {"day": _L("an.035"), "hour": _L("an.036"), "minute": _L("an.037")}
        window_val = ci.get("touch_cycle_num")
        window_unit = unit_map.get(ci.get("touch_cycle_num_unit"), ci.get("touch_cycle_num_unit"))
        # bubbleInfo / taPropQuota can both be explicitly null or oddly shaped;
        # `ev.get("bubbleInfo", {})` only covers a missing key and still returns None
        # when the value itself is None.
        bubble = as_dict(ev.get("bubbleInfo"))
        quota = as_dict(ev.get("taPropQuota"))
        out.append({
            "event_name": ev.get("eventName"),
            "event_desc": ev.get("eventDesc") or bubble.get("displayName"),
            "window": f"{window_val}{window_unit}" if window_val else None,
            "window_value": window_val,
            "window_unit": ci.get("touch_cycle_num_unit"),
            "condition": f"{ev.get('op', '')} {ev.get('num', '')}".strip(),
            "analysis_type": quota.get("analysisDesc"),
            "raw": ci,
        })
    return out


def parse_experiment(raw_overview, raw_detail):
    """Parse the AB experiment report; None means the task has no experiment."""
    ov = as_dict(raw_overview)
    dd = as_dict(raw_detail)
    ov_data = as_dict(ov.get("data")).get("overviewData")
    detail_data = as_dict(dd.get("data")).get("detailData")
    # overviewData is expected to be a list of groups and detailData an object. When
    # upstream changes shape they can become a dict / str, and iterating them
    # directly either yields fake keys or blows up on `.get`.
    if not isinstance(ov_data, list):
        ov_data = None
    if not isinstance(detail_data, dict):
        detail_data = None
    if not ov_data and not detail_data:
        return None

    groups = []
    for g in ov_data or []:
        if not isinstance(g, dict):
            log(_L("an.038") % (g,))
            continue
        groups.append({
            "group_id": g.get("expGroupId"),
            "group_name": g.get("expGroupName"),
            "group_type": g.get("expGroupType"),
            "group_role": {1: _L("an.039"), 2: _L("an.040")}.get(g.get("expGroupType"), _L("an.041")),
            "success_user_num": to_int(g.get("successUserNum")),
            "lift_rate": g.get("liftRate"),
            "ci_floor": g.get("confidenceIntervalFloor"),
            "ci_ceil": g.get("confidenceIntervalCeil"),
            "significance_level": g.get("significanceLevel"),
            "win": g.get("win"),
        })

    # Detail matrix: headers are metric keys, values[date][group] holds the numbers
    matrix = None
    if detail_data:
        def _list(key):
            v = detail_data.get(key)
            return v if isinstance(v, list) else []

        headers = _list("headers")
        glist = _list("expGroupList")
        values = _list("values")
        dates = _list("x")
        inst_ids = _list("taskInstanceIdList")
        rows = []
        for di, date in enumerate(dates):
            if date in ("total", _L("an.031")):
                continue
            for gi, g in enumerate(glist):
                if not isinstance(g, dict):
                    continue
                try:
                    raw_vals = values[di][gi]
                except (IndexError, TypeError):
                    continue
                if not isinstance(raw_vals, list):
                    raw_vals = []
                rec = {
                    "date": date,
                    "instance_id": inst_ids[di] if di < len(inst_ids) else "",
                    "group_name": g.get("expGroupName"),
                    "group_id": g.get("expGroupId"),
                }
                for hi, h in enumerate(headers):
                    v = raw_vals[hi] if hi < len(raw_vals) else None
                    rec[str(h)] = None if v in ("-", "", None) else to_int(v)
                rows.append(rec)
        matrix = rows or None

    # experiment conclusion
    ctrl = next((g for g in groups if g["group_role"] == _L("an.039")), None)
    treat = next((g for g in groups if g["group_role"] == _L("an.040")), None)
    has_sig = any(g.get("significance_level") is not None for g in groups)
    conclusion, verdict = None, None
    if ctrl and treat:
        lift = treat.get("lift_rate")
        sig = treat.get("significance_level")
        win = treat.get("win")
        if not has_sig and (lift is None or lift == 0):
            verdict = _L("an.042")
            conclusion = (_L("an.043"))
        elif lift is None:
            verdict = _L("an.042")
            conclusion = _L("an.044")
        elif not has_sig:
            verdict = _L("an.045")
            conclusion = _F("an.t005", a1=lift)
        elif win is True and (sig is None or sig < 0.05):
            verdict = _L("an.046")
            conclusion = _F("an.t006", a1=lift, a2=sig)
        elif isinstance(win, bool) and not win and lift is not None and abs(lift) < 0.05:
            verdict = _L("an.047")
            conclusion = _F("an.t007", a1=lift)
        else:
            verdict = _L("an.045")
            conclusion = _F("an.t008", a1=lift)
    return {
        "group_count": len(groups),
        "groups": groups,
        "matrix": matrix,
        "verdict": verdict,
        "conclusion": conclusion,
        "has_significance": has_sig,
    }


# ---------------------------------------------------------------- core computation

def build_funnel(metrics):
    """Build the funnel: stage rates, cumulative rates and drop-off volumes."""
    stages = []
    prev_val = None
    base_val = None
    for key, label, desc in FUNNEL_STAGES:
        if key not in metrics:
            continue
        v = metrics[key]
        if base_val is None:
            base_val = v
        stage_conv = safe_div(v, prev_val) if prev_val is not None else None
        overall_conv = safe_div(v, base_val) if base_val else None
        drop = (prev_val - v) if prev_val is not None else None
        drop_rate = safe_div(drop, prev_val) if (prev_val is not None and drop is not None) else None
        stages.append({
            "metric_key": key,
            "stage": label,
            "desc": desc,
            "value": v,
            "stage_conv": stage_conv,
            "overall_conv": overall_conv,
            "drop": drop,
            "drop_rate": drop_rate,
        })
        prev_val = v
    return stages


def find_data_break(funnel):
    """
    Locate the data-chain break: the first stage whose value is 0 and whose every
    downstream stage is 0 as well.

    This is the case that must be told apart from real churn -- say the platform
    never returns view/click, so the impression stage collapses to 0. That is not
    users leaving, it is missing data. Confusing the two produces a completely wrong
    diagnosis.
    """
    for i, s in enumerate(funnel):
        if s["metric_key"] == "plan":
            continue
        if s["value"] == 0 and all(x["value"] == 0 for x in funnel[i:]):
            upstream = funnel[i - 1] if i > 0 else None
            downstream = [x["stage"] for x in funnel[i:]]
            if upstream is None:
                # The break sits on the funnel's first stage: common in mode B (no impression event configured, or the event carries no data)
                reason = (_F("an.t009", a1=s['stage'], a2='、'.join(downstream)))
            else:
                reason = (_F("an.t010", a1=s['stage'], a2='、'.join(downstream), a3=upstream['stage'], a4=upstream['value']))
            return {
                "metric_key": s["metric_key"],
                "stage": s["stage"],
                "upstream_stage": upstream["stage"] if upstream else None,
                "upstream_value": upstream["value"] if upstream else None,
                "downstream_stages": downstream,
                "reason": reason,
            }
    return None


def find_max_bleed(rates, data_break):
    """
    Locate the bleeding point: only a stage rate below the industry benchmark counts
    as a problem, ranked by how many users could be recovered.

    Ranking by "largest absolute drop-off" is deliberately not used -- the
    impression-to-click stage always loses more than 95% (CTR is typically 3-5%), so
    absolute ranking would point at that stage forever, which is noise rather than
    insight. Only a stage whose actual rate sits below its benchmark is worth
    investing in, and its potential gain is estimated as
    "(benchmark - actual) x denominator volume".

    The data break and every stage downstream of it are excluded, because their data
    is missing.
    """
    brk_key = (data_break or {}).get("metric_key")
    downstream = set((data_break or {}).get("downstream_stages") or [])

    cands = []
    for r in rates:
        if r["value"] is None or r["threshold"] is None:
            continue
        if r["value"] >= r["threshold"]:
            continue
        stage_label = METRIC_LABELS.get(r["numerator_metric"], r["numerator_metric"])
        # The data break and its downstream stages are excluded from the bleeding-point test, being data-missing
        if stage_label in downstream:
            continue
        den = r.get("denominator") or 0
        # round rather than int: both the threshold and the actual rate are binary
        # floats, (0.03-0.02)*12000 is 119.999... (14 nines) under IEEE754, and
        # truncating with int() would reliably undercount by one person.
        recoverable = round((r["threshold"] - r["value"]) * den)
        cands.append({
            "metric_key": r["numerator_metric"],
            "stage": stage_label,
            "rate_name": r["name"],
            "value": r["value"],
            "threshold": r["threshold"],
            "denominator": den,
            "recoverable": recoverable,
            "reason": (_F("an.t011", a1=r['name'], a2=r['value'], a3=r['threshold'], a4=recoverable, a5=den)),
        })

    if not cands:
        return None
    return max(cands, key=lambda x: x["recoverable"])


def build_rates(metrics):
    """Absolute stage rates against their benchmarks, including degraded denominators."""
    out = []
    for name, num_k, den_k, desc in RATE_DEFS:
        num, den = metrics.get(num_k), metrics.get(den_k)
        den_used = den_k
        degraded = False

        # Degrade: with no view data, approximate the click rate using send volume as denominator
        if name == _L("an.019") and not den and metrics.get("trigger"):
            den, den_used, degraded = metrics.get("trigger"), "trigger", True
        # Degrade: with no click data, approximate the conversion rate using successful sends as denominator
        if name == _L("an.021") and not den and metrics.get("trigger"):
            den, den_used, degraded = metrics.get("trigger"), "trigger", True

        val = safe_div(num, den) if num is not None and den is not None else None
        # A ratio above 100% is physically impossible: the numerator is meant to be a
        # subset of the denominator (anyone who clicks was necessarily shown the ad).
        # When it does appear, upstream has almost certainly failed to report the
        # denominator event -- only click arrives, no view. Judging that as "normal"
        # against the benchmark would read missing events as excellent performance.
        impossible = val is not None and val > 1.0

        flag, advice, threshold = "⚪", _L("an.048"), None
        for bn, bt, cmp_op, bf, ba in BENCHMARKS:
            if bn != name:
                continue
            threshold = bt
            if val is None:
                flag, advice = "⚪", _L("an.048")
            elif impossible:
                flag, advice = "🔴", _L("an.049")
            elif cmp_op == "lt" and val < bt:
                flag, advice = bf, ba
            elif cmp_op == "gt" and val > bt:
                flag, advice = bf, ba
            else:
                flag, advice = "🟢", _L("an.050")
            break
        else:
            # Metrics with no benchmark configured (reach rate, for instance)
            if val is None:
                flag, advice = "⚪", _L("an.048")
            elif impossible:
                flag, advice = "🔴", _L("an.049")
            else:
                flag, advice = "⚪", _L("an.051")

        out.append({
            "name": name,
            "numerator_metric": num_k,
            "numerator": num,
            "denominator_metric": den_used,
            "denominator": den,
            "denominator_declared": den_k,
            "degraded": degraded,
            "value": val,
            "threshold": threshold,
            "flag": flag,
            "advice": advice,
            "desc": desc,
        })
    return out


def build_diagnosis(funnel, rates, experiment, data_break, max_bleed):
    """Problem localisation, ordered by priority: data break > invalid experiment > audience mismatch > content and timing."""
    issues = []

    # 0. Data consistency (tied with the data break for top priority -- once the
    #    numbers themselves are untrustworthy, every later conclusion is void.
    #    Judging purely by value would read missing events as excellent results.)
    impossible = [r for r in rates if r["value"] is not None and r["value"] > 1.0]
    if impossible:
        shown = "、".join("%s %.1f%%" % (r["name"], r["value"] * 100) for r in impossible)
        issues.append({
            "priority": 1,
            "category": _L("an.052"),
            "severity": "🔴",
            "title": _F("an.t012", a1=shown),
            "detail": (_L("an.053")),
            "evidence": _L("an.054"),
        })

    # 1. Data chain break (top priority -- it decides whether the rest can be trusted)
    if data_break:
        issues.append({
            "priority": 1,
            "category": _L("an.055"),
            "severity": "🔴",
            "title": _F("an.t013", a1=data_break['stage']),
            "detail": data_break["reason"],
            "evidence": _L("an.054"),
        })

    # 2. Bleeding point (a stage rate below its benchmark)
    if max_bleed:
        issues.append({
            "priority": 2,
            "category": _L("an.056"),
            "severity": "🟠",
            # "below benchmark" is used instead of a bare `<`: the report renderer
            # HTML-escapes the whole analysis payload, so a raw angle bracket would land in
            # the Markdown source as an HTML entity.
            "title": _F("an.t014", a1=max_bleed['rate_name'], a2=max_bleed['value'], a3=max_bleed['threshold']),
            "detail": max_bleed["reason"],
            "evidence": _L("an.054"),
        })

    # The data break and its downstream stages are necessarily 0, so they are not reported again
    missing_stages = set((data_break or {}).get("downstream_stages") or [])

    # 3. Channel problem (send success rate) -- skipped when already reported as a bleeding point, to avoid a duplicate
    bleed_rate = (max_bleed or {}).get("rate_name")
    send_rate = next((r for r in rates if r["name"] == _L("an.015")), None)
    if (send_rate and send_rate["value"] is not None and send_rate["value"] < 0.90
            and bleed_rate != _L("an.015") and _L("an.005") not in missing_stages):
        issues.append({
            "priority": 2,
            "category": _L("an.057"),
            "severity": "🔴",
            "title": _F("an.t015", a1=send_rate['value']),
            "detail": _L("an.058"),
            "evidence": _L("an.054"),
        })

    # 4. Invalid AB experiment
    if experiment and experiment.get("verdict") in (_L("an.047"), _L("an.042")):
        issues.append({
            "priority": 2,
            "category": _L("an.059"),
            "severity": "🟡",
            "title": _F("an.t016", a1=experiment['verdict']),
            "detail": experiment.get("conclusion") or "",
            "evidence": _L("an.060"),
        })

    # 5. Content and timing (click rate) -- as above, skipped when a bleeding point or the data break already covers it
    ctr = next((r for r in rates if r["name"] == _L("an.019")), None)
    if (ctr and ctr["value"] is not None and ctr["value"] < 0.03
            and bleed_rate != _L("an.019") and _L("an.009") not in missing_stages):
        note = _L("an.061") if ctr.get("degraded") else ""
        issues.append({
            "priority": 4,
            "category": _L("an.062"),
            "severity": "🟠",
            "title": _F("an.t017", a1=ctr['value'], a2=note),
            "detail": _L("an.063"),
            "evidence": _L("an.054"),
        })

    if not issues:
        issues.append({
            "priority": 9,
            "category": _L("an.064"),
            "severity": "🟢",
            "title": _L("an.065"),
            "detail": _L("an.066"),
            "evidence": _L("an.054"),
        })
    return sorted(issues, key=lambda x: x["priority"])


def build_recommendations(funnel, rates, experiment, issues):
    """Turn each problem into concrete, actionable steps, each with its expected impact."""
    recs = []
    for it in issues:
        if it["category"] == _L("an.055"):
            stage = it["title"].split("「")[1].split("」")[0]
            recs.append({
                "action": _F("an.t018", a1=stage),
                "detail": _L("an.067"),
                "expected": _L("an.068"),
                "priority": 1,
            })
        elif it["category"] == _L("an.056"):
            recs.append({
                "action": _F("an.t019", a1=it['title'].split('「')[1].split('」')[0]),
                "detail": _L("an.069"),
                "expected": _L("an.070"),
                "priority": 2,
            })
        elif it["category"] == _L("an.057"):
            recs.append({
                "action": _L("an.071"),
                "detail": _L("an.072"),
                "expected": _L("an.073"),
                "priority": 2,
            })
        elif it["category"] == _L("an.059"):
            recs.append({
                "action": _L("an.074"),
                "detail": _L("an.075"),
                "expected": _L("an.076"),
                "priority": 2,
            })
        elif it["category"] == _L("an.062"):
            recs.append({
                "action": _L("an.077"),
                "detail": _L("an.078"),
                "expected": _L("an.079"),
                "priority": 4,
            })

    # "No anomaly" must not mean "no advice" -- the report owes the business a next
    # step. Otherwise a report where every stage is on target ends on an empty
    # advice section and the reader has nothing to act on.
    if not recs:
        ctr = next((r for r in rates if r["name"] == _L("an.019") and r["value"] is not None), None)
        conv = next((r for r in rates if r["name"] == _L("an.021") and r["value"] is not None), None)
        if ctr or conv:
            recs.append({
                "action": _L("an.080"),
                "detail": _L("an.081"),
                "expected": _L("an.082"),
                "priority": 3,
            })
            recs.append({
                "action": _L("an.083"),
                "detail": _L("an.084"),
                "expected": _L("an.085"),
                "priority": 4,
            })
        else:
            recs.append({
                "action": _L("an.086"),
                "detail": _L("an.087"),
                "expected": _L("an.088"),
                "priority": 1,
            })
    return recs


def build_validation_plan(metrics, rates, experiment):
    """How to verify the optimisation.

    When no metric can be computed (nothing was returned), indicators is empty --
    and that has to be stated explicitly as "no baseline could be established". An
    empty verification plan must not pass silently, or the reader will assume a
    comparison baseline was actually provided.
    """
    indicators = [
        {"metric": r["name"], "baseline": r["value"], "target": _target(r)}
        for r in rates if r["value"] is not None
    ]
    steps = [
        _L("an.089"),
        _L("an.090"),
        _L("an.091"),
        _L("an.092"),
    ]
    notes = []
    if not indicators:
        notes.append(
            _L("an.093")
        )
        steps.insert(0, _L("an.094"))
    return {
        "method": _L("an.095") if not (experiment and experiment.get("group_count", 0) >= 2)
                  else _L("an.096"),
        "baseline_available": bool(indicators),
        "indicators": indicators,
        "steps": steps,
        "notes": notes,
    }


def _target(rate):
    """Propose targets: below-benchmark stages return to their benchmark, on-target ones improve slightly."""
    if rate["threshold"] is None:
        return None
    if rate["value"] is not None and rate["value"] < rate["threshold"]:
        return rate["threshold"]
    return round(min(rate["value"] * 1.2, 1.0), 4) if rate["value"] is not None else None


def build_degradations(blocks_present, metrics, experiment_meta, mode="A",
                       event_meta=None):
    """Record every degradation and precision loss so the report can declare confidence. Wording varies by data-source mode."""
    d = []
    src = _L("an.097") if mode == "A" else _L("an.098")

    if "time" not in blocks_present:
        d.append({"item": _L("an.099"), "impact": _L("an.100"), "loss": "~15%"})
    if "instance" not in blocks_present and mode == "A":
        d.append({"item": _L("an.101"), "impact": _L("an.102"), "loss": "~10%"})
    if not experiment_meta:
        note = (_L("an.103") if mode == "A"
                else _L("an.104"))
        d.append({"item": _L("an.105"), "impact": note, "loss": "~20%"})
    elif not experiment_meta.get("has_significance"):
        d.append({"item": _L("an.106"), "impact": _L("an.107"), "loss": "~15%"})

    if metrics.get("view", 0) == 0:
        impact = (_L("an.108")
                  if mode == "A" else
                  _L("an.109"))
        d.append({"item": _L("an.110"), "impact": impact, "loss": "~25%"})
    if metrics.get("click", 0) == 0:
        impact = (_L("an.111")
                  if mode == "A" else
                  _L("an.112"))
        d.append({"item": _L("an.113"), "impact": impact, "loss": "~25%"})
    if metrics.get("main", 0) == 0:
        impact = (_L("an.114")
                  if mode == "A" else
                  _L("an.115"))
        d.append({"item": _L("an.116"), "impact": impact, "loss": "~20%"})

    if mode == "B" and metrics.get("plan") is None:
        d.append({"item": _L("an.117"), "impact": _L("an.118"), "loss": _L("an.119")})

    # The discriminator (strategy_id / campaign / channel) is what isolates this
    # campaign's events from overlapping sends in the same window. Missing it
    # means the audience is the whole window; providing it but failing to apply
    # it (1.x silently drops `filters`) leaves the same contamination, only with
    # the user believing the result was isolated. Both are the same ~20% hit, so
    # both are stated - the second so an unfiltered number is not trusted as a
    # filtered one.
    if mode == "B":
        disc = (event_meta or {}).get("discriminator")
        applied = (event_meta or {}).get("discriminator_applied")
        if not disc:
            d.append({"item": _L("an.120"),
                      "impact": _L("an.121"), "loss": "~20%"})
        elif not applied:
            d.append({"item": _L("an.120"),
                      "impact": _L("an.122") % str(disc.get("property")),
                      "loss": "~20%"})

    # A truncated result is not a degraded measurement, it is an incomplete one:
    # every row returned is correct, they are simply not all of them. That
    # distinction matters because it cannot be repaired by reasoning about
    # precision - the missing days are missing outright - so it must reach the
    # same statement as the conclusion. Mode B only; mode A reads its payload
    # from endpoints that do not truncate.
    truncated = (event_meta or {}).get("truncated") or []
    if truncated:
        d.append({"item": _L("an.123"),
                  "impact": _L("an.124") % "、".join(map(str, truncated)),
                  "loss": _L("an.125")})

    # A step the platform rendered in an unexpected column is *unknown*, not
    # zero. Those two readings support opposite conclusions - "nobody
    # converted" versus "we could not measure it" - so the gap has to be
    # stated wherever the funnel is.
    unmapped = (event_meta or {}).get("unmapped_steps") or []
    if unmapped:
        d.append({"item": _L("an.126"),
                  "impact": _L("an.127") % "、".join(map(str, unmapped)),
                  "loss": _L("an.128")})
    return d


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=_L("an.129"))
    ap.add_argument("--raw-dir", default="tmp", help=_L("an.130"))
    ap.add_argument("--out", default=None, help=_L("an.131"))
    ap.add_argument("--task-id", default=None, help=_L("an.132"))
    ap.add_argument("--mode", default="A", choices=["A", "B"], help=_L("an.133"))
    ap.add_argument("--strategy-name", default=None, help=_L("an.134"))
    args = ap.parse_args()

    rd = args.raw_dir
    out_path = args.out or os.path.join(rd, "analysis.json")

    raw_overview = load_json(os.path.join(rd, "raw_overview.json"))
    raw_time = load_json(os.path.join(rd, "raw_detail_time.json"))
    raw_inst = load_json(os.path.join(rd, "raw_detail_instance.json"))
    raw_exp_ov = load_json(os.path.join(rd, "raw_exp_overview.json"))
    raw_exp_dt = load_json(os.path.join(rd, "raw_exp_detail.json"))
    raw_tl = load_json(os.path.join(rd, "raw_tasklist.json"))
    event_meta = as_dict(load_json(os.path.join(rd, "raw_event_meta.json")))

    metrics = parse_overview(raw_overview)
    if not metrics:
        log(_L("an.135"))
        sys.exit(2)

    blocks_present = []
    if raw_time:
        blocks_present.append("time")
    if raw_inst:
        blocks_present.append("instance")
    if raw_exp_ov or raw_exp_dt:
        blocks_present.append("experiment")

    timeline, time_total = parse_time_series(raw_time)
    instances = parse_instances(raw_inst)

    # task_id fallback: prefer the CLI value, then read raw_meta.json written by
    # Step 2. Step 2 nests the identifiers under "object" (object.task_id /
    # flow_id / config_id) rather than at the top level -- both shapes must be
    # accepted, or the metadata is silently lost and the report header goes blank.
    if not args.task_id:
        m2 = load_json(os.path.join(rd, "raw_meta.json")) or {}
        obj = m2.get("object") if isinstance(m2.get("object"), dict) else {}
        args.task_id = (m2.get("task_id") or m2.get("object_id")
                        or obj.get("task_id") or obj.get("common_id"))
        if args.task_id:
            log(_F("an.t020", a1=args.task_id))

    task_meta = get_task_meta(raw_tl, args.task_id) if args.task_id else None
    if args.task_id and task_meta is None:
        log(_F("an.t021", a1=args.task_id))
    if not args.task_id and args.mode == "A":
        log(_L("an.136"))
    indicators = parse_conversion_indicators(task_meta)
    experiment = parse_experiment(raw_exp_ov, raw_exp_dt)

    funnel = build_funnel(metrics)
    rates = build_rates(metrics)
    data_break = find_data_break(funnel)
    max_bleed = find_max_bleed(rates, data_break)
    degradations = build_degradations(blocks_present, metrics, experiment,
                                      args.mode, event_meta)
    issues = build_diagnosis(funnel, rates, experiment, data_break, max_bleed)
    recs = build_recommendations(funnel, rates, experiment, issues)
    validation = build_validation_plan(metrics, rates, experiment)

    # ---- metadata
    mode_label = {"A": _L("an.137"), "B": _L("an.138")}[args.mode]
    strategy_name = args.strategy_name or (task_meta or {}).get("taskName") or args.task_id or _L("an.139")
    exp_conf = as_dict(parse_embedded((task_meta or {}).get("expConfig")))
    tz = (task_meta or {}).get("tzOffset")
    trigger_time, trigger_time_source, trigger_time_label = parse_trigger_time(task_meta)
    if task_meta and not trigger_time_source:
        log(_L("an.140"))
    caveats = build_field_caveats(task_meta, metrics)
    if caveats:
        log(_F("an.t022", a1=len(caveats)) + "、".join(c["field"] for c in caveats))
    meta = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": args.mode,
        "mode_label": mode_label,
        "project_id": (task_meta or {}).get("projectId") or (event_meta or {}).get("project_id"),
        "task_id": args.task_id or (task_meta or {}).get("taskId"),
        "strategy_name": strategy_name,
        "task_name": (task_meta or {}).get("taskName"),
        "channel": (task_meta or {}).get("channelName") or (event_meta or {}).get("channel"),
        "channel_type": (task_meta or {}).get("channelType"),
        "status": (task_meta or {}).get("statusName"),
        "trigger_time": trigger_time,
        "trigger_time_source": trigger_time_source,
        "trigger_time_label": trigger_time_label,
        "trigger_rule": humanize_crontab((task_meta or {}).get("triggerCrontab")),
        "creator": (task_meta or {}).get("creator"),
        "timezone": f"UTC+{tz}" if tz is not None else None,
        "target_cluster": (task_meta or {}).get("clusterKey"),
        "target_cluster_type": (task_meta or {}).get("targetClusterType"),
        "experiment_enabled": bool(exp_conf.get("enableExp")),
        "frequency_limit_enabled": as_dict(parse_embedded((task_meta or {}).get("frequencyLimits"))).get("enableFrequencyLimits"),
        "conversion_indicators": indicators,
        "blocks_present": blocks_present,
        "event_meta": event_meta,          # 模式 B 专有：事件链 / 归因窗口
        "data_range": {
            "start": min((r["date"] for r in timeline), default=None) if timeline else None,
            "end": max((r["date"] for r in timeline), default=None) if timeline else None,
            "days": len(timeline) if timeline else None,
        },
    }

    analysis = {
        "meta": meta,
        "metrics": metrics,
        "funnel": funnel,
        "rates": rates,
        "max_bleed": max_bleed,
        "data_break": data_break,
        "timeline": timeline or [],
        "timeline_total": time_total,
        "instances": instances or [],
        "experiment": experiment,
        "segments": [],          # 模式 A 沙盒无人群属性分组能力，留空并记入降级
        "issues": issues,
        "recommendations": recs,
        "validation_plan": validation,
        "degradations": degradations,
        "field_caveats": caveats,
    }

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=1)

    log(_F("an.t023", a1=out_path))
    log(_F("an.t024", a1=strategy_name, a2=metrics))
    log(_F("an.t025", a1=len(funnel), a2=len(rates), a3=len(issues), a4=len(degradations)))


if __name__ == "__main__":
    main()
