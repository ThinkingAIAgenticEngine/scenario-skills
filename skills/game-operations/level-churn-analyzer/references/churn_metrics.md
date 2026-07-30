# Churn Metrics Calculation Library

## Level Churn Rate

**Formula:**
```
Level Churn Rate = (Churned Users at Level / Total Challenging Users) × 100%
```

**Variables:**
- `churned_users`: Users who became inactive (inactive_days) after failing this level
- `total_users`: All users who attempted this level

**Example:**
```
Level 12 Churn Rate = 450 / 995 × 100% = 45.2%
```

---

## Overall Churn Rate

**Formula:**
```
Overall Churn Rate = (Total Churned Users / Total Challenging Users) × 100%
```

**Example:**
```
Overall 3-Day Churn Rate = 3,240 / 12,500 × 100% = 25.9%
```

---

## Churn Contribution Percentage

**Formula:**
```
Churn Contribution % = (Level Churn Count / Total Churn Count) × 100%
```

**Example:**
```
Level 12 Contribution = 450 / 3,240 × 100% = 13.9%
```

---

## 3-Day Return Rate

**Formula:**
```
Return Rate = (Returned Users / Churned Users) × 100%
```

**Variables:**
- `returned_users`: Churned users who returned within 3 days
- `churned_users`: Total users who churned at this level

**Quality Assessment:**
| Return Rate | Quality |
|-------------|---------|
| ≥ 30% | Excellent |
| 15-30% | Good |
| 5-15% | Needs improvement |
| < 5% | Critical issue |

---

## Pass Rate Metrics

### Overall Pass Rate
```
Pass Rate = (Passed Users / Total Challenging Users) × 100%
```

### First-Attempt Pass Rate
```
First-Attempt Pass Rate = (First-Try Success / Total Users) × 100%
```

**Benchmarks:**
| Pass Rate | Assessment |
|-----------|------------|
| ≥ 70% | Easy |
| 50-70% | Normal |
| 30-50% | Challenging |
| < 30% | Excessive difficulty |

---

## Retry Rate

**Formula:**
```
Retry Rate = (Users Retrying / Users Failed) × 100%
```

**Interpretation:**
- High retry rate (> 60%): Players are motivated but level may be too hard
- Low retry rate (< 30%): Players give up quickly, possible frustration issue

---

## Severity Classification

### P0 (Critical)
```
IF churn_contribution_pct > 15% OR level_churn_rate > 40%
THEN severity = "P0 Critical"
```

### P1 (High)
```
IF churn_contribution_pct > 10% OR level_churn_rate > 30%
THEN severity = "P1 High"
```

### P2 (Medium)
```
IF churn_contribution_pct > 5% OR level_churn_rate > 20%
THEN severity = "P2 Medium"
```

### Normal
```
IF below all P2 thresholds
THEN severity = "Normal"
```

---

## Statistical Significance (For Comparison)

### Standard Error
```
SE = sqrt((p1*(1-p1)/n1) + (p2*(1-p2)/n2))
```

### Z-Score
```
Z = (p2 - p1) / SE
```

Where:
- `p1` = churn rate period A
- `p2` = churn rate period B
- `n1` = sample size period A
- `n2` = sample size period B

### Significance Thresholds
| Z-Score | P-Value | Significance |
|---------|---------|--------------|
| ≥ 2.58 | < 0.01 | Highly significant |
| ≥ 1.96 | < 0.05 | Significant |
| ≥ 1.645 | < 0.10 | Marginal |
| < 1.645 | ≥ 0.10 | Not significant |

---

## Data Quality Indicators

### Sample Size Adequacy
```
IF sample_size < 100 THEN "⚠️ Sample size too small"
IF 100 ≤ sample_size < 500 THEN "⚠️ Small sample - use caution"
IF 500 ≤ sample_size < 1000 THEN "✓ Adequate sample size"
IF sample_size ≥ 1000 THEN "✓ Excellent sample size"
```

### Completeness
```
Completeness = (Complete Records / Total Records) × 100%
```

---

## Churn Attribution

### Last Level Attribution
```
Traceable Rate = (Users with Traceable Last Level / Total Churned Users) × 100%
```

Target: > 90% for reliable analysis

### Concentration Zone
```
Find level range covering top 50% of churn
```

---

## Impact Estimation

### Expected Churn Reduction
```
Expected Reduction = (Affected Users × Success Rate) / Total Churned Users × 100%
```

**Success Rate Assumptions by Action Type:**
| Action Type | Expected Success Rate | Source |
|-------------|----------------------|--------|
| Difficulty reduction | 30-50% | Industry patterns, varies by game type |
| Add checkpoint | 25-40% | Industry patterns, varies by game type |
| Improve guidance | 15-25% | Industry patterns, varies by game type |
| Push notification | 10-20% | Industry patterns, varies by game type |
| Gift items | 20-35% | Industry patterns, varies by game type |

⚠️ **Disclaimer**: These are estimated ranges based on general industry observations. Actual results vary significantly based on:
- Game genre and audience
- Implementation quality
- Baseline churn rate
- Other concurrent changes

Always A/B test interventions and measure actual impact.

---

## Calculation Checklist

When computing churn metrics:

- [ ] Confirm `inactive_days` threshold (typically 3, 7, or 14)
- [ ] Verify user segment definition
- [ ] Check date range consistency
- [ ] Ensure level IDs match between tables
- [ ] Validate churn count ≤ challenging users
- [ ] Verify return rate ≤ 100%
- [ ] Confirm severity classifications
