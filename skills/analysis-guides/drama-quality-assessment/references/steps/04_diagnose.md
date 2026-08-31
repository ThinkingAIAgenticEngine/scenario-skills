# Step 4: Diagnosis

## Objective

Based on Step 3's score data and heatmap, perform AI-driven anomaly detection, pattern attribution, and optimization-suggestion generation.

## Prerequisites

- `score_data` produced by Step 3 (dimension scores, grade, heatmap, `missing_dimensions`, `raw_data` reference).
- `references/anomaly_patterns.md` is available for pattern matching (read it in 4.1).
- The user has chosen "deep diagnosis" at Checkpoint 2; otherwise skip this step and go to Step 5.

## Input

- `score_data`: total score, grade, all nine dimension entries (numeric 0-100, `N/A`, or `Not scored`) with status, per-episode heatmap, missing-dimension list, and non-scoring dimensions with exclusion reasons.
- `raw_data`: reference to Step 2 raw query results (used as evidence for root causes).

## Execution Instructions

### 4.1 Read the Anomaly Pattern Library

Read `references/anomaly_patterns.md` and load the full descriptions of the 12 anomaly/opportunity patterns for subsequent pattern matching.

### 4.2 Anomaly Detection

#### 4.2.1 Dimension-Level Anomalies

Iterate all dimension scores and mark the anomaly level:

```
for each dimension in score_data.dimension_scores:
    if dimension.score is N/A or Not scored: retain its existing ⚪ status and exclude from anomaly detection
    elif dimension.score < 40: mark as 🔴 severe problem
    elif dimension.score <= 55: mark as 🟡 needs attention
    else: mark as 🟢 normal
```

#### 4.2.2 Per-Episode Anomalies

Iterate the heatmap data and detect anomalous episodes:

**Rule A - cliff detection:**
```
for each episode i (except episode 1):
    for each metric in heatmap[i]:
        delta = heatmap[i][metric] - heatmap[i-1][metric]
        if delta < -20:  # dropped more than 20 points vs. the previous episode
            mark episode i's metric as 🔴 anomalous
```

**Rule B - trend decline:**
```
for each metric:
    check if 3+ consecutive episodes decline continuously (each episode drops > 0):
        mark that metric as 🟡 trend decline
```

**Rule C - cross-episode comparison anomaly:**
```
for each episode i:
    if a dimension score of episode i < (mean of that dimension across all episodes - 1.5 × stddev):
        mark that episode's dimension as 🔴 outlier
```

### 4.3 Pattern Matching

Match the detected anomalies against the patterns in `references/anomaly_patterns.md`:

**Matching logic:**
```
1. Collect all anomaly signals
2. Compare characteristics against the 12 patterns one by one
3. For each matched pattern, record:
   - pattern name and severity level
   - the concrete matching evidence (which data points triggered the pattern)
   - the recommended root cause and diagnostic wording
4. If the same anomaly matches multiple patterns, choose the most specific one (best-matching characteristics)
```

**Pattern-matching priority:**
1. Match precise patterns first (Cliff Episode, Pacing Collapse Episode, Cliffhanger Failure Episode, Payment Friction Episode)
2. Then match trend patterns (Weak Opening, Mid-Series Fatigue, Late-Series Collapse, High Open Low Finish, Binge Break)
3. Finally identify opportunity signals (Word-of-Mouth Effect, Payment Sweet Spot, Counter-Trend Upturn)

### 4.4 Cross-Validate Root Causes

When an anomaly is detected, cross-validate with data from other dimensions:

**Example cross-validation logic:**

| Anomaly Signal | Cross-Validation Method |
|---------|------------|
| Low completion rate of an episode | Check that episode's pacing curve → locate the specific drop-off position |
| Low inter-episode jump rate | Check the previous episode's cliffhanger effect → judge whether it is a hook or content problem |
| Low payment conversion | Check completion rates around the paywall → judge whether it is a price barrier or insufficient content appeal |
| Low binge depth | Check inter-episode retention and cliffhanger effect → locate whether it is inter-episode coherence or single-episode problems |

### 4.5 Generate Diagnostic Insights

Based on the analysis above, generate a natural-language diagnosis report with the following structure:

```
🔍 Diagnosis

📋 Overall assessment:
{1-2 sentences summarizing the drama's overall performance and positioning}

{If anomalies are found:}

⚠️ N issues found:

1. 🔴/🟠/🟡 [Pattern name] (episodes X~Y)
   - Data evidence: {concrete numbers}
   - Root-cause hypothesis: {cross-validated root-cause analysis}
   - Impact scope: {which downstream metrics are affected}

2. {next issue...}

{If all dimensions are normal:}
The drama performs evenly across dimensions; no significant anomalies found.

{If opportunity signals are found:}
🌟 Positive signals:
1. [Pattern name]: {data evidence}
```

### 4.6 Generate Optimization Suggestions

Based on the diagnostic conclusions, generate optimization suggestions sorted by priority:

```
💡 Optimization suggestions

Priority levels:
- [Urgent] = affects business results (payment conversion, large-scale churn)
- [Important] = affects user retention and experience
- [Suggested] = incremental improvement

Per-suggestion format:
[Priority label] Episodes X-Y: {concrete action suggestion}
  - Current issue: {one-line description}
  - Expected effect: {which metric is expected to improve}
```

**Suggestion-generation principles:**
- Suggestions must be based on actual data; never fabricate suggestions
- Suggestions must be concrete down to episode numbers and action direction (e.g. "re-cut the middle of episode 3", "redesign the ending hook of episode 8")
- Prioritize content-side suggestions (more actionable), then operations-side suggestions
- If the data is insufficient to support concrete suggestions, state honestly "the data is insufficient to pinpoint the specific problem; suggest further analysis of XX data"

## Output

Pass the following structured data to Step 5:

```
diagnosis_data:
  anomalies:
    - type: "{pattern name}"
      severity: "🔴/🟠/🟡"
      episodes: [X, Y]
      description: "{diagnostic wording}"
      evidence: "{data evidence}"
      root_cause: "{root-cause hypothesis}"
  positive_signals:
    - type: "{pattern name}"
      evidence: "{data evidence}"
  recommendations:
    - priority: "urgent/important/suggested"
      episodes: [X, Y]
      action: "{concrete action suggestion}"
      current_issue: "{current problem}"
      expected_effect: "{expected effect}"
  narrative_summary: "{1-2 sentence overall assessment}"
```

## Verification

Before passing `diagnosis_data` to Step 5, self-check:

- [ ] Every `anomaly` entry has non-empty `evidence` that traces back to `raw_data` (no fabricated numbers).
- [ ] Every `anomaly` is matched to a specific pattern from `anomaly_patterns.md`, and the severity matches the pattern's level.
- [ ] Each `recommendation` references concrete episode numbers and an actionable direction (not generic advice).
- [ ] The number of issues/signals is consistent with the 🔴/🟡 counts from Step 3's scorecard and heatmap.
- [ ] If data is insufficient for a conclusion, the wording honestly states so instead of guessing.
