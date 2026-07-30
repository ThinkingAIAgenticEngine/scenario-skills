# Drama Type Adaptation Decision Table — Short Drama (3 Types)

> This file is the **single source of drama type parameter adaptation**. Before Step 2, load the corresponding parameters from this table based on the user's input drama type.
> Does not cover horizontal long dramas — this skill only analyzes short dramas.

---

## Supported Drama Types Overview

| Drama Type | Typical Episodes | Per-Episode Duration | Total Duration | Typical Paywall Position | D1 Desensitization Required |
|------------|-----------------|----------------------|----------------|------------------------|---------------------------|
| Vertical short drama | 60-100 episodes | 3-8 min | 3-8 hours | Episodes 20-40 | **Conditional** (see §1) |
| Mini-program drama | 80-120 episodes | 1-3 min | 2-4 hours | Episodes 20-30 | **Mandatory** (same as vertical micro-short) |
| Vertical micro-short drama | 8-30 episodes | 1-3 min | 0.5-1.5 hours | Episodes 5-15 (if any) | **Mandatory** (see §3) |

---

## § 1 Vertical Short Drama

### Threshold Parameters

| Metric | Pass Line | Excellent Line | Notes |
|--------|-----------|---------------|-------|
| Start-play rate | ≥40% | ≥60% | Click-based |
| E1 completion rate | ≥70% | ≥85% | |
| E2 completion rate | ≥65% | ≥78% | |
| 3-episode retention | ≥35% | ≥50% | Industry golden standard dividing line |
| 7-episode retention | ≥20% | ≥35% | |
| Full-drama retention | ≥12% | ≥20% | |
| Abandonment rate | <70% | <50% | |
| Paywall reach rate | ≥40% | ≥60% | |
| D1 retention | ≥20% | ≥35% | |
| 7-day user re-engagement rate | ≥15% | ≥25% | |
| 30-day platform revisit rate | ≥8% | ≥15% | |
| Cross-drama transition rate | ≥5% | ≥12% | |

### D1 Desensitization Rule

Vertical short drama: 3-8 min/episode, 60-100 episodes, total 3-8 hours. Most users **cannot** finish the entire drama on Day0 (especially paid dramas).

- **Normal case**: D1 retention is used normally, no desensitization needed
- **Desensitization trigger condition**: All episodes released at once (non-continuous update) AND same-day cross-drama viewing rate ≥15%
- **Desensitization method**: Also report "same-day cross-drama viewing rate"; if ≥15%, supplement with "non-completer D1 retention"

### Segment Definition

| Segment Name | Episode Range | Notes |
|--------------|---------------|-------|
| Opening segment | E1-E3 | Opening hook zone |
| Middle segment | E4 to E{paywall-1} | Free buildup zone |
| Paywall segment | E{paywall}±1 episode | Core commercialization checkpoint |
| Post-paywall segment | E{paywall+1} to last 6 episodes | Paid user retention zone |
| Finale segment | Last 5 episodes | Ending quality |

---

## § 2 Mini-Program Drama

### Threshold Parameters

| Metric | Pass Line | Excellent Line | Notes |
|--------|-----------|---------------|-------|
| Start-play rate | ≥35% | ≥55% | Mini-program entry friction slightly higher |
| E1 completion rate | ≥65% | ≥80% | |
| E2 completion rate | ≥60% | ≥75% | |
| 3-episode retention | ≥30% | ≥45% | Mini-program slightly lower than vertical benchmark |
| 7-episode retention | ≥18% | ≥30% | |
| Full-drama retention | ≥10% | ≥18% | |
| Abandonment rate | <75% | <55% | |
| Paywall reach rate | ≥35% | ≥55% | |
| D1 retention | ≥18% | ≥30% | |

### D1 Desensitization Rule

Mini-program drama: 1-3 min/episode, 80-120 episodes, theoretically finishable in 2-4 hours. **Must check same-day cross-drama viewing rate**.

