#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 3 gate - validate analysis.json.

Every condition here maps to a defect found during the sandbox run, so the
gate exists to stop those defects from ever reaching a customer again:

  * funnel must have >= 2 stages            - otherwise there is no chain
  * max_bleed must reference a real rate    - guards the fixed ranking logic
  * data_break must be explicitly null/populated - guards missing-vs-churn mixup
  * issues must not duplicate a category    - guards the de-duplication fix
  * degradations must be a list             - forces the confidence statement
  * meta.mode_label must be set             - the report must state its source

Usage:
    python3 validate_analysis.py tmp/analysis.json

Exit codes:
  0  SUCCESS / EMPTY (soft warnings only)
  1  FATAL
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402

REQUIRED_BLOCKS = ["meta", "metrics", "funnel", "rates", "issues",
                   "recommendations", "validation_plan", "degradations"]


def main():
    ap = argparse.ArgumentParser(description="Step 3 gate")
    ap.add_argument("analysis")
    args = ap.parse_args()

    if not os.path.exists(args.analysis):
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "analysis_exists", "status": "FATAL",
                             "message": "analysis.json not found: %s" % args.analysis}]})
    try:
        with open(args.analysis, encoding="utf-8") as f:
            a = json.load(f)
    except Exception as e:
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "analysis_parse", "status": "FATAL",
                             "message": "cannot parse analysis.json: %s" % e}]})

    checks = []

    def add(name, ok, message, soft=False):
        checks.append({"check": name, "status": "SUCCESS" if ok else ("EMPTY" if soft else "FATAL"),
                       "message": message})

    missing = [k for k in REQUIRED_BLOCKS if k not in a]
    add("required_blocks", not missing,
        "missing %s" % missing if missing else "all %d blocks present" % len(REQUIRED_BLOCKS))

    funnel = a.get("funnel") or []
    add("funnel_stages", len(funnel) >= 2, "%d stage(s)" % len(funnel))

    rates = a.get("rates") or []
    add("rate_checks", len(rates) >= 1, "%d rate(s) evaluated" % len(rates))

    # A rate entry must carry both the measured value and the benchmark it was
    # compared against, otherwise the flag is meaningless.
    incomplete = [r.get("name") for r in rates if "threshold" not in r or "flag" not in r]
    add("rate_shape", not incomplete,
        "entries missing threshold/flag: %s" % incomplete if incomplete else "ok")

    mb = a.get("max_bleed")
    if mb is None:
        add("max_bleed", True, "no bleed point reported (all rates at or above benchmark)")
    else:
        has_ref = bool(mb.get("rate_name")) and mb.get("value") is not None \
            and mb.get("threshold") is not None and mb.get("recoverable") is not None
        add("max_bleed", has_ref,
            "bleed point references rate '%s' (%.2f%% vs %.2f%% threshold, recoverable %s)"
            % (mb.get("rate_name"), (mb.get("value") or 0) * 100,
               (mb.get("threshold") or 0) * 100, mb.get("recoverable"))
            if has_ref else
            "bleed point is missing rate_name/value/threshold/recoverable; the legacy "
            "absolute-volume ranking may have been reintroduced")

    # data_break may legitimately be null, but when present it must be complete:
    # the distinction between "no data returned" and "users churned" is the
    # single most damaging thing to get wrong in this report.
    db = a.get("data_break")
    if db is None:
        add("data_break_shape", True, "no data break detected")
    else:
        ok = bool(db.get("stage")) and "reason" in db
        add("data_break_shape", ok,
            "data break at stage '%s'" % db.get("stage") if ok
            else "data break present but incomplete: %s" % sorted(db.keys()))

    issues = a.get("issues") or []
    add("issues_present", len(issues) >= 1, "%d issue(s)" % len(issues))
    cats = [i.get("category") for i in issues]
    dupes = sorted({c for c in cats if cats.count(c) > 1})
    add("issues_deduplicated", not dupes,
        "duplicated categories: %s" % dupes if dupes else "no duplicate category")

    for it in issues:
        for field in ("priority", "severity", "title", "detail", "evidence"):
            if field not in it:
                add("issue_fields", False, "issue '%s' missing field '%s'"
                    % (it.get("title"), field))
                break
        else:
            continue
        break
    else:
        add("issue_fields", True, "every issue carries priority/severity/title/detail/evidence")

    recs = a.get("recommendations") or []
    add("recommendations", len(recs) >= 1, "%d recommendation(s)" % len(recs))
    bad_rec = [r.get("action") for r in recs if not r.get("expected")]
    add("recommendation_expected_impact", not bad_rec,
        "recommendations lacking an expected impact: %s" % bad_rec if bad_rec
        else "every recommendation states its expected impact")

    vp = a.get("validation_plan")
    if isinstance(vp, dict):
        if vp.get("indicators") and vp.get("steps"):
            add("validation_plan", True,
                "%d indicator(s), %d step(s)"
                % (len(vp["indicators"]), len(vp["steps"])))
        elif vp.get("notes") and vp.get("steps"):
            # No measurable baseline is acceptable only when the plan says so
            # out loud; a silently empty indicator list is not.
            add("validation_plan", True,
                "no baseline available, explicitly declared: %s" % vp["notes"][0][:80],
                soft=True)
        else:
            add("validation_plan", False,
                "validation_plan has neither indicators nor an explicit "
                "no-baseline explanation: %s" % sorted(vp.keys()))
    elif isinstance(vp, list):
        add("validation_plan", len(vp) >= 1, "%d validation step(s)" % len(vp))
    else:
        add("validation_plan", False, "validation_plan missing or of unexpected type")

    add("degradations_recorded", isinstance(a.get("degradations"), list),
        "%d degradation(s)" % len(a.get("degradations") or []))
    add("mode_label", bool((a.get("meta") or {}).get("mode_label")),
        "mode_label=%s" % (a.get("meta") or {}).get("mode_label"))

    # A report whose whole chain is zero must not claim to have measured
    # anything; that is the EMPTY case, not a success.
    nonzero = {k: v for k, v in (a.get("metrics") or {}).items() if v}
    add("metrics_non_zero", bool(nonzero),
        "%d metric(s) above zero" % len(nonzero) if nonzero
        else "every metric is 0 - the report can only state that data was not returned",
        soft=True)

    fatals = [c for c in checks if c["status"] == "FATAL"]
    empties = [c for c in checks if c["status"] == "EMPTY"]
    status = "FATAL" if fatals else ("EMPTY" if empties else "SUCCESS")
    print(json.dumps({"status": status, "checks": checks}, ensure_ascii=False, indent=2))
    sys.exit(1 if fatals else 0)


if __name__ == "__main__":
    main()
