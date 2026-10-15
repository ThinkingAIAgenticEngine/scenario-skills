#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 5 -- render the effectiveness analysis report (shared by both data modes).

Reads tmp/analysis.json and renders the six-section Markdown report.
All six sections are required: conclusion first / effect overview / attribution
analysis / problem localisation / optimisation advice / verification plan.

Usage:
    python3 generate_report.py --analysis tmp/analysis.json --out-dir output \
        --strategy-name "shiyan" --excel-name "shiyan_detail_20260914.xlsx"
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wording import _L, _F  # noqa: E402

SECTION_TITLES = [_L("gr.001"), _L("gr.002"), _L("gr.003"), _L("gr.004"), _L("gr.005"), _L("gr.006")]


def log(msg):
    print(f"[report] {msg}", file=sys.stderr)


def safe_filename(s):
    s = re.sub(r'[\\/:*?"<>|\n\r\t]', "_", str(s or ""))
    return s.strip().strip(".")[:60] or "unnamed"


def esc(s):
    """Turn HTML metacharacters in external text into entities.

    The report is Markdown, but renderers such as GitHub or Typora execute inline
    HTML. Strategy names, channels and event names all come from the client side or
    from platform responses, so a single `<img src=x onerror=...>` would run for
    whoever opens the report.
    Escaped text still renders as the original, so normal names are unaffected.
    """
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def esc_deep(v):
    """Recursively escape dict / list / str; numbers and booleans pass through."""
    if isinstance(v, str):
        return esc(v)
    if isinstance(v, dict):
        return {k: esc_deep(x) for k, x in v.items()}
    if isinstance(v, list):
        return [esc_deep(x) for x in v]
    return v


def tcell(v):
    """For Markdown table cells only.

    A `|` is parsed as a column separator and stretches a 3-column table into 4
    columns; a newline splits one row into two. Both are structural breakages that
    only surface once external text reaches a table, and both fail silently -- the
    table is simply misaligned. `\\|` still renders as `|`, so readability is
    preserved.
    """
    return str(v).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def pct(v, digits=1):
    if v is None:
        return "—"
    try:
        return f"{v * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def _material_degradations(a):
    """Degradations that affect how far the conclusion can be trusted.

    Degradations come in two kinds: those that genuinely change the conclusion
    (~20%, ~15%, conclusion unusable ...) and those explicitly marked as not
    affecting it ("does not affect the conclusion"). Only the former need a coverage
    caveat appended to the verdict -- because the risk of "found no problem" being
    read as "no problem" comes precisely from the unobserved stages hidden behind a
    degradation notice (for example a push that never arrived, invisible because the
    channel layer is unobservable).
    """
    return [d for d in (a.get("degradations") or [])
            if (d.get("loss") or "") not in ("", _L("gr.007"))]


def overall_verdict(a):
    """One-line effectiveness verdict."""
    if a.get("data_break"):
        return (_L("gr.008"),
                _L("gr.009"))
    issues = a.get("issues") or []
    # "Data consistency" is a separate axis from effectiveness: it says the number
    # itself cannot be trusted. Reporting it as "below expectation" sends the client
    # off to tune the strategy, when the real fix is to repair event ingestion.
    if any(i.get("category") == _L("gr.010") for i in issues):
        return (_L("gr.011"),
                _L("gr.012"))
    reds = [i for i in issues if i.get("severity") == "🔴"]
    oranges = [i for i in issues if i.get("severity") == "🟠"]
    if reds:
        verdict, desc = _L("gr.013"), _L("gr.014")
    elif oranges:
        verdict, desc = _L("gr.015"), _L("gr.016")
    else:
        verdict, desc = _L("gr.017"), _L("gr.018")

    # When data is thin, "on target / good" only holds for the observable stages.
    # Unobserved upstream layers take no part in the verdict, and that has to be
    # stated explicitly on the verdict line -- otherwise "found no problem" reads as
    # "no problem", especially when the real bleeding point sits in an unobserved
    # stage.
    mat = _material_degradations(a)
    if mat:
        names = "、".join(d["item"] for d in mat)
        desc += (_F("gr.t001", a1=names))
    return verdict, desc


