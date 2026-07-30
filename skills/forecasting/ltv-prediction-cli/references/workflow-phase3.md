# LTV Prediction - Workflow Phase 3: Computation & Output (CLI Edition)

## Language Policy

All content in English. Exception: user explicitly requests Chinese.

---

## Phase 3: Computation & Prediction

### B2: Cohort LTV Curve Fitting

**Model**: Shifted exponential decay

```
LTV(n) = LTV_base + (LTV_inf - LTV_base) × (1 - e^(-k×n))
```

**Parameters**:
- `LTV_base`: Baseline LTV (captures D0 value, e.g. first-pay conversion)
- `LTV_inf`: Asymptotic maximum LTV (the steady-state ceiling)
- `k`: Decay rate (how fast LTV approaches ceiling)

**Why shifted model**: Simple model `LTV_inf*(1-e^(-kn))` assumes LTV(0)=0, but real D0 LTV is often nonzero. The shifted model represents that baseline explicitly; judge fit quality from the returned R² and MAE rather than assuming an improvement.

#### Computation Steps

1. **Prepare data**: Extract cohort LTV values at day markers from Phase 2 data.

2. **Run the packaged fitter**:

   ```bash
   "$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/fit_ltv.py" \
     --points '[[0,1.2],[1,1.8],[3,2.4],[7,3.1],[14,3.8],[30,4.5]]'
   ```

   Replace every value with observations from Phase 2. The script validates
   inputs and returns parameters, covariance, R², MAE, predictions, half-life,
   and the 90% steady-state day.

#### Output Structure

```json
{
  "model": "shifted_exponential",
  "parameters": {
    "ltv_base": "<value>",
    "ltv_inf": "<value>",
    "decay": "<value>"
  },
  "quality": {
    "r_squared": "<value>",
    "mae": "<value>",
    "point_count": "<value>"
  },
  "predictions": {
    "D60": "<value>",
    "D90": "<value>",
    "D180": "<value>",
    "D365": "<value>"
  },
  "half_life_days": "<value>",
  "steady_state_90pct_days": "<value>",
  "covariance": {
    "parameter_order": ["ltv_base", "ltv_gain", "decay"],
    "matrix": []
  }
}
```

---

### B3: Stratified LTV Computation

**Goal**: Compute per-segment LTV across RFM, pay-tier, and VIP dimensions.

#### Computation Steps

1. **RFM segments**: For each RFM tag value, compute:
   - `avg_ltv` = total_revenue / user_count
   - `revenue_share_pct` = segment_revenue / total_revenue × 100

2. **VIP levels**: Group by VIP level property, compute same metrics.

3. **Pay tiers**: If a cumulative-payment property is compiler-resolved or explicitly confirmed, classify users from its observed percentiles:
   - Determine thresholds from data distribution
   - Compute per-tier LTV metrics

4. **Aggregate results**: Build segment comparison table.

#### Pay-Tier Auto-Classification

When no predefined pay-tier tag exists, use only a confirmed cumulative-payment
property. The names and numeric ranges below are presentation examples, not
defaults to send to ae-cli:

| Tier | Condition | Typical Range |
|------|-----------|---------------|
| Non-payer | confirmed property = 0 | observed zero |
| Micro payer | 0 < confirmed property <= P25 | observed range |
| Small payer | P25 < confirmed property <= P50 | observed range |
| Medium payer | P50 < confirmed property <= P75 | observed range |
| Large payer | P75 < confirmed property <= P95 | observed range |
| Whale | confirmed property > P95 | observed range |

P25/P50/P75/P95 = 25th/50th/75th/95th percentile of payer distribution.
If the required property is unavailable, omit pay-tier output and report the
data gap.

#### Output Structure

```json
{
  "segments": [
    {
      "segment_name": "<name>",
      "segment_type": "RFM|pay_tier|VIP",
      "user_count": "<count>",
      "avg_ltv": "<value>",
      "total_revenue": "<value>",
      "revenue_share_pct": "<value>"
    }
  ],
  "segmentation_dimensions": ["RFM", "pay_tier", "VIP"],
  "data_period": "recent_90_days"
}
```

---

## Recommendations Template

Based on B2 and B3 results, generate actionable recommendations:

### From B2 (Cohort LTV Curve)

1. **Acquisition budget**: Compare `ltv_inf` with the user's confirmed target LTV:CAC ratio; do not impose a universal ratio.
2. **Paywall optimization**: If `ltv_base` is low relative to `ltv_inf`, investigate early pay conversion.
3. **Retention focus**: If `decay` is high (fast saturation), investigate whether extending retention can capture more long-term value.
4. **Prediction confidence**: If `quality.r_squared` is below the agreed quality threshold, recommend a longer cohort window or more data points.

### From B3 (Stratified LTV)

1. **Whale identification**: Quantify the observed top-segment revenue share before recommending VIP retention.
2. **Conversion funnel**: Identify the largest observed conversion opportunity rather than assuming it is the micro-to-small tier.
3. **Segment-specific ROI**: Allocate CAC budget proportional to segment LTV.
4. **Risk alert**: If whale segment LTV drops, investigate immediately (revenue concentration risk).

### Combined Recommendations

```json
{
  "recommendations": [
    {
      "action": "Set CPI ceiling from ltv_inf and the confirmed target LTV:CAC ratio",
      "priority": "high",
      "expected_impact": "Ensure profitable acquisition",
      "source": "B2"
    },
    {
      "action": "Launch micro-to-small payer conversion campaign",
      "priority": "high",
      "expected_impact": "Unlock largest payer pool",
      "source": "B3"
    },
    {
      "action": "Implement VIP retention program for whale segment",
      "priority": "medium",
      "expected_impact": "Protect the observed high-value revenue concentration",
      "source": "B3"
    },
    {
      "action": "Optimize first-pay flow to increase ltv_base",
      "priority": "medium",
      "expected_impact": "Higher early conversion raises total LTV trajectory",
      "source": "B2"
    }
  ]
}
```
