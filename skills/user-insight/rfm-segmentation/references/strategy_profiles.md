# RFM Operational Strategy Profiles

> **Role:** fallback library and guardrail for the dynamic strategy step. This file is **not** a user-facing table template. Stage 7 generates the per-segment strategy dynamically per `references/dynamic_strategy.md` and uses this file only as a completeness check / fallback when project metadata is insufficient.

## 0. Relationship to dynamic strategy

| Stage 7 step | Source of truth |
| --- | --- |
| Generate per-segment objective/actions/KPI | `references/dynamic_strategy.md` (grounded in project event metadata) |
| Completeness + direction guardrail | This file (fixed archetype entries below) |
| Fallback when project metadata insufficient | This file (closest archetype) |

**Naming rule**

Persistent segment keys below are analytical keys. Do not copy them directly as normal user-facing segment names. Localize at render time per `references/output_format.md` §7.

## 1. Game / MMO profile

| Segment key | Objective | Example actions | Core KPIs |
| --- | --- | --- | --- |
| `champions_elite` | Retain apex players; reinforce top-tier status | Dedicated 1:1 service; top-tier exclusive items; pre-launch content access; cross-server leaderboard / guild leader privilege | Top-decile retention; share of wallet; apex churn rate |
| `champions` | Retain high-value players and deepen engagement | VIP benefits; exclusive/high-value packs; early content/event access; dedicated service; guild/social privileges | Payer retention; ARPPU; high-value churn rate |
| `lost_high_value` | Reclaim historically valuable players efficiently | Targeted return pack; new-version/content message; return missions; high-touch CS outreach | Reactivation rate; reclaim revenue; reclaim ROI |
| `loyal_premium` | Push warm upper-mid payers toward `champions` | Premium bundles; progression boost; social/guild leadership role; personalized high-value offers | Upgrade rate to `champions`; repeat-pay rate; ARPPU uplift |
| `loyal` | Prevent warm high-value players from cooling further | Lifecycle reminder; personalized pack/content; social/guild re-engagement | Payer active rate; repeat-pay rate; 30-day payer retention |
| `potential` | Drive second/repeat payment and habit formation | First-pay follow-up; progression-based offers; personalized pay-point guidance | Second-pay rate; 7/14-day repeat pay; conversion |
| `promising` | Strengthen the weaker of F/M while preserving the stronger dimension | Targeted bundle; event participation; progression/content recommendation | F uplift; ARPPU uplift; event conversion |
| `hibernating` | Reactivate before full churn | Comeback content; return tasks; moderate incentives; social reconnect | Reactivation; D7 post-return retention |
| `at_risk` | Low-cost win-back or controlled suppression | Lightweight push; comeback campaign; incentive only when expected value supports it | Win-back rate; ROI; unsubscribe/negative feedback |

### MMO identity reminder

For role-heavy MMO projects:

- RFM subject = **real-player custom account field** when TE `#account_id` is a role ID.
- Operational delivery may still be personalized by role/server after player-level segmentation.

## 2. Social profile

For social apps (friend / chat / feed / party-group / gift / gacha / ad surfaces). User noun = `用户`.

| Segment key | Objective | Example actions | Core KPIs |
| --- | --- | --- | --- |
| `champions` | Retain high-value users and deepen social + paid engagement | VIP badge/privilege; high-value pack/limited cosmetic priority; party-group create/manage privilege; dedicated service | Payer retention; ARPPU; high-value churn rate |
| `lost_high_value` | Reclaim historically high-value users | Exclusive return pack/limited cosmetic; new-version/feed content outreach; high-touch 1:1 CS | Reactivation rate; reclaim revenue; reclaim ROI |
| `loyal` | Prevent warm high-value users from cooling | Lifecycle reminder (feed/friend interaction); personalized pack; party-group and friend re-engagement | Payer active rate; repeat-pay rate; 30-day payer retention |
| `potential` | Drive second/repeat payment and habit formation | First-pay follow-up pack; progression-style paid-point guidance (cosmetic/privilege/gift); personalized recommendation | Second-pay rate; 7/14-day repeat pay; conversion |
| `promising` | Strengthen the weaker of F/M dimension | Targeted pack/cosmetic; gacha/event participation guidance; feed content recommendation | F uplift; ARPPU uplift; event conversion |
| `hibernating` | Reactivate before full churn | Comeback tasks/sign-in; moderate incentive; social reconnect (friend recommendation / party-group recall) | Reactivation rate; D7 post-return retention |
| `at_risk` | Low-cost win-back or controlled suppression | Lightweight push/feed reminder; comeback campaign; incentive only when expected value supports it | Win-back rate; ROI; negative-feedback / unsubscribe rate |

## 3. E-commerce profile

| Segment key | Objective | Example actions | Core KPIs |
| --- | --- | --- | --- |
| `champions_elite` | Apex VIP retention | 1:1 personal shopper; first access to limited stock; top loyalty tier; referral rewards | Top-tier LTV; referral conversion; apex retention |
| `champions` | Retain and expand | VIP; early access; referral; cross-sell | Repeat rate; AOV; LTV |
| `lost_high_value` | Win back high-value customers | High-touch reclaim; tailored offer | Reactivation; reclaim ROI |
| `loyal_premium` | Upsell toward `champions` | Premium cross-sell; early access to sales; loyalty tier upgrade nudge | AOV uplift; tier-up rate |
| `loyal` | Maintain repeat behavior | Personalized recommendations; loyalty benefits | Repeat rate; retention |
| `potential` | Drive second purchase | Post-first-order nurture; relevant incentive | Second-order rate |
| `promising` | Increase the missing F or M dimension | Bundles; category expansion | F uplift; AOV uplift |
| `hibernating` | Reactivate | Content + moderate offer | Reactivation |
| `at_risk` | Efficient win-back | Low-cost reminder; targeted coupon | Win-back ROI |

## 4. SaaS / subscription profile

### Applicability rule

Map M → net subscription/payment value, F → payment/renewal cadence, only when transaction frequency meaningfully varies. When contract tier / renewal status is more actionable than raw F, use that.

### Typical operations

CSM outreach; renewal-risk review; feature-adoption nudges; expansion offers; downgrade/churn prevention.

### Typical KPIs

Renewal; expansion; NRR; product adoption.

## 5. Generic lifecycle direction

Use this table when an archetype lacks a dedicated per-segment fallback row. Optional extended cohorts inherit their parent direction.

| Segment key | Fallback direction |
| --- | --- |
| `champions_elite` | Retain / deepen; inherit from `champions` with higher service priority |
| `champions` | Retain / deepen |
| `lost_high_value` | Reclaim / win back |
| `loyal_premium` | Retain / upgrade; inherit from `loyal` |
| `loyal` | Retain / prevent cooling |
| `potential` | Develop / drive repeat conversion |
| `promising` | Develop the weaker F/M dimension |
| `hibernating` | Reactivate |
| `at_risk` | Efficient win-back / suppress when value is too low |

## 6. Generic strategy rule

For each segment provide:

| Component | Requirement |
| --- | --- |
| Business objective | Exactly one clear objective |
| Actions | 1–3 concrete actions |
| KPIs | 1–3 measurable KPIs |
| Guardrail | Cost, contact frequency, expected value, only when relevant |

**Do not**

- copy one archetype's vocabulary into another;
- copy English wording verbatim into user-facing output;
- name project features that the project's event metadata does not contain.

Localize the semantics at render time.
