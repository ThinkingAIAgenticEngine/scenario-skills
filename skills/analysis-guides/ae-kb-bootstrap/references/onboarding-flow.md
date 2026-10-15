# New customer KB initialization: company onboarding + caliber probing flow

## Goal

First run **company onboarding** (once per customer; initializes that customer's company KB directory), then **project onboarding** (once per project; appends a `project-<N>/` under that company KB's `projects/`), probing the new project N's "real events / fields / aggregations / report IDs" and filling them into `projects/project-<N>/registry.md`. Probing takes the **authoritative report definition** as the source of truth — never infer the caliber from report names.

## Company onboarding (once per customer, hard gate)

For a customer's first onboarding, initialize "that customer's company KB directory" (single directory: company-level abstraction layer + empty `projects/`). The deterministic part is done by `company-scaffold.sh`; caliber judgments are done by the agent after confirming with the user.

```bash
bash scripts/company-scaffold.sh --company <slug> --company-name "<CompanyName>" [--families event,retention,prop]
```

Produces `kb-<slug>/` (single directory, company-level files + empty `projects/`). Confirm item by item:

| todo | confirmation question | default |
| --- | --- | --- |
| metric family set | which families to include? | default 9 families; delete families the customer does not need (no LTV → delete `metrics/ltv.md`) |
| per-family applicable sub-metrics | do the family's "applicable sub-metrics" match the customer's business? | template examples; must be rewritten for the customer, removing irrelevant sub-metrics |
| per-family recommended machine-readable definition | what is the family's company-level default (initial/return event, value field role, aggregation, subject, window)? | none (must confirm, never guess) |
| index title | replace `<CompanyName>` with the real name? | must change |
| mandatory default vs project override | which are company-level mandatory defaults, which allow project-level override? | value field semantics, pay-rate denominator, default analysis subject must be clarified |

> **Company onboarding hard gate**: the metric family set + per-family caliber defaults must be confirmed by the user; the agent must not scan all projects and guess the customer's caliber on its own.

When done, replace the `index.md` title with the real company name and record it in the "Changelog" at the bottom of `index.md` (this is the onboarding-completion marker). Afterwards, this customer's projects use `scaffold.sh --company-layer ./kb-<slug>` to append the project layer to this directory.

### Company-layer versioning note

