# Project Configuration

> **This file is the sole bridge between business concepts and database fields. When switching projects, only modify this file.**
>
> `{{event.xxx}}` and `{{prop.xxx}}` are business concept placeholders, NOT actual database field names.
> Leave a value empty if unsure. Step 01 will assist with discovery and confirmation.

---

## 1. Project Identity

| Concept | Value | Description | Example |
|---------|-------|-------------|---------|
| Project ID | [Fill in] | TE platform project ID | `196` |
| Timezone | `UTC+8` | Analysis timezone | `UTC+8` |
| Game Name | [Fill in] | Used in report title | `Happy Match` |
| Version | [Fill in] | Current postmortem version | `v2.3.0` |

## 2. Analysis Time Window

| Concept | Value | Description | Example |
|---------|-------|-------------|---------|
| Start Date | [Fill in] | Format yyyy-MM-dd | `2026-07-01` |
| End Date | [Fill in] | Format yyyy-MM-dd | `2026-07-07` |

## 3. Event Name Mapping

Fill in actual event names from the project tracking plan.

| Concept | Actual Name | Description | Example |
|---------|------------|-------------|---------|
| `{{event.register}}` | [Fill in] | Registration | `user_register` |
| `{{event.daily_login}}` | [Fill in] | Daily login / App launch | `daily_login` |
| `{{event.level_start}}` | [Fill in] | Level start | `level_start` |
| `{{event.level_complete}}` | [Fill in] | Level completed | `level_complete` |
| `{{event.level_fail}}` | [Fill in] | Level failed | `level_fail` |
| `{{event.ad_impression}}` | [Fill in] | Ad impression | `ad_show` |
| `{{event.ad_click}}` | [Fill in] | Ad click | `ad_click` |
| `{{event.session_end}}` | [Fill in] | Session end / app background | `session_end` |

## 4. Property Field Mapping

| Concept | Actual Name | Parent Event | Type | Example |
|---------|------------|-------------|------|---------|
| `{{prop.level_id}}` | [Fill in] | Level events | string/number | `level_id` |
| `{{prop.pass_result}}` | [Fill in] | Level complete/fail | bool/string | `is_win` |
| `{{prop.move_count}}` | [Fill in] | Level complete | number | `moves` |
| `{{prop.attempt_count}}` | [Fill in] | Level complete | number | `attempts` |
| `{{prop.ad_type}}` | [Fill in] | Ad event | string | `ad_type` |
| `{{prop.ad_scene}}` | [Fill in] | Ad event | string | `ad_placement` |
| `{{prop.session_duration}}` | [Fill in] | Session end | number (sec) | `duration` |
| `{{prop.register_date}}` | [Fill in] | Register / user prop | date | `register_date` |

## 5. Thresholds

| Concept | Default | Description |
|---------|---------|-------------|
| `{{threshold.first_level_pass_rate}}` | `95%` | First level pass rate warning line |
| `{{threshold.churn_definition_days}}` | `1` | Days without login = churned |
| `{{threshold.newbie_zone_levels}}` | `10` | Newbie zone range |
| `{{threshold.content_light_max}}` | `5` | Light consumption cap |
| `{{threshold.content_medium_max}}` | `20` | Medium consumption cap |
| `{{threshold.content_heavy_max}}` | `40` | Heavy consumption cap |
| `{{threshold.overdraft_warning}}` | `40` | D1 levels > this → overdraft |
| `{{threshold.duration_overdraft_ratio}}` | `3` | D1/D2 duration ratio warning |
| `{{threshold.retention_fracture_ratio}}` | `2` | Decay ratio fracture signal |

## 6. Output / Publishing

| Concept | Value | Description |
|---------|-------|-------------|
| `{{workspace_dir}}` | `/tmp/puzzle-iaa-analytics/` | Intermediate file dir |
| Publish Target | [Fill in] | Feishu Wiki / Cloud Space / Group / Local |
