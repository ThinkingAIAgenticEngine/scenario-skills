# Read-only Query Playbook

> Use only after target, permission, time-range and masking prechecks pass. These are templates, not evidence that a query has run.

## 1. Input and Output Safety

- Validate a numeric Project ID before substituting `{project_id}`.
- Prefer validated numeric `#user_id` lists for sample reconstruction.
- If an Account ID or Distinct ID literal is unavoidable, escape single quotes and keep the value out of the user-facing response.
- Give every event query an explicit `$part_date` range and `LIMIT`; expand the window deliberately when first-seen evidence is insufficient.
- Do not use an unbounded `OR` chain across Account ID, Distinct ID and Device ID. It can combine different people and aliases can make filters ambiguous.
- Return aggregates and stable sample labels by default. Do not expose raw identifiers, IP addresses, device identifiers or complete raw payloads.

## 2. User-profile Composition (Screening Only)

```sql
SELECT
  COUNT(*) AS "total_profiles",
  COUNT_IF("#account_id" IS NOT NULL AND "#distinct_id" IS NULL) AS "account_only_profiles",
  COUNT_IF("#account_id" IS NULL AND "#distinct_id" IS NOT NULL) AS "distinct_only_profiles",
  COUNT_IF("#account_id" IS NOT NULL AND "#distinct_id" IS NOT NULL) AS "dual_id_profiles",
  COUNT_IF("#account_id" IS NULL AND "#distinct_id" IS NULL) AS "missing_both_profiles"
FROM ta.v_user_{project_id}
```

Label the result "user-profile ID composition". It is not the event missing rate and not the fragmentation rate. Do not apply universal 5% / 10% severity thresholds. Account-only, guest-only and role-based products require different baselines.

Select samples with stable internal keys:

```sql
SELECT "#user_id", "#account_id", "#distinct_id", "#reg_time"
FROM ta.v_user_{project_id}
WHERE "#account_id" IS NOT NULL
  AND "#distinct_id" IS NULL
LIMIT 10
```

Use a complementary query for Distinct-ID-only profiles when relevant. Keep the selected `#user_id` values internal and present `sample_01`, `sample_02`, etc. in the report.

## 3. Bounded Behavior Sequences

Query each selected set by AE User ID rather than mixing several raw-ID predicates:

```sql
SELECT
  "#user_id",
  "#event_name",
  "#event_time",
  "#server_time",
  "#account_id",
  "#distinct_id",
  "#data_source"
FROM ta.v_event_{project_id}
WHERE "$part_date" BETWEEN '{start_date}' AND '{end_date}'
  AND "#user_id" IN ({validated_numeric_user_ids})
ORDER BY "#user_id", "#server_time", "#event_time"
LIMIT 1000
```

If `#data_source` is unavailable in the project, record that limitation and use an actually available source/library field. Do not invent source classifications.

The earliest row in this result is only the earliest observation inside `{start_date}` to `{end_date}`. Expand the window or obtain raw-ingestion evidence before calling it the first-ever report.

## 4. Time Fields and Evidence Meaning

| Field | Meaning | Do not infer |
|---|---|---|
| `#event_time` | When the event occurred according to the reported event data | It is not necessarily the ingestion or binding time |
| `#server_time` | When the server received the data | It does not repair an out-of-order client timestamp by itself |
| `#reg_time` | User-profile creation/registration time shown by the user table | It is not a dedicated Account ID–Distinct ID binding timestamp |
| Query-window start | Left boundary of available evidence | No earlier row in the result does not prove no earlier report existed |

Compare both event and server chronology when diagnosing ordering. Explain significant clock skew or late-arriving data instead of hiding it.

## 5. Optional Kafka / Raw-ingestion Investigation

Do not assume `kafka.ta."ta-data"` or any equivalent table exists. Before constructing a raw query, confirm all of the following:

1. The deployment supports this route and the current identity is authorized for it.
2. The actual catalog, table, message schema and timestamp fields have been inspected.
3. APP_ID, a narrow server-receipt time range, and a specific sample or UUID filter are present.
4. The query selects only required fields; raw message bodies are not returned to the conversation.
5. The user is told that raw access is an additional investigation step and any permission failure is reported verbatim.

If a checked raw query is used, retain the original skill's JSON extraction only after adapting it to the verified schema. Add bounded `#server_time` filtering and selective ID/UUID predicates. Do not return `origin_data` by default.

If prechecks fail, request an authorized export or support investigation. Never claim that Kafka evidence was inspected.

## 6. Empty Results and Query Failures

- Empty result: state the exact filters and window; offer a wider window or a specific sample rather than concluding that no data exists.
- Permission failure: stop that route and request access or an export; do not repeatedly retry.
- Missing column/table: inspect metadata and adapt only to observed schema.
- Timeout: narrow the time range and sample set; do not remove all filters.
