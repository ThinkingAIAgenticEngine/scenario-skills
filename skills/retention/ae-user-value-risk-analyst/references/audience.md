# Complete Results for a Selected Audience

Use this workflow when users want results for every member of an AE tag, cluster,
registration cohort or supplied ID list, including users already inactive for D
days. The model's prevention/winback cohort still determines who can receive its
future prediction. The audience determines who must appear in the result table.

## Resolve and Freeze the Audience

Use `ae-analysis` for AE metadata and member retrieval; follow its discovery and
export references rather than guessing table names or iterating preview pages.
For a tag, identify the exact tag and desired tag value, not merely all users with
any value. For a registration cohort, resolve the authoritative registration
property/event; observed `tenure_days` is not registration age.

Save a CSV with `user_id` as a string. IDs must use the same entity and identity
as the event export. The full requested list is authoritative, including users
without event rows. Duplicate IDs are collapsed in first-occurrence order and
counted in coverage; invalid IDs or conflicting snapshot evidence are rejected.

Optional columns:

- `snapshot_time`: each value must match scoring T. For historical evaluation,
  use membership available at T; a current dynamic group does not prove past
  membership. Record AE resource, tag value, time/version and identity mapping
  in the source manifest. Do not invent unavailable historical versions.
- `last_qualifying_event_time`: a verified last activity strictly before T,
  under the saved activity criterion. This supports old users whose activity
  predates the exported feature window. Use the latest qualifying activity
  across the event export and the verified audience snapshot. The evidence must
  match the saved activity criterion and scoring cutoff. Missing values remain
  unknown if both sources lack qualifying activity.
- `data_kind`: provenance propagates conservatively into scores and candidates.

Other audience columns are not model features and are not copied into the final
result. Keep richer source metadata with the audience manifest.

## Score While Keeping the Feature Reference

```bash
.venv/bin/python scripts/run_pipeline.py --mode score \
    --model model/churn_model.pkl --events events.csv \
    --audience-users audience.csv --obs-end '<snapshot-T>' \
    --output-dir outputs/audience_score
```

This default delivers the full audience. Add `--top-k K` only for a requested
priority list or stated contact capacity; K never limits the delivered audience.

The option is restricted to score mode; it does not change model training or its
saved W/D/H/criterion/cohort. Use a model trained and validated for the requested
project, population and horizon. Selecting a different N does not convert an
existing H-day model into an N-day model.

The pipeline computes `reference_user_features.csv` from all supplied events
under the saved cohort, then filters feature rows to the audience. Relative
features (percentiles, z-scores and pay tiers) keep that reference. Supply the
same reference scope as the saved workflow; the program cannot infer whether a
CSV was already narrowed upstream. Do not silently prefilter source events to
the target IDs if that changes the feature reference. A separately trained and
validated audience-specific model may use its own consistent reference.

The pipeline resolves verified audience clocks before applying the saved cohort
filter to the reference features. It never synthesizes events from those clocks.
For legacy heuristic bundles, min/max normalization also uses this complete
reference before audience filtering; requesting one user must not reset their
risk score to zero. Standalone `predict_churn_risk.py` callers selecting a subset
must pass the same snapshot's full `--reference-features` CSV.

`user_features.csv` contains only audience users with compatible model features.
A newer verified qualifying activity inside [T−W,T) reveals a missing feature
event. Keep that user's observed state, mark the missing event, and leave the
score blank until the event history is complete. If the verified activity
predates the feature window, use it for the clock and reuse compatible feature
rows. `scored_prediction_result.csv` contains the scored subset used for Top-K.
These intermediates are temporary by default. Use `--diagnostics` to retain
them at the run directory root.

## Complete Output and State Semantics

`churn_prediction_result.csv` contains exactly one row per unique requested ID,
in audience order, with these additional fields:

