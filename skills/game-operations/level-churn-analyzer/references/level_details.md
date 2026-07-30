# Level Details Section Template

## Usage
Deep dive into a specific chokepoint level.

## Template

```markdown
## 3. Top Chokepoint Level Details

### {severity_emoji} Level {level_id} - {severity_label}

#### Churn Attribution Data
- **Level {inactive_days}-Day Churn Count**: {churn_count} users
- **Level Total Challenging Users**: {total_users}
- **Level {inactive_days}-Day Churn Rate**: **{churn_rate}%**
- **% of Segment Total Churn**: {pct_of_total}%

#### Level Performance Metrics
- **Total Attempts**: {total_attempts}
- **Average Attempts per User**: {avg_attempts}
- **Overall Pass Rate**: {pass_rate}%
- **First-Attempt Pass Rate**: {first_attempt_pass_rate}%
- **Retry Rate After Failure**: {retry_rate}%
- **Average Retry Interval**: {retry_interval} hours

#### User Demographics
- **New User Ratio**: {new_user_ratio}%
- **Paid User Ratio**: {paid_user_ratio}%
- **Free User Ratio**: {free_user_ratio}%
- **Average Game Days**: {avg_game_days}
- **Average User Level/Power**: {avg_user_power}

#### 3-Day Return Analysis
- **Users Who Churned at This Level**: {churned_count}
- **Returned Within 3 Days**: {returned_count}
- **3-Day Return Rate**: **{return_rate}%**
- **Return Quality**: {return_quality}

#### Root Cause Diagnosis
**Primary Cause**: {primary_cause}

**Contributing Factors**:
1. {factor_1}
2. {factor_2}
3. {factor_3}

**Evidence**:
- {evidence_1}
- {evidence_2}

#### Game Type Specific Analysis
**Identified Issues for {game_type}**:
- {issue_1}
- {issue_2}

#### Recommended Actions

**Immediate (This Week)**:
1. {immediate_action_1}
2. {immediate_action_2}

**Short-term (This Month)**:
1. {short_term_action_1}
2. {short_term_action_2}

**Long-term (Next Quarter)**:
1. {long_term_action_1}

#### Expected Impact
- **Estimated Churn Reduction**: {estimated_reduction}%
- **Affected User Count**: ~{affected_users} users
- **Implementation Effort**: {effort_level}
- **Confidence Level**: {confidence_level}
```

## Root Cause Library

| Data Pattern | Inferred Cause | Threshold |
|--------------|----------------|-----------|
| New user ratio > 70% | Difficulty mismatch for beginners | > 70% |
| Avg attempts > 4 | Insufficient forgiveness | > 4 |
| Retry interval > 24h | Excessive cooldown after failure | > 24h |
| Return rate < 10% | Failed return mechanism | < 10% |
| Pass rate < 30% | Excessive difficulty | < 30% |
| First-attempt pass rate < 20% | Poor onboarding | < 20% |

## Game Type Specific Issues

