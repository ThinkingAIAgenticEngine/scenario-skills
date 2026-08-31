# Sample Quality and Independence Checks

Run these checks **before** interpreting a hypothesis test.

## 1. Sample-size diagnostic

- Independent designs: `n_A < 30` or `n_B < 30` is a **small-sample warning**, not an automatic block. Fisher exact remains valid for sparse independent 2×2 tables.
- Paired design: `paired_n < 30` is also a warning. When `b+c < 25`, use exact McNemar/binomial rather than relying on the chi-square approximation.
- Block only structurally unusable inputs (for example n=0, invalid counts, or paired data with no matched cells).

Treat 30 as an operational precision threshold, not a mathematical validity theorem.

## 2. Binary-count validity and boundary rates

For independent designs:
- Require `0 <= outcome <= n`.
- If either group has rate 0 or 1, use Fisher's exact test rather than Z.
- If both groups share the same boundary (0 vs 0 or 1 vs 1), observed difference is exactly 0; Fisher will return no evidence of a difference.
- If the groups are at opposite boundaries (0 vs 1), Fisher is still valid and should not be blocked merely because both are boundary rates.
- Otherwise, Fisher is the fallback when any expected 2×2 cell is <5.

For paired design:
- a/b/c/d must be nonnegative counts.
- If `b+c=0`, there are no discordant pairs and no within-user change to test; block the inferential claim (the calculator can mathematically return p=1 as a diagnostic, but the skill should surface "no discordant pairs").

## 3. File-level integrity

When user-level data are supplied:
- normalize group labels to exactly A/B before analysis;
- reject duplicate `user_id` within the same independent group;
- paired-wide rows must uniquely identify one user with two binary outcomes;
- reject non-binary outcome values.

## 4. Period ordering

A/B time ranges should be disjoint for a pre/post comparison, with A ending before B begins. If reversed/overlapping and the business intent is unclear, clarify rather than assuming which period is pre/post.

## 5. `period_active` overlap diagnostic

When user IDs are available:

`overlap_rate = |A ∩ B| / min(n_A, n_B)`

Interpretation:
- `<10%`: nearly independent; the independent primary analysis is generally a reasonable approximation.
- `10% to <30%`: moderate overlap; disclose the dependence risk.
- `>=30%`: independence is materially violated. **Do not silently replace the business question.** Keep the period-level Z/Fisher result as the primary full-population view, mark it as assumption-sensitive, and trigger a secondary `paired`/McNemar run on matched users when user-level pairing can be extracted.

The paired result answers within-user change on the consistently-active subset; it is not a drop-in replacement for the period-level population comparison.

If only aggregate counts are available, overlap is unknown; state that limitation.

## 6. Paired-sample representativeness

When `n_A_active` and `n_B_active` are available, compute:
`paired_share = paired_n / min(n_A_active, n_B_active)`.

If `<30%`, warn that the matched sample is a small consistently-active subset and may not represent the full period populations.

For paired-wide CSV containing only matched users, this diagnostic is unavailable because per-period active totals are unknown; say so instead of reporting an artificial 100%.

## 7. Allocation / cohort-size balance diagnostic

Let `analyze.py` compute the count-balance diagnostic and its decision. For `concurrent_ab`, this is classical SRM against the expected randomized allocation. For sequential `pre_post`, treat the same calculation only as a **cohort-size/traffic-balance diagnostic**, not proof of an assignment bug. Pass `cohort_design`, `design_type`, period lengths, expected ratio when explicitly known, and overlap.

Interpret `srm_decision.decision`:
- `skip`: not applicable / insufficient allocation information.
- `proceed`: no allocation/count-balance concern under the chosen diagnostic.
- `proceed_with_warning`: continue but surface the reason; common in sequential pre/post traffic drift or period-active overlap.
- `hard_reject`: concurrent A/B allocation mismatch consistent with a data-quality/assignment problem. Stop hypothesis testing and investigate instrumentation/randomization first.

For pre/post designs, unequal sample sizes are not automatically a data bug; period lengths and organic traffic can differ.


## Non-negotiable execution rules

- A `hard_reject` decision is reserved for concurrent randomized A/B allocation mismatch and blocks inferential testing; do not merely print a warning and continue.
- `proceed_with_warning` for pre/post traffic drift or overlap is surfaced but does not itself block the primary test.
- For paired SQL output, compare `paired_n` with `min(n_A_active,n_B_active)` when those denominators exist; `<30%` triggers a representativeness warning, not a statistical rejection.
- For Schema 2 paired CSV with no per-period active denominators, mark the representativeness check unavailable rather than treating paired share as 100%.
