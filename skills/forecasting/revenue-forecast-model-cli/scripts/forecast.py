#!/usr/bin/env python3
"""
Revenue Forecast Engine — Game Dynamic Revenue Prediction Model
===============================================================
Core algorithm implementing forward prediction, reverse calculation,
retention curve fitting, LTV estimation, and dual-drive optimization.

Usage:
  python3 forecast.py forward --initial-dau 50000 --daily-dnu 2000 ...
  python3 forecast.py reverse-dnu ...
  python3 forecast.py reverse-arpu ...
  python3 forecast.py fit-retention ...
  python3 forecast.py dual-drive ...
"""

import argparse
import json
import sys
from typing import List, Tuple, Optional

import numpy as np
from scipy.optimize import curve_fit

# ============================================================================
# Retention Curve Model
# ============================================================================

def retention_log_func(t: float, a: float, b: float) -> float:
    """
    Logarithmic retention model: R(t) = a * ln(t + 1) + b
    This is the standard curve-fitting model widely used in game analytics.
    """
    return a * np.log(t + 1) + b

def retention_log_func_clamped(t: float, a: float, b: float) -> float:
    """Log retention model clamped to non-negative."""
    return max(0, a * np.log(t + 1) + b)

def retention_power_func(t: float, alpha: float, beta: float) -> float:
    """
    Power-law retention model: R(t) = alpha * t^beta
    Often provides better fit for long-tail retention.
    """
    return alpha * (t ** beta)

def retention_power_func_clamped(t: float, alpha: float, beta: float) -> float:
    """Power-law retention model clamped to non-negative."""
    return max(0, alpha * (t ** beta))

def fit_retention_curve(
    points: List[Tuple[float, float]],
    model: str = "log"
) -> Tuple[callable, dict]:
    """
    Fit a retention curve from known data points.
    
    Args:
        points: List of (day, retention_rate) tuples, e.g. [(1,0.42), (7,0.15), ...]
        model: 'log' for logarithmic, 'power' for power-law
    
    Returns:
        (fitted_function, parameters_dict)
    """
    days = np.array([p[0] for p in points], dtype=float)
    rates = np.array([p[1] for p in points], dtype=float)
    
    if model == "log":
        try:
            popt, _ = curve_fit(retention_log_func, days, rates, maxfev=10000)
        except RuntimeError:
            # Fallback: use simple linear regression on log-transformed data
            ln_days = np.log(days + 1)
            A = np.vstack([ln_days, np.ones_like(ln_days)]).T
            b_coeff, a_coeff = np.linalg.lstsq(A, rates, rcond=None)[0]
            a, b = a_coeff, b_coeff
        a, b = popt if 'popt' in dir() else (a, b)
        # Use clamped version to prevent negative predictions
        def fitted(t):
            return retention_log_func_clamped(t, a, b)
        return fitted, {"a": round(a, 6), "b": round(b, 6), "model": "log"}
    
    elif model == "power":
        try:
            popt, _ = curve_fit(retention_power_func, days, rates, maxfev=10000)
        except RuntimeError:
            # Fallback: linear regression on log-log scale
            log_days = np.log(days)
            log_rates = np.log(rates)
            A = np.vstack([log_days, np.ones_like(log_days)]).T
            beta_c, log_alpha = np.linalg.lstsq(A, log_rates, rcond=None)[0]
            alpha, beta = np.exp(log_alpha), beta_c
        alpha, beta = popt if 'popt' in dir() else (alpha, beta)
        def fitted(t):
            return retention_power_func_clamped(t, alpha, beta)
        return fitted, {"alpha": round(alpha, 6), "beta": round(beta, 6), "model": "power"}
    
    raise ValueError(f"Unknown model type: {model}")

# ============================================================================
# Forward Prediction — DAU Daily Roll + Revenue
# ============================================================================

