"""
Map high-risk personas to a retention playbook and emit a Markdown report.

Inputs:
- high_risk_segments.csv (from segment_high_risk.py)
- shap_local.csv          (optional; from explain_churn.py)

Output:
- retention_strategy_report.md

Usage:
    python recommend_strategy.py --segments high_risk_segments.csv \
        --shap shap_local.csv --output retention_strategy_report.md
"""
import argparse
import json
import math
from pathlib import Path

import pandas as pd
from feature_schema import read_csv


PLAYBOOK = {
    "silent-quitter": {
        "channel": "Push + SMS",
        "offer": "Comeback bonus / free 7-day perk",
        "content": "We miss you + new content highlight",
        "timing": "Day 1-3 of inactivity",
    },
    "declining-engagement": {
        "channel": "In-app + Email",
        "offer": "Personalized recommendations",
        "content": "Re-engagement based on last events",
        "timing": "Within 3 days",
    },
    "price-sensitive": {
        "channel": "Push",
        "offer": "Time-limited discount / coupon",
        "content": "Offer matched to past spend level",
        "timing": "Day 1, escalate by day 7",
    },
    "new-and-unstable": {
        "channel": "In-app + onboarding push",
        "offer": "Beginner tasks + reward",
        "content": "Tutorial / guided next step",
        "timing": "Day 1-3 of inactivity",
    },
    "at-risk-whale": {
        "channel": "1:1 account manager",
        "offer": "VIP perk / personal benefit",
        "content": "Personal outreach + satisfaction survey",
        "timing": "Day 1, high priority",
    },
    "other-at-risk": {
        "channel": "Push + Email",
        "offer": "General re-engagement perk",
        "content": "What's-new digest",
        "timing": "Within 3-5 days",
    },
}


