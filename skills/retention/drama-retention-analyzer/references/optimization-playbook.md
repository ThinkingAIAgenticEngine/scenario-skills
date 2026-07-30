# Optimization Playbook — Short Drama Retention

> Per-layer optimization strategies + consolidated monitoring metrics + industry benchmarks.

---

## Layer 1: Traffic

### Fake Traffic / Channel Quality
- **Quick Fix**: Reduce budget for channels with high CTR but low start-play rate / completion; prepare 2-3 creative variants, test start-play rate
- **System Fix**: Channel quality scoring (CTR × start-play × D1 retention); creative review standards (≥80% consistency with actual content); narrow audience targeting
- **A/B Test**: Creative style (highlight vs narrative vs character); targeting (broad vs precision vs profile)

---

## Layer 2: Opening

### Opening Hook / 3-Episode Hook
- **Quick Fix**: Re-edit first 15s — move conflict/cliffhanger upfront; add 15s preview on playback page; if paywall at E2-3, delay to after E5
- **System Fix**: Opening hook standard (first 15s must include 1 conflict/cliffhanger/emotional impact); E3 ending must have unresolved core cliffhanger; 3-ep retention target by type (vertical ≥35% pass, ≥50% premium)
- **A/B Test**: Opening version (original vs conflict-upfront vs cliffhanger-upfront); paywall popup position (E3 vs E5 vs E10)

---

## Layer 3: Plot

### Paywall Blocking
- **Quick Fix**: 30s free preview for paid eps; limited-time first-purchase discount; first paid ep free trial
- **System Fix**: Adjust paywall start position (move from E29 to E15-20, A/B test); 3-day free membership trial; tiered pricing (per-ep / monthly / quarterly)

### Content Quality / Pacing
- **Quick Fix**: Review episodes with dropout >15%; mark skip-view hotspots; keep 1-2 core progression points per episode
- **System Fix**: Writing pacing standards — 1 mini-cliffhanger every 5 eps, 1 major every 10 eps; resolution episodes must open new cliffhanger; per-episode completion rate estimation pre-launch
- **A/B Test**: Episode duration (5min vs 8min vs 10min); skip-view assistance (none vs key-point markers vs fast-forward rec)

### Bad Ending
- **Quick Fix**: Finale cliffhanger preview in penultimate episode; ensure final 2-3 eps have core conflict progression; analyze finale review sentiment
- **System Fix**: Final 3 eps must have core conflict + reasonable resolution; ending A/B test (2-3 versions); user feedback loop to content team

### Segment-Based (Lifecycle)
- Opening (E1-E3) dropout >40% → re-edit first 3 eps for hook density
- Middle (E4 to pre-paywall) dropout >30% → compress padding, accelerate conflict
- Paywall segment transition <50% → add 30s paid preview, test position shift
- Post-paywall paid users <50% total → review post-paywall script, add completion incentives
- Finale (last 5) dropout >20% → ensure core conflict + emotional payoff

---

## Layer 4: Commercialization & Product

### Paywall Node
- **Quick Fix**: Delay paywall popup (E2-3 → after E5); popup UX (between-episode → in-episode natural transition); 30s free preview
- **System Fix**: Paywall position by type — micro-short (1-3min): E10-15; standard (5-10min): E20-30; long (20-45min): E5-8. Tiered pricing + 3-day free trial.

### Ad & Product Experience
- **Quick Fix**: ≤2 ads per episode; move ads from plot climax to scene transition points; increase close button size
- **System Fix**: Crash rate <2%; auto-alert for technical anomalies; auto-adjust ad frequency by completion rate

### Paid Content Expectation
- **Quick Fix**: 30s highlight clip before paid eps; show paid user ratings per episode; creative consistency review
- **System Fix**: Paid episode quality review pre-launch; user feedback loop; refund/compensation mechanism

---

## Layer 5: Long-term

### Re-engagement
- **Quick Fix**: New episode release push ("The drama you're following has updated"); resume playback prompt ("You left off at episode X"); hot comments push
- **System Fix**: Auto follow reminder on episode update; limited-time free re-view events; follow ranking / check-in / comment interaction

### Cross-Drama Transition
- **Quick Fix**: Same-genre recommendation at ending; completion recommendation popup; same-genre sequel preview
- **System Fix**: Cross-drama recommendation chain; same-genre batch strategy (reuse script templates); 7/15/30-day post-completion push series

### Re-view Value
- **Quick Fix**: Completion easter egg / hidden ending; director commentary / behind-the-scenes; highlight compilation push
- **System Fix**: Drama-level discussion area; rating/review system; derivative content (spin-offs / parallel endings)

---

## Dimension A-E Quick Reference (Phase 2)

- **Dim A (Segment)**: Segment-specific push timing; genre preference matching engine; payment path-specific hooks
- **Dim B (Time)**: Phase-specific engagement hooks (launch/stable/decline); gap day content filler; dynamic update schedule
- **Dim C (Social)**: One-tap share with auto-preview; share-worthy scene markers; UGC clip encouragement; comment sentiment tracking
- **Dim D (Genre)**: Same-genre Top5 benchmark overlay; genre positioning audit; genre retention benchmark database
- **Dim E (ROI)**: Per-drama LTV/CAC dashboard; dynamic acquisition budget; monetization-retention balance model; full pay funnel audit

---

## Consolidated Monitoring Metrics (All Layers)