def forward_forecast(
    initial_dau: float,
    daily_dnu: float,
    arpu: float,
    daily_churn_rate: float,
    days: int,
    dnu_growth_fn: Optional[callable] = None,
    arpu_growth_fn: Optional[callable] = None,
) -> dict:
    """
    Forward revenue prediction using daily DAU iteration.
    
    Core formula per day:
        today_DAU = yesterday_DAU + today_DNU - today_Churned
        today_Churned = yesterday_DAU * daily_churn_rate
        today_Revenue = today_DAU * ARPU
    
    Args:
        initial_dau: Starting DAU on day 0
        daily_dnu: Daily new users (constant or base value)
        arpu: Average revenue per daily user (constant or base value)
        daily_churn_rate: Fraction of users who churn each day (1 / avg LT)
        days: Number of days to forecast
        dnu_growth_fn: Optional function(day) -> DNU for that day (e.g., ramp-up)
        arpu_growth_fn: Optional function(day) -> ARPU for that day (e.g., event lift)
    
    Returns:
        dict with daily_snapshot and monthly aggregation
    """
    daus = [initial_dau]
    revenues = []
    dnus_used = []
    arpus_used = []
    
    for day in range(1, days + 1):
        prev_dau = daus[-1]
        
        # Dynamic DNU
        dnu_today = daily_dnu if dnu_growth_fn is None else dnu_growth_fn(day)
        
        # Dynamic ARPU
        arpu_today = arpu if arpu_growth_fn is None else arpu_growth_fn(day)
        
        # Churn calculation
        churned_today = prev_dau * daily_churn_rate
        
        # DAU iteration
        dau_today = max(prev_dau + dnu_today - churned_today, 0)
        revenue_today = dau_today * arpu_today
        
        daus.append(dau_today)
        revenues.append(revenue_today)
        dnus_used.append(dnu_today)
        arpus_used.append(arpu_today)
    
    # Build daily snapshot (day 1..days)
    daily = []
    for d in range(1, days + 1):
        daily.append({
            "day": d,
            "dau": round(daus[d], 0),
            "dnu": round(dnus_used[d - 1], 0),
            "arpu": round(arpus_used[d - 1], 2),
            "revenue": round(revenues[d - 1], 2),
        })
    
    # Monthly aggregation
    monthly = {}
    for d in range(1, days + 1):
        month = (d - 1) // 30 + 1
        if month not in monthly:
            monthly[month] = {"revenue": 0, "dau_sum": 0, "count": 0, "arpu_sum": 0}
        monthly[month]["revenue"] += revenues[d - 1]
        monthly[month]["dau_sum"] += daus[d]
        monthly[month]["count"] += 1
        monthly[month]["arpu_sum"] += arpus_used[d - 1]
    
    monthly_report = []
    for m in sorted(monthly.keys()):
        data = monthly[m]
        monthly_report.append({
            "month": m,
            "revenue": round(data["revenue"], 2),
            "avg_dau": round(data["dau_sum"] / data["count"], 0),
            "avg_arpu": round(data["arpu_sum"] / data["count"], 2),
            "days": data["count"],
        })
    
    return {
        "daily_snapshot": daily,
        "monthly_revenue": monthly_report,
        "cumulative_180d_revenue": round(sum(revenues), 2),
        "final_day_dau": round(daus[-1], 0),
    }

# ============================================================================
# Reverse — Solve for DNU (target DAU → required DNU)
# ============================================================================

