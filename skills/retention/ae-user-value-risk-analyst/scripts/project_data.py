"""Validate declared export semantics and observability before feature generation.

Inputs are canonical event CSVs, not raw AE tables. Business mappings are resolved
by the agent and confirmed before use; declarations do not prove ingestion health.
"""
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from event_time import parse_timestamps


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"project config {field} must be a nonempty string")
    return value.strip()


def _names(value, field):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"project config {field} must be a list of nonempty event names")
    return sorted(set(v.strip() for v in value))


def normalize_project_config(value):
    """Return a deterministic semantic contract, excluding per-export coverage."""
    if not isinstance(value, dict):
        raise ValueError("project config must be a JSON object")
    required = {"schema_version", "project_id", "identity_field", "timezone", "timestamp_mode",
                "event_catalog", "event_scope", "core_events", "payment", "session_mode",
                "feature_reference", "sampling"}
    missing = required - value.keys()
    extra = value.keys() - required - {"coverage", "notes"}
    if missing or extra:
        raise ValueError(f"project config missing fields={sorted(missing)}, unknown fields={sorted(extra)}")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("project config schema_version must be 1")
    result = {"schema_version": 1}
    for field in ("project_id", "identity_field", "timezone", "feature_reference", "sampling"):
        result[field] = _text(value[field], field)
    ZoneInfo(result["timezone"])
    for field, choices in (("timestamp_mode", ("naive_local", "aware")),
                           ("session_mode", ("provided", "derived"))):
        if value[field] not in choices:
            raise ValueError(f"project config {field} must be one of {choices}")
        result[field] = value[field]
    catalog = set(_names(value["event_catalog"], "event_catalog"))
    if not catalog:
        raise ValueError("project config event_catalog cannot be empty; resolve metadata first")
    scope = value["event_scope"]
    if not isinstance(scope, dict) or set(scope) != {"include", "exclude"}:
        raise ValueError("project config event_scope requires include and exclude lists")
    scope = {k: _names(scope[k], f"event_scope.{k}") for k in ("include", "exclude")}
    if (set(scope["include"]) | set(scope["exclude"])) - catalog:
        raise ValueError("event_scope contains names absent from event_catalog")
    if set(scope["include"]) & set(scope["exclude"]):
        raise ValueError("event_scope include and exclude overlap")
    allowed = (set(scope["include"]) or catalog) - set(scope["exclude"])
    if not allowed:
        raise ValueError("event_scope leaves no allowed activity events")
    core = _names(value["core_events"], "core_events")
    if set(core) - allowed:
        raise ValueError("core_events must exist in event_catalog and the exported event_scope")
    payment = value["payment"]
    if not isinstance(payment, dict) or payment.get("mode") not in ("measured", "not_applicable", "unavailable"):
        raise ValueError("payment.mode must be measured, not_applicable or unavailable")
    if payment["mode"] == "measured":
        if set(payment) != {"mode", "events", "source_field", "currency"}:
            raise ValueError("measured payment requires mode, events, source_field and currency")
        names = _names(payment["events"], "payment.events")
        if not names or set(names) - allowed:
            raise ValueError("payment.events must exist in event_catalog and the exported event_scope")
        payment = {"mode": "measured", "events": names,
                   "source_field": _text(payment["source_field"], "payment.source_field"),
                   "currency": _text(payment["currency"], "payment.currency")}
    elif set(payment) != {"mode"}:
        raise ValueError("disabled payment accepts only mode; remove monetary mappings")
    result.update(event_catalog=sorted(catalog), event_scope=scope, core_events=core, payment=payment)
    return result


