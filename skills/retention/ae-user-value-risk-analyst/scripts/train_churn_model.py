"""Train a recommended classifier with adaptive CV and failure fallbacks."""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from feature_schema import META_COLS, model_features, read_csv
from onset_constraints import onset_reachability, constrain_probabilities
from evaluation_metrics import evaluate_predictions, select_top_k

FALLBACKS = {
    "lightgbm": ["lightgbm", "xgboost", "random_forest", "logistic_regression"],
    "xgboost": ["xgboost", "random_forest", "logistic_regression"],
    "random_forest": ["random_forest", "logistic_regression"],
    "logistic_regression": ["logistic_regression"],
}


def get_model(name):
    if name == "logistic_regression":
        return Pipeline([("scaler", StandardScaler()),
                         ("clf", LogisticRegression(max_iter=1000, random_state=42))])
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    if name == "lightgbm":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                              random_state=42, n_jobs=-1)
    if name == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=6,
                             random_state=42, n_jobs=-1, eval_metric="aucpr")
    raise ValueError(f"unknown model {name}")


def _labels(frame, name, require_both=False):
    if frame.empty or "churn" not in frame or not frame["churn"].isin([0, 1]).all():
        raise ValueError(f"{name} requires nonempty complete binary churn labels (0 or 1)")
    labels = frame["churn"].astype(int)
    if require_both and labels.nunique() != 2:
        raise ValueError(f"{name} needs both churn classes; adjust snapshot/window or supply more data")
    return labels


def _same_snapshot(left, right, features):
    """Detect reused feature rows, including a copied subset of a snapshot."""
    if left is right:
        return True
    # Changing labels does not turn the same observed feature rows into a
    # holdout. IDs distinguish different users with coincidentally equal data.
    columns = (["user_id"] if "user_id" in left and "user_id" in right else []) + features
    if not set(columns).issubset(left.columns) or not set(columns).issubset(right.columns):
        return False
    first = pd.util.hash_pandas_object(left[columns], index=False).to_numpy()
    second = pd.util.hash_pandas_object(right[columns], index=False).to_numpy()
    return bool(np.isin(first, second).any())


def _calibrator(model, method, n_rows):
    try:
        from sklearn.frozen import FrozenEstimator
    except ImportError:  # sklearn 1.2–1.5 compatibility; no base-model refitting
        return CalibratedClassifierCV(model, method=method, cv="prefit", n_jobs=1)
    # FrozenEstimator.fit is a no-op. All calibration rows must contribute to
    # the one probability mapping; default CV otherwise imposes an unrelated
    # five-fold minimum even though the base model is already frozen.
    indices = np.arange(n_rows)
    return CalibratedClassifierCV(FrozenEstimator(model), method=method,
                                  cv=[(indices, indices)], ensemble=False, n_jobs=1)


def _verified_time_order(config, earlier_end_key, later_end_key):
    """Validate known snapshot times; absent metadata cannot prove independence."""
    horizon = config.get("prediction_days")
    if horizon is None:
        horizon = config.get("churn_inactivity_days")
    if horizon is not None and (isinstance(horizon, (bool, np.bool_))
                                or not isinstance(horizon, (int, np.integer)) or horizon <= 0):
        raise ValueError("prediction_days must be positive in snapshot time metadata")
    dates = {}
    for key in (earlier_end_key, later_end_key):
        if config.get(key) is None:
            continue
        try:
            dates[key] = pd.Timestamp(config[key])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{key} must be a valid snapshot timestamp") from exc
        if pd.isna(dates[key]):
            raise ValueError(f"{key} must be a valid snapshot timestamp")
    if horizon is None or len(dates) != 2:
        return False
    earlier_end = dates[earlier_end_key]
    later_start = dates[later_end_key] - pd.Timedelta(days=int(horizon))
    try:
        overlaps = later_start < earlier_end
    except TypeError as exc:
        raise ValueError("snapshot timestamps must use compatible timezones") from exc
    if overlaps:
        raise ValueError(f"{later_end_key} label window overlaps {earlier_end_key}; snapshots must be temporally separated")
    return True