def solve_dnu(
    initial_dau: float,
    current_arpu: float,
    target_daily_revenue: float,
    daily_churn_rate: float,
    days: int,
) -> dict:
    """
    Reverse-calculate the DNU needed to achieve a target daily revenue.
    
    Logic:
        1. Target DAU = target_daily_revenue / ARPU
        2. At steady state: target_DAU = DNU / daily_churn_rate
        3. DNU = target_DAU * daily_churn_rate
        But we also account for ramp-up period (DNU needs to start earlier).
        
    More precise: run forward simulation with varying DNU to find the right value.
    """
    target_dau = target_daily_revenue / current_arpu
    
    # Steady-state DNU: at equilibrium, DAU = DNU / churn_rate
    steady_dnu = target_dau * daily_churn_rate
    
    # Natural DAU at day 180 with current DNU (assuming current DNU is not known,
    # we solve for steady state)
    # For a more precise answer, we binary-search the DNU that produces target DAU
    lo, hi = 0, target_dau * 2
    best_dnu = steady_dnu
    best_error = float('inf')
    
    for _ in range(50):
        mid = (lo + hi) / 2
        # Simulate
        result = forward_forecast(initial_dau, mid, current_arpu, daily_churn_rate, days)
        end_dau = result["final_day_dau"]
        end_revenue = result["daily_snapshot"][-1]["revenue"]
        error = abs(end_revenue - target_daily_revenue) / target_daily_revenue
        
        if error < best_error:
            best_error = error
            best_dnu = mid
        
        if end_revenue < target_daily_revenue:
            lo = mid
        else:
            hi = mid
    
    # Generate a DNU ramp schedule (recommended: gradual ramp over 60 days)
    ramp_days = min(60, days)
    def dnu_ramp(day: int):
        if day <= ramp_days:
            return best_dnu * (day / ramp_days)
        return best_dnu
    
    ramp_result = forward_forecast(
        initial_dau, best_dnu, current_arpu, daily_churn_rate, days,
        dnu_growth_fn=dnu_ramp
    )
    
    return {
        "required_dnu_per_day": round(best_dnu, 0),
        "target_dau": round(target_dau, 0),
        "target_daily_revenue": target_daily_revenue,
        "steady_state_dnu": round(steady_dnu, 0),
        "ramp_days": ramp_days,
        "recommendation": (
            f"Requires daily new users ≈ {round(best_dnu):,.0f}. Ramp up over {ramp_days} days; "
            f"build a traffic buffer 1-2 months in advance."
        ),
        "forward_forecast_with_dnu": ramp_result,
    }

# ============================================================================
# Reverse — Solve for ARPU (target revenue → required ARPU lift)
# ============================================================================

def solve_arpu(
    initial_dau: float,
    daily_dnu: float,
    daily_churn_rate: float,
    target_daily_revenue: float,
    days: int,
) -> dict:
    """
    Reverse-calculate the ARPU needed to achieve a target daily revenue,
    assuming DNU stays constant (no UA budget increase).
    
    Logic:
        1. Run natural forward to get natural_DAU at day N
        2. Target ARPU = target_daily_revenue / natural_DAU_N
    """
    natural = forward_forecast(initial_dau, daily_dnu, 0, daily_churn_rate, days)
    # We use ARPU=0 for the run, just tracking DAU
    # Actually use a placeholder ARPU=1, then revenue = DAU*1
    natural_v2 = forward_forecast(initial_dau, daily_dnu, 1.0, daily_churn_rate, days)
    natural_dau_end = natural_v2["final_day_dau"]
    natural_snapshots = natural_v2["daily_snapshot"]
    
    target_arpu = target_daily_revenue / natural_dau_end if natural_dau_end > 0 else 0
    
    # User should provide current ARPU to compute lift
    return {
        "natural_dau_at_day_N": round(natural_dau_end, 0),
        "target_arpu": round(target_arpu, 2),
        "target_daily_revenue": target_daily_revenue,
        "natural_forecast": natural_v2,
    }

def solve_arpu_with_current(
    initial_dau: float,
    daily_dnu: float,
    current_arpu: float,
    daily_churn_rate: float,
    target_daily_revenue: float,
    days: int,
) -> dict:
    """
    Solve for ARPU lift given current ARPU baseline.
    """
    result = solve_arpu(initial_dau, daily_dnu, daily_churn_rate, target_daily_revenue, days)
    lift_pct = (result["target_arpu"] - current_arpu) / current_arpu if current_arpu > 0 else 0
    
    result["current_arpu"] = current_arpu
    result["arpu_lift_pct"] = round(lift_pct * 100, 1)
    
    if lift_pct > 0.5:
        result["recommendation"] = (
            f"ARPU lift of {round(lift_pct * 100, 1)}% required (current {current_arpu} → "
            f"target {result['target_arpu']}). Routine events cannot sustain this; plan major promotions."
        )
    elif lift_pct > 0.2:
        result["recommendation"] = (
            f"ARPU lift of {round(lift_pct * 100, 1)}% required (current {current_arpu} → "
            f"target {result['target_arpu']}). Achievable through version updates + limited-time events."
        )
    else:
        result["recommendation"] = (
            f"ARPU fine-tuning of {round(lift_pct * 100, 1)}% needed (current {current_arpu} → "
            f"target {result['target_arpu']}). Small-scale operations can cover this."
        )
    
    return result

# ============================================================================
# Dual-Drive Optimization — UA + Operations synergy
# ============================================================================

