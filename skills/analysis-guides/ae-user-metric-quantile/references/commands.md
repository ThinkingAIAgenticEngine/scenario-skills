# Step-by-Step Command Templates and Full Walkthrough

> All commands run through the AE CLI. Confirm `<project_id>` with `ae-cli project info list`; event/property names can use either display names or technical names — after creation, verify the resolution against the `resolved` field in the response.

> **Event confirmation**: before starting, only confirm the "metric event + numeric property" business detail; if the request is vague, use AskUserQuestion to let the user choose (in plain language), and if the user does not specify, look them up yourself with `ae-cli analysis-meta event list` / `analysis-meta property list`. **The trigger event is not asked of the user**; it defaults to the metric event (both the first/last tag and the report metric event use the same event as the metric-value tag); only switch to an activity event (login/launch) when the user explicitly asks to count all active users (including those who did not trigger the metric event).

## Step 1: Metric-value tag (each user's daily duration P75)

**The `value` of `time_range` is determined by the "metric value granularity"**:

- Each user **per day** XX → `{"mode":"recent","unit":"day","value":1}` (this walkthrough)
- Each user over the **past N days** XX → `recent day N` (including today) or `previous day N` (excluding today), depending on whether "past N days" includes today

**For daily scenarios (day 1) you must use `recent` (including today)**, not `previous` (excluding today) — the latter shifts the tag version date off by one day from the value date (off-by-one), so `#event_time = first-occurrence time` no longer matches, dedup fails, and the report returns empty:

```bash
ae-cli analysis user-tag create \
  --project-id <project_id> \
  --tag-name user_daily_duration_p75 \
  --display-name "Each user's daily duration P75" \
  --definition-request '{"type":"metric","metric":{"event":"Logout","aggregation":"percentile","property":"Online Duration","percentile":75,"time_range":{"mode":"recent","unit":"day","value":1}}}' \
  --zone-offset 8 \
  --enable-auto-refresh true \
  --auto-refresh-schedule '{"frequency":"daily","time":"23:59"}'
```

- The tag subject = user (consistent with the analysis subject); the time zone matches the analysis time zone.
- Creation automatically starts the first computation — **do NOT manually refresh again**; check the computation status and `next_action` with `ae-cli analysis user-tag get --project-id <project_id> --tag-names '["user_daily_duration_p75"]'`.

Backfill the historical versions for the past 7 days in batch (adjust the dates to your summary window):

```bash
ae-cli analysis history-tag batch-refresh \
  --project-id <project_id> \
  --tag-name user_daily_duration_p75 \
  --refresh-request '{"start_time":"2026-09-13","end_time":"2026-09-19"}'
```

Use `ae-cli analysis history-tag list --project-id <project_id> --tag-name user_daily_duration_p75` to confirm every date's version exists.

## Step 1 Quick Reference by Caliber

Step 1 is the only step that varies by caliber; all other steps are identical. Just swap `metric.aggregation` (percentile additionally takes `percentile`):

| Caliber | semantic key | Requires `property` | `definition_request` fragment (`time_range` is mandatory) |
|---|---|---|---|
| Total Count | `count` | No (pure event counting) | `{"type":"metric","metric":{"event":"Payment","aggregation":"count","time_range":{"mode":"recent","unit":"day","value":1}}}` |
| Active Days | `active_days` | No | `{...,"aggregation":"active_days",...}` |
| Sum | `sum` | Yes | `{...,"aggregation":"sum","property":"Amount",...}` |
| Average | `avg` | Yes | `{...,"aggregation":"avg","property":"Amount",...}` |
| Maximum | `max` | Yes | `{...,"aggregation":"max","property":"Amount",...}` |
| Minimum | `min` | Yes | `{...,"aggregation":"min","property":"Amount",...}` |
| Median | `median` | Yes | `{...,"aggregation":"median","property":"Amount",...}` |
| Percentile | `percentile` | Yes + `percentile` | `{...,"aggregation":"percentile","property":"Amount","percentile":90,...}` |

Notes:

