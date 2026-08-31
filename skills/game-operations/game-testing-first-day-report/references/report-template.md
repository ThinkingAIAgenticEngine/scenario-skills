# Game Testing First-Day Data Report Template

> This template is Section 6 — Report Output Template — of the `game-testing-first-day-report` skill.
> Read this template first during execution, then populate placeholders with query results.

````markdown
# 📊 {{Project Name}} Testing First-Day Data Report

**Test Date**: {{YYYY-MM-DD}} (UTC+{{offset}})
**Report Generated**: {{current time}}
**Project**: {{Project Name}} (projectId={{pid}})

---

# ⚠️ Anomaly Findings & Improvement Suggestions (Priority Focus)

> Only list **business anomalies** (based on real data inflection points/cliffs). Infra issues are in the end-of-report 📝 Data Quality table.

## 🔴 High Priority — Impacting Core Experience / Revenue

| # | Issue | Data Evidence (must be specific values) | Impact Scope | Suggested Action |
|----|------|-------------------------|---------|---------|
| 1 | {{Issue description}} | {{Data evidence}} | {{Impact scope}} | {{Suggestion}} |
| 2 | {{Issue description}} | {{Data evidence}} | {{Impact scope}} | {{Suggestion}} |
| 3 | {{Issue description}} | {{Data evidence}} | {{Impact scope}} | {{Suggestion}} |

## 🟡 Medium Priority — Requires Ongoing Attention

| # | Issue | Data Evidence (must be specific values) | Impact Scope | Suggested Action |
|----|------|-------------------------|---------|---------|
| 1 | {{Issue description}} | {{Data evidence}} | {{Impact scope}} | {{Suggestion}} |
| 2 | {{Issue description}} | {{Data evidence}} | {{Impact scope}} | {{Suggestion}} |
| 3 | {{Issue description}} | {{Data evidence}} | {{Impact scope}} | {{Suggestion}} |

---

# 1. Basic Data Overview

| Metric | Value | Assessment |
|------|------|------|
| New Registrations | {{X}} | — |
| DAU | {{X}} | — |
| Avg Online Time (median) | {{X}} min | ✅/⚠️/🔴 |
| Payment Rate PUR | {{X}}% | ✅/⚠️/🔴 |
| First-Day Revenue | ¥{{X}} | — |
| ARPU | ¥{{X}} | — |
| ARPPU | ¥{{X}} | — |
| Core Gameplay Reach Rate | {{X}}% | — |
| Crash Rate | {{X}}% or Not Reported | ✅/⚠️ |

> **Module Summary**: {{Overall assessment with specific values}}.

---

# 2. User Acquisition

## 2.1 New User Hourly Distribution

```chart
{
  "type": "line",
  "title": "New Registered User Hourly Distribution",
  "xLabel": "Hour",
  "yLabel": "New Users",
  "data": [{{24-hour data in { "label": "HH:00", "value": N } format}}]
}
```

- Peak new-user hour: {{XX:00}}, {{X}} users
- Trough new-user hour: {{XX:00}}, {{X}} users
- Note any cliff anomalies here (if any)

## 2.2 Channel Distribution

```chart
{ "type": "pie", "title": "Channel Distribution", "data": [{{channel data}}] }
```

| Channel | New Users | Share |
|------|------|------|
| ... | ... | ... |

> **Module Summary**: {{XX:00}} is the new-user peak, {{channel}} is the best acquisition channel.

---

# 3. User Quality & Online Time

## 3.1 Online Time Distribution (based on {{logout.online_time / ta_app_end.#duration / #vp@online_time_1d}}, per-user sum)

```chart
{ "type": "bar", "title": "Online Time Distribution (per-user sum)", "xLabel": "Time Range", "yLabel": "Users", "data": [{{time-range data}}] }
```

| Time Range | Users | Share |
|--------|-------|------|
| 0-5 min | {{X}} | {{X}}% |
| 5-15 min | {{X}} | {{X}}% |
| 15-30 min | {{X}} | {{X}}% |
| 30-60 min | {{X}} | {{X}}% |
| 60-90 min | {{X}} | {{X}}% |
| 90-120 min | {{X}} | {{X}}% |
| 120-180 min | {{X}} | {{X}}% |
| 180 min+ | {{X}} | {{X}}% |

