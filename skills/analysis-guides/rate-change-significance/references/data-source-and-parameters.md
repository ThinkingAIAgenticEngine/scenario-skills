# Data Source and Parameters

## Data-source priority

Resolve in this order and stop at the first usable source.

1. **Currently selected TE project**
   - Exactly one selected project: use it directly; do not ask for its ID again.
   - Multiple or no selected projects: list accessible projects with `ae-cli project info list` (with optional `-q <keyword>` filter and `-l <limit>`) and let the user choose one. Do not guess, merge, or average projects. Do NOT use `ae-cli analysis project-space list` — it requires `--project-id` up front and is not a project-discovery command.
2. **Uploaded CSV/Excel**
   - Independent/period-active long format: `user_id`, `group` (`A`/`B`), `outcome` (`0`/`1`).
   - Paired wide format: `user_id`, `group_A_outcome`, `group_B_outcome`.
   - A precomputed cohort user-id list may be used when an event/property combination cannot reconstruct the intended cohort.
3. **Aggregate-rate mode**
   - Accept `n_A`, `outcome_A` (or rate), `n_B`, `outcome_B` when user-level data are unavailable.
   - State that overlap/duplicate-user diagnostics and matched-pair analysis are unavailable. Treat the comparison as an aggregate independent-rate analysis only.

## Parameters

Required before extraction/testing:
- Group A time range
- Group B time range
- observation window `N`
- cohort event (explicit for custom; preset may suggest but should not silently invent when ambiguous)
- outcome event

Optional:
- scenario
- cohort design
- cohort filter
- outcome filter
- expected A allocation ratio for concurrent A/B
- timezone override only when the user explicitly requires one

Derived; do not ask merely because the script needs them:
- `design_type`: `pre_post` or `concurrent_ab`
- period lengths
- `window_mode`
- overlap rate when count + group sizes are available

## Aggregate-only limitation

When only aggregate counts/rates are available, report:
"Overlap detection unavailable; treated as independent (aggregate-rate mode)."

Do not pretend that a high-overlap or paired question has been validated from aggregate totals alone.


## Uploaded-data schemas

### Schema 1 — independent/period-active long format
Required columns: `user_id`, `group`, `outcome`.
- normalize group to exactly A/B;
- outcome must be binary;
- no duplicate `user_id` within a group.

### Schema 2 — paired wide format
Required columns: `user_id`, `group_A_outcome`, `group_B_outcome`.
- one row per matched user;
- both outcomes binary;
- compute McNemar a/b/c/d locally.
- per-period active denominators are unavailable unless separately supplied, so paired representativeness cannot be inferred from this schema alone.

### Schema 3 — precomputed cohort list
Use when event data cannot reconstruct the intended first-occurrence cohort because the qualifying property/event is unavailable.
- uploaded list defines cohort membership, so `cohort_filter` is not reapplied;
- `outcome_filter` still applies to outcome extraction;
- supports independent/period-active comparison; use Schema 2 for paired outcomes.

## SQL failure fallback

If the SQL capability/table cannot be resolved or execution returns a query/parameter failure:
- first_occurrence/period_active → aggregate-rate mode is allowed but loses user overlap diagnostics;
- paired → aggregate totals are insufficient for McNemar; require matched user-level data/Schema 2 rather than pretending the design is paired.