Once the company layer changes (adding/removing a metric family, changing a family's default caliber), previously compiled KBs are not synced automatically — a recompile is needed to pick up the new caliber. **Caliber changes should be made on the company layer + recompiled, not by editing a single project registry, which would make the company layer drift from reality.**

## Confirmation checklist (5 gates)

The whole initialization has 5 confirmation points. **Hard gates (①②③) must be confirmed before continuing**; **conditional confirmations (④⑤) have defaults and only interrupt when a caveat is hit or the user wants to customize**. Prefer option-style questions for hard gates (offer default/recommended options) to avoid open-ended questions blocking the flow.

### ① Project confirmation (hard gate)

Rationale: if the target project is wrong, all subsequent probing, caliber filling, and compiling is wasted work.

> The project I'm going to initialize is project_id=`<N>` "<ProjectName>", correct?

Default: none (must confirm).

### ② Authoritative caliber source (hard gate)

Rationale: the same project may have multiple dashboards with conflicting calibers; "which one wins" determines every subsequent event/field value.

Search the project's readable assets first, then ask:

> Which dashboard/report (or set of assets) is the authoritative caliber template?

Default: none (must be specified by the user; the agent must not scan all projects and guess).

### ③ Metric family scope (hard gate)

Rationale: the scanned metric families are listed (model→family mapping + the reports covered by each family).

> Which metric families to include?

Default: all core families; exclude non-standard families such as SQL, rank_list.

### ④ Per-metric caliber (conditional confirmation)

Rationale: show the probed caliber summary for each metric.

> `<metric>` caliber: initial=`<X>` / return=`<Y>` / value=`<Z>` / subject=`<S>` / window=`<W>`, anything to change?

Default: only interrupt when a caveat is hit (name/config mismatch, subject inconsistency, unclear value field semantics, incomplete observation window); otherwise fill in the probed values directly.

### ⑤ Compile parameters (conditional confirmation)

Rationale: show the KB name and compile command.

> Use the default KB name "<CompanyName> Business Metrics Definition Library" and compile with `--mode incremental`, correct?

Default: pass through; only interrupt if the user wants a custom KB name / scope / mode.

## Probing flow

### 1. Confirm the project (gate ①②)

First run gates ①② from the confirmation checklist: confirm `project_id` / project name, then have the user specify the authoritative caliber dashboard or report from the readable asset candidates.

```bash
ae-cli analysis asset search --project-id <N> --queries '["<business metric or dashboard keyword>"]' --limit 100 --offset 0
```

Do not set `--asset-types` on the first pass: the search should include every readable dashboard and report, including shared read-only assets. If the response has `has_more: true` and no strong candidate, continue with `--offset <next_offset>`. After checking the broad pages, refine with the business object, metric name, domain term, or a shorter asset-name fragment. Ask the user to choose the authoritative dashboard or report from the results. Use `dashboard list` only when the user specifically wants manageable dashboards or asset search is unavailable. If project metadata needs verification, use `ae-cli analysis` project-info commands or the project metadata file to confirm `project_id` and the project name.

### 2. Read the authoritative report definitions

If the user selects a dashboard, get its report IDs and read each authoritative report definition. If the user selects a report directly, skip the dashboard lookup:

```bash
# dashboard selected: get its report IDs
ae-cli analysis dashboard get --project-id <N> --dashboard-id <id>

# dashboard or report selected: read the authoritative report definition
ae-cli analysis report get --project-id <N> --report-id <id>
```

`report get` returns the report's model config (`model` / events / fields / aggregations / groupings / filters / windows). **Only read the definition — do not execute a data query.**

### 3. Extract caliber fields

Extract item by item from the `report get` definition:

| to extract | corresponding field | use |
| --- | --- | --- |
| model type | `model` | fill `registry.md`'s `model` (e.g. `retention`) |
| initial event | `initial_event` | cohort start |
| return / payment event | `return_event` | return, conversion, or revenue event |
| value field | `value_field` / `simultaneous_metrics` | revenue aggregation field (e.g. `#vp@pay_price`) |
| aggregation | `value_aggregation` / metric config | `sum` / `count` etc. |
| grouping | `group_by` | split dimension |
| filters | `filters` / `initial_filters` | new-user filter, tag filter, etc. |
| observation window | `observation_window` / `unit_num` | metric definition window |

**Field mapping / adaptation**: when a probed field does not match the expected role (name differs, value field missing, subject differs), map it explicitly — record the real field name in `registry.md` and the mismatch in `caveats`; never silently reuse a placeholder. Different customers bury data differently (payment as a dedicated event vs. as a property of another event); when the mapping is not obvious, resolve it with the user at gate ④ instead of guessing.

### 4. Fill the registry

Following the schema contract in `reference/metric-registry.md`, turn the fields above into `registry.md`'s "field mapping" table + "metric quick-reference" table + "YAML instances". Each metric is annotated with `source_report_id` and caveats.

## Pitfalls checklist

| pitfall | symptom | handling |
| --- | --- | --- |
| `dashboard list` / `report list` empty | manageable-asset lists omit a shared read-only dashboard or report | use `asset search` without `--asset-types`; after selection, use `dashboard get` when needed, then `report get` |
| asset search has no candidate | the first page or business keyword finds no relevant asset | follow `next_offset` while `has_more` is true, then refine the keyword; if still empty, ask for access or authoritative dashboard/report IDs instead of guessing |
| report name/config mismatch | name contains "platform/channel/segment" but config has no corresponding group_by/filter | fill only by the config caliber; note the name/config mismatch in caveats |
| model ambiguity | LTV has no standalone `retention_ltv` model | LTV uses `model: retention` + `simultaneous_metrics` to carry the amount (see the instantiation notes in `metrics/ltv.md`) |
| filter scope | some models only support top-level `filters`, not `initial_filters` | before filling the registry, confirm which filter fields the model supports, to avoid writing fields the model rejects |
| guessing event/field names | reusing an old project's events/fields (e.g. project 4's `iap_end` / `#vp@pay_price`) | a new project must use events/fields actually observed via `report get`; never reuse an old project's values |
| `+add` with `projects/` directory errors | `No supported files found in directory: .../projects` | `--files` is non-recursive; `projects/` only contains the `project-<N>/` subdirectory with no direct `.md`; pass `projects/project-<N>` instead, or list full paths individually |
| `+schema` then immediate `+compile` errors | `Schema has not been generated` | `+schema` is async; poll `kb +status` until `schemaStatus: generated` before compiling |
| `+compile` does not return compiled immediately | returns `status: queued`, `buildStatus: compiling` persists for minutes | compile is async; poll `kb +status` until `buildStatus: compiled`, treating `failed:0 / parse_failed:0` as pass |
| incomplete observation window | the latest cohort's window is not full | fill the window as the metric definition; when trend-analyzing, exclude cohorts whose observation window is incomplete (record in caveats) |

## Completion self-check

- [ ] The three hard gates (①②③) are all confirmed; the defaults of the conditional confirmations (④⑤) have been shown to the user.
- [ ] Every `metric_id`'s `initial_event` / `return_event` / `value_field` comes from an actual `report get` reading — no placeholders, no reuse of an old project's values.
- [ ] Every event name / field name maps to a real value in the data assets.
- [ ] Project-private report IDs / dashboard IDs / tag IDs appear only in `registry.md`, never in the four company-level files.
- [ ] `updated_at` is set to the current date and the changelog has been updated.
