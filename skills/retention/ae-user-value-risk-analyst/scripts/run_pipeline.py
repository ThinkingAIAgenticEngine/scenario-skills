"""Train, calibrate and evaluate churn models, or score a saved definition."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import joblib
import pandas as pd

from feature_schema import read_csv
from data_provenance import csv_data_kind, resolve_data_kind
from audience_results import complete_audience_results, resolve_audience_activity
from feature_schema import FEATURE_COLS
from project_data import load_project_config, compare_contracts, preflight_events

SCRIPT_DIR = Path(__file__).resolve().parent
DEFINITION_FIELDS = ("churn_days", "core_events", "session_gap_minutes",
                     "label_criterion", "churn_inactivity_days", "prediction_days",
                     "label_target", "cohort")


def normalize_core_events(value):
    return ",".join(sorted({s.strip() for s in value.split(",") if s.strip()}))


def run(script, arguments, step_name):
    cmd = [sys.executable, str(SCRIPT_DIR / script)] + [str(a) for a in arguments]
    print(f"\n=== {step_name} ===", flush=True)
    subprocess.run(cmd, check=True)


def require_columns(path, required, step_name):
    try:
        df = read_csv(path, nrows=5)
    except (OSError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f"before {step_name}: cannot read {path}: {exc}") from exc
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"before {step_name}: {path} missing columns {sorted(missing)}")


def training_config(args):
    # Existing commands retain the v3 target. Explicit H opts into onset prediction.
    target = args.label_target
    if target is None:
        if args.cohort in ("all", "winback"):
            target = "window_inactive"
        else:
            target = "churn_onset" if args.prediction_days is not None or args.cohort == "prevention" else "window_inactive"
    return {
        "definition_version": 2, "churn_days": args.churn_days,
        "churn_inactivity_days": args.churn_inactivity_days,
        "prediction_days": args.prediction_days if args.prediction_days is not None else args.churn_inactivity_days,
        "core_events": args.core_events or "",
        "session_gap_minutes": args.session_gap_minutes if args.session_gap_minutes is not None else 30,
        "label_criterion": args.label_criterion or "any", "label_target": target,
        "cohort": args.cohort or ("prevention" if target == "churn_onset" else "all"),
        "training_obs_end": args.obs_end,
    }


def scoring_config(args, bundle, parser):
    saved = dict(bundle.get("feature_config", {}))
    if "core_events" in saved:
        saved["core_events"] = normalize_core_events(saved["core_events"])
    # Older bundles explicitly mean the original fixed-window target.
    saved.setdefault("prediction_days", saved.get("churn_inactivity_days"))
    saved.setdefault("label_target", "window_inactive")
    saved.setdefault("cohort", "all")
    config = {}
    for key in DEFINITION_FIELDS:
        supplied = getattr(args, key)
        if key in saved and supplied is not None and supplied != saved[key]:
            parser.error(f"--{key.replace('_', '-')} differs from the saved training definition")
        config[key] = saved.get(key, supplied)
    if any(config[k] is None for k in ("churn_days", "core_events", "session_gap_minutes", "label_criterion")):
        parser.error("legacy model lacks feature_config; supply W, core events, session gap and label criterion")
    return config


def validate_operational_snapshot(snapshot_time, bundle, *, timezone=None):
    """Require an elapsed cutoff with all fitting labels already available."""
    snapshot = pd.Timestamp(snapshot_time)
    if pd.isna(snapshot):
        raise ValueError("scoring snapshot time must be a valid timestamp")
    now = pd.Timestamp.now(tz=snapshot.tz or timezone)
    if snapshot.tz is None:
        now = now.tz_localize(None)
    if snapshot > now:
        raise ValueError("scoring snapshot time cannot be in the future")
    config = bundle.get("feature_config", {})
    for key in ("training_obs_end", "calibration_obs_end"):
        if config.get(key):
            end = pd.Timestamp(config[key])
            if pd.isna(end):
                raise ValueError(f"saved {key} is not a valid timestamp")
            try:
                too_early = snapshot < end
            except TypeError as exc:
                raise ValueError("score and saved model timestamps must use consistent timezones") from exc
            if too_early:
                raise ValueError(f"scoring snapshot precedes {key}; the model used labels from after this prediction time")


def run_pipeline(resources: ExitStack):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("train", "score"), default="train")
    ap.add_argument("--events", default="events.csv")
    ap.add_argument("--project-config", help="confirmed project/export JSON; required when reusing a contracted model")
    ap.add_argument("--calibration-project-config", help="declaration for a separate calibration export")
    ap.add_argument("--test-project-config", help="declaration for a separate test export")
    ap.add_argument("--audience-users", help="score-mode CSV with user_id; retain every requested user in the final result")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--data-kind", choices=("real", "simulated"), help="label supplied event data; --sample implies simulated")
    ap.add_argument("--output-dir", default=".")
    ap.add_argument("--model", help="saved model to reuse in score mode")
    ap.add_argument("--model-type", choices=("auto", "logistic_regression", "lightgbm", "xgboost", "random_forest"), default="auto")
    ap.add_argument("--churn-days", type=int, help="feature observation length W")
    ap.add_argument("--core-events")
    ap.add_argument("--session-gap-minutes", type=int)
    ap.add_argument("--churn-inactivity-days", "--label-future-days", dest="churn_inactivity_days", type=int, help="inactivity threshold D")
    ap.add_argument("--prediction-days", type=int, help="independent prediction horizon H")
    ap.add_argument("--label-target", choices=("window_inactive", "churn_onset"))
    ap.add_argument("--cohort", choices=("all", "prevention", "winback"))
    ap.add_argument("--label-criterion", choices=("any", "core", "pay"))
    ap.add_argument("--obs-end", required=True, help="exclusive T+H for train; T for score")
    ap.add_argument("--data-end", help="verified exclusive event-coverage endpoint")
    ap.add_argument("--calibration-events", help="defaults to --events when calibration date is supplied")
    ap.add_argument("--calibration-obs-end", help="exclusive calibration T+H, separated from training")
    ap.add_argument("--calibration-data-end")
    ap.add_argument("--calibration-method", choices=("sigmoid", "isotonic"), default="sigmoid")
    ap.add_argument("--test-events", help="defaults to --events when test date is supplied")
    ap.add_argument("--test-obs-end", help="exclusive test T+H, separated from calibration/training")
    ap.add_argument("--test-data-end")
    ap.add_argument("--high", type=float, default=0.6)
    ap.add_argument("--medium", type=float, default=0.3)
    ap.add_argument("--top-k", type=int, help="candidate capacity; select at most K users by risk")
    ap.add_argument("--min-contact-score", type=float, default=0.0)
    ap.add_argument("--risk-filter", choices=("High", "Medium", "Low"), default="High")
    ap.add_argument("--diagnostics", action="store_true",
                    help="retain intermediate files and write diagnostic reports in the original flat layout")
    ap.add_argument("--skip-explain", action="store_true", help="omit feature explanations from --diagnostics")
    args = ap.parse_args()
    try:
        contract, project_coverage = load_project_config(args.project_config) if args.project_config else (None, None)
    except (ValueError, OSError, KeyError) as exc:
        ap.error(str(exc))
    if args.sample and contract is not None:
        ap.error("--sample cannot declare an external project mapping")
    if contract is not None and args.core_events is None:
        args.core_events = ",".join(contract["core_events"])
    for phase in ("calibration", "test"):
        if getattr(args, f"{phase}_project_config") and not getattr(args, f"{phase}_events"):
            ap.error(f"--{phase}-project-config requires --{phase}-events")
        if getattr(args, f"{phase}_project_config") and contract is None:
            ap.error(f"--{phase}-project-config requires the training --project-config")
    if args.audience_users and (args.mode != "score" or args.sample):
        ap.error("--audience-users requires score mode with supplied events, not --sample")
    if args.core_events is not None:
        args.core_events = normalize_core_events(args.core_events)
    if not 0 <= args.medium < args.high <= 1 or not 0 <= args.min_contact_score <= 1:
        ap.error("risk thresholds must satisfy 0 <= medium < high <= 1; contact floor must be in [0,1]")
    if args.top_k is not None and args.top_k <= 0:
        ap.error("--top-k must be positive")
    if args.mode == "score":
        if not args.model:
            ap.error("--mode score requires --model")
        if any(getattr(args, name) for name in ("calibration_events", "calibration_obs_end", "test_events", "test_obs_end")):
            ap.error("score mode does not accept training/calibration/test datasets")
        model_path = Path(args.model).resolve()
        bundle = joblib.load(model_path)
        try:
            compare_contracts(bundle.get("feature_config", {}).get("source_contract"), contract)
            validate_operational_snapshot(args.obs_end, bundle, timezone=contract["timezone"] if contract else None)
        except ValueError as exc:
            ap.error(str(exc))
        config = scoring_config(args, bundle, ap)
    else:
        if args.model:
            ap.error("--model is for score mode; training writes output-dir/churn_model.pkl")
        if args.churn_days is None or args.churn_inactivity_days is None:
            ap.error("training requires --churn-days W and --churn-inactivity-days D")
        config = training_config(args)
        if args.calibration_events and not args.calibration_obs_end:
            ap.error("--calibration-events requires --calibration-obs-end")
        if args.test_events and not args.test_obs_end:
            ap.error("--test-events requires --test-obs-end")
        previous_end = pd.Timestamp(args.obs_end)
        for name, end in (("calibration", args.calibration_obs_end), ("future holdout", args.test_obs_end)):
            if end:
                snapshot = pd.Timestamp(end) - pd.Timedelta(days=config["prediction_days"])
                if snapshot < previous_end:
                    ap.error(f"{name} snapshot T must be >= the preceding label-window end")
                previous_end = pd.Timestamp(end)
        config["calibration_obs_end"] = args.calibration_obs_end
        config["test_obs_end"] = args.test_obs_end
    for name in ("churn_days", "session_gap_minutes", "churn_inactivity_days", "prediction_days"):
        if config.get(name) is not None and config[name] <= 0:
            ap.error(f"--{name.replace('_', '-')} must be positive")
    if config["label_target"] == "churn_onset" and config["cohort"] != "prevention":
        ap.error("churn_onset requires --cohort prevention")
    if config["cohort"] != "all" and config.get("churn_inactivity_days") is None:
        ap.error("cohort filtering requires an inactivity threshold D")
    if args.audience_users and config.get("churn_inactivity_days") is None:
        ap.error("audience current-state classification requires a saved inactivity threshold D")

    audience = read_csv(Path(args.audience_users).resolve()) if args.audience_users else None

    output = Path(args.output_dir).resolve()
    work = output if args.diagnostics else output / "work"
    work.mkdir(parents=True, exist_ok=True)
    scratch = work if args.diagnostics else Path(resources.enter_context(
        TemporaryDirectory(prefix="value-risk-")))
    paths = {key: scratch / name for key, name in {
        "features": "user_features.csv", "rec": "model_recommendation.json",
        "segments": "high_risk_segments.csv", "shap": "shap_local.csv",
        "report": "retention_strategy_report.md", "config": "feature_config.json",
        "test": "future_evaluation_features.csv", "calibration": "calibration_features.csv"}.items()}
    paths.update(pred=output / "churn_prediction_result.csv", model=output / "churn_model.pkl",
                 candidates=output / "contact_candidates.csv", metrics=work / "model_metrics.json",
                 prediction_meta=work / "prediction_metadata.json")
    events = Path(args.events).resolve()
    if args.sample:
        events = work / "sample_events.csv"
        end = max(pd.Timestamp(value) for value in
                  (args.obs_end, args.calibration_obs_end, args.test_obs_end) if value)
        run("make_sample_events.py", ["--output", events, "--end", end.isoformat()], "generate sample data")
        args.data_end = end.isoformat()
    event_provenance = csv_data_kind(events, "simulated" if args.sample else args.data_kind)

    # Validate every source before training or writing new prediction artifacts.
    # A declared source does not inherit a different file's coverage evidence.
    checks = {}
    phases = [("score" if args.mode == "score" else "training", events, args.obs_end,
               args.data_end, contract, project_coverage, args.mode == "train")]
    try:
        for phase in ("calibration", "test"):
            end = getattr(args, f"{phase}_obs_end")
            if end:
                source_arg = getattr(args, f"{phase}_events")
                phase_path = Path(source_arg).resolve() if source_arg else events
                declaration = getattr(args, f"{phase}_project_config")
                if contract is not None and source_arg and not declaration:
                    raise ValueError(f"separate {phase} export requires --{phase}-project-config")
                phase_contract, phase_coverage = load_project_config(declaration) if declaration else (contract, project_coverage)
                compare_contracts(contract, phase_contract)
                phases.append((phase, phase_path, end, getattr(args, f"{phase}_data_end") or
                               (args.data_end if phase_path == events else None),
                               phase_contract, phase_coverage, True))
        for phase, source, end, bound, source_contract, source_coverage, labeled in phases:
            T = pd.Timestamp(end) - pd.Timedelta(days=config["prediction_days"]) if labeled else end
            checks[phase] = preflight_events(
                read_csv(source), config, T, source_contract, source_coverage, bound,
                labeled=labeled, allow_empty=audience is not None)
            if source_coverage is not None and not checks[phase]["errors"] and bound is None:
                setattr(args, "data_end" if phase in ("training", "score") else f"{phase}_data_end",
                        source_coverage["end"])
    except (ValueError, OSError, KeyError) as exc:
        ap.error(str(exc))
    quality = {"status": "blocked" if any(c["errors"] for c in checks.values()) else
               "warning" if any(c["warnings"] for c in checks.values()) else "ok", "phases": checks}
    quality_path = work / "data_quality_report.json"
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    if contract is not None:
        (work / "project_config.json").write_text(json.dumps(
            {**contract, **({"coverage": project_coverage} if project_coverage is not None else {})},
            ensure_ascii=False, indent=2), encoding="utf-8")
        config["source_contract"] = contract
    for phase, check in checks.items():
        for warning in check["warnings"]:
            print(f"[data quality: {phase}] {warning}", flush=True)
    if quality["status"] == "blocked":
        ap.error("data preflight blocked: " + "; ".join(
            f"{phase}: {error}" for phase, check in checks.items() for error in check["errors"]))
    if args.mode == "score" and contract is not None and not bundle.get("feature_config", {}).get("source_contract"):
        checks["score"]["warnings"].append("Current export checked, but legacy training semantics cannot be verified retrospectively.")
        checks["score"]["contract_status"] = "legacy_training_unverified"
        checks["score"]["status"] = quality["status"] = "warning"
        quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")

    def build(source, destination, end, coverage, labeled, activity_evidence=None):
        require_columns(source, ["user_id", "event_name", "event_time"], "feature engineering")
        options = ["--input", source, "--output", destination, "--churn-days", config["churn_days"],
                   "--core-events", config["core_events"], "--session-gap-minutes", config["session_gap_minutes"],
                   "--label-criterion", config["label_criterion"], "--obs-end", end,
                   "--label-target", config["label_target"], "--cohort", config["cohort"]]
        if config.get("churn_inactivity_days") is not None:
            options += ["--churn-inactivity-days", config["churn_inactivity_days"]]
        if config.get("prediction_days") is not None:
            options += ["--prediction-days", config["prediction_days"]]
        if not labeled:
            options += ["--score-only"]
        if activity_evidence is not None:
            options += ["--activity-evidence", activity_evidence]
        if coverage:
            options += ["--data-end", coverage]
        if contract is not None:
            options += ["--timezone", contract["timezone"]]
        run("churn_feature_engineering.py", options, "build labeled features" if labeled else "build scoring features")

    if audience is not None:
        event_provenance = resolve_data_kind(args.data_kind, frames=[
            ("events", pd.DataFrame({"data_kind": [event_provenance["data_kind"]]})), ("audience", audience)])
        try:
            audience_activity = resolve_audience_activity(
                audience, read_csv(events, usecols=lambda column: column in
                                   ("user_id", "event_name", "event_time", "pay_amount")), args.obs_end, config)
        except (ValueError, TypeError, AttributeError) as exc:
            ap.error(str(exc))
        reference = scratch / "reference_user_features.csv"
        activity_evidence = scratch / "audience_activity.csv"
        audience_activity[["user_id", "snapshot_time", "last_qualifying_event_time"]].to_csv(activity_evidence, index=False)
        require_columns(events, ["user_id", "event_name", "event_time"], "audience feature engineering")
        if read_csv(events, nrows=1).empty:
            if args.data_end is not None and pd.Timestamp(args.obs_end) > pd.Timestamp(args.data_end):
                ap.error("scoring snapshot is beyond --data-end")
            pd.DataFrame(columns=["user_id", *FEATURE_COLS]).to_csv(reference, index=False)
        else:
            build(events, reference, args.obs_end, args.data_end, False, activity_evidence=activity_evidence)
        reference_features = read_csv(reference)
        # Do not recompute percentiles, z-scores or pay tiers on the requested subset.
        can_score = audience_activity.model_cohort_compatible & ~audience_activity.activity_missing_from_event_export
        scoring_clock = audience_activity.loc[can_score].set_index("user_id").last_qualifying_event_time
        target_features = reference_features[reference_features.user_id.isin(scoring_clock.index)].copy()
        if config["label_target"] == "churn_onset":
            target_features["last_qualifying_event_time"] = scoring_clock.reindex(target_features.user_id).array
        target_features["data_kind"] = event_provenance["data_kind"]
        target_features.to_csv(paths["features"], index=False)
    else:
        build(events, paths["features"], args.obs_end, args.data_end, args.mode == "train")
    if args.mode == "train":
        config["training_data_kind"] = event_provenance["data_kind"]
        phase_kinds = [event_provenance["data_kind"]]
        for kind, source_arg, end_arg in (("calibration", args.calibration_events, args.calibration_obs_end),
                                         ("test", args.test_events, args.test_obs_end)):
            if end_arg:
                provenance = csv_data_kind(Path(source_arg).resolve(), args.data_kind) if source_arg else event_provenance
                config[f"{kind}_data_kind"] = provenance["data_kind"]
                phase_kinds.append(provenance["data_kind"])
        config["evaluation_data_kind"] = resolve_data_kind(
            frames=[("modeling_phases", pd.DataFrame({"data_kind": phase_kinds}))])["data_kind"]
        paths["config"].write_text(json.dumps(config, indent=2), encoding="utf-8")
        run("auto_model_selection.py", ["--input", paths["features"], "--output", paths["rec"],
                                        "--model-type", args.model_type], "select model")
        options = ["--input", paths["features"], "--rec", paths["rec"], "--output", paths["model"],
                   "--feature-config", paths["config"], "--metrics-output", paths["metrics"],
                   "--calibration-method", args.calibration_method]
        if not args.diagnostics:
            options.append("--skip-report")
        if args.top_k is not None:
            options += ["--top-k", args.top_k]
        for kind, source_arg, end_arg, coverage_arg in (
                ("calibration", args.calibration_events, args.calibration_obs_end, args.calibration_data_end),
                ("test", args.test_events, args.test_obs_end, args.test_data_end)):
            if end_arg:
                source = Path(source_arg).resolve() if source_arg else events
                coverage = coverage_arg or (args.data_end if source == events else None)
                build(source, paths[kind], end_arg, coverage, True)
                options += ["--calibration-features" if kind == "calibration" else "--evaluation-features", paths[kind]]
        run("train_churn_model.py", options, "train, calibrate and evaluate")
        model_path = paths["model"]

    scored_predictions = scratch / "scored_prediction_result.csv" if audience is not None else paths["pred"]
    options = ["--input", paths["features"], "--model", model_path, "--output", scored_predictions,
               "--high", args.high, "--medium", args.medium, "--metadata-output", paths["prediction_meta"],
               "--snapshot-time", (pd.Timestamp(args.obs_end) - pd.Timedelta(days=config["prediction_days"])).isoformat()
               if args.mode == "train" else args.obs_end]
    if audience is not None and (bundle["name"] == "heuristic" or bundle.get("model") is None):
        options += ["--reference-features", reference]
    if event_provenance["data_kind"] != "unknown":
        options += ["--data-kind", event_provenance["data_kind"]]
    if args.top_k is not None:
        options += ["--top-k", args.top_k, "--min-contact-score", args.min_contact_score,
                    "--candidates-output", paths["candidates"]]
    run("predict_churn_risk.py", options, "score risk and select candidates")
    metadata = json.loads(paths["prediction_meta"].read_text(encoding="utf-8"))
    metadata["score_scope"] = "training_snapshot" if args.mode == "train" else "new_snapshot"
    if audience is not None:
        complete, coverage, _ = complete_audience_results(
            audience, None, read_csv(scored_predictions), args.obs_end, config,
            event_provenance["data_kind"], activity=audience_activity)
        for field in ("scoring_data_kind", "model_training_data_kind", "model_calibration_data_kind"):
            if field in metadata:
                complete[field] = metadata[field]
        complete.to_csv(paths["pred"], index=False)
        metadata.update(users=len(complete), scored_users=coverage["scored_users"],
                        audience_coverage=coverage, **event_provenance)
        metadata["audience"] = {"source_file": str(Path(args.audience_users).resolve()),
                                "snapshot_time": args.obs_end,
                                "reference_feature_users": len(reference_features),
                                "feature_reference": "all supplied events under the saved cohort, before audience filtering"}
        if args.diagnostics:
            (work / "audience_coverage.json").write_text(json.dumps(
                {**coverage, **event_provenance, "snapshot_time": args.obs_end},
                ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    metadata["data_quality"] = quality
    paths["prediction_meta"].write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"\nResults: {paths['pred']}", flush=True)
    if not args.diagnostics:
        return

    options = ["--pred", paths["pred"], "--features", paths["features"], "--output", paths["segments"],
               "--risk-filter", args.risk_filter]
    if args.top_k is not None:
        options += ["--selected-only"]
    run("segment_high_risk.py", options, "segment selected population")
    if not args.skip_explain:
        run("explain_churn.py", ["--input", paths["features"], "--model", model_path,
                                "--segments", paths["segments"], "--out-csv", paths["shap"],
                                "--out-segment-csv", output / "shap_by_segment.csv",
                                "--out-png", output / "shap_global.png"], "explain drivers")
    require_columns(paths["segments"], ["user_id", "persona_tag"], "strategy report")
    options = ["--segments", paths["segments"], "--output", paths["report"],
               "--prediction-metadata", paths["prediction_meta"],
               "--score-scope", metadata["score_scope"]]
    if not args.skip_explain:
        options += ["--shap", paths["shap"], "--shap-by-segment", output / "shap_by_segment.csv"]
    else:
        options += ["--shap", "", "--shap-by-segment", ""]
    run("recommend_strategy.py", options, "write strategy report")
    print(f"\nDone. Report: {paths['report']}")


def main():
    with ExitStack() as resources:
        run_pipeline(resources)


if __name__ == "__main__":
    main()
