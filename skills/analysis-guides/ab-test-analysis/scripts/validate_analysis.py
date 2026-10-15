#!/usr/bin/env python3
"""Validation gate: check statistical analysis output structure.

Exit codes: 0 = SUCCESS, 1 = EMPTY / ERROR / FATAL.

A metric entry that carries an `error` key is reported as an ERROR check (the
metric could not be analysed) while the remaining metrics are still validated —
so one bad metric never hides the health of the others.
"""
import json
import sys

VALID_VERDICTS = ("treatment_wins", "treatment_harmful", "mixed", "inconclusive")
VALID_TYPES = ("proportion", "continuous")
VALID_DECISION_BASES = ("raw", "bonferroni")
VALID_MC_METHODS = ("bonferroni", "none", "single-comparison")
VALID_MC_FAMILIES = ("all", "success")

REQUIRED_BY_TYPE = {
    "proportion": ["control_rate", "treatment_rate", "relative_lift_pct", "diff_ci"],
    "continuous": ["control_mean", "treatment_mean", "cohens_d", "diff_ci"],
}


def _fatal(msg, check="input"):
    return {"status": "FATAL", "checks": [{"check": check, "status": "FATAL", "message": msg}]}


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_probability(v):
    return _is_number(v) and 0 < v < 0.5


