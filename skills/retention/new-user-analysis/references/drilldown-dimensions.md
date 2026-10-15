---
title: "New User Drill-Down Dimensions"
summary: "Phase 5 optional drill-downs: organic/paid quality, geo Top10, channel attribution ranking + field placeholders + channel merge rules + tiered anomaly thresholds + data validation gates"
---

# Drill-Down Dimensions (Phase 5 Expansion)

Version: 1.0.0
Companion to: SKILL.md §1 Phase 5 "Optional Drill-Down Dimensions", `root-cause-rules.md`, `industry-benchmarks.md` §8.

> **Core principle**: the three drill-downs below are **optional extensions** of Phase 5. Trigger condition = the main diagnosis surfaced a mutation in some dimension, OR the user explicitly asked to decompose. All field names are **parameterized placeholders** — confirm the actual field with the user at runtime (same style as the Phase 1 caliber confirmation). Never hardcode any customer-specific field name.

---

## 0. Field Placeholder Conventions (confirm first, then query)

Before querying each dimension, confirm the actual field name with the user. Common variants for reference:

| Placeholder | Meaning | Common field-name variants |
|-------------|---------|---------------------------|
| `{traffic_source}` | Organic/paid flag (user property) | `#vp@total_is_organic` / `is_organic` / `media_source` / `traffic_type` |
| `{region}` | Country/region (user property or event property) | `locale` / `#vp@country` / `country` / `region` |
| `{channel}` | Paid attribution channel (user property) | `#vp@attribution_channel` / `attribution_channel` / `channel` / `utm_source` |
| `{channel_market}` | Register-market channel (rarely used; do NOT confuse with attribution channel) | `#vp@register_info_market_channel` / `register_channel` |

**Key pitfalls**:
- `{traffic_source}` values may include natural markers like `organic` / `自然量`, which are NOT paid channels — strip them out before computing paid volume.
- `{region}` may exist in BOTH a user-property and an event-property form. Use the event property to distinguish domestic/overseas; use the user property to break out "specific country Top10". Confirm `table_type` and `prop_type` via `ae-cli analysis-meta property list` before querying.
- When mixing group/filter, one dimension being `user_property` and another `event_property` is allowed — write them by their actual type.

---

## 1. Organic vs Paid Quality

**Purpose**: quantify the quality gap between the organic-acquisition cohort and the paid-acquisition cohort, to judge whether buy-volume ROI is healthy and whether organic volume is polluted by fraud/incentivized traffic.

### 1.1 Organic/Paid Split Caliber

- `{traffic_source}` values are typically three classes: `paid` (= ad-bought volume), `organicA`, `organicB`.
- **Organic = organicA + organicB**; paid = `paid`.
- Three-line aggregation (report-3 style): `paid new users` / `domestic organic` / `overseas organic` (domestic/overseas split by `{region}`; domestic organic = A+B of CN, overseas organic = A+B of non-CN).

### 1.2 Query

```bash
ae-cli analysis adhoc run --model-type event --project-id {pid} \
  --definition '{
    "time_range": {"mode":"custom","start_time":"...","end_time":"..."},
    "time_particle_size": "month",
    "metrics": [{"event":"{caliber_event}","aggregation":"user_count"}],
    "groups": [{"field":{"name":"{traffic_source}","type":"user_property"}}]
  }'
```

### 1.3 Quality Comparison Method

For the organic cohort and the paid cohort separately, compute the Phase 2 four-dimension quality score (D1 retention, session, feature adoption, monetization readiness), and produce a gap table:

| Metric | Paid new users | Organic | Gap |
|--------|----------------|---------|-----|
| D1 retention | {x}% | {y}% | paid - organic = {z}pp |
| Daily sessions | ... | ... | ... |

**Judgment**:
- Organic D1 retention 20-40% higher than paid is normal (organic users have stronger intent).
- Organic quality score **abnormally high** (e.g. D1 retention >80% with very few sessions) → suspected fraud/incentivized traffic, verify.
- Paid quality score drops sharply → buy-volume channel quality declined; go back to `root-cause-rules.md` Rule 1 (channel mix).

---

## 2. Geo Top10 MoM (Geo Segment Deep-Dive)

**Purpose**: identify which country/region is driving new-user growth or shrinkage.

### 2.1 Query

```bash
# Monthly registration count per country, Top10
ae-cli analysis adhoc run --model-type event --project-id {pid} \
  --definition '{
    "time_range": {"mode":"custom","start_time":"...","end_time":"..."},
    "time_particle_size": "month",
    "metrics": [{"event":"{caliber_event}","aggregation":"user_count"}],
    "groups": [{"field":{"name":"{region}","type":"user_property"}}]
  }'
```

