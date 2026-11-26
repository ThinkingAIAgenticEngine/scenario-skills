"""Forward-only churn backtests with an independent calibration snapshot.

Snapshot dates are feature cutoffs T, not label-window endpoints. Each test
snapshot uses only training labels available by its calibration cutoff, and
calibration labels available by its test cutoff. No model is published here.
"""
import argparse
import json
from numbers import Integral
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from auto_model_selection import has_lib
from churn_feature_engineering import _parse_endpoint, build_features, qualifying_events
from data_provenance import resolve_data_kind
from evaluation_metrics import evaluate_predictions, contact_mask
from event_time import parse_timestamps
from feature_schema import META_COLS, model_features, read_csv
from onset_constraints import onset_reachability, constrain_probabilities
from train_churn_model import train_bundle
from project_data import load_project_config, preflight_events

MODEL_NAMES = {"recency_rule", "logistic_regression", "lightgbm", "xgboost", "random_forest"}
PREDICTION_COLS = ["snapshot_time", "requested_model", "model", "user_id", "churn",
                   "risk_score", "churn_probability", "model_score", "onset_reachable_within_horizon",
                   "score_type", "rank", "selected_for_contact"]
SUMMARY_COLS = ["snapshot_time", "calibration_snapshot_time", "requested_model", "model", "status",
                "users", "positives", "base_rate", "roc_auc", "pr_auc", "brier_score", "log_loss",
                "selected", "precision_at_k", "recall_at_k", "lift_at_k", "ece", "calibrated", "reason"]


def make_schedule(snapshot_dates, prediction_days, coverage_end, now=None, *,
                  coverage_start=None, history_days=None, allow_empty=False):
    """Return auditable expanding-window folds without overlapping label windows."""
    if not isinstance(prediction_days, (int, np.integer)) or prediction_days <= 0:
        raise ValueError("prediction_days must be a positive integer")
    coverage_end = pd.Timestamp(coverage_end)
    if pd.isna(coverage_end):
        raise ValueError("data coverage endpoint must be a valid timestamp")
    timezone = coverage_end.tz
    dates = sorted(_parse_endpoint(value, "snapshot date", timezone) for value in snapshot_dates)
    if len(set(dates)) != len(dates):
        raise ValueError("snapshot dates must be valid and unique")
    if coverage_start is not None:
        coverage_start = _parse_endpoint(coverage_start, "data coverage start", timezone)
        if coverage_start > coverage_end:
            raise ValueError("data coverage start must not exceed its end")
        if not isinstance(history_days, Integral) or history_days <= 0:
            raise ValueError("history_days must be a positive integer when checking coverage start")
        lookback = pd.Timedelta(days=int(history_days))
    now = pd.Timestamp.now(tz=timezone) if now is None else _parse_endpoint(now, "current time", timezone)
    horizon = pd.Timedelta(days=int(prediction_days))
    manifest = []
    mature = []
    for date in dates:
        end = date + horizon
        entry = {"snapshot_time": date.isoformat(), "label_end": end.isoformat(), "status": "mature", "reason": ""}
        if coverage_start is not None:
            history_start = date - lookback
            entry["history_start"] = history_start.isoformat()
            if history_start < coverage_start:
                entry.update(status="skipped", reason="history window starts before data coverage")
        if end > coverage_end or end > now:
            entry.update(status="skipped", reason="label window exceeds data coverage or current time")
        manifest.append(entry)
        if entry["status"] == "mature":
            mature.append(date)
    if len(mature) < 3 and not allow_empty:
        raise ValueError("backtesting needs at least three mature snapshot dates for train/calibration/test")
    folds = []
    for test in mature:
        candidates = [date for date in mature if date + horizon <= test]
        if not candidates:
            manifest[dates.index(test)].update(status="skipped", reason="no prior mature calibration window")
            continue
        calibration = candidates[-1]
        training = [date for date in mature if date + horizon <= calibration]
        if not training:
            manifest[dates.index(test)].update(status="skipped", reason="no training labels mature before calibration cutoff")
            continue
        folds.append({"training_snapshot_times": [date.isoformat() for date in training],
                      "training_label_end": (training[-1] + horizon).isoformat(),
                      "calibration_snapshot_time": calibration.isoformat(),
                      "calibration_label_end": (calibration + horizon).isoformat(),
                      "test_snapshot_time": test.isoformat(), "test_label_end": (test + horizon).isoformat()})
    if not folds and not allow_empty:
        raise ValueError("snapshot spacing must allow training labels to mature before calibration and calibration labels before test")
    return folds, manifest


