# Tag Hierarchy Architecture and Specification

> Used for Step 3: Generate tag definitions based on industry category.

---

## Hierarchy Architecture Overview

Tag system consists of **General Basic Layer** and **Industry Exclusive Layer**:

| Layer | Name | Type | Core value | Data source |
|-----|------|------|---------|---------|
| 1 | User profile & identity | General static profile | User basic characteristics | User property table (tableType=1) |
| 2 | Active behavior | General | User stickiness | Login/launch events (tableType=0) |
| 3 | Usage depth | General+Industry | Core function usage | Core function events (tableType=0) |
| 4 | Payment & commercial value | General | User commercial value | Payment/order events (tableType=0) |
| 5 | Industry exclusive | **Differentiation core** | Industry insight | Industry core events (tableType=0) |
| 6 | Lifecycle & comprehensive | Comprehensive | User status management | Multi-layer tag comprehensive calculation |

> ⚠️ **Important principle**: Layer 5 industry exclusive tags are the core differentiation value of this solution, must be carefully designed based on actual industry category, not apply generic templates.

---

## Layer 1: User Profile & Identity Tags

**Recommended TE tag types**: Condition Tag, SQL Tag, ID Tag

**Design principle**: Resolutely don't copy raw detail fields (such as directly output province, single device model), only design static features that need [rule calculation, status extraction, interval division or multi-field merging] to conclude.

### Tag reference

| Tag name | Tag type | Business definition | Calculation logic |
|---------|---------|---------|---------|
| Account tenure tiering | Condition tag | Registration time converted to business phase | Hatch phase (<7 days), Growth phase (7-30 days), Stable phase (1-6 months), Veteran phase (>6 months) |
| Acquisition quality attribution | Condition tag | Channel refined to macro category | High quality paid placement, social viral, organic search, matrix referral |
| Profile completeness | Condition/SQL tag | Multi-property comprehensive judgment | High (avatar+real name+bound card), Low (only registered) |
| Cross-device ecosystem | Metric value/Condition tag | Count unique devices logged in | Single device loyal user, multi-device active user |
| Risk identity feature | ID tag/SQL tag | Abnormal account identification | Black market suspect device, testing whitelist, high frequency rebind abnormal |

---

## Layer 2: Active Behavior Tags

**Recommended TE tag types**: Metric Value Tag, Condition Tag

**Design principle**: Measure user contact frequency and stickiness with product

### Tag reference

| Tag name | Tag type | Calculation logic |
|---------|---------|---------|
| Last 7 days active days | Metric value tag | Count distinct login/launch events in last 7 days |
| Last 30 days active days | Metric value tag | Count distinct login/launch events in last 30 days |
| Current consecutive active days | SQL tag | Cumulative days counting backward from today with login |
| Last active time | First-Last tag | Last login event time |
| Days inactive to today | Metric value tag | Current date - last active time |

### Active tiering (Condition tag)

| Tag value | Definition condition | Business meaning |
|-------|---------|---------|
| High active | Last 7 days active days ≥ 5 | Daily visit user |
| Medium active | Last 7 days active days 2-4 | Regular visit user |
| Low active | Last 7 days active days = 1 | Occasional visit user |
| Dormant | 7-30 days inactive | Recall possible |
| Churned | 30+ days inactive | Need strong recall or abandon |

---

## Layer 3: Usage Depth Tags

**Recommended TE tag types**: Metric Value Tag, Condition Tag

**Design principle**: Measure user depth of using product core value, need to combine industry core function definition

### General tags

| Tag name | Calculation logic |
|---------|---------|
| Last 7 days/Last 30 days usage duration | Session duration cumulative |
| Core function operation count | Core event count |
| Function coverage breadth | Used function module count |
| Usage time slot preference | Judge by time slot distribution (morning/noon/evening/late night) |

### Industry adjustment notes

- Core function event names based on real tracking
- Measurement dimension varies by industry:
  - Gaming → Battle count, dungeon participation count
  - Education → Learning duration, course completion count
  - Social → Interaction count (like/comment/share)

---

## Layer 4: Payment & Commercial Value Tags

**Recommended TE tag types**: Metric Value Tag, Condition Tag, First-Last Tag

**Design principle**: Measure user commercial value and payment behavior pattern

### Payment capability tags

| Tag name | Tag type | Calculation logic |
|---------|---------|---------|
| Cumulative payment amount | Metric value tag | Sum all payment event amounts |
| Last 30 days payment amount | Metric value tag | Sum last 30 days payment event amounts |
| Average order value | Metric value tag | Cumulative amount / cumulative count |
| Highest single payment | Metric value tag | Take maximum payment amount |

### Payment tiering (Condition tag, need to adjust threshold by industry)

