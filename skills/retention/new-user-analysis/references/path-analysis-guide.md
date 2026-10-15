# Path Analysis Guide

> **Purpose**: Methodology for first-day behavior sequence analysis — path extraction, aggregation, entropy computation, and funnel definition.
> **Usage**: Load during Phase 3 execution. Reference for path interpretation and anomaly detection.
> **Single source of truth**: This file is the **authoritative** home for the entropy interpretation table (§2.3) and funnel-definition rules (§3). `SKILL.md` only links here — it does not restate these tables.

---

## 1. Path Extraction Methodology

### 1.1 What is a "Path"?

A path is an ordered sequence of events a user triggers on their first day:

```
User A: launch → tutorial_start → tutorial_complete → level_1 → level_1_complete → purchase
User B: launch → tutorial_start → tutorial_complete → level_1 → level_1_complete
User C: launch → browse → product_view → add_cart → purchase
```

**Key properties**:
- **Ordered**: Sequence matters. `A→B` ≠ `B→A`.
- **First-day only**: Events after day 1 are excluded (they belong to retention analysis).
- **Filtered**: Only user-confirmed events are included (not every raw event).

### 1.2 Path Length Rules

| Length | Interpretation | Action |
|--------|---------------|--------|
| **1** | Bounce — opened app, did nothing meaningful | Investigate activation friction |
| **2-3** | Shallow engagement — completed tutorial or first action only | Normal for utility apps |
| **4-6** | Moderate engagement — core loop + some exploration | Healthy for most products |
| **7-8** | Deep engagement — multiple features, possibly monetization | Power user or whale |
| **>8** | Extreme — likely bot, developer testing, or tracking error | Flag for manual review |

**Cap at 10 steps**: Longer paths are noise. Truncate or group as "8+".

### 1.3 Path Aggregation

**Group identical paths**:

```
Raw paths (per user):
  User A: launch→tutorial→level_1→purchase
  User B: launch→tutorial→level_1→purchase
  User C: launch→tutorial→level_1
  User D: launch→browse→purchase

Aggregated:
  launch→tutorial→level_1→purchase: 2 users (50%)
  launch→tutorial→level_1: 1 user (25%)
  launch→browse→purchase: 1 user (25%)
```

**Path normalization** (optional):
- Remove consecutive duplicates: `A→A→B` → `A→B`
- Group similar events: `level_1`, `level_2`, `level_3` → `level_N`
- Merge synonymous events: `like`, `heart`, `upvote` → `engage`

---

## 2. Entropy Computation

### 2.1 Shannon Entropy

Measures the "randomness" or "diversity" of behavior in a cohort:

```
H = -Σ(p_i × log2(p_i))
```

Where `p_i` = proportion of users who triggered action `i`.

**Example**:

```
Cohort of 100 users:
  - 60 did "launch→tutorial→level_1"
  - 25 did "launch→browse→purchase"
  - 10 did "launch→settings"
  - 5 did "launch→purchase"

p = [0.60, 0.25, 0.10, 0.05]
H = -(0.60×log2(0.60) + 0.25×log2(0.25) + 0.10×log2(0.10) + 0.05×log2(0.05))
H = -(0.60×(-0.737) + 0.25×(-2.000) + 0.10×(-3.322) + 0.05×(-4.322))
H = -(-0.442 - 0.500 - 0.332 - 0.216)
H = 1.490
```

### 2.2 Normalized Entropy

Raw entropy depends on the number of unique actions. Normalized entropy scales to 0-1:

```
H_norm = H / log2(N)
```

Where `N` = number of unique actions.

**Example** (from above):
```
N = 4 unique actions
H_norm = 1.490 / log2(4) = 1.490 / 2.000 = 0.745
```

### 2.3 Entropy Interpretation

| Normalized Entropy | Label | Meaning | Action |
|-------------------|-------|---------|--------|
| **0.0 - 0.3** | Robotic | All users follow identical paths | Investigate bot traffic or incentive abuse |
| **0.3 - 0.6** | Focused | Most users follow 1-2 dominant paths | Healthy for utility/task-oriented apps |
| **0.6 - 0.9** | Exploratory | Diverse paths, no single dominant flow | Healthy for content/social apps |
| **>0.9** | Chaotic | Nearly uniform distribution across many paths | Investigate tracking errors or UI confusion |

