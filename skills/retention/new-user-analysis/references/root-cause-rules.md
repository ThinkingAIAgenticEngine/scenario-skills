---
title: "Structural Mutation Root-Cause Rules"
summary: "Trigger → hypothesis → validation → action rules for all 6 mutation types in Phase 5"
---

# Root-Cause Rules for Structural Mutation Diagnosis

Version: 1.0.0
Companion to: `industry-benchmarks.md` §8 (thresholds), `sql-templates.md` T4.x (detection queries).

Each rule follows the same contract:

- **Trigger**: the measurable condition that fires the rule (with benchmark reference).
- **Hypotheses**: ranked candidate causes, most likely first.
- **Validate**: the concrete next query or check that confirms/rejects each hypothesis.
- **Action**: what to tell the stakeholder once confirmed.

Do not present a mutation to the user without running at least one validation step. "Channel share moved 30%" is an observation, not a diagnosis.

---

## Rule 1 — Channel Mix Shift

**Trigger**: Top-channel new-user share changes >15% WoW (warning) or >25% (critical); or chi-square p<0.05 vs baseline distribution; or KL divergence >0.3. (`sql-templates.md` T4.1, T4.2)

**Hypotheses (ranked)**:
1. A channel's UA campaign started/stopped (budget change, campaign end, account suspension).
2. Attribution window or SDK config changed (re-attribution, deferred deep-link fix).
3. Channel fraud spike (click injection flooding one source).
4. Organic uplift from featuring/ASO shifting the mix denominator.

**Validate**:
- Pull daily new-user count by channel for baseline + comparison windows (T4.1). Absolute counts, not just shares — a share shift with flat absolutes on the "losing" channel means the winner grew, not the loser died.
- Check the suspect channel's D1 retention & session quality vs its own history. Fraud traffic shows <50% of its historical D1 and near-zero durations.
- Ask the UA/marketing owner for campaign calendar; check release notes for SDK version bumps in the window.

