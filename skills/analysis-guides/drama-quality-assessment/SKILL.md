---
name: drama-quality-assessment
description: Quantitatively scores a single short drama across nine quality dimensions (first-episode appeal, completion quality, in-episode pacing, cliffhanger effect, inter-episode retention, binge depth, payment conversion, heat trend, and user engagement) and provides AI-powered diagnosis and optimization suggestions based on ThinkingEngine tracking data. Use when the user asks to evaluate a short drama's episode quality, diagnose episode-level quality issues, or assess drama performance. Requires a TE project ID. Not for long-form dramas, games, or general retention-only analysis; use drama-retention-analyzer for funnel-based retention drill-downs.
---

# drama-quality-assessment

> **CRITICAL - This skill orchestrates a multi-step analysis flow.** Execute in the order of `references/steps/`; do not skip steps or fabricate data.
> **CRITICAL - Step 01 is a mandatory gate.** The analysis target (short drama name) and analysis time range must be explicitly confirmed by the user before data collection begins. Never infer the drama name automatically when it is missing.
> **CRITICAL - Use only `ae-cli` for all data operations.** Command patterns are in `references/adapters/ae-cli.md`. Do not guess command names, flags, JSON payloads, project_id, event names, or property names.
> **CRITICAL - `references/config/event_mapping.yaml` is the bridge between business concepts and fields.** The standard event/property candidate-name lists live in this file; reuse it to complete the mapping when switching projects (mapping results go to user memory, never written back to this file).

## Applicable Scenarios

- Post-launch performance evaluation of a drama
- Locating problematic episodes and their root causes
- Providing data support for content optimization and promotion decisions
- Supports three formats: vertical mini-drama (Douyin/Kuaishou), horizontal short drama (iQiyi/Youku/Tencent), and private-platform drama

## Global Conventions

### Interaction Checkpoints

The whole flow has two mandatory interaction checkpoints that let the user participate in decisions instead of running through to completion in one go:

| Checkpoint | Location | User Decision |
|------|------|---------|
| Checkpoint 1 | After Step 02 data collection | Choose which dimensions participate in scoring |
| Checkpoint 2 | After Step 03 score calculation | Whether to run deep diagnosis, output the report directly, or inspect a specific episode first |

### Parallelism Convention

- Step 02 runs queries in three dependency-aware phases (see [steps/02_query_data.md](references/steps/02_query_data.md) and [query_patterns.md](references/query_patterns.md)): Phase A issues all independent synchronous queries in parallel; Phase B runs the paywall-dependent payment funnel and submits the async detail exports; Phase C polls the async artifacts. Queries within a phase run in parallel, across phases in order — never guess a dependency away or serialize independent calls.
- A single dimension query failure does not block the overall flow; the final report marks "this dimension was not collected due to XX and has been skipped."

### Language Convention

