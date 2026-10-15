#!/usr/bin/env python3
"""Independently validate measurement JSON and optional rendered artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from render_charts import render_svg
from render_report import build_summary, render_markdown
from report_model import (
    REPORT_CONTRACT_VERSION,
    RESULT_SCHEMA_VERSION,
    ReportModelError,
    enrich_result,
    validate_result,
)


class OutputValidationError(ValueError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OutputValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OutputValidationError(f"{path} must contain a JSON object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise OutputValidationError(message)


def validate_measurement(result: dict[str, Any]) -> list[str]:
    warnings = validate_result(result, strict=True)
    require(result.get("schema_version") == RESULT_SCHEMA_VERSION, "unexpected result schema version")
    require(
        result.get("report_contract_version") == REPORT_CONTRACT_VERSION,
        "unexpected report contract version",
    )
    require(result.get("verdict") in {"delay_observed", "no_delay_observed"}, "measurement is not complete")

    total = int(result.get("total_rows") or 0)
    require(total >= 0, "total_rows must be non-negative")
    segments = result.get("delay_segments") or {}
    require(bool(segments), "delay_segments is required")
    for name, segment in segments.items():
        if segment.get("status") != "measured":
            continue
        samples = int(segment.get("sample_count") or 0)
        require(0 < samples <= total, f"{name} sample_count is outside total_rows")
        seconds = segment.get("seconds") or {}
        require(all(key in seconds for key in ("min", "p50", "p95", "max")), f"{name} percentiles are incomplete")

    timezone = result.get("timezone_quality") or {}
    for key in ("valid_count", "missing_count", "invalid_count", "covered_count"):
        count = int(timezone.get(key) or 0)
        require(0 <= count <= total, f"timezone_quality.{key} is outside total_rows")
    require(bool(result.get("diagnosis")), "diagnosis is required")
    require(isinstance(result.get("warnings"), list), "warnings must be a list")
    return warnings


def validate_artifacts(
    result: dict[str, Any],
    report_path: Path,
    summary_path: Path,
    chart_path: Path,
    chart_ref: str,
) -> None:
    try:
        report = report_path.read_text(encoding="utf-8")
        chart = chart_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise OutputValidationError(f"cannot read rendered artifact: {exc}") from exc
    summary = load_object(summary_path)
    enriched = enrich_result(result)
    require(report == render_markdown(enriched, chart_ref), "report does not match the current result JSON")
    require(summary == build_summary(enriched), "summary does not match the current result JSON")
    require(chart == render_svg(enriched), "chart does not match the current result JSON")


def self_test() -> None:
    segment = {
        "status": "measured",
        "sample_count": 1,
        "seconds": {"min": 1, "p50": 1, "p95": 1, "max": 1},
        "distribution": {"b1": 1, "b2": 0, "b3": 0, "b4": 0, "b5": 0, "b6": 0, "b7": 0, "negative": 0},
    }
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "report_contract_version": REPORT_CONTRACT_VERSION,
        "verdict": "no_delay_observed",
        "window": {"start_date": "2026-01-01", "end_date": "2026-01-01"},
        "total_rows": 1,
        "delay_segments": {"event_to_receive": segment},
        "timezone_quality": {"valid_count": 1, "missing_count": 0, "invalid_count": 0, "covered_count": 1},
        "diagnosis": {"overall": {"code": "no_delay_observed"}},
        "warnings": [],
    }
    enriched = enrich_result(result)
    validate_measurement(enriched)
    with TemporaryDirectory(prefix="ae-delay-validator-") as directory:
        root = Path(directory)
        report = root / "report.md"
        summary = root / "summary.json"
        chart = root / "chart.svg"
        report.write_text(render_markdown(enriched, "delay_charts.svg"), encoding="utf-8")
        summary.write_text(
            json.dumps(build_summary(enriched), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        chart.write_text(render_svg(enriched), encoding="utf-8")
        validate_artifacts(enriched, report, summary, chart, "delay_charts.svg")
        changed = {**enriched, "project_name": "stale-artifact-check"}
        try:
            validate_artifacts(changed, report, summary, chart, "delay_charts.svg")
        except (OutputValidationError, ReportModelError):
            pass
        else:
            raise OutputValidationError("stale artifact set was accepted")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_json", nargs="?", help="Processed checker result JSON")
    parser.add_argument("--report", help="Rendered Markdown report")
    parser.add_argument("--summary", help="Rendered report summary JSON")
    parser.add_argument("--chart", help="Rendered SVG chart")
    parser.add_argument("--chart-ref", default="delay_charts.svg", help="Chart reference used in the Markdown report")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.self_test:
            self_test()
            print(json.dumps({"ok": True, "self_test": "passed"}))
            return
        require(bool(args.result_json), "result_json is required")
        artifact_args = (args.report, args.summary, args.chart)
        require(all(artifact_args) or not any(artifact_args), "--report, --summary, and --chart must be provided together")
        result = load_object(Path(args.result_json))
        warnings = validate_measurement(result)
        if all(artifact_args):
            validate_artifacts(
                result,
                Path(args.report),
                Path(args.summary),
                Path(args.chart),
                args.chart_ref,
            )
        print(json.dumps({"ok": True, "warnings": warnings, "artifacts_checked": bool(args.report)}))
    except (OutputValidationError, ReportModelError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
