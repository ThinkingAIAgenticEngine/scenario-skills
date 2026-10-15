# <CompanyName> Business Metrics Definition Library

> Company-level knowledge base with layered design: **metric definition layer** (reference / metrics / rules) + **project instance layer** (projects). When querying data, first match the metric definition, then map down to project-specific events and fields.
>
> **This file is a template**: `<CompanyName>`, the metric family collection, and each family's "applicable sub-metrics" are example defaults. Complete the Skill's company-onboarding flow and confirm/rewrite every item before use.

## Module navigation

| Module | Path | Purpose |
| --- | --- | --- |
| Metric Definition Table Schema | [reference/metric-registry.md](reference/metric-registry.md) | Field specification and confirmation rules for the machine-readable metric definition table |
| LTV metric family common definition | [metrics/ltv.md](metrics/ltv.md) | Common calculation definition for revenue-type LTV (placeholder form) |
| Retention metric family common definition | [metrics/retention.md](metrics/retention.md) | Common calculation definition for retention metrics (placeholder form) |
| Event metric family common definition | [metrics/event.md](metrics/event.md) | Core metrics such as active/new/pay scale/per-user/ARPU (placeholder form) |
| Funnel metric family common definition | [metrics/funnel.md](metrics/funnel.md) | Multi-step conversion rate (placeholder form) |
| Distribution metric family common definition | [metrics/distribution.md](metrics/distribution.md) | Segmented distribution (placeholder form) |
| Interval metric family common definition | [metrics/interval.md](metrics/interval.md) | Time interval between key behaviors (placeholder form) |
| Path metric family common definition | [metrics/path.md](metrics/path.md) | User behavior path (placeholder form) |
| Attribution metric family common definition | [metrics/attribution.md](metrics/attribution.md) | Conversion touchpoint attribution / contribution (placeholder form) |
| Property metric family common definition | [metrics/prop.md](metrics/prop.md) | User profile / composition / level distribution (placeholder form) |
| Metric Definition Confirmation Caveats Checklist | [rules/caveats-checklist.md](rules/caveats-checklist.md) | Identify the difference between "metric definition" and "query parameters" before querying data |
| Project instances | `projects/project-<N>/registry.md` | Specific event names, field names, and metric instances for each project |

## Layering principles

- **Company level** (`reference/`, `metrics/`, `rules/`): keep only field roles and placeholders; do not write specific project event names, field names, report IDs, dashboard IDs, or tag names.
- **Project level** (`projects/project-<N>/registry.md`): replace placeholders with real event names, field names, and aggregation methods; it is the single source of truth for querying data.

## Usage flow

1. Match a metric family → read the corresponding common definition in `metrics/`.
2. Map to a project → read `projects/project-<N>/registry.md` to get real events / fields / aggregations.
3. Before querying data → read `rules/caveats-checklist.md` to decide whether to confirm the metric definition with the user.

## Changelog

- <YYYY-MM-DD>: Initialized the company KB (company onboarding); the metric family collection and each family's default definitions are pending confirmation.