def _is_nonnegative_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def validate(input_file):
    # ---- read + parse -----------------------------------------------------
    try:
        with open(input_file, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return _fatal(f"Analysis file not found: {input_file}", "file_readable")
    except OSError as exc:
        return _fatal(f"Cannot read analysis file: {exc}", "file_readable")

    if not raw.strip():
        return _fatal("Analysis output file is empty. Step 2 (ab_test_stats.py) did not run "
                      "or wrote nothing.", "file_not_empty")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _fatal(f"Analysis output is not valid JSON: {exc}", "json_parse")

    checks = []

    if not isinstance(data, dict) or not data:
        return _fatal(f"Expected a JSON object at top level, got {type(data).__name__}.",
                      "top_level_shape")

    # ---- required top-level fields ---------------------------------------
    for field in ("verdict", "results", "guardrail_status", "multiple_comparison"):
        if field not in data:
            checks.append({"check": f"top_field_{field}", "status": "FATAL",
                           "message": f"Missing required field: {field}"})

    mc = data.get("multiple_comparison")
    if not isinstance(mc, dict):
        checks.append({"check": "multiple_comparison_shape", "status": "FATAL",
                       "message": "multiple_comparison must be an object describing the decision threshold"})
    else:
        method = mc.get("method")
        family = mc.get("family")
        basis = mc.get("decision_basis")
        corrected_alpha = mc.get("corrected_alpha")
        n_comparisons = mc.get("n_comparisons")
        applied = mc.get("applied")

        if method not in VALID_MC_METHODS:
            checks.append({"check": "multiple_comparison_method", "status": "ERROR",
                           "message": f"Unknown multiple-comparison method: {method!r}"})
        if family not in VALID_MC_FAMILIES:
            checks.append({"check": "multiple_comparison_family", "status": "ERROR",
                           "message": f"Unknown multiple-comparison family: {family!r}"})
        if basis not in VALID_DECISION_BASES:
            checks.append({"check": "multiple_comparison_basis", "status": "ERROR",
                           "message": f"Unknown decision basis: {basis!r}"})
        if not _is_probability(corrected_alpha):
            checks.append({"check": "multiple_comparison_alpha", "status": "ERROR",
                           "message": f"corrected_alpha must be a number in (0, 0.5), got {corrected_alpha!r}"})
        if not _is_nonnegative_int(n_comparisons):
            checks.append({"check": "multiple_comparison_count", "status": "ERROR",
                           "message": f"n_comparisons must be a non-negative integer, got {n_comparisons!r}"})
        if not isinstance(applied, bool):
            checks.append({"check": "multiple_comparison_applied", "status": "ERROR",
                           "message": f"multiple_comparison.applied must be boolean, got {applied!r}"})
        if not any(c["check"].startswith("multiple_comparison_") and
                   c["status"] in ("FATAL", "ERROR") for c in checks):
            checks.append({"check": "multiple_comparison_complete", "status": "PASS",
                           "message": f"decision basis={basis}, corrected alpha={corrected_alpha}, "
                                      f"comparisons={n_comparisons}"})

    verdict = data.get("verdict")
    if not isinstance(verdict, dict) or not verdict.get("status"):
        checks.append({"check": "verdict_status", "status": "FATAL",
                       "message": "verdict.status is missing"})
    elif verdict["status"] not in VALID_VERDICTS:
        checks.append({"check": "verdict_status", "status": "ERROR",
                       "message": f"Unknown verdict status: {verdict['status']}"})
    else:
        checks.append({"check": "verdict_status", "status": "PASS",
                       "message": f"verdict = {verdict['status']}"})

    results = data.get("results")
    if results is None or (isinstance(results, list) and not results):
        checks.append({"check": "has_results", "status": "EMPTY",
                       "message": "No metric results in analysis output. Every metric was either "
                                  "missing or failed validation — check the analysis input."})
        results = []
    elif not isinstance(results, list):
        return _fatal(f"`results` must be an array, got {type(results).__name__}.", "results_shape")

    # ---- per-metric checks ------------------------------------------------
    valid_metrics = 0
    for i, r in enumerate(results):
        if not isinstance(r, dict):
            checks.append({"check": f"metric_shape_{i}", "status": "ERROR",
                           "message": f"Result entry {i} is {type(r).__name__}, expected an object."})
            continue

        metric_name = r.get("metric_name") or f"metric_{i}"

        if r.get("error"):
            checks.append({"check": f"metric_error_{metric_name}", "status": "ERROR",
                           "message": f"Metric '{metric_name}' could not be analysed: {r['error']}"})
            continue

        if not r.get("metric_name"):
            checks.append({"check": f"metric_name_{i}", "status": "ERROR",
                           "message": f"Result entry {i} has no metric_name; report will show it unnamed."})

        p = r.get("p_value")
        if "p_value" not in r:
            checks.append({"check": f"p_value_{metric_name}", "status": "FATAL",
                           "message": f"Missing p_value for metric '{metric_name}'"})
        elif not _is_number(p):
            checks.append({"check": f"p_value_{metric_name}", "status": "ERROR",
                           "message": f"p_value for '{metric_name}' is not a number: {p!r}"})
        elif not (0 <= p <= 1):
            checks.append({"check": f"p_value_{metric_name}", "status": "ERROR",
                           "message": f"p_value {p} out of [0,1] range for '{metric_name}'"})

        if "significant" not in r:
            checks.append({"check": f"significant_{metric_name}", "status": "FATAL",
                           "message": f"Missing 'significant' boolean for metric '{metric_name}'"})
        elif not isinstance(r["significant"], bool):
            checks.append({"check": f"significant_{metric_name}", "status": "ERROR",
                           "message": f"'significant' for '{metric_name}' must be a boolean, "
                                      f"got {type(r['significant']).__name__}"})

        decision_significant = r.get("decision_significant")
        if "decision_significant" not in r:
            checks.append({"check": f"decision_significant_{metric_name}", "status": "FATAL",
                           "message": f"Missing authoritative decision_significant for '{metric_name}'"})
        elif not isinstance(decision_significant, bool):
            checks.append({"check": f"decision_significant_{metric_name}", "status": "ERROR",
                           "message": f"decision_significant for '{metric_name}' must be boolean, "
                                      f"got {type(decision_significant).__name__}"})

        decision_alpha = r.get("decision_alpha")
        if "decision_alpha" not in r:
            checks.append({"check": f"decision_alpha_{metric_name}", "status": "FATAL",
                           "message": f"Missing corrected decision_alpha for '{metric_name}'"})
        elif not _is_probability(decision_alpha):
            checks.append({"check": f"decision_alpha_{metric_name}", "status": "ERROR",
                           "message": f"decision_alpha for '{metric_name}' must be in (0, 0.5), "
                                      f"got {decision_alpha!r}"})

        decision_basis = r.get("decision_basis")
        if decision_basis not in VALID_DECISION_BASES:
            checks.append({"check": f"decision_basis_{metric_name}", "status": "ERROR",
                           "message": f"decision_basis for '{metric_name}' must be one of "
                                      f"{VALID_DECISION_BASES}, got {decision_basis!r}"})

        metric_n_comparisons = r.get("n_comparisons")
        if not _is_nonnegative_int(metric_n_comparisons):
            checks.append({"check": f"n_comparisons_{metric_name}", "status": "ERROR",
                           "message": f"n_comparisons for '{metric_name}' must be a non-negative "
                                      f"integer, got {metric_n_comparisons!r}"})

        mtype = r.get("metric_type")
        if mtype is None:
            checks.append({"check": f"metric_type_{metric_name}", "status": "FATAL",
                           "message": f"Missing metric_type for '{metric_name}'"})
        elif mtype not in VALID_TYPES:
            checks.append({"check": f"metric_type_{metric_name}", "status": "ERROR",
                           "message": f"Unknown metric_type '{mtype}' for '{metric_name}' "
                                      f"(expected one of {VALID_TYPES})"})
        else:
            for field in REQUIRED_BY_TYPE[mtype]:
                if r.get(field) is None:
                    checks.append({"check": f"field_{field}_{metric_name}", "status": "ERROR",
                                   "message": f"Missing {field} for {mtype} metric '{metric_name}'"})

        metric_failed = any(
            c["status"] in ("FATAL", "ERROR") and metric_name in c["check"] for c in checks
        )
        if not metric_failed:
            valid_metrics += 1
            checks.append({"check": f"metric_complete_{metric_name}", "status": "PASS",
                           "message": f"Metric '{metric_name}' validated: p={p}, "
                                      f"raw_significant={r.get('significant')}, "
                                      f"decision_significant={decision_significant}"})

    if results and valid_metrics == 0:
        checks.append({"check": "any_valid_metric", "status": "ERROR",
                       "message": "No metric passed validation — the report would be empty."})
    elif valid_metrics:
        checks.append({"check": "any_valid_metric", "status": "PASS",
                       "message": f"{valid_metrics}/{len(results)} metric(s) passed validation."})

    # ---- aggregate ---------------------------------------------------------
    fatals = [c for c in checks if c["status"] == "FATAL"]
    errors = [c for c in checks if c["status"] == "ERROR"]
    empties = [c for c in checks if c["status"] == "EMPTY"]

    if fatals:
        final_status = "FATAL"
    elif errors:
        final_status = "ERROR"
    elif empties:
        final_status = "EMPTY"
    else:
        final_status = "SUCCESS"

    return {"status": final_status, "checks": checks}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"status": "FATAL", "checks": [
            {"check": "usage", "status": "FATAL",
             "message": "Usage: python validate_analysis.py <input_file>"}
        ]}, ensure_ascii=False, indent=2))
        sys.exit(1)

    result = validate(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] in ("FATAL", "ERROR", "EMPTY"):
        sys.exit(1)
    sys.exit(0)
