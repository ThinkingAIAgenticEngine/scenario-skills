---
name: ae-data-delay-troubleshooter
description: Use when investigating AE/TE data delays, stale dashboards or reports, missing recent events, late ingestion, today's data not appearing, or other freshness and arrival-time complaints. It uses read-only SQL through ae-cli to separate upload, warehouse, and end-to-end latency and produces validated JSON, Markdown, and SVG evidence. Do not use for ordinary dashboard configuration, metric-definition work, or no-data questions without a freshness or arrival-time symptom.
compatibility: "Python 3.10+ and ae-cli."
version: 2.8.1
---

# AE Data Delay Troubleshooter

Use this skill when a customer reports delayed arrival, stale dashboards, or missing recent events. The workflow is read-only: it must not upload events, rerun jobs, change schedules, or alter ingestion settings.

## Required scope

Confirm the project, absolute start/end dates, and event scope. If the user did not provide a range, use the latest seven calendar days. Keep the confirmed host and scope unchanged.

Use uncached SQL with partition pruning:

- every query must contain `$part_date`;
- add `$part_event` only for a specific-event query;
- an all-events query intentionally omits `$part_event` and is protected by the window and scan-row guards.

## Measurement contract

Measure these segments separately:

1. Upload: convert `#event_time` from its `#zone_offset` to the server time zone, then subtract it from `#server_time`.
2. Warehouse: `date_diff('second', "#server_time", "#dw_create_time")`.
3. End to end: convert `#event_time` from its `#zone_offset` to the server time zone, then subtract it from `#dw_create_time`.

Treat `#server_time` and `#dw_create_time` as server-local timestamps. Their common UTC offset is the **server time zone**, configured by `--server-zone-offset`. Require the user to confirm this offset; never assume UTC+8 or another deployment time zone.

Normalize event time with `date_add('minute', (server_offset - event_offset) * 60, #event_time)` before calculating upload and end-to-end delay. Rows with null or invalid `#zone_offset` are excluded from those two measurements by default and must be reported. If the user provides the actual offset for null rows, pass `--missing-zone-offset <hours>`; use that value to normalize those rows. Invalid non-null offsets remain excluded.

The expected-delay threshold is configured with `--expected-seconds`. Require the user to confirm it instead of inventing a service expectation. Values must be from 1 through 599 seconds so the fixed later buckets remain non-overlapping. The one-hour boundary is a severity observation, not the sole delay verdict.

## Required execution sequence

Follow these steps in order. Do not render or deliver a report from an unvalidated result.

1. Confirm project, host, absolute dates, event scope, threshold, and available time-zone offsets.
2. Authenticate and run the checker's preflight/probe. Stop on authentication, schema, or scan-guard failure.
3. Run the read-only measurement and write the canonical result atomically with `--output`.
4. Run the independent result validator. Stop if it reports `ok: false` or exits nonzero.
5. Render the chart, Markdown report, and report summary.
6. Run the validator again with all rendered artifacts, then deliver only if this second check passes.

## Standard run

From this skill directory:

```bash
python3 scripts/check_ingestion_delay.py \
  --project-id <id> \
  --project-name "<name>" \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --server-zone-offset <confirmed-hours> \
  --expected-seconds <confirmed-seconds> \
  --json \
  --output result.json

python3 scripts/validate_output.py result.json
python3 scripts/render_charts.py result.json --out delay_charts.svg
python3 scripts/render_report.py result.json --out report.md --summary-out report-summary.json --chart-ref delay_charts.svg
python3 scripts/validate_output.py result.json \
  --report report.md \
  --summary report-summary.json \
  --chart delay_charts.svg
```

Add `--event-name <event>` only for a confirmed single event. `--server-zone-offset` and `--expected-seconds` are mandatory user-confirmed inputs. Add `--missing-zone-offset <hours>` only when the user provides the actual offset for null event-offset rows. Never use shell redirection for the canonical result; `--output` writes JSON atomically so a failed process cannot leave a new empty `result.json`.

Exit codes are `0` for a completed measurement, `3` for inconclusive, and `2` for blocked or invalid input. Delay findings belong in the JSON verdict and report, not in a nonzero success exit code.
The checker always emits the machine-readable JSON contract; use `render_report.py` for all human-readable output so there is only one reporting implementation.
The independent validator is a release and delivery gate. A validation failure blocks report delivery; do not bypass it or manually reinterpret malformed output.
After every ae-cli call, preserve `_notice.host_compat` and explicit compatibility warnings. Open the result with the exact upgrade commands when such a notice exists; unrelated stderr is not a version warning.

## Interpretation and delivery

Use `scripts/render_report.py` for the formal report and read the visible conclusion from `report-summary.json`. Keep measurements, diagnostic inference, hypotheses, and limitations separate. Never invent event meaning, business impact, owner, root cause, or configuration advice.

When a segment exceeds the threshold, follow [references/diagnosis-matrix.md](references/diagnosis-matrix.md): a large `#event_time` to `#server_time` difference localizes delay before TE receipt, while a large `#server_time` to `#dw_create_time` difference localizes delay inside the TE ingestion path. Treat network conditions, client buffering, transfer nodes, Kafka backlog, and resource contention as hypotheses that require logs or operational evidence, never as conclusions from timestamps alone.

Return a clear chart plus a short written conclusion covering:

- whether upload, warehouse, or both exceed the configured threshold;
- the delayed share, one-hour-or-more share, and key percentiles;
- time-zone coverage, including null offsets and any user-confirmed fallback;
- scan, timestamp, or attribution limitations.

If `#server_time` is constant across many rows, or all covered upload durations are negative, mark upload measurement as unusable instead of converting or taking absolute values. If `#dw_create_time` is unavailable, degrade only warehouse-dependent analysis.

## Safety and performance

The checker runs a one-partition probe, then a compact `GROUPING SETS` aggregation. When the range ends today, the probe uses the previous complete partition when possible. Windows over 31 days or estimated scans over the row budget stop unless the user deliberately authorizes `--allow-large-scan`.

Use `--include-zone-offset-detail` only when an exact per-day offset breakdown is needed. Use `--serial-queries` only when the deployment cannot safely run two independent read-only queries concurrently.

## References

- [references/timing-model.md](references/timing-model.md) — field semantics and calculation rules.
- [references/steps.md](references/steps.md) — execution flow and SQL templates.
- [references/diagnosis-matrix.md](references/diagnosis-matrix.md) — permitted evidence-based interpretations.
- [references/report-template.md](references/report-template.md) — required report structure and wording.
- [references/setup-guide.md](references/setup-guide.md) — minimal setup and authentication.
- [references/verification.md](references/verification.md) — release validation checklist.
