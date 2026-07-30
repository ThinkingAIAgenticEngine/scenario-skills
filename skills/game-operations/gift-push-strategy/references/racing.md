# Racing Genre Template

## Genre Characteristics

- Racing as core
- Vehicle progression and modification
- Real-time racing competition
- Operation and strategy both important

## Progression System List

### Core Progression

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Racing Car | Core racing unit | Racing cars, Car fragments, Car unlock vouchers |
| Driver/Racer | Attribute bonus | Drivers, Driver skill books, Driver fragments |
| Modification System | Vehicle performance | Modification parts, Modification materials, Modification blueprints |
| Track Mastery | Achievement collection | Track rewards, Mastery points |

### Advanced Progression

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Paint/Decal | Appearance customization | Paints, Decals, Spray paint |
| Garage/Collection | Vehicle collection | Garage slots, Collection display |
| Driver Equipment | Driver bonus | Helmets, Racing suits, Equipment |
| Team System | Team bonus | Team contribution, Team coins |
| License Level | Level system | License test, License upgrade |

### Resource System

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Gold/Gems | Universal currency | Gold, Gems, Tokens |
| Fuel/Stamina | Challenge consumption | Fuel, Stamina potions |
| Gacha Resources | Summon resources | Summon vouchers, Draw vouchers |

## Gameplay Classification

### Racing Gameplay (In-match No Push)

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Solo Racing/Time Trial | Solo challenge | Car fragments, Mastery points, Gold | In-match push banned |
| Multi-player Race/Real-time Battle | Real player battle | Arena coins, Rare paints, Car fragments | In-match push banned |
| Challenge Race/Limited Race | Limited challenge | Challenge coins, Rare materials, Modification parts | In-match push banned |
| Ranked Race | Tier competition | Tier protection cards, Arena coins, Limited paints | In-match push banned |
| Drift Race | Drift points | Drift coins, Modification parts, Driver fragments | In-match push banned |
| Elimination Race | Last place eliminated | Elimination coins, Rare skins, Car fragments | In-match push banned |
| Item Race | Item racing | Item race coins, Rare materials, Paints | In-match push banned |

> Warning: **Important**: Above racing modes, only push in **out-of-match** (Lobby/Settlement screen/Match waiting)

### Career Mode/PVE Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Career Mode | Story stages | Car fragments, Modification parts, Gold | Stage complete, Stage failure |
| Season Challenge | Season task | Season tokens, Rare paints, Driver fragments | Task complete, Task failure |
| Vehicle Test Drive | Test drive | Test drive rewards, Car purchase coupons | Test drive ended, Purchase prompt |
| License Test | Level unlock | License rewards, Unlock materials, Gold | Test failure, Test passed |

### Social/Team Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Team Race | Team competition | Team contribution, Team coins, Rare materials | Race ended, Contribution settlement |
| Friend Battle | Friend challenge | Friendship points, Gold, Experience cards | Battle ended, Battle record display |
| Leaderboard | Ranking competition | Ranking rewards, Rare paints, Titles | Rank drop, Rank rise |

### Out-of-match Scenarios (Pushable)

| Scenario | Description | Push Timing |
|----------|-------------|-------------|
| Lobby | Main interface stay | Push after staying over X seconds |
| Match Waiting | Match countdown | Push during wait |
| Settlement Screen | Match ended | Push after showing results |
| Garage/Modification | Vehicle modification interface | Push when entering modification interface |
| Shop | Shop browsing | Push when opening shop |
| Team Interface | Team management | Push when viewing team info |

## Unique Scenario Types

| Scenario Type | Description |
|---------------|-------------|
| New Track Open | Unlock new track/season |
| New Car Release | New car release |
| Season Settlement | Season ranking settlement |
| Paint Unlock | New paint/decal unlock |
| Team Upgrade | Team level up |
| License Upgrade | License level up |
| Loss Compensation | Lost multiple consecutive matches |
| Personal Best | Break personal record |

## Example Strategies

### Progression Behavior Strategy Example