- Skill instructions, config files, templates, and reference docs are written in English (language-compliance requirement).
- **User-visible output MUST be translated to Chinese** before being presented: report content, checkpoint summaries, interaction prompts, diagnostic wording, and confirmation dialogs.
- Translate dimension names, grade labels, and suggested actions using the authoritative terms in [Chinese Output Glossary](#chinese-output-glossary) so terminology stays consistent across reports.
- Event/property names in the report keep the mapped project-specific actual names (never translate event/property identifiers).

### Chinese Output Glossary

Standard Chinese terms for user-facing output. When translating English terms from config files or templates into the report, use these exact terms:

| English term | 中文译名 |
|---|---|
| First-Episode Appeal | 首集吸引力 |
| Completion Quality | 完播质量 |
| In-Episode Pacing | 集内节奏 |
| Cliffhanger Effect | 卡点效果 |
| Inter-Episode Retention | 集间留存 |
| Binge Depth | 连读深度 |
| Payment Conversion | 付费转化 |
| Heat Trend | 热度趋势 |
| User Engagement | 用户互动 |
| Potential Hit (grade S) | 爆款潜力 |
| Quality Content (grade A) | 优质内容 |
| Average (grade B) | 中规中矩 |
| Multiple Issues (grade C) | 问题较多 |
| Poor Quality (grade D) | 质量不佳 |
| Full Promotion | 全力推广 |
| Continued Investment | 持续投入 |
| Targeted Optimization | 针对性优化 |
| Key Rectification | 重点整改 |
| Stop Loss | 建议止损 |
| Vertical mini-drama | 竖屏微短剧 |
| Horizontal short drama | 横屏短剧 |
| Private-platform drama | 自有平台短剧 |

### Key Principles

Before analysis, the short drama name and analysis time range must be confirmed first; only after confirmation load config files and call ae-cli.
- **In-Episode Pacing degrades gracefully**: it needs either a play-progress event with a progress property, or a play-duration property (detail-export fallback). When neither exists, the whole dimension is marked N/A (its weight is reallocated) rather than guessed.

---

## Architecture

```
drama-quality-assessment/
├── SKILL.md                          ← Orchestrator (this file)
├── references/
│   ├── adapters/ae-cli.md            ← ae-cli command patterns (tool adapter layer)
│   ├── config/
│   │   ├── dimensions.yaml           ← 9 dimension definitions, weights
│   │   ├── scoring_rules.yaml        ← scoring thresholds, tiered mapping rules
│   │   └── event_mapping.yaml        ← standard event/property candidate-name list
│   ├── steps/
│   │   ├── 01_parse_config.md        ← business confirmation + technical config
│   │   ├── 02_query_data.md          ← data collection (9 dimensions in parallel)
│   │   ├── 03_calculate_score.md     ← score calculation + heatmap
│   │   ├── 04_diagnose.md            ← AI diagnosis
│   │   └── 05_generate_report.md     ← report generation
│   ├── templates/
│   │   └── report_template.md        ← report template
│   ├── dimension_details.md          ← dimension calculation formulas
│   ├── query_patterns.md             ← per-dimension query templates (definition JSON)
│   └── anomaly_patterns.md           ← library of 12 anomaly/opportunity patterns
```

---

## Step Overview

```
Step 1 Parse Config → Step 2 Data Collection → 🛑Checkpoint 1 → Step 3 Score Calculation → 🛑Checkpoint 2 → Step 4 Diagnosis → Step 5 Report Generation
```

| Step | File | Depends on | Output |
|------|------|------|------|
| 01 | [steps/01_parse_config.md](references/steps/01_parse_config.md) | — | Business/technical config, event mapping, drama filter |
| 02 | [steps/02_query_data.md](references/steps/02_query_data.md) | Step 01 | Raw data for 9 dimensions |
| 🛑 Checkpoint 1 | — | Step 02 | User chooses scoring scope |
| 03 | [steps/03_calculate_score.md](references/steps/03_calculate_score.md) | Step 02 | Scorecard + heatmap |
| 🛑 Checkpoint 2 | — | Step 03 | User decides whether to diagnose |
| 04 | [steps/04_diagnose.md](references/steps/04_diagnose.md) | Step 03 | Diagnostic insights + optimization suggestions |
| 05 | [steps/05_generate_report.md](references/steps/05_generate_report.md) | Step 03/04 | Full report |

---

## Core Index

### Config

| File | Purpose |
|------|------|
| [config/dimensions.yaml](references/config/dimensions.yaml) | 9 dimension definitions, weights, metric list |
| [config/scoring_rules.yaml](references/config/scoring_rules.yaml) | Scoring thresholds, tiered linear mapping rules, grade definitions |
| [config/event_mapping.yaml](references/config/event_mapping.yaml) | Standard event/property candidate-name list (business-concept ↔ field bridge) |

### Reference Docs

| File | Purpose |
|------|------|
| [dimension_details.md](references/dimension_details.md) | Calculation formulas and special handling rules per dimension |
| [query_patterns.md](references/query_patterns.md) | Per-dimension query templates (definition JSON) |
| [anomaly_patterns.md](references/anomaly_patterns.md) | Library of 12 anomaly/opportunity patterns (used by Step 04) |

### Output Template

| File | Purpose |
|------|------|
| [templates/report_template.md](references/templates/report_template.md) | Full report structure (five sections) |

### Tool Adapter

| File | Purpose |
|------|------|
| [adapters/ae-cli.md](references/adapters/ae-cli.md) | ae-cli command patterns — load only when ae-cli is available |

---

## 9 Evaluation Dimensions

| Dimension | Weight | Key Metrics |
|------|:---:|------|
| First-Episode Appeal | 15% | First-episode click→play conversion, first-episode completion rate, 1→2 episode jump rate |
| Completion Quality | 10% | Per-episode completion rate, time-segmented completion trend |
| In-Episode Pacing | 10% | Progress retention curve (25%/50%/75%/100%), high-churn positions |
| Cliffhanger Effect | 15% | Episode-end jump rate, 5s cliffhanger jump rate, cliffhanger failure ratio |
| Inter-Episode Retention | 15% | Next-day retention, inter-episode jump rate, churn point distribution |
| Binge Depth | 10% | Binge ≥3 episodes ratio, median binge episodes |
| Payment Conversion | 15% | Payment trigger rate, post-payment watch rate |
| Heat Trend | 5% | Daily average plays, new-user ratio, play peak |
| User Engagement | 5% | Like rate, comment rate, share rate |

Weights can be overridden via conversation, or persisted to `references/config/dimensions.yaml`.

---

## User Input Requirements

**Required:** short drama name, TE project ID

**Optional (with defaults):** analysis time range (default: last 30 days), analysis episode range (default: all), drama type (default: vertical mini-drama), total episode count (auto-inferred), paywall position, custom weights

---

## Weight Customization

- Temporary override: "Set payment conversion weight to 20% and lower heat trend to 3%"
- Persist: "Remember this weight config"
- Restore defaults: "Restore default weights"

---

## Report Output

The report always contains five sections. If the user skips deep diagnosis, sections 3 and 4 remain present with explicit skip notes:
1. **📊 Comprehensive Scorecard** — total score, grade, per-dimension scores
2. **🔥 Per-Episode Heatmap** — episode × dimension score matrix, anomalies highlighted
3. **🔍 AI Diagnosis** — AI-generated data insights and root-cause analysis
4. **💡 Optimization Suggestions** — concrete action suggestions sorted by priority
5. **📝 Data Notes** — data source, coverage, missing dimensions, and weight handling

---

## Start Execution

Read and execute [references/steps/01_parse_config.md](references/steps/01_parse_config.md).
