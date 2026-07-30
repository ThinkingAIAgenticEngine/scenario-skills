# Report Templates — Short Drama Retention (2-Phase Model)

Phase 1 core report + Phase 2 full report. Output language follows user's question language.

---

## Phase 1 Core Report (1 Page, 1-2 Min Read)

```markdown
# Short Drama Retention Overview — {drama_name}

## Basic Info
- Drama type: {drama_type} | Total episodes: {total_episodes}
- Analysis period: {time_range}
- Data source: {ThinkingData / CSV / Manual}

## Core Metric Dashboard

| Metric | Current Value | Industry Benchmark | Rating |
|--------|--------------|-------------------|--------|
| Start-play rate | {start_rate}% | ≥40% | {rating} |
| E1 completion rate | {e1_completion}% | ≥70% | {rating} |
| 3-episode retention | {e3_retention}% | ≥35% pass / ≥50% premium | {rating} |
| Max churn episode | E{N} (churn rate {dropout_rate}%) | — | {severity} |
| Finale retention | {finale_retention}% | ≥12%-18% | {rating} |
| Average episodes watched | {avg_episodes} / {total} | ≥30% of total | {rating} |
| Abandonment rate | {abandon_rate}% | <70% | {rating} |

**Drama Health Label**: {Top hit / Short-term cash-cow / Opening failure / Post-paywall attrition / Insufficient data}
(Definitions in `references/episode_churn_table.md`)

## Retention Curve (Key Milestones)
E1: 100% — E3: {val}% — E10: {val}% — E{pw} (paywall): {val}% — Finale: {val}%

## Max Churn Episodes Top3

| Rank | Episode | Churn Rate | Churn Contribution | Severity | Attribution Summary | Attribution Layer |
|------|---------|-----------|---------------------|----------|---------------------|-------------------|
| 1 | E{N} | {rate}% | {contrib}% | P0 | {attribution} | Layer {X} |
| 2 | E{N} | {rate}% | {contrib}% | P1 | {attribution} | Layer {X} |
| 3 | E{N} | {rate}% | {contrib}% | P2 | {attribution} | Layer {X} |

**One-line conclusion**: {summary}

---

Core analysis complete — Select next drill-down:
1. Churn episode deep-dive → Diagnose churn causes for episode {X}
2. Traffic layer deep-dive → Per-channel retention comparison
3. Payment deep-dive → Payment conversion rate and blocking points
4. Long-term layer deep-dive → 7-day re-view / 30-day revisit / cross-drama conversion
5. Segment deep-dive → New/returning/paid/channel segment retention differences
6. Time dynamics → D1→D7→D30 lifecycle decay
7. Social viral → Share→new viewer→retention funnel
8. Genre comparison → Compare with same-genre benchmark
9. ROI loop → LTV/CAC + full payment funnel
10. Comparison mode → Before/after comparison
11. End → Reply: end
```

> Drill-down options that cannot be executed due to data gaps should be labeled "Data unavailable".

---

## Phase 2 Full Report (5-Layer Per-Layer Diagnosis + Selected Dimension, 3-8 Min Read)