def dual_drive_optimization(
    initial_dau: float,
    current_dnu: float,
    current_arpu: float,
    daily_churn_rate: float,
    target_daily_revenue: float,
    days: int,
    arpu_lift_pct: float = 0.2,
) -> dict:
    """
    Dual-drive optimization: solve for the optimal combination of DNU increase
    and ARPU lift to hit the target revenue.
    
    The method:
        1. User proposes a realistic ARPU lift (e.g., 20%)
        2. Model computes the remaining gap to be filled by DNU
        3. Outputs the combined DNU + ARPU plan
    """
    # Step 1: Apply ARPU lift
    lifted_arpu = current_arpu * (1 + arpu_lift_pct)
    
    # Step 2: What revenue do we get at day N with current DNU + lifted ARPU?
    with_lift = forward_forecast(
        initial_dau, current_dnu, lifted_arpu, daily_churn_rate, days
    )
    revenue_with_lift = with_lift["daily_snapshot"][-1]["revenue"]
    
    # Step 3: If still below target, solve for additional DNU
    if revenue_with_lift < target_daily_revenue:
        dnu_result = solve_dnu(
            initial_dau, lifted_arpu, target_daily_revenue, daily_churn_rate, days
        )
        extra_dnu_needed = dnu_result["required_dnu_per_day"] - current_dnu
        
        recommendation = (
            f"After ARPU lift of {round(arpu_lift_pct * 100, 1)}% ({current_arpu} → {round(lifted_arpu, 2)}), "
            f"still need extra daily new users ≈ {round(extra_dnu_needed):,.0f} "
            f"(total daily new users ≈ {round(dnu_result['required_dnu_per_day']):,.0f}) to reach target."
        )
        return {
            "feasible": True,
            "arpu_lift_pct": round(arpu_lift_pct * 100, 1),
            "lifted_arpu": round(lifted_arpu, 2),
            "current_dnu": round(current_dnu, 0),
            "required_dnu_total": round(dnu_result["required_dnu_per_day"], 0),
            "required_dnu_extra": round(extra_dnu_needed, 0),
            "projected_revenue_with_lift": round(revenue_with_lift, 2),
            "target_revenue": target_daily_revenue,
            "forward_with_lift": with_lift,
            "forward_with_both": dnu_result["forward_forecast_with_dnu"],
            "recommendation": recommendation,
        }
    else:
        # Already hit target with ARPU lift alone
        recommendation = (
            f"ARPU lift of {round(arpu_lift_pct * 100, 1)}% alone ({current_arpu} → "
            f"{round(lifted_arpu, 2)}) is sufficient to reach target; no extra UA needed."
        )
        return {
            "feasible": True,
            "arpu_lift_pct": round(arpu_lift_pct * 100, 1),
            "lifted_arpu": round(lifted_arpu, 2),
            "current_dnu": round(current_dnu, 0),
            "required_dnu_extra": 0,
            "projected_revenue_with_lift": round(revenue_with_lift, 2),
            "target_revenue": target_daily_revenue,
            "forward_with_lift": with_lift,
            "recommendation": recommendation,
        }

# ============================================================================
# LTV Estimation
# ============================================================================

def estimate_ltv(
    arpu: float,
    day_1_retention: float,
    total_active_days: int = 180,
    retention_fn: Optional[callable] = None,
) -> dict:
    """
    Estimate LTV using retention-weighted active days.
    
    LTV ≈ ARPU × Σ_{t=1}^{N} R(t)
    where R(t) is the retention rate on day t.
    
    If no retention function is provided, a simple formula is used:
        LTV ≈ ARPU × (1 + day_1_retention) / (2 × daily_churn_rate)
    """
    if retention_fn is not None:
        total_active = sum(retention_fn(t) for t in range(1, total_active_days + 1))
    else:
        # Simplified: assume retention decays linearly from day_1 to 0 over LT
        lt = 1 / (1 - day_1_retention) if day_1_retention < 1 else 30
        total_active = lt
    
    ltv = arpu * total_active
    return {
        "arpu": arpu,
        "total_active_days_estimated": round(total_active, 2),
        "estimated_ltv": round(ltv, 2),
        "horizon_days": total_active_days,
    }

# ============================================================================
# CLI Interface
# ============================================================================

