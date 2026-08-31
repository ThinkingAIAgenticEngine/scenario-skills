---
name: propensity-score-matching
description: Trigger when game operations, marketing, product, or data teams need to estimate the incremental effect of a non-random campaign, offer, message, feature, channel, or intervention from user-level CSV, spreadsheet, database or warehouse, or AE/TE data. Validate pre-treatment covariates, estimate propensity scores, match comparable controls, diagnose overlap and balance, and return ATT, confidence bounds, matched users, and quality evidence. Do not use when a credible randomized experiment exists, treatment timing is unknown, or observed covariates cannot support a defensible comparison.
version: 2.0.0
---

# User Propensity Score Matching

Estimate whether an operational intervention created incremental impact by comparing treated users with untreated users who looked similar before the intervention. Keep the workflow independent of any analytics platform. Operate read-only by default and never write cohorts, tags, tables, or reports back to a source system without explicit approval.

## What This Skill Solves

Game teams often compare campaign participants with non-participants and mistakenly attribute pre-existing user differences to the campaign. This skill reduces that selection bias with propensity score matching (PSM), then exposes the evidence needed to decide whether the comparison is credible.

Explain the distinction on first use:

- **Propensity prediction** asks who is likely to pay, churn, or participate.
- **Propensity score matching** asks whether an intervention helped users who received it.

Primary users are game operations, growth, monetization, product, and data teams. Common delivery variants include:

1. Campaign, offer, coupon, or bundle effectiveness.
2. Push, inbox, win-back, or churn-intervention effectiveness.
3. Feature, mode, difficulty, or gameplay-change effectiveness.
4. Acquisition-channel, retargeting, support, or compensation effectiveness.

The standard output is an evidence package containing matched users, propensity scores, balance diagnostics, the average treatment effect for treated users (ATT), an approximate confidence interval, limitations, and an operational recommendation.

## Beginner Entry Point

Ask only these three business questions before discussing statistical parameters:

1. What intervention should be evaluated?
2. What outcome should improve?
3. When did the intervention occur?

Then restate one executable design containing the treatment group, candidate control group, pre-treatment feature window, post-treatment outcome window, and eligible population. If the request is vague, propose two or three designs and wait for selection before querying business data.

Use these defaults unless the user supplies justified alternatives:

- Estimand: ATT.
- Matching: 1:1 nearest neighbor, without replacement.
- Caliper: 0.2 standard deviations of the propensity-score logit.
- Covariates: demographics, activity, progression, historical payment, and prior intervention exposure measured before treatment.
- Acceptance gate: at least 70% of treated users matched and every post-match absolute standardized mean difference below 0.10.

## Game Industry Use Cases

| Scenario | Example treatment | Candidate outcomes |
|---|---|---|
| Campaign effectiveness | Joined a seasonal, login, or guild campaign | Retention, activity, revenue, LTV |
| Offers and promotions | Received a bundle, discount, or coupon | First purchase, repeat purchase, revenue |
| Messaging and reactivation | Received push, inbox, or win-back messaging | Return, reactivation, retention |
| Churn intervention | Received compensation, resources, or support | Churn, reactivation, future revenue |
| Features and modes | Adopted or was exposed to a dungeon, guild, PvP, or pet feature | Activity, retention, revenue |
| Difficulty and experience | Was affected by level, reward, or matchmaking changes | Completion, retries, churn |
| Advertising and acquisition | Came from a channel or received retargeting | Retention, revenue, LTV |
| Incident handling | Received customer support or incident compensation | Retention, refunds, future revenue |

## Six-Dimension Analysis Framework

Evaluate every request across all six dimensions. Do not skip a dimension because the script completed successfully.

| Dimension | Required evidence | Decision question |
|---|---|---|
| 1. Causal design | Treatment, index time, estimand, outcome, and observation windows | Is the comparison aligned to one defensible causal question? |
| 2. Eligibility and sample | Inclusion rules, exclusions, unique-user counts, and missingness | Did treated and control users have the same opportunity to receive treatment? |
| 3. Overlap and positivity | Propensity distributions, common-support counts, and match rate | Are comparable controls available for enough treated users? |
| 4. Covariate balance | Pre/post standardized mean differences for every covariate | Did matching remove observable pre-treatment differences? |
| 5. Effect and uncertainty | ATT, relative lift, standard error, and confidence interval | Is the effect meaningful and sufficiently precise? |
| 6. Robustness and actionability | Alternative specifications, residual risks, and targetable segments | Does the conclusion survive reasonable choices and support a safe action? |