def recency_scores(events, user_ids, snapshot_time, label_criterion="any", core_events=None):
    """Rank by inactivity using only qualifying activity before T."""
    cutoff = pd.Timestamp(snapshot_time)
    historical = events[events["event_time"] < cutoff]
    qualified = qualifying_events(historical, label_criterion, core_events)
    last = qualified.groupby("user_id", observed=True)["event_time"].max().reindex(user_ids)
    scores = (cutoff - last).dt.total_seconds() / 86400.0
    sentinel = max(float(scores.max()) if scores.notna().any() else 0.0, 0.0) + 1
    return scores.fillna(sentinel).to_numpy(dtype=float)


def ranking_metrics(y_true, scores, top_k, contact_eligible=None, user_ids=None):
    """Ranking metrics only: recency is deliberately not treated as probability."""
    y = np.asarray(y_true, dtype=float)
    scores = np.asarray(scores, dtype=float)
    if y.ndim != 1 or scores.ndim != 1 or len(y) == 0 or len(y) != len(scores) \
            or not np.isin(y, [0, 1]).all() or not np.isfinite(scores).all():
        raise ValueError("ranking evaluation needs nonempty binary labels and finite aligned scores")
    if isinstance(top_k, (bool, np.bool_)) or not isinstance(top_k, Integral) or top_k <= 0:
        raise ValueError("top_k must be a positive integer")
    y = y.astype(int)
    if user_ids is None:
        order = np.argsort(-scores, kind="mergesort")
    else:
        identifiers = np.asarray(user_ids, dtype=object)
        if identifiers.ndim != 1 or len(identifiers) != len(y) or pd.isna(identifiers).any():
            raise ValueError("user_ids must contain one non-null ID per row")
        identifiers = identifiers.astype(str)
        if len(np.unique(identifiers)) != len(identifiers):
            raise ValueError("user_ids must be unique within snapshot")
        id_order = np.argsort(identifiers, kind="stable")
        order = id_order[np.argsort(-scores[id_order], kind="stable")]
    eligible = contact_mask(contact_eligible, len(y))
    selected = order[eligible[order]][:int(top_k)]
    positives = int(y.sum())
    hits = int(y[selected].sum())
    base_rate = float(y.mean())
    precision = hits / len(selected) if len(selected) else None
    both_classes = len(np.unique(y)) == 2
    return {"users": len(y), "positives": positives, "base_rate": base_rate,
            "roc_auc": float(roc_auc_score(y, scores)) if both_classes else None,
            "pr_auc": float(average_precision_score(y, scores)) if both_classes else None,
            "auc_reason": "" if both_classes else "only one label class",
            "brier_score": None, "log_loss": None, "calibration": None,
            "probability_metrics_reason": "recency is an uncalibrated ranking score",
            "top_k": {"requested": int(top_k), "selected": len(selected), "precision": precision,
                      "recall": hits / positives if positives else None,
                      "lift": precision / base_rate if positives and precision is not None else None,
                      "threshold": float(scores[selected[-1]]) if len(selected) else None,
                      "tie_breaker": "user_id ascending" if user_ids is not None else "input_order"}}


def _prepare_properties(properties, group_columns, *, project_timezone=None):
    if properties is None:
        if group_columns:
            raise ValueError("group-columns requires user-properties")
        return None, []
    properties = properties.copy()
    if "user_id" not in properties or properties["user_id"].isna().any():
        raise ValueError("user-properties requires non-null user_id")
    properties["user_id"] = properties["user_id"].astype(str)
    groups = list(group_columns) if group_columns else (["channel"] if "channel" in properties else [])
    if len(set(groups)) != len(groups) or set(groups) & {"user_id", "snapshot_time"}:
        raise ValueError("group columns must be distinct attributes, excluding user_id and snapshot_time")
    missing = set(groups) - set(properties.columns)
    if missing:
        raise ValueError(f"user-properties missing group columns: {sorted(missing)}")
    keys = ["user_id"]
    if "snapshot_time" in properties:
        properties["snapshot_time"] = parse_timestamps(
            properties["snapshot_time"], "user-properties snapshot_time", project_timezone=project_timezone)
        keys.append("snapshot_time")
    if properties.duplicated(keys).any():
        raise ValueError(f"user-properties must be unique on {keys}")
    return properties, groups


