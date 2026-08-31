# Step 03: Anomaly Detection

## Objective

Analyze the 30-day trend lines, detect slow-variable anomalies, and execute cross-domain cross-validation.

## Input

- `/tmp/game-economy-inspection/baseline_{domain}.json` — baseline data per domain
- `/tmp/game-economy-inspection/scenario.json` — scenario config (including cross_domain_rules)
- [../methodology.md](../methodology.md) — judgment rules
- [../metric_definitions.md](../metric_definitions.md) — thresholds of each metric (§N)

## Output

- `/tmp/game-economy-inspection/anomalies.json` — anomaly signal list

---

## Execution Steps

> This step is **pure data analysis**, no tool calls required. Load the judgment rules from `../methodology.md`.

### 3.1 Calculate each metric's slope

For each metric's 30-day data series:
1. Fit a trend line using least-squares linear regression
2. Calculate the slope (per-week change)
3. Compare against the §N Judgment thresholds in `../metric_definitions.md`:
   - Slope within normal range → normal
   - Slope above attention threshold → "attention"
   - Slope above alert threshold → "warning"

### 3.2 Cross-domain cross-validation

For each "attention" or "warning" signal:
1. Find the matching rule from `cross_domain_rules` in `scenario.json`
2. Check whether related-domain metrics are anomalous in the same direction
3. Judge per the confidence rules in `../methodology.md`:
   - All echo → high
   - Partial echo → medium
   - Isolated → low

### 3.3 Output anomaly signals

Write results to `/tmp/game-economy-inspection/anomalies.json`:

```json
{
  "verdict": "attention|warning|normal",
  "signals": [
    {
      "metric_id": "pvp_hhi",
      "domain": "battle",
      "label": "PVP Appearance Rate HHI Index",
      "start_value": 0.18,
      "end_value": 0.33,
      "slope_per_week": 0.0188,
      "threshold_attention": 0.015,
      "threshold_alert": 0.025,
      "level": "attention",
      "cross_domain_validations": [
        {"domain": "economy", "metric": "consume_concentration_top5", "correlated": true},
        {"domain": "backpack", "metric": "cold_hero_fragment_accumulation", "correlated": true}
      ],
      "confidence": "high"
    }
  ]
}
```

### 3.4 Branch

- `verdict = normal` → tell the user the inspection passed, flow ends
- `verdict = attention/warning` → enter Step 04 attribution

---

## Acceptance Criteria

- [ ] Per-metric 30-day slope computed via least-squares regression
- [ ] Cross-domain validation run for every attention/warning signal
- [ ] `anomalies.json` written with a final `verdict` and per-signal confidence

---

## Status Output

- `STEP_SUCCESS` — detection complete, with or without anomalies
- `STEP_EMPTY` — baseline data insufficient for judgment (annotate in report)