def calibration_report_lines(prediction_meta):
    """Retain known probability failures instead of equating fitting with quality."""
    if not prediction_meta.get("calibration", {}).get("enabled", False):
        return ["Risk scores are not probability-calibrated and are used for relative risk ranking."]
    lines = ["A probability calibrator was fitted; fitting one does not by itself improve probability quality."]
    validation = prediction_meta.get("probability_validation", {})
    status = validation.get("status", "untested")
    if status == "untested":
        lines.append("A valid before/after calibration comparison on the same holdout is missing; probability improvement is unverified.")
    else:
        scope = ("a future holdout with verified time order" if validation.get("temporal_verified") is True
                 and validation.get("evaluation_scope") == "future_holdout" else "a holdout with unverified time order")
        conclusions = {"improved": "point estimates of the comparable probability metrics improved",
                       "worsened": "point estimates of the comparable probability metrics worsened",
                       "mixed": "comparable probability metrics improved on some measures and worsened on others",
                       "unchanged": "comparable probability metrics show no change"}
        lines.append(f"Validated on {scope}: {conclusions.get(status, 'quality status unknown')}.")
        values = []
        for name, label in (("brier_score", "Brier"), ("log_loss", "LogLoss"), ("ece", "ECE")):
            before, after = validation.get("raw", {}).get(name), validation.get("calibrated", {}).get(name)
            try:
                before, after = float(before), float(after)
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(before) and math.isfinite(after):
                values.append(f"{label} {before:.6g} → {after:.6g}")
        if values:
            lines.append("Before → after calibration (lower is better): " + "; ".join(values) + ".")
        lines.append("The final test is for evaluation only; after adjusting the model or calibration, reserve a later time period for validation.")
    if validation.get("single_class") is True:
        lines.append("This holdout has a single label class; probability error is still describable, but it cannot validate the ability to separate the two classes.")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments", default="high_risk_segments.csv")
    ap.add_argument("--shap", default="shap_local.csv")
    ap.add_argument("--shap-by-segment", default="shap_by_segment.csv")
    ap.add_argument("--score-scope", choices=("training_snapshot", "new_snapshot"), default="new_snapshot")
    ap.add_argument("--prediction-metadata", help="saved target, cohort, calibration and capacity selection")
    ap.add_argument("--output", default="retention_strategy_report.md")
    args = ap.parse_args()

    seg = read_csv(args.segments)
    prediction_meta = {}
    if args.prediction_metadata:
        prediction_meta = json.loads(Path(args.prediction_metadata).read_text())

    top_drivers = []
    try:
        sh = pd.read_csv(args.shap, index_col=0).iloc[:, 0].sort_values(ascending=False)
        top_drivers = sh.head(5).index.tolist()
    except (OSError, ValueError, IndexError):
        pass

    method = "unknown"
    explanation_scope = "scoring_model"
    if args.shap and Path(args.shap + ".meta.json").exists():
        explanation_meta = json.loads(Path(args.shap + ".meta.json").read_text())
        method = explanation_meta["method"]
        explanation_scope = explanation_meta.get("explained_model", "scoring_model")
    by_segment = pd.DataFrame()
    if args.shap_by_segment:
        try:
            by_segment = pd.read_csv(args.shap_by_segment, index_col=0)
        except (OSError, ValueError):
            pass

    summary = seg.groupby("persona_tag").agg(
        users=("user_id", "count"),
        avg_prob=("churn_probability", "mean"),
    ).sort_values("users", ascending=False)

    selection = prediction_meta.get("selection", {})
    definition = prediction_meta.get("definition", {})
    prevention_onset = definition.get("cohort") == "prevention" and definition.get("label_target") == "churn_onset"
    def timing(playbook):
        return "Check each user's remaining lead time before the threshold and reserve time-to-effect" if prevention_onset else playbook["timing"]
    lines = ["# User Risk Segments and Retention Strategy Report", ""]
    scoring_kind = prediction_meta.get("scoring_data_kind", prediction_meta.get("data_kind"))
    training_kind = prediction_meta.get("model_training_data_kind", definition.get("training_data_kind"))
    calibration_kind = prediction_meta.get("model_calibration_data_kind")
    kinds = {"real": "real data", "simulated": "simulated data", "unknown": "unlabeled provenance"}
    sources = [f"{label} ({kinds.get(kind, 'unlabeled provenance')})"
               for label, kind in (("scoring input", scoring_kind), ("model training", training_kind), ("model calibration", calibration_kind))
               if kind is not None]
    if sources:
        lines.extend(["Data sources: " + ", ".join(sources) + ".", ""])
    if scoring_kind == "simulated":
        lines.extend(["**This run treats the data as demo/simulated, workflow validation only; this report does not represent real business performance.**", ""])
    if "simulated" in (training_kind, calibration_kind):
        lines.extend(["**The model was fitted on simulated data; predictive performance still needs validation on real data.**", ""])
    coverage = prediction_meta.get("audience_coverage")
    if coverage is not None:
        lines.append(f"Target users in this batch: **{coverage['target_users']}**")
        lines.append(f"Users scored by the model in this batch: **{coverage['scored_users']}**; "
                     f"unscored status records retained: **{coverage['unscored_users']}**.")
        labels = coverage.get("result_label_counts", {})
        lines.append("Full audience status: " + ("; ".join(f"{label} {count} users" for label, count in labels.items()) if labels else "empty audience") + ".")
        lines.append("already_churned is the observed state as of the snapshot; users without history stay insufficient_data."
                     "Future probabilities of unscored users stay blank; they are not filled with 0 or 100%.")
        lines.append("Model quality metrics come from the saved model's historical holdout validation and are not a dedicated validation of this batch.")
    elif prediction_meta.get("users") is not None:
        lines.append(f"Users scored in this batch: **{prediction_meta['users']}**")
    else:
        lines.append("Users scored in this batch: not provided; it cannot be inferred from segment size.")
    lines.append(f"Users in this segmentation file: **{len(seg)}**")
    if selection.get("mode") == "top_k":
        lines.append(f"Selected by contact capacity: requested {selection.get('requested', 'not provided')} users, "
                     f"actual candidates {selection.get('selected', 'not provided')}."
                     "The list is ranked by risk; randomized control groups belong in the offline experiment tool.")
    if definition:
        target_names = {"churn_onset": "reaching the silence threshold within the horizon", "window_inactive": "no qualifying activity for the whole horizon"}
        cohort_names = {"prevention": "not yet churned, pre-emptive retention", "winback": "already churned, win-back", "all": "all users in the observation window"}
        cohort_label = "population scored by the model" if coverage is not None else "population"
        lines.append(f"Prediction target: {target_names.get(definition.get('label_target'), 'no qualifying activity for the whole horizon')}; "
                     f"{cohort_label}: {cohort_names.get(definition.get('cohort', 'all'), definition.get('cohort'))}.")
        lines.append(f"Silence threshold D={definition.get('churn_inactivity_days')} days, prediction horizon H="
                     f"{definition.get('prediction_days', definition.get('churn_inactivity_days'))} days, "
                     f"qualifying activity criterion={definition.get('label_criterion', 'any')}.")
    if prediction_meta.get("snapshot_time"):
        lines.append(f"Behavior snapshot cutoff T={prediction_meta['snapshot_time']}.")
    quality = prediction_meta.get("data_quality")
    if quality:
        lines.append(f"Data preflight status: {quality['status']}; see data_quality_report.json.")
        for phase, check in quality.get("phases", {}).items():
            availability = check.get("feature_availability")
            if availability:
                lines.append(f"{phase} feature observability: core={availability['core']}, "
                             f"payment={availability['payment']}, sessions={availability['sessions']}.")
            lines.extend(f"Data note ({phase}): {message}" for message in check.get("warnings", []))
    lines.extend(calibration_report_lines(prediction_meta))
    constraint = prediction_meta.get("probability_constraint", {})
    if constraint.get("enabled"):
        lines.append(f"Time constraint: {constraint.get('unreachable_users', 0)} users cannot reach D days of silence within this H-day horizon, "
                     "their final probability is 0, their low-risk record is retained and they are excluded from contact; model_probability keeps the pre-constraint model score."
                     "A 0 here does not guarantee future activity. SHAP explains the pre-constraint model; rule-based zeros need separate interpretation.")
    lines.append("Persona tags come from clustering rules and playbook suggestions from a preset table; the retention increment requires a randomized controlled experiment.")
    if prevention_onset:
        lines.append("The prevention deadline per user is the last qualifying activity time + D. Contact should arrive before that deadline,"
                     "reserving time for the strategy to take effect and for execution delay; with insufficient lead time a prevention window is not guaranteed."
                     "Precise scheduling requires checking each user's activity times and execution conditions; the timings below are conditional requirements, not fixed-day schedules.")
    if explanation_scope == "base_model_before_calibration":
        lines.append("The feature explanations below target the base model before calibration and cannot directly decompose calibrated probabilities.")
    if args.score_scope == "training_snapshot":
        lines.append("This report contains fitted scores from the training snapshot; for generalization see cross-validation or the independent future-snapshot evaluation.")
    if top_drivers:
        method_names = {"shap": "SHAP", "tree_importance": "tree-model feature importance",
                        "linear_contribution": "linear-model contribution estimate", "heuristic_weights": "rule weights"}
        lines.append(f"Top risk-associated features ({method_names.get(method, 'feature importance')}): {', '.join(top_drivers)}")
    else:
        lines.append("No feature explanations were obtained for this run.")
    if seg.empty:
        lines.append("No target users under the current filters.")
    lines.append("")
    lines.append("## Segment Overview")
    lines.append("")
    lines.append("| Persona tag | Users | Mean risk score | Channel | Offer | Content | Timing |")
    lines.append("|---|---:|---:|---|---|---|---|")
    for tag, row in summary.iterrows():
        pb = PLAYBOOK.get(tag, PLAYBOOK["other-at-risk"])
        lines.append(f"| {tag} | {int(row['users'])} | {row['avg_prob']:.3f} | "
                    f"{pb['channel']} | {pb['offer']} | {pb['content']} | {timing(pb)} |")
    lines.append("")
    lines.append("## Per-Persona Strategy Draft")
    lines.append("")
    for tag in summary.index:
        pb = PLAYBOOK.get(tag, PLAYBOOK["other-at-risk"])
        n = int(summary.loc[tag, "users"])
        lines.append(f"### {tag} ({n} users)")
        lines.append("")
        if method == "shap" and tag in by_segment:
            drivers = by_segment[tag].dropna().sort_values(ascending=False).head(5).index.tolist()
            lines.append(f"- Risk-associated features for this persona (SHAP): {', '.join(drivers)}")
        lines.append(f"- Channel: {pb['channel']}")
        lines.append(f"- Offer: {pb['offer']}")
        lines.append(f"- Content: {pb['content']}")
        lines.append(f"- Timing: {timing(pb)}")
        lines.append("")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {args.output}; personas={list(summary.index)}")


if __name__ == "__main__":
    main()
