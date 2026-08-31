# External execution and delivery

Keep the entire monitoring control plane outside AE. AE is a read-only event-data source.

## Pipeline

```text
External scheduler (non-overlapping)
  -> one batched authenticated ae-cli read-only query per rule
  -> normalize event rows
  -> evaluate_rules.py with persistent state
  -> route unsuppressed alerts by severity
  -> approved messaging connector or webhook
  -> delivery receipt and audit log
```

## Scheduler choices

Choose only a scheduler available and approved in the user's environment:

- Codex automation for recurring conversational monitoring
- CI/CD scheduled job
- cron/systemd/Windows Task Scheduler on a managed worker
- Airflow, Dagster, or another orchestration platform

Do not create a recurring schedule unless the user has specified the project, cadence, timezone, destination, and credential owner. For low-latency monitoring, use a one-minute cadence, 30-second ingestion watermark, and 60-second query timeout. Use a five-minute cadence when query cost is more important than detection speed. Never queue overlapping runs; skip a tick and report scheduler lag.

## Safe run order

1. Acquire AE authentication without embedding tokens in scripts or files.
2. Query a bounded lookback interval that covers the largest rule baseline plus lateness. Compile all metrics and consecutive periods for one rule into one query with `scripts/compile_ae_rule_query.py`.
3. Write normalized CSV to a restricted temporary path.
4. Run `evaluate_rules.py --state <persistent-path>`.
5. If the query fails or data is stale, send a separate pipeline-health notification; do not claim a business anomaly.
6. Send `notification_batches` when present, falling back to individual `alerts`; record `suppressed` and `diagnostics` without notifying.
7. Persist delivery result, run timestamp, and query correlation/request ID.

## Delivery routing

Suggested routing:

| Severity | Primary route | Escalation |
| --- | --- | --- |
| INFO | digest or log | none |
| WARNING | operations/risk group | escalate if repeated |
| CRITICAL | operations/risk group | on-call or manager |
| DATA_PIPELINE_SUSPECTED | data/engineering group | platform owner |

Use installed purpose-built messaging tools when available. For Feishu/Lark, use the Lark messaging capability after resolving the exact user or group. For Slack, Teams, or email, use the corresponding authenticated connector. If using a webhook, require explicit approval of the exact URL and payload format.

## Failure handling

- Query failure: do not evaluate stale cached data as current unless the config explicitly permits it.
- Evaluator failure: preserve input and diagnostics; do not send partial anomaly claims.
- Delivery failure: retry with bounded exponential backoff and the same deduplication key.
- Slow query or scheduler overlap: cancel or skip the stale cycle; do not let monitoring latency grow through queued runs.
- State-file failure: fail closed for delivery or use a transactional external store; do not risk notification storms.
- Credential failure: report the affected stage without printing secrets.

## Prohibited AE operations

Never call or configure:

- `ae-cli analysis alert create|update|start|stop|delete`
- `ae-cli analysis alert-job ...`
- `ae-cli analysis alert-detail ...`
- `ae-cli analysis alert-notice-config ...`

Do not silently substitute these features if the external scheduler or delivery connector is unavailable.
