---
name: ae-user-value-risk-analyst
description: Prioritize users for retention by combining decay risk with recent value, including in-app purchases and ad revenue. Use for early-warning signals on users whose activity or payment is declining relative to their own baseline, predicting which active users will go silent, ranking whom to retain first when retention budget is limited, deciding which already-inactive or churned users are worth winning back by payment recency, and complete churn-status summaries for a selected audience.
metadata:
  version: "6.1"
---

# User Value Risk Analyst

## Step 1. Choose the workflow

| User question | Workflow |
|---|---|
| Who to retain first given recent payment or ad value | Use the decay and value priority workflow in Step 3. |
| Who will reach a silence threshold or what is the status of a selected audience | Use the silence-churn workflow in Step 3. For authoritative audiences, read [Complete Audience Results](references/audience.md). |
| Which already-inactive users are worth winning back | Use the winback value ranking workflow in Step 3. |
| Rolling silence-churn backtests, lead time, calibration diagnostics, or offline experiments | Read [Evaluation and Retention Experiments](references/evaluation.md). For decay, read the held-out results in the decay summary. |

## Step 2. Prepare the data

The scripts use local CSV exports. Resolve project data through ae-analysis or ae-cli as needed. Two data shapes exist: the decay and silence-churn workflows consume an event export (user_id,event_name,event_time, one row per event); the winback workflow consumes a user-level aggregate (one row per user with last-login, last-activity and payment-window columns), prepared with Winback Aggregate Export.

Use the active Python environment if it has the required packages. For a fresh environment, run:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
```

Install `shap` and `matplotlib` when full feature explanations or plots are needed. LightGBM and XGBoost are optional model candidates.

- Reuse confirmed business definitions. Resolve the project, user identity, timezone, included events, and value sources before scoring. Record the chosen mapping and independently verified data coverage.
- Export `user_id,event_name,event_time` with opaque string user IDs. Include `session_id` if available. The feature engine derives sessions using a 30-minute gap when absent.
- Use `analysis sql-table list --usage analysis` to discover the authorized table and its exact `sql_reference`. Preview with `analysis adhoc run --preview-rows 100`, then export using `analysis adhoc export --model-type sql`. Decompress a gzip export before running the scripts.
- Trim the export to the declared `[start, end)` interval: silence-churn preflight blocks event rows outside the declared coverage, while the decay CLI silently filters rows to the snapshot, so never rely on silent filtering to drop rows. Historical label windows (training, backtests, held-out evaluation) require full-day endpoints so every label window is complete. An operational status snapshot may use the live query instant as T and as the coverage end; declare that instant and trim to it. Keep one set of bounds for all workflows in the same analysis.
- Activity criterion `any` requires the full agreed activity scope. For a bounded sample, sample users deterministically and keep their full event histories.
- Discover the actual revenue events, amount fields, and queryable sources in the target project. Confirm unresolved mappings, currency, or units with the user before scoring with that source. Map verified amounts to `pay_amount` and a separate ad column such as `ads_revenue`. Use zeros for events outside each source and resolve missing amounts on applicable events. [Revenue source discovery](references/project-data.md#resolve-revenue-sources)
- For exports with multiple UTC offsets, keep each row's explicit offset and use the confirmed IANA project timezone. The scripts convert those instants to the project calendar. Pass explicit offsets on cutoffs and coverage bounds too. If the project timezone or any offset-free timestamp's source is ambiguous, confirm it and prepare a consistent export before scoring. Rows without a source offset cannot carry an explicit offset: verify whether they are in-scope user activity, then export them with a resolved offset or exclude them and record the excluded row count and reason in the export notes. [Timestamp handling](references/project-data.md#timestamps-and-project-calendar)
- For new silence-churn projects, declare the source mapping and verified coverage with `--project-config` using [Project Mapping and Data Preflight](references/project-data.md). Scoring must match the saved definition. Older models may report unverified source semantics.
- Use `--data-kind simulated` for simulated exports, including demo or seeded projects exported from the live project table when the evidence shows generated data (batch ingestion timestamps, near-deterministic patterns, near-perfect separability). When that provenance is uncertain, keep `data_kind` unknown and record the uncertainty. Synthetic and demo runs validate workflow behavior only; never present their near-perfect metrics as expected real-world performance.

## Step 3. Run the selected workflow

Use a fresh output directory for each scoring snapshot.

### Decay and value priority

At cutoff T, the personal baseline uses W days ending R days before T. The decay label is met when the user's rate in the next H days falls below X times the baseline rate.

| Setting | Default | Meaning |
|---|---|---|
| `--window-days W` | 45 | Personal baseline window |
| `--recent-days R` | 14 | Recent window for the rule's current signal and trend |
| `--horizon-days H` | 14 | Future label window |
| `--decay-ratio X` | 0.3 | Fraction of the personal baseline |
| `--decay-criterion` | `any` | `any` counts active 24-hour bins from the start of each window. `pay` uses `pay_amount` per day. |
| `--value-cols` / `--value-days V` | `pay_amount` / 30 | Sum the configured columns over the last V days. Include ads explicitly when in scope. |
| `--min-baseline-days` | 5 | Minimum baseline active days for `any`. For `pay`, the baseline payment total must be positive. |
| `--train-snapshots` / `--gate-snapshots` | 6 / 3 | Historical training and held-out snapshots to attempt |

#### Check coverage and run scoring

- `--snapshot` defaults to the exclusive coverage end. Provide `--data-start` and `--data-end` after verifying continuous coverage against the upstream export or partition records. Optionally record the source of this verification with `--coverage-evidence`. If either bound is inferred from observed events, the script skips training and held-out evaluation and returns a provisional rule ranking.
- Scoring and held-out snapshots each require max(W + R, V) days of history. Training requires W + R days before each cutoff. The default nine historical snapshots require 185 days before T to attempt them all. Every historical label ends by T, and training label windows end by the earliest held-out snapshot. With the defaults, the model path needs at least W + R + H×(G+1) ≈ 115 days of attested continuous coverage, and two valid held-out snapshots alone need W + R + 2H ≈ 87 days; younger projects fall back to the rule with the reason recorded in the gate summary. Shorten W/R/H/V only as a confirmed redefinition and state the change in the delivery.

This example uses timezone-naive timestamps, verified export boundaries, and
two confirmed value columns. For offset-aware exports that cross offsets, add
`--timezone` with the confirmed project timezone and give full offset-aware bounds.

```bash
.venv/bin/python scripts/decay_value_risk.py --events events.csv \
    --data-start 2026-04-01 --data-end 2026-11-01 \
    --value-cols pay_amount,ads_revenue --output-dir outputs/decay
