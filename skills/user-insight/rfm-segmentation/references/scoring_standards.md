# RFM Scoring Standards

> Canonical rules for Stage 4–5. Concrete thresholds are runtime values; never hardcode project-specific numbers here.

## 1. Resolution-first scoring design

### 1.1 Hard priority order

Use this priority whenever granularity and ties conflict:

```text
same raw value → same score band
  > preserve each metric's usable resolution
  > operational actionability/readability
  > uniform band count across R/F/M
  > equal population per band
```

**Hard rule:** never split identical raw values across score bands solely to hit quantile targets or equalize counts.

### 1.2 Per-metric band metadata

Band count belongs to each metric, not to the RFM model as a whole.

For each of R, F, and `M_scoring`, record:

| Field | Meaning |
| --- | --- |
| `requested_bands` | Intended maximum granularity before tie-resolution |
| `effective_bands` | Actual non-empty score bands after tie-aware boundary construction |
| `adjustment_reason` | Why `effective_bands < requested_bands`, when applicable |
| `score_direction` | R: lower raw value is better; F/M: higher raw value is better |

Also record a compact runtime profile, for example:

```text
band_profile = R5-F3-M5
```

A profile such as `R5-F3-M5` is a normal outcome when F is highly discrete but R/M retain enough resolution. It does **not** require special business approval merely because the effective band counts differ.

### 1.3 Choosing requested granularity

There is no universal sample-size cutoff. User count is only a supporting signal.

| Prefer requested 3-band when | Prefer requested 5-band when |
| --- | --- |
| The metric has low effective cardinality or severe ties | The metric has enough distinct values/gaps to support five meaningful bands |
| Extra raw-score granularity has no operational use | Fine ranking or differentiated treatment has a clear use |
| Expected score cells would be too small/noisy | Bands remain stable and interpretable |
| Simpler scoring is easier to explain/maintain | Additional granularity materially helps prioritization |

Inspect per metric:

- [ ] `COUNT(DISTINCT metric)`
- [ ] effective cardinality
- [ ] top tie concentration
- [ ] zero mass
- [ ] candidate cutoff gaps
- [ ] minimum expected band size
- [ ] downstream operational need

Do not use a mechanical sample-size rule or a "2 of 4 factors" vote.

### 1.4 Per-metric resolution algorithm

For each metric independently:

1. Start from `requested_bands = N`.
2. Within that metric's threshold base from §3.1, sort distinct raw values and enumerate the **global candidate gaps** between adjacent distinct values. A valid cutoff must lie in one of these gaps; therefore no tied raw value can be split.
3. If business thresholds are approved, map those thresholds to valid gaps and validate non-empty bands.
4. For quantile scoring, target cumulative shares `1/N, 2/N, …, (N-1)/N` and choose **N-1 unique ordered gaps jointly**, minimizing total deviation from those target cumulative shares. Do not move each quantile cutoff independently.
5. Preserve `N` bands whenever there are enough valid gaps and the resulting bands satisfy any explicitly approved minimum-band/actionability guardrail.
6. Reduce to the largest feasible `effective_bands < N` only when there are not enough valid distinct-value gaps or an explicit operational minimum-band-size guardrail makes N infeasible.
7. Record a concrete `adjustment_reason`, e.g. `insufficient_distinct_gaps`, `minimum_band_size_guardrail`, or `business_threshold_structure`.
8. Do **not** reduce another metric merely to make the three counts equal.

Interpretation:

| Effective bands | Default treatment |
| ---: | --- |
| 5 | Keep full 5-band raw resolution |
| 4 | Keep 4-band raw resolution; map to semantic levels via §2.4 |
| 3 | Keep 3-band raw resolution |
| 2 | Allowed when this is the true usable resolution; map to Low/High and flag reduced discrimination |
| 1 | Non-informative dimension; standard 3D lifecycle mapping is NO-GO unless the business explicitly approves neutralizing that dimension as Mid |

### 1.5 Example: ties do not automatically imply band collapse

```text
Requested: R5 / F5 / M5
F distinct-value masses: F=1 (40%), F=2 (25%), F=3 (15%), F=4 (10%), F=5 (10%)
```

Five distinct ordered values provide four valid gaps, so a tie-safe five-band solution still exists even though it is not population-balanced. Preserve `F_effective_bands=5`; do not collapse merely because several ideal quintile targets fall inside large tie masses.

A true mixed-band result occurs when an affected metric lacks enough usable distinct gaps, for example:

```text
Requested: R5 / F5 / M5
R: sufficient distinct day values  → effective 5
F: only three distinct valid values → effective 3 (`insufficient_distinct_gaps`)
M: sufficient distinct net amounts → effective 5

Runtime band_profile = R5-F3-M5
```

