# Statistical Method Selection and Formula Specification

`analyze.py` is the authoritative calculator. The formulas below are a specification/fallback, not the preferred path. If they are used because the script is unavailable, mark the result `manual_fallback`.

## Routing

### Paired observations
Use **McNemar** when the same users have binary outcomes in A and B, or equivalent a/b/c/d cells are available.
- `b+c = 0`: block the within-user inferential claim; there are no discordant pairs.
- `b+c < 25`: exact two-sided binomial McNemar.
- otherwise: continuity-corrected McNemar chi-square.

### Independent/full-period observations
For `first_occurrence`, `period_active`, and aggregate-rate mode:
1. validate counts and sample structure; `n<30` is a warning, not an automatic block;
2. if either group is at rate 0 or 1 → Fisher exact;
3. any expected 2×2 cell <5 → Fisher exact;
4. otherwise → two-proportion Z-test.

Fisher is an independent-table test only. Paired before/after outcomes always use McNemar/exact McNemar.

## `period_active` overlap rule

`period_active` answers a full-period population question. Overlap diagnoses the independence approximation; it does not silently change the estimand.
- `<10%`: nearly independent;
- `10%–<30%`: moderate overlap;
- `>=30%`: primary Z/Fisher remains the period-level view but is assumption-sensitive; emit/recommend a secondary `paired` McNemar view when matched data can be extracted.

Do not substitute the paired result for the period-level result. Report both when both are run and explain population-composition vs within-user change.

## Fisher 2x2 mapping

For independent groups:

| | outcome=1 | outcome=0 |
|---|---:|---:|
| A | `a=r_A` | `b=n_A-r_A` |
| B | `c=r_B` | `d=n_B-r_B` |

For paired analysis, the standard matched table is:

| | B=1 | B=0 |
|---|---:|---:|
| A=1 | a | b |
| A=0 | c | d |

Do not reuse paired a/b/c/d as the independent Fisher table.

## Formula fallback

Let `p_A=r_A/n_A`, `p_B=r_B/n_B`, and `p_pool=(r_A+r_B)/(n_A+n_B)`.

### Two-proportion Z

`SE_pool = sqrt(p_pool*(1-p_pool)*(1/n_A + 1/n_B))`

`z = (p_B - p_A) / SE_pool`

Two-sided `p = 2 * (1 - Phi(|z|))`.

### 95% CI for independent difference

`SE_unpooled = sqrt(p_A*(1-p_A)/n_A + p_B*(1-p_B)/n_B)`

`CI95 = (p_B-p_A) ± 1.96*SE_unpooled`.

### Relative uplift

`(p_B-p_A)/p_A`; undefined/null when `p_A=0`.

### Cohen's h

`h = 2*(asin(sqrt(p_B)) - asin(sqrt(p_A)))`.

Magnitude by `|h|`: `<0.2 negligible`, `<0.5 small`, `<0.8 medium`, `>=0.8 large`.

### MDD planning approximation

At two-sided alpha=.05 and ~80% power:

`MDD ≈ (1.96+0.84)*sqrt(p_pool*(1-p_pool)*(1/n_A+1/n_B))`.

### Approximate equal-per-group n for observed difference

`n ≈ ((1.96*sqrt(2*p_pool*(1-p_pool)) + 0.84*sqrt(p_A*(1-p_A)+p_B*(1-p_B))) / |p_B-p_A|)^2`.

This is post-hoc planning guidance only; do not use it as evidence for the current hypothesis.

### McNemar

Continuity-corrected statistic:

`chi2 = (|b-c|-1)^2/(b+c)` for `b+c>0`, df=1.

When `b+c<25`, use the exact two-sided binomial test with `n=b+c`, null probability .5, based on `min(b,c)`.

### Edwards-form paired 95% CI of the marginal difference

The marginal rates are `p_A = (a+b)/n` and `p_B = (a+c)/n` where `n = a+b+c+d`. The observed marginal difference is `observed_diff = p_B - p_A = (c-b)/n`.

Edwards-form standard error: `SE_diff = sqrt((b+c) - (c-b)^2/n) / n` (when the term under the sqrt is negative due to small-sample noise, clamp to 0).

95% CI of the marginal difference: `observed_diff ± 1.96 * SE_diff`.

This CI is on the marginal difference (per-user shift in outcome rate across periods), not on the discordant count alone; report it alongside the p-value for paired designs so Part 3 has both the significance test and the effect-size uncertainty.

### Discordant-pair power

McNemar power depends on the discordant structure, not `n` alone. Let `ψ = |b-c|/(b+c)` be the discordant asymmetry, in `[0,1]`.

Discordant pairs needed at two-sided α=.05 and ~80% power: `n_disc_needed = ((1.96 + 0.84)/ψ)^2`.

Report `discordant_pairs_needed_for_80pct = ceil(n_disc_needed)`. When `ψ=0` (i.e. `b=c`, no observed asymmetry), the value is `null` — there is no observed direction to detect. When `b+c=0`, McNemar is undefined entirely (return `p_value=1.0` with `method="no_discordant_pairs"`).

### Fisher exact

For fixed margins, the cell probability is hypergeometric. The two-sided p-value is the sum of probabilities of feasible tables whose probability is less than or equal to the observed table's probability (matching the calculator implementation).

### Fisher odds ratio direction

With independent layout `A=[a,b]`, `B=[c,d]`, report the odds ratio in the same B-vs-A direction as the rest of the skill: `OR_B_vs_A = (c/d)/(a/b) = (b*c)/(a*d)` when finite. The JSON also emits `odds_ratio_direction = "B_vs_A"`.

## Interpretation invariants

- `p<alpha` supports a difference under the stated design/assumptions; it does not establish business importance or causality.
- `p>=alpha` means insufficient evidence to establish a difference; it is not proof of equality/no effect.
- Effect size, CI, design quality and sample sufficiency must accompany the p-value.