| Tag value | Definition condition | Description |
|-------|---------|------|
| High Spender/High value | Monthly payment ≥ [Industry high threshold] | Core revenue source |
| Mid Spender/Mid value | Monthly payment ∈ [Industry median range] | Stable paying group |
| Low Spender/Low value | Monthly payment < [Industry low threshold] | Low contribution but convertible |
| Non-paying | Never performed payment behavior | Free user pool |

### Payment behavior tags

| Tag name | Calculation logic |
|---------|---------|
| Cumulative payment count | Payment event count |
| First payment time/amount | First payment event property |
| Days from first payment to registration | First payment date - registration date |
| Last payment time | Last payment event time |
| Days unpaid to today | Current date - last payment time |
| Average payment interval | (Last payment time - first payment time) / payment count |
| Whether last 30 days paid | Condition tag: Yes/No |

### Payment preference tags

| Tag name | Calculation logic |
|---------|---------|
| Most purchased product type | Take maximum by product type frequency |
| Product price preference | High price/Mid price/Low price preference |
| Promotion sensitivity | Promotion period payment ratio |

---

## Layer 5: Industry Exclusive Tags ⭐ Core Differentiation

> This layer must be customized based on identified **Industry + Sub-category**, reference `industry-dict.md` sub-category exclusive tag focus.

**Design principles**:
1. Must reflect industry category difference, different categories should not have identical content
2. Event names and property names come from real tracking
3. Tag value tiering has clear business meaning

### Design method

1. Determine core behavior events based on sub-category (e.g.: Gaming's battle, Education's lesson_complete)
2. Design 5-10 depth tags around core behavior
3. Supplement differentiation tags combining category feature keywords (reference industry-dict.md)

---

## Layer 6: Lifecycle & Comprehensive Tags

**Recommended TE tag types**: Condition Tag, SQL Tag

**Design principle**: Define lifecycle phases comprehensively combining user activity, payment, industry exclusive behavior

### Lifecycle phases (Condition tag, need to adjust by industry)

| Phase | Definition condition | Description |
|-----|---------|------|
| Newbie phase | Registered within 7 days, not completed core behavior | Need guidance nurturing |
| Growth phase | Registered 7-30 days, completed core behavior but not paid | Potential paying user |
| Mature phase | Paid and active | Core value user |
| High value phase | High payment + high active + industry core behavior high frequency | VIP user |
| Decline phase | Previously paid, activity significantly dropped | Need retention |
| Dormant phase | 7-30 days inactive | Recall possible |
| Churned phase | 30+ days inactive | Need strong recall |
| Return phase | Active again after churn | Successfully recalled user |

### Comprehensive value tags

| Tag name | Calculation logic |
|---------|---------|
| RFM comprehensive score | R (last active timeliness) + F (frequency) + M (amount) comprehensive calculation |
| User value level | High value/Mid value/Low value/Negative value |
| Churn risk warning | Activity last 7 days dropped >50% + last payment >30 days |
| Return user mark | Active again within 7 days after churn |

---

## TE Tag Type Selection Guide

| Tag type | Applicable scenario | Typical example |
|---------|---------|---------|
| **Condition Tag** | Divide users into mutually exclusive categories | Active tiering, Payment tiering, Lifecycle phase |
| **Metric Value Tag** | Calculate numerical value within time range | Last 30 days payment amount, Last 7 days active days |
| **First-Last Tag** | Record first/last event time or property | First payment amount, Last active time |
| **SQL Tag** | Complex calculation (consecutive days, ratio, ranking) | Consecutive active days, Payment conversion rate |
| **ID Tag** | Import external list | VIP list, Test accounts, Risk control blacklist |

---

## Field Validation Principles

### Basic validation rules

- **Must use real fields**: Event names and property names must come from metadata query results
- **Field missing handling**: Cannot fabricate, must point out in [Missing field supplement suggestions], provide:
  - Existing field alternative solution
  - Suggest adding tracking event or property
- **Property value format validation**: Numeric properties need to confirm value range, enum type need to confirm available value list

### Field substitutability check process

```
When target field does not exist:
1. Search synonymous/similar properties (e.g.: pay_amount → payment_value, order_price)
2. Search related events (e.g.: no payment event → check order event, recharge event)
3. Search derivable properties (e.g.: no registration time → infer through first login time)
4. If none above feasible → Clearly mark [Need add tracking] and explain specific requirement
```

### Common field substitution examples

| Original target field | Alternative solution | Substitution logic explanation |
|-----------|---------|-------------|
| `register_time` | `first_login_time` | First login can approximately represent registration time |
| `pay_amount` | `order_total_price` | Order total price approximately payment amount |
| `vip_level` | `user_type` + `subscription_status` | Combine to judge VIP identity |
| `battle_duration` | `session_duration` in battle events | Infer from battle event session duration |

---

