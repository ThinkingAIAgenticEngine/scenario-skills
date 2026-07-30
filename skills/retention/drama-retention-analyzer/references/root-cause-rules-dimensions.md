# Root Cause Rules — Phase 2 Dimensions (Load on Demand)

> Load this file ONLY when user selects a Phase 2 drill-down. Phase 1 core rules live in `root-cause-rules.md`.
>
> **Selective loading**: Each dimension is independent. Load only the dimension matching the user's drill-down selection — do NOT load all 5 dimensions at once.
>
> Dimension selection guide:
> - User selected "Segment deep-dive" (option 5) → load §A only
> - User selected "Time dynamics" (option 6) → load §B only
> - User selected "Social viral" (option 7) → load §C only
> - User selected "Genre comparison" (option 8) → load §D only
> - User selected "ROI loop" (option 9) → load §E only

---

## §A Dimension A: Segment Depth

### RA-1: Segment Retention Divergence
- **Trigger**: Different user segments (new/returning, organic/paid, channel) show 3-episode retention difference >15pp
- **Cause**: Content or product experience favors specific segment; others find mismatched value
- **Validation**: Compare per-segment per-episode completion curves; check paywall/ad experience across segments
- **Confidence**: High

### RA-2: Genre Preference Mismatch
- **Trigger**: Genre-preference-tagged users (e.g., sweet-romance lovers watching revenge drama) show E1 completion <40% AND 3-episode retention <20%
- **Cause**: Traffic acquisition brings users whose genre preference doesn't match drama
- **Validation**: Compare genre preference distribution of acquired traffic vs high-retention base
- **Confidence**: High
- **Note**: Cross-layer with R1-4 — adds genre preference dimension

### RA-3: Payment Path Divergence
- **Trigger**: Single-episode buyers vs monthly members vs discount-conversion users show finale retention difference >2x
- **Cause**: Payment path affects viewing commitment — monthly members binge, single-episode buyers sample
- **Validation**: Compare per-payment-path viewing pace (eps/day) and completion curves
- **Confidence**: Medium

---

## §B Dimension B: Time Dynamics

### RB-1: First-Day Burst Then Decay
- **Trigger**: D1 retention ≥30% BUT D7 retention <10% (7-day decay >60% of D1 base)
- **Cause**: Initial buzz/hype-driven traffic but content doesn't sustain interest; update gap or novelty fades
- **Validation**: Compare D1→D7 retention curve across dramas; check update schedule impact
- **Confidence**: High

### RB-2: Update Rhythm Disruption
- **Trigger**: Daily-update drama shows dropout spike on gap days >3x average daily dropout
- **Cause**: Habitual viewing disrupted when expected episode doesn't arrive; users turn to alternatives
- **Validation**: Compare dropout on update days vs gap days; check competitor release schedule
- **Confidence**: High
- **Note**: Overlaps with R4-5; focuses on temporal pattern rather than per-episode spike

### RB-3: Seasonal/Holiday Pattern
- **Trigger**: Drama launched during holiday shows D1≥35% BUT post-holiday D7 drops >25% (more than typical)
- **Cause**: Holiday-attracted traffic is casual/low-commitment; engagement doesn't persist
- **Validation**: Compare holiday vs non-holiday launch retention curves
- **Confidence**: Medium

### RB-4: Lifecycle Stage Decay Model
- **Trigger**: Drama in D30+ phase shows per-day active viewers declining >5%/day consistently for 7+ days
- **Cause**: Natural lifecycle exhaustion; content has exhausted its audience pool
- **Validation**: Fit exponential decay model to daily active viewers; compare with genre-typical half-life
- **Confidence**: Medium

### RB-5: Three-Tier Retention Divergence
- **Trigger**: D1/D7/D30 on three bases (all visitors / paywall-reaching / full-completion) shows divergence:
  - Visitor D7 <15% BUT paywall D7 >40% → leak is before paywall
  - Paywall D7 >40% BUT completion D7 <20% → leak is after payment
  - All three low (<20%/<30%/<10%) → universal retention problem
- **Cause**: Different user commitment levels respond differently to content
- **Validation**: Calculate D1/D7/D30 on all three bases; compare tier-specific decay curves
- **Confidence**: High

