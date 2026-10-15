---
name: ae-kb-bootstrap
display_name: AE Business Metrics KB Bootstrap
description: Initialize a shared business metrics definition knowledge base (KB) and append project-specific metric definitions so AE analysis can reuse verified calibers. Use when bootstrapping the metrics KB, onboarding a new project into it, building a caliber library, or extracting metric calibers from report definitions before the first data query. Do not use for querying data, diagnosing metric declines, or editing an already-compiled KB's calibers.
version: 0.4.0
---

# AE New Project KB Bootstrap (ae-kb-bootstrap)

> Purpose: when a **new customer (company / caliber subject)** is onboarded to AE analysis, use a two-stage flow — **company onboarding (once per customer) → project onboarding (once per project)** — to produce a compiled business metrics definition KB that is "query-ready". Afterwards, querying data for this project via `kb-driven-data-analysis` / `ae-analysis` reuses this caliber.

## Why this skill exists (customer pain) and prerequisites

**Customer pain**: before a customer's metric calibers are written down, every data query re-guesses which events / fields / aggregations back a metric, so numbers drift and do not match the customer's own dashboards. This skill turns the customer's authoritative dashboards or reports into one compiled caliber library so later queries reuse a single definition instead of re-deriving it.

**Prerequisites** (check before starting; if any is missing, stop and ask — do not guess):

- ae-cli is authenticated and can search readable assets and read the selected report definitions (`ae-cli analysis asset search` and `report get` succeed).
- The authenticated user can create and edit company knowledge bases. If any `--scope company` write fails because of insufficient permission, stop, preserve the generated local files, and ask a company-KB administrator to grant access or execute the remaining commands. Never omit `--scope company` or silently fall back to a personal knowledge base.
- The target `project_id`, project name, and the **authoritative caliber source** are known (the user must pick the dashboard or report at gate ②).
- Company onboarding requires the metric family set and per-family default calibers to be confirmed with the user (hard gate).
- **Degradation when data is unavailable**: if asset search finds no readable candidate, broaden the search terms once; if it still returns empty, ask the user to grant access or provide the authoritative dashboard/report IDs. Never infer lack of access from `dashboard list` alone, and never guess event or field names.

## Core concept: one directory, two layers

