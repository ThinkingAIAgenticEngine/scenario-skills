"""Exact, pre-snapshot bounds on a churn-onset prediction, never learned features."""
from numbers import Integral

import numpy as np
import pandas as pd

ONSET_META_COLS = ("snapshot_time", "last_qualifying_event_time")


def _clock(values):
    stamps = [pd.Timestamp(value) for value in values]
    if any(pd.isna(value) for value in stamps):
        raise ValueError("missing timestamp")
    awareness = {value.tzinfo is not None for value in stamps}
    if len(awareness) != 1:
        raise ValueError("mixed timestamp awareness")
    # CSVs can contain different UTC offsets across daylight-saving changes.
    # Normalize aware clocks to UTC without silently localizing naive clocks.
    return pd.Series(pd.to_datetime(stamps, utc=awareness.pop()), index=values.index)


def onset_reachability(frame, config, snapshot_time=None):
    """Return eligible contact positions and an auditable constraint summary.

    In prevention, L+D is the earliest possible future onset. A return can only
    postpone it. The half-open label window excludes L+D == T+H. Unknown history
    is an error here, not evidence for a zero probability; unscored audience rows
    are joined later and never pass through this function.
    """
    enabled = config.get("label_target") == "churn_onset"
    summary = {"enabled": enabled, "users": len(frame), "unreachable_users": 0}
    if not enabled:
        return np.ones(len(frame), dtype=bool), summary
    D, H = config.get("churn_inactivity_days"), config.get("prediction_days")
    H = D if H is None else H
    for value, name in ((D, "D"), (H, "H")):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value <= 0:
            raise ValueError(f"churn_onset requires positive integer {name}")
    if config.get("cohort") != "prevention":
        raise ValueError("churn_onset constraint requires prevention cohort")
    summary.update(rule="L+D < T+H; exact qualifying timestamps; [T,T+H)",
                   probability_when_unreachable=0.0,
                   note="Zero describes this onset horizon, not future engagement or lifetime retention.")
    if frame.empty:
        return np.array([], dtype=bool), summary
    missing = set(ONSET_META_COLS) - set(frame.columns)
    if missing:
        raise ValueError(f"churn_onset needs exact timestamp metadata {sorted(missing)}; "
                         "regenerate features from source events (integer recency is insufficient)")
    try:
        T = _clock(frame.snapshot_time)
        L = _clock(frame.last_qualifying_event_time)
        if T.isna().any() or L.isna().any() or (T.dt.tz is None) != (L.dt.tz is None):
            raise ValueError("missing or incompatible timestamps")
        if snapshot_time is not None:
            requested = pd.Timestamp(snapshot_time)
            if pd.isna(requested) or (requested.tzinfo is None) != (T.dt.tz is None) or not T.eq(requested).all():
                raise ValueError("snapshot_time differs from feature cutoff")
        elapsed = T - L
        if not (elapsed.gt(pd.Timedelta(0)) & elapsed.lt(pd.Timedelta(days=int(D)))).all():
            raise ValueError("timestamps contradict pre-T prevention eligibility")
        reachable = (L + pd.Timedelta(days=int(D)) < T + pd.Timedelta(days=int(H))).to_numpy()
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"invalid churn_onset timestamp metadata: {exc}") from exc
    if "churn" in frame and frame.loc[~reachable, "churn"].eq(1).any():
        raise ValueError("positive churn_onset label outside reachable horizon")
    summary["unreachable_users"] = int((~reachable).sum())
    return reachable, summary


def constrain_probabilities(probabilities, reachable):
    """Keep model output intact for reachable users; zero only proved impossibility."""
    scores = np.asarray(probabilities, dtype=float)
    if scores.ndim != 1 or len(scores) != len(reachable) or not np.isfinite(scores).all() \
            or ((scores < 0) | (scores > 1)).any():
        raise ValueError("model returned invalid probabilities")
    return np.where(reachable, scores, 0.0)
