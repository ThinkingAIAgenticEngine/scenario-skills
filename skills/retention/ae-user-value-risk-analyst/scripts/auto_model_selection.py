"""
Inspect the feature dataset and pick the best prediction model.
Writes model_recommendation.json.

Selection rules (see SKILL.md for the full table):
- no churn label                      -> heuristic RFM-decline score
- n < 1000 OR n_features > n/30       -> logistic_regression (overfit/low-data guard)
- lightgbm available                   -> lightgbm (default tabular churn winner)
- lightgbm missing                     -> xgboost -> random_forest -> logistic_regression fallback chain

Usage:
    python auto_model_selection.py --input user_features.csv --output model_recommendation.json
"""
import argparse
import importlib
import json

import pandas as pd
from feature_schema import META_COLS, read_csv


def has_lib(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception as exc:
        print(f"optional model library {name} unavailable: {exc}")
        return False


def recommend(df: pd.DataFrame, model_type: str = "auto") -> dict:
    n = len(df)
    has_label = "churn" in df.columns
    drop = [c for c in ("user_id", "churn", *META_COLS) if c in df.columns]
    feat_df = df.drop(columns=drop)
    n_features = feat_df.shape[1]
    # "Categorical-like" here means low-cardinality columns (ordinal-encoded
    # fields like lifecycle_stage/pay_tier, or genuine object/string columns)
    # rather than select_dtypes(object), which is always empty since feature
    # engineering emits purely numeric columns — that made this check a
    # permanent no-op before.
    CAT_CARDINALITY_MAX = 10
    cat_cols = [c for c in feat_df.columns
                if pd.api.types.is_string_dtype(feat_df[c].dtype) or
                feat_df[c].dtype == object or feat_df[c].nunique(dropna=True) <= CAT_CARDINALITY_MAX]
    n_cat = len(cat_cols)

    if not has_label:
        return {"model": "heuristic", "reason": "no churn label; use RFM-decline heuristic score"}

    if model_type != "auto":
        if model_type not in ("logistic_regression", "lightgbm", "xgboost", "random_forest"):
            raise ValueError(f"unknown model type: {model_type}")
        return {"model": model_type, "reason": "explicit model choice; compare forward backtest performance",
                "categorical_features": cat_cols if model_type == "lightgbm" and n_cat > 3 else []}

    # overfit / low-sample guard
    if n < 1000 or n_features > max(10, n / 30):
        return {"model": "logistic_regression",
                "reason": f"n={n}, n_features={n_features}; interpretable baseline, overfit guard"}

    if has_lib("lightgbm"):
        if n_cat > 3:
            return {"model": "lightgbm",
                    "reason": f"n={n}, n_features={n_features}, n_cat={n_cat}; lightgbm handles categoricals natively",
                    "categorical_features": cat_cols}
        return {"model": "lightgbm",
                "reason": f"n={n}, n_features={n_features}; lightgbm is the strong default for tabular churn",
                "categorical_features": []}

    if has_lib("xgboost"):
        return {"model": "xgboost", "reason": "lightgbm unavailable; xgboost fallback"}

    return {"model": "random_forest", "reason": "no boosting libs available; sklearn RandomForest fallback"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="user_features.csv")
    ap.add_argument("--output", default="model_recommendation.json")
    ap.add_argument("--model-type", default="auto", choices=("auto", "logistic_regression", "lightgbm", "xgboost", "random_forest"))
    args = ap.parse_args()

    df = read_csv(args.input)
    rec = recommend(df, args.model_type)
    rec["n_rows"] = int(len(df))
    drop = [c for c in ("user_id", "churn", *META_COLS) if c in df.columns]
    rec["n_features"] = int(df.drop(columns=drop).shape[1])
    with open(args.output, "w") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    print(json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()
