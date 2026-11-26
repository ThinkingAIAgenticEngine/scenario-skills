# Evaluation and Retention Experiments

Use this reference when validating a model, choosing an operational candidate
capacity, inspecting probability reliability, or evaluating retention intervention
outcomes. Confirm W, D, H, target, criterion and cohort before comparing results.
For a configured customer model, use the same `--project-config` semantics in
backtesting and training. Read [project-data.md](project-data.md) and inspect
the data quality report. An event mapping or payment-availability change is
not an interchangeable export of the old model's inputs.

## Chronological Training, Calibration and Test

Each labeled snapshot has features [T-W,T) and outcomes [T,T+H). The fit, calibration
and final test label windows are separated. The same user may occur at different
times; a test label cannot update the fitted model or calibrator.

Choose development and final test dates before comparing methods. Use development
folds to choose models, calibration and capacity policies; keep the final window
untouched until those choices are fixed. A standalone holdout can be independent
of fitting while sharing the last backtest's dates and outcomes. Disclose that
overlap: it is one source of outcome evidence, not two independent successes.
Once a final window has informed a new choice, evaluate that choice on a later
untouched window rather than relabeling the same data as final validation.

The standalone training API/CLI also checks known dates and rejects obvious reuse
of training/calibration rows, including copied subsets. Content checks catch
accidental reuse; they are not proof that a dataset comes from the future. Supply
`training_obs_end`, `calibration_obs_end`, `test_obs_end` and `prediction_days` in
`feature_config` where applicable. Reported `temporal_verified` and
`evaluation_scope` distinguish verified future snapshots from ordinary holdouts.

The pipeline's `--obs-end`, `--calibration-obs-end` and `--test-obs-end` specify
label-window ends. Thus each corresponding T is end-H. The rolling backtest's
`--snapshot-dates` instead specifies T directly.

`--calibration-method sigmoid` is the default. Isotonic is available but more prone
to overfitting small calibration sets. Evaluate calibration on the subsequent test
snapshot, not on the data used to fit it. Without a final holdout, report that
probability quality has not yet been independently tested.
Compare the raw and calibrated predictor on the same subsequent observations.
Carry that comparison, its time-verification scope, and any deterioration into
operational reports. A worse point estimate is not a statistical significance
claim. Do not automatically switch to the raw predictor on final-test results.

The model bundle retains both the scoring predictor and the underlying
`explanation_model`. CV metrics refer to the uncalibrated training classifier.
Future metrics include raw and calibrated results when calibration is enabled.

## Rolling Backtests

```bash
.venv/bin/python scripts/backtest_churn.py \
    --events outputs/validated/work/sample_events.csv --data-end 2026-09-01 \
    --data-kind simulated \
    --snapshot-dates 2026-07-14,2026-07-28,2026-08-11,2026-08-25 \
    --churn-days 30 --churn-inactivity-days 14 --prediction-days 7 \
    --label-target churn_onset --cohort prevention --label-criterion any \
    --top-k 80 --models recency_rule,logistic_regression,lightgbm \
    --output-dir outputs/backtest
```

For each eligible test date, choose the latest preceding calibration snapshot
whose labels have matured. Train on all earlier snapshots whose label windows
end before that calibration T. At least three appropriately separated dates are
needed for one evaluated fold. Each cutoff is checked for max(W, D) days of
history and a complete label window through T+H. Skip dates that fall outside
the coverage and retain the remaining dates. If no fold can be evaluated, the
run reports `no_valid_folds` and lists the skip reasons.

Use verified project coverage, or supply `--data-start` and `--data-end` after
checking continuous coverage. Missing boundaries fall back to the first and
last observed event timestamps. Metrics derived from inferred bounds have
unverified coverage and are exploratory.

Compare:

- `recency_rule`: last qualifying activity, with the same any/core/pay criterion.
- `logistic_regression`: simple supervised baseline.
- `lightgbm`: optional non-linear candidate. If unavailable, report unavailable;
  do not infer its performance. Fallbacks retain the actual trained model name.

The recency rule is a ranking score; its Brier/log-loss/calibration fields are
unavailable, since it does not produce calibrated probabilities.

Outputs:

