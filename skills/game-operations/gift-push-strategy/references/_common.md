# Common Field Definitions

<!-- Common fields and rules for all genres -->

## Progression Line and Gift Pack Association Constraint

**Core principle**: Each progression line/gameplay only pushes **associated gift pack types**, avoiding invalid combinations.

**Priority rule**:
1. **User-provided association information takes priority**: If user explicitly provides progression line/gameplay and gift pack association relationship in conversation, use user-provided information
2. **Template defaults as fallback**: When user does not provide, use predefined association relationship in genre template

**Progression line association rule**:
- Progression line and gift pack type are predefined in genre template (in "Associated Gift Pack Types" column of progression system table)
- When generating strategy, only push gift packs associated with current progression line
- Example: Equipment enhancement scenario -> Equipment materials, not hero materials
- Example: Hero upgrade node -> Hero experience/fragments, not equipment materials

**Gameplay association rule**:
- Gameplay and gift pack type are predefined in genre template (in "Output/Associated Gift Pack" column of gameplay classification table)
- Gameplay-triggered strategy pushes gift pack types specified in that gameplay's "Output/Associated Gift Pack" column
- Example: Main dungeon outputs hero fragments -> Main dungeon failure scenario pushes hero-related gift packs
- Example: Arena outputs arena coins and honor points -> Arena failure scenario pushes arena-related gift packs

**Progression line association example (SLG genre)**:

| Progression Line | Associated Gift Pack Types | Valid Push Scenarios |
|------------------|---------------------------|----------------------|
| Hero | Hero experience, Hero fragments, Hero star upgrade, Hero awakening | Hero upgrade node, Hero material shortage |
| Equipment | Equipment enhancement materials, Equipment fragments, Treasure refinement stones | Equipment enhancement failure, Equipment material shortage |
| Tech | Tech research materials, Talent points, Tech acceleration | Tech research material shortage, Tech acceleration consumption |

**Gameplay association example (Card genre)**:

| Gameplay | Output/Associated Gift Pack | Valid Push Scenarios |
|----------|----------------------------|----------------------|
| Adventure/Main | Hero fragments, Experience potions | Stage failure, Chapter completion |
| Arena | Arena coins, Honor points | Rank drop, Challenge failure |
| Guild Boss | Guild contribution, Hero fragments | Low damage ranking, Boss kill |
| Tower/Trial | Tower coins, Rare materials | Floor stuck, Challenge failure |

---

## Trigger Channel Enumeration

**Default channel**: Server-side

| Enum Value | Description |
|------------|-------------|
| Server-side | Reach via push channel (Push/In-app message) |
| Client-side | Game client actively fetches/pop-up reach |

## Scenario Type Enumeration (Common)

| Enum Value | Description |
|------------|-------------|
| Node Trigger | Progression reaches specified level/star rating etc. key node |
| Material Shortage | Missing materials for next progression target |
| Item Consumption | Large consumption of acceleration items etc. |
| Failure Trigger | PVP/PVE battle failure, stimulate desire to become stronger |
| Stamina Consumption | Stamina consumption reaches threshold |
| Battle Loss | Resources/troops etc. suffered losses |

## User Tiering Rules (Default)

**Default tiering**: High Spender, Mid Spender, Low Spender - 3 tiers. User can customize to add "Potential User" tier.

| Tier | Classification Rule | Default Push Gift Pack |
|------|---------------------|------------------------|
| High Spender | Max single payment in past 14 days >= 328 RMB | 328 RMB gift pack |
| Mid Spender | Max single payment in past 14 days 98-328 RMB | 98 RMB gift pack |
| Low Spender | Max single payment in past 14 days < 98 RMB | 30 RMB gift pack |

> **Optional extension**: To cover non-paying users, can add "Potential User" tier (14 days no payment, default push 6 RMB gift pack)

## Scenario Tiering Rules

**Core principle**: Different scenario types adopt different tiering strategies, balancing user growth experience and monetization goals.

> **Important**: When generating no-tiering scenario strategy, briefly explain reason for no tiering: Ensure Low Spenders can equally purchase gift packs at each growth node during their progression to High Spenders, cultivating payment habits.

### Growth Node Scenario (No Tiering)

**Applicable scenario type**: Node Trigger

**Tiering strategy**: **No tiering**, all users (High/Mid/Low Spender) see **the same gift pack**

**Design reason**:
- Ensure Low Spenders during progression to High Spenders can equally purchase gift packs at each growth node
- Avoid Low Spenders missing key growth node discount opportunities due to tiering
- Cultivate user payment habits, improve long-term payment conversion

**Recommended configuration**:
- Price tier: Moderate (recommend 98 RMB), accommodating all users' purchasing ability
- Value ratio: Mid-high (120%-140%), providing sufficient attraction
- Display duration: 8-12 hours (corresponding to 120%-140% value ratio), giving users sufficient decision time

> **Important**: When generating node trigger scenario strategy, explain:
> 1. Reason for default 98 RMB gift pack: Moderate price, accommodating High/Mid/Low Spender purchasing abilities
> 2. Remind user can choose other price tiers based on actual needs (e.g., 30 RMB, 128 RMB, etc.)
> 3. If user provides specific price preference, adjust based on user needs

### Resource Consumption Scenario (Tiered)

**Applicable scenario types**: Material shortage, Item consumption, Stamina consumption, Battle loss

**Tiering strategy**: **Tiered push**, push corresponding tier gift packs based on user payment capability

**Design reason**:
- Resource consumption scenarios are more personalized, can precisely match based on user payment capability
- High Spenders have higher consumption capability, can push high-price gift packs; Low Spenders push low-price gift packs to avoid churn
- Improve overall revenue efficiency

**Recommended configuration**:

