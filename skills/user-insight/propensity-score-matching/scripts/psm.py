#!/usr/bin/env python3
"""Dependency-free propensity score matching for AE user-level CSV exports."""

import argparse
import csv
import json
import math
import statistics
from pathlib import Path


EPS = 1e-9


def sigmoid(value):
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def logit(value):
    value = min(max(value, 1e-6), 1.0 - 1e-6)
    return math.log(value / (1.0 - value))


def weighted_mean(values, weights):
    total = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total


def weighted_var(values, weights):
    mean = weighted_mean(values, weights)
    total = sum(weights)
    return sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / total


def smd(t_values, c_values, t_weights=None, c_weights=None):
    t_weights = t_weights or [1.0] * len(t_values)
    c_weights = c_weights or [1.0] * len(c_values)
    mt = weighted_mean(t_values, t_weights)
    mc = weighted_mean(c_values, c_weights)
    pooled = math.sqrt((weighted_var(t_values, t_weights) + weighted_var(c_values, c_weights)) / 2.0)
    if pooled < EPS:
        return 0.0 if abs(mt - mc) < EPS else math.copysign(float("inf"), mt - mc)
    return (mt - mc) / pooled


def parse_args():
    parser = argparse.ArgumentParser(description="Propensity score matching for AE user CSV data")
    parser.add_argument("--input", required=True)
    parser.add_argument("--id-col", required=True)
    parser.add_argument("--treatment-col", required=True)
    parser.add_argument("--covariates", required=True, help="Comma-separated numeric columns")
    parser.add_argument("--outcome-col")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ratio", type=int, default=1)
    parser.add_argument("--caliper", type=float, default=0.2, help="Multiplier of pooled logit SD")
    parser.add_argument("--with-replacement", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=5000)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--l2", type=float, default=0.01)
    parser.add_argument(
        "--max-covariate-missing-rate",
        type=float,
        default=0.10,
        help="Stop when any covariate's missing-or-invalid rate exceeds this value",
    )
    return parser.parse_args()


