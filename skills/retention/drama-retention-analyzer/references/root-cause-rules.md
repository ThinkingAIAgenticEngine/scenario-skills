# Root Cause Rules — Core (5-Layer, Phase 1)

> Phase 1 core rules. Phase 2 dimension rules (RA-RE) live in `root-cause-rules-dimensions.md` — load only when user selects a drill-down.
> Rules are sorted by layer priority. **Must investigate from Layer 1 (Traffic) first** — avoid misjudging traffic issues as content issues.

---

## Layer 1: Traffic

### R1-1: Fake Traffic / Clickbait Mismatch
- **Trigger**: Impression CTR > 2x industry avg AND start-play rate <30% AND E1 completion <40%
- **Cause**: Clickbait materials, cover mismatch with actual content
- **Validation**: Compare material-displayed content vs actual drama content; AB test start-play rate across materials
- **Confidence**: High

### R1-2: Channel Quality Stratification
- **Trigger**: Same drama, different channels D1 retention difference >10pp
- **Cause**: Channel traffic quality stratification; low-retention channel traffic is generic/low-quality
- **Validation**: Compare per-channel start-play rate + E1 completion + D1 retention; confirm persistence
- **Confidence**: High

### R1-3: Overall D1 Retention Too Low
- **Trigger**: All-channel D1 next-day retention <20%
- **⚠️ Short-Drama Guard (Mandatory)**: For micro-short dramas (1-3min/episode, binge-completable same-day), MUST check same-day cross-drama viewing rate first. If ≥15%, D1 is structurally suppressed — recompute non-completer D1 retention before judging. Only fire R1-3 if non-completer D1 <20%. See `drama-type-configs.md §Vertical Micro-Short Drama`.
- **Cause**: Overall paid traffic watered down, untargeted traffic, audience mismatch
- **Validation**: Match rate between paid traffic audience profile and target; compare organic vs paid D1
- **Confidence**: High (with guard applied)

### R1-4: High Traffic Volume But Low Retention
- **Trigger**: Daily start-play >10,000 BUT 3-episode retention <25%
- **Cause**: Low-quality paid traffic, exaggerated clickbait, untargeted audience
- **Validation**: Compare paid vs organic start-play rate and retention; check material-content gap
- **Confidence**: High

---

## Layer 2: Opening

### R2-1: Opening Hook Failure
- **Trigger**: E1→E2 dropout >25% AND E1 completion <60%
- **Cause**: E1 opening lacks conflict/suspense/immersion; first 15-30s fail to hook
- **Validation**: AB test opening versions; analyze dropout time within first 30s of E1
- **Confidence**: High

### R2-2: 3-Episode Hook Failure
- **Trigger**: E1 completion normal (≥65%) BUT 3-episode retention <30% (cliff decline)
- **Cause**: First 3 episodes lack core suspense/hook; free-section ending has no retention point
- **Validation**: Check whether E3 ending has suspense setup; compare with high-retention dramas
- **Confidence**: High

### R2-3 / R4-1: Early Paywall Impact (Cross-Layer: Opening + Commercialization)
- **Trigger**: Paywall popup at episode 2-5 AND 3-episode retention cliff decline >10-15pp (vs no-popup version)
- **Cause**: Users resist premature paywall; viewing momentum interrupted
- **Validation**: Compare 3-episode retention with deferred popup version; check post-popup dropout rate
- **Confidence**: High
- **Cross-layer**: Affects Layer 2 (Opening) + Layer 4 (Commercialization)
- **See also**: R4-1 in Layer 4 below (same rule, commercialization perspective)

---

## Layer 3: Plot

### R3-1 / R3-S3: Paywall Blocking (Per-Episode + Segment)
- **Per-Episode Trigger**: Free→Paid dropout >50% AND paid conversion <15%
- **Segment Trigger**: Paywall segment (first paid ep ±1) dropout >50% OR free→paid transition retention <50%
- **Cause**: Paywall too early or priced too high, blocking free users' path
- **Validation**: Compare conversion rates at different paywall starting positions; test discount/trial
- **Confidence**: High
- **Cross-layer**: Layer 3+4
- **See also**: R3-S3 in §Layer 3 Segment rules below (same rule, segment perspective); R4-4 in Layer 4 (paywall conversion moderate)

### R3-2: Episode Content Quality Collapse
- **Trigger**: Within-episode completion <40% AND next-episode dropout spike >25%
- **Cause**: Pacing disruption / plot disconnect / rough production
- **Validation**: Watch episode content, check screenwriting/editing; compare completion with same-genre
- **Confidence**: High

### R3-3: Post-Cliffhanger Dropout
- **Trigger**: >15% dropout at episode immediately following cliffhanger resolution
- **Cause**: Suspense overdraw — viewers leave after satisfaction, or resolution unsatisfying
- **Validation**: Compare completion of cliffhanger ep vs resolution ep; user comment sentiment
- **Confidence**: Medium

### R3-4 / R3-S2: Pacing Drag (Per-Episode + Segment)
- **Per-Episode Trigger**: Skip-ahead rate >30% AND completion 40-60% AND gradual dropout acceleration
- **Segment Trigger**: Middle segment (E4 to pre-paywall) dropout >30% OR avg per-episode dropout in segment >15%
- **Cause**: Plot padding, formulaic repetition, pacing drag, conflict gap
- **Validation**: Analyze skip-view distribution; compare fast-paced vs slow-paced episodes
- **Confidence**: Medium
- **See also**: R3-S2 in §Layer 3 Segment rules below (same rule, segment perspective)

