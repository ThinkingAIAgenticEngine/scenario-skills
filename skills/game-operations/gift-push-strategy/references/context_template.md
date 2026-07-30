# Project Context

<!-- Memory mechanism: Record current project game information and user configuration preferences -->

## Current Project

| Field | Value | Update Time |
|-------|-------|-------------|
| Game Name | {{game_name}} | {{timestamp}} |
| Game Genre | {{SLG/MMORPG/...}} | {{timestamp}} |
| TE Project ID | {{projectId}} | {{timestamp}} |

## Lifecycle Configuration

| Field | Value | Update Time |
|-------|-------|-------------|
| Server Age Range | {{1-N days}} | {{timestamp}} |
| Lifecycle Phase Count | {{N phases}} | {{timestamp}} |
| Grouping Rule | Default 90 days per phase, maximum 180 days / Custom | {{timestamp}} |

### Lifecycle Phase Details

| Phase | Day Range |
|-------|-----------|
| New Server Phase | 1-30 days |
| Growth Phase I | 31-120 days |
| ... | ... |

> **Detailed rules see `references/_common.md` Server Age Phase section**

## Confirmed Progression Systems

<!-- User confirmed progression system list -->

### Core Progression

- {{progression_system_1}}
- {{progression_system_2}}

### Advanced Progression

- {{progression_system_3}}
- {{progression_system_4}}

## Confirmed Gameplay Classification

<!-- User confirmed gameplay classification list -->

### PVE Gameplay

- {{gameplay_1}}
- {{gameplay_2}}

### PVP Gameplay

- {{gameplay_3}}
- {{gameplay_4}}

### Real-time Battle Gameplay (No In-match Push)

> If has real-time battle gameplay, record here, only push out-of-match

- {{real_time_gameplay_1}}

## Gameplay Output/Associated Gift Pack Information

<!-- User provided gameplay output/associated gift pack information, priority over template defaults -->

| Gameplay | Output/Associated Gift Pack | Source |
|----------|------------------------------|--------|
| {{gameplay_1}} | {{gift_pack_type}} | User specified/Template default |
| {{gameplay_2}} | {{gift_pack_type}} | User specified/Template default |

## User Tiering Configuration

> **Detailed rules see `references/_common.md` User Tiering Rules section**

**Current configuration**: {{High/Mid/Low Spender 3 tiers / Custom tiering}}

| Tier | Classification Rule | Default Push Gift Pack |
|------|---------------------|------------------------|
| High Spender | Max single payment in past 14 days >= 328 RMB | 328 RMB gift pack |
| Mid Spender | Max single payment in past 14 days 98-328 RMB | 98 RMB gift pack |
| Low Spender | Max single payment in past 14 days < 98 RMB | 30 RMB gift pack |

### User Custom Tiering (If any)

| Tier | Classification Rule | Default Push Gift Pack |
|------|---------------------|------------------------|
| {{custom_tier}} | {{custom_rule}} | {{custom_gift_pack}} |

## Scenario Tiering Configuration

> **Detailed rules see `references/_common.md` Scenario Tiering Rules section**

**Core principle**: Node trigger scenario no tiering, other scenarios tiered push

| Scenario Type | Current Tiering Strategy |
|---------------|--------------------------|
| Node Trigger | No tiering (All users same gift pack) |
| Material Shortage | Tiered |
| Item Consumption | Tiered |
| Stamina Consumption | Tiered |
| Battle Loss | Tiered |
| Failure Trigger | Tiered |

## Cartesian Product Configuration

| Dimension | Current Selection | Available Options |
|-----------|-------------------|-------------------|
| Lifecycle | {{selected_phase}} | All/Filter |
| User Tier | {{selected_tier}} | High/Mid/Low Spender/All |
| Progression Line | {{selected_progression}} | {{available_progression_list}} |
| Scenario Type | {{selected_scenario}} | Node Trigger/Material Shortage/Item Consumption/Failure Trigger/Stamina Consumption/Battle Loss |

## Gift Pack Configuration Preferences

> **Detailed rules see `references/_common.md` Gift Pack Configuration Rules section**

- Trigger channel: Server-side (default) / Client-side
- Price tier source: TE system pull / User specified
- Value ratio rule: Within same phase higher price lower value ratio; Across phases increment 5%-10%
- Display duration rule: Higher value ratio shorter display duration (2-24 hours)
- Strategy effective period: 1 year

## Filter Condition Record

<!-- User most recent filter conditions -->

- Lifecycle filter: {{condition}}
- User tier filter: {{condition}}
- Progression line filter: {{condition}}
- Scenario type filter: {{condition}}

---

*User can input "forget" to clear all content, or "forget {field}" to clear specified field*
*Supported clearable fields: Game type, Lifecycle, Progression systems, Gameplay, Tiering rules, Filter conditions*

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.