def parse_retention_points(raw: str) -> List[Tuple[float, float]]:
    """Parse retention points from JSON string like '[[1,0.42],[7,0.15]]'"""
    return [(float(p[0]), float(p[1])) for p in json.loads(raw)]


def derive_params(
    dau_json: str,
    dnu_json: Optional[str] = None,
    revenue_json: Optional[str] = None,
    dau_row_index: int = 0,
    window_days: int = 7,
) -> dict:
    """
    Extract DAU, DNU, ARPU, and churn rate from ae-cli query results.
    
    Accepts ae-cli JSON output with 'rows' containing daily time series.
    Row format: [date_string, value1, value2, ...]
    Handles dashboard-report-data and ad-hoc analysis output formats.
    
    Args:
        dau_json: ae-cli query result JSON string for DAU
        dnu_json: ae-cli query result JSON string for DNU (optional)
        revenue_json: ae-cli query result JSON string for revenue (optional)
        dau_row_index: column index within each row containing the DAU value
        window_days: number of recent days to average
    
    Returns:
        dict with extracted parameters and confidence estimates
    """
    def parse_ae_json(raw: str) -> list:
        """Parse ae-cli JSON and extract daily rows."""
        data = json.loads(raw)
        # Handle both dashboard and adhoc response formats
        if "reportDataList" in data.get("data", {}).get("data", {}):
            # dashboard format
            rd = data["data"]["data"]["reportDataList"][0]
            rows = rd.get("data", {}).get("rows", [])
        elif "data" in data:
            rows = data.get("data", {}).get("rows", data.get("data", {}).get("data", {}).get("rows", []))
        else:
            rows = data.get("rows", data.get("data", {}).get("rows", []))
        return [r for r in rows if r and len(r) > dau_row_index + 1 and r[0] not in ("Overview", "Phase Summary") and "-" in str(r[0])]
    
    # Parse DAU
    dau_rows = parse_ae_json(dau_json)
    if not dau_rows:
        return {"error": "Could not parse DAU data from JSON. Check format."}
    
    recent_dau = [float(r[dau_row_index + 1]) for r in dau_rows[-window_days:]]
    avg_dau = sum(recent_dau) / len(recent_dau)
    
    # Parse DNU
    avg_dnu = None
    if dnu_json:
        dnu_rows = parse_ae_json(dnu_json)
        if dnu_rows:
            recent_dnu = [float(r[dau_row_index + 1]) for r in dnu_rows[-window_days:]]
            avg_dnu = sum(recent_dnu) / len(recent_dnu)
    
    # Parse Revenue
    avg_arpu = None
    if revenue_json:
        rev_rows = parse_ae_json(revenue_json)
        if rev_rows:
            recent_rev = [float(r[dau_row_index + 1]) for r in rev_rows[-window_days:]]
            avg_rev = sum(recent_rev) / len(recent_rev)
            avg_arpu = avg_rev / avg_dau if avg_dau > 0 else 0
    
    # Churn rate from DAU + DNU
    daily_churn_rate = None
    if avg_dnu is not None:
        # At steady state: DAU ≈ DNU / churn_rate
        daily_churn_rate = avg_dnu / avg_dau if avg_dau > 0 else 0.03
    else:
        # Derive from DAU trend
        dau_changes = []
        for i in range(1, len(recent_dau)):
            change = (recent_dau[i-1] - recent_dau[i]) / recent_dau[i-1]
            dau_changes.append(max(0, change))
        daily_churn_rate = sum(dau_changes) / len(dau_changes) if dau_changes else 0.03
    
    # Cap churn rate to reasonable range
    daily_churn_rate = max(0.005, min(0.95, daily_churn_rate))
    
    result = {
        "data_source": "ae-cli",
        "window_days": window_days,
        "avg_dau": round(avg_dau, 0),
        "daily_churn_rate": round(daily_churn_rate, 4),
        "estimated_user_lifetime_days": round(1 / daily_churn_rate, 1) if daily_churn_rate > 0 else "infinite",
        "churn_derivation_method": "DNU/DAU" if avg_dnu is not None else "DAU_trend",
        "confidence": "medium",
        "recent_dau_values": [round(d, 0) for d in recent_dau],
    }
    
    if avg_dnu is not None:
        result["avg_dnu"] = round(avg_dnu, 0)
        result["suggested_dnu"] = [f"--daily-dnu {round(avg_dnu, 0)}"]
    
    if avg_arpu is not None:
        result["avg_arpu"] = round(avg_arpu, 2)
        result["suggested_arpu"] = [f"--arpu {round(avg_arpu, 2)}"]
    
    # Generate ready-to-use CLI params
    cli_parts = [
        f"--initial-dau {round(avg_dau, 0)}",
        f"--daily-churn-rate {round(daily_churn_rate, 4)}",
    ]
    if avg_dnu is not None:
        cli_parts.append(f"--daily-dnu {round(avg_dnu, 0)}")
    if avg_arpu is not None:
        cli_parts.append(f"--arpu {round(avg_arpu, 2)}")
    
    result["forecast_command"] = f"forecast.py forward {' '.join(cli_parts)}"
    
    return result

