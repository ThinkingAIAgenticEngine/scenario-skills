# Revenue Forecast Model — Detailed Workflow (ae-cli Integrated)

## Phase 0: Prepare an Isolated Python Environment

Resolve `SKILL_DIR` from this skill's location. Never use a path copied from
another machine. First verify the local virtual environment:

```bash
"$SKILL_DIR/.venv/bin/python" -c "import numpy, scipy"
```

If setup is required, tell the user that it creates `$SKILL_DIR/.venv` and
downloads dependencies. Run `bash "$SKILL_DIR/scripts/setup.sh"` only after
approval. Do not install into system Python.

## Phase 1: ae-cli Data Collection

### Step 0: Verify Project

```bash
ae-cli team +list-projects
```

### Data Collection Path Selection

Prioritize reusing saved assets; fall back to AI-facing ad-hoc only when none exist:

| Path | Condition | Method |
|------|-----------|--------|
| **A: Existing Dashboard/Report** | Project already has relevant assets | `dashboard/report list` → `dashboard-report-data/report-data run` |
| **B: AI-facing Ad-hoc** | No reusable assets | `analysis-meta` to confirm names → `analysis adhoc run` |

Do not use removed builder, schema helper, or hand-crafted raw QP.

### Step 1: Resolve Relevant Events

Submit the semantic definitions in Step 2 first. Inspect `meta.resolved`,
`meta.warnings`, and structured compiler errors. Only after a clarification or
resolution capability error, run:

```bash
ae-cli analysis-meta event list --project-id <id> --format table
ae-cli analysis-meta property list --project-id <id> --format table
```

**Semantic candidates to resolve:**

| Data Need | Likely Event Name (varies by project) | Aggregation |
|-----------|---------------------------------------|-------------|
| DAU | `$page_view`, `$AnyEvent`, or game-specific active event | `user_count` |
| DNU | `$sign_up`, `$register`, `create_role` or game-specific install | `user_count` |
| Revenue | `$pay`, `$iap`, `pay_order`, `purchase` | `sum` of revenue property |
| Retention | Initial: `$sign_up` / `$register`, Return: `$AnyEvent` or active event | retention analysis |

Some projects have pre-built metrics for DAU/DNU/ARPU which can be queried as saved metrics.

### Step 2: Query DAU, DNU, and Revenue Trends

```bash
ae-cli analysis adhoc run --project-id <id> --model-type event --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","metrics":[{"event":"<active_event>","aggregation":"user_count"}]}' --format json

ae-cli analysis adhoc run --project-id <id> --model-type event --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","metrics":[{"event":"<register_event>","aggregation":"user_count"}]}' --format json

ae-cli analysis adhoc run --project-id <id> --model-type event --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","metrics":[{"event":"<pay_event>","aggregation":"sum","property":"<revenue_property>"}]}' --format json
```

All placeholders must be replaced by exact metadata or compiler candidates. Review
`meta.resolved`, `meta.warnings`, timezone, and actual cluster scope. ARPU is
derived per day as Revenue / DAU.

### Step 3: Query Retention

```bash
ae-cli analysis adhoc run --project-id <id> --model-type retention --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","retention":{"initial_event":"<register_event>","return_event":"<active_event>","stat_type":"retention","unit_num":1,"rtn_rate_or_num":"rate"}}' --format json
```

Repeat with `unit_num` 3, 7, 14, and 30 when the project supports those horizons.
Do not assume `$AnyEvent` exists.

### Step 4: Extract Model Parameters from Query Results

From the DAU/DNU/revenue trend data, use `derive-params` to automatically compute parameters:

```bash
# Save ae-cli JSON output to files, then:
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" derive-params \
  --dau-json '{"rows":[["2026-06-09","2857"],["2026-06-08","3965"],...]}' \
  --dnu-json '{"rows":[...]}' \
  --revenue-json '{"rows":[...]}' \
  --window-days 7

# Output:
# {
#   "avg_dau": 3877,
#   "avg_dnu": 1378,
#   "avg_arpu": 30.0,
#   "daily_churn_rate": 0.35,
#   "forecast_command": "forecast.py forward --initial-dau 3877 ..."
# }
```

If query results are in the dashboard format (with `reportDataList`), `derive-params` handles that format automatically.

If the data comes from multiple queries (DAU from dashboard, DNU from another), pass JSON strings separately.

