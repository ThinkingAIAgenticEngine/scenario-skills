#!/usr/bin/env python3
"""Deterministic diagnosis model for data-delay reports."""

from __future__ import annotations

import copy
import math
from typing import Any


RESULT_SCHEMA_VERSION = "2.0"
REPORT_CONTRACT_VERSION = "2.0"

UPLOAD_SEGMENT = "event_to_receive"
WAREHOUSE_SEGMENT = "receive_to_warehouse"
END_TO_END_SEGMENT = "event_to_warehouse"

EXPECTED_SECONDS = 300
LONG_DELAY_SECONDS = 3_600
SMALL_DELAY_SHARE = 0.01
TOP_CONTRIBUTOR_SHARE = 0.50

DECISION_POLICY = {
    "expected_seconds": EXPECTED_SECONDS,
    "long_delay_observation_seconds": LONG_DELAY_SECONDS,
    "small_delay_share": SMALL_DELAY_SHARE,
    "top_contributor_share": TOP_CONTRIBUTOR_SHARE,
    "long_delay_is_not_delay_verdict_threshold": True,
}


class ReportModelError(ValueError):
    pass


def as_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def as_count(value: Any) -> int:
    number = as_number(value)
    return int(number) if number is not None else 0


def measured(segment: dict[str, Any] | None) -> bool:
    return bool(segment and segment.get("status") == "measured" and sample_count(segment) > 0)


def sample_count(population: dict[str, Any] | None) -> int:
    return as_count((population or {}).get("sample_count"))


def bucket_count(population: dict[str, Any] | None, bucket: str) -> int:
    return as_count(((population or {}).get("distribution") or {}).get(bucket))


def bucket_share(population: dict[str, Any] | None, bucket: str) -> float:
    total = sample_count(population)
    return bucket_count(population, bucket) / total if total else 0.0


def is_v2_distribution(population: dict[str, Any] | None) -> bool:
    return "b7" in ((population or {}).get("distribution") or {})


def expected_count(population: dict[str, Any] | None) -> int | None:
    if not is_v2_distribution(population):
        return None
    return bucket_count(population, "b1")


def delayed_count(population: dict[str, Any] | None) -> int | None:
    if not is_v2_distribution(population):
        return None
    return sum(bucket_count(population, f"b{i}") for i in range(2, 8))


def long_delay_count(population: dict[str, Any] | None) -> int:
    if is_v2_distribution(population):
        return sum(bucket_count(population, key) for key in ("b5", "b6", "b7"))
    return sum(bucket_count(population, key) for key in ("b4", "b5", "b6"))


def share(count: int | None, population: dict[str, Any] | None) -> float | None:
    total = sample_count(population)
    return (count / total) if count is not None and total else None


def p95_seconds(population: dict[str, Any] | None) -> float | None:
    return as_number(((population or {}).get("seconds") or {}).get("p95"))


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "未统计"
    if 0 < value < 0.0001:
        return "不足 0.01%"
    return f"{value * 100:.2f}%"


def duration_label(seconds: int) -> str:
    if seconds % 60 == 0:
        return f"{seconds // 60}分钟"
    return f"{seconds}秒"


