"""Export future-holdout ranking and probability diagnostics for review."""
import argparse
import csv
import json
from pathlib import Path


def _number(value, digits=4):
    return "unavailable" if value is None else f"{value:.{digits}f}"


def write_evaluation_report(metrics, output_dir, calibration=None, data_kind=None):
    """Write Markdown, future-holdout calibration bins and an optional plot.

    Only held-out metrics enter the comparison and curves; their recorded
    temporal verification determines whether they can be called future tests.
    Training CV and fitting the calibration set cannot establish deployment
    performance. The caller is responsible for chronological data separation.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "model_evaluation_report.md"
    csv_path = output_dir / "calibration_curve.csv"
    png_path = output_dir / "calibration_curve.png"
    png_path.unlink(missing_ok=True)
    calibration = calibration or {}
    comparisons = []
    if "future_holdout_raw" in metrics:
        comparisons.append(("raw", "Before calibration", metrics["future_holdout_raw"]))
    if "future_holdout_calibrated" in metrics:
        comparisons.append(("calibrated", "After calibration", metrics["future_holdout_calibrated"]))
    elif "future_holdout" in metrics:
        comparisons.append(("final", "Final model", metrics["future_holdout"]))
    constraint = metrics.get("future_holdout", {}).get("probability_constraint", {})
    if constraint.get("enabled") and "future_holdout_calibrated" in metrics:
        comparisons.append(("final", "Final probability (time-constrained)", metrics["future_holdout"]))
    temporal_verified = bool(comparisons) and all(
        values.get("temporal_verified") is True for _, _, values in comparisons)

    lines = ["# Model Performance and Probability Diagnostics", ""]
    if constraint.get("enabled"):
        lines += [f"Time-reachability constraint: {constraint.get('unreachable_users', 0)} users cannot reach the silence threshold within this horizon,"
                  "their final probability is set to 0 and they are excluded from contact candidates. The before/after calibration rows keep pre-constraint scores; the final-probability row is used for delivery assessment.", ""]
    if data_kind == "simulated":
        lines += ["**Demo/simulated data, workflow validation only; these metrics cannot prove real business performance. Data provenance follows the data-kind declaration.**", ""]
    if calibration.get("enabled") or "future_holdout_calibrated" in metrics:
        if calibration.get("enabled"):
            lines.append(f"Independent calibration method: {calibration.get('method', 'unknown')}; calibration rows: {calibration.get('rows', 'unknown')}.")
        else:
            lines.append("The metrics include a before/after calibration comparison; this metrics file does not record the calibration method or row count.")
        lines.append("The calibration set fits the probability mapping; the metrics below come from a separate holdout, with temporal verification status below.")
        if calibration.get("warnings"):
            lines.append("")
        for warning in calibration.get("warnings", []):
            lines.append(f"- Calibration warning: {warning}")
    else:
        lines.append("This model has no independent probability-calibration record.")
    lines.append("")

    if not comparisons:
        lines.append("Only training-stage cross-validation is available; business-performance validation on an independent future snapshot has not been completed.")
        cv = metrics.get("cv", {})
        if cv.get("folds"):
            lines.append(f"Training CV: {cv['folds']} folds, ROC-AUC={_number(cv.get('roc_auc_mean'))}, PR-AUC={_number(cv.get('pr_auc_mean'))}.")
        elif cv.get("reason"):
            lines.append(f"Training CV unavailable: {cv['reason']}.")
        lines.append("Provide time-separated future data with complete label windows before comparing list hit rate and probability error.")
    else:
        scope_title = "Independent Future Snapshots" if temporal_verified else "Ordinary Holdout (time order unverified)"
        lines += [f"## {scope_title}", ""]
        if not temporal_verified:
            lines += ["These holdout metrics do not verify the time order of training, calibration and test label windows, and must not be treated as validation on an independent future snapshot.", ""]
        lines += [
                  "| Model | Users | ROC-AUC | PR-AUC | Brier ↓ | LogLoss ↓ | ECE ↓ | Selected K | Precision@K | Recall@K | Lift@K |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        notes = []
        for _, label, values in comparisons:
            top = values.get("top_k", {})
            cells = [label, str(values.get("users", "unavailable")), _number(values.get("roc_auc")),
                     _number(values.get("pr_auc")), _number(values.get("brier_score")),
                     _number(values.get("log_loss")), _number(values.get("calibration", {}).get("ece")),
                     str(top.get("selected", "unavailable")), _number(top.get("precision")),
                     _number(top.get("recall")), _number(top.get("lift"))]
            lines.append("| " + " | ".join(cells) + " |")
            if values.get("reason"):
                notes.append(f"{label} metric note: {values['reason']}.")
        if notes:
            lines += [""] + notes
        tie_policies = {values.get("top_k", {}).get("tie_breaker", "input_order") for _, _, values in comparisons}
        tie_note = ("Ties are cut by ascending user_id, matching the contact list." if tie_policies == {"user_id ascending"}
                    else "Tie-breaking follows the tie_breaker recorded per metric; input_order means a fixed input order.")
        lines += ["", f"K is the smaller of reachable capacity and sample size; {tie_note}Lift is the list churn rate divided by the population churn rate.",
                  "Lower Brier, LogLoss and ECE are generally better. Binned curves and ECE depend on binning and sample size; judge them against per-bin counts.",
                  "Risk-list performance and the operational retention increment require separate validation; the latter needs an independent controlled experiment.", ""]
        raw = metrics.get("future_holdout_raw", {})
        calibrated = metrics.get("future_holdout_calibrated", {})
        worsened = [name for name in ("brier_score", "log_loss")
                    if raw.get(name) is not None and calibrated.get(name) is not None
                    and calibrated[name] > raw[name]]
        if worsened:
            lines += [f"On this future set's point estimates, calibrated {', '.join(worsened)} worsened; fitting a calibrator does not guarantee better probability quality.", ""]

    columns = ["model", "evaluation_source", "temporal_verified", "evaluation_scope", "lower", "upper", "count",
               "mean_probability", "observed_rate", "absolute_gap"]
    rows = []
    for model_name, _, values in comparisons:
        for entry in values.get("calibration", {}).get("bins", []):
            rows.append({"model": model_name, "evaluation_source": "future_holdout",
                         "temporal_verified": values.get("temporal_verified", False),
                         "evaluation_scope": values.get("evaluation_scope", "holdout_time_unverified"),
                         **{key: entry.get(key) for key in columns
                            if key not in ("model", "evaluation_source", "temporal_verified", "evaluation_scope")}})
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    plotted = False
    if any(row["count"] for row in rows):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(6, 5))
            ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Ideal calibration")
            for model_name, _, _ in comparisons:
                points = [row for row in rows if row["model"] == model_name and row["count"]]
                if points:
                    ax.plot([row["mean_probability"] for row in points],
                            [row["observed_rate"] for row in points], marker="o", label=model_name)
            ax.set(xlabel="Mean predicted probability", ylabel="Observed churn rate",
                   title="Calibration on future holdout" if temporal_verified else "Calibration on holdout (time unverified)",
                   xlim=(0, 1), ylim=(0, 1))
            ax.legend()
            ax.grid(alpha=0.2)
            fig.savefig(png_path, bbox_inches="tight")
            plt.close(fig)
            plotted = True
        except Exception as exc:
            print(f"WARNING: calibration curve plot skipped: {exc}")
            png_path.unlink(missing_ok=True)
    if plotted:
        curve_label = "Probability calibration curve on independent future snapshots" if temporal_verified else "Probability calibration curve on ordinary holdout (time unverified)"
        lines += ["## Probability Calibration Curve", "", f"![{curve_label}](calibration_curve.png)", ""]
    if rows:
        lines += ["Per-bin detail is in calibration_curve.csv; empty bins leave the predicted mean and observed churn rate blank.", ""]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {"report": str(report_path), "calibration_csv": str(csv_path),
            "calibration_png": str(png_path) if plotted else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metrics", default="model_metrics.json")
    ap.add_argument("--output-dir")
    args = ap.parse_args()
    path = Path(args.metrics)
    metrics = json.loads(path.read_text(encoding="utf-8"))
    output = args.output_dir or path.parent
    print(json.dumps(write_evaluation_report(metrics, output), ensure_ascii=False))


if __name__ == "__main__":
    main()
