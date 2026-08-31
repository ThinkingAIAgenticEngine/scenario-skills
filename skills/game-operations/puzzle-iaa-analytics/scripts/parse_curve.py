#!/usr/bin/env python3
"""
Retention/revenue curve knee-point detection script.

Input: JSON (x, y) data points
Output: knee point position and confidence

Usage:
  python3 parse_curve.py --input data.json --x-col ad_count --y-col retention_rate --output knee.json
"""

import json
import argparse
import sys


def detect_knee(points: list[dict], x_key: str, y_key: str) -> dict:
    """
    Detect the "elbow" knee point of a curve.

    Algorithm: For sorted data points, compute the straight-line distance
    from first to last point. The knee is defined as the point with the
    maximum perpendicular distance to that line.

    Returns:
      {
        "knee_x": knee point x value,
        "knee_y": knee point y value,
        "knee_index": knee point array index,
        "confidence": 0.0-1.0,
        "method": "max_perpendicular_distance"
      }
    """

    if len(points) < 3:
        return {
            "knee_x": None,
            "knee_y": None,
            "knee_index": None,
            "confidence": 0.0,
            "method": "max_perpendicular_distance",
            "error": "Need at least 3 data points"
        }

    # Sort by x
    sorted_points = sorted(points, key=lambda p: p[x_key])
    xs = [p[x_key] for p in sorted_points]
    ys = [p[y_key] for p in sorted_points]

    # First-to-last point line
    x1, y1 = xs[0], ys[0]
    x2, y2 = xs[-1], ys[-1]

    # Line segment length
    line_len = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if line_len == 0:
        return {
            "knee_x": None, "knee_y": None, "knee_index": None,
            "confidence": 0.0,
            "method": "max_perpendicular_distance",
            "error": "First and last points coincide, cannot detect knee"
        }

    # Compute perpendicular distance from each point to the line
    max_dist = 0
    knee_idx = 0
    for i in range(1, len(points) - 1):
        # Point-to-line distance = |(x2-x1)(y1-yi) - (x1-xi)(y2-y1)| / line_len
        dist = abs((x2 - x1) * (y1 - ys[i]) - (x1 - xs[i]) * (y2 - y1)) / line_len
        if dist > max_dist:
            max_dist = dist
            knee_idx = i

    # Confidence = knee distance / y-value range (normalized)
    y_range = max(ys) - min(ys)
    if y_range > 0:
        confidence = min(max_dist / y_range, 1.0)
    else:
        confidence = 0.0

    return {
        "knee_x": xs[knee_idx],
        "knee_y": ys[knee_idx],
        "knee_index": knee_idx,
        "confidence": round(confidence, 4),
        "method": "max_perpendicular_distance",
        "all_points": [
            {"x": xs[i], "y": ys[i], "distance": round(
                abs((x2 - x1) * (y1 - ys[i]) - (x1 - xs[i]) * (y2 - y1)) / line_len, 4
            ) if i > 0 and i < len(points) - 1 else 0.0}
            for i in range(len(points))
        ]
    }


def detect_drop_point(points: list[dict], x_key: str, y_key: str, threshold: float = 0.15) -> dict:
    """
    Detect the first point where retention drops by more than threshold.

    Starting from the highest retention point, find the first point where
    the drop exceeds the threshold.

    Returns:
      {
        "drop_x": drop point x value,
        "drop_y": y value after drop,
        "prev_y": y value before drop,
        "drop_pct": drop percentage
      }
    """

    if len(points) < 2:
        return {"drop_x": None, "drop_y": None, "error": "Need at least 2 data points"}

    sorted_points = sorted(points, key=lambda p: p[x_key])

    # Find the point with highest y
    max_y = max(p[y_key] for p in sorted_points)
    max_idx = next(i for i, p in enumerate(sorted_points) if p[y_key] == max_y)

    # From the peak, find the first significant drop
    for i in range(max_idx + 1, len(sorted_points)):
        drop_pct = (sorted_points[max_idx][y_key] - sorted_points[i][y_key]) / sorted_points[max_idx][y_key]
        if drop_pct >= threshold:
            return {
                "drop_x": sorted_points[i][x_key],
                "drop_y": sorted_points[i][y_key],
                "prev_x": sorted_points[max_idx][x_key],
                "prev_y": sorted_points[max_idx][y_key],
                "drop_pct": round(drop_pct, 4),
                "method": "first_significant_drop"
            }

    return {
        "drop_x": None, "drop_y": None,
        "method": "first_significant_drop",
        "message": f"No drop exceeding {threshold*100}% found"
    }