| Game Type | Common Issues | Indicators |
|-----------|---------------|------------|
| **Card** | Enemy deck counters, insufficient cards | High fail rate on specific enemy types |
| **RPG** | Boss mechanics, power gates | Power distribution vs pass rate gap |
| **Match-3** | Move limits, special obstacles | High attempt count, low pass rate |
| **Runner** | Speed requirements, obstacle density | Quick fails, low retry rate |
| **SLG** | Resource scarcity, strategy complexity | Long session before attempt |
| **Casual** | Wait times, complex controls | Early exits, low engagement |
| **MOBA** | Matchmaking, skill gap | Variable performance metrics |
| **Idle** | Progress bottlenecks | Long gaps between attempts |

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{severity_emoji}` | Visual severity indicator | 🔴, 🟠, 🟡, 🟢 |
| `{severity_label}` | Severity description | "Critical Chokepoint" |
| `{level_id}` | Level identifier | "12", "Boss_3" |
| `{inactive_days}` | Churn threshold | 3 |
| `{churn_count}` | Users churned at this level | 450 |
| `{total_users}` | Total users challenging this level | 995 |
| `{churn_rate}` | Calculated churn rate | 45.2 |
| `{pct_of_total}` | % of all churns | 13.9 |
| `{total_attempts}` | Total challenge attempts | 3200 |
| `{avg_attempts}` | Average attempts per user | 3.2 |
| `{pass_rate}` | Level pass rate | 35.6 |
| `{first_attempt_pass_rate}` | First-time pass rate | 24.3 |
| `{retry_rate}` | Users who retry after fail | 68.5 |
| `{retry_interval}` | Hours between retries | 18.5 |
| `{new_user_ratio}` | % new users | 78 |
| `{paid_user_ratio}` | % paid users | 9 |
| `{free_user_ratio}` | % free users | 91 |
| `{avg_game_days}` | Average days since first play | 5.2 |
| `{avg_user_power}` | Average user power/level | "Level 15, 2,450 power" |
| `{churned_count}` | Total churned at this level | 450 |
| `{returned_count}` | Users who returned | 31 |
| `{return_rate}` | 3-day return rate | 6.9 |
| `{return_quality}` | Assessment | "Low - improve recall mechanism" |
| `{primary_cause}` | Main identified cause | "Difficulty mismatch for beginners" |
| `{game_type}` | Game genre | "RPG" |
| `{effort_level}` | Implementation effort | "Medium - requires level redesign" |
| `{confidence_level}` | Confidence in recommendation | "High - supported by strong evidence" |
| `{estimated_reduction}` | Expected churn reduction | 8.5 |
| `{affected_users}` | Users who would benefit | 380 |

## Example Output

```markdown
## 3. Top Chokepoint Level Details

### 🔴 Level 12 - Critical Chokepoint

#### Churn Attribution Data
- **Level 3-Day Churn Count**: 450 users
- **Level Total Challenging Users**: 995
- **Level 3-Day Churn Rate**: **45.2%**
- **% of Segment Total Churn**: 13.9%

#### Level Performance Metrics
- **Total Attempts**: 3,184
- **Average Attempts per User**: 3.2
- **Overall Pass Rate**: 35.6%
- **First-Attempt Pass Rate**: 24.3%
- **Retry Rate After Failure**: 68.5%
- **Average Retry Interval**: 18.5 hours

#### User Demographics
- **New User Ratio**: 78%
- **Paid User Ratio**: 9%
- **Free User Ratio**: 91%
- **Average Game Days**: 5.2
- **Average User Level/Power**: Level 12, 2,450 power

#### 3-Day Return Analysis
- **Users Who Churned at This Level**: 450
- **Returned Within 3 Days**: 31
- **3-Day Return Rate**: **6.9%**
- **Return Quality**: Low - improve recall mechanism

#### Root Cause Diagnosis
**Primary Cause**: Difficulty mismatch for beginners

**Contributing Factors**:
1. First-boss encounter without adequate preparation
2. No warning about difficulty spike
3. Insufficient power gain from previous levels

**Evidence**:
- First-attempt pass rate only 24.3% (very low)
- 78% of churned users are new (< 7 days)
- Retry rate high (68.5%) but return rate low (6.9%)

#### Game Type Specific Analysis
**Identified Issues for RPG**:
- Boss mechanics too complex for current gear level
- No alternative progression paths available

#### Recommended Actions

**Immediate (This Week)**:
1. Reduce boss HP by 15% and add telegraphing for attacks
2. Add pre-boss checkpoint and power-up opportunity

**Short-term (This Month)**:
1. Create optional side quest for gear before boss
2. Add "practice mode" with no penalty

**Long-term (Next Quarter)**:
1. Redesign level 11-12 progression curve

#### Expected Impact
- **Estimated Churn Reduction**: 8-12%
- **Affected User Count**: ~380 users
- **Implementation Effort**: Low-Medium
- **Confidence Level**: High - supported by strong evidence
```
