---
name: ad-delivery-analysis
description: "Comprehensive ad campaign performance analysis covering channel efficiency, conversion funnels, attribution analysis, retention quality, and ROI calculation on the ThinkingEngine (TE) platform. Use when users need to evaluate ad campaign performance, analyze channel efficiency, diagnose funnel drop-offs, attribute conversions to touchpoints, or calculate ROI across channels."
---

# Ad Delivery Analysis

## Language Policy

**CRITICAL**: Always respond in the user's language.
- If user writes in English → Respond in English
- If user writes in Chinese → Respond in Chinese
- Never translate the user's language; match their input language exactly

## Core Scenarios

### 1. Channel Performance Overview

Analyze core ad metrics by channel, OS, and region dimensions.

**Common metrics:**
- Impressions: `ad_impression` + `total_count`
- Clicks: `ad_click` + `total_count`
- Installs: `app_install` + `user_count`
- Registrations: `register` + `user_count`
- Revenue: `payment` + `sum` + `amount`

**Common grouping dimensions:**
- Channel: `channel`, `utm_source`, `media_source`
- Campaign: `campaign_id`, `campaign_name`
- Creative: `creative_id`
- OS: `#os`
- Region: `#city`, `#province`, `#country`

**Workflow:**
1. Compose the semantic `event` AI-facing definition
2. `analysis adhoc run --model-type event --definition '<json>'` — compile and query metrics with `groups`
3. Use `analysis-meta event/property list` only after structured clarification
4. For comparisons, run explicitly aligned periods and verify timezone/scope

### 2. Ad Conversion Funnel

Analyze the full conversion path from impression → click → install → register → payment to identify drop-off points.

**Workflow:**
1. Confirm event names for each funnel step
2. Use `--model-type funnel`
3. Set `funnel.window`
   - Click to install: 1-7 days recommended
   - Install to register: 1 day recommended
   - Register to first payment: 7-30 days recommended
4. Add channel to `funnel.groups` when segmentation is required
5. After a successful query, use only the advertised query-context drilldown actions

### 3. Ad Attribution Analysis

Determine which ad touchpoint contributes most to conversions.

**Three attribution models:**
| Model | Description | Best For |
|-------|-------------|----------|
| `first` | First touch — 100% credit to first ad touchpoint | Brand awareness campaigns |
| `last` | Last touch — 100% credit to last ad touchpoint | Performance-driven campaigns |
| `linear` | Equal credit to all touchpoints | Fair multi-channel evaluation |

**Workflow:**
1. Select `attribution.target_event`, e.g. `payment` or `register`
2. Select `attribution.attribution_events`, e.g. `ad_impression`, `ad_click`
3. Set `attribution.window` (typically 7-30 days for mobile)
4. Set `direct_conversion=true` to include conversions without touchpoints
5. Run `analysis adhoc run --model-type attribution`
6. Drill down to view specific user touchpoint sequences

### 4. Channel Retention Analysis

Measure long-term user quality by acquisition channel.

**Workflow:**
1. Use `--model-type retention`
2. Set `retention.initial_event` and `retention.return_event`
3. Set `retention.unit_num`, e.g. 7 for day-7 retention
4. Set `rtn_rate_or_num` to `rate` or `count`
5. Set `stat_type` to `retention` or `lost`
6. Add the channel property to `retention.groups`

Use a top-level AI-facing filter only when its field type and exact value have
been verified. Do not copy raw-QP event type codes.

### 5. ROI & LTV Analysis

Calculate user lifetime value and campaign ROI by channel.

**LTV Analysis:**
- Use tags/clusters to mark users' first channel
- Persist a tag or cluster only after user confirmation
- Query cumulative payments within N days per cluster

**ROI formulas:**
- CPA = Ad Spend / Acquired Users
- ARPU = Total Revenue / Users
- ROAS = Revenue / Ad Spend

### 6. Creating Monitoring Reports & Dashboards

**Workflow:**
1. Run and verify the AI-facing definition first
2. Ask for confirmation before creating or updating assets
3. `analysis report create` — create a standalone report with `--model-type` and `--definition`
4. `analysis dashboard create --initial-report-id <report_id>` — create a dashboard

## Query Template Reference

See [`references/query-templates.md`](references/query-templates.md) for AI-facing JSON templates.

## Notes

1. **Event and property names must resolve exactly**: inspect compiler resolution; use `analysis-meta` only after clarification
2. **Time calculation rules**:
   - `past N days` = `[today-N-1, today-1]` (excludes today)
   - `recent N days` = `[today-N+1, today]` (includes today)
3. **Attribution window** depends on business conversion cycle: typically 7 days for gaming, 30 days for e-commerce
4. **Do not pass raw QP**: `--definition` accepts only the documented AI-facing structure
5. **Drilldown**: use only coordinates and actions advertised by the returned query context
6. **Results can be written to Feishu docs** using the `lark-doc` skill
7. **Multi-model combined analysis**: Channel overview → Funnel diagnosis → Attribution confirmation → Retention validation forms a complete analysis loop