**Important**: Entropy is **relative to product type**:
- Utility app with H_norm = 0.4 → Healthy (users follow task completion path)
- Social app with H_norm = 0.4 → Concerning (users should explore more)
- Utility app with H_norm = 0.9 → Concerning (UI may be confusing)
- Social app with H_norm = 0.9 → Healthy (rich exploration)

### 2.4 Entropy Over Time

Track entropy trend to detect behavioral shifts:

| Trend | Interpretation |
|-------|---------------|
| **Entropy ↓ over time** | Users converging to dominant path (product maturity) or bot influx |
| **Entropy ↑ over time** | Users exploring more (feature discovery) or UI confusion |
| **Sudden entropy spike** | New feature launch, tracking change, or fraud attack |
| **Sudden entropy drop** | Onboarding simplification, or bot campaign started |

---

## 3. Funnel Definition Rules

### 3.1 Sequential vs Non-Sequential

| Type | Definition | Use Case | Conversion Formula |
|------|-----------|----------|-------------------|
| **Sequential** | User must complete step N before step N+1 | Onboarding flow, checkout process | `step_N+1_users / step_N_users` |
| **Non-Sequential** | User can trigger steps in any order | Feature adoption, engagement breadth | `step_N_users / total_cohort` |

**Sequential example** (e-commerce checkout):
```
Step 1: product_view (1000 users)
Step 2: add_cart (400 users, 40% conversion)
Step 3: checkout_start (200 users, 50% conversion)
Step 4: purchase (100 users, 50% conversion)
```

**Non-sequential example** (feature adoption):
```
Cohort: 1000 users
  - 600 used search (60% adoption)
  - 400 used filter (40% adoption)
  - 200 used wishlist (20% adoption)
  (No ordering implied)
```

### 3.2 Step Ordering Rules

For sequential funnels:

1. **Logical dependency**: Step N+1 must be impossible or meaningless without step N
   - ✅ Good: `tutorial_start → tutorial_complete → level_1`
   - ❌ Bad: `like → follow → share` (independent actions)

2. **Temporal constraint**: Step N+1 should typically happen after step N in time
   - But allow for edge cases (user might revisit earlier step)

3. **Business logic**: Steps should represent the intended user journey
   - Not just "most common" order, but "designed" order

### 3.3 Drop-Off Thresholds

| Drop-Off Rate | Severity | Action |
|-------------|----------|--------|
| **<20%** | Healthy | Monitor only |
| **20-40%** | Acceptable | Optimize if funnel is critical |
| **40-60%** | Concerning | A/B test improvements |
| **60-80%** | Critical | Emergency redesign |
| **>80%** | Broken | Verify tracking, then redesign |

### 3.4 Funnel Segmentation

Always segment funnel drop-off by:
- **Channel**: Do paid users drop more than organic?
- **Device**: Do older devices drop at specific steps?
- **Region**: Do certain regions have cultural/UX barriers?
- **Cohort date**: Is drop-off getting better or worse over time?

---

## 4. Path Visualization

### 4.1 Sankey Diagram

Best for showing path distribution and flow volume:

```
[launch] ──100%──→ [tutorial] ──80%──→ [level_1] ──60%──→ [purchase]
              └────20%──→ [browse] ──15%──→ [purchase]
```

**Chart.js implementation** (for HTML reports):
- Use `chartjs-chart-sankey` plugin
- Node width = % of cohort
- Link width = % flowing from source to target

### 4.2 Path Table

Best for precise numbers:

| Rank | Path | Users | % of Cohort | Avg Length | D1 Retention |
|------|------|-------|-------------|------------|--------------|
| 1 | launch→tutorial→level_1→purchase | 320 | 32% | 4.0 | 45% |
| 2 | launch→tutorial→level_1 | 280 | 28% | 3.0 | 38% |
| 3 | launch→browse→purchase | 150 | 15% | 3.0 | 52% |
| 4 | launch→tutorial | 100 | 10% | 2.0 | 25% |
| 5 | launch→settings | 80 | 8% | 2.0 | 15% |

**Key insight**: Path 3 (browse→purchase) has highest D1 retention (52%) despite being shorter. Suggests tutorial may not be necessary for high-intent users.

### 4.3 Funnel Chart

