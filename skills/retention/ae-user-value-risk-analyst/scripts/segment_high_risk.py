"""
Cluster high-risk users on behavioral features and assign persona tags.

Pipeline:
1. Filter users with risk_level == High.
2. Standardize behavioral features.
3. Auto-pick k via silhouette over k=2..6.
4. K-Means cluster.
5. Label each cluster with a persona tag based on its profile.

Output: high_risk_segments.csv
    user_id, churn_probability, risk_level, segment, persona_tag

Usage:
    python segment_high_risk.py --pred churn_prediction_result.csv \
        --features user_features.csv --output high_risk_segments.csv
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from feature_schema import read_csv

OUTPUT_COLS = ["user_id", "churn_probability", "risk_level", "segment", "persona_tag"]

from feature_schema import (DAYS_SINCE_LAST_EVENT, TOTAL_EVENTS, ACTIVE_DAYS_TOTAL,
                             MONETARY_TOTAL, TREND_7D_EVENTS, TENURE_DAYS, SESSION_COUNT,
                             EVENT_TYPES, AVG_EVENTS_PER_DAY, PAY_COUNT, check_coverage)

# Column names must match churn_feature_engineering.py's output exactly (see
# feature_schema.py). A mismatch here silently drops columns from clustering
# and starves the persona rules below (they previously never saw monetary or
# trend_7d at all).
CLUSTER_COLS = [
    DAYS_SINCE_LAST_EVENT, TOTAL_EVENTS, ACTIVE_DAYS_TOTAL, MONETARY_TOTAL,
    TREND_7D_EVENTS, TENURE_DAYS, SESSION_COUNT, EVENT_TYPES,
    AVG_EVENTS_PER_DAY, PAY_COUNT,
]


# Each rule's predicate is a gate — "is this cluster's profile plausibly this
# persona at all". Each rule's score measures how strongly the profile fits,
# so that when a cluster satisfies multiple personas (e.g. a whale that is
# also generically declining) the more specific/extreme match wins instead of
# whichever rule happened to be listed first.
PERSONA_RULES = [
    ("at-risk-whale",
     lambda p: p.get(MONETARY_TOTAL, 0) > 0.6 and p.get(TREND_7D_EVENTS, 1) < 0.3,
     lambda p: p.get(MONETARY_TOTAL, 0) - p.get(TREND_7D_EVENTS, 0)),
    ("silent-quitter",
     lambda p: p.get(DAYS_SINCE_LAST_EVENT, 0) > 0.6 and p.get(TOTAL_EVENTS, 1) < 0.4,
     lambda p: p.get(DAYS_SINCE_LAST_EVENT, 0) - p.get(TOTAL_EVENTS, 0)),
    ("price-sensitive",
     lambda p: 0.2 < p.get(MONETARY_TOTAL, 0) <= 0.6 and p.get(PAY_COUNT, 0) > 0.2 and p.get(TREND_7D_EVENTS, 1) < 0.5,
     lambda p: p.get(MONETARY_TOTAL, 0) + p.get(PAY_COUNT, 0) - p.get(TREND_7D_EVENTS, 0)),
    ("new-and-unstable",
     lambda p: p.get(TENURE_DAYS, 1) < 0.3 and p.get(TOTAL_EVENTS, 0) > 0.4,
     lambda p: p.get(TOTAL_EVENTS, 0) - p.get(TENURE_DAYS, 0)),
    ("declining-engagement",
     lambda p: p.get(TREND_7D_EVENTS, 1) < 0.3,
     lambda p: -p.get(TREND_7D_EVENTS, 0)),
]


def pick_k(X, k_min=2, k_max=6):
    # Silhouette is only defined for 2 <= n_labels <= n_samples-1.
    upper = min(k_max, len(X) - 1, len(np.unique(X, axis=0)))
    best_k, best_s = 1, -1.0
    for k in range(k_min, upper + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
        n_labels = len(set(labels))
        try:
            s = silhouette_score(X, labels, sample_size=min(5000, len(X)), random_state=42) \
                if 1 < n_labels < len(X) else -1.0
        except ValueError:  # a capped sample may miss a very small cluster
            continue
        if s > best_s:
            best_k, best_s = k, s
    return best_k, best_s


def label_persona(profile: dict) -> str:
    """Among personas whose gate predicate matches, return the one with the
    highest fit score (see PERSONA_RULES docstring above) rather than the
    first match in list order.
    """
    candidates = []
    for tag, gate, score_fn in PERSONA_RULES:
        try:
            if gate(profile):
                candidates.append((tag, score_fn(profile)))
        except Exception:
            continue
    if not candidates:
        return "other-at-risk"
    return max(candidates, key=lambda ts: ts[1])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="churn_prediction_result.csv")
    ap.add_argument("--features", default="user_features.csv")
    ap.add_argument("--output", default="high_risk_segments.csv")
    ap.add_argument("--risk-filter", default="High", help="risk_level to segment (default High)")
    ap.add_argument("--selected-only", action="store_true", help="segment capacity-selected candidates regardless of risk tier")
    args = ap.parse_args()

    pred = read_csv(args.pred)
    feat = read_csv(args.features)
    df = pred.merge(feat, on="user_id", how="left", validate="one_to_one")

    if args.selected_only:
        if "selected_for_contact" not in df:
            raise ValueError("--selected-only requires selected_for_contact in predictions")
        target = df[df["selected_for_contact"].isin([True, "True", "true", 1])].copy()
    else:
        target = df[df["risk_level"] == args.risk_filter].copy()
    if target.empty:
        pd.DataFrame(columns=OUTPUT_COLS).to_csv(args.output, index=False)
        print(f"no users at risk_level={args.risk_filter}")
        return

    # Audience order is a presentation choice, not a clustering input. Keep
    # K-Means initialization stable when the same selected users are reordered.
    target = target.sort_values("user_id", kind="mergesort").reset_index(drop=True)

    cols = check_coverage({c: 1 for c in CLUSTER_COLS}, target.columns, context="segment_high_risk.cluster_cols")

    X = target[cols].fillna(0).astype(float)
    Xs = StandardScaler().fit_transform(X)
    k, sil = pick_k(Xs)
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(Xs)
    target["segment"] = km.labels_

    prof = pd.DataFrame(Xs, columns=cols)
    prof["segment"] = km.labels_
    means = prof.groupby("segment").mean().to_dict("index")
    # A single standardized cluster has zero means, so relative persona gates
    # cannot distinguish its behavior. Preserve users with the neutral fallback.
    seg_persona = {s: "other-at-risk" if k == 1 else label_persona({c: float(v) for c, v in row.items()})
                   for s, row in means.items()}
    target["persona_tag"] = target["segment"].map(seg_persona)

    out = target[OUTPUT_COLS]
    out.to_csv(args.output, index=False)
    print(f"k={k} silhouette={sil:.3f}")
    print(out["persona_tag"].value_counts())
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
