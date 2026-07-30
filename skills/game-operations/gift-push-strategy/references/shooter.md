# Shooter Genre Template

## Genre Characteristics

- Shooting combat as core
- Gun/Weapon progression
- Real-time competition
- Operation and strategy both important

## Progression System List

### Core Progression

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Gun/Weapon | Core weapon | Guns, Gun parts, Modification accessories, Weapon skins |
| Character/Operator | Character progression | Character unlock, Character upgrade, Character fragments |
| Skill/Tactics | Combat bonus | Skill cards, Tactical items, Skill upgrade materials |
| Level/Tier | Ranking system | Tier protection cards, Experience bonus cards |

### Advanced Progression

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Character/Skin | Display progression | Character skins, Character unlock, Limited skins |
| Accessories/Modification | Weapon modification | Muzzle, Scope, Grip, Magazine accessories |
| Talent/Specialization | Character enhancement | Talent points, Specialization materials |
| Achievement/Medal | Collection system | Medals, Achievement rewards |
| Battle Record/Data | Data statistics | Battle record display, Data panel |

### Resource System

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Gold/Gems | Universal currency | Gold, Gems, Tokens |
| Stamina/Energy | Challenge consumption | Stamina potions, Energy potions |
| Gacha Resources | Summon resources | Summon vouchers, Draw vouchers |

## Gameplay Classification

### Real-time Battle Gameplay (In-match No Push)

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Multi-player Match | Real player battle | Arena coins, Experience cards, Weapon parts | In-match push banned |
| Ranked Match | Tier competition | Tier protection cards, Arena coins, Rare skins | In-match push banned |
| Team Deathmatch | Team battle | Arena coins, Experience cards, Gold | In-match push banned |
| Bomb Mode | Plant/Defuse bomb | Arena coins, Tactical items, Weapon parts | In-match push banned |
| Domination Mode | Point capture | Arena coins, Experience cards, Character fragments | In-match push banned |
| Battle Royale | Survival competition | Arena coins, Rare skins, Character fragments | In-match push banned |

> Warning: **Important**: Above real-time battle modes, only push in **out-of-match** (Lobby/Settlement screen/Match waiting)

### PVE/Challenge Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Story Mode | PVE stages | Gun parts, Character fragments, Gold | Chapter complete, Stage settlement, Stage failure |
| Survival Mode | Extreme challenge | Survival coins, Rare materials, Weapon skins | Challenge ended (settlement screen), Challenge failure |
| Zombie Mode | PvE battle | Zombie coins, Weapon parts, Character fragments | Wave failure, Wave complete |
| Shooting Range/Training | Shooting practice | Training rewards, Gold, Experience cards | Practice ended, Exit range |
| Challenge Stage | Special challenge | Challenge coins, Rare materials, Weapon parts | Challenge failure, Challenge success |
| Boss Battle | Boss challenge | Boss coins, Rare skins, Character fragments | Boss kill failure, Boss kill success |

### Special Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Hide and Seek/Hide Mode | Casual gameplay | Casual coins, Skin fragments, Gold | Game ended, Settlement screen |
| Bio Mode | Special rules | Bio coins, Rare materials, Character fragments | Game ended, Settlement screen |
| Legion War/Guild War | Team competition | Legion contribution, Legion coins, Rare materials | Battle ended, Contribution settlement |
| Tournament | Elimination format | Tournament coins, Limited skins, Titles | Eliminated, Promotion success |

### Out-of-match Scenarios (Pushable)

| Scenario | Description | Push Timing |
|----------|-------------|-------------|
| Lobby | Main interface stay | Push after staying over X seconds |
| Match Waiting | Match countdown | Push during wait |
| Settlement Screen | Match ended | Push after showing battle record |
| Inventory/Modification | Gun modification interface | Push when entering modification interface |
| Shop | Shop browsing | Push when opening shop |
| Season Interface | Tier/Season view | Push when viewing season rewards |

## Unique Scenario Types