def core_findings(a):
    """The 3 core findings."""
    out = []
    mb = a.get("max_bleed")
    if mb:
        out.append(_F("gr.t002", a1=mb['rate_name'], a2=pct(mb['value']), a3=pct(mb['threshold']), a4=mb['recoverable'], a5=mb['denominator']))
    db = a.get("data_break")
    if db:
        out.append(_F("gr.t003", a1=db['stage'], a2=db['upstream_stage'], a3=db['upstream_value']))
    exp = a.get("experiment")
    if exp and exp.get("groups"):
        out.append(_F("gr.t004", a1=exp.get('verdict'), a2=exp.get('conclusion')))
    rates = a.get("rates") or []
    # A bleeding point already covered in prose is not repeated -- saying the same
    # thing twice dilutes the point.
    already = {mb["rate_name"]} if mb else set()
    abnormal = [r for r in rates if r["flag"] in ("🔴", "🟠") and r["name"] not in already]
    for r in abnormal[:2]:
        if r["value"] is None:
            continue
        note = _L("gr.019") if r.get("degraded") else ""
        # The direction of the baseline comparison depends on the problem type: a ratio
        # above 100% is a data anomaly, so the actual value is "above" the baseline, and
        # forcing the "below baseline" phrasing would produce a self-contradictory
        # sentence.
        if r["value"] > 1.0:
            cmp_txt = _L("gr.020")
        elif r["threshold"] is not None:
            cmp_txt = _F("gr.t005", a1=pct(r['threshold']))
        else:
            cmp_txt = ""
        sep = ("，" + cmp_txt) if cmp_txt else ""
        out.append(_F("gr.t006", a1=r['name'], a2=pct(r['value']), a3=sep, a4=note, a5=r['advice']))
    if not out:
        vals = [f"{r['name']} {pct(r['value'])}" for r in rates if r["value"] is not None]
        if vals:
            out.append(_L("gr.021") + "；".join(vals) + _L("gr.022"))
            mr = a.get("metrics") or {}
            reach = [f"{k}={v}" for k, v in mr.items()]
            if reach:
                out.append(_L("gr.023") + "、".join(reach) + _L("gr.024"))
        else:
            out.append(_L("gr.025"))
    return out[:3]


