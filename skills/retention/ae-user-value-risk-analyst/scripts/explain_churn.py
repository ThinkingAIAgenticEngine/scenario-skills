"""
SHAP-based churn driver explanation, global and per-segment.

Outputs:
- shap_local.csv       : global mean(|SHAP value|) per feature, sorted desc
- shap_by_segment.csv  : mean(|SHAP value|) per feature x persona_tag (only for
                          segments with enough sampled rows to be meaningful);
                          wide format, one column per persona_tag
- shap_global.png      : SHAP summary plot (best-effort; skipped if matplotlib/shap unavailable)

Usage:
    python explain_churn.py --input user_features.csv --model churn_model.pkl \
        --segments high_risk_segments.csv --out-csv shap_local.csv \
        --out-segment-csv shap_by_segment.csv --out-png shap_global.png
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from feature_schema import model_features, read_csv

MIN_SEGMENT_ROWS = 5  # below this, a per-segment mean(|SHAP|) is too noisy to report


def fallback_importance(model, X):
    if hasattr(model, "feature_importances_"):
        return pd.Series(model.feature_importances_, index=X.columns), "tree_importance"
    if isinstance(model, Pipeline):
        clf = model.named_steps.get("clf", model.steps[-1][1])
        if hasattr(clf, "coef_"):
            transformed = model[:-1].transform(X)
            values = np.abs((transformed - transformed.mean(axis=0)) * clf.coef_[0]).mean(axis=0)
            return pd.Series(values, index=X.columns), "linear_contribution"
    return pd.Series(dtype=float), "unavailable"


def _make_explainer(model, X, shap):
    """Pick a working SHAP explainer for whatever estimator is in the bundle.

    `model` can be a bare tree/linear estimator, or a Pipeline (e.g.
    logistic_regression is StandardScaler + LogisticRegression). Passing a
    Pipeline straight into TreeExplainer/LinearExplainer/KernelExplainer
    fails for different reasons each time (unsupported type, unknown model,
    or a shap-internal AttributeError when it tries to monkeypatch
    Pipeline.predict_proba). Dispatch explicitly instead of relying on a
    blind try/except chain that silently falls through to a crash.

    Returns (explainer, X_for_explainer, positive_class_only: bool).
    """
    # Tree ensembles: xgboost/lightgbm/random_forest are used bare (not wrapped
    # in a Pipeline) in train_churn_model.py's get_model().
    if hasattr(model, "feature_importances_"):
        return shap.TreeExplainer(model), X, False

    # logistic_regression is Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression())]).
    if isinstance(model, Pipeline):
        clf = model.named_steps.get("clf", model.steps[-1][1])
        scaler = model.named_steps.get("scaler")
        Xs = scaler.transform(X) if scaler is not None else X.to_numpy()
        Xs = pd.DataFrame(Xs, columns=X.columns, index=X.index)
        return shap.LinearExplainer(clf, Xs), Xs, False

    # Fallback for anything else: KernelExplainer needs a plain function (not
    # a bound Pipeline.predict_proba method — shap tries to set an attribute
    # on the bound method's __self__, which raises on Pipeline) and a capped
    # background + foreground sample since it's O(n_background * n_explain).
    background = X.sample(min(100, len(X)), random_state=42)
    foreground = X.sample(min(200, len(X)), random_state=42) if len(X) > 200 else X
    predict_positive = lambda data: model.predict_proba(data)[:, 1]
    return shap.KernelExplainer(predict_positive, background), foreground, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="user_features.csv")
    ap.add_argument("--model", default="churn_model.pkl")
    ap.add_argument("--segments", default="high_risk_segments.csv")
    ap.add_argument("--out-csv", default="shap_local.csv")
    ap.add_argument("--out-segment-csv", default="shap_by_segment.csv")
    ap.add_argument("--out-png", default="shap_global.png")
    args = ap.parse_args()
    explanation_scope = "scoring_model"

    # Never let an old run's plot or persona attribution leak into a new report.
    for path in (args.out_csv, args.out_segment_csv, args.out_png, args.out_csv + ".meta.json"):
        Path(path).unlink(missing_ok=True)
    pd.DataFrame(columns=["feature", "importance"]).to_csv(args.out_csv, index=False)
    pd.DataFrame(columns=["feature", "global"]).to_csv(args.out_segment_csv, index=False)

    def metadata(method, reason=""):
        Path(args.out_csv + ".meta.json").write_text(
            json.dumps({"method": method, "reason": reason, "explained_model": explanation_scope,
                        "before_onset_constraint": bundle.get("feature_config", {}).get("label_target") == "churn_onset",
                        "interpretation": "Model feature associations before any onset constraint; not an additive decomposition of final constrained probabilities. Structurally unreachable zeros are explained by the target rule."},
                       ensure_ascii=False), encoding="utf-8")

    df = read_csv(args.input)
    bundle = joblib.load(args.model)
    name = bundle["name"]
    if df.empty:
        metadata("unavailable", "No explainable users.")
        return

    if name == "heuristic":
        from predict_churn_risk import HEURISTIC_WEIGHTS
        pd.Series({k: abs(v) for k, v in HEURISTIC_WEIGHTS.items()}).sort_values(ascending=False) \
            .to_csv(args.out_csv, index_label="feature", header=["importance"])
        metadata("heuristic_weights")
        return

    X = model_features(df, bundle)
    feats = list(X.columns)
    model = bundle.get("explanation_model", bundle["model"])
    if bundle.get("calibration", {}).get("enabled"):
        explanation_scope = "base_model_before_calibration"

    try:
        import shap
        explainer, X_explain, is_kernel = _make_explainer(model, X, shap)
        sv = explainer.shap_values(X_explain)
    except Exception as exc:
        imp, method = fallback_importance(model, X)
        imp.sort_values(ascending=False).to_csv(args.out_csv, index_label="feature", header=["importance"])
        metadata(method, str(exc))
        print(f"WARNING: SHAP unavailable ({exc}); explanation method={method}")
        return
    if isinstance(sv, list):
        # some explainer/version combos still return a per-class list
        sv = sv[1] if len(sv) > 1 else sv[0]
    sv = np.asarray(sv)
    if sv.ndim == 3:
        # (n_samples, n_features, n_classes) -> take the positive class
        sv = sv[:, :, 1] if sv.shape[2] > 1 else sv[:, :, 0]

    mean_abs = np.abs(sv).mean(axis=0)
    imp = pd.Series(mean_abs, index=feats).sort_values(ascending=False)
    imp.to_csv(args.out_csv, index_label="feature", header=["importance"])
    metadata("shap")

    # ---- Per-segment breakdown ----
    # X_explain's rows are a subset/reorder of df's rows but keep df's original
    # index (fillna/sample don't touch the index), so we can map SHAP rows back
    # to user_id -> persona_tag via that index rather than assuming row order.
    try:
        seg = read_csv(args.segments)
        if "user_id" in df.columns and "persona_tag" in seg.columns and not seg.empty:
            uid_by_row = df.loc[X_explain.index, "user_id"]
            persona_by_uid = seg.set_index("user_id")["persona_tag"]
            persona_by_row = uid_by_row.map(persona_by_uid)  # NaN for rows not in any high-risk segment

            sv_df = pd.DataFrame(np.abs(sv), columns=feats, index=X_explain.index)
            sv_df["persona_tag"] = persona_by_row.values
            counts = sv_df["persona_tag"].value_counts()
            keep_tags = counts[counts >= MIN_SEGMENT_ROWS].index
            if len(keep_tags):
                seg_imp = sv_df[sv_df["persona_tag"].isin(keep_tags)] \
                    .groupby("persona_tag")[feats].mean().T
                seg_imp["global"] = imp
                seg_imp = seg_imp.sort_values("global", ascending=False)
                seg_imp.to_csv(args.out_segment_csv)
                print(f"wrote {args.out_segment_csv} (segments: {list(keep_tags)}; "
                      f"skipped for <{MIN_SEGMENT_ROWS}-row segments: "
                      f"{list(counts[counts < MIN_SEGMENT_ROWS].index)})")
            else:
                print(f"no persona had >= {MIN_SEGMENT_ROWS} sampled rows in the SHAP "
                      f"explanation set; skipping per-segment breakdown")
        else:
            print("no user_id/persona_tag overlap available; skipping per-segment breakdown")
    except FileNotFoundError:
        print(f"{args.segments} not found; skipping per-segment breakdown")

    try:
        import matplotlib
        matplotlib.use("Agg")
        shap.summary_plot(sv, X_explain, show=False)
        import matplotlib.pyplot as plt
        plt.savefig(args.out_png, bbox_inches="tight")
        plt.close()
        print(f"wrote {args.out_png}")
    except Exception as e:
        print(f"plot skipped: {e}")

    print("top drivers:")
    print(imp.head(20))


if __name__ == "__main__":
    main()