- Same-day cross-drama viewing rate ≥15%: Low D1 is due to consumption completion; supplement with "non-completer D1 retention" as traffic quality indicator
- Mini-program drama also needs additional attention to **mini-program open rate** (whether users are lost within the mini-program framework)

### Segment Definition

Same as vertical short drama (see §1), but paywall position reference range adjusted to episodes 20-30.

---

## § 3 Vertical Micro-Short Drama

> The most special drama type. Extremely short per-episode, entire drama can be finished same-day. D1 desensitization is a **mandatory prerequisite step**.

### Threshold Parameters

| Metric | Pass Line | Excellent Line | Notes |
|--------|-----------|---------------|-------|
| Start-play rate | ≥45% | ≥65% | Micro-short drama users decide fast |
| E1 completion rate | ≥75% | ≥90% | Episodes very short, completion threshold low |
| E2 completion rate | ≥68% | ≥82% | |
| 3-episode retention | ≥40% | ≥58% | Micro-short drama golden standard higher |
| Full-drama retention | ≥15% | ≥25% | Fewer episodes, higher benchmark |
| Abandonment rate | <65% | <45% | |
| Paywall reach rate | ≥45% | ≥65% | |
| D1 retention | ≥15% (desensitized) | ≥28% | Raw D1 may be low due to same-day completion, must desensitize |
| 7-day user re-engagement rate | ≥12% | ≥22% | |

### D1 Desensitization Rule (Mandatory)

Vertical micro-short drama (1-3 min/episode, 8-30 episodes). **Users can finish the entire drama on the same day**. Users who finish same-day have no reason to return on Day1 — this is not churn, it is consumption completion.

**Mandatory execution steps**:

1. Calculate **same-day cross-drama viewing rate**: `Day0 users who finished this drama AND watched other short dramas on the same Day0 / Day0 total`
2. Judge:
   - Same-day cross-drama viewing rate **≥15%** AND D1 low → D1 is suppressed by consumption completion, **does not indicate poor traffic quality**. Use **non-completer D1 retention** as the traffic quality basis
   - Same-day cross-drama viewing rate **<15%** AND D1 low → Traffic quality may have issues, trigger R1-3 rule
3. Report must show all three: raw D1, same-day cross-drama viewing rate, non-completer D1 retention

> Metric rationale: Same-day cross-drama viewing rate measures users' sustained consumption willingness for the short-drama category (traffic quality), not this drama's content quality. Using it to desensitize D1 separates traffic issues from content issues.

### Segment Definition (Small Episode Count Adjustment)

| Segment Name | Episode Range (Example: 20-episode drama) | Notes |
|--------------|------------------------------------------|-------|
| Opening segment | E1-E3 | Fixed, regardless of episode count |
| Middle segment | E4 to E{paywall-1} | If paywall at episode 12: E4-E11 |
| Paywall segment | E{paywall}±1 episode | |
| Post-paywall segment | E{paywall+1} to last 3 episodes | Before finale segment |
| Finale segment | Last 3 episodes (≤20-episode dramas) | Reduced to 3 episodes for small-count dramas |

**3-episode retention context label**: If total episodes ≤15, label in report: "3-episode retention = {3/total×100}% progress of full drama", noting that the meaning differs from longer dramas.

### Paywall Position Range

Vertical micro-short drama paywall recommended position: episodes at `total_episodes × 50%` to `total_episodes × 70%` (reference ratio, not hard rule). If paywall is in the first 30% of episodes, trigger R4-1 rule.

---

## Quick Lookup Table

| User Description | Corresponding Drama Type | Key Differences |
|-----------------|--------------------------|-----------------|
| "5 min/episode, 80 episodes" | Vertical short drama | D1 usually no desensitization needed |
| "WeChat mini-program drama, 2 min/episode, 100 episodes" | Mini-program drama | D1 mandatory check, watch mini-program open rate |
| "Vertical short video format, 8 episodes, 1 min/episode" | Vertical micro-short drama | D1 mandatory desensitization, 3-episode retention context needs labeling |
| "1-3 min/episode, 20-30 episodes" | Vertical micro-short drama | Same as above |
