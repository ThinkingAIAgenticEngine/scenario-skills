# Inspection Metric Definitions

> This document is the core of game-economy-inspection — **all metrics use the six-element template; a metric IS a mathematical formula, not bound to any tool.**
> See `adapters/ae-cli.md` for tool invocation (loaded only when ae-cli is present).

---

## Table of Contents

### Combat Domain
1. [PVP Appearance Rate HHI Index](#1-pvp-appearance-rate-hhi-index)
2. [Class Appearance Rate Distribution](#2-class-appearance-rate-distribution)
3. [Class Win Rate Gap](#3-class-win-rate-gap)

### Economy Domain
4. [Nurturing Currency Earn/Consume Ratio](#4-nurturing-currency-earnconsume-ratio)
5. [Nurturing Currency Consumption Concentration](#5-nurturing-currency-consumption-concentration)
6. [Average Nurtured Heroes per Player](#6-average-nurtured-heroes-per-player)

### Backpack Domain
7. [Nurturing Material Holding Change Rate](#7-nurturing-material-holding-change-rate)
8. [Cold Hero Fragment Accumulation Rate](#8-cold-hero-fragment-accumulation-rate)

### Monetization Domain
9. [Nurturing Bundle Conversion Rate](#9-nurturing-bundle-conversion-rate)
10. [Nurturing Category Revenue Share Change](#10-nurturing-category-revenue-share-change)

### Equipment Domain
11. [Equipment Recycle-before-use Ratio](#11-equipment-recycle-before-use-ratio)

---

## Combat Domain

### 1. PVP Appearance Rate HHI Index

- **Intent**: Detect whether PVP lineup diversity is narrowing (hero meta solidifying)
- **Semantics**: HHI = Σ(per-hero appearance share)², range 0~1, higher = more concentrated. Appearance share = that hero's `{{event.battle_start}}` count / total `{{event.battle_start}}` count across all heroes
- **Input**: `{{event.battle_start}}`, grouped by `{{prop.hero_id}}`, window `{{window.start}}`–`{{window.end}}`
- **Dimension**: aggregate weekly
- **Judgment**: HHI < 0.25 normal (≥4 mainstream choices); 30-day slope > `{{threshold.hhi_attention_slope}}` attention; > `{{threshold.hhi_alert_slope}}` warning
- **Output**: 30-day HHI trend series + slope + verdict

### 2. Class Appearance Rate Distribution

- **Intent**: Detect whether a single class monopolizes PVP
- **Semantics**: Class appearance share = that class's hero `{{event.battle_start}}` count / total `{{event.battle_start}}` count
- **Input**: `{{event.battle_start}}`, grouped by `{{prop.hero_class}}`
- **Dimension**: aggregate weekly
- **Judgment**: Top class share < 35% normal; single class 30-day gain > 8 percentage points attention
- **Output**: weekly per-class appearance share trend table

### 3. Class Win Rate Gap

- **Intent**: Detect whether class strength imbalance is widening
- **Semantics**: Class win rate = that class's `{{event.battle_result}}`(win) / that class's `{{event.battle_result}}`(total). Win rate gap = highest-win-rate class − lowest-win-rate class
- **Input**: `{{event.battle_result}}`, grouped by `{{prop.hero_class}}`
- **Dimension**: aggregate weekly
- **Judgment**: Gap < 10% normal; 30-day gap widening > 5% attention
- **Output**: weekly per-class win rate + gap trend

---

## Economy Domain

### 4. Nurturing Currency Earn/Consume Ratio

- **Intent**: Detect the balance between currency supply and consumption
- **Semantics**: Earn/consume ratio = Σ`{{event.currency_earn}}`(amount) / Σ`{{event.currency_consume}}`(amount)
- **Input**: `{{event.currency_earn}}`, `{{event.currency_consume}}`, property `{{prop.consume_amount}}`
- **Dimension**: aggregate weekly
- **Judgment**: 0.90~1.10 normal. **Note**: normal ratio ≠ healthy economy — MUST be read together with §5 consumption concentration
- **Output**: 30-day earn/consume ratio trend

### 5. Nurturing Currency Consumption Concentration (Top 5 paths share)

- **Intent**: Detect whether consumption outlets are narrowing (consumption concentrated on very few nurturing paths)
- **Semantics**: Top 5 share = sum of consumption of the 5 largest paths (hero × nurturing type) / total consumption
- **Input**: `{{event.currency_consume}}`, grouped by `{{prop.hero_id}}` × `{{prop.consume_type}}`, aggregate `{{prop.consume_amount}}`
- **Dimension**: aggregate weekly
- **Judgment**: Top 5 < 50% normal; 30-day slope > `{{threshold.concentration_attention_slope}}` attention; > `{{threshold.concentration_alert_slope}}` warning
- **Output**: 30-day Top 5 consumption share trend + detailed distribution

### 6. Average Nurtured Heroes per Player

- **Intent**: Detect the breadth of player nurturing behavior (whether players nurture only a few heroes)
- **Semantics**: Average nurtured heroes = distinct nurtured heroes / distinct players
- **Input**: `{{event.currency_consume}}`, deduplicated by `{{prop.hero_id}}`
- **Dimension**: aggregate weekly
- **Judgment**: ≥ 3.5 normal; 30-day drop > 0.5 attention
- **Output**: 30-day average nurtured heroes trend

---

## Backpack Domain

### 7. Nurturing Material Holding Change Rate

- **Intent**: Detect accumulation or depletion of currency/materials in the backpack
- **Semantics**: Holding = average `{{event.backpack_snapshot}}` material quantity per player. Change rate = (current − 30 days ago) / 30 days ago
- **Input**: `{{event.backpack_snapshot}}`, property `{{prop.currency_type}}`
- **Dimension**: aggregate weekly
- **Judgment**: 30-day cumulative change within ±20% normal; gain > 20% accumulation (devaluation signal); drop > 20% depletion
- **Output**: 30-day holding trend + change rate

### 8. Cold Hero Fragment Accumulation Rate

- **Intent**: Detect cold-hero materials piling up due to "nobody nurturing them"
- **Semantics**: Cold fragment holding = average fragment holding of bottom-50%-appearance-rate heroes. Accumulation rate = week-over-week growth rate
- **Input**: `{{event.backpack_snapshot}}`, tiered by `{{prop.hero_id}}` (bottom 50% by appearance rate)
- **Dimension**: aggregate weekly
- **Judgment**: 30-day slope > `{{threshold.fragment_attention_slope}}` attention; > `{{threshold.fragment_alert_slope}}` warning
- **Output**: 30-day cold fragment holding trend + accumulation rate

---

## Monetization Domain

### 9. Nurturing Bundle Conversion Rate

- **Intent**: Detect changes in nurturing-category payment attractiveness
- **Semantics**: Conversion rate = `{{event.purchase_complete}}`(nurturing bundle) / `{{event.shop_view}}`(nurturing category)
- **Input**: `{{event.shop_view}}`, `{{event.purchase_complete}}`, property `{{prop.shop_category}}`/`{{prop.purchase_category}}` = nurturing
- **Dimension**: aggregate weekly
- **Judgment**: Conversion rate ≥ 5% normal; 30-day drop > `{{threshold.conversion_attention_drop}}` attention; > `{{threshold.conversion_alert_drop}}` warning
- **Output**: 30-day conversion rate trend (funnel: exposure→click→purchase)

### 10. Nurturing Category Revenue Share Change

- **Intent**: Detect changes in the share of nurturing revenue within total payment structure
- **Semantics**: Nurturing revenue share = nurturing-category `{{event.purchase_complete}}` amount / all `{{event.purchase_complete}}` amount
- **Input**: `{{event.purchase_complete}}`, grouped by `{{prop.purchase_category}}`
- **Dimension**: aggregate weekly
- **Judgment**: Category share stable (fluctuation within ±3%) normal; 30-day drop > 5 percentage points attention
- **Output**: 30-day nurturing revenue share trend + payment structure table

---

## Equipment Domain

### 11. Equipment Recycle-before-use Ratio

- **Intent**: Detect whether newly handled equipment is increasingly recycled before it creates gameplay value, rather than being equipped or otherwise used first
- **Semantics**: For each week, classify every `{{prop.equipment_instance_id}}` once by its first disposition. `recycle_before_use` = distinct instances in `{{event.equipment_recycle}}` where `{{prop.was_used_before}} = false`; `first_use` = distinct instances in `{{event.equipment_first_use}}`. Recycle-before-use ratio = `recycle_before_use / (recycle_before_use + first_use)`. The two sets MUST be mutually exclusive. If the project has no reliable lifecycle flag or validated sequence logic, mark the metric "Data Missing"; never substitute raw recycle event count.
- **Input**: `{{event.equipment_recycle}}`, `{{event.equipment_first_use}}`, required `{{prop.equipment_instance_id}}` and `{{prop.was_used_before}}`; optional breakdowns by `{{prop.equipment_type}}`, `{{prop.equipment_tier}}`, `{{prop.recycle_material_type}}`, and `{{prop.recycle_material_amount}}`
- **Dimension**: aggregate weekly; deduplicate by equipment instance before calculating the ratio
- **Judgment**: Compare the 30-day slope with user-confirmed `{{threshold.recycle_ratio_attention_slope}}` and `{{threshold.recycle_ratio_alert_slope}}`. There is no universal default: Step 01 MUST obtain project-specific values before this scenario runs. A warning requires the ratio signal plus at least one echo from §7 material holding or §4 earn/consume ratio.
- **Output**: 30-day recycle-before-use ratio trend + slope + recycle material/type breakdown + cross-domain echo status

---

> **Usage**: step files reference metric IDs (e.g. "Execute §1"). The agent chooses tools itself; tool invocation is defined only in the adapter layer.
