# Cohort Retention Deep Dive - Methodology Detail

Operational steps for the five modules in the SKILL.md. Module 1 is always first; run later modules only when the user's question requires them. Compose every ae-cli query per the `ae-analysis` skill references; discover real events, properties, tables, and columns before composing. Never fabricate identifiers or definition JSON.

## Module 1 - Cohort Matrix Reading

1. Run the retention model (generic cohort or active-user per the interaction flow) with bounded daily granularity.
2. Render the cohort matrix: rows = cohort (first-active day), columns = D1..D30 (or the agreed window).
3. Classify the curve shape using the SKILL.md shape table.
4. If the shape is ambiguous, pull two summary numbers: the across-cohort D7 trend and the within-cohort D1-to-D7 gap.

Do not jump to segment slicing before the shape is classified - the shape tells you which module matters next.

## Module 2 - Layered Attribution

1. Fix the retention metric and window from Module 1.
2. For each confirmed dimension (channel, version, device, new-vs-old, pay status, geo), run the **retention model** with the dimension in `retention.groups`. Request counts when rates must be regrouped, and compute each grouped rate from matched numerator and denominator rows.
3. Confirm that slices are mutually exclusive and exhaustive. Preserve missing/unknown values as a named slice; do not silently drop them.
4. If the user asks which slices are above or below the current overall rate, compute the single-window drag/lift from `metrics.md` section 3A. State that the values sum to zero and are not an explanation of change.
5. If the user asks why retention changed between periods, query both periods and compute the rate and mix effects from `metrics.md` section 3B. Do not substitute a single-window baseline calculation.
6. Rank by the material effect relevant to the question. Report at most 5 rows; fold the rest into an "Other" bucket while preserving totals.

Pitfall: a slice with terrible retention but tiny share is a curiosity, not a lever. Always multiply by share.

## Module 3 - Inflection-Point Detection

1. From the bounded daily retention series, compute `daily_drop_rate(d)` per `metrics.md` section 4.
2. Flag days above 1.5x the window median.
3. For each flagged day, list candidate product beats in that day's position. Ask the user to confirm which beats exist (tutorial end day, stamina reset, paywall, level ramp).
4. Label each flag: `beat confirmed` (high confidence) or `no known beat` (route to data-quality or external-factor check).

## Module 4 - Key-Behavior Correlation

1. Agree a candidate behavior set with the user; do not self-select from event names. If the request is specifically about new users or first-day behavior, route to `new-user-analysis`.
2. Confirm each behavior's event and completion property, the cohort-entry event, identity key, exposure window, and later outcome window.
3. Prevent temporal leakage: the exposure window must end before the outcome window. If exposure spans multiple days, use a landmark design with a clearly stated eligibility population; do not let survival into the exposure window mechanically define the retained group.
4. If the retention model can express the confirmed exposed/non-exposed grouping or filters, use it. Otherwise, read `ae-analysis`'s SQL model reference, discover an authorized table and its columns with `analysis sql-table list/columns --usage analysis`, and use read-only SQL with a date-partition predicate. Never guess a table or column and never create a tag/cluster without approval.
5. Compute association lift and coverage per `metrics.md` section 5. Rank by `association lift x coverage` only as a prioritization signal.
6. Always append the correlation-is-not-causation caveat and route validation to `ae-experiment-design`.

## Module 5 - Optimization Lever Ranking

Combine Modules 2-4 into one table:

```
| Rank | Breakpoint day | Segment | Behavior | Opportunity index | Confidence |
```

Before causal validation, sort by the opportunity index and label it non-causal; do not call it expected impact. After an experiment provides a causal uplift, the table may include expected incremental retained users. Cap at 5 rows. For each row state the confidence and the validation experiment to run next.

## Guardrails

- Confirm project timezone before any query; a wrong timezone shifts day-0 boundaries and corrupts the whole analysis.
- Data latency: prefer T-1 or earlier windows; do not diagnose an incomplete "today" cohort.
- Sample size: apply the `metrics.md` section 7 guardrails to every slice.
- Do not over-infer: state confidence, mark heuristics, and always offer an experiment.
