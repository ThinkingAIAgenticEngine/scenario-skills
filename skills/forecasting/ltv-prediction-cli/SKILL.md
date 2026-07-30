---
name: ltv-prediction-cli
description: >
  Predict user lifetime value (LTV) and forecast cohort revenue using ae-cli data with exponential curve fitting and RFM/VIP segmentation. Use when users ask about LTV prediction, lifetime value forecast, cohort revenue projection, user value estimation, LTV segmentation, payback period calculation, or how much revenue a user cohort will generate. Do not use for single metric queries, dashboard-only work, or retention analysis without LTV forecasting intent.
---

# LTV Prediction Skill (CLI Edition)

## Language Policy

All generated skill content MUST be written in English by default.
Exception: If the user explicitly requests Chinese, comply.
Output charts and tables use the user's language for labels.

---

## Role

LTV Prediction Specialist specializing in:
- Detecting and mapping project-specific payment events and properties
- Executing cohort LTV curve fitting with exponential decay models
- Computing stratified LTV across RFM / pay-tier / VIP segments
- Interactive clarification when prerequisites are incomplete

---

## Core Definitions

### LTV (Lifetime Value)

Total revenue a user generates from acquisition to churn.

### Prediction Methodologies

| Method | ID | Model | Input | Output |
|--------|----|-------|-------|--------|
| Cohort LTV Curve | B2 | Exponential decay | Historical cohort LTV data | LTV_inf, k, fitted curve, predictions |
| Stratified LTV | B3 | Segment aggregation | RFM / pay-tier / VIP groups | Per-segment LTV table |

### Key AE Data Assets

| Asset | Semantic Example | Type | Purpose |
|-------|-------------|------|---------|
| Cohort event | `register` | Event | Defines the initial cohort |
| Payment event | `payment` | Event | Revenue source |
| Payment amount | `pay_amount` | Event property (number) | Monetary value |
| First pay flag | `is_first_pay` | Event property (bool) | First purchase detection |
| Total pay amount | `total_pay_amount` | Optional user property (number) | Pay-tier grouping when compiler-resolved |
| First pay time | `first_pay_time` | User property (datetime) | Conversion timing |
| VIP level | `vip_level` | User property (number) | Tier stratification |
| Pay tier tag | `pay_stratum` / `pay_layer` | Tag / Virtual property | Payment segmentation |
| RFM tag | `rfm` / `付费RFM标签` | Tag | RFM segmentation |
| LTV reports | Various (D7/D14/D30) | Report | Existing LTV data |
| LTV metrics | `day_1_ltv`, `ltv_7`, `d30_ltv` | Metric | Saved LTV values |

Names in this table are semantic examples, not project defaults. Verify the
compiler's resolved names.

---

## Workflow Overview

```
Gate G1: Data Mapping → Gate G2: LTV Report Check → Gate G3: Python Env Check
    ↓
Execute B2 and/or B3 branches
    ↓
Output: Parameters + Predictions + Charts + Recommendations
```

### Phase 1: Prerequisite Check (Interactive Gates)

Execute 3 interactive gates before any analysis. Stop and ask user if any gate fails.

### Phase 2: Data Collection

Use ae-cli three-path priority to fetch required data per methodology.

### Phase 3: Computation & Prediction

- B2: Python scipy curve_fit for exponential decay
- B3: ae-cli revenue analysis for segment LTV

### Phase 4: Output & Visualization

Deliver results with charts, tables, and actionable recommendations.

---

## Interactive Gates (MANDATORY — execute before analysis)

### G1: Data Mapping

**Purpose**: Resolve the cohort event, payment event, and amount property without guessing.

**Procedure**:
1. Submit the semantic `revenue` or `event` AI-facing definition first; the compiler resolves project metadata.
2. Inspect `meta.resolved`, `meta.warnings`, and any structured `meta.errors`.
3. Only when compilation returns clarification candidates or an explicit resolution capability error, use `analysis-meta event list` / `property list`.
4. Ask the user only when multiple returned candidates remain semantically plausible.
5. Store the resolved names as `COHORT_EVENT`, `PAYMENT_EVENT`, and
   `PAY_AMOUNT_PROP` for subsequent queries.

