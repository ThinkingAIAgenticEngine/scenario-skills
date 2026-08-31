# Inspection Methodology

> This document defines the core methodology of game-economy-inspection — slow-variable judgment, cross-domain correlation rules, and confidence assessment. Not bound to any tool.

---

## I. Core Concept: Fast Variables vs Slow Variables

### Fast variables (captured by traditional BI)
- Characteristic: large single-week fluctuation (±5% ~ ±20%), triggers traditional threshold alerts
- Example: DAU day-over-day plunge of 15%, a hero's win rate jumping 5% in one week
- Traditional approach: dashboard thresholds, manual investigation after trigger
- Limitation: fast variables are already the "result", not the "signal"

### Slow variables (most easily missed by traditional BI)
- Characteristic: tiny single-week fluctuation (±0.3% ~ ±1%), trend only surfaces after 30 days of accumulation
- Example: HHI up 0.02/week, fragment holding up 2%/week, consumption concentration up 1%/week
- Traditional approach: none — single-week values are always normal, no alert fires
- **This skill's value**: not looking at a single week, but at "which direction 30 days are heading"

### Judgment rule

```
Slow-variable anomaly = (30-day trend slope > threshold) AND (single-week values within historical normal range)
```

That is: any single week looks normal, but the connected trend line is rising (or falling), and the direction is opposite to business-health direction.

Default threshold values are in `config/project_mapping.md`'s threshold configuration section, adjustable per game characteristics.

---

## II. Cross-Domain Correlation Rules

### Why cross-domain is required

Single-domain total metrics are "deceptive" — an earn/consume ratio of 1.05 looks normal, but if consumption concentrates on 3 heroes, the outlet is actually narrowing. Only by putting multiple domains together can you see "normal totals but deteriorating structure".

### Cross-domain validation matrix

When one domain detects a slow-variable anomaly, check whether related domains have echo signals:

| Anomaly domain | Signal direction | Related domain | Expected echo signal |
|----------------|------------------|----------------|----------------------|
| Combat HHI↑ | Lineup concentration | Economy | Consumption distribution should narrow (Top N share↑, §5) |
| Combat HHI↑ | Lineup concentration | Backpack | Cold materials should accumulate (holding↑, §8) |
| Combat HHI↑ | Lineup concentration | Monetization | Nurturing bundle conversion should drop (§9) |
| Economy consumption narrowing | Consumption outlet narrowing | Backpack | Currency holding should rise (§7) |
| Economy consumption narrowing | Consumption outlet narrowing | Monetization | Nurturing revenue share should worsen (§10) |
| Backpack accumulation↑ | Material piling | Monetization | Nurturing payment perception should worsen (§9/§10) |
| Equipment recycle-before-use ratio↑ | Equipment discarded before creating gameplay value | Backpack / Economy | Recycled-material holding or earn/consume ratio should move abnormally (§7/§4) |

### Confidence assessment

| Cross-validation result | Confidence | Meaning |
|-------------------------|------------|---------|
| All related domains echo in the same direction | **High** | Problem has fermented systemically, start attribution immediately |
| ≥50% related domains echo | **Medium** | Problem in incubation, best intervention window |
| Only primary domain has signal (isolated) | **Low** | Likely data noise or localized issue |

---

## III. Inspection Cadence

### Routine inspection (recommended weekly)
1. Pull 30-day trend lines (per domain per metric)
2. Calculate 30-day slope per metric
3. Cross-domain validation
4. No anomaly → record baseline, pass silently
5. Confidence "Medium" or above → enter attribution

### Event-driven inspection (after version update / event launch)
- Anchor on the event date, compare 4 weeks before vs 4 weeks after
- Focus on whether the event changed the slow-variable direction (slope inflection)

### Output standard

Each inspection produces one of three conclusions:

| Conclusion | Definition | Action |
|------------|------------|--------|
| **Normal** | All metrics within safe zone | No action |
| **Attention** | Confidence "Medium" | Recommend scheduling investigation within N weeks |
| **Warning** | Confidence "High" | Start attribution immediately + prepare evidence for remediation handoff |
