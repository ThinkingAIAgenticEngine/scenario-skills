# Casual Genre Template

## Genre Characteristics

- Relaxing and casual, easy to pick up
- Diverse gameplay, fragmented sessions
- Visual/Character decoration focused
- Strong social sharing attributes

## Progression System List

### Core Progression

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Character Decoration/Fashion | Display progression | Clothes, Skins, Accessories, Hairstyles |
| Home/Decoration | Free building | Furniture, Decorations, Building materials, Land |
| Pet/Cute Pet | Companion progression | Pets, Pet clothes, Pet upgrade materials |
| Achievement/Collection | Collection elements | Limited collection items, Achievement rewards |

### Advanced Progression

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Manor/Farm | Planting progression | Seeds, Fertilizer, Decorations, Expansion materials |
| Album/Collection | Collection system | Album fragments, Collection items |
| Level/Experience | Basic growth | Experience potions, Double experience cards |
| Plant Garden | Plant progression | Plant seeds, Flower pots, Fertilizer |
| Zoo/Ranch | Animal progression | Animals, Animal feed, Animal decorations |
| Skill/Talent | Ability boost | Skill points, Talent materials |

### Resource System

| Progression System | Description | Associated Gift Pack Types |
|--------------------|-------------|----------------------------|
| Gold/Gems | Universal currency | Gold, Gems, Tokens |
| Stamina/Energy | Challenge consumption | Stamina potions, Energy potions |
| Synthesis Materials | Synthesis items | Synthesis materials, Synthesis acceleration |

## Gameplay Classification

### Core Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Stage Challenge | Simple stages | Gold, Experience potions, Decoration materials | Stage stuck, Failure, Stage clear |
| Match-3/Three-match | Match gameplay | Gold, Stamina potions, Decoration materials | Stage failure, Moves exhausted |
| Synthesis Gameplay | Material synthesis | Synthesis materials, Rare items, Decorations | Synthesis failure, Materials shortage |
| Decoration Layout | Free building | Furniture, Decorations, Building materials, Gold | Furniture shortage, Space insufficient |
| Parkour/Adventure | Dodge obstacles | Gold, Character fragments, Rare items | Death, Stage clear, Record breakthrough |

### Planting/Operation Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Planting Harvest | Crop planting | Seeds, Fertilizer, Gold | Harvest complete, Crop withered |
| Order Delivery | Order completion | Gold, Experience potions, Decoration materials | Order timeout, Materials shortage |
| Shop Operation | Shop management | Gold, Rare decorations, Upgrade materials | Revenue settlement, Upgrade materials shortage |
| Fishing Gameplay | Leisure fishing | Gold, Rare fish, Decorations | Fishing ended, Rare fish caught |

### Social Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Friend Interaction | Gift/Visit | Friendship points, Gifts, Decoration materials | Friend gift, Visit friend |
| Leaderboard | Ranking competition | Ranking rewards, Rare decorations, Titles | Rank drop, Rank rise |
| Collaboration Task | Friend collaboration | Collaboration coins, Rare materials, Decorations | Task complete, Task failure |
| Party Event | Multi-player event | Party rewards, Limited decorations, Gold | Event start, Event end |

### Limited-time/Event Gameplay

| Gameplay | Description | Output/Associated Gift Pack | Trigger Scenario |
|----------|-------------|------------------------------|------------------|
| Daily Check-in | Check-in rewards | Check-in rewards, Gold, Decoration materials | Check-in missed, Consecutive check-in |
| Limited-time Event | Holiday event | Event tokens, Limited decorations, Rare items | Event start, Reward claim |
| Holiday Event | Holiday theme | Holiday rewards, Limited fashion, Decorations | Holiday event start |
| Season Task | Season goals | Season tokens, Rare decorations, Titles | Task complete, Season settlement |

## Unique Scenario Types

| Scenario Type | Description |
|---------------|-------------|
| Daily Check-in | Check-in reward |
| Fashion Release | New fashion release |
| Holiday Event | Holiday theme |
| Home Upgrade | Home level up |
| Pet Obtained | Get new pet |
| Album Complete | Complete album collection |
| Friend Gift | Friend gift |
| Limited-time Discount | Item discount |

## Example Strategies

### Progression Behavior Strategy Example

| Strategy Name | Progression Line | Trigger Scenario | Scenario Type |
|---------------|------------------|------------------|---------------|
| Furniture_High Spender_Furniture Shortage | Home/Decoration | Furniture shortage | Material Shortage |
| Home_High Spender_Expansion Material Shortage | Home/Decoration | Expansion materials shortage | Material Shortage |
| Pet_Mid Spender_Upgrade Consumption | Pet/Cute Pet | Pet upgrade consumed large items | Item Consumption |
| Pet_Mid Spender_Food Shortage | Pet/Cute Pet | Pet food shortage | Material Shortage |
| Achievement_Low Spender_Collection Progress Slow | Achievement/Collection | Collection progress below 70% | Material Shortage |
| Album_Low Spender_Fragment Shortage | Album/Collection | Album fragments shortage | Material Shortage |
| Clothes_All_New Fashion Release | Character Decoration | Fashion release | Node Trigger |
| Manor_All_Seed Shortage | Manor/Farm | Seeds shortage | Material Shortage |
| Plant_All_Fertilizer Shortage | Plant Garden | Fertilizer shortage | Material Shortage |

### Gameplay Behavior Strategy Example

| Strategy Name | Gameplay Type | Trigger Scenario | Scenario Type |
|---------------|---------------|------------------|---------------|
| Stage_All_Stage Failure | Stage Challenge | Failed same stage 3 times | Failure Trigger |
| Match-3_All_Moves Exhausted | Match-3/Three-match | Moves exhausted, not cleared | Failure Trigger |
| Synthesis_All_Progress Slow | Synthesis Gameplay | Synthesis materials shortage | Material Shortage |
| Parkour_All_Death Trigger | Parkour/Adventure | Death over 3 times | Failure Trigger |
| Collection_All_Progress Slow | Collection Gameplay | Collection progress stalled 3 days | Material Shortage |
| Stage_Low Spender_Stamina Consumption | Stage Challenge | Stamina consumption reached threshold | Stamina Consumption |
| Leaderboard_High Spender_Rank Drop | Leaderboard | Rank drop over 10 positions | Failure Trigger |
| Order_All_Timeout Failure | Order Delivery | Order timeout | Failure Trigger |
| Planting_All_Crop Withered | Planting Harvest | Crop withered | Failure Trigger |
| Fishing_All_Rare Fish Caught | Fishing Gameplay | Caught rare fish | Node Trigger |

### Social Behavior Strategy Example

| Strategy Name | Gameplay Type | Trigger Scenario | Scenario Type |
|---------------|---------------|------------------|---------------|
| Friend_All_Gift Received | Friend Interaction | Received friend gift | Node Trigger |
| Visit_All_Friend Visit | Friend Interaction | Friend visited home | Node Trigger |
| Collaboration_All_Task Complete | Collaboration Task | Collaboration task complete | Node Trigger |
| Party_All_Event Start | Party Event | Party event start | Node Trigger |

---

*Inherits common rules from [_common.md](_common.md)*

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.