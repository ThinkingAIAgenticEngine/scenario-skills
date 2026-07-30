# churn-define | Industry Reference & Cases

## Gaming Industry

### Churn Definition Reference

| Game Type | Recommended Churn Days | Description |
|---|---|---|
| SLG (Strategy) | 7-14 days | Long cultivation cycle, 7 days without login typically indicates churn |
| MMO (Massive Multiplayer) | 3-7 days | Strong social attributes, 3 days without login may indicate churn |
| Casual | 1-3 days | High frequency, 1 day without login can indicate churn |
| Card Games | 7 days | Daily task-driven, 7 days without login is standard churn line |
| Idle Games | 14-30 days | Players can be offline, churn threshold is relatively longer |

### Segmentation Dimension Recommendations

#### Dimension 1: Payment Value

```
Segmentation Criteria:
- High Value: Cumulative payment >= 1000 CNY
- Medium Value: Cumulative payment 100-1000 CNY
- Low Value: Cumulative payment < 100 CNY
- Non-Paying: Cumulative payment = 0

Business Significance:
- High-value user churn → Priority recall, can invest more resources
- Low-value user churn → Consider automated recall or give up
```

#### Dimension 2: Level/Progress

```
Segmentation Criteria (using SLG as example):
- High Level: Level >= 30
- Medium Level: Level 15-30
- Low Level: Level < 15

Business Significance:
- High-level user churn → Possibly insufficient content or social conflict
- Low-level user churn → Possibly insufficient new player guidance
```

#### Dimension 3: Lifecycle Days

```
Segmentation Criteria:
- New Users: Registered <= 7 days
- Growth Phase: Registered 8-30 days
- Mature Phase: Registered > 30 days

Business Significance:
- New user churn → New player guidance issues
- Mature user churn → Content/social issues
```

#### Dimension 4: Activity Level

```
Segmentation Criteria (last 30 days):
- High Activity: Login days >= 20 days
- Medium Activity: Login days 10-20 days
- Low Activity: Login days < 10 days

Business Significance:
- High-activity user churn → Sudden incident (version issue, social conflict)
- Low-activity user churn → Long-term dissatisfaction
```

### Real-World Cases

#### Case 1: SLG Game Churn Analysis

**Background:** An SLG game with 500K daily active users, 35% 7-day churn rate

**Churn Definition:** 7 days without login

**Segmentation Dimensions:** Payment Value × Level × Activity Level

**Findings:**
- High-value users (payment > 1000 CNY) churn rate only 5%
- Low-value users (non-paying) churn rate 60%
- New player stage (level < 15) churn rate 70%

**Actions:**
- Prioritize improving new player guidance to reduce new user churn
- Use automated recall for low-value users
- Use manual operations for high-value users

#### Case 2: Casual Game Churn Analysis

**Background:** A casual game with 1M daily active users, 45% 1-day churn rate

**Churn Definition:** 1 day without login

**Segmentation Dimensions:** Activity Level × Lifecycle

**Findings:**
- New users (registered <= 7 days) 1-day churn rate 80%
- Mature users (registered > 30 days) 1-day churn rate 20%
- High-activity users churn rate far lower than low-activity users

**Actions:**
- Strengthen new user retention, optimize new player experience
- Use content updates to drive engagement for mature users

---

## Social Products

### Churn Definition Reference

| Product Type | Recommended Churn Days | Description |
|---|---|---|
| Short Video | 1-3 days | High frequency, 1 day without login can indicate churn |
| Social Network | 3-7 days | Medium frequency, 3-7 days without login is churn line |
| Live Streaming | 3-7 days | Content-driven, 3-7 days without login is churn line |
| Community | 7-14 days | Low frequency, 7-14 days without login is churn line |

### Segmentation Dimension Recommendations

#### Dimension 1: Follower Count

```
Segmentation Criteria:
- Influencer: Followers >= 10,000
- Medium: Followers 1,000-10,000
- Small Account: Followers < 1,000

Business Significance:
- Influencer churn → Affects platform content ecosystem
- Small account churn → Affects user base
```

