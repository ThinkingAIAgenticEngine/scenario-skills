# Project Configuration

> **This file is the sole bridge between business concepts and database fields. When switching projects, only modify this file.**
>
> `{{event.xxx}}` and `{{prop.xxx}}` are business concept placeholders, **NOT** actual field names.
> The "Match keywords" column is used for fuzzy search in Step 00; the "Actual name" column holds the real field name after search confirmation.
> Leave uncertain values empty. Step 00 will assist discovery and confirmation.

---

## 1. Project Identity

| Concept | Value | Description | Example |
|---------|-------|-------------|---------|
| Project ID | [Fill in] | TE platform project ID | `196` |
| Timezone | [Fill in] | Analysis timezone, **obtain from `ae-cli project info get`, or confirm with the user** — do not hardcode | `8` (UTC+8) |
| Game name | [Fill in] | Used in report title | `Idle Card RPG` |
| Game type | [Fill in] | Card / RPG / SLG, etc. | `Idle Card` |

## 2. Inspection Time Window

| Concept | Value | Description | Example |
|---------|-------|-------------|---------|
| Inspection window days | `30` | Slow-variable trend tracking period | `30` |
| Start Date | [Fill in] | Format yyyy-MM-dd (auto = 30 days ago) | `2026-07-18` |
| End Date | [Fill in] | Format yyyy-MM-dd (auto = yesterday) | `2026-08-16` |

## 3. Event Name Mapping

> "Match keywords" are used for `analysis-meta event list` fuzzy search — provide several English variants to improve hit rate.

| Concept | Actual name | Distinguishing filter | Match keywords | Description |
|---------|-------------|-----------------------|----------------|-------------|
| `{{event.battle_start}}` | [Fill in] | — | battle_start, combat_start, fight_begin, pvp_start | Battle start (PVP/PVE) |
| `{{event.battle_result}}` | [Fill in] | — | battle_result, battle_end, combat_result, fight_result | Battle result (win/loss) |
| `{{event.currency_earn}}` | [Fill in] | — | currency_earn, currency_gain, gold_earn, item_gain, resource_obtain | Nurturing currency earned |
| `{{event.currency_consume}}` | [Fill in] | — | currency_consume, currency_spend, gold_consume, item_use, resource_consume | Nurturing currency consumed |
| `{{event.backpack_snapshot}}` | [Fill in] | — | backpack, bag, inventory, item_balance | Backpack/material holding snapshot |
| `{{event.shop_view}}` | [Fill in] | — | shop_view, shop_open, store_view, mall_view | Shop exposure |
| `{{event.purchase_complete}}` | [Fill in] | — | purchase, pay, buy, order, recharge | Purchase complete |
| `{{event.daily_login}}` | [Fill in] | — | login, app_launch, app_open, session_start, daily_login | Daily login / app launch |
| `{{event.equipment_recycle}}` | [Fill in] | — | equipment_recycle, equipment_salvage, gear_recycle, gear_salvage | Equipment recycled/salvaged |
| `{{event.equipment_first_use}}` | [Fill in] | — | equipment_first_use, equipment_equip, gear_first_equip, gear_use | Equipment first equipped or used |

### Event merge scenario (one event carries multiple semantics)

When one business event carries multiple semantics (e.g. `currency_flow` distinguishes earn/consume via a `flow_type` property), **multiple concepts map to the same event**, distinguished by the "Distinguishing filter":

| Concept | Actual name | Distinguishing filter | Match keywords |
|---------|-------------|-----------------------|----------------|
| `{{event.currency_earn}}` | currency_flow | `flow_type = earn` | currency_flow, currency_change |
| `{{event.currency_consume}}` | currency_flow | `flow_type = consume` | currency_flow, currency_change |

> **When querying, add the `distinguishing filter` to that event**: e.g. "earn" queries add `flow_type=earn`, "consume" queries add `flow_type=consume`. The Semantics in metric definitions (`../metric_definitions.md`) should be written accordingly as "some event + distinguishing filter".

