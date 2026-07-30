# Report Templates

Complete report templates for the main skill to reference.

---

## L1 - Overview Report

Use for: Trend queries, health assessments

```markdown
## Repurchase Overview
- **Overall Repurchase Rate**: {rate}% (Benchmark: {benchmark}%)
- **MoM Change**: {change}% (Last month: {last_rate}%)
- **Health Rating**: {level}
- **Trend Assessment**: {trend}

## Key Findings
1. {Finding 1}
2. {Finding 2}

## Recommendations
1. {Recommendation 1}
```

---

## L2 - Diagnostic Report

Use for: Churn diagnosis, problem identification

```markdown
## Repurchase Overview
- **Overall Repurchase Rate**: {rate}% (Benchmark: {benchmark}%)
- **MoM Change**: {change}%
- **Health Rating**: {level}
- **Issue Severity**: {severity}

## Segment Comparison

| Segment | Rate | vs. Overall | Risk Level |
|---------|------|-------------|------------|
| New Users | {rate}% | {diff}% | {level} |
| Returning Users | {rate}% | {diff}% | {level} |
| {Channel A} | {rate}% | {diff}% | {level} |
| {Channel B} | {rate}% | {diff}% | {level} |

## Key Findings
1. {Finding 1}
2. {Finding 2}
3. {Finding 3}

## Problem Identification
- **Primary Issue**: {description}
- **Affected Segments**: {segments}
- **Likely Causes**: {causes}

## Recommendations
1. {Recommendation 1}
2. {Recommendation 2}
```

---

## L3 - Deep Analysis Report

Use for: Root cause analysis

```markdown
## Repurchase Overview
- **Overall Repurchase Rate**: {rate}% (Benchmark: {benchmark}%)
- **MoM Change**: {change}%
- **Health Rating**: {level}

## Segment Analysis
[Same as L2]

## Behavioral Patterns

| Metric | Value | Benchmark | Status |
|--------|-------|-----------|--------|
| Pre-Expiry Purchase % | {value}% | ≥30% | {status} |
| Early Renewal Rate | {value}% | ≥15% | {status} |
| Win-Back Rate | {value}% | ≥5% | {status} |
| Avg. Repurchase Interval | {value} days | {benchmark} | {status} |

## Root Cause Analysis

### Primary Issue: {issue}
**Evidence**:
- {Evidence 1}
- {Evidence 2}

**Inferred Root Cause**: {cause}
*Note: Requires further research validation*

**Recommended Validation**:
- {Validation method 1}
- {Validation method 2}

## Detailed Recommendations

### Immediate Actions (This Week)
1. {Action 1} - Expected impact: {impact}

### Short-term Measures (This Month)
1. {Action 1} - Expected impact: {impact}

### Long-term Improvements (Next Quarter)
1. {Action 1} - Expected impact: {impact}
```

---

## Post-Report Interaction Guidance

After delivering any report, **always** provide clear next-step guidance:

```
---

📋 **Report Complete.**

### What would you like to do next?

**🔍 Deep Dive** (Diagnose specific issues):
- Analyze churn reasons for [specific channel/segment]
- Diagnose post-first-order conversion path
- Analyze causes of long repurchase intervals
- Compare [Dimension A] vs. [Dimension B]

**📈 Extended Analysis** (Additional perspectives):
- View detailed data for [specific dimension]
- Analyze win-back effectiveness for [specific channel]
- Generate specific optimization plan for [specific issue]

**✅ Complete**:
- Export full analysis report
- End current consultation

---

**What would you like to do next?** (Enter number or describe your need)
```

**Guidance Principles**:
1. Be specific, not generic
2. Reference content from the delivered report
3. Give users clear choices to reduce decision cost
4. Proactively suggest ending if analysis is sufficiently deep
