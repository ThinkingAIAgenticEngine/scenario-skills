---
name: level-churn-analyzer
description: |
  Diagnose game level churn by identifying chokepoint levels, analyzing root causes, and providing actionable optimization recommendations.
  **Standard Analysis**: Triggered by "level churn analysis", "users stuck at level X", "chokepoint diagnosis".
  **Comparison Mode**: Triggered by "compare before and after update", "did the patch improve retention", "analyze event impact".
  **Applicable Games**: All games with level-based progression (Card, RPG, SLG, Casual, Match-3, Runner, etc.).
---

# Level Churn Analyzer

> One-liner: Identify game chokepoints by analyzing the last level users attempted before churning, with targeted optimization recommendations.

## Core Capabilities

1. **Chokepoint Identification** - Find levels causing the most user churn
2. **Root Cause Analysis** - Determine why users churn at specific levels
3. **Segment Comparison** - Compare level performance across new vs. returning, paid vs. free users
4. **Optimization Recommendations** - Provide targeted level design and intervention strategies
5. **Before/After Comparison** - Compare level churn across time periods to measure update/event impact

---

## Quick Start

### Example: Standard Level Churn Analysis

**User:** "Analyze level churn for our Match-3 game"

**Skill:**
```
I'll help you analyze level churn. Please provide:

1. **Game Type**: Match-3 ✓
2. **Level Type**: Main / Challenge / Event?
3. **Level Range**: e.g., "1-100" or "all"
4. **User Segment**: All users / New users / Paid users?
5. **Churn Definition**: Days of inactivity (default: 3)
6. **Time Range**: e.g., "Last 30 days" or "2026-04-01 to 2026-05-01"
7. **Project ID**: Your ThinkingData project ID
```

**User:**
- Level Type: Main
- Level Range: 1-100
- User Segment: All users
- Churn Definition: 3 days
- Time Range: Last 30 days
- Project ID: 123

**Skill:** *[Executes analysis]*

**Output:**
```markdown
# Level Churn Diagnostic Report

## Analysis Overview
- Total Challenging Users: 12,500
- Churned Users: 3,240
- Overall 3-Day Churn Rate: 25.9%

## Key Chokepoint Levels

| Rank | Level | Churn % | Severity |
|------|-------|---------|----------|
| 1 | Level 32 | 13.9% | 🔴 P0 |
| 2 | Level 28 | 11.7% | 🟠 P1 |
| 3 | Level 15 | 6.5% | 🟡 P2 |

**Root Cause - Level 32**: Excessive difficulty [High Confidence]
- Pass rate: 18% (below 20% threshold)
- Avg attempts: 4.2x

**Recommended Action**: Reduce obstacle density by 15-20%
```

---

### Example: Comparison Mode

**User:** "Compare level churn before and after the update"

**Skill:**
```
I'll compare level churn between two periods.

Period A (Before): [Start date] to [End date]
Period B (After): [Start date] to [End date]

Other parameters same as standard analysis.
```

**User:** Period A: 2026-04-01 to 2026-04-14, Period B: 2026-04-15 to 2026-04-28

**Skill:** *[Runs parallel analysis and generates comparison report]*

---

## Templates and Libraries

This skill uses modular templates for report generation. Reference these files when generating reports:

### Report Templates

| Template | File | Purpose |
|----------|------|---------|
| Overview Section | `references/overview_section.md` | Report header and analysis overview |
| Chokepoint Table | `references/chokepoint_table.md` | Top N chokepoint levels table |
| Level Details | `references/level_details.md` | Deep dive into specific levels |
| Comparison Report | `references/comparison_report.md` | Before/after comparison analysis |
| Action Recommendations | `references/action_recommendations.md` | Prioritized action items |
| Deep Analysis Guide | `references/deep_analysis_guide.md` | Deep analysis workflow guidance |
| Recommendations Library | `references/recommendations.md` | Genre-specific optimization recommendations |

### Calculation Library

| Library | File | Purpose |
|---------|------|---------|
| Churn Metrics | `references/churn_metrics.md` | Reusable churn calculation formulas |

### Severity Classification with Confidence Intervals

#### Base Thresholds by Game Genre