def _snapshot_properties(properties, groups, user_ids, snapshot):
    if properties is None or not groups:
        return None
    available = properties
    if "snapshot_time" in available:
        available = available[available["snapshot_time"] == snapshot]
    merged = pd.DataFrame({"user_id": list(user_ids)}).merge(
        available[["user_id", *groups]], on="user_id", how="left", validate="one_to_one", indicator=True)
    if (merged["_merge"] != "both").any() or merged[groups].isna().any().any():
        raise ValueError(f"user-properties lacks complete group values for test snapshot {snapshot.isoformat()}")
    return merged.drop(columns="_merge")


def _group_evaluations(properties, groups, y, scores, top_k, ranking_only, contact_eligible=None):
    result = []
    if properties is None:
        return result
    for column in groups:
        for value, indices in properties.groupby(column, sort=True, observed=True).groups.items():
            indices = np.asarray(list(indices), dtype=int)
            function = ranking_metrics if ranking_only else evaluate_predictions
            options = {"user_ids": properties["user_id"].iloc[indices]}
            if contact_eligible is not None:
                options["contact_eligible"] = contact_eligible[indices]
            result.append({"column": column, "value": str(value), "selection_scope": "within_group",
                           "metrics": function(np.asarray(y)[indices], np.asarray(scores)[indices], top_k=top_k,
                                               **options)})
    return result


