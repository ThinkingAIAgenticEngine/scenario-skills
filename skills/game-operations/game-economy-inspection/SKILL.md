---
name: game-economy-inspection
version: 2.0.0
description: Proactive game economy ecology health inspection using the 'slow variable + cross-domain correlation' methodology. Inspects combat, economy, equipment, backpack, and monetization domains together to detect gradual structural degradation while macro economy totals may still appear normal. Covers nurturing currency devaluation, equipment recycle anomalies, content pacing imbalance, and related ecosystem issues. Trigger for routine or event-driven early-warning inspection, hero/meta diversity analysis, or monitoring of this Skill's defined slow-variable signals. Use ae-cli, read the matching references/ command manual, and never guess project_id, event names, or parameter formats. Do NOT use when a production-consumption imbalance is already confirmed or when source-point breakdown, suspicious-user investigation, quantified intervention design, or a general economy dashboard is needed; route those to game-economy-balance. Do NOT use for single-metric ad-hoc queries or non-game analysis; route those to ae-analysis.
---

# game-economy-inspection

> **CRITICAL - This skill orchestrates a multi-step inspection pipeline.** Read each step file in `references/steps/` before executing. Do not skip steps or fabricate data.
> **CRITICAL - Step 00 and Step 01 are both mandatory gates.** All uncertain values (timezone, event names, property names, distinguishing properties, thresholds, scenarios, time window) MUST be explicitly confirmed by the user via numbered text replies — never assume them. Step 00 not confirmed → MUST NOT proceed to Step 01; Step 01 not confirmed → MUST NOT proceed to Steps 02-05.
> **CRITICAL - Use `ae-cli` for all data operations.** Read `references/adapters/ae-cli.md` for command patterns. Never guess command names, flags, JSON payloads, project_id, event names, property names, or parameter formats.
> **CRITICAL - `references/config/project_mapping.md` is the sole bridge between business concepts and database fields.** `{{event.xxx}}` and `{{prop.xxx}}` are business concept placeholders, NOT actual field names. When switching projects, only modify this file.
> **CRITICAL - Treat `references/adapters/ae-cli.md` as the source of truth for command syntax.** Keep methodology and metric definitions tool-agnostic.

## When to Use

Use `game-economy-inspection` for **proactive health inspection** of game economy ecosystems:

- Check whether cross-domain structures are gradually degrading even though macro economy totals still look normal
- Inspect whether nurturing currency is silently devaluing (evolution stones, spirit fragments, and other nurturing resources)
- Detect equipment recycle anomalies, material accumulation, and other economy-loop issues
- Detect hero/lineup meta imbalance and narrowing consumption outlets
- Run cross-domain correlation inspection on "multi-domain, gradual, single-metric-silent" ecosystem problems

### Boundary with `game-economy-balance`

Use this Skill to answer **"Is a gradual cross-domain problem emerging?"** Stop after producing verified slow-variable signals, cross-domain confidence, attribution evidence, and investigation urgency.

Do NOT use this Skill when the user already knows that production and consumption are imbalanced, or asks for any of the following; route to `game-economy-balance`:

- Production/consumption source-point breakdown or user-tier comparison
- Suspicious-user, studio, cheat, exploit, or RMT investigation
- Quantified resource adjustment, intervention parameters, rollback design, or governance actions
- A general-purpose economy alert system, dashboard, or monitoring SOP

If this inspection discovers a confirmed economy impact, preserve the metric evidence and attribution chain, then hand off remediation to `game-economy-balance`. This Skill may persist only its own §1-§11 inspection queries and configure alerts only for their user-confirmed slow-variable thresholds.

If the user intent is a single-metric ad-hoc query or non-game analysis, do NOT use this Skill — use `ae-analysis` directly.

## Core Philosophy

Traditional BI dashboards alert on single-week thresholds — slow variables (0.3% weekly fluctuation) never trigger, but 30 days of accumulation slides them out of the safe zone. This skill fills exactly that gap:

> **Do not ask "is there an anomaly this week" — ask "which direction is this heading over the last period".**

At the same time, it puts data scattered across combat, economy, backpack, and monetization dashboards into one chain for cross-validation — normal totals ≠ healthy structure.

