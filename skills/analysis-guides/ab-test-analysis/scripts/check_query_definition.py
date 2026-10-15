#!/usr/bin/env python3
"""Gate the ae-cli query DEFINITION before it is executed.

The statistical engine can only be as correct as the numbers fed to it. This
gate checks the query itself against the model contract, so a query that cannot
support the claimed test fails *before* it burns a run — and fails loudly,
instead of returning plausible numbers for the wrong population.

Usage:
    check_query_definition.py <definition.json> --model-type <model> --kind <kind> [options]

    --model-type      event | funnel | retention (same value passed to ae-cli)
    --kind            proportion | guardrail | continuous | retention
    --exposure-event  the exposure event the cohort is built from (proportion/guardrail)
    --variant-field   the A/B group field the query must be split by
    --distribution    `user_level` when the per-user distribution comes from an
                      external per-user export rather than an aggregate query
                      (required for inferential `continuous` analysis)

Exit codes: 0 = SUCCESS / WARN, 1 = ERROR / FATAL.

## Contracts enforced (each one traces to a way the numbers can be silently wrong)

**proportion / guardrail — the exposure cohort and ordering.**
Counting exposure users and success users as two independent `user_count`
metrics does NOT make the ratio a conversion rate: nothing in that query forces
success users to belong to the exposed cohort, nor to have converted *after*
exposure. The accepted construction is the funnel model with the exposure event
as step 1 and the success event as step 2 (plus a conversion window), because the
funnel model imposes both the ordering and the subset relation.

**continuous — the distribution, not the payers' average.**
ARPU = revenue / exposed users. Feeding Welch's t-test the avg/stddev of the
purchase event with n = number of paying users describes the distribution of
PAYERS only; it excludes every user who paid nothing, which is most of the
cohort, and it is exactly the comparison that makes a test look better than it
is. An event-model `avg_per_user` is only a descriptive aggregate: it neither
proves that non-triggering exposed users were included as zero nor supplies the
same-cohort per-user variance required by Welch's t-test. The accepted
construction is an explicit user-level distribution with one row per exposed
user, including zero contributors.

**retention — the nested contract.**
`initial_event` / `return_event` / `stat_type` / `unit_num` / `rtn_rate_or_num`
live inside a nested `retention` object; the retention model rejects top-level
`filters` and `time_granularity`, and a flat `definition.initial_event` is a
silent no-op that returns the wrong window.
"""
import argparse
import json
import sys

VALID_KINDS = ("proportion", "guardrail", "continuous", "retention")

# Retention result types. The rate forms give a proportion this skill can test
# directly; the count forms return users, which need the cohort size to become a
# rate at all.
RTN_RATE_FORMS = ("r0", "rate", "retention")
RTN_COUNT_FORMS = ("r1", "number", "count")
VALID_STAT_TYPES = ("retention", "lost")

# Aggregations that describe a per-user rollup rather than a per-event statistic.
PER_USER_AGGREGATIONS = ("avg_per_user",)
# Aggregations over an event property that describe events (or payers), not users.
EVENT_LEVEL_DISTRIBUTION = ("avg", "stddev", "variance", "median", "percentile")


def _fatal(msg, check="input"):
    return {"status": "FATAL", "checks": [{"check": check, "status": "FATAL", "message": msg}]}


