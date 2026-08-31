# Step 3: Score Calculation

## Objective

Based on the raw data collected in Step 2, calculate each dimension score and the composite total score according to the scoring rules.

## Prerequisites

- `raw_data` produced by Step 2, with per-metric sample-size labels from Step 2.6.
- `scoring_rules` and `weights` loaded in Step 1 phase B and passed through Step 2 — use them directly; do not re-read config files.

## Input

- `raw_data`: per-dimension raw values, `drama_type`, episode list, missing-dimension list.
- `scoring_rules`: per-metric piecewise linear tiers + `grade_definitions`.
- `weights`: per-dimension weights (possibly overridden by the user).

## ⚠️ Key Principles

- **Do not re-read config files.** `scoring_rules` and `weights` were loaded in Step 1 phase B and passed through Step 2; use them directly. Do not re-read references/config/*.yaml.
- **The calculation runs silently.** No need to tell the user "calculating dimension X" step by step; present the results directly once done.

## Execution Instructions

### 3.1 Confirm Scoring Rules

Use the `scoring_rules` variable passed from Step 1/2 directly:
- The scoring thresholds for the current drama type (`drama_type`) were already determined in B.1
- If it is `private_platform` with `_inherit` configured, the inherited type's rules are already in effect
- No need to re-read `references/config/scoring_rules.yaml`

### 3.2 Per-Metric Normalization

For each metric value in `raw_data`, normalize then apply the piecewise linear mapping:

```
function normalize(raw_value, tiers):
    # 1. clamp to the metric domain
    value = clamp(raw_value, tiers[0].range[0], tiers[-1].range[1])
    # 2. round to the nearest integer (0.5 rounds up) so it matches exactly one tier
    value = round_half_up(value)
    # 3. find the matching tier and map linearly
    for each tier in tiers:
        [range_min, range_max] = tier.range
        [score_min, score_max] = tier.score
        if range_min <= value <= range_max:
            if range_min == range_max:      # point tier: constant score, no division
                return score_min
            score = score_min + (value - range_min) / (range_max - range_min) * (score_max - score_min)
            return clamp(score, 0, 100)
    # unreachable: steps 1+2 guarantee value is inside the metric domain
    return tiers[-1].score[1]
```

**Note: reverse-metric handling**
Some metrics are better when lower (e.g. `cliffhanger_failure_rate`, `churn_point_distribution`).
In `scoring_rules.yaml`, the tiers for these metrics use DESCENDING score ranges (score_min > score_max), so the unified formula yields a negative slope directly. Do not invert the score direction a second time.

### 3.3 Compute Per-Dimension Scores

Compute according to the sub-metric weight rules for each dimension in `references/dimension_details.md`.

**Missing sub-metric rule**: when a sub-metric is missing (insufficient data), drop it and re-normalize the remaining sub-metric weights proportionally so they sum to 1, then compute the dimension score from the remaining sub-metrics. Mark the dropped sub-metric N/A in the report. If ALL sub-metrics of a dimension are missing, mark the whole dimension N/A (excluded from the total; its dimension weight is reallocated in 3.4).

#### Dimension 1: First-Episode Appeal
```
score_d1 = (first_episode_click_to_play_rate_score 
         + first_episode_completion_rate_score 
         + ep1_to_ep2_rate_score) / 3
```

#### Dimension 2: Completion Quality
```
avg_completion_score = mean(per-episode completion rate scores)
segmented_score = segmented_completion_rate_score
score_d2 = avg_completion_score × 0.7 + segmented_score × 0.3

# stability deduction
if std(per-episode completion rate scores) > 15:
    score_d2 = max(0, score_d2 - 5)
```

#### Dimension 3: In-Episode Pacing
```
score_d3 = (retention_at_25pct_score + retention_at_50pct_score 
         + retention_at_75pct_score + retention_at_100pct_score) / 4
```

#### Dimension 4: Cliffhanger Effect
```
score_d4 = episode_end_jump_rate_score × 0.4 
         + cliffhanger_5s_jump_rate_score × 0.4 
         + cliffhanger_failure_rate_score × 0.2
```

#### Dimension 5: Inter-Episode Retention
```
avg_jump_score = mean(per-inter-episode jump rate scores)
score_d5 = next_day_retention_score × 0.3 
         + avg_jump_score × 0.4 
         + churn_point_distribution_score × 0.3
```

#### Dimension 6: Binge Depth
```
score_d6 = binge_3plus_rate_score × 0.6 + binge_median_episodes_score × 0.4
```

#### Dimension 7: Payment Conversion
```
score_d7 = payment_trigger_rate_score × 0.6 + post_payment_watch_rate_score × 0.4
```

#### Dimension 8: Heat Trend
```
score_d8 = daily_avg_play_count_score × 0.3 
         + new_user_ratio_score × 0.3 
         + play_peak_count_score × 0.4
```

#### Dimension 9: User Engagement
```
score_d9 = like_rate_score × 0.3 + comment_rate_score × 0.3 + share_rate_score × 0.4
```

### 3.4 Compute the Composite Total Score

```
total_score = 0
total_weight = 0
scoring_dimensions = dimensions enabled in config AND selected by the user at Checkpoint 1

for each dimension in all 9 dimensions:
    dimension.configured_weight = dimension.weight
    if dimension not in scoring_dimensions:
        dimension.score = "Not scored"
        dimension.effective_weight = 0
        dimension.status = "⚪ Not scored"
    elif dimension has valid score:
        total_score += dimension.score × dimension.weight
        total_weight += dimension.weight

# if all dimensions are missing (extreme case)
if total_weight == 0:
    report error: "All dimension data is unavailable; scoring is not possible."

# otherwise, handle missing dimensions by reallocating weights proportionally
for each dimension in all 9 dimensions:
    if dimension in scoring_dimensions AND dimension has valid score:
        dimension.effective_weight = dimension.configured_weight / total_weight × 100
        if dimension.score < 40: dimension.status = "🔴"
        elif dimension.score <= 55: dimension.status = "🟡"
        else: dimension.status = "🟢"
    elif dimension in scoring_dimensions:
        dimension.score = "N/A"
        dimension.effective_weight = 0
        dimension.status = "⚪ N/A"
    else:
        dimension.effective_weight = 0

total_score = total_score / total_weight
```

`configured_weight` is the user-configured/default weight before scope selection and missing-data handling. `effective_weight` is the normalized weight that actually contributes to the total score. The scorecard MUST display `effective_weight`; a missing or user-excluded dimension displays `0%`. Preserve full precision internally. For display, round effective weights to at most two decimals and assign any rounding residual to the last valid dimension so the displayed effective weights sum to exactly 100%. Data Notes may additionally state excluded configured weights for traceability.

### 3.5 Determine the Grade

Read the grade definitions from `scoring_rules.grade_definitions` (the sole authoritative source), match the current `total_score` against `score_range`, and obtain grade, label, action. **Do not hardcode thresholds.**

```
for each grade_def in scoring_rules.grade_definitions:
    if grade_def.score_range[0] <= total_score <= grade_def.score_range[1]:
        grade = grade_def.grade
        grade_label = grade_def.label
        grade_action = grade_def.action
        break
```

### 3.6 Generate Per-Episode Heatmap Data

Compute the following dimension scores independently for each episode:

```
for each episode in actual_episodes:
    heatmap[episode]["completion_quality"] = normalize_episode_completion_rate(episode)
    heatmap[episode]["episode_pacing"] = normalize_episode_pacing(episode)
    heatmap[episode]["cliffhanger_effect"] = normalize_episode_cliffhanger(episode)
    # inter-episode retention is recorded on the episode_i → episode_i+1 transition
    if episode has next episode:
        heatmap[episode]["inter_episode_retention"] = normalize_inter_episode_jump(episode, episode+1)
```

### 3.7 Output the Score Data Structure

Pass the following structured data to Step 4 (when diagnosis runs) and Step 5:

```
score_data:
  drama_name: "{drama_name}"
  drama_type: "{drama_type}"
  total_score: {value}
  grade: "{grade}"
  grade_label: "{grade label}"
  grade_action: "{suggested action}"
  dimension_scores:
    first_episode_appeal: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
    completion_quality: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
    episode_pacing: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
    cliffhanger_effect: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
    inter_episode_retention: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
    binge_depth: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
    payment_conversion: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
    heat_trend: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
    user_engagement: {score: "XX, N/A, or Not scored", configured_weight: XX, effective_weight: XX, status: "🟢/🟡/🔴/⚪ N/A/⚪ Not scored"}
  missing_dimensions: ["{list of missing dimensions}"]
  excluded_dimensions:
    - dimension: "{dimension not in scoring_dimensions}"
      reason: "disabled_in_config or user_excluded"
  heatmap:
    - episode: 1
      completion_quality: XX
      episode_pacing: XX
      cliffhanger_effect: XX
      inter_episode_retention: XX  # retention of 1→2
    - episode: 2
      ...
  raw_data: {reference to Step 2 raw data}
```

### 3.8 Scoring Complete → Interaction Checkpoint (mandatory)

**After the score calculation completes, immediately show the scorecard and heatmap to the user so they can digest the core conclusions before deciding whether to run deep diagnosis.**

Output the score summary to the user (not the full report yet, only the two core sections; translate to Chinese per the Language Convention):

Use the same display semantics as the final report: valid dimensions show a numeric score and status; missing dimensions show `N/A` / `⚪ N/A`; dimensions disabled in config or excluded by the user show `Not scored` / `⚪ Not scored`. Both non-numeric cases use `—` instead of a progress bar.

```
📊 Scoring complete!

┌────────────────────────────────────────────┐
│                                            │
│  《{drama_name}》 total score: {total_score}/100 │
│  Grade: ⭐{grade} — {grade_label}          │
│                                            │
│  First-Episode Appeal   ████████░░  {d1}  🟢 │
│  Completion Quality     ███████░░░  {d2}  🟢 │
│  In-Episode Pacing      ██████░░░░  {d3}  🟡 │
│  Cliffhanger Effect     ████████░░  {d4}  🟢 │
│  Inter-Episode Retention ████████░░  {d5}  🟢 │
│  Binge Depth            ███████░░░  {d6}  🟢 │
│  Payment Conversion     ████████░░  {d7}  🟢 │
│  Heat Trend             █████████░  {d8}  🟢 │
│  User Engagement        ██████░░░░  {d9}  🟡 │
│                                            │
│  🔥 Anomalous episodes:                    │
│  {if any:}                                 │
│  🔴 Episode 3 — completion & pacing both low │
│  🟡 Episodes 7-9 — cliffhanger effect declining │
│  {if none:}                                │
│  even across episodes; no significant anomalies │
│                                            │
│  ⏱️  Scoring time: {elapsed_time}           │
│                                            │
└────────────────────────────────────────────┘

The scorecard and heatmap now answer "overall quality + problem-episode location". Next:

A) 🔍 Deep diagnosis — AI analyzes root causes and suggests optimizations (est. {estimated_time})
B) 📝 Direct report — generate the report from current scores, skipping diagnosis
C) 🔎 Inspect an episode — dig into the underlying data of a specific episode

Which one?
```

**Interaction rules:**
- If the score > 70 with no anomalous episodes, you may remind the user "this drama performs well and the marginal benefit of deep diagnosis may be limited"
- If the score <= 55 or there are 🔴 anomalous episodes, strongly suggest option A "deep diagnosis" to locate root causes
- When the user chooses B, skip Step 4 and go directly to Step 5. Generate the same five-section report, with explicit skip notes in the diagnosis and optimization sections.
- When the user chooses C, enter interactive mode and show that episode's detailed underlying data (pacing curve, drop-off points, etc.); after showing, return to this checkpoint's A/B/C options and continue, without hanging
- **Must wait for the user's explicit choice before proceeding**

## Output

- `score_data`: the full score structure defined in 3.7 (total score, grade, all nine dimension entries with configured/effective weights, heatmap, missing dimensions, and non-scoring dimensions with exclusion reasons).

## Verification (result validation)

After computing the total score and heatmap, validate the results before presenting them:

- [ ] Total score ∈ [0, 100] and every valid numeric dimension score ∈ [0, 100]; missing/user-excluded dimensions are non-numeric.
- [ ] Σ(`effective_weight`) across valid dimensions = 100; every missing or user-excluded dimension has `effective_weight = 0`.
- [ ] Missing and user-excluded dimensions were excluded and valid configured weights were reallocated proportionally (3.4), not double-counted.
- [ ] Grade matches `score_range` in `scoring_rules.grade_definitions` — no hardcoded threshold was used.
- [ ] Reverse metrics (`cliffhanger_failure_rate`, `churn_point_distribution`) yield higher scores for lower raw values, per their reverse tiers.
- [ ] Spot-check one dimension: recompute its score from the raw value independently and confirm it equals the computed score.
- [ ] Heatmap rows cover every episode in `{target_episodes}` with no gaps or duplicates.