#### Dimension 2: Content Contribution

```
Segmentation Criteria (last 30 days):
- High Contribution: Published content >= 10 posts
- Medium Contribution: Published content 3-10 posts
- Low Contribution: Published content < 3 posts

Business Significance:
- High-contribution user churn → Content ecosystem damaged
- Low-contribution user churn → User base decline
```

---

## Tool Products

### Churn Definition Reference

| Product Type | Recommended Churn Days | Description |
|---|---|---|
| Productivity Tools | 7-14 days | Work-driven, 7-14 days without usage is churn line |
| Learning Tools | 3-7 days | Learning-driven, 3-7 days without usage is churn line |
| Health Tools | 7-30 days | Habit-driven, 7-30 days without usage is churn line |

### Segmentation Dimension Recommendations

#### Dimension 1: Usage Frequency

```
Segmentation Criteria (last 30 days):
- High Frequency: Usage days >= 20 days
- Medium Frequency: Usage days 10-20 days
- Low Frequency: Usage days < 10 days

Business Significance:
- High-frequency user churn → Product issues or competitor impact
- Low-frequency user churn → Usage habit not formed
```

#### Dimension 2: Feature Coverage

```
Segmentation Criteria:
- Power Users: Used features >= 5
- Medium Users: Used features 2-5
- Light Users: Used features < 2

Business Significance:
- Power user churn → Product issues
- Light user churn → Insufficient feature discovery
```

---

## Segmentation Dimension Selection Framework

### Step 1: Confirm Product Characteristics

| Characteristic | Recommended Dimensions |
|---|---|
| Payment-driven | Payment Value, Payment Frequency |
| Content-driven | Content Consumption, Content Contribution |
| Social-driven | Follower Count, Interaction Frequency |
| Progress-driven | Level, Progress, Lifecycle |
| Habit-driven | Activity Level, Usage Frequency |

### Step 2: Choose 2-3 Dimension Combination

**Principles:**
- No more than 3 dimensions (avoid over-segmentation)
- Dimensions should be relatively independent (don't choose highly correlated dimensions)
- Dimensions should guide operational decisions

**Example Combinations:**
- Gaming: Payment Value + Level + Activity Level
- Social: Follower Count + Content Contribution
- Tool: Usage Frequency + Feature Coverage

---

## Common Segmentation Interval Reference

### Payment Value Segmentation

```
High-end Market (ARPU > 100):
- High Value: >= 1000 CNY
- Medium Value: 100-1000 CNY
- Low Value: < 100 CNY

Mid-market (ARPU 10-100):
- High Value: >= 100 CNY
- Medium Value: 10-100 CNY
- Low Value: < 10 CNY

Low-end Market (ARPU < 10):
- High Value: >= 10 CNY
- Medium Value: 1-10 CNY
- Low Value: < 1 CNY
```

### Level Segmentation (Gaming)

```
SLG/MMO:
- High Level: >= 30
- Medium Level: 15-30
- Low Level: < 15

Card Games/Idle Games:
- High Level: >= 50
- Medium Level: 25-50
- Low Level: < 25
```

### Activity Level Segmentation (Last 30 Days)

```
High-frequency Products (DAU > 50%):
- High Activity: >= 20 days
- Medium Activity: 10-20 days
- Low Activity: < 10 days

Medium-frequency Products (DAU 10-50%):
- High Activity: >= 15 days
- Medium Activity: 7-15 days
- Low Activity: < 7 days

Low-frequency Products (DAU < 10%):
- High Activity: >= 10 days
- Medium Activity: 5-10 days
- Low Activity: < 5 days
```

---

## Usage Suggestions

1. **Reference is not Standard**: These data are industry references and need adjustment based on your product characteristics
2. **Data Validation**: After recommending dimensions, suggest users first check the data distribution to confirm if segmentation is reasonable
3. **Iterative Optimization**: The first version may not be perfect, suggest users adjust later based on operational results
4. **Industry Benchmarking**: If you have competitor data, you can calibrate and adjust accordingly