def segment_judgement(segment: dict[str, Any] | None, label: str, expected_seconds: int) -> dict[str, Any]:
    threshold = duration_label(expected_seconds)
    if not measured(segment):
        return {
            "code": "not_measured",
            "sample_count": sample_count(segment),
            "expected_count": None,
            "expected_share": None,
            "delayed_count": None,
            "delayed_share": None,
            "long_delay_count": 0,
            "long_delay_share": None,
            "text": f"{label}未取得可用测量结果。",
        }

    expected = expected_count(segment)
    delayed = delayed_count(segment)
    long_count = long_delay_count(segment)
    expected_share = share(expected, segment)
    delayed_share = share(delayed, segment)
    long_share = share(long_count, segment)
    if delayed is None:
        code = "legacy_threshold_unavailable"
        text = f"{label}使用旧分桶结果，无法判断{threshold}内符合预期的比例；1小时及以上占{fmt_pct(long_share)}。"
    elif delayed == 0:
        code = "no_delay_observed"
        text = f"{label}中{fmt_pct(expected_share)}的数据在{threshold}内完成，视为不存在延迟；未观察到超过{threshold}的数据。"
    elif (delayed_share or 0) < SMALL_DELAY_SHARE:
        code = "small_delay_present"
        text = (
            f"{label}中{fmt_pct(expected_share)}的数据在{threshold}内完成，视为不存在延迟；"
            f"{fmt_pct(delayed_share)}的数据超过{threshold}，存在少量延迟，其中{fmt_pct(long_share)}达到1小时及以上。"
        )
    else:
        code = "delay_present"
        text = (
            f"{label}中{fmt_pct(expected_share)}的数据在{threshold}内完成，视为不存在延迟；"
            f"{fmt_pct(delayed_share)}的数据超过{threshold}，存在一定比例延迟，其中{fmt_pct(long_share)}达到1小时及以上。"
        )
    return {
        "code": code,
        "sample_count": sample_count(segment),
        "expected_count": expected,
        "expected_share": expected_share,
        "delayed_count": delayed,
        "delayed_share": delayed_share,
        "long_delay_count": long_count,
        "long_delay_share": long_share,
        "p95_seconds": p95_seconds(segment),
        "text": text,
    }


def validate_result(result: dict[str, Any], *, strict: bool = True) -> list[str]:
    if not isinstance(result, dict):
        raise ReportModelError("result must be a JSON object")
    version = result.get("schema_version")
    if version not in (None, "1.0", RESULT_SCHEMA_VERSION):
        raise ReportModelError(f"unsupported result schema_version: {version}")
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(result.get("window"), dict):
        errors.append("window is required")
    if as_number(result.get("total_rows")) is not None and as_count(result.get("total_rows")) < 0:
        errors.append("total_rows must be non-negative")
    for key, population in (result.get("delay_segments") or {}).items():
        if not isinstance(population, dict):
            continue
        total = sample_count(population)
        distribution = population.get("distribution") or {}
        for bucket, value in distribution.items():
            number = as_number(value)
            if number is None or number < 0:
                errors.append(f"delay_segments.{key}.distribution.{bucket} must be non-negative")
        if total and distribution:
            distributed = sum(as_count(value) for value in distribution.values())
            if distributed != total:
                message = f"delay_segments.{key} distribution sums to {distributed}, expected {total}"
                (errors if strict else warnings).append(message)
    if errors:
        raise ReportModelError("; ".join(errors))
    return warnings