## Required Data and Minimum Conditions

Build one row per eligible user. Read [references/data-contract.md](references/data-contract.md) before extraction.

Required fields:

- A stable user ID used only for joining and output, never as a model covariate.
- A binary treatment indicator.
- A known intervention or index time.
- Numeric pre-treatment covariates covering major drivers of both treatment and outcome.
- An optional post-treatment outcome. Without it, the skill may match users and diagnose balance but must not estimate ATT.

Recommended production conditions:

- At least 100 treated users and 200 candidate controls. Smaller samples are exploratory only.
- At least five meaningful pre-treatment covariates across activity, progression, monetization, profile, and prior exposure when those domains are relevant.
- No duplicate user IDs in the modeling dataset.
- Primary-covariate missingness no greater than 5% after eligibility rules. At 5% to 10%, document and justify preprocessing. The script reports missing and invalid values by field and rejects any covariate above 10% by default. Above 10%, stop and redesign or apply an approved missing-data method before matching; do not weaken the command-line gate to bypass review.
- Treatment and control users drawn from the same calendar period and eligibility rules.
- Covariate windows ending strictly before treatment and outcome windows beginning after treatment.

For event-based sources such as AE/TE, resolve the real project, treatment event or property, pre-period behavior and profile fields, outcome event or property, user identity, and timezone before extraction. Never invent event or property names.

## Supported Data Environments

Reuse the environment already supplied or authorized. Do not force migration.

| Environment | Approach |
|---|---|
| CSV or TSV | Validate columns and run `scripts/psm.py` directly |
| Excel or spreadsheet | Read the selected sheet and convert it to a user-level UTF-8 CSV |
| Database or warehouse | Use an available read-only query tool to build the user-level table |
| Notebook or Python | Export a DataFrame that follows the data contract |
| AE or TE | Read [references/ae-adapter.md](references/ae-adapter.md) only for an AE/TE request |
| Other analytics platforms | Use the platform export, API, or SQL capability to prepare the same contract |

AE CLI is an optional adapter, not a requirement for this skill.

## Boundary Statement

Do not use this skill when:

- A credible randomized A/B experiment exists; analyze the experiment instead.
- The request is only to predict payment, churn, or participation.
- Treatment timing cannot be determined.
- Reliable pre-treatment covariates are unavailable or a key confounder is known to be missing.
- Treatment and control groups have almost no common support.
- Treatment materially affects other users, such as an intervention assigned at guild or server level, unless the design and standard errors operate at that level.
- The requested conclusion would exceed the observed population or time window.

PSM adjusts only for observed differences. Never describe a PSM estimate as proof of causality.

## Mandatory Execution Sequence

Complete the steps in order. Each step must produce its stated output before continuing.

### Step 1: Frame the Causal Question

**Action**

- Confirm the binary treatment, index time, post-treatment outcome, eligible population, and ATT estimand.
- List candidate pre-treatment confounders and explain why each may affect both treatment and outcome.
- Confirm that treatment precedes the outcome.

**Output**

- A one-paragraph design specification and a field/window table.

**Stop if**

- Treatment, timing, population, or outcome remains ambiguous.

### Step 2: Resolve and Inspect the Data Source

**Action**

- Use supplied files directly, or inspect connected source metadata before querying.
- For AE/TE, follow [references/ae-adapter.md](references/ae-adapter.md).
- Prefer read-only queries and exports. Never request secrets embedded in connection strings.

**Output**

- Confirmed source, table/report/project, fields, timezone, expected user grain, and read path.

**Stop if**

- The source cannot reproduce the treatment, windows, or user identity.

### Step 3: Build the Eligible User Dataset

**Action**

