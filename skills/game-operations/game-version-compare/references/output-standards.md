# Output Standards

Format and content standards for Step 8 (output the report). All reports must comply.

## Color and Currency Conventions (important)

- **Up = red 🔴, down = green 🟢** (A-share convention, opposite of Western convention). Use this color scheme by default unless the user explicitly requests otherwise.
- Amount/currency defaults to **¥ (CNY)**.
- Relative changes must carry a sign (+11.2% / -3.6%) and a red/green marker.

## Report Structure

Keep these seven core sections in this order:

1. **结论速览** (3-5 sentences): primary goal conclusion + whether expectations were met + whether action is needed
2. **Core metric comparison table**: new vs old, absolute values + relative changes (red/green color-coded)
3. **Key charts**: time series + grouped comparison bar chart (use chart)
4. **Drill-down findings**: 1-3 most important segment findings
5. **Root-cause diagnosis**: each key difference → inferred version cause + confidence level (use "confidence level", not "statistical confidence")
6. **Risks / concerns**: data anomalies, approach limitations, confounding factors, points needing further verification
7. **Recommended actions**: tiered (P0/P1/P2/monitor)

Insert applicable supporting sections (for example overall retention, behavior-hit retention, or target-version vs baseline-version cross-checks) after key charts and before drill-down findings. Omit an inapplicable section rather than filling it with invented data, and explain any unavailable required cross-check under risks/concerns.

## Recommendation Tiers

| Tier | Trigger condition | Action |
|------|------|------|
| P0 immediate | The version caused a clear regression (high confidence) | Rollback / hotfix the specific change |
| P1 within this week | Mixed impact, one dimension worsened | Adjust change parameters; keep monitoring |
| P2 within this month | Ambiguous / low confidence | Run A/B test or retention cohort confirmation |
| Monitor | Positive or neutral | Keep; track on the monitoring board |

## Output Principles (four iron rules)

1. **Conclusion first**: the 结论速览 (Summary) must stand alone independently, not depend on later content
2. **Data must be compared**: there must be an old-version or not-updated control; never list only new-version data
3. **Beware false causality**: when a difference is found, proactively check channel-mix change, campaigns, and holiday interference
4. **Honestly mark uncertainty**: insufficient observation period, small sample, missing fields, low confidence level — all must be stated

## Required Report Footer

- **Data source statement**: platform (e.g. ThinkingAI) + project_id + query command (ae-cli `analysis.adhoc.run`, event/sql model)
- Any conclusion involving "correlation but not causation" must carry a disclaimer (correlation ≠ causation)

## Delivery Format

- Return the report inline by default. Create a `.md` artifact only when the user asks for a file or the runtime provides an artifact workflow.
- Use an available chart or visualization capability for the time series and grouped comparison when one exists. Otherwise use a compact Markdown table and state that no chart renderer was available.
- Deliver any created artifact using the runtime's supported file-link or presentation mechanism; do not assume a specific tool name.
