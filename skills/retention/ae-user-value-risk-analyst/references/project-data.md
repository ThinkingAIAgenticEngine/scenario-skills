# Project Mapping and Data Preflight

Read this before training a customer model or adapting an export to another
project. Use `--project-config project.json` with `run_pipeline.py` and
`backtest_churn.py`. Configured models require a current export declaration at
scoring time. Older models remain usable without one, with explicit warnings.

## Resolve the Business Mapping

Use AE metadata through `ae-analysis` to resolve the person identifier, event
dictionary, properties and timezone. Reuse mappings already confirmed for the
project. Ask the user for a decision when the available evidence leaves a
material ambiguity.

- A game's meaningful activity might be login, battle or level participation;
  a social product might use reading, posting or messaging. These are examples,
  not automatic defaults. Exclude heartbeat/aggregate/system events only with
  evidence. Merely observing a name does not establish its business meaning.
- Keep the activity definition, core-feature events and payment mapping explicit.
  `label_criterion=core` changes the target/cohort clock; it does not restrict all
  features to core events. Generic features use all exported allowed events.
- Export canonical `user_id,event_name,event_time` with `session_id` when available
  and any confirmed revenue columns. This configuration validates the mapped
  export. Apply aliases and event filters when preparing the CSV.
- Event names must match metadata exactly. A configured name absent from the
  catalog is an error. A valid event with zero observations in the current history
  is a warning requiring investigation, not proof of a broken mapping.

## Resolve Revenue Sources

For each revenue source in scope, identify the actual event or data source and
the property that measures revenue. Use `ae-cli analysis-meta event list` and
`ae-cli analysis-meta property list --scope event --event-name <confirmed-event>`
with the target `--project-id`. Verify queryable fields with
`ae-cli analysis sql-table list --usage analysis` and
`ae-cli analysis sql-table columns --usage analysis --table-ref <sql_reference>`.
An event property may be backed by a virtual calculation or a dimension table.
Check the SQL schema before referencing it as a column.

- Record the measurement represented by each field, its grain, its currency
  and unit, and the conversion used. Apply the project's confirmed conversion
  policy before summing value columns, including for minor currency units or
  mixed currencies.
- For a derived or dimension-backed amount, use a verified join or another
  authorized event-level export. Confirm the join key and grain, preserve the
  intended activity rows and check for unmatched values or duplicated revenue.
  If a required source is unavailable, report the gap and confirm any narrower
  value scope before using it.
- Map verified payments to `pay_amount`. Map verified ad revenue to a separate
  column such as `ads_revenue` and include that column in `--value-cols` when
  requested. Use explicit zeros only outside the revenue source or for a
  measured zero. Preserve missing values on applicable revenue events and
  resolve them before scoring with that source.

## Example Event Export

Replace placeholders with the authorized SQL table, queryable columns, and
confirmed expressions for the project. Include each revenue projection only
when its mapping and normalized units are verified. The following template uses
both sources and expects SQL timestamp literals that match the source calendar
and column type.

```sql
SELECT CAST(e."<person_id_column>" AS VARCHAR) AS user_id,
       e."<event_name_column>" AS event_name,
       e."<event_time_column>" AS event_time,
       CASE WHEN <confirmed_payment_event_predicate>
            THEN CAST(<normalized_payment_expression> AS DOUBLE) ELSE 0.0 END AS pay_amount,
       CASE WHEN <confirmed_ad_revenue_event_predicate>
            THEN CAST(<normalized_ad_revenue_expression> AS DOUBLE) ELSE 0.0 END AS ads_revenue
FROM <exact_sql_reference_returned_by_discovery> AS e
WHERE e."$part_date" BETWEEN '<first_partition>' AND '<last_partition>'
  AND e."<event_time_column>" >= <start_timestamp_literal>
  AND e."<event_time_column>" < <end_timestamp_literal>
  AND e."<person_id_column>" IS NOT NULL
  AND <confirmed_activity_scope_predicate>
```

Keep the full agreed activity scope for the `any` criterion. Confirm the
timestamp coverage separately from the partition filter. Select partition dates
that include the entire half-open timestamp interval.

## Timestamps and Project Calendar

Use the project's confirmed IANA timezone for calendar features such as evening
activity, weekends and activity dates. For aware exports, keep the original
instant by including the offset on every timestamp. A project in `America/New_York`
can contain both `-04:00` and `-05:00`, and an upstream UTC export can also be
used. The scripts convert these instants to the declared project calendar before
computing features. Cutoffs, coverage endpoints and audience evidence must also
have offsets when events are aware. Elapsed durations still use actual 24-hour days.

Supply `timezone` in `--project-config` for silence-churn scoring and backtests.
Use `--timezone` for the decay CLI. A single-offset export without a named zone
keeps its existing fixed-offset calendar. Legacy `naive_local` data retains its
wall times. For data spanning a clock change, use aware timestamps to distinguish
repeated wall times and measure elapsed gaps. When a source mixes aware and
offset-free values, confirm how the offset-free times were recorded and repair
the source export. Resolve the business calendar if multiple real source zones
contribute events to the same analysis.

## Configuration

