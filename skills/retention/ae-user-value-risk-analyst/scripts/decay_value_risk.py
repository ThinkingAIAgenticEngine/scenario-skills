#!/usr/bin/env python3
"""Rank users by decay risk weighted by recent value."""
import argparse
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from churn_feature_engineering import _parse_endpoint, build_features
from data_provenance import resolve_data_kind
from event_time import parse_timestamps
from feature_schema import FEATURE_COLS, read_csv

TOP_TIER_SHARE = 0.10
MID_TIER_SHARE = 0.20
MIN_GATE_SNAPSHOTS = 2
TREND_DROP_RATIO = 0.7
DECAYED_FLOOR = 0.7
DECAYING_BASE = 0.4
DECAYING_CAP = np.nextafter(DECAYED_FLOOR, 0.0)
NORMAL_CAP = 0.39


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", required=True)
    p.add_argument("--snapshot", help="exclusive scoring cutoff T; defaults to the coverage end")
    p.add_argument("--data-start", help="attested inclusive coverage start; defaults to first observed event")
    p.add_argument("--data-end", help="attested exclusive coverage end; defaults to last observed event")
    p.add_argument("--coverage-evidence", help="optional upstream partition or watermark evidence for the declared bounds")
    p.add_argument("--timezone", help="IANA project timezone for offset-aware events (e.g. America/New_York)")
    p.add_argument("--window-days", type=int, default=45, help="personal baseline window W")
    p.add_argument("--recent-days", type=int, default=14, help="recent window R for the rule signal")
    p.add_argument("--horizon-days", type=int, default=14, help="prediction horizon H")
    p.add_argument("--decay-ratio", type=float, default=0.3, help="baseline fraction X defining decay")
    p.add_argument("--decay-criterion", choices=["any", "pay"], default="any",
                   help="any = active days per day; pay = pay_amount per day")
    p.add_argument("--value-cols", default="pay_amount",
                   help="comma-separated value columns (e.g. pay_amount,ads_revenue)")
    p.add_argument("--value-days", type=int, default=30, help="value window V")
    p.add_argument("--train-snapshots", type=int, default=6, help="training snapshots (disjoint from gate)")
    p.add_argument("--gate-snapshots", type=int, default=3, help="held-out snapshots to attempt (0 uses the rule)")
    p.add_argument("--min-baseline-days", type=int, default=5,
                   help="minimum baseline active days for the any criterion")
    p.add_argument("--min-snapshot-users", type=int, default=100)
    p.add_argument("--gate-auc-margin", type=float, default=0.02)
    p.add_argument("--data-kind", choices=("real", "simulated"), help="provenance of the event export")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--report", action="store_true", help="also write a standalone Markdown report")
    opt = p.parse_args()
    for arg in ("window_days", "recent_days", "horizon_days", "value_days",
                "min_baseline_days", "min_snapshot_users"):
        if getattr(opt, arg) < 1:
            p.error(f"--{arg.replace('_', '-')} must be positive")
    if opt.train_snapshots < 1 or opt.gate_snapshots < 0:
        p.error("--train-snapshots must be positive and --gate-snapshots must be nonnegative")
    if not 0 < opt.decay_ratio <= 1 or not 0 <= opt.gate_auc_margin <= 1:
        p.error("--decay-ratio must be in (0,1] and --gate-auc-margin in [0,1]")
    return opt


