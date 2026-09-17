# Metrics and Drill-down Dimensions Standard

The complete recommendation table for Step 5 (confirm metrics and dimensions). Generate the suggested list from here based on the primary goal identified in Step 1.

## Metric Recommendation Table

| Goal | Recommended core metrics |
|------|------------|
| A. New feature acceptance | New feature penetration rate, usage frequency, post-usage retention difference, entry funnel |
| B. Retention optimization | New user funnel conversion rate, churn point distribution, retention curve (cohort aligned) |
| C. Monetization | Payment rate, ARPPU, ARPU, first purchase conversion rate, payment depth distribution |
| D. Performance | Crash rate, ANR rate, launch duration, level load duration |
| E. Balance | Level pass rate, bottleneck churn rate, resource output/consumption ratio, PVP win rate |
| F. Overall health | DAU, WAU, new users, per-user duration, D1/D3/D7 retention |

## Universal Base (check for any goal)

- **Activity**: DAU, WAU, new users, returning-user count
- **Duration**: per-user online duration, per-user launch count
- **Retention**: D1, D3, D7

## Add by Goal (detailed)

**A. New feature acceptance**
- New feature penetration rate (reached users / updated users)
- New feature usage frequency (per-user usage count)
- Post-usage retention difference (users who used it vs not, D1/D7 comparison)
- Entry funnel (see entry → click → complete first experience)

**B. Retention optimization**
- New user funnel conversion rate at each step
- Churn point distribution (which level/step churns the most)
- Retention curve (cohort aligned by registration day, **do not look at blended retention**)

**C. Monetization**
- Payment rate, ARPPU, ARPU
- First purchase conversion rate, time to first purchase
- Payment depth distribution (low/mid/high tier share change)
- ⚠️ Payment rate up + ARPPU down = possibly squeezing high-value payment

**D. Performance**
- Crash rate, ANR rate (if tracked)
- Launch duration, level load duration
- Lag-related behavior metrics (duration/retention change on low/mid-end devices)

**E. Balance**
- Level pass rate, bottleneck churn rate
- Resource output/consumption ratio
- Matchmaking duration, match duration distribution
- PVP win rate distribution (if applicable)

**F. Overall health**
- All universal base metrics
- DAU breakdown by channel dimension
- User-tier activity (new / returning / resurrected)

## Dimension Recommendation Table

| Dimension | Drill-down purpose | Applicable goals |
|------|---------|---------|
| Channel (mandatory by default) | Exclude channel-mix change interference; locate whether a specific channel alone drops/rises | All goals |
| User tier (new / returning / resurrected) | Determine which user type the version affects | A, B, C, F |
| Region / country | Locate regional issues (especially overseas releases) | A, C, D, F |
| Device model / OS | Must-check for performance versions; whether low/mid-end devices improved | D, F |
| Version-number breakdown | With version tracking, look at differences across minor versions | All goals when version tracking exists |

## Notes on Generating Suggestions

- Select **3-5** metrics, do not pile everything on
- Select **1-3** dimensions, avoid over-fragmented samples after multi-dimension cross (conclusion is unreliable when a single cell has <100 users)
- **Channel dimension is mandatory by default**, unless the user explicitly says "do not look at channel"

## Interactive Confirmation Discipline

After generating the suggested list, **you MUST ask the user to confirm**; do not execute directly. Example confirmation wording:

> Based on the "XX goal" you selected, I suggest analyzing the following metrics and dimensions:
> **Metrics**: 1. XXX 2. XXX 3. XXX
> **Drill-down dimensions**: 1. XXX 2. XXX
> Do you need any adjustments or additions?

User feedback handling:
| Feedback | Handling |
|------|------|
| "OK, that works" | Confirm the list, proceed to query |
| "I want to see XX metric" | Add to core metrics, replace or supplement |
| "Break down by XX dimension" | Add to drill-down dimensions |
| "This metric/dimension does not exist" | Re-check the Step 3 probe results to confirm whether the field exists; if not, tell "the current project has no such field; suggest using YY instead" |
| "Go with your suggestion" | Use the suggested list; note in the report that "metrics/dimensions are recommended values" |
