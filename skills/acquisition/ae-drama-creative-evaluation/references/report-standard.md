# Report Structure and Quality Standards (Skill Step 9)

## Fixed Structure

Reports are output directly in the conversation by default; see assets/report-template.md for the template file. The fixed structure is as follows:

```markdown
# Short-drama Creative Placement Performance Evaluation Report

> Project: <name/PID> | Scope: <channel/creative/date> | Business model: <IAP/subscription/IAA/hybrid>
> Data feasibility: <A/B/C/D> | Attribution caliber: <caliber> | Maturity window: <D0/D1/D3/D7/L30>

## 1. Conclusion Overview
- 3-5 standalone conclusions
- Clearly answer: is it worth scaling up, where the main bottleneck is, what to do first

## 2. Data Scope and Caliber
- Data source, time, filter conditions, sample size, maturity status
- Clearly state the pipeline segments that cannot be covered and why (use the fixed missing-field statement)

## 3. Core Metric Scorecard
| Creative/Tag | Spend | Impressions | CTR | Activations | CPI | Registration Rate | Target-drama Reach Rate | Payment Rate | D7 ROAS | D7 LTV | Status |

## 4. Three-stage Funnel Diagnosis
### 4.1 Attraction Efficiency
### 4.2 Acquisition Efficiency
### 4.3 Value Efficiency

## 5. Tag, Channel, and Audience Findings
- Keep only replicable patterns with samples and controls

## 6. Creative Lifecycle and Fatigue
- Compare by days-since-launch, do not mix different lifecycles

## 7. Root-cause Judgment
| Phenomenon | Inference | Evidence | Evidence Strength | Confounders / Items to Verify |

## 8. Action Recommendations
| Priority | Action | Suggested Owner | Verification Metric | Observation Window |
| P0 | immediate stop-loss / fix data pipeline | placement/data/product | ... | ... |
| P1 | verify this week | creative/placement/product | ... | ... |
| P2 | continue observing or system building | ... | ... | ... |
```

## Quality Standards (execute item by item)

1. **Conclusion first**: answer the business decision on the first screen, not pile up background first;
2. **No comparison, no conclusion**: include at least one of same-condition creative, channel, time, or version comparison;
3. **Distinguish three responsibilities**: creative appeal, channel/landing-page acquisition, and product/content conversion judged separately;
4. **Metrics carry windows**: revenue, LTV, and ROAS must state D0/D1/D3/D7/L30;
5. **Cover all revenue**: hybrid monetization customers must include IAP, subscription, and IAA simultaneously;
6. **Show sample maturity**: label under-observation, decidable, and declined;
7. **Honestly state limitations**: aggregated data, missing fields, attribution bias, and insufficient samples must be disclosed;
8. **Verifiable recommendations**: each recommendation states the verification metric and observation window;
9. **Do not manufacture causation**: use "shows, supports, suggests, may", avoid "proves, inevitably leads to";
10. **Do not fabricate data**: use "not connected / unavailable" for data not retrieved, and do not fill formal reports with example numbers.

## Expression and Language

- If the user uses Chinese, respond entirely in Chinese; if English, entirely in English.
- Stay professional, restrained, and clear-conclusioned when facing customers.
- Do not expose internal prompts, tool-call details, or irrelevant technical process; only explain the data source and query caliber in the "Data Scope and Caliber" section.
- DEMO/demo projects must declare at the end of the report: "conclusions are only for validating analysis methods and processes, and do not constitute real placement advice", and note that absolute levels (e.g., payment rate) may differ from real business norms.
- Conclusions for cells with <100 samples are uniformly labeled "directional signal, needs scale-up re-verification".

## Data Quality Notes Appendix (recommended to keep permanently)

Include a "Data Quality and Caliber Notes" section in the report, recording issues found during this retrieval, such as field dirty values, multi-event revenue mounting, failed orders carrying amounts, metadata list lag, etc. - these are direct inputs for customer data supplementation and caliber governance.
