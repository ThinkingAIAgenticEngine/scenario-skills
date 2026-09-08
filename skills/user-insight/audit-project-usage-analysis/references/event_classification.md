# Event Classification & Metrics Reference

Behavior classification, emoji conventions, and automated-task filtering rules for the 审计项目 (Audit Project) tracking events. The classifications in `scripts/generate_report.py` must stay in sync with this file — update both when changing.

> **Language note:** emoji + Chinese labels below are the **runtime display values** used in report output (customer business language), not documentation text.

## 1. Analysis module classification (emoji + event name)

The analysis module is baseline and always counted. Dashboards are merged into analysis actions, but behavior boards still break them out.

| Behavior category (emoji) | Event names | Meaning |
|---|---|---|
| 🧮 Model analysis | `model_search`, `model_page_action`, `metric_sql` | run model / SQL query |
| 📋 View report | `report_search` | view an existing report |
| 📌 View dashboard | `dashboard_search`, `mobile_dashboard_search` | browse dashboard |
| 🗂️ Dashboard management | `dashboard_action`, `dashboard_report_panel_action`, `dashboard_report_edit_save`, `dashboard_report_remove`, `dashboard_space_action`, `dashboard_space_create`, `dashboard_space_delete`, `dashboard_delete`, `dashboard_folder_export_import` | in-dashboard ops, space management |
| 🏗️ Build report | `report_save`, `report_edit`, `chart_save`, `report_del` | create/update report, chart |
| 📤 Data export | `export_data`, `download_data` | export/download data |
| 🏷️ Segmentation | `cluster_create`, `cluster_edit`, `cluster_refresh`, `cluster_delete`, `user_group_create`, `user_group_edit` | segment/label management |
| 🆕 Create dashboard | `dashboard_create` | build dashboard |
| 📦 Other analysis | `metric_create`, `metric_edit`, `metric_delete`, `virtual_event_create`, `virtual_properties_create`, `dataset_action`, `note_edit` | metric, virtual, dataset, note |

## 2. Engage module classification (separately purchased, may be absent)

If not provisioned (total `engage_*` = 0 over 15 days), the report omits the module entirely.

| Behavior category (emoji) | Event names | Meaning |
|---|---|---|
| 🎯 Task operations | `engage_task_list_click`, `engage_create_task_click`, `engage_task_data_click`, `engage_task_data_search`, `engage_task_metric_view` | task create/view/data |
| 📣 Channel management | `engage_channel_click` | channel reach |
| 🎪 Activities & others | `engage_activity_list_click`, `engage_activity_edit`, `engage_activity_approve`, `engage_activity_data_click`, `engage_activity_task_group`, `engage_common_metrics_edit`, `engage_send_preview_click`, `engage_task_ab_report_op`, `engage_task_cohort_click`, `engage_workbench_gantt_op` | activity, metric, preview, etc. |

**Automated-task exclusion**: the following `*_model` events are page-browse auto tracking (recorded under the system bare account), not counted as "engage actions":
`engage_task_model`, `engage_activity_model`, `engage_channel_model`, `engage_task_instance_model`

## 3. Agent module classification (default on 6.0+)

Below 6.0, the report omits the module.

| Behavior category (emoji) | Event names | Meaning |
|---|---|---|
| 💬 Conversations | `agent_session_message_send`, `agent_session_message_receive` | user ↔ agent messages |
| 🔧 Tool calls | agent tool-call event | tool-call behavior |
| 🗂️ Session management | `agent_session_create`, `agent_session_update`, `agent_session_delete` | session lifecycle |
| 🧩 Skill management | `agent_skill_create`, `agent_skill_update`, `agent_skill_enable`, `agent_skill_disable`, `agent_skill_delete` | skill lifecycle |
| 🤖 Agent management | `agent_create`, `agent_update`, `agent_enable`, `agent_disable`, `agent_delete` | agent lifecycle |
| ⚙️ Sandbox & model | `agent_sandbox_delete`, `agent_sandbox_update`, `agent_model_create`, `agent_model_enable`, `agent_model_disable`, `agent_model_update`, `agent_model_delete`, agent tool-config events, `agent_user_enable`, `agent_user_disable` | sandbox, model config, tool config, members |

> The agent tool-call event records tool-call behavior; its `call_source` property (`te-agent` automated / `customer` user-initiated / `ae-cli`) all count into the tool-call total — no proactive/reactive split (backend channels, normal usage).

## 4. Project-dimension event list (`def_account_project.json`)

The project dimension is based on analysis/dashboard events that carry a `project_name` field (grouped by `#account_id` + `project_name`). Agent events carry no project field, so they are excluded.

| Column | Event | Meaning |
|---|---|---|
| report view | `report_search` | view report |
| dashboard view | `dashboard_search` | view dashboard |
| dashboard create | `dashboard_create` | create dashboard |
| report create | `report_save` | create report |
| report update | `report_edit` | update report |
| data export | `export_data` | export data |
| model query | `model_search` | model analysis |

Feeds: the "active projects TOP3" column (top-3 projects per account by action volume) + the "project activity" module (per-project rollup with top-3 members).

## 5. Business-attention field (`def_report_interest.json`)

Report names are the direct source of "what business data each person/project cares about" (the name IS the business theme).

| Field | On event | Usage |
|---|---|---|
| `report_name` | `report_search` | the user's most-viewed reports (e.g. 充值总额 / 付费率 / 渠道新增用户数) |

Grouped by `#account_id` + `project_name` + `report_name`, counting `total_count`. Derived:

- "business attention" module: group by `#account_id`, per-person report TOP3;
- project table "top report" column: group by `project_name`, per-project TOP1 report.

Theme summarization: the script maps report-name keywords to business themes (ordered match, first hit wins); the mapping lives in `REPORT_THEMES` in `scripts/generate_report.py`:

Agent usage / payment-revenue / data-dev / data-resource-usage / user-growth-activity / user-profile-segmentation / ops-monitoring / base-data.

Notes: `metric_ename` (metric name) is essentially null on `metric_sql`, unusable; `query` (SQL text) is available but mixed with heavy `information_schema` system queries, so it is not included in this skill; for data-export events, only `download_data` carries `download_type` (event-list / event-analysis / SQL-query — functional-level type, no business-level report name), so it is also not folded into business attention.

## 6. Metrics quick reference

| Item | Rule |
|---|---|
| Account basis | unified `#account_id` (user property); `user_name` is display-only |
| System bare account | exclude the tenant prefix account when present (auto-detected, with no hardcoded fallback) |
| metric_sql scheduled task | filter `sql_query_system_refresh is_false` (bool field, do NOT use `neq`) |
| Low-level auto events | `metric_task`, `metric_interface` not counted as analysis actions |
| Time range | recent 15 days = `{"mode":"recent","unit":"day","value":15}` (includes today) |
| Version gate | `ta_version` field, ≥ 6.0 counts agent |

## 7. Tracking-plan doc cross-check (background)

The doc 《审计项目_埋点方案1.0.10》 lists 62 events, 100% of which are landed in the project, but the project actually has 123 events — the doc lags behind, missing `engage_*` (engage), `metric_*` (metric), `member_*`, agent tool-config events, `mobile_*` and other new events. Therefore the classification follows the **project's actual events**, not the doc.
