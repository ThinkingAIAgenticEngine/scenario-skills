"""
Score every user and assign a risk tier (High / Medium / Low).

For the heuristic model, churn probability is a normalized weighted RFM-decline
score. Trained model output is retained as model_probability; onset's exact
timestamp bound is applied before final probability, tiers and contact selection.

Usage:
    python predict_churn_risk.py --input user_features.csv --model churn_model.pkl \
        --output churn_prediction_result.csv --high 0.6 --medium 0.3
"""
import argparse
import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from feature_schema import model_features, read_csv
from data_provenance import resolve_data_kind
from onset_constraints import onset_reachability, constrain_probabilities

from feature_schema import (DAYS_SINCE_LAST_EVENT, TREND_7D_EVENTS, ACTIVE_DAYS_TOTAL,
                             TOTAL_EVENTS, MONETARY_TOTAL, check_coverage)

# Column names must match churn_feature_engineering.py's output exactly (see
# feature_schema.py). A mismatch here silently degrades the heuristic to
# whichever columns happen to match, which previously made it collapse to
# days_since_last_event alone.
HEURISTIC_WEIGHTS = {
    DAYS_SINCE_LAST_EVENT: 0.35,
    TREND_7D_EVENTS: -0.20,        # negative slope -> more risk
    ACTIVE_DAYS_TOTAL: -0.15,
    TOTAL_EVENTS: -0.15,
    MONETARY_TOTAL: -0.15,
}


def _finite_metric(value):
    """Keep persisted diagnostics JSON-safe without inventing missing values."""
    if value is None or isinstance(value, (bool, np.bool_)):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def probability_validation(bundle):
    """Describe saved paired holdout results; never choose a scoring model here.

    Brier/log-loss remain defined on a single-class holdout. Such a comparison
    is explicitly marked, and does not establish discrimination of both classes.
    Missing or nonfinite metrics stay unavailable rather than becoming zeros.
    """
    metrics = bundle.get("metrics", {})
    enabled = bundle.get("calibration", {}).get("enabled", False) is True
    raw = metrics.get("future_holdout_raw")
    calibrated = metrics.get("future_holdout_calibrated")
    if enabled and calibrated is None:
        calibrated = metrics.get("future_holdout")
    if not enabled and raw is None:
        raw = metrics.get("future_holdout")
    raw = raw if isinstance(raw, dict) else {}
    calibrated = calibrated if isinstance(calibrated, dict) else {}
    sections = [section for section in (raw, calibrated) if section]
    scopes = [section.get("evaluation_scope") for section in sections]
    verification = [section.get("temporal_verified") for section in sections]
    common_scope = scopes[0] if scopes and all(scope == scopes[0] for scope in scopes) else None
    temporal_verified = (True if verification and all(value is True for value in verification)
                         else False if any(value is False for value in verification) else None)
    observed = calibrated or raw
    users = _finite_metric(observed.get("users"))
    positives = _finite_metric(observed.get("positives"))
    valid_counts = (users is not None and positives is not None and users > 0
                    and users.is_integer() and positives.is_integer() and 0 <= positives <= users)
    result = {"status": "untested", "reason": "no_paired_holdout",
              "evaluation_scope": common_scope, "temporal_verified": temporal_verified,
              "raw_evaluation_scope": raw.get("evaluation_scope"),
              "calibrated_evaluation_scope": calibrated.get("evaluation_scope"),
              "users": int(users) if valid_counts else None,
              "positives": int(positives) if valid_counts else None,
              "single_class": positives in (0, users) if valid_counts else None,
              "raw": {}, "calibrated": {}, "metric_deltas": {},
              "compared_metrics": [], "unavailable_metrics": []}
    for name in ("brier_score", "log_loss", "ece"):
        def value(section):
            source = section.get("calibration", {}) if name == "ece" else section
            return _finite_metric(source.get(name)) if isinstance(source, dict) else None
        before, after = value(raw), value(calibrated)
        delta = _finite_metric(after - before) if before is not None and after is not None else None
        result["raw"][name], result["calibrated"][name] = before, after
        result["metric_deltas"][name] = delta
        result["compared_metrics" if delta is not None else "unavailable_metrics"].append(name)
    if not enabled:
        result["reason"] = "calibration_not_fitted"
        return result
    if not raw or not calibrated:
        return result
    for name in ("users", "positives"):
        before, after = _finite_metric(raw.get(name)), _finite_metric(calibrated.get(name))
        if before is not None and after is not None and before != after:
            result["reason"] = "holdout_counts_mismatch"
            return result
    if raw.get("evaluation_scope") and calibrated.get("evaluation_scope") and common_scope is None:
        result["reason"] = "holdout_scope_mismatch"
        return result
    if not result["compared_metrics"]:
        result["reason"] = "no_comparable_probability_metrics"
        return result
    directions = []
    for name in result["compared_metrics"]:
        before, after = result["raw"][name], result["calibrated"][name]
        directions.append(0 if math.isclose(before, after, rel_tol=1e-9, abs_tol=1e-12)
                          else -1 if after < before else 1)
    improved, worsened = -1 in directions, 1 in directions
    result["status"] = ("mixed" if improved and worsened else "improved" if improved
                        else "worsened" if worsened else "unchanged")
    result["reason"] = "paired_holdout_point_estimates"
    return result


