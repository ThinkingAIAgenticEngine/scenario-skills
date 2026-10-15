# Indicator Calibers & Root-Cause Library (Universal Edition)

> This document carries two kinds of content pushed down from SKILL.md: ① the core metric caliber table (pinning numerator/denominator/event names); ② the high-frequency root-cause library (evidence-chain judgment).
> Event names / field names are all `{placeholder}` read from the product config. Judgment thresholds single-source from `references/judgment-parameters.md`.

---

## 1. Core Metric Calibers (confirm numerator/denominator/event names before analysis)

| # | Metric | Caliber (numerator/denominator) | Data source (event.property) | Status |
|---|------|------------------|----------------------|------|
| 1 | DAU | daily distinct active users | `{dau_event}` distinct `#user_id` | 🟢 |
| 2 | Live penetration (entry caliber) | daily `{enter_event}` distinct users ÷ DAU | `{enter_event}` | 🟢 |
| 3 | Live penetration (valid-watch caliber, optional) | daily `{enter_event}` with `{stay_duration_field} ≥ threshold` distinct users ÷ DAU | `{enter_event}` + `{stay_duration_field}` | 🟡 needs stay-duration field |
| 4 | Live exposure volume / exposed users | live card/entry exposure count, exposure distinct users | `{exposure_event}` (if configured) | 🟡 needs exposure event |
| 5 | Exposure → entry conversion (approx CTR) | exposure → `{enter_event}` conversion (most products: tap card = enter) | `{exposure_event}` + `{enter_event}` | 🟡 approx CTR; "tapped but not entered" intermediate state needs a click event |
| 6 | Entry rate | daily `{enter_event}` count (or distinct users) ÷ DAU | `{enter_event}` (split by `{enter_source_field}`) | 🟢 |
| 7 | Live-room entry distribution | each entry's distinct entering users, share, and day-over-day | `{enter_event}.{enter_source_field}` | 🟢 |
| 8 | Quick-exit rate (short-stay share) | `{stay_duration_field} < threshold` count ÷ entry count | `{stay_duration_field}` | 🟡 needs stay-duration field |
| 9 | Avg watch time per user | Σ`{stay_duration_field}` ÷ watch users | `{stay_duration_field}` | 🟡 |
| 10 | Live watch retention (T+1/T+3) | first-day watch users re-`{enter_event}` after N days ratio | `{enter_event}` by date | 🟢 |
| 11 | Online room count | concurrent rooms with `{live_start_event}` not yet `{live_end_event}` | `{live_start_event}`/`{live_end_event}` | 🟢 (approx) |
| 12 | Prime-time streaming room count | 20:00–23:59 distinct streaming rooms | `{live_start_event}` | 🟢 |
| 13 | Active streamer count | daily distinct users with `{live_start_event}` | `{live_start_event}` | 🟢 |
| 14 | New streamer count | daily first-time `{live_start_event}` streamers | `{live_start_event}` | 🟢 |
| 15 | Room interaction rate | entry count with comment/gift/mic/emotion etc. interaction ÷ total entry count | interaction events (per product config) | 🟢 |
| 16 | Valid-streaming-duration share | `{live_end_event}.{live_duration_field} ≥ threshold` streams ÷ streams | `{live_end_event}.{live_duration_field}` | 🟡 |
| 17 | Streamer daily streaming rate | daily streaming streamers ÷ total streamers (`{host_field}=true`) | `{live_start_event}` + user property | 🟢 |

**Caliber verification convergence action**: before each analysis, re-verify #1–#3's numerator/denominator definitions and whether `{enter_source_field}` enum changed (product release or tracking-doc update), then proceed to the next layer.

---

## 2. Dimension Breakdown Fields (from product config)

| Dimension | Numerator split field | Denominator split field | Note |
|------|-------------|-------------|------|
| OS | `#os` GROUP BY | `#os` GROUP BY | watch cross-event case inconsistency; `LOWER()` normalize if needed |
| New/old user | join user table `{new_user_field}` | join user table `{new_user_field}` | new user = registration day (`{new_user_field} = $part_date`), not "registered within N days" |
| Organic/paid | event model `{organic_field}` GROUP BY | event model `{organic_field}` GROUP BY | virtual property, SQL model cannot query |
| Channel | event model `{channel_field}` GROUP BY | event model `{channel_field}` GROUP BY | virtual property |
| App version | `#app_version` GROUP BY | `#app_version` GROUP BY | **GROUP BY original value (x.x.xx three-segment); do NOT SUBSTR-truncate / aggregate major version** |
| Country/region | join user table `{locale_field}` | join user table `{locale_field}` | |
| Entry source - primary | `{enter_source_field}` GROUP BY | — (DAU has no such property; use aggregate DAU as denominator) | null-rate check + non-null part entry distribution |
| Entry source - second | `{enter_source_vp}` (event model GROUP BY) | — (DAU has no such property; use aggregate DAU as denominator) | virtual property, SQL model cannot query |

**Entry-source dimension penetration uses aggregate DAU as denominator**: entry source is an event-level property (which entry the user entered from); the DAU event has no such property, so DAU cannot be split by entry source. Therefore entry-source dimension only splits numerator UV; penetration = each source's UV / aggregate DAU.

---

## 3. Funnel Breakdown (exposure → entry → stay → interaction)

**Computable segments (exposure → entry → stay → interaction):**

```
DAU ──exposure→entry──▶ enter room ──quick-exit──▶ valid watch ──interaction──▶ retention
 🟢      🟢          🟢              🟢           🟢
{dau_event}   {enter_event}    {stay_duration_field}  interaction events
+ {exposure_event}  (enter_source_field)
```