| Field | Meaning |
|---|---|
| `current_status` | `already_churned`, `not_churned`, or `unknown` at T |
| `result_label` | already_churned / churn_risk_high, churn_risk_medium, churn_risk_low / insufficient_data / not_applicable_to_model |
| `prediction_status` | Whether scored, outside the saved cohort, missing qualifying history or an event from the feature window, or lacking a feature row |
| `status_reason` | Reason for the state/score outcome |
| `last_qualifying_event_time`, `last_activity_source` | Exact pre-T clock and its evidence source |
| `inactivity_days` | Exact elapsed time; empty when unknown |
| `churn_probability`, `risk_level` | Final future forecast after the onset bound; empty for unscored users |
| `model_probability` | Model output before the onset bound (after calibration if fitted); empty for unscored users |
| `onset_reachable_within_horizon`, `probability_constraint` | For onset, reachability for known pre-onset users and constraint reason for scored users. Unreachable scored users have final probability 0 and are excluded from contact selection. |
| `scoring_data_kind`, `model_training_data_kind` | Provenance of the score inputs and model training, respectively |
| `model_calibration_data_kind` | Provenance of the calibration dataset when calibration was fitted |

Legacy exports before the English-token update used Chinese labels. Map them when
reading old artifacts: 已流失 → `already_churned`, 流失风险高/中/低 →
`churn_risk_high`/`churn_risk_medium`/`churn_risk_low`, 数据不足 →
`insufficient_data`, 不适用当前模型 → `not_applicable_to_model`. Update downstream
value matching when mixing artifacts across that change.

With known last qualifying activity L, T−L≥D means observed already-churned,
including equality. Future events and events exactly at T cannot change pre-T
state. An unknown L is not proof of churn, even if no event was exported. The
completeness and coverage limitations of the source still apply.

For a prevention model, already-churned users have a status row and no future
probability. A valid winback/all `window_inactive` model may also score already-
churned users; the probability then describes future inactivity, while the
current observed status remains already-churned. Keep those meanings distinct.

`work/prediction_metadata.json` counts target users, deduplicated memberships,
scored/unscored users, observed states and result labels. Read the provenance
fields when preparing the user-facing summary. With `--diagnostics`,
working files use the original flat paths, and the pipeline also writes
`audience_coverage.json` and a strategy report. An empty scoring subset still
yields the complete status table and an empty candidate file if Top-K was requested.
An empty event export yields unknown states unless verified pre-T last activity
was supplied.

## AE Status-group Delivery

The default summary is a complete status table with counts. Add member-list
access when requested. Use the final `result_label`, not `risk_level` alone: already-
churned users may have a scored window-inactive probability, but their mutually
exclusive displayed status is still already_churned. Preserve all unscored statuses.
Include not_applicable_to_model when present; do not merge it into insufficient_data or low risk.

Python currently produces local reports/CSVs. It does not create AE groups/tags
or turn a local count into a native drilldown cell. The agent performs these
additional steps for AE delivery when within the user's authorized scope:

1. Freeze the scored batch: project, entity, original audience/version, snapshot
   T, W/D/H, activity criterion, target/cohort, model and data provenance. Keep
   the final result and partition its unique IDs by displayed status. A saved
   group is this prediction snapshot, not a continuously refreshed model.
2. Discover the current AE entity and import options through `ae-analysis`.
   Use its current cluster/tag and resource-link contracts instead of guessing
   request fields or URLs. For the primary user entity, imported values must
   use an allowed association property: internal `#user_id` is not accepted by
   the ID-import route. Resolve an authorized, unambiguous mapping; do not cast
   internal IDs into account IDs or assume account IDs are unique. Detect missing
   mappings and identity collisions before publishing. If mapping cannot preserve
   this batch's membership, report the blocker and keep the local complete result.
