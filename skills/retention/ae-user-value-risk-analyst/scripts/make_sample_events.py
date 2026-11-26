"""
Generate a small synthetic events.csv for end-to-end smoke-testing the
churn-risk-analyst pipeline. Not part of the skill itself -- a dev-time helper.

Covers: payers/non-payers, still-active/declining/already-churned users,
short-tenure "new" users, varying event diversity.
"""
import argparse
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--end", default="2026-08-24", help="exclusive end of complete synthetic coverage")
ap.add_argument("--output", default="sample_events.csv")
ap.add_argument("--users", type=int, default=600)
args = ap.parse_args()
if args.users <= 0:
    ap.error("--users must be positive")
rng = np.random.default_rng(42)

EVENTS = ["login", "enter_dungeon", "level_up", "payment", "battle:win", "battle:lose", "chat"]
NOW = pd.Timestamp(args.end).normalize() - pd.Timedelta(days=1)
N_USERS = args.users

rows = []
for uid in range(N_USERS):
    user_id = f"u{uid:05d}"
    # user archetype
    archetype = rng.choice(
        ["stable_payer", "declining_payer", "silent_quitter", "new_unstable", "casual_free"],
        p=[0.15, 0.15, 0.25, 0.15, 0.30],
    )
    tenure_days = int(rng.integers(3, 200))
    first_day = NOW - pd.Timedelta(days=tenure_days)

    if archetype == "stable_payer":
        active_days = rng.integers(int(tenure_days * 0.6), tenure_days + 1)
        last_active_offset = rng.integers(0, 2)
        pay_prob = 0.4
    elif archetype == "declining_payer":
        active_days = rng.integers(int(tenure_days * 0.3), int(tenure_days * 0.6) + 1)
        last_active_offset = rng.integers(10, 20)
        pay_prob = 0.3
    elif archetype == "silent_quitter":
        active_days = rng.integers(2, max(3, int(tenure_days * 0.2)))
        last_active_offset = rng.integers(20, 60)
        pay_prob = 0.02
    elif archetype == "new_unstable":
        tenure_days = int(rng.integers(1, 6))
        first_day = NOW - pd.Timedelta(days=tenure_days)
        active_days = rng.integers(1, tenure_days + 1)
        last_active_offset = rng.integers(0, 3)
        pay_prob = 0.05
    else:  # casual_free
        active_days = rng.integers(int(tenure_days * 0.2), int(tenure_days * 0.5) + 1)
        last_active_offset = rng.integers(0, 10)
        pay_prob = 0.0

    active_days = max(1, min(active_days, tenure_days + 1))
    last_active_day = NOW - pd.Timedelta(days=int(last_active_offset))
    active_day_offsets = sorted(rng.choice(
        range(0, max(1, tenure_days - last_active_offset) + 1), size=min(active_days, tenure_days - int(last_active_offset) + 1),
        replace=False,
    )) if tenure_days - int(last_active_offset) >= 0 else [0]

    for off in active_day_offsets:
        day = first_day + pd.Timedelta(days=int(off))
        n_events_today = rng.integers(1, 8)
        for _ in range(n_events_today):
            hour = int(rng.integers(0, 24))
            minute = int(rng.integers(0, 60))
            ts = day + pd.Timedelta(hours=hour, minutes=minute)
            ev = rng.choice(EVENTS, p=[0.3, 0.2, 0.15, 0.05, 0.15, 0.1, 0.05])
            pay_amount = 0.0
            if ev == "payment" or (rng.random() < pay_prob * 0.1):
                ev = "payment"
                pay_amount = float(rng.choice([6, 30, 98, 328], p=[0.5, 0.3, 0.15, 0.05]))
            rows.append((user_id, ev, ts, pay_amount))

df = pd.DataFrame(rows, columns=["user_id", "event_name", "event_time", "pay_amount"])
df = df.sort_values(["user_id", "event_time"]).reset_index(drop=True)
df = df[df["event_time"] < pd.Timestamp(args.end)]
df.to_csv(args.output, index=False)
print(f"wrote {args.output}: {len(df)} rows, {df['user_id'].nunique()} users, "
      f"time range {df['event_time'].min()} .. {df['event_time'].max()}")
