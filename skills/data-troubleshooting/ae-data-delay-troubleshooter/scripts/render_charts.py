#!/usr/bin/env python3
"""Render a deterministic SVG matrix for the three delay segments."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


SEGMENTS = [
    ("event_to_receive", "上报段"),
    ("receive_to_warehouse", "平台入库段"),
    ("event_to_warehouse", "总延迟"),
]

BUCKETS = [
    ("b1", "预期阈值内", "#d8f3dc"),
    ("b2", "预期阈值-10分钟", "#e9f5db"),
    ("b3", "10-30分钟", "#fff3bf"),
    ("b4", "30-60分钟", "#ffe8a1"),
    ("b5", "1-3小时", "#ffd8a8"),
    ("b6", "3-24小时", "#ffc9c9"),
    ("b7", "≥24小时", "#ffa8a8"),
    ("negative", "时间异常", "#dee2e6"),
]

FONT = "font-family='Helvetica Neue, Arial, PingFang SC, Microsoft YaHei, sans-serif'"
LABEL_W = 180
CELL_W = 158
HEADER_H = 82
COL_H = 58
ROW_H = 92
WIDTH = LABEL_W + CELL_W * len(BUCKETS) + 30


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def text(x: float, y: float, value: Any, size: int = 12, anchor: str = "start", fill: str = "#212529", weight: str = "normal") -> str:
    return (
        f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' text-anchor='{anchor}' "
        f"fill='{fill}' font-weight='{weight}' {FONT}>{esc(value)}</text>"
    )


def pct(value: float) -> str:
    if value == 0:
        return "0.00%"
    if 0 < value < 0.0001:
        return "<0.01%"
    if 0.9999 < value < 1:
        return ">99.99%"
    return f"{value * 100:.2f}%"


def render_svg(result: dict[str, Any]) -> str:
    segments = result.get("delay_segments") or {}
    window = result.get("window") or {}
    expected_seconds = int((result.get("decision_policy") or {}).get("expected_seconds") or 300)
    threshold = f"{expected_seconds // 60}分钟" if expected_seconds % 60 == 0 else f"{expected_seconds}秒"
    buckets = [
        ("b1", f"{threshold}内", BUCKETS[0][2]),
        ("b2", f"{threshold}-10分钟", BUCKETS[1][2]),
        *BUCKETS[2:],
    ]
    height = HEADER_H + COL_H + ROW_H * len(SEGMENTS) + 74
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{WIDTH}' height='{height}' viewBox='0 0 {WIDTH} {height}'>",
        f"<rect width='{WIDTH}' height='{height}' fill='#ffffff'/>",
        text(20, 30, "各环节延迟分布", 20, weight="bold"),
        text(
            20,
            54,
            f"项目：{result.get('project_name', '?')}   事件：{result.get('event_name', '?')}   时间：{window.get('start_date', '?')} 至 {window.get('end_date', '?')}",
            12,
            fill="#495057",
        ),
        text(20, HEADER_H + 35, "环节 / 时间区间", 12, weight="bold"),
    ]

    for index, (_key, label, _color) in enumerate(buckets):
        x = LABEL_W + index * CELL_W
        parts.append(f"<rect x='{x}' y='{HEADER_H}' width='{CELL_W}' height='{COL_H}' fill='#f8f9fa' stroke='#ced4da'/>")
        parts.append(text(x + CELL_W / 2, HEADER_H + 35, label, 12, anchor="middle", weight="bold"))

    for row_index, (segment_key, segment_label) in enumerate(SEGMENTS):
        segment = segments.get(segment_key) or {}
        y = HEADER_H + COL_H + row_index * ROW_H
        sample = int(segment.get("sample_count") or 0)
        measured = segment.get("status") == "measured" and sample > 0
        parts.append(f"<rect x='20' y='{y}' width='{LABEL_W - 20}' height='{ROW_H}' fill='#f8f9fa' stroke='#ced4da'/>")
        parts.append(text(34, y + 35, segment_label, 14, weight="bold"))
        parts.append(text(34, y + 59, f"样本 {sample:,}" if sample else "未测量", 11, fill="#6c757d"))
        distribution = segment.get("distribution") or {}
        for col_index, (bucket, _label, color) in enumerate(buckets):
            x = LABEL_W + col_index * CELL_W
            count = int(distribution.get(bucket, 0) or 0)
            bucket_share = count / sample if measured else 0.0
            fill = color if measured else "#f1f3f5"
            parts.append(f"<rect x='{x}' y='{y}' width='{CELL_W}' height='{ROW_H}' fill='{fill}' stroke='#ced4da'/>")
            if measured:
                parts.append(text(x + CELL_W / 2, y + 37, pct(bucket_share), 15, anchor="middle", weight="bold"))
                parts.append(text(x + CELL_W / 2, y + 61, f"({count:,})", 11, anchor="middle", fill="#495057"))
            else:
                parts.append(text(x + CELL_W / 2, y + 50, "未测量", 12, anchor="middle", fill="#868e96"))

    note_y = HEADER_H + COL_H + ROW_H * len(SEGMENTS) + 28
    parts.append(text(20, note_y, f"单元格先显示比例，括号内为数据量。{threshold}内视为符合预期；1小时及以上为长延迟观察区间。", 12, fill="#495057"))
    timezone = result.get("timezone_quality") or {}
    timestamp_zones = result.get("timestamp_zones") or {}
    server_zone = timestamp_zones.get("server_time") or {}
    server_offset_value = server_zone.get("offset")
    server_offset = float(server_offset_value) if server_offset_value is not None else None
    source_note = "用户提供" if server_offset is not None else "未记录"
    confirmed_offset = timezone.get("confirmed_missing_offset")
    zone_note = (
        f"服务器时区为 UTC{server_offset:+g}（{source_note}）；空时区样本按 UTC{float(confirmed_offset):+g} 转换后纳入。"
        if confirmed_offset is not None
        else (
            f"服务器时区为 UTC{server_offset:+g}（{source_note}）；事件时间按 #zone_offset 转换，空时区样本排除。"
            if server_offset is not None
            else "服务器时区未记录；无法确认事件时间转换口径。"
        )
    )
    parts.append(text(20, note_y + 24, zone_note, 12, fill="#495057"))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Result JSON from check_ingestion_delay.py --json; - for stdin")
    parser.add_argument("--out", default="delay_charts.svg", help="Output SVG path")
    args = parser.parse_args()
    try:
        result = json.load(sys.stdin) if args.input == "-" else json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": f"cannot read result JSON: {exc}"}, ensure_ascii=False))
        raise SystemExit(2)
    if not isinstance(result, dict) or "delay_segments" not in result:
        print(json.dumps({"ok": False, "error": "input is not a checker result JSON"}, ensure_ascii=False))
        raise SystemExit(2)
    svg = render_svg(result)
    out_path = Path(args.out)
    out_path.write_text(svg, encoding="utf-8")
    measured_count = sum(
        1 for key, _label in SEGMENTS if (result.get("delay_segments") or {}).get(key, {}).get("status") == "measured"
    )
    print(json.dumps({"ok": True, "output": str(out_path.resolve()), "bytes": len(svg.encode("utf-8")), "charts": {"measured_segments": measured_count}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