def load_project_config(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalize_project_config(raw), raw.get("coverage")


def contract_fingerprint(contract):
    return hashlib.sha256(json.dumps(contract, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def compare_contracts(saved, current):
    if saved is not None:
        if current is None:
            raise ValueError("saved model requires --project-config for the current export")
        changed = [key for key in sorted(set(saved) | set(current)) if saved.get(key) != current.get(key)]
        if changed:
            raise ValueError(f"project data definition differs from saved model: {', '.join(changed)}; "
                             "restore the trained definition or retrain and validate")


def _endpoint(value, timezone, field):
    result = pd.Timestamp(value)
    if pd.isna(result) or (result.tz is None) != (timezone is None):
        raise ValueError(f"{field} must have the same timestamp awareness as event_time")
    return result.tz_convert(timezone) if timezone is not None else result


def preflight_events(events, definition, snapshot_time, contract=None, coverage=None,
                     data_end=None, labeled=False, allow_empty=False):
    """Report blockers/warnings without filling missing observations with behavior.

    Contracted runs block unobservable measured payment, mapping/scope/session
    mismatches and insufficient declared coverage. Legacy runs remain explicit
    about unknown semantics. The feature schema is unchanged.
    """
    report = {"status": "ok", "errors": [], "warnings": [], "rows": len(events),
              "users": 0, "contract_status": "declared" if contract else "unverified_legacy",
              "contract_fingerprint": contract_fingerprint(contract) if contract else None}
    errors, warnings = report["errors"], report["warnings"]
    required = ["user_id", "event_name", "event_time"]
    if set(required) - set(events):
        errors.append(f"missing required columns: {sorted(set(required) - set(events))}")
    elif events[required].isna().any().any():
        errors.append("user_id, event_name and event_time cannot contain null values")
    elif any(events[c].astype(str).str.strip().eq("").any() for c in required):
        errors.append("user_id, event_name and event_time cannot contain empty strings")
    if events.empty and not allow_empty:
        errors.append("event export is empty")
    if errors:
        report["status"] = "blocked"
        return report
    report["users"] = int(events.user_id.nunique())
    if "session_id" in events and (events.session_id.isna().any() or events.session_id.astype(str).str.strip().eq("").any()):
        errors.append("supplied session_id contains missing/empty values; omit the whole column to derive sessions")
    if contract is None and "pay_amount" in events:
        try:
            amounts = pd.to_numeric(events.pay_amount, errors="raise")
            if np.isinf(amounts.to_numpy(dtype=float)).any():
                errors.append("pay_amount contains nonfinite values")
        except (ValueError, TypeError):
            errors.append("pay_amount contains nonnumeric values")
    try:
        times = parse_timestamps(events.event_time, project_timezone=contract["timezone"] if contract else None)
        if events.empty:
            if contract is None:
                empty_timezone = pd.Timestamp(snapshot_time).tz
            else:
                empty_timezone = contract["timezone"] if contract["timestamp_mode"] == "aware" else None
            times = pd.Series(pd.DatetimeIndex([], tz=empty_timezone), index=events.index)
        timezone = times.dt.tz
        T = _endpoint(snapshot_time, timezone, "snapshot T")
        horizon = pd.Timedelta(days=definition.get("prediction_days") or 0)
        end = T + horizon if labeled else T
        if contract:
            expected_aware = contract["timestamp_mode"] == "aware"
            # Empty exports have no timestamp representation to check.
            if not events.empty and (timezone is not None) != expected_aware:
                raise ValueError("event_time awareness differs from project timestamp_mode")
        if data_end is not None and end > _endpoint(data_end, timezone, "data-end"):
            errors.append("snapshot/label end exceeds data-end")
        if coverage is not None:
            if not isinstance(coverage, dict) or set(coverage) != {"start", "end", "verified", "evidence"}:
                raise ValueError("coverage requires start, end, verified and evidence")
            if coverage["verified"] is not True:
                raise ValueError("coverage must be independently verified; omit it when unknown")
            _text(coverage["evidence"], "coverage.evidence")
            start = _endpoint(coverage["start"], timezone, "coverage.start")
            bound = _endpoint(coverage["end"], timezone, "coverage.end")
            history_days = max(definition["churn_days"], definition.get("churn_inactivity_days") or 0)
            if start >= bound or start > T - pd.Timedelta(days=history_days) or bound < end:
                errors.append("verified coverage does not contain the required history and label/snapshot interval")
            if data_end is not None and _endpoint(data_end, timezone, "data-end") != bound:
                errors.append("data-end differs from project coverage.end")
            if ((times < start) | (times >= bound)).any():
                errors.append("event rows lie outside the declared [coverage.start, coverage.end)")
            report["coverage"] = coverage
        else:
            warnings.append("No verified coverage interval: event presence cannot prove history or stream completeness.")
        historical = events.loc[times < T]
    except (ValueError, TypeError, AttributeError) as exc:
        errors.append(str(exc))
        report["status"] = "blocked"
        return report
    core = set(filter(None, (definition.get("core_events") or "").split(",")))
    if definition.get("label_criterion") == "core" and not core:
        errors.append("core activity criterion requires configured core events")
    if core and not historical.event_name.isin(core).any():
        warnings.append("No configured core activity observed before T; absence is not proof of no instrumentation.")
    if contract:
        allowed = (set(contract["event_scope"]["include"]) or set(contract["event_catalog"])) - set(contract["event_scope"]["exclude"])
        unexpected = sorted(set(events.event_name) - allowed)
        if unexpected:
            errors.append(f"event export violates catalog/scope: {unexpected}")
        if core != set(contract["core_events"]):
            errors.append("core_events differ from project config")
        if contract["session_mode"] == "provided":
            if "session_id" not in events or events.session_id.isna().any() or events.session_id.astype(str).str.strip().eq("").any():
                errors.append("provided session mode requires complete nonempty session_id")
        elif "session_id" in events:
            errors.append("derived session mode requires omitting session_id; do not silently change session semantics")
        payment = contract["payment"]
        report["feature_availability"] = {"core": "configured" if core else "disabled_unconfigured",
                                          "payment": payment["mode"], "sessions": contract["session_mode"]}
        if definition.get("label_criterion") == "pay" and payment["mode"] != "measured":
            errors.append("pay activity criterion requires measured payment")
        try:
            if payment["mode"] == "measured" and "pay_amount" not in events:
                raise ValueError("measured payment requires pay_amount; missing money is not zero spend")
            if "pay_amount" in events:
                amounts = pd.to_numeric(events.pay_amount, errors="raise")
                if not np.isfinite(amounts.to_numpy(dtype=float)).all():
                    raise ValueError("pay_amount contains missing/nonfinite values; resolve the export mapping")
                if payment["mode"] == "measured":
                    if (amounts < 0).any() or amounts.loc[~events.event_name.isin(payment["events"])].ne(0).any():
                        raise ValueError("pay_amount must be nonnegative and zero outside mapped payment events")
                elif amounts.ne(0).any():
                    raise ValueError("disabled payment must omit pay_amount or supply only explicit zeros")
        except (ValueError, TypeError) as exc:
            errors.append(str(exc))
        if payment["mode"] != "measured":
            warnings.append(f"Payment is {payment['mode']}; constant monetary placeholders are disabled inputs, not observed zero spend. Changing this mode requires retraining.")
        if not core:
            warnings.append("Core features are disabled/unconfigured; 0/9999 placeholders are not observations of core behavior.")
    else:
        warnings.append("Legacy run: project/event/payment/reference semantics are unverified; use --project-config for new customer models.")
        if "pay_amount" not in events or events.pay_amount.isna().any():
            warnings.append("Monetary data is absent/partially missing; legacy features may encode it as zero, not verified no-payment behavior.")
    report["status"] = "blocked" if errors else "warning" if warnings else "ok"
    return report
