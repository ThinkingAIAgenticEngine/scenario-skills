# Output Spec Self-Check List (Universal Edition)

Check item by item after generating the report. HARD RULES + AMA + delegation rules live in `governance.md`; judgment thresholds and confidence tiers in `judgment-parameters.md`.

## Output Spec: Do / Don't

❌ Don't (forbidden) — first/last comparison only:
| Dimension | W1 rate | W2 rate | Change |
|------|------|------|------|
| Android | 20.37% | 19.34% | -1.03pp |

✅ Do (required) — full daily data + pattern description:
| Dimension | 08-06 | 08-07 | 08-08 | 08-09 | 08-10 | 08-11 | 08-12 | 08-13 | 08-14 | 08-15 | 08-16 | 08-17 | 08-18 |
|------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| Android | 20.43% | 18.95% | 21.31% | 20.84% | 20.63% | 20.21% | 19.17% | 19.12% | 19.37% | 18.98% | 19.42% | 19.49% | 19.87% |

> **Fluctuation pattern**: 8/11→8/12 single-day drop -1.04pp, fell 4 consecutive days to bottom 18.98% on 8/15, V-shaped rebound from 8/16 but not recovered to W1 level.

## Self-Check List

- [ ] Product config filled and persisted (Part 0)
- [ ] Aggregate trend table has N date columns (not just first/last 2)
- [ ] Each dimension breakdown table has N date columns
- [ ] **Every queried detail table fully output**: aggregate trend, each dimension's numerator UV/denominator DAU/penetration, each cross drill-down combination — all daily columns, no "queried but omitted into summary"
- [ ] Each dimension has "fluctuation pattern" text description (single-day jump / consecutive rise-fall / V-shape / inverted-U)
- [ ] **Part 3 full dimension breakdown all queried**: check SKILL.md execution checklist row by row
- [ ] Cross drill-down tables have N date columns
- [ ] All "change" columns computed from full N-day data, not first/last only
- [ ] Report notes timezone caliber (default UTC+8); if analyzing a specific region, mark it
- [ ] Current-day data excluded or marked as partial
- [ ] Part 4 has a record of user confirmation before drilling (AskUserQuestion call or plain-text question record)
- [ ] Conclusion has five elements (inflection/root cause/confirmed caliber/action recommendations/remaining to-do); multi-round progression obeys "incremental by default, override requires authorization"
- [ ] Drill-down recursed to the bottom: dimensions with trend continued drilling by "remaining splittable dimensions" (did not stop at preset mapping / single drill-down)
- [ ] "Residual-signal check" done: suspect dimension's intra-group rate re-verified by the next un-split dimension, confirming no "opposite direction / far-exceeding-magnitude" subgroup
- [ ] Anomaly judgment "uniform": every dimension judged by trend-inflection dual threshold, anomaly-dimension list produced, did not skip drilling because "aggregate flat"
- [ ] When first round has no anomaly, asked the user "whether to proactively cross-drill by some dimension" rather than closing directly with "no fluctuation"
- [ ] Supply-side / environment-layer root cause hit the "high-frequency root-cause library" evidence combination (none missing), no guessing
- [ ] Anomaly dimension's intra-group rate judgment carries **sample-size confidence** label (Low/Very Low groups marked "pending verification", not used as root cause)
- [ ] Root-cause conclusion carries **confidence-level** label (High/Medium/Low), not treating borderline hits as ironclad
- [ ] Conclusion ends with the fixed format proactively guiding next step (deep-dive / incremental / comparison / end)
