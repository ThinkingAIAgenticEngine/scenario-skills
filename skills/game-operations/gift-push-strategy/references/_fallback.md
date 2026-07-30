# Fallback Template (Unknown Genre)

<!-- Use when user's game genre is not in preset templates -->

## Genre Characteristics

> Please supplement based on actual game

## Progression System List

> Please supplement based on actual game, below are common progression system references:

### Core Progression (Common)

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Character/Hero | Core combat unit | Character fragments, Character upgrade materials, Character unlock vouchers |
| Equipment/Weapon | Power boost | Equipment enhancement materials, Equipment fragments, Weapon upgrade materials |
| Skill/Talent | Ability enhancement | Skill books, Talent points, Skill upgrade materials |
| Level/Experience | Basic growth | Experience potions, Double experience cards |

### Advanced Progression (Common)

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Pet/Companion | Companion progression | Pet eggs, Pet upgrade materials, Pet skill books |
| Mount/Vehicle | Movement/Attribute bonus | Mount advancement materials, Mount cultivation materials |
| Fashion/Appearance | Display system | Fashion, Appearance fragments, Fashion vouchers |
| Gem/Rune | Socket system | Gems, Rune fragments, Socket materials |
| Bond/Destiny | Combination bonus | Bond activation materials, Destiny materials |
| Title/Achievement | Attribute bonus | Title unlock, Achievement rewards |

### Resource System (Common)

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Gold/Gems | Universal currency | Gold, Gems, Tokens |
| Stamina/Energy | Challenge consumption | Stamina potions, Energy potions |
| Gacha Resources | Summon resources | Summon vouchers, Draw vouchers, Gacha tokens |

## Gameplay Classification

> Please supplement based on actual game, below are common gameplay classification references:

### PVE Gameplay (Common)

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Main Dungeon/Stage | Story progression | Character fragments, Equipment materials, Experience potions | Stage failure, Chapter completion, Stage stuck |
| Elite Dungeon | High difficulty challenge | Elite materials, Rare equipment fragments | Challenge failure, Three-star failure |
| Daily Dungeon | Resource acquisition | Daily materials, Gold, Experience potions | Stamina shortage, Attempts exhausted |
| Tower/Trial | Extreme challenge | Tower coins, Rare materials, Character fragments | Floor stuck, Challenge failure |
| World Boss | Server-wide challenge | Boss rewards, Rare materials, Equipment fragments | Low damage ranking, Killed |
| Event Dungeon | Limited-time challenge | Event tokens, Limited items, Rare materials | Event participation, Rewards not fully claimed |

### PVP Gameplay (Common)

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Arena | Ranking battle | Arena coins, Honor points, Character fragments | Rank drop, Challenge failure, Win streak broken |
| Guild War/Alliance War | Team competition | Guild contribution, Guild coins, Rare materials | Battle failure, Contribution insufficient |
| Cross-server War | Server competition | Cross-server rewards, Rare materials, Titles | Battle failure, Rank drop |
| Tournament | Elimination format | Tournament coins, Limited rewards, Titles | Eliminated, Promotion success |

### Social Gameplay (Common)

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Guild Task | Daily task | Guild contribution, Guild coins, Experience potions | Task not completed, Contribution insufficient |
| Friend Interaction | Gift/Visit | Friendship points, Gifts, Gold | Friend gift, Visit friend |
| Leaderboard | Ranking competition | Ranking rewards, Rare items, Titles | Rank drop, Rank rise |

### Casual Gameplay (Common)

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Check-in/Reward | Daily welfare | Check-in rewards, Resource gift packs | Check-in missed, Reward claim |
| Home/Manor | Free building | Furniture, Decoration materials, Building materials | Furniture shortage, Space insufficient |
| Collection/Album | Collection elements | Album fragments, Collection items | Collection progress slow, Fragments shortage |

## Unique Scenario Types

> Please supplement based on actual game, below are common scenario type references:

