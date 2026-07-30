# {{game_name}} Refined Push Strategy Plan

<!--
Data filling instructions:
1. {{game_name}}: Get from .gift-push-context.md or user input
2. {{timestamp}}: Document generation datetime, format YYYY-MM-DD HH:mm:ss
3. {{game_platform/server}}: Get from user input or context
4. {{SLG/MMORPG...}}: Confirmed game genre
5. {{progression_strategy_data}}: Fill line by line in following format
   | Strategy Name | Progression Line | Lifecycle | User Tier | Trigger Scenario | Scenario Type | Trigger Channel | Gift Pack ID | Recommended Gift Pack | Price Tier | Value Ratio | Display Duration |
   |---------------|------------------|-----------|-----------|------------------|---------------|-----------------|--------------|----------------------|------------|-------------|------------------|
   | Hero_New Server_Star Node | Hero | New Server Phase | All | Hero star upgrade to 3 stars | Node Trigger | Server-side | To be created | Hero experience gift pack | 98 | 130%-140% | 8 hours |
   | Hero_New Server_High Spender_Material Shortage | Hero | New Server Phase | High Spender | Hero star upgrade materials shortage | Material Shortage | Server-side | To be created | Hero materials gift pack | 328 | 110%-120% | 15 hours |
   Note: Node trigger scenario no tiering (User Tier="All"), other scenarios tiered push
6. {{gameplay_strategy_data}}: Same format above, strategy name format "Gameplay_Lifecycle_Tier_Trigger Scenario"
7. Combination count verification: Calculation formula = Sum(Phase count x Tier count x Progression line scenario count x Associated gift pack type count)
-->

**Generation Time**: {{timestamp}}
**Applicable Range**: {{game_platform/server}}
**Version**: v1.0

---

## Revision History

| Version | Date | Modification Content |
|---------|------|----------------------|
| v1.0 | {{date}} | Initial generation |

---

## I. Game Basic Information

| Item | Content |
|------|---------|
| Game Type | {{SLG/MMORPG...}} |
| Online Duration | {{X months}} |
| Server Age Range | {{1-N days}} |
| Lifecycle Phase Count | {{N phases}} |
| Progression Systems | {{system list}} |
| Gameplay Classification | {{gameplay list}} |

---

## II. User Tiering Strategy

> **Detailed rules see `references/_common.md` User Tiering Rules section**

**Default tiering**: High/Mid/Low Spender 3 tiers (customizable extension)

| Tier | Classification Rule | Default Push Gift Pack |
|------|---------------------|------------------------|
| High Spender | Max single payment in past 14 days >= 328 RMB | 328 RMB gift pack |
| Mid Spender | Max single payment in past 14 days 98-328 RMB | 98 RMB gift pack |
| Low Spender | Max single payment in past 14 days < 98 RMB | 30 RMB gift pack |

> **Optional extension**: To cover non-paying users, can add "Potential User" tier (14 days no payment, default push 6 RMB gift pack)

### Scenario Tiering Rules

> **Detailed rules see `references/_common.md` Scenario Tiering Rules section**

**Core principle**: Different scenario types adopt different tiering strategies

| Scenario Type | Tiering Strategy | Description |
|---------------|------------------|-------------|
| Node Trigger (Growth Node) | **No tiering** | All users see same gift pack |
| Material Shortage | Tiered | High/Mid/Low Spender push different tier gift packs |
| Item Consumption | Tiered | High/Mid/Low Spender push different tier gift packs |
| Stamina Consumption | Tiered | High/Mid/Low Spender push different tier gift packs |
| Battle Loss | Tiered | High/Mid/Low Spender push different tier gift packs |
| Failure Trigger | Tiered | High/Mid/Low Spender push different tier gift packs |

**Node trigger scenario recommended configuration** (no tiering):
- Price tier: Recommend 98 RMB (moderate price; user can customize other tier)
- Value ratio: Mid-high (120%-140%)
- Display duration: 8-12 hours

---

## III. Value Ratio and Display Duration Rules

> **Detailed rules see `references/_common.md` Gift Pack Configuration Rules section**

**Design principle**:
1. Within same phase, higher price = lower value ratio
2. Across phases, later phase = higher value ratio (+5%~10%)