**Manual extraction** (if `derive-params` output looks wrong):
1. Parse DAU values from the last 7 days → average = `current_dau`
2. Parse DNU values from the last 7 days → average = `daily_dnu`  
3. Compute daily ARPU: Revenue(t) / DAU(t) → average = `current_arpu`
4. Derive churn rate:
   - If at equilibrium: `daily_churn_rate = daily_dnu / current_dau`
   - From retention: `daily_churn_rate ≈ 1 - D30_retention^(1/30)`

---

## Phase 2: Conversation Flow (Data Collection)

When the user asks for a revenue forecast:

```
1. Ask for project_id
   → "Please provide the project ID so I can pull real DAU/DNU/ARPU data from the system"

2. Resolve events
   → Submit semantic definitions and inspect compiler resolution
   → Use analysis-meta only after structured clarification
   → Confirm with user if multiple exact candidates remain

3. Query and summarize current state
   → "Current game: last 7-day average DAU = X, DNU = Y, ARPU = ¥Z"
   → "D30 retention = W%"

4. User specifies forecast direction
   → Forward: "Predict revenue for the next 6 months"
   → Reverse: "Target daily revenue of X million"
   → Dual-drive: "How to balance UA spend and operations"
```

---

## Phase 3: Build & Execute Model

### Forward Prediction

```bash
# After extracting params from ae-cli data:
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" forward \
  --initial-dau <current_dau> \
  --daily-dnu <current_dnu> \
  --arpu <current_arpu> \
  --daily-churn-rate <derived_churn> \
  --days 180
```

### Reverse — DNU Path

```bash
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" reverse-dnu \
  --initial-dau <current_dau> \
  --current-arpu <current_arpu> \
  --target-daily-revenue <target> \
  --daily-churn-rate <derived_churn> \
  --days 180
```

### Reverse — ARPU Path

```bash
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" reverse-arpu \
  --initial-dau <current_dau> \
  --daily-dnu <current_dnu> \
  --current-arpu <current_arpu> \
  --daily-churn-rate <derived_churn> \
  --target-daily-revenue <target> \
  --days 180
```

### Dual-Drive

```bash
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" dual-drive \
  --initial-dau <current_dau> \
  --current-dnu <current_dnu> \
  --current-arpu <current_arpu> \
  --daily-churn-rate <derived_churn> \
  --target-daily-revenue <target> \
  --days 180 \
  --arpu-lift-pct 0.2
```

### Retention Curve Fitting (from ae-cli retention data)

```bash
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/forecast.py" fit-retention \
  --retention-points '[[1,0.42],[3,0.27],[7,0.15],[14,0.10],[30,0.06]]'
```

---

## Phase 4: Interpret & Recommend

### Forward Forecast Interpretation

| Revenue Trend | What It Means |
|--------------|---------------|
| Declining | DNU insufficient to offset churn → need UA increase or ARPU lift |
| Stable | User base at equilibrium |
| Growing | Healthy acquisition pipeline |

### Churn Rate Estimation from DAU Data

If the project has DAU and DNU data, churn rate can be derived:

```
Daily_Churn(t) ≈ (DAU(t-1) - DAU(t) + DNU(t)) / DAU(t-1)
Average_Churn = mean(Daily_Churn over last 14 days)
```

### ARPU Calculation

```
ARPU(t) = Revenue(t) / DAU(t)
```

### Typical ae-cli Pitfalls

1. **Wrong event name**: inspect compiler candidates, then use `analysis-meta event list` if needed
2. **Missing retention data**: Do not assume `$AnyEvent`; use a metadata-confirmed active event
3. **Revenue property unknown**: Use `analysis-meta property list` on the pay event
4. **Compilation needs clarification**: Show exact candidates from `meta.errors` and ask
5. **Long time range needed**: For DAU trend analysis, 30-90 days of data is recommended

### Advanced: Segment-Based Prediction via ae-cli

If the game tracks user segments (channels, pay vs non-pay), group by those dimensions:

```bash
ae-cli analysis adhoc run --project-id <id> --model-type event --definition \
  '{"time_range":{"mode":"previous","unit":"day","value":30},"time_particle_size":"day","metrics":[{"event":"<active_event>","aggregation":"user_count"}],"groups":[{"field":{"name":"<channel_property>","type":"user_property"}}]}' \
  --format json
```

Then run separate forecasts per segment.