- `backtest_metrics.json`: window boundaries, definitions, per-fold and per-group
  metrics, failed/unavailable models, and skip reasons.
- `backtest_summary.csv`: model/date comparisons.
- `backtest_calibration.csv`: future probability bins, observed rates and sample counts.
- `backtest_predictions.csv`: per-user future predictions, ranks and candidate flags.
- `backtest_report.md`: readable comparison and subgroup stability.

No model is automatically deployed from test comparisons. After development chooses
a method, validate it on one final untouched future period.

## Onset Reachability and Operational Lead Time

For `churn_onset/prevention`, let L be the last qualifying activity strictly before
T, and let exact recency r=T−L, in the same time units as D/H. Eligible users have
0≤r<D. Their current inactivity deadline is L+D, so onset within [T,T+H) requires
**r>D−H**. At equality the deadline is T+H and is excluded. Later activity can
prevent the current deadline; reachability is a necessary condition, not a
probability estimate or a sufficient label rule.

When H<D, users with r≤D−H are structurally unable to reach onset during H. Report
their share, and compare the model with the recency baseline both overall and
within the reachable subgroup. Use the same users, outcomes and K policy for
each comparison. Single-class subgroup AUC is undefined, even if Top-K precision
is 100%; its within-group lift may be only 1. Do not confuse easy separation of
reachable/ineligible deadlines with useful discrimination among reachable users.

The scorer, future-holdout evaluation and rolling backtest enforce this bound
after calibration. Such users receive final probability 0 and cannot enter the
contact list, even if K exceeds the reachable population. They remain in the
delivered audience with their risk tier and rule reason. `model_probability`
preserves the calibrated model output before this constraint; backtests preserve
`model_score` (the recency rule remains a ranking score, not a probability).
Feature exports carry exact `snapshot_time` and `last_qualifying_event_time` as
non-feature metadata; old onset feature files without these must be regenerated.
Unknown history never becomes a deterministic zero. `window_inactive` is unchanged.

`future_holdout_raw` and `future_holdout_calibrated` compare the model before the
constraint; `future_holdout` evaluates the final delivered probabilities and its
eligible contact pool. Reports show all three stages when applicable. These
deterministic zeros improve consistency, not evidence of added model skill.
SHAP describes the base model before calibration/constraint; explain rule zeros
separately rather than claiming SHAP sums to the final probability.

Compute this clock from exact qualifying timestamps, not the integer-day feature
`days_since_last_event`. Core/pay clocks must use the matching criterion and the
same source event exclusions. Use `scripts/diagnose_churn_onset.py` for an existing
single-snapshot prediction table and its source events; read `--help` for inputs.
This is a diagnostic, not a new model, candidate filter or estimate of an event's
actual future occurrence time.

For selected candidates, report the distribution of D−r (time remaining to the
current inactivity deadline), including how many deadlines are within 24/48/72
hours. Report snapshot T explicitly. If scoring is stale by age A and an action
requires lead time B, the remaining window is at most D−r−A; additionally account
for action delivery/effect latency. Before executing, refresh activity and cohort
eligibility. A user may already have crossed the deadline or returned since T.
Do not treat a fixed “Day 1” or “within 3 days” template as an executable schedule
without checking those constraints.

Ask for the minimum useful lead time when operational decisions depend on it.
Until it is known, report the distribution and the unresolved constraint; do not
silently remove near-deadline users, alter D/H, or rewrite the target. If the user
chooses a lead-time restriction, apply it consistently to baseline, model and
candidate evaluation and disclose the revised population.

Inspect observed active-day distribution and future return behavior when a score
is nearly perfect. A demo dominated by one-day users and almost no returns can
make recency effectively reproduce the target. That supports a pipeline check,
not production model superiority. Likewise, many equal rows after projecting
away event identifiers/properties cannot establish duplicate ingestion: retain
the original identifier when available and investigate before deduplicating.

## Capacity and Probability Diagnostics

K is the number of candidates the operation can review/include before control
allocation. Top-K selection uses scores from one snapshot and deterministic ties.

