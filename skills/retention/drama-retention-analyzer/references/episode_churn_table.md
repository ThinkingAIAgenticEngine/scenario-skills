# Per-Episode Churn Table Template + Health Label Definitions

> This file is the **single definition source of churn table format and health labels**. Other files reference this; definitions are not duplicated.

---

## Standard Churn Episode Table

```markdown
## Key Churn Episodes

| Rank | Episode | Churn Rate | Churn Contribution | Completion Rate | Severity | Attribution Summary | Attribution Layer |
|------|---------|-----------|---------------------|-----------------|----------|---------------------|-------------------|
| 1 | E{N} | {dropout_rate}% | {contribution}% | {completion}% | 🔴 P0 | {one-line attribution} | Layer {X}-{name} |
| 2 | E{N} | {dropout_rate}% | {contribution}% | {completion}% | 🟠 P1 | {one-line attribution} | Layer {X}-{name} |
| 3 | E{N} | {dropout_rate}% | {contribution}% | {completion}% | 🟡 P2 | {one-line attribution} | Layer {X}-{name} |
```

### Severity Badges

- 🔴 P0 — Immediate action (churn rate >30% OR churn contribution >15%)
- 🟠 P1 — Fix this week (churn rate >20% OR churn contribution >10%)
- 🟡 P2 — Monitor this month (churn rate >15% OR churn contribution >5%)
- 🟢 Normal — Monitor

### Paywall Episode Special Marker

Paywall episodes get a 🔒 marker and cross-layer label: `| E29 🔒 | 52.3% | 27.3% | 65% | 🔴 P0 | Paywall blocking | Layer 3+4-cross-layer |`

### Attribution Layer Labels

Layer 1-Traffic / Layer 2-Opening / Layer 3-Plot / Layer 4-Commercialization / Layer 5-Long-term / Layer 3+4-cross-layer / Layer 2+4-cross-layer / Dim A-Segment / Dim B-Time / Dim C-Social / Dim D-Genre / Dim E-ROI

### Confidence Interval (when n < 1000)

`| E{N} | {rate}% (95% CI: {low}-{high}%) | ... |`

### Per-Episode Retention Detail (Phase 2 Drill-Down)

```markdown
| Episode | Retention Rate | Churn Rate | Churn Contribution | Completion Rate | Skip Rate | Narrative Tag | Attribution Layer | Severity |
|---------|---------------|-----------|---------------------|-----------------|-----------|---------------|-------------------|----------|
| E1 | 100% | — | — | {comp}% | {skip}% | Opening conflict | Layer 2-Opening | — |
| E29 | {ret}% | {drop}% | {cont}% | {comp}% | {skip}% | Paywall🔒 | Layer 3+4 | 🔴 |
| Finale | {ret}% | {drop}% | {cont}% | {comp}% | {skip}% | Finale | Layer 3+5 | {sev} |
```

Narrative tag options: Opening / Hook / Paywall🔒 / Paid continuation / Turning point / Genre shift / Finale

---

## Drama Health Labels (Single Definition Source)

| Health Label | Judgment Criteria | Characteristics | Strategy Recommendation |
|--------------|-------------------|-----------------|----------------------|
| **Top hit** | High paywall reach + high completion + high completion retention | Excellent full-funnel performance, high long-term value | Reuse template, scale production |
| **Short-term cash-cow** | High paywall reach + high completion + low completion retention | Quick monetization but lacks long-term stickiness | Optimize cross-drama transition, improve revisit |
| **Opening failure** | Low paywall reach + severe first-3-episode dropout | Opening hook failed, users cannot enter | Re-edit first 3 episodes, optimize material matching |
| **Post-paywall attrition** | High paywall reach + heavy post-paywall abandonment | Good pre-paywall performance, collapses post-paywall | Optimize post-paywall content quality |
| **⚠️ Insufficient data** | Sample below threshold (see exemption rule below) | Metrics statistically unreliable; no diagnosis possible | Expand time range / accumulate sample, re-run later |

### Insufficient-Data Exemption Rule (Mandatory Pre-Check)

Before assigning ANY of the 4 diagnostic labels above, check sample size:

- **play_start UV < 100** (analysis period), OR
- **any key episode's UV < 30** (episodes feeding the label criteria, e.g., E1–E3 for Opening failure)

→ **Force-assign `⚠️ Insufficient data`** and do NOT fire the 4 diagnostic labels, regardless of how closely the metrics match a label's criteria. With UV=49, one user = 2 percentage points — metric-based label matching is coincidence, not signal. Report aggregate metrics with the ⚠️ low-sample label instead, and recommend expanding the time range.

Exemption: if the user explicitly requests a directional read despite low sample, the closest label MAY be mentioned but MUST be written as "⚠️ 非可诊断 (directional only): closest to {label}, confidence insufficient".

Judgment standards:
- High paywall reach: Paywall reach rate ≥40% (short drama)
- High completion: Full-drama completion rate ≥ industry benchmark (see `optimization-playbook.md`)
- High completion retention: Completer D7 retention ≥30%
- Low paywall reach: Paywall reach rate <20%
- Severe first-3-episode dropout: Opening segment dropout rate >40%
- Heavy post-paywall abandonment: Post-paywall segment dropout rate >35%
