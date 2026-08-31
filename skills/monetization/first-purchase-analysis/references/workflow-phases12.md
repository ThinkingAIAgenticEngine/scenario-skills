# Phase 1-2 Workflow Details

## Phase 1: Pre-Analysis

### Context Collection

Before starting any analysis, collect:

1. **Time range**: Confirm the analysis period (default: last 30 days if not specified)
2. **Game type**: RPG, SLG, Casual, MOBA, etc.
3. **New user count**: How many new users registered in the period?
4. **First purchase rate**: Current value vs historical baseline
5. **Comparison baseline**: Same period last month/year? Or arbitrary?

### Confirmation Template

```
I need to confirm a few details to begin the analysis:

1. Analysis Period: [default: last 30 days]
2. Game Type: [RPG/SLG/Casual/MOBA/Other]
3. Current First Purchase Rate: [X%]
4. Comparison Baseline: [Last week/month/year/other]
```

### First Purchase Rate Definition Alignment

Different definitions lead to different results:

| Definition | Formula | Use Case |
|------------|---------|----------|
| Standard | First-time payers / new registered users | General monitoring |
| Narrow | First-time payers / paying-intent users | Precise targeting |
| Broad | First-time payers / DAU | Funnel analysis |

Confirm with the user which definition to use, or use the standard definition if not specified.

---

## Phase 2: Data Acquisition

### Step 1: Try Existing Dashboards

```bash
# Search for first purchase related dashboards
ae-cli analysis dashboard list \
  --project-id <project_id> \
  --queries '["<first_purchase_keyword>"]' \
  --format json
```

**If dashboards found**:
```
Found [N] related dashboards:
1. [Dashboard Name 1] - ID: [id]
2. [Dashboard Name 2] - ID: [id]

I will use [Dashboard Name] for data acquisition.
```

**If no dashboards found**:
```
No related dashboards found. Switching to direct event query.
```

### Step 2: Direct Event Query

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --definition '{
    "time_range":{"mode":"custom","start_time":"<start_date>","end_time":"<end_date>"},
    "time_particle_size":"day",
    "metrics":[
      {"event":"<first_purchase_event>","aggregation":"user_count"},
      {"event":"<registration_event>","aggregation":"user_count"}
    ]
  }'
```

### Step 3: Auto-Create Dashboard (Fallback)

```bash
# Step 1: Save the exact definition that already passed adhoc run.
ae-cli analysis report create \
  --project-id <project_id> \
  --report-name "first_purchase_rate_trend" \
  --model-type event \
  --definition '<verified_ai_definition>'

# Step 2: Create dashboard
ae-cli analysis dashboard create \
  --project-id <project_id> \
  --dashboard-name "First Purchase Rate Monitoring" \
  --initial-report-id <report_id_from_create_response>
```

---

## Data Verification Checklist

After data acquisition, verify:

- [ ] Data is within expected range (0-100% for rates)
- [ ] No missing dates in the time series
- [ ] New users > First purchase users (sanity check)
- [ ] Time trend is consistent with user description

---

## Phase Completion Checkpoint

At the end of Phase 2, present the user with:

```
### Data Acquisition Complete

| Metric | Value |
|--------|-------|
| Analysis Period | [start] to [end] |
| New Users | [N] |
| First-Time Payers | [N] |
| **First Purchase Rate** | **[X.X%]** |
| Comparison Baseline | [X.X%] (last week/month) |
| Trend | [↑/↓/→] [X.X]% |

Phase 1-2 data acquisition complete. Continue with deep root cause analysis?
- Continue: Deep dive into root causes and influencing factors
- Add context: Please provide more background information
- Focus: Conduct specialized analysis on specific dimensions (e.g., user segmentation, funnel analysis)
```
