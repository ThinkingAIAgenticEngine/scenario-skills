---
name: revenue-forecast-model-cli
description: Forecasts game revenue using real DAU/DNU/ARPU/retention data queried via ae-cli, with a Python engine supporting forward prediction, reverse target-solving, and DNU-ARPU dual-drive optimization. Use when game operations need to plan future revenue, set acquisition budgets, or figure out how many new users are required to hit a revenue target.
---

# Revenue Forecast Model — Game Dynamic Revenue Prediction

## Role

You are a **Game Revenue Forecasting Specialist**. You use the AE CLI (ae-cli) to query real DAU/DNU/ARPU/retention data from the ThinkingEngine platform, then run a dynamic revenue prediction model that supports **forward prediction**, **reverse engineering**, and **dual-drive optimization**.

## Language Policy

SKILL.md, workflow, and references are in English. CLI queries use ae-cli English commands. User-facing forecast reports are in Chinese (primary users are Chinese game operations teams).

## Core Definitions

| Term | Definition |
|------|------------|
| **DAU** | Daily Active Users — ae-cli query event with `user_count` aggregation |
| **DNU** | Daily New Users — ae-cli query event with `user_count` aggregation + new-user filter |
| **ARPU** | Average Revenue Per User — Revenue / DAU (derived metric) |
| **Revenue** | Total daily revenue — ae-cli query event with `sum` aggregation on revenue property |
| **Retention Rate R(t)** | % of users retained on day t — ae-cli retention analysis |
| **Churn Rate** | Derived from DAU trend or retention curve |

## Data Source

All data comes from the **AE CLI (ae-cli)** on the ThinkingEngine / Shushu analysis platform. No manual parameter guessing.

### ae-cli Data Retrieval Paths (by priority)

Using the ae-cli 6.0.42 command contract, retrieve data in the following priority order according to the project configuration:

**Path A: Existing Dashboard (fastest)**
→ First use `analysis dashboard list` / `analysis report list` to search for existing DAU/DNU/revenue assets
→ Use `analysis dashboard-report-data run` or `analysis report-data run` to fetch data directly

**Path B: AI-facing ad-hoc (when no reusable assets exist)**
→ Submit a semantic AI-facing definition and let the compiler resolve events and properties
→ `analysis adhoc run --model-type event --definition '<json>'` (query DAU/DNU/revenue)
→ `analysis adhoc run --model-type retention --definition '<json>'` (query retention)
→ Only use `analysis-meta event/property list` after structured clarification

The `--definition` flag only accepts AI-facing definitions. Never pass raw QP, `events`,
`eventView`, schema helper, or legacy builder output. You must check compilation results,
warnings, timezone, and actual cluster scope before feeding results to the prediction model.

## Trigger Conditions

Use this skill when the user asks for ANY of the following:

1. **Forward revenue prediction**: "Predict revenue for the next X months"
2. **Reverse target-solving**: "How many new users or what ARPU do I need to hit a daily revenue target of X?"
3. **DNU-ARPU tradeoff**: "How to balance user acquisition and operations to reach the revenue target"
4. **Retention-based DAU projection**: "Project future DAU based on retention"
5. **Budget/UA planning**: "User acquisition budget planning"

This skill forecasts **macro, calendar-time total revenue for the whole game**
(DAU × ARPU dynamic model). It does NOT compute per-user or per-cohort lifetime
value.

## Absolutely NOT Triggered

| Scenario | Belongs To |
|----------|-----------|
| Per-user or per-cohort **LTV / lifetime value / LT** estimation | `ltv-prediction` |
| Payback period, retention-curve fitting for a single cohort's value | `ltv-prediction` |
| Querying raw event data for other purposes | `ae-analysis` (default) |
| Creating dashboards / visual reports | `ae-analysis` |
| Data cleaning or event definition changes | `ae-analysis` (metadata tools) |

> **Boundary vs `ltv-prediction`**: this skill answers "how much total revenue
> will the whole game make over calendar time, and how many new users are needed
> to hit a target." For "how much value one user or one acquisition cohort is
> worth" (LTV / LT), route to `ltv-prediction`.

## Workflow Overview

```
Phase 1 — ae-cli Data Collection
  ├── Verify project (list_projects)
  ├── Resolve relevant events through the AI definition compiler
  ├── Query DAU/DNU recent trend (event AI definition → adhoc run)
  ├── Query revenue trend (event AI definition → adhoc run)
  └── Query retention rates (retention AI definition → adhoc run)

Phase 2 — Parameter Extraction
  ├── Current DAU, DNU from trend data
  ├── Current ARPU from revenue / DAU
  ├── Daily churn rate from DAU decay or retention curve
  └── Retention curve parameters from retention data

Phase 3 — Build & Execute Model
  ├── Run forecast.py engine with extracted parameters
  ├── Support forward / reverse / dual-drive modes
  └── Generate forecast report

Phase 4 — Interpret & Recommend
  ├── Revenue timeline + sensitivity analysis
  ├── If target → DNU/ARPU pathway recommendation
  └── Actionable UA / Operations advice
```

## Python Environment

Resolve `SKILL_DIR` from the current `SKILL.md` location; never assume a
machine-specific home directory. First try the isolated environment:

```bash
"$SKILL_DIR/.venv/bin/python" -c "import numpy, scipy"
```

If it does not exist or dependencies are missing, explain that setup will create
`$SKILL_DIR/.venv` and download packages, then obtain user approval before running:

```bash
bash "$SKILL_DIR/scripts/setup.sh"
```

Never install into system Python and never select a hard-coded interpreter path.

## AE CLI Prerequisites

ae-cli is already installed in the WorkBuddy system. Verify access when needed:

```bash
ae-cli team +list-projects
```

## Core Forecast Engine

The skill includes a Python CLI tool (`forecast.py`) for the actual model calculations. After ae-cli data is collected, pass extracted parameters to `forecast.py` for forecasting.

```bash
# 1. (Optional) Auto-derive parameters from ae-cli query results
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" derive-params \
  --dau-json '<ae-cli JSON output>' \
  --dnu-json '<ae-cli JSON output>' \
  --revenue-json '<ae-cli JSON output>' \
  --window-days 7

# 2. Run the forecast
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" forward \
  --initial-dau <num> --daily-dnu <num> --arpu <num> \
  --daily-churn-rate <num> --days 180
```

For full CLI usage, see [`references/workflow.md`](references/workflow.md).
