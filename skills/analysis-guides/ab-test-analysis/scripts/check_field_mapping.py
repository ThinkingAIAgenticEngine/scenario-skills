#!/usr/bin/env python3
"""Step 0b gate: verify the A/B field mapping before any query is run.

Four fields decide whether a two-group comparison means anything: the variant
field, its two stored values, the exposure event (denominator) and the success
event(s) (numerator). A wrong mapping does not raise an error anywhere in the
pipeline — it returns plausible numbers for the wrong population. This gate is
the checkpoint that catches it.

Input:  a field_mapping.json (see references/field_mapping.md for the schema)
Output: {"status", "checks": [...], "resolved_mapping": {...}}
Exit codes: 0 = SUCCESS / WARN, 1 = FATAL / ERROR.

Rules enforced (see references/field_mapping.md section 3):
  1. exactly two valid groups after exclusions          FATAL
  2. no null-like value left in the observed domain     FATAL
  3. no internal / test group left in the domain        ERROR
  4. control_value != treatment_value, both non-empty   FATAL
  5. both mapped values present in observed_domain      FATAL
  6. sample balance >= min_group_ratio                  ERROR
  7. exposure event not reused as a success metric      WARN
  8. counts are non-negative integers                   ERROR
  9. cohort block declares an exposed-users-after-exposure numerator/denominator
     relationship (basis + order_enforced)              ERROR / WARN
 10. every metric that will be tested declares how its numerator / distribution
     is derived (proportion vs per-user over the cohort) ERROR / WARN
"""
import argparse
import json
import sys

COHORT_BASIS_EXPECTED = "exposed_users_after_exposure"
CONTINUOUS_BASIS_EXPECTED = "per_user_over_exposed_cohort"

NULL_LIKE = {
    "", "null", "none", "nil", "undefined", "nan", "n/a", "na", "-", "--",
    "unknown", "未知", "空", "其他", "其它", "0_-1", "-1",
}

# Substrings that mark internal / test traffic rather than a real experiment arm.
INTERNAL_MARKERS = (
    "test", "inner", "internal", "debug", "whitelist", "staff", "qa",
    "灰度测试", "内部", "白名单", "压测", "测试",
)

VALID_FIELD_TYPES = ("event_property", "user_property")
DEFAULT_MIN_GROUP_RATIO = 0.20
RATIO_WARN_BAND = 0.05  # treat "just above the threshold" as a warning


