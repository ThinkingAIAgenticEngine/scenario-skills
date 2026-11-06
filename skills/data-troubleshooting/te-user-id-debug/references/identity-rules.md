# Identity Rules and Scenario Interpretation

> Authoritative source: ThinkingAI "User identification rules", last checked 2026-10-30.
> https://docs.thinkingai.io/zh/integration/user_identify
> English: https://docs.thinkingai.io/en/integration/user_identify

## 1. Three Different IDs

| ID | Meaning | Diagnostic caution |
|---|---|---|
| `#account_id` | Login Account ID; a game may intentionally use role ID at this field | Confirm the intended granularity before calling role separation a defect |
| `#distinct_id` | Visitor ID used before login or outside the account | It is not equivalent to `#device_id`; do not silently substitute one for the other |
| `#user_id` | AE internal user identity used to attribute data | The user table and event table show outcomes, not a complete binding-operation audit log |

When both Account ID and Distinct ID are present, data is associated with the Account ID's AE User ID. When only Distinct ID is present, its associated AE User ID is used.

## 2. Binding Rules

| Account ID state | Distinct ID state | Result when received |
|---|---|---|
| New | New | Bind the IDs and associate them with one AE User ID |
| Existing | New | Bind the new Distinct ID to the existing Account ID; one Account ID can bind multiple Distinct IDs |
| New | Existing, not bound to an Account ID | Bind the new Account ID to the Distinct ID's existing AE User ID |
| New | Existing, already bound to another Account ID | Do not bind; associate the new Account ID with a new AE User ID |
| Existing | Existing | Do not adjust the mapping table, even if the IDs currently map to different AE User IDs |
| New, received alone | Absent | Create and associate a new AE User ID for the Account ID |
| Absent | New, received alone | Create and associate a new AE User ID for the Distinct ID |

One Account ID can bind multiple Distinct IDs. One Distinct ID can bind only one Account ID. AE User ID and Account ID map one-to-one.

## 3. What Timing Alone Cannot Prove

The following are investigation clues, not sufficient root-cause evidence:

- A server-side event contains Account ID but no Distinct ID.
- A `user_set` / `user_setOnce` record arrives before the first observed event containing both IDs.
- The first observed client event occurs later than a server-side event.
- `#reg_time` is earlier than the first event observed in a limited query window.

For each case, establish whether the Distinct ID was new, unbound, or already bound elsewhere when the later combined-ID record arrived. A new Distinct ID can bind to an existing Account ID, so "server first" or "user property first" does not necessarily fragment a user.

## 4. Scenario Interpretation

| Scenario | Correct interpretation |
|---|---|
| Multiple roles on one device | If Account ID is role-level and the shared Distinct ID is already bound to another role, separate AE users can be expected. Confirm the product design rather than calling all such cases defects |
| Old account on a new device | A newly appearing Distinct ID can bind to the existing Account ID. A split profile needs evidence; it is not the default outcome |
| Reinstall followed by login | Same as new-device login; check whether a new Distinct ID was generated and whether it was already bound elsewhere |
| Guest-only product | Missing Account ID is expected when a valid Distinct ID is present |
| Intentional account-only/server-only path | Missing Distinct ID may match the design. Assess whether cross-device identity is required instead of applying a universal threshold |
| Both IDs missing | Investigate as an identification defect; do not classify it as a normal guest scenario |

## 5. Evidence Boundary

The warehouse can show the current profile and events inside a query window. It may not prove the first-ever appearance of an ID or the exact binding operation. Label such conclusions as bounded observations and obtain earlier or raw-ingestion evidence when the conclusion depends on first-seen state.
