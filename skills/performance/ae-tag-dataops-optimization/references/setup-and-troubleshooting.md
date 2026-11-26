# Setup and Troubleshooting

## Installation

This is the final customer distribution. Keep the package directory named `ae-tag-dataops-optimization`.

1. Extract the ZIP and locate `SKILL.md` directly inside the skill directory.
2. Import the entire directory with `references/`, `assets/`, and `scripts/`. Codex normally uses `~/.codex/skills/`, or `skills/` under `CODEX_HOME` when configured. Other hosts use their documented import flow.
3. Refresh skill discovery or open a new session and confirm the skill is available.
4. For an upgrade, preserve the old directory and replace it with the complete new package. Merge personal customizations explicitly and keep files consistent.

Recommended request, translated into the user's preferred language:

> Use DataOps to optimize [tag name or ID] in [analysis project name or ID], using [DataOps space name or ID].

Hosts supporting explicit invocation may add `$ae-tag-dataops-optimization`.

## Required and conditional capabilities

| Dependency | Purpose and completion check |
|---|---|
| Skill host | Loads SKILL.md and its supporting resources. |
| `ae-cli` | Executes compatible analysis/DataOps capabilities; logged-in account can access the selected project and space. |
| `ae-analysis` | Reads definitions, references, source metadata/catalog, and analysis-side application/access rules. |
| `ae-dataops` | Reads target-space rules and manages tables, workflows, release, runs, queries, and backfill. |
| Browser tool or plugin | Complements insufficient or persistently failing APIs; connected and authorized for the relevant platform page. |
| `lark-doc`, `lark-shared` | Required when Feishu is the chosen delivery medium; current-user identity, document access, actual write/readback, and preview available. |
| `lark-whiteboard` | Used as needed for complex figures; generated diagrams are inspected. Simple diagrams can use available document capabilities. |
| `te-tag-incremental-update` | Used when the user explicitly selects incremental updates inside the tag engine. |
| Python 3 with SQLite 3.39+ | Runs the included synthetic semantic self-check using the standard library. |

The package supplies instructions, references, templates, and a local check. Tools, related skills, accounts, enterprise feature enablement, and permissions come from the host or organization.

Use the [official ae-cli installation guide](https://github.com/ThinkingAIAgenticEngine/ae-cli/blob/main/cli-installation-guide.md) and release prerequisites for the installed version:

```sh
npx @thinkingai/ae-cli@latest install --format json

ae-cli auth login --host <enterprise-platform-url>
```

Inspect the installation report's `ok` and CLI/companion-skill validation results. Verify the environment and account. Follow enterprise compatibility requirements and current help for `ae-cli update --host <enterprise-platform-url>`, then start a fresh session when required. DataOps capability availability depends on enterprise configuration. Obtain Feishu skills from the host or administrator and follow their current-user authorization instructions.

## Recovery procedure

1. Capture the sanitized command, environment, exit state, original error, and request ID, including stdout and stderr. Store diagnostic detail in execution records.
2. Classify the problem using evidence:

| Condition | Action and resume condition |
|---|---|
| Tool or companion skill missing | Give the official installation/setup path. Continue independent design from known evidence. Resume platform operations after verifying the capability. |
| Not logged in or authentication expired | Confirm account/environment, initiate the official login flow, and prompt for authorization. Retry the original read after authorization actually succeeds. |
| Explicit project, space, or resource permission denial | Name the resource, operation, minimum permission, and application path. A permitted owner/admin grants access; verify it before continuing. The browser uses the same access boundary. |
| `fetch failed`, timeout, or disconnected request | Check URL, login state, parameters, compatibility hints, and evidence of network/proxy/certificate issues. Retry a transient read once. Persistent failure moves to the authorized browser route. |
| API operation unsupported | Use the relevant platform page within the existing task scope. |
| Browser tool, plugin, connection, or page authorization missing | Provide a verified official host entry point or installation/connection/authorization path, its purpose, and a completion check. Ask the user to complete the missing setup; resume once available. |
| Feishu unavailable or unauthorized | Save a local draft and resource evidence. Complete the requested online delivery and readback once access is available. |

3. Reuse valid sessions and existing authorizations. Required authorization remains pending until actually granted; continue independent work meanwhile.
4. On recovery, re-read the page, resources, and asynchronous operation state and continue from the last known checkpoint. If a write response is ambiguous, inspect the actual resource before retrying. Track the same asynchronous operation ID through its terminal state.
5. When both API and browser paths remain restricted, or waiting becomes unreasonable, report completed items, failure evidence, outstanding actions, and recovery conditions. Label unexecuted operations as unverified.

Locate original definitions, composite events, source tables, and fields in the original analysis project. Use DataOps only to verify established mappings and manage outputs. A source that remains unknown is a discovery gap, not a reason to search the target space for a substitute.

## Local self-check

From the installed skill directory:

```sh
python3 scripts/validate_templates.py
```

`result: PASS` covers SQLite-adapted synthetic semantics for cumulative state, NULL/zero/negative values, date boundaries, reruns, failure gates, and historical repair. It does not validate TE-native date parameters, Trino syntax, grants, schedules, or write visibility; verify those in the actual environment.

## Beginner questions and response pattern

Answer briefly with the observed condition, required action, and resume check. Keep raw logs separate.

| Question | Response pattern |
|---|---|
| The skill is not visible | Check that SKILL.md is directly inside the imported directory; refresh discovery or open a new session. |
| Which information must I provide? | Project and tag identifiers, then the target DataOps space after scope acceptance. Reuse current-task information and retrieve saved calculation details from the platform. |
| Will my existing tag change? | A new tag is created by default. Original definitions, schedules, and references remain unless an explicit change or migration is authorized. |
| Why did a request fail? | Identify authentication, resource access, transient transport, or missing capability from evidence; follow the corresponding recovery path rather than inferring a cause. |
| Why does the result end yesterday? | Snapshots contain complete business days. A range including today is adapted to the period ending yesterday and explained in the plan. |
| When are schedules enabled? | After creation, release, manual acceptance, and document preparation, the user chooses whether to enable them before final delivery. |
| Why was this tag excluded? | The tag or an actual existing input is cross-source. Explain the identified asset and suggest optimizing that asset or its consumption. |
| SQLite is too old | Use Python linked to SQLite 3.39+ and rerun the local self-check. |

## Reference map

- [SKILL.md](../SKILL.md): scope, defaults, routing, and risk/authorization.
- [Implementation steps](steps/implementation.md): ordered inputs, actions, and completion conditions.
- [Source discovery](source-discovery.md): definitions, references, source tables, and DataOps read mapping.
- [SQL design](sql-design.md): states, bindings, dates, nodes, and native parameters.
- [Validation and recovery](validation-and-recovery.md): reconciliation, failure, backfill, migration, and rollback.
- [Delivery document](delivery-document.md): document structure, visuals, SQL, and the delivery review.
- `assets/sql/`: 13 Trino templates; `assets/tag-yesterday-parameter.json`: minimal native-parameter example.
