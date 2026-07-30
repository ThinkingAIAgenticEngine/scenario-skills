# Revenue Forecast Model — Quick Reference

## Core Formulas

### 1. Revenue = DAU × ARPU

### 2. DAU Iteration
```
DAU(t) = DAU(t-1) + DNU(t) - Churned(t)
Churned(t) = DAU(t-1) × Daily_Churn_Rate
```

### 3. Churn Rate from DAU Trend
```
Daily_Churn(t) ≈ (DAU(t-1) - DAU(t) + DNU(t)) / DAU(t-1)
Avg_Churn = mean(churn over last 14 days)
```

### 4. ARPU from ae-cli Data
```
ARPU(t) = Revenue(t) / DAU(t)
```

### 5. Retention Curve (Log)
```
R(t) = a × ln(t + 1) + b
```

### 6. Retention Curve (Power)
```
R(t) = α × t^β
```

### 7. Churn from Retention
```
Daily_Churn ≈ 1 - D30_Retention^(1/30)
```

### 8. Steady-State DAU
```
DAU_ss = DNU / Daily_Churn_Rate
```

### 9. Required DNU
```
Required_DNU = Target_DAU × Daily_Churn
Target_DAU = Target_Revenue / ARPU
```

### 10. Required ARPU Lift
```
Required_ARPU = Target_Revenue / Natural_DAU
Lift% = (Required_ARPU - Current_ARPU) / Current_ARPU
```

---

## ae-cli Commands Quick Reference

### Project & Discovery

```bash
# List projects
ae-cli team +list-projects

# Use only after the compiler asks for event clarification
ae-cli analysis-meta event list --project-id <id> --format table

# Use only after the compiler asks for property clarification
ae-cli analysis-meta property list --project-id <id> --event-name "<event>" --format table

# Search existing reports and dashboards
ae-cli analysis report list --project-id <id> --query "dau" --format table
ae-cli analysis dashboard list --project-id <id> --query "revenue" --format table
```

### DAU / DNU / Revenue (Event Analysis)

```bash
# DAU. Verify the compiler's resolved event name.
ae-cli analysis adhoc run --project-id <id> --model-type event --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","metrics":[{"event":"<active_event>","aggregation":"user_count"}]}' --format json

# DNU. Do not assume $sign_up exists.
ae-cli analysis adhoc run --project-id <id> --model-type event --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","metrics":[{"event":"<register_event>","aggregation":"user_count"}]}' --format json

# Revenue
ae-cli analysis adhoc run --project-id <id> --model-type event --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","metrics":[{"event":"<pay_event>","aggregation":"sum","property":"<revenue_property>"}]}' --format json
```

### Retention Analysis

```bash
# Day-1 retention. Replace both events with real metadata names.
ae-cli analysis adhoc run --project-id <id> --model-type retention --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","retention":{"initial_event":"<register_event>","return_event":"<active_event>","stat_type":"retention","unit_num":1,"rtn_rate_or_num":"rate"}}' --format json
```

### Existing Dashboards (Faster Path)

```bash
# Check if DAU/DNU/revenue dashboards already exist
ae-cli analysis dashboard list --project-id <id> --query "dau" --format table
ae-cli analysis report list --project-id <id> --query "dau" --format table

# If found, query directly
ae-cli analysis dashboard-report-data run \
  --project-id <id> \
  --dashboard-id <id> \
  --report-ids '["<report_id>"]' \
  --format table
```

---

## Industry Benchmarks (China Mobile Games — 2025/2026)

### Retention

| Metric | Top 25% | Median | Bottom 25% |
|--------|---------|--------|------------|
| D1 | >45% | 35-45% | <30% |
| D7 | >20% | 12-20% | <10% |
| D30 | >10% | 6-10% | <4% |

### Daily ARPU by Game Type

| Genre | Daily ARPU Range |
|-------|-----------------|
| Super-casual | ¥0.003 - 0.017 |
| Casual / Puzzle | ¥0.07 - 0.33 |
| Mid-core (RPG, Strategy) | ¥0.33 - 1.67 |
| Heavy (MMO, SLG) | ¥1.0 - 5.0 |
| Card / CCG | ¥0.5 - 2.67 |

### User Lifetime by Game Type

| Genre | Avg LT (days) | Daily Churn |
|-------|--------------|-------------|
| Super-casual | 1-3 | 0.33 - 1.0 |
| Casual | 7-14 | 0.07 - 0.14 |
| Mid-core | 14-30 | 0.03 - 0.07 |
| Heavy / SLG | 30-90+ | 0.01 - 0.03 |

---

## CLI Quick Reference (forecast.py)

```bash
# After user approval, prepare the isolated Skill environment
bash "$SKILL_DIR/scripts/setup.sh"

# Forward
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" forward \
  --initial-dau 50000 --daily-dnu 2000 --arpu 12.5 \
  --daily-churn-rate 0.03 --days 180

# Reverse DNU
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" reverse-dnu \
  --initial-dau 50000 --current-arpu 12.5 \
  --target-daily-revenue 1000000 --daily-churn-rate 0.03 --days 180

# Reverse ARPU
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" reverse-arpu \
  --initial-dau 50000 --daily-dnu 2000 --current-arpu 12.5 \
  --target-daily-revenue 800000 --daily-churn-rate 0.03 --days 180

# Dual-Drive
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" dual-drive \
  --initial-dau 50000 --current-dnu 2000 --current-arpu 12.5 \
  --daily-churn-rate 0.03 --target-daily-revenue 800000 \
  --days 180 --arpu-lift-pct 0.2

# Fit Retention
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" fit-retention \
  --retention-points '[[1,0.42],[3,0.27],[7,0.15],[14,0.10],[30,0.06]]'

# LTV
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" ltv \
  --arpu 12.5 --day1-retention 0.42 --horizon 180
```
