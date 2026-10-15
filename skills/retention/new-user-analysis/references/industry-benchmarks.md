---
title: "New User Industry Benchmarks"
summary: "D1 retention, session count, feature adoption, monetization readiness benchmarks by product type"
---

# New User Industry Benchmarks

Version: 1.0.0
Scope: first-day quality scoring (Phase 2) and behavior sequence analysis (Phase 3) reference values.

---

## 1. How to Use This File

- Benchmarks are **directional ranges**, not hard pass/fail lines. Always compare against the project's own 7-14 day trend before declaring an anomaly.
- Each metric gives three tiers: **Healthy** (green), **Warning** (yellow), **Critical** (red). These map directly to the Phase 2 score dashboard in `report-templates.md`.
- When a project falls outside its product-type range, check `root-cause-rules.md` for the matching hypothesis.
- Sources: public industry reports (GameAnalytics, AppsFlyer, Adjust, Localytics), ThinkingData customer aggregate observations, and practitioner consensus. Ranges are intentionally wide to cover sub-genres.

---

## 2. D1 Retention (Next-Day Return of New Users)

Definition: % of users whose first-active date is D0 who trigger any event on D1.

| Product Type | Healthy | Warning | Critical | Notes |
|---|---|---|---|---|
| Game - Casual/Hyper-casual | 35-50% | 25-35% | <25% | Hyper-casual lives on ad ARPU; D1 <25% usually kills the UA economics |
| Game - Midcore (SLG/RPG/Card) | 40-55% | 30-40% | <30% | Midcore players are stickier; tutorial completion strongly predicts D1 |
| Game - Hardcore (MMO/MOBA/FPS) | 45-60% | 35-45% | <35% | High install intent; <35% signals server/performance or expectation mismatch |
| E-commerce / Retail | 25-40% | 15-25% | <15% | Many users install for a single purchase; D1 naturally lower |
| Social / Community | 35-50% | 25-35% | <25% | Content feed depth drives return; empty-feed problem shows here first |
| Social - Dating / Matching | 40-55% | 30-40% | <30% | Match success on D0 is the strongest D1 predictor |
| Tool / Utility | 20-35% | 12-20% | <12% | Utilities are need-driven; judge on D7/D30 instead |
| SaaS / Productivity (mobile) | 30-45% | 20-30% | <20% | Activation (aha-moment) matters more than raw return |
| Content / Media (video, news) | 35-50% | 25-35% | <25% | D0 watch time >10 min is the leading indicator |
| Education / Learning | 30-45% | 20-30% | <20% | Streak mechanics inflate D1; check D7 to confirm real habit |

Quick sanity rules:
- D1 within a product type should not swing >5pp day-over-day without a release, campaign, or holiday.
- Weekday vs weekend gap of 3-8pp is normal for games and content; >10pp deserves a look.

---

## 3. First-Day Session Count

Definition: average number of distinct sessions on the first-active day (session gap default 30 min).

| Product Type | Healthy | Warning | Critical | Notes |
|---|---|---|---|---|
| Game - Casual | 3-5 | 2-3 | <2 | Short sessions are fine; count matters more than length |
| Game - Midcore/Hardcore | 2-4 | 1.5-2 | <1.5 | Fewer but longer sessions; pair with duration |
| E-commerce | 1.5-3 | 1-1.5 | <1 | Single-session purchase is a healthy pattern here |
| Social / Community | 3-6 | 2-3 | <2 | Feed checking is habitual; high count expected |
| Social - Dating | 4-8 | 2-4 | <2 | Notification-driven reopens inflate count; verify with duration |
| Tool / Utility | 1-2 | 1 | <1 | 1 task-focused session is completely normal |
| SaaS / Productivity | 2-4 | 1-2 | <1 | Activation flow often spans 2+ sessions |
| Content / Media | 2-4 | 1.5-2 | <1.5 | Binge pattern: 1-2 long sessions can be healthy |

Cross-check: session count <1.5 **and** total duration <2 min on D0 strongly suggests install-fraud or deep-link landing failure — see synthetic-data checks in `data-validation.md`.

---

## 4. First-Day Session Duration (per session, median)

| Product Type | Healthy | Warning | Critical |
|---|---|---|---|
| Game - Casual | 3-8 min | 1.5-3 min | <1.5 min |
| Game - Midcore/Hardcore | 8-20 min | 4-8 min | <4 min |
| E-commerce | 4-10 min | 2-4 min | <2 min |
| Social / Community | 5-15 min | 2-5 min | <2 min |
| Social - Dating | 8-20 min | 3-8 min | <3 min |
| Tool / Utility | 1-5 min | 0.5-1 min | <0.5 min |
| SaaS / Productivity | 5-12 min | 2-5 min | <2 min |
| Content / Media | 10-30 min | 5-10 min | <5 min |

Median over mean: duration distributions are right-skewed; means get inflated by a few marathon users. Report median, and p25/p75 if volume allows.

---

## 5. Feature Adoption (First-Day)

Definition: % of D0 new users who trigger the product's core feature event at least once on D0.

