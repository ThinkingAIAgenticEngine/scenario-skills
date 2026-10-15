#!/usr/bin/env python3
"""Validate experiment parameters before running ae-cli queries."""
import argparse
import json
import sys


def validate_params(project_id, variant_property, success_events, time_range="", guardrail_events="", filters=""):
    """Check that all required experiment parameters are present.

    Required: project_id, variant_property, success_events, time_range.
    Optional (format-checked only): guardrail_events, filters.
    """
    checks = []

    if not project_id:
        checks.append({"check": "project_id", "status": "FATAL",
                        "message": "project_id is required. Ask user which AE/TE project the experiment is in."})
    else:
        try:
            pid = int(project_id)
            if pid <= 0:
                checks.append({"check": "project_id", "status": "FATAL",
                                "message": f"project_id must be a positive integer, got {pid}"})
            else:
                checks.append({"check": "project_id", "status": "PASS",
                                "message": f"project_id = {pid}"})
        except (ValueError, TypeError):
            checks.append({"check": "project_id", "status": "FATAL",
                            "message": f"project_id must be numeric, got '{project_id}'"})

    if not variant_property:
        checks.append({"check": "variant_property", "status": "FATAL",
                        "message": "variant_property is required. Ask user which event/user property stores the A/B group assignment (e.g., ab_group, experiment_variant)."})
    else:
        checks.append({"check": "variant_property", "status": "PASS",
                        "message": f"variant_property = {variant_property}"})

    if not success_events:
        checks.append({"check": "success_events", "status": "FATAL",
                        "message": "success_events is required. Ask user which events measure success (e.g., purchase, level_complete)."})
    else:
        events = [e.strip() for e in success_events.split(",") if e.strip()]
        if len(events) == 0:
            checks.append({"check": "success_events", "status": "FATAL",
                            "message": "At least one success event is required."})
        else:
            checks.append({"check": "success_events", "status": "PASS",
                            "message": f"success_events = {events}"})

    if not time_range:
        checks.append({"check": "time_range", "status": "FATAL",
                        "message": "time_range is required. Ask user the experiment time range (e.g., 'recent 7 days', '2026-01-01 to 2026-01-14')."})
    else:
        checks.append({"check": "time_range", "status": "PASS",
                        "message": f"time_range = {time_range}"})

    # Optional: guardrail events (metrics that should NOT regress)
    if guardrail_events:
        g_events = [e.strip() for e in guardrail_events.split(",") if e.strip()]
        checks.append({"check": "guardrail_events", "status": "PASS",
                        "message": f"guardrail_events = {g_events}"})
    else:
        checks.append({"check": "guardrail_events", "status": "WARN",
                        "message": "No guardrail metrics specified. Guardrail check will be skipped."})

    # Optional: global filters (platform/country/etc.)
    if filters:
        checks.append({"check": "filters", "status": "PASS",
                        "message": f"filters = {filters}"})

    fatals = [c for c in checks if c["status"] == "FATAL"]
    if fatals:
        return {"status": "FATAL", "checks": checks}
    return {"status": "SUCCESS", "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="Validate A/B test experiment parameters")
    parser.add_argument("--project-id", required=False, default="")
    parser.add_argument("--variant-property", required=False, default="")
    parser.add_argument("--success-events", required=False, default="")
    parser.add_argument("--time-range", required=False, default="")
    parser.add_argument("--guardrail-events", required=False, default="")
    parser.add_argument("--filters", required=False, default="")
    args = parser.parse_args()

    result = validate_params(args.project_id, args.variant_property, args.success_events,
                             args.time_range, args.guardrail_events, args.filters)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "FATAL":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