### Baseline Value Ratio (New Server Phase)

| Price Tier | Default Value Ratio |
|------------|--------------------|
| 6 RMB | 150%-180% |
| 30 RMB | 130%-150% |
| 98 RMB | 120%-130% |
| 128 RMB | 115%-125% |
| 198 RMB | 112%-118% |
| 328 RMB | 110%-120% |
| 648 RMB | 105%-115% |

### Display Duration and Value Ratio Correspondence

| Value Ratio Range | Display Duration |
|-------------------|------------------|
| >= 150% | 2-4 hours |
| 130%-150% | 4-8 hours |
| 120%-130% | 8-12 hours |
| 110%-120% | 12-18 hours |
| < 110% | 18-24 hours |

---

## IV. Lifecycle Grouping

> **Detailed rules see `references/_common.md` Server Age Phase section**

| Phase | Day Range |
|-------|-----------|
| New Server Phase | 1-30 days |
| Growth Phase I | 31-120 days |
| Growth Phase II | 121-210 days |
| ... | Increment by 90 days |

---

## V. Field Description

> **Complete enumeration see `references/_common.md` Trigger Channel Enumeration, Scenario Type Enumeration sections**

### Trigger Channel
- **Server-side** (default): Reach via push channel
- **Client-side**: Game client actively fetches/pop-up reach

### Scenario Type
- **Node Trigger**: Progression reaches key node
- **Material Shortage**: Missing materials
- **Item Consumption**: Large consumption of items
- **Failure Trigger**: Battle failure
- **Stamina Consumption**: Stamina consumption reached threshold
- **Battle Loss**: Resources suffered loss

---

## VI. Behavior Trigger Scenario Strategy Matrix

> **Cartesian product full expansion**: Below strategy matrix is fully expanded by all dimension combinations, no omissions

### 6.1 Progression Behavior Strategy

| Strategy Name | Progression Line | Lifecycle | User Tier | Trigger Scenario | Scenario Type | Trigger Channel | Gift Pack ID | Recommended Gift Pack | Price Tier | Value Ratio | Display Duration |
|---------------|------------------|-----------|-----------|------------------|---------------|-----------------|--------------|----------------------|------------|-------------|------------------|
{{progression_strategy_data}}

### 6.2 Gameplay Behavior Strategy

| Strategy Name | Gameplay Type | Lifecycle | User Tier | Trigger Scenario | Scenario Type | Trigger Channel | Gift Pack ID | Recommended Gift Pack | Price Tier | Value Ratio | Display Duration |
|---------------|---------------|-----------|-----------|------------------|---------------|-----------------|--------------|----------------------|------------|-------------|------------------|
{{gameplay_strategy_data}}

---

## VII. Combination Count Verification

| Dimension | Count |
|-----------|-------|
| Lifecycle Phase Count | {{N}} |
| User Tier Count | 3 |
| Progression Line Count | {{N}} |
| Progression Line Associated Gift Pack Type Count | {{List by progression line}} |
| Scenario Type Count | {{Scenario count per progression line}} |
| **Actually Generated Strategy Count** | {{total}} |
| **Verification Formula** | Sum(Phase count x Tier count x Progression line scenario count x Associated gift pack type count) |
| **Verification Result** | Verified: No omissions, association constraint effective |

---

## VIII. Execution Instructions

- Expected coverage strategy count: {{N}}
- Expected coverage users: {{X%}}
- Strategy effective period: 1 year (calculated from creation date)
- Recommended launch time: {{date}}

---

## IX. Expected Effect Metrics

| Metric | Target Value |
|--------|--------------|
| Global Payment Growth Rate | +10% |
| Gift Pack Purchase Conversion Rate | TBD |
| User Payment Experience Satisfaction | TBD |

---

## X. Appendix: Real-time Battle Games Out-of-match Push Description

> If applicable, list out-of-match pushable scenarios

| Scenario | Description | Push Timing |
|----------|-------------|-------------|
| Lobby | Main interface stay | Push after staying over X seconds |
| Match Waiting | Match countdown | Push during wait |
| Settlement Screen | Match ended | Push after showing battle results |
| Shop | Shop browsing | Push when opening shop |

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.