---
name: ae-risk-monitoring
description: Trigger when game operations, risk, or data teams need external monitoring over AE/TE event data for account bursts, traffic drops, withdrawals, payment failures, or custom formulas. Accept a verified project plus event/property mappings and a rule configuration; return a read-only query plan, backtest evidence, external schedule, deduplicated masked alerts, and an audit trail. Do not use for AE native alerts, automatic user enforcement, or monitoring without data-freshness validation.
version: 2.0.0
---

# AE Risk Monitoring

Build a closed loop outside AE: query AE read-only, evaluate rules in an external runner, persist deduplication state, deliver through an approved messaging channel, and audit alert quality.

## Customer problem and outcome

Use this Skill for game operations managers, risk operators, and data engineers who need fast evidence without relying on AE native alerts. It covers account farms / credential abuse, login or traffic drops, withdrawal activity, and custom game-economy or payment formulas.

## Trigger and boundary

Trigger when the user asks to monitor AE/TE event data for account bursts, traffic drops, withdrawals, payment failures, or custom formulas. This Skill may notify operators about risk evidence; it is not a substitute for a transactional fraud engine or human investigation.

Do not use this Skill when:
1. The user requires AE native alert tasks or notice configuration.
2. The required outcome is real-time transactional blocking, account banning, withdrawal freezing, or another automated enforcement decision.
3. Event freshness cannot be measured but the requested rule interprets missing events as a business outage.
4. The request is only for historical analysis with no recurring monitoring, deduplication, or delivery requirement; use the appropriate AE analysis workflow instead.
5. The project, event, property, identity, currency, status, or destination cannot be verified.

## Prerequisites

Minimum viable requirements:

- Require `event_time`, `event_name`, and a stable account/user identifier for user-level monitoring. Event-count-only rules may omit account ID but must not claim distinct users.
- Require a server/ingestion timestamp or a fresh heartbeat event for zero/drop outage classification. Without it, report the zero as unverified.
- Require verified numeric metadata for `sum`, `avg`, `min`, and `max`; require a verified immutable transaction ID for exact withdrawal deduplication when available.
- Require at least 7 days or 500 comparable windows for percentile-driven calibration. With less history, use starter thresholds in delivery-disabled shadow mode.
- Require a baseline of at least 20 distinct users per window before enabling a percentage-drop rule. For lower traffic, widen the window and compare equivalent weekday/time buckets.
- Require at least 95% non-empty coverage for a key filter or grouping property before using it for production routing. Otherwise fall back to aggregate monitoring and report coverage.
- Cap evaluated groups at 50 and delivered anomalous groups at 5 per rule cycle.

Apply this Skill to event-driven game operations and account/payment risk where AE can be used read-only and an external scheduler/destination is available.

## Mandatory execution sequence

Follow these steps in order. Do not skip a gate because a query or destination appears obvious.

### Step 1 - Capture the monitoring contract
Open the interactive configurator (`assets/rule-configurator.html`) or use the structured fallback question. Collect project, timezone, events, metrics, filters, grouping, formula, threshold, consecutive periods, cooldown, cadence, notification language, and exact destination. Output one validated `AE_RISK_MONITOR_CONFIG` payload. Stop if project, rule, authorization, or destination is missing. Do not infer credentials, physical fields, or notification recipients.

### Step 2 - Resolve the AE project and schema
Use installed `ae-analysis` procedures:
1. Resolve the project with `ae-cli project info list` or `ae-cli project info get`.
2. Discover the authorized event table with `ae-cli analysis sql-table list`.
3. Read its columns with `ae-cli analysis sql-table columns`.
4. Map each business event/property to a metadata-verified physical identifier and type.
5. Reuse a matching saved report when available; otherwise prepare a bounded read-only query.

Output a verified project ID, table, event mapping, property mapping, types, timezone, and partition fields. Stop if any participating event, filter property, grouping property, numeric property, or user identifier cannot be verified. Never guess names such as `login`, `register`, `withdraw`, `#ip`, or `amount`.