Never split tied values, and never demote R/M solely for symmetry.

## 2. Score direction and boundary convention

### 2.1 Direction

| Metric | Better raw value | Higher raw score means |
| --- | --- | --- |
| R (days) | Smaller | More recent |
| F (valid orders) | Larger | More frequent |
| `M_scoring` | Larger | Higher monetary value |

Raw score values always run from `1` (lowest end) to `effective_bands` (highest end).

### 2.2 General cutoff convention

For a metric with `N = effective_bands`, use `N-1` ordered cutoffs and strict `<` comparisons.

For ascending-value metrics F/M:

```text
x < c1        → score 1
c1 <= x < c2 → score 2
...
x >= cN-1    → score N
```

For R, reverse the score direction:

```text
R < c1        → score N
c1 <= R < c2 → score N-1
...
R >= cN-1    → score 1
```

The same operators and cutoffs must be reused in:

- analytical scoring;
- report logic;
- AE tag SQL/condition logic;
- user-cluster SQL/condition logic;
- downstream scoring/migration logic.

### 2.3 Canonical 3-band and 5-band examples

**3-band:**

```sql
CASE WHEN R_days    < <r_lo> THEN 3 WHEN R_days    < <r_hi> THEN 2 ELSE 1 END AS R_score,
CASE WHEN F_orders  < <f_lo> THEN 1 WHEN F_orders  < <f_hi> THEN 2 ELSE 3 END AS F_score,
CASE WHEN M_scoring < <m_lo> THEN 1 WHEN M_scoring < <m_hi> THEN 2 ELSE 3 END AS M_score
```

**5-band:**

```sql
CASE WHEN R_days    < <r_p20> THEN 5 WHEN R_days    < <r_p40> THEN 4 WHEN R_days    < <r_p60> THEN 3 WHEN R_days    < <r_p80> THEN 2 ELSE 1 END AS R_score,
CASE WHEN F_orders  < <f_p20> THEN 1 WHEN F_orders  < <f_p40> THEN 2 WHEN F_orders  < <f_p60> THEN 3 WHEN F_orders  < <f_p80> THEN 4 ELSE 5 END AS F_score,
CASE WHEN M_scoring < <m_p20> THEN 1 WHEN M_scoring < <m_p40> THEN 2 WHEN M_scoring < <m_p60> THEN 3 WHEN M_scoring < <m_p80> THEN 4 ELSE 5 END AS M_score
```

Mixed-band scoring applies the appropriate per-metric cutoff count independently; there is no separate mixed-band formula.

### 2.4 Raw score → semantic level

Default lifecycle segmentation uses `R_level/F_level/M_level` semantic values, so it does not require equal raw-score scales.

| `effective_bands` | Low (`level=1`) | Mid (`level=2`) | High (`level=3`) |
| ---: | --- | --- | --- |
| 2 | score 1 | — | score 2 |
| 3 | score 1 | score 2 | score 3 |
| 4 | score 1 | scores 2–3 | score 4 |
| 5 | scores 1–2 | score 3 | scores 4–5 |

Rules:

- Preserve the raw per-metric score for ranking, prioritization, migration, LTV, retention, and campaign analysis.
- Convert raw scores to semantic levels only for the default lifecycle mapping in §6.
- If a dimension has only one effective band, stop standard lifecycle classification unless the business explicitly approves `level=2 (Mid)` as a neutralized dimension; record that override.
- A business-approved alternative score→level mapping is allowed only with explicit rationale and must be reused consistently in analysis, tag/cluster definitions, reports, and downstream work.

Example:

```text
band_profile = R5-F3-M5
R_score=4 → R_level=High
F_score=3 → F_level=High
M_score=5 → M_level=High
→ Champions under §6
```

## 3. Threshold / segmentation mode

Choose one primary segmentation mode.

| Mode | Use when | Required behavior |
| --- | --- | --- |
| Business thresholds | Approved operational cutoffs already exist; VIP/tier rules exist; quantiles are not meaningful | Record threshold source and approval |
| Quantile thresholds | Distribution supports data-driven cutoffs | Use tie-aware per-metric cutoffs; do not force equal counts |
| Clustering | Explicitly requested or clearly justified exploratory segmentation | Treat as separate data-driven segmentation, not a threshold generator |

### 3.1 Quantile rules