Example for a game with measured payments; replace identifiers and mappings with
the confirmed project definition. Coverage is optional and must never be invented.

```json
{
  "schema_version": 1,
  "project_id": "confirmed-project-id",
  "identity_field": "#user_id",
  "timezone": "Asia/Shanghai",
  "timestamp_mode": "naive_local",
  "event_catalog": ["login", "battle", "payment", "online"],
  "event_scope": {"include": [], "exclude": ["online"]},
  "core_events": ["battle"],
  "payment": {
    "mode": "measured",
    "events": ["payment"],
    "source_field": "pay_amount",
    "currency": "CNY"
  },
  "session_mode": "derived",
  "feature_reference": "all project users eligible under the saved model cohort",
  "sampling": "all_users",
  "coverage": {
    "start": "2026-08-01T00:00:00",
    "end": "2026-11-01T00:00:00",
    "verified": true,
    "evidence": "Replace with independently checked ingestion/export coverage evidence"
  }
}
```

- `event_catalog` is the resolved event dictionary relevant to this source
  definition, including exclusions. Empty `include` means all catalog events
  except `exclude`. Otherwise only the listed inclusions are allowed. Excluded
  or undeclared rows cause a blocker; apply the confirmed filter in the export.
- `core_events` can be `[]` when not configured. Core placeholders then indicate
  a disabled feature family, not observed absence of core behavior. Core labels
  require a nonempty mapping.
- `payment.mode=measured` requires complete finite `pay_amount`, nonnegative
  payment amounts, and explicit zeros outside the mapped payment events. Do not
  put balances, prices, refunds or unrelated currencies into this field. Resolve
  missing amounts in the source; never fill missing payment measurements with 0.
- Use `payment: {"mode": "not_applicable"}` for a product without the relevant
  payment business; `{"mode": "unavailable"}` means measurements are unavailable.
  Both disable monetary inputs and require omitting the amount column or supplying
  only explicit zeros. The stable 35-column schema retains constant placeholders,
  reported as disabled inputs. Pay labels are prohibited. Changing availability
  or restoring payments requires a newly trained and validated model.
- `session_mode=provided` requires complete, nonempty session IDs. `derived`
  requires omitting that column and uses the saved session-gap setting.
- `timestamp_mode=naive_local` declares local wall times; `aware` accepts timestamps
  with explicit offsets and converts them to the declared project calendar.
  Use matching awareness for events and endpoints. [Timestamp handling](#timestamps-and-project-calendar)
- `feature_reference` defines the population used to compute percentiles,
  z-scores and pay tiers, before filtering the requested audience. `sampling`
  records full-user coverage or the exact deterministic sampling rule. These
  declarations cannot prove that the supplied CSV actually contains every
  reference user; retain the export query and source manifest as evidence.
- Verified `coverage` uses [start,end). It must contain at least max(W,D) days
  before T and, for labels, the full [T,T+H) window. The rolling backtest skips
  cutoffs outside that interval and records the reason. Rows outside the
  declared export interval are blocked. Coverage supplies omitted bounds.
  Conflicting bounds are errors.
  For core/pay winback, older qualifying history may still be needed. Missing
  coverage yields a warning, not fabricated completeness evidence.

For a non-monetized social project, use its confirmed event catalog and core
actions, `payment: {"mode":"not_applicable"}`, and the same explicit identity,
timezone, reference and coverage decisions. Do not copy game event names.

## Train, Evaluate and Reuse

Add the declaration to an otherwise confirmed training/backtest command:

```bash
.venv/bin/python scripts/run_pipeline.py --events events.csv \
  --project-config project.json --churn-days 30 \
  --churn-inactivity-days 14 --prediction-days 7 \
  --label-target churn_onset --cohort prevention --label-criterion any \
  --obs-end 2026-10-01 --model-type logistic_regression \
  --output-dir outputs/project_train

.venv/bin/python scripts/run_pipeline.py --mode score \
  --model outputs/project_train/churn_model.pkl --events scoring_events.csv \
  --project-config scoring_project.json --audience-users audience.csv \
  --obs-end 2026-11-01 --output-dir outputs/project_score
```

Core events are inherited from the declaration when the CLI omits them. Overrides
must agree. Separate calibration/test CSVs require their own
`--calibration-project-config` / `--test-project-config`; semantic mappings must
match, while their verified coverage intervals can differ.

The model stores the normalized semantic contract. Scoring compares project,
identity, timezone, event scope/catalog, core and payment mapping, session mode,
reference population and sampling. Coverage and notes are excluded from the
semantic comparison. Changed semantics require restoring the old definition or
retraining and future validation; editing a model's stored declaration does not
validate the change. A declaration added only at scoring cannot retrospectively
verify a legacy model's training export.

Inspect `work/data_quality_report.json` before interpreting pipeline scores.
The pipeline's `--diagnostics` mode and the standalone backtest use the flat
path `data_quality_report.json`. Blockers stop the pipeline before new
features, models or scores are generated. Warnings are propagated into
prediction metadata and any requested strategy report. Fix a blocked export
and rerun into a fresh output directory.
The checks establish declared consistency and observable data conditions, not
automatic semantic understanding, source authenticity or production readiness.
