"""Inspect onset reachability and current inactivity deadlines without changing scores.

The current gap's deadline is conditional on no earlier qualifying activity. It
is neither a predicted event time nor an estimate of intervention benefit.
"""
import argparse
import json
from numbers import Integral
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from churn_feature_engineering import qualifying_events
from data_provenance import resolve_data_kind
from event_time import parse_timestamps
from feature_schema import read_csv


def _positive_days(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _endpoint(value, timezone, name):
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a valid timestamp") from exc
    if pd.isna(stamp) or (stamp.tzinfo is None) != (timezone is None):
        raise ValueError(f"{name} must be nonmissing and use the same timezone awareness as events")
    return stamp.tz_convert(timezone) if timezone is not None else stamp


def _identifiers(frame, name, unique=False):
    if "user_id" not in frame or frame.user_id.isna().any():
        raise ValueError(f"{name} requires non-null user_id")
    frame["user_id"] = frame.user_id.astype(str)
    if frame.user_id.str.strip().eq("").any() or (unique and frame.user_id.duplicated().any()):
        raise ValueError(f"{name} user_id must be nonempty" + (" and unique within one snapshot/model" if unique else ""))


def _selection(values):
    # Do not let strings such as 'False' become truthy and mark everyone selected.
    mapped = values.astype("string").str.lower().map({"true": True, "false": False,
                                                     "1": True, "0": False})
    if mapped.isna().any():
        raise ValueError("selected_for_contact must contain complete boolean or 0/1 values")
    return mapped.astype(bool)


def diagnose_onset(events, predictions, snapshot_time, churn_inactivity_days,
                   prediction_days, label_criterion="any", core_events=None,
                   score_column=None, data_kind=None, *, project_timezone=None):
    """Return a JSON-safe summary and one diagnostic row per supplied prediction.

    Predictions must represent one snapshot and one model. Ineligible users are
    retained and counted explicitly. Without selected_for_contact, no candidate
    population is inferred. Optional churn labels are analyzed, not regenerated.
    """
    D = _positive_days(churn_inactivity_days, "churn_inactivity_days")
    H = _positive_days(prediction_days, "prediction_days")
    events, predictions = events.copy(), predictions.copy().reset_index(drop=True)
    _identifiers(events, "events")
    _identifiers(predictions, "predictions", unique=True)
    if not {"event_name", "event_time"}.issubset(events) or events.empty:
        raise ValueError("events requires nonempty event_name and event_time columns")
    if events[["event_name", "event_time"]].isna().any().any():
        raise ValueError("events requires non-null event_name and event_time")
    events["event_time"] = parse_timestamps(events.event_time, project_timezone=project_timezone)
    timezone = events.event_time.dt.tz
    T = _endpoint(snapshot_time, timezone, "snapshot_time")
    for column in ("snapshot_time", "snapshot_date"):
        if column in predictions:
            if not predictions[column].map(lambda v: _endpoint(v, timezone, column) == T).all():
                raise ValueError(f"predictions {column} differs from requested snapshot_time")
    if "requested_model" in predictions and predictions.requested_model.nunique(dropna=False) > 1:
        raise ValueError("predictions must contain only one requested_model")
    if "model" in predictions and predictions.model.nunique(dropna=False) > 1:
        raise ValueError("predictions must contain only one model")
    if isinstance(core_events, str):
        core_events = {v.strip() for v in core_events.split(",") if v.strip()}
    if label_criterion == "pay" and "pay_amount" in events:
        events["pay_amount"] = pd.to_numeric(events.pay_amount, errors="raise").fillna(0)
        if not np.isfinite(events.pay_amount.to_numpy(dtype=float)).all():
            raise ValueError("pay_amount must be finite")
    qualified = qualifying_events(events[events.event_time < T], label_criterion, core_events)
    last = qualified.groupby("user_id", observed=True).event_time.max()
    missing = ~predictions.user_id.isin(last.index)
    if missing.any():
        raise ValueError(f"{int(missing.sum())} prediction users lack qualifying activity strictly before T")
    detail = predictions.copy()
    detail["last_qualifying_event_time"] = last.reindex(detail.user_id).array
    # Keep elapsed seconds: the feature builder's integer recency loses boundary information.
    elapsed = T - detail.last_qualifying_event_time
    recency = elapsed.dt.total_seconds() / 86400.0
    detail["recency_days_exact"] = recency
    detail["eligible_at_snapshot"] = elapsed.ge(pd.Timedelta(0)) & elapsed.lt(pd.Timedelta(days=D))
    detail["current_gap_deadline"] = detail.last_qualifying_event_time + pd.Timedelta(days=D)
    detail["hours_until_current_gap_deadline"] = (detail.current_gap_deadline - T).dt.total_seconds() / 3600.0
    detail["onset_reachable_within_horizon"] = detail.eligible_at_snapshot & detail.current_gap_deadline.lt(T + pd.Timedelta(days=H))
    eligible = detail[detail.eligible_at_snapshot]
    reachable = eligible[eligible.onset_reachable_within_horizon]
    n_unreachable = len(eligible) - len(reachable)
    summary = {
        "snapshot_time": T.isoformat(), "users": len(detail),
        **resolve_data_kind(data_kind, frames=(("events", events), ("predictions", predictions))),
        "definition": {"churn_inactivity_days": D, "prediction_days": H,
                       "label_criterion": label_criterion, "core_events": sorted(core_events or [])},
        "eligible_users": len(eligible), "ineligible_users": len(detail) - len(eligible),
        "reachability": {"necessary_condition": "0 <= r < D and r > D-H; r is exact qualifying-activity recency",
                         "reachable_users": len(reachable), "unreachable_users": n_unreachable,
                         "unreachable_fraction_of_eligible": n_unreachable / len(eligible) if len(eligible) else None},
        "reachable_label_metrics": {"available": False, "reason": "no churn labels supplied"},
        "candidates": {"available": False, "reason": "selected_for_contact absent; no candidate population inferred"},
        "interpretation": "Current-gap deadlines assume no earlier qualifying return. They are not predicted event times or intervention effects; this diagnostic does not alter scores, eligibility or D/H.",
    }
    if "churn" in detail:
        labels = pd.to_numeric(detail.churn, errors="raise")
        if labels.isna().any() or not labels.isin([0, 1]).all():
            raise ValueError("churn must contain complete binary 0/1 labels")
        detail["churn"] = labels.astype(int)
        subset = detail[detail.onset_reachable_within_horizon]
        positives = int(subset.churn.sum())
        metric = {"available": True, "users": len(subset), "positives": positives,
                  "negatives": len(subset) - positives, "roc_auc": None,
                  "positive_labels_outside_reachable": int(detail.loc[~detail.onset_reachable_within_horizon, "churn"].sum())}
        score_column = score_column or next((c for c in ("risk_score", "churn_probability") if c in detail), None)
        if subset.churn.nunique() < 2:
            metric["reason"] = "reachable subgroup has fewer than two label classes; AUC undefined"
        elif score_column is None:
            metric["reason"] = "no ranking score column supplied"
        else:
            if score_column not in detail:
                raise ValueError(f"score column missing: {score_column}")
            scores = pd.to_numeric(detail[score_column], errors="raise")
            if not np.isfinite(scores.to_numpy(dtype=float)).all():
                raise ValueError("ranking scores must be finite")
            metric["roc_auc"] = float(roc_auc_score(subset.churn, scores.loc[subset.index]))
            metric["reason"] = ""
        metric["score_column"] = score_column
        summary["reachable_label_metrics"] = metric
    if "selected_for_contact" in detail:
        detail["selected_for_contact"] = _selection(detail.selected_for_contact)
        selected = detail[detail.selected_for_contact]
        hours = selected.hours_until_current_gap_deadline
        remaining = selected.current_gap_deadline - T
        future = hours[hours > 0]
        summary["candidates"] = {
            "available": True, "users": len(selected),
            "eligible_at_snapshot": int(selected.eligible_at_snapshot.sum()),
            "at_or_past_deadline": int(remaining.le(pd.Timedelta(0)).sum()),
            "future_deadline_within_hours": {str(h): int((remaining.gt(pd.Timedelta(0)) & remaining.le(pd.Timedelta(hours=h))).sum()) for h in (24, 48, 72)},
            "remaining_hours_eligible": {"min": float(future.min()) if len(future) else None,
                                         "median": float(future.median()) if len(future) else None,
                                         "max": float(future.max()) if len(future) else None},
        }
    detail["data_kind"] = summary["data_kind"]
    return summary, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True)
    parser.add_argument("--predictions", required=True, help="one snapshot and one model; user_id required")
    parser.add_argument("--snapshot-time", required=True)
    parser.add_argument("--timezone", help="project timezone for offset-aware event timestamps")
    parser.add_argument("--churn-inactivity-days", type=int, required=True)
    parser.add_argument("--prediction-days", type=int, required=True)
    parser.add_argument("--label-criterion", choices=("any", "core", "pay"), default="any")
    parser.add_argument("--core-events")
    parser.add_argument("--score-column")
    parser.add_argument("--data-kind", choices=("real", "simulated"))
    parser.add_argument("--output", required=True, help="JSON summary")
    parser.add_argument("--details-output", help="optional per-user CSV")
    args = parser.parse_args()
    try:
        result, detail = diagnose_onset(read_csv(args.events), read_csv(args.predictions),
                                       args.snapshot_time, args.churn_inactivity_days,
                                       args.prediction_days, args.label_criterion,
                                       args.core_events, args.score_column, args.data_kind,
                                       project_timezone=args.timezone)
    except (TypeError, ValueError, OverflowError) as exc:
        parser.error(str(exc))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    if args.details_output:
        target = Path(args.details_output)
        target.parent.mkdir(parents=True, exist_ok=True)
        detail.to_csv(target, index=False)
    print(f"diagnosed {result['users']} users; output: {output}")


if __name__ == "__main__":
    main()