### Step 3 - Compile the rule safely
Validate formula aliases, operators, filters, grouping cardinality, consecutive periods, and masking. Compile each rule into one bounded read-only query using `scripts/compile_ae_rule_query.py`:

```bash
python3 scripts/compile_ae_rule_query.py \
  --config monitor-config.json \
  --rule-id payment_failure_rate \
  --as-of 2026-08-19T16:00:00+08:00 \
  --output compiled-rule.json
```

Output a reviewed query plan containing the physical table, verified identifiers, partition predicate, event-time bounds, aggregation, and grouping tuple. Stop if the compiler reports an unsupported expression, unresolved field, unsafe identifier, missing `"$part_date"` predicate, or incompatible type.

### Step 4 - Establish data health
Query the latest event/server timestamps and expected heartbeat volume before interpreting business zeros. Output `FRESH`, `LATE`, or `DATA_PIPELINE_SUSPECTED` with measured lag and the configured lateness allowance. Stop if data is late or missing; report pipeline health separately and do not evaluate stale data as a business anomaly.

### Step 5 - Backtest the baseline rule
Run the compiled query over 7-30 days when available, normalize the result, and execute:

```bash
python3 scripts/evaluate_rules.py \
  --input normalized-events.csv \
  --config monitor-config.json \
  --output baseline-alerts.json
```

Measure windows evaluated, candidate alerts, alerts per day, median/peak value, affected users, lateness, missing windows, grouping cardinality, top masked groups, and time-to-detect. Output a reproducible backtest summary and representative evidence for at least one normal period and one historical or injected anomaly.

### Step 6 - Compare a candidate with the baseline
Create a candidate configuration that changes only the intended threshold, consecutive-period requirement, filter, or grouping. Replay baseline and candidate over the same immutable data snapshot. Compare alert volume, precision, recall against labeled incidents, detection delay, and operator workload. Output a side-by-side A/B recommendation: keep baseline, adopt candidate, or continue shadow testing.

### Step 7 - Present the activation plan
Show the user the verified project, query scope, schedule, timezone, expected alert rate, cooldown, masked notification preview, state path, delivery destination, rollback trigger, and unresolved risks. Output explicit authorization for the exact external schedule and destination. Stop if the user has not approved the destination and schedule, or either differs from the submitted configuration.

### Step 8 - Run the external monitor
Use a user-approved scheduler outside AE. Execute the read-only query, normalize rows, then run the evaluator with persistent state:

```bash
python3 scripts/evaluate_rules.py \
  --input normalized-events.csv \
  --config monitor-config.json \
  --state monitor-state.json \
  --output alerts.json
```

Output structured evidence, unsuppressed `notification_batches`, suppression records, diagnostics, and a persisted deduplication state. Stop if authentication, query, evaluator, state persistence, or delivery fails. Do not use AE native alerts as a fallback.

### Step 9 - Deliver and verify the first cycle
Send `notification_batches` through the approved destination; otherwise send individual `alerts`. Never send `suppressed`. Verify the delivery receipt and retain the same deduplication key for bounded retries. Every warning must contain severity, rule name, project, window, observed value, threshold/baseline, affected population, masked top dimension, freshness, recommendation, and deduplication key. Render customer text in `notification_language`; preserve user-entered names and dimension values. Stop if the destination is unapproved, masking fails, or a retry would create a new deduplication key.

### Step 10 - Audit, correct, and roll back safely
Inspect scheduler runs, query failures, freshness, evaluator diagnostics, duplicate suppression, delivery receipts, acknowledgements, true/false positives, missed incidents, and time-to-detect. Generate threshold corrections from recent percentiles and response capacity, but test them in shadow mode before activation. Output an audit record plus one of `NO_CHANGE`, `PROPOSE_CHANGE`, `ROLLBACK`, or `DISABLE_AND_INVESTIGATE`. Stop if schema changes, stale data, abnormal alert volume, a missed critical incident, or delivery storms occur. Roll back to the last accepted configuration; never auto-block accounts, freeze withdrawals, or silently change a production threshold.

## Tool contracts

Use `ae-cli` through the installed `ae-analysis` procedures for project and metadata resolution. Read the dedicated command reference before execution and preserve host-compat notices, request IDs, structured errors, partial results, and empty-success semantics.

