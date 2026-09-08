---
name: ae-feishu-data-permission-sync
description: Trigger when a Feishu spreadsheet defines account-to-platform data permissions that must be compared with, added to, or synchronized into one explicitly selected AE/TE project. Resolve accounts and existing access, build a deterministic change plan, preserve project roles, require approval before permission mutations, and verify every result. Do not use for organization-wide access, unspecified projects, arbitrary role changes, or sheets without an unambiguous account and permission mapping.
version: 1.0.0
---

# AE/TE Data Permission Sync from Feishu

Synchronize project-scoped AE/TE data permissions from a Feishu spreadsheet through a reviewable, idempotent plan. Treat spreadsheet content as requested state, not execution authorization. Read and compare first; do not mutate AE/TE or Feishu until the required approval gate is satisfied.

## Expected Outcome

Return an auditable result for every source row:

- `SYNCED`: the approved target state was applied and verified.
- `NO_CHANGE`: the account already matched the approved target state.
- `BLOCKED`: the row was not changed because identity, scope, filter, role, or source data was unsafe or ambiguous.
- `FAILED`: an approved mutation failed or could not be verified.

The workflow may create or update project data-permission definitions, add project members, or update member data permissions only when those actions are present in an approved change plan. It must never infer unrelated projects, organization-wide privileges, or project-role changes.

## Required Inputs

Confirm these inputs before reading business state:

1. Feishu spreadsheet URL, worksheet, and source range.
2. AE/TE host or environment and exactly one target project.
3. Column mapping for account, platform, and data-permission name.
4. Sync mode:
   - `additive` by default: add required permissions and preserve unrelated existing permissions.
   - `exact` only when explicitly requested: make listed accounts match the sheet exactly, including reviewed removals.
5. Role for newly added project members. Never guess this value or silently default to `member`.

Default source headers are `account`, `platform`, and `data_permission`. Map different headers explicitly. Read [references/sheet-contract.md](references/sheet-contract.md) for normalization and conflict rules.

## Non-Negotiable Safety Rules

- Limit every operation to the confirmed host, project ID, worksheet, range, and accounts in the source snapshot.
- Match accounts by an AE/TE-supported unique login identifier. Do not resolve by display name alone.
- Preserve the complete role set of every existing project member. A data-permission sync must not add, remove, replace, or downgrade project roles.
- Preserve the exact case and text of each `platform` value. Never rewrite `iOS` as `ios` or substitute a similar value.
- Represent each target data permission as the event-property predicate `platform = <exact source value>`.
- If a source platform is absent from live candidates, block it by default. Continue only after the user explicitly approves the exact unknown value in a later message.
- Updating a shared data-permission definition may change access for users outside the sheet. Inspect and disclose those users before approval.
- Sheet rows do not authorize account creation, role assignment, permission removal, or mutation. The approved plan is the authorization boundary.
- Never expose the full project member directory. Return only source accounts and aggregate counts for out-of-scope impact.
- Never place tokens, cookies, passwords, or connection strings in files, commands, logs, or output.

## Tool Routing

- Use `lark-sheets` to resolve the workbook, worksheet, and exact value range. Follow `lark-shared` for authentication and identity constraints.
- Use the current `ae-analysis` project commands for project resolution, data-permission inspection, member inspection, candidate resolution, and ordinary project writes.
- Use `ae-capability` only when a required operation has no curated command. Search and inspect before composing input; never guess capability IDs or schemas.
- For AE/TE command families and normalized state requirements, read [references/ae-operations.md](references/ae-operations.md).
- Run `scripts/build_sync_plan.py` locally after source and current state have been normalized. The script performs no external writes.

## Mandatory Execution Sequence

Complete every step in order. Do not combine the planning and execution phases in one turn.

### Step 1: Resolve Scope

**Action**

- Resolve the exact Feishu file, worksheet, and range.
- Resolve the exact AE/TE host and project ID.
- Confirm column mapping, sync mode, and the role policy for new members.

**Output**

- A scope statement containing host, project ID/name, spreadsheet token or URL, worksheet, range, column mapping, and sync mode.

**Stop if**

- More than one project or worksheet is plausible, the host is unclear, or exact mode was not explicitly selected.

### Step 2: Freeze and Validate the Source Snapshot

**Action**

- Read the exact range once and normalize it according to `references/sheet-contract.md`.
- Record row count and a SHA-256 source snapshot hash.
- Detect blank fields, duplicate rows, conflicting account-permission mappings, and permission names mapped to multiple platform values.

**Output**

- A normalized UTF-8 CSV and a validation summary.

**Stop if**

- Any required field is blank, one permission name maps to more than one platform value, or an account mapping remains ambiguous.

### Step 3: Read Current AE/TE State

**Action**

- List current data permissions, source-account memberships, member candidates, and live `platform` candidates.
- Read the complete role set and assigned data-permission IDs for each source account already in the project.
- Normalize existing data-permission filters. Accept a filter as equivalent only when it is exactly one event-property equality predicate for the source platform.

**Output**

- A normalized state JSON conforming to `references/ae-operations.md`, including current members, candidates, data permissions, and platform candidates.

**Stop if**