3. Persist one snapshot group per nonempty status, or a single status tag with
   one status value per user when that better fits the request. Discover existing
   assets before reuse; update only an exact asset authorized for the same scope.
   Use names/remarks that identify prediction T, horizon and original audience.
   Preserve previous batches unless replacement is explicitly intended. A zero
   count needs no empty asset and remains plain `0` in the table.
4. Poll the returned computation operation until complete, then verify member
   identities and deduplicated counts against each local status partition. Count
   equality alone cannot prove that the correct users matched. Check the union
   covers this batch and partitions do not overlap; retain any unmatched/ambiguous
   IDs with their reason. Do not show a submitted operation as a completed group.
5. Obtain real resource links with the supported asset URL capability. A link to
   the group/tag page may require one more click to see members; describe that
   accurately. A value-specific tag link must select that exact status. If only
   a generic tag page link is returned, label it as a tag-page entry rather than
   implying it opens the exact status list. Never construct query coordinates
   from local CSV rows: native result drilldown requires the platform's genuine
   query context and advertised actions.
6. Render verified status counts as Markdown links to their corresponding assets.
   Keep local-result counts distinct from matched AE counts if they differ; mark
   incomplete publication explicitly instead of presenting a partial AE group as
   the complete state population. Record the mapping evidence, expected/matched
   counts, member-check outcome, returned resource identity/link and operation
   status beside the run artifacts so the delivery can be checked later.

Reuse any authorization already given to publish this requested batch. A request
only to edit the skill, inspect results or export local files does not publish AE
assets. Do not execute engagement campaigns as part of saving a group. When AE
access, write authorization, identity mapping, matching or URL generation is
unavailable, finish the local delivery and state the specific remaining issue;
never mark a plain count as linked or an unsaved group as created.