def load_scoring_events(opt, value_cols, history_days):
    events = read_csv(opt.events)
    value_fields = set(value_cols)
    if opt.decay_criterion == "pay":
        value_fields.add("pay_amount")
    required = {"user_id", "event_name", "event_time"}
    missing = (required | value_fields) - set(events.columns)
    if missing:
        raise ValueError(f"events CSV is missing required columns: {sorted(missing)}")
    if events.empty or events[sorted(required)].isna().any().any():
        raise ValueError("events must be nonempty with non-null user_id, event_name and event_time")
    project_timezone = getattr(opt, "timezone", None)
    events["event_time"] = parse_timestamps(events.event_time, project_timezone=project_timezone)
    timezone = events.event_time.dt.tz
    start = (_parse_endpoint(opt.data_start, "--data-start", timezone)
             if opt.data_start else events.event_time.min())
    end = (_parse_endpoint(opt.data_end, "--data-end", timezone)
           if opt.data_end else events.event_time.max())
    snapshot = _parse_endpoint(opt.snapshot, "--snapshot", timezone) if opt.snapshot else end
    if snapshot > end or snapshot > pd.Timestamp.now(tz=timezone):
        raise ValueError("--snapshot must be at or before the coverage end and the current time")
    if snapshot - timedelta(days=history_days) < start:
        raise ValueError("event coverage is too short for the baseline and value windows at --snapshot")
    events = events.loc[(events.event_time >= start) & (events.event_time < snapshot)].copy()
    if events.empty:
        raise ValueError("no events inside the coverage window before --snapshot")
    for col in sorted(value_fields):
        try:
            values = pd.to_numeric(events[col], errors="raise").astype(float)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{col} contains nonnumeric values") from exc
        if not np.isfinite(values).all():
            raise ValueError(f"{col} contains missing or nonfinite values; use explicit zeros for non-value events")
        events[col] = values
    coverage = {
        "start": start.isoformat(), "end": end.isoformat(),
        "start_source": "declared_coverage" if opt.data_start else "first_observed_event",
        "end_source": "declared_coverage" if opt.data_end else "last_observed_event",
        "status": "attested" if opt.data_start and opt.data_end else "unverified",
        "evidence": getattr(opt, "coverage_evidence", None),
        "timezone": project_timezone or (str(timezone) if timezone is not None else None),
    }
    return events, snapshot, start, coverage


def _rate(events, start, end, criterion):
    """Count occupied 24-hour bins anchored to start, or sum pay over [start, end)."""
    df = events[(events.event_time >= start) & (events.event_time < end)]
    if df.empty:
        return pd.Series(dtype=float)
    if criterion == "pay":
        return df.groupby("user_id").pay_amount.sum()
    bins = (df.event_time - start) // pd.Timedelta(days=1)
    return bins.groupby(df.user_id).nunique()


def value_series(events, T, days, value_cols):
    """Combined recent value per user over [T-days, T)."""
    df = events[(events.event_time >= T - timedelta(days=days)) & (events.event_time < T)]
    if df.empty or not value_cols:
        return pd.Series(dtype=float)
    return df.groupby("user_id")[value_cols].sum().sum(axis=1)


def snapshot_frame(events, T, opt, with_label, *, recent_values=None):
    """Per-user frame at snapshot T: 35 features + baseline/recent/trend rates +
    rule score + dual signal (+ optional decay label)."""
    base_start = T - timedelta(days=opt.window_days + opt.recent_days)
    base_end = T - timedelta(days=opt.recent_days)
    feats = build_features(events, churn_days=opt.window_days, obs_end=T,
                           label_criterion=opt.decay_criterion, score_only=True,
                           project_timezone=getattr(opt, "timezone", None))
    feats = feats.set_index("user_id")
    candidates = feats.index
    if recent_values is not None and opt.value_days > opt.window_days:
        positive_value_users = recent_values.index[recent_values.gt(0)]
        candidates = candidates.union(positive_value_users, sort=False).rename("user_id")
    base = _rate(events, base_start, base_end, opt.decay_criterion).reindex(candidates).fillna(0.0)
    recent = _rate(events, base_end, T, opt.decay_criterion).reindex(candidates).fillna(0.0)
    half = opt.recent_days // 2
    if half:
        mid = base_end + timedelta(days=half)
        former = _rate(events, base_end, mid, opt.decay_criterion).reindex(candidates).fillna(0.0) / half
        latter = (_rate(events, mid, T, opt.decay_criterion).reindex(candidates).fillna(0.0)
                  / (opt.recent_days - half))
    else:
        former = latter = pd.Series(0.0, index=candidates)
    base_rate, recent_rate = base / opt.window_days, recent / opt.recent_days
    ok = base >= opt.min_baseline_days if opt.decay_criterion == "any" else base > 0

    frame = pd.DataFrame({"baseline_rate": base_rate, "recent_rate": recent_rate,
                          "former_rate": former, "latter_rate": latter,
                          "baseline_ok": ok, "has_feature_history": candidates.isin(feats.index)},
                         index=candidates).join(feats)

    # Dual signal: "decayed" is the observed fact (same threshold family as the
    # label); "decaying" is the leading trend (latter half collapsing vs former
    # half while already below baseline). Rule score stays monotone:
    # decayed >= 0.7 > decaying [0.4, 0.7) > normal <= 0.39.
    decayed = ok & (recent_rate < opt.decay_ratio * base_rate)
    decaying = (~decayed & ok & (half >= 1)
                & (frame.latter_rate < TREND_DROP_RATIO * frame.former_rate.replace(0, np.nan))
                & (frame.latter_rate < frame.baseline_rate))
    signal = np.where(decayed, "decayed", np.where(decaying, "decaying", "normal"))
    recent_drop = 1.0 - recent_rate / base_rate.replace(0, np.nan)
    trend_drop = 1.0 - latter / former.replace(0, np.nan)
    score = np.select([decayed, decaying], [
        recent_drop.clip(lower=DECAYED_FLOOR, upper=1.0),
        (DECAYING_BASE + 0.3 * trend_drop).clip(lower=DECAYING_BASE, upper=DECAYING_CAP),
    ], default=recent_drop.clip(lower=0.0, upper=NORMAL_CAP))
    frame["signal"] = signal
    frame["rule_score"] = np.nan_to_num(np.asarray(score, dtype=float), nan=0.0)

    if with_label:
        fut = _rate(events, T, T + timedelta(days=opt.horizon_days),
                    opt.decay_criterion).reindex(frame.index).fillna(0.0) / opt.horizon_days
        frame["decay"] = ((fut < opt.decay_ratio * frame.baseline_rate) & ok).astype(int)
    return frame


