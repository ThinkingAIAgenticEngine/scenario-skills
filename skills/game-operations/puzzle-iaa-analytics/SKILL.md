---
name: puzzle-iaa-analytics
description: Analyze puzzle IAA game post-launch version data covering retention, levels, monetization, segmentation, and churn. Trigger when reviewing casual/puzzle game retention, level experience, ad placements, user segmentation, or churn attribution. Not for ad-hoc single-metric queries or non-game analytics.
version: 4.0.0
---

# puzzle-iaa-analytics

> **CRITICAL - This skill orchestrates a multi-step analysis pipeline.** Read each step file in `references/steps/` before executing. Do not skip steps or fabricate data.
> **CRITICAL - Step 01 is a mandatory gate.** All config values MUST be explicitly confirmed by the user via numbered text replies. `data_inventory.json` MUST NOT be written until 1.8 Summary Confirmation. Step 01 not confirmed → MUST NOT proceed to Steps 02-06.
> **CRITICAL - Use `ae-cli` exclusively for all data operations.** Read `references/adapters/ae-cli.md` for command patterns. Use `ae-cli analysis adhoc run` (unified) for all ad-hoc analysis — no separate builder step. Never guess command names, flags, JSON payloads, project_id, event names, property names, or parameter formats.
> **CRITICAL - The `references/config/project_mapping.md` file is the sole bridge between business concepts and database fields.** `{{event.xxx}}` and `{{prop.xxx}}` are business concept placeholders, NOT actual database field names. When switching projects, only modify this file.
> **CRITICAL - SKILL.md and references body MUST NEVER reference `references/adapters/`.** Tool knowledge lives only in the adapter layer and does not pollute methodology.

## When to Use

Use `puzzle-iaa-analytics` for IAA puzzle/casual game post-launch data review:

- Post-launch version review: identify core issues in retention, monetization, and level experience
- Provide data-driven priority recommendations for the next version
- Applicable to pure IAA (ad-monetized) puzzle/casual games

If user intent is raw ad-hoc analysis, single-metric queries, or non-game analytics, do NOT use this skill — use `ae-analysis` directly.

## Global Conventions

### Working Directory

All intermediate files written to `{{workspace_dir}}` (default: `/tmp/puzzle-iaa-analytics/`). Do NOT rely on LLM memory between steps.

### Status Codes

| Status Code | Meaning | Next Action |
|-------------|---------|-------------|
| `STEP_SUCCESS` | Step completed, valid data | Continue |
| `STEP_EMPTY` | Step completed, no matching data | Write empty placeholder, continue |
| `STEP_ERROR` | Step partially failed | Write error placeholder, continue |
| `STEP_FATAL` | Prerequisites not met | Terminate Skill immediately |

### Degradation Strategy

- At least **4/7** analysis steps (Steps 02-06) must succeed to enter Step 07 (synthesis).
- Individual query failures do not block the overall flow — mark as "Data Missing" in final report.
- Step 01 failure → `STEP_FATAL`.

### User Confirmation (Mandatory Gate)

Step 01 is the sole interaction window. All confirmations use **text replies**: you list numbered options, the user enters numbers.

- All config final values MUST be explicitly confirmed by user entering a number.
- Exact-match candidates must be reviewed; no auto-accept with "default configuration."
- Zero fuzzy-match results must be reported; user decides manual entry or explicit skip.
- `data_inventory.json` and `project_mapping.md` write-back wait for 1.8 Summary Confirmation.
- Step 01 not confirmed → MUST NOT proceed to Steps 02-06.
- Only mark skipped when user explicitly chooses. Do NOT fabricate user replies.

### Parallelism

- Steps 02, 03, 04: mutually independent, execute fully in parallel.
- Steps 05, 06: depend on Step 02 results.
- Step 07: depends on all Steps 02-06.
- Sub-analyses within each step are also mutually independent — fire in one parallel batch.

### Language Convention

- User-facing output: Chinese (中文).
- Confirmation options MUST be bilingual: format `[N] English name — Chinese meaning`.
- `{{event.xxx}}`, `{{prop.xxx}}` are business concept placeholders.
- Actual field names come from `references/config/project_mapping.md`.

### Metric Reference Convention

Each analysis step references metric IDs from `references/metric_definitions.md` (e.g., "Execute §1 Retention Decay"). The six-element analysis unit template ensures metrics are independently verifiable mathematical formulas.

---

## Architecture

```
puzzle-iaa-analytics/
├── SKILL.md                        ← Orchestrator (this file)
├── references/                     ← Platform-visible content
│   ├── adapters/ae-cli.md          ← ae-cli command patterns
│   ├── config/project_mapping.md   ← Project config (sole bridge)
│   ├── steps/                      ← Step-by-step execution
│   │   ├── 01_validate_data.md
│   │   ├── 02_core_diagnostics.md
│   │   ├── 03_level_deep_dive.md
│   │   ├── 04_user_path_funnel.md
│   │   ├── 05_user_segmentation.md
│   │   ├── 06_data_driven_intervals.md
│   │   ├── 07_synthesis_report.md
│   │   └── 08_publish.md
│   ├── templates/                  ← Output templates
│   │   ├── final_report_template.md
│   │   ├── key_metrics_table.md
│   │   ├── churn_analysis.md
│   │   ├── user_profile.md
│   │   └── recommendations.md
│   ├── metric_definitions.md       ← 17 analysis units (§1-§17)
│   ├── methodology.md              ← Business methodology
│   ├── drilldown_guide.md          ← User drilldown semantics
│   └── segmentation_guide.md       ← Segmentation semantics
└── scripts/
    └── parse_curve.py              ← Knee-point detection
```