def load_rows(args, covariates):
    required = [args.id_col, args.treatment_col] + covariates
    if args.outcome_col:
        required.append(args.outcome_col)
    kept, dropped, total_rows = [], 0, 0
    seen_ids = set()
    missing_by_field = {name: 0 for name in required}
    invalid_by_field = {name: 0 for name in required}
    with open(args.input, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in required if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("Missing columns: " + ", ".join(missing))
        for line_no, raw in enumerate(reader, start=2):
            total_rows += 1
            user_value = raw.get(args.id_col)
            user_id = str(user_value).strip() if user_value is not None else ""
            if not user_id:
                missing_by_field[args.id_col] += 1
                dropped += 1
                continue
            if user_id in seen_ids:
                raise ValueError(f"Duplicate user ID at line {line_no}: {user_id}")
            seen_ids.add(user_id)

            parsed = {}
            row_invalid = False
            for name in [args.treatment_col] + covariates + ([args.outcome_col] if args.outcome_col else []):
                value = raw.get(name)
                if value is None or not str(value).strip():
                    missing_by_field[name] += 1
                    row_invalid = True
                    continue
                try:
                    if name == args.treatment_col:
                        parsed[name] = int(value)
                        if parsed[name] not in (0, 1):
                            raise ValueError
                    else:
                        parsed[name] = float(value)
                        if not math.isfinite(parsed[name]):
                            raise ValueError
                except (TypeError, ValueError):
                    invalid_by_field[name] += 1
                    row_invalid = True
            if row_invalid:
                dropped += 1
                continue
            kept.append(
                {
                    "id": user_id,
                    "t": parsed[args.treatment_col],
                    "x": [parsed[name] for name in covariates],
                    "outcome": parsed[args.outcome_col] if args.outcome_col else None,
                }
            )
    if total_rows == 0:
        raise ValueError("Input CSV contains no data rows")
    rates = {
        name: (missing_by_field[name] + invalid_by_field[name]) / total_rows
        for name in required
    }
    invalid_keys = [name for name in (args.id_col, args.treatment_col) if rates[name] > 0]
    if invalid_keys:
        detail = ", ".join(f"{name}={rates[name]:.1%}" for name in invalid_keys)
        raise ValueError(f"Identity and treatment fields must be complete and valid: {detail}")
    excessive = [name for name in covariates if rates[name] > args.max_covariate_missing_rate]
    if excessive:
        detail = ", ".join(f"{name}={rates[name]:.1%}" for name in excessive)
        raise ValueError(
            "Covariate missing-or-invalid rate exceeds "
            f"{args.max_covariate_missing_rate:.1%}: {detail}"
        )
    if len(kept) < 4:
        raise ValueError("Fewer than four complete rows remain")
    if sum(row["t"] for row in kept) < 2 or sum(1 - row["t"] for row in kept) < 2:
        raise ValueError("Treatment and control groups must each contain at least two users")
    return kept, {
        "rows_total": total_rows,
        "rows_dropped_missing_or_invalid": dropped,
        "missing_by_field": missing_by_field,
        "invalid_by_field": invalid_by_field,
        "missing_or_invalid_rate_by_field": rates,
        "max_covariate_missing_rate": args.max_covariate_missing_rate,
    }


def standardize(rows):
    width = len(rows[0]["x"])
    means = [statistics.fmean(row["x"][j] for row in rows) for j in range(width)]
    scales = []
    for j in range(width):
        values = [row["x"][j] for row in rows]
        scale = statistics.pstdev(values)
        scales.append(scale if scale > EPS else 1.0)
    matrix = [[1.0] + [(row["x"][j] - means[j]) / scales[j] for j in range(width)] for row in rows]
    return matrix


def logistic_loss(beta, matrix, labels, l2):
    probs = [sigmoid(sum(b * x for b, x in zip(beta, row))) for row in matrix]
    return -sum(
        y * math.log(max(p, EPS)) + (1 - y) * math.log(max(1 - p, EPS))
        for y, p in zip(labels, probs)
    ) / len(labels) + 0.5 * l2 * sum(b * b for b in beta[1:])


def fit_logistic(matrix, labels, max_iterations, learning_rate, l2):
    width = len(matrix[0])
    beta = [0.0] * width
    previous_loss = logistic_loss(beta, matrix, labels, l2)
    for iteration in range(1, max_iterations + 1):
        probs = [sigmoid(sum(b * x for b, x in zip(beta, row))) for row in matrix]
        gradient = [0.0] * width
        for row, label, prob in zip(matrix, labels, probs):
            for j, value in enumerate(row):
                gradient[j] += (prob - label) * value
        n = len(labels)
        for j in range(width):
            penalty = 0.0 if j == 0 else l2 * beta[j]
            beta[j] -= learning_rate * (gradient[j] / n + penalty)
        if not all(math.isfinite(value) for value in beta):
            raise ValueError("Logistic regression produced non-finite coefficients")
        loss = logistic_loss(beta, matrix, labels, l2)
        if not math.isfinite(loss):
            raise ValueError("Logistic regression produced a non-finite loss")
        if abs(previous_loss - loss) < 1e-9:
            return beta, iteration, loss, True
        previous_loss = loss
    return beta, max_iterations, previous_loss, False


def match_rows(rows, ratio, caliper_multiplier, with_replacement):
    treated = [i for i, row in enumerate(rows) if row["t"] == 1 and row["in_support"]]
    controls = [i for i, row in enumerate(rows) if row["t"] == 0 and row["in_support"]]
    pooled_logits = [rows[i]["logit"] for i in treated + controls]
    caliper = caliper_multiplier * statistics.pstdev(pooled_logits)
    if caliper <= EPS:
        raise ValueError("Propensity logits have no usable variation")
    candidates = {
        i: sorted((abs(rows[i]["logit"] - rows[j]["logit"]), j) for j in controls)
        for i in treated
    }
    treated.sort(key=lambda i: candidates[i][0][0] if candidates[i] else float("inf"), reverse=True)
    used, pairs = set(), []
    for ti in treated:
        selected = []
        for distance, ci in candidates[ti]:
            if distance > caliper:
                break
            if not with_replacement and ci in used:
                continue
            selected.append((distance, ci))
            if len(selected) == ratio:
                break
        if len(selected) != ratio:
            continue
        for distance, ci in selected:
            pairs.append((ti, ci, distance, 1.0 / ratio))
            if not with_replacement:
                used.add(ci)
    return pairs, caliper, len(treated), len(controls)


def balance(rows, covariates, pairs):
    before_t = [row for row in rows if row["t"] == 1]
    before_c = [row for row in rows if row["t"] == 0]
    treated_ids = sorted(set(ti for ti, _, _, _ in pairs))
    after_t = [rows[i] for i in treated_ids]
    after_c = [rows[ci] for _, ci, _, _ in pairs]
    control_weights = [weight for _, _, _, weight in pairs]
    result = {}
    for j, name in enumerate(covariates):
        result[name] = {
            "smd_before": smd([r["x"][j] for r in before_t], [r["x"][j] for r in before_c]),
            "smd_after": smd(
                [r["x"][j] for r in after_t],
                [r["x"][j] for r in after_c],
                [1.0] * len(after_t),
                control_weights,
            ),
        }
    result["propensity_score"] = {
        "smd_before": smd([r["score"] for r in before_t], [r["score"] for r in before_c]),
        "smd_after": smd(
            [r["score"] for r in after_t],
            [r["score"] for r in after_c],
            [1.0] * len(after_t),
            control_weights,
        ),
    }
    return result


def estimate_att(rows, pairs, with_replacement):
    grouped = {}
    for ti, ci, _, _ in pairs:
        grouped.setdefault(ti, []).append(ci)
    effects = []
    for ti, controls in grouped.items():
        control_mean = statistics.fmean(rows[ci]["outcome"] for ci in controls)
        effects.append(rows[ti]["outcome"] - control_mean)
    att = statistics.fmean(effects)
    se = None
    uncertainty_note = None
    if with_replacement:
        uncertainty_note = (
            "Not reported: reused controls make matched-set effects dependent; "
            "use a dependence-aware bootstrap or cluster-robust method."
        )
    elif len(effects) > 1:
        se = statistics.stdev(effects) / math.sqrt(len(effects))
    treated_mean = statistics.fmean(rows[ti]["outcome"] for ti in grouped)
    control_mean = statistics.fmean(
        statistics.fmean(rows[ci]["outcome"] for ci in controls)
        for controls in grouped.values()
    )
    return {
        "att": att,
        "treated_mean": treated_mean,
        "matched_control_mean": control_mean,
        "relative_lift": att / control_mean if abs(control_mean) > EPS else None,
        "standard_error_approx": se,
        "ci95_approx": [att - 1.96 * se, att + 1.96 * se] if se is not None else None,
        "uncertainty_note": uncertainty_note,
    }


def finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: finite_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite_json(v) for v in value]
    return value


