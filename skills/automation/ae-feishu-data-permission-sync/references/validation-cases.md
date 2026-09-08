# Validation Cases

Run these cases with synthetic accounts and local normalized state. External systems should remain read-only; use dry-run for AE/TE payload validation.

## Acceptance Matrix

| Case | Input condition | Expected result |
|---|---|---|
| Additive existing member | One required permission missing | Add only the missing permission; preserve unrelated permissions and every role |
| Additive idempotency | Target state already satisfied | No planned mutation and `NO_CHANGE` |
| Exact removal | Existing unrelated permission and explicit exact mode | Removal appears prominently in the plan; no execution without approval |
| Multiple rows per account | Distinct valid permissions | Merge into one target permission set |
| Duplicate row | Byte-equivalent normalized row | Deduplicate and report source rows |
| Permission conflict | One permission name maps to two platforms | Plan status `BLOCKED` |
| Unknown platform | Source value absent from live candidates | `BLOCKED_UNKNOWN_PLATFORM` unless explicitly overridden |
| Missing new-member role | Candidate user is not a project member | Block the member addition |
| Ambiguous account | Account resolves to multiple users | Block that account |
| Shared definition update | Existing permission has out-of-scope members | Show count and access direction; require approval |
| Compound existing filter | Existing definition is not exact platform equality | Block automatic equivalence or update |
| Source drift | Sheet hash changes after approval | Stop and regenerate the plan |
| State drift | Member or permission state changes after approval | Stop and regenerate the plan |
| Partial execution failure | One approved action fails | Report partial completion; do not improvise rollback or repairs |
| Verification mismatch | Readback differs from approved target | Mark failed and require a new plan |

## Release Gates

A release passes only when:

- Package structure contains only `SKILL.md`, `references/`, `scripts/`, and optional `assets/`.
- All package text is English and frontmatter contains semantic versioning.
- The planner rejects every blocking case above.
- Additive mode never emits permission removals.
- Exact mode never changes users absent from the sheet.
- Existing member roles are unchanged in every plan.
- A second run against the planned final state emits no mutations.
- No test requires live permission writes.

## Forward Test Prompt

Use a synthetic sheet with two existing users and one candidate user. Include one known platform, one unknown platform, and one existing shared data-permission definition. Ask the skill to synchronize in additive mode. A correct run must stop at `READY_FOR_APPROVAL` or `BLOCKED`, disclose the shared-definition impact, preserve roles, and avoid any mutation before a later explicit confirmation.
