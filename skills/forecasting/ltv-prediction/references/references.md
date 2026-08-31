# LTV Prediction - Quick Reference & Benchmarks (CLI Edition)

## Language Policy

All content in English. Exception: user explicitly requests Chinese.

---

## CLI Command Quick Reference

### Metadata Commands

| Purpose | Command |
|---------|---------|
| List events | `ae-cli analysis-meta event list --project-id <id> --format json` |
| List event properties | `ae-cli analysis-meta property list --project-id <id> --format json` |
| List user properties | `ae-cli analysis-meta property list --project-id <id> --scope user --format json` |
| List tags | `ae-cli analysis user-tag list --project-id <id> --queries '["<keyword>"]'` |

### Analysis Commands

| Purpose | Command |
|---------|---------|
| Query ad-hoc | `ae-cli analysis adhoc run --project-id <id> --model-type event --definition '<ai_definition_json>'` |
| List dashboards | `ae-cli analysis dashboard list --project-id <id> --queries '["LTV"]' --format json` |
| Query dashboard | `ae-cli analysis dashboard-report-data run --project-id <id> --dashboard-id <id> --start-time <date> --end-time <date> --format json` |
| List reports | `ae-cli analysis report list --project-id <id> --queries '["LTV"]'` |
| Query report | `ae-cli analysis report-data run --project-id <id> --report-ids '[<id>]' --start-time <date> --end-time <date>` |

### Creation Commands

| Purpose | Command |
|---------|---------|
| Create adhoc report | `ae-cli analysis report create --project-id <id> --report-name "<name>" --model-type <type> --definition '<ai_definition_json>'`
| Create dashboard | `ae-cli analysis dashboard create --project-id <id> --dashboard-name "<name>" --initial-report-id <id>` |

---

## Time Particle Size Codes

| Code | Granularity | Use Case |
|------|-------------|----------|
| T0 | Hour | Real-time monitoring |
| T1 | Day | Daily LTV trend |
| T2 | Week | Weekly cohort |
| T3 | Month | Monthly stratified LTV |

---

## Analysis Codes

| Code | Meaning | Use in LTV |
|------|---------|------------|
| A100 | Total count | Event frequency |
| A101 | User count | Payer count |
| A102 | Per-user average | ARPU |
| A103 | Sum | Revenue (pay_amount sum) |
| A104 | Unique count | Unique event count |

---

## Industry LTV Benchmarks (Mobile Gaming)

| Genre | D30 LTV (USD) | D90 LTV (USD) | LTV:CAC Target |
|-------|---------------|---------------|-----------------|
| Casual | 0.5 - 2 | 1 - 5 | 3:1 |
| Mid-core | 2 - 10 | 5 - 30 | 3:1 |
| Hard-core / RPG | 5 - 30 | 15 - 100 | 5:1 |
| Card / Strategy | 3 - 20 | 10 - 60 | 3:1 |
| True-money games | 10 - 100+ | 30 - 300+ | 5:1 |

**Key ratios**:
- Healthy LTV:CAC ≥ 3:1 (stop acquisition if < 1:1)
- Whale share: Top 5% users typically drive 40-60% of revenue
- First-pay conversion: 3-8% of new users within D7

---

## Python Troubleshooting

| Error | Fix |
|-------|-----|
| `externally-managed-environment` PEP 668 | Create a project-local virtual environment |
| `ModuleNotFoundError: numpy/scipy` | Install packaged requirements inside that virtual environment after approval |
| `curve_fit` fails to converge | Increase `maxfev=10000`, adjust `p0` initial guesses |
| R² < 0.90 | Use shifted model (not simple), add more data points, extend date range |

---

## LTV Model Selection Guide

| Scenario | Recommended Model | Reason |
|----------|-------------------|--------|
| Product with 30+ days data | B2 (exponential decay) | Sufficient points for curve fitting |
| Product with segmentation data | B3 (stratified) | Direct per-segment LTV |
| Product with both | B2 + B3 combined | Best accuracy and actionable insights |
| Product with < 7 days data | B3 only (no curve fitting) | Not enough points for B2 |
| No payment event data | Cannot proceed | Ask user to configure payment tracking |

---

## Key Formulas

### B2: Shifted Exponential Decay

```
LTV(n) = LTV_base + (LTV_inf - LTV_base) × (1 - e^(-k×n))

Half-life = ln(2) / k
90% steady-state = -ln(0.1) / k
```

### B3: Segment LTV

```
Segment LTV = Total segment revenue / Segment user count
Revenue share = Segment revenue / Total revenue × 100%
```

### ROI Calculation

```
ROI = LTV / CAC
Healthy threshold: ROI ≥ 3 (i.e., LTV:CAC ≥ 3:1)
```