| Scenario Type | Description |
|---------------|-------------|
| New Character/Hero Release | Limited-time character pool |
| New Equipment/Weapon Release | New equipment release |
| Holiday Event | Holiday theme event |
| Season Settlement | Season ranking rewards |
| Level Breakthrough | Character level breakthrough |
| Class Change/Awakening | Class advancement completion |

## Example Strategies

### Progression Behavior Strategy Example

| Strategy Name | Progression Line | Trigger Scenario | Scenario Type |
|---------------|------------------|------------------|---------------|
| Character_High Spender_Level Node | Character/Hero | Level up to key level | Node Trigger |
| Character_High Spender_Fragment Shortage | Character/Hero | Character fragments shortage | Material Shortage |
| Equipment_Mid Spender_Material Shortage | Equipment/Weapon | Equipment enhancement materials shortage | Material Shortage |
| Skill_Low Spender_Large Consumption | Skill/Talent | Skill upgrade consumed large items | Item Consumption |
| Pet_All_Tier Breakthrough | Pet/Companion | Pet tier advancement success | Node Trigger |
| Fashion_All_New Release | Fashion/Appearance | New fashion release | Node Trigger |

### Gameplay Behavior Strategy Example

| Strategy Name | Gameplay Type | Trigger Scenario | Scenario Type |
|---------------|---------------|------------------|---------------|
| Main Dungeon_High Spender_Stage Failure | Main Dungeon | Stage failure | Failure Trigger |
| Tower_Mid Spender_Floor Stuck | Tower/Trial | Floor stuck over 3 times | Failure Trigger |
| Daily Dungeon_Low Spender_Stamina Consumption | Daily Dungeon | Stamina consumption reached threshold | Stamina Consumption |
| Arena_All_Loss Compensation | Arena | Lost 3 consecutive matches | Failure Trigger |
| Guild War_All_Battle Loss | Guild War | Team loss over 30% | Battle Loss |
| Event_All_Time Shortage | Event Dungeon | Event ending soon, rewards not fully claimed | Node Trigger |

### Differentiated Strategy Example

| Strategy Name | Progression Line/Gameplay | Trigger Scenario | Scenario Type |
|---------------|---------------------------|------------------|---------------|
| Character_High Spender_Fragment Shortage | Character/Hero | Core character fragments shortage, 10 fragments away from star upgrade | Material Shortage |
| Equipment_All_Enhancement Failure | Equipment/Weapon | Equipment enhancement failed 3 times | Failure Trigger |
| Main Dungeon_All_Stage Failure | Main Dungeon | Failed same stage 5 times | Failure Trigger |
| Arena_All_Loss Compensation | Arena | Lost 5 consecutive matches then trigger | Failure Trigger |

---

## Real-time Battle Genre Notes

> Warning: If your game includes **real-time battle** gameplay (such as MOBA, Fighting, Multi-player Competitive, Racing, Shooter, etc.), note:
> - **During match in progress** strictly forbid pushing gift packs
> - Only allowed to push in **out-of-match** (Lobby/Settlement screen/Match waiting/Shop, etc.)
> - Please supplement out-of-match pushable scenario list based on actual game

### Out-of-match Scenarios (Pushable)

| Scenario | Description | Push Timing |
|----------|-------------|-------------|
| Lobby | Main interface stay | Push after staying over X seconds |
| Match Waiting | Match countdown | Push during wait |
| Settlement Screen | Match ended | Push after showing battle results |
| Shop | Shop browsing | Push when opening shop |
| Inventory/Bag | Item management | Push when opening inventory |

---

*Inherits common rules from [_common.md](_common.md)*

---

## Usage Instructions

When user's game genre is not in preset templates:
1. Load this file as base
2. Ask user about game progression systems and gameplay classification
3. Fill specific content based on user answers
4. Replace {{xxx}} placeholders with actual content
5. If involves real-time battle gameplay, remind user about in-match push ban constraint

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.