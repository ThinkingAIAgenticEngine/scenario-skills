# Short-drama Creative Placement Performance Evaluation Report

> Project: <name/PID> | Scope: <channel/creative/date> | Business model: <IAP/subscription/IAA/hybrid>
> Data feasibility: <A/B/C/D> | Attribution caliber: <caliber> | Maturity window: <D0/D1/D3/D7/L30>
> Analysis date: <yyyy-MM-dd> | cohort: <activation start-end> | behavior observed through: <yyyy-MM-dd>

## 1. Conclusion Overview
- <3-5 standalone conclusions; clearly answer: is it worth scaling up, where the main bottleneck is, what to do first>

## 2. Data Scope and Caliber
- Activation: <event name + cohort range + maturity note>
- Creative/channel/campaign: <field name>
- Registration: <event + success-status field (tested value)>
- Payment (IAP): <event + success filter + amount field>
- Ad revenue (IAA): <billing event (single) + revenue field>
- Retention: <event>; viewing: <event + duration/episode-count field>
- ROAS: <computable caliber / unavailable and why>
- Sample threshold: <creative-level / cell-level>; under-observation data: <immature cohort range>

> This analysis is limited by [missing data/fields]. We can currently complete [analyzable scope], and cannot reliably answer [non-analyzable questions]. It is recommended to supplement [specific data] before upgrading the conclusion.

## 3. Core Metric Scorecard

| Creative/Tag | Spend | Impressions | CTR | Activations | CPI | D0 Registration Rate | Payment Rate (D7) | D7 ROAS | D7 LTV | D1/D3/D7 Retention | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| <one creative per row; fill "not connected/unavailable" for unobtainable columns; status = under observation / decidable / declined> |

## 4. Three-stage Funnel Diagnosis
### 4.1 Attraction Efficiency
<CTR/play depth/frequency; Level B data must be labeled "not evaluable" with proxy-metric limitations explained>
### 4.2 Acquisition Efficiency
<click -> activation -> registration; post-registration catch-up; abnormal traffic investigation>
### 4.3 Value Efficiency
<viewing depth/payment/retention/LTV; payment structure breakdown; product conversion judgment>

## 5. Tag, Channel, and Audience Findings
- <keep only replicable patterns with samples, controls; cells <100 labeled "directional signal">

## 6. Creative Lifecycle and Fatigue
- <compare aligned by days-since-launch, do not mix different lifecycles; if data start point != launch date, explain>

## 7. Root-cause Judgment
| Phenomenon | Inference | Evidence | Evidence Strength | Confounders / Items to Verify |
|---|---|---|---|---|
| <...> | <...> | <...> | high/medium/low | <...> |

## 8. Action Recommendations
| Priority | Action | Suggested Owner | Verification Metric | Observation Window |
|---|---|---|---|---|
| P0 | <immediate stop-loss / fix data pipeline> | placement/data/product | <...> | <...> |
| P1 | <verify this week> | creative/placement/product | <...> | <...> |
| P2 | <continue observing or system building> | <...> | <...> | <...> |

## Appendix: Data Quality and Caliber Notes
- <issues found during this retrieval: dirty values, multi-event revenue mounting, failed-order amounts, metadata lag, etc.>
- <DEMO/demo projects must declare: conclusions are only for validating analysis methods and processes, and do not constitute real placement advice>