| Item | Rule |
| --- | --- |
| Requested 3-band | Target p33/p66 cumulative shares, then jointly select two unique ordered distinct-value gaps minimizing total target deviation |
| Requested 5-band | Target p20/p40/p60/p80 cumulative shares, then jointly select four unique ordered distinct-value gaps minimizing total target deviation |
| R threshold base | Full universe |
| F threshold base | Scoring-window subjects with F>0; F=0 universe members remain at the lowest raw score |
| M threshold base | Normally scoring-window subjects with F>0 |

If M has a large zero mass after refunds:

- do not force quantiles;
- use a zero/nonzero rule or business/tie-aware cutoffs.

### 3.1.1 Tie-aware global-gap rule

For quantile scoring of one metric:

1. Aggregate counts by each distinct raw value and compute cumulative population share at every gap between adjacent distinct values.
2. For requested `N` bands, define target cumulative shares `t_k = k/N`, `k=1..N-1`.
3. Choose `N-1` **unique ordered gaps jointly**. Prefer the combination minimizing a deterministic objective such as:

```text
sum_k |cumulative_share(gap_k) - t_k|
```

4. Never put a boundary inside one raw value and never split ties.
5. Do not collapse bands merely because two independently rounded quantiles would have landed on the same gap; the joint selection must consider alternative gaps first.
6. Reduce `effective_bands` only when fewer than `N-1` usable gaps exist, or when an explicitly approved minimum-band/actionability constraint makes N bands infeasible.
7. Keep the other R/F/M metrics at their own supported resolution.

Deterministic tie-breaking when multiple gap combinations have equal objective:

1. prefer the combination with the larger minimum band population;
2. then prefer the lower lexicographic sequence of raw cutoff values;
3. record the chosen cutoff values and objective/tie-break result for reproducibility.

**Efficiency rule:** compute the distinct-value frequency histogram once, then solve the ordered target-to-gap assignment locally (for example dynamic programming / monotone assignment in roughly `O(number_of_gaps × N)`). Do not issue repeated AE queries per cutoff and do not brute-force all gap combinations.

Example — **no collapse required**:

```text
F masses: 1=40%, 2=25%, 3=15%, 4=10%, 5=10%
Requested bands: 5
Distinct values: 5 → four valid gaps exist
Result: effective_bands=5 (uneven band sizes are acceptable)
```

Example — **collapse required**:

```text
F has only values {1,2,3}
Requested bands: 5
Only two valid gaps exist
Result: effective_bands=3
adjustment_reason=insufficient_distinct_gaps
```

### 3.2 Clustering rules

- Standardize/transform features appropriately.
- Fit only when explicitly requested or clearly justified.
- Do not fabricate threshold bands from cluster centres.
- Report cluster profiles directly.
- If lifecycle labels are later required, map cluster profiles with explicit rationale.

## 4. Tie handling

### 4.1 Hard invariants

For each scored metric:

- Same raw value must map to exactly one raw score.
- `effective_bands <= requested_bands`.
- Effective scores must be contiguous `1..effective_bands` and every effective band must be non-empty.
- Every reduction in band count must have an `adjustment_reason`.
- Equal-population targets are advisory only.

### 4.2 Preferred fallback order

1. Move cutoffs to distinct-value gaps.
2. Collapse duplicate/unsupported cutoffs for only the affected metric.
3. Use a small-integer, business-readable scheme when the metric is highly discrete.
4. Use approved business thresholds.

Fallback example only:

```text
F = 1
F = 2–3
F >= 4
```

This is not a universal default.

## 5. Monetary handling

### 5.1 Preserve two fields

| Field | Purpose |
| --- | --- |
| `M_raw` | Business net revenue used for reporting and reconciliation |
| `M_scoring` | Value used for score construction |

Default:

```text
M_scoring = M_raw
```

### 5.2 Transformation decision

Do not default to p99 winsorization merely because M is right-skewed.

Why:

- top spenders may be the most important customers;
- quantile cutoffs are relatively robust to extreme magnitude.

Possible scoring-only treatments when justified:

- `log1p(M_raw)` for highly skewed continuous values;
- winsorized `M_scoring` for clustering/model stability;
- raw M with business/quantile cutoffs when tails are meaningful.

### 5.3 Reporting rule

Always use `M_raw` for:

- revenue share;
- total revenue;
- mean/median business value;
- reconciliation.

Never use capped/transformed `M_scoring` for business revenue reporting.

## 6. Default lifecycle-oriented mapping

This is the skill's **default operational mapping**, not a universal/statistical RFM standard.

Apply these first-match rules to semantic levels (`Low=1`, `Mid=2`, `High=3`):

