# General Data Contract

## Required Fields

| Field | Type | Description |
|---|---|---|
| `user_id` | string | Unique user identifier, used only for linkage and output |
| `treatment` | integer | Whether the user received treatment; values must be 0 or 1 |
| `outcome` | numeric, optional | Post-treatment outcome |
| covariates | numeric | Pre-treatment covariates |

Include exactly one row per user. Apply the same eligibility criteria to treatment and control groups. Use UTF-8 CSV input. Source field names may differ, but map them accurately with script arguments.

## Recommended Covariates

- User profile: account age, country or region, platform, acquisition channel, and device tier.
- Pre-treatment activity: login days, session count, and play time.
- Pre-treatment progression: level, stage, power, and resource inventory.
- Pre-treatment monetization: historical revenue, payment count, and recency of last payment.
- Pre-treatment campaign exposure: prior campaign participation and previous messaging.

Encode categorical variables as 0/1 indicators in the source SQL, spreadsheet, or preprocessing flow. Group rare categories into "other" to reduce sparsity and complete separation.

## Prohibited Fields

- Any behavior or attribute generated after treatment.
- Activity, revenue, or retention information from the outcome window.
- Mediators directly changed by the intervention.
- User IDs, order IDs, device IDs, or other identifiers as covariates.
- Derived fields that directly contain outcome information.

## Timeline

```text
Eligibility ── Covariate window ── index_time/treatment ── Outcome window
```

Use a consistent time zone and identical window boundaries for all users. Record the source-system time zone when computing cross-day retention or revenue metrics.

## Data Quality Checks

- Verify that total rows equal unique `user_id` values.
- Verify that `treatment` contains only 0 and 1 and that both groups have observations.
- Report missing and invalid values by column. The script records field-level counts and rates, drops incomplete rows only after counting them, and stops when any covariate exceeds the default 10% gate. Use `--max-covariate-missing-rate` only to impose a stricter approved threshold, not to bypass the documented gate.
- Check for near-constant covariates and extreme outliers.
- Freeze the covariate list before modeling to avoid outcome-driven variable selection.

## Recommended Production Gates

| Check | Gate | Action when failed |
|---|---|---|
| Treated users | At least 100 recommended | Label exploratory or extend the observation period |
| Candidate controls | At least 200 recommended | Extend the pool or consider replacement after overlap inspection |
| Duplicate user IDs | Exactly 0 | Stop and correct aggregation |
| Primary-covariate missingness | At most 5% for a clean pass | Document 5% to 10%; stop or approve a method above 10% |
| Treatment values | Only 0 and 1 | Stop and correct treatment mapping |
| Window leakage | Exactly 0 post-treatment covariates | Stop and rebuild fields |

The script's ability to run on a small dataset is not evidence that the estimate is operationally reliable.
