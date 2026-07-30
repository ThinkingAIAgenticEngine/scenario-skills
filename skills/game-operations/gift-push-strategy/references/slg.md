# SLG Genre Template

<!-- Based on reference document: Data Application Case - SLG Game Gift Pack Refined Push Strategy -->

## Genre Characteristics

- Numeric growth as core
- Strong competition (PVP)
- Resource management and strategic planning
- Long-term progression, season rotation

## Progression System List

### Core Progression

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Hero/General | Core progression, unit cultivation | Hero experience, Hero fragments, Hero star upgrade, Hero awakening |
| Equipment/Treasure | Power boost important path | Equipment enhancement materials, Equipment fragments, Treasure refinement stones |
| Unit Type/Troops | Combat unit | Unit advancement, Unit unlock, Troop expansion |
| Tech/Talent | Lord/Kingdom tech | Tech research materials, Talent points, Tech acceleration |

### Advanced Progression

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Formation/Formation | Team configuration | Formation upgrade materials, Formation books |
| Alliance/Guild | Alliance tech, Alliance construction | Alliance contribution, Alliance construction materials, Alliance coins |
| City/Territory | City construction, Territory expansion | City upgrade materials, Territory resources |
| Gem/Rune | Attribute socket | Gems, Rune fragments, Socket materials |
| War Horse/Mount | Movement/Attribute bonus | War horses, Horse gear, Mount cultivation materials |
| Bond/Destiny | Combination bonus | Bond activation items, Destiny materials |

### Resource System

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Resource Building | Wood, Stone, Iron, Gold, Food | Resource gift packs, Acceleration items |
| Storage | Resource storage limit | Storage expansion items |
| VIP Level | Privilege bonus | VIP experience, VIP gift packs |

## Gameplay Classification

### PVE Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Main Dungeon | PVE stage progression | Hero fragments, Experience potions, Equipment materials | Stage failure, Chapter completion, Chapter stuck |
| Resource Dungeon | Wood/Stone/Iron/Gold output | Resource gift packs, Acceleration items | Resource shortage, Dungeon failure |
| Trial Tower/Tower | Floor challenge | Tower coins, Rare materials, Hero fragments | Challenge failure, Floor breakthrough, Floor stuck |
| Expedition/Explore | Expedition exploration gameplay | Expedition resources, Hero fragments | Expedition failure, Exploration complete |
| World Boss | Collective challenge | Boss rewards, Rare materials, Hero fragments | Low damage ranking, Boss kill |
| Elite Dungeon | High difficulty stages | Elite materials, Equipment fragments, Hero fragments | Challenge failure, Three-star failure |

### PVP Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Solo Base Battle | Player competition | Resource gift packs, Acceleration items, Troop recovery | Battle failure, Base attacked, Resources stolen |
| Alliance War/Guild War | Team competition | Alliance contribution, Alliance coins, Rare materials | Battle failure, Alliance contribution insufficient, City lost |
| Arena | PVP ranking | Arena coins, Honor points, Hero fragments | Challenge failure, Rank drop, Win streak broken |
| Kingdom War/Cross-server War | Large-scale competition | Kingdom war rewards, Rare materials, Hero fragments | Battle failure, City lost, Kingdom contribution low |
| Territory War | Resource point contest | Resource gift packs, Acceleration items | Contest failure, Defense breached |

### Social/Casual Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Alliance Donation | Daily donation | Alliance contribution, Alliance coins | Donation complete, Donation attempts exhausted |
| Alliance Shop | Exchange items | Alliance coins exchange materials | Points insufficient, Item refresh |
| Check-in/Reward | Daily welfare | Check-in rewards, Resource gift packs | Check-in missed, Reward claim |
| Escort/Transport | Resource escort | Resource gift packs, Escort rewards | Escort failure, Robbed |

### Season Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Season Settlement | Season ranking rewards | Season rewards, Rare hero fragments | Season end, Ranking settlement |
| Season Task | Season goals | Season tokens, Rare materials | Task not completed, Progress behind |
| Season Shop | Limited exchange | Season tokens exchange items | Tokens insufficient, Item off shelf |

## Unique Scenario Types

| Scenario Type | Description |
|---------------|-------------|
| Alliance Donation | Trigger after alliance donation |
| City Attack/Defense | City attacked, Siege win/loss |
| Season Settlement | Season ranking reward distribution |
| Server Open Event | New server exclusive event |
| Server Merge Event | Server merge event |
| New Hero Release | Limited-time hero pool |
| Battle Loss Recovery | After massive troop loss |

## Example Strategies

### Progression Behavior Strategy Example

| Strategy Name | Progression Line | Trigger Scenario | Scenario Type |
|---------------|------------------|------------------|---------------|
| Hero_High Spender_Level Node Trigger | Hero | Hero upgrade to 3/5/8/10 level | Node Trigger |
| Hero_High Spender_Awakening Material Shortage | Hero | Hero awakening materials shortage | Material Shortage |
| Equipment_Mid Spender_Material Shortage | Equipment | Equipment enhancement materials shortage | Material Shortage |
| Gem_Mid Spender_Socket Shortage | Gem | Gem shortage cannot socket | Material Shortage |
| Tech_Low Spender_Acceleration Consumption | Tech | Large use of acceleration items | Item Consumption |
| Unit_Low Spender_Advancement Material Shortage | Unit Type | Unit advancement materials shortage | Material Shortage |
| War Horse_All_Cultivation Node | War Horse | War horse advancement success | Node Trigger |
| Bond_All_Activation Success | Bond | Bond activation success | Node Trigger |

### Gameplay Behavior Strategy Example

| Strategy Name | Gameplay Type | Trigger Scenario | Scenario Type |
|---------------|---------------|------------------|---------------|
| Base Battle_High Spender_Failure Trigger | Solo Base Battle | Battle failure | Failure Trigger |
| Resources Stolen_High Spender_Revenge Gift | Solo Base Battle | Resources stolen over 100k | Battle Loss |
| Arena_Mid Spender_Rank Drop | Arena | Rank drop over 10 positions | Failure Trigger |
| Resource Dungeon_Low Spender_Stamina Consumption | Resource Dungeon | Stamina consumption reached threshold | Stamina Consumption |
| Alliance War_All_Troop Loss | Alliance War | Troop loss over 30% | Battle Loss |
| Trial Tower_All_Floor Stuck 3 Days | Trial Tower | Same floor stuck over 3 days | Failure Trigger |
| Kingdom War_All_City Lost | Kingdom War | Own city captured | Battle Loss |
| Escort_All_Robbed | Escort | Escort robbed | Failure Trigger |
| Season_All_Settlement Supplement | Season Task | Season task not completed | Node Trigger |

### Differentiated Strategy Example

| Strategy Name | Progression Line/Gameplay | Trigger Scenario | Scenario Type |
|---------------|---------------------------|------------------|---------------|
| Alliance War_High Spender_Pre-war Reserve | Alliance War | Alliance war about to start, resources insufficient | Node Trigger |
| Alliance War_All_Troop Loss Supplement | Alliance War | Troop loss over 30% during battle | Battle Loss |
| Territory_All_New Area Unlock | City/Territory | Unlock new territory needs materials | Material Shortage |
| Unit_All_Counter Transition | Unit Type/Troops | Defeated by counter unit after | Failure Trigger |

---

*Inherits common rules from [_common.md](_common.md)*

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.