"""Prepare offline randomized assignments and evaluate complete ITT outcomes.

This module writes local CSV/JSON/Markdown only. It never delivers a touchpoint.
Naive times are interpreted in Asia/Shanghai. Experiment follow-up is measured
from assignment and is independent of the churn model's inactivity/horizon.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, fisher_exact, norm

from data_provenance import resolve_data_kind
from feature_schema import read_csv

GENERATOR = "churn-risk-analyst.retention_experiment.assign"
# Historical manifests are immutable provenance records. Keep accepting their
# original identifier while applying exactly the same fingerprint/replay checks.
LEGACY_GENERATORS = {"ai-churn-analyst.retention_experiment.assign"}
ALLOCATION = "fixed_count_random_permutation"
TIMEZONE = "Asia/Shanghai"


# Compatibility for callers that used the previous private helper.
_data_kind_info = resolve_data_kind


def _timestamp(value):
    value = pd.Timestamp(value)
    if pd.isna(value):
        raise ValueError("timestamps cannot be missing")
    return value.tz_localize(TIMEZONE) if value.tzinfo is None else value.tz_convert(TIMEZONE)


def _users(frame, context):
    if "user_id" not in frame:
        raise ValueError(f"{context} requires user_id")
    frame = frame.copy()
    if frame["user_id"].isna().any():
        raise ValueError(f"{context} has missing user_id")
    frame["user_id"] = frame["user_id"].astype(str)
    if frame["user_id"].str.strip().eq("").any() or frame["user_id"].duplicated().any():
        raise ValueError(f"{context} requires unique, nonempty user_id")
    return frame


def _random_groups(size, control_count, seed):
    groups = np.full(size, "treatment", dtype=object)
    groups[np.random.default_rng(seed).permutation(size)[:control_count]] = "control"
    return groups


def assignment_digest(assignments):
    """Fingerprint assignment semantics, independent of CSV row order/encoding."""
    canonical = assignments[["user_id", "group", "assigned_at"]].copy()
    canonical["assigned_at"] = canonical["assigned_at"].map(lambda x: _timestamp(x).isoformat())
    canonical = canonical.sort_values("user_id", kind="mergesort")
    data = canonical.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def assign_candidates(candidates, assigned_at, control_fraction=0.2, seed=42, *, data_kind=None):
    candidates = _users(candidates, "candidates")
    provenance = _data_kind_info(data_kind, frames=[("candidates", candidates)])
    if not 0 < control_fraction < 1:
        raise ValueError("control_fraction must be strictly between 0 and 1")
    if not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if "selected_for_contact" in candidates:
        selected = candidates["selected_for_contact"].astype(str).str.lower()
        if not selected.isin(["true", "false", "1", "0"]).all():
            raise ValueError("selected_for_contact must contain complete boolean values")
        candidates = candidates[selected.isin(["true", "1"])].copy()
    candidates = candidates.sort_values("user_id", kind="mergesort").reset_index(drop=True)
    size = len(candidates)
    if size < 2:
        raise ValueError("at least two selected candidates are needed, one per group")
    controls = min(size - 1, max(1, int(round(size * control_fraction))))
    groups = _random_groups(size, controls, seed)
    assigned = _timestamp(assigned_at).isoformat()
    candidates["group"] = groups
    candidates["assigned_at"] = assigned
    if provenance["data_kind"] != "unknown":
        candidates["data_kind"] = provenance["data_kind"]
    order = ["user_id", "group", "assigned_at"]
    assignments = candidates[order + [c for c in candidates if c not in order]]
    manifest = {
        "version": 1, "generator": GENERATOR, "randomized": True,
        "allocation": ALLOCATION, "seed": int(seed), "assigned_at": assigned,
        "requested_control_fraction": float(control_fraction),
        "group_counts": {"treatment": size - controls, "control": controls},
        "expected_treatment_share": (size - controls) / size,
        "assignment_sha256": assignment_digest(assignments),
        "execution": "offline_assignment_only", **provenance,
    }
    return assignments, manifest


def _wilson(successes, size, confidence):
    rate = successes / size
    z = float(norm.ppf(0.5 + confidence / 2))
    denominator = 1 + z * z / size
    center = (rate + z * z / (2 * size)) / denominator
    half = z * np.sqrt(rate * (1 - rate) / size + z * z / (4 * size * size)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def newcombe_interval(treatment_successes, treatment_size, control_successes, control_size, confidence=0.95):
    """Newcombe difference interval constructed from two Wilson intervals.

    Reference implementation/formulation: statsmodels.stats.proportion.
    confint_proportions_2indep(method='newcomb', compare='diff').
    """
    if not 0 < confidence < 1 or min(treatment_size, control_size) <= 0:
        raise ValueError("confidence must be between 0 and 1 and group sizes must be positive")
    if not (0 <= treatment_successes <= treatment_size and 0 <= control_successes <= control_size):
        raise ValueError("success counts must lie between zero and group size")
    treatment = treatment_successes / treatment_size
    control = control_successes / control_size
    treatment_low, treatment_high = _wilson(treatment_successes, treatment_size, confidence)
    control_low, control_high = _wilson(control_successes, control_size, confidence)
    difference = treatment - control
    low = difference - np.hypot(treatment - treatment_low, control_high - control)
    high = difference + np.hypot(treatment_high - treatment, control - control_low)
    return float(max(-1.0, low)), float(min(1.0, high))


def _verify_manifest(assignments, manifest, counts):
    if manifest is None:
        return False, "no assignment manifest was supplied"
    if not isinstance(manifest, dict):
        raise ValueError("assignment manifest must be a JSON object")
    generator = manifest.get("generator")
    known = (isinstance(generator, str) and generator in {GENERATOR, *LEGACY_GENERATORS} and manifest.get("version") == 1 and
             manifest.get("randomized") is True and manifest.get("allocation") == ALLOCATION)
    if not known:
        return False, "manifest does not identify this tool's randomized assignment procedure"
    if manifest.get("assignment_sha256") != assignment_digest(assignments):
        raise ValueError("assignment manifest hash does not match the original assignments")
    if manifest.get("group_counts") != counts:
        raise ValueError("assignment manifest group counts do not match assignments")
    seed = manifest.get("seed")
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("assignment manifest has an invalid random seed")
    ordered = assignments.sort_values("user_id", kind="mergesort")
    if ordered["group"].tolist() != _random_groups(len(ordered), counts["control"], seed).tolist():
        raise ValueError("assignments cannot be reproduced using the manifest's random seed")
    share = manifest.get("expected_treatment_share")
    if not isinstance(share, (float, int)) or not 0 < share < 1:
        raise ValueError("manifest expected_treatment_share must lie strictly between 0 and 1")
    return True, "random assignment manifest, fingerprint and seed replay verified"


def _economic_results(frame, counts, causal_eligible, simulation_only=False):
    interpretation = "simulated_group_difference" if simulation_only else \
        "incremental_point_estimate" if causal_eligible else "descriptive_group_difference"
    results = {"interpretation": interpretation}
    for column in ("revenue", "cost"):
        if column in frame:
            means = frame.groupby("group")[column].mean()
            difference = float(means["treatment"] - means["control"])
            scaled = difference * counts["treatment"]
            if not np.isfinite([difference, scaled]).all():
                raise ValueError(f"{column} summary overflowed; check the input units and values")
            results[column] = {"treatment_mean": float(means["treatment"]),
                               "control_mean": float(means["control"]),
                               "mean_difference": difference, "treatment_scaled_difference": scaled}
    if "revenue" in results and "cost" in results:
        revenue = results["revenue"]["treatment_scaled_difference"]
        cost = results["cost"]["treatment_scaled_difference"]
        if not np.isfinite(revenue - cost):
            raise ValueError("profit summary overflowed; check the monetary units and values")
        results["treatment_scaled_profit_difference"] = revenue - cost
        if causal_eligible:
            results.update(incremental_revenue_point_estimate=revenue,
                           incremental_cost_point_estimate=cost,
                           incremental_profit_point_estimate=revenue - cost)
        if causal_eligible and cost > 0:
            roi = (revenue - cost) / cost
            results.update(roi=roi if np.isfinite(roi) else None,
                           roi_reason="" if np.isfinite(roi) else "ROI overflowed; check the monetary units")
        else:
            reason = "simulation_only: simulated data cannot establish real ROI" if simulation_only else \
                "randomized assignment was not verified or SRM failed" if not causal_eligible else "incremental cost is not positive"
            results.update(roi=None, roi_reason=reason)
    else:
        reason = "simulation_only: simulated data cannot establish real ROI" if simulation_only else \
            "both revenue and cost columns are required"
        results.update(roi=None, roi_reason=reason)
    return results


def analyze_experiment(assignments, outcomes, outcome_days, data_end, manifest=None, confidence=0.95, *, data_kind=None):
    assignments = _users(assignments, "assignments")
    outcomes = _users(outcomes, "outcomes")
    provenance = _data_kind_info(data_kind, frames=[("assignments", assignments), ("outcomes", outcomes)], manifest=manifest)
    if not isinstance(outcome_days, (int, np.integer)) or outcome_days <= 0:
        raise ValueError("outcome_days must be a positive integer")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be strictly between 0 and 1")
    if not {"group", "assigned_at"}.issubset(assignments):
        raise ValueError("assignments require group and assigned_at")
    if set(assignments["group"]) != {"treatment", "control"}:
        raise ValueError("assignments must contain both treatment and control groups only")
    if set(assignments["user_id"]) != set(outcomes["user_id"]):
        raise ValueError("ITT requires exactly one outcome for every originally assigned user; missing/extra users are not allowed")
    if "retained" not in outcomes:
        raise ValueError("outcomes require the complete binary retained column")
    for column in ("retained", "revenue", "cost"):
        if column in outcomes:
            outcomes[column] = pd.to_numeric(outcomes[column], errors="raise")
            if not np.isfinite(outcomes[column].to_numpy(dtype=float)).all():
                raise ValueError(f"{column} must be complete and finite; missing outcomes are never filled with zero")
    if not outcomes["retained"].isin([0, 1]).all():
        raise ValueError("retained must contain only 0 or 1")
    end = _timestamp(data_end)
    if end > pd.Timestamp.now(tz=TIMEZONE):
        raise ValueError("data_end cannot be in the actual future")
    assignment_times = assignments["assigned_at"].map(_timestamp)
    if (assignment_times + pd.Timedelta(days=outcome_days) > end).any():
        raise ValueError("outcome window is not mature for every assigned user")
    original_groups = assignments.set_index("user_id")["group"]
    if "group" in outcomes:
        if not outcomes.set_index("user_id")["group"].eq(original_groups.reindex(outcomes["user_id"])).all():
            raise ValueError("outcome group cannot change the original random assignment")
    columns = [c for c in ("user_id", "retained", "revenue", "cost") if c in outcomes]
    frame = assignments[["user_id", "group"]].merge(outcomes[columns], on="user_id", validate="one_to_one")
    counts = {group: int((frame["group"] == group).sum()) for group in ("treatment", "control")}
    verified, provenance_reason = _verify_manifest(assignments, manifest, counts)
    expected = manifest["expected_treatment_share"] if verified else None
    srm_p = float(binomtest(counts["treatment"], n=len(frame), p=expected).pvalue) if verified else None
    srm_failed = srm_p is not None and srm_p < 0.001
    causal_eligible = verified and not srm_failed and not provenance["simulation_only"]
    successes = {group: int(frame.loc[frame["group"] == group, "retained"].sum()) for group in counts}
    rates = {group: successes[group] / counts[group] for group in counts}
    difference = rates["treatment"] - rates["control"]
    low, high = newcombe_interval(successes["treatment"], counts["treatment"],
                                  successes["control"], counts["control"], confidence)
    p_value = float(fisher_exact([[successes["treatment"], counts["treatment"] - successes["treatment"]],
                                  [successes["control"], counts["control"] - successes["control"]]],
                                 alternative="two-sided").pvalue)
    warnings = []
    if provenance["simulation_only"]:
        warnings.append("Simulated data, workflow validation only, no real contact was sent; statistic and monetary differences do not represent real causal gains.")
    if not verified:
        warnings.append("Random assignment records are unverified; group differences are descriptive only and cannot be attributed to the contact.")
    if srm_failed:
        warnings.append("SRM p < 0.001: group proportions are anomalous; pause causal-increment interpretation and check the raw assignment and data.")
    if min(counts.values()) < 30:
        warnings.append("At least one group has fewer than 30 users; weigh small-sample uncertainty against the interval width.")
    if p_value >= 1 - confidence:
        warnings.append("The current test lacks sufficient evidence of a retention-rate difference; judge together with the interval and the complete experiment plan.")
    return {
        "analysis": "intention_to_treat", "randomization_verified": verified,
        **provenance,
        "causal_estimate_eligible": causal_eligible, "provenance_reason": provenance_reason,
        "outcome_days": int(outcome_days), "data_end": end.isoformat(), "timezone": TIMEZONE,
        "followup": {"earliest_assignment": assignment_times.min().isoformat(),
                     "latest_assignment": assignment_times.max().isoformat(), "all_windows_mature": True},
        "groups": {group: {"users": counts[group], "retained": successes[group], "retention_rate": rates[group]}
                   for group in counts},
        "effect": {"absolute_difference": difference, "absolute_difference_pp": difference * 100,
                   "relative_lift": difference / rates["control"] if rates["control"] > 0 else None,
                   "relative_lift_reason": "" if rates["control"] > 0 else "control retention rate is zero",
                   "confidence_level": confidence, "ci_method": "Newcombe/Wilson",
                   "absolute_difference_ci": [low, high], "absolute_difference_ci_pp": [100 * low, 100 * high],
                   "p_value": p_value, "test": "two-sided Fisher exact",
                   "treatment_scaled_retention_difference": difference * counts["treatment"]},
        "srm": {"expected_treatment_share": expected, "p_value": srm_p, "threshold": 0.001,
                "failed": srm_failed, "method": "two-sided binomial diagnostic" if verified else "unavailable"},
        "economics": _economic_results(frame, counts, causal_eligible, provenance["simulation_only"]), "warnings": warnings,
    }


def experiment_report(metrics):
    effect = metrics["effect"]
    simulation_only = metrics.get("simulation_only", False)
    heading = "Simulated Retention Analysis (workflow validation only)" if simulation_only else \
        "Randomized Controlled Retention Increment Estimate" if metrics["causal_estimate_eligible"] else "Retention Group Difference Description"
    low, high = effect["absolute_difference_ci_pp"]
    lines = [f"# {heading}", "", "Analyzed by initial assignment (ITT), including users not delivered, not clicked and not returned.", "",
             f"Follow-up: each user is observed for {metrics['outcome_days']} days from assigned_at; all windows are mature.",
             "The follow-up window is independent of the prediction model's silence threshold D and horizon H. The business definition of retained must be agreed before the experiment.", "",
             "| Group | Assigned users | Retained | Retention rate |", "|---|---:|---:|---:|"]
    if simulation_only:
        lines[2:2] = ["Simulated data, workflow validation only, no real contact was sent. The differences and intervals below are computations on simulated data.", ""]
    for group, row in metrics["groups"].items():
        lines.append(f"| {group} | {row['users']} | {row['retained']} | {row['retention_rate']:.2%} |")
    lines += ["", f"Absolute retention-rate difference (treatment − control): {effect['absolute_difference_pp']:+.3f} percentage points.",
              f"{effect['confidence_level']:.0%} Newcombe/Wilson interval: [{low:+.3f}, {high:+.3f}] percentage points.",
              f"Two-sided Fisher exact test p-value: {effect['p_value']:.6g}."]
    if effect["relative_lift"] is None:
        lines.append("The control retention rate is zero; relative lift is undefined.")
    else:
        lines.append(f"Relative group difference: {effect['relative_lift']:+.2%}.")
    if metrics["causal_estimate_eligible"]:
        lines.append(f"Estimated incremental retained users at treatment-group scale: {effect['treatment_scaled_retention_difference']:+.3f} (point estimate).")
    for warning in metrics["warnings"]:
        lines += ["", warning]
    if metrics["srm"]["p_value"] is not None:
        lines += ["", f"Assignment-ratio diagnostic SRM p-value: {metrics['srm']['p_value']:.6g}.",
                  "This tool assigns randomly under fixed quotas; when assigned counts match the designed ratios, this test mainly serves as a record check."]
    money = metrics["economics"]
    if "revenue" in money or "cost" in money:
        monetary_note = "The monetary differences below are descriptive computations on simulated amounts, workflow validation only, not real gains." if simulation_only else \
            "Monetary values keep the input unit; the amounts below are point estimates without intervals."
        lines += ["", monetary_note, "",
                  "| Metric | treatment mean | control mean | Mean difference | Scaled to treatment size |",
                  "|---|---:|---:|---:|---:|"]
        for column in ("revenue", "cost"):
            if column in money:
                row = money[column]
                lines.append(f"| {column} | {row['treatment_mean']:.4f} | {row['control_mean']:.4f} | "
                             f"{row['mean_difference']:+.4f} | {row['treatment_scaled_difference']:+.4f} |")
        if "treatment_scaled_profit_difference" in money:
            lines += ["", f"Profit difference scaled to treatment-group size: {money['treatment_scaled_profit_difference']:+.4f}."]
        if money["roi"] is not None:
            lines.append(f"Incremental profit / incremental cost (ROI): {money['roi']:.4f}.")
        else:
            lines.append(f"ROI not computed: {money['roi_reason']}.")
    lines += ["", "Intervals and tests: [Newcombe/Wilson](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html), "
              "[Fisher exact test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.fisher_exact.html)."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    assign = subparsers.add_parser("assign", help="prepare local random assignments; no touchpoint delivery")
    assign.add_argument("--candidates", required=True)
    assign.add_argument("--assigned-at", required=True)
    assign.add_argument("--control-fraction", type=float, default=0.2)
    assign.add_argument("--seed", type=int, default=42)
    assign.add_argument("--output", default="assignments.csv")
    assign.add_argument("--manifest", help="default: manifest.json beside output CSV")
    assign.add_argument("--data-kind", choices=("real", "simulated"), default=None,
                        help="declare data provenance; cannot override an existing simulation marker")
    analyze = subparsers.add_parser("analyze", help="analyze complete, mature ITT outcomes locally")
    analyze.add_argument("--assignments", required=True)
    analyze.add_argument("--outcomes", required=True)
    analyze.add_argument("--outcome-days", type=int, required=True)
    analyze.add_argument("--data-end", required=True)
    analyze.add_argument("--confidence", type=float, default=0.95)
    analyze.add_argument("--manifest", help="default: manifest.json beside assignments; absence allows descriptive analysis")
    analyze.add_argument("--output-dir", default=".")
    analyze.add_argument("--data-kind", choices=("real", "simulated"), default=None,
                         help="declare data provenance; any simulation source remains simulation-only")
    args = parser.parse_args()
    if args.command == "assign":
        assignments, manifest = assign_candidates(read_csv(args.candidates), args.assigned_at, args.control_fraction,
                                                  args.seed, data_kind=args.data_kind)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        manifest_path = Path(args.manifest) if args.manifest else output.with_name("manifest.json")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        assignments.to_csv(output, index=False)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        print(f"Wrote offline assignments: {output}; manifest: {manifest_path}")
    else:
        manifest_path = Path(args.manifest) if args.manifest else Path(args.assignments).with_name("manifest.json")
        if args.manifest and not manifest_path.exists():
            raise ValueError(f"explicit manifest does not exist: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
        metrics = analyze_experiment(read_csv(args.assignments), read_csv(args.outcomes), args.outcome_days,
                                     args.data_end, manifest, args.confidence, data_kind=args.data_kind)
        output = Path(args.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "experiment_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        (output / "experiment_report.md").write_text(experiment_report(metrics), encoding="utf-8")
        print(f"Wrote experiment analysis: {output / 'experiment_report.md'}")


if __name__ == "__main__":
    main()