The platform supports member access by clicking group counts and entering user
lists from tags; exact link targets depend on returned URLs and project access.
See [AE user groups](https://docs.thinkingdata.cn/ta-manual/latest/user_guide/user/cohort/cohort.html)
and [user lists](https://docs.thinkingdata.cn/ta-manual/v4.1/user_guide/analysis/user_list.html).

## Winback Aggregate Export

`scripts/winback_value_ranking.py` ranks users with no login in [T-D, T) by
payment recency tiers. It needs one row per user with `user_id`,
`last_login_time`, `last_activity_time`, `pay_recent`, `pay_prior` and
`pay_total`, computed with exact instant windows at the same cutoff T and the
same value window V passed to the script. Build it with a project-authorized
SQL export. For confirmed local `#event_time` values and offsets measured in
hours, use this **UTC wall-time** expression as `<instant_utc_expr>`:

```sql
date_add('second',
         -CAST(round(CAST("#zone_offset" AS DOUBLE) * 3600) AS BIGINT),
         CAST("#event_time" AS TIMESTAMP))
```

Convert the offset to seconds before rounding; never round it to whole hours.
This preserves offsets such as +05:30, +05:45 and -03:30. Do not apply this
conversion to an already-UTC or offset-aware source. Verify the source type,
offset unit and meaning first. Resolve missing source offsets or exclude their
rows only after verifying they are not in-scope activity and recording why.

The template below compares UTC wall times with UTC literals. Convert T, T-V
and T-2V to UTC first, then substitute `<T_UTC>`, `<T_MINUS_V_UTC>` and
`<T_MINUS_2V_UTC>`. For example, T `2026-11-24 10:26:58+08:00` becomes
`2026-11-24 02:26:58` in these SQL literals. Attach UTC and serialize the aggregate
timestamps as ISO 8601 strings with explicit offsets for the CSV and Python:

```sql
SELECT CAST("<person_id_column>" AS VARCHAR) AS user_id,
       to_iso8601(with_timezone(max(CASE WHEN <login_event_predicate> THEN <instant_utc_expr> END), 'UTC')) AS last_login_time,
       to_iso8601(with_timezone(max(CASE WHEN <qualifying_activity_predicate> THEN <instant_utc_expr> END), 'UTC')) AS last_activity_time,
       sum(CASE WHEN <payment_event_predicate> AND <instant_utc_expr> >= TIMESTAMP '<T_MINUS_V_UTC>' THEN <amount_expr> ELSE 0 END) AS pay_recent,
       sum(CASE WHEN <payment_event_predicate> AND <instant_utc_expr> >= TIMESTAMP '<T_MINUS_2V_UTC>' AND <instant_utc_expr> < TIMESTAMP '<T_MINUS_V_UTC>' THEN <amount_expr> ELSE 0 END) AS pay_prior,
       sum(CASE WHEN <payment_event_predicate> THEN <amount_expr> ELSE 0 END) AS pay_total
FROM <exact_sql_reference>
WHERE "$part_date" BETWEEN '<first_partition>' AND '<last_partition>'
  AND <person_id_column> IS NOT NULL
  AND <instant_utc_expr> < TIMESTAMP '<T_UTC>'
GROUP BY 1
```

Use the confirmed payment mapping and amount unit from the project definition.
Keep IDs opaque, including leading zeros and literal values such as `NA`. The
script rejects duplicate IDs, missing IDs and nonfinite/negative amounts.
Missing last activity stays unknown (`segment=unknown_activity`), not fully
silent. Users with no known login are excluded and counted separately.

For an older CSV containing offset-free UTC timestamps, explicitly add
`--timestamp-timezone UTC` and use an offset-aware cutoff. If the verified
source is another local zone, declare that zone instead; ambiguous/nonexistent
DST wall times must be resolved upstream. `--timezone` only selects the display
calendar of aware timestamps; it does not guess where naive timestamps came
from. A legacy all-naive CSV with an all-naive cutoff remains supported, but
must have one confirmed common time basis. Do not remove a cutoff's offset to
make an incompatible export run. Retain the export SQL and its T/V as evidence.
Tier definitions, ranking and summary fields are documented in the script
header and Step 3 of SKILL.md.

## Final Delivery Template

Write the answer in the user's language. For Chinese delivery, start with:

> Completed the churn-status analysis for this audience. Scoring snapshot is <T and timezone>,
> activity criterion is <qualifying activity>, the churn threshold is <D> consecutive silent days,
> predicting the next <H> days; the target scope is <selected batch>, <N> users in total.

Then provide a table with Status, Users, and Access. The example below describes the
format; replace each placeholder with verified output, never a sample URL:

| Status | Users | Access |
|---|---:|---|
| already_churned | Actual count | Verified member link, or explicit pending/unavailable reason |
| churn_risk_high | Actual count | Same status-specific entry |
| churn_risk_medium | Actual count | Same status-specific entry |
| churn_risk_low | Actual count | Same status-specific entry |
| insufficient_data | Actual count | Same status-specific entry, with missing-data reasons |
| not_applicable_to_model (when present) | Actual count | Same status-specific entry |
| Total | Unique requested audience count | Complete list entry if needed |

When a member link is verified, put it on the actual count, with the Access column stating
whether it opens members directly or the group/tag page. Show zero plainly.
When there is no link, use a plain count and explain the remaining issue; local
files are detail/download entries, not AE member-list links.

When the user needs the complete list and AE member access is unavailable, link
`churn_prediction_result.csv` as the single default attachment. For a count-only
request, the status table and data/evaluation limits are sufficient. State that
already_churned is the current observed state, missing probabilities remain empty, and
rule-constrained zeros only concern this horizon. Include feature associations
when an explanation was requested and obtained. State the scoring, training,
and available calibration sources separately.
If training/holdout reports exist, scope them to their own dates/population;
score-only delivery must not imply this new batch has mature outcome validation.

Append a priority/contact section only when requested; include K and actual
eligible candidates, keeping all status-group counts unchanged. Persona groups
and strategy suggestions are optional supporting views, not the five/six main
status groups. Saving prediction groups is not execution of an intervention.
