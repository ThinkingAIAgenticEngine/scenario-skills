#!/usr/bin/env python3
"""Audit-project usage analysis — data processing and report generation.

Two usages:

1) Generate query definitions (for ae-cli analysis adhoc export):
   python3 generate_report.py --prepare --out-dir /tmp/audit

2) Parse exported data and render the report:
   python3 generate_report.py \
       --analysis analysis_by_account.jsonl.gz \
       --engage engage_by_account.jsonl.gz \
       --agent agent_by_account.jsonl.gz \
       --mapping-raw mapping_by_account.jsonl.gz \
       --account-project account_project.jsonl.gz \
       --report-interest report_interest.jsonl.gz \
       --top-n 20 \
       --out-json 审计项目_按人统计_细分.json \
       --feishu-xml report.xml

Note: Chinese strings below (labels, display names, conclusions, themes) are the
report's runtime output in the customer's business language, not documentation.
"""

import argparse
import gzip
import json
import re
import sys
import unicodedata

# ---------------------------------------------------------------------------
# Event classification: each item is (event_name, display_name). Parsing accepts
# both the display name and "<event_name>.Event totals" as column names.
# ---------------------------------------------------------------------------
ANALYSIS = {
    "🧮 模型分析": [("model_search", "模型查询"), ("model_page_action", "模型页操作"), ("metric_sql", "所有查询")],
    "📋 查看报表": [("report_search", "报表查询")],
    "📌 查看看板": [("dashboard_search", "看板查询"), ("mobile_dashboard_search", "mobile_dashboard_search")],
    "🗂️ 看板管理": [
        ("dashboard_action", "看板操作"), ("dashboard_report_panel_action", "看板报表面板操作"),
        ("dashboard_report_edit_save", "dashboard_report_edit_save"), ("dashboard_report_remove", "dashboard_report_remove"),
        ("dashboard_space_action", "dashboard_space_action"), ("dashboard_space_create", "dashboard_space_create"),
        ("dashboard_space_delete", "dashboard_space_delete"), ("dashboard_delete", "看板删除"),
        ("dashboard_folder_export_import", "dashboard_folder_export_import"),
    ],
    "🏗️ 搭建报表": [("report_save", "报表新建"), ("report_edit", "报表更新"), ("chart_save", "chart_save"), ("report_del", "report_del")],
    "📤 数据导出": [("export_data", "数据导出"), ("download_data", "下载数据")],
    "🏷️ 分群标签": [
        ("cluster_create", "分群标签创建"), ("cluster_edit", "分群标签编辑"), ("cluster_refresh", "分群标签手动更新"),
        ("cluster_delete", "cluster_delete"), ("user_group_create", "user_group_create"), ("user_group_edit", "user_group_edit"),
    ],
    "🆕 新建看板": [("dashboard_create", "看板新建")],
    "📦 其他分析": [
        ("metric_create", "metric_create"), ("metric_edit", "metric_edit"), ("metric_delete", "metric_delete"),
        ("virtual_event_create", "virtual_event_create"), ("virtual_properties_create", "virtual_properties_create"),
        ("dataset_action", "dataset_action"), ("note_edit", "note_edit"), ("export_dashboard_pdf", "export_dashboard_pdf"),
    ],
}

ENGAGE = {
    "🎯 任务运营": [
        ("engage_task_list_click", "engage_task_list_click"), ("engage_create_task_click", "engage_create_task_click"),
        ("engage_task_data_click", "engage_task_data_click"), ("engage_task_data_search", "engage_task_data_search"),
        ("engage_task_metric_view", "engage_task_metric_view"),
    ],
    "📣 渠道管理": [("engage_channel_click", "engage_channel_click")],
    "🎪 活动与其他": [
        ("engage_activity_list_click", "engage_activity_list_click"), ("engage_activity_edit", "engage_activity_edit"),
        ("engage_activity_approve", "engage_activity_approve"), ("engage_activity_data_click", "engage_activity_data_click"),
        ("engage_activity_task_group", "engage_activity_task_group"), ("engage_common_metrics_edit", "engage_common_metrics_edit"),
        ("engage_send_preview_click", "engage_send_preview_click"), ("engage_task_ab_report_op", "engage_task_ab_report_op"),
        ("engage_task_cohort_click", "engage_task_cohort_click"), ("engage_workbench_gantt_op", "engage_workbench_gantt_op"),
    ],
}