| Scenario Type | Description |
|---------------|-------------|
| Out-of-match Stay | Player stay in non-battle interface |
| Match Settlement | Show results after match ended |
| Match Waiting | Wait time during match process |
| Weapon Modification | Open gun modification interface |
| Battle Record Review | View historical battle record/data |
| New Weapon Release | New gun release |
| New Character Release | New character release |
| Season Update | Season reset/update |
| Loss Compensation | Lost multiple consecutive matches |

## Example Strategies

### Progression Behavior Strategy Example

| Strategy Name | Progression Line | Trigger Scenario | Scenario Type |
|---------------|------------------|------------------|---------------|
| Gun_High Spender_Level Node | Gun | Gun upgrade to 3/5/7 level | Node Trigger |
| Gun_High Spender_Accessory Material Shortage | Accessories/Modification | Accessory upgrade materials shortage | Material Shortage |
| Accessories_Mid Spender_Material Shortage | Modification Accessories | Accessory upgrade materials shortage | Material Shortage |
| Character_Low Spender_Skin Unlock | Character/Skin | Skin unlock consumed large items | Item Consumption |
| Character_All_Fragment Shortage | Character/Operator | Character fragments shortage | Material Shortage |
| Skill_All_New Skill Card | Skill/Tactics | New skill card release | Node Trigger |
| Talent_All_Points Shortage | Talent/Specialization | Talent points shortage | Material Shortage |

### Gameplay Behavior Strategy Example (Out-of-match Push)

| Strategy Name | Gameplay Type | Trigger Scenario | Scenario Type |
|---------------|---------------|------------------|---------------|
| Ranked_High Spender_Post-match Trigger | Ranked Match | Match ended, Lobby stay | Node Trigger |
| Ranked_All_Loss Compensation | Ranked Match | Lost 3 matches, Settlement screen | Failure Trigger |
| Team Death_Mid Spender_Match Trigger | Team Deathmatch | Match ended, Battle record display | Node Trigger |
| Battle Royale_All_Match Trigger | Battle Royale | Match ended, Settlement screen | Node Trigger |
| Story_All_Chapter Complete | Story Mode | Chapter clear, Settlement screen | Node Trigger |
| Survival_All_Challenge Ended | Survival Mode | Challenge ended, Show results | Node Trigger |
| Zombie_All_Wave Failure | Zombie Mode | Wave failure, Settlement screen | Failure Trigger |
| Boss_All_Kill Failure | Boss Battle | Boss kill failure, Settlement screen | Failure Trigger |

### Out-of-match Behavior Strategy Example

| Strategy Name | Scenario | Trigger Scenario | Scenario Type |
|---------------|----------|------------------|---------------|
| Lobby_High Spender_Stay Trigger | Lobby | Lobby stay over 30 seconds | Node Trigger |
| Inventory_Mid Spender_Modification Interface | Inventory/Modification | Enter gun modification interface | Node Trigger |
| Shop_Low Spender_Browse Trigger | Shop | Open shop interface | Node Trigger |
| Match_All_Waiting Trigger | Match Waiting | Match wait over 10 seconds | Node Trigger |
| Season_All_Tier View | Season Interface | View season rewards interface | Node Trigger |
| New Weapon_All_Release Reminder | Lobby | New weapon release, Lobby stay | Node Trigger |

### Differentiated Strategy Example (Out-of-match Push)

| Strategy Name | Progression Line/Gameplay | Trigger Scenario | Scenario Type |
|---------------|---------------------------|------------------|---------------|
| Tier_Mid Spender_Promotion Failure | Ranked Match | Promotion match failure, Settlement screen | Failure Trigger |
| Tier_All_Protection Trigger | Ranked Match | Tier protection card effective, Settlement screen | Node Trigger |
| Mode_All_Nearing End | Limited Mode | Event mode remaining less than 24 hours | Node Trigger |

> Warning: Above strategies only push in **out-of-match** (Lobby/Settlement screen/Match waiting)

---

*Inherits common rules from [_common.md](_common.md)*

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.