**Action**:
- Campaign-driven: annotate, no product action; flag expected D1 retention drift (mix shifts move blended metrics even when per-channel quality is flat — Simpson's paradox).
- Attribution-driven: restate baseline; do not compare pre/post change directly.
- Fraud-driven: hand evidence (device duplication %, zero-duration %, IP clustering) to UA team; recommend pausing the sub-source.

---

## Rule 2 — Device / Region Composition Shift

**Trigger**: any single device-model share WoW >10% (warning) / >20% (critical); or OS version mix shift; or single province/country share WoW >8pp/15pp. (T4.2, T4.4)

**Hypotheses (ranked)**:
1. New channel/sub-source targeting different device tier (e.g., low-end Android flood from a new DSP).
2. Device-farm or emulator traffic (one model, one OS build, one city).
3. OS release adoption wave (new iOS/Android version rollout week).
4. Geo-targeted campaign or store featuring in one region.

**Validate**:
- Cross-tab the shifted device model × channel. If the model concentrates in one sub-source → targeting; if spread everywhere → organic/OS wave.
- Emulator/farm signatures: identical OS build string, screen resolution cluster, battery/gyro missing, timezone ≠ geo, zero-duration sessions (see `data-validation.md` §6).
- Check OS vendor release calendar for rollout-week explanation.

**Action**:
- Fraud: blocklist evidence pack, same as Rule 1.
- Targeting: quality-check the new cohort (D1, duration) before scaling; low-end device influx often needs performance profiling (ANR/crash on those models).
- Organic wave: annotate; update baseline after 7 days.

---

## Rule 3 — Behavioral Shift (Retention / Engagement Break)

**Trigger**: D1 retention WoW drop >8pp (warning) / >15pp (critical); or D0 median duration shift >30%; or path entropy shift >0.15/0.3. (T4.3, `path-analysis-guide.md`)

**Hypotheses (ranked)**:
1. App version release in the window (onboarding change, new FTUE, paywall move, bug).
2. Server-side incident during first-session (login failures, content feed empty, matchmaking broken).
3. Traffic quality change (new channel mix dragging blended retention — check Rule 1 first).
4. Seasonality/holiday baseline distortion.
5. Tracking change (event renamed, property dropped — metric moves, behavior didn't).

**Validate**:
- Segment D1 by app version: if only the new version dropped → product change; if all versions dropped equally → traffic or server.
- Segment D1 by channel: if blended dropped but per-channel flat → mix effect (Simpson's), not a product regression.
- Check error-event volume (login_fail, api_error, crash) in the window vs baseline.
- Diff event taxonomy between windows (new/missing events) to rule out tracking change.

**Action**:
- Version regression: hotfix/rollback recommendation with the specific step where funnel drop-off spiked (>60% single-step = broken, `industry-benchmarks.md` §7).
- Server incident: annotate the window; exclude from baseline.
- Tracking change: restate metrics; do not alarm stakeholders with phantom churn.

---

## Rule 4 — Value Shift (Monetization Readiness Break)

**Trigger**: D0 payer rate WoW relative change >30% (warning) / >50% (critical); or D0 store-view rate WoW >25%. (T4.3 variant + T2.3)

**Hypotheses (ranked)**:
1. Paywall/pricing/store UI change shipped in window.
2. Promo or discount started/ended (first-recharge pack expiry).
3. Channel mix shift toward non-paying geos/tiers (Rule 1 upstream cause).
4. Payment SDK failure (order-create success but callback lost → undercount).
5. Economy imbalance introduced by version update (currency inflation killing first-purchase value).

**Validate**:
- Order funnel: store_view → sku_view → order_create → pay_success, step rates vs baseline. Find the broken step.
- Check payment-success event volume against server-side order records (if accessible): gap = callback/tracking loss.
- Segment payer rate by channel and version, same Simpson's check as Rule 3.

**Action**:
- Broken funnel step: pinpoint step + version, escalate to product.
- Promo end: annotate; expected reversion, no action.
- Tracking loss: data fix; do not report a revenue drop that didn't happen.

---

## Rule 5 — Traffic Source Shift (Organic vs Paid)

**Trigger**: organic share WoW change >10pp (warning) / >20pp (critical). (T4.3)

**Hypotheses (ranked)**:
1. Paid budget change (most common — same root as Rule 1 but at source level).
2. Store featuring or keyword ranking jump/drop (ASO event).
3. Attribution reclassification (e.g., previously "organic" now resolved to a partner via deferred deep-links).
4. PR/viral event driving genuine organic spike.

**Validate**:
- Absolute organic count trend, not just share. Share up + count flat = paid shrank. Count up = real organic movement.
- Check store ranking/featuring history for the window.
- Verify attribution SDK changelog.

**Action**:
- Real organic spike: identify the content/keyword driving it; brief growth team to amplify.
- Paid-driven: annotate; recalibrate blended quality expectations (organic cohorts typically retain 20-40% better than paid).

---

## Rule 6 — Geo Concentration Shift

**Trigger**: top-1 province/country new-user share WoW >8pp (warning) / >15pp (critical); or HHI (Herfindahl index of geo distribution) WoW change >20%. (T4.4)

**Hypotheses (ranked)**:
1. Geo-targeted campaign launch/stop.
2. Single-region fraud farm (city-level IP clustering).
3. Regional holiday or event (elections, festivals, weather emergencies shifting install behavior).
4. ISP/CDN misclassification (IP→geo mapping change).

**Validate**:
- Geo × channel cross-tab: campaign hypothesis needs the geo surge tied to specific sub-sources.
- Fraud: device duplication + zero-duration + IP ASN clustering in the suspect city.
- Check IP-geo database version notes if the shift is sudden and flat across channels.

**Action**:
- Fraud: evidence pack to UA team.
- Campaign: annotate; adjust regional quality expectations (new geo cohorts need their own retention baseline — do not judge a new market by mature-market benchmarks).
- Misclassification: data note; restate if material.

---

## Meta-Rules (apply to all six)

1. **Mix before product.** For any blended-metric alarm (retention, payer rate, duration), first decompose by channel and version. Mix shifts explain the majority of "behavior changes" — Simpson's paradox is the default suspect.
2. **Absolutes before shares.** A share move with stable absolute counts on both sides is a denominator effect. Always pull counts first.
3. **Version × channel matrix.** Most Phase 5 mysteries resolve inside a 2×2: {old version, new version} × {existing channels, new channel}. Build it before writing hypotheses.
4. **Annotate, don't alarm.** Confirmed benign causes (campaign calendar, holidays, OS rollouts, promo cycles) go into the report as annotations. Reserve "critical" for fraud, regressions, and tracking breaks.
5. **One mutation, one owner.** Every confirmed mutation in the Phase 5 report must carry an owner (UA / product / data) and a next check date. A mutation without an owner is a report decoration.
6. **Baseline hygiene.** After any confirmed structural change (new version, new channel strategy, attribution change), propose a new baseline window. Comparing against a dead baseline manufactures false alarms forever.
