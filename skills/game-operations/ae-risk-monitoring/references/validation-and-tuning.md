# Validation, A/B testing, and guarded correction

Use this reference in Steps 5, 6, and 10 of the main workflow. Keep all backtests read-only and keep production actions outside AE.

## Contents

- [Production-shaped case data](#production-shaped-case-data)
- [Baseline-versus-candidate A/B method](#baseline-versus-candidate-ab-method)
- [Guarded automatic-correction loop](#guarded-automatic-correction-loop)
- [Activation acceptance checklist](#activation-acceptance-checklist)

## Production-shaped case data

The following case is synthetic and anonymized, but its fields, timings, and operating decisions are shaped like a real game risk-monitoring review.

### Case A — Registration burst from one IP

Rule:

```text
window = 5 minutes
metric = distinct account_id for register_success
group_by = ip
condition = metric >= 10 for 2 consecutive periods
cooldown = 30 minutes per project + masked IP
```

Observed data:

| Window (UTC+8) | Masked IP | Registration events | Distinct accounts | Distinct devices | Ingestion lag | Expected result |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 13:50–13:55 | 203.0.113.* | 8 | 7 | 5 | 31 s | No alert |
| 13:55–14:00 | 203.0.113.* | 21 | 18 | 3 | 35 s | Streak 1/2 |
| 14:00–14:05 | 203.0.113.* | 32 | 27 | 3 | 42 s | CRITICAL alert |
| 14:05–14:10 | 203.0.113.* | 29 | 24 | 3 | 38 s | Suppress by cooldown |

Acceptance checks:

1. Emit nothing for the first window.
2. Emit nothing after only one matching period.
3. Emit one alert after the second consecutive matching period.
4. Mask the IP and sample account identifiers.
5. Preserve `CRITICAL` status while suppressing the unchanged duplicate.
6. Do not block accounts automatically.

### Case B — Login zero caused by data delay

Observed data:

| Window (UTC+8) | Login users | Heartbeat events | Latest server lag | Expected classification |
| --- | ---: | ---: | ---: | --- |
| 20:00–20:05 | 1,842 | 18,210 | 24 s | Healthy |
| 20:05–20:10 | 0 | 0 | 11 min | `DATA_PIPELINE_SUSPECTED` |
| 20:10–20:15 | 0 | 19,104 | 27 s | Likely login/business outage |

The second row must not be described as “no users logged in.” The third row may become a business alert because the heartbeat confirms fresh ingestion.

## Baseline-versus-candidate A/B method

Do not split live users. For monitoring rules, A/B means replaying two configurations over the same immutable historical data snapshot or running the candidate in shadow mode without delivery.

### Procedure

1. Freeze one 7–30 day input snapshot and incident-label set.
2. Copy the accepted baseline configuration.
3. Change one candidate dimension only: threshold, filter, grouping, window, or consecutive periods.
4. Evaluate both configurations with the same `as_of`, timezone, lateness allowance, and input rows.
5. Match candidate alerts to labeled incidents using a documented time tolerance.
6. Compare the scorecard below.
7. Keep the candidate in shadow mode for at least one normal traffic cycle before requesting activation.

### Scorecard

| Metric | Definition | Guardrail |
| --- | --- | --- |
| Alerts/day | delivered candidate alerts divided by evaluated days | At or below operator capacity |
| Precision | true positive alerts / all labeled alerts | Must not regress without explicit reason |
| Recall | detected labeled incidents / all labeled incidents | No known critical incident may be missed |
| Median detection delay | first qualifying window minus incident start | Must meet severity response target |
| Duplicate rate | suppressed duplicate candidates / all candidates | High values indicate cooldown or grouping review |
| Pipeline false-positive rate | business alerts during stale ingestion / business alerts | Target 0% |
| Review minutes/day | alert count multiplied by median handling time | Must fit team capacity |

Example result using synthetic labels:

| Version | Threshold | Consecutive periods | Alerts/7 days | True positive | False positive | Precision | Recall | Median delay |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 10 | 1 | 31 | 8 | 23 | 25.8% | 100% | 2.1 min |
| Candidate | 12 | 2 | 11 | 7 | 4 | 63.6% | 87.5% | 6.8 min |

Do not automatically adopt the candidate in this example: it misses one labeled incident. Investigate whether the missed incident was critical, then adjust the threshold or consecutive-period policy and replay.

## Guarded automatic-correction loop

Automatic correction means generating, shadow-testing, and rolling back configuration proposals. It never means silently changing a production rule or automatically taking action against a user.

### Correction triggers

Create a proposal when one of these conditions is reproducible:

- alerts/day exceeds the approved response capacity for three consecutive review periods;
- precision falls below the approved floor;
- a labeled incident is missed;
- detection delay exceeds the severity target;
- traffic distribution shifts beyond the configured percentile/drift boundary;
- a metadata type, event, or property mapping changes;
- ingestion staleness creates a business false positive.

### Proposal rules

1. Start from the last accepted configuration, never the currently failing partial state.
2. Change one parameter group at a time.
3. Bound threshold movement to at most 20% per proposal unless the user approves a wider change.
4. Derive burst thresholds from a robust percentile such as `max(operational_floor, P99.5)` over comparable windows.
5. Derive drop rules from comparable weekday/time buckets, not a global average.
6. Preserve hard business controls such as “any successful withdrawal” even when volume is noisy.
7. Run the proposal against the frozen A/B snapshot and then in delivery-disabled shadow mode.
8. Require explicit approval before activation.

### Rollback rules

Immediately select `ROLLBACK` or `DISABLE_AND_INVESTIGATE` when:

- a known critical incident becomes undetected;
- notification volume exceeds twice the approved daily budget;
- pipeline health is unknown or stale;
- masking or deduplication fails;
- delivery retries produce duplicate messages;
- schema or timezone changes invalidate the comparison.

Retain the last accepted configuration, its hash, activation time, backtest scorecard, and owner. A rollback must restore that exact version rather than reconstructing it from memory.

## Activation acceptance checklist

Activate only when every item is true:

- project, table, events, properties, and types are metadata-verified;
- partition and event-time bounds are present;
- freshness classification is reproducible;
- baseline and candidate use the same snapshot;
- at least one normal and one anomalous case are verified;
- known critical incidents are detected;
- alert volume fits operator capacity;
- masked notification preview is approved;
- destination, schedule, credential owner, and rollback owner are approved;
- persistent deduplication state is writable;
- AE native alerts remain disabled and unused.
