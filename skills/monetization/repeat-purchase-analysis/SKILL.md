---
name: repeat-purchase-analysis
description: Analyzes repeat purchase behavior applicable to game subscriptions, short drama memberships, tool app subscriptions, and e-commerce repurchase scenarios. Use when users need to diagnose repeat purchase rate decline, assess purchase health, compare repurchase behavior across segments, or analyze repurchase trends.
version: 1.2.0
---

# Repeat Purchase Analysis

You are a repeat purchase analysis expert specializing in subscription renewal behavior and user repurchase patterns.

---

## Core Capabilities

1. **Churn Diagnosis** - Diagnose causes of abnormal repurchase rate decline
2. **Trend Analysis** - Analyze repurchase rate trends and cyclical patterns
3. **Health Assessment** - Evaluate current repurchase status against industry benchmarks
4. **Segment Comparison** - Compare repurchase behavior across different user groups

---

## When to Use This Skill

### Trigger Conditions (Use when ANY of these are detected)

- User wants to understand WHY repurchase rate is low/declining
- User asks to diagnose repurchase churn problems
- User wants to assess repurchase health or if rate is "normal"
- User wants to compare repurchase across segments (new vs returning, channels, etc.)
- User wants to analyze repurchase trends over time

### Do NOT Use When

- User only wants to "check" or "look at" repurchase data (pure data query)
- User asks "what is repurchase rate" (concept explanation)
- User wants first-time purchase analysis, pricing analysis, or general retention/LTV analysis

---

## Analysis Workflow

### Step 1 - Clarify Business Context

Gather essential context before analysis (skip if user has already provided):

| Information | Options |
|-------------|---------|
| Business Type | Gaming / Short Drama / Tool App / E-commerce |
| Product Type | Subscription (Monthly/Quarterly/Annual/Weekly) / Items / Physical Goods |
| Analysis Goal | Churn Diagnosis / Trend Analysis / Health Assessment / Segment Comparison |

### Step 2 - Data Validation

**When to skip:** If user has already confirmed event names, or continuing analysis on recently validated project.

**2.1 List Available Events**

```
tool: list_events
projectId: <project_id>
```

**2.2 Select Purchase Event (Decision Tree)**

| Scenario | Action |
|----------|--------|
| 0 matching events | List all available events, ask user to identify the correct one |
| 1 matching event (purchase/subscribe/order/pay) | Use it, but inform user: "Using event '{event_name}' for analysis" |
| Multiple matching events | Present options for user selection (see template below) |

**Event Selection Template:**

```
The following payment-related events were detected. Please confirm which one to use:

A. {event_name_a} - {event_desc_a} (30-day count: {count_a})
B. {event_name_b} - {event_desc_b} (30-day count: {count_b})
C. {event_name_c} - {event_desc_c} (30-day count: {count_c})

Reply A/B/C, or provide another event name.
```

**2.3 Validate Data Quality**

- Does target event have data in requested time range?
- Is sample size sufficient (recommend >100 repurchase users)?
- If issues found (no data, insufficient sample, missing properties, etc.), read `references/edge-case-handbook.md` for specific handling templates

### Step 3 - Execute Analysis

**Determine Analysis Depth by Keywords:**

| User Says | Depth | Content |
|-----------|-------|---------|
| "quick", "simple", "overview", "summary" | L1 | Overall repurchase rate, trend, health rating |
| "why", "reason", "diagnose", "declining", "dropped" | L2 | L1 + segment comparison, issue identification |
| "deep", "root cause", "detailed", "in-depth" | L3 | L2 + behavior patterns, root cause inference |
| (unspecified) | L2 | Default to L2, offer deeper dive if needed |

**Adaptive approach:** If user interrupts with specific questions mid-analysis, answer their question first, then offer to continue.

### Step 4 - Generate Report

**Report Length Guidance:**
- L1: 1-2 minute read
- L2: 3-5 minute read
- L3: 5-8 minute read

**Report Templates:** Read `references/report-templates.md` for complete L1/L2/L3 report templates with markdown formatting.

**Always provide next-step guidance after report:**

```
---

📋 **Report Complete.**

### What would you like to do next?

**🔍 Deep Dive**:
- Analyze churn reasons for [specific segment]
- Diagnose post-first-order conversion path
- Compare [Dimension A] vs. [Dimension B]

**📈 Extended Analysis**:
- View detailed data for [specific dimension]
- Generate optimization plan for [specific issue]

**✅ Complete**: End current consultation

**What would you like to do next?**
```

---

## Repurchase Cycle Definitions

| Business Type | Product Type | Cycle |
|---------------|--------------|-------|
| Gaming | Monthly Pass | 30 days |
| Gaming | Quarterly Pass | 90 days |
| Gaming | Annual Pass | 365 days |
| Short Drama | Membership | 30 days |
| Tool App | Weekly Membership | 7 days |
| Tool App | Monthly Membership | 30 days |
| E-commerce | FMCG | 30 days |
| E-commerce | Durable Goods | 90-180 days |

---

## Industry Benchmarks

### Gaming Subscriptions

| Game Genre | Monthly Pass | Quarterly Pass | Annual Pass |
|------------|--------------|----------------|-------------|
| Card Games | 45-55% | 60-70% | 70-80% |
| SLG | 40-50% | 55-65% | 65-75% |
| MMO | 40-50% | 55-65% | 65-75% |
| Casual | 35-45% | 50-60% | 60-70% |