def _norm(value):
    """Normalise a domain value for comparison (case/whitespace insensitive)."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_null_like(value):
    return _norm(value) in NULL_LIKE


def _is_internal(value):
    n = _norm(value)
    return any(m in n for m in INTERNAL_MARKERS)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [value]


def _as_count(value):
    """Return (ok, int_value_or_None, is_integer)."""
    if isinstance(value, bool):
        return False, None, False
    if isinstance(value, int):
        return True, value, True
    if isinstance(value, float):
        return True, value, float(value).is_integer()
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        try:
            f = float(s)
        except ValueError:
            return False, None, False
        return True, f, f.is_integer()
    return False, None, False


def validate(mapping, min_group_ratio=DEFAULT_MIN_GROUP_RATIO, allow_extra_groups=False):
    checks = []

    def add(check, status, message):
        checks.append({"check": check, "status": status, "message": message})

    # ---- 1. shape -------------------------------------------------------
    if not isinstance(mapping, dict) or not mapping:
        return {"status": "FATAL", "checks": [{
            "check": "top_level_shape", "status": "FATAL",
            "message": f"Expected a JSON object, got {type(mapping).__name__}. "
                       f"See references/field_mapping.md section 5 for the schema."}]}

    required = ["variant_field", "variant_field_type", "control_value",
                "treatment_value", "exposure_event", "success_events"]
    missing = [k for k in required if mapping.get(k) in (None, "", [])]
    if missing:
        return {"status": "FATAL", "checks": [{
            "check": "required_fields", "status": "FATAL",
            "message": f"Missing required field(s): {missing}. Parse the user's answers into these "
                       f"keys, then re-run. Required: {required}"}]}

    # ---- 2. project_id --------------------------------------------------
    pid = mapping.get("project_id")
    if pid in (None, ""):
        add("project_id", "WARN",
            "project_id is absent from the mapping — the report will have no data source. "
            "Recommended: record it so the mapping is tied to one project.")
    else:
        try:
            pid_int = int(str(pid).strip())
            if pid_int <= 0:
                add("project_id", "FATAL", f"project_id must be a positive integer, got {pid_int}.")
            else:
                add("project_id", "PASS", f"project_id = {pid_int}")
        except (ValueError, TypeError):
            add("project_id", "FATAL", f"project_id must be numeric, got '{pid}'.")

    # ---- 3. field type --------------------------------------------------
    ftype = str(mapping.get("variant_field_type", "")).strip()
    if ftype not in VALID_FIELD_TYPES:
        add("variant_field_type", "FATAL",
            f"variant_field_type must be one of {list(VALID_FIELD_TYPES)}, got '{ftype}'. "
            f"This value goes straight into groups[].field.type — a wrong value makes the query "
            f"return one group or nothing.")
    else:
        add("variant_field_type", "PASS", f"variant_field_type = {ftype}")

    variant_field = str(mapping.get("variant_field", "")).strip()
    if not variant_field:
        add("variant_field", "FATAL", "variant_field is empty.")
    elif any(ch.isspace() for ch in variant_field):
        add("variant_field", "WARN",
            f"variant_field '{variant_field}' contains whitespace — field names in the tracking "
            f"platform are exact; confirm there is no stray space.")
    else:
        add("variant_field", "PASS", f"variant_field = {variant_field}")

    # ---- 4. control / treatment ----------------------------------------
    control = mapping.get("control_value")
    treatment = mapping.get("treatment_value")
    control_s = "" if control is None else str(control)
    treatment_s = "" if treatment is None else str(treatment)

    if control_s == "" or treatment_s == "":
        add("group_values", "FATAL",
            f"control_value and treatment_value must both be non-empty, got "
            f"control={control_s!r}, treatment={treatment_s!r}.")
    elif _norm(control_s) == _norm(treatment_s):
        add("group_values", "FATAL",
            f"control_value and treatment_value are the same value ({control_s!r}) — "
            f"that is one arm compared with itself.")
    else:
        add("group_values", "PASS",
            f"control_value = {control_s!r}, treatment_value = {treatment_s!r}")

    if _is_null_like(control_s) or _is_null_like(treatment_s):
        add("group_values_null_like", "FATAL",
            "One of the mapped values is a null-like placeholder — that is 'never entered the "
            "experiment', not an arm. Re-read the field's actual values.")

    # ---- 5. events ------------------------------------------------------
    exposure = str(mapping.get("exposure_event", "")).strip()
    success_events = [str(e).strip() for e in _as_list(mapping.get("success_events")) if str(e).strip()]
    guardrail_events = [str(e).strip() for e in _as_list(mapping.get("guardrail_events")) if str(e).strip()]

    if not exposure:
        add("exposure_event", "FATAL",
            "exposure_event is required — it is the denominator. If no dedicated exposure event "
            "exists, say so explicitly (the report must disclose that a proxy denominator was used).")
    else:
        add("exposure_event", "PASS", f"exposure_event = {exposure}")

    if not success_events:
        add("success_events", "FATAL", "At least one success event is required (it is the numerator).")
    else:
        add("success_events", "PASS", f"success_events = {success_events}")

    if guardrail_events:
        add("guardrail_events", "PASS", f"guardrail_events = {guardrail_events}")
    else:
        add("guardrail_events", "WARN",
            "No guardrail metrics declared — the guardrail check will be skipped. "
            "State that in the report's limitations rather than implying safety was verified.")

    if exposure and _norm(exposure) in {_norm(e) for e in success_events}:
        add("event_self_comparison", "WARN",
            f"exposure_event '{exposure}' is also a success event — the conversion rate would be "
            f"100% by construction. Confirm this is intentional.")
    if exposure and _norm(exposure) in {_norm(e) for e in guardrail_events}:
        add("event_self_comparison_guardrail", "WARN",
            f"exposure_event '{exposure}' is also used as a guardrail metric.")

    overlap = {_norm(e) for e in success_events} & {_norm(e) for e in guardrail_events}
    if overlap:
        add("success_guardrail_overlap", "WARN",
            f"Event(s) used as both success and guardrail metrics: {sorted(overlap)}. "
            f"They will get contradictory polarity treatment — pick one role per event.")

    # ---- 6. observed domain --------------------------------------------
    domain = _as_list(mapping.get("observed_domain"))
    excluded = _as_list(mapping.get("excluded_values"))
    domain_norm = [_norm(d) for d in domain]

    if not domain:
        add("observed_domain", "WARN",
            "observed_domain is absent — the gate cannot verify that the mapped values actually "
            "exist in the field, nor that dirty values were excluded. Recommended: list the field's "
            "observed values after exclusions.")
    else:
        if len(domain) != 2:
            status = "WARN" if allow_extra_groups else ("FATAL" if len(domain) < 2 else "ERROR")
            add("observed_domain_size", status,
                f"observed_domain has {len(domain)} value(s): {domain}. This skill analyses "
                f"two-group tests — expected exactly 2. {len(domain) > 2 and 'If the extra groups are known-benign and will be filtered in the query, re-run with --allow-extra-groups and disclose it in the report.' or 'Fewer than 2 means the field is not populated per arm.'}")
        else:
            add("observed_domain_size", "PASS", f"observed_domain = {domain}")

        nulls = [d for d in domain if _is_null_like(d)]
        if nulls:
            add("domain_null_like", "FATAL",
                f"observed_domain still contains null-like value(s) {nulls}. These are users who "
                f"never entered the experiment — move them to excluded_values, or they will be "
                f"analysed as a third arm and bias both arms.")

        internals = [d for d in domain if _is_internal(d)]
        if internals:
            add("domain_internal", "ERROR",
                f"observed_domain contains internal/test value(s) {internals}. Internal traffic "
                f"behaves differently and inflates one arm — exclude them.")

        # rule 5: mapped values must exist in the observed domain
        for label, val in (("control_value", control_s), ("treatment_value", treatment_s)):
            if val and _norm(val) not in domain_norm:
                add(f"{label}_in_domain", "FATAL",
                    f"{label} = {val!r} does not appear in observed_domain {domain}. A mapping to a "
                    f"value the field never takes produces empty results that look like 'no traffic'.")

        matched = {_norm(control_s), _norm(treatment_s)} & set(domain_norm)
        if len(matched) == 2 and len(domain) == 2:
            add("group_mapping", "PASS",
                "Both mapped values resolve to the two observed groups.")

    # ---- 7. sample balance ---------------------------------------------
    counts = mapping.get("observed_counts")
    if not counts:
        add("observed_counts", "WARN",
            "observed_counts is absent — the sample-balance check cannot run. A 1:10 split usually "
            "means dirty values or a broken assignment, not a real experiment. Recommended: supply "
            "per-arm user counts.")
    elif not isinstance(counts, dict):
        add("observed_counts_shape", "ERROR",
            f"observed_counts must be an object like {{\"control\": 10000, \"treatment\": 10000}}, "
            f"got {type(counts).__name__}.")
    else:
        bad = []
        parsed = {}
        for key, raw in counts.items():
            ok, num, is_int = _as_count(raw)
            if not ok:
                bad.append(f"{key}={raw!r} is not numeric")
            elif num < 0:
                bad.append(f"{key}={num} is negative")
            elif not is_int:
                bad.append(f"{key}={num} is not a whole number of users")
            else:
                parsed[key] = int(num)

        if bad:
            add("observed_counts_values", "ERROR",
                "Invalid per-arm counts: " + "; ".join(bad) +
                ". Counts are user counts — non-negative integers.")
        if len(parsed) >= 2:
            values = sorted(parsed.values())
            small, large = values[0], values[-1]
            if large <= 0:
                add("sample_balance", "ERROR", f"All arms report 0 users: {parsed}.")
            else:
                ratio = small / large
                if ratio < min_group_ratio:
                    add("sample_balance", "ERROR",
                        f"Sample ratio {small}:{large} = {ratio:.3f} is below the "
                        f"{min_group_ratio:.2f} threshold ({parsed}). Clean the dirty values and "
                        f"re-query; if it stays imbalanced, report it as an experiment-configuration "
                        f"risk rather than analysing it as-is.")
                elif ratio < min_group_ratio + RATIO_WARN_BAND:
                    add("sample_balance", "WARN",
                        f"Sample ratio {small}:{large} = {ratio:.3f} is only just above the "
                        f"{min_group_ratio:.2f} threshold ({parsed}) — worth a second look.")
                else:
                    add("sample_balance", "PASS",
                        f"Sample ratio {small}:{large} = {ratio:.3f} ({parsed}).")
        elif parsed:
            add("sample_balance", "WARN",
                f"Only one arm has counts recorded ({parsed}) — expected one entry per group.")

    # ---- 8. alias audit trail ------------------------------------------
    aliases = mapping.get("field_aliases_resolved")
    if aliases and not isinstance(aliases, dict):
        add("field_aliases_resolved", "WARN",
            f"field_aliases_resolved should be an object mapping role -> resolved name, got "
            f"{type(aliases).__name__}.")
    elif aliases:
        add("field_aliases_resolved", "PASS",
            f"{len(aliases)} alias(es) recorded — the mapping is auditable if the conclusion is "
            f"questioned.")
    else:
        add("field_aliases_resolved", "WARN",
            "field_aliases_resolved is absent — without it there is no record of which business term "
            "was resolved to which field name. Recommended when the user described fields loosely.")

    if excluded:
        add("excluded_values", "PASS", f"excluded_values = {excluded}")
    else:
        add("excluded_values", "WARN",
            "excluded_values is empty — confirm the field genuinely has no dirty values (null-like "
            "placeholders, internal/test groups), otherwise one of them is being analysed as an arm.")

    # ---- 9. cohort contract ---------------------------------------------
    # A conversion rate is only a rate if the numerator is a subset of the
    # denominator AND the success happened after exposure. Two independently
    # counted `user_count` metrics do not guarantee either property, so the
    # mapping has to declare the relationship the query is built to enforce.
    cohort = mapping.get("cohort")
    if cohort is None:
        add("cohort_declaration", "ERROR",
            "Missing `cohort` block. The query needs an explicit numerator/denominator contract: "
            "without it the gate cannot tell whether the success count is restricted to the exposed "
            "cohort, and a success count over 'all users' still looks like a valid conversion rate. "
            f"Add: {{\"basis\": \"{COHORT_BASIS_EXPECTED}\", \"exposure_event\": \"...\", "
            f"\"order_enforced\": true, \"denominator_column\": \"...\", "
            f"\"numerator_columns\": {{\"<metric>\": \"<column>\"}}}}")
    elif not isinstance(cohort, dict):
        add("cohort_shape", "ERROR",
            f"`cohort` must be an object, got {type(cohort).__name__}.")
    else:
        basis = str(cohort.get("basis") or "").strip()
        if not basis:
            add("cohort_basis", "ERROR",
                f"cohort.basis is required and must be {COHORT_BASIS_EXPECTED!r} — it is the statement "
                f"that the numerator users were exposed first and converted after.")
        elif basis != COHORT_BASIS_EXPECTED:
            add("cohort_basis", "ERROR",
                f"cohort.basis = {basis!r} is not {COHORT_BASIS_EXPECTED!r}. Any other basis means the "
                f"numerator is not guaranteed to be a subset of the exposed cohort, so the ratio is "
                f"not a conversion rate and the z-test is comparing the wrong populations.")
        else:
            add("cohort_basis", "PASS", f"cohort.basis = {basis}")

        order = cohort.get("order_enforced")
        if order is True:
            add("cohort_order_enforced", "PASS",
                "Exposure-before-success ordering is declared as enforced by the query.")
        elif order is False:
            add("cohort_order_enforced", "ERROR",
                "cohort.order_enforced = false: success events are being counted without requiring "
                "them to happen AFTER exposure. A user who converted before seeing the experiment is "
                "in the numerator but was never treated. Use the funnel model (exposure as step 1).")
        else:
            add("cohort_order_enforced", "ERROR",
                "cohort.order_enforced is not declared. Set it to true and make the query enforce it "
                "(funnel model: step 1 = exposure event, step 2 = success event, with a conversion "
                "window) — otherwise the ordering is unverified and the numerator may include "
                "pre-exposure conversions.")

        cohort_exposure = str(cohort.get("exposure_event") or "").strip()
        if cohort_exposure and exposure and _norm(cohort_exposure) != _norm(exposure):
            add("cohort_exposure_event", "ERROR",
                f"cohort.exposure_event = {cohort_exposure!r} contradicts exposure_event = "
                f"{exposure!r}. One of them is stale — the denominator must come from the same event "
                f"the mapping declares.")
        elif not cohort_exposure:
            add("cohort_exposure_event", "WARN",
                "cohort.exposure_event is not repeated in the cohort block. Recommended so the "
                "denominator cannot drift away from the declared exposure event.")

        if not str(cohort.get("denominator_column") or "").strip():
            add("cohort_denominator_column", "WARN",
                "cohort.denominator_column is not declared — the query-output gate will have to guess "
                "which returned column is the exposed cohort, and it refuses to guess when more than "
                "one column looks like a user count. Recommended: name the exact column.")
        if not isinstance(cohort.get("numerator_columns"), dict) or not cohort.get("numerator_columns"):
            add("cohort_numerator_columns", "WARN",
                "cohort.numerator_columns is not declared — the gate cannot check that each numerator "
                "stays within the denominator. Recommended: {\"<metric>\": \"<returned column>\"}.")

    # ---- 10. metric declarations -----------------------------------------
    metric_defs = mapping.get("metrics")
    if metric_defs is None:
        add("metric_declarations", "WARN",
            "No `metrics` array — the gate cannot verify how each tested metric is derived. "
            "Recommended: [{\"name\": ..., \"type\": \"proportion\", \"numerator_column\": ...}, "
            "{\"name\": ..., \"type\": \"continuous\", "
            f"\"basis\": \"{CONTINUOUS_BASIS_EXPECTED}\", "
            "\"distribution\": \"user_level\"}].")
    elif not isinstance(metric_defs, list):
        add("metric_declarations_shape", "ERROR",
            f"`metrics` must be an array, got {type(metric_defs).__name__}.")
    else:
        for i, md in enumerate(metric_defs):
            if not isinstance(md, dict):
                add(f"metric_declaration_{i}", "ERROR",
                    f"metrics[{i}] must be an object, got {type(md).__name__}.")
                continue
            mname = str(md.get("name") or f"metrics[{i}]")
            mtype = str(md.get("type") or "").strip()
            if mtype == "proportion":
                if not str(md.get("numerator_column") or "").strip():
                    add(f"metric_numerator_{i}", "WARN",
                        f"{mname}: proportion metric without `numerator_column` — the gate cannot "
                        f"check the numerator against the declared denominator.")
            elif mtype == "continuous":
                cbasis = str(md.get("basis") or "").strip()
                distribution = str(md.get("distribution") or "").strip()
                if cbasis != CONTINUOUS_BASIS_EXPECTED:
                    add(f"metric_basis_{i}", "ERROR",
                        f"{mname}: a continuous metric must declare basis = "
                        f"{CONTINUOUS_BASIS_EXPECTED!r} (got {cbasis!r}). Welch's t-test compares "
                        f"per-user MEANS with a per-user variance, so mean/stddev/n must all come "
                        f"from the same exposed cohort — including the users who contributed zero. "
                        f"Taking avg/stddev over the purchase event and n = paying users describes "
                        f"the distribution of payers only, which is a different (and much more "
                        f"favourable) comparison.")
                else:
                    add(f"metric_basis_{i}", "PASS",
                        f"{mname}: continuous basis = {cbasis}")
                if distribution != "user_level":
                    add(f"metric_distribution_{i}", "ERROR",
                        f"{mname}: inferential continuous metrics require distribution = "
                        f"'user_level' (got {distribution!r}). An ae-cli event-model avg_per_user "
                        f"aggregate is descriptive only: it does not prove that non-triggering "
                        f"exposed users are represented as zero or provide their per-user variance.")
                else:
                    add(f"metric_distribution_{i}", "PASS",
                        f"{mname}: distribution = user_level")
            elif mtype:
                add(f"metric_type_{i}", "ERROR",
                    f"{mname}: unknown metric type {mtype!r}; expected 'proportion' or 'continuous'.")
            else:
                add(f"metric_type_{i}", "WARN",
                    f"{mname}: no `type` declared — the numerator/denominator contract cannot be "
                    f"verified for it.")

    # ---- 11. aggregate ---------------------------------------------------
    if any(c["status"] == "FATAL" for c in checks):
        status = "FATAL"
    elif any(c["status"] == "ERROR" for c in checks):
        status = "ERROR"
    elif any(c["status"] == "WARN" for c in checks):
        status = "WARN"
    else:
        status = "SUCCESS"

    result = {"status": status, "checks": checks}
    if status in ("SUCCESS", "WARN"):
        # Downstream steps consume this block so the query and the report metadata
        # cannot drift away from the confirmed mapping.
        result["resolved_mapping"] = {
            "project_id": mapping.get("project_id"),
            "variant_field": variant_field,
            "variant_field_type": ftype,
            "control_value": control_s,
            "treatment_value": treatment_s,
            "exposure_event": exposure,
            "success_events": success_events,
            "guardrail_events": guardrail_events,
            "excluded_values": [_norm_keep_original(v) for v in excluded],
            # Carried through verbatim: these are what the query is built from and
            # what validate_query_output.py reads to identify the denominator.
            "cohort": cohort if isinstance(cohort, dict) else None,
            "metrics": metric_defs if isinstance(metric_defs, list) else None,
        }
    return result


def _norm_keep_original(value):
    return value if isinstance(value, str) else str(value)


def main():
    parser = argparse.ArgumentParser(description="Validate A/B test field mapping (Step 0b gate)")
    parser.add_argument("mapping_file", help="Path to field_mapping.json")
    parser.add_argument("--min-group-ratio", type=float, default=DEFAULT_MIN_GROUP_RATIO,
                        help=f"Minimum smaller/larger sample ratio before ERROR (default "
                             f"{DEFAULT_MIN_GROUP_RATIO})")
    parser.add_argument("--allow-extra-groups", action="store_true",
                        help="Downgrade 'more than 2 groups' from ERROR to WARN (only when the extra "
                             "groups are known-benign and will be filtered in the query)")
    args = parser.parse_args()

    try:
        with open(args.mapping_file, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        print(json.dumps({"status": "FATAL", "checks": [{
            "check": "file_readable", "status": "FATAL",
            "message": f"Mapping file not found: {args.mapping_file}"}]}, ensure_ascii=False, indent=2))
        sys.exit(1)
    except OSError as exc:
        print(json.dumps({"status": "FATAL", "checks": [{
            "check": "file_readable", "status": "FATAL",
            "message": f"Cannot read mapping file: {exc}"}]}, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not raw.strip():
        print(json.dumps({"status": "FATAL", "checks": [{
            "check": "file_not_empty", "status": "FATAL",
            "message": "Mapping file is empty (0 bytes)."}]}, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "FATAL", "checks": [{
            "check": "json_parse", "status": "FATAL",
            "message": f"Mapping file is not valid JSON: {exc}. First 120 chars: {raw[:120]!r}"}]},
            ensure_ascii=False, indent=2))
        sys.exit(1)

    result = validate(mapping, min_group_ratio=args.min_group_ratio,
                      allow_extra_groups=args.allow_extra_groups)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] in ("FATAL", "ERROR"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