def run_backtest(events, snapshot_dates, churn_days, churn_inactivity_days, prediction_days,
                 label_target="churn_onset", cohort="prevention", label_criterion="any",
                 core_events=None, data_end=None, top_k=500, models=None, user_properties=None,
                 group_columns=None, session_gap_minutes=30, data_kind="unknown", *, data_start=None,
                 project_timezone=None):
    """Evaluate chronological snapshots; test labels are never passed to training."""
    if churn_days <= 0 or churn_inactivity_days <= 0 or top_k <= 0:
        raise ValueError("observation window, inactivity threshold, and top_k must be positive")
    if isinstance(top_k, (bool, np.bool_)) or not isinstance(top_k, Integral):
        raise ValueError("top_k must be a positive integer")
    models = list(models) if models is not None else ["recency_rule", "logistic_regression", "lightgbm"]
    if not models or len(set(models)) != len(models) or set(models) - MODEL_NAMES:
        raise ValueError(f"models must be distinct choices from {sorted(MODEL_NAMES)}")
    if events.empty or not {"user_id", "event_name", "event_time"}.issubset(events):
        raise ValueError("events requires nonempty user_id,event_name,event_time")
    # A declared simulation source must stay visible even when the caller omits
    # --data-kind or passes real. The source CSV is an independent declaration.
    provenance = resolve_data_kind(data_kind, frames=[("events", events)])
    events = events.copy()
    if events[["user_id", "event_name", "event_time"]].isna().any().any():
        raise ValueError("event identifiers/timestamps cannot be null")
    events["user_id"] = events["user_id"].astype(str)
    events["event_time"] = parse_timestamps(events["event_time"], project_timezone=project_timezone)
    core_events = {part.strip() for part in core_events.split(",") if part.strip()} \
        if isinstance(core_events, str) else set(core_events or [])
    if "pay_amount" in events:
        events["pay_amount"] = pd.to_numeric(events["pay_amount"], errors="raise").fillna(0)
    timezone = events["event_time"].dt.tz
    start = (_parse_endpoint(data_start, "--data-start", timezone)
             if data_start is not None else events["event_time"].min())
    end = (_parse_endpoint(data_end, "--data-end", timezone)
           if data_end is not None else events["event_time"].max())
    schedule, manifest = make_schedule(snapshot_dates, prediction_days, end, coverage_start=start,
                                       history_days=max(churn_days, churn_inactivity_days), allow_empty=True)
    coverage = {"start": start.isoformat(), "end": end.isoformat(),
                "start_source": "declared_coverage" if data_start is not None else "first_observed_event",
                "end_source": "declared_coverage" if data_end is not None else "last_observed_event",
                "status": "attested" if data_start is not None and data_end is not None else "unverified"}
    properties, groups = _prepare_properties(user_properties, group_columns, project_timezone=project_timezone)
    config = {"churn_days": int(churn_days), "churn_inactivity_days": int(churn_inactivity_days),
              "prediction_days": int(prediction_days), "label_target": label_target, "cohort": cohort,
              "label_criterion": label_criterion, "core_events": ",".join(sorted(core_events)),
              "session_gap_minutes": int(session_gap_minutes)}
    cache = {}

    def snapshot(date):
        key = pd.Timestamp(date)
        if key not in cache:
            cache[key] = build_features(
                events, churn_days, obs_end=(key + pd.Timedelta(days=prediction_days)).isoformat(),
                core_events=core_events, session_gap_minutes=session_gap_minutes,
                churn_inactivity_days=churn_inactivity_days, label_criterion=label_criterion,
                data_end=end.isoformat(), prediction_days=prediction_days,
                label_target=label_target, cohort=cohort).sort_values("user_id", kind="mergesort").reset_index(drop=True)
        return cache[key]

    available = {name: (has_lib(name) if name in ("lightgbm", "xgboost") else True) for name in models}
    folds, predictions = [], []
    for specification in schedule:
        train = pd.concat([snapshot(date) for date in specification["training_snapshot_times"]], ignore_index=True)
        calibration = snapshot(specification["calibration_snapshot_time"])
        test_date = pd.Timestamp(specification["test_snapshot_time"])
        test = snapshot(test_date)
        fold = {**specification, "training_rows": len(train), "training_unique_users": int(train["user_id"].nunique()),
                "calibration_users": len(calibration), "test_users": len(test), "results": []}
        if test.empty:
            fold.update(status="skipped", reason="no eligible users at the test snapshot")
            folds.append(fold)
            continue
        attrs = _snapshot_properties(properties, groups, test["user_id"], test_date)
        y = test["churn"].to_numpy(dtype=int)
        for requested in models:
            result = {"requested_model": requested, "model": requested, "status": "unavailable", "metrics": None,
                      "group_metrics": [], "reason": "optional model library is not installed"}
            if not available[requested]:
                fold["results"].append(result)
                continue
            try:
                reachable, constraint = onset_reachability(test, config, test_date)
                ranking_only = requested == "recency_rule"
                if ranking_only:
                    model_scores = recency_scores(events, test["user_id"], test_date, label_criterion, core_events)
                    scores = np.where(reachable, model_scores, 0.0)
                    metrics = ranking_metrics(y, scores, top_k, contact_eligible=reachable,
                                              user_ids=test["user_id"])
                    calibrated = False
                else:
                    categorical = [c for c in train.columns if c not in ("user_id", "churn", *META_COLS) and
                                   train[c].nunique(dropna=True) <= 10] if requested == "lightgbm" else []
                    rec = {"model": requested, "categorical_features": categorical if len(categorical) > 3 else []}
                    bundle = train_bundle(train, rec, feature_config={
                                              **config, "training_obs_end": specification["training_label_end"],
                                              "calibration_obs_end": specification["calibration_label_end"],
                                              "test_obs_end": specification["test_label_end"]},
                                          calibration=calibration, top_k=top_k, cv_enabled=False)
                    result["model"] = bundle["name"]
                    model_scores = bundle["model"].predict_proba(model_features(test, bundle))[:, 1]
                    scores = constrain_probabilities(model_scores, reachable)
                    metrics = evaluate_predictions(y, scores, top_k=top_k, user_ids=test["user_id"],
                                                   contact_eligible=reachable)
                    result["fallback_failures"] = bundle.get("fallback_failures", [])
                    result["calibration"] = bundle.get("calibration", {})
                    calibrated = bool(bundle.get("calibration", {}).get("enabled", False))
                result.update(status="ok", reason="", metrics=metrics, calibrated=calibrated,
                              probability_constraint=constraint,
                              score_type="ranking_only" if ranking_only else "probability",
                              group_metrics=_group_evaluations(attrs, groups, y, scores, top_k, ranking_only, reachable))
                id_order = np.argsort(test["user_id"].astype(str).to_numpy(), kind="stable")
                order = id_order[np.argsort(-scores[id_order], kind="stable")]
                rank = np.empty(len(scores), dtype=int)
                rank[order] = np.arange(1, len(scores) + 1)
                selected = set(order[reachable[order]][:top_k])
                for index, uid in enumerate(test["user_id"]):
                    predictions.append({"snapshot_time": test_date.isoformat(), "requested_model": requested,
                                        "model": result["model"], "user_id": str(uid), "churn": int(y[index]),
                                        "risk_score": float(scores[index]),
                                        "model_score": float(model_scores[index]),
                                        "onset_reachable_within_horizon": bool(reachable[index]) if constraint["enabled"] else None,
                                        "churn_probability": None if ranking_only else float(scores[index]),
                                        "score_type": result["score_type"], "rank": int(rank[index]),
                                        "selected_for_contact": index in selected})
            except (ValueError, RuntimeError, ImportError, OSError) as exc:
                result.update(status="failed", reason=str(exc))
            fold["results"].append(result)
        fold["status"] = "ok" if any(r["status"] == "ok" for r in fold["results"]) else "failed"
        folds.append(fold)
    successful = sum(r["status"] == "ok" for fold in folds for r in fold["results"])
    return {"status": "ok" if successful else "no_valid_folds", "definition": config, **provenance,
            "data_start": coverage["start"], "data_end": coverage["end"], "coverage": coverage,
            "top_k": int(top_k), "group_columns": groups,
            "group_selection_scope": "Top K is recomputed within each group; global contact selection is in predictions CSV",
            "properties_mode": "snapshot" if properties is not None and "snapshot_time" in properties else "static",
            "snapshot_manifest": manifest, "folds": folds, "predictions": predictions,
            "notes": ["Only chronological future snapshots estimate generalization; fitted calibration scores are not reported.",
                      "Repeated users across snapshots are allowed; each test snapshot has its own ranking metrics.",
                      "Recency baseline has no probability calibration and does not report Brier/log loss.",
                      "Model comparisons are developmental evidence; confirm the chosen approach on a final untouched future period."]}