Different game types have different "normal" churn baselines. Adjust thresholds accordingly:

| Genre | Typical D1 Churn | P0 Threshold | P1 Threshold | P2 Threshold |
|-------|------------------|--------------|--------------|--------------|
| Hyper-casual | 60-70% | >55% or >12% contribution | >45% or >8% contribution | >35% or >4% contribution |
| Casual (Match-3/Runner) | 40-50% | >40% or >15% contribution | >30% or >10% contribution | >20% or >5% contribution |
| Mid-core (RPG/Card) | 30-40% | >35% or >15% contribution | >25% or >10% contribution | >18% or >5% contribution |
| Hardcore/SLG | 20-30% | >25% or >15% contribution | >20% or >10% contribution | >15% or >5% contribution |

**Default thresholds** (when genre unknown): Use Casual tier.

#### Severity Classification Table

| Severity | Condition | Label | Priority |
|----------|-----------|-------|----------|
| P0 | Churn rate > genre threshold OR % of total churn >15% | 🔴 Critical | Immediate |
| P1 | Churn rate > genre threshold OR % of total churn >10% | 🟠 High | This week |
| P2 | Churn rate > genre threshold OR % of total churn >5% | 🟡 Medium | This month |
| Normal | Below P2 thresholds | 🟢 Normal | Monitor |

**Sample Size Confidence Guidelines:**

| Sample Size (n) | Confidence Level | Severity Adjustment |
|----------------|------------------|---------------------|
| n ≥ 1000 | High (±2-3%) | Use classification as-is |
| 500 ≤ n < 1000 | Medium (±3-5%) | Downgrade one level if at boundary |
| 100 ≤ n < 500 | Low (±5-10%) | Downgrade one level; flag for verification |
| n < 100 | Very Low (±10%+) | Do not classify; require larger sample |

**Confidence Interval Calculation:**
```
95% CI for churn rate = p ± 1.96 × √(p(1-p)/n)

Where:
- p = observed churn rate (proportion)
- n = sample size (total challenging users)
```

**Display Format with Confidence:**
```
🔴 P0 - Level 32: 13.9% of churn (95% CI: 12.1%-15.7%)
     Level churn rate: 45.2% (95% CI: 42.8%-47.6%)
     Confidence: High (n=2,847 users) ✓

🟠 P1 - Level 28: 11.2% of churn (95% CI: 8.9%-13.5%) ⚠️
     Level churn rate: 38.5% (95% CI: 35.2%-41.8%)
     Confidence: Medium (n=892 users)
     Note: At P0 boundary; consider verification before prioritization
```

---

## Interaction Flow

**Reference**: `references/interaction_flow.md`

This guide provides the complete 4-step interaction workflow:

1. **Define Analysis Parameters** (7 parameters with validation)
   - Game Type, Level Type, Level Range, User Segment, Churn Definition, Time Range, Project ID
   - Includes input validation templates and production limits

2. **Event Confirmation & Data Validation**
   - Level event discovery and confirmation
   - Sample size assessment with confidence tiers
   - Data anomaly handling

3. **Output Diagnostic Report**
   - Report generation using modular templates
   - Standard report ending format

4. **Guide Deep Analysis (Optional)**
   - Property pre-validation
   - Dimension-based analysis
   - Dynamic report generation

---

## Analysis Methodology

**Core Method**: Churn Attribution Analysis

Identify "churn-trigger levels" by finding the last level attempted by specific user segments before becoming inactive.

**Analysis Target:**
- Based on segment selected in Step 2 (All users/New users/Silent users/Paid users/Custom)
- Supports custom segment conditions: registration time, payment status, activity level, current progress
- Analyze which levels users were last at before churning

**Key Parameters:**
- `inactive_days`: Days of consecutive inactivity to define churn (default: 3)
- `lookback_days`: Days to look back for last level (default: 7)
- `level_range`: Level range to analyze
- `user_segment`: User segment conditions

**Core Metrics:**

See `references/churn_metrics.md` for complete formula reference.

### 1. Overall Churn Rate (Analysis Overview)

```
Overall Churn Rate = Churned Users / Total Challenging Users × 100%
```