def heuristic_score(df: pd.DataFrame, reference: pd.DataFrame = None) -> np.ndarray:
    if df.empty:
        return np.array([], dtype=float)
    reference = df if reference is None else reference
    if reference.empty:
        raise ValueError("nonempty heuristic scores require a nonempty feature reference")
    cols = check_coverage(HEURISTIC_WEIGHTS, df.columns, context="predict_churn_risk.heuristic_score")
    sub = model_features(df, {"features": cols}).astype(float)
    reference_sub = model_features(reference, {"features": cols}).astype(float)

    def raw_score(frame):
        score = np.zeros(len(frame))
        for c in cols:
            lo, hi = reference_sub[c].min(), reference_sub[c].max()
            norm = (frame[c].to_numpy() - lo) / (hi - lo) if hi > lo else np.zeros(len(frame))
            weight = HEURISTIC_WEIGHTS[c]
            score += abs(weight) * (norm if weight > 0 else 1.0 - norm)
        return score

    reference_scores = raw_score(reference_sub)
    low, high = reference_scores.min(), reference_scores.max()
    return np.clip((raw_score(sub) - low) / (high - low + 1e-9), 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="user_features.csv")
    ap.add_argument("--reference-features", help="full same-snapshot feature reference for heuristic normalization before audience filtering")
    ap.add_argument("--model", default="churn_model.pkl")
    ap.add_argument("--output", default="churn_prediction_result.csv")
    ap.add_argument("--high", type=float, default=0.6)
    ap.add_argument("--medium", type=float, default=0.3)
    ap.add_argument("--top-k", type=int, help="select at most K candidates by risk, independent of tier")
    ap.add_argument("--min-contact-score", type=float, default=0.0)
    ap.add_argument("--candidates-output", default="contact_candidates.csv")
    ap.add_argument("--metadata-output", help="JSON score meaning and selection policy")
    ap.add_argument("--snapshot-time", help="exclusive feature cutoff T for this scoring run")
    ap.add_argument("--data-kind", choices=("real", "simulated"), help="propagate explicit data provenance")
    args = ap.parse_args()
    if not 0 <= args.medium < args.high <= 1:
        ap.error("thresholds must satisfy 0 <= --medium < --high <= 1")
    if args.top_k is not None and args.top_k <= 0:
        ap.error("--top-k must be positive")
    if not 0 <= args.min_contact_score <= 1:
        ap.error("--min-contact-score must be in [0,1]")

    df = read_csv(args.input)
    provenance = resolve_data_kind(args.data_kind, frames=[("features", df)])
    if "user_id" not in df or df["user_id"].isna().any() or df["user_id"].duplicated().any():
        raise ValueError("prediction needs one non-null row per user_id")
    bundle = joblib.load(args.model)
    name = bundle["name"]
    definition = bundle.get("feature_config", {})
    calibration = bundle.get("calibration", {"enabled": False})
    score_provenance = {
        "scoring_data_kind": provenance["data_kind"],
        "model_training_data_kind": resolve_data_kind(definition.get("training_data_kind"))["data_kind"],
    }
    if calibration.get("enabled"):
        score_provenance["model_calibration_data_kind"] = resolve_data_kind(
            definition.get("calibration_data_kind"))["data_kind"]

    if df.empty:
        prob = np.array([], dtype=float)
    elif name == "heuristic" or bundle.get("model") is None:
        reference = read_csv(args.reference_features) if args.reference_features else df
        if ("user_id" not in reference or reference.user_id.isna().any() or
                reference.user_id.duplicated().any() or not df.user_id.isin(reference.user_id).all()):
            raise ValueError("heuristic reference must contain unique non-null IDs covering every scored user")
        prob = heuristic_score(df, reference=reference)
    else:
        X = model_features(df, bundle)
        prob = bundle["model"].predict_proba(X)[:, 1]

    model_prob = np.asarray(prob).copy()
    reachable, constraint = onset_reachability(df, definition, args.snapshot_time)
    prob = constrain_probabilities(model_prob, reachable)
    out = pd.DataFrame({"user_id": df["user_id"] if "user_id" in df.columns else range(len(df))})
    out["model_probability"] = model_prob
    out["churn_probability"] = prob
    if constraint["enabled"]:
        out["onset_reachable_within_horizon"] = reachable
        out["probability_constraint"] = np.where(reachable, "none", "onset_unreachable")
    if provenance["data_kind"] != "unknown" or "data_kind" in df:
        out["data_kind"] = provenance["data_kind"]
    for field, kind in score_provenance.items():
        out[field] = kind
    out["risk_level"] = pd.cut(prob, bins=[-0.01, args.medium, args.high, 1.01],
                               labels=["Low", "Medium", "High"], right=False)
    out.loc[~reachable, "risk_level"] = "Low"
    if not np.isfinite(prob).all() or ((prob < 0) | (prob > 1)).any():
        raise ValueError("model returned nonfinite scores or values outside [0,1]")
    selection = {"mode": "risk_tier", "high": args.high, "medium": args.medium}
    if args.top_k is not None:
        from evaluation_metrics import select_top_k
        # Stable IDs make tied-score selection reproducible across input order.
        id_order = np.argsort(out["user_id"].astype(str).to_numpy(), kind="stable")
        order = id_order[select_top_k(prob[id_order], max(1, len(out)))] if len(out) else np.array([], dtype=int)
        ranks = np.empty(len(out), dtype=int)
        ranks[order] = np.arange(1, len(out) + 1)
        eligible = order[(prob[order] >= args.min_contact_score) & reachable[order]]
        chosen = eligible[:args.top_k]
        out["risk_rank"] = ranks
        out["selected_for_contact"] = False
        out.loc[chosen, "selected_for_contact"] = True
        out.iloc[chosen].to_csv(args.candidates_output, index=False)
        selection = {"mode": "top_k", "requested": args.top_k, "selected": len(chosen),
                     "minimum_score": args.min_contact_score,
                     "cutoff_score": float(prob[chosen[-1]]) if len(chosen) else None,
                     "tie_breaker": "user_id ascending", "candidate_file": str(args.candidates_output)}
    out.to_csv(args.output, index=False)
    if args.metadata_output:
        validation = probability_validation(bundle)
        metadata = {"users": len(out), "model": name, "snapshot_time": args.snapshot_time,
                    **provenance, **score_provenance,
                    "definition": definition,
                    "probability_constraint": constraint,
                    "score_columns": {"model_probability": "model output before target constraint (after calibration if fitted)",
                                      "churn_probability": "final probability after target constraint"},
                    "calibration": calibration, "selection": selection,
                    "probability_validation": validation,
                    "probability_note": "calibration fitted; saved paired holdout status=" + validation["status"]
                    if calibration.get("enabled") else "uncalibrated risk score"}
        Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(out["risk_level"].value_counts())
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