| Layer | Metric | Alert Threshold | Frequency |
|-------|--------|----------------|-----------|
| L1 | Start-play rate | <30% | Daily |
| L1 | D1 next-day retention | <20% | Daily |
| L1 | Same-day cross-drama viewing rate (short drama) | ≥15% (D1 distortion) | Daily |
| L2 | E1 completion rate | <50% (vertical short) | Daily |
| L2 | 3-episode retention | <35% | Daily |
| L3 | E1→E10 retention | <50% (short drama) | Weekly |
| L3 | E1→Finale retention | <10% (short drama) | Weekly |
| L3 | Avg episodes watched per visitor | <30% of total | Weekly |
| L3 | Drama abandonment rate | >70% | Weekly |
| L3 | Opening segment (E1-E3) dropout | >40% | Weekly |
| L3 | Middle segment dropout | >30% | Weekly |
| L3 | Finale segment dropout | >20% | Per episode |
| L3 | Max per-episode dropout | >25% | Per episode |
| L4 | Pay conversion rate | <15% | Daily |
| L4 | Paywall dropout rate | >50% | Daily |
| L4 | Per-episode mid-exit rate | >15% | Daily |
| L4 | Crash rate | >5% | Daily |
| L5 | 7-day re-view rate | <3% | Weekly |
| L5 | 7-day user re-engagement rate | <15% | Weekly |
| L5 | 30-day revisit rate | <8% | Weekly |
| L5 | Cross-drama transition rate | <5% | Weekly |

---

## Industry Benchmarks by Drama Type

| Type | 3-Ep Retention Pass | 3-Ep Premium | Finale Pass | Finale Premium | D1 Pass | D1 Premium |
|------|-------------------|--------------|-------------|-----------------|---------|------------|
| Vertical Micro-Short (1-3min) | ≥35% | ≥50% | ≥15% | ≥25% | ≥25% | ≥35% |
| Vertical Short (5-10min) | ≥35% | ≥50% | ≥12% | ≥20% | ≥20% | ≥30% |

> Horizontal short dramas (10-20min/episode) are not supported by this skill. See SKILL.md "Not Applicable" section.

### Paywall Benchmarks

| Paywall Position | Pay Conv Pass | Pay Conv Premium | Dropout Pass | Dropout Premium |
|-----------------|---------------|------------------|--------------|-----------------|
| E5 (very early) | ≥20% | ≥30% | <40% | <30% |
| E10-15 (early) | ≥18% | ≥25% | <45% | <35% |
| E20-30 (standard) | ≥15% | ≥25% | <50% | <40% |
| E40+ (late) | ≥12% | ≥20% | <55% | <45% |

### LTV/CAC Benchmarks

| Type | LTV/CAC Healthy | LTV/CAC Premium | Monetization Model |
|------|----------------|-----------------|-------------------|
| Vertical Micro-Short | ≥1.5 | ≥2.0 | Light ads + early paywall |
| Vertical Short | ≥1.5 | ≥2.5 | Moderate ads + standard paywall |

### Pay Funnel Benchmarks

| Stage | Pass | Premium |
|-------|------|---------|
| Impression → Click | ≥2% | ≥5% |
| Click → Start Play | ≥40% | ≥60% |
| Start Play → 3-ep Retention | ≥35% | ≥50% |
| 3-ep → Paywall Encounter | ≥80% | ≥90% |
| Paywall → Pay Conversion | ≥15% | ≥25% |
| Pay → 7-day Retention | ≥60% | ≥75% |
| Pay → Completion | ≥50% | ≥70% |
| Completion → Cross-drama | ≥8% | ≥15% |

---

## Post-Implementation Verification Loop

After implementing any optimization (Quick Fix, System Fix, or A/B Test), verify effectiveness through a structured re-run:

### Verification Flow

1. **Wait for data accumulation**: 7 days for traffic/opening fixes, 14 days for paywall/conversion fixes, 30 days for long-term retention fixes
2. **Re-run Phase 1 core analysis** on the same drama (same project ID, same drama, updated time range covering the post-implementation period)
3. **Compare before vs after** on the key metric tied to the implemented fix (see table below)
4. **Judge effectiveness**:
   - Improvement ≥ threshold → document as proven fix, move to monitoring
   - Improvement < threshold → escalate: Quick Fix → System Fix → A/B Test → re-diagnose
5. **Iterate**: if no improvement after escalation, re-run root-cause rules to check if the original attribution was correct

### Per-Fix Verification Metrics

| Fix Category | Key Metric to Compare | Improvement Threshold | Re-run After |
|--------------|----------------------|----------------------|-------------|
| Traffic / channel quality | D1 retention, start-play rate | ↑ >5pp | 7 days |
| Opening hook (E1-E3) | E1 completion, 3-episode retention | ↑ >5pp | 7 days |
| Paywall position | Paywall pass rate, pay conversion | ↑ >5pp | 14 days |
| Content quality (specific episodes) | Max churn episode churn rate | ↓ >15% | 7 days |
| Ad frequency / product | Mid-episode exit rate, crash rate | ↓ >50% relative | 7 days |
| Re-engagement push | 7-day re-engagement rate | ↑ >3pp | 30 days |
| Cross-drama transition | Cross-drama transition rate | ↑ >2pp | 30 days |

> When presenting optimization recommendations, always append the verification metric and re-run period. Example: "Delay paywall to E15 → Re-run in 14 days, check paywall pass rate ↑ >5pp".
> If the user cannot wait for the full verification period, run a directional check at 50% of the recommended window and label results as "preliminary, directional only".
