# Step 05: Generate Report

## Objective

Assemble the structured inspection report per the template, output it in-conversation, and optionally persist this Skill's defined inspection queries or slow-variable alerts.

## Input

- `/tmp/game-economy-inspection/scenario.json` — scenario config
- `/tmp/game-economy-inspection/anomalies.json` — anomaly signals
- `/tmp/game-economy-inspection/attribution.json` — attribution results
- [../templates/report_template.md](../templates/report_template.md) — report template

## Output

- In-conversation inspection report (Markdown)
- Optional: AE report / alert configuration

---

## Execution Steps

### 5.1 Assemble report

Read `../templates/report_template.md`, fill the four-section structure:

1. **Inspection overview**: per-domain metric status summary table + overall verdict (normal/attention/warning)
2. **Anomaly signal details**: one card per signal — 30-day trend, threshold judgment, cross-domain echo validation
3. **Attribution chains**: causal chain from root cause to impact, layer-by-layer analysis
4. **Recommended follow-up**: urgency judgment + evidence gaps + investigation priorities + handoff point

Recommendations MUST remain diagnostic and non-prescriptive. Do not calculate adjustment quantities, propose intervention parameters, design rollback plans, investigate suspicious users, or design a general economy dashboard. If any of those are requested, pass the verified metric evidence and attribution chain to `game-economy-balance`.

### 5.2 Output report in-conversation

Output the complete Markdown report body directly; writing to a file is not required.

### 5.3 User-side verification

After outputting the report, run the verification flow in `SKILL.md` → Verification:

1. Ask the user to spot-check 2-3 key metric values against their own dashboards
2. Ask the user to confirm the anomaly judgment direction for each warning/attention signal
3. Ask the user to confirm whether the traced root cause aligns with known version/operations events

If any check fails, return to the failed step and re-run before signing off.

### 5.4 Ask for follow-up actions

After verification passes, ask:

```
Inspection report generated and verified. Do you need any of the following:
[1] Persist inspection queries as AE reports — re-run with one click later
[2] Configure automatic alerts only on this Skill's §1-§11 metrics — use the confirmed slow-variable thresholds
[3] Continue with source-point diagnosis or quantified intervention — hand off to game-economy-balance
[4] None — finish
```

- Selected [1] → use the adapter layer's report create to persist core inspection queries
- Selected [2] → use the adapter layer's alert create to create threshold alerts
- Selected [3] → summarize confirmed signals, mappings, time window, and attribution evidence; then route to `game-economy-balance`
- Selected [4] → flow ends

---

## Acceptance Criteria

- [ ] Report assembled per the four-section template, no unfilled placeholder left
- [ ] User-side verification completed (spot-check + anomaly confirmation + attribution confirmation)
- [ ] Follow-up action asked and handled

---

## Status Output

- `STEP_SUCCESS` — report output and verified, flow complete