- `metric.time_range` is strictly validated as mandatory by the backend; if missing it reports `recentDay or (startTime and endTime)`.
- Calibers that take a `property` require the property to be **numeric**.
- `count / active_days` are property-less counting calibers usable as tag values; the tag-side semantic key for "Total Count" is `count` (not `total_count`), and that counting result can be further analyzed with median/percentile statistics (the core usage of this skill).
- **The tag side and the report side are two separate aggregation enums**: `variance`/`stddev`/`distinct_count`/`avg_per_user`/`user_count`/`per_user_count` etc. are aggregations of the Events Analysis report (Step 4) — they run cross-user statistics over the Step 3 virtual property and **cannot** be used as Step 1 tag calibers.
- **Creation success ≠ valid caliber**: the backend performs no strict enum validation on `metric.aggregation`; an invalid key does not error at the `create`/`--validate` stage — it only fails at computation time (`analysis user-tag get`'s `debug_msg` reports `unknown analysisTypeValue: <key>`). After creation you must check the computation status with `analysis user-tag get`.
- Recommended tag naming includes the caliber for later identification: `user_daily_amount_sum`, `user_daily_amount_avg`, `user_daily_amount_max`, `user_daily_duration_p75`.

## Step 2: First/last tag (time of the first logout each day)

> The first/last tag's event **defaults to the same event as the Step 1 metric-value tag** (logout in this walkthrough), serving as the "dedup anchor"; only switch to an activity event (login/launch) when the user explicitly asks to count all active users.

```bash
ae-cli analysis user-tag create \
  --project-id <project_id> \
  --tag-name user_daily_first_logout_time \
  --display-name "First Logout Time Each Day" \
  --definition-request '{"type":"first_last","first_last":{"event":"Logout","occurrence":"first","calculation":"specific_time","time_range":{"mode":"recent","unit":"day","value":1}}}' \
  --zone-offset 8 \
  --enable-auto-refresh true \
  --auto-refresh-schedule '{"frequency":"daily","time":"23:59"}'
```

**`time_range` must exactly match the Step 1 metric tag** (both day 1 for daily, both day N for window); keep the time zone and refresh schedule consistent with Step 1; also backfill historical versions in batch:

```bash
ae-cli analysis history-tag batch-refresh \
  --project-id <project_id> \
  --tag-name user_daily_first_logout_time \
  --refresh-request '{"start_time":"2026-09-13","end_time":"2026-09-19"}'
```

> **Auto backup (mandatory; enable it manually in the UI)**: auto-update (`--enable-auto-refresh`) and "auto backup" are two independent switches; enabling the former does not automatically enable the latter. `ae-cli` has no "enable auto backup" API (only the `analysis-governance asset batch-disable-auto-backup` disable capability). After creating the two tags, be sure to manually turn on "Auto Backup" for both tags in the TE UI under "Tag Management → Edit Tag"; otherwise daily historical versions will not accumulate automatically and the report's historical trend will stop updating. For the first run, use the `history-tag batch-refresh` above to manually backfill historical versions as a fallback.

## Step 3: Virtual event properties (referencing tags, created via CLI)

Reference the metric-value tag with `ta_tag."<tag_name>"`, and specify dynamic matching (AUTO) via `--tag-date-policies`:

```bash
ae-cli analysis-meta virtual-property create \
  --project-id <project_id> \
  --property-name '#vp@daily_duration_p75' \
  --property-desc 'Daily duration P75 per user (referencing a tag)' \
  --table-type event \
  --select-type number \
  --sql-expression 'ta_tag."user_daily_duration_p75"' \
  --sql-event-relation-type relation_always \
  --tag-date-policies '[{"tag_name":"user_daily_duration_p75","cluster_date_policy":"AUTO"}]'
```

Then create the boolean dedup property (marking the user's first metric event of the day):

```bash
ae-cli analysis-meta virtual-property create \
  --project-id <project_id> \
  --property-name '#vp@is_first_Logout' \
  --property-desc 'Whether this is the first logout of the day for the user' \
  --table-type event \
  --select-type bool \
  --sql-expression '("#event_time" = ta_tag."user_daily_first_logout_time")' \
  --sql-event-relation-type relation_always \
  --tag-date-policies '[{"tag_name":"user_daily_first_logout_time","cluster_date_policy":"AUTO"}]'
```

Key points:

- `ta_tag."<tag_name>"` references the tag result; the percentile is still computed by the tag, not by pure SQL statistics; `#event_time` must be wrapped in double quotes.
- The field name of each `--tag-date-policies` entry is `tag_name` (**NOT `cluster_name`**), combined with `cluster_date_policy` set to `AUTO` for dynamic matching; a wrong field name causes CAPABILITY_EXECUTION_FAILED. A missing entry or `LATEST` causes historical dates to pick the wrong version (old dates get 0 or equal the latest day).
- `--sql-event-relation-type=relation_always` means the property relates to all events.
- Verification: `ae-cli analysis-meta property get --project-id <project_id> --prop-name '#vp@daily_duration_p75' --table-type event`, confirming `vir_prop_column_rule` is `ta_tag."user_daily_duration_p75"`.

## Step 4: Events Analysis report (average of the daily logout duration P75 over the past 7 days)

**DO NOT use an SQL report to dynamically match historical tag versions**; use `--model-type event`:

```bash
ae-cli analysis report create \
  --project-id <project_id> \
  --report-name "Average of daily logout duration P75 over the past 7 days" \
  --model-type event \
  --definition '{
    "time_range": {"mode":"previous","unit":"day","value":7},
    "time_particle_size": "day",
    "metrics": [
      {"event":"Logout","aggregation":"avg","property":"#vp@daily_duration_p75"}
    ],
    "filters": [
      {"field":{"name":"#vp@is_first_Logout"},"operator":"is_true"}
    ],
    "relation":"and"
  }'
```

Key points:

- The report metric event = the metric-value tag's event (same as Step 1 by default, logout in this walkthrough); swap `"aggregation":"avg"` for `percentile` (with `"percentile":<P>`), `max`, `min`, `median`, `variance`, `stddev`, or `distinct_count` to get the corresponding statistic.
- The metric `property` is the virtual property name (`#vp@...`), not the tag name; tags cannot be used directly as metric properties (error: `No property matched the input`).
- The first/last tag value is datetime, so the `relative_event_time` operator does not apply (error: `FILTER_OPERATOR_TYPE_INVALID`); always dedup with the boolean virtual property `is_true`.
- If the compiler reports errors, fix them per the `resolutions` in the response. Pre-validate the same command with `analysis report create ... --validate`; `analysis query-context get` is a post-query drilldown command and cannot validate a report definition before execution.

## Step 5: Publish the report to a dashboard

```bash
# View dashboards
ae-cli analysis dashboard list --project-id <project_id> --limit 50

# User-specified dashboard: add to the existing dashboard
ae-cli analysis dashboard-report add --project-id <project_id> --dashboard-id <dashboard_id> --report-ids '[<report_id>]'

# User unspecified: create a default dashboard and add the report as its initial report
ae-cli analysis dashboard create --project-id <project_id> --dashboard-name "Default Dashboard" --initial-report-id <report_id>
```

Verify the data (`report_id` comes from the report create response, or look it up first with `ae-cli analysis report list`). Use `--timeout-seconds 180` for a bounded synchronous query. Omit `--zone-offset` to match the report UI; only pass a fixed offset when it has been verified for the current project and requested analysis:

```bash
ae-cli analysis report-data run --project-id <project_id> --report-ids '[<report_id>]' --preview-rows 100 --timeout-seconds 180
```

## Step 6: Provide the report/dashboard links (delivery)

Deliver **exactly two links: one report link + one dashboard link**; do not list any more links (extra reports, the report list page, etc. must not be given):

- The report link must be **the daily trend report only** (the one broken down by day with `time_particle_size:"day"` in Step 4). Other reports created/verified along the way (e.g., the overall window summary report) must not appear in the delivered links.
- **Links must state their type explicitly**: the two links each on their own line, labeled "Report" / "Dashboard" at the start of the line, with a `Report:` / `Dashboard:` prefix in the link text.
- **Obtain both real links with `analysis-meta asset url-get`**. Use the report and dashboard IDs returned by the create/add flow, and return each command's `markdown_link`. Do not construct a route or assume a tenant domain: the capability resolves the actual host and rewrites supported relative links to absolute URLs.

```bash
ae-cli analysis-meta asset url-get --project-id <project_id> --resource-type report --resource-id <report_id>
ae-cli analysis-meta asset url-get --project-id <project_id> --resource-type dashboard --resource-id <dashboard_id>
```

The following illustrates the required labeled output shape only. `web-ta-demo.thinkingdata.cn` is an example host; actual output must use the `markdown_link` returned by `asset url-get`:

```markdown
- Report: [Report: Average of daily logout duration P75 over the past 7 days](https://web-ta-demo.thinkingdata.cn/#/tga/event/9_123456)
- Dashboard: [Dashboard: User Online Duration Analysis](https://web-ta-demo.thinkingdata.cn/#/panel/panel/9_654321_0)
```

`report_id` comes from the `report create` response or `analysis report list` (take the daily trend report's ID); `dashboard_id` comes from `dashboard create` / `dashboard list`.

## Troubleshooting

| Problem | Investigation |
|---|---|
| Average is too large/small and fluctuates with activity | Missing boolean virtual property dedup, or the filter is not `is_true` |
| Report returns empty / only the latest date has values | The daily-scenario tag used `mode=previous` (excluding today), causing version misalignment (off-by-one), or the `time_range` of the metric and first_last tags is inconsistent; change daily to `mode=recent` and make the two tags consistent |
| All historical dates have the same value | The virtual property's `--tag-date-policies` did not use `AUTO` (dynamic matching), or the field name is wrong (should be `tag_name`, not `cluster_name`) |
| Virtual property creation fails with CAPABILITY_EXECUTION_FAILED | Wrong field name in `--tag-date-policies`; the correct form is `[{"tag_name":"<tag_name>","cluster_date_policy":"AUTO"}]` |
| No values for historical dates | Tag historical versions were not backfilled in batch (Step 1/2 batch-refresh) |
| Report query raises QUERY_TIMEOUT | Add `--timeout-seconds 180` to `report-data run`; omit `--zone-offset` unless the current project requires a verified fixed offset |
| Percentile errors | percentile only supports 5/10/20/25/30/40/60/70/75/80/90/95/99, and the property must be numeric |
| Creating a tag raises `recentDay or (startTime and endTime)` | `metric.time_range` was not provided; metric tags must specify a time range |
| `sum`/`avg`/`max`/`min`/`median`/`percentile` etc. error | That caliber requires a numeric property |
| Invalid caliber error | Use the semantic keys from the table above; do not pass internal A-codes or non-English caliber names |
| Report compilation raises `No property matched the input` | The metric `property` was set to the tag name; it should be the Step 3 virtual property name `#vp@...` |
| Report compilation raises `relative_event_time is not supported` / `FILTER_OPERATOR_TYPE_INVALID` | The first/last tag value is datetime; switch to the boolean virtual property `is_true` for dedup |
| Report is not in the dashboard | Step 5 was not executed; add it with `dashboard-report add` or `dashboard create --initial-report-id` |