def derive_diagnosis(result: dict[str, Any]) -> dict[str, Any]:
    expected_seconds = as_count((result.get("decision_policy") or {}).get("expected_seconds")) or EXPECTED_SECONDS
    segments = result.get("delay_segments") or {}
    upload = segments.get(UPLOAD_SEGMENT) or {}
    warehouse = segments.get(WAREHOUSE_SEGMENT) or {}
    total = segments.get(END_TO_END_SEGMENT) or {}
    judgements = {
        "upload": segment_judgement(upload, "上报段", expected_seconds),
        "warehouse": segment_judgement(warehouse, "平台入库段", expected_seconds),
        "end_to_end": segment_judgement(total, "总延迟", expected_seconds),
    }

    up_share = judgements["upload"].get("delayed_share")
    wh_share = judgements["warehouse"].get("delayed_share")
    if up_share is None or wh_share is None:
        boundary_code = "not_localizable"
    elif up_share == 0 and wh_share == 0:
        boundary_code = "no_delay_boundary"
    elif up_share >= SMALL_DELAY_SHARE and wh_share >= SMALL_DELAY_SHARE:
        if up_share > wh_share:
            boundary_code = "both_segments_upload_higher"
        elif wh_share > up_share:
            boundary_code = "both_segments_warehouse_higher"
        else:
            boundary_code = "multiple_boundaries_similar"
    elif up_share > wh_share:
        boundary_code = "upload_dominant"
    elif wh_share > up_share:
        boundary_code = "warehouse_dominant"
    else:
        boundary_code = "multiple_boundaries_similar"
    threshold = duration_label(expected_seconds)
    boundary_text = {
        "upload_dominant": f"超过{threshold}的数据主要集中在上报段，延迟主要来源于事件发生到服务器收到之间。",
        "warehouse_dominant": f"超过{threshold}的数据主要集中在平台入库段，延迟主要来源于服务器收到到写入数仓之间。",
        "both_segments_upload_higher": f"上报段和平台入库段均存在一定比例延迟；上报段超过{threshold}的比例更高，但两个环节均需关注。",
        "both_segments_warehouse_higher": f"上报段和平台入库段均存在一定比例延迟；平台入库段超过{threshold}的比例更高，但两个环节均需关注。",
        "multiple_boundaries_similar": "上报段和平台入库段均存在相近比例的延迟，需要分别核查。",
        "no_delay_boundary": f"上报段和平台入库段均未观察到超过{threshold}的数据。",
        "not_localizable": "现有分段测量不足以判断延迟主要来源。",
    }

    return {
        "segments": judgements,
        "overall": copy.deepcopy(judgements["end_to_end"]),
        "boundary": {"code": boundary_code, "text": boundary_text[boundary_code]},
        "platform_ingestion": copy.deepcopy(judgements["warehouse"]),
    }