## Global Conventions

### Working Directory

All intermediate files written to `{{workspace_dir}}` (default: `/tmp/game-economy-inspection/`). Do NOT rely on LLM memory between steps.

### Status Codes

| Status Code | Meaning | Next Action |
|-------------|---------|-------------|
| `STEP_SUCCESS` | Step completed, valid data | Continue |
| `STEP_EMPTY` | Step completed, no matching data | Write empty placeholder, continue |
| `STEP_ERROR` | Step partially failed | Write error placeholder, continue |
| `STEP_FATAL` | Prerequisites not met | Terminate immediately |

### Degradation Strategy

- Individual metric query failures do not block the overall flow — mark as "Data Missing" in the final report.
- Step 00 failure → `STEP_FATAL`.
- Step 01 user termination → `STEP_FATAL`.

### User Confirmation (Mandatory Gate)

Step 00 and Step 01 both have user-confirmation nodes. All confirmations use **text replies**: list numbered options, the user enters numbers.

- All uncertain values (timezone, event names, property names, distinguishing properties, thresholds) MUST be confirmed by the user — never assume.
- Step 00: project_id, timezone, event/property mapping, distinguishing properties.
- Step 01: scenario, time window, thresholds.
- Fuzzy matching only narrows the candidate range; the final mapping MUST be approved by the user.
- Do NOT fabricate user replies or skip confirmation nodes.

### Parallelism

- Step 02: queries across domains and metrics are mutually independent — fire in one parallel batch.
- Step 04: attribution drilldowns per anomaly signal are mutually independent — parallelizable.

### Language Convention

- All documentation and user-facing output are in English.
- `{{event.xxx}}`, `{{prop.xxx}}` are business concept placeholders.
- Actual field names come from `references/config/project_mapping.md`.

### Metric Reference Convention

Step files reference metric IDs from `references/metric_definitions.md` (e.g. "Execute §1"). The six-element template (Intent/Semantics/Input/Dimension/Judgment/Output) keeps every metric an independently verifiable formula.

---

## Architecture

```
game-economy-inspection/
├── SKILL.md                                ← Orchestrator (this file)
├── references/                             ← Platform-visible content
│   ├── adapters/ae-cli.md                  ← ae-cli command patterns (tool adapter)
│   ├── config/                             ← Configuration
│   │   ├── project_mapping.md              ← Project config (sole bridge)
│   │   └── scenarios.json                  ← Preset scenario templates
│   ├── steps/                              ← Step-by-step execution
│   │   ├── 00_preflight.md                 ← Step 00 pre-flight check
│   │   ├── 01_scope.md                     ← Step 01 define scope
│   │   ├── 02_baseline.md                  ← Step 02 baseline query
│   │   ├── 03_anomaly.md                   ← Step 03 anomaly detection
│   │   ├── 04_attribution.md               ← Step 04 attribution
│   │   └── 05_report.md                    ← Step 05 generate report
│   ├── templates/report_template.md        ← Report output template
│   ├── metric_definitions.md               ← 10 inspection metrics (§1-§10)
│   ├── methodology.md                      ← Methodology (slow variable, cross-domain, confidence)
│   ├── attribution_chains.md               ← Attribution chain templates
│   └── scenario_guide.md                   ← Custom scenario guide
└── scripts/                                ← Reserved (no scripts yet)
```

---

## Step Overview

```
┌─────────────────────────────────────────┐
│          00 Pre-flight Check            │
└────────────────────┬────────────────────┘
                     ▼
┌─────────────────────────────────────────┐
│          01 Define Scope (Gate)         │
└────────────────────┬────────────────────┘
                     ▼
┌─────────────────────────────────────────┐
│          02 Baseline Query              │
│   (parallel 30-day trend per domain)    │
└────────────────────┬────────────────────┘
                     ▼
┌─────────────────────────────────────────┐
│          03 Anomaly Detection           │
│   (slope calc + cross-domain check)     │
└────────────────────┬────────────────────┘
                     │
              ┌──────┴──────┐
              │ anomaly?    │
              └──────┬──────┘
              no ↓       ↓ yes
            [End]   ┌──────────────┐
                    │ 04 Attribution│
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │ 05 Report    │
                    └──────────────┘
```

