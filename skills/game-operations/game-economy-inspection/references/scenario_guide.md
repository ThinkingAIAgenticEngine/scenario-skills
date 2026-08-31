# Custom Inspection Scenario Configuration Guide

If the scenario you need to inspect is not in the preset templates, follow the steps below to define a new inspection scenario.

## Step 1: Define the scenario

Answer three questions clearly:
1. **What to inspect**: which game economy subsystem do you want to monitor? (e.g. guild contribution economy, limited-time event reward inflation, PVE nurturing efficiency)
2. **Why inspect it**: if this problem occurs but nobody notices, what is the worst outcome?
3. **Time window**: how long is this problem's change cycle? Fast variable (day-level) or slow variable (week-level)?

## Step 2: Decompose into domains

Decompose one inspection scenario into 2-4 data domains, each answering "from which angle do we look at this problem".

Common data domains:
- **Combat domain**: PVP/PVE appearance rate, win rate, lineup diversity
- **Economy domain**: currency flow, consumption distribution, produce/consume balance
- **Backpack domain**: item holding, hoarding rate, usage rate
- **Monetization domain**: bundle conversion, payment structure, ARPPU
- **Social domain**: guild activity, mutual-help response rate, friend-invite conversion
- **Retention domain**: D2/D7/D30 retention, activity tiering

## Step 3: Define metrics for each domain

Pick 2-3 metrics per domain. If `metric_definitions.md` already has matching metrics (§1-§10), reference the IDs directly. Otherwise define new metrics following the six-element template:

```
Metric name (§N):
- Intent: what this metric measures and why to watch it
- Semantics: calculation formula (using {{event.xxx}} / {{prop.xxx}} placeholders)
- Input: which events and properties are needed
- Dimension: day / week / month
- Judgment: what trend/threshold counts as anomaly
- Output: expected output shape
```

Append new metrics to the end of `metric_definitions.md`.

## Step 4: Define cross-domain correlation rules

This is the core — inspection is not just about looking at each metric, but about the echo between metrics.

For each primary signal, list which related-domain metrics **should change in the same direction**. For example:
- Primary signal "guild activity declining" → related signals should include "mutual-help response rate declining", "guild revenue share declining"
- Correlation threshold: at least N related signals appear before triggering an alert

## Step 5: Define attribution chains

Draw the causal chain from root cause to impact. Three-stage structure:
1. **Root cause layer**: what event triggered the change (version update, numeric tuning, operations activity, etc.)
2. **Transmission layer**: how the signal propagates between data domains
3. **Impact layer**: which business metrics are ultimately affected (retention, payment, activity)

Reference the template format in `attribution_chains.md`, and append new chains there.

## Configuration format

After defining, append to `config/scenarios.json` in the following JSON format:

```json
{
  "id": "your_scenario_id",
  "name": "Scenario English Name",
  "description": "One-sentence description of what this scenario inspects and what game types it applies to",
  "domains": {
    "domain_key": {
      "label": "Domain label",
      "metrics": ["§1", "§4", "§9"]
    }
  },
  "cross_domain_rules": [
    {
      "primary_signal": "§1",
      "expected_correlated": ["§4"],
      "min_correlation_for_alert": 1
    }
  ],
  "attribution_chains": ["chain_id"]
}
```
