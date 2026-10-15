#!/usr/bin/env python3
"""Render the deterministic eight-chapter data-delay report."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from report_model import (
    END_TO_END_SEGMENT,
    REPORT_CONTRACT_VERSION,
    UPLOAD_SEGMENT,
    WAREHOUSE_SEGMENT,
    ReportModelError,
    as_count,
    as_number,
    bucket_count,
    bucket_share,
    delayed_count,
    enrich_result,
    expected_count,
    long_delay_count,
    measured,
    sample_count,
    share,
)


BUCKETS = [
    ("b1", "预期阈值内"),
    ("b2", "预期阈值~10 分钟"),
    ("b3", "10~30 分钟"),
    ("b4", "30~60 分钟"),
    ("b5", "1~3 小时"),
    ("b6", "3~24 小时"),
    ("b7", "≥ 24 小时"),
    ("negative", "时间异常"),
]

SEGMENTS = [
    (UPLOAD_SEGMENT, "上报段（事件发生👉服务器收到）"),
    (WAREHOUSE_SEGMENT, "平台入库段（服务器收到👉写入数仓）"),
    (END_TO_END_SEGMENT, "总延迟（事件发生👉写入数仓，具备时区覆盖）"),
]


def md(value: Any) -> str:
    text = str(value if value not in (None, "") else "未提供")
    return text.replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def host_compat_lines(result: dict[str, Any]) -> list[str]:
    notice = result.get("_notice") or {}
    if not isinstance(notice, dict):
        return []
    value = notice.get("host_compat")
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


def fmt_count(value: Any) -> str:
    number = as_number(value)
    return f"{int(number):,}" if number is not None else "未统计"


def fmt_pct(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "未统计"
    if value == 0:
        return "0.00%"
    if 0 < value < 0.0001:
        return "< 0.01%"
    if 0.9999 < value < 1:
        return "> 99.99%"
    return f"{value * 100:.2f}%"


def fmt_duration(value: Any) -> str:
    number = as_number(value)
    if number is None or number < 0:
        return "未统计"
    seconds = int(round(number))
    if seconds < 60:
        return f"{seconds} 秒"
    minutes, second = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} 分钟" + (f" {second} 秒" if second else "")
    hours, minute = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} 小时" + (f" {minute} 分钟" if minute else "")
    days, hour = divmod(hours, 24)
    return f"{days} 天" + (f" {hour} 小时" if hour else "") + (f" {minute} 分钟" if minute else "")


def segment_share(segment: dict[str, Any] | None, count: int | None) -> float | None:
    return share(count, segment)


def bucket_cell(segment: dict[str, Any] | None, bucket: str) -> str:
    if not measured(segment):
        return "未测量"
    count = bucket_count(segment, bucket)
    return f"{fmt_pct(bucket_share(segment, bucket))}（{fmt_count(count)}）"


def metric_row(label: str, segment: dict[str, Any] | None) -> str:
    if not measured(segment):
        return f"| {label} | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |"
    seconds = segment.get("seconds") or {}
    return (
        f"| {label} | {fmt_count(sample_count(segment))} | "
        f"{fmt_pct(segment_share(segment, expected_count(segment)))} | "
        f"{fmt_pct(segment_share(segment, delayed_count(segment)))} | "
        f"{fmt_pct(segment_share(segment, long_delay_count(segment)))} | "
        f"{fmt_duration(seconds.get('p50'))} | {fmt_duration(seconds.get('p95'))} | "
        f"{fmt_duration(seconds.get('max'))} |"
    )


def dominant_delay_bucket(segment: dict[str, Any] | None) -> str | None:
    if not measured(segment):
        return None
    candidates = [(bucket_count(segment, key), label) for key, label in BUCKETS if key not in {"b1", "negative"}]
    count, label = max(candidates, default=(0, ""), key=lambda item: item[0])
    return label if count > 0 else None


def threshold_label(result: dict[str, Any]) -> str:
    seconds = as_count((result.get("decision_policy") or {}).get("expected_seconds")) or 300
    return f"{seconds // 60}分钟" if seconds % 60 == 0 else f"{seconds}秒"


def display_buckets(result: dict[str, Any]) -> list[tuple[str, str]]:
    threshold = threshold_label(result)
    return [("b1", f"{threshold}内"), ("b2", f"{threshold}~10分钟"), *BUCKETS[2:]]


def distribution_conclusion(segment: dict[str, Any] | None, label: str, threshold: str) -> str:
    if not measured(segment):
        return f"{label}未取得可用分布。"
    expected_share = segment_share(segment, expected_count(segment))
    delay_share = segment_share(segment, delayed_count(segment))
    long_share = segment_share(segment, long_delay_count(segment))
    dominant = dominant_delay_bucket(segment)
    if not delayed_count(segment):
        return f"{label}中{fmt_pct(expected_share)}的数据在{threshold}内完成，未观察到超过{threshold}的数据。"
    return (
        f"{label}中{fmt_pct(expected_share)}的数据在{threshold}内完成；{fmt_pct(delay_share)}超过{threshold}，"
        f"其中{fmt_pct(long_share)}达到1小时及以上；超出预期的数据主要集中在{dominant}。"
    )


def event_share(item: dict[str, Any], count_key: str, sample_key: str) -> float | None:
    total = as_count(item.get(sample_key))
    return as_count(item.get(count_key)) / total if total else None


def event_conclusion(item: dict[str, Any]) -> str:
    source = str(item.get("data_source") or "未记录")
    if source == "未记录":
        return "上报方式未记录，暂不能按方式判断延迟环节。"
    up = event_share(item, "upload_ge_1h_count", "upload_sample_count") or 0.0
    wh = event_share(item, "warehouse_ge_1h_count", "warehouse_sample_count") or 0.0
    total = event_share(item, "end_to_end_ge_1h_count", "end_to_end_sample_count") or 0.0
    if up == 0 and wh == 0 and total > 0:
        return f"{source} 样本的单段延迟均未达到1小时，累计后总延迟达到1小时。"
    if up > wh:
        return f"{source} 样本的1小时及以上延迟主要集中在上报段。"
    if wh > up:
        return f"{source} 样本的1小时及以上延迟主要集中在平台入库段。"
    if up > 0:
        return f"{source} 样本的上报段和平台入库段均出现1小时及以上延迟。"
    return f"{source} 样本未观察到1小时及以上延迟。"


def render_markdown(result: dict[str, Any], chart_ref: str) -> str:
    scope = result["scope"]
    project = scope["project"]
    window = scope["window"]
    diagnosis = result["diagnosis"]
    judgements = diagnosis.get("segments") or {}
    segments = result.get("delay_segments") or {}
    upload = segments.get(UPLOAD_SEGMENT) or {}
    warehouse = segments.get(WAREHOUSE_SEGMENT) or {}
    total_segment = segments.get(END_TO_END_SEGMENT) or {}
    observed_at = scope.get("observed_at") or "未提供"
    threshold = threshold_label(result)
    buckets = display_buckets(result)
    timezone = result.get("timezone_quality") or {}
    timestamp_zones = result.get("timestamp_zones") or {}
    server_zone = timestamp_zones.get("server_time") or {}
    server_offset_value = server_zone.get("offset")
    server_offset = float(server_offset_value) if server_offset_value is not None else None
    server_source = "用户提供" if server_offset is not None else "未记录"
    confirmed_offset = timezone.get("confirmed_missing_offset")
    confirmed_missing = as_count(timezone.get("confirmed_missing_count"))
    if confirmed_offset is not None and server_offset is not None:
        coverage_note = (
        f"#zone_offset 为空的 {fmt_count(confirmed_missing)} 条数据已按用户确认值 UTC{float(confirmed_offset):+g} 纳入覆盖；"
        f"事件时间按该值转换到服务器时区 UTC{server_offset:+g} 后计算。无效非空时区仍不参与上报段和总延迟统计。"
        )
    elif confirmed_offset is not None:
        coverage_note = "已提供空时区样本的偏移，但结果缺少服务器时区；上报段和总延迟口径不可用。"
    else:
        coverage_note = "没有有效时区信息的数据不参与上报段和总延迟统计；平台入库段不依赖时区信息，使用全部具备接收时间和入库时间的数据。"
    timezone_basis_note = (
        f"服务器时区：#server_time 和 #dw_create_time 按 "
        + (f"UTC{server_offset:+g}（{server_source}）" if server_offset is not None else "未记录")
        + "；#event_time 根据每行 #zone_offset 转换到同一服务器时区后再计算。"
    )
    lines: list[str] = []

    compatibility = host_compat_lines(result)
    if compatibility:
        lines.extend([
            "> ⚠️ CLI 与当前 AE 环境版本不兼容",
            *[f"> {md(line)}" for line in compatibility],
            "",
        ])

    lines.extend([
        f"# {md(project.get('name'))}项目数据延迟排查报告",
        "",
        "## 一、项目背景与排查范围",
        "",
        "| 项目 | 内容 |",
        "|---|---|",
        f"| 项目名称 | {md(project.get('name'))} |",
        f"| 项目 ID | {md(project.get('id'))} |",
        f"| 分析环境 | {md(project.get('host'))} |",
        f"| 排查日期 | {md(window.get('start_date'))} 至 {md(window.get('end_date'))} |",
        f"| 事件范围 | {md(scope['events'].get('label'))} |",
        f"| 总数据量 | {fmt_count(result.get('total_rows'))} 条 |",
        f"| 排查目标 | {md(scope.get('question'))} |",
        f"| 观察时间 | {md(observed_at)} |",
        "",
        f"{threshold}内从事件发生到完成入库视为符合预期。1小时及以上作为长延迟观察线，但不作为是否存在延迟的唯一判断标准。",
        "",
        "## 二、诊断结论",
        "",
        f"**上报段判断：** {judgements['upload']['text']}",
        "",
        f"**平台入库段判断：** {judgements['warehouse']['text']}",
        "",
        f"**总延迟判断：** {judgements['end_to_end']['text']}",
        "",
        f"**延迟来源判断：** {diagnosis['boundary']['text']}",
        "",
        "## 三、测算模型与总体结果",
        "",
        "① 事件发生 ─► ② 服务器收到 ─► ③ 写入数仓",
        "",
        f"| 环节 | 样本量 | {threshold}内（符合预期） | 超过{threshold} | 1小时及以上 | 50% ≤ | 95% ≤ | 最大值 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for key, label in SEGMENTS:
        lines.append(metric_row(label, segments.get(key)))
    lines.extend([
        "",
        timezone_basis_note,
        "",
        coverage_note,
        "",
    ])
    freshness = result.get("freshness") or {}
    lines.extend([
        f"最新事件时间：{md(freshness.get('newest_event_time'))}。",
        "",
        f"最新服务器接收时间：{md(freshness.get('newest_server_time'))}。",
        "",
        "## 四、各环节延迟分布",
        "",
        distribution_conclusion(upload, "上报段", threshold),
        "",
        distribution_conclusion(warehouse, "平台入库段", threshold),
        "",
        distribution_conclusion(total_segment, "总延迟", threshold),
        "",
    ])
    if chart_ref:
        lines.append(f"![各环节延迟分布]({md(chart_ref)})")
    else:
        lines.append("本次未生成图表；下表保留完整分布。")
    lines.extend([
        "",
        "表格以三个环节为行、时间区间为列；单元格先显示比例，括号内为数据量。",
        "",
        "| 环节 | " + " | ".join(label for _key, label in buckets) + " |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for key, label in SEGMENTS:
        segment = segments.get(key) or {}
        lines.append(f"| {label} | " + " | ".join(bucket_cell(segment, key_) for key_, _ in buckets) + " |")
    lines.extend([
        "",
        "时间异常表示前序时间晚于后续时间，单独列示，不并入正向延迟。",
        "",
        "## 五、高延迟事件分析",
        "",
    ])
    top_events = [
        item for item in sorted(
            result.get("top_slow_events") or [],
            key=lambda item: (-as_count(item.get("end_to_end_ge_1h_count")), str(item.get("event", "")), str(item.get("data_source", ""))),
        )
        if as_count(item.get("end_to_end_ge_1h_count")) > 0
    ]
    if top_events:
        lines.extend([
            "本章按具备时区覆盖数据的总延迟≥1小时数量排序；同时列出同一事件与上报方式在上报段、平台入库段的≥1小时比例，用于判断延迟主要出现在哪个环节。",
            "",
            "| 事件 | 上报方式 | 总延迟样本量 | 总延迟≥1小时 | 上报段≥1小时 | 入库段≥1小时 | 总延迟95% ≤ | 观察结论 |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ])
        for item in top_events:
            lines.append(
                f"| {md(item.get('event'))} | {md(item.get('data_source'))} | "
                f"{fmt_count(item.get('end_to_end_sample_count'))} | "
                f"{fmt_pct(event_share(item, 'end_to_end_ge_1h_count', 'end_to_end_sample_count'))}（{fmt_count(item.get('end_to_end_ge_1h_count'))}） | "
                f"{fmt_pct(event_share(item, 'upload_ge_1h_count', 'upload_sample_count'))} | "
                f"{fmt_pct(event_share(item, 'warehouse_ge_1h_count', 'warehouse_sample_count'))} | "
                f"{fmt_duration(item.get('end_to_end_p95_seconds'))} | {md(event_conclusion(item))} |"
            )
    elif scope["events"].get("mode") == "single":
        lines.append("本章不适用：本次仅检查单一事件。")
    elif result.get("top_slow_events_note"):
        lines.append(f"本次未取得可用的事件与上报方式排行：{md(result['top_slow_events_note'])}")
    else:
        lines.append("本次未取得可用的事件与上报方式排行。")
    lines.extend(["", "## 六、平台入库逐日统计", ""])
    lines.append("本章使用全部具备接收时间和入库时间的数据，不受时区信息缺失影响。")
    lines.append("")
    per_date = sorted(result.get("per_date") or [], key=lambda item: str(item.get("event_date", "")))
    measured_days = [day for day in per_date if measured(day.get("warehouse_lag") or {})]
    if measured_days:
        lines.extend([
            f"| 日期 | 样本量 | {threshold}内 | 超过{threshold} | 1小时及以上 | 50% ≤ | 95% ≤ | 最大值 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for day in measured_days:
            daily = day.get("warehouse_lag") or {}
            lines.append(
                f"| {md(day.get('event_date'))} | {fmt_count(sample_count(daily))} | "
                f"{fmt_pct(segment_share(daily, expected_count(daily)))} | "
                f"{fmt_pct(segment_share(daily, delayed_count(daily)))} | "
                f"{fmt_pct(segment_share(daily, long_delay_count(daily)))} | "
                f"{fmt_duration(daily.get('p50'))} | {fmt_duration(daily.get('p95'))} | {fmt_duration(daily.get('max'))} |"
            )
        peak_day = max(measured_days, key=lambda day: (segment_share(day.get("warehouse_lag") or {}, delayed_count(day.get("warehouse_lag") or {})) or 0, str(day.get("event_date", ""))))
        peak_lag = peak_day.get("warehouse_lag") or {}
        lines.extend([
            "",
            f"逐日判断：{peak_day.get('event_date')} 超过{threshold}的数据占比最高，为{fmt_pct(segment_share(peak_lag, delayed_count(peak_lag)))}。",
        ])
    else:
        lines.append("本章不适用：本次未取得平台入库段逐日测量结果。")

    coverage = result.get("sample_coverage") or {}
    total_rows = as_count(coverage.get("total_rows")) or as_count(result.get("total_rows"))
    covered_rows = as_count(coverage.get("zone_covered_rows"))
    warehouse_rows = sample_count(warehouse)
    e2e_rows = sample_count(total_segment)
    lines.extend([
        "",
        "## 七、样本与异常提醒",
        "",
        "### 7.1 样本情况",
        "",
        "| 样本 | 数据量 | 占范围内总数据比例 | 用途 |",
        "|---|---:|---:|---|",
        f"| 范围内总数据 | {fmt_count(total_rows)} | 100.00% | 排查范围总量 |",
        f"| 平台入库段可测数据 | {fmt_count(warehouse_rows)} | {fmt_pct(warehouse_rows / total_rows if total_rows else None)} | 平台入库段判断 |",
        f"| 时区覆盖数据 | {fmt_count(covered_rows)} | {fmt_pct(covered_rows / total_rows if total_rows else None)} | 上报段判断 |",
        f"| 总延迟可测数据 | {fmt_count(e2e_rows)} | {fmt_pct(e2e_rows / total_rows if total_rows else None)} | 总延迟判断 |",
        f"| 缺少时区信息的数据 | {fmt_count(timezone.get('missing_count'))} | {fmt_pct(as_count(timezone.get('missing_count')) / total_rows if total_rows else None)} | "
        + (f"其中 {fmt_count(confirmed_missing)} 条按 UTC{float(confirmed_offset):+g} 确认纳入" if confirmed_offset is not None else "不参与上报段和总延迟统计") + " |",
        "",
        "### 7.2 异常情况提醒",
        "",
    ])
    anomaly_rows = [
        ("上报段", upload),
        ("平台入库段", warehouse),
        ("总延迟", total_segment),
    ]
    observed_anomaly = False
    for label, segment in anomaly_rows:
        anomaly_count = bucket_count(segment, "negative")
        if anomaly_count:
            observed_anomaly = True
            lines.append(
                f"{label}可测数据中有{fmt_count(anomaly_count)}条时间异常，占{fmt_pct(bucket_share(segment, 'negative'))}。"
            )
    if not observed_anomaly:
        lines.append("三个可测环节均未观察到时间异常。")
    if result.get("top_slow_events_note"):
        lines.append("")
        lines.append("事件与上报方式排行未取得，事件级归因受限。")
    lines.extend(["", "### 7.3 待确认事项", ""])
    pending: list[str] = []
    if (as_count(timezone.get("missing_count")) and confirmed_offset is None) or as_count(timezone.get("invalid_count")):
        pending.append("缺少或无效时区信息的数据使用何种事件时间与时区定义。")
    if observed_anomaly:
        pending.append("时间异常来自来源时钟、时区转换还是历史数据写入。")
    if diagnosis["boundary"]["code"] in {"upload_dominant", "multiple_boundaries_similar", "both_segments_upload_higher"}:
        pending.append("主要事件的上报节奏、缓存策略以及是否存在补录或批次写入。")
    lines.extend(f"- {item}" for item in pending) if pending else lines.append("当前没有由测量结果触发的待确认事项。")

    lines.extend(["", "## 八、处理建议与验证方式", ""])
    recommendations = result.get("recommendations") or []
    if recommendations:
        lines.extend([
            "| 优先级 | 依据 | 建议方向 | 验证方式 |",
            "|---|---|---|---|",
        ])
        for item in recommendations:
            lines.append(
                f"| {md(item.get('priority'))} | {md(item.get('evidence'))} | "
                f"{md(item.get('action'))} | {md(item.get('verification'))} |"
            )
    else:
        lines.append(f"当前数据整体符合{threshold}预期，暂无需要优先推进的定向排查建议。")
    lines.extend(["", f"生成时间：{md(observed_at)}", ""])
    return "\n".join(lines)


def metric_summary(segment: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": segment.get("status"),
        "sample_count": sample_count(segment),
        "expected_share": segment_share(segment, expected_count(segment)),
        "delayed_share": segment_share(segment, delayed_count(segment)),
        "long_delay_share": segment_share(segment, long_delay_count(segment)),
        "p95_seconds": as_number((segment.get("seconds") or {}).get("p95")),
    }


def build_summary(result: dict[str, Any]) -> dict[str, Any]:
    segments = result.get("delay_segments") or {}
    return {
        "report_contract_version": REPORT_CONTRACT_VERSION,
        "scope": result["scope"],
        "diagnosis": result["diagnosis"],
        "core_metrics": {
            "total_rows": as_count(result.get("total_rows")),
            "upload": metric_summary(segments.get(UPLOAD_SEGMENT) or {}),
            "warehouse": metric_summary(segments.get(WAREHOUSE_SEGMENT) or {}),
            "end_to_end": metric_summary(segments.get(END_TO_END_SEGMENT) or {}),
        },
        "quality_issues": result.get("quality_issues") or [],
        "recommendations": result.get("recommendations") or [],
        "capabilities": result.get("capabilities") or {},
        "scan_protection": result.get("scan_protection") or {},
        "top_slow_events_note": result.get("top_slow_events_note"),
        "_notice": result.get("_notice") or {},
    }


def synthetic_fixture(delay_share: float = 0.10) -> dict[str, Any]:
    def dist(total: int, delayed: int, long: int, negative: int = 0) -> dict[str, int]:
        return {
            "b1": total - delayed - negative,
            "b2": delayed - long,
            "b3": 0,
            "b4": 0,
            "b5": long,
            "b6": 0,
            "b7": 0,
            "negative": negative,
        }
    up_dist = dist(100, int(100 * delay_share), 5)
    wh_dist = dist(1000, 2, 0)
    total_dist = dist(100, int(100 * delay_share), 5)
    return {
        "measurement_schema": "2.0",
        "project_id": 123,
        "project_name": "合成测试项目",
        "host": "https://example.invalid",
        "window": {"start_date": "2026-01-01", "end_date": "2026-01-01"},
        "event_name": "全部事件",
        "total_rows": 1000,
        "freshness": {"observed_at": "2026-01-02T00:00:00+08:00", "newest_event_time": "2026-01-01 23:59:59", "newest_server_time": "2026-01-02 00:00:01"},
        "sample_coverage": {"total_rows": 1000, "zone_covered_rows": 100, "zone_covered_share": 0.1, "warehouse_rows": 1000, "end_to_end_rows": 100},
        "timezone_quality": {"valid_count": 100, "missing_count": 900, "invalid_count": 0, "all_null_or_invalid": False},
        "server_time_semantics": "row_level",
        "delay_segments": {
            UPLOAD_SEGMENT: {"status": "measured", "sample_count": 100, "seconds": {"p50": 30, "p95": 4000, "max": 90000}, "distribution": up_dist},
            WAREHOUSE_SEGMENT: {"status": "measured", "sample_count": 1000, "seconds": {"p50": 20, "p95": 50, "max": 500}, "distribution": wh_dist},
            END_TO_END_SEGMENT: {"status": "measured", "sample_count": 100, "seconds": {"p50": 45, "p95": 5000, "max": 91000}, "distribution": total_dist},
        },
        "top_slow_events": [{
            "event": "event_a", "data_source": "server_sdk",
            "upload_sample_count": 100, "upload_ge_1h_count": 5,
            "warehouse_sample_count": 200, "warehouse_ge_1h_count": 0,
            "end_to_end_sample_count": 100, "end_to_end_p50_seconds": 45,
            "end_to_end_p95_seconds": 5000, "end_to_end_ge_1h_count": 5,
        }],
        "per_date": [{"event_date": "2026-01-01", "warehouse_lag": {"status": "measured", "sample_count": 1000, "p50": 20, "p95": 50, "max": 500, "distribution": wh_dist}}],
    }


def self_test() -> None:
    first = enrich_result(synthetic_fixture())
    report_one = render_markdown(first, "delay_charts.svg")
    report_two = render_markdown(enrich_result(synthetic_fixture()), "delay_charts.svg")
    assert report_one == report_two
    headings = [
        "## 一、项目背景与排查范围", "## 二、诊断结论", "## 三、测算模型与总体结果",
        "## 四、各环节延迟分布", "## 五、高延迟事件分析", "## 六、平台入库逐日统计",
        "## 七、样本与异常提醒", "## 八、处理建议与验证方式",
    ]
    assert [report_one.index(item) for item in headings] == sorted(report_one.index(item) for item in headings)
    assert "1小时及以上作为长延迟观察线，但不作为是否存在延迟的唯一判断标准" in report_one
    assert "上报段判断" in report_one and "平台入库段判断" in report_one and "总延迟判断" in report_one
    assert "总延迟（全部可测数据）" not in report_one
    assert "没有有效时区信息的数据不参与上报段和总延迟统计" in report_one
    assert "上报方式" in report_one and "server_sdk" in report_one
    assert "| 优先级 | 依据 | 建议方向 | 验证方式 |" in report_one
    assert "| 对象 |" not in report_one
    summary = build_summary(first)
    assert summary["diagnosis"]["segments"]["upload"]["code"] == "delay_present"
    assert summary["core_metrics"]["warehouse"]["sample_count"] == 1000
    print(json.dumps({"ok": True, "self_test": "passed", "contract": REPORT_CONTRACT_VERSION}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", nargs="?", help="Processed result JSON from check_ingestion_delay.py")
    parser.add_argument("--out", default="report.md", help="Markdown output path")
    parser.add_argument("--summary-out", default="report-summary.json", help="Stable summary JSON output path")
    parser.add_argument("--chart-ref", default="delay_charts.svg", help="Chart path written into Markdown")
    parser.add_argument("--validate-only", action="store_true", help="Validate and print diagnosis without writing files")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic contract tests")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.self_test:
        self_test()
        return
    if not args.input_json:
        raise SystemExit("input_json is required unless --self-test is used")
    try:
        payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        result = enrich_result(payload)
        if args.validate_only:
            print(json.dumps({"ok": True, "diagnosis": result["diagnosis"], "schema_version": result["schema_version"]}, ensure_ascii=False, sort_keys=True))
            return
        report = render_markdown(result, args.chart_ref)
        summary = build_summary(result)
        Path(args.out).write_text(report, encoding="utf-8")
        Path(args.summary_out).write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(Path(args.out)), "report_contract_version": REPORT_CONTRACT_VERSION, "summary_output": str(Path(args.summary_out))}, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, ReportModelError, AssertionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