| Tool stage | Required call or artifact | Success evidence | Failure interpretation |
| --- | --- | --- | --- |
| Project gate | `ae-cli project info list` or `ae-cli project info get` | One verified project ID/name on the intended host | Zero matches or multiple plausible matches require user selection |
| Table discovery | `ae-cli analysis sql-table list` | One authorized event table for the verified project | Empty success means no visible table, not query failure |
| Column discovery | `ae-cli analysis sql-table columns` | Verified physical fields, types, event/user/time/partition mapping | Missing property or incompatible type blocks dependent rules |
| Rule compilation | `scripts/compile_ae_rule_query.py` output | `query_count = 1`; expected periods, metrics, groups, columns, watermark, and bounded SQL | Any mismatch blocks query execution; never repair by string interpolation |
| Rule evaluation | `scripts/evaluate_rules.py` output | `status`, `alerts`, `notification_batches`, `suppressed`, and `diagnostics` are internally consistent | `HEALTHY` means no candidate match; suppression alone never means recovery |
| Delivery | Connector/webhook receipt | Approved destination, stable deduplication key, timestamp, receipt ID | Retry with the same key; route delivery failure separately from anomaly evidence |

Never call or configure AE native alert tasks or notice configurations: `ae-cli analysis alert create|update|start|stop|delete`, `alert-job`, `alert-detail`, or `alert-notice-config`.

## Rule interpretation

Read `references/rule-catalog.md` for formulas, recommended starter thresholds, severity escalation, and false-positive guards. The initial catalog includes:

- `ip_account_burst`: one IP or device touches many distinct accounts in a short window
- `login_silence_or_drop`: login count reaches zero or falls sharply against comparable windows
- `withdrawal_activity`: any withdrawal, large withdrawal, or rapid repeated withdrawals

The configurator also supports user-defined formulas such as `A / B * 100`, `(A - B) / B * 100`, `A - B`, and `A / B`.

## Degradation strategy

| Missing or weak input | Safe fallback | Consequence |
| --- | --- | --- |
| IP is unavailable | Group by verified device ID | Cannot identify shared network origin; state lower confidence |
| Device ID is unavailable | Group by masked IP and add an allowlist | NAT/shared-office false positives may increase |
| Stable account ID is unavailable | Use event count only | Do not label the result as distinct accounts/users |
| Heartbeat/server time is unavailable | Emit an unverified data-health diagnostic | Do not send a 'users stopped logging in' business alert |
| History is shorter than 7 days or 500 windows | Use catalog starter thresholds in shadow mode | Do not activate percentile-derived thresholds |
| Baseline is below 20 users per window | Widen the window and compare equivalent low-traffic periods | Detection is slower but percentage noise is reduced |
| Group property coverage is below 95% | Remove grouping and monitor the aggregate | Segment localization is unavailable; include coverage evidence |
| Withdrawal currency cannot be normalized | Split by currency and require currency-specific thresholds | Never compare mixed currencies in one amount threshold |
| AE query or authentication is unavailable | Return validated config/query artifacts only | Do not activate scheduling or delivery |

## Output contract

Return four sections:

1. **Status** - healthy, warning, critical, or data-pipeline-suspected.
2. **Evidence** - observed value, threshold/baseline, time window, affected population, freshness.
3. **Notification** - the exact masked message sent or ready to send.
4. **Configuration** - project, physical event/property mapping, external schedule, state path, cooldown, and approved destination.

If authentication, permission, metadata, scheduler, persistent state, or notification destination is missing, state the exact blocker. Still provide the validated rule/query/config artifacts that do not require the blocked action. Do not fall back to AE native alert functionality.

## Self-check before final output

- Event/property mapping is metadata-verified; no guessed names.
- Query includes partition predicate, bounded time, and safe identifiers.
- Data freshness is classified before business interpretation.
- Deduplication and masking are verified.
- Delivery is only to an approved destination; no automated enforcement.
- Backtest includes at least one normal and one anomaly case.
- All activation acceptance checks from `references/validation-and-tuning.md` are true.
