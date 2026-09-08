# AE/TE Operation Contract

Read this reference after the target host and project are known. Use the installed `ae-analysis` documentation as the current source of command syntax and payload schemas.

## Current Command Families

Use curated project commands when available:

| Purpose | Command family |
|---|---|
| Resolve project | `ae-cli analysis project info list` |
| List data permissions | `ae-cli project data-power list` |
| Read one data permission | `ae-cli project data-power get` |
| Create or update a data permission | `ae-cli project data-power upsert` |
| List project members | `ae-cli project member list` |
| Resolve candidate users and options | `ae-cli project member-candidate list` |
| Add a project member | `ae-cli project member add` |
| Update one project member | `ae-cli project member update` |

Do not copy remembered payload shapes into a live request. Read the dedicated command reference or inspect the capability before constructing payloads. Use snake_case fields required by the current schema.

## Project Gate

Resolve the supplied name or ID on the current host. Reuse a project only when ID and host were verified in the same continuous task. If multiple projects match, stop and ask the user to select one.

## Normalized State JSON

Convert read-only AE/TE responses into this local planning contract:

```json
{
  "host": "https://example.invalid",
  "project_id": 123,
  "project_name": "Example",
  "platform_candidates": ["Android", "iOS"],
  "data_powers": [
    {
      "id": 10,
      "name": "iOS Data",
      "platform": "iOS",
      "filter_summary": "platform = iOS",
      "member_accounts": ["existing@example.com"]
    }
  ],
  "members": [
    {
      "account": "existing@example.com",
      "user_id": 501,
      "role_names": ["analyst"],
      "data_power_ids": [10]
    }
  ],
  "candidates": [
    {
      "account": "new@example.com",
      "user_id": 502
    }
  ]
}
```

The `platform` field of an existing data power may be populated only after confirming that its filter is exactly one equality condition on the event property `platform`. Set it to `null` when the filter is broader, narrower, compound, dynamic, or ambiguous. An ambiguous existing filter blocks automatic update.

The member list should contain source accounts only. The `member_accounts` array for data permissions may be replaced with an aggregate `member_count` and `out_of_scope_member_count` when returning identifiers would expose unrelated users.

## Role Invariant

For an existing member:

```text
target_role_names = current_role_names
```

Do not reorder, collapse, substitute, or default roles in a way that changes semantics. Compare roles as sets for verification, but send the exact schema required by the current command.

For a new member, the role must come from an explicit user choice or an already approved source field. The literal value `member` is not a universal safe default.

## Data-Permission Impact

Before updating an existing data-permission definition:

1. Read its complete current definition.
2. Determine how many assigned members are outside the source sheet.
3. Compare current and proposed filter semantics.
4. Label the change as expanding, narrowing, or changing access.
5. Include the impact in the approval summary.

If impact cannot be determined, block the update. Creating a new unused definition is lower impact, but it still belongs in the approved plan.

## Dry-Run and Confirmation

Run one dry-run on each final mutation payload when supported. Do not execute mutations in the same turn as the final dry-run. Present project ID, action, target account or permission, role preservation, additions, removals, and out-of-scope impact. Wait for the user's next message.

After approval, execute only unchanged payloads. If a command is classified as high-risk-write, use its required confirmation mechanism only after chat approval. Ordinary write classification does not remove the skill's approval requirement for access changes.

## Verification

After execution, reread:

- Every created or updated data permission.
- Every added or updated source account.

Verify exact platform predicate, assigned permission IDs, account state, and preserved roles. Preserve request IDs, invocation IDs, and structured failures. Empty or partial responses are not proof of success.