```

The ranking uses `value_priority_score` = `risk_score` × max(recent value, 0).
`risk_tier` reflects relative value priority. Users with nonpositive recent
value remain Low even when their underlying decay risk is high. Probability
estimates and forecast losses in currency require separate validation.
If V extends beyond W, baseline-qualified users with positive value in V can
enter the list with a rule score even when they have no events in W. The
held-out comparison applies the same eligibility and fallback rules.

- `decayed` indicates that the recent rate is already below X times the personal
  baseline. Use it to describe observed decay.
- `decaying` flags an early-warning trend among users who have yet to meet the
  `decayed` threshold. The latter part of the recent window falls below 70% of
  the earlier part's rate and below the personal baseline.

For activity-based decay, check whether a low personal baseline makes zero
future active days the only outcome that meets the decay label.

### Silence churn and audience status

#### Define the target and cohort

Define historical observation W (`--churn-days`), continuous inactivity D (`--churn-inactivity-days`), and prediction horizon H (`--prediction-days`). Set the activity criterion to `any`, `core` with `--core-events`, or `pay`. Select the target and cohort explicitly for new work.

- `churn_onset` predicts the first time a user reaches D days of inactivity in [T,T+H). Use `prevention`. A deadline at T+H is outside the label. Activity exactly at a deadline still completes the D-day gap.
- `window_inactive` predicts zero qualifying activity in [T,T+H). Choose `all`, `prevention`, or `winback`. Prevention requires known prior qualifying activity less than D days ago. Win-back covers D or more days. The all cohort includes users with events in [T−W,T).
- Older D-only commands keep H=D and the original fixed-window semantics.

#### Train or reuse a model

Reuse a saved model with matching source mapping, feature reference, and label
definitions. For a new project, add `--project-config` to the examples below.
[Project-specific commands](references/project-data.md#train-evaluate-and-reuse)

When training, set each labeled snapshot's `--obs-end` to T+H. Calibrate on a separate snapshot
and report paired metrics on a later holdout. Training labels must end by
calibration T, and calibration labels must end by test T. Training saves
`churn_model.pkl` and marks fitted scores as `training_snapshot`.

```bash
.venv/bin/python scripts/run_pipeline.py --events events.csv --data-end 2026-09-01 \
    --churn-days 30 --churn-inactivity-days 14 --prediction-days 7 \
    --label-target churn_onset --cohort prevention --label-criterion any \
    --obs-end 2026-08-04 --calibration-obs-end 2026-08-18 --test-obs-end 2026-09-01 \
    --model-type logistic_regression --output-dir outputs/validated
```

#### Score an operational snapshot

- Set `--obs-end` to T. T must be at or before the current time in the declared project calendar.
- For a selected batch, tag, group, or all-user delivery, obtain the authoritative member inventory and pass it as `--audience-users`. Score against the saved feature reference. Resolve the latest verified qualifying activity before checking cohort membership, onset reachability, and Top-K eligibility. When this reveals a missing event inside the feature window, keep the observed state and report insufficient event history for scoring. [Complete Audience Results](references/audience.md#score-while-keeping-the-feature-reference)
- For onset scoring, the final probability is zero when the earliest inactivity deadline is at or after T+H. These users remain in the results and are excluded from contact candidates. Check remaining lead time and compare against same-criterion recency. [Onset Reachability and Operational Lead Time](references/evaluation.md#onset-reachability-and-operational-lead-time)
- High/Medium thresholds start at 0.6/0.3. Add `--top-k` to a score run when the user requests a shortlist or gives capacity. It writes `contact_candidates.csv` alongside the complete result.

```bash
.venv/bin/python scripts/run_pipeline.py --mode score \
    --model outputs/validated/churn_model.pkl --events events.csv \
    --obs-end 2026-09-01 --data-end 2026-09-01 \
    --audience-users audience.csv --output-dir outputs/score