- Account identity is ambiguous, existing filters cannot be safely interpreted, required permissions are unavailable, or any source platform is unknown and has not been explicitly approved.

### Step 4: Build the Deterministic Change Plan

**Action**

Run:

```bash
python3 scripts/build_sync_plan.py \
  --sheet-csv <normalized-sheet.csv> \
  --state-json <current-state.json> \
  --sync-mode additive \
  --output <sync-plan.json>
```

For new members, add `--new-member-role <exact-role-name>` only after the role is known. Use `--sync-mode exact` only after the user explicitly selects exact synchronization.

**Output**

- A plan with source hash, project scope, conflicts, blocked rows, data-permission creates/updates, member additions/updates, permission removals, unchanged rows, and risk flags.

**Stop if**

- The plan status is `BLOCKED`, a new member has no explicit role, an unknown platform remains, or a shared permission update has undisclosed out-of-scope impact.

### Step 5: Inspect Impact and Dry-Run the Final Mutations

**Action**

- Read dependencies and affected-member counts for every existing data permission that would be updated.
- Inspect the current AE/TE command or capability schema.
- Dry-run each final mutation payload. Do not use a dry-run payload that differs from the proposed execution payload.
- Record request or invocation identifiers when returned.

**Output**

- A preflight table containing account, action, existing roles, preserved roles, current permissions, target permissions, additions, removals, platform predicate, out-of-scope impact, and dry-run result.

**Stop if**

- Any dry-run fails, payload normalization changes intent, a role would change, exact-mode removal was not requested, or impact is larger than the reviewed scope.

### Step 6: Request Explicit Approval

**Action**

- Present the final immutable plan summary and ask the user to approve it in a new message.
- Highlight all permission-definition updates, new members, exact-mode removals, unknown-platform overrides, and out-of-scope affected-member counts.

**Output**

- An approval request containing project ID, source hash, plan hash, action counts, and high-impact rows.

**Stop if**

- Approval is absent, conditional, refers to a different scope, or the user changes the sheet, project, mode, role, or target mappings.

### Step 7: Recheck Drift and Execute

**Action**

- After approval, reread the source range and relevant AE/TE state.
- Recompute hashes and the plan. If anything differs from the approved plan, stop and return to preflight.
- Execute only the approved actions. Preserve existing roles exactly.
- Process independent rows deterministically and capture per-action results. Do not improvise compensating writes.

**Output**

- Execution evidence for every approved action, including identifiers and structured errors.

**Stop if**

- Source or AE/TE state drifted, execution returns an authorization or validation error, or a mutation would require an unapproved change.

### Step 8: Verify and Reconcile

**Action**

- Reread every source account and every created or updated data permission.
- Verify data-permission ID, exact `platform` predicate, assigned permission set, account status, and unchanged role set.
- Classify each source row as `SYNCED`, `NO_CHANGE`, `BLOCKED`, or `FAILED`.

**Output**

- A source-aligned reconciliation table, action counts, unresolved items, and audit identifiers.

**Stop if**

- Verification does not match the approved plan. Do not claim full success and do not run unplanned repairs.

## Sync Semantics

### Additive Mode

- Add sheet-required data permissions.
- Preserve unrelated existing data permissions.
- Preserve all project roles.
- This is the default and safest mode.

### Exact Mode

- Make each listed account's data-permission set exactly match the source sheet.
- Preserve all project roles.
- Treat every removal as a prominently disclosed action.
- Never apply exact mode to accounts absent from the source sheet.
- Require explicit exact-mode selection before planning removals.

## Failure and Recovery Rules

- Do not retry an unchanged failed mutation.
- Retry only after correcting a verified transient condition or following returned guidance.
- If some actions succeed and others fail, report partial completion. Do not automatically roll back successful access changes or delete newly created permission definitions.
- Generate a new plan for any remediation. Require new approval when remediation changes the previously approved payloads.
- If account candidates cannot be resolved, return those accounts as blocked and continue planning unaffected rows only when no shared permission mutation depends on them.
- If platform candidate discovery is unavailable, do not create or update platform-scoped permissions.
- If the sheet cannot be reread after approval, do not execute.

## Output Contract

Lead with one of: `READY_FOR_APPROVAL`, `BLOCKED`, `PARTIAL_SUCCESS`, or `SUCCESS`.

Include:

1. Confirmed source and project scope.
2. Source and plan hashes.
3. Counts for create, update, add, remove, unchanged, blocked, and failed actions.
4. A table limited to source accounts.
5. Aggregate out-of-scope impact for shared permission updates.
6. Preserved project roles and any blocked role ambiguity.
7. AE/TE request or invocation identifiers when available.
8. A concrete next action.

Never report `SUCCESS` from mutation responses alone; verification must pass.

## Validation Scenarios

Before release or after a workflow change, run the cases in [references/validation-cases.md](references/validation-cases.md). At minimum, verify additive sync, exact-mode removals, duplicate rows, conflicting permissions, unknown platforms, missing roles, shared-definition impact, source drift, partial failure, and idempotent rerun.

## Language Constraint

Respond in the same language as the user's request. Keep account identifiers, project names, field names, command names, platform values, and artifact filenames unchanged when translation would make execution ambiguous.