| Product Type | Core Feature | Healthy | Warning | Critical |
|---|---|---|---|---|
| Game | Complete tutorial / FTUE | 70-85% | 50-70% | <50% |
| Game | Reach first progression milestone (level up, first win) | 50-70% | 35-50% | <35% |
| E-commerce | View product detail (PDP) | 60-80% | 40-60% | <40% |
| E-commerce | Add to cart on D0 | 15-30% | 8-15% | <8% |
| Social | Consume content (view >N items) | 60-80% | 40-60% | <40% |
| Social | First interaction (like/comment/follow) | 25-45% | 15-25% | <15% |
| Social - Dating | Complete profile | 60-80% | 40-60% | <40% |
| Tool | Complete core task once | 50-70% | 35-50% | <35% |
| SaaS | Reach activation milestone (create first artifact) | 40-60% | 25-40% | <25% |
| Content | Play/watch first content to 50%+ | 50-70% | 35-50% | <35% |

Tutorial completion is the single strongest universal predictor across games: users who finish FTUE retain 1.5-2.5x better on D1/D7 than skippers/abandoners.

---

## 6. Monetization Readiness (First-Day)

Definition: D0 behaviors indicating payment intent, not necessarily D0 payment itself.

| Metric | Healthy | Warning | Critical | Notes |
|---|---|---|---|---|
| D0 payer conversion (game) | 1-3% | 0.5-1% | <0.5% | Midcore/hardcore higher (2-5%); hyper-casual near 0 by design |
| D0 payer conversion (e-commerce) | 3-10% | 1.5-3% | <1.5% | Includes first-order users; promo-driven spikes normal |
| D0 payer conversion (social/live) | 0.5-2% | 0.2-0.5% | <0.2% | Gift/subscription products convert later; D0 low is OK |
| D0 view paywall / store (game) | 20-40% | 10-20% | <10% | Leading indicator; low exposure = monetization invisible |
| D0 first recharge within 10 min of tutorial end | Strong positive signal | — | — | Track as segment, not threshold |

Do not score monetization on D0 revenue for ad-driven products; use D0 ad impressions per user instead (healthy: 3-8 for hyper-casual).

---

## 7. Behavior Sequence / Path Benchmarks (Phase 3)

| Metric | Healthy | Warning | Critical | Reference |
|---|---|---|---|---|
| Path entropy (normalized, 0-1) | 0.5-0.85 | 0.3-0.5 or 0.85-0.95 | <0.3 or >0.95 | See `path-analysis-guide.md` §entropy |
| First event = core feature event | 40-60% | 25-40% | <25% | Low values = onboarding misroutes users |
| Bounce (path length 1) rate | <15% | 15-30% | >30% | >30% often means landing page / tracking issue |
| Median path length | 3-6 events | 2-3 or 6-8 | <2 or >8 | >8 with low entropy = bot signature |
| Top-3 paths coverage | 40-60% | 25-40% or 60-75% | <25% or >75% | Too concentrated = rigid funnel; too scattered = no clear journey |

Sequential funnel drop-off (any single step): healthy <40%, warning 40-60%, critical >60%; >80% single-step drop means the step is functionally broken, not "optimizable".

---

## 8. Structural Mutation Reference Values (Phase 5)

These feed the alert thresholds used by `root-cause-rules.md`.

| Mutation Type | Metric | Warning | Critical |
|---|---|---|---|
| Channel mix shift | Top-channel share WoW change | >15% | >25% |
| Channel mix shift | Chi-square p-value | <0.05 | <0.01 |
| Device/region shift | Any single device-model share WoW | >10% | >20% |
| Behavioral shift | D1 retention WoW | >8pp | >15pp |
| Behavioral shift | Entropy WoW | >0.15 | >0.3 |
| Value shift | D0 payer rate WoW | >30% relative | >50% relative |
| Traffic source shift | Organic vs paid share WoW | >10pp | >20pp |
| Geo concentration | Top-1 province/country share WoW | >8pp | >15pp |

KL divergence (channel distribution vs baseline): <0.1 stable, 0.1-0.3 watch, >0.3 significant shift, >0.6 structural break.

---

## 9. New User Volume & Data Quality Floors

| Signal | Healthy | Warning | Critical |
|---|---|---|---|
| Daily new users for daily-grain analysis | >200/day | 50-200/day | <50/day (use monthly grain) |
| Device ID duplication rate (same device, multiple new accounts/day) | <2% | 2-8% | >8% |
| New users with zero properties (no channel/os/model) | <5% | 5-15% | >15% |
| Events per new user on D0 (median) | >=5 | 2-5 | <2 |
| D0 session duration = exactly 0s share | <3% | 3-10% | >10% |

Cross-reference: full synthetic-data checklist in `data-validation.md` §6.

---

## 10. Composite Score Anchors (Phase 2)

Composite = weighted sum of 4 dimension scores (weights per product type in `product-type-configs.md`).

| Composite | Label | Interpretation |
|---|---|---|
| >=80 | Excellent | Scale UA spend; protect what works |
| 65-79 | Healthy | Normal optimization territory |
| 50-64 | Watch | One dimension dragging; fix before scaling |
| 40-49 | Poor | Quality problem likely suppressing retention |
| <40 | Failure | Do not scale spend; audit traffic quality first |

---

## 11. Caveats

- Benchmarks drift with privacy policy (ATT on iOS lowered measurable retention 3-8pp across categories). Note OS mix before comparing to history.
- Regional differences are large: SEA casual-game D1 runs 5-10pp below NA/EU; CN Android channel fragmentation inflates channel-mix mutation alerts.
- Holidays and version releases routinely move metrics 10-30% for 1-3 days. Always annotate before alarming.
- When in doubt, trust the project's own baseline over this file. This file exists to catch "we don't know what normal looks like" situations.