One customer = **one KB directory**. The directory holds both the **company-level abstraction layer** (reused unchanged across that customer's projects) and the **project-level instance layer** (appended once per project). **Do not split into "company-layer directory + project directory" as two KBs.**

```text
kb-<slug>/                       # one KB per customer (company layer + all project instance layers)
├── index.md                     # company level: navigation + layering principles + changelog
├── reference/
│   └── metric-registry.md       # company level: registry schema contract + confirmation rules
├── metrics/                     # company level: metric-family generic calibers (placeholder form; family set = .md files present)
│   ├── event.md
│   ├── retention.md
│   └── ... (funnel/ltv/distribution/interval/path/attribution/prop, trimmed per customer)
├── rules/
│   └── caveats-checklist.md     # company level: pre-query caliber confirmation checklist
└── projects/                    # project-level instance layer
    └── project-<N>/
        ├── registry.md          # project instance caliber (real events/fields/aggregations/report IDs)
        └── context.md           # business background / data availability boundaries
```

Key principles:

- **One KB per customer.** Company-level files are only reused unchanged across projects of the same customer; they do not transfer across customers — different customers are different caliber subjects, and the company layer (especially the family set and "applicable sub-metrics" in `metrics/*.md`) must be onboarded per customer. Never reuse one customer's company layer as a generic template for another customer.
- New project onboarding = **append** a `project-<N>/` under the existing `kb-<slug>/projects/`; do not touch company-level files, do not copy, do not create another directory.
- Company-level files only keep field roles and placeholders; they never contain concrete project event names, field names, report IDs, dashboard IDs, or tag names. Project-private content lives only in `projects/project-<N>/registry.md` (caliber) and `context.md` (business background).
- Company-level caliber changes are recorded in the "Changelog" section at the bottom of `index.md` (adding/removing metric families, changing default calibers, etc.); no separate metadata file.

## Stage 0: company onboarding (once per customer, hard gate)

For a customer's first onboarding, first initialize "that customer's company KB directory". Scripts and checklist live in [references/onboarding-flow.md](references/onboarding-flow.md), section "Company onboarding".

```bash
bash scripts/company-scaffold.sh --company <slug> --company-name "<CompanyName>" [--families event,retention,prop]
```

This produces `kb-<slug>/`. The agent completes the company-onboarding checklist and confirms with the user:

1. **Metric family set**: which families to include (default 9); delete families the customer does not need (e.g. delete `metrics/ltv.md` if there is no LTV).
2. **Per-family "applicable sub-metrics" and "recommended machine-readable definition"**: rewrite `metrics/*.md` to match the customer's business; confirm the family's company-level default (initial event / return event / value field role / aggregation / analysis subject / observation window).
3. **Replace the `index.md` title** with the real company name.
4. Clarify which items are "company-level mandatory defaults" and which allow "project-level override".
5. When done, record it in the "Changelog" at the bottom of `index.md` and replace the title with the real company name (this is the onboarding-completion marker).

> **Company onboarding hard gate**: the metric family set + per-family caliber defaults must be confirmed by the user; the agent must not scan all projects and guess the customer's caliber on its own.

## Stage 1-4: project onboarding (four stages, five gates)

After company onboarding is complete (real title, changelog, metric families, and family defaults are confirmed), run once per project of that customer. Each stage ends with a "confirmation point". **Hard gates (①②③) must be confirmed before continuing**; **conditional confirmations (④⑤) have defaults and only interrupt when a caveat is hit or the user wants to customize**. Script templates live in [references/onboarding-flow.md](references/onboarding-flow.md), section "Confirmation checklist".

### Confirmation point overview

| gate | stage | confirmation question | type |
| --- | --- | --- | --- |
| ① | define project | is `project_id` + project name correct | hard gate |
| ② | define project | which dashboard/report is the **authoritative caliber template** | hard gate |
| ③ | after probing caliber | which metric families to include | hard gate |
| ④ | before generating registry | any per-metric caliber to change | conditional |
| ⑤ | before compiling | use default KB name? compile incremental? | conditional |

### 1. Define project (gate ①②)

> **Input**: `project_id` + project name from the user. **Output**: confirmed project identity + the authoritative caliber dashboard/report. **Non-skippable** (gates ①②).

Confirm `project_id` and project name (gate ①); **then confirm the authoritative caliber source dashboard/report** (gate ②).

> **① hard gate**: confirm with the user that "target project = project_id N, project name X".
>
> **② hard gate**: confirm with the user "which dashboard/report (or set of assets) is the authoritative caliber template". Multiple assets in the same project may have conflicting calibers; **the user must specify — the agent must not scan all projects and guess**.

### 2. Probe caliber (gate ③)

> **Input**: the authoritative dashboard/report chosen at gate ②. **Output**: real events / fields / aggregations / report IDs + a model→metric-family mapping. **Non-skippable** (gate ③).

Read the authoritative dashboard or report's **report definitions** to get real events / fields / aggregations / report IDs. Saved-asset discovery and definition-reading steps are in [references/onboarding-flow.md](references/onboarding-flow.md).

> **③ hard gate**: list the scan results (model→metric-family mapping + the reports covered by each family) and confirm "which metric families to include". Use the families already present in the company-layer `metrics/` as candidates; if a new family appears in the scan, or some family is not needed, confirm with the user before adjusting.

### 3. Generate project instance layer (gate ④)

> **Input**: the probed caliber from step 2. **Output**: filled `projects/project-<N>/registry.md` + `context.md`. **Conditional** (gate ④).

Fill the probed caliber into `projects/project-<N>/registry.md`. The field contract follows the company-layer `reference/metric-registry.md`; the YAML skeleton follows the company-layer `metrics/<family>.md`. The core is "initial event + return event + value field + aggregation"; window / grouping can be adjusted per user needs. Business background (data availability boundaries caused by bans, version changes, migrations, etc.) goes into the sibling `context.md`.

> **④ conditional confirmation**: per metric, show a caliber summary (initial/return event, value field, subject, window). Only interrupt when a caveat is hit (name/config mismatch, subject inconsistency, unclear value field semantics, incomplete observation window); otherwise fill in the probed values directly.

### 4. Create and compile the KB (gate ⑤)

> **Input**: the filled project instance layer from step 3. **Output**: a KB with `buildStatus: compiled`. **Conditional** (gate ⑤).

> **⑤ conditional confirmation**: KB name defaults to "<CompanyName> Business Metrics Definition Library", compile with `--mode incremental`; only interrupt if the user wants to customize, otherwise execute directly.

First run `scaffold.sh` to append the project layer to the company KB, then run the compile commands in order. **`+new` runs only once, when onboarding the customer's first project**; subsequent projects start from `+add` and append files incrementally:

```bash
bash scripts/scaffold.sh --project-id <N> --project-name "<ProjectName>" --company-layer ./kb-<slug>

# First time (first project):
ae-cli kb +new --scope company --name "<KBName>" --project-id <N> --project-name "<CompanyName>"

# Every project (incremental):
ae-cli kb +add --scope company --name "<KBName>" --files '["<kb-<slug>>/index.md","<kb-<slug>>/reference","<kb-<slug>>/metrics","<kb-<slug>>/rules","<kb-<slug>>/projects/project-<N>"]'
ae-cli kb +schema --scope company --name "<KBName>"
ae-cli kb +status --scope company --name "<KBName>"        # poll until schemaStatus: generated
ae-cli kb +compile --scope company --name "<KBName>" --mode incremental
ae-cli kb +status --scope company --name "<KBName>"        # poll until buildStatus: compiled
```

> `+add` `--files` uploads a directory non-recursively (one level of files). **The `projects/` directory only contains the `project-<N>/` subdirectory and has no direct `.md` files, so passing `projects/` directly fails with `No supported files found`**; pass `projects/project-<N>` (which directly contains `registry.md` + `context.md`), or list the full paths individually.
>
> `+schema` and `+compile` are both **asynchronous**: after `+schema` returns `status: generating`, poll `kb +status` until `schemaStatus: generated` before `+compile`, otherwise compile fails immediately with "Schema has not been generated"; after `+compile` returns `status: queued`, poll until `buildStatus: compiled` (may take minutes), treating `failed:0 / parse_failed:0` as pass.

## Scripts

- `scripts/company-scaffold.sh`: the deterministic part of company onboarding (copies the company-layer skeleton `scripts/{index.md,reference,metrics,rules}` → `kb-<slug>/`, creates an empty `projects/`, supports `--families` to trim families and `--list` to list existing company KBs).
- `scripts/scaffold.sh`: the deterministic part of project onboarding (appends `projects/project-<N>/{registry,context}` to the company KB pointed at by `--company-layer` and prints the compile commands; it does not copy company-level files nor create a separate directory).
- `scripts/` also holds the **company-layer skeleton shared across customers**: `index.md` (navigation + changelog), `reference/metric-registry.md` (schema contract), `metrics/*.md` (9 family placeholder templates), `rules/caveats-checklist.md`. The "applicable sub-metrics" in `metrics/*.md` are example defaults — during company onboarding they must be rewritten for the customer and must not be used directly as the customer's caliber.

The agent is responsible for only two judgment calls: confirming/rewriting family calibers during company onboarding, and probing calibers then filling registry/context during project onboarding.

## Completion criteria

- (First time for this customer) the company KB's `index.md` title has been replaced with the real company name, the "Changelog" at the bottom has been recorded, and the metric family set + per-family default calibers have been confirmed by the user.
- `+compile` returns `buildStatus: compiled`.
- Every event name / field name in `registry.md` maps to a real value in the data assets (no placeholders or guessed values left).
- Project-private report IDs / dashboard IDs / tag IDs appear only in `projects/project-<N>/registry.md`, never in company-level files.
- Project business background and data availability boundaries are captured in `context.md` (note "none" when there is no business event).

## FAQ / common mistakes

- **"Can I reuse another project's events/fields?"** No — a new project must use events/fields observed via its own `report get`; old values are almost always wrong (see pitfalls).
- **"`+add` failed with `No supported files found`."** `--files` is non-recursive; pass `projects/project-<N>` (which directly contains `registry.md` + `context.md`), not `projects/`.
- **"`+compile` failed with `Schema has not been generated`."** `+schema` is async; poll `kb +status` until `schemaStatus: generated` first, and again until `buildStatus: compiled` after `+compile`.
- **"Is one KB per project or per customer?"** Per customer — the company layer is shared across that customer's projects, and each project appends its own `project-<N>/`.

## Boundary with other skills

- This skill only does "initialization / bootstrap", not querying. Querying goes through `kb-driven-data-analysis` (orchestration) + `ae-analysis` (execution).
- KB commands themselves reference `ae-kb` (command wrapper); this skill only invokes it at compile time and does not restate every command.
