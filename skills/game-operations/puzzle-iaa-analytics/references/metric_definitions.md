# Analysis Metric Definitions

> This document is the core of puzzle-iaa-analytics — **all analysis units use a six-element template, metrics as mathematical formulas, bound to no specific tool.**
> For specific tool invocation patterns, see `adapters/ae-cli.md` (only when ae-cli is present).

---

## Table of Contents

1. [Retention Decay](#1-retention-decay)
2. [Play Duration](#2-play-duration)
3. [Levels Completed per User](#3-levels-completed-per-user)
4. [Ad Placement Breakdown](#4-ad-placement-breakdown)
5. [First Level Pass Rate](#5-first-level-pass-rate)
6. [IPU per 10-Level Stage](#6-ipu-per-10-level-stage)
7. [Per-Level Ad Trigger Cause](#7-per-level-ad-trigger-cause)
8. [Level Retention Curve](#8-level-retention-curve)
9. [Level Pass Rate Curve](#9-level-pass-rate-curve)
10. [Register → First 10 Levels Funnel](#10-register--first-10-levels-event-funnel)
11. [Churned User Last-Session Trace](#11-churned-user-last-session-behavior-trace)
12. [Ad Niche Segmentation](#12-ad-niche-segmentation-comparison)
13. [Content Consumption Segmentation](#13-content-consumption-segmentation-comparison)
14. [Ad Frequency-Retention Curve](#14-ad-frequency-retention-curve)
15. [Levels-Retention Curve](#15-levels-completed-retention-curve)
16. [Stabilized Baseline](#16-stabilized-user-behavior-baseline)
17. [Core User Identification](#17-core-user-identification)

---

### 1. Retention Decay

- **Intent**: Determine if retention is healthy; detect post-newbie churn acceleration
- **Semantics**: D2/D3/D7 = unique users triggering `{{event.daily_login}}` on Day N / registered users. Decay 1 = (D2-D3)/D2; Decay 2 = (D3-D7)/D3
- **Input**: Initial: `{{event.daily_login}}`, Return: `{{event.daily_login}}`, Window: `{{window.start}}`–`{{window.end}}`
- **Dimension**: By registration date
- **Judgment**: Decay 2 > Decay 1 × `{{threshold.retention_fracture_ratio}}` → mid-term fracture. D2<35%: attention; D2<25%: severe. D7<12%: attention; D7<8%: severe
- **Output**: Daily retention table + averages + decay ratios + judgment

### 2. Play Duration

- **Intent**: Detect D1 overdose / D2 cliff
- **Semantics**: Avg duration = sum(`{{prop.session_duration}}`) / unique users of `{{event.session_end}}`
- **Input**: `{{event.session_end}}`, `{{prop.session_duration}}` (sec)
- **Dimension**: By day (D1, D2, D3-7 avg)
- **Judgment**: D1/D2 > `{{threshold.duration_overdraft_ratio}}` → overdraft. D1>90min & D2<20min → one-day player
- **Output**: Daily avg duration trend + D1/D2 ratio

### 3. Levels Completed per User

- **Intent**: Balance of content consumption vs goal traction
- **Semantics**: Levels/user = total `{{event.level_complete}}` / unique users
- **Input**: `{{event.level_complete}}`, window
- **Dimension**: By day
- **Judgment**: D1 > `{{threshold.overdraft_warning}}` → too fast. High D1 + low D2 → no appeal. Moderate D1 + stable → healthy
- **Output**: Daily avg levels trend

### 4. Ad Placement Breakdown

- **Intent**: Understand ad monetization structure; identify punitive ad share
- **Semantics**: Type share = type `{{event.ad_impression}}` / all impressions
- **Input**: `{{event.ad_impression}}`, `{{prop.ad_type}}`, `{{prop.ad_scene}}`
- **Dimension**: By type + by scene (two analyses)
- **Judgment**: Punitive (revive/fail-forced) high share → churn risk. Reward-type higher → healthier
- **Output**: Type table + scene table

### 5. First Level Pass Rate

- **Intent**: Detect tutorial breakage
- **Semantics**: Users completing level_id=1 / users starting level_id=1
- **Input**: `{{event.level_start}}`(id=1), `{{event.level_complete}}`(id=1)
- **Judgment**: < `{{threshold.first_level_pass_rate}}` → investigate. <85% → severe
- **Output**: Single value + status

### 6. IPU per 10-Level Stage

- **Intent**: Find difficulty turning points
- **Semantics**: Stage IPU = ad impressions in 10-level bucket / unique users
- **Input**: `{{event.ad_impression}}`, group by `{{prop.level_id}}`, bucket 1-10/11-20/...
- **Judgment**: Stage jump >50% → difficulty spike
- **Output**: Stage × IPU table

### 7. Per-Level Ad Trigger Cause

- **Intent**: Why each level triggers ads (forced vs voluntary)
- **Semantics**: Count by level_id × ad_scene cross-group
- **Input**: `{{event.ad_impression}}`, `{{prop.level_id}}` × `{{prop.ad_scene}}`
- **Judgment**: Revive-type >60% → difficulty signal
- **Output**: Level × scene heatmap

### 8. Level Retention Curve

- **Intent**: Find critical levels where retention drops sharply
- **Semantics**: Day-after retention for users who passed level N
- **Input**: Initial: `{{event.level_complete}}`(id=N), Return: `{{event.daily_login}}`, N=10,20,...,60
- **Judgment**: Adjacent drop >30% → severe
- **Output**: Stage × D2 retention table

### 9. Level Pass Rate Curve

- **Intent**: Find difficulty jump points
- **Semantics**: Pass rate = complete(id=N) / start(id=N)
- **Input**: `{{event.level_start}}`, `{{event.level_complete}}`, grouped by `{{prop.level_id}}`
- **Judgment**: Record first <80%, first <50%, max adjacent drop
- **Output**: Full curve data + 3 key annotations

### 10. Register → First 10 Levels Funnel

- **Intent**: Locate churn bottlenecks
- **Semantics**: 6-step sequential funnel: register → start L1 → complete L1 → first ad → complete L5 → complete L10
- **Input**: Window=7d
- **Judgment**: 1→2 churn = tech; 3→4 = ad deterrence; 4→5 = weak content
- **Output**: 6-step table (users + relative + absolute conversion)

### 11. Churned User Last-Session Trace

- **Intent**: What happened in the last session before churn
- **Semantics**: Frustration exit = (watched ad + still failed + no return) / total churned. No-ad exit = (no ads + churned) / total
- **Input**: Retention (lost side, `unit_num={{threshold.churn_definition_days}}`), context-driven drilldown, sample 30-50 users
- **Judgment**: Frustration>30% → punitive ads primary cause. No-ad>40% → content issue
- **Output**: Pattern distribution + top-5 stuck levels + rates

### 12. Ad Niche Segmentation

- **Intent**: Retention differences by ad frequency
- **Semantics**: D1 ad count per user → segment (zero/light/medium/heavy, data-driven)
- **Input**: `{{event.ad_impression}}`(D1), compare D2/D3/login count
- **Output**: Segment × retention + activity tables

### 13. Content Consumption Segmentation

- **Intent**: One-day player consumption boundary
- **Semantics**: D1 levels per user → segment (light≤5/medium≤20/heavy≤40/overdraft>40)
- **Input**: `{{event.level_complete}}`(D1), compare D2/D3/activity
- **Output**: Segment × retention table

### 14. Ad Frequency-Retention Curve

- **Intent**: Precise knee point detection
- **Semantics**: Fine-grained ad count buckets (0,1,2,3,4-5,6-8,9-12,13-20,>20) × D2/D7
- **Input**: Per-user D1 ad count, bucket, retention per bucket
- **Judgment**: Knee = elbow detection. Overlay contribution share
- **Output**: Curve data + knee coordinates

### 15. Levels-Retention Curve

- **Intent**: Optimal daily level volume; overdraft boundary
- **Semantics**: Fine-grained level buckets (≤3,4-5,6-10,11-15,16-20,21-30,31-40,>40) × D2/D7
- **Output**: Curve data + optimal interval + cliff point

### 16. Stabilized Baseline

- **Intent**: Natural rhythm from post-newbie users
- **Semantics**: D3-7 active users' daily level distribution (P25/P50/P75)
- **Output**: Histogram + percentiles

### 17. Core User Identification

- **Intent**: Who contributes healthy long-term value
- **Semantics**: Cross-ref §14 knee + §15 optimal → 4 types. IPU contribution per type
- **Judgment**: Core IPU>50% → healthy. Squeeze IPU>40% → unsustainable. Pure content>50% → under-penetration
- **Output**: 4-type table + IPU structure

---

> **How to use**: Step files reference metric IDs (e.g., "Execute §1"). Agent chooses the tool.