Best for sequential drop-off:

```
Step 1: launch        ████████████████████ 1000 (100%)
Step 2: tutorial      ████████████████      800 (80%)
Step 3: level_1       ██████████            500 (63% drop-off)
Step 4: level_3       ██████                300 (40% drop-off)
Step 5: purchase      ███                   150 (50% drop-off)
```

**Chart.js implementation**:
- Use horizontal bar chart
- X-axis = % conversion
- Color = green (healthy), yellow (warning), red (critical drop-off)

---

## 5. Anomaly Detection in Paths

### 5.1 Bot Detection

| Signal | Threshold | Action |
|--------|-----------|--------|
| Identical paths across many users | >30% of cohort on exact same path | Flag for fraud review |
| Path length = 1 | >20% of cohort | Investigate activation friction or bot |
| Path length >8 | >5% of cohort | Flag for manual review |
| Uniform step timing | `STDDEV(time_between_steps) < 1s` | Bot signature |
| No null/optional steps | All users trigger all events in funnel | Suspiciously perfect tracking |

### 5.2 Tracking Error Detection

| Signal | Threshold | Action |
|--------|-----------|--------|
| Missing first step | >10% of users don't have `launch` as step 1 | Check launch event tracking |
| Missing last step | >50% of users don't reach final funnel step | Check if step is tracked correctly |
| Out-of-order events | >5% of users have step N+1 before step N | Check event timestamps or logic |
| Duplicate events | >20% of paths have consecutive duplicates | Check for double-tracking |

---

## 6. Product-Type Path Patterns

### 6.1 Game

**Healthy pattern**:
```
launch → tutorial_start → tutorial_complete → level_1 → level_1_complete → level_2 → level_2_complete
```

**Red flags**:
- `launch → level_1` (skipping tutorial): Tutorial may be broken or users are returning (not new)
- `launch → paywall_view → purchase`: Extremely aggressive monetization, check for forced ads

### 6.2 E-commerce

**Healthy pattern**:
```
launch → browse → product_view → product_view → add_cart → checkout_start → purchase
```

**Red flags**:
- `launch → purchase`: No browsing = suspicious (could be bot or deep link)
- `launch → browse → browse → browse → exit`: No product view = poor discovery or irrelevant inventory

### 6.3 Social/Content

**Healthy pattern**:
```
launch → feed_view → content_click → like → content_click → comment → follow → share
```

**Red flags**:
- `launch → profile_edit → settings`: No content consumption = wrong intent or tracking error
- `launch → content_click → exit`: Single content view = poor content quality or misleading thumbnail

### 6.4 SaaS/Tool

**Healthy pattern**:
```
launch → signup → onboarding_step1 → onboarding_complete → feature_use → feature_use → task_complete
```

**Red flags**:
- `launch → signup → upgrade_view`: No feature use = wrong expectations or aggressive paywall
- `launch → feature_use → exit`: No onboarding = confusing UX or power user

---

## 7. SQL Implementation Notes

### 7.1 Path Extraction with LISTAGG

```sql
-- Presto/Trino syntax
SELECT 
  user_id,
  LISTAGG(event_name, '→') WITHIN GROUP (ORDER BY event_time) as path,
  COUNT(*) as path_length
FROM first_day_events
GROUP BY user_id

-- Hive syntax (alternative)
SELECT 
  user_id,
  CONCAT_WS('→', COLLECT_LIST(event_name)) as path,
  SIZE(COLLECT_LIST(event_name)) as path_length
FROM (
  SELECT user_id, event_name, event_time
  FROM first_day_events
  ORDER BY user_id, event_time
) t
GROUP BY user_id
```

### 7.2 Entropy with Window Functions

```sql
-- Compute per-cohort entropy in one query
WITH action_probs AS (
  SELECT 
    cohort_date,
    event_name,
    COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY cohort_date) as p
  FROM first_day_events
  GROUP BY cohort_date, event_name
)
SELECT 
  cohort_date,
  -SUM(p * LOG2(p)) as entropy,
  -SUM(p * LOG2(p)) / LOG2(COUNT(DISTINCT event_name)) as normalized_entropy
FROM action_probs
GROUP BY cohort_date
```

---

*File version: 1.0.0 | Last updated: 2026-09-14*