- Median: {{X}} min
- Data source: {{logout.online_time / ta_app_end.#duration / interval approximation}}

> If all online-time sources are empty, fall back to the interval model and note in this module: "⚠️ Online-time property not effective; using interval approximation."

> **Module Summary**: {{X}}% of users stay under 5 minutes; {{time range}} has the highest payment conversion.

---

# 4. Core Behavior Funnel

| Step | Reach | Step Conv. Rate | Cumulative Conv. Rate | Churn Rate |
|------|---------|-----------|-----------|--------|
| Register | {{X}} | — | 100% | — |
| Login | {{X}} | {{X}}% | {{X}}% | {{X}}% |
| Complete Tutorial | {{X}} | {{X}}% | {{X}}% | {{X}}% |
| Start Battle | {{X}} | {{X}}% | {{X}}% | {{X}}% |

> Data source: SQL per-event COUNT(DISTINCT #user_id) approximation (AI-facing funnel.window field not supported).

> **Module Summary**: Cumulative conversion rate {{X}}%, bottleneck at {{node}}, loss accounts for {{X}}% of total loss.

---

# 5. Payment

## 5.1 Payment Overview

| Metric | Value |
|------|------|
| First-Day Revenue | ¥{{X}} |
| Paying Users | {{X}} |
| Payment Rate PUR | {{X}}% |
| ARPU | ¥{{X}} |
| ARPPU | ¥{{X}} |

## 5.2 Payment Tier Distribution

```chart
{ "type": "bar", "title": "Payment Tier Distribution", "xLabel": "Tier", "yLabel": "Users", "data": [{{tier data}}] }
```

## 5.3 Payment Item Amount TOP

```chart
{ "type": "bar", "title": "Payment Item Revenue Contribution TOP", "xLabel": "Item", "yLabel": "Amount (¥)", "data": [{{item data}}] }
```

## 5.4 Top Spenders Top 20

| Rank | User ID (masked) | Amount | Count | Main Item |
|------|------------|---------|------|---------|
| 1 | xxx***xxx | ¥{{X}} | {{X}} | ... |

> **Module Summary**: {{tier}} dominates ({{X}}%), top {{X}}% contribute {{X}}% of revenue, concentration is {{high/medium/low}}.

---

# 6. Game Progression

## 6.1 Level Distribution

```chart
{ "type": "bar", "title": "User Current Level Distribution", "xLabel": "Level", "yLabel": "Users", "data": [{{level data}}] }
```

> Data source: v_user_<pid>.role_level / level_up latest record (using user level fields such as `level`/`role_level`/`player_level`; **do not use `hero_level`**). If both are absent, mark "⚠️ Level property has no valid data reported" and write to the end-of-report 📝 Data Quality table.

## 6.2 Stage Pass Rate (Top 30)

```chart
{ "type": "line", "title": "Stage Pass/Fail Rate Top 30", "xLabel": "Stage ID", "yLabel": "Percentage", "data": [{{pass-rate list}}] }
```

| Stage | Started | Won | Lost | Pass Rate | Fail Rate |
|------|------|------|------|--------|--------|
| ... | ... | ... | ... | ... | ... |

## 6.3 Gameplay Mode Participation Rate

| Gameplay Mode | Participants | % of New Users |
|------|---------|----------|
| Gacha | {{X}} | {{X}}% |
| Shop | {{X}} | {{X}}% |
| Tower | {{X}} | {{X}}% |
| Arena | {{X}} | {{X}}% |
| Guild | {{X}} | {{X}}% |
| Add Friend | {{X}} | {{X}}% |

> **Module Summary**: Average progress to {{stage X}}, stage {{X}} has the highest fail rate ({{X}}%), gameplay coverage is {{good}}.

---

# 7. Game Bottlenecks

## 7.1 Stage Bottlenecks Top 10 (by fail rate descending)

| Rank | Stage | Started | Pass Rate | Fail Rate |
|------|------|---------|--------|--------|
| 1 | {{X}} | {{X}} | {{X}}% | {{X}}% |
| ... | ... | ... | ... | ... |

## 7.2 Level Staying

> Data source: {{v_user_<pid>.role_level / level_up latest level}}. If not reported, mark "⚠️ Not Reported" and write to the end-of-report 📝 Data Quality table.

> **Module Summary**: Top 1 bottleneck is stage {{X}} (fail rate {{X}}%), recommend {{action}}.

---

# 8. Economy System

> Focus on paid currency (diamond) spend destinations — this is the core lever for monetization tuning.

## 8.1 Currency Overview

| Currency | Gain Users | Spend Users | Total Output | Total Spend | Avg Output/User | Avg Spend/User |
|------|-----------|-----------|---------|---------|---------|---------|
| Diamond | {{X}} | {{X}} | {{X}} | {{X}} | {{X}} | {{X}} |
| Gold | {{X}} | {{X}} | {{X}} | {{X}} | {{X}} | {{X}} |

## 8.2 Diamond Spend Destination TOP (change_reason)

```chart
{ "type": "bar", "title": "Diamond Spend Destination TOP", "xLabel": "Spend Reason", "yLabel": "Spend Amount", "data": [{{reason data}}] }
```

| Spend Reason | Spend Users | Total Spend | Share | Avg Spend/User |
|---------|-----------|---------|------|---------|
| {{Gacha}} | {{X}} | {{X}} | {{X}}% | {{X}} |
| {{Shop}} | {{X}} | {{X}} | {{X}}% | {{X}} |
| ... | ... | ... | ... | ... |

## 8.3 Gold Spend Destination TOP (change_reason)

```chart
{ "type": "bar", "title": "Gold Spend Destination TOP", "xLabel": "Spend Reason", "yLabel": "Spend Amount", "data": [{{reason data}}] }
```

| Spend Reason | Spend Users | Total Spend | Share | Avg Spend/User |
|---------|-----------|---------|------|---------|
| ... | ... | ... | ... | ... |

## 8.4 Diamond Gain Source TOP (change_reason)

| Gain Reason | Gain Users | Total Gain | Share |
|---------|-----------|---------|------|
| {{Top-up}} | {{X}} | {{X}} | {{X}}% |
| {{Quests}} | {{X}} | {{X}} | {{X}}% |
| {{Events}} | {{X}} | {{X}} | {{X}}% |
| ... | ... | ... | ... |

> If the economy event has no change_amount property, approximate with user_count and note: "⚠️ No change-amount property; user count only."

> **Module Summary**: Top 1 diamond spend destination is {{reason}} ({{X}}% share), {{whether excessive reliance on a single spend sink}}; main output source is {{reason}} ({{X}}% share).

---

# 9. Social

> Social is an optional module. If add_guild / add_friend and similar events are all not reported, this section is directly marked "⚠️ Social events not reported."

| Metric | Value | % of New Users |
|------|------|----------|
| Joined Guild | {{X}} | {{X}}% |
| Guild Activity | {{X}} | {{X}}% |
| Added Friend | {{X}} | {{X}}% |
| Friend Requests Sent | {{X}} | — |
| Friend Requests Accepted | {{X}} | — |
| Friend Accept Rate | {{X}}% | — |

> **Module Summary**: Guild penetration gap {{X}}pp, friend accept rate {{X}}%, {{whether anomalous}}.

---

# 10. Tech Quality

| Metric | Value | Assessment |
|------|------|------|
| Crash Rate | {{X}}% or Not Reported | ✅/⚠️ |
| ANR Rate | {{X}}% or Not Reported | ✅/⚠️ |
| Login Success Rate | {{X}}% or Cannot Compute | ✅/⚠️ |

> **Module Summary**: Stability data is {{complete/missing}}; need to integrate {{crash SDK}}.

---

# 11. User Profile

```chart
{ "type": "pie", "title": "Device OS Distribution", "data": [{{iOS/Android}}] }
```

| Dimension | Distribution |
|------|------|
| Device OS | iOS {{X}}% / Android {{X}}% |
| Channel Top 3 | {{...}} |
| Network/Region | Not Reported or {{...}} |

> **Module Summary**: Users are predominantly {{iOS/Android}}; {{channel}} leads.

---

# 12. Anomaly Monitoring

| Check Item | Result |
|--------|------|
| Same IP ≥5 Registrations | {{X}} IPs or Cannot Identify |
| Same Device Model Batch | {{X}} or Not Analyzed |
| Payment Bad Debt | {{X}} transactions or Not Reported |

> **Module Summary**: {{Presence/absence}} of anomalous behavior.

---

# 📋 Report Summary

## Core Assessment
First-day overall {{exceeds/meets/falls below}} expectations: new users {{X}}, payment rate {{X}}%, tutorial completion rate {{X}}%, crash rate {{X}}%.

## Top 3 Improvements
1. {{Most important improvement point}}
2. {{Second}}
3. {{Third}}

## Urgent Action Items
- {{e.g. Crash exceeds threshold, payment anomaly, etc.}}

## 📝 Data Quality & Tracking Supplement Suggestions

> The following are **data infra issues** (not business anomalies) discovered during the query process. Fix in subsequent releases.

| # | Issue | Affected Module | Suggestion |
|----|------|---------|------|
| 1 | {{Issue}} | {{Module}} | {{Suggestion}} |
| 2 | {{Issue}} | {{Module}} | {{Suggestion}} |
| 3 | {{Issue}} | {{Module}} | {{Suggestion}} |

---

*Report generated: {{current time}} | Data source: TE Analysis System | Project: {{Project Name}}*
````
