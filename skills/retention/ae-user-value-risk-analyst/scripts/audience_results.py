"""Keep every requested user while separating observed state from future risk."""
from numbers import Integral

import numpy as np
import pandas as pd

from churn_feature_engineering import _parse_endpoint, qualifying_events
from data_provenance import resolve_data_kind
from event_time import parse_timestamps


def prepare_audience(audience):
    """Preserve opaque IDs and first-occurrence order; report duplicate membership."""
    if "user_id" not in audience or audience.user_id.isna().any():
        raise ValueError("audience requires non-null user_id")
    result = audience.copy()
    result["user_id"] = result.user_id.astype(str)
    if result.user_id.str.strip().eq("").any():
        raise ValueError("audience user_id must be nonempty")
    # Conflicting state evidence must not depend on which duplicate happens first.
    for column in ("last_qualifying_event_time", "snapshot_time"):
        if column in result and (result.groupby("user_id")[column].nunique(dropna=False) > 1).any():
            raise ValueError(f"duplicate audience users have conflicting {column}")
    return result.drop_duplicates("user_id", keep="first").reset_index(drop=True)


def resolve_audience_activity(audience, events, snapshot_time, config):
    """Resolve the as-of clock and its implications before using model features."""
    audience = prepare_audience(audience)
    D = config.get("churn_inactivity_days")
    if isinstance(D, (bool, np.bool_)) or not isinstance(D, Integral) or D <= 0:
        raise ValueError("complete audience results require a positive inactivity threshold D")
    T = pd.Timestamp(snapshot_time)
    if pd.isna(T):
        raise ValueError("audience snapshot_time must be a valid timestamp")
    if "snapshot_time" in audience:
        if not audience.snapshot_time.map(lambda value: _parse_endpoint(value, "audience snapshot_time", T.tz) == T).all():
            raise ValueError("audience snapshot_time differs from scoring snapshot")
    required = {"user_id", "event_name", "event_time"}
    if not required.issubset(events) or events[list(required)].isna().any().any():
        raise ValueError("audience events require non-null user_id, event_name and event_time")
    events = events.copy()
    events["user_id"] = events.user_id.astype(str)
    contract = config.get("source_contract") or {}
    project_timezone = contract.get("timezone")
    if events.empty:
        timezone = project_timezone if project_timezone is not None and T.tz is not None else T.tz
        events["event_time"] = pd.Series(pd.DatetimeIndex([], tz=timezone), index=events.index)
    else:
        events["event_time"] = parse_timestamps(events.event_time, "audience event_time",
                                                project_timezone=project_timezone)
    T = _parse_endpoint(T, "snapshot_time", events.event_time.dt.tz)
    historical = events[events.event_time < T]
    criterion = config.get("label_criterion", "any")
    core = config.get("core_events")
    if isinstance(core, str):
        core = {s.strip() for s in core.split(",") if s.strip()}
    if criterion == "pay" and "pay_amount" in historical:
        historical = historical.copy()
        historical["pay_amount"] = pd.to_numeric(historical.pay_amount, errors="raise").fillna(0)
        if not np.isfinite(historical.pay_amount).all():
            raise ValueError("pay_amount must be finite")
    if historical.empty:
        qualified = historical
    else:
        qualified = qualifying_events(historical, criterion, core)
    observed_last = qualified.groupby("user_id", observed=True).event_time.max()
    result = audience[["user_id"]].copy()
    last = observed_last.reindex(result.user_id)
    last.index = result.index
    source = pd.Series(np.where(last.notna(), "events", "unknown"), index=result.index)
    if "last_qualifying_event_time" in audience:
        supplied = audience.last_qualifying_event_time.map(
            lambda value: pd.NaT if pd.isna(value) else _parse_endpoint(value, "audience last activity", T.tz))
        supplied = pd.to_datetime(supplied)
        if supplied.notna().any():
            if supplied[supplied.notna()].ge(T).any():
                raise ValueError("audience last qualifying activity must be strictly before T")
            use_supplied = supplied.notna() & (last.isna() | supplied.gt(last))
            last = last.where(~use_supplied, supplied)
            source.loc[use_supplied] = "audience_snapshot"
    elapsed = T - last
    known = last.notna()
    already = known & elapsed.ge(pd.Timedelta(days=int(D)))
    current_status = pd.Series("unknown", index=result.index)
    current_status.loc[known & ~already] = "not_churned"
    current_status.loc[already] = "already_churned"

    cohort = config.get("cohort", "all")
    result["snapshot_time"] = T.isoformat()
    result["current_status"] = current_status
    result["last_qualifying_event_time"] = last
    result["last_activity_source"] = source
    result["inactivity_days"] = elapsed.dt.total_seconds() / 86400
    result["has_event_history"] = result.user_id.isin(historical.user_id)
    result["model_cohort_compatible"] = (known & ~already if cohort == "prevention" else
                                         already if cohort == "winback" else True)
    W = config.get("churn_days")
    result["activity_missing_from_event_export"] = (
        source.eq("audience_snapshot") & last.ge(T - pd.Timedelta(days=W)) if W is not None else False
    )
    if config.get("label_target") == "churn_onset":
        H = config.get("prediction_days") or D
        reachable = last + pd.Timedelta(days=int(D)) < T + pd.Timedelta(days=int(H))
        result["onset_reachable_within_horizon"] = reachable.astype("boolean").where(known & ~already)
    return result