**Calculation Logic:**
1. **Churned Users (Numerator)**: Unique users who churned at any level within analysis time range
   - A user is counted once regardless of how many levels they churned at
   - Deduplicated by user

2. **Total Challenging Users (Denominator)**: Unique users who challenged any level in analysis time range

**Example Calculation:**
- User A: Churned at Level A → Counted as churned (1 user)
- User B: Churned at Level B → Counted as churned (1 user)
- User C: Did not churn at Level C → Not counted as churned
- User D: Churned at both Level A and B → Counted once (deduplicated)

**Result:**
- Churned Users: 3 (A + B + D)
- Total Users: 4 (A + B + C + D)
- **Overall Churn Rate = 3/4 = 75%**

---

### 2. Level Churn Rate (Per-Level Metric)

```
Level Churn Rate = Churns at Level / Total Users Challenging Level × 100%
```

**Calculation Logic:**
1. **Churn Count (Numerator)**: Each instance of "last at Level + inactive ≥ threshold" counts as 1 churn
   - Same user can contribute to multiple levels' churn counts (different time periods)
   - Same level same user: Only count the most recent (deduplicate multiple churns at same level)

2. **Total Challenging Users (Denominator)**: Unique users challenging Level in analysis time range

**Example Calculation:**
- User A:
  - Mar 1: Last at Level A, inactive 3+ days → Level A churn: 1
  - Mar 5: Recalled
  - Mar 10: Last at Level B, inactive 3+ days → Level B churn: 1
  - Mar 15: Challenged Level A again, Mar 20: Last at Level A, inactive → Level A still 1 (overwrites Mar 1)
- User B: Mar 5: Last at Level A, inactive 3+ days → Level A churn: 1
- User C: Challenged Level A but didn't churn → Not counted

**Result:**
- Level A Churn Count: 2 (User A + User B)
- Level A Total Users: 3 (A + B + C)
- **Level A Churn Rate = 2/3 = 66.7%**

---

**Level Performance Statistics:**

Consistent with churn rate calculation, denominator uses "Total Challenging Users" (deduplicated).

### Basic Metrics

| Metric | Calculation | Notes |
|--------|-------------|-------|
| **Total Challenging Users** | Unique users challenging Level | Deduplicated, denominator standard |
| **Total Attempts** | All challenge attempts at Level | Not deduplicated, includes retries |
| **Avg Attempts** | Total Attempts / Total Challenging Users | Average per user |

### Pass/Fail Metrics

| Metric | Calculation | Notes |
|--------|-------------|-------|
| **Level Overall Pass Rate** | Passes / Total Attempts × 100% | Success proportion of all attempts |
| **Level Overall Fail Rate** | (Total Attempts - Passes) / Total Attempts × 100% | Failure proportion |
| **First-Attempt Pass Rate** | Users passing on first try / Total Challenging Users × 100% | First-try success rate |

### User Attribute Metrics

| Metric | Calculation | Notes |
|--------|-------------|-------|
| **New User Ratio** | New users / Total Challenging Users × 100% | Proportion of new users |
| **Paid User Ratio** | Paid users / Total Challenging Users × 100% | Proportion of paid users |
| **3-Day Return Rate** | Users returning within 3 days of churn / Churn Count × 100% | Post-churn return rate |

---

## Root Cause Inference Rules

Infer churn causes based on data characteristics. **Note: These are heuristic indicators, not definitive causes. Confidence levels indicate diagnostic certainty.**

| Data Characteristic | Inferred Cause | Threshold | Confidence | Limitations |
|---------------------|----------------|-----------|------------|-------------|
| New user ratio >70% | Difficulty mismatch for beginners | >70% | **High** | Clear segment signal; verify with tutorial completion data |
| Pass rate <20% | Excessive level difficulty | <20% | **High** | Definitive difficulty signal; check if intentional (boss levels) |
| 3-Day return rate <5% | Failed return mechanism | <5% | **High** | Strong signal for recall system failure |
| Pass rate <30% | Excessive level difficulty | <30% | **Medium** | May be intended challenge; check level design docs |
| 3-Day return rate <10% | Failed return mechanism | <10% | **Medium** | Could be normal for late-game levels |
| Avg attempts >5 | Insufficient forgiveness | >5% | **Medium** | High attempts can indicate engagement OR frustration |
| Retry interval after fail >24h | Excessive cooldown after failure | >24h | **Medium** | May reflect natural play patterns, not system issue |
| New user ratio >50% | Difficulty mismatch for beginners | >50% | **Low** | Weak signal; could reflect normal user distribution |
| Avg attempts >3 | Insufficient forgiveness | >3 | **Low** | Common across many levels; not diagnostic alone |

