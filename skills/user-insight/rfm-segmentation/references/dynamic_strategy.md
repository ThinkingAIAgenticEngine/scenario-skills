# Dynamic Operational Strategy Generation

> Canonical rule for Stage 7 `operational_strategy`. Produces the per-segment objective / actions / KPI table grounded in the **actual project**, not in a fixed industry template. Render-time localization follows `references/output_format.md` §2; this reference is locale-neutral.

## 1. Why dynamic

`references/strategy_profiles.md` is a fixed fallback library with four archetypes (game/MMO, e-commerce, SaaS, generic). It cannot cover every business. Forcing a social or hybrid project onto the game template leaks foreign vocabulary into the output. Dynamic generation reads the real project event/property metadata already gathered in Stage 1 and produces strategy text that matches the project's actual features, then localizes at render time to `output_locale`.

## 2. Inputs

| Input | Source | Already required by |
| --- | --- | --- |
| Project event list + descriptions | `ae-cli analysis-meta event list` (Stage 1) | Stage 1 transaction-caliber discovery |
| Payment event properties | `ae-cli analysis-meta event get` (Stage 1) | Stage 1 |
| Project type / name | `ae-cli project info list` (Stage 0) | Stage 0 |
| RFM segment results | Stage 5 output | Stage 5 |
| Segment medians / averages | Stage 5 aggregation | Stage 5 |

Do **not** call new metadata queries only for strategy text. Reuse what Stage 1 already collected. If event discovery was skipped (it must not be), stop and run Stage 1 first.

## 3. Procedure

### 3.1 Collect project feature signals

From the Stage 1 event list, record the feature surface actually present:

- **Monetization signals**: payment/order/recharge/purchase/cost events; virtual-currency properties (diamond, coin, gold, token); ad monetization (ads_show/ads_click/ads_end).
- **Social signals**: friend (add_friend/accept_friend/del_friend), chat (friend_chat/send_group_message), feed/content (send_feed/comment_feed/like_feed), group/party (create_party_group/enter_party_group/leave_party_group), gift (send_gift/receive_gift).
- **Gameplay / content signals**: match (start_match/match_end/match_success), round (join_game/game_end/game_quit), gacha (gacha_click/gacha_result/gacha_again), search (search_game).
- **Lifecycle signals**: register/login/ta_app_install/ta_app_start/ta_app_end/guide completion.
- **Custom**: any other materially present feature bucket.

### 3.2 Classify the project archetype from evidence

Pick the archetype by **feature evidence**, not by project name or `project_type`:

| Archetype | Evidence (any materially present) |
| --- | --- |
| `game_mmo` | match/round/gacha events + role/server fields + payment; OR user explicitly confirms MMO |
| `game_casual` | match/round/gacha events without MMO role structure |
| `social` | friend/chat/feed/group/gift events as the primary feature surface |
| `ecommerce` | cart/order/refund/sku/category events; payment tied to physical/virtual goods checkout |
| `saas_subscription` | subscription/renewal/contract events; payment is recurring billing |
| `hybrid` | two surfaces materially present (e.g. social + gacha + ads = social-game hybrid) |
| `other` | none of the above dominates |

Record the archetype and the 2–4 strongest feature signals used to pick it.

### 3.3 Resolve the project-appropriate vocabulary

Resolve vocabulary at render time to `output_locale`, using these archetype rules:

| Token class | Rule |
| --- | --- |
| User noun | The localized equivalent of `user` for social / e-commerce / SaaS / hybrid / other; the localized equivalent of `player` only for `game_mmo` / `game_casual` |
| Feature nouns | Pull from the project's real event descriptions in the output locale; do not import foreign nouns (guild/quest/cart/sku) from another archetype |
| Monetization noun | Match the payment event description actually returned by metadata (in-app purchase / payment / recharge / subscription / order) |
| Verbs | Use the project's real action verbs in the output locale (e.g. social: feed/friend/party-group/gift/gacha; ecommerce: repurchase/bundle/category; saas: renew/expand/adopt) |

### 3.4 Generate per-segment strategy

For each RFM segment produced in Stage 5, fill the four columns of the `operational_strategy` table (`segment | objective | recommended_actions | kpi`):

1. **objective** — exactly one clear business goal for that lifecycle state, using the project-appropriate user noun and the segment's R/F/M shape (e.g. champions → retain; at_risk → low-cost win-back; lost_high_value → reclaim).
2. **recommended_actions** — 1–3 concrete actions grounded in the project's real features identified in §3.1. Reference the actual feature surface (e.g. for social: party-group recall, friend recommendation, feed content outreach; for game: guild/level/gacha; for ecommerce: category/bundle/membership). Do not name features absent from the project.
3. **kpi** — 1–3 measurable KPIs appropriate to the archetype (retention / ARPPU / repeat-pay rate / reactivation rate / win-back ROI / NRR / AOV uplift / second-pay rate / etc.).

Rules:
- Segment display names must exactly match `segment_result` (Stage 7 §4.6).
- Exactly one row per displayed segment. Do not merge rows in the core strategy table.
- Keep each row concise.
- Never insert a feature the project does not have. If unsure, use a generic verb (e.g. content/activity/incentive) rather than a foreign one.

### 3.5 Guardrail against the fallback library

After generating the dynamic table, cross-check against `references/strategy_profiles.md`:

- Confirm that every produced segment has a strategy row in the dynamic output.
- When the selected archetype provides a per-segment fallback entry, compare the dynamic objective direction with that entry.
- When the archetype does **not** provide a per-segment entry (for example a generic SaaS guardrail or an optional extended split), use the generic lifecycle direction / parent-segment direction instead of treating the missing template row as an error.
- `champions_elite` inherits the retain/deepen direction of `champions`; `loyal_premium` inherits the retain/upgrade direction of `loyal` unless a project-specific strategy justifies a refinement.
- If dynamic generation is blocked (e.g. Stage 1 metadata is insufficient), fall back to the closest archetype/generic lifecycle guardrail and state the fallback explicitly in the quality note.

## 4. Audit record

Record in the run's caliber/quality context:

- `archetype`: the chosen archetype key.
- `feature_signals`: the 2–4 strongest feature buckets used.
- `strategy_source`: `dynamic` | `fallback` | `dynamic_with_fallback_check`.

## 5. Output schema

Dynamic generation does **not** change the output table schema. The `operational_strategy` table still uses exactly:

```text
segment | objective | recommended_actions | kpi
```

as defined in `assets/output_contract.yaml`. Only the cell content changes from fixed-template text to project-grounded, locale-localized text.
