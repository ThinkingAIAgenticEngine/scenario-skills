# Deep Analysis Guide

## Overview

After identifying P0/P1 chokepoints in the initial report, proceed with deep analysis using this guide.

## Guidance Prompt

```
📊 Initial analysis complete. The following levels require attention:
- 🔴 Level 12 (P0): Affects 12.2% of churned users
- 🟠 Level 8 (P1): Affects 9.5% of churned users

Need detailed attribute analysis for these levels?

I can analyze from these dimensions:
1️⃣ Level difficulty attributes (enemy strength/obstacle config/time limits)
2️⃣ Failure reason distribution (time out/HP depleted/voluntary exit)
3️⃣ User behavior paths (action sequence before entering level)
4️⃣ First-attempt vs. repeat-challenge user comparison
5️⃣ Other: ________ (custom)

Which dimensions would you like to analyze?
```

## Deep Analysis Report Structure (Dynamic)

Generate report depth based on user selections:

### Lean Version (1-2 dimensions, ~300-400 lines)

```markdown
# Level {X} Deep Diagnostic Report - {Dimension Name}

## 1. {Selected Dimension} Analysis
[Content based on selected dimension]

## 2. Root Cause Diagnosis
- Direct cause
- Deep cause

## 3. Optimization Recommendations
- Short-term measures
- Medium-term measures
```

### Core Version (Default, ~500-600 lines)

```markdown
# Level {X} Deep Diagnostic Report

## 1. Key Metrics Overview
## 2. {Dimension 1} Analysis
## 3. {Dimension 2} Analysis (if applicable)
## 4. Comprehensive Root Cause Diagnosis
## 5. Optimization Plan & Monitoring Metrics
```

### Full Version (3+ dimensions, ~800-1000 lines)

```markdown
# Level {X} Deep Diagnostic Report - Complete Analysis

## 1. Level Base Attributes
## 2. Failure Reason Breakdown
## 3. User Behavior Path Analysis
## 4. First-Attempt vs. Repeat Challenge Comparison
## 5. Associated Event Properties
## 6. Comprehensive Root Cause Diagnosis
## 7. Targeted Optimization Plan
## 8. Effect Monitoring Metrics

Recommended metrics to track for optimization validation:
- [ ] Level Churn Rate change: Target from {X}% to {Y}%
- [ ] Avg Attempts: Target from {X} to {Y}
- [ ] 3-Day Return Rate: Target from {X}% to {Y}%
- [ ] First-Attempt Pass Rate: Target from {X}% to {Y}%
```

## Dimension-to-Content Mapping

| User Selection | Generated Content |
|----------------|-------------------|
| Failure reasons | Failure breakdown + Failure pattern combinations |
| Power differences | Power distribution + Power vs. pass rate correlation |
| Item usage | Item usage rate + Paid vs. free comparison + Item effectiveness |
| Behavior paths | Pre-actions + Post-failure actions + Path patterns |
| User comparison | Segment comparison table + Difference analysis |

## Getting Level Event Properties

When user selects deep analysis:
1. Use `list_properties` to get level event property list
2. Recommend analysis dimensions based on property types (numeric/string/boolean)
3. Key property examples:
   - Difficulty: enemy_count, enemy_hp, time_limit, obstacle_density
   - Behavior: fail_reason, retry_count, item_used, power_level
   - Path: pre_action, post_action, session_sequence

## Analysis Dimension Selection Guide

Recommend dimensions based on identified problems:

| Initial Diagnosis | Recommended Deep Analysis | Expected Discovery |
|-------------------|---------------------------|-------------------|
| Excessive difficulty | Level config + First-attempt vs. repeat comparison | Which specific parameters exceed norms |
| Beginner chokepoint | Failure distribution + User behavior paths | Where beginners get lost |
| Low forgiveness | Failure distribution + Post-failure behavior | When users give up |
| Unclear mechanics | User behavior paths + Associated event properties | User comprehension gaps |
| Excessive cooldown | Post-failure behavior + First-attempt vs. repeat | Return flow blockers |

## Interaction Example

```
User: "Help me deeply analyze Level 12"

Skill:
Sure, let me conduct deep analysis for Level 12.

First, let me read the level event property list...
[Call list_properties for properties]

Available properties found:
- fail_reason (Failure reason): string type
- enemy_count (Enemy count): number type
- time_limit (Time limit): number type
- retry_count (Retry count): number type
- is_first_attempt (First attempt): boolean type

Based on Level 12 initial diagnosis (beginner chokepoint), I recommend:
1️⃣ Failure reason distribution (fail_reason)
2️⃣ First-attempt vs. repeat-challenge comparison (is_first_attempt + retry_count)
3️⃣ Level config parameters (enemy_count, time_limit, etc.)

Proceed with this plan, or any other dimensions of interest?
```