def train_bundle(df, rec, evaluation=None, feature_config=None, calibration=None,
                 calibration_method="sigmoid", top_k=500, cv_enabled=True):
    if df.empty:
        raise ValueError("no users in the training observation window")
    features = [c for c in df.columns if c not in
                ("user_id", "churn", *META_COLS)]
    bundle = {"features": features, "feature_config": feature_config or {},
              "categorical_features": [], "category_levels": {}, "metrics": {},
              "calibration": {"enabled": False, "method": None, "rows": 0,
                              "class_counts": {}, "warnings": []}}
    select_top_k([0.5], top_k)  # validate the capacity even without evaluation
    for frame in (df, calibration, evaluation):
        if frame is not None:
            onset_reachability(frame, bundle["feature_config"])
    if evaluation is not None:
        _labels(evaluation, "future evaluation")
        train_test_separated = _verified_time_order(bundle["feature_config"], "training_obs_end", "test_obs_end")
        if df is evaluation or (not train_test_separated and _same_snapshot(df, evaluation, features)):
            raise ValueError("future evaluation must use a separate snapshot from training")
    if calibration is not None:
        calibration_y = _labels(calibration, "calibration", require_both=True)
        if calibration_method not in ("sigmoid", "isotonic"):
            raise ValueError("calibration_method must be sigmoid or isotonic")
        train_cal_separated = _verified_time_order(bundle["feature_config"], "training_obs_end", "calibration_obs_end")
        if df is calibration or (not train_cal_separated and _same_snapshot(df, calibration, features)):
            raise ValueError("calibration must use a separate snapshot from training")
        if evaluation is not None:
            cal_test_separated = _verified_time_order(bundle["feature_config"], "calibration_obs_end", "test_obs_end")
            if evaluation is calibration or (not cal_test_separated and _same_snapshot(evaluation, calibration, features)):
                raise ValueError("calibration must use a separate snapshot from future evaluation")
    requested = rec["model"]
    if requested == "heuristic":
        if calibration is not None:
            raise ValueError("probability calibration requires a trained classifier, not a heuristic")
        return {**bundle, "model": None, "name": "heuristic"}
    y = _labels(df, "training", require_both=True)
    if requested not in FALLBACKS:
        raise ValueError(f"unknown model {requested}")
    folds = min(5, int(y.value_counts().min()))
    failures = []
    for name in FALLBACKS[requested]:
        cat_cols = rec.get("categorical_features", []) if name == "lightgbm" else []
        levels = {c: sorted(df[c].fillna(0).unique().tolist()) for c in cat_cols}
        candidate = {**bundle, "name": name, "categorical_features": cat_cols,
                     "category_levels": levels}
        X = model_features(df, candidate)
        try:
            model = get_model(name)
            cv_metrics = {"folds": folds if cv_enabled and folds >= 2 else 0,
                          "scope": "uncalibrated_training_cv"}
            if not cv_enabled:
                cv_metrics["reason"] = "disabled; use temporally separated evaluation"
            elif folds >= 2:
                cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
                scores = cross_validate(model, X, y, cv=cv,
                                        scoring={"roc_auc": "roc_auc", "pr_auc": "average_precision"},
                                        n_jobs=1, error_score="raise")
                for metric in ("roc_auc", "pr_auc"):
                    values = scores[f"test_{metric}"]
                    cv_metrics[f"{metric}_mean"] = float(np.mean(values))
                    cv_metrics[f"{metric}_std"] = float(np.std(values))
            else:
                cv_metrics["reason"] = "minority class has only one user; CV is unavailable"
                print(f"WARNING: {cv_metrics['reason']}")
            model.fit(X, y)
        except Exception as exc:
            failures.append({"model": name, "error": str(exc)})
            print(f"WARNING: {name} failed: {exc}; trying next fallback")
            continue
        candidate.update(model=model, requested_model=requested, fallback_failures=failures,
                         metrics={"cv": cv_metrics})
        if calibration is not None:
            calibrator = _calibrator(model, calibration_method, len(calibration))
            calibrator.fit(model_features(calibration, candidate), calibration_y)
            warnings = []
            if calibration_method == "isotonic" and len(calibration) < 1000:
                warnings.append("isotonic calibration may overfit with fewer than 1000 calibration rows")
            if calibration_y.value_counts().min() < 5:
                warnings.append("one calibration class has fewer than 5 users; assess reliability on a future snapshot")
            candidate.update(model=calibrator, explanation_model=model,
                             calibration={"enabled": True, "method": calibration_method,
                                          "rows": int(len(calibration)), "source": "independent_holdout",
                                          "class_counts": {str(k): int(v) for k, v in calibration_y.value_counts().items()},
                                          "warnings": warnings})
        if evaluation is not None:
            X_eval = model_features(evaluation, candidate)
            model_prob = candidate["model"].predict_proba(X_eval)[:, 1]
            reachable, constraint = onset_reachability(evaluation, candidate["feature_config"])
            prob = constrain_probabilities(model_prob, reachable)
            actual = evaluation["churn"].astype(int)
            user_ids = evaluation["user_id"] if "user_id" in evaluation else None
            candidate["metrics"]["future_holdout"] = evaluate_predictions(actual, prob, top_k,
                                                                           user_ids=user_ids,
                                                                           contact_eligible=reachable)
            if constraint["enabled"]:
                candidate["metrics"]["future_holdout"]["probability_constraint"] = constraint
            if calibration is not None:
                raw_prob = model.predict_proba(X_eval)[:, 1]
                candidate["metrics"]["future_holdout_raw"] = evaluate_predictions(actual, raw_prob, top_k,
                                                                                   user_ids=user_ids)
                candidate["metrics"]["future_holdout_calibrated"] = evaluate_predictions(
                    actual, model_prob, top_k, user_ids=user_ids)
            temporal_verified = train_test_separated and (
                calibration is None or (train_cal_separated and cal_test_separated))
            for key in ("future_holdout", "future_holdout_raw", "future_holdout_calibrated"):
                if key in candidate["metrics"]:
                    candidate["metrics"][key].update(
                        temporal_verified=temporal_verified,
                        evaluation_scope="future_holdout" if temporal_verified else "holdout_time_unverified")
        return candidate
    raise RuntimeError(f"all model candidates failed: {failures}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="user_features.csv")
    ap.add_argument("--rec", default="model_recommendation.json")
    ap.add_argument("--output", default="churn_model.pkl")
    ap.add_argument("--feature-config", help="JSON feature/window definition to persist with the model")
    ap.add_argument("--evaluation-features", help="labeled features from a later, separate snapshot")
    ap.add_argument("--calibration-features", help="labeled independent calibration snapshot, before future evaluation")
    ap.add_argument("--calibration-method", choices=("sigmoid", "isotonic"), default="sigmoid")
    ap.add_argument("--top-k", type=int, default=500, help="operational capacity used in held-out ranking metrics")
    ap.add_argument("--metrics-output", default="model_metrics.json")
    ap.add_argument("--skip-report", action="store_true", help="save metrics without the report or calibration curve")
    args = ap.parse_args()
    with open(args.rec) as f:
        rec = json.load(f)
    config = {}
    if args.feature_config:
        with open(args.feature_config) as f:
            config = json.load(f)
    evaluation = read_csv(args.evaluation_features) if args.evaluation_features else None
    calibration = read_csv(args.calibration_features) if args.calibration_features else None
    bundle = train_bundle(read_csv(args.input), rec, evaluation, config, calibration=calibration,
                          calibration_method=args.calibration_method, top_k=args.top_k)
    joblib.dump(bundle, args.output)
    with open(args.metrics_output, "w") as f:
        json.dump(bundle["metrics"], f, indent=2, allow_nan=False)
    if not args.skip_report:
        from model_evaluation_report import write_evaluation_report
        write_evaluation_report(bundle["metrics"], Path(args.metrics_output).parent, bundle["calibration"],
                                data_kind=config.get("evaluation_data_kind", config.get("training_data_kind")))
    print(f"model={bundle['name']} metrics={json.dumps(bundle['metrics'])}")


if __name__ == "__main__":
    main()
