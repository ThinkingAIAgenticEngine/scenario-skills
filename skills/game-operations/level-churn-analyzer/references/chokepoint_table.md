# Key Chokepoint Table Template

## Usage
Display top chokepoint levels in a structured table.

## Template

```markdown
## 2. Key Chokepoint Levels (Top {top_n})

| Rank | Level | Churn Count | % of Total Churn | Level {inactive_days}-Day Churn Rate | Severity | Trend |
|------|-------|-------------|------------------|--------------------------------------|----------|-------|
| 1 | Level {level_1} | {count_1} | {pct_1}% | {rate_1}% | {severity_1} | {trend_1} |
| 2 | Level {level_2} | {count_2} | {pct_2}% | {rate_2}% | {severity_2} | {trend_2} |
| 3 | Level {level_3} | {count_3} | {pct_3}% | {rate_3}% | {severity_3} | {trend_3} |
| 4 | Level {level_4} | {count_4} | {pct_4}% | {rate_4}% | {severity_4} | {trend_4} |
| 5 | Level {level_5} | {count_5} | {pct_5}% | {rate_5}% | {severity_5} | {trend_5} |

### Severity Legend
- 🔴 **P0 (Critical)**: Immediate action required
- 🟠 **P1 (High)**: Address this week
- 🟡 **P2 (Medium)**: Address this month
- 🟢 **Normal**: Monitor

### Summary Statistics
- **Total Chokepoints**: {total_chokepoints} levels with significant churn
- **P0 Levels**: {p0_count} (requiring immediate attention)
- **P1 Levels**: {p1_count} (address this week)
- **P2 Levels**: {p2_count} (address this month)
```

## Severity Classification Rules

| Severity | Condition | Action Priority |
|----------|-----------|-----------------|
| 🔴 P0 | % of total churn > 15% OR churn rate > 40% | Immediate |
| 🟠 P1 | % of total churn > 10% OR churn rate > 30% | This week |
| 🟡 P2 | % of total churn > 5% OR churn rate > 20% | This month |
| 🟢 Normal | Below P2 thresholds | Monitor |

## Trend Indicators (for Comparison Mode)

| Trend | Symbol | Meaning |
|-------|--------|---------|
| Improved | ↓ | Churn rate decreased |
| Worsened | ↑ | Churn rate increased |
| Stable | → | No significant change |
| New | 🆕 | Newly appeared chokepoint |

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{top_n}` | Number of top levels to show | 5 |
| `{inactive_days}` | Churn threshold days | 3 |
| `{level_N}` | Level identifier | "12", "Boss_3" |
| `{count_N}` | Churn count for this level | 450 |
| `{pct_N}` | Percentage of total churn | 12.5 |
| `{rate_N}` | Churn rate for this level | 45.2 |
| `{severity_N}` | Severity emoji + label | "🔴 P0" |
| `{trend_N}` | Trend indicator | "↑", "↓", "→" |
| `{total_chokepoints}` | Total problematic levels | 15 |
| `{p0_count}` | P0 level count | 3 |
| `{p1_count}` | P1 level count | 5 |
| `{p2_count}` | P2 level count | 7 |

## Example Output

```markdown
## 2. Key Chokepoint Levels (Top 5)

| Rank | Level | Churn Count | % of Total Churn | Level 3-Day Churn Rate | Severity | Trend |
|------|-------|-------------|------------------|------------------------|----------|-------|
| 1 | Level 12 | 450 | 13.9% | 45.2% | 🔴 P0 | ↑ |
| 2 | Level 8 | 380 | 11.7% | 38.5% | 🟠 P1 | ↓ |
| 3 | Level 15 | 290 | 9.0% | 32.1% | 🟠 P1 | → |
| 4 | Level 22 | 210 | 6.5% | 28.4% | 🟡 P2 | 🆕 |
| 5 | Level 5 | 195 | 6.0% | 24.8% | 🟡 P2 | ↓ |

### Severity Legend
- 🔴 **P0 (Critical)**: Immediate action required
- 🟠 **P1 (High)**: Address this week
- 🟡 **P2 (Medium)**: Address this month
- 🟢 **Normal**: Monitor

### Summary Statistics
- **Total Chokepoints**: 15 levels with significant churn
- **P0 Levels**: 3 (requiring immediate attention)
- **P1 Levels**: 5 (address this week)
- **P2 Levels**: 7 (address this month)
```