| Strategy Name | Progression Line | Trigger Scenario | Scenario Type |
|---------------|------------------|------------------|---------------|
| Car_High Spender_Level Node | Racing Car | Car star upgrade to 3/5/7 level | Node Trigger |
| Car_High Spender_Fragment Shortage | Racing Car | Car fragments shortage | Material Shortage |
| Modification_Mid Spender_Parts Shortage | Modification System | Modification parts shortage | Material Shortage |
| Modification_Mid Spender_Upgrade Failure | Modification System | Modification upgrade failure | Failure Trigger |
| Driver_Low Spender_Skill Upgrade | Driver/Racer | Driver skill upgrade consumed large items | Item Consumption |
| Driver_Low Spender_Fragment Shortage | Driver/Racer | Driver fragments shortage | Material Shortage |
| Track_All_Star Rating Achieved | Track Mastery | Complete track three-star rating | Node Trigger |
| Paint_All_New Release | Paint/Decal | New paint release | Node Trigger |
| Team_All_Contribution Shortage | Team System | Team contribution shortage | Material Shortage |

### Gameplay Behavior Strategy Example (Out-of-match Push)

| Strategy Name | Gameplay Type | Trigger Scenario | Scenario Type |
|---------------|---------------|------------------|---------------|
| Solo Race_High Spender_Post-match Trigger | Solo Racing | Match ended, Lobby stay | Node Trigger |
| Multi-player Race_Mid Spender_Match Trigger | Multi-player Race | Match ended, Battle record display | Node Trigger |
| Ranked Race_All_Loss Compensation | Ranked Race | Lost 3 matches, Settlement screen | Failure Trigger |
| Challenge Race_All_Challenge Ended | Challenge Race | Challenge ended, Settlement screen | Node Trigger |
| Drift Race_All_Match Trigger | Drift Race | Match ended, Settlement screen | Node Trigger |
| Elimination Race_All_Elimination Trigger | Elimination Race | Eliminated, Settlement screen | Failure Trigger |
| Career_All_Stage Failure | Career Mode | Stage failure, Settlement screen | Failure Trigger |
| License_All_Test Failure | License Test | Test failure | Failure Trigger |
| Team Race_All_Race Ended | Team Race | Race ended, Contribution settlement | Node Trigger |

### Out-of-match Behavior Strategy Example

| Strategy Name | Scenario | Trigger Scenario | Scenario Type |
|---------------|----------|------------------|---------------|
| Lobby_High Spender_Stay Trigger | Lobby | Lobby stay over 30 seconds | Node Trigger |
| Garage_Mid Spender_Modification Interface | Garage/Modification | Enter vehicle modification interface | Node Trigger |
| Shop_Low Spender_Browse Trigger | Shop | Open shop interface | Node Trigger |
| Match_All_Waiting Trigger | Match Waiting | Match wait over 10 seconds | Node Trigger |
| Team_All_Interface Trigger | Team Interface | View team info | Node Trigger |
| New Car_All_Release Reminder | Lobby | New car release, Lobby stay | Node Trigger |
| New Track_All_Open Reminder | Lobby | New track open, Lobby stay | Node Trigger |

### Differentiated Strategy Example (Out-of-match Push)

| Strategy Name | Progression Line/Gameplay | Trigger Scenario | Scenario Type |
|---------------|---------------------------|------------------|---------------|
| Track_All_Three-star Failure | Track Mastery | Track three-star rating failure, Settlement screen | Failure Trigger |
| Track_Mid Spender_Mastery Point Shortage | Track Mastery | Track mastery points shortage | Material Shortage |
| Ranked Race_All_Loss Compensation | Ranked Race | Lost 3 matches, Settlement screen | Failure Trigger |
| Team Race_All_Contribution Shortage | Team Race | Team race contribution shortage | Material Shortage |

> Warning: Above strategies only push in **out-of-match** (Lobby/Settlement screen/Match waiting)

---

*Inherits common rules from [_common.md](_common.md)*

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.