## Tag Naming Specification

> Unified naming rules help tag system maintainability and retrievability.

### Basic naming rules

| Rule | Description | Correct example | Wrong example |
|-----|------|---------|---------|
| Use Chinese or English lowercase + underscore | Avoid mixed naming confusion | `Last 7 days active days` / `act_7d_days` | `Last 7 daysActiveDays` |
| Time range prefix | Time dimension explicit priority | `Last 30 days payment amount` | `Payment amount last 30 days` |
| Industry prefix differentiation | Multi-business line scenario prevent confusion | `game_battle_freq` / `edu_course_complete` | Single `Battle frequency` |
| Tag layer code optional | Large scale system easy management | `l2_act_7d_days` | No code hard to locate |

### Tag group naming suggestion

```
Group prefix example (Recommended lowercase + underscore):
- act_: Active behavior class (act_7d_days, act_level)
- pay_: Payment commercial class (pay_total, pay_level)
- use_: Usage depth class (use_duration, use_func_coverage)
- life_: Lifecycle class (life_stage, life_risk)
- ind_: Industry exclusive class (ind_game_battle_freq)

Coding style selection:
- Recommended: Pure lowercase + underscore (act_7d_days) → Modern standard, good compatibility, easy input
- Optional: All uppercase (ACT_7D_DAYS) → Constant style, eye-catching but hard input
- Avoid: Mixed case (ACT_7d_Days) → Error prone, hard maintenance
```

---

## Tag Update and Maintenance Strategy

### Tag calculation period

| Period type | Applicable tag type | Typical tag | Update mechanism |
|---------|-------------|---------|---------|
| **Real-time/Near real-time** | ID tag, Key status tag | VIP identity, Ban status | Data import trigger |
| **Daily update** | Metric value tag, Condition tag | Last 7 days active days, Active tiering | TE scheduled task |
| **Weekly update** | Weekly dimension statistics tag | Last 7 days weekly active, Weekly payment amount | TE scheduled task |
| **Monthly update** | Monthly dimension statistics, Lifecycle tag | Last 30 days payment amount, Lifecycle phase | TE scheduled task |
| **Quarterly/Annual** | Long cycle profile tag | Annual consumption total, Account tenure tiering | Manual trigger or annual task |

### Tag version management

- **Tag change record**: Each modification of tag logic must record change reason, impact scope
- **Deprecated tag handling**: Mark deprecated time, keep 3 months before delete, avoid downstream dependency interruption
- **Tag canary release**: New tag first small scope validation, confirm stable then full launch

### Tag health check

| Check item | Check method | Abnormal threshold | Handling suggestion |
|-------|---------|---------|---------|
| Coverage rate abnormal | Users with tag value / total users | <10% or >95% possibly abnormal | Check if calculation logic too strict or loose |
| Value distribution abnormal | Each tag value ratio | Single value ratio >80% | Tiering threshold may need adjustment |
| Calculation failure rate | Failed users / should calculate users | >5% | Check data source field completeness |
| Timeliness abnormal | Tag update time to current | >预设周期×1.5 | Check if task executing normally |

---

## Tag Effect Evaluation and Iteration

### Evaluation dimensions

| Dimension | Evaluation metric | Evaluation method |
|-----|---------|---------|
| **Business relevance** | Tag correlation with business goal | Tag value distribution and key indicator (retention/payment) correlation analysis |
| **Discrimination ability** | Difference degree between different tag value users | Retention rate/payment rate variance by each tag value user |
| **Stability** | Tag value distribution time stability | Consecutive multi-cycle tag value distribution change amplitude |
| **Practicality** | Business application frequency and feedback | Operation/product team usage feedback, automated strategy invocation frequency |

### Tag iteration process

```
1. Identify problem tags (Coverage abnormal / Low discrimination / Poor stability)
2. Analyze root cause (Threshold unreasonable / Data source missing / Calculation logic error)
3. Design optimization solution (Adjust threshold / Supplement data source / Rewrite logic)
4. Canary validation (New old tags parallel compare effect)
5. Full replacement (Confirm optimization effective then official launch)
```

### Tag elimination mechanism

- **Consecutive 3 months no business invocation** → Mark as [Pending elimination]
- **Elimination process**: Notify downstream users → Mark deprecated → Delete after 3 months
- **Retention exception**: Basic profile tags (e.g.: gender, tenure) keep even if invocation low

---

## Common Problems and Pitfall Avoidance Guide

### Design stage common problems

| Problem | Manifestation | Solution |
|-----|------|---------|
| **Too many too detailed tags** | Same dimension splits dozens of tags | Reasonably converge, one dimension no more than 10 tags |
| **Naming meaning vague** | `User level 1/2/3` no business meaning | Use concrete names: `Newbie/Growth/Mature/VIP` |
| **Threshold template copy** | Payment tiering directly use gaming threshold | Must adjust according to industry average order value |
| **Ignore data source limit** | Design tag then find field missing | First check metadata, then design tag |

