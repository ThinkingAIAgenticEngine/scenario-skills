# drama-retention-analyzer

Short drama retention analysis skill with a 5-layer funnel model (traffic → opening → plot → commercialization → long-term) and 5 optional drill-down dimensions (segment, time, social, genre comparison, ROI).

## What It Does

Decomposes short drama retention through a structured funnel to precisely locate where retention problems occur — at which layer, which episode, and why. Outputs layered actionable optimization strategies with industry benchmarks.

Not a prediction tool. Not applicable to long-form dramas, games, or e-commerce.

## Prerequisites

- **ae-cli** (6.x) installed and authenticated against ThinkingData
- A short-drama project ID in ThinkingData
- Drama name and drama type (vertical short / mini-program / vertical micro-short)

## Quick Start

1. Ask: "Analyze retention for drama [name] in project [ID]"
2. The skill runs Phase 1 (5-layer core analysis) → outputs a 1-page report with health label, churn Top3, and drill-down menu
3. User selects a drill-down option → Phase 2 expands the selected dimension

## File Structure

```
drama-retention-analyzer/
├── SKILL.md                              # Core instructions (entry point)
├── manifest.yaml                         # Triggers, dependencies, file list
├── README.md                             # This file
└── references/
    ├── drama-type-configs.md             # Per-type thresholds, D1 desensitization, paywall ranges
    ├── data-validation.md               # Data contract, ae-cli commands, quality validation
    ├── sql-templates.md                 # SQL templates (T1-T5) for ae-cli SQL model
    ├── root-cause-rules.md              # Phase 1 attribution rules (13 rules, 5 layers)
    ├── root-cause-rules-dimensions.md   # Phase 2 dimension rules (18 rules, load on demand)
    ├── optimization-playbook.md         # Optimization strategies + benchmarks + verification loop
    ├── report-templates.md              # Phase 1 + Phase 2 report templates
    └── episode_churn_table.md           # Churn table format + health label definitions
```

## Key Design Decisions

See SKILL.md for full design rationale. Highlights: dynamic rule loading (3-5 rules/session), 4-level error degradation chain, low-sample degradation (UV<100), post-implementation verification loop.

## Version

6.1.3
