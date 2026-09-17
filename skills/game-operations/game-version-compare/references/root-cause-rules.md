# Root-cause Diagnosis Rule Table and Confidence-level Standard

Inference rules and confidence-level grading criteria for Step 7 (root-cause diagnosis).

## Core Principle

Root-cause diagnosis is **heuristic inference, not causal proof**. The deliverable is "a candidate explanation that needs further verification", not "a confirmed conclusion".

> ⚠️ "Confidence level" refers to the reliability of the inference, **NOT statistical confidence/significance**. It is not a p-value, not a confidence interval, but a subjective grading of how well the inference holds up. The term "statistical confidence" is deliberately avoided to prevent confusion with statistics.

## Change-impact Inference Rule Table

| Observed difference pattern | Inferred version cause | Confidence | Note |
|------|------|------|------|
| High new-feature penetration + users' retention significantly higher than non-users | The new feature is accepted and has a positive pull (goal A) | High | Rule out the selection bias that "highly active users were already more likely to use it" |
| Retention ↓ + a new system/module was added | Learning-curve friction from new content (goal B) | Medium | Check whether it is an intentional increase in new-user difficulty |
| Payment ↑ + new gift pack / repricing, and ARPPU did not drop | Monetization improvement (goal C) | High | Confirm the gift pack is the only change; watch for squeezing high-value payment |
| Payment rate ↑ but ARPPU ↓ | Low-value payment expansion, squeezing high-value (goal C) | Medium | Look at the payment depth distribution; not necessarily a net positive |
| Level churn at the patched level ↑ + numeric patch | Difficulty spike from rebalancing (goal E) | High | Confirm the patch actually touched that level |
| Crash rate / load duration ↓ + retention / duration ↑ | Performance optimization took effect (goal D) | High | Focus on whether low/mid-end devices improved |
| DAU ↑ but payment rate ↓ | User-quality drift (broader reach) | Medium | Could be acquisition-mix change, not the version |
| Node churn ↓ + a new recall/return feature was added | Recall mechanism took effect (goal B) | High | Confirm the feature is in this version |
| Behavior barely changed + major visual redesign | Purely cosmetic, low behavior impact | Low | May need a longer observation window |
| Retention ↓ + holiday end / big-push end within the same window | Seasonal or operational rhythm, not the version | High | Confounding factor - do not credit the version |

## Confidence-level Grading Criteria

Grade by **two negative conditions**:

1. **Is it "singular and clear"**: can only one change explain this difference? (If 5 things changed at once, it is impossible to say which one, so it must be downgraded.)
2. **Are there confounding factors**: season, holidays, channel-mix change, campaigns, or selection bias interference?

| Confidence | Grading rule | Next step |
|--------|---------|--------|
| High | A singular clear change matches the difference, and there are no confounding factors | Can act on it (rollback / tune parameters) |
| Medium | There is a reasonable association, or slight confounding factors exist | Verify before acting |
| Low | Signal is weak/ambiguous | Do qualitative research or extend the observation period |

## Distinguish the Two Judgment Axes

- **Correlation**: whether the data difference is real and significant (e.g. a retention difference of 74% vs 40% is certain)
- **Causation**: whether this difference is caused by the version change (it may be polluted by selection bias)

The two are independent. Example: users who added friends retain significantly higher than those who did not, so the **"correlation" confidence is high**, but the **"causation" (the social feature drove the retention lift) confidence is low** — because people who proactively add friends are inherently more active (selection bias). In the report, label them separately; do not collapse them into a single "high confidence" statement.

## Confounding Factor Checklist (check each one)

- Seasonality / holidays
- Marketing peak / heavy promotion
- Competitor moves
- Channel-mix change
- Data latency
- Selection bias (users who proactively update are inherently more active)

When the dual approach (time + cohort) conclusions agree, it is more trustworthy; when they conflict, **prioritize suspecting approach interference over version effect**. When possible, verify with A/B testing or a holdout retention cohort.
