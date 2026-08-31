# Dimension Details and Calculation Formulas

> This document defines the calculation method and scoring logic for each dimension, for the Agent to reference during Step 3 score calculation.

---

## 1. Linear Mapping Formula

All metrics use the same piecewise linear mapping formula:

```
score = score_min + (value - range_min) / (range_max - range_min) × (score_max - score_min)
```

Where `range_min`/`range_max`/`score_min`/`score_max` come from the `tiers` config of the corresponding metric and drama type in `references/config/scoring_rules.yaml`.

**Before matching, normalize the raw value (see the conventions at the top of scoring_rules.yaml):**

1. `value = clamp(raw_value, first_tier.range_min, last_tier.range_max)` — clamp to the metric's full domain.
2. `value = round_half_up(value)` — round to the nearest integer (0.5 rounds up), so every real value matches exactly one tier.
3. Find the tier whose integer range contains `value`.
4. **Point tier** (`range_min == range_max`): return the constant `score_min` directly, no division.
5. **Reverse metric** (`cliffhanger_failure_rate`, `churn_point_distribution`): the tiers use descending score ranges, so the same formula yields a negative slope — do not invert anything manually.

**Calculation example:**
Vertical mini-drama first-episode completion rate = 42%
→ falls in tier 2: [31, 50] → [31, 60]
→ score = 31 + (42 - 31) / (50 - 31) × (60 - 31) = 31 + 11/19 × 29 = 31 + 16.8 = 47.8

---

## 2. Dimension Scoring Rules

### Scoring flow for each dimension:

1. **Per-metric scoring**: apply linear mapping to every metric under the dimension to obtain each metric's score
2. **Weighted combination**: dimension score = Σ(sub-metric score × sub-metric weight). Sub-metric weights come from each dimension's formula below (e.g. Dimension 4: 0.4 / 0.4 / 0.2); equal weight by default where no explicit weights are given.
3. **Missing sub-metric**: drop the missing sub-metric and re-normalize the remaining weights to sum to 1; mark the dropped sub-metric N/A in the report. Only when ALL sub-metrics are missing is the whole dimension N/A (its dimension-level weight is then reallocated in Step 3.4).
4. **Anomaly marking**:
   - dimension score < 40 → 🔴 severe problem
   - dimension score 40-55 → 🟡 needs attention
   - dimension score > 55 → 🟢 normal

### Special handling rules per dimension:

#### Dimension 1: First-Episode Appeal
```
dimension score = (first-episode click-to-play conversion score + first-episode completion rate score + 1→2 episode jump rate score) / 3
```
- If the 1→2 episode jump rate score is 20+ points lower than the first-episode completion rate score, it means "the first episode is decent but fails to retain viewers"; flag this specifically in the diagnosis.

#### Dimension 2: Completion Quality
```
dimension score = (mean of per-episode completion rate scores × 0.7 + time-segmented completion trend score × 0.3)
```
- If the standard deviation of per-episode completion rates > 15, quality is unstable; deduct an extra 5 points.

#### Dimension 3: In-Episode Pacing
```
dimension score = (25% retention score + 50% retention score + 75% retention score + 100% retention score) / 4
```
- The "steepness" of the progress retention curve is the diagnostic focus:
  - 25%→50% loss > 15% → insufficient content appeal after the opening
  - 50%→75% loss > 10% → pacing problem in the middle segment
  - 75%→100% loss < 5% → the ending hook works (a positive signal)
- High-churn positions are located via event-detail query, used only for Step 4 diagnosis, not counted into the Dimension 3 score.

#### Dimension 4: Cliffhanger Effect
```
dimension score = (episode-end jump rate score × 0.4 + 5s cliffhanger jump rate score × 0.4 + cliffhanger failure ratio score × 0.2)
```
- The 5s cliffhanger jump rate carries the highest weight because it best reflects "whether the hook is strong enough".

#### Dimension 5: Inter-Episode Retention
```
dimension score = (next-day retention score × 0.3 + mean inter-episode jump rate score × 0.4 + churn concentration score × 0.3)
```
- Trend analysis of per-episode jump rates:
  - first 5 episodes jump rate consistently > 60% → strong user stickiness
  - sudden drop in the middle → plot turn or pacing problem
  - recovery at the end → driven by ending anticipation

#### Dimension 6: Binge Depth
```
dimension score = (binge ≥3 episodes ratio score × 0.6 + binge median score × 0.4)
```
- The binge ≥3 episodes ratio is the most critical metric for measuring the "hooked" index.

#### Dimension 7: Payment Conversion
```
dimension score = (payment trigger rate score × 0.6 + post-payment watch rate score × 0.4)
```
- A low post-payment watch rate (< 60 points) means "poor payment experience"; diagnose whether it is a price or content problem.

#### Dimension 8: Heat Trend
```
dimension score = (daily average plays score × 0.3 + new-user ratio score × 0.3 + play peak score × 0.4)
```
- Heat trend is not a direct content-quality metric, but reflects dissemination capability.

#### Dimension 9: User Engagement
```
dimension score = (like rate score × 0.3 + comment rate score × 0.3 + share rate score × 0.4)
```
- Share rate best reflects "whether users proactively spread the content", so its weight is slightly higher.

---

## 3. Total Score Calculation

```
total score = Σ(dimension score × dimension weight) / 100
```

Dimension weights come from `references/config/dimensions.yaml`, defaults:
```
First-Episode Appeal(15) + Completion Quality(10) + In-Episode Pacing(10) + Cliffhanger Effect(15)
+ Inter-Episode Retention(15) + Binge Depth(10) + Payment Conversion(15) + Heat Trend(5) + User Engagement(5)
= 100
```

---

## 4. Grade Determination

Grade thresholds come solely and authoritatively from `grade_definitions` in `references/config/scoring_rules.yaml` (five tiers: S/A/B/C/D). Step 3 reads from that config and does not redefine them here.

---

## 5. Per-Episode Heatmap Data

Independently compute the following dimension scores per episode (only applicable to dimensions that can be split by episode):

| Dimension | Per-Episode | Notes |
|------|:---:|------|
| First-Episode Appeal | ❌ | Episode 1 only |
| Completion Quality | ✅ | Independent per episode |
| In-Episode Pacing | ✅ | Independent per episode |
| Cliffhanger Effect | ✅ | Independent per episode |
| Inter-Episode Retention | ✅ | Transition between each pair of episodes |
| Binge Depth | ❌ | Overall metric |
| Payment Conversion | ❌ | Near the paywall only |
| Heat Trend | ❌ | Overall metric |
| User Engagement | ❌ | Overall metric, not shown per episode in the heatmap |

Heatmap "composite score" = equal-weight mean of the available dimension scores for that episode (averaged only over dimensions that can be split by episode).

Heatmap anomaly marking rules:
- An episode's dimension score is 20+ points lower than the same dimension of adjacent episodes → 🔴 mark as an anomalous episode
- A dimension declines continuously across 3+ consecutive episodes → 🟡 mark as a trend decline
