# Validation and Recovery

Apply after scope acceptance. Save original definitions, input and source mappings, processing resources, operation IDs, differences, and necessary samples. Distinguish real-environment evidence, local synthetic tests, and unverified items.

## Step 1: Reconcile four layers

Align subject, definition, time zone, precision, and completed cutoff date. Compare subjects with NULL-safe equality and the original tolerance. Identify missing, extra, duplicate, and differing subjects.

| Layer | Comparison and acceptance |
|---|---|
| Daily | D state against raw detail; unique subjects and matching state/counts. |
| Cumulative | D snapshot against expected D-1 merged with D; zero differences. |
| Independent full history | Independently calculate from detail through D and compare with the snapshot; verify baseline B as well. |
| Actual consumption | Saved tag or cross-source consumer matches the target partition's subject, date, type, and value. |

## Step 2: Check boundaries and settings

| Area | Check |
|---|---|
| Date and time zone | Original date ownership, conversion, [D,D+1) boundaries, and date-field alignment. |
| Partition pruning | Complete coverage and expected pruning in the execution plan. |
| Completed day | An unfinished D is rejected before cleanup. |
| Reruns and consecutive days | Correct recurrence, identical same-day results, and retained other partitions. |
| Daily failure | Statistics or validation failure blocks cumulative writes and cleanup; D-1 is retained. |
| Legitimate empty day | Source truly has no events, daily processing succeeded, and cumulative state carries D-1 forward. |
| Values and consumption | NULL, zero, negative values, metric-specific boundaries, missing partitions, partial writes, and failed validation. |
| Sources and access | Analysis-side definition/source evidence, DataOps mapping and read check, subject, and minimum PROD grants. |
| Native parameter | Stored settings, relative range, expanded date, and target partition. |
| Scheduling | Off during manual acceptance; after the final choice, read back switches, frequency, time, zone, parameters, backups, and dependencies. |
| Actual scheduled execution | Verify effective configuration separately from the first real scheduled run. |
| Performance | Metric source, node, scope, and units; distinguish processed rows from physical scan volume. |

Investigate historical differences from original definitions and source evidence first. Ask only about a critical unresolved gap. After acceptance, confirm scheduling before delivery. Downstream switching requires an explicit user request.

## Step 3: Recover and backfill

| Condition | Action |
|---|---|
| Daily statistics or validation fails | Retain D-1; repair and rebuild D statistics and cumulative state. |
| Cumulative write or validation fails | Inspect D's consumer visibility; rebuild and accept before refreshing. |
| Target partition is missing | Apply the confirmed empty-update policy, or skip refresh and retain the previous value. |
| Multiple days missed | Start on the day after the last complete baseline L and process sequentially. |
| Corrected day H is after baseline B | Rebuild H daily and cumulative state, then every dependent date. |
| Corrected day H is on or before B | Rebuild B, pass independent full reconciliation, and rebuild B+1 onward. |
| Date basis or time zone changes | Rebind parameters and evaluate day boundaries and historical rebuild scope. |
| Source-history coverage changes | Establish retention, restoration, or rebuild rules before repairing. |

Verify source-history coverage before reconstruction. Repairing snapshots before B requires an earlier baseline. If source history is missing, establish the intended historical treatment first.

Check write atomicity, node-success dependencies, and consumer-success dependencies separately. Success-triggered consumption checks the upstream terminal state. Independent schedules need calendar alignment, margin, refresh controls, and an exception policy. Run the same date and dependent dates serially.

## Step 4: Preserve, migrate, and roll back

Create new resources by default and preserve the original tag, schedule, and downstream references. For an explicit original-tag edit, check permission and save rollback evidence. For an explicit migration, replace authorized references, verify each, then handle the old schedule.

Record migration coverage, outstanding work, and discovery limitations. Rollback restores the relevant definitions, references, and schedules. Limit grants to required PROD resources. Record and authorize disabling, recycling, and migration separately.

## Step 5: Report acceptance status precisely

| Status | Required evidence |
|---|---|
| Deployed | Saved and necessarily released. |
| Manual validation passed | Target dates actually executed and reconciled. |
| Schedule configuration effective | Switches and scheduling settings read back. |
| Scheduled validation passed | Actual scheduled instance and consumption results verified. |
| Outstanding | Restricted step, responsible party, and next action identified. |

Write the document to the requested medium under [delivery standards](delivery-document.md). Read back text, SQL, and links; inspect diagrams, screenshots, and layout. Date retrospective documentation and state its evidence scope. Keep detailed scripts and runs separately. See [local self-check](setup-and-troubleshooting.md#local-self-check) for its limits.