---

## Step Overview

```
┌─────────────────────────────────────────┐
│          01 Data Validation             │
└────────────────┬────────────────────────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ 02 Core │ │ 03 Level│ │ 04 Path │
│ Diag    │ │ Deep    │ │ Funnel  │
└────┬────┘ └────┬────┘ └────┬────┘
     │           │            │
     └─────┬─────┘            │
           ▼                  │
     ┌───────────┐            │
     │ 05 Segmen │            │
     └─────┬─────┘            │
           ▼                  │
     ┌───────────┐            │
     │ 06 Interv │            │
     └─────┬─────┘            │
           │                  │
           └────┬─────────────┘
                ▼
         ┌───────────┐
         │07 Synthesis│
         └─────┬─────┘
               ▼
         ┌───────────┐
         │08 Publish │
         └───────────┘
```

| Step | File | Depends | Metrics | Output |
|------|------|---------|---------|--------|
| 01 | [steps/01_validate_data.md](references/steps/01_validate_data.md) | None | — | `data_inventory.json` |
| 02 | [steps/02_core_diagnostics.md](references/steps/02_core_diagnostics.md) | Step 01 | §1 §2 §3 §4 | `core_diagnostics.md` |
| 03 | [steps/03_level_deep_dive.md](references/steps/03_level_deep_dive.md) | Step 01 | §5 §6 §7 §8 §9 | `level_analysis.md` |
| 04 | [steps/04_user_path_funnel.md](references/steps/04_user_path_funnel.md) | Step 01 | §10 §11 | `user_path_analysis.md` |
| 05 | [steps/05_user_segmentation.md](references/steps/05_user_segmentation.md) | Step 02 | §12 §13 | `segmentation_report.md` |
| 06 | [steps/06_data_driven_intervals.md](references/steps/06_data_driven_intervals.md) | Step 02 | §14 §15 §16 §17 | `interval_analysis.md` |
| 07 | [steps/07_synthesis_report.md](references/steps/07_synthesis_report.md) | Steps 02-06 | — | `final_report.md` |
| 08 | [steps/08_publish.md](references/steps/08_publish.md) | Step 07 | — | Feishu doc link |

---

## Core Index

### Metric Definitions → metric_definitions.md

| § | Metric | Domain |
|---|--------|--------|
| §1 | Retention Decay (D2/D3/D7 + decay ratios) | Core |
| §2 | Play Duration (D1/D2/D3-7 per-user avg) | Core |
| §3 | Levels Completed per User | Core |
| §4 | Ad Placement Breakdown (type × scene) | Monetization |
| §5 | First Level Pass Rate | Level |
| §6 | IPU per 10-Level Stage | Level |
| §7 | Per-Level Ad Trigger Cause | Level |
| §8 | Level Retention Curve | Level |
| §9 | Level Pass Rate Curve | Level |
| §10 | Register → First 10 Levels Event Funnel | Path |
| §11 | Churned User Last-Session Behavior Trace | Path |
| §12 | Ad Niche Segmentation Comparison | Segment |
| §13 | Content Consumption Segmentation Comparison | Segment |
| §14 | Ad Frequency-Retention Curve + Knee Detection | Data-Driven |
| §15 | Levels Completed-Retention Curve + Knee Detection | Data-Driven |
| §16 | Stabilized User Behavior Baseline | Data-Driven |
| §17 | Core User Identification (4 types × IPU contribution) | Synthesis |

### Reference Documents

| Document | Purpose |
|----------|---------|
| [methodology.md](references/methodology.md) | Business methodology: judgment criteria, causal logic |
| [drilldown_guide.md](references/drilldown_guide.md) | User drilldown operational semantics |
| [segmentation_guide.md](references/segmentation_guide.md) | Segmentation creation semantics |
| [config/project_mapping.md](references/config/project_mapping.md) | Project configuration — sole bridge between concepts and fields |

### Output Templates

| Template | Purpose |
|----------|---------|
| [templates/final_report_template.md](references/templates/final_report_template.md) | Final report structure (Chapter 1-5 + Appendix) |
| [templates/key_metrics_table.md](references/templates/key_metrics_table.md) | Key metrics one-page summary |
| [templates/churn_analysis.md](references/templates/churn_analysis.md) | Churn causal chain diagram |
| [templates/user_profile.md](references/templates/user_profile.md) | Core user profile |
| [templates/recommendations.md](references/templates/recommendations.md) | Optimization action checklist |

### Tool Adapter

| Document | Purpose |
|----------|---------|
| [adapters/ae-cli.md](references/adapters/ae-cli.md) | ae-cli command patterns — load only when ae-cli is present |

---

## Start Execution

Read and execute [references/steps/01_validate_data.md](references/steps/01_validate_data.md).
