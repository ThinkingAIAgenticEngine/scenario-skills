# Cohort Retention Deep Dive - Metric Formulas

Reference library for every metric used across the methodology. All formulas assume the project timezone has been confirmed first.

## 1. Retention Metrics

### Definition Checklist (align before computing)

Retention definitions differ per project. Confirm and record these five items before computing any metric below:

| # | Item | Options / questions |
|---|------|---------------------|
| 1 | Active / return events | Which events count as "active" and "returned"? Confirm exact event names (any event vs a specific session / open / login event). |
| 2 | Dedup dimension | `#user_id` vs `#account_id` vs `#distinct_id` — which key is the denominator? |
| 3 | Bounded vs unbounded | "Returned exactly on day N" (bounded) vs "returned on day N or later" (unbounded). |
| 4 | Day-0 offset | Is D1 the next calendar day after day 0, or day 0 itself? |
| 5 | New-user definition | First event / registration / first active day? |

If the user quotes a number from an existing dashboard, reconcile your computed value against it first; a mismatch means the definition is not aligned — reconcile before diagnosing.

### N-day retention (new-user model)

```
N-day retention = unique users active on day N after first-active day / new users on day 0
```

- `day 0` = the user's first active day (registration / first open)
- `day N` = the Nth calendar day after day 0 (D1 = next day)
- A user counts once per cohort, regardless of how many sessions they have on day N

### Active-user retention (active-user model)

```
N-day retention = users active on day 0 AND day N / users active on day 0
```

Use when the question is about engagement of an existing base, not onboarding quality.

### Unbounded vs bounded

| Variant | Meaning | Use |
|---------|---------|-----|
| Unbounded | "returned on day N or later" | LTV / return windows |
| Bounded | "returned exactly on day N" | Curve shape and inflection detection |

For inflection detection (Module 3), use **bounded** retention so each day's drop is independent.

## 2. Cohort Matrix Shape

Two orthogonal reads:

```
Across-cohort slope = D7 retention of cohort C+1 - D7 retention of cohort C
Within-cohort slope = D1 retention of cohort C - D7 retention of cohort C
```

| Read | Question | Signal |
|------|----------|--------|
| Across-cohort | "Are newer users better or worse?" | acquisition quality trend |
| Within-cohort | "How fast does a cohort decay?" | product stickiness |

A within-cohort slope that is steep (large D1-to-D7 gap) means users who survive day 1 still leave; a flat within-cohort slope means day-1 survivors tend to stay.

## 3. Segment Effects and Period Decomposition

Use mutually exclusive, exhaustive slices. Keep unknown values as a slice and preserve an "Other" bucket when rows are folded.

### 3A. Single-window drag/lift

For one window, let `r_i` be slice retention, `w_i` its denominator share, and `R = sum(w_i x r_i)` the overall retention:

```
drag_or_lift_i = w_i x (r_i - R)
```

These effects sum to zero. Use them to rank which slices sit below or above the same-window overall rate. Never say they explain a period-over-period change.

### 3B. Period-over-period change

For baseline period `0` and current period `t`:

```
R_t - R_0 = sum_i rate_effect_i + sum_i mix_effect_i
rate_effect_i = w_i,t x (r_i,t - r_i,0)
mix_effect_i  = r_i,0 x (w_i,t - w_i,0)
```

This base-period decomposition is exact when the same exhaustive slices are used in both periods. `rate_effect` captures within-slice retention change; `mix_effect` captures population-share change. State the convention because alternative symmetric decompositions allocate the interaction differently.

Example with unchanged shares: overall D7 fell 3.0pp.

| Slice | D7 baseline | D7 current | Current share | Rate effect |
|-------|-------------|------------|---------------|-------------|
| Channel A | 30.0% | 25.0% | 40% | -2.0pp |
| Channel B | 26.0% | 24.0% | 35% | -0.7pp |
| Channel C | 24.0% | 22.8% | 25% | -0.3pp |

With unchanged shares, mix effects are zero and Channel A accounts for 2.0pp of the 3.0pp decline. When shares change, report both effects; do not attribute the full change to rate deltas alone.

## 4. Inflection-Point Detection

```
daily_drop_rate(d) = ( retention_d - retention_d+1 ) / retention_d
```

Flag day `d` only when the drop is positive and exceeds both a relative and materiality threshold agreed for the analysis. A starting heuristic is:

```
daily_drop_rate(d) > 1.5 x median(positive daily_drop_rate over the window)
```

If the positive-drop median is zero, missing, or unstable, use a percentile or median-absolute-deviation rule instead and label it as a heuristic. Then map flagged days to product beats (tutorial end, stamina exhaustion, first-pay prompt, level ramp). A matching beat supports a hypothesis, not a proven cause; an unexplained cliff is a data-quality or external-factor signal, not a product conclusion.

## 5. Key-Behavior Correlation

```
association_lift(behavior B) = later retention of eligible users who did B - later retention of eligible users who did not B
coverage(B) = eligible users who did B in the exposure window / total eligible users
```

Rank by:

```
priority_signal(B) = association_lift(B) x coverage(B)
```

Interpretation:

| lift | coverage | Reading |
|------|----------|---------|
| High (>=20pp) | Low (<30%) | Candidate worth causal validation before any nudge |
| High | High (>=60%) | Widely adopted candidate; protect only after validation |
| Low (<10pp) | Any | Weak differentiating signal in this sample |

The behavior exposure window must end before the outcome window. For multi-day exposure, define a landmark eligibility population so survival into the exposure window does not mechanically inflate the exposed group's retention.

## 6. Lever Opportunity and Causal Impact

Before an experiment, the observed association may be used only as an opportunity index:

```
opportunity_index = eligible_users x (1 - current_coverage) x association_lift
```

This is not an expected causal gain and may be confounded. Label it as a prioritization signal only.

After a randomized or otherwise defensible causal estimate exists:

```
expected_incremental_retained_users = eligible_unexposed_users x causal_uplift
```

Route causal validation to `ae-experiment-design` before using the result as a forecast.

## 7. Confidence Interval

```
95% CI = p +/- 1.96 x sqrt( p x (1-p) / n )
```

- `p` = observed retention rate
- `n` = denominator sample size for that slice

Sample-size guardrails:

| n | Action |
|---|--------|
| n >= 1000 | Report as-is |
| 500 <= n < 1000 | Downgrade confidence one level near boundaries |
| 100 <= n < 500 | Flag for verification |
| n < 50 | Do not classify; request more data or a wider window |
