# PSM Methodology

## Objective

The propensity score is the probability of receiving treatment conditional on observed pre-treatment features. Matching untreated users with similar scores approximates the counterfactual outcome for treated users. The default estimand is:

```text
ATT = E[Y(1) - Y(0) | T=1]
```

## Default Implementation

- Estimate propensity scores with logistic regression.
- Standardize numeric covariates before fitting.
- Apply L2 regularization to reduce complete-separation risk.
- Require the optimizer to converge to the implementation's loss tolerance; do not match on scores from a run that exhausts its iteration budget.
- Retain only the overlap of treatment and control propensity-score ranges.
- Perform greedy nearest-neighbor matching on the propensity-score logit.
- Default to 1:1 matching without replacement and a caliper equal to 0.2 times the logit standard deviation.
- Evaluate balance with standardized mean differences (SMD).

For matching without replacement, the script reports a simple matched-set standard error and labels it approximate. With replacement, reused controls make matched-set effects dependent; the script therefore returns no standard error or confidence interval. Use a reviewed dependence-aware bootstrap or cluster-robust variance estimator when uncertainty from a replacement match is required.

## Interpretation Limits

PSM depends on assumptions that cannot be fully verified:

1. **Conditional exchangeability**: all confounders affecting both treatment and outcome are observed and included.
2. **Positivity**: every eligible user type has a nonzero chance of being treated and untreated.
3. **Consistency**: treatment is well defined and comparable across users.
4. **No interference**: one user's treatment does not change another user's outcome.

Describe results as "estimated incremental impact after adjustment for observed characteristics," not as unconditional proof of causality.

## Diagnostic Thresholds

| Metric | Guidance |
|---|---|
| Post-match `|SMD| < 0.10` | Acceptable |
| `0.10 <= |SMD| < 0.20` | Warning; interpret cautiously |
| `|SMD| >= 0.20` | Imbalanced; do not report the primary effect |
| Treated-user match rate `< 70%` | High generalizability risk |
| Propensity scores near 0 or 1 | Poor overlap; consider stopping |

## When Not to Use PSM

- A randomized experiment is feasible at acceptable cost.
- Reliable pre-treatment covariates are unavailable.
- Treatment and outcome timing cannot be established.
- Treatment and control groups have almost no common support.
- The intervention creates strong interference between users or groups.

## Sensitivity Analysis

After freezing the primary specification, optionally report:

- Calipers of 0.1, 0.2, and 0.25.
- 1:1 and 1:2 matching.
- Matching with and without replacement.
- Alternative covariate specifications that were justified in advance.

Always report match rate and balance alongside the effect. Never show only the specification with the largest effect.
