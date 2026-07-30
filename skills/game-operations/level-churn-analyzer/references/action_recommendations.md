# Action Recommendations Template

## Usage
Generate prioritized, actionable recommendations with expected impact.

## Template

```markdown
## {section_number}. Action Recommendations

### 🔴 Immediate Actions (This Week)

**Priority 1: Address {p0_level_count} P0 Critical Levels**

{for each P0 level}
#### Level {level_id} - {severity_emoji} {severity_label}
- **Impact**: Affects {impact_users} users ({impact_pct}% of churn)
- **Expected Improvement**: {expected_reduction}% churn reduction
- **Actions**:
  1. {action_1}
  2. {action_2}
- **Effort**: {effort}
- **Owner**: {owner}
- **Deadline**: {deadline}
{/for}

---

### 🟠 Short-term Actions (This Month)

**Priority 2: Address {p1_level_count} P1 High Priority Levels**

{for each P1 level}
#### Level {level_id}
- **Impact**: {impact_users} users ({impact_pct}%)
- **Expected Improvement**: {expected_reduction}%
- **Actions**:
  1. {action_1}
  2. {action_2}
- **Effort**: {effort}
{/for}

**Priority 3: System-wide Improvements**

| Initiative | Expected Impact | Effort | Owner |
|-----------|-----------------|--------|-------|
| {initiative_1} | {impact_1} | {effort_1} | {owner_1} |
| {initiative_2} | {impact_2} | {effort_2} | {owner_2} |

---

### 🟡 Medium-term Actions (Next Quarter)

**Priority 4: Strategic Improvements**

1. **{strategic_item_1}**
   - Goal: {goal_1}
   - Approach: {approach_1}
   - Success Metric: {metric_1}

2. **{strategic_item_2}**
   - Goal: {goal_2}
   - Approach: {approach_2}
   - Success Metric: {metric_2}

---

### 📊 Impact Summary

| Priority Level | Levels | Users Affected | Est. Churn Reduction | Timeline |
|---------------|--------|----------------|---------------------|----------|
| 🔴 Immediate | {p0_count} | {p0_users} | {p0_reduction}% | This week |
| 🟠 Short-term | {p1_count} | {p1_users} | {p1_reduction}% | This month |
| 🟡 Medium-term | {p2_count} | {p2_users} | {p2_reduction}% | This quarter |
| **Total** | **{total_levels}** | **{total_users}** | **{total_reduction}%** | **-** |

---

### 🎯 Success Metrics to Track

**Primary KPIs**:
- [ ] Overall {inactive_days}-day churn rate: {current_overall}% → Target: {target_overall}%
- [ ] P0 level count: {current_p0} → Target: {target_p0}

**Level-specific KPIs**:
{for each tracked level}
- [ ] Level {level_id} churn rate: {current_rate}% → Target: {target_rate}%
{/for}

**Process KPIs**:
- [ ] Action completion rate: Target {action_completion_target}%
- [ ] Time to fix P0 issues: Target {time_to_fix} days

---

### 🔄 Follow-up Schedule

| Check-in | Date | Focus | Deliverable |
|----------|------|-------|-------------|
| 3-day review | {date_3d} | Quick wins assessment | Status update |
| 1-week review | {date_1w} | P0 resolution | P0 closure report |
| 2-week review | {date_2w} | P1 progress | Progress dashboard |
| Monthly review | {date_1m} | Full impact analysis | Impact report |

---

### 📝 Action Items Template

Copy this for project tracking:

```
[ ] Fix Level {level_id} - {brief_description}
   Owner: @{owner}
   Due: {due_date}
   Acceptance Criteria:
   - Churn rate reduced from {current}% to {target}%
   - No negative impact on other metrics
```
```

## Universal Optimization Measures Library

### By Problem Type

| Problem Type | Recommended Action | Expected Impact | Effort | Confidence |
|-------------|-------------------|-----------------|--------|------------|
| **Excessive difficulty** | Reduce enemy HP / Decrease obstacles / Increase time limit | +10-20% pass rate | Low | High |
| **Beginner chokepoint** | Add guidance hints / Simplify controls / Lower early difficulty | +5-10% new user retention | Medium | High |
| **Low forgiveness** | Add checkpoints / Increase moves / Add continue mechanic | Reduced frustration | Low | Medium |
| **Excessive cooldown** | Push recall notification / Gift retry items / Lower retry cost | +15-25% return rate | Low | High |
| **Unclear mechanics** | Add tutorial step / Show hints / Demonstrate mechanic | Reduced invalid attempts | Medium | High |

