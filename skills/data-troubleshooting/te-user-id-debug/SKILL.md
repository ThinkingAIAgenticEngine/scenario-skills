---
name: te-user-id-debug
description: "Read-only diagnosis of AE/TE user identity fragmentation and Account ID/Distinct ID binding. Use whenever users report duplicate user profiles, one person split across devices or client/server reporting, unexpected #user_id assignment, missing Account ID/Distinct ID, login/logout identity conflicts, or multi-role identity issues. Builds evidence from profile counts and bounded behavior sequences, then gives prevention guidance; does not auto-merge historical profiles or treat missing-ID ratios as proof of fragmentation."
---

# User ID Binding and Fragmentation Diagnosis

> Reply in the user's language. Keep identifiers and SQL field names unchanged, but translate explanations and recommendations.
> This is a read-only diagnostic skill. It can help prevent new fragmentation; it does not merge historical profiles, rewrite IDs, delete data, or trigger reprocessing.

## 1. Diagnostic Standard

A missing ID, an early `user_set`, or a server-side event is a clue, not a root cause by itself. Confirm the ID mapping state and the actual data sequence before concluding that fragmentation occurred.

Apply these rules throughout:

- Distinguish `#distinct_id` (visitor ID) from `#device_id`; they are not interchangeable.
- Treat user-profile ID composition as a sample-screening metric, not as the event missing rate or the fragmentation rate.
- Do not use universal 5% / 10% thresholds. Interpret counts against the product's account, guest, role, platform, and reporting design.
- Do not infer a binding failure from event timing alone. A later record containing both IDs can bind a new Distinct ID to an existing Account ID.
- Separate observed evidence, inference, and unresolved questions. Empty query results within a limited window do not prove that an ID never appeared.
- Proceed through read-only stages without repeated "continue" prompts. Pause only for missing target information, insufficient permission, an optional raw-log request, or any proposed write operation.

## 2. Load the Required References

| Need | Reference |
|---|---|
| Binding decisions, new-device and multi-role interpretation | `references/identity-rules.md` |
| Profile counts, bounded event queries, Kafka prechecks, time semantics and masking | `references/query-playbook.md` |
| SDK corrections, prevention steps and historical-data boundaries | `references/remediation.md` |

Read the identity rules before diagnosing. Load the query playbook before constructing SQL, and the remediation guide before giving code or repair advice.

## 3. Workflow

### Step 1: Frame the Identity Design

Collect only what is needed for the next read-only step:

1. Project ID and the observed phenomenon, including when it was first noticed.
2. Account design: no account, login account, or role-level Account ID.
3. Distinct ID generation and lifecycle: SDK-generated or customized, and whether reinstall/new-device flows create a new one.
4. Reporting paths involved: client, server, or both; guest-only and server-only paths must be identified.
5. A bounded investigation window. If the user has no preference, propose a recent bounded window and disclose that earlier history may be excluded.
6. APP_ID only when an authorized raw-ingestion/Kafka investigation is actually required.

Use these interpretations to avoid false conclusions:

- Multiple roles on one device can be expected role-level separation when the same Distinct ID is already bound to another role's Account ID. Verify the intended Account ID granularity.
- A new device or reinstall does not by itself explain fragmentation. An existing Account ID can bind a newly appearing Distinct ID.
- Missing Account ID can be expected for guest-only products; missing Distinct ID can be expected for intentionally account-only/server-only reporting. Neither is universally abnormal.
- A first record containing only one ID, or an early user-property operation, does not prove that later binding failed.

### Step 2: Preflight the Read-only Environment

Before running `ae-cli analysis adhoc run` or another query tool:

1. Discover the installed command contract with targeted help; do not guess flags or project routing.
2. Confirm the target project, query identity, table access and required columns.
3. Confirm that event queries have an explicit partition/date range and a row limit.
4. Validate Project ID and all ID literals before placing them into SQL. Prefer numeric `#user_id` sample lists for behavior reconstruction.
5. If any check fails, report the actual limitation and request the missing access or exported result. Do not claim that a query ran.

Kafka/raw-ingestion access is optional, not assumed. Confirm environment, authorization, table and schema before considering it.

### Step 3: Measure and Sample

Follow `references/query-playbook.md`:

1. Measure the user table's Account ID / Distinct ID composition and label it exactly as such.
2. Compare relevant cohorts or reporting paths only when the product design makes them comparable.
3. Select representative `#user_id` samples; do not declare a root cause from aggregate missing counts.
4. Mask identifiers in the conversation and report aggregate counts by default.

### Step 4: Reconstruct the Evidence

For each selected sample:

1. Query a bounded event sequence by `#user_id`, including `#event_time`, `#server_time`, Account ID, Distinct ID, event name and data source.
2. Identify the earliest observed appearance of each ID, while labeling the left boundary of the query window.
3. Check whether the two IDs were already associated with different `#user_id` values before they appeared together. Existing mappings are not automatically merged.
4. Distinguish client event time, server receipt time and user-profile creation time. Do not treat `#reg_time` as the binding timestamp.
5. Use raw ingestion only when the bounded warehouse evidence is insufficient and the Kafka prechecks pass. Redact raw payloads and omit unrelated properties.

A defensible root cause normally requires a concrete mapping conflict, an identity-configuration error, or a reproducible reporting sequence whose first-seen states are known. Otherwise provide a ranked hypothesis and the next evidence needed.

### Step 5: Diagnose and Recommend

Classify the result as one of:

- **Expected business separation**: the observed mapping matches the confirmed account/role design.
- **Confirmed identity conflict**: evidence shows incompatible existing bindings, reused Distinct IDs across accounts, or an incorrect Account ID granularity.
- **Confirmed reporting/configuration defect**: evidence shows required IDs absent or changed contrary to the confirmed design.
- **Unresolved / insufficient evidence**: the current window or available tables cannot establish first-seen state or binding history.

Follow `references/remediation.md` for prevention. Do not prescribe "delay user properties" as a universal fix; reporting both correct IDs is usually the key issue. Do not claim that a prospective SDK fix repairs existing profiles.

## 4. Response Contract

Return a concise diagnostic report in the user's language:

1. **Conclusion and confidence**: expected, confirmed, or unresolved.
2. **Scope**: project and investigation window; state any excluded history.
3. **Evidence**: aggregate composition and masked sample sequences, with source tables/tools actually used.
4. **Reasoning**: apply the binding rules to the observed first-seen state; distinguish facts from hypotheses.
5. **Recommendation**: prospective reporting/SDK correction and validation method.
6. **Historical-data boundary**: state that existing mappings are not automatically merged and that any repair, backfill or reprocessing needs a separately verified plan and explicit authorization.
7. **Next evidence**: only when the conclusion remains unresolved.

Never expose raw Account IDs, Distinct IDs, AE User IDs, IP addresses, device identifiers or complete raw payloads in the response. Use stable sample labels such as `sample_01` unless the user has explicitly authorized a narrower internal exception; even then, minimize the fields shown.
