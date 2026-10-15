# Report contract

The generated report must remain simple and evidence based, with this order:

1. Scope: project, host, dates, event scope, row count, configured threshold.
2. Short conclusion: upload, warehouse, end-to-end, and first diagnosable boundary.
3. Overall table: sample size, within-threshold share, above-threshold share, one-hour-or-more share, p50, p95, maximum.
4. Distribution chart and table.
5. High-delay event ranking when available.
6. Per-day warehouse statistics.
7. Coverage and anomaly notes, including null/invalid offsets and any confirmed fallback.
8. Evidence-triggered recommendations and verification steps.

Labels must use the result's user-confirmed `decision_policy.expected_seconds`; never hard-code a threshold. The chart and prose must use identical bucket boundaries.

State explicitly that event time is normalized from `#zone_offset` to the user-confirmed server time zone before upload and end-to-end subtraction. Show the confirmed offset and any supplied fallback for null event offsets; never assume UTC+8.
