# Comparison Analysis Report Template

## Usage
Generate before/after comparison reports to measure update, event, or change impact.

## Template

```markdown
# Level Churn Comparison Report

## Comparison Configuration
- **Period A ({period_a_label})**: {period_a_start} ~ {period_a_end}
- **Period B ({period_b_label})**: {period_b_start} ~ {period_b_end}
- **Game Type**: {game_type}
- **Level Range**: {level_range}
- **User Segment**: {user_segment}
- **Churn Definition**: {inactive_days} days

---

## Executive Summary

### Overall Trend: {trend_direction}

| Metric | Period A | Period B | Change | Significance |
|--------|----------|----------|--------|--------------|
| Overall Churn Rate | {rate_a}% | {rate_b}% | {delta_rate} | {sig_overall} |
| P0 Level Count | {p0_a} | {p0_b} | {delta_p0} | {sig_p0} |
| Avg Attempts per Level | {attempts_a} | {attempts_b} | {delta_attempts} | {sig_attempts} |

**Key Findings**:
1. {finding_1}
2. {finding_2}
3. {finding_3}

---

## Detailed Metrics Comparison

### Overall Performance

| Metric | Period A | Period B | Absolute Δ | Relative Δ | Trend |
|--------|----------|----------|------------|------------|-------|
| Total Users | {users_a} | {users_b} | {users_delta} | {users_pct}% | {users_trend} |
| Churned Users | {churn_a} | {churn_b} | {churn_delta} | {churn_pct}% | {churn_trend} |
| **Overall Churn Rate** | **{rate_a}%** | **{rate_b}%** | **{rate_delta}** | **{rate_pct}%** | **{rate_trend}** |
| Avg Attempts | {attempts_a} | {attempts_b} | {attempts_delta} | {attempts_pct}% | {attempts_trend} |
| 3-Day Return Rate | {return_a}% | {return_b}% | {return_delta} | {return_pct}% | {return_trend} |

### Chokepoint Severity Distribution

| Severity | Period A | Period B | Change | Assessment |
|----------|----------|----------|--------|------------|
| 🔴 P0 (Critical) | {p0_a} | {p0_b} | {p0_delta} | {p0_assessment} |
| 🟠 P1 (High) | {p1_a} | {p1_b} | {p1_delta} | {p1_assessment} |
| 🟡 P2 (Medium) | {p2_a} | {p2_b} | {p2_delta} | {p2_assessment} |
| 🟢 Normal | {normal_a} | {normal_b} | {normal_delta} | {normal_assessment} |

---

## Level-by-Level Comparison

### 🟢 Significantly Improved (Δ > -10%)

| Level | Period A | Period B | Δ Churn Rate | Significance |
|-------|----------|----------|--------------|--------------|
| Level {level_imp_1} | {rate_a_1}% | {rate_b_1}% | **{delta_1}%** | {sig_1} |
| Level {level_imp_2} | {rate_a_2}% | {rate_b_2}% | **{delta_2}%** | {sig_2} |

**Analysis**: {improvement_analysis}

---

### 🔴 Significantly Worsened (Δ > +10%)

| Level | Period A | Period B | Δ Churn Rate | Significance |
|-------|----------|----------|--------------|--------------|
| Level {level_worse_1} | {rate_a_1}% | {rate_b_1}% | **+{delta_1}%** | {sig_1} |
| Level {level_worse_2} | {rate_a_2}% | {rate_b_2}% | **+{delta_2}%** | {sig_2} |

**Analysis**: {regression_analysis}

---

### ⚪ Stable (Δ within ±10%)

{stable_levels_summary}

---

## Severity Migration Analysis

### Escalated (Became More Severe)
```
Level {level_esc_1}: 🟡 P2 → 🔴 P0 (+{delta_1}% churn) 🔴 New Critical
Level {level_esc_2}: 🟢 Normal → 🟠 P1 (+{delta_2}% churn) 🟠 New Problem
```

### De-escalated (Improved)
```
Level {level_deesc_1}: 🔴 P0 → 🟠 P1 (-{delta_1}% churn) ✅ Fixed
Level {level_deesc_2}: 🟠 P1 → 🟡 P2 (-{delta_2}% churn) ✅ Improved
```

---

## Most Changed Level Deep Dive

### Level {most_changed_level} - {change_direction} {max_delta}%

**Period A Data**:
- Churn Rate: {rate_a}%
- Total Users: {users_a}
- Avg Attempts: {attempts_a}
- Pass Rate: {pass_a}%
- Primary Issue: {issue_a}

**Period B Data**:
- Churn Rate: {rate_b}%
- Total Users: {users_b}
- Avg Attempts: {attempts_b}
- Pass Rate: {pass_b}%
- Primary Issue: {issue_b}

**Root Cause of Change**:
1. {hypothesis_1}
2. {hypothesis_2}

**Recommended Actions**:
- If improved: {improved_recommendation}
- If worsened: {worsened_recommendation}

---

## Recommendations

### {scenario_title}

{scenario_recommendations}

---

## Statistical Notes

⚠️ **Significance Thresholds**:
- ✅ **Highly Significant** (p < 0.01): |Z-score| > 2.58
- ✓ **Significant** (p < 0.05): |Z-score| > 1.96
- ~ **Marginal** (p < 0.10): |Z-score| > 1.645
- ⚪ **Not Significant** (p ≥ 0.10): |Z-score| ≤ 1.645

**Sample Size Considerations**:
- Period A: {users_a} users ({sample_assessment_a})
- Period B: {users_b} users ({sample_assessment_b})

---

**📋 Comparison Complete - Choose Next Step:**

**1. Deep Dive Specific Level**
   → Compare detailed metrics for a specific level
   → Example: `Compare Level 12 details`

**2. Export Comparison Report**
   → Save to Feishu Doc / Download as PDF

**3. Schedule Follow-up Comparison**
   → Set up automatic comparison for next period

**4. End Analysis**
   → Reply: `End`

---
```

