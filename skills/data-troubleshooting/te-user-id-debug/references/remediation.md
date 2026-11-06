# Remediation and Validation Guide

> Prevention and historical repair are different deliverables. This skill recommends prospective fixes but performs no writes.

## 1. Correct the Reporting Design First

Only recommend a change supported by the diagnosis:

| Evidence-supported issue | Prospective correction |
|---|---|
| A required reporting path omits Distinct ID contrary to the confirmed design | Pass the same visitor identity used by the client, together with Account ID, on relevant server reports |
| Distinct ID is reused across different accounts | Make visitor identity unique within its intended scope; do not share one Distinct ID across role/account identities |
| Distinct ID changes unexpectedly after events start | Set a custom Distinct ID immediately after SDK initialization when needed; avoid changing it again after events have been uploaded |
| Account ID granularity conflicts with the product design | Confirm login-account versus role-level identity and apply that decision consistently across client and server |
| User-property records create an unexpected identity path | Include the correct IDs on the user-property call; do not assume that delaying the call alone repairs a mapping conflict |

An early `user_set` is not inherently defective. Likewise, moving every user-property call after an event is not a universal solution. The required correction depends on the IDs present and their existing binding state.

## 2. Correct Python SDK Example

Official source, checked 2026-10-30:
https://docs.thinkingai.io/en/integration/python_sdk_installation

For Python SDK v3, use `tgasdk.sdk`. Positional `track` arguments are Distinct ID first, Account ID second:

```python
from tgasdk.sdk import TDAnalytics, TDLogConsumer

te = TDAnalytics(TDLogConsumer("LOG_DIRECTORY"))

distinct_id = "visitor-id-from-the-confirmed-identity-design"
account_id = "account-or-role-id-from-the-confirmed-identity-design"

# Prospective event reporting: both IDs follow the confirmed design.
te.track(distinct_id, account_id, "login_success", {
    "login_method": "account"
})

# User properties also carry the intended IDs; timing alone is not the fix.
te.user_set(
    distinct_id=distinct_id,
    account_id=account_id,
    properties={"level": 1}
)
```

Do not replace these examples with `from thinkingdata import TDAnalytics`, and do not reverse the positional IDs. For another SDK, consult that SDK's current official documentation instead of transliterating Python argument order.

## 3. Client-side Prevention

- Initialize the client SDK before identity-dependent reporting.
- Set a custom Distinct ID immediately after initialization only when the design requires customization.
- Keep Account ID assignment consistent at registration, login, role selection and logout boundaries.
- Ensure the server receives the intended visitor identity through an authenticated, authorized flow; do not accept arbitrary client-supplied identity mappings without validation.
- Test new-device, reinstall, guest-to-login, role-switch and client/server ordering cases explicitly.

## 4. Validation After a Prospective Fix

Use new test identities and a bounded observation window:

1. Record the expected Account ID and Distinct ID lifecycle before testing.
2. Verify that new records carry the intended IDs and map to the expected AE User ID.
3. Confirm that no new conflicting profile is created across the tested client/server sequence.
4. Compare user-profile composition only against the same product/design cohort; do not claim success from a missing-ratio threshold.
5. Keep sample identifiers masked in the report.

## 5. Historical Fragmentation Boundary

Existing ID mappings are not automatically merged when two already-known IDs appear together. A prospective SDK correction therefore does not prove that historical profiles were repaired.

This skill does not provide or execute automatic profile merging, ID rewriting, backfill, deletion or reprocessing. For historical impact:

1. Quantify the affected cohort and time range with masked aggregates.
2. Preserve evidence and assess the project's available official recovery path with TE support or the responsible engineering team.
3. Require a separately verified plan, backup/rollback strategy, dry-run where supported, and explicit authorization before any write or reprocessing.
4. Never describe historical repair as complete without independent post-operation verification.