### Confidence-Based Inference Guidelines

**High Confidence Indicators** (Strong signal, act with confidence):
- Multiple high-confidence signals align
- Threshold exceeded by >20% margin
- Consistent across user segments

**Medium Confidence Indicators** (Probable cause, verify before acting):
- Single medium-confidence signal
- Threshold exceeded by 10-20% margin
- Consider A/B testing interventions

**Low Confidence Indicators** (Weak signal, investigate further):
- Requires corroborating evidence
- May be normal variation
- Recommend qualitative research (user interviews, session replay)

### Compound Diagnosis Format

Connect multiple causes with confidence markers:
```
Primary: High confidence causes first
Secondary: Medium confidence causes (verify)
Tertiary: Low confidence causes (investigate)
```

**Examples:**
```
Level 12 Analysis:
- Primary: Difficulty mismatch for beginners (High confidence: 78% new users)
- Secondary: Insufficient forgiveness (Medium confidence: 4.2 avg attempts)
- Tertiary: Excessive cooldown (Low confidence: 22h avg retry, borderline)
```

### Inference Limitations Disclaimer

⚠️ **Important**: Root cause analysis is based on data pattern matching, not causal inference.

- Correlation ≠ Causation: High new user ratio may indicate popular level, not difficulty issue
- Thresholds are heuristics: Adjust based on your game's specific patterns
- Missing variables: External factors (events, updates, competitors) not captured
- Recommend validation: Always combine with user feedback, session replay, or A/B tests

**Output Format**: Connect multiple causes with "+", and include confidence level: e.g., "Difficulty mismatch [High] + Insufficient forgiveness [Medium]"

---

## Optimization Recommendation Library

**Reference**: `references/recommendations.md`

This template provides:
- Universal optimization measures by problem type
- Genre-specific recommendations (8 game types)
- Intervention strategies by timing

### Quick Reference

**Problem Type → Recommended Actions:**
| Problem Type | Quick Fix | System Fix |
|--------------|-----------|------------|
| Excessive difficulty | Lower HP/damage | Rebalance progression curve |
| Beginner chokepoint | Add hints | Simplify early levels |
| Low forgiveness | Add checkpoints | Revise fail conditions |
| Excessive cooldown | Push notification | Lower retry cost |
| Unclear mechanics | Add tutorial | Improve UX feedback |

**Genre-Specific Quick Links:**
- Card: Deck building hints, trial cards
- RPG: Mechanic tutorials, gear drops
- Match-3: Move cap, special items
- Runner: Speed/obstacle adjustment
- SLG: Resource output, strategy hints
- Casual/Sim: Wait time reduction
- MOBA: Newbie matchmaking
- Idle: Offline earnings boost

---

## Comparison Analysis Mode

Compare level churn between two time periods to measure impact of updates, events, or changes.

**Trigger Phrases:**
- "Compare before and after the update"
- "Analyze the impact of the event"
- "Compare this week vs last week"
- "Did the patch improve level retention?"

### Comparison Flow

**Step 1 - Identify Comparison Intent**

When user mentions comparison keywords, switch to comparison mode:

```
User: "Compare level churn before and after the update"

Skill: "I'll help you compare level churn between two time periods.

Please provide:
- Period A (Before): Start and end date
- Period B (After): Start and end date
- Other parameters remain the same (game type, level range, user segment, etc.)

Example:
- Period A: 2026-04-01 to 2026-04-14
- Period B: 2026-04-15 to 2026-04-28"
```

**Step 2 - Collect Parameters**

Collect standard parameters (game type, level range, user segment, churn definition) plus:

**Period A (Baseline):**
- Time range: `period_a_start` to `period_a_end`
- Label: e.g., "Before Update", "Week 1", "Control Group"