AGENT = {
    "💬 会话对话": [("agent_session_message_send", "Agent 用户发送消息"), ("agent_session_message_receive", "Agent 收到消息")],
    "🔧 工具调用": [("mcp_tool_call", "Agent MCP工具调用")],
    "🗂️ 会话管理": [
        ("agent_session_create", "Agent 新建会话"), ("agent_session_update", "Agent 修改会话属性"),
        ("agent_session_delete", "Agent 删除会话"),
    ],
    "🧩 Skill管理": [
        ("agent_skill_create", "Agent 新建Skill"), ("agent_skill_update", "Agent 编辑Skill"),
        ("agent_skill_enable", "Agent 启用Skill"), ("agent_skill_disable", "Agent 停用Skill"),
        ("agent_skill_delete", "Agent 删除Skill"),
    ],
    "🤖 Agent管理": [
        ("agent_create", "新建Agent"), ("agent_update", "编辑Agent"), ("agent_enable", "启用Agent"),
        ("agent_disable", "停用Agent"), ("agent_delete", "删除Agent"),
    ],
    "⚙️ 沙箱与模型": [
        ("agent_sandbox_delete", "Agent 沙箱销毁"), ("agent_sandbox_update", "Agent 沙箱属性变更"),
        ("agent_model_create", "Agent 新建模型配置"), ("agent_model_enable", "Agent 启用模型"),
        ("agent_model_disable", "Agent 停用模型"), ("agent_model_update", "agent_model_update"),
        ("agent_model_delete", "agent_model_delete"), ("agent_mcp_create", "agent_mcp_create"),
        ("agent_mcp_update", "Agent 编辑MCP配置"), ("agent_mcp_enable", "agent_mcp_enable"),
        ("agent_mcp_disable", "agent_mcp_disable"), ("agent_user_enable", "Agent 成员启用"),
        ("agent_user_disable", "Agent 成员停用"),
    ],
}

# Engage *_model page-browse auto tracking (not counted as "engage actions", but still exported for completeness)
ENGAGE_MODEL_EVENTS = ["engage_task_model", "engage_activity_model", "engage_channel_model", "engage_task_instance_model"]

def detect_system_account(accounts):
    """Auto-detect the system bare-account prefix: an account starting with `ta-` and containing no `_` (username suffix) is the tenant prefix itself.

    Different customers have different AE tenant prefixes, so there is no hardcoded fallback. Returns None when no bare-account row is present.
    """
    candidates = sorted(
        acct for acct in accounts
        if isinstance(acct, str) and acct.startswith("ta-") and "_" not in acct
    )
    if len(candidates) > 1:
        raise SystemExit("multiple possible system bare accounts found; verify the account identifiers before continuing")
    return candidates[0] if candidates else None


def fallback_display_name(account, system_account):
    """Strip an auto-detected tenant prefix; otherwise preserve the full account ID."""
    if system_account and account.startswith(f"{system_account}_"):
        return account[len(system_account) + 1:]
    return account

# Project-dimension events (analysis/dashboard events that carry project_name; agent events carry no project field, so they are excluded)
PROJECT_EVENTS = {
    "报表查询": "report_search",
    "看板查询": "dashboard_search",
    "看板新建": "dashboard_create",
    "报表新建": "report_save",
    "报表更新": "report_edit",
    "数据导出": "export_data",
    "模型查询": "model_search",
}

# report-name keyword → business theme mapping (feeds the "attention-data" column). Ordered match, first hit wins; unmatched names get no theme.
REPORT_THEMES = [
    ("agent|会话|mcp|skill", "Agent 使用"),
    ("充值|付费|arpu|arppu|收入|营收|流水|礼包|购买|订单|gmv", "付费/收入"),
    ("数开|dataops|工作空间|ide|任务流|指标|维度", "数据开发"),
    ("数据量|存储|集群|资源|容量|预估可使用|查询次数", "数据/资源用量"),
    ("新增|注册|激活|渠道|留存|流失|活跃|dau|mau|用户数|客户数", "用户增长/活跃"),
    ("标签|分群|画像", "用户画像/分群"),
    ("巡检|监控|告警|健康|异常", "运维监控"),
    ("基础数据", "基础数据"),
]


def summarize_reports(names):
    """Summarize a report-name list (should pass the user's ALL watched reports) into business themes (deduped, order-preserving, at most 6)."""
    themes = []
    for name in names:
        low = name.lower()
        for pat, theme in REPORT_THEMES:
            if re.search(pat, low):
                if theme not in themes:
                    themes.append(theme)
                break
    return themes[:6]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def display_width(s):
    return sum(2 if unicodedata.east_asian_width(c) in ("F", "W") else 1 for c in str(s))


def pad(s, w):
    s = str(s)
    return s + " " * max(0, w - display_width(s))


def num(v):
    s = str(v).replace(",", "").replace("-", "0").strip()
    try:
        return int(float(s))
    except ValueError:
        return 0


