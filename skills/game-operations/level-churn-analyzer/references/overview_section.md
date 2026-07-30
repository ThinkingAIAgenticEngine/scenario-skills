# Report Section Template

## Usage
Standard report header and overview section for all diagnostic reports.

## Template

### Report Header

```markdown
# Level Churn Diagnostic Report

## Analysis Configuration
- Analysis Mode: {mode_desc}
- Level Type: {level_type}
- Level Range: {level_range}
- Time Range: {start_date} ~ {end_date}
- Analysis Date: {report_date}
```

### Overview Section

```markdown
## 1. Analysis Overview

### Target Population
- **Segment**: {user_segment_desc} (e.g., All users / New users / Silent users / Custom)
- **Segment Definition**: {user_segment_definition}
- **Churn Definition**: {inactive_days} days of inactivity

### Key Metrics
- **Total Challenging Users**: {total_users}
- **Churned Users**: {total_churned_users}
- **Overall {inactive_days}-Day Churn Rate**: **{overall_churn_rate}%** ({total_churned_users}/{total_users})
- **Traceable to Last Level**: {traceable_count} ({traceable_rate}%)
- **Level Concentration Zone**: {concentrated_zone}

### Data Quality Indicators
- Sample Size: {sample_size} users
- Data Completeness: {completeness}%
- Recommended Action: {data_quality_recommendation}
```

## Variables

### Header Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{mode_desc}` | Description of analysis mode | "Standard Analysis", "Comparison: Before/After Update" |
| `{level_type}` | Type of levels analyzed | "Main", "Challenge", "Event" |
| `{level_range}` | Range of levels | "1-50", "all", "level_1,level_2" |
| `{start_date}` | Analysis start date | "2026-04-01" |
| `{end_date}` | Analysis end date | "2026-04-28" |
| `{report_date}` | Report generation date | "2026-05-18" |

### Overview Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{user_segment_desc}` | User segment name | "New users" |
| `{user_segment_definition}` | Segment criteria | "Users registered within 7 days" |
| `{inactive_days}` | Churn threshold | 3 |
| `{total_users}` | Total users analyzed | 12500 |
| `{total_churned_users}` | Churned user count | 3240 |
| `{overall_churn_rate}` | Calculated churn rate | 25.9 |
| `{traceable_count}` | Users with traceable last level | 3100 |
| `{traceable_rate}` | Percentage traceable | 95.7 |
| `{concentrated_zone}` | Where most users churned | "Levels 8-15" |
| `{sample_size}` | Total sample size | 12500 |
| `{completeness}` | Data completeness % | 98.5 |
| `{data_quality_recommendation}` | Quality assessment | "Sample size adequate for analysis" |

## Data Quality Recommendations

| Sample Size | Recommendation |
|-------------|----------------|
| < 100 | "⚠️ Sample size too small - results may be unreliable" |
| 100-500 | "⚠️ Small sample - use caution in interpretation" |
| 500-1000 | "✓ Adequate sample size" |
| > 1000 | "✓ Excellent sample size" |

## Example Output

### Full Report Example

```markdown
# Level Churn Diagnostic Report

## Analysis Configuration
- Analysis Mode: Standard Analysis
- Level Type: Main
- Level Range: 1-50
- Time Range: 2026-04-01 ~ 2026-04-28
- Analysis Date: 2026-05-18

## 1. Analysis Overview

### Target Population
- **Segment**: New users
- **Segment Definition**: Users registered within 7 days
- **Churn Definition**: 3 days of inactivity

### Key Metrics
- **Total Challenging Users**: 12,500
- **Churned Users**: 3,240
- **Overall 3-Day Churn Rate**: **25.9%** (3,240/12,500)
- **Traceable to Last Level**: 3,100 (95.7%)
- **Level Concentration Zone**: Levels 8-15

### Data Quality Indicators
- Sample Size: 12,500 users
- Data Completeness: 98.5%
- Recommended Action: ✓ Excellent sample size
```
