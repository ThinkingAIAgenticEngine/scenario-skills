---
name: ae-tag-dataops-optimization
metadata:
  version: final
  category: data-engineering
  platforms:
    - codex
    - workbuddy
description: Use when asked to optimize a local TE analysis tag that repeatedly scans historical data, or to build a DataOps complete-day snapshot for that tag. Inspect inputs, design and implement snapshots, reconcile results, confirm scheduling, and deliver the verified design and handover. Stop for existing cross-source tags or inputs. Route tag-engine incremental updates to te-tag-incremental-update.
---

# TE Tag Optimization with DataOps

Move reusable historical calculations into complete-day snapshots. Keep business filters, classification, and presentation in the analysis application.

Use the user's preferred language for questions, the brief plan, and customer deliverables. These English instructions do not change the output language.

## Scope

Inspect the original tag and its direct and transitive inputs in the original analysis project. If the tag is cross-source, or an actual input is a cross-source event, tag, property, or table, explain the scope boundary and end this workflow. Establish types, source mappings, and actual references before deciding; an unrelated cross-source configuration in the project is not evidence of use.

This check concerns existing inputs. Results newly produced by this workflow may still be consumed through cross-source configuration. If the user explicitly chooses incremental updates inside the tag engine, route to `te-tag-incremental-update`.

For an out-of-scope request, give a concise response in this order:

1. Identify the tag type or the referenced cross-source asset.
2. Explain that this workflow covers local analysis inputs.
3. Suggest reviewing the upstream cross-source asset's processing and update efficiency, or its read scope, query conditions, and refresh method.
4. State the actual resource status. Claim that resources were preserved without modification only after checking the actions taken.

Keep scope classification separate from a performance diagnosis. Further optimization needs a user request. Store raw fields, API values, internal rules, and local paths in execution records; provide relevant evidence when requested or required by the host.

## Inputs and defaults

Resolve project and tag first, check scope, then resolve the target DataOps space. Reuse information confirmed for the current task or established by a supplied link. Combine missing identifiers into one question. Read metadata before asking the user to choose among genuinely ambiguous assets. Treat information from other tasks as a lead, not as current authorization. Resolve the platform environment when unclear.

| Item | Action |
|---|---|
| Project, tag, target space | Accept names or IDs and resolve them in the order above. |
| Definition and inputs | Read saved logic, events, fields, filters, thresholds, date basis, and time zones from the original analysis project. The saved definition is authoritative; document discrepancies with names or descriptions. |
| Tag creation | Create a new tag by default, regardless of ownership. Preserve the original definition, schedule, and downstream references. Check permissions and scope when the user explicitly requests modification or migration. |
| Range includes today | Adapt to the completed period ending yesterday. Derive other dates, windows, and filters from the saved definition; explain the adaptation in the plan and delivery. |
| Resource names | Name tables, workflows, and the new tag automatically; check naming limits and collisions. Reuse this task's resources on retry. Establish ownership and purpose before using an existing same-name resource. |
| Recurring execution | Keep new workflow schedules and tag auto-refresh off during manual acceptance. Confirm scheduling just before final delivery. |

Obtain available metadata yourself. Ask for a critical definition only after both the API and the original analysis-project page cannot provide it.

## Workflow

Follow [the implementation steps](references/steps/implementation.md), including the input, action, and completion condition for each step:

1. **Inspect the original tag and its inputs.** Resolve scope and semantics using [source discovery](references/source-discovery.md).
2. **Design and briefly explain the plan.** Write the full design into the delivery draft, summarize it once in chat, and continue authorized work.
3. **Implement DataOps processing.** Use [SQL design and templates](references/sql-design.md) for initialization, daily state, validation, and cumulative snapshots.
4. **Create the analysis application.** Create a new tag or cross-source consumer that reads the target complete-day result.
5. **Reconcile actual results.** Apply [validation and recovery](references/validation-and-recovery.md) before any requested migration.
6. **Confirm and configure scheduling.** After creation, release, manual validation, and document preparation, ask whether to enable recurring execution; reuse an explicit answer for this task.
7. **Verify and deliver the handover.** Apply [delivery standards](references/delivery-document.md), inspect the rendered result, correct issues, and return the real document link.

After the one-time plan summary, work quietly. Interact briefly for authentication or authorization, missing critical identifiers, user decisions, blockers, and the final scheduling choice. Consolidate questions and reuse answers. Keep host-required progress updates to one sentence. Store exploration, retries, logs, and troubleshooting outside the customer narrative. Finish with the result, outstanding actions, and delivery links; expand when asked.

## Tools and recovery

| Work | Preferred capability and location |
|---|---|
| Original tag, input assets, source events, tables, and fields | `ae-analysis`; original analysis project |
| Output tables, workflows, release, runs, and backfill | `ae-dataops`; target DataOps space |
| Native date parameters and cross-source configuration | API first; the relevant platform page when API support is insufficient |
| Feishu delivery | `lark-doc` and `lark-shared`; use `lark-whiteboard` when complex diagrams need it |

Read [setup and troubleshooting](references/setup-and-troubleshooting.md) for installation, permission handling, fallback, and beginner questions. Use the corresponding skill and current CLI help for commands. Read-only transient requests may be retried once after diagnosis. Unsupported operations or persistent failures move to the authorized browser path. Missing browser tools, connections, or page authorization require verified official setup guidance and real authorization before dependent work resumes.

## Risk and authorization

| Level | Operations | Required handling |
|---|---|---|
| Read | Definitions, metadata, bounded queries, evidence, and document review | Continue within the identified project, space, and current task. |
| Scoped write | New resources, target-date partition rebuilds, and requested delivery-document edits | Continue within the optimization request; apply validation gates, bounded writes, and readback. |
| Explicit choice | New resource grants, recurring schedules, edits to original assets, and downstream migration | Explain the concrete scope and impact. Reuse explicit current-task authorization; otherwise obtain the relevant choice at its workflow stage. |

The platform's access controls and the host's action policies still apply. Recovery, disabling, recycling, and migration are distinct operations and follow their authorized scope. This skill's optimization request does not imply permission to clean up unrelated assets.