### 2.2 Analysis Points

- Take Top10 countries, compute share + MoM.
- **Share denominator = current-period total registrations** (NOT the sum of the region dictionary, because region contains `(null)` empty values).
- Tier labels: MoM >+10% mark "highlight"; <-10% mark "watch"; organic MoM >50% mark "⚠ suspicious, verify quality".
- Top10 set is ranked by **all-period cumulative**, not a single month.

---

## 3. Channel Attribution Quality Ranking (Channel Quality Deep-Dive)

**Purpose**: quality ranking of paid attribution channels, to identify channels to "scale up / scale down / retire".

### 3.1 Query

```bash
ae-cli analysis adhoc run --model-type event --project-id {pid} \
  --definition '{
    "time_range": {"mode":"custom","start_time":"...","end_time":"..."},
    "time_particle_size": "month",
    "metrics": [{"event":"{caliber_event}","aggregation":"user_count"}],
    "groups": [
      {"field":{"name":"{channel}","type":"user_property"}},
      {"field":{"name":"{region}","type":"event_property"}}
    ]
  }'
```

### 3.2 Channel Merge Rules (template, configure per customer channel ecosystem)

`{channel}` raw values are often hundreds, with a long tail. Fix the merge rules into a script to avoid rewriting on the spot:

- **Synonym merge**: e.g. `Apple Search Ads` and `ASA` merge into `ASA` (and split domestic/overseas).
- **Keyword merge**: merge by keyword containment (e.g. Xiaomi/OPPO/vivo/Huawei/Honor → domestic Android OEMs; Google/Facebook/TikTok → overseas ad platforms).
- **Default attribution**: Android OEM channels default to domestic; Google/Facebook/TikTok default to overseas (adjustable per actual placement regions).
- Domestic/overseas **unified ranking** (by paid volume), not split by region.

### 3.3 Judgment

- Single channel MoM >100% (paid volume doubled) → mark "⚠ verify attribution".
- Single channel MoM <-50% → placement shrunk; check whether it was deliberately paused (campaign calendar).
- Long-tail channels (share <1%) are not analyzed one by one; fold into "Other".

---

## 4. Tiered Anomaly Thresholds (replaces a single >15% threshold)

A lespark-style unified tiering, finer than a single threshold. Coexists with the mutation thresholds in `industry-benchmarks.md` §8 — §8 decides "whether a mutation fires"; this table decides "post-fire tiering + report label".

| MoM magnitude | Tier | Label / action |
|---------------|------|----------------|
| +10% ~ -10% | Normal fluctuation | No label |
| >+10% | Highlight | Mark "highlight", check placement/activity |
| <-10% | Watch | Mark "watch", check whether deliberately shrunk |
| >50% (organic) | Suspicious anomaly | ⚠ Verify quality (suspected fraud/incentivized) |
| >100% (paid) | Verify attribution | ⚠ Verify attribution (suspected attribution mismatch) |

---

## 5. Data Validation Gate (run before any output)

Before producing the report from the main diagnosis + any drill-down, run these checks; any failure → re-check:

1. **Trend-tail alignment**: the last two periods of the trend chart must exactly match the MoM table (same-source query, values must be identical).
2. **Split-sum reconciliation**: organic + paid = total; three lines (paid + domestic organic + overseas organic) = total; channel Top sum ≈ total (long-tail "Other" fills the gap).
3. **Share-denominator sanity**: the region Top10 share sum should fall in a reasonable range (e.g. 60%-90%); too low means the denominator used the region-dictionary sum (with nulls), too high means the long tail was missed.
4. **No hardcoded column names**: read column names from the result schema and index by position; do not assume columns are named "time" / "register". Column names differ across customers (Chinese/English/Japanese).

---

## 6. Relationship to the Main Framework

| Position | Content |
|----------|---------|
| Main diagnosis (Phase 5 Step 2) | 6 mutation detection methods, the trigger condition for drill-downs |
| Drill-down (after Phase 5 Step 3, optional) | This file §1-3 three-dimension decomposition |
| Tiering | This file §4 tiered thresholds |
| Gate | This file §5 validation |

Drill-downs are not run every time — only enter them when the main diagnosis surfaced a mutation, or the user explicitly asked to decompose. Avoid dragging all three drill-downs into every report, which bloats output.