## Statistical Significance Calculation

```
Standard Error (SE) = sqrt((p1*(1-p1)/n1) + (p2*(1-p2)/n2))
Z-score = (p2 - p1) / SE

Where:
- p1 = churn rate period A
- p2 = churn rate period B
- n1 = sample size period A
- n2 = sample size period B
```

## Scenario Recommendations

### If Overall Improved
```markdown
### ✅ Overall Trend: Improved

1. **Document Success Factors**
   - What specific changes were made?
   - Which improvement strategies were most effective?
   - Create playbook for future updates

2. **Address Regressions**
   - {worsened_count} levels worsened - investigate causes
   - Implement targeted fixes for degraded levels

3. **Scale Wins**
   - Apply successful optimizations to similar levels
   - Share findings with level design team
```

### If Overall Worsened
```markdown
### 🚨 Overall Trend: Worsened

1. **Immediate Assessment**
   - Consider rollback if P0 levels increased significantly
   - Identify which specific changes caused regressions

2. **Damage Control**
   - Prioritize fixing newly degraded critical levels
   - Implement hotfixes for P0 issues

3. **Post-Mortem**
   - Analyze why changes had negative impact
   - Update testing procedures
```

### If Stable with Shifts
```markdown
### ⚖️ Overall Trend: Stable with Shifts

1. **Analyze Trade-offs**
   - Some levels improved while others worsened
   - Net effect is neutral but distribution changed

2. **Selective Optimization**
   - Double down on what worked for improved levels
   - Fix specific regressions without touching stable areas
```

## Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `{period_a_label}` | Label for period A | "Before Update" |
| `{period_b_label}` | Label for period B | "After Update" |
| `{trend_direction}` | Overall trend | "Improved", "Worsened", "Stable" |
| `{sig_*}` | Significance indicator | "✅ Significant", "⚪ Not Significant" |
| `{delta_*}` | Absolute change | "-5.2" |
| `{*_pct}` | Percentage change | "-15.3%" |
| `{*_trend}` | Trend emoji | "↓ Improved", "↑ Worsened", "→ Stable" |
| `{scenario_title}` | Dynamic title based on trend | "Actions for Improvement Scenario" |

## Example Output

See full example in the main SKILL.md comparison analysis section.
