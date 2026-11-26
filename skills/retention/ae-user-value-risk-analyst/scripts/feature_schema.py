"""
Canonical feature column names produced by churn_feature_engineering.py.

Any script that references feature columns by name (heuristic scoring,
clustering, persona rules, ...) should import the names from here instead of
hardcoding strings. This is the single source of truth that keeps
predict_churn_risk.py / segment_high_risk.py in sync with whatever
churn_feature_engineering.py actually emits.

If churn_feature_engineering.py's output columns change, update this file in
the same commit.
"""

# ---- Recency ----
DAYS_SINCE_LAST_EVENT = "days_since_last_event"
DAYS_SINCE_LAST_CORE_EVENT = "days_since_last_core_event"

# ---- Frequency ----
TOTAL_EVENTS = "total_events"
ACTIVE_DAYS_TOTAL = "active_days_total"
ACTIVE_DAYS_7D = "active_days_7d"
ACTIVE_DAYS_30D = "active_days_30d"
CORE_EVENT_COUNT = "core_event_count"
AVG_EVENTS_PER_DAY = "avg_events_per_day"

# ---- Monetary ----
MONETARY_TOTAL = "monetary_total"
PAY_COUNT = "pay_count"
DAYS_SINCE_LAST_PAY = "days_since_last_pay"
DAYS_SINCE_FIRST_PAY = "days_since_first_pay"
PAY_DECLINE_7D = "pay_decline_7d"
PAY_TIER = "pay_tier"

# ---- Tenure ----
TENURE_DAYS = "tenure_days"
LIFECYCLE_STAGE = "lifecycle_stage"

# ---- Trend ----
TREND_7D_EVENTS = "trend_7d_events"
TREND_7D_ACTIVE_DAYS = "trend_7d_active_days"
TREND_7D_PAY = "trend_7d_pay"
CHANGE_RATE_7D_EVENTS = "change_rate_7d_events"

# ---- Session ----
SESSION_COUNT = "session_count"
AVG_EVENTS_PER_SESSION = "avg_events_per_session"
AVG_SESSION_DURATION_MIN = "avg_session_duration_min"
AVG_SESSION_INTERVAL_DAYS = "avg_session_interval_days"
MAX_INACTIVE_GAP_DAYS = "max_inactive_gap_days"

# ---- Diversity ----
EVENT_TYPES = "event_types"
EVENT_ENTROPY = "event_entropy"
MODULE_COVERAGE = "module_coverage"

# ---- Streak ----
CURRENT_STREAK = "current_streak"
MAX_STREAK = "max_streak"
STREAK_BROKEN = "streak_broken"

# ---- Time pattern ----
NIGHT_RATIO = "night_ratio"
WEEKEND_RATIO = "weekend_ratio"

# ---- Relative ----
FREQ_PERCENTILE = "freq_percentile"
RECENCY_ZSCORE = "recency_zscore"

# Non-feature columns that show up in user_features.csv / churn_prediction_result.csv
ID_COLS = ("user_id",)
LABEL_COL = "churn"
META_COLS = ("first_event_time", "last_event_time", "snapshot_time", "last_qualifying_event_time")

FEATURE_COLS = [
    DAYS_SINCE_LAST_EVENT, DAYS_SINCE_LAST_CORE_EVENT, TOTAL_EVENTS,
    ACTIVE_DAYS_TOTAL, ACTIVE_DAYS_7D, ACTIVE_DAYS_30D, CORE_EVENT_COUNT,
    AVG_EVENTS_PER_DAY, MONETARY_TOTAL, PAY_COUNT, DAYS_SINCE_LAST_PAY,
    DAYS_SINCE_FIRST_PAY, PAY_DECLINE_7D, PAY_TIER, TENURE_DAYS,
    LIFECYCLE_STAGE, TREND_7D_EVENTS, TREND_7D_ACTIVE_DAYS, TREND_7D_PAY,
    CHANGE_RATE_7D_EVENTS, SESSION_COUNT, AVG_EVENTS_PER_SESSION,
    AVG_SESSION_DURATION_MIN, AVG_SESSION_INTERVAL_DAYS, MAX_INACTIVE_GAP_DAYS,
    EVENT_TYPES, EVENT_ENTROPY, MODULE_COVERAGE, CURRENT_STREAK, MAX_STREAK,
    STREAK_BROKEN, NIGHT_RATIO, WEEKEND_RATIO, FREQ_PERCENTILE, RECENCY_ZSCORE,
]


def read_csv(path, **kwargs):
    """Preserve opaque user/session IDs and normal null rules for other columns."""
    import pandas as pd
    from pandas._libs.parsers import STR_NA_VALUES

    boxed_columns = set()

    def identifier_converter(column):
        def convert(value):
            if not value.strip():
                return pd.NA
            # pandas 3.1+ reapplies default NA tokens after converters. Box only
            # those rare literals, not every ID in a multi-million-event export.
            if value in STR_NA_VALUES:
                boxed_columns.add(column)
                return (value,)
            return value
        return convert

    converters = dict(kwargs.pop("converters", {}))
    for column in ("user_id", "session_id"):
        converters.setdefault(column, identifier_converter(column))
    result = pd.read_csv(path, converters=converters, **kwargs)
    for column in boxed_columns:
        result[column] = result[column].map(lambda value: value[0] if isinstance(value, tuple) else value)
    return result


def model_features(df, bundle):
    """Use the exact training schema and category levels when scoring/explaining."""
    import pandas as pd
    import numpy as np
    features = bundle["features"]
    missing = [c for c in features if c not in df.columns]
    if missing:
        raise ValueError(f"input is missing trained features: {missing}")
    X = df[features].copy()
    categories = bundle.get("category_levels", {})
    categorical = set(bundle.get("categorical_features", []))
    for c in features:
        if c in categorical:
            continue
        try:
            X[c] = pd.to_numeric(X[c], errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"numeric feature {c!r} contains nonnumeric values") from exc
        if not np.isfinite(X[c].to_numpy(dtype=float)).all():
            raise ValueError(f"numeric feature {c!r} contains missing or nonfinite values")
    for c in categorical:
        if c not in X:
            raise ValueError(f"categorical feature {c!r} is not in the trained schema")
        if c in categories:
            values = X[c].where(X[c].isin(categories[c]))
            X[c] = pd.Categorical(values, categories=categories[c])
        else:  # compatibility with pre-v3 model bundles
            X[c] = X[c].astype("category")
    return X


def check_coverage(requested: dict, available_cols, context: str, min_ratio: float = 0.6) -> list:
    """Warn/raise if too many referenced feature names don't exist in the dataframe.

    `requested` is a dict of {col_name: weight_or_anything}; only the keys are checked.
    Returns the list of matched column names. Raises ValueError if coverage is too low,
    so a future rename in churn_feature_engineering.py fails loudly here instead of
    silently degrading the heuristic score / clustering feature set.
    """
    available = set(available_cols)
    matched = [c for c in requested if c in available]
    missing = [c for c in requested if c not in available]
    ratio = len(matched) / len(requested) if requested else 1.0
    if missing:
        print(f"[{context}] missing columns (check for a naming drift vs "
              f"churn_feature_engineering.py): {missing}")
    if ratio < min_ratio:
        raise ValueError(
            f"[{context}] only {len(matched)}/{len(requested)} referenced columns "
            f"found in input ({ratio:.0%} < {min_ratio:.0%} minimum). "
            f"This usually means feature_schema.py is out of sync with "
            f"churn_feature_engineering.py's output columns. Missing: {missing}"
        )
    return matched