- Entry rate: `{enter_event}` ÷ DAU, split by `{enter_source_field}`, find entry-level differences
- Entry-level breakdown: each entry's volume share & day-over-day, each entry's quick-exit rate / avg time comparison → locate "which entry is dropping"
- Quick-exit rate: `{stay_duration_field} < threshold` share; if rising → "content/matching" problem, not "reach" problem
- Avg watch time / interaction rate / next-day retention: same calibers as the table above

**Exposure segment (if exposure event configured):**

```
Live exposure ──exposure→entry conversion──▶ enter room
   🟢            🟡
{exposure_event}   {enter_event} as click action
```

- Exposure volume: `{exposure_event}`, split by `scene`/`position`/`{enter_source_field}` for exposure distribution & share
- CTR caliber: most live products "tap card = enter", approximate CTR with "exposure → `{enter_event}`" conversion; if a "tapped but not entered" intermediate state exists, add a click event
- **`{enter_source_field}` boundary**: it records "which entry the user entered live from" (🟢); combined with exposure event it can compute "entry-level exposure → entry conversion"; `{enter_source_field}` alone cannot compute exposure volume

**Output**: bottleneck = insufficient reach (exposure↓ / exposure→entry conversion↓ / entry volume↓) or poor retention (quick-exit↑ / time↓ / interaction↓), or both.

---

## 4. Supply-Side Breakdown (core for live products)

| Metric group | Metric | Data source |
|--------|------|---------|
| Supply quantity | online room count, prime-time streaming room count, active streamer count, new streamer count | `{live_start_event}`/`{live_end_event}` aggregation |
| Supply quality | per-room avg stay (aggregate `{stay_duration_field}` by room id), room interaction rate, valid-streaming-duration share | `{stay_duration_field}` + interaction events + `{live_end_event}` |
| Streamer behavior | streamer daily streaming rate, re-stream rate (stream again next day ratio), avg streaming time per streamer | `{live_start_event}`/`{live_end_event}` per streamer |
| Supply-demand linkage | daily "online rooms / prime-time streaming count" vs "watch penetration" correlation (≥14 days) | cross comparison |

**Judgment**: supply down AND penetration down in sync, entry rate unchanged → supply shrinking holds; supply not down but interaction rate / stay time down → supply-quality problem.

---

## 5. Environment-Layer Breakdown (distinguish "quantifiable" vs "needs external info")

| Dimension | Quantifiable part | Needs external info |
|------|-----------|---------------|
| Product side | exposure volume & entry-level volume distribution both computable (`{exposure_event}` + `{enter_event}.{enter_source_field}`, 🟢) | recommendation-feed distribution volume / algorithm-weight changes need product schedule records (🟡) |
| Ops side | event-participation events show user-side participation (🟢) | event up/down timeline, incentive policy need ops calendar (🟡 external) |
| Scenario substitution | live/voice-room time computable (🟢) | other scenarios (DM/feed) without time events 🔴, need `page_duration` or switch to event-frequency share |
| External side | `{channel_field}` × `{new_user_field}` × profile fields (🟢) | aggregate active structure from `{dau_event}` structure |

---

## 6. Root-Cause Verification Methods

| Method | Action | Data source |
|------|---------|------|
| Group comparison | version (`#app_version`), channel (`{channel_field}`) group penetration comparison; gray-release experiments need `is_gray` public property | event table |
| Cohort | group by `{new_user_field}` week/month, view each cohort's "live-watch penetration N weeks after registration" curve | `{new_user_field}` + `{enter_event}` |
| Metric correlation | supply, entry rate, stay time vs penetration correlation (≥14 days daily data) | cross computation |

---

## 7. High-Frequency Root-Cause Library (evidence-chain judgment; all must hit to judge)

> **Judgment discipline (MUST, HARD RULE #18)**: before concluding a root cause, you MUST hit all indicators in the "evidence combination" below (none missing). Judging "supply shrinking" from just "online room count dropped" = violation.

| Root cause | Evidence combination (none missing) | Computable |
|------|---------------------------|--------|
| 1. Supply shrinking | online rooms↓ + prime-time streaming↓ + active streamers↓ + penetration↓ in sync + **entry rate unchanged** | 🟢 |
| 2. Product-traffic downgrade | entry exposure↓ (`{exposure_event}` 🟢) + entry-level volume distribution change (`{enter_source_field}`: some entry↓ or all↓) + exposure→entry conversion unchanged + supply unchanged | 🟢 (feed distribution / algorithm weight need product schedule info) |
| 3. User-structure change | new-user penetration < old-user + new-user share↑ + aggregate dragged down | 🟢 |
| 4. Scenario substitution | live/voice-room time share↓ + other-scenario time/frequency share↑ + total active time unchanged | 🟡 needs other-scenario time |
| 5. Algorithm-match failure | exposure→entry conversion↓ + exposure unchanged + supply quality unchanged | 🟡 approx CTR; strict CTR needs click event |
| 6. Policy-control impact | valid streaming↓ + streamer streaming rate↓ + incentive-policy timeline match (ops calendar) | 🟡 needs ops info |

> **Root-cause confidence labeling (MUST, see `references/judgment-parameters.md` §2.2)**: after the evidence chain establishes a root cause, also label the confidence level — High (evidence all significantly over threshold + supporting groups High confidence) / Medium (borderline hit or supporting groups Medium) / Low (alternative explanation not ruled out). Confidence labeling does not replace evidence-chain judgment; it is the second step of "how hard". Display format: `supply shrinking [High] + algorithm match failure [Medium]`.

**Conclusion template (fixed four segments)**: decline facts (numbers + start) → bottleneck segment (which funnel stage) → dominant root cause (evidence-chain hit + confidence label) → recommended action (validation experiment / ops action).
