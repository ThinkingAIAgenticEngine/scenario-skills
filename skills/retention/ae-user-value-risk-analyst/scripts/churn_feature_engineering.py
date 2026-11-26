"""
Feature engineering + churn label builder for TE event data.

Required input CSV columns: user_id, event_name, event_time
Optional columns: session_id, pay_amount, event_value

When session_id is missing, pseudo-sessions are derived from a configurable
inactivity gap (--session-gap-minutes, default 30).

Core events (e.g. battle, level_up, pay) can be supplied via --core-events
"battle,level_up,pay" to compute core-recency / core-frequency features.

Feature taxonomy (10 categories, 35 features):
  Recency      : days_since_last_event, days_since_last_core_event
  Frequency    : total_events, active_days_total, active_days_7d, active_days_30d, core_event_count,
                 avg_events_per_day
  Monetary     : monetary_total, pay_count, days_since_last_pay, days_since_first_pay,
                 pay_decline_7d, pay_tier
  Tenure       : tenure_days, lifecycle_stage
  Trend        : trend_7d_events, trend_7d_active_days, trend_7d_pay, change_rate_7d_events
  Session      : session_count, avg_events_per_session, avg_session_duration_min,
                 avg_session_interval_days, max_inactive_gap_days
  Diversity    : event_types, event_entropy, module_coverage
  Streak       : current_streak, max_streak, streak_broken
  Time pattern : night_ratio, weekend_ratio
  Relative     : freq_percentile, recency_zscore

Features use [T-W, T). D is the inactivity threshold and H is the independent
--prediction-days horizon (defaults to D for compatibility). Training uses
T = obs_end-H. window_inactive labels no qualifying activity in [T, obs_end);
churn_onset labels reaching D days of inactivity during that interval.
Without D, or with --score-only, build an unlabeled snapshot ending at obs_end.

--label-criterion controls what counts as "activity" for the label:
  any  : any event counts as activity (default, broadest)
  core : only events listed in --core-events count (requires --core-events)
  pay  : only events with pay_amount > 0 count (requires a pay_amount column)
Note: --core-events ALSO drives core-recency / core-frequency features; the two
roles are independent. To get core-event features with an any-event label, pass
--core-events without --label-criterion (defaults to "any").

Implementation note: every per-user computation is vectorized (sort + groupby
on the whole frame, no `groupby.apply(lambda)`). The previous version used
`g.apply(_per_user_fn)` for session derivation / max-inactive-gap / streaks /
entropy / session interval, which on 49k users × 4.4M events peaked above the
cgroup memory limit and was OOM-killed. Vectorized form keeps memory bounded
to a handful of column vectors and runs entirely in the pandas/numpy C layer.

Usage:
    python churn_feature_engineering.py \\
        --input events.csv --output user_features.csv \\
        --churn-days 14 --core-events "battle,level_up,pay" \\
        --session-gap-minutes 30 --churn-inactivity-days 14
"""
import argparse

import numpy as np
import pandas as pd

from event_time import parse_timestamps
from feature_schema import FEATURE_COLS, read_csv


# ---------- helpers ----------

def _parse_endpoint(value, name: str, timezone) -> pd.Timestamp:
    """Validate a cutoff and express it in the event calendar's timezone."""
    try:
        endpoint = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a valid timestamp") from exc
    if pd.isna(endpoint):
        raise ValueError(f"{name} must be a valid non-missing timestamp")
    if (endpoint.tzinfo is None) != (timezone is None):
        raise ValueError(f"{name} and event_time must use the same timezone awareness")
    # Calendar-day features must not change when the same instant is supplied
    # as, for example, UTC rather than the event stream's Asia/Shanghai time.
    return endpoint.tz_convert(timezone) if timezone is not None else endpoint


def _require_finite(values, description: str) -> None:
    if not np.isfinite(np.asarray(values, dtype=float)).all():
        raise ValueError(f"{description} contains non-finite values")


