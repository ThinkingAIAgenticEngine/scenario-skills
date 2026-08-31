# Window Semantics and Event Filters

## Outcome-window semantics

Use the same window rule across `first_occurrence`, `period_active`, and `paired` so different designs test the same outcome definition.

- `exact_day`: outcome must occur exactly on cohort date + N. Typical for project definitions of day-N retention.
- `within_window`: outcome occurs after cohort entry and on/before cohort date + N. Typical for repurchase, conversion, churn, renewal, custom, and cumulative-retention definitions.

For non-retention repeat/action scenarios, normally exclude the cohort date itself (`outcome_date > cohort_date`) so the triggering cohort action is not miscounted as a later outcome.

Do not mix exact-day headline rates with cumulative-window trend data or vice versa.

## Cohort filter

Use an optional event-property predicate when the business's "first" depends on a property rather than the bare event name.

Example: first **successful** payment:
`{"property":"status","op":"=","value":"success"}`

Apply the filter **before** taking the user's first occurrence. Otherwise `min(date)` may select the first failed/nonqualifying event.

If the required property does not exist and no alternative event can isolate the cohort, do not fabricate the cohort. Fall back to a defined `period_active` question or request/upload a precomputed cohort list.

## Outcome filter

Outcome filters are independent from cohort filters.

"first diamond purchase → any repurchase" needs a cohort filter for diamond and no outcome filter.
"first diamond purchase → diamond repurchase" needs both.

Do not silently copy a cohort filter to the outcome side unless the user explicitly means the same subtype.

## Time semantics

- State fixed calendar periods explicitly.
- Do not confuse rolling windows such as "last 7 days" with fixed dates.
- A and B inference periods must be disjoint and ordered unless the user explicitly defines a different design.
- Keep timezone semantics consistent within one run.


## TE date/time note

When SQL uses `"$part_date"`, treat it as the project's pre-materialized analysis-date field. Keep one timezone convention across A/B. Do not imply that an ad-hoc `--zone-offset` retroactively changes already stored `$part_date` slicing. If true UTC/raw timestamp slicing is required, use the appropriate raw event-time field rather than pretending `$part_date` is UTC.

## Ambiguous retention definition

If it is unclear whether the team's “day N retention” means `exact_day` or cumulative `within_window`, do not silently choose when the distinction may be material. If cheap, compute both variants and surface the difference; otherwise confirm the business definition before inferential testing.
