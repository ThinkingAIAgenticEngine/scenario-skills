"""Ranking and probability diagnostics on an independent labeled snapshot.

The caller supplies probabilities, not arbitrary ranking scores. Tied scores
keep input order. Capacity selects min(K, contact-eligible users); probability
metrics still describe the entire labeled population.
"""
from numbers import Integral

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score


def _positive_integer(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _probabilities(values):
    try:
        probabilities = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("probabilities must be a one-dimensional numeric array") from exc
    if probabilities.ndim != 1:
        raise ValueError("probabilities must be one-dimensional")
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("probabilities must be finite and between 0 and 1")
    return probabilities


def select_top_k(probabilities, top_k):
    """Return ranked input positions, preserving input order for tied scores.

    An empty eligible population yields an empty array. Evaluation, in contrast,
    requires a nonempty population because its rates would be undefined.
    """
    top_k = _positive_integer(top_k, "top_k")
    probabilities = _probabilities(probabilities)
    return np.argsort(-probabilities, kind="mergesort")[:top_k]


def contact_mask(values, size):
    if values is None:
        return np.ones(size, dtype=bool)
    mask = np.asarray(values)
    if mask.ndim != 1 or len(mask) != size or mask.dtype.kind != "b":
        raise ValueError("contact_eligible must contain one boolean per row")
    return mask


def evaluate_predictions(y_true, probabilities, top_k=500, n_bins=10, user_ids=None,
                         contact_eligible=None):
    """Return JSON-safe discrimination, Top-K and calibration diagnostics.

    Single-class snapshots still have Brier/log-loss and observed rates, but
    AUC/AP are reported as unavailable. Reliability bins and ECE are descriptive
    diagnostics; small samples do not establish that probabilities are reliable.
    When IDs are supplied, tied scores use ascending string IDs, matching the
    operational candidate exporter regardless of the input row order.
    """
    top_k = _positive_integer(top_k, "top_k")
    n_bins = _positive_integer(n_bins, "n_bins")
    probabilities = _probabilities(probabilities)
    try:
        labels = np.asarray(y_true, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("y_true must contain complete binary labels (0 or 1)") from exc
    if labels.ndim != 1 or len(labels) != len(probabilities) or len(labels) == 0:
        raise ValueError("labels and probabilities must be nonempty one-dimensional arrays of equal length")
    if not np.isfinite(labels).all() or not np.isin(labels, [0, 1]).all():
        raise ValueError("y_true must contain complete binary labels (0 or 1)")
    labels = labels.astype(int)
    eligible = contact_mask(contact_eligible, len(labels))
    if user_ids is None:
        positions = np.flatnonzero(eligible)
        selected = positions[select_top_k(probabilities[positions], top_k)]
        tie_breaker = "input_order"
    else:
        identifiers = np.asarray(user_ids, dtype=object)
        if identifiers.ndim != 1 or len(identifiers) != len(labels) or pd.isna(identifiers).any():
            raise ValueError("user_ids must contain one non-null ID per evaluated row")
        identifiers = identifiers.astype(str)
        if len(np.unique(identifiers)) != len(identifiers):
            raise ValueError("user_ids must be unique within the evaluation snapshot")
        order = np.argsort(identifiers, kind="stable")
        order = order[eligible[order]]
        selected = order[select_top_k(probabilities[order], top_k)]
        tie_breaker = "user_id ascending"
    positives = int(labels.sum())
    base_rate = float(labels.mean())
    hits = int(labels[selected].sum())
    precision = float(hits / len(selected)) if len(selected) else None
    metrics = {
        "users": int(len(labels)),
        "positives": positives,
        "base_rate": base_rate,
        "roc_auc": None,
        "pr_auc": None,
        "brier_score": float(np.mean((probabilities - labels) ** 2)),
        "log_loss": float(log_loss(labels, probabilities, labels=[0, 1])),
        "top_k": {
            "requested": top_k,
            "selected": int(len(selected)),
            "positives": hits,
            "precision": precision,
            "recall": float(hits / positives) if positives else None,
            "lift": float(precision / base_rate) if positives and precision is not None else None,
            "threshold": float(probabilities[selected[-1]]) if len(selected) else None,
            "tie_breaker": tie_breaker,
        },
    }
    if len(np.unique(labels)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(labels, probabilities))
        metrics["pr_auc"] = float(average_precision_score(labels, probabilities))
    else:
        metrics["reason"] = "only one label class; AUC/PR-AUC unavailable"

    # Equal-width bins include probability 1 in the final bin.
    assignments = np.minimum((probabilities * n_bins).astype(int), n_bins - 1)
    bins = []
    ece = 0.0
    for i in range(n_bins):
        mask = assignments == i
        count = int(mask.sum())
        mean_probability = float(probabilities[mask].mean()) if count else None
        observed_rate = float(labels[mask].mean()) if count else None
        gap = abs(mean_probability - observed_rate) if count else None
        if count:
            ece += count / len(labels) * gap
        bins.append({"lower": float(i / n_bins), "upper": float((i + 1) / n_bins),
                     "count": count, "mean_probability": mean_probability,
                     "observed_rate": observed_rate, "absolute_gap": gap})
    metrics["calibration"] = {"n_bins": n_bins, "bins": bins, "ece": float(ece)}
    return metrics