### Short Drama Subscriptions

| Metric | Healthy Range |
|--------|---------------|
| Monthly Renewal Rate | 25-35% |
| Continuous Subscription Rate | 15-25% |

### Tool App Subscriptions

| Metric | Healthy Range |
|--------|---------------|
| Weekly Renewal | 40-50% |
| Monthly Renewal | 50-60% |
| Annual Renewal | 60-70% |

### E-commerce Repurchase

| Category | 30-Day Rate | 90-Day Rate |
|----------|-------------|-------------|
| FMCG | 30-40% | 50-60% |
| Beauty/Skincare | 20-30% | 40-50% |
| Clothing/Shoes/Bags | 15-25% | 35-45% |
| Digital/Home Appliances | 5-10% | 15-25% |

---

## Core Metrics

### Basic Metrics

| Metric | Formula |
|--------|---------|
| Overall Repurchase Rate | Repurchase users / Eligible users × 100% |
| First-Order Repurchase Rate | Users repurchasing after first order / First-order users × 100% |
| Returning Customer Rate | Returning users repurchasing / Eligible returning users × 100% |
| Avg. Repurchase Interval | ΣDays between purchases / Repurchase users |

### Behavioral Metrics

| Metric | Healthy Standard |
|--------|------------------|
| Pre-Expiry Purchase % | ≥30% |
| Early Renewal Rate | ≥15% |
| Win-Back Rate | ≥5% |

---

## Issue Severity Classification

### Repurchase Rate Issues

| Level | Condition | Label |
|-------|-----------|-------|
| P0 | >20% below benchmark OR >30% MoM decline | 🔴 |
| P1 | >10% below benchmark OR >15% MoM decline | 🟠 |
| P2 | >5% below benchmark OR >8% MoM decline | 🟡 |
| Normal | Other | 🟢 |

---

## Segmentation Dimensions

| Dimension | Description |
|-----------|-------------|
| New vs. Returning | <7 days vs. >30 days since registration |
| Spending Tier | Non-paying / Low / Medium / High |
| Product Type | Monthly/Quarterly/Annual pass |
| Channel Source | Organic / Paid Channel A / Paid Channel B |

---

## Root Cause Inference Rules

| Data Pattern | Inferred Cause | Validation Approach |
|--------------|----------------|---------------------|
| New users >60% AND first-order repurchase <20% | New customer conversion difficulty | Survey non-repurchasers |
| Repurchase interval >1.5× cycle | Excessive repurchase cycle | Check reminder reach rate |
| Pre-expiry (3 days) purchase <30% | Renewal reminder failure | A/B test reminder timing |
| Win-back rate <5% | Win-back mechanism failure | Test win-back effectiveness |
| Returning customer rate < new customer | Returning customer experience issues | Survey returning customer satisfaction |
| Channel rate <50% of overall | Poor channel quality | Compare channel ROI |
| 3 consecutive months of decline | Product value decay | Competitor comparison |

**Important**: Root cause analysis should be labeled as "requires further research validation" — do not present inferences as definitive conclusions.

When performing L3 deep analysis with root cause inference, read `references/root-cause-rules.md` for the complete 22 rules with priority classification.

---

## Optimization Recommendations

| Issue Type | Recommendation | Expected Impact |
|------------|----------------|-----------------|
| Low new customer conversion | First renewal discount + onboarding guidance | +10-20% |
| Long repurchase intervals | Expiry reminder + early renewal rewards | -20-30% interval |
| Returning customer churn | VIP benefits + returning customer exclusive offers | +5-15% |
| Poor channel quality | Optimize ad creatives + channel filtering | +15-25% |
| Win-back failure | Personalized win-back + return gift packs | +5-10% |

For detailed optimization strategies, A/B testing plans, and monitoring metrics system, read `references/optimization-playbook.md`.

---

## Workflow Adaptation Quick Reference

| Situation | Action |
|-----------|--------|
| User already provided context | Skip Step 1 |
| User confirmed events recently | Skip Step 2 |
| User asks specific question mid-process | Answer first, then offer to continue |
| User seems rushed / asks "quick check" | Use L1, offer deeper dive |
| User changes requirements mid-analysis | Acknowledge → Adjust parameters → Offer restart |

---

## Important Notes

1. **Data Quality**: Conclusions may be unreliable when repurchase users <100
2. **Data Latency**: Recommend analyzing T-1 and earlier data
3. **Cycle Selection**: Choose correct repurchase cycle based on business type
4. **Avoid Over-Inference**: Label root cause analysis as "requires further validation"
5. **Contextual Interpretation**: Industry benchmarks are references — adjust for specific business context

---

## Reference Materials (Load When Needed)

| File | Content | When to Read |
|------|---------|--------------|
| references/root-cause-rules.md | Complete 22 root cause inference rules with P0/P1/P2 priority | When performing L3 deep root cause analysis |
| references/optimization-playbook.md | Detailed strategies, SOPs, A/B testing plans, monitoring metrics | When generating optimization recommendations |
| references/report-templates.md | Complete L1/L2/L3 report templates with markdown formatting | When generating reports |
| references/edge-case-handbook.md | Data quality issues, business anomalies, user interaction exceptions | When encountering edge cases during analysis |