def esc_xml(s):
    """Escape text for Feishu XML."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse_jsonl(fname):
    """Parse an adhoc-export jsonl.gz: first line is schema, then {'type':'row','data':{...}}. Returns {account: {column: value}}."""
    rows = {}
    with gzip.open(fname, "rt") as f:
        for line in f:
            line = line.strip()
            if not line or line == "null":
                continue
            d = json.loads(line)
            if isinstance(d, dict) and d.get("type") == "row":
                data = d["data"]
                acct = data.get("Account ID", "(null)")
                if acct and acct != "(null)":
                    rows[acct] = data
    return rows


def col_value(data, event_name, display_name):
    """Pick a value by candidate column names: display name first, then '<event_name>.Event totals'."""
    for col in (display_name, f"{event_name}.Event totals"):
        if col in data:
            return data[col]
    return "0"


def parse_mapping_jsonl(fname):
    """Parse the mapping aggregation jsonl.gz (#account_id + user_name group), return {account: user_name}."""
    mapping = {}
    with gzip.open(fname, "rt") as f:
        for line in f:
            line = line.strip()
            if not line or line == "null":
                continue
            d = json.loads(line)
            if isinstance(d, dict) and d.get("type") == "row":
                data = d["data"]
                acct = data.get("Account ID", "(null)")
                name = data.get("成员显示名", "") or data.get("user_name", "")
                if acct and acct != "(null)" and name:
                    mapping.setdefault(acct, name)
    return mapping


def parse_account_project(fname):
    """Parse the account×project jsonl.gz (#account_id + project_name group), return (acct_proj_count, proj_list).

    acct_proj_count: {account: {project: action volume}} — feeds the "active projects TOP3" column.
    proj_list: [(project name, active users, {column: count}, total, [top3 accounts])], sorted by total desc.
    """
    acct_proj_count = {}
    proj_acct = {}
    proj_metrics = {}
    if not fname:
        return {}, []
    with gzip.open(fname, "rt") as f:
        for line in f:
            line = line.strip()
            if not line or line == "null":
                continue
            d = json.loads(line)
            if not (isinstance(d, dict) and d.get("type") == "row"):
                continue
            data = d["data"]
            acct = data.get("Account ID", "(null)")
            proj = data.get("当前项目名称", "(null)")
            if not acct or acct == "(null)" or not proj or proj == "(null)":
                continue
            tot = sum(num(data.get(c, "0")) for c in PROJECT_EVENTS)
            if tot <= 0:
                continue
            apc = acct_proj_count.setdefault(acct, {})
            apc[proj] = apc.get(proj, 0) + tot
            pac = proj_acct.setdefault(proj, {})
            pac[acct] = pac.get(acct, 0) + tot
            pm = proj_metrics.setdefault(proj, {c: 0 for c in PROJECT_EVENTS})
            pm["_users"] = pm.get("_users", set())
            pm["_users"].add(acct)
            for c in PROJECT_EVENTS:
                pm[c] += num(data.get(c, "0"))
    proj_list = []
    for proj, pm in proj_metrics.items():
        total = sum(pm[c] for c in PROJECT_EVENTS)
        members = sorted(proj_acct.get(proj, {}).items(), key=lambda x: -x[1])[:3]
        proj_list.append((proj, len(pm["_users"]), pm, total, [a for a, _ in members]))
    proj_list.sort(key=lambda x: -x[3])
    return acct_proj_count, proj_list


def parse_interest(fname, name_col, count_col):
    """Parse the interest jsonl.gz (#account_id + project_name + name group), return (acct_interest, proj_interest).

    acct_interest: {account: [(name, count), ...]} sorted desc — feeds the business-attention module.
    proj_interest: {project: [(name, count), ...]} sorted desc — feeds the project-table "top report" column.
    """
    acct_agg = {}
    proj_agg = {}
    if not fname:
        return {}, {}
    with gzip.open(fname, "rt") as f:
        for line in f:
            line = line.strip()
            if not line or line == "null":
                continue
            d = json.loads(line)
            if not (isinstance(d, dict) and d.get("type") == "row"):
                continue
            data = d["data"]
            acct = data.get("Account ID", "(null)")
            proj = data.get("当前项目名称", "(null)")
            name = data.get(name_col, "(null)")
            cnt = num(data.get(count_col, "0"))
            if acct == "(null)" or name in ("(null)", None, "") or cnt <= 0:
                continue
            acct_agg.setdefault(acct, {}).setdefault(name, 0)
            acct_agg[acct][name] += cnt
            if proj not in ("(null)", None, ""):
                proj_agg.setdefault(proj, {}).setdefault(name, 0)
                proj_agg[proj][name] += cnt
    acct_interest = {a: sorted(d.items(), key=lambda x: -x[1]) for a, d in acct_agg.items()}
    proj_interest = {p: sorted(d.items(), key=lambda x: -x[1]) for p, d in proj_agg.items()}
    return acct_interest, proj_interest


def build_definition(events, sql_filter_event=None):
    """Build an adhoc export's AI-facing definition."""
    metrics = []
    for ev in events:
        m = {"event": ev, "aggregation": "total_count"}
        if ev == sql_filter_event:
            m["filters"] = [{"field": {"name": "sql_query_system_refresh", "type": "event_property"}, "operator": "is_false"}]
        metrics.append(m)
    return {
        "time_range": {"mode": "recent", "unit": "day", "value": 15},
        "metrics": metrics,
        "groups": [{"field": {"name": "#account_id", "type": "user_property"}}],
    }


# ---------------------------------------------------------------------------
# --prepare: generate query definitions
# ---------------------------------------------------------------------------
def prepare(out_dir):
    import os
    os.makedirs(out_dir, exist_ok=True)

    analysis_events = [ev for cat in ANALYSIS.values() for ev, _ in cat]
    engage_events = [ev for cat in ENGAGE.values() for ev, _ in cat] + ENGAGE_MODEL_EVENTS
    agent_events = [ev for cat in AGENT.values() for ev, _ in cat]

    # analysis + dashboard: ANALYSIS already includes dashboard events; filter scheduled refresh on metric_sql
    analysis_events_with_sql = analysis_events + ["metric_sql"]
    analysis_events_with_sql = sorted(set(analysis_events_with_sql))
    # account → display-name mapping: group #account_id + user_name (instead of a detail export); user_name is a user property
    mapping_def = {
        "time_range": {"mode": "recent", "unit": "day", "value": 15},
        "metrics": [
            {"event": "report_search", "aggregation": "total_count"},
            {"event": "model_search", "aggregation": "total_count"},
        ],
        "groups": [
            {"field": {"name": "#account_id", "type": "user_property"}},
            {"field": {"name": "user_name", "type": "user_property"}},
        ],
    }
    # account × project: group #account_id + project_name (project dimension; only analysis/dashboard events carry project fields)
    project_def = {
        "time_range": {"mode": "recent", "unit": "day", "value": 15},
        "metrics": [{"event": ev, "aggregation": "total_count"} for ev in PROJECT_EVENTS.values()],
        "groups": [
            {"field": {"name": "#account_id", "type": "user_property"}},
            {"field": {"name": "project_name", "type": "event_property"}},
        ],
    }
    # business attention (report-name dimension): group #account_id + project_name + report_name
    report_interest_def = {
        "time_range": {"mode": "recent", "unit": "day", "value": 15},
        "metrics": [{"event": "report_search", "aggregation": "total_count"}],
        "groups": [
            {"field": {"name": "#account_id", "type": "user_property"}},
            {"field": {"name": "project_name", "type": "event_property"}},
            {"field": {"name": "report_name", "type": "event_property"}},
        ],
    }
    defs = {
        "def_analysis.json": build_definition(analysis_events_with_sql, sql_filter_event="metric_sql"),
        "def_engage.json": build_definition(engage_events),
        "def_agent.json": build_definition(agent_events),
        "def_mapping.json": mapping_def,
        "def_account_project.json": project_def,
        "def_report_interest.json": report_interest_def,
    }
    for fname, d in defs.items():
        with open(os.path.join(out_dir, fname), "w") as f:
            json.dump(d, f, ensure_ascii=False)
    print(f"Query definitions written to {out_dir}/")
    print("Next, run these six exports:")
    print(f"  ae-cli analysis adhoc export --project-id <id> --model-type event --definition \"$(cat {out_dir}/def_analysis.json)\" --artifact-format jsonl --output analysis_by_account.jsonl.gz --force")
    print(f"  ae-cli analysis adhoc export --project-id <id> --model-type event --definition \"$(cat {out_dir}/def_engage.json)\" --artifact-format jsonl --output engage_by_account.jsonl.gz --force")
    print(f"  ae-cli analysis adhoc export --project-id <id> --model-type event --definition \"$(cat {out_dir}/def_agent.json)\" --artifact-format jsonl --output agent_by_account.jsonl.gz --force")
    print(f"  ae-cli analysis adhoc export --project-id <id> --model-type event --definition \"$(cat {out_dir}/def_mapping.json)\" --artifact-format jsonl --output mapping_by_account.jsonl.gz --force")
    print(f"  ae-cli analysis adhoc export --project-id <id> --model-type event --definition \"$(cat {out_dir}/def_account_project.json)\" --artifact-format jsonl --output account_project.jsonl.gz --force")
    print(f"  ae-cli analysis adhoc export --project-id <id> --model-type event --definition \"$(cat {out_dir}/def_report_interest.json)\" --artifact-format jsonl --output report_interest.jsonl.gz --force")


# ---------------------------------------------------------------------------
# Main flow: parse + tag + report
# ---------------------------------------------------------------------------
# Pure functions below are shared by the markdown and Feishu-XML renderers (avoid dual-writing the conclusions and data-prep logic)


def cat_total(ranked, cat):
    return sum(r[cat] for r in ranked)


def cat_count(ranked, cat):
    return sum(1 for r in ranked if r[cat] > 0)


def top5(ranked, cat):
    r2 = sorted(ranked, key=lambda r: -r[cat])
    return [r for r in r2 if r[cat] > 0][:5]


def active_proj_top3(acct_proj_count, acct):
    d = acct_proj_count.get(acct, {})
    return sorted(d.items(), key=lambda x: -x[1])[:3]


def build_conclusions(ranked, n, has_engage, has_agent):
    """Generate conditional value conclusions shared by markdown and Feishu XML."""
    total_all = sum(r["分析总量"] + r["运营总量"] + r["agent总量"] for r in ranked)
    ta = cat_total(ranked, "分析总量")
    pct_a = round(ta / total_all * 100) if total_all else 0
    pct_p = round(cat_count(ranked, "分析总量") / n * 100) if n else 0
    deep = sum(1 for r in ranked if "深度使用" in r["tags"])
    view = sum(1 for r in ranked if "查看者" in r["tags"])
    none = sum(1 for r in ranked if not r["tags"])
    conclusions = [
        f"分析是底座：{cat_count(ranked, '分析总量')}/{n} 人（{pct_p}%）在分析模块活跃，动作量 {ta} 占已纳入模块总量 {pct_a}%，是系统价值的主要承载。",
        f"看板以查阅为主：查看看板 {cat_total(ranked, '📌 查看看板')} 次、看板管理 {cat_total(ranked, '🗂️ 看板管理')} 次，看板是固化分析成果的高频查阅载体；新建看板 {cat_total(ranked, '🆕 新建看板')} 次、搭建报表 {cat_total(ranked, '🏗️ 搭建报表')} 次相对较少，对成熟项目属正常——多数人直接查阅既有看板，而非新建。",
    ]
    if has_engage:
        conclusions.append(
            f"运营模块：15 天内有 {cat_count(ranked, '运营总量')} 人活跃、动作量 {cat_total(ranked, '运营总量')}（任务运营 {cat_total(ranked, '🎯 任务运营')}、渠道管理 {cat_total(ranked, '📣 渠道管理')}、活动与其他 {cat_total(ranked, '🎪 活动与其他')}）。"
        )
    if has_agent:
        agent_total = cat_total(ranked, "agent总量")
        if agent_total > 0:
            conclusions.append(
                f"agent 以对话为核心：会话对话 {cat_total(ranked, '💬 会话对话')} 次，工具调用 {cat_total(ranked, '🔧 工具调用')} 次（含 te-agent / customer / ae-cli 全渠道）；搭建 Agent（{cat_total(ranked, '🤖 Agent管理')}）、Skill 管理（{cat_total(ranked, '🧩 Skill管理')}）等建设性配置动作需结合实际占比判断。"
            )
        else:
            conclusions.append("agent 模块已纳入统计，但最近 15 天未记录到相关动作。")
    conclusions.append(
        f"用户呈金字塔分层：深度使用 {deep} 人（{round(deep/n*100) if n else 0}%）vs 查看者 {view} 人（{round(view/n*100) if n else 0}%）vs 无标签 {none} 人；头部用户是运营重点跟进的种子用户。"
    )
    return conclusions


def analyze(ana_file, engage_file, agent_file, mapping_file, mapping_raw_file, account_project_file, report_interest_file, top_n, out_json, feishu_xml=None):
    ana = parse_jsonl(ana_file) if ana_file else {}
    eng = parse_jsonl(engage_file) if engage_file else {}
    agt = parse_jsonl(agent_file) if agent_file else {}
    if mapping_raw_file:
        mapping = parse_mapping_jsonl(mapping_raw_file)
    else:
        mapping = json.load(open(mapping_file)) if mapping_file else {}
    acct_proj_count, proj_list = parse_account_project(account_project_file)
    acct_report_interest, proj_report_interest = parse_interest(report_interest_file, "报表名", "报表查询")

    accounts = set(ana) | set(eng) | set(agt)
    system_account = detect_system_account(accounts)
    # Engage appears only when a real user has a recognized active action. Agent
    # availability is version-gated by the caller, represented by providing its export.
    has_engage = any(
        sum(
            num(col_value(data, event_name, display_name))
            for columns in ENGAGE.values()
            for event_name, display_name in columns
        ) > 0
        for account, data in eng.items()
        if account != system_account
    )
    has_agent = bool(agt)  # whether agent data was provided (version >= 6.0)

    analysis_accounts = set(ana)
    if system_account:
        analysis_accounts.discard(system_account)

    # A missing or zero-valued analysis export is a hard stop: an empty report would be misleading.
    analysis_action_total = sum(
        num(col_value(data, event_name, display_name))
        for account, data in ana.items()
        if account in analysis_accounts
        for columns in ANALYSIS.values()
        for event_name, display_name in columns
    )
    if not analysis_accounts:
        raise SystemExit("analysis export contains no account rows; verify the project, time range, and export definition")
    if analysis_action_total == 0:
        raise SystemExit("analysis export contains no recognized actions; verify event names and exported column names")

    # Optional module files may still be empty because the module is unavailable or inactive.
    def _all_zero(rows):
        return bool(rows) and all(
            num(v) == 0 for d in rows.values() for k, v in d.items() if k not in ("Time", "Account ID")
        )

    if _all_zero(eng):
        print("[warning] engage data exists but all event counts are 0 — check def_engage export column names against the script", file=sys.stderr)
    if _all_zero(agt):
        print("[warning] agent data exists but all event counts are 0 — check def_agent export column names against the script", file=sys.stderr)

    if system_account:
        accounts.discard(system_account)
    if not accounts:
        raise SystemExit("analysis export contains no user accounts after excluding the system bare account")

    detail = {}
    for acct in accounts:
        a, e, g = ana.get(acct, {}), eng.get(acct, {}), agt.get(acct, {})
        r = {"acct": acct, "user_name": mapping.get(acct, fallback_display_name(acct, system_account))}
        for cat, cols in ANALYSIS.items():
            r[cat] = sum(num(col_value(a, ev, dn)) for ev, dn in cols)
        for cat, cols in ENGAGE.items():
            r[cat] = sum(num(col_value(e, ev, dn)) for ev, dn in cols)
        for cat, cols in AGENT.items():
            r[cat] = sum(num(col_value(g, ev, dn)) for ev, dn in cols)
        r["分析总量"] = sum(r[c] for c in ANALYSIS)
        r["运营总量"] = sum(r[c] for c in ENGAGE)
        r["agent总量"] = sum(r[c] for c in AGENT)

        is_deep = r["🏗️ 搭建报表"] > 0 or r["📤 数据导出"] > 0 or r["🆕 新建看板"] > 0
        is_view = r["📋 查看报表"] > 0 or r["📌 查看看板"] > 0 or r["🧮 模型分析"] > 0 or r["🗂️ 看板管理"] > 0
        tags = []
        tags.append("深度使用" if is_deep else ("查看者" if is_view else None))
        if r["运营总量"] > 0:
            tags.append("运营任务")
        if r["📤 数据导出"] > 0:
            tags.append("数据导出")
        r["tags"] = [t for t in tags if t]
        detail[acct] = r

    ranked = sorted(detail.values(), key=lambda r: -(r["分析总量"] + r["运营总量"] + r["agent总量"]))
    n = len(ranked)

    def total(cat):
        return cat_total(ranked, cat)

    def count(cat):
        return cat_count(ranked, cat)

    # ---- render report ----
    lines = []
    lines.append("# 审计项目系统使用情况报告\n")
    lines.append("**统计时间范围**：最近 15 天（含今天）\n")
    lines.append("**统计口径**：账号统一用 `#account_id`（`user_name` 为显示名）；已剔除自动任务与系统裸账号；未开通的模块不体现；项目维度基于分析/看板事件的 project_name 字段，agent 行为无项目埋点故不纳入项目维度。\n")

    # ===== 1. Module usage & value assessment =====
    lines.append("## 一、模块功能使用与价值评估\n")
    lines.append("### 价值评估结论\n")
    for i, c in enumerate(build_conclusions(ranked, n, has_engage, has_agent), 1):
        lines.append(f"{i}. {c}")
    lines.append("")

    # usage overview
    lines.append("### 使用量概览\n")
    lines.append("| 模块 | 活跃账号 | 动作总量 |")
    lines.append("|---|---|---|")
    lines.append(f"| 分析（含看板） | {count('分析总量')} 人 | {total('分析总量')} |")
    if has_agent:
        lines.append(f"| agent | {count('agent总量')} 人 | {total('agent总量')} |")
    if has_engage:
        lines.append(f"| 运营 | {count('运营总量')} 人 | {total('运营总量')} |")
    lines.append("")

    # per-module feature distribution (module heading + sub-table)
    lines.append("### 各模块功能分布\n")
    def sub_table(cats):
        t = ["| 功能类别 | 次数 |", "|---|---|"]
        for cat in cats:
            v = total(cat)
            if v > 0:
                t.append(f"| {cat} | {v} |")
        return t
    lines.append("**分析**\n")
    lines.extend(sub_table(ANALYSIS))
    lines.append("")
    if has_engage:
        lines.append("**运营**\n")
        lines.extend(sub_table(ENGAGE))
        lines.append("")
    if has_agent:
        lines.append("**agent**\n")
        lines.extend(sub_table(AGENT))
        lines.append("")

    # ===== 2. Per-user statistics =====
    lines.append("## 二、按人统计\n")
    lines.append("### 总览表（全量 %d 名）\n" % n)

    header = ["排名", "账号", "关注数据", "标签", "活跃项目（TOP3）", "关注报表", "数据导出", "分析动作"]
    if has_engage:
        header.append("运营动作")
    if has_agent:
        header.append("agent动作")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))

    def active_proj_cell(acct):
        top = active_proj_top3(acct_proj_count, acct)
        if not top:
            return "-"
        return "<br>".join(f"{p}（{c}）" for p, c in top)

    limit = n if top_n == 0 else min(top_n, n)
    for i, r in enumerate(ranked[:limit], 1):
        all_reports = acct_report_interest.get(r["acct"], [])
        reports = all_reports[:3]  # 「关注报表」列只展示 TOP3
        rc = "<br>".join(f"{nm.replace('|', '\\|')}（{c}）" for nm, c in reports) if reports else "-"
        summary = "、".join(summarize_reports([nm for nm, _ in all_reports])) if all_reports else "-"
        row = [str(i), r["user_name"], summary,
               "<br>".join(r["tags"]) if r["tags"] else "-",
               active_proj_cell(r["acct"]), rc,
               str(r["📤 数据导出"]), str(r["分析总量"])]
        if has_engage:
            row.append(str(r["运营总量"]))
        if has_agent:
            row.append(str(r["agent总量"]))
        lines.append("| " + " | ".join(row) + " |")

    from collections import Counter
    tc = Counter("、".join(r["tags"]) if r["tags"] else "(无标签)" for r in ranked)
    lines.append("")
    lines.append(f"**全量 {n} 名用户汇总**：")
    lines.append("　" + "｜".join(f"{k} {v} 人" for k, v in sorted(tc.items(), key=lambda x: -x[1])))
    lines.append("")

    # TOP boards (table: rank + one column per behavior category, cell = name count)
    def board_table(cats):
        maxn = max(len(top5(ranked, c)) for c in cats)
        t = ["| 排名 | " + " | ".join(cats) + " |", "|---|" + "---|" * len(cats)]
        for i in range(maxn):
            cells = []
            for c in cats:
                tp = top5(ranked, c)
                cells.append(f"{tp[i]['user_name']} {tp[i][c]}" if i < len(tp) else "")
            t.append(f"| {i+1} | " + " | ".join(cells) + " |")
        return t

    lines.append("### 分析动作 TOP 榜\n")
    lines.extend(board_table(ANALYSIS))
    lines.append("")
    if has_engage:
        lines.append("### 运营动作 TOP 榜\n")
        lines.extend(board_table(ENGAGE))
        lines.append("")
    if has_agent:
        lines.append("### agent 动作 TOP 榜\n")
        lines.extend(board_table(AGENT))
        lines.append("")

    # ===== 3. Project activity =====
    lines.append("## 三、项目活跃情况\n")
    lines.append("按项目聚合分析/看板行为的活跃情况（agent 行为无项目埋点，不纳入）。共 %d 个活跃项目。\n" % len(proj_list))
    lines.append("| 排名 | 项目名称 | 活跃人数 | 查看报表 | 查看看板 | 模型分析 | 新建看板 | 搭建报表 | 数据导出 | 动作总量 | 最活跃成员 | 最受关注报表 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, (proj, users, pm, tot, member_accts) in enumerate(proj_list, 1):
        mnames = [mapping.get(a, fallback_display_name(a, system_account)) for a in member_accts]
        build = pm["报表新建"] + pm["报表更新"]
        rep = proj_report_interest.get(proj, [])
        interest = f"报表：{rep[0][0].replace('|', '\\|')}（{rep[0][1]}）" if rep else "-"
        lines.append(f"| {i} | {proj} | {users} | {pm['报表查询']} | {pm['看板查询']} | {pm['模型查询']} | {pm['看板新建']} | {build} | {pm['数据导出']} | {tot} | {'、'.join(mnames)} | {interest} |")

    report = "\n".join(lines)
    print(report)

    if out_json:
        json.dump(ranked, open(out_json, "w"), ensure_ascii=False, indent=1)
        print(f"\n[full data saved] {out_json}")
    if feishu_xml:
        xml = render_feishu_xml(ranked, has_engage, has_agent, mapping, acct_proj_count, acct_report_interest, proj_report_interest, proj_list, system_account)
        open(feishu_xml, "w").write(xml)
        print(f"\n[Feishu XML saved] {feishu_xml}")
    return ranked


def render_feishu_xml(ranked, has_engage, has_agent, mapping, acct_proj_count, acct_report_interest, proj_report_interest, proj_list, system_account):
    """Generate the Feishu doc XML (structure matches the markdown report); write the file and import via lark-cli docs +create/+update."""
    esc = esc_xml
    n = len(ranked)

    def total(cat): return cat_total(ranked, cat)
    def count(cat): return cat_count(ranked, cat)

    X = []
    X.append('<title>审计项目系统使用情况报告</title>')
    X.append('<p>统计时间范围：最近 15 天（含今天）。统计口径：账号统一用 #account_id（user_name 为显示名）；已剔除自动任务与系统裸账号；未开通的模块不体现；项目维度基于分析/看板事件的 project_name 字段，agent 行为无项目埋点故不纳入项目维度。</p>')

    # ===== 1. Module usage & value assessment =====
    X.append('<h1>一、模块功能使用与价值评估</h1>')
    X.append('<h2>价值评估结论</h2>')
    X.append('<ol>')
    for c in build_conclusions(ranked, n, has_engage, has_agent):
        X.append(f'<li>{esc(c)}</li>')
    X.append('</ol>')

    X.append('<h2>使用量概览</h2>')
    X.append('<table><thead><tr><th>模块</th><th>活跃账号</th><th>动作总量</th></tr></thead><tbody>')
    X.append(f'<tr><td>分析（含看板）</td><td>{count("分析总量")} 人</td><td>{total("分析总量")}</td></tr>')
    if has_agent:
        X.append(f'<tr><td>agent</td><td>{count("agent总量")} 人</td><td>{total("agent总量")}</td></tr>')
    if has_engage:
        X.append(f'<tr><td>运营</td><td>{count("运营总量")} 人</td><td>{total("运营总量")}</td></tr>')
    X.append('</tbody></table>')

    X.append('<h2>各模块功能分布</h2>')

    def sub_table(cats):
        x = ['<table><thead><tr><th>功能类别</th><th>次数</th></tr></thead><tbody>']
        for cat in cats:
            v = total(cat)
            if v > 0:
                x.append(f'<tr><td>{esc(cat)}</td><td>{v}</td></tr>')
        x.append('</tbody></table>')
        return "".join(x)

    for name, cats in [("分析", ANALYSIS), ("运营", ENGAGE), ("agent", AGENT)]:
        if name == "运营" and not has_engage:
            continue
        if name == "agent" and not has_agent:
            continue
        X.append(f'<p><b>{name}</b></p>')
        X.append(sub_table(cats))

    # ===== 2. Per-user statistics =====
    X.append('<h1>二、按人统计</h1>')
    X.append(f'<h2>总览表（全量 {n} 名）</h2>')
    header = ["排名", "账号", "关注数据", "标签", "活跃项目（TOP3）", "关注报表", "数据导出", "分析动作"]
    if has_engage:
        header.append("运营动作")
    if has_agent:
        header.append("agent动作")
    X.append('<table><thead><tr>' + "".join(f'<th>{h}</th>' for h in header) + '</tr></thead><tbody>')

    def active_proj_cell(acct):
        top = active_proj_top3(acct_proj_count, acct)
        if not top:
            return "<p>-</p>"
        return "".join(f"<p>{esc(p)}（{c}）</p>" for p, c in top)

    def tags_cell(tags):
        if not tags:
            return "<p>-</p>"
        return "".join(f"<p>{esc(t)}</p>" for t in tags)

    for i, r in enumerate(ranked, 1):
        all_reports = acct_report_interest.get(r["acct"], [])
        reports = all_reports[:3]
        rc = "".join(f"<p>{esc(nm)}（{c}）</p>" for nm, c in reports) if reports else "<p>-</p>"
        summary = "、".join(summarize_reports([nm for nm, _ in all_reports])) if all_reports else "-"
        row = [f'<td>{i}</td>', f'<td>{esc(r["user_name"])}</td>', f'<td>{esc(summary)}</td>', f'<td>{tags_cell(r["tags"])}</td>',
               f'<td>{active_proj_cell(r["acct"])}</td>', f'<td>{rc}</td>', f'<td>{r["📤 数据导出"]}</td>', f'<td>{r["分析总量"]}</td>']
        if has_engage:
            row.append(f'<td>{r["运营总量"]}</td>')
        if has_agent:
            row.append(f'<td>{r["agent总量"]}</td>')
        X.append('<tr>' + "".join(row) + '</tr>')
    X.append('</tbody></table>')
    from collections import Counter
    tc = Counter("、".join(r["tags"]) if r["tags"] else "(无标签)" for r in ranked)
    X.append(f'<p><b>全量 {n} 名用户汇总</b>：' + "｜".join(f"{k} {v} 人" for k, v in sorted(tc.items(), key=lambda x: -x[1])) + '</p>')

    def board_table(cats):
        maxn = max(len(top5(ranked, c)) for c in cats)
        x = ['<table><thead><tr><th>排名</th>' + "".join(f"<th>{esc(c)}</th>" for c in cats) + '</tr></thead><tbody>']
        for i in range(maxn):
            cells = []
            for c in cats:
                tp = top5(ranked, c)
                cells.append(f'<td>{esc(tp[i]["user_name"])}　{tp[i][c]}</td>' if i < len(tp) else '<td></td>')
            x.append(f'<tr><td>{i+1}</td>' + "".join(cells) + '</tr>')
        x.append('</tbody></table>')
        return "".join(x)

    X.append('<h2>分析动作 TOP 榜</h2>')
    X.append(board_table(ANALYSIS))
    if has_engage:
        X.append('<h2>运营动作 TOP 榜</h2>')
        X.append(board_table(ENGAGE))
    if has_agent:
        X.append('<h2>agent 动作 TOP 榜</h2>')
        X.append(board_table(AGENT))

    # ===== 3. Project activity =====
    X.append('<h1>三、项目活跃情况</h1>')
    X.append(f'<p>按项目聚合分析/看板行为的活跃情况（agent 行为无项目埋点，不纳入）。共 {len(proj_list)} 个活跃项目。</p>')
    X.append('<table><thead><tr><th>排名</th><th>项目名称</th><th>活跃人数</th><th>查看报表</th><th>查看看板</th><th>模型分析</th><th>新建看板</th><th>搭建报表</th><th>数据导出</th><th>动作总量</th><th>最活跃成员</th><th>最受关注报表</th></tr></thead><tbody>')
    for i, (proj, users, pm, tot, member_accts) in enumerate(proj_list, 1):
        mnames = [mapping.get(a, fallback_display_name(a, system_account)) for a in member_accts]
        build = pm["报表新建"] + pm["报表更新"]
        rep = proj_report_interest.get(proj, [])
        interest = f"报表：{esc(rep[0][0])}（{rep[0][1]}）" if rep else "-"
        X.append(f'<tr><td>{i}</td><td>{esc(proj)}</td><td>{users}</td><td>{pm["报表查询"]}</td><td>{pm["看板查询"]}</td><td>{pm["模型查询"]}</td><td>{pm["看板新建"]}</td><td>{build}</td><td>{pm["数据导出"]}</td><td>{tot}</td><td>{"、".join(esc(m) for m in mnames)}</td><td>{interest}</td></tr>')
    X.append('</tbody></table>')

    return "\n".join(X)


def main():
    ap = argparse.ArgumentParser(description="审计项目使用分析")
    ap.add_argument("--prepare", action="store_true", help="generate query definition files")
    ap.add_argument("--out-dir", default="/tmp/audit", help="output dir for --prepare")
    ap.add_argument("--analysis", help="analysis+dashboard module jsonl.gz")
    ap.add_argument("--engage", help="engage module jsonl.gz (omit if not provisioned)")
    ap.add_argument("--agent", help="agent module jsonl.gz (omit if version < 6.0)")
    ap.add_argument("--mapping", help="account→display-name mapping json")
    ap.add_argument("--mapping-raw", help="account→display-name aggregated export jsonl.gz (replaces --mapping)")
    ap.add_argument("--account-project", help="account×project aggregated export jsonl.gz (project dimension)")
    ap.add_argument("--report-interest", help="report-interest aggregated export jsonl.gz (account×project×report name)")
    ap.add_argument("--top-n", type=int, default=20, help="overview table rows; 0 = full")
    ap.add_argument("--out-json", help="full detail dump path")
    ap.add_argument("--feishu-xml", help="also emit Feishu doc XML to this path (importable via lark-cli docs)")
    args = ap.parse_args()

    if args.prepare:
        prepare(args.out_dir)
        return
    if not args.analysis:
        ap.error("需提供 --analysis，或用 --prepare 生成定义")
    analyze(args.analysis, args.engage, args.agent, args.mapping, args.mapping_raw, args.account_project, args.report_interest, args.top_n, args.out_json, args.feishu_xml)


if __name__ == "__main__":
    main()