def derive_quality_issues(result: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    timezone = result.get("timezone_quality") or {}
    timestamp_zones = result.get("timestamp_zones") or {}
    server_zone = timestamp_zones.get("server_time") or {}
    warehouse_zone = timestamp_zones.get("dw_create_time") or {}
    if server_zone.get("offset") is None or warehouse_zone.get("offset") is None:
        issues.append({
            "code": "server_timezone_missing",
            "server_offset": server_zone.get("offset"),
            "warehouse_offset": warehouse_zone.get("offset"),
        })
    total = as_count(result.get("total_rows"))
    unconfirmed_missing = max(
        0,
        as_count(timezone.get("missing_count")) - as_count(timezone.get("confirmed_missing_count")),
    )
    if unconfirmed_missing:
        issues.append({
            "code": "timezone_missing",
            "count": unconfirmed_missing,
            "total": total,
            "valid": as_count(timezone.get("valid_count")),
        })
    if as_count(timezone.get("invalid_count")):
        issues.append({"code": "timezone_invalid", "count": as_count(timezone.get("invalid_count")), "total": total})
    segments = result.get("delay_segments") or {}
    anomaly_by_segment = {
        key: bucket_count(segments.get(key) or {}, "negative")
        for key in (UPLOAD_SEGMENT, WAREHOUSE_SEGMENT, END_TO_END_SEGMENT)
    }
    if any(anomaly_by_segment.values()):
        issues.append({"code": "time_anomaly", "by_segment": anomaly_by_segment})
    if result.get("server_time_semantics") not in (None, "row_level"):
        issues.append({"code": "receive_time_not_row_level"})
    if result.get("top_slow_events_note"):
        issues.append({"code": "top_events_unavailable"})
    return issues


def derive_evidence(result: dict[str, Any], diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    segments = result.get("delay_segments") or {}
    for key, code in (
        (UPLOAD_SEGMENT, "E_UPLOAD_SEGMENT"),
        (WAREHOUSE_SEGMENT, "E_WAREHOUSE_SEGMENT"),
        (END_TO_END_SEGMENT, "E_END_TO_END_SEGMENT"),
    ):
        segment = segments.get(key) or {}
        if measured(segment):
            evidence.append({
                "code": code,
                "sample_count": sample_count(segment),
                "expected_share": share(expected_count(segment), segment),
                "delayed_share": share(delayed_count(segment), segment),
                "long_delay_count": long_delay_count(segment),
                "long_delay_share": share(long_delay_count(segment), segment),
                "p95_seconds": p95_seconds(segment),
            })
    total_long = as_count(((diagnosis.get("segments") or {}).get("end_to_end") or {}).get("long_delay_count"))
    ranked = sorted(
        result.get("top_slow_events") or [],
        key=lambda item: (-as_count(item.get("end_to_end_ge_1h_count")), str(item.get("event", "")), str(item.get("data_source", ""))),
    )
    if total_long and ranked:
        top = ranked[0]
        contribution = as_count(top.get("end_to_end_ge_1h_count")) / total_long
        evidence.append({
            "code": "E_TOP_CONTRIBUTOR",
            "event": str(top.get("event") or ""),
            "data_source": str(top.get("data_source") or "未记录"),
            "long_delay_count": as_count(top.get("end_to_end_ge_1h_count")),
            "contribution_share": contribution,
        })
    coverage = result.get("sample_coverage") or {}
    evidence.append({
        "code": "E_TIMEZONE_COVERAGE",
        "covered_rows": as_count(coverage.get("zone_covered_rows")),
        "total_rows": as_count(coverage.get("total_rows")) or as_count(result.get("total_rows")),
        "covered_share": as_number(coverage.get("zone_covered_share")) or 0.0,
    })
    return evidence


def derive_recommendations(
    result: dict[str, Any],
    diagnosis: dict[str, Any],
    evidence: list[dict[str, Any]],
    quality_issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    evidence_by_code = {item["code"]: item for item in evidence}
    issue_codes = {item["code"] for item in quality_issues}
    top = evidence_by_code.get("E_TOP_CONTRIBUTOR")
    if top and (top.get("contribution_share") or 0) >= TOP_CONTRIBUTOR_SHARE:
        recommendations.append({
            "priority": "P0",
            "rule_id": "R_TOP_CONCENTRATION",
            "evidence": f"{top['event']}（{top['data_source']}）贡献了总延迟中1小时及以上数据的 {(top['contribution_share'] or 0) * 100:.2f}%",
            "action": "优先核对该事件的事件时间定义、上报节奏以及是否存在补录或批次写入。",
            "verification": "来源日志或事件定义能够解释该事件的长延迟分布。",
        })
    boundary_code = (diagnosis.get("boundary") or {}).get("code")
    if boundary_code == "upload_dominant":
        recommendations.append({
            "priority": "P0", "rule_id": "R_UPLOAD_DIRECTION",
            "evidence": diagnosis["boundary"]["text"],
            "action": "延迟边界位于客户端采集到 TE 集群接收之间。可能原因包括客户端无网络或网络较差、客户端缓存或批量发送、转接点到 TE 集群网络不稳定、历史数据补录；需结合日志验证。",
            "verification": "客户端采集/发送日志、缓存与 flush 配置、请求响应和重试日志、转接服务及网络监控能够解释超过预期阈值的数据；同范围复测观察到比例变化。",
        })
    elif boundary_code == "warehouse_dominant":
        recommendations.append({
            "priority": "P0", "rule_id": "R_WAREHOUSE_DIRECTION",
            "evidence": diagnosis["boundary"]["text"],
            "action": "延迟边界位于 TE 集群内部处理和入库链路。可能原因包括 Kafka 数据积压、消费或写入处理较慢、集群资源竞争、内部排队或重试；需结合运行指标验证。",
            "verification": "Kafka lag、消费速率、队列指标、入库任务日志、资源利用率或重试记录能够对应延迟日期和事件；同范围复测后比例下降。",
        })
    elif boundary_code in {"multiple_boundaries_similar", "both_segments_upload_higher", "both_segments_warehouse_higher"}:
        recommendations.append({
            "priority": "P0", "rule_id": "R_MULTI_DIRECTION",
            "evidence": diagnosis["boundary"]["text"],
            "action": "分别核对客户端采集到 TE 接收的上报链路，以及 TE 集群内部处理和入库链路，避免只处理其中一个环节。",
            "verification": "上报段取得客户端/网络/转接日志，入库段取得 Kafka/消费/写入/资源指标，并能分别解释超过预期阈值的数据。",
        })
    if "timezone_missing" in issue_codes or "timezone_invalid" in issue_codes:
        recommendations.append({
            "priority": "P1", "rule_id": "R_TIMEZONE_COVERAGE",
            "evidence": "部分数据没有有效时区信息，未参与上报段和总延迟统计",
            "action": "确认各上报方式的时区与事件时间定义，再决定是否补充或修正时区信息。",
            "verification": "重新测量时能够明确说明上报段和总延迟的覆盖范围。",
        })
    if "server_timezone_missing" in issue_codes:
        recommendations.append({
            "priority": "P1", "rule_id": "R_SERVER_TIMEZONE_CONFIRM",
            "evidence": "结果中缺少 #server_time 或 #dw_create_time 的已确认服务器时区",
            "action": "请用户确认服务器部署时区，并使用实际时区偏移重新测量。",
            "verification": "报告中的服务器时区来源显示为用户提供。",
        })
    if "time_anomaly" in issue_codes:
        recommendations.append({
            "priority": "P1", "rule_id": "R_TIME_ANOMALY",
            "evidence": "存在事件时间晚于后续时间的数据",
            "action": "核对来源时钟、事件时间生成、时区转换和历史数据写入规则。",
            "verification": "时间异常能够按来源解释，且不会被误计为正向延迟。",
        })
    if not measured((result.get("delay_segments") or {}).get(WAREHOUSE_SEGMENT) or {}):
        recommendations.append({
            "priority": "P2", "rule_id": "R_NO_WAREHOUSE_MEASUREMENT",
            "evidence": "本次未取得平台入库段测量结果",
            "action": "补充可验证的入库时间证据后再判断平台入库情况。",
            "verification": "能够取得服务器收到到写入数仓的分段数据。",
        })
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    recommendations.sort(key=lambda item: (priority_order.get(item["priority"], 9), item["rule_id"]))
    return recommendations


def enrich_result(result: dict[str, Any], *, strict: bool = True) -> dict[str, Any]:
    validate_result(result, strict=strict)
    enriched = copy.deepcopy(result)
    enriched["schema_version"] = RESULT_SCHEMA_VERSION
    enriched["report_contract_version"] = REPORT_CONTRACT_VERSION
    policy = copy.deepcopy(DECISION_POLICY)
    policy.update(enriched.get("decision_policy") or {})
    enriched["decision_policy"] = policy
    expected_seconds = as_count(policy.get("expected_seconds")) or EXPECTED_SECONDS
    threshold = duration_label(expected_seconds)
    event_name = str(enriched.get("event_name") or "全部事件")
    enriched["scope"] = {
        "project": {
            "id": enriched.get("project_id"),
            "name": enriched.get("project_name") or enriched.get("project_id") or "未提供",
            "host": enriched.get("host") or "未提供",
        },
        "window": copy.deepcopy(enriched.get("window") or {}),
        "events": {"mode": "all" if event_name == "全部事件" else "single", "label": event_name},
        "question": f"判断数据在{threshold}内完成的比例、1小时及以上长延迟比例，并定位延迟主要环节。",
        "observed_at": (enriched.get("freshness") or {}).get("observed_at"),
    }
    diagnosis = derive_diagnosis(enriched)
    quality_issues = derive_quality_issues(enriched)
    evidence = derive_evidence(enriched, diagnosis)
    enriched["diagnosis"] = diagnosis
    enriched["quality_issues"] = quality_issues
    enriched["evidence"] = evidence
    enriched["recommendations"] = derive_recommendations(enriched, diagnosis, evidence, quality_issues)
    return enriched
