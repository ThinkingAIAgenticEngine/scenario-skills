# SQL Templates

> **Status: ✅ VERIFIED (2026-09-17).** The `--model-type sql` path IS raw SQL. Correct shape is `{"sql":"..."}` with table `hive.ta.v_event_N` and column `"#event_name"`. Full verified spec (format, table/column naming, date-partition requirement, identity-field gotchas) lives in `data-validation.md` §4.3.5 — **read it before writing any SQL**.
> These templates are **reference/education templates** (use `{placeholders}`), not copy-paste-run code. Before executing, substitute the real table (`hive.ta.v_event_{project_id}`), real column names, and add the mandatory `"$part_date"` predicate (event tables reject SQL without it).
> **Cohort rule**: In T2/T3, `{caliber_event}` is the user-confirmed new-user event. Build `first_day_users` from that event only; a user's first event inside the query window is not evidence that the user is new.
> **Convention**: Escape single quotes by doubling (`''`). Dialect: Presto/Trino-compatible. Identifiers containing `#`/`$`/`@`/spaces MUST be double-quoted (`"#event_name"`, `"$part_date"`, `"#account_id"`).

> **Template verification status** (what's been live-tested vs reference-only):
> | Template group | Status |
> |----------------|--------|
> | T1.x–T4.x (all below) | 🔶 Reference templates — logic is sound but not every variant has been executed against a live project |
> | "注册当天抽卡 → D1 留存" pattern | ✅ Live-tested (project 2, 2026-09-17) — see `data-validation.md` §4.3.5 for the exact verified SQL |
> | Behavior × retention lift (did X on D0) | ✅ Live-tested — same §4.3.5 pattern, change `DATE_ADD('day',1,...)` to 3/7 for D3/D7 |

---

## Phase 1 — Caliber Confirmation (Data Quality Verification)

> Phase 1 不仲裁口径（口径由用户直接确认，见 SKILL.md §1）。这里的 SQL 用于在口径确定后**验证数据质量**，而非比较多个口径推荐最优解。

### T1.1 New-User Count by Confirmed Caliber

```sql
-- Count new users by the user-confirmed caliber event
-- Replace {caliber_event} with the event name the user provided (e.g., 'register')
SELECT 
  COUNT(DISTINCT "#account_id") as new_user_count,
  COUNT(DISTINCT "#distinct_id") as distinct_id_count
FROM hive.ta.v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
  AND "#event_name" = '{caliber_event}'
```

**Notes**:
- Use the caliber event **verbatim** as the user stated it. Do NOT substitute your own event guess.
- `#account_id` (logged-in identity) vs `#distinct_id` (device/anonymous) mismatch reveals guest-play or multi-device inflation.

### T1.2 Caliber Coverage / Missing-Property Check

```sql
-- Data-quality check: what fraction of the confirmed-caliber cohort has each key property?
SELECT 
  COUNT(*) as total,
  COUNT("#account_id") as with_account_id,
  COUNT("channel") as with_channel,
  COUNT("device_model") as with_device_model,
  COUNT("region") as with_region
FROM (
  SELECT DISTINCT "#account_id", "channel", "device_model", "region"
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
)
```

**Notes**:
- Low `with_channel` ratio (e.g., <50%) means channel analysis will be distorted — flag it in the report, do not silently drop the null channel.
- This is the "does my caliber actually have clean data" check, NOT a caliber comparison.

---

## Phase 2 — First-Day Quality Scoring

### T2.1 Engagement Depth Metrics

```sql
-- Per-cohort engagement depth on first day
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
first_day_sessions AS (
  SELECT 
    e."#distinct_id" as user_id,
    f.first_date,
    COUNT(DISTINCT e."#session_id") as session_count,
    SUM(e.duration) as total_duration_sec,
    COUNT(DISTINCT e."#event_name") as unique_event_types,
    COUNT(*) as total_events
  FROM hive.ta.v_event_{project_id} e
  JOIN first_day_users f ON e."#distinct_id" = f.user_id AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY e."#distinct_id", f.first_date
)
SELECT 
  first_date as cohort_date,
  COUNT(*) as cohort_size,
  AVG(session_count) as avg_sessions,
  AVG(total_duration_sec) as avg_duration_sec,
  AVG(unique_event_types) as avg_unique_events,
  AVG(total_events) as avg_total_events,
  PERCENTILE(session_count, 0.5) as median_sessions,
  PERCENTILE(total_duration_sec, 0.5) as median_duration_sec
FROM first_day_sessions
GROUP BY first_date
ORDER BY first_date
```

### T2.2 Feature Adoption Metrics

```sql
-- Per-cohort feature adoption rates
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
feature_usage AS (
  SELECT 
    f.first_date,
    e."#event_name",
    COUNT(DISTINCT e."#distinct_id") as users_used
  FROM hive.ta.v_event_{project_id} e
  JOIN first_day_users f ON e."#distinct_id" = f.user_id AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND e."#event_name" IN ({feature_event_list})
    -- e.g., ('tutorial_complete', 'search', 'add_cart', 'like', 'signup')
  GROUP BY f.first_date, e."#event_name"
),
cohort_sizes AS (
  SELECT first_date, COUNT(*) as cohort_size
  FROM first_day_users
  GROUP BY first_date
)
SELECT 
  fu.first_date,
  fu."#event_name",
  fu.users_used,
  cs.cohort_size,
  fu.users_used * 100.0 / cs.cohort_size as adoption_rate_pct
FROM feature_usage fu
JOIN cohort_sizes cs ON fu.first_date = cs.first_date
ORDER BY fu.first_date, adoption_rate_pct DESC
```

### T2.3 Monetization Readiness Metrics

```sql
-- Per-cohort monetization signals on first day
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
monetization_events AS (
  SELECT 
    f.first_date,
    e."#distinct_id" as user_id,
    MAX(CASE WHEN e."#event_name" IN ('paywall_view', 'shop_open', 'premium_view', 'upgrade_view') THEN 1 ELSE 0 END) as saw_paywall,
    MAX(CASE WHEN e."#event_name" IN ('add_cart', 'checkout_start', 'trial_start', 'purchase_intent') THEN 1 ELSE 0 END) as purchase_intent,
    MAX(CASE WHEN e."#event_name" IN ('purchase', 'payment_complete', 'order_success', 'subscription_start') THEN 1 ELSE 0 END) as purchased,
    SUM(CASE WHEN e."#event_name" IN ('purchase', 'payment_complete', 'order_success') THEN e.revenue ELSE 0 END) as revenue
  FROM hive.ta.v_event_{project_id} e
  JOIN first_day_users f ON e."#distinct_id" = f.user_id AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY f.first_date, e."#distinct_id"
)
SELECT 
  first_date,
  COUNT(*) as cohort_size,
  SUM(saw_paywall) as paywall_viewers,
  SUM(purchase_intent) as intent_users,
  SUM(purchased) as purchasers,
  SUM(saw_paywall) * 100.0 / COUNT(*) as paywall_rate_pct,
  SUM(purchase_intent) * 100.0 / COUNT(*) as intent_rate_pct,
  SUM(purchased) * 100.0 / COUNT(*) as purchase_rate_pct,
  SUM(revenue) as total_revenue,
  SUM(revenue) / COUNT(*) as arpu
FROM monetization_events
GROUP BY first_date
ORDER BY first_date
```

### T2.4 Retention Signal Metrics

```sql
-- Per-cohort retention signals
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
d1_retention AS (
  SELECT 
    f.first_date,
    COUNT(DISTINCT f.user_id) as cohort_size,
    COUNT(DISTINCT e."#distinct_id") as retained_users
  FROM first_day_users f
  LEFT JOIN v_event_{project_id} e 
    ON f.user_id = e."#distinct_id" 
    AND e."$part_date" = DATE_ADD('day', 1, f.first_date)
  GROUP BY f.first_date
),
retention_markers AS (
  SELECT 
    f.first_date,
    COUNT(DISTINCT CASE WHEN e."#event_name" IN ('push_allow', 'notification_enable', 'permission_grant') THEN e."#distinct_id" END) as push_optin,
    COUNT(DISTINCT CASE WHEN e."#event_name" IN ('account_bind', 'email_verify', 'phone_bind') THEN e."#distinct_id" END) as account_bind,
    COUNT(DISTINCT CASE WHEN e."#event_name" IN ('widget_add', 'shortcut_create', 'home_screen_add') THEN e."#distinct_id" END) as widget_add
  FROM first_day_users f
  LEFT JOIN v_event_{project_id} e 
    ON f.user_id = e."#distinct_id" 
    AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY f.first_date
)
SELECT 
  r.first_date,
  r.cohort_size,
  r.retained_users,
  r.retained_users * 100.0 / r.cohort_size as d1_retention_pct,
  m.push_optin,
  m.account_bind,
  m.widget_add,
  m.push_optin * 100.0 / r.cohort_size as push_optin_pct,
  m.account_bind * 100.0 / r.cohort_size as account_bind_pct
FROM d1_retention r
JOIN retention_markers m ON r.first_date = m.first_date
ORDER BY r.first_date
```

---

## Phase 3 — Behavior Sequence Analysis

### T3.0 Event Auto-Discovery (First-Day High-Frequency Events)

```sql
-- Discover top first-day events by user coverage
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
event_coverage AS (
  SELECT 
    e."#event_name",
    COUNT(DISTINCT e."#distinct_id") as user_count,
    COUNT(*) as total_events,
    COUNT(DISTINCT e."#distinct_id") * 100.0 / (SELECT COUNT(*) FROM first_day_users) as coverage_pct
  FROM hive.ta.v_event_{project_id} e
  JOIN first_day_users f ON e."#distinct_id" = f.user_id AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY e."#event_name"
)
SELECT 
  "#event_name",
  user_count,
  total_events,
  coverage_pct,
  total_events * 1.0 / user_count as avg_events_per_user
FROM event_coverage
ORDER BY user_count DESC
LIMIT 20
```

**Usage**: Present Top 15 to user for confirmation. User selects 5-8 events for path analysis.

### T3.1 Per-User First-Day Path Extraction

```sql
-- Extract first-day action sequence per user (confirmed event set only)
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
path_events AS (
  SELECT 
    e."#distinct_id" as user_id,
    f.first_date,
    e."#event_name",
    e."#event_time",
    ROW_NUMBER() OVER (PARTITION BY e."#distinct_id" ORDER BY e."#event_time") as step_num
  FROM hive.ta.v_event_{project_id} e
  JOIN first_day_users f ON e."#distinct_id" = f.user_id AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND e."#event_name" IN ({confirmed_event_list})
    -- User-confirmed 5-8 events, e.g., ('launch', 'tutorial_complete', 'level_1', 'purchase')
)
SELECT 
  user_id,
  first_date,
  LISTAGG("#event_name", '→') WITHIN GROUP (ORDER BY step_num) as path,
  COUNT(*) as path_length,
  MAX(step_num) as max_step
FROM path_events
GROUP BY user_id, first_date
```

### T3.2 Path Distribution (Top N Paths)

```sql
-- Aggregate paths and rank by frequency
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
path_events AS (
  SELECT 
    e."#distinct_id" as user_id,
    f.first_date,
    e."#event_name",
    e."#event_time",
    ROW_NUMBER() OVER (PARTITION BY e."#distinct_id" ORDER BY e."#event_time") as step_num
  FROM hive.ta.v_event_{project_id} e
  JOIN first_day_users f ON e."#distinct_id" = f.user_id AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND e."#event_name" IN ({confirmed_event_list})
),
user_paths AS (
  SELECT 
    user_id,
    first_date,
    LISTAGG("#event_name", '→') WITHIN GROUP (ORDER BY step_num) as path,
    COUNT(*) as path_length
  FROM path_events
  GROUP BY user_id, first_date
)
SELECT 
  first_date,
  path,
  COUNT(*) as user_count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY first_date) as pct_of_cohort,
  AVG(path_length) as avg_path_length
FROM user_paths
GROUP BY first_date, path
ORDER BY first_date, user_count DESC
LIMIT {top_n}  -- e.g., 10
```

### T3.3 Funnel Drop-Off Analysis

```sql
-- Sequential funnel: Step1→Step2→...→StepN conversion
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
funnel_steps AS (
  SELECT 
    f.first_date,
    e."#distinct_id" as user_id,
    MAX(CASE WHEN e."#event_name" = '{step1_event}' THEN 1 ELSE 0 END) as step1,
    MAX(CASE WHEN e."#event_name" = '{step2_event}' THEN 1 ELSE 0 END) as step2,
    MAX(CASE WHEN e."#event_name" = '{step3_event}' THEN 1 ELSE 0 END) as step3,
    MAX(CASE WHEN e."#event_name" = '{step4_event}' THEN 1 ELSE 0 END) as step4,
    MAX(CASE WHEN e."#event_name" = '{step5_event}' THEN 1 ELSE 0 END) as step5,
    MAX(CASE WHEN e."#event_name" = '{step6_event}' THEN 1 ELSE 0 END) as step6,
    MAX(CASE WHEN e."#event_name" = '{step7_event}' THEN 1 ELSE 0 END) as step7,
    MAX(CASE WHEN e."#event_name" = '{step8_event}' THEN 1 ELSE 0 END) as step8
  FROM first_day_users f
  LEFT JOIN v_event_{project_id} e 
    ON f.user_id = e."#distinct_id" AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY f.first_date, e."#distinct_id"
)
SELECT 
  first_date,
  COUNT(*) as cohort_size,
  SUM(step1) as step1_users,
  SUM(step2) as step2_users,
  SUM(step3) as step3_users,
  SUM(step4) as step4_users,
  SUM(step5) as step5_users,
  SUM(step6) as step6_users,
  SUM(step7) as step7_users,
  SUM(step8) as step8_users,
  SUM(step1) * 100.0 / COUNT(*) as step1_rate,
  SUM(step2) * 100.0 / SUM(step1) as step1_to_2_rate,
  SUM(step3) * 100.0 / SUM(step2) as step2_to_3_rate,
  SUM(step4) * 100.0 / SUM(step3) as step3_to_4_rate,
  SUM(step5) * 100.0 / SUM(step4) as step4_to_5_rate,
  SUM(step6) * 100.0 / SUM(step5) as step5_to_6_rate,
  SUM(step7) * 100.0 / SUM(step6) as step6_to_7_rate,
  SUM(step8) * 100.0 / SUM(step7) as step7_to_8_rate
FROM funnel_steps
GROUP BY first_date
ORDER BY first_date
```

**Notes**:
- This is a **sequential funnel** — user must complete step N to be counted in step N+1.
- For non-sequential (any-order) funnel, remove `SUM(stepN) * 100.0 / SUM(stepN-1)` and use `SUM(stepN) * 100.0 / COUNT(*)` instead.
- Drop-off >40% at any step = red flag.

### T3.4 Action Entropy Computation

```sql
-- Compute Shannon entropy of first-day action distribution
-- Note: This is a simplified version. Full entropy requires per-user action frequency, then aggregated.
WITH first_day_users AS (
  SELECT DISTINCT "#distinct_id" as user_id, MIN("$part_date") as first_date
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND "#event_name" = '{caliber_event}'
  GROUP BY "#distinct_id"
),
action_counts AS (
  SELECT 
    f.first_date,
    e."#event_name",
    COUNT(*) as action_count
  FROM hive.ta.v_event_{project_id} e
  JOIN first_day_users f ON e."#distinct_id" = f.user_id AND e."$part_date" = f.first_date
  WHERE e."$part_date" BETWEEN '{start_date}' AND '{end_date}'
    AND e."#event_name" IN ({confirmed_event_list})
  GROUP BY f.first_date, e."#event_name"
),
total_actions AS (
  SELECT first_date, SUM(action_count) as total
  FROM action_counts
  GROUP BY first_date
),
probabilities AS (
  SELECT 
    a.first_date,
    a."#event_name",
    a.action_count * 1.0 / t.total as p
  FROM action_counts a
  JOIN total_actions t ON a.first_date = t.first_date
)
SELECT 
  first_date,
  -SUM(p * LOG2(p)) as shannon_entropy,
  COUNT(DISTINCT "#event_name") as unique_actions,
  -- Normalized entropy (0-1 scale): entropy / log2(unique_actions)
  -SUM(p * LOG2(p)) / LOG2(COUNT(DISTINCT "#event_name")) as normalized_entropy
FROM probabilities
GROUP BY first_date
ORDER BY first_date
```

**Notes**:
- `normalized_entropy` scales entropy to 0-1 range. 0 = all users do the same single action; 1 = uniform distribution across all actions.
- Interpretation: 0.0-0.3 robotic, 0.3-0.6 focused, 0.6-0.9 exploratory, >0.9 chaotic.

---

## Phase 5 — Structural Mutation Diagnosis

### T4.1 Channel Mix Shift (Chi-Square Test)

```sql
-- Compare channel distribution between baseline and comparison periods
WITH baseline_channels AS (
  SELECT 
    COALESCE(channel, 'unknown') as channel,
    COUNT(DISTINCT "#distinct_id") as user_count
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{baseline_start}' AND '{baseline_end}'
    AND "#event_name" IN ({active_event_list})
  GROUP BY channel
),
comparison_channels AS (
  SELECT 
    COALESCE(channel, 'unknown') as channel,
    COUNT(DISTINCT "#distinct_id") as user_count
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{comparison_start}' AND '{comparison_end}'
    AND "#event_name" IN ({active_event_list})
  GROUP BY channel
),
merged AS (
  SELECT 
    COALESCE(b.channel, c.channel) as channel,
    COALESCE(b.user_count, 0) as baseline_count,
    COALESCE(c.user_count, 0) as comparison_count
  FROM baseline_channels b
  FULL OUTER JOIN comparison_channels c ON b.channel = c.channel
)
SELECT 
  channel,
  baseline_count,
  comparison_count,
  baseline_count * 100.0 / SUM(baseline_count) OVER () as baseline_pct,
  comparison_count * 100.0 / SUM(comparison_count) OVER () as comparison_pct,
  (comparison_count * 100.0 / SUM(comparison_count) OVER ()) - 
    (baseline_count * 100.0 / SUM(baseline_count) OVER ()) as pct_point_change,
  -- Chi-square contribution: (observed - expected)^2 / expected
  POW(comparison_count - (SUM(comparison_count) OVER () * baseline_count / SUM(baseline_count) OVER ()), 2) / 
    (SUM(comparison_count) OVER () * baseline_count / SUM(baseline_count) OVER ()) as chi2_contribution
FROM merged
ORDER BY ABS(pct_point_change) DESC
```

**Notes**:
- Sum of `chi2_contribution` = chi-square statistic. Compare to critical value (df = n_channels - 1).
- `pct_point_change` > ±5% = notable shift; > ±10% = significant shift.

### T4.2 Device/Region Shift (KL Divergence)

```sql
-- Compute KL divergence for device or region distribution
-- Replace {dimension} with 'device_model' or 'region'
WITH baseline_dist AS (
  SELECT 
    COALESCE({dimension}, 'unknown') as segment,
    COUNT(DISTINCT "#distinct_id") * 1.0 / SUM(COUNT(DISTINCT "#distinct_id")) OVER () as p
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{baseline_start}' AND '{baseline_end}'
    AND "#event_name" IN ({active_event_list})
  GROUP BY {dimension}
),
comparison_dist AS (
  SELECT 
    COALESCE({dimension}, 'unknown') as segment,
    COUNT(DISTINCT "#distinct_id") * 1.0 / SUM(COUNT(DISTINCT "#distinct_id")) OVER () as q
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{comparison_start}' AND '{comparison_end}'
    AND "#event_name" IN ({active_event_list})
  GROUP BY {dimension}
),
kl_terms AS (
  SELECT 
    COALESCE(b.segment, c.segment) as segment,
    COALESCE(b.p, 0.0001) as p,  -- smoothing to avoid log(0)
    COALESCE(c.q, 0.0001) as q,
    COALESCE(b.p, 0.0001) * LOG2(COALESCE(b.p, 0.0001) / COALESCE(c.q, 0.0001)) as kl_term
  FROM baseline_dist b
  FULL OUTER JOIN comparison_dist c ON b.segment = c.segment
)
SELECT 
  segment,
  p as baseline_share,
  q as comparison_share,
  q - p as share_change,
  kl_term
FROM kl_terms
ORDER BY ABS(share_change) DESC
-- Total KL divergence = SUM(kl_term). >0.1 = notable shift, >0.25 = significant shift
```

### T4.3 Traffic Source Shift (Organic vs Paid)

```sql
-- Compare organic vs paid ratio between periods
WITH baseline_traffic AS (
  SELECT 
    CASE 
      WHEN traffic_source IN ('organic', 'natural', 'seo', 'direct', 'referral') THEN 'organic'
      WHEN traffic_source IN ('paid', 'ads', 'cpc', 'display', 'social_ads') THEN 'paid'
      ELSE 'other'
    END as traffic_type,
    COUNT(DISTINCT "#distinct_id") as user_count
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{baseline_start}' AND '{baseline_end}'
    AND "#event_name" IN ({active_event_list})
  GROUP BY 1
),
comparison_traffic AS (
  SELECT 
    CASE 
      WHEN traffic_source IN ('organic', 'natural', 'seo', 'direct', 'referral') THEN 'organic'
      WHEN traffic_source IN ('paid', 'ads', 'cpc', 'display', 'social_ads') THEN 'paid'
      ELSE 'other'
    END as traffic_type,
    COUNT(DISTINCT "#distinct_id") as user_count
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{comparison_start}' AND '{comparison_end}'
    AND "#event_name" IN ({active_event_list})
  GROUP BY 1
)
SELECT 
  COALESCE(b.traffic_type, c.traffic_type) as traffic_type,
  COALESCE(b.user_count, 0) as baseline_count,
  COALESCE(c.user_count, 0) as comparison_count,
  COALESCE(b.user_count, 0) * 100.0 / (SELECT SUM(user_count) FROM baseline_traffic) as baseline_pct,
  COALESCE(c.user_count, 0) * 100.0 / (SELECT SUM(user_count) FROM comparison_traffic) as comparison_pct
FROM baseline_traffic b
FULL OUTER JOIN comparison_traffic c ON b.traffic_type = c.traffic_type
```

### T4.4 Geo Concentration Shift

```sql
-- Compute top region concentration and shifts
WITH baseline_geo AS (
  SELECT 
    COALESCE(region, 'unknown') as region,
    COUNT(DISTINCT "#distinct_id") as user_count
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{baseline_start}' AND '{baseline_end}'
    AND "#event_name" IN ({active_event_list})
  GROUP BY region
),
comparison_geo AS (
  SELECT 
    COALESCE(region, 'unknown') as region,
    COUNT(DISTINCT "#distinct_id") as user_count
  FROM hive.ta.v_event_{project_id}
  WHERE "$part_date" BETWEEN '{comparison_start}' AND '{comparison_end}'
    AND "#event_name" IN ({active_event_list})
  GROUP BY region
),
ranked AS (
  SELECT 
    'baseline' as period,
    region,
    user_count,
    user_count * 100.0 / SUM(user_count) OVER () as share_pct,
    ROW_NUMBER() OVER (ORDER BY user_count DESC) as rank
  FROM baseline_geo
  UNION ALL
  SELECT 
    'comparison' as period,
    region,
    user_count,
    user_count * 100.0 / SUM(user_count) OVER () as share_pct,
    ROW_NUMBER() OVER (ORDER BY user_count DESC) as rank
  FROM comparison_geo
)
SELECT 
  period,
  region,
  user_count,
  share_pct,
  rank,
  -- Top 1 concentration
  SUM(CASE WHEN rank = 1 THEN share_pct ELSE 0 END) OVER (PARTITION BY period) as top1_concentration,
  -- Top 3 concentration
  SUM(CASE WHEN rank <= 3 THEN share_pct ELSE 0 END) OVER (PARTITION BY period) as top3_concentration,
  -- Top 5 concentration
  SUM(CASE WHEN rank <= 5 THEN share_pct ELSE 0 END) OVER (PARTITION BY period) as top5_concentration
FROM ranked
ORDER BY period, rank
```

---

## Utility Queries

### T5.1 Low-Sample Check

```sql
-- Check daily new user counts for sample size validation
SELECT 
  "$part_date" as date,
  COUNT(DISTINCT "#distinct_id") as new_users
FROM hive.ta.v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
  AND "#event_name" IN ({active_event_list})
GROUP BY "$part_date"
ORDER BY "$part_date"
```

**Interpretation**:
- <50/day: aggregate to monthly, suppress daily scores
- 50-200/day: daily with "low sample" warning
- >200/day: normal analysis

### T5.2 Synthetic Data Sanity Check

```sql
-- Detect synthetic/test data patterns
SELECT 
  'all_same_device' as check_name,
  COUNT(DISTINCT device_model) as unique_values,
  CASE WHEN COUNT(DISTINCT device_model) = 1 THEN 'FAIL' ELSE 'PASS' END as result
FROM hive.ta.v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
UNION ALL
SELECT 
  'all_same_region' as check_name,
  COUNT(DISTINCT region) as unique_values,
  CASE WHEN COUNT(DISTINCT region) = 1 THEN 'FAIL' ELSE 'PASS' END as result
FROM hive.ta.v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
UNION ALL
SELECT 
  'all_same_channel' as check_name,
  COUNT(DISTINCT channel) as unique_values,
  CASE WHEN COUNT(DISTINCT channel) = 1 THEN 'FAIL' ELSE 'PASS' END as result
FROM hive.ta.v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
UNION ALL
SELECT 
  'round_numbers' as check_name,
  CASE WHEN COUNT(DISTINCT "#distinct_id") % 1000 = 0 THEN 'WARN' ELSE 'PASS' END as result,
  COUNT(DISTINCT "#distinct_id") as user_count
FROM hive.ta.v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
```

---

*File version: 1.1.0 | Last updated: 2026-09-17 | SQL model verified; table/column naming corrected to hive.ta.v_event_N + "#event_name"*
