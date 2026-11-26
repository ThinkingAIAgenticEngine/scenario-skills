#!/usr/bin/env python3
"""Rank already-inactive users by win-back value tiers.

Input: a user-level aggregate CSV with one row per user and these columns:
- user_id: opaque string user ID
- last_login_time: the user's last login instant (consistent awareness)
- last_activity_time: the user's last qualifying-activity instant
- pay_recent: payment amount in [T-V, T)
- pay_prior: payment amount in [T-2V, T-V)
- pay_total: lifetime payment amount

The aggregate must be computed as of the same cutoff T and window V passed
here (see references/audience.md for the export SQL template). All windows
are exact instant intervals; no login in [T-D, T) defines the winback
population. Value tiers:
- T1_paid_recent: paid within the recent V-day window
- T2_paid_prior: paid in the previous V-day window only
- T3_dormant_payer: paid earlier only
- T4_never_paid: no recorded payment

Ranking inside the population: tier, pay_total, pay_recent, then days since
login. Users without a recorded login are excluded and counted separately.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data_provenance import resolve_data_kind
from event_time import parse_timestamps
from feature_schema import read_csv

REQUIRED = ["user_id", "last_login_time", "last_activity_time",
            "pay_recent", "pay_prior", "pay_total"]
TIERS = ["T1_paid_recent", "T2_paid_prior", "T3_dormant_payer", "T4_never_paid"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--users", required=True, help="user-level aggregate CSV")
    p.add_argument("--cutoff", required=True,
                   help="exclusive snapshot cutoff T the aggregate was computed at")
    p.add_argument("--inactive-days", type=int, default=14,
                   help="D: winback means no login in [T-D, T)")
    p.add_argument("--value-days", type=int, default=30,
                   help="V: recent payment window [T-V, T); must match the aggregate")
    p.add_argument("--timezone", help="IANA project timezone for aware timestamps")
    p.add_argument("--timestamp-timezone", help="confirmed source timezone of offset-free aggregate timestamps; never guessed")
    p.add_argument("--data-kind", choices=("real", "simulated"))
    p.add_argument("--output-dir", required=True)
    return p.parse_args()


def _parse_endpoint(value, name, timezone):
    result = pd.Timestamp(value)
    if pd.isna(result):
        raise SystemExit(f"{name} must be a valid timestamp")
    if timezone is not None:
        if result.tz is None:
            raise SystemExit(f"{name} must be offset-aware when --timezone is set")
        result = result.tz_convert(timezone)
    return result


def main():
    opt = parse_args()
    users = read_csv(opt.users)
    missing = [c for c in REQUIRED if c not in users.columns]
    if missing:
        raise SystemExit(f"aggregate is missing required columns: {missing}")
    if users.user_id.isna().any() or users.user_id.astype(str).str.strip().eq("").any():
        raise SystemExit("user_id cannot contain missing or empty values")
    if users.user_id.duplicated().any():
        raise SystemExit("aggregate requires exactly one row per user_id; duplicate IDs are not ranked")
    if opt.inactive_days <= 0 or opt.value_days <= 0:
        raise SystemExit("--inactive-days and --value-days must be positive")

    timezone = opt.timezone
    T = _parse_endpoint(opt.cutoff, "--cutoff", timezone)
    if opt.timestamp_timezone and T.tz is None:
        raise SystemExit("--timestamp-timezone requires an offset-aware --cutoff")
    for column in ("last_login_time", "last_activity_time"):
        known = users[column].notna()
        # Even all-missing columns must share the cutoff's timestamp awareness.
        dtype = pd.DatetimeTZDtype(tz=T.tz, unit="ns") if T.tz is not None else "datetime64[ns]"
        result = pd.Series(pd.NaT, index=users.index, dtype=dtype)
        if known.any():
            parsed = parse_timestamps(users.loc[known, column], field=column, project_timezone=timezone)
            if parsed.dt.tz is None and opt.timestamp_timezone:
                parsed = parsed.dt.tz_localize(opt.timestamp_timezone, ambiguous="raise", nonexistent="raise")
            if (parsed.dt.tz is None) != (T.tz is None):
                raise SystemExit(f"{column} and --cutoff must use the same timestamp awareness; "
                                 "export explicit offsets or declare the confirmed source with --timestamp-timezone")
            if T.tz is not None:
                parsed = parsed.dt.tz_convert(T.tz)
            result.loc[known] = parsed
        users[column] = result

    for column in ("pay_recent", "pay_prior", "pay_total"):
        amounts = pd.to_numeric(users[column], errors="coerce")
        if not np.isfinite(amounts.to_numpy(dtype=float)).all() or (amounts < 0).any():
            raise SystemExit(f"{column} must be complete finite nonnegative numbers; "
                             "resolve the aggregate export before ranking")
        users[column] = amounts

    for column in ("last_login_time", "last_activity_time"):
        known = users[users[column].notna()]
        if len(known) and (known[column] > T).any():
            raise SystemExit(f"{column} contains instants after --cutoff; "
                             "the aggregate must be computed as of T")

    D = pd.Timedelta(days=opt.inactive_days)
    never_logged_in = users.last_login_time.isna()
    winback = users[~never_logged_in & (users.last_login_time < T - D)].copy()
    winback["days_since_login"] = (T - winback.last_login_time).dt.total_seconds() / 86400
    winback["days_since_activity"] = (T - winback.last_activity_time).dt.total_seconds() / 86400
    winback["segment"] = np.select(
        [winback.last_activity_time.isna(), winback.last_activity_time >= T - D],
        ["unknown_activity", "still_active_otherwise"], default="fully_silent")
    winback["tier"] = np.select(
        [winback.pay_recent > 0, winback.pay_prior > 0, winback.pay_total > 0],
        TIERS[:3], default=TIERS[3])
    winback = winback.sort_values(
        ["tier", "pay_total", "pay_recent", "days_since_login", "user_id"],
        ascending=[True, False, False, True, True], kind="mergesort")
    winback["priority_rank"] = range(1, len(winback) + 1)

    output = Path(opt.output_dir)
    work = output / "work"
    work.mkdir(parents=True, exist_ok=True)

    out_cols = ["priority_rank", "user_id", "tier", "days_since_login", "last_login_time",
                "days_since_activity", "segment", "pay_recent", "pay_prior", "pay_total"]
    result = output / "winback_value_ranking_result.csv"
    winback[out_cols].to_csv(result, index=False)

    edges = [opt.inactive_days, opt.inactive_days + 7, opt.inactive_days + 16,
             opt.inactive_days + 31, opt.inactive_days + 46, np.inf]
    payers = winback[winback.pay_total > 0]
    provenance = resolve_data_kind(opt.data_kind, frames=[("users", users)])
    tier_stats = {}
    for name in TIERS:
        subset = winback[winback.tier == name]
        tier_stats[name] = {
            "users": int(len(subset)),
            "pay_recent_sum": float(subset.pay_recent.sum()),
            "pay_prior_sum": float(subset.pay_prior.sum()),
            "pay_total_sum": float(subset.pay_total.sum()),
            "median_days_since_login": float(subset.days_since_login.median()) if len(subset) else None,
        }
    summary = {
        "mode": "winback_value_ranking",
        "cutoff": T.isoformat(), "timezone": timezone,
        "params": {k: v for k, v in vars(opt).items() if k != "users"},
        "label": (f"Winback means no login in [T-{opt.inactive_days}d, T); tiers use "
                  f"payment in [T-{opt.value_days}d, T), [T-{2*opt.value_days}d, T-{opt.value_days}d) "
                  "and lifetime payment."),
        "population": {
            "users_total": int(len(users)),
            "never_logged_in": int(never_logged_in.sum()),
            "winback_users": int(len(winback)),
            "winback_rate": float(len(winback) / len(users)) if len(users) else 0.0,
            "segments": {k: int(v) for k, v in winback.segment.value_counts().items()},
            "payers": int(len(payers)),
        },
        "tiers": tier_stats,
        "days_since_login_buckets_payers": {
            f"({edges[i] if np.isfinite(edges[i]) else edges[i]},{edges[i+1] if np.isfinite(edges[i+1]) else '+'}]":
            int(((payers.days_since_login > edges[i]) & (payers.days_since_login <= edges[i+1])).sum())
            for i in range(len(edges) - 1)},
        "value_at_risk": {
            "pay_recent_sum": float(winback.pay_recent.sum()),
            "pay_prior_sum": float(winback.pay_prior.sum()),
            "pay_total_sum": float(winback.pay_total.sum()),
        },
        "aggregate_note": ("The aggregate must be computed as of the same cutoff T and "
                           "window V with exact instant windows; retain the export SQL as evidence."),
        **provenance,
    }
    (work / "winback_value_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Results: {result} ({len(winback)} winback users, "
          f"{len(payers)} payers). Tiers: " +
          ", ".join(f"{k}={v['users']}" for k, v in tier_stats.items()))


if __name__ == "__main__":
    main()