### Calculation stage common problems

| Problem | Manifestation | Solution |
|-----|------|---------|
| **Time window inconsistent** | [Last 7 days] actually calculates last 10 days | Clarify time window definition (include/exclude current day) |
| **Distinct logic missing** | Active days not distinct causing inflated | Clearly mark [Count distinct] |
| **Null value improper handling** | Null value participates calculation causing abnormal result | Clarify null exclusion or special value handling rule |
| **Boundary attribution error** | [Last 7 days active ≥5] boundary attribution unclear | Clarify boundary attribution (≥5 belongs to high active or medium active) |

### Application stage common problems

| Problem | Manifestation | Solution |
|-----|------|---------|
| **Tag timeliness ignored** | Use monthly update tag for daily level strategy | Tag selection confirm update period matches strategy timeliness |
| **Tag combination no business explanation** | Combined tag no clear cohort definition | Combined tag needs clear business cohort profile description |
| **Over rely single tag** | Key strategy only relies on one tag | Core strategy should rely on multi-dimension tag combination |

---

## Industry Exclusive Tag Design Examples

> This section provides several typical industry exclusive tag examples, for reference but **cannot directly apply**, must adjust according to actual tracking and business.

### Gaming Industry Example (MMORPG type)

| Tag name | Tag type | Calculation logic | Business meaning |
|---------|---------|---------|---------|
| Battle activity | Condition tag | Last 7 days battle count tiering | High freq warrior (≥50) / Regular player (10-50) / Casual player (<10) |
| PVP participation | Condition tag | PVP battle count ratio | PVP enthusiast / Balanced player / PVE preferencer |
| Dungeon progress | Metric value tag | Cleared dungeon count | Game progress assessment |
| Social activity | Metric value tag | Team count + guild interaction count | Social player identification |
| Resource accumulation speed | Metric value tag | Last 7 days gold/diamond increment | Consumption potential assessment |

### Education Industry Example (Online course type)

| Tag name | Tag type | Calculation logic | Business meaning |
|---------|---------|---------|---------|
| Learning engagement | Condition tag | Last 7 days learning duration tiering | Deep learner (≥3h) / Light learner (<1h) |
| Course completion progress | Metric value tag | Completed course count / total enrolled course count | Learning progress tracking |
| Knowledge point mastery | Metric value tag | Quiz correct rate | Learning effect assessment |
| Learning time slot preference | Condition tag | Learning time slot distribution | Early bird type / Night owl type / Fragment time type |
| Review behavior intensity | Metric value tag | Course repeat view count | Learning habit analysis |

### E-commerce Industry Example (General e-commerce type)

| Tag name | Tag type | Calculation logic | Business meaning |
|---------|---------|---------|---------|
| Shopping frequency tiering | Condition tag | Last 30 days order count | High freq buyer (≥5) / Medium freq (2-4) / Low freq (1) |
| Category preference | Condition tag | Main purchase category ratio | Vertical category preference / All category browsing type |
| Price sensitivity | Metric value tag | Low price product purchase ratio | Price sensitive type / Quality first type |
| Add-to-cart conversion rate | Metric value tag | Order count / add-to-cart count | Purchase willingness strength |
| Refund tendency | Metric value tag | Refund order count / total order count | Service quality risk |

---

## Appendix: Tag Configuration Checklist Template

> Core information checklist when tag landing configuration

### Single tag configuration information

```yaml
Tag name: [Chinese name]
Tag code: [Optional, e.g.: act_7d_days]
Tag type: [Condition tag/Metric value tag/First-Last tag/SQL tag/ID tag]
Tag layer: [1-6 layers]
Belongs to group: [Active/Payment/Usage/Lifecycle/Industry exclusive]
Business definition: [One sentence business meaning]
Calculation logic:
  - Data source event: [Event name]
  - Data source property: [Property name]
  - Calculation formula/rule: [Specific logic]
  - Time window: [Last 7 days/Last 30 days/Full etc.]
Tag value definition: [Each tag value and corresponding condition]
Update period: [Daily/Weekly/Monthly]
Dependency field check: [Already exists/Need add/Alternative solution]
```

### Tag system checklist summary

```markdown
| No. | Tag name | Tag type | Layer | Update period | Data source event | Tag code | Status |
|-----|---------|---------|-----|---------|-----------|------|
| 1 | Last 7 days active days | Metric value | L2 | Daily | app_launch | act_7d_days | Configured |
| 2 | Active tiering | Condition | L2 | Daily | app_launch | act_level | Pending config |
| ... | ... | ... | ... | ... | ... | ... |
```

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.