**Period B (Comparison):**
- Time range: `period_b_start` to `period_b_end`
- Label: e.g., "After Update", "Week 2", "Test Group"

**Validation Rules:**
- Both periods must be valid date ranges
- Periods should not overlap (recommendation)
- Period B should be after Period A (for temporal comparisons)
- Same duration recommended for fair comparison (e.g., both 14 days)

**Step 3 - Execute Parallel Analysis**

Run standard level churn analysis for both periods with identical parameters, then generate comparison report using `references/comparison_report.md`.

---

## Deep Analysis Template (Step 4)

After identifying P0/P1 chokepoints in the initial report, proceed with deep analysis.

**Reference**: Use `references/deep_analysis_guide.md` for complete guidance including:
- Guidance prompts for user interaction
- Report structure templates (Lean/Core/Full versions)
- Dimension-to-content mapping
- Property discovery guidance
- Analysis dimension selection guide

### Quick Reference

**Report Depth by Selection:**
| Selection Count | Template Version | Sections |
|-----------------|------------------|----------|
| 1-2 dimensions | Lean | 3 sections |
| 3+ dimensions | Full | 6-8 sections |
| Unclear | Core | 5 sections (default) |

**Dimension Recommendations by Problem Type:**
| Problem Type | Recommended Analysis |
|--------------|---------------------|
| Excessive difficulty | Level config + First-attempt vs repeat |
| Beginner chokepoint | Failure distribution + User behavior paths |
| Low forgiveness | Failure distribution + Post-failure behavior |
| Unclear mechanics | User behavior paths + Event properties |
| Excessive cooldown | Post-failure behavior + Retry patterns |

---

## Quick Reference

| User Query | Recommended Segment | Key Parameter Suggestions |
|------------|---------------------|--------------------------|
| "Which levels are users stuck at?" | All users | inactive_days: 3 |
| "Analyze users inactive 7 days" | Silent users (7 days inactive) | Focus on high concentration levels |
| "New user churn is severe" | New users (registered <7 days) | Focus on levels 1-30 |
| "Challenge level churn" | All users | level_type: "Challenge" |
| "Silent user analysis" | Silent users (7-14 days inactive) | Focus on recall opportunities |
| "Find hardest level" | All users | Focus on churn conversion metrics |
| "Paid user churn" | Paid users | Focus on paid experience |
| "Compare before and after update" | **Comparison Mode** | Define Period A (before) and Period B (after) |
| "Did the patch improve retention?" | **Comparison Mode** | Same parameters, different time ranges |
| "Analyze event impact" | **Comparison Mode** | Compare during-event vs baseline |

---

## Important Notes

1. **Data Quality**: When level challenging user count is low (<100), conclusions may be unreliable. Warn user.
2. **Data Latency**: Account for data reporting latency, recommend analyzing T-1 or earlier data
3. **Event Consistency**: Confirm event names match actual project instrumentation
4. **Multi-dimensional Comparison**: Recommend comparing "New vs. Returning" users - differences are often significant
5. **Avoid Over-inference**: Root cause analysis is inference-based, mark "Recommend further research validation"

---

## Report Output Requirements

1. **Must include**: Header overview, Key chokepoint list, Root cause diagnosis, Action recommendations
2. **Recommended visualization**: Level churn rate trend chart, Chokepoint distribution heatmap
3. **Tiered output**: Display by P0/P1/P2 priority for operations team processing
4. **Actionable**: All recommendations must be specific and executable, avoid vague suggestions
5. **Must include next-step guidance**: Every report must end with clear next options (continue analysis / other levels / end)

### Standard Report Ending Format

After every report, use this format to guide users:

```markdown
---

**📋 Analysis Complete - Choose Next Step:**

**1. Continue Deep Analysis of Current Level**
   → I can analyze any dimension by level event properties
   → Example reply: `Analyze Level {X}, show failure reason distribution`
   → Example reply: `Analyze Level {X}, compare pass rates by power level`
   → Example reply: `Analyze Level {X}, show item usage and completion correlation`

**2. Analyze Other Chokepoint Levels**
   → Reply: `Analyze Level {Y}`

**3. End Analysis**
   → Reply: `End`

---
```