| Priority | Segment key | Rule |
| ---: | --- | --- |
| 1 | `champions` | `R=3 & F=3 & M=3` |
| 2 | `lost_high_value` | `R=1 & F=3 & M=3` |
| 3 | `loyal` | `R=2 & F=3 & M=3` |
| 4 | `potential` | `R=3 & F<=2 & M<=2` |
| 5 | `promising` | `R=3`, not matched above |
| 6 | `hibernating` | `R=2`, not matched above |
| 7 | `at_risk` | `R=1`, not matched above |

### 6.1 Canonical CASE

```sql
CASE
  WHEN R_level=3 AND F_level=3 AND M_level=3   THEN 'champions'
  WHEN R_level=1 AND F_level=3 AND M_level=3   THEN 'lost_high_value'
  WHEN R_level=2 AND F_level=3 AND M_level=3   THEN 'loyal'
  WHEN R_level=3 AND F_level<=2 AND M_level<=2 THEN 'potential'
  WHEN R_level=3                               THEN 'promising'
  WHEN R_level=2                               THEN 'hibernating'
  WHEN R_level=1                               THEN 'at_risk'
END
```

### 6.2 Mapping semantics

- Exhaustive for all semantic-level combinations that actually occur.
- Mixed raw band profiles (`R5-F3-M5`, etc.) are normalized here through semantic levels.
- Lifecycle-oriented: R sets the broad lifecycle state; F/M refine value.
- If the business has approved lifecycle definitions, an approved alternative mapping may replace the default.

### 6.3 Optional 5-band-native extension — split only, never remap

**Status:** opt-in.

Eligibility:

- `R_effective_bands = 5`
- `F_effective_bands = 5`
- `M_effective_bands = 5`
- business explicitly approves additional operational cohorts

If any metric has fewer than five effective bands, skip this extension and use §6 semantic lifecycle mapping.

**Important:** first assign the default `base_segment` using §2.4 → §6. The extension may only split users *inside* existing base cohorts; it must not move users between the seven default lifecycle cohorts.

| Priority | Extended key | Required base segment | Raw 5-band condition |
| ---: | --- | --- | --- |
| 1 | `champions_elite` | `champions` | `R_score=5 & F_score=5 & M_score=5` |
| 2 | `loyal_premium` | `loyal` | `F_score=5 & M_score=5` (base `loyal` already constrains R to the Mid semantic level) |
| 3 | otherwise | keep `base_segment` | no split condition matched |

Canonical pattern:

```sql
CASE
  WHEN base_segment='champions'
       AND R_score=5 AND F_score=5 AND M_score=5
    THEN 'champions_elite'
  WHEN base_segment='loyal'
       AND F_score=5 AND M_score=5
    THEN 'loyal_premium'
  ELSE base_segment
END AS segment
```

This guarantees that the extension adds granularity without silently changing the default seven lifecycle boundaries.

Before enabling it, confirm:

- the added cohorts are operationally useful;
- expected segment sizes are actionable;
- strategy handling exists or can inherit the parent cohort direction.

### 6.4 End-to-end mixed-band example

Given:

```text
band_profile = R5-F3-M5
R_score=5
F_score=3
M_score=4
```

Semantic mapping:

```text
R5 score 5 → High
F3 score 3 → High
M5 score 4 → High
```

Default lifecycle result:

```text
R_level=3 & F_level=3 & M_level=3 → champions
```

The 5-band-native extension is not eligible because F has only three effective bands. Raw R/M granularity is still retained for within-segment prioritization and downstream analysis.

## 7. Sub-profile diagnostics

Broad segments can hide different F/M shapes.

Optional non-tag `sub_profile` examples:

- `high_frequency_low_value`
- `low_frequency_high_value`
- `balanced_mid`
- `zero_window_activity`

Rules:

- Do not automatically multiply AE tags for every sub-profile.
- Surface a sub-profile only when it changes interpretation or action.

## 8. Optional New segment

Create a dedicated first-time/new-payer segment only when operations needs it.

Preferred definition:

- lifetime purchase count; or
- eligibility-window purchase count when lifetime is unavailable.

Do not rely on:

```text
R = high AND F = 1
```

This may mix true first-time payers with historically old payers who paid only once inside the scoring window.

## 9. User-facing segment names

Stable analytical keys are not user-facing display labels.

Default lifecycle keys:

```text
champions
lost_high_value
loyal
potential
promising
hibernating
at_risk
```

Optional extension keys:

```text
champions_elite
loyal_premium
```

At Stage 7:

1. localize each runtime key once to `output_locale`;
2. store the localized display name in the result object;
3. reuse it consistently in result, quality, strategy, migration, and operationalization previews;
4. hide raw analytical keys in normal business output unless technical detail is requested.
