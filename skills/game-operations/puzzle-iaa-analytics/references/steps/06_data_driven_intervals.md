# Step 06: Data-Driven Interval Analysis

## Objective

Probe optimal ad frequency and level completion intervals via retention curve knee points. Identify core user groups.

**Depends on Step 02 baseline.**

## Input / Output

Input: `data_inventory.json`, `core_diagnostics.md`, `segmentation_report.md` (if available)
Output: `{{workspace_dir}}/interval_analysis.md`

> Core principle: Do NOT preset intervals. Fine-grained data probing → natural knee points define boundaries.

### 6.1 Ad Frequency-Retention Curve (§14)

#### 6.1.1 Get Per-User D1 Ad Count

```bash
ae-cli analysis adhoc run \
  --project-id {{project.id}} \
  --model-type event \
  --preview-rows 100 \
  --definition '{
    "time_range":{"mode":"custom","start_time":"{{window.start}}","end_time":"{{window.end}}"},
    "metrics":[{"event":"{{event.ad_impression}}","aggregation":"total_count"}],
    "groups":[{"field":{"name":"#user_id","type":"user_property"}}]
  }'
```

#### 6.1.2 Bucket and Compute Retention

Fine-grained buckets: 0, 1, 2, 3, 4-5, 6-8, 9-12, 13-20, >20.
For each bucket, compute D2/D7 retention via `adhoc run --model-type retention`.

#### 6.1.3 Knee Detection

```bash
python3 ../../scripts/parse_curve.py \
  --input {{workspace_dir}}/ad_freq_retention.json \
  --x-col ad_count --y-col retention_rate \
  --output {{workspace_dir}}/ad_freq_knee.json
```

#### 6.1.4 Overlay Contribution Share

Per-bucket ad impressions / total impressions.

### 6.2 Levels-Retention Curve (§15)

Same flow: get per-user D1 level count → bucket (≤3,4-5,6-10,11-15,16-20,21-30,31-40,>40) → retention per bucket → knee detection.

### 6.3 Stabilized Baseline (§16)

Filter D3-7 active users, compute daily level distribution (P25/P50/P75).

### 6.4 Core User Identification (§17)

Cross-ref 6.1 knee + 6.2 optimal:
- Core: ad ≤ knee ∩ levels in optimal
- Squeeze: ad > knee ∩ D7 < baseline
- Pure content: zero ad ∩ high retention
- Compute IPU contribution per type

### 6.5 Write

```markdown
# Data-Driven Interval Analysis

## Ad Frequency-Retention
| Ad Count | Users | D2 | D7 |
Knee: X times/day. Healthy cap: X.

## Levels-Retention
| Levels | Users | D2 | D7 |
Optimal: XX-XX. Overdraft: >XX.

## Stabilized Baseline
P25/P50/P75: XX/XX/XX

## Core User Identification
| Type | Share | D2 | D7 | IPU Contribution |
```

## Status Output

- `STEP_SUCCESS` — ≥1 dimension complete
- `STEP_ERROR` — Partial
- `STEP_FATAL` — Query failed