def write_backtest_outputs(result, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {key: value for key, value in result.items() if key != "predictions"}
    (output / "backtest_metrics.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    pd.DataFrame(result["predictions"], columns=PREDICTION_COLS).to_csv(output / "backtest_predictions.csv", index=False)
    summary, group_rows, calibration_rows = [], [], []
    for fold in result["folds"]:
        for item in fold["results"]:
            metrics = item.get("metrics") or {}
            top = metrics.get("top_k") or {}
            summary.append({"snapshot_time": fold["test_snapshot_time"],
                            "calibration_snapshot_time": fold["calibration_snapshot_time"],
                            "requested_model": item["requested_model"], "model": item["model"], "status": item["status"],
                            **{key: metrics.get(key) for key in ("users", "positives", "base_rate", "roc_auc", "pr_auc", "brier_score", "log_loss")},
                            "selected": top.get("selected"), "precision_at_k": top.get("precision"),
                            "recall_at_k": top.get("recall"), "lift_at_k": top.get("lift"),
                            "ece": (metrics.get("calibration") or {}).get("ece"),
                            "calibrated": item.get("calibrated", False), "reason": item.get("reason", "")})
            for entry in (metrics.get("calibration") or {}).get("bins", []):
                calibration_rows.append({"snapshot_time": fold["test_snapshot_time"],
                                         "requested_model": item["requested_model"], "model": item["model"], **entry})
            for group in item.get("group_metrics", []):
                group_rows.append((fold["test_snapshot_time"], item["requested_model"], group))
    pd.DataFrame(summary, columns=SUMMARY_COLS).to_csv(output / "backtest_summary.csv", index=False)
    pd.DataFrame(calibration_rows, columns=["snapshot_time", "requested_model", "model", "lower", "upper",
                                          "count", "mean_probability", "observed_rate", "absolute_gap"]) \
        .to_csv(output / "backtest_calibration.csv", index=False)

    def number(value):
        return "—" if value is None else f"{value:.3f}"

    lines = ["# Churn Prediction Rolling Backtest", ""]
    if result.get("definition", {}).get("label_target") == "churn_onset":
        lines += ["Metrics and lists use time-constrained scores: users unreachable within [T,T+H) are set to 0 and excluded from contact."
                  "The per-row model_score keeps the pre-constraint score; rule scores are still not probabilities.", ""]
    if result.get("data_kind") == "simulated":
        lines += ["**Demo/simulated data, workflow validation only; these metrics do not represent real business performance. Data provenance follows the data-kind declaration.**", ""]
    coverage = result.get("coverage")
    if coverage:
        lines += [f"Backtest coverage interval: [{coverage['start']}, {coverage['end']}).", ""]
        if coverage["status"] == "unverified":
            lines += ["**At least one bound was inferred from the first or last observed event. Continuous coverage is unverified; treat these backtest results as exploratory.**", ""]
    lines += [f"Status: {result['status']}; list capacity K={result['top_k']}.",
             "Training labels end no later than the calibration snapshot, and calibration labels end no later than the test snapshot; test labels were not used in training or calibration.", "",
             "## Independent Test Snapshots", "", "| Test date | Requested / actual model | Status | Users | Precision@K | Recall@K | Lift@K | Brier | ECE |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in summary:
        name = row["requested_model"] if row["requested_model"] == row["model"] else f"{row['requested_model']} / {row['model']}"
        lines.append(f"| {row['snapshot_time']} | {name} | {row['status']} | {row['users'] or '—'} | "
                     f"{number(row['precision_at_k'])} | {number(row['recall_at_k'])} | {number(row['lift_at_k'])} | {number(row['brier_score'])} | {number(row['ece'])} |")
    if calibration_rows:
        lines += ["", "## Future Test Probability Bins", "", "List hit rate and probability reliability must be judged separately; the per-bin figures below are point estimates, weigh uncertainty against bin sizes.", "",
                  "| Test date | Model | Probability bin | Users | Mean predicted probability | Observed churn rate |",
                  "|---|---|---|---:|---:|---:|"]
        for row in calibration_rows:
            if row["count"]:
                lines.append(f"| {row['snapshot_time']} | {row['model']} | {row['lower']:.1f}–{row['upper']:.1f} | "
                             f"{row['count']} | {row['mean_probability']:.3f} | {row['observed_rate']:.3f} |")
    if group_rows:
        lines += ["", "## Segment Stability", "", "Each segment's Top K is ranked independently within the segment; see the prediction detail for the actual global list.",
                  "Static user attributes must be time-invariant; time-varying attributes should supply a snapshot_time version.", "",
                  "| Test date | Model | Segment | Users | Precision@K | Lift@K | ROC-AUC |",
                  "|---|---|---|---:|---:|---:|---:|"]
        for date, model, group in group_rows:
            metric, top = group["metrics"], group["metrics"]["top_k"]
            lines.append(f"| {date} | {model} | {group['column']}={group['value']} | {metric['users']} | "
                         f"{number(top['precision'])} | {number(top['lift'])} | {number(metric['roc_auc'])} |")
    lines += ["", "## Time Boundaries and Skip Reasons", ""]
    for entry in result["snapshot_manifest"]:
        if entry["status"] == "skipped":
            lines.append(f"- {entry['snapshot_time']}: {entry['reason']}")
    for fold in result["folds"]:
        lines.append(f"- Test {fold['test_snapshot_time']}: training labels ended by {fold['training_label_end']},"
                     f"calibration snapshot {fold['calibration_snapshot_time']}, calibration labels ended by {fold['calibration_label_end']}.")
        for item in fold["results"]:
            if item["status"] != "ok":
                lines.append(f"  - {item['requested_model']}: {item['status']}, {item.get('reason', '')}")
    lines += ["", "The recency rule is used only for risk ranking; its scores are not treated as probabilities. After model selection, keep one final untouched future-period validation.",
              "This report compares predictive performance; the incremental effect of retention actions requires a separate randomized controlled experiment.", ""]
    (output / "backtest_report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events", required=True)
    ap.add_argument("--project-config", help="confirmed project/export declaration; same semantics as pipeline")
    ap.add_argument("--data-kind", choices=("real", "simulated"), default="unknown")
    ap.add_argument("--snapshot-dates", required=True, help="comma-separated feature cutoff dates T")
    ap.add_argument("--churn-days", type=int, required=True)
    ap.add_argument("--churn-inactivity-days", type=int, required=True)
    ap.add_argument("--prediction-days", type=int, required=True)
    ap.add_argument("--label-target", choices=("window_inactive", "churn_onset"), default="churn_onset")
    ap.add_argument("--cohort", choices=("all", "prevention", "winback"), default="prevention")
    ap.add_argument("--label-criterion", choices=("any", "core", "pay"), default="any")
    ap.add_argument("--core-events")
    ap.add_argument("--session-gap-minutes", type=int, default=30)
    ap.add_argument("--data-start", help="attested inclusive coverage start; defaults to first observed event")
    ap.add_argument("--data-end", help="attested exclusive coverage end; defaults to last observed event")
    ap.add_argument("--top-k", type=int, default=500)
    ap.add_argument("--models", default="recency_rule,logistic_regression,lightgbm")
    ap.add_argument("--user-properties", help="static user_id attributes or user_id,snapshot_time attributes")
    ap.add_argument("--group-columns", default="", help="comma-separated attributes used only for group evaluation")
    ap.add_argument("--output-dir", default="outputs/backtest")
    args = ap.parse_args()
    try:
        events = read_csv(args.events)
        contract = None
        dates = [d.strip() for d in args.snapshot_dates.split(",") if d.strip()]
        if not dates:
            raise ValueError("--snapshot-dates requires at least one cutoff")
        if args.project_config:
            contract, coverage = load_project_config(args.project_config)
            if args.core_events is None:
                args.core_events = ",".join(contract["core_events"])
            # Validate the source once at the coverage end. The schedule below
            # checks each actual snapshot's observation and outcome windows.
            definition = {"churn_days": 0, "label_criterion": args.label_criterion, "core_events": args.core_events}
            source_end = coverage.get("end") if isinstance(coverage, dict) else None
            check = preflight_events(events, definition, source_end or args.data_end or dates[-1],
                                     contract, coverage, args.data_end)
            if coverage is not None and not check["errors"] and args.data_start is not None:
                if pd.Timestamp(args.data_start) != pd.Timestamp(coverage["start"]):
                    check["status"] = "blocked"
                    check["errors"].append("data-start differs from project coverage.start")
            quality = {"status": check["status"], "phases": {"export": check}}
            output = Path(args.output_dir)
            output.mkdir(parents=True, exist_ok=True)
            (output / "data_quality_report.json").write_text(json.dumps(quality, indent=2, ensure_ascii=False))
            if check["errors"]:
                raise ValueError("data preflight blocked: " + "; ".join(check["errors"]))
            if coverage is not None:
                args.data_start = coverage["start"]
                args.data_end = coverage["end"]
        result = run_backtest(
            events, dates,
            args.churn_days, args.churn_inactivity_days, args.prediction_days,
            label_target=args.label_target, cohort=args.cohort, label_criterion=args.label_criterion,
            core_events=args.core_events or "", data_end=args.data_end, top_k=args.top_k,
            models=[m.strip() for m in args.models.split(",") if m.strip()],
            user_properties=read_csv(args.user_properties) if args.user_properties else None,
            group_columns=[c.strip() for c in args.group_columns.split(",") if c.strip()],
            session_gap_minutes=args.session_gap_minutes, data_kind=args.data_kind, data_start=args.data_start,
            project_timezone=contract["timezone"] if contract else None)
        if args.project_config:
            result["definition"]["source_contract"] = contract
            result["data_quality"] = quality
        write_backtest_outputs(result, args.output_dir)
    except (ValueError, TypeError) as exc:
        ap.error(str(exc))
    print(f"backtest status={result['status']}; report: {Path(args.output_dir) / 'backtest_report.md'}")
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