def main():
    parser = argparse.ArgumentParser(
        description="Game Revenue Forecast Engine — Dynamic DAU/ARPU Modeling"
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")
    
    # forward
    fwd = subparsers.add_parser("forward", help="Forward revenue forecast")
    fwd.add_argument("--initial-dau", type=float, required=True)
    fwd.add_argument("--daily-dnu", type=float, required=True)
    fwd.add_argument("--arpu", type=float, required=True)
    fwd.add_argument("--daily-churn-rate", type=float, required=True)
    fwd.add_argument("--days", type=int, default=180)
    fwd.add_argument("--dnu-growth", type=str, default=None,
                     help="JSON: [{'day':30,'dnu':3000},{'day':60,'dnu':4000}]")
    fwd.add_argument("--arpu-growth", type=str, default=None,
                     help="JSON: [{'day':45,'arpu':15.0}]")
    fwd.add_argument("--output", choices=["json", "table"], default="table")
    
    # reverse-dnu
    rdnu = subparsers.add_parser("reverse-dnu", help="Reverse-calculate required DNU")
    rdnu.add_argument("--initial-dau", type=float, required=True)
    rdnu.add_argument("--current-arpu", type=float, required=True)
    rdnu.add_argument("--target-daily-revenue", type=float, required=True)
    rdnu.add_argument("--daily-churn-rate", type=float, required=True)
    rdnu.add_argument("--days", type=int, default=180)
    rdnu.add_argument("--output", choices=["json", "table"], default="table")
    
    # reverse-arpu
    rapu = subparsers.add_parser("reverse-arpu", help="Reverse-calculate required ARPU")
    rapu.add_argument("--initial-dau", type=float, required=True)
    rapu.add_argument("--daily-dnu", type=float, required=True)
    rapu.add_argument("--current-arpu", type=float, required=True)
    rapu.add_argument("--daily-churn-rate", type=float, required=True)
    rapu.add_argument("--target-daily-revenue", type=float, required=True)
    rapu.add_argument("--days", type=int, default=180)
    rapu.add_argument("--output", choices=["json", "table"], default="table")
    
    # fit-retention
    rfit = subparsers.add_parser("fit-retention", help="Fit retention curve from known points")
    rfit.add_argument("--retention-points", type=str, required=True)
    rfit.add_argument("--model", choices=["log", "power"], default="log")
    
    # dual-drive
    dd = subparsers.add_parser("dual-drive", help="Dual-drive optimization (UA + Operations)")
    dd.add_argument("--initial-dau", type=float, required=True)
    dd.add_argument("--current-dnu", type=float, required=True)
    dd.add_argument("--current-arpu", type=float, required=True)
    dd.add_argument("--daily-churn-rate", type=float, required=True)
    dd.add_argument("--target-daily-revenue", type=float, required=True)
    dd.add_argument("--days", type=int, default=180)
    dd.add_argument("--arpu-lift-pct", type=float, default=0.2)
    dd.add_argument("--output", choices=["json", "table"], default="table")
    
    # ltv
    ltv_p = subparsers.add_parser("ltv", help="Estimate LTV")
    ltv_p.add_argument("--arpu", type=float, required=True)
    ltv_p.add_argument("--day1-retention", type=float, required=True)
    ltv_p.add_argument("--horizon", type=int, default=180)
    
    # derive-params
    dp = subparsers.add_parser("derive-params", help="Extract DAU/DNU/ARPU/churn from ae-cli data")
    dp.add_argument("--dau-json", type=str, required=True,
                    help="ae-cli query result JSON (time-series with 'rows' containing daily DAU)")
    dp.add_argument("--dnu-json", type=str, default=None,
                    help="ae-cli query result JSON for DNU")
    dp.add_argument("--revenue-json", type=str, default=None,
                    help="ae-cli query result JSON for revenue")
    dp.add_argument("--dau-row-index", type=int, default=0,
                    help="Row index in dau-json that contains daily user counts (default: 0 = first data column)")
    dp.add_argument("--window-days", type=int, default=7,
                    help="Number of recent days to average (default: 7)")
    
    args = parser.parse_args()
    
    if args.command == "forward":
        result = forward_forecast(
            args.initial_dau, args.daily_dnu, args.arpu,
            args.daily_churn_rate, args.days
        )
        output_result(result, args.output)
    
    elif args.command == "reverse-dnu":
        result = solve_dnu(
            args.initial_dau, args.current_arpu,
            args.target_daily_revenue, args.daily_churn_rate, args.days
        )
        output_result(result, args.output)
    
    elif args.command == "reverse-arpu":
        result = solve_arpu_with_current(
            args.initial_dau, args.daily_dnu, args.current_arpu,
            args.daily_churn_rate, args.target_daily_revenue, args.days
        )
        output_result(result, args.output)
    
    elif args.command == "fit-retention":
        points = parse_retention_points(args.retention_points)
        fn, params = fit_retention_curve(points, args.model)
        print(f"Fitted retention model: {params['model']}")
        print(f"Parameters: { {k:v for k,v in params.items() if k != 'model'} }")
        print(f"\nPredicted retention rates:")
        for d in [1, 3, 7, 14, 30, 60, 90, 180]:
            rate = fn(d)
            rate_clamped = max(0, min(1, rate))
            print(f"  Day {d:3d}: {rate_clamped*100:.2f}%")
    
    elif args.command == "dual-drive":
        result = dual_drive_optimization(
            args.initial_dau, args.current_dnu, args.current_arpu,
            args.daily_churn_rate, args.target_daily_revenue,
            args.days, args.arpu_lift_pct
        )
        output_result(result, args.output)
    
    elif args.command == "ltv":
        result = estimate_ltv(args.arpu, args.day1_retention, args.horizon)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "derive-params":
        result = derive_params(
            args.dau_json, args.dnu_json, args.revenue_json,
            args.dau_row_index, args.window_days
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

def output_result(data: dict, fmt: str):
    """Output result in the requested format."""
    if fmt == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return
    
    # Table format — print key fields
    if "recommendation" in data:
        print(f"\n📋 {data['recommendation']}\n")
    
    print("=" * 70)
    print("📊 Revenue Forecast Report")
    print("=" * 70)
    
    if "monthly_revenue" in data.get("forward_forecast", data):
        monthly = data.get("forward_forecast", data)["monthly_revenue"]
    elif "monthly_revenue" in data:
        monthly = data["monthly_revenue"]
    else:
        monthly = None
    
    if monthly:
        print(f"\n{'Month':>6} {'Revenue':>14} {'Avg DAU':>10} {'Avg ARPU':>10}")
        print("-" * 42)
        total_rev = 0
        for m in monthly:
            print(f"{m['month']:>6} ¥{m['revenue']:>10,.0f} {m['avg_dau']:>10,.0f} ¥{m['avg_arpu']:>8,.2f}")
            total_rev += m['revenue']
        print("-" * 42)
        print(f"{'Total':>6} ¥{total_rev:>10,.0f}")
    
    if "cumulative_180d_revenue" in data:
        print(f"\nCumulative 180d Revenue: ¥{data['cumulative_180d_revenue']:,.2f}")
    
    if "required_dnu_per_day" in data:
        print(f"\n📈 Key Metrics:")
        print(f"  Required DNU/day : {data['required_dnu_per_day']:>10,.0f}")
        print(f"  Target DAU       : {data['target_dau']:>10,.0f}")
        print(f"  Target Daily Rev : ¥{data['target_daily_revenue']:>10,.0f}")
    
    if "arpu_lift_pct" in data:
        print(f"  ARPU Lift %      : {data['arpu_lift_pct']:>10.1f}%")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