```

### Winback value ranking

Rank users with no login in the last D days by payment recency tiers. Build the
user-level aggregate with exact instant windows at cutoff T (SQL template:
[Winback Aggregate Export](references/audience.md#winback-aggregate-export)), then:

| Setting | Default | Meaning |
|---|---|---|
| `--cutoff` | required | Exclusive snapshot instant the aggregate was computed at; use explicit offsets with the SQL export below |
| `--timestamp-timezone` | none | Explicit source zone for older offset-free aggregates (for example `UTC`); never inferred |
| `--inactive-days D` | 14 | Winback means no login in [T-D, T) |
| `--value-days V` | 30 | Recent payment window [T-V, T); previous window [T-2V, T-V) |
| `--data-kind` | none | Declare `simulated` for demo/generated exports |

Tiers: `T1_paid_recent` paid in [T-V, T); `T2_paid_prior` paid in the previous
V-day window only; `T3_dormant_payer` paid earlier only; `T4_never_paid` no
recorded payment. The aggregate must use the same T and V; ranking inside the
population is tier, `pay_total`, `pay_recent`, then days since login.

```bash
.venv/bin/python scripts/winback_value_ranking.py --users user_agg.csv \
    --cutoff '2026-11-24 10:26:58+08:00' --inactive-days 14 --value-days 30 \
    --data-kind simulated --output-dir outputs/winback
```

The SQL template emits ISO 8601 UTC timestamps with explicit offsets. For an
older verified UTC export without offsets, add `--timestamp-timezone UTC`;
`--timezone` alone does not localize naive timestamps. Preserve one row per
opaque user ID; duplicate IDs block ranking. Missing last activity is unknown,
not observed silence. [Export and time contract](references/audience.md#winback-aggregate-export)

## Step 4. Verify and deliver

- **Decay**. Read `work/decay_value_risk_summary.json` for coverage, signals, and the gate result. Show eligible users as a share of users with pre-cutoff history, explain exclusions, and report the number scored by each source. Report observed decay (`decayed`) and early-warning trends (`decaying`) separately.
  - Model selection requires at least two paired holdouts with both AUC and measurable top-10% value capture. The model's mean AUC must be at least the rule's mean AUC plus `--gate-auc-margin` (default 0.02), and its mean capture must meet or exceed the rule's. Capture measures the share of actual decayed users' recent positive value reached by the top 10% of the value-priority ranking. Explain why the rule was used when evidence or metrics fell short.
- **Silence churn**. Read `work/prediction_metadata.json` for coverage, validation and data quality. With `--diagnostics`, the metadata file is at the run directory root. Audience-scored runs (`--audience-users`) must have one row per unique requested ID, with mutually exclusive `result_label` counts (risk levels plus already-churned, insufficient data, and incompatible states) matching the requested population. Plain train or score runs expose `risk_level` instead; check one row per scored user and its counts. Interpret historical validation separately from operational scores and note if calibration worsened the holdout metrics. Report `scoring_data_kind`, `model_training_data_kind`, and `model_calibration_data_kind` when available.
- **Winback value ranking**. Read `work/winback_value_summary.json` for the cutoff, population, tier counts and value at risk. Report payers as the worth-winning-back core, tiers and segments separately, and the payment recency behind each tier. The ranking is a transparent value rule, not a model probability.

By default, give the business summary in the reply in the user's language. Include the cutoff and
timezone, definition, population, coverage, key findings, and evidence limits.
Identify provisional rules, unverified coverage, and simulated or unknown
scoring or fit provenance where applicable. For a requested standalone summary,
save these findings as a single Markdown report and link it in **Output files**.

Omit **Output files** when the reply carries the full delivery. When the user
requests a downloadable list, include only the matching CSV by default.

| Requested list | CSV |
|---|---|
| Decay priorities | `decay_value_risk_result.csv` |
| Complete silence-churn status | `churn_prediction_result.csv` |
| Top-K contact candidates | `contact_candidates.csv` |
| Winback priorities | `winback_value_ranking_result.csv` |

For AE member access, verify membership and link the authorized assets. If the
requested member links are unavailable, explain why and link the local result.
[AE status-group delivery](references/audience.md#ae-status-group-delivery)

Keep run metadata and the reusable model as working artifacts. Share a model,
detailed report, diagnostics, or multiple lists only when requested. Use `--report`
for the decay script's report with ranked user rows and `--diagnostics` for
silence-churn evaluation, personas, model explanations or strategy reports.
Diagnostics preserve intermediate files in the run directory. Use
`--skip-explain` to omit SHAP explanations, which describe base-model associations.

Forecasts cover the configured horizon. Validate predictive performance on real
holdouts from the target project. Contact execution uses its own authorized
workflow. For follow-up analysis, use
`engagement-effectiveness-analysis` for campaign performance and
`propensity-score-matching` for observational estimates of intervention effects.