### By Game Type

| Game Type | Common Issues | Targeted Actions | Expected Impact |
|-----------|--------------|------------------|-----------------|
| **Card** | Deck counters, insufficient cards | Add card drops in prior levels; Trial cards | +8-12% pass rate |
| **RPG** | Boss mechanics, power gates | Lower boss stats; Gear-up side quests | +10-15% completion |
| **Match-3** | Move limits, special obstacles | +2 moves; Lower spawn rate | +15-20% pass rate |
| **Runner** | Speed requirements, obstacle density | Reduce speed; Add warning indicators | +5-10% survival |
| **SLG** | Resource scarcity, strategy complexity | Increase resource drops; Simplify objectives | +10% progression |
| **Casual** | Wait times, complex controls | Reduce CDs; Simplify inputs | +5-8% engagement |
| **MOBA** | Matchmaking, skill gap | Newbie pool; AI practice | +5-10% retention |
| **Idle** | Progress bottlenecks, number gates | Increase offline earnings; Boost items | +10-15% progression |

## Intervention Strategies Library

### Immediate (Within 24h of failure)
- Push level-specific guide/tips notification
- Offer free revive or continue
- Gift power-up items
- Show "You were close!" encouragement

### Recall (3-7 days after churn)
- "Stuck at Level X?" push notification
- Offer "Skip this level" option (one-time)
- "We've made it easier!" return campaign
- Gift package with level-specific counter items

### Pre-emptive (Before entering level)
- Prior level power-up opportunities
- Difficulty warning for known chokepoints
- Optional practice mode
- Power recommendation check

## Effort Levels

| Level | Description | Typical Time | Examples |
|-------|-------------|--------------|----------|
| **Low** | Configuration changes | Hours - 1 day | Adjust numbers, add items |
| **Medium** | Content modifications | Days - 1 week | Add checkpoints, redesign section |
| **High** | System changes | Weeks - 1 month | New mechanics, progression redesign |
| **Very High** | Major overhaul | 1+ months | Full level redesign, new features |

## Confidence Levels

| Level | Criteria | How to Increase |
|-------|----------|-----------------|
| **Very High** | Strong data (>1000 users), clear pattern, proven solution | - |
| **High** | Good data (>500 users), identifiable pattern | Add more data sources |
| **Medium** | Limited data, some pattern visible | Run A/B test |
| **Low** | Small sample, unclear pattern | Gather more data first |

## Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `{section_number}` | Section number | "5" |
| `{level_id}` | Level identifier | "12" |
| `{impact_users}` | Number of users affected | 450 |
| `{impact_pct}` | Percentage of total churn | 13.9 |
| `{expected_reduction}` | Expected churn reduction % | 8.5 |
| `{effort}` | Effort level | "Low", "Medium", "High" |
| `{owner}` | Responsible team/person | "Level Design Team" |
| `{deadline}` | Target completion date | "2026-05-25" |

## Example Output

```markdown
## 5. Action Recommendations

### 🔴 Immediate Actions (This Week)

**Priority 1: Address 2 P0 Critical Levels**

#### Level 12 - 🔴 Critical
- **Impact**: Affects 450 users (13.9% of churn)
- **Expected Improvement**: 8-12% churn reduction
- **Actions**:
  1. Reduce boss HP by 15% and add attack telegraphing
  2. Add checkpoint before boss encounter
- **Effort**: Low
- **Owner**: @LevelDesign
- **Deadline**: 2026-05-20

#### Level 8 - 🔴 Critical
- **Impact**: Affects 380 users (11.7% of churn)
- **Expected Improvement**: 10-15% churn reduction
- **Actions**:
  1. Increase time limit by 30 seconds
  2. Reduce obstacle spawn rate
- **Effort**: Low
- **Owner**: @LevelDesign
- **Deadline**: 2026-05-20

---

### 📊 Impact Summary

| Priority Level | Levels | Users Affected | Est. Churn Reduction | Timeline |
|---------------|--------|----------------|---------------------|----------|
| 🔴 Immediate | 2 | 830 | 18-27% | This week |
| 🟠 Short-term | 5 | 1,240 | 12-18% | This month |
| 🟡 Medium-term | 8 | 890 | 8-12% | This quarter |
| **Total** | **15** | **2,960** | **38-57%** | **-** |
```
