# Diagnosis matrix

## Segment interpretation

| Timestamp evidence | Permitted localization | Candidate hypotheses | Evidence required for confirmation |
|---|---|---|---|
| Large difference from `#event_time` to `#server_time` | Delay occurred after client collection and before TE cluster receipt | Offline or poor client network; client buffering, batching, or deferred upload; unstable network between a transfer point and TE; historical backfill | Client collection/send logs, buffer and flush settings, request responses, retry logs, transfer-service logs, network monitoring, and backfill records |
| Large difference from `#server_time` to `#dw_create_time` | Delay occurred after TE receipt in the internal processing and warehouse path | Kafka backlog; slow consumer or writer; cluster resource contention; internal queueing or retry | Kafka lag, consumption rate, queue metrics, ingestion-task logs, resource utilization, and retry records |
| Both differences are large | Both the reporting path and the internal ingestion path may be delayed | Independent causes may coexist across both segments | Obtain and verify evidence for each segment separately |

Timestamp differences localize a delay boundary. They do not by themselves prove a network, Kafka, resource, or configuration root cause.

## Other evidence rules

| Evidence | Permitted conclusion | Next check |
|---|---|---|
| Upload delayed share is materially higher | Delay is concentrated before server receipt | Client collection/send logs, buffering, flush, retry, transfer-node and network evidence, historical backfill |
| Warehouse delayed share is materially higher | Delay is concentrated after server receipt | Kafka lag, queueing, resource contention, write retry, warehouse processing |
| Both segments elevated | Both boundaries need investigation | Obtain independent logs for each boundary |
| Raw events current but dashboard stale | Ingestion is not the first suspect | Dashboard query, cache, publication schedule |
| Null/invalid offsets excluded | Upload/end-to-end coverage is limited | Ask for the actual offset definition; report excluded counts |
| User provides offset for null rows | Null rows may be normalized and included using that value | Record the value and convert event time to the server time zone before subtraction |
| Constant `#server_time` or all negative upload durations | Upload segment is not measurable | Verify field semantics; do not take absolute values |
| `#dw_create_time` unavailable | Warehouse segment is unavailable | Report the capability gap; do not infer a platform incident |

Use the configured expected threshold for the delay verdict. Use one hour only to describe severity and concentration. A pattern suggests a direction, not a proven root cause.