- Apply identical eligibility rules to treatment and candidate-control users.
- Aggregate to one row per user.
- End covariate windows before treatment and begin outcome windows after treatment.
- One-hot encode categorical variables, reasonably cap extreme values when justified, and document missing-value handling.

**Output**

- A UTF-8 CSV conforming to `references/data-contract.md`, plus row count, unique-user count, treated/control counts, duplicates, and missingness.

**Stop if**

- Duplicate IDs, post-treatment leakage, incomplete pagination, or unexplained high missingness remains.

### Step 4: Run the Primary Match

**Action**

Run the deterministic implementation:

```bash
python3 scripts/psm.py \
  --input <users.csv> \
  --id-col user_id \
  --treatment-col treatment \
  --outcome-col revenue_7d \
  --covariates level,login_days,pay_amount_pre7d,vip,prior_campaigns \
  --output-dir <output-dir> \
  --ratio 1 \
  --caliper 0.2 \
  --max-covariate-missing-rate 0.10
```

Omit `--outcome-col` for matching-only analysis. Use `--with-replacement` only when a limited control pool justifies reusing controls. Reused controls make matched-set effects dependent, so the bundled script suppresses its approximate standard error and confidence interval in that mode; use a reviewed dependence-aware bootstrap or cluster-robust method if uncertainty is required.

**Output**

- `matched_pairs.csv`: treated-control links and match distances.
- `scored_users.csv`: propensity scores and support status.
- `report.json`: per-field missing/invalid rates, model convergence, sample, balance, and effect diagnostics.

**Stop if**

- The script rejects high covariate missingness, the propensity model does not converge, no common support exists, or no treated users can be matched.

### Step 5: Apply Quality Gates

**Action**

- Read all three outputs and apply the validation priorities below.
- Report the maximum post-match absolute SMD, propensity-score SMD, matched-treated count, and match rate.

**Output**

- A PASS, WARN, or FAIL decision with the evidence for every failed threshold.

**Stop if**

- Any P0 condition or P1 fail condition remains unresolved. Do not report ATT as a decision metric.

### Step 6: Run Predeclared Sensitivity Checks

**Action**

- Compare the primary specification with justified alternatives such as calipers 0.10 and 0.25, 1:2 matching when controls are abundant, or matching with replacement when controls are scarce.
- Keep the causal question, outcome window, and core confounders fixed.
- Do not select a specification because it produces a favorable effect.

**Output**

- A comparison table of match rate, maximum post-match SMD, ATT, and confidence interval for each specification.

**Stop if**

- Direction or magnitude changes materially without a substantive explanation; label the result unstable.

### Step 7: Report the Business Result

**Action**

Report:

1. Business question, population, and windows.
2. Original and matched sample counts.
3. Overlap and balance evidence.
4. ATT and relative lift when an outcome exists, plus the approximate 95% confidence interval only when controls are not reused. When matching with replacement, state that the bundled interval is unavailable and name the dependence-aware method required to produce one.
5. Sensitivity results and residual confounding risks.
6. A scoped recommendation: expand, narrow, continue testing, or stop.

**Output**

- A decision-ready summary and links or paths to the three standard artifacts.

**Stop if**

- The narrative implies effects outside common support or claims causality beyond the evidence.

### Step 8: Write Back Only with Approval

**Action**

- If requested, propose the exact destination, asset name, schema, matched-user count, and overwrite behavior.
- Obtain explicit approval before creating a cohort, tag, table, or report.

**Output**

- Either a preserved local evidence package or a verified external asset with creation evidence.

**Stop if**

- Permissions, schema, destination, or import capability is uncertain.

## Validation Priorities and Thresholds

| Priority | Condition | Required response |
|---|---|---|
| P0 | Post-treatment leakage, duplicate user IDs, invalid treatment values, outcome used as a covariate, covariate missingness above the approved gate, a non-convergent propensity model, or no common support | Stop and rebuild the dataset, model, or design |
| P1 fail | Match rate below 70%, any post-match `|SMD| >= 0.20`, or propensity-score `|SMD| >= 0.20` | Do not use ATT for an operational decision |
| P1 warning | Any post-match `0.10 <= |SMD| < 0.20` | Show the imbalance prominently and attempt a justified correction |
| P2 | Wide confidence interval, low power, or sensitivity across reasonable specifications | Limit the recommendation and propose more data or an experiment |
| Pass | Match rate at least 70% and every post-match `|SMD| < 0.10` | Report the estimate with scope and residual-bias caveats |

