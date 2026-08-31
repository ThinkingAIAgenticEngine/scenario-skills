# Validation, Sensitivity, and Correction

## Contents

1. Acceptance checklist
2. Reproducible validation fixture
3. Sensitivity comparison
4. Correction log
5. Decision template

## 1. Acceptance Checklist

Validate the workflow at four levels:

### Package validation

- `SKILL.md` contains English frontmatter with `name`, `description`, and semantic `version`.
- Package root contains only `SKILL.md`, `scripts/`, `references/`, and optional `assets/`.
- The Python script compiles without syntax errors.

### Input validation

- One row per unique user.
- Treatment values are exactly 0 and 1.
- Both treatment groups contain users.
- Covariates are numeric and measured before treatment.
- The optional outcome is numeric and measured after treatment.
- Missing and invalid rates are reported by field, identity/treatment fields are complete, and no covariate exceeds the approved missingness gate.

### Match validation

- Common support contains treated and control users.
- The propensity model converged before scores were used.
- At least 70% of treated users are matched.
- Every post-match absolute covariate SMD is below 0.10 for a clean pass.
- Propensity-score absolute SMD is below 0.10 for a clean pass.

### Reporting validation

- ATT is reported only when an outcome exists and P0/P1 gates pass.
- Absolute effect, relative lift, population scope, and residual-confounding caveat are included. Include the approximate confidence interval only without replacement; with replacement, verify that it is suppressed unless a dependence-aware method was run.
- Standard output files exist and counts reconcile.

## 2. Reproducible Validation Fixture

Run the bundled deterministic validator from the Skill directory:

```bash
python3 scripts/validate_fixture.py
```

It creates a temporary synthetic game-user CSV with a fixed seed, invokes `psm.py`, asserts the primary match gates, verifies that high covariate missingness and non-convergence are rejected, and verifies that replacement matching suppresses the naive confidence interval. Temporary data and outputs are removed after the run. This is a functional test, not customer evidence.

Fixture design:

| Item | Value |
|---|---:|
| Users | 800 |
| Random seed | 275 |
| Treated users | 267 |
| Candidate controls | 533 |
| Pre-treatment covariates | `level`, `login_days`, `pre_pay`, `vip`, `prior_campaigns` |
| Continuous outcome | `revenue_7d` |
| Injected true ATT | 8.0 outcome units |

Primary 1:1 matching result:

| Diagnostic | Result | Gate |
|---|---:|---:|
| Matched treated users | 254 | Informational |
| Treated-user match rate | 95.13% | At least 70% |
| Maximum post-match absolute SMD | 0.0440 | Below 0.10 |
| Estimated ATT | 7.4109 | Compare with injected 8.0 |
| Approximate 95% interval | 6.6075 to 8.2143 | Includes injected effect |

Acceptance interpretation:

- Matching and balance pass the production thresholds.
- Estimated ATT differs from the injected truth by about 0.59 units and the interval includes the injected effect.
- This fixture validates implementation behavior only. It does not validate the exchangeability assumption for a real business dataset.

Additional deterministic assertions:

- Blank one primary covariate for 81 of 800 users (10.125%): the run must fail the default 10% missingness gate.
- Limit logistic regression to one iteration: the run must fail the convergence gate and produce no match artifacts.
- Enable matching with replacement: ATT may be reported, but `standard_error_approx` and `ci95_approx` must be `null` with an uncertainty note.

## 3. Sensitivity Comparison

Freeze the causal question, eligible population, outcome window, and core covariates before running alternatives. Use this table:

| Specification | Caliper | Ratio | Replacement | Match rate | Max post SMD | ATT | 95% interval | Decision |
|---|---:|---:|---|---:|---:|---:|---|---|
| Primary | 0.20 | 1:1 | No | | | | | |
| Tighter | 0.10 | 1:1 | No | | | | | |
| Wider | 0.25 | 1:1 | No | | | | | |
| More controls | 0.20 | 1:2 | No | | | | | |
| Scarce controls | 0.20 | 1:1 | Yes | | | | | |

Treat the result as robust only when reasonable passing specifications preserve the business direction and do not materially alter the magnitude without explanation. Do not use a failed specification to average with a passing one.

If a randomized A/B test is feasible, use it as the preferred future validation. PSM may be used to design eligibility or estimate historical baselines, but it must not replace credible randomization.

## 4. Correction Log

Record every change in order:

| Attempt | Triggering failure | Change | Causal justification | Match rate before/after | Max SMD before/after | Kept or rolled back |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

Correction priority:

1. Fix invalid values, duplicates, missing pages, and time leakage.
2. Correct eligibility and field mappings.
3. Add justified pre-treatment confounders.
4. Add justified nonlinear terms or interactions.
5. Restrict common support or adjust caliper.
6. Allow replacement only for documented control scarcity.

Rollback a change when it does not resolve the targeted quality failure, introduces a higher-priority failure, or was selected based on the observed effect rather than design quality.

## 5. Decision Template

```text
Question:
Population and timeline:
Source and extraction evidence:
Original treated/control users:
Common-support and matched users:
Match rate:
Maximum pre/post-match absolute SMD:
ATT and absolute outcome units:
Relative lift:
Approximate 95% confidence interval:
Sensitivity result:
Residual risks:
Scoped recommendation:
Next validation action:
```