def complete_audience_results(audience, events, predictions, snapshot_time, config, data_kind=None, *, activity=None):
    """Left-join the requested audience onto scores using its resolved activity."""
    if activity is None:
        activity = resolve_audience_activity(audience, events, snapshot_time, config)
    result = activity[["user_id"]].copy()
    predictions = predictions.copy()
    if "user_id" not in predictions or predictions.user_id.isna().any():
        raise ValueError("predictions require non-null user_id")
    predictions["user_id"] = predictions.user_id.astype(str)
    if predictions.user_id.duplicated().any() or not predictions.user_id.isin(result.user_id).all():
        raise ValueError("predictions must contain unique users within the requested audience")
    if not {"churn_probability", "risk_level"}.issubset(predictions):
        raise ValueError("predictions require churn_probability and risk_level")
    if len(predictions):
        probability = pd.to_numeric(predictions.churn_probability, errors="raise")
        if not np.isfinite(probability).all() or not probability.between(0, 1).all():
            raise ValueError("scored probabilities must be finite and within [0,1]")
        predictions["churn_probability"] = probability
        if not predictions.risk_level.isin(["High", "Medium", "Low"]).all():
            raise ValueError("scored risk_level must be High, Medium or Low")
    columns = [c for c in ("user_id", "churn_probability", "model_probability", "onset_reachable_within_horizon",
                           "probability_constraint", "risk_level", "risk_rank", "selected_for_contact")
               if c in predictions]
    result = result.merge(predictions[columns], on="user_id", how="left", validate="one_to_one", sort=False)
    scored = result.churn_probability.notna()
    known = activity.last_qualifying_event_time.notna()
    already = activity.current_status.eq("already_churned")
    compatible = activity.model_cohort_compatible
    missing_activity = activity.activity_missing_from_event_export
    if (scored & ~compatible).any():
        raise ValueError("scored users contradict the saved model cohort")
    if (scored & missing_activity).any():
        raise ValueError("scored users lack a verified activity in the exported feature window")
    if "selected_for_contact" in result:
        present = result.selected_for_contact.dropna().astype(str).str.lower()
        if not present.isin(["true", "false", "1", "0", "1.0", "0.0"]).all():
            raise ValueError("selected_for_contact must contain booleans")
        result["selected_for_contact"] = result.selected_for_contact.astype("string").str.lower().isin(["true", "1", "1.0"])
    else:
        result["selected_for_contact"] = False
    state_columns = ["snapshot_time", "current_status", "last_qualifying_event_time", "last_activity_source",
                     "inactivity_days"]
    result[state_columns] = activity[state_columns]
    if "onset_reachable_within_horizon" in activity:
        reachable = activity.onset_reachable_within_horizon
        unreachable = reachable.eq(False).fillna(False)
        if (unreachable & ((scored & result.churn_probability.ne(0)) | result.selected_for_contact)).any():
            raise ValueError("scored onset forecasts contradict the resolved last-activity clock")
        result["onset_reachable_within_horizon"] = reachable
        if "probability_constraint" in result:
            result.loc[scored, "probability_constraint"] = np.where(unreachable[scored], "onset_unreachable", "none")
    result["prediction_status"] = "insufficient_observation_history"
    result["status_reason"] = "No compatible feature row was available; no probability was imputed."
    no_history = ~activity.has_event_history & ~known
    result.loc[~known, ["prediction_status", "status_reason"]] = [
        "no_qualifying_history", "No known qualifying activity before T; missing history is not observed churn."]
    result.loc[no_history, ["prediction_status", "status_reason"]] = [
        "no_event_history", "No observed pre-T history or verified last-activity snapshot."]
    result.loc[known & ~compatible, ["prediction_status", "status_reason"]] = [
        "outside_model_cohort", "Current state is outside the saved model cohort."]
    result.loc[compatible & missing_activity, ["prediction_status", "status_reason"]] = [
        "activity_missing_from_event_export",
        "Verified qualifying activity is missing from the exported feature window. Model scoring requires the event history."]
    result.loc[scored, ["prediction_status", "status_reason"]] = ["scored", "Future risk estimated by the saved model."]
    if "probability_constraint" in result:
        result.loc[scored & result.probability_constraint.eq("onset_unreachable"), "status_reason"] = (
            "Onset cannot occur within [T,T+H) under the saved definition; final probability is zero.")
    result["result_label"] = "insufficient_data"
    result.loc[known & ~compatible, "result_label"] = "not_applicable_to_model"
    result.loc[scored, "result_label"] = result.loc[scored, "risk_level"].map(
        {"High": "churn_risk_high", "Medium": "churn_risk_medium", "Low": "churn_risk_low"}).astype(object)
    result.loc[already, "result_label"] = "already_churned"
    sources = [("audience", audience), ("predictions", predictions)]
    if events is not None:
        sources.append(("events", events))
    provenance = resolve_data_kind(data_kind, frames=sources)
    result["data_kind"] = provenance["data_kind"]
    coverage = {"input_rows": len(audience), "target_users": len(result),
                "duplicate_memberships": len(audience) - len(result), "scored_users": int(scored.sum()),
                "unscored_users": int((~scored).sum()),
                "current_status_counts": result.current_status.value_counts().to_dict(),
                "result_label_counts": result.result_label.value_counts().to_dict(),
                "prediction_status_counts": result.prediction_status.value_counts().to_dict(),
                "state_note": "Current state is inferred from supplied as-of-T activity evidence; missing records do not prove churn.",
                "probability_note": "Probabilities describe the saved future target; observed churn is not a synthetic 100% prediction."}
    return result, coverage, provenance