def rank_by_priority(risk_score, recent_value):
    priority = risk_score * recent_value.clip(lower=0.0)
    # Use user_id to break ties in both the held-out comparison and the final export.
    return priority.sort_index(kind="stable").sort_values(ascending=False, kind="stable")


def score_candidates(eligible, model):
    scores = eligible.rule_score.copy()
    uses_model = eligible.has_feature_history & (model is not None)
    if uses_model.any():
        scores.loc[uses_model] = model.predict_proba(eligible.loc[uses_model, FEATURE_COLS])[:, 1]
    return scores, uses_model


def evaluate_snapshots(model, events, snapshots, earliest, opt, value_cols):
    from sklearn.metrics import roc_auc_score

    rows = []
    for T in snapshots:
        row = {"snapshot": T.isoformat()}
        rows.append(row)
        if T < earliest:
            row["status"] = "incomplete_history"
            continue
        recent_values = value_series(events, T, opt.value_days, value_cols)
        frame = snapshot_frame(events, T, opt, with_label=True, recent_values=recent_values)
        eligible = frame[frame.baseline_ok]
        row["users"] = len(eligible)
        if len(eligible) < opt.min_snapshot_users or eligible.decay.nunique() != 2:
            row["status"] = "insufficient_users_or_label_classes"
            continue
        if not eligible.has_feature_history.any():
            row["status"] = "no_feature_history_for_model"
            continue

        scores, uses_model = score_candidates(eligible, model)
        row["model_scored_users"] = int(uses_model.sum())
        row["rule_only_users"] = len(eligible) - row["model_scored_users"]
        row["model_auc"] = float(roc_auc_score(eligible.decay, scores))
        row["rule_auc"] = float(roc_auc_score(eligible.decay, eligible.rule_score))
        values = recent_values.reindex(eligible.index).fillna(0.0)
        observed_value = eligible.decay * values.clip(lower=0.0)
        total = float(observed_value.sum())
        if total <= 0:
            row["status"] = "no_positive_value_among_decayed_users"
            continue
        k = max(int(len(eligible) * TOP_TIER_SHARE), 1)
        model_top = rank_by_priority(scores, values).index[:k]
        rule_top = rank_by_priority(eligible.rule_score, values).index[:k]
        row.update(status="valid", top_k=k,
                   model_capture_10pct=float(observed_value.loc[model_top].sum()) / total,
                   rule_capture_10pct=float(observed_value.loc[rule_top].sum()) / total)
    return rows


