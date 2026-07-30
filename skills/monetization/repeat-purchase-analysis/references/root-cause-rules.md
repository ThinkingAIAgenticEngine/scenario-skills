# Root Cause Inference Rules Manual

This document provides structured rules for inferring repurchase issues based on data characteristics.

---

## 1. Root Cause Inference Rules Table

| Rule | Trigger Condition | Inferred Cause | Validation Method |
|------|-------------------|----------------|-------------------|
| New customer conversion difficulty | New user proportion >60% AND first-order repurchase rate <20% | Insufficient onboarding / Excessive first-order discounts / High product barriers | Survey non-repurchasers |
| Poor first-order quality | Channel first-order repurchase rate <50% of overall | Inaccurate channel targeting / Misleading creatives | Compare channel LTV |
| Poor first-order experience | Churn rate within 7 days after first order >50% | Product value below expectations / Usage barriers | Analyze post-first-order behavior |
| Excessive repurchase interval | Repurchase interval >1.5× cycle | Reminder failure / User forgetting / Competitor attraction | Check reminder reach rate |
| Expiry churn | Pre-expiry (3 days) purchase proportion <30% | Poor reminder timing / Unattractive offers | A/B test reminder timing |
| Passive repurchase dominance | Same-day expiry purchase proportion >50% | Low user stickiness / Over-reliance on reminders | Analyze repurchase proactivity |
| Returning customer experience issues | Returning customer repurchase rate < new customer | Product value decay / Insufficient VIP benefits / Competitor migration | Survey returning customer satisfaction |
| High-value user churn | Big R user repurchase rate decline >20% | Big R benefits insufficient / Content exhaustion | Big R one-on-one research |
| Long-term silence | Users with no repurchase in 90 days >30% | Recall mechanism failure / High return barriers | Test recall effectiveness |
| Poor channel quality | Channel repurchase rate <50% of overall | Inaccurate channel users / Misleading creatives | Compare channel ROI |
| Low organic repurchase | Organic repurchase rate < paid channels | Insufficient product attractiveness / Reputation issues | Analyze user reviews |
| Product value decay | Decline for 3 consecutive months | Competitor impact / Insufficient content updates / UX decline | Competitor comparison analysis |

---

## 2. Root Cause Output Format

### Single Issue Root Cause
```
[Root Cause Diagnosis] {Primary root cause}
[Data Evidence] {Trigger condition}
[Validation Recommendation] {Validation method}
```

### Multiple Issue Root Cause
```
[Root Cause Diagnosis] {Cause A} + {Cause B}
[Data Evidence] {Trigger condition A}, {Trigger condition B}
[Validation Recommendation] {Validation method}
```

---

## 3. Root Cause Priority Sorting

| Priority | Root Cause Type | Processing Timeline |
|----------|-----------------|---------------------|
| P0 | New customer conversion difficulty, Returning customer repurchase rate < new customer, Main channel quality collapse | Immediate |
| P1 | Excessive repurchase interval, Low pre-expiry purchase proportion, High-value user churn | This week |
| P2 | Single channel quality deviation, Poor recall mechanism, Significant segment differences | This month |