def _is_int(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    if isinstance(v, float):
        return float(v).is_integer()
    if isinstance(v, str):
        try:
            return float(v.strip()).is_integer()
        except ValueError:
            return False
    return False


def _events_of(definition):
    """Every event name referenced by an event-model definition."""
    out = []
    for m in _dict_list((definition or {}).get("metrics")):
        if m.get("event"):
            out.append(str(m["event"]))
    return out


def _dict_list(v):
    """A list of dicts, or [] when the container shape is wrong.

    Every nested collection in an agent-authored query can arrive with the wrong
    type; the shape is reported by the caller and the walk must survive it.
    """
    if not isinstance(v, list):
        return []
    return [x for x in v if isinstance(x, dict)]


def _dim_name(dim):
    """`groups[].field.name`, or None when the dimension is malformed."""
    if not isinstance(dim, dict):
        return None
    field = dim.get("field")
    if not isinstance(field, dict):
        return None
    name = field.get("name")
    if name in (None, ""):
        return None
    return str(name)


def _norm(v):
    return str(v or "").strip().lower()


def check_retention(definition, ctx, add):
    if not isinstance(definition, dict):
        add("definition_shape", "FATAL",
            f"definition must be an object for the retention model, got "
            f"{type(definition).__name__}.")
        return

    # The flat form used by older patterns is a silent no-op for this model.
    flat = [k for k in ("initial_event", "return_event") if k in definition]
    if flat:
        add("retention_nesting", "FATAL",
            f"definition.{flat[0]} is at the top level. The retention model reads "
            f"definition.retention.{{initial_event, return_event}} — a top-level key is ignored, so "
            f"the query silently returns a different cohort (usually everyone) while looking "
            f"correct. Move it into the nested `retention` object.")
        return

    ret = definition.get("retention")
    if ret is None:
        add("retention_object", "FATAL",
            "definition.retention is missing. The retention model requires "
            "{\"time_range\": ..., \"retention\": {initial_event, return_event, unit_num, ...}}.")
        return
    if not isinstance(ret, dict):
        add("retention_shape", "FATAL",
            f"definition.retention must be an object, got {type(ret).__name__}.")
        return

    for field in ("initial_event", "return_event", "unit_num"):
        if ret.get(field) in (None, ""):
            add(f"retention_{field}", "FATAL",
                f"retention.{field} is required by the retention model. "
                f"{'The initial event defines the cohort.' if field == 'initial_event' else ''}"
                f"{'The return event defines who counts as retained.' if field == 'return_event' else ''}"
                f"{'unit_num is the interval: 1 = D1, 7 = D7.' if field == 'unit_num' else ''}")
        elif field == "unit_num":
            if not _is_int(ret["unit_num"]) or int(float(ret["unit_num"])) < 1:
                add("retention_unit_num", "ERROR",
                    f"retention.unit_num must be an integer >= 1 (1 = D1, 7 = D7), got "
                    f"{ret['unit_num']!r}.")

    stat_type = _norm(ret.get("stat_type"))
    if not stat_type:
        add("retention_stat_type", "ERROR",
            "retention.stat_type is not set. It has no safe implicit reading: `retention` counts "
            "the users who came back, `lost` counts the users who did not — opposite-signed "
            "numbers that look equally valid downstream. Declare "
            "\"stat_type\": \"retention\" explicitly.")
    elif stat_type not in VALID_STAT_TYPES:
        add("retention_stat_type", "ERROR",
            f"retention.stat_type = {ret['stat_type']!r} is not one of {list(VALID_STAT_TYPES)}.")
    else:
        add("retention_stat_type", "PASS", f"retention.stat_type = {stat_type}")

    rtn = _norm(ret.get("rtn_rate_or_num"))
    if not rtn:
        add("retention_rtn_rate_or_num", "WARN",
            "retention.rtn_rate_or_num is not set; it defaults to R0 (a rate). Declare it anyway — "
            "this skill runs a proportion test, so a count form would silently feed it user counts "
            "where it expects a rate. Use \"rtn_rate_or_num\": \"rate\".")
    elif rtn in RTN_RATE_FORMS:
        add("retention_rtn_rate_or_num", "PASS",
            f"retention.rtn_rate_or_num = {ret['rtn_rate_or_num']} (rate form)")
    elif rtn in RTN_COUNT_FORMS:
        add("retention_rtn_rate_or_num", "ERROR",
            f"retention.rtn_rate_or_num = {ret['rtn_rate_or_num']!r} returns USER COUNTS, not a "
            f"rate. A proportion test needs the rate; a count would have to be divided by the "
            f"cohort size you did not query. Use \"rate\" (or \"R0\").")
    else:
        add("retention_rtn_rate_or_num", "ERROR",
            f"retention.rtn_rate_or_num = {ret['rtn_rate_or_num']!r} is not a recognised form "
            f"({list(RTN_RATE_FORMS + RTN_COUNT_FORMS)}).")

    # Model-level unsupported keys (they are accepted by other models, so they
    # read as harmless here and then change nothing).
    for bad in ("filters", "time_granularity"):
        if bad in definition:
            add(f"retention_unsupported_{bad}", "ERROR",
                f"definition.{bad} is not supported by the retention model and is dropped — the "
                f"query returns unfiltered data while appearing filtered. "
                f"{'Use retention.initial_filters for cohort filters.' if bad == 'filters' else 'Use time_particle_size.'}")
        if bad in ret:
            add(f"retention_unsupported_ret_{bad}", "ERROR",
                f"retention.{bad} is not supported by the retention model; "
                f"{'use initial_filters' if bad == 'filters' else 'use time_particle_size'} instead.")

    if not ret.get("initial_filters") and not _dict_list(ret.get("groups")):
        add("retention_scope", "WARN",
            "Neither retention.initial_filters nor retention.groups is set. The query will return "
            "one overall cohort row per arm with no internal split — fine for a single number, but "
            "confirm that is what you want before running it.")

    filters_raw = ret.get("initial_filters")
    if filters_raw is not None and not isinstance(filters_raw, list):
        add("retention_filters_shape", "ERROR",
            f"retention.initial_filters must be an array, got {type(filters_raw).__name__}.")
    else:
        for i, flt in enumerate(filters_raw or []):
            if not isinstance(flt, dict):
                add(f"retention_filter_{i}", "ERROR",
                    f"initial_filters[{i}] must be an object, got {type(flt).__name__}.")
                continue
            if not flt.get("event_property_name"):
                add(f"retention_filter_{i}", "ERROR",
                    f"initial_filters[{i}] is missing `event_property_name`. The retention model takes "
                    f"event-only filters here ({{event_property_name, operator, values}}).")
            if not flt.get("operator"):
                add(f"retention_filter_op_{i}", "ERROR",
                    f"initial_filters[{i}] is missing `operator`.")

    groups_raw = ret.get("groups")
    if groups_raw is not None and not isinstance(groups_raw, list):
        add("retention_groups_shape", "ERROR",
            f"retention.groups must be an array, got {type(groups_raw).__name__}.")
    else:
        malformed = [i for i, g in enumerate(groups_raw or []) if _dim_name(g) is None]
        if malformed:
            add("retention_groups_malformed", "ERROR",
                f"retention.groups entries {malformed} are missing "
                f"field.name — each entry must be {{\"field\": {{\"name\": ..., \"type\": "
                f"event_property|user_property}}}}.")
        elif ctx.get("variant_field") and not groups_raw:
            add("retention_groups", "ERROR",
                f"retention.groups is empty but the A/B group field "
                f"{ctx['variant_field']!r} was declared — without it the query cannot split control "
                f"from treatment.")


def check_funnel(definition, ctx, add, kind):
    if not isinstance(definition, dict):
        add("definition_shape", "FATAL",
            f"definition must be an object, got {type(definition).__name__}.")
        return
    funnel = definition.get("funnel")
    if not isinstance(funnel, dict):
        add("funnel_object", "FATAL",
            "definition.funnel is missing. Use the funnel model with step 1 = the exposure event "
            "and step 2 = the success event.")
        return

    steps = funnel.get("steps")
    if not isinstance(steps, list) or len(steps) < 2:
        add("funnel_steps", "FATAL",
            f"funnel.steps must be a list of at least 2 ordered steps (exposure first, then "
            f"success), got {steps!r}. With fewer than two steps the query cannot express "
            f"'exposed and then converted'.")
        return

    non_dict = [i for i, s in enumerate(steps) if not isinstance(s, dict)]
    if non_dict:
        add("funnel_step_shape", "ERROR",
            f"funnel.steps entries {non_dict} must be objects like {{\"event\": \"...\"}}, got "
            f"{[type(steps[i]).__name__ for i in non_dict]}.")
        return

    step_events = [s.get("event") for s in steps]
    if any(not e for e in step_events):
        add("funnel_step_event", "ERROR",
            f"Every funnel step needs an `event`: {step_events}.")

    exposure = ctx.get("exposure_event")
    if exposure and _norm(step_events[0]) != _norm(exposure):
        add("funnel_step_order", "ERROR",
            f"funnel step 1 is {step_events[0]!r} but the declared exposure event is {exposure!r}. "
            f"Step 1 defines the denominator cohort — if it is not the exposure event, the "
            f"denominator is not the exposed cohort and the ratio is not a conversion rate.")

    missing_window = not isinstance(funnel.get("window"), dict) or not funnel["window"]
    if missing_window:
        add("funnel_window", "WARN",
            "funnel.window is not set. Without a conversion window the funnel lets a success count "
            "at ANY later time, including long after the experiment ended — the lift then reflects "
            "time, not the change. Set {\"value\": 7, \"unit\": \"day\"} or the window that matches "
            "the experiment design.")
    else:
        add("funnel_window", "PASS", f"conversion window = {funnel['window']}")

    groups_raw = funnel.get("groups")
    if groups_raw is not None and not isinstance(groups_raw, list):
        add("funnel_groups_shape", "ERROR",
            f"funnel.groups must be an array, got {type(groups_raw).__name__}.")
        return

    groups = groups_raw or []
    malformed = [i for i, g in enumerate(groups) if _dim_name(g) is None]
    if malformed:
        add("funnel_groups_malformed", "ERROR",
            f"funnel.groups entries {malformed} are missing field.name — each entry must be "
            f"{{\"field\": {{\"name\": ..., \"type\": event_property|user_property}}}}.")
    elif ctx.get("variant_field"):
        names = [_dim_name(g) for g in groups]
        if _norm(ctx["variant_field"]) not in {_norm(n) for n in names}:
            add("funnel_groups", "ERROR",
                f"funnel.groups {names} does not include the declared A/B group field "
                f"{ctx['variant_field']!r}, so the result cannot be split into control/treatment.")
        else:
            add("funnel_groups", "PASS", f"grouped by {ctx['variant_field']}")

    if kind == "guardrail":
        add("guardrail_cohort", "PASS",
            "Guardrail is measured over the same funnel cohort, so the guardrail rate and the "
            "success rate share a denominator. Comparing a guardrail over a different population "
            "than the success metric is a common source of contradictory conclusions.")


def check_proportion_event_model(definition, ctx, add):
    add("cohort_construction", "ERROR",
        "model_type='event' with independent user_count metrics cannot express this test. Two "
        "separately counted user counts do not force the success users to be a subset of the "
        "exposed cohort, nor to have converted after exposure, so success/total can exceed 100% "
        "and the z-test compares the wrong populations. Rebuild the query as a funnel with the "
        "exposure event as step 1 and the success event as step 2.")


def check_continuous(definition, ctx, add):
    if not isinstance(definition, dict):
        add("definition_shape", "FATAL",
            f"definition must be an object, got {type(definition).__name__}.")
        return

    metrics_raw = definition.get("metrics")
    if metrics_raw is not None and not isinstance(metrics_raw, list):
        add("continuous_metrics_shape", "ERROR",
            f"definition.metrics must be an array, got {type(metrics_raw).__name__}.")
        return
    metrics = metrics_raw or []
    non_dict = [i for i, m in enumerate(metrics) if not isinstance(m, dict)]
    if non_dict:
        add("continuous_metrics_malformed", "ERROR",
            f"definition.metrics entries {non_dict} must be objects like "
            f"{{\"event\": ..., \"aggregation\": ...}}, got "
            f"{[type(metrics[i]).__name__ for i in non_dict]}.")
        return

    per_user = [m for m in metrics
                if _norm(m.get("aggregation")) in PER_USER_AGGREGATIONS]
    dist = [m for m in metrics
            if _norm(m.get("aggregation")) in EVENT_LEVEL_DISTRIBUTION]

    if ctx.get("distribution") == "user_level":
        add("continuous_basis", "PASS",
            "Continuous inference uses an explicitly declared external user-level distribution. "
            "Build mean/std/n from one row per exposed user, including zero contributors, and keep "
            "the same cohort definition for both arms.")
        return

    if per_user:
        add("continuous_basis", "ERROR",
            "The event-model avg_per_user aggregate is descriptive only. It does not prove that "
            "exposed users who never fired the metric event were included as zero, and it does not "
            "supply a per-user standard deviation over that same exposed cohort. Do not feed it to "
            "Welch's t-test. Supply an external one-row-per-exposed-user distribution and declare "
            "`--distribution user_level`, or report the aggregate as a point estimate without a "
            "significance claim.")
        return

    if dist:
        aggs = [m.get("aggregation") for m in dist]
        events = sorted({str(m.get("event")) for m in dist if m.get("event")})
        props = sorted({str(m.get("property")) for m in dist if m.get("property")})
        add("continuous_basis", "ERROR",
            f"The continuous metric is built from event-level {aggs} of {props} on {events}. That is "
            f"the distribution of the EVENT (or of the users who triggered it) — typically payers "
            f"only — not of the exposed cohort. Welch's t-test on those numbers compares payers with "
            f"payers and ignores every exposed user who contributed 0, which is most of the cohort "
            f"and is exactly what ARPU is supposed to include. Supply a user-level distribution "
            f"with one row per exposed user, including zero contributors "
            f"(--distribution user_level).")
        return

    add("continuous_basis", "ERROR",
        "No per-user basis declared for a continuous metric. A mean and a standard deviation have "
        "to come from ONE observation per user over the exposed cohort — an event-count or "
        "event-sum denominator describes a different quantity. Supply a one-row-per-exposed-user "
        "distribution and declare --distribution user_level.")


def check(payload, kind, ctx):
    checks = []

    def add(check, status, message):
        checks.append({"check": check, "status": status, "message": message})

    if not isinstance(payload, dict) or not payload:
        return _fatal(f"Expected a JSON object, got {type(payload).__name__}.", "top_level_shape")

    # The curated CLI takes project/model/definition as separate arguments:
    #   ae-cli analysis adhoc run --project-id ... --model-type ... --definition ...
    # This file is therefore the model definition only. Reject the legacy
    # generic-capability envelope instead of silently accepting a shape that
    # cannot be passed to `--definition`.
    legacy_keys = [k for k in ("project_id", "model_type", "definition") if k in payload]
    if legacy_keys:
        return _fatal(
            "Query file uses the legacy generic-capability envelope "
            f"({', '.join(legacy_keys)}). Store only the model definition in this file and pass "
            "project/model separately with `--project-id` and `--model-type`.",
            "definition_envelope",
        )

    definition = payload
    model_type = _norm(ctx.get("model_type"))

    if kind == "retention":
        if model_type and model_type != "retention":
            # The nested contract does not exist on any other model, so there is
            # nothing meaningful left to inspect.
            add("model_type", "ERROR",
                f"model_type = {model_type!r} but the retention contract was requested. The nested "
                f"`retention` object only exists on the retention model.")
        else:
            add("model_type", "PASS", "model_type = retention")
            check_retention(definition, ctx, add)
    elif kind in ("proportion", "guardrail"):
        if model_type == "funnel":
            add("model_type", "PASS", "model_type = funnel (exposure → success, ordered)")
            check_funnel(definition, ctx, add, kind)
        elif model_type in ("", "event"):
            check_proportion_event_model(definition, ctx, add)
        elif model_type == "retention":
            add("model_type", "ERROR",
                "model_type = retention cannot produce a per-arm conversion count. Use the funnel "
                "model.")
        else:
            add("model_type", "ERROR",
                f"model_type = {model_type!r} does not establish an exposure cohort. Use the funnel "
                f"model.")
    elif kind == "continuous":
        if model_type != "event":
            add("model_type", "ERROR",
                f"model_type = {model_type!r}, but continuous metrics in this workflow require "
                "the event model (or an explicitly declared external user-level distribution).")
        else:
            add("model_type", "PASS", "model_type = event")
            check_continuous(definition, ctx, add)

    if any(c["status"] == "FATAL" for c in checks):
        status = "FATAL"
    elif any(c["status"] == "ERROR" for c in checks):
        status = "ERROR"
    elif any(c["status"] == "WARN" for c in checks):
        status = "WARN"
    else:
        status = "SUCCESS"
    return {"status": status, "kind": kind, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="Validate an ae-cli query definition")
    parser.add_argument("definition_file", help="Path to the JSON passed to ae-cli --definition")
    parser.add_argument("--model-type", required=True,
                        choices=("event", "funnel", "retention"),
                        help="Value passed to ae-cli analysis adhoc run --model-type")
    parser.add_argument("--kind", required=True, choices=VALID_KINDS,
                        help="Which contract to enforce")
    parser.add_argument("--exposure-event", default="",
                        help="Declared exposure event (proportion / guardrail)")
    parser.add_argument("--variant-field", default="",
                        help="Declared A/B group field")
    parser.add_argument("--distribution", default="",
                        help="`user_level` when the per-user distribution is sourced externally")
    args = parser.parse_args()

    try:
        with open(args.definition_file, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        print(json.dumps(_fatal(f"Query definition not found: {args.definition_file}",
                                "file_readable"), ensure_ascii=False, indent=2))
        sys.exit(1)
    except OSError as exc:
        print(json.dumps(_fatal(f"Cannot read query definition: {exc}", "file_readable"),
                         ensure_ascii=False, indent=2))
        sys.exit(1)

    if not raw.strip():
        print(json.dumps(_fatal("Query definition file is empty (0 bytes).", "file_not_empty"),
                         ensure_ascii=False, indent=2))
        sys.exit(1)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps(_fatal(f"Query definition is not valid JSON: {exc}", "json_parse"),
                         ensure_ascii=False, indent=2))
        sys.exit(1)

    ctx = {"model_type": args.model_type,
           "exposure_event": args.exposure_event, "variant_field": args.variant_field,
           "distribution": args.distribution}
    result = check(payload, args.kind, ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result["status"] in ("FATAL", "ERROR") else 0)


if __name__ == "__main__":
    main()
