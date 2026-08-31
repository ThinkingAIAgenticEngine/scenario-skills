# Step 04: Attribution

## Objective

For anomaly signals with confidence "medium" or above, trace root causes along the causal chain and reconstruct the complete chain from root cause to business impact.

## Input

- `/tmp/game-economy-inspection/anomalies.json` — anomaly signal list
- [../attribution_chains.md](../attribution_chains.md) — attribution chain templates

## Output

- `/tmp/game-economy-inspection/attribution.json` — attribution analysis results

---

## Execution Steps

### 4.1 Match attribution chains

Read `../attribution_chains.md`, match attribution chain templates by the anomaly signal's metric combination:
- HHI↑ (§1) + consumption concentration↑ (§5) → Chain 1 (numeric tuning → meta imbalance → economy narrowing → payment deterioration)
- Nurtured heroes↓ (§6) + earn/consume ratio↑ (§4) → Chain 2 (content pacing imbalance → outlet depletion → currency devaluation)
- Recycle-before-use ratio↑ (§11) + holding fluctuation (§7) → Chain 3 (recycle anomaly → economy loop rupture)

If the signal matches no preset chain → do not block, annotate "new attribution pattern", analyze yourself following the three-stage structure (root cause → transmission → impact).

### 4.2 Layer-by-layer verification

Verify each layer per the chain template's "investigation steps":

1. **Root cause layer**: confirm the triggering event (version update time point, numeric change records). Can use time-inflection analysis — compare slope before/after the change
2. **Transmission layer**: verify the propagation relationship between domains. Run time-offset analysis on related metrics to confirm order
3. **Impact layer**: quantify the final impact on retention and payment

Investigation operations (choose as needed; see adapter layer for tool invocation):
- Time-inflection verification: pull trends before/after the change point for key metrics, compare slopes
- Propagation verification: time-offset analysis of related metrics
- Impact quantification: funnel/retention comparison
- User drilldown: drill down into the anomalous user cohort to observe behavior characteristics

### 4.3 Output attribution results

Write attribution results to `/tmp/game-economy-inspection/attribution.json`:

```json
{
  "chains": [
    {
      "signal": "pvp_hhi",
      "chain_name": "Numeric tuning → Meta imbalance → Economy narrowing → Payment deterioration",
      "root_cause": "Warrior-A damage multiplier raised 15%, two new heroes positioned as warriors in the same period",
      "layers": [
        {"layer": "Combat", "evidence": "HHI 0.18→0.33, warrior appearance 35%→51%"},
        {"layer": "Economy", "evidence": "Top 5 consumption share 41%→62%"},
        {"layer": "Backpack", "evidence": "Cold fragment holding +34% in 4 weeks"},
        {"layer": "Monetization", "evidence": "Nurturing bundle conversion declining"}
      ]
    }
  ]
}
```

---

## Acceptance Criteria

- [ ] Attribution chain matched (or annotated as a new attribution pattern)
- [ ] Layer-by-layer verification done: root cause + transmission + impact
- [ ] `attribution.json` written with root cause and layered evidence

---

## Status Output

- `STEP_SUCCESS` — attribution chain reconstruction complete
- `STEP_ERROR` — some signals failed attribution (annotate "attribution incomplete" in report)