def _lifecycle_stage_vec(tenure_days: pd.Series, active_days: pd.Series) -> np.ndarray:
    """0=new (tenure<7), 1=growing (7..29), 2=mature (active/tenure>=0.3), 3=declining."""
    tenure = tenure_days.astype(int)
    active = active_days.astype(int)
    intensity = active / tenure.clip(lower=1)
    return np.where(tenure < 7, 0,
           np.where(tenure < 30, 1,
           np.where(intensity < 0.3, 3, 2)))


def _pay_tier_vec(monetary: pd.Series, q50: float, q90: float) -> np.ndarray:
    """0=non-payer, 1=small, 2=mid, 3=whale."""
    m = monetary.values
    return np.where(m <= 0, 0,
           np.where(m >= q90, 3,
           np.where(m >= q50, 2, 1)))


def qualifying_events(events: pd.DataFrame, label_criterion: str = "any",
                      core_events: set = None) -> pd.DataFrame:
    """Select the same activity definition for labels, cohort state and baselines.

    The caller supplies parsed event timestamps. This helper does not modify
    the input and does not decide observation or label time bounds.
    """
    if label_criterion == "core":
        if not core_events:
            raise ValueError("--label-criterion=core requires --core-events")
        return events[events["event_name"].isin(core_events)]
    if label_criterion == "pay":
        if "pay_amount" not in events:
            raise ValueError("--label-criterion=pay requires a pay_amount column")
        return events[events["pay_amount"].fillna(0) > 0]
    if label_criterion != "any":
        raise ValueError("--label-criterion must be any, core or pay")
    return events


def _merge_activity_evidence(observed, evidence, cutoff, observation_start):
    """Merge verified clocks without inventing feature events or missing activity."""
    required = {"user_id", "last_qualifying_event_time"}
    if not required.issubset(evidence):
        raise ValueError("activity evidence requires user_id and last_qualifying_event_time")
    ids = evidence.user_id
    if ids.isna().any() or ids.astype(str).str.strip().eq("").any() or ids.duplicated().any():
        raise ValueError("activity evidence requires unique, nonempty user_id")
    if "snapshot_time" in evidence and not evidence.snapshot_time.map(
            lambda value: _parse_endpoint(value, "activity evidence snapshot", cutoff.tz) == cutoff).all():
        raise ValueError("activity evidence snapshot differs from feature cutoff")
    supplied = pd.Series([
        pd.NaT if pd.isna(value) else _parse_endpoint(value, "activity evidence clock", cutoff.tz)
        for value in evidence.last_qualifying_event_time
    ], index=pd.Index(ids, name="user_id"), dtype=observed.dtype)
    if supplied.dropna().ge(cutoff).any():
        raise ValueError("activity evidence must be strictly before the feature cutoff")
    previous = observed.reindex(supplied.index)
    newer = supplied.notna() & (previous.isna() | supplied.gt(previous))
    missing_feature_users = supplied.index[newer & supplied.ge(observation_start)]
    merged = pd.concat([observed, supplied.dropna()]).groupby(level=0, sort=False).max()
    return merged, missing_feature_users


# ---------- main builder ----------

