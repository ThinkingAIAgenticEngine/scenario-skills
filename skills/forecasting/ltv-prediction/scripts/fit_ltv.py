#!/usr/bin/env python3
"""Fit a shifted exponential curve to cumulative cohort LTV observations."""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Sequence


def parse_points(raw: str) -> tuple[list[float], list[float]]:
    value = json.loads(raw)
    if not isinstance(value, list) or len(value) < 4:
        raise ValueError("points must be a JSON array with at least four [day, ltv] pairs")

    pairs: list[tuple[float, float]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("each point must be [day, ltv]")
        day, ltv = float(item[0]), float(item[1])
        if not math.isfinite(day) or not math.isfinite(ltv):
            raise ValueError("day and ltv values must be finite")
        if day < 0 or ltv < 0:
            raise ValueError("day and ltv values must be non-negative")
        pairs.append((day, ltv))

    pairs.sort()
    days = [item[0] for item in pairs]
    if len(set(days)) != len(days):
        raise ValueError("day values must be unique")
    values = [item[1] for item in pairs]
    if any(current > following for current, following in zip(values, values[1:])):
        raise ValueError("cumulative LTV values must be non-decreasing by day")
    return days, values


def fit_ltv(days: Sequence[float], values: Sequence[float]) -> dict[str, object]:
    try:
        import numpy as np
        from scipy.optimize import curve_fit
    except ImportError as error:
        raise RuntimeError(
            "numpy and scipy are required; create the skill-local .venv after user approval"
        ) from error

    x = np.asarray(days, dtype=float)
    y = np.asarray(values, dtype=float)

    def shifted_decay(n, ltv_base, ltv_gain, decay):
        return ltv_base + ltv_gain * (1 - np.exp(-decay * n))

    initial_gain = max(float(y.max()) * 1.2 - float(y[0]), 1e-6)
    params, covariance = curve_fit(
        shifted_decay,
        x,
        y,
        p0=[float(y[0]), initial_gain, 0.06],
        bounds=([0.0, 0.0, 1e-9], [math.inf, math.inf, math.inf]),
        maxfev=20_000,
    )
    ltv_base, ltv_gain, decay = (float(item) for item in params)
    ltv_inf = ltv_base + ltv_gain
    fitted = shifted_decay(x, *params)
    residuals = y - fitted
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = None if ss_tot == 0 else 1 - ss_res / ss_tot
    mae = float(np.mean(np.abs(residuals)))

    prediction_days = [60, 90, 180, 365]
    predictions = {
        f"D{day}": round(float(shifted_decay(day, *params)), 6)
        for day in prediction_days
    }

    return {
        "model": "shifted_exponential",
        "parameters": {
            "ltv_base": round(ltv_base, 6),
            "ltv_inf": round(ltv_inf, 6),
            "decay": round(decay, 9),
        },
        "quality": {
            "r_squared": None if r_squared is None else round(r_squared, 6),
            "mae": round(mae, 6),
            "point_count": len(days),
        },
        "predictions": predictions,
        "half_life_days": round(math.log(2) / decay, 6),
        "steady_state_90pct_days": round(-math.log(0.1) / decay, 6),
        "covariance": {
            "parameter_order": ["ltv_base", "ltv_gain", "decay"],
            "matrix": covariance.tolist(),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fit cumulative LTV points with a shifted exponential curve."
    )
    parser.add_argument(
        "--points",
        required=True,
        help='JSON array such as [[0,1.2],[1,1.8],[3,2.4],[7,3.1],[14,3.8],[30,4.5]]',
    )
    parser.add_argument(
        "--output",
        choices=("json", "pretty"),
        default="pretty",
        help="Output JSON formatting.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        days, values = parse_points(args.points)
        result = fit_ltv(days, values)
    except (ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    indent = 2 if args.output == "pretty" else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