def render(a, excel_name):
    # External text (strategy name / channel / event name / discriminator property
    # / client-defined fields) does not only appear in `meta` -- the analysis layer
    # splices it into the wording of `degradations` / `issues`, and that wording
    # lands in the Markdown tables. Escaping `meta` alone is not enough: in practice
    # `discriminator.property` leaked out of the degradation table verbatim, both
    # executing inline HTML and using a `|` to stretch a 3-column table into 4.
    # So the whole analysis payload is deep-escaped here: the report body renders
    # from entities, the Markdown output matches the original, and normal names are
    # unaffected. Deliverable filenames take the raw `meta` in main(), skipping
    # this.
    a = esc_deep(a)
    m = a.get("meta") or {}
    excel_name = esc(excel_name)
    lines = []
    A = lines.append

    # ---------------- header metadata
    A(_F("gr.t007", a1=m.get('strategy_name')))
    A("")
    A(_F("gr.t008", a1=m.get('mode_label')))
    ci = m.get("conversion_indicators") or []
    ci_text = "；".join(
        f"`{c.get('event_name')}`（{c.get('event_desc') or '—'}）"
        + (_F("gr.t009", a1=c['window']) if c.get("window") else "")
        for c in ci
    ) or _L("gr.026")

    if m.get("mode") == "B":
        em = m.get("event_meta") or {}
        chain = " → ".join(em.get("event_chain") or []) or _L("gr.027")
        win = em.get("attribution_window") or {}
        unit_cn = {"hour": _L("gr.028"), "day": _L("gr.029"), "minute": _L("gr.030")}
        win_txt = (_F("gr.t010", a1=win.get('value'), a2=unit_cn.get(win.get('unit'), win.get('unit')))
                   if win else "")
        A(_F("gr.t011", a1=m.get('strategy_name'), a2=chain, a3=win_txt))
        # Whether the discriminator property actually became a query filter decides
        # whether this batch is "the current campaign" or "a blend of every campaign in
        # the window". When it is applied, isolation must be stated as holding; when it
        # is not (1.x), it must be flagged, or an unisolated figure gets read as if it
        # had been isolated.
        disc = em.get("discriminator")
        if disc:
            if em.get("discriminator_applied"):
                A(_F("gr.t012", a1=disc.get('property'), a2=disc.get('value')))
            else:
                A(_F("gr.t013", a1=disc.get('property')))
    else:
        A(_F("gr.t014", a1=m.get('task_name') or m.get('strategy_name'), a2=m.get('task_id'), a3=ci_text))

    channel_txt = m.get("channel") or (_L("gr.031") if m.get("mode") == "B" else "—")
    rule_txt = m.get("trigger_rule")
    # Timezone and source flag share one pair of parentheses, avoiding stacked
    # brackets such as "(task start date)(UTC+8)"; the source flag appears only when
    # the actual trigger time is missing and the task start date was used instead.
    trigger_txt = m.get("trigger_time") or m.get("data_range", {}).get("start") or "—"
    tz_txt = m.get("timezone") or "—"
    if m.get("trigger_time_source") == "startDate":
        trigger_txt = _F("gr.t015", a1=trigger_txt, a2=tz_txt)
    else:
        trigger_txt = f"{trigger_txt}（{tz_txt}）"
    A(_F("gr.t016", a1=channel_txt, a2=trigger_txt)
      + (_F("gr.t017", a1=rule_txt) if rule_txt else "")
      + "  ")
    A(_F("gr.t018", a1=m.get('data_range', {}).get('start'), a2=m.get('data_range', {}).get('end'), a3=m.get('data_range', {}).get('days'), a4=m.get('generated_at')))
    A(_F("gr.t019", a1=excel_name))
    A("")

    # confidence statement
    if a["degradations"]:
        A(_L("gr.032"))
        A(">")
        A(_L("gr.033"))
        A("> |---|---|---|")
        for d in a["degradations"]:
            A(f"> | {tcell(d['item'])} | {tcell(d['impact'])} | {tcell(d['loss'])} |")
        A("")

    # Caliber note: the same business volume is measured differently per endpoint,
    # so stating it explicitly keeps readers from miscomputing.
    cavs = a.get("field_caveats") or []
    if cavs:
        A(_L("gr.034"))
        A(">")
        for c in cavs:
            A(f"> - **{c.get('field')}**：{c.get('source')} = {c.get('value')}；"
              f"{c.get('counterpart')}。{c.get('note')}")
        A("")

    A("---")
    A("")

    # ---------------- 1. Conclusion first
    verdict, verdict_desc = overall_verdict(a)
    A(_F("gr.t020"))
    A("")
    A(_F("gr.t021", a1=verdict, a2=verdict_desc))
    A("")
    A(_L("gr.035"))
    A("")
    for i, f in enumerate(core_findings(a), 1):
        A(f"{i}. {f}")
    A("")
    recs = a.get("recommendations") or []
    if recs:
        A(_L("gr.036"))
        A("")
        for r in recs[:3]:
            A(f"- **{r['action']}** —— {r['expected']}")
        A("")

    # ---------------- 2. Effect overview
    A(_L("gr.037"))
    A("")
    A(_L("gr.038"))
    A("")
    A(_L("gr.039"))
    A("|---|---|---|---|---|---|---|")
    brk_key = (a.get("data_break") or {}).get("metric_key")
    downstream = (a.get("data_break") or {}).get("downstream_stages") or []
    for s in a["funnel"]:
        note = ""
        if s["metric_key"] == brk_key:
            note = _L("gr.040")
        elif s["metric_key"] in downstream:
            note = _L("gr.041")
        A(f"| {tcell(s['stage'])} | {s['value']} | {pct(s['stage_conv'])} | {pct(s['overall_conv'])} | "
          f"{'—' if s['drop'] is None else s['drop']} | {pct(s['drop_rate'])} | {note} |")
    A("")
    A(_L("gr.042"))
    A("")

    A(_L("gr.043"))
    A("")
    A(_L("gr.044"))
    A("|---|---|---|---|---|")
    for r in a["rates"]:
        thr = pct(r["threshold"]) if r["threshold"] else "—"
        note = r["desc"]
        if r.get("degraded"):
            note += _F("gr.t022", a1=r['denominator_metric'])
        A(f"| {tcell(r['name'])} | {pct(r['value'])} | {thr} | {tcell(r['flag'])} {tcell(r['advice'])} | {tcell(note)} |")
    A("")

    if a.get("experiment") and a["experiment"].get("groups"):
        exp = a["experiment"]
        A(_L("gr.045"))
        A("")
        A(_L("gr.046"))
        A("|---|---|---|---|---|---|---|")
        for g in exp["groups"]:
            ci_txt = (f"[{g['ci_floor']}, {g['ci_ceil']}]"
                      if g.get("ci_floor") is not None and g.get("ci_ceil") is not None else "—")
            win = {True: _L("gr.047"), False: _L("gr.048"), None: "—"}.get(g.get("win"), "—")
            A(f"| {tcell(g.get('group_name'))} | {tcell(g.get('group_role'))} | {g.get('success_user_num')} | "
              f"{g.get('lift_rate') if g.get('lift_rate') is not None else '—'} | {ci_txt} | "
              f"{g.get('significance_level') if g.get('significance_level') is not None else '—'} | {win} |")
        A("")
        A(_F("gr.t023", a1=exp.get('verdict'), a2=exp.get('conclusion')))
        A("")
        A(_L("gr.049"))
        A("")

    # ---------------- 3. Attribution analysis
    A(_L("gr.050"))
    A("")
    A(_L("gr.051"))
    A("")
    comp = []
    mr = a["metrics"]
    # Audience
    # Mode B (client-hosted backend) cannot reach plan / actualTrigger / trigger,
    # the three platform-side fields. Their absence means "unobservable", not
    # "zero people". Using .get(..., 0) narrates null as zero and yields baseless
    # conclusions such as "the audience was filtered out by the flow" or "the
    # channel is the main source of loss".
    plan, actual = mr.get("plan"), mr.get("actualTrigger")
    if plan is not None and actual is not None:
        comp.append((_L("gr.052"),
                     _F("gr.t024", a1=plan, a2=actual, a3=pct(_div(actual, plan)))
                     + (_L("gr.053") if _ratio_ok(actual, plan)
                        else _L("gr.054"))))
    else:
        comp.append((_L("gr.052"),
                     _L("gr.055")))
    # Channel
    trigger = mr.get("trigger")
    if trigger is not None and actual is not None:
        sr = _div(trigger, actual)
        comp.append((_L("gr.056"),
                     _F("gr.t025", a1=trigger, a2=pct(sr))
                     + (_L("gr.057") if (sr or 0) >= 0.9
                        else _L("gr.058"))))
    else:
        comp.append((_L("gr.056"),
                     _L("gr.059")))
    # Content
    if mr.get("view", 0) and mr.get("click") is not None:
        comp.append((_L("gr.060"),
                     _F("gr.t026", a1=mr.get('view'), a2=mr.get('click'), a3=pct(_div(mr.get('click'), mr.get('view'))))))
    else:
        comp.append((_L("gr.060"), _L("gr.061")))
    # Follow-up (landing)
    if mr.get("main", 0):
        comp.append((_L("gr.062"), _F("gr.t027", a1=mr.get('main'), a2=pct(_div(mr.get('main'), mr.get('click'))))))
    else:
        ci_hint = "、".join(c.get("event_name", "") for c in ci) or _L("gr.063")
        comp.append((_L("gr.062"), _F("gr.t028", a1=ci_hint)))
    for name, txt in comp:
        A(f"- **{name}**：{txt}")
    A("")
    A(_L("gr.064"))
    A("")

    # ---------------- 4. Problem localisation
    A(_L("gr.065"))
    A("")
    A(_L("gr.066"))
    A("")
    A(_L("gr.067"))
    A("|---|---|---|---|---|---|")
    for i in a["issues"]:
        A(f"| P{i['priority']} | {tcell(i['category'])} | {tcell(i['severity'])} | {tcell(i['title'])} | "
          f"{tcell(i['detail'])} | `Sheet {tcell(i.get('evidence', _L('gr.068')))}` |")
    A("")

    # ---------------- 5. Optimisation advice
    A(_L("gr.069"))
    A("")
    if a["recommendations"]:
        for r in a["recommendations"]:
            A(f"### P{r['priority']}｜{r['action']}")
            A("")
            A(_F("gr.t029", a1=r['detail']))
            A(_F("gr.t030", a1=r['expected']))
            A("")
    else:
        A(_L("gr.070"))
        A("")

    # ---------------- 6. Verification plan
    A(_L("gr.071"))
    A("")
    vp = a.get("validation_plan") or {}
    A(_F("gr.t031", a1=vp.get('method', '—')))
    A("")
    for note in vp.get("notes") or []:
        A(f"> ⚠️ {note}")
        A("")
    if vp.get("indicators"):
        A(_L("gr.072"))
        A("|---|---|---|")
        for x in vp["indicators"]:
            A(f"| {tcell(x['metric'])} | {pct(x['baseline'])} | {pct(x['target']) if x['target'] is not None else '—'} |")
        A("")
    if vp.get("steps"):
        A(_L("gr.073"))
        A("")
        for i, s in enumerate(vp["steps"], 1):
            A(f"{i}. {s}")
        A("")

    A("---")
    A("")
    A(_F("gr.t032", a1=m.get('generated_at'), a2=m.get('mode_label')))
    return "\n".join(lines)


def _div(a, b):
    try:
        if not b:
            return None
        return a / b
    except (TypeError, ZeroDivisionError):
        return None


def _ratio_ok(a, b):
    r = _div(a, b)
    return r is not None and r >= 0.95


def main():
    ap = argparse.ArgumentParser(description=_L("gr.074"))
    ap.add_argument("--analysis", default="tmp/analysis.json")
    ap.add_argument("--out-dir", default="output")
    ap.add_argument("--strategy-name", default=None)
    ap.add_argument("--excel-name", default=None)
    args = ap.parse_args()

    with open(args.analysis, encoding="utf-8") as f:
        a = json.load(f)

    strategy = args.strategy_name or a["meta"].get("strategy_name") or a["meta"].get("task_id") or "strategy"
    date = datetime.now().strftime("%Y%m%d")
    os.makedirs(args.out_dir, exist_ok=True)
    out_path = os.path.join(args.out_dir, _F("gr.t033", a1=safe_filename(strategy), a2=date))

    md = render(a, args.excel_name or "—")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    log(_F("gr.t034", a1=out_path, a2=len(md)))
    print(out_path)


if __name__ == "__main__":
    main()