def build_features(events: pd.DataFrame, churn_days: int,
                   obs_end: str = None,
                   core_events: set = None,
                   session_gap_minutes: int = 30,
                   churn_inactivity_days: int = None,
                   label_criterion: str = "any",
                   data_end: str = None,
                   prediction_days: int = None,
                   label_target: str = "window_inactive",
                   cohort: str = "all",
                   score_only: bool = False,
                   *, project_timezone=None, activity_evidence=None) -> pd.DataFrame:
    """Build features on [T-W, T) and optional labels on [T, T+H).

    Training requires D and uses T = obs_end-H (H defaults to D). score_only
    retains D for cohort eligibility but creates no label and uses T=obs_end.
    prevention users last had qualifying activity less than D days ago;
    winback users last had it at least D days ago. Both require known prior
    qualifying activity. Cohort candidates must have an event in [T-W, T).

    window_inactive means no qualifying activity in the future H-day window.
    churn_onset, available for prevention, means a D-day inactivity deadline
    occurs within that window, even if the user subsequently returns. A new
    activity exactly at the deadline still completes a D-day inactive gap.

    data_end is the exclusive endpoint through which the caller verified data
    completeness; snapshots and labels cannot extend beyond an explicit bound.
    Without it, training conservatively uses the latest event timestamp as its
    coverage bound; unlabeled snapshots cannot verify absence of later events.
    Aware timestamps are converted to project_timezone when specified, so
    calendar-day, hour and weekday features use that project's local time.
    Score-only activity_evidence may supply verified pre-T clocks before cohort
    filtering. Newer activity missing inside [T-W,T) excludes that feature row;
    older evidence changes only the clock, never the observed feature events.
    """
    required = {"user_id", "event_name", "event_time"}
    if not required.issubset(events.columns):
        raise ValueError(f"events missing required columns: {sorted(required - set(events.columns))}")
    if churn_days <= 0 or session_gap_minutes <= 0:
        raise ValueError("--churn-days and --session-gap-minutes must be positive")
    if churn_inactivity_days is not None and churn_inactivity_days <= 0:
        raise ValueError("--churn-inactivity-days must be positive")
    if prediction_days is not None and prediction_days <= 0:
        raise ValueError("--prediction-days must be positive")
    if prediction_days is not None and churn_inactivity_days is None:
        raise ValueError("--prediction-days requires --churn-inactivity-days")
    if label_target not in ("window_inactive", "churn_onset"):
        raise ValueError("--label-target must be window_inactive or churn_onset")
    if cohort not in ("all", "prevention", "winback"):
        raise ValueError("--cohort must be all, prevention or winback")
    if cohort != "all" and churn_inactivity_days is None:
        raise ValueError("--cohort prevention/winback requires --churn-inactivity-days")
    if label_target == "churn_onset" and cohort != "prevention":
        raise ValueError("--label-target=churn_onset requires --cohort=prevention")
    if label_criterion not in ("any", "core", "pay"):
        raise ValueError("--label-criterion must be any, core or pay")
    if label_criterion == "core" and not core_events:
        raise ValueError("--label-criterion=core requires --core-events")
    if label_criterion == "pay" and "pay_amount" not in events.columns:
        raise ValueError("--label-criterion=pay requires a pay_amount column")
    if events.empty or events[list(required)].isna().any().any():
        raise ValueError("events must be nonempty with non-null user_id, event_name and event_time")
    events = events.copy()
    events["event_time"] = parse_timestamps(events["event_time"], project_timezone=project_timezone)
    if "pay_amount" in events:
        # Monetary features are floating-point model inputs. Converting before
        # aggregation avoids int64 sums silently wrapping positive spend below
        # zero. Missing amounts mean no payment; infinities are invalid data.
        events["pay_amount"] = pd.to_numeric(events["pay_amount"], errors="raise").fillna(0).astype(float)
        _require_finite(events["pay_amount"], "pay_amount")
    # Categorical-encode high-cardinality string columns to keep memory bounded:
    # 4.4M rows × a 40-byte UUID string = ~170MB; as categorical with int32 codes
    # the same column is ~18MB. event_name is even smaller (4-10 unique values).
    # The 2GB cgroup on small pods otherwise OOMs on full-scale pulls.
    for col in ("user_id", "event_name"):
        if events[col].dtype == object or pd.api.types.is_string_dtype(events[col].dtype):
            events[col] = events[col].astype("category")
    timezone = events["event_time"].dt.tz
    max_time = (_parse_endpoint(obs_end, "--obs-end", timezone)
                if obs_end is not None else events["event_time"].max())
    coverage_end = (_parse_endpoint(data_end, "--data-end", timezone)
                    if data_end is not None else events["event_time"].max())
    training = churn_inactivity_days is not None and not score_only
    horizon = prediction_days if prediction_days is not None else churn_inactivity_days
    if training:
        now = pd.Timestamp.now(tz=timezone)
        if max_time > now or max_time > coverage_end:
            raise ValueError("training label window is incomplete: --obs-end must be in the past "
                             "and within event coverage; supply --data-end only for a verified "
                             "exclusive data-completeness endpoint")
    elif data_end is not None and max_time > coverage_end:
        raise ValueError("scoring snapshot is incomplete: --obs-end must be within the "
                         "verified --data-end coverage")

    # Features stop strictly before the training label window (or scoring T).
    if training:
        label_start = max_time - pd.Timedelta(days=horizon)
        feature_max_time = label_start
    else:
        label_start = None
        feature_max_time = max_time

    obs_start = feature_max_time - pd.Timedelta(days=churn_days)
    feature_events = events[(events["event_time"] >= obs_start) &
                            (events["event_time"] < feature_max_time)].copy()
    qualified = qualifying_events(events, label_criterion, core_events)
    last_qualifying = qualified[qualified["event_time"] < feature_max_time] \
        .groupby("user_id", observed=True)["event_time"].max()
    if activity_evidence is not None:
        if not score_only:
            raise ValueError("activity evidence is only supported for score-only snapshots, not training labels")
        last_qualifying, missing_users = _merge_activity_evidence(
            last_qualifying, activity_evidence, feature_max_time, obs_start)
        feature_events = feature_events[~feature_events.user_id.isin(missing_users)].copy()
    if cohort != "all":
        elapsed = feature_max_time - last_qualifying
        threshold = pd.Timedelta(days=churn_inactivity_days)
        eligible = elapsed < threshold if cohort == "prevention" else elapsed >= threshold
        feature_events = feature_events[feature_events["user_id"].isin(last_qualifying[eligible].index)].copy()
    if feature_events.empty:
        columns = ["user_id"] + FEATURE_COLS + (["churn"] if training else [])
        if label_target == "churn_onset":
            columns += ["snapshot_time", "last_qualifying_event_time"]
        return pd.DataFrame(columns=columns)
    last7_start = feature_max_time - pd.Timedelta(days=7)
    prev7_start = feature_max_time - pd.Timedelta(days=14)
    end_date = (feature_max_time - pd.Timedelta(nanoseconds=1)).date()

    fe = feature_events
    fe["is_core"] = fe["event_name"].isin(core_events) if core_events else False
    # Sort once by (user, time) and reuse for session derivation + max-inactive-gap.
    # Both computations need the same order; the previous version sorted twice
    # and kept two full-frame copies alive, which was the main memory hog.
    fe_sorted = fe.sort_values(["user_id", "event_time"], kind="mergesort")
    gap_secs = fe_sorted.groupby("user_id", observed=True)["event_time"].diff().dt.total_seconds()
    if "session_id" not in fe_sorted.columns:
        is_new_session = (gap_secs > session_gap_minutes * 60) | gap_secs.isna()
        fe_sorted["session_id"] = is_new_session.groupby(fe_sorted["user_id"], observed=True).cumsum().astype(int)
    elif fe_sorted["session_id"].isna().any():
        raise ValueError("session_id contains missing values; fill them or omit the column to derive sessions")
    # diff once for max_inactive_gap too — same sorted frame, same gap column
    fe_sorted["_gap_secs"] = gap_secs
    max_gap_per_user = fe_sorted.groupby("user_id", observed=True)["_gap_secs"].max() / 86400.0
    # drop the helper column to free memory before subsequent steps
    fe_sorted = fe_sorted.drop(columns=["_gap_secs"], errors="ignore")

    fe = fe_sorted  # subsequent groupbys operate on the sorted frame
    fe["day"] = fe["event_time"].dt.date
    fe["hour"] = fe["event_time"].dt.hour
    fe["dow"] = fe["event_time"].dt.day_of_week

    g = fe.groupby("user_id", observed=True)
    feat = pd.DataFrame(index=g.size().index)

    # ---- Recency ----
    feat["days_since_last_event"] = (feature_max_time - g["event_time"].max()).dt.days
    if core_events:
        core_evt = fe[fe["is_core"]]
        if not core_evt.empty:
            last_core = core_evt.groupby("user_id", observed=True)["event_time"].max()
            feat["days_since_last_core_event"] = (feature_max_time - last_core.reindex(feat.index)).dt.days
        else:
            feat["days_since_last_core_event"] = np.nan
    else:
        feat["days_since_last_core_event"] = np.nan

    # ---- Frequency ----
    feat["total_events"] = g.size()
    feat["active_days_total"] = g["day"].nunique()
    feat["active_days_7d"] = fe[fe["event_time"] >= last7_start].groupby("user_id", observed=True)["day"].nunique()
    feat["active_days_30d"] = fe[fe["event_time"] >= feature_max_time - pd.Timedelta(days=30)]\
        .groupby("user_id", observed=True)["day"].nunique()
    if core_events:
        feat["core_event_count"] = fe[fe["is_core"]].groupby("user_id", observed=True).size()
    else:
        feat["core_event_count"] = 0
    feat = feat.fillna({"active_days_7d": 0, "active_days_30d": 0, "core_event_count": 0})

    # ---- Monetary ----
    if "pay_amount" in fe.columns:
        pay = fe["pay_amount"].fillna(0)
        payers = g["pay_amount"].sum()
        _require_finite(payers, "pay_amount aggregation")
        payers_pos = payers[payers > 0]
        q50 = payers_pos.quantile(0.5) if not payers_pos.empty else 0
        q90 = payers_pos.quantile(0.9) if not payers_pos.empty else 0
        feat["monetary_total"] = payers
        # pay_count: count of rows where pay_amount > 0, per user (vectorized)
        is_pay_row = (fe["pay_amount"] > 0)
        feat["pay_count"] = is_pay_row.groupby(fe["user_id"], observed=True).sum().astype(int)
        last_pay = fe[pay > 0].groupby("user_id", observed=True)["event_time"].max()
        first_pay = fe[pay > 0].groupby("user_id", observed=True)["event_time"].min()
        feat["days_since_last_pay"] = (feature_max_time - last_pay.reindex(feat.index)).dt.days
        feat["days_since_first_pay"] = (feature_max_time - first_pay.reindex(feat.index)).dt.days
        last7_pay = fe[fe["event_time"] >= last7_start]["pay_amount"].fillna(0).groupby(fe["user_id"], observed=True).sum()
        prev7_pay = fe[(fe["event_time"] >= prev7_start) & (fe["event_time"] < last7_start)]["pay_amount"].fillna(0).groupby(fe["user_id"], observed=True).sum()
        feat["pay_decline_7d"] = (last7_pay.reindex(feat.index, fill_value=0) - prev7_pay.reindex(feat.index, fill_value=0))
        _require_finite(feat["pay_decline_7d"], "pay_amount trend aggregation")
        feat["pay_tier"] = _pay_tier_vec(feat["monetary_total"], q50, q90)
    else:
        for c in ["monetary_total", "pay_count", "pay_decline_7d"]:
            feat[c] = 0.0
        feat["days_since_last_pay"] = np.nan
        feat["days_since_first_pay"] = np.nan
        feat["pay_tier"] = 0

    # ---- Tenure ----
    first_evt = g["event_time"].min()
    feat["tenure_days"] = (feature_max_time - first_evt).dt.days + 1
    feat["lifecycle_stage"] = _lifecycle_stage_vec(feat["tenure_days"], feat["active_days_total"])
    feat["avg_events_per_day"] = feat["total_events"] / feat["tenure_days"].clip(lower=1)

    # ---- Trend (last 7d vs prior 7d) ----
    last7 = fe[fe["event_time"] >= last7_start]
    prev7 = fe[(fe["event_time"] >= prev7_start) & (fe["event_time"] < last7_start)]
    last7_c = last7.groupby("user_id", observed=True).size()
    prev7_c = prev7.groupby("user_id", observed=True).size()
    feat["trend_7d_events"] = (last7_c.reindex(feat.index, fill_value=0) -
                                prev7_c.reindex(feat.index, fill_value=0)).astype(float)
    last7_ad = last7.groupby("user_id", observed=True)["day"].nunique()
    prev7_ad = prev7.groupby("user_id", observed=True)["day"].nunique()
    feat["trend_7d_active_days"] = (last7_ad.reindex(feat.index, fill_value=0) -
                                     prev7_ad.reindex(feat.index, fill_value=0)).astype(float)
    feat["trend_7d_pay"] = feat["pay_decline_7d"].fillna(0)
    prev7_c_aligned = prev7_c.reindex(feat.index, fill_value=0)
    feat["change_rate_7d_events"] = feat["trend_7d_events"] / (prev7_c_aligned + 1)

    # ---- Session ----
    sess = fe.groupby(["user_id", "session_id"], observed=True)["event_time"].agg(["count", "min", "max"])
    sess["dur_min"] = (sess["max"] - sess["min"]).dt.total_seconds() / 60.0
    sess_count = sess.groupby("user_id", observed=True).size()
    feat["session_count"] = sess_count.reindex(feat.index, fill_value=0)
    feat["avg_events_per_session"] = (g.size() / feat["session_count"].clip(lower=1)).fillna(0)
    feat["avg_session_duration_min"] = sess.groupby("user_id", observed=True)["dur_min"].mean().reindex(feat.index, fill_value=0)

    # avg_session_interval_days: mean gap between consecutive session starts (vectorized)
    sess_sorted = sess.reset_index().sort_values(["user_id", "min"], kind="mergesort")
    sess_sorted["start_gap_secs"] = sess_sorted.groupby("user_id", observed=True)["min"].diff().dt.total_seconds()
    sess_int = sess_sorted.groupby("user_id", observed=True)["start_gap_secs"].mean() / 86400.0
    feat["avg_session_interval_days"] = sess_int.reindex(feat.index, fill_value=0).fillna(0)

    # max_inactive_gap_days: already computed above from the single sorted frame
    feat["max_inactive_gap_days"] = max_gap_per_user.reindex(feat.index, fill_value=0).fillna(0)

    # ---- Diversity ----
    feat["event_types"] = g["event_name"].nunique()
    # event_entropy (normalized Shannon): vectorized over (user, event_name) count matrix
    counts = fe.groupby(["user_id", "event_name"], observed=True).size().unstack(fill_value=0).astype(float)
    totals = counts.sum(axis=1)
    totals_safe = totals.where(totals > 0, 1)
    p = counts.div(totals_safe, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_p = np.where(p.values > 0, np.log(p.values), 0.0)
    entropy = -(p.values * log_p).sum(axis=1)
    ent_series = pd.Series(entropy, index=counts.index)
    k = (counts > 0).sum(axis=1)
    max_ent = np.log(k.where(k > 1, 1).astype(float))
    max_ent_s = pd.Series(max_ent, index=counts.index)
    feat["event_entropy"] = (ent_series / max_ent_s).fillna(0.0).clip(upper=1.0, lower=0.0).reindex(feat.index, fill_value=0.0)
    if fe["event_name"].str.contains(":").any():
        fe["module"] = fe["event_name"].str.split(":").str[0]
        feat["module_coverage"] = g["module"].nunique()
    else:
        feat["module_coverage"] = feat["event_types"]

    # ---- Streak (vectorized) ----
    days_df = fe[["user_id", "day"]].drop_duplicates()
    days_df = days_df.sort_values(["user_id", "day"], kind="mergesort").reset_index(drop=True)
    days_df["_ord"] = days_df["day"].map(lambda d: d.toordinal())
    days_df["_prev_ord"] = days_df.groupby("user_id", observed=True)["_ord"].shift(1)
    days_df["_is_break"] = days_df["_prev_ord"].isna() | ((days_df["_ord"] - days_df["_prev_ord"]) != 1)
    days_df["_run_id"] = days_df.groupby("user_id", observed=True)["_is_break"].cumsum()
    run_lens = days_df.groupby(["user_id", "_run_id"], observed=True).size().rename("run_len").reset_index()
    run_lens["_is_last"] = run_lens.groupby("user_id", observed=True)["_run_id"].transform("max") == run_lens["_run_id"]

    feat["max_streak"] = run_lens.groupby("user_id", observed=True)["run_len"].max().reindex(feat.index, fill_value=1)
    # The exclusive cutoff's preceding instant defines the last observed day.
    last_day_per_user = days_df.groupby("user_id", observed=True)["day"].max()
    matched_end = last_day_per_user == end_date
    last_run_lens = run_lens[run_lens["_is_last"]].set_index("user_id")["run_len"]
    cur = pd.Series(0, index=feat.index, dtype=int)
    matched_users = matched_end[matched_end].index.intersection(last_run_lens.index)
    cur.loc[matched_users] = last_run_lens.loc[matched_users]
    feat["current_streak"] = cur
    # streak_broken: any non-last run with length > 1
    non_last_long = run_lens[~run_lens["_is_last"] & (run_lens["run_len"] > 1)]
    broken_users = non_last_long["user_id"].unique()
    feat["streak_broken"] = feat.index.isin(broken_users).astype(int)

    # ---- Time pattern ----
    total = g.size()
    night = fe[fe["hour"].between(0, 6)].groupby("user_id", observed=True).size()
    weekend = fe[fe["dow"] >= 5].groupby("user_id", observed=True).size()
    feat["night_ratio"] = (night / total).reindex(feat.index, fill_value=0).fillna(0)
    feat["weekend_ratio"] = (weekend / total).reindex(feat.index, fill_value=0).fillna(0)

    # ---- Relative ----
    feat["freq_percentile"] = feat["total_events"].rank(pct=True)
    recency_mean = feat["days_since_last_event"].mean()
    recency_std = feat["days_since_last_event"].std(ddof=0)
    feat["recency_zscore"] = (feat["days_since_last_event"] - recency_mean) / (recency_std + 1e-9)

    # ---- NaN cleanup ----
    # "days_since_*" recency columns are NaN when the event in question never
    # happened for that user (e.g. never paid, no core event). NaN breaks
    # sklearn training downstream (LogisticRegression/RandomForest reject it
    # outright), and it isn't safe to fillna(0) here since 0 would read as
    # "just happened", the opposite of the truth. Use a large sentinel so the
    # model instead learns "this recency is maximally stale / never occurred".
    NEVER_HAPPENED_SENTINEL = 9999
    for col in ("days_since_last_core_event", "days_since_last_pay", "days_since_first_pay"):
        if col in feat.columns:
            feat[col] = feat[col].fillna(NEVER_HAPPENED_SENTINEL)

    feat = feat.reindex(columns=FEATURE_COLS).fillna(0)
    _require_finite(feat, "engineered features")
    if label_target == "churn_onset":
        # Keep exact clock metadata outside the 35 learned features. Generic
        # integer-day recency can refer to a different (nonqualifying) event.
        feat["snapshot_time"] = feature_max_time
        feat["last_qualifying_event_time"] = last_qualifying.reindex(feat.index)
    if not training:
        return feat.reset_index()

    # Labels use only qualifying activity; other events never reset inactivity.
    win = qualified[(qualified["event_time"] >= label_start) & (qualified["event_time"] < max_time)]
    if label_target == "window_inactive":
        feat["churn"] = (~feat.index.isin(win["user_id"].unique())).astype(int)
    else:
        # Start each user's timeline at the last known pre-T qualifying event.
        # Every subsequent qualifying activity resets the inactivity deadline.
        initial = last_qualifying.reindex(feat.index).rename("event_time").reset_index()
        future = win.loc[win["user_id"].isin(feat.index), ["user_id", "event_time"]]
        timeline = pd.concat([initial, future], ignore_index=True) \
            .sort_values(["user_id", "event_time"], kind="mergesort")
        next_activity = timeline.groupby("user_id", observed=True)["event_time"].shift(-1)
        deadlines = timeline["event_time"] + pd.Timedelta(days=churn_inactivity_days)
        reached = (deadlines >= label_start) & (deadlines < max_time) & \
            (next_activity.isna() | (next_activity >= deadlines))
        feat["churn"] = feat.index.isin(timeline.loc[reached, "user_id"].unique()).astype(int)

    if label_target == "churn_onset":
        feat = feat[[*FEATURE_COLS, "churn", "snapshot_time", "last_qualifying_event_time"]]
    return feat.reset_index().rename(columns={"index": "user_id"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="events.csv")
    ap.add_argument("--output", default="user_features.csv")
    ap.add_argument("--churn-days", type=int, default=14)
    ap.add_argument("--obs-end", default=None)
    ap.add_argument("--data-end", default=None, help="verified exclusive data-completeness endpoint")
    ap.add_argument("--timezone", help="IANA project timezone for offset-aware events (e.g. America/New_York)")
    ap.add_argument("--core-events", default="", help="comma-separated core event names, e.g. 'battle,level_up,pay'")
    ap.add_argument("--session-gap-minutes", type=int, default=30,
                    help="inactivity gap (min) used to derive pseudo-sessions when session_id is absent")
    ap.add_argument("--churn-inactivity-days", type=int, default=None, dest="churn_inactivity_days",
                    help="inactivity threshold D; H defaults to D if --prediction-days is omitted")
    ap.add_argument("--label-future-days", type=int, default=None, dest="churn_inactivity_days",
                    help="(deprecated alias for --churn-inactivity-days; same semantics)")
    ap.add_argument("--prediction-days", type=int, default=None,
                    help="independent future label horizon H; training T=obs-end-H")
    ap.add_argument("--label-target", choices=("window_inactive", "churn_onset"), default="window_inactive")
    ap.add_argument("--cohort", choices=("all", "prevention", "winback"), default="all")
    ap.add_argument("--score-only", action="store_true",
                    help="build unlabeled features at obs-end, retaining D for cohort eligibility")
    ap.add_argument("--activity-evidence", help="score-only CSV of verified as-of-T qualifying clocks; not synthetic events")
    ap.add_argument("--label-criterion", default="any", choices=("any", "core", "pay"),
                    help="what counts as activity for the churn label: any event (default), "
                         "core event only (requires --core-events), or pay event only (requires pay_amount)")
    args = ap.parse_args()

    core = {c.strip() for c in args.core_events.split(",") if c.strip()} or None
    df = read_csv(args.input)
    feat = build_features(df, args.churn_days, args.obs_end, core, args.session_gap_minutes,
                         churn_inactivity_days=args.churn_inactivity_days,
                         label_criterion=args.label_criterion, data_end=args.data_end,
                         prediction_days=args.prediction_days, label_target=args.label_target,
                         cohort=args.cohort, score_only=args.score_only, project_timezone=args.timezone,
                         activity_evidence=read_csv(args.activity_evidence) if args.activity_evidence else None)
    feat.to_csv(args.output, index=False)
    label_info = f"; churn rate={feat['churn'].mean():.3f}" if "churn" in feat else "; scoring snapshot (no label)"
    print(f"wrote {len(feat)} users x {len(FEATURE_COLS)} features to {args.output}{label_info}")


if __name__ == "__main__":
    main()