def summarize_gate(rows, opt, training_count, *, coverage_attested):
    valid_rows = [row for row in rows if row["status"] == "valid"]
    gate = {"status": "insufficient_evidence", "snapshots": rows,
            "requested_snapshots": opt.gate_snapshots, "valid_snapshots": len(valid_rows),
            "min_valid_snapshots": MIN_GATE_SNAPSHOTS, "training_snapshots_used": training_count,
            "model_strategy": "Score feature-window users with the model and other eligible users with the rule.",
            "auc_margin": opt.gate_auc_margin}
    if not coverage_attested:
        gate["reason"] = ("Model evaluation requires attested continuous coverage. "
                          "At least one coverage bound was inferred from observed events.")
        return gate
    if not opt.gate_snapshots:
        gate["reason"] = "Held-out evaluation was disabled."
        return gate
    if not training_count:
        gate["reason"] = "No training snapshot met coverage, user count and label requirements."
        return gate
    if len(valid_rows) < MIN_GATE_SNAPSHOTS:
        gate["reason"] = (f"Only {len(valid_rows)} held-out snapshots had both AUC and measurable value capture. "
                          f"At least {MIN_GATE_SNAPSHOTS} are required.")
        return gate

    for metric in ("model_auc", "rule_auc", "model_capture_10pct", "rule_capture_10pct"):
        gate[f"mean_{metric}"] = float(np.mean([row[metric] for row in valid_rows]))
    auc_pass = gate["mean_model_auc"] >= gate["mean_rule_auc"] + opt.gate_auc_margin
    capture_pass = gate["mean_model_capture_10pct"] >= gate["mean_rule_capture_10pct"]
    gate["status"] = "passed" if auc_pass and capture_pass else "below_threshold"
    gate["auc_pass"] = auc_pass
    gate["capture_pass"] = capture_pass
    gate["reason"] = (f"AUC margin {'met' if auc_pass else 'missed'}. "
                      f"Value capture threshold {'met' if capture_pass else 'missed'}.")
    return gate