```markdown
# Short Drama Retention Full Diagnosis — {drama_name}

## Analysis Overview
- Drama type: {drama_type} | Total episodes: {total_episodes}
- Analysis period: {time_range} | Paywall model: {paywall_info}
- Lifecycle stage: {Launch / Stable / Decline}
- Drill-down dimension: {user-selected item}
- Data source: {data_source_type}

## Core Metric Dashboard
(Same as Phase 1 — update values if re-queried)

**Health Label**: {label}

---

## Layer 1: Traffic Layer Diagnosis

| Metric | Current Value | Healthy Range | Rating |
|--------|--------------|---------------|--------|
| Impression CTR | {ctr}% | — | {rating} |
| Start-play rate | {start_rate}% | ≥40% | {rating} |
| E1 completion rate | {e1_comp}% | ≥70% | {rating} |
| D1 retention | {d1}% | ≥20% | {rating} |
| Same-day cross-drama viewing rate | {cross}% | ≥15% triggers desensitization | {rating} |
| Non-completer D1 retention | {nc_d1}% | ≥20% | {rating} |
| Per-channel D1 retention difference | {diff} | — | {rating} |

**Traffic Layer Conclusion**: {conclusion}

---

## Layer 2: Opening Layer Diagnosis

| Metric | Current Value | Healthy Threshold | Rating |
|--------|--------------|-------------------|--------|
| E1 completion rate | {e1}% | ≥70% | {rating} |
| E2 completion rate | {e2}% | ≥65% | {rating} |
| 3-episode retention | {e3}% | ≥35%/≥50% | {rating} |
| E1→E2 churn rate | {drop}% | <25% | {rating} |

**Opening Layer Conclusion**: {conclusion}

---

## Layer 3: Plot Layer Diagnosis

### Key Churn Episodes (format: see `references/episode_churn_table.md`)

| Rank | Episode | Churn Rate | Churn Contribution | Completion Rate | Severity | Attribution | Layer |
|------|---------|-----------|---------------------|-----------------|----------|-------------|-------|
| 1 | E{N} | {rate}% | {contrib}% | {comp}% | P0 | {cause} | Layer {X} |
| 2 | E{N} | {rate}% | {contrib}% | {comp}% | P1 | {cause} | Layer {X} |
| 3 | E{N} | {rate}% | {contrib}% | {comp}% | P2 | {cause} | Layer {X} |

### Segment Retention Diagnosis

| Segment | Episode Range | Segment Retention | Segment Dropout | Diagnosis |
|---------|---------------|-------------------|-----------------|-----------|
| Opening | E1-E3 | {ret}% | {drop}% | {diagnosis} |
| Middle | E4 to E{pw-1} | {ret}% | {drop}% | {diagnosis} |
| Paywall | E{pw}±1 | {ret}% | {drop}% | {diagnosis} |
| Post-paywall | E{pw+1} to last 6 | {ret}% | {drop}% | {diagnosis} |
| Finale | Last 5 eps | {ret}% | {drop}% | {diagnosis} |

---

## Layer 4: Commercialization / Product Layer Diagnosis

| Metric | Current Value | Healthy Range | Rating |
|--------|--------------|---------------|--------|
| Paywall position | Episode {pw} | — | {rating} |
| Pay conversion rate | {paid_conv}% | 15-25% | {rating} |
| Free user paywall dropout | {free_drop}% | <50% | {rating} |
| Ad mid-episode exit rate | {ad_exit}% | — | {rating} |
| Crash rate | {crash}% | <5% | {rating} |
| Refund rate | {refund}% | <5% | {rating} |

**Commercialization Layer Conclusion**: {conclusion}

---

## Layer 5: Long-term User Layer Diagnosis

| Metric | Current Value | Industry Benchmark | Rating |
|--------|--------------|-------------------|--------|
| Finale retention | {finale}% | ≥12%-18% | {rating} |
| 7-day re-view rate | {replay}% | ≥5% | {rating} |
| 7-day user re-engagement rate | {reeng_7d}% | ≥15% | {rating} |
| 30-day platform revisit rate | {return}% | ≥8% | {rating} |
| Cross-drama transition rate | {cross}% | ≥5% | {rating} |

**Long-term Layer Conclusion**: {conclusion}

---

## Drill-Down Dimension (Expanded Per User Selection)

### Dim A: User Segment Comparison (option 5)

| Segment | E1 Completion | 3-Ep Retention | Finale Retention | Pay Conversion |
|---------|---------------|-----------------|-----------------|----------------|
| Paid traffic | {val}% | {val}% | {val}% | {val}% |
| Organic | {val}% | {val}% | {val}% | {val}% |
| Social viral | {val}% | {val}% | {val}% | {val}% |

### Dim B: Time Dynamics (option 6)

| Lifecycle Stage | 3-Ep Retention | 7-Ep Retention | Finale Retention |
|----------------|-----------------|-----------------|-----------------|
| Launch (D1-D7) | {val}% | {val}% | {val}% |
| Stable (D7-D30) | {val}% | {val}% | {val}% |
| Decline (D30+) | {val}% | {val}% | {val}% |

Three-Tier Retention Basis:
| Basis | D1 | D7 | D30 | Diagnosis |
|-------|-----|-----|------|-----------|
| Visitor (E1) | {val}% | {val}% | {val}% | {diagnosis} |
| Paywall-reaching | {val}% | {val}% | {val}% | {diagnosis} |
| Full-completion | {val}% | {val}% | {val}% | {diagnosis} |

### Dim C: Social Viral (option 7)
| Metric | Value | Rating |
|--------|-------|--------|
| Share rate | {share}% | {rating} |
| Share→new viewer conversion | {s2n}% | {rating} |
| Social-acquired 3-ep retention | {social_e3}% | {rating} |
| Danmaku density | {danmaku}/ep | {rating} |

### Dim D: Same-Genre Comparison (option 8)
| Metric | This Drama | Same-Genre Top5 Avg | Deviation |
|--------|-----------|---------------------|-----------|
| 3-ep retention | {val}% | {bench}% | {diff}% |
| E1 completion | {val}% | {bench}% | {diff}% |
| Finale retention | {val}% | {bench}% | {diff}% |

### Dim E: ROI (option 9)
| Metric | Value | Industry Reference |
|--------|-------|-------------------|
| Per-drama CAC | ¥{cac} | — |
| Per-drama ARPU | ¥{arpu} | — |
| LTV/CAC ratio | {ratio} | ≥1.5 |
| Payback period | {days} days | ≤30 days |
| Full payment funnel conversion | {funnel}% | — |

---

## Optimization Recommendations (By Layer + Priority)

| Priority | Layer | Issue | Recommendation | Expected Effect |
|----------|-------|-------|----------------|-----------------|
| P0 | {layer} | {issue} | {action} | {expected} |
| P1 | {layer} | {issue} | {action} | {expected} |
| P2 | {layer} | {issue} | {action} | {expected} |

---

**Attribution Disclaimer**: Root cause analysis is based on data pattern inference, not causal inference. Attribution is sorted by layer priority (Layer 1 Traffic first) to avoid misjudging traffic problems as content problems.

**Full diagnosis complete — select another drill-down or reply `end` to finish.**
```

---

## Comparison Mode (Incremental Rules)

When user selects "Comparison mode" (option 10), apply the Phase 2 full report template with these modifications:

1. **Add Version A / Version B columns** to every metric table (2 periods or 2 content versions)
2. **Change column header** from "Current Value" to "Version A | Version B | Change | Rating"
3. **Change arrow legend**: ↑ improvement, ↓ deterioration, → no significant change
4. **Change rating**: >5% improvement = significant; 2-5% = moderate; -2% to +2% = neutral; -2% to -5% = moderate deterioration; >5% deterioration = significant
5. **Add comparison setup table** at top: time range, viewers, paywall strategy, content version, distribution channels for each version
6. **Per-episode churn table**: add Version A Churn / Version B Churn / Change columns
7. **Key change points section**: list episodes with largest improvement/worsening
8. **Sample size note**: if two versions' sample size difference >5x, flag in setup table