def find_optimal_range(points: list[dict], x_key: str, y_key: str) -> dict:
    """
    Find the x-range where y values are highest (optimal interval).

    If multiple points have y values within 5% of the max, return the range.
    """

    if not points:
        return {"optimal_min": None, "optimal_max": None, "error": "No data"}

    sorted_points = sorted(points, key=lambda p: p[x_key])
    max_y = max(p[y_key] for p in sorted_points)

    # Find all points with y within 5% of the max
    near_optimal = [p for p in sorted_points if p[y_key] >= max_y * 0.95]

    return {
        "optimal_min_x": near_optimal[0][x_key],
        "optimal_max_x": near_optimal[-1][x_key],
        "optimal_max_y": max_y,
        "points_in_range": len(near_optimal),
        "total_points": len(points),
        "method": "top_5pct_range"
    }


def main():
    parser = argparse.ArgumentParser(description="Knee point detection")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--x-col", required=True, help="X-axis field name")
    parser.add_argument("--y-col", required=True, help="Y-axis field name")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--threshold", type=float, default=0.15,
                        help="Drop detection threshold, default 0.15 (15%%)")
    args = parser.parse_args()

    try:
        with open(args.input, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Cannot read input file: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure data is a list
    if isinstance(data, dict):
        # Try to extract data from common keys
        if "points" in data:
            data = data["points"]
        elif "data" in data:
            data = data["data"]
        elif "rows" in data:
            data = data["rows"]
        else:
            data = [data]

    if not isinstance(data, list) or len(data) == 0:
        print("ERROR: Input data is empty or has incorrect format", file=sys.stderr)
        sys.exit(1)

    # Ensure every point has x_key and y_key
    for i, point in enumerate(data):
        if args.x_col not in point or args.y_col not in point:
            print(f"ERROR: Data point {i} missing field {args.x_col} or {args.y_col}", file=sys.stderr)
            sys.exit(1)

    results = {
        "input_file": args.input,
        "x_col": args.x_col,
        "y_col": args.y_col,
        "total_points": len(data),
        "knee": detect_knee(data, args.x_col, args.y_col),
        "drop_point": detect_drop_point(data, args.x_col, args.y_col, args.threshold),
        "optimal_range": find_optimal_range(data, args.x_col, args.y_col),
    }

    with open(args.output, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"Knee detection complete ({len(data)} data points)")
    knee = results["knee"]
    if knee.get("knee_x") is not None:
        print(f"  Elbow knee: x={knee['knee_x']}, y={knee['knee_y']}, confidence={knee['confidence']}")
    else:
        print(f"  Elbow knee: {knee.get('error', 'Not detected')}")

    drop = results["drop_point"]
    if drop.get("drop_x") is not None:
        print(f"  First significant drop: x={drop['drop_x']}, drop={drop['drop_pct']*100:.1f}%")
    else:
        print(f"  First significant drop: {drop.get('message', drop.get('error', 'Not detected'))}")

    optimal = results["optimal_range"]
    if optimal.get("optimal_min_x") is not None:
        print(f"  Optimal range: {optimal['optimal_min_x']} - {optimal['optimal_max_x']}")


if __name__ == "__main__":
    main()