- Precision@K = actual churners among selected users / selected users.
- Recall@K = actual churners selected / all churners in that snapshot.
- Lift@K = Precision@K / snapshot churn rate.
- If K exceeds population size, select the whole population and report the actual
  count. With no positive cases, recall/lift are undefined, not zero evidence.
- Default 0.3/0.6 risk tiers should not determine a campaign budget without validation.
- Brier and log-loss assess probabilistic quality; inspect the calibration curve
  and bin counts as well. ECE is descriptive and sensitive to binning/sample size.
- Calibration can worsen a later test result. Compare raw/calibrated diagnostics;
  do not declare improvement simply because a calibrator was fitted.

With the pipeline's `--diagnostics` option, or when running the trainer CLI
directly, training writes `model_evaluation_report.md`, `calibration_curve.csv`
and a best-effort `calibration_curve.png`. The default pipeline keeps the
metrics in `work/model_metrics.json`. When only training CV exists, use it
as training evidence and report that future business performance is unverified.

For channel stability, pass `--user-properties user_properties.csv` and optionally
`--group-columns channel`. A static file has unique `user_id`; a snapshot file has
unique `user_id,snapshot_time` plus attributes available at that time. Attributes
are used only for grouping, never as model inputs. Group Top-K is recomputed within
each group and is distinct from the global candidate selection in prediction CSV.

## Offline Randomized Retention Evaluation

A risk model identifies likely outcomes under observed behavior. To measure the
incremental effect of a retention action, use randomized treatment and control
assignments and complete followup outcomes.

Prepare an offline assignment table from an operational scoring candidate file:

```bash
.venv/bin/python scripts/retention_experiment.py assign \
    --candidates outputs/score/contact_candidates.csv \
    --assigned-at 2026-09-01 --control-fraction 0.2 --seed 42 \
    --output outputs/experiment/assignments.csv
```

For decay, first prepare the eligible shortlist at the requested capacity
from the value-priority result. The assignment script accepts that shortlist
with unique `user_id` values and preserves its data provenance.

The tool writes a fixed-quota randomized assignment manifest next to the CSV.
For simulated candidates/outcomes, use `--data-kind simulated` or retain their
`data_kind` column. Simulation metadata propagates to the manifest and report;
simulation results validate computation and do not establish real causal effects.
Candidate CSVs can also record model training and calibration provenance. Use
those fields to describe how the shortlist was scored. Experimental data
provenance follows the candidate data and observed outcomes.
Analysis verifies the saved assignments against the manifest fingerprint and
replays the recorded seed to check the allocation.
The candidate pool must contain at least two unique users so both arms exist.
A candidate capacity of 80 with a 20% control fraction leaves approximately 64
treatment users; the remaining users are controls. No messages are sent.

Execute the agreed action through an authorized external process. After the agreed
outcome window matures, supply `outcomes.csv`:

```csv
user_id,retained,revenue,cost
u00001,1,30,2
u00002,0,0,0
```

Here retained is a predefined binary retention outcome; revenue/cost are optional.
Its followup length is independent of the model's D/H. Do not fabricate missing
outcomes or remove assigned users who did not receive/click a message.

```bash
.venv/bin/python scripts/retention_experiment.py analyze \
    --assignments outputs/experiment/assignments.csv \
    --outcomes outcomes.csv --outcome-days 14 --data-end 2026-09-15 \
    --output-dir outputs/experiment
```

Every original assignment must have one complete outcome, group identities must
remain unchanged, and assigned_at+outcome-days must be within verified coverage.
This preserves intention-to-treat. Missing users and immature outcomes cause a
clear error rather than an invented outcome or a filtered comparison.

The report provides group rates, absolute percentage-point difference, relative
lift, a confidence interval, a Fisher exact p-value and allocation diagnostics.
Optional monetary columns yield point estimates for incremental revenue/cost/profit.
ROI is only defined when incremental cost is positive. Retention uncertainty is
not a confidence interval for profit.

A valid tool-generated manifest supports reporting the randomized group comparison
as an incremental-effect estimate under faithful execution and complete measurement.
Without a verifiable randomization manifest, report descriptive group differences.
A non-significant result is inconclusive; it does not prove no effect. Avoid repeated
peeking or changing the outcome/cohort after inspecting results.