| Scenario Type | High Spender Recommendation | Mid Spender Recommendation | Low Spender Recommendation |
|---------------|----------------------------|---------------------------|---------------------------|
| Material Shortage | 328 RMB | 98 RMB | 30 RMB |
| Item Consumption | 198-328 RMB | 98 RMB | 30 RMB |
| Stamina Consumption | 98-128 RMB | 30 RMB | 6 RMB |
| Battle Loss | 198-328 RMB | 98 RMB | 30 RMB |

### Failure Trigger Scenario (Special Handling)

**Applicable scenario type**: Failure Trigger (PVP/PVE battle failure)

**Tiering strategy**: **Tiered push**, stimulate desire to become stronger

**Design reason**:
- Failure scenarios have strong immediate payment motivation
- Can precisely push based on user payment capability to maximize conversion

**Recommended configuration**:
- High Spender: 198-328 RMB (high value ratio, stimulate purchase)
- Mid Spender: 98 RMB
- Low Spender: 30 RMB

## Gift Pack Configuration Rules (Default)

### Value Ratio Rules

**Design logic**:
1. **Within same phase, higher price = lower value ratio**: High-price gift packs control value ratio to avoid affecting payment balance; low-price gift packs provide higher value ratio to improve conversion
2. **Across phases, later phase = higher value ratio**: As lifecycle progresses, same-price gift pack value ratio defaults to 5%-10% higher than previous phase, incentivizing old players to continue paying

#### Baseline Value Ratio (New Server Phase)

| Price Tier | Default Value Ratio | Description |
|------------|--------------------|-------------|
| 6 RMB | 150%-180% | Low price high value ratio, promote first purchase conversion |
| 30 RMB | 130%-150% | Mid-low price, moderate value ratio |
| 98 RMB | 120%-130% | Mid-range price, slightly high value ratio |
| 128 RMB | 115%-125% | Mid-high range, value ratio close to same-period gift packs |
| 198 RMB | 112%-118% | High range price, moderate value ratio |
| 328 RMB | 110%-120% | High range price, slightly higher value ratio than same period |
| 648 RMB | 105%-115% | Highest tier, value ratio close to same-period gift packs |

#### Cross-phase Value Ratio Increment Rule

| Lifecycle | Increment | Calculation Method |
|-----------|-----------|--------------------|
| New Server Phase | Baseline | - |
| Growth Phase I | +5%~10% | Baseline value ratio x (1.05~1.10) |
| Growth Phase II | +5%~10% | Growth Phase I value ratio x (1.05~1.10) |
| Growth Phase III+ | +5%~10% | Previous phase value ratio x (1.05~1.10) |

#### Example: 6 RMB Gift Pack Cross-phase Value Ratio

| Lifecycle | Value Ratio Range | Calculation Process |
|-----------|-------------------|--------------------|
| New Server Phase | 150%-180% | Baseline |
| Growth Phase I | 157.5%-198% | 150%x1.05 ~ 180%x1.10 |
| Growth Phase II | 165%-218% | 157.5%x1.05 ~ 198%x1.10 |

> **User can customize**: User can specify specific value ratio value, user configuration takes priority

### Other Configuration

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| Strategy Effective Period | 1 year | Calculated from creation date |

### Display Duration Rules

**Design logic**: Higher gift pack value ratio = shorter display duration (create urgency, promote conversion)

**Default range**: 2-24 hours, minimum granularity 1 hour

#### Value Ratio and Display Duration Correspondence Rule

| Value Ratio Range | Display Duration | Description |
|-------------------|------------------|-------------|
| >= 150% | 2-4 hours | Ultra-high value ratio, short time limit, create urgency |
| 130%-150% | 4-8 hours | High value ratio, moderate duration |
| 120%-130% | 8-12 hours | Mid-high value ratio, longer duration |
| 110%-120% | 12-18 hours | Moderate value ratio, long duration |
| < 110% | 18-24 hours | Low value ratio, longest duration, give users sufficient consideration time |

**Calculation formula** (reference):
```
Display duration (hours) = max(2, 24 - (value ratio - 100) / 5)
```

**Example**:
- Value ratio 180%: 24 - (180-100)/5 = 24 - 16 = 8 hours -> Recommend 4-8 hours
- Value ratio 140%: 24 - (140-100)/5 = 24 - 8 = 16 hours -> Recommend 8-12 hours
- Value ratio 110%: 24 - (110-100)/5 = 24 - 2 = 22 hours -> Recommend 18-24 hours

> **User can customize**: User can specify specific display duration, user configuration takes priority

## Server Age Phase (Default Rule)

### Grouping Rule

1. **New Server Phase**: Fixed as 1-30 days
2. **Subsequent phases**: Every 90 days after day 30 is one phase
3. **Phase limit**: No limit, dynamically generated based on actual server age

### Example

| Server Age Range | Phase Division |
|------------------|----------------|
| 1-30 days | New Server Phase |
| 31-120 days | Growth Phase I |
| 121-210 days | Growth Phase II |
| 211-300 days | Growth Phase III |
| 301-390 days | Growth Phase IV |
| 391-480 days | Growth Phase V |
| ... | Continue incrementing by 90 days |

### Calculation Formula

```
Phase count = 1 (New Server Phase) + ceil((Total days - 30) / 90)

**Default generation range**: Maximum strategy generation up to 180 days

Day range for Nth Growth Phase (N >= 1):
- Start: 30 + (N-1) x 90 + 1
- End: min(30 + N x 90, 180)  # No more than 180 days
```

> **Custom rule**: User can specify specific lifecycle grouping, such as "group by month", "group by quarter" or custom day range. User specification takes priority.

---

*This file is common definition, each genre template inherits and extends*

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.