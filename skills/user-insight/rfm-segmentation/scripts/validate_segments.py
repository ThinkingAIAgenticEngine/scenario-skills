#!/usr/bin/env python3
"""Deterministic spot-checks for an exported lifecycle RFM segment CSV/CSV.GZ.

Core expected columns: subject (or --subject), R_days, F_orders, M_raw,
R_score, F_score, M_score, segment.

Optional R_effective_bands/F_effective_bands/M_effective_bands columns are
validated when present. This is a file-level validator; it cannot prove
external universe coverage, revenue lineage, or tag/cluster SQL fidelity.
"""
import argparse
import json
import pandas as pd

BASE_SEGMENTS = {
    "champions", "lost_high_value", "loyal", "potential", "promising",
    "hibernating", "at_risk",
}
EXTENSION_SEGMENTS = {"champions_elite", "loyal_premium"}


def _is_blank(series):
    return series.isna() | series.astype(str).str.strip().eq("")


def _numeric_integer_scores(df, score, issues):
    vals = pd.to_numeric(df[score], errors="coerce")
    if vals.isna().any():
        issues.append(f"null/non-numeric {score}")
        return None
    if ((vals % 1) != 0).any():
        issues.append(f"non-integer {score}")
    if (vals < 1).any():
        issues.append(f"{score} contains values < 1")
    return vals.astype(int)


def validate(df, subject, segment_mode="lifecycle", extra_segments=None):
    issues = []
    if subject not in df.columns:
        return {"go": False, "issues": [f"missing subject column: {subject}"]}

    required = ["R_days", "F_orders", "M_raw", "R_score", "F_score", "M_score", "segment"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {"go": False, "issues": [f"missing required columns: {', '.join(missing)}"]}

    if _is_blank(df[subject]).any():
        issues.append("null/empty subject values")
    if df[subject].duplicated().any():
        issues.append("duplicate subjects")
    if _is_blank(df["segment"]).any():
        issues.append("unassigned/blank segments")

    r = pd.to_numeric(df["R_days"], errors="coerce")
    f = pd.to_numeric(df["F_orders"], errors="coerce")
    m_raw = pd.to_numeric(df["M_raw"], errors="coerce")
    if r.isna().any() or (r < 0).any():
        issues.append("null/non-numeric/negative R_days")
    if f.isna().any() or (f < 0).any():
        issues.append("null/non-numeric/negative F_orders")
    if m_raw.isna().any():
        issues.append("null/non-numeric M_raw")

    numeric_metrics = {
        "R_days": r,
        "F_orders": f,
        "M_raw": m_raw,
    }
    if "M_scoring" in df.columns:
        m_scoring = pd.to_numeric(df["M_scoring"], errors="coerce")
        numeric_metrics["M_scoring"] = m_scoring
        if m_scoring.isna().any():
            issues.append("null/non-numeric M_scoring")

    if segment_mode == "lifecycle":
        allowed = BASE_SEGMENTS | EXTENSION_SEGMENTS | set(extra_segments or [])
        bad = sorted(set(df["segment"].dropna().astype(str)) - allowed)
        if bad:
            issues.append(f"illegal lifecycle segment keys: {bad[:20]}")

    score_values = {s: _numeric_integer_scores(df, s, issues) for s in ["R_score", "F_score", "M_score"]}

    metric_score_pairs = [
        ("R_days", "R_score", "R_effective_bands"),
        ("F_orders", "F_score", "F_effective_bands"),
        (("M_scoring" if "M_scoring" in df.columns else "M_raw"), "M_score", "M_effective_bands"),
    ]
    for metric, score, effective_col in metric_score_pairs:
        metric_scores = pd.DataFrame({"metric": numeric_metrics[metric], "score": df[score]})
        split_ties = metric_scores.groupby("metric", dropna=False)["score"].nunique(dropna=False)
        if (split_ties > 1).any():
            bad_values = split_ties[split_ties > 1].index.tolist()[:10]
            issues.append(f"same raw {metric} value mapped to multiple {score} bands: {bad_values}")

        vals = score_values.get(score)
        if vals is not None and len(vals):
            observed = sorted(set(vals.tolist()))
            if observed != list(range(1, max(observed) + 1)):
                issues.append(f"non-contiguous observed {score} values: {observed}")

            if effective_col in df.columns:
                eff = pd.to_numeric(df[effective_col], errors="coerce")
                if eff.isna().any() or ((eff % 1) != 0).any() or (eff < 1).any():
                    issues.append(f"invalid {effective_col}")
                else:
                    uniq_eff = sorted(set(eff.astype(int).tolist()))
                    if len(uniq_eff) != 1:
                        issues.append(f"{effective_col} is not constant across file: {uniq_eff}")
                    else:
                        effective = uniq_eff[0]
                        if vals.max() > effective:
                            issues.append(f"{score} exceeds {effective_col}={effective}")
                        if observed != list(range(1, effective + 1)):
                            issues.append(f"{score} does not cover contiguous 1..{effective}: observed={observed}")

    for metric, score, ascending_better in [
        ("R_days", "R_score", False),
        ("F_orders", "F_score", True),
        (("M_scoring" if "M_scoring" in df.columns else "M_raw"), "M_score", True),
    ]:
        pairs = pd.DataFrame({metric: numeric_metrics[metric], score: df[score]})
        pairs = pairs.dropna().drop_duplicates().sort_values(metric)
        vals = pd.to_numeric(pairs[score], errors="coerce").to_numpy()
        if len(vals) > 1 and not pd.isna(vals).any():
            if ascending_better and (vals[1:] < vals[:-1]).any():
                issues.append(f"non-monotonic score direction for {metric}/{score}")
            if (not ascending_better) and (vals[1:] > vals[:-1]).any():
                issues.append(f"non-monotonic score direction for {metric}/{score}")

    summary_df = df.assign(_M_raw_numeric=m_raw.fillna(0))
    segment_summary = (
        summary_df.groupby("segment", dropna=False)
          .agg(users=(subject, "count"), revenue=("_M_raw_numeric", "sum"))
          .reset_index()
    )
    total_users = len(df)
    total_revenue = float(m_raw.fillna(0).sum())
    segment_summary["user_share"] = segment_summary["users"] / total_users if total_users else 0
    segment_summary["revenue_share"] = segment_summary["revenue"] / total_revenue if total_revenue else 0

    return {
        "go": not issues,
        "issues": issues,
        "total_users": total_users,
        "total_revenue": total_revenue,
        "segment_summary": segment_summary.to_dict(orient="records"),
        "limitations": [
            "file-level validation only; does not prove external universe coverage",
            "does not prove exact threshold/operator reproduction against tag/cluster SQL",
            "does not prove revenue lineage or entity semantics",
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--subject", default="subject")
    p.add_argument("--segment-mode", choices=["lifecycle", "custom"], default="lifecycle")
    p.add_argument("--allow-segment", action="append", default=[])
    args = p.parse_args()
    df = pd.read_csv(args.file)
    print(json.dumps(validate(df, args.subject, args.segment_mode, args.allow_segment), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