## 4. Property Field Mapping

> "Match keywords" are used for `analysis-meta property list` fuzzy search. The "Distinguishing property" column holds the property used to distinguish semantics in event-merge scenarios (e.g. `flow_type`).

| Concept | Actual name | Parent event | Distinguishing property | Match keywords | Type |
|---------|-------------|--------------|-------------------------|----------------|------|
| `{{prop.hero_id}}` | [Fill in] | battle/nurturing events | No | hero_id, hero, character_id | string/number |
| `{{prop.hero_class}}` | [Fill in] | battle events | No | hero_class, hero_type, class, profession | string |
| `{{prop.consume_type}}` | [Fill in] | currency consume events | No | consume_type, use_type, spend_type, cost_type | string |
| `{{prop.currency_type}}` | [Fill in] | currency events | No | currency_type, currency_id, coin_type, item_type | string |
| `{{prop.consume_amount}}` | [Fill in] | currency consume events | No | amount, num, count, value | number |
| `{{prop.shop_category}}` | [Fill in] | shop exposure events | No | shop_category, shop_type, store_category | string |
| `{{prop.purchase_category}}` | [Fill in] | purchase complete events | No | purchase_category, pay_category, product_type, goods_type | string |
| `{{prop.equipment_instance_id}}` | [Fill in] | equipment recycle/first-use events | No | equipment_instance_id, gear_instance_id, item_instance_id, equipment_uid | string/number |
| `{{prop.was_used_before}}` | [Fill in] | equipment recycle events | No | was_used_before, ever_equipped, used_before, equipped_before | boolean |
| `{{prop.equipment_type}}` | [Fill in] | equipment recycle/first-use events | No | equipment_type, gear_type, item_type | string |
| `{{prop.equipment_tier}}` | [Fill in] | equipment recycle/first-use events | No | equipment_tier, gear_tier, equipment_rarity, quality | string/number |
| `{{prop.recycle_material_type}}` | [Fill in] | equipment recycle events | No | recycle_material_type, salvage_material_type, return_item_type | string |
| `{{prop.recycle_material_amount}}` | [Fill in] | equipment recycle events | No | recycle_material_amount, salvage_amount, return_item_amount | number |

## 5. Threshold Configuration

> Default values are methodology reference values — **MUST be confirmed or adjusted by the user in Step 01**, never applied blindly.

| Concept | Default | Description |
|---------|---------|-------------|
| `{{threshold.hhi_attention_slope}}` | `0.015` | HHI index attention slope (/week) |
| `{{threshold.hhi_alert_slope}}` | `0.025` | HHI index alert slope (/week) |
| `{{threshold.concentration_attention_slope}}` | `0.02` | Consumption concentration attention slope (/week) |
| `{{threshold.concentration_alert_slope}}` | `0.04` | Consumption concentration alert slope (/week) |
| `{{threshold.fragment_attention_slope}}` | `0.03` | Fragment accumulation attention slope (/week) |
| `{{threshold.fragment_alert_slope}}` | `0.05` | Fragment accumulation alert slope (/week) |
| `{{threshold.conversion_attention_drop}}` | `0.015` | Conversion rate attention drop (30 days) |
| `{{threshold.conversion_alert_drop}}` | `0.03` | Conversion rate alert drop (30 days) |
| `{{threshold.recycle_ratio_attention_slope}}` | [Fill in] | Equipment recycle-before-use ratio attention slope (/week); no universal default |
| `{{threshold.recycle_ratio_alert_slope}}` | [Fill in] | Equipment recycle-before-use ratio alert slope (/week); no universal default |

## 6. Output

| Concept | Value | Description |
|---------|-------|-------------|
| `{{workspace_dir}}` | `/tmp/game-economy-inspection/` | Intermediate file directory |