## Degradation and Recovery Strategy

| Problem | Safe degradation or recovery |
|---|---|
| AE/TE access is unavailable | Export a user-level CSV and run the platform-independent path |
| Categorical covariates exist | One-hot encode before invoking the numeric-only script |
| Outcome is unavailable | Produce matched users and balance diagnostics only; do not report ATT |
| Control pool is small | Restrict common support first, then consider matching with replacement, disclose reused controls, and suppress the bundled naive confidence interval |
| Match rate is below 70% | Narrow the estimand to supported treated users and avoid generalizing to excluded users |
| Balance is poor | Correct data issues, add substantively justified nonlinear terms or interactions, then adjust caliper |
| Common support is absent | Stop; do not manufacture a comparison or extrapolate |
| Sample size is small | Label results exploratory and recommend longer observation or a randomized test |
| A key confounder is unavailable | State that residual bias is likely and do not make a causal operational claim |
| One specification alone looks favorable | Run and disclose predeclared sensitivity checks; never cherry-pick |

## Output Interpretation

- `matched_pairs.csv` is the auditable mapping between each treated user and selected control users. Smaller distance means closer estimated treatment propensity.
- `scored_users.csv` supports overlap inspection and downstream segmentation. A propensity score is not a churn or payment probability; it is the estimated probability of receiving treatment given observed covariates.
- `report.json` is the decision gate. Interpret ATT only after overlap and balance pass.
- For binary outcomes, ATT is a percentage-point difference. For continuous outcomes, ATT is expressed in the outcome's original units.
- Relative lift is contextual and can be unstable when the matched-control mean is near zero; always show the absolute ATT.
- `model.converged` must be true before interpreting scores or matches. The script stops rather than emitting artifacts from a non-convergent model.
- With replacement, `standard_error_approx` and `ci95_approx` are `null` because reused controls induce dependence. Do not reconstruct a naive interval from the matched rows.

## Automatic Correction Rules

Corrections must improve design quality, not the apparent effect:

1. Fix data-contract violations and leakage first.
2. Add only pre-treatment covariates supported by the causal rationale.
3. Add nonlinear terms or interactions only when their relationship is plausible and documented.
4. Tighten common support or caliper before accepting imbalance.
5. Use replacement only when control scarcity is the documented reason.
6. Preserve every attempted specification and roll back any change that worsens balance without solving a higher-priority problem.

Read [references/validation-and-tuning.md](references/validation-and-tuning.md) for the validated fixture, sensitivity template, and correction log.

## FAQ

### Is PSM the same as an A/B test?

No. An A/B test uses randomized assignment and is preferred when credible. PSM uses observed historical data and cannot remove unmeasured confounding.

### Why is the match rate low?

Treated users may differ greatly from available controls, the caliper may be strict, or eligibility rules may be inconsistent. Inspect common support before changing parameters.

### Can this skill run without AE/TE?

Yes. It works with any source that can produce the documented user-level CSV.

### Can it run without an outcome?

Yes, but only to create comparable groups and validate balance. It cannot estimate incremental effect without a post-treatment outcome.

### Does a significant ATT prove causality?

No. It supports a conditional comparison under observed-covariate assumptions. State residual risks and recommend randomization when feasible.

### What should I do if quality gates fail?

Do not publish the effect. Follow the degradation order, retain the failure evidence, and redesign the data or evaluation.

## References

- [Data contract](references/data-contract.md)
- [Methodology and limitations](references/methodology.md)
- [AE/TE adapter](references/ae-adapter.md)
- [Validation, sensitivity, and correction](references/validation-and-tuning.md)

## Language Constraint

Respond in the same language as the user's request. Keep identifiers, command names, fields, and artifact filenames unchanged when translation would make execution ambiguous.