**Never proceed without confirmed data mapping.**

### G2: LTV Report Check

**Purpose**: Determine if the project already has LTV reports/dashboards to reuse.

**Procedure**:
1. Run `ae-cli analysis report list --project-id <id> --query LTV`
2. Run `ae-cli analysis dashboard list --project-id <id> --query LTV`
3. If LTV reports exist → inform user and ask: "Existing LTV reports found (IDs: X, Y, Z). Should I reuse them or create fresh ad-hoc queries?"
4. If no LTV reports → proceed with `analysis adhoc run` using an AI-facing definition.
5. If reports exist but are empty/incomplete → fall back to ad-hoc queries.

### G3: Python Environment Check

**Purpose**: Ensure scipy/numpy are available for curve fitting (B2).

**Procedure**:
1. Run `python3 -c "import numpy; import scipy; print('OK')"` to check availability.
2. If import fails, ask for permission to create an isolated virtual environment:
   ```bash
   python3 -m venv "$SKILL_DIR/.venv"
   "$SKILL_DIR/.venv/bin/python" -m pip install -r "$SKILL_DIR/scripts/requirements.txt"
   ```
3. If installation fails → ask user: "Python scipy installation failed. B2 (curve fitting) requires it. Should I proceed with B3 only (no Python dependency)?"

**Important**: Never use `--break-system-packages`, never modify the system Python environment, and never assume a machine-specific installation path.

---

## Output Format

### B2 Output Structure

```json
{
  "model": "shifted_exponential",
  "parameters": {
    "ltv_base": 27.83,
    "ltv_inf": 120.86,
    "decay": 0.0685
  },
  "quality": {
    "r_squared": 0.9823,
    "mae": 2.39,
    "point_count": 6
  },
  "predictions": {
    "D60": 119.34,
    "D90": 120.67,
    "D180": 120.86,
    "D365": 120.86
  },
  "half_life_days": 10.1,
  "steady_state_90pct_days": 33.6,
  "covariance": {
    "parameter_order": ["ltv_base", "ltv_gain", "decay"],
    "matrix": []
  }
}
```

### B3 Output Structure

```json
{
  "segments": [
    {
      "segment_name": "重要保持客户",
      "segment_type": "RFM",
      "user_count": 1161,
      "avg_ltv": 2250.62,
      "total_revenue": 2612970,
      "revenue_share_pct": 17.2
    }
  ],
  "segmentation_dimensions": ["RFM", "pay_tier", "VIP"],
  "data_period": "recent_90_days"
}
```

---

## Trigger Conditions (must satisfy ALL)

- Intent verb: predict / forecast / estimate / calculate LTV
- Target: user lifetime value or revenue projection
- Context: standalone LTV prediction request (not just querying a single metric)

---

## Absolutely NOT Triggered

- Request to query a single data value (e.g., "what is today's revenue?") → ae-analysis-intent
- Request to create a report or dashboard without prediction intent → ae-analysis-intent
- General data exploration without LTV context → ae-analysis
- Request about retention rate alone (without LTV) → ae-analysis-intent
- Request for ML-based early LTV prediction (B1/XGBoost) or survival analysis (B4/Cox) → not supported by this skill; recommend external ML tools

---

## Skill Boundaries

This skill covers ae-cli-driven LTV prediction with exponential curve fitting (B2) and stratified segmentation (B3). For the following scenarios, route to the companion skill:

- **User directly provides data without a TE project** → `ltv-prediction`
- **User needs payback period / CAC analysis** → `ltv-prediction`
- **User needs mature cohort decay rate borrowing** → `ltv-prediction`
- **User needs multi-function comparison (Power/Log/Exponential) instead of shifted exponential only** → `ltv-prediction`
- **User needs ML-based user-level prediction (RandomForest)** → `ltv-prediction` (Path C)

This skill is preferred when the user has a TE project with ae-cli access, needs automated data retrieval, or requires stratified LTV by RFM/pay-tier/VIP.

---

## Dependencies

- ae-cli: All data queries
- Python3 + numpy + scipy: Curve fitting (B2)
- Installation mirror: https://pypi.tuna.tsinghua.edu.cn/simple
