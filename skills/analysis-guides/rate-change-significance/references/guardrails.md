# Guardrails and Hand-offs

## Common pitfalls

- Do not confuse significance testing with auditing the rate calculation.
- Do not use `first_occurrence` for "all visitors/active users" when the cohort event is recurring.
- Do not use `paired` for "all visitors" unless the user explicitly asks about the same users in both periods.
- Do not treat high-overlap `period_active` users as fully independent without disclosure and a paired sensitivity view when available.
- Do not claim causality from a sequential pre/post significance test.
- Do not declare business success from p-value alone.
- Do not treat p>=0.05 as proof of no effect.
- Do not skip sample-size/power planning guidance.
- Do not hardcode within-window semantics for paired analysis when the headline metric is exact-day retention.
- Do not use a period-level outcome window for paired users; outcomes must remain relative to each user's per-period cohort date.
- Do not guess event names/dates when ambiguity materially changes the analysis.

## Multiple comparisons

This skill is designed for one primary two-period binary-rate comparison. If the user tests many metrics or segments, do not interpret unadjusted p<0.05 discoveries as independent wins. Apply an appropriate family correction (e.g. Bonferroni or Benjamini-Hochberg) or narrow to a pre-specified primary comparison.

## Hand-offs

- retention calculation correctness → `retention-verification`
- segment-driver drilldown → appropriate analysis/drilldown skill/tool
- continuous metric comparison → continuous-metric method (e.g. t-test/Mann-Whitney as appropriate), not this skill
- multi-period forecasting/trend modeling → dedicated trend/time-series workflow

## Regression-test artifact separation

When testing this skill itself, keep verification notes, version checks, mismatch findings, and prior-run comparisons out of the normal business report. Put them in a separate `test-log.md` so regression testing does not alter the production report contract.