def write_report(path, summary, eligible):
    counts = summary["coverage"]
    gate = summary["gate"]
    lines = [
        "# Decay Value-Risk Report",
        "",
        f"Scoring cutoff {summary['snapshot']}. {summary['label']}",
        f"Coverage from {counts['start']} to {counts['end']} is {counts['status']}.",
        f"{summary['gate_verdict']} {gate['reason']}",
        f"{gate['valid_snapshots']} of {gate['requested_snapshots']} held-out snapshots had both metrics.",
        f"{counts['eligible_users']} of {counts['sample_users']} historical users were eligible. "
        f"{counts['excluded_no_baseline']} lacked a qualifying baseline and "
        f"{counts['excluded_no_feature_history']} had neither feature-window events nor positive recent value.",
        f"Recent value uses {', '.join(summary['value_cols'])} over {summary['value_days']} days.",
        summary["score_note"],
    ]
    if "mean_model_auc" in gate:
        lines.append(
            f"Model-enabled and all-rule mean AUC were {gate['mean_model_auc']:.3f} and {gate['mean_rule_auc']:.3f}. "
            f"Top-10% value capture was {gate['mean_model_capture_10pct']:.1%} and "
            f"{gate['mean_rule_capture_10pct']:.1%}, respectively.")
    if summary["simulation_only"]:
        lines.append("These simulated results verify workflow behavior only.")
    lines += ["", "| User | Signal | Risk score | Score source | Recent value | Value priority score | Tier |",
              "|---|---|---|---|---|---|---|"]
    for row in eligible.head(10).reset_index().itertuples(index=False):
        lines.append(f"| {row.user_id} | {row.signal} | {row.risk_score:.3f} | {row.score_source} | {row.recent_value:.2f} | "
                     f"{row.value_priority_score:.2f} | {row.risk_tier} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    opt = parse_args()
    value_cols = [col.strip() for col in opt.value_cols.split(",") if col.strip()]
    if not value_cols or len(set(value_cols)) != len(value_cols):
        raise SystemExit("--value-cols must contain one or more distinct column names")
    baseline_days = opt.window_days + opt.recent_days
    history_days = max(baseline_days, opt.value_days)
    try:
        events, T, data_start, coverage = load_scoring_events(opt, value_cols, history_days)
    except (ValueError, OSError, AttributeError, TypeError) as exc:
        raise SystemExit(str(exc)) from exc
    coverage_attested = coverage["status"] == "attested"
    earliest_train = data_start + timedelta(days=baseline_days)
    earliest_gate = data_start + timedelta(days=history_days)
    horizon = timedelta(days=opt.horizon_days)
    # All label windows end by T. The latest training labels end by the oldest held-out T.
    gate_Ts = [T - horizon * i for i in range(1, opt.gate_snapshots + 1)] if coverage_attested else []
    train_Ts = [T - horizon * (opt.gate_snapshots + i)
                for i in range(1, opt.train_snapshots + 1)] if gate_Ts else []
    frames = []
    for Ts in train_Ts:
        if Ts < earliest_train:
            continue
        frame = snapshot_frame(events, Ts, opt, with_label=True)
        frame = frame[frame.baseline_ok]
        if len(frame) >= opt.min_snapshot_users and frame.decay.nunique() == 2:
            frames.append(frame)

    model, gate_rows = None, []
    if frames:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        train = pd.concat(frames)
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        model.fit(train[FEATURE_COLS], train.decay)
        gate_rows = evaluate_snapshots(model, events, gate_Ts, earliest_gate, opt, value_cols)
    gate = summarize_gate(gate_rows, opt, len(frames), coverage_attested=coverage_attested)

    recent_values = value_series(events, T, opt.value_days, value_cols)
    score = snapshot_frame(events, T, opt, with_label=False, recent_values=recent_values)
    eligible = score[score.baseline_ok].copy()
    use_model = gate["status"] == "passed"
    eligible["risk_score"], uses_model = score_candidates(eligible, model if use_model else None)
    eligible["score_source"] = np.where(uses_model, "model", "rule")
    eligible["recent_value"] = recent_values.reindex(eligible.index).fillna(0.0)
    priority = rank_by_priority(eligible.risk_score, eligible.recent_value)
    eligible = eligible.loc[priority.index].assign(value_priority_score=priority)
    n = len(eligible)
    model_scored_users = int(uses_model.sum())
    rule_scored_users = n - model_scored_users
    gate_verdict = "Model selected." if use_model else "Rule fallback."
    if not coverage_attested:
        gate_verdict = "Provisional rule scoring."
    score_source = "model" if use_model else "rule"
    if use_model and rule_scored_users:
        score_source = "model_and_rule" if model_scored_users else "rule"
        gate_verdict = (f"Model passed the gate. {rule_scored_users} current candidates used rule scores "
                        "because they lack feature-window history.")
    rank = np.arange(n)
    positive = eligible.value_priority_score > 0
    high_limit = max(int(n * TOP_TIER_SHARE), 1)
    medium_limit = int(n * (TOP_TIER_SHARE + MID_TIER_SHARE))
    eligible["risk_tier"] = np.select([positive & (rank < high_limit), positive & (rank < medium_limit)],
                                     ["high", "medium"], default="low")

    provenance = resolve_data_kind(opt.data_kind, frames=[("events", events)])
    eligible["data_kind"] = provenance["data_kind"]
    sample_users = int(events.user_id.nunique())
    summary = {
        "mode": "decay_value_risk", "snapshot": T.isoformat(), "score_source": score_source,
        "label": (f"Decay means the {opt.decay_criterion} rate over the next {opt.horizon_days} days is "
                  f"below {opt.decay_ratio:.0%} of the personal {opt.window_days}-day baseline "
                  f"ending {opt.recent_days} days before cutoff."),
        "gate": gate, "gate_verdict": gate_verdict,
        "coverage": {
            **coverage, "sample_users": sample_users, "eligible_users": n,
            "eligible_rate": n / sample_users,
            "excluded_no_baseline": len(score) - n,
            "excluded_no_feature_history": sample_users - len(score),
            "eligible_without_feature_history": int((~eligible.has_feature_history).sum()),
            "model_scored_users": model_scored_users,
            "rule_scored_users": rule_scored_users,
            "nonpositive_value_users": int((eligible.recent_value <= 0).sum()),
        },
        "signals": {signal: int(count) for signal, count in eligible.signal.value_counts().items()},
        "value_cols": value_cols, "value_days": opt.value_days, **provenance,
        "score_note": ("Value priority equals the risk score times positive recent value. "
                       "Both model and rule scores are for ranking."),
        "params": {key: value for key, value in vars(opt).items() if key != "events"},
    }
    output = Path(opt.output_dir)
    work = output / "work"
    work.mkdir(parents=True, exist_ok=True)
    out_cols = ["user_id", "baseline_rate", "recent_rate", "latter_rate", "signal", "rule_score",
                "risk_score", "score_source", "recent_value", "value_priority_score", "risk_tier", "data_kind"]
    result = output / "decay_value_risk_result.csv"
    eligible.reset_index()[out_cols].to_csv(result, index=False)
    (work / "decay_value_risk_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    if opt.report:
        write_report(output / "decay_value_risk_report.md", summary, eligible)
    print(f"Results: {result} ({n} eligible). {summary['gate_verdict']} {gate['reason']}")


if __name__ == "__main__":
    main()