| Step | File | Depends | Metrics | Output | Acceptance |
|------|------|---------|---------|--------|------------|
| 00 | [00_preflight.md](references/steps/00_preflight.md) | None | — | project_id confirmed | project_id + event/property mapping written back |
| 01 | [01_scope.md](references/steps/01_scope.md) | Step 00 | — | `scenario.json` | scenario + window + thresholds confirmed |
| 02 | [02_baseline.md](references/steps/02_baseline.md) | Step 01 | §1-§10 | `baseline_{domain}.json` | ≥4 weekly points per domain |
| 03 | [03_anomaly.md](references/steps/03_anomaly.md) | Step 02 | — | `anomalies.json` | slope + cross-domain confidence computed |
| 04 | [04_attribution.md](references/steps/04_attribution.md) | Step 03 | — | `attribution.json` | root cause + transmission + impact chain |
| 05 | [05_report.md](references/steps/05_report.md) | Steps 03-04 | — | inspection report | user-side verification passed |

---

## Core Index

### Metric Definitions → metric_definitions.md

| § | Metric | Domain |
|---|--------|--------|
| §1 | PVP Appearance Rate HHI Index | Combat |
| §2 | Class Appearance Rate Distribution | Combat |
| §3 | Class Win Rate Gap | Combat |
| §4 | Nurturing Currency Earn/Consume Ratio | Economy |
| §5 | Nurturing Currency Consumption Concentration | Economy |
| §6 | Average Nurtured Heroes per Player | Economy |
| §7 | Nurturing Material Holding Change Rate | Backpack |
| §8 | Cold Hero Fragment Accumulation Rate | Backpack |
| §9 | Nurturing Bundle Conversion Rate | Monetization |
| §10 | Nurturing Category Revenue Share Change | Monetization |
| §11 | Equipment Recycle-before-use Ratio | Equipment |

### Reference Documents

| Document | Purpose |
|----------|---------|
| [methodology.md](references/methodology.md) | Methodology: slow-variable judgment, cross-domain correlation rules, confidence assessment |
| [attribution_chains.md](references/attribution_chains.md) | Attribution chain templates + investigation steps |
| [config/scenarios.json](references/config/scenarios.json) | Preset scenario templates (loaded in Step 01) |
| [scenario_guide.md](references/scenario_guide.md) | Custom scenario definition guide |
| [config/project_mapping.md](references/config/project_mapping.md) | Project config — sole bridge between concepts and fields |

### Output Templates

| Template | Purpose |
|----------|---------|
| [templates/report_template.md](references/templates/report_template.md) | Inspection report structure (four sections + appendix) |

### Tool Adapter

| Document | Purpose |
|----------|---------|
| [adapters/ae-cli.md](references/adapters/ae-cli.md) | ae-cli command patterns — load only when ae-cli is present |

---

## Verification

Every step defines explicit acceptance criteria (see each step file's "Acceptance Criteria" section). The final report must pass user-side verification before sign-off.

### Data Verification (execution-time)

| Check | Method | Pass criterion |
|-------|--------|----------------|
| Trend completeness | Inspect per-domain baseline series | ≥4 weekly data points, no large gaps |
| Slope correctness | Least-squares linear regression | Slope unit = per-week, direction consistent with the series |
| Cross-domain echo | Apply §3.2 validation matrix | ≥1 related domain echoes in the expected direction |

### User-side Verification (report sign-off)

After Step 05 outputs the report, ask the user to verify before signing off:

1. **Spot-check key numbers**: pick 2-3 metric values and compare against the game's own dashboards. Any mismatch requires re-query.
2. **Confirm anomaly judgment**: for each warning/attention signal, the user confirms whether the detected direction matches business intuition.
3. **Confirm attribution root cause**: the user validates whether the traced root cause aligns with known version/operations events.
4. **Sign-off criteria**: the report is verified when (a) no critical metric is marked "Data Missing", (b) slope values are reproducible from the baseline data, and (c) the user confirms the anomaly and attribution conclusions. Otherwise return to the failed step and re-run.

---

## Start Execution

Read and execute [references/steps/00_preflight.md](references/steps/00_preflight.md).
