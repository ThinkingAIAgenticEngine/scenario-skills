# Game Version Data Comparison Report — <feature name> (boundary day <date>)

> Project: project_id=<PID> (<game type>) | Approach: <time comparison / dual approach> (pre-launch <date-date> vs post-launch <date-date>, N days each)

## 结论速览

<3-5 sentences: primary goal conclusion + whether expectations were met + whether action is needed>

## Core Metric Comparison Table

| Metric | Pre-launch (N days) | Post-launch (N days) | Change |
|------|------|------|------|
| Active users (login distinct) | — | — | — |
| Total logins | — | — | — |
| Online duration (seconds) | — | — | — |
| <target event> users | — | — | — |
| <target event> count | — | — | — |
| New registrations | — | — | — |

> Note: up = red 🔴, down = green 🟢 (A-share color convention).

**Derived metrics:**
- <feature> penetration rate: <target event users> / <active users> = **XX%**
- Per-user <behavior>: <total count> / <users> = **X.XX times/user**

## Key Charts

<Time series for the aligned pre/post windows, with launch day shown as a boundary but excluded from the default comparison>

<Grouped comparison of the most decision-relevant metrics. If no chart renderer is available, provide the same values in a compact Markdown table.>

## Cross-check: target version vs baseline version(s)

<Compare the confirmed version cohorts over the identical post-launch window. Report missing/unknown version values separately. If the project has no usable version field, state that this cross-check is unavailable under Risks / Concerns.>

<Include the following retention sections only when retention or feature adoption is in scope.>

## Overall Retention Baseline (cohort aligned)

| cohort | Registrations | D1 | D3 | D7 |
|--------|------|------|------|------|
| Pre-launch registrations (<date>) | — | —% | —% | —% |
| Post-launch registrations (<date>) | — | —% | —% | —% |

→ <overall retention conclusion>

## Key Finding: retention difference between registration-day <segment variable> vs non-<segment variable>

| Registration-day segment | Users | D1 | D7 |
|------|------|------|------|
| <hit> | — | **XX%** | **XX%** |
| non-<hit> | — | XX% | XX% |
| **Difference** | — | **+XX pp** | **+XX pp** |

→ <conclusion, note selection bias>

## Drill-down Findings (<dimension>)

<1-3 most important segment findings, compared against the overall conclusion>

## Root-cause Diagnosis (with confidence level)

> "Confidence level" refers to the reliability of heuristic inference, not statistical confidence; correlation ≠ causation.

| Observed difference | Inference | Confidence | Note |
|---------|------|------|------|
| <difference 1> | <inference> | high/medium/low | <confounding / selection bias note> |

## Risks / Concerns

1. <data anomaly / approach limitation / confounding factor / point to verify>

## Recommended Actions

| Tier | Action |
|------|------|
| Monitor | <positive/neutral → keep tracking> |
| P2 within this month | <low confidence → A/B test / retention cohort confirmation> |

---

**Data source**: <platform> (project_id=<PID>), ae-cli `analysis.adhoc.run` (event + sql model).