def main():
    args = parse_args()
    if args.ratio < 1:
        raise ValueError("--ratio must be at least 1")
    if args.caliper <= 0:
        raise ValueError("--caliper must be positive")
    if args.max_iterations < 1:
        raise ValueError("--max-iterations must be at least 1")
    if args.learning_rate <= 0:
        raise ValueError("--learning-rate must be positive")
    if args.l2 < 0:
        raise ValueError("--l2 must be non-negative")
    if not 0 <= args.max_covariate_missing_rate <= 1:
        raise ValueError("--max-covariate-missing-rate must be between 0 and 1")
    covariates = [name.strip() for name in args.covariates.split(",") if name.strip()]
    if not covariates:
        raise ValueError("At least one covariate is required")
    if len(set(covariates)) != len(covariates):
        raise ValueError("Covariate names must be unique")
    prohibited_covariates = {args.id_col, args.treatment_col}
    if args.outcome_col:
        prohibited_covariates.add(args.outcome_col)
    overlap = sorted(set(covariates) & prohibited_covariates)
    if overlap:
        raise ValueError("Identifiers, treatment, and outcome cannot be covariates: " + ", ".join(overlap))
    rows, input_quality = load_rows(args, covariates)
    matrix = standardize(rows)
    labels = [row["t"] for row in rows]
    beta, iterations, loss, converged = fit_logistic(
        matrix, labels, args.max_iterations, args.learning_rate, args.l2
    )
    if not converged:
        raise ValueError(
            "Logistic regression did not converge within "
            f"{args.max_iterations} iterations; review scaling or solver settings"
        )
    for row, vector in zip(rows, matrix):
        row["score"] = sigmoid(sum(b * x for b, x in zip(beta, vector)))
        row["logit"] = logit(row["score"])
    t_scores = [row["score"] for row in rows if row["t"] == 1]
    c_scores = [row["score"] for row in rows if row["t"] == 0]
    support_low = max(min(t_scores), min(c_scores))
    support_high = min(max(t_scores), max(c_scores))
    if support_low >= support_high:
        raise ValueError("No common propensity-score support between groups")
    for row in rows:
        row["in_support"] = support_low <= row["score"] <= support_high
    pairs, caliper, eligible_t, eligible_c = match_rows(
        rows, args.ratio, args.caliper, args.with_replacement
    )
    matched_t = len(set(ti for ti, _, _, _ in pairs))
    if not pairs:
        raise ValueError("No matches found within the caliper")
    diagnostics = balance(rows, covariates, pairs)
    max_after = max(abs(item["smd_after"]) for item in diagnostics.values())
    report = {
        "input": {
            **input_quality,
            "rows_complete": len(rows),
            "treated": sum(row["t"] for row in rows),
            "control": sum(1 - row["t"] for row in rows),
            "covariates": covariates,
        },
        "model": {
            "type": "logistic_regression_l2",
            "iterations": iterations,
            "converged": converged,
            "loss": loss,
            "coefficients": {"intercept": beta[0], **dict(zip(covariates, beta[1:]))},
        },
        "matching": {
            "estimand": "ATT",
            "ratio": args.ratio,
            "with_replacement": args.with_replacement,
            "caliper_logit": caliper,
            "common_support": [support_low, support_high],
            "eligible_treated": eligible_t,
            "eligible_control": eligible_c,
            "matched_treated": matched_t,
            "matched_pairs": len(pairs),
            "treated_match_rate": matched_t / sum(row["t"] for row in rows),
        },
        "balance": diagnostics,
        "quality": {
            "max_abs_smd_after": max_after,
            "balanced_at_0_10": max_after < 0.10,
            "match_rate_at_least_0_70": matched_t / sum(row["t"] for row in rows) >= 0.70,
        },
    }
    if args.outcome_col:
        report["effect"] = estimate_att(rows, pairs, args.with_replacement)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pair_counts = {}
    for ti, _, _, _ in pairs:
        pair_counts[ti] = pair_counts.get(ti, 0) + 1
    with open(output_dir / "matched_pairs.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["treated_user_id", "control_user_id", "distance_logit", "control_weight"])
        for ti, ci, distance, weight in pairs:
            writer.writerow([rows[ti]["id"], rows[ci]["id"], distance, weight])
    with open(output_dir / "scored_users.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "treatment", "propensity_score", "in_common_support", "matched"])
        matched_indices = set(i for pair in pairs for i in pair[:2])
        for i, row in enumerate(rows):
            writer.writerow([row["id"], row["t"], row["score"], int(row["in_support"]), int(i in matched_indices)])
    with open(output_dir / "report.json", "w", encoding="utf-8") as handle:
        json.dump(finite_json(report), handle, ensure_ascii=False, indent=2)
    print(json.dumps(finite_json(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