### R3-5 / R3-S5: Bad Ending (Per-Episode + Segment)
- **Per-Episode Trigger**: Last 1-3 episodes dropout >15% (vs early-stage avg) AND final ep completion <50%
- **Segment Trigger**: Finale segment (last 5 eps) dropout >20% OR finale completion <50%
- **Cause**: Rushed ending, unresolved threads, insufficient emotional payoff
- **Validation**: Compare finale completion with drama avg; analyze user comments on ending
- **Confidence**: High
- **See also**: R3-S5 in §Layer 3 Segment rules below (same rule, segment perspective)

### R3-6: Genre Shift Mismatch
- **Trigger**: >15% dropout spike at episode where genre/tone noticeably shifts
- **Cause**: Genre abrupt shift (comedy→tragedy/sweet→angsty/light→heavy), exceeding expectations
- **Validation**: Map emotional curve, compare genre shift point with dropout spike
- **Confidence**: Medium

### R3-7: Uniform Decline
- **Trigger**: Per-episode dropout stays 5-8%, no obvious peak, but overall retention far below benchmark
- **Cause**: Overall script quality poor, character collapse, logic inconsistent
- **Validation**: Compare per-episode curve shape with same-genre high-retention dramas
- **Confidence**: Medium

### R3-S1: Opening Segment Failure (E1-E3)
- **Trigger**: Opening segment dropout >40% OR segment retention E1→E4 <60%
- **Cause**: Opening hook insufficient, E1-E3 lack core progression, or early paywall disrupts
- **Validation**: Compare opening segment retention with genre benchmark
- **Confidence**: High

### R3-S4: Post-Paywall Segment Attrition
- **Trigger**: Post-paywall segment dropout >35% OR paid users avg episodes <50% of total
- **Cause**: Post-paywall content doesn't deliver on pre-paywall promise; pacing collapse after monetization
- **Validation**: Compare paid user per-episode completion pre vs post paywall; check refund rate
- **Confidence**: High

---

## Layer 4: Commercialization & Product

### R4-2: Ad Frequency / Product Issues
- **Trigger**: Mid-episode exit rate >15% but no plot turning point (adjacent eps completion normal) AND/OR crash rate >5%
- **Cause**: Excessive ads, accidental taps, stuttering/crashes — non-content product issues
- **Validation**: Compare exit rate between ad-free vs ad-supported versions; check technical logs
- **Confidence**: High

### R4-3: Paid Content Not Meeting Expectations
- **Trigger**: Retention plummets after payment (paid user dropout >20%) AND refund rate >5%
- **Cause**: Material promotion inconsistent with actual content, cash-grab content
- **Validation**: Compare material clips with actual paid content; check paid user ratings
- **Confidence**: High

### R4-4: Paywall Conversion Failure Moderate
- **Trigger**: Free→Paid dropout 30-50% AND paid conversion 15-25%
- **Cause**: Pricing on high side but not fatal, optimization space exists
- **Validation**: Test different pricing/discounts/trial viewing duration
- **Confidence**: Medium

### R4-5: Update Gap Dropout
- **Trigger**: Dropout spike on episodes expected to release on a specific day but delayed, OR cross-day dropout >10% higher during update gaps in daily-update drama
- **Cause**: Continuous-update rhythm interrupted, user habit disrupted
- **Validation**: Compare dropout on days with/without update gaps; check update logs vs dropout curve
- **Confidence**: Medium
- **Note**: Only triggers when `update_pattern = daily continuous update`

---

## Layer 5: Long-term

### R5-1: Short-Lived Hit Drama
- **Trigger**: High play volume (daily avg >50,000) BUT 30-day return rate <8% AND 7-day re-watch <5% AND 7-day re-engagement <15%
- **Cause**: Pure fast-food-style traffic drama, no long-term user value
- **Validation**: Compare content characteristics with same-genre high re-watch dramas
- **Confidence**: Medium

### R5-2: High-Value Long-Term Drama
- **Trigger**: Full-drama completion retention ≥15% AND 7-day re-watch ≥10% AND cross-drama jump ≥8%
- **Cause**: Good content reputation, users willing to re-watch and jump
- **Confidence**: Medium (positive attribution, not issue diagnosis)

### R5-3: Recall Mechanism Failure
- **Trigger**: 3-day return rate <5% after dropout from any episode AND 7-day re-watch <3%
- **Cause**: Push/notification/reminder mechanisms ineffective
- **Validation**: Test return effectiveness with different push frequency and copy
- **Confidence**: Medium

---

## Compound Diagnosis

When multiple rules match:
1. **Layer 1 (Traffic) first** — exclude traffic issues before content attribution
2. **Layer 2 (Opening)** → **Layer 3 (Plot)** → **Layer 4 (Commercialization)** → **Layer 5 (Long-term)**
3. Mark cross-layer issues (e.g. R2-3/R4-1 affects both Opening + Commercialization)
4. **Always include disclaimer**: "Attribution is based on data pattern inference; recommend combining content review and user research for validation"