---

## §C Dimension C: Social / Viral

### RC-1: Share-Driven New Viewer Pipeline Break
- **Trigger**: Social share volume declining >30% vs previous 5-ep average AND same-period new viewer inflow declining >20%
- **Cause**: Content no longer generates share-worthy moments; sharing UX friction
- **Validation**: Track share→new viewer→3-episode retention funnel
- **Confidence**: Medium

### RC-2: Comment/Danmaku Engagement Correlation
- **Trigger**: Episodes with danmaku density >2x average show completion >15% higher than low-engagement episodes
- **Cause**: Social viewing experience enhances stickiness; low-engagement episodes feel isolating
- **Validation**: Calculate correlation between comment density and per-episode completion
- **Confidence**: Medium

### RC-3: UGC Secondary Propagation Impact
- **Trigger**: Drama with active UGC clipping (clips >50 in past 7 days) shows organic traffic >30% of total AND organic 3-ep retention >paid by 10+pp
- **Cause**: UGC clips attract genuinely interested viewers; clip creators act as taste-matching filters
- **Validation**: Track UGC clip volume → organic traffic → retention pipeline
- **Confidence**: Low

### RC-4: Social Recall vs Platform Push
- **Trigger**: Social-recommended return users show 3-ep retention >2x platform-push-recalled users
- **Cause**: Social recommendation carries personal endorsement weight; platform push feels impersonal
- **Validation**: Compare 3-ep retention between social-recalled vs push-recalled users
- **Confidence**: Medium

---

## §D Dimension D: Genre Comparison

### RD-1: Genre Benchmark Gap
- **Trigger**: Drama 3-ep retention >15pp below same-genre benchmark average (Top 5 comparable)
- **Cause**: Content quality/positioning below genre standard; or genre tag doesn't match content
- **Validation**: Compare retention curve with 3-5 same-genre dramas; identify divergence point
- **Confidence**: High

### RD-2: Genre Positioning Mismatch
- **Trigger**: Drama tagged as genre X but shows retention curve pattern typical of genre Y
- **Cause**: Marketing positioning misaligns with actual content; attracts wrong audience expectations
- **Validation**: Compare actual retention curve shape with genre-typical templates
- **Confidence**: Medium

### RD-3: Genre Lifecycle Mismatch
- **Trigger**: Drama in genre with typically short lifecycle shows unusually long decay tail OR vice versa
- **Cause**: Content pacing doesn't match genre audience expectations
- **Validation**: Compare D1→D7→D30 curve with genre-typical lifecycle patterns
- **Confidence**: Medium

---

## §E Dimension E: ROI / Commercialization Full-Loop

### RF-1: LTV/CAC Mismatch
- **Trigger**: Drama LTV < CAC — negative ROI
- **Cause**: Over-investment in acquisition for underperforming content; or monetization extracts too little
- **Validation**: Calculate per-drama LTV (ad + paid revenue per user × lifespan) and compare with CAC
- **Confidence**: High
- **Action**: Reduce acquisition spend, shift to organic/social, or increase monetization

### RF-2: Pay Funnel Bottleneck
- **Trigger**: Pay funnel conversion drops >50% at any single stage vs previous stage
- **Cause**: Specific stage UX/friction/pricing issue blocking monetization flow
- **Validation**: Build full pay funnel with stage-by-stage conversion; identify bottleneck
- **Confidence**: High

### RF-3: ARPU-Retention Paradox
- **Trigger**: High-ARPU drama (ARPU >2x genre avg) shows 3-ep retention <25% AND finale retention <10%
- **Cause**: Aggressive monetization extracts revenue from small committed audience but blocks broader retention
- **Validation**: Compare ARPU vs retention scatter across dramas
- **Confidence**: Medium

### RF-4: Paid User Lifecycle Attrition
- **Trigger**: Paid user 30-day churn >40% after first payment AND paid user avg viewing <50% of total episodes
- **Cause**: Post-payment content quality drops, or payment was impulse-driven
- **Validation**: Compare paid user per-episode completion with free user (pre-paywall); check refund rate
- **Confidence**: Medium
