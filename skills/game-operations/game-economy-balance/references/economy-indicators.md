# Economy System Core Metric Definitions and Formulas

## I. Production-Consumption Balance Metrics

### 1.1 Daily Production Total

- **Definition**: The sum of resource amounts across all production events for a specified resource type on a specified date.
- **Formula**: `Σ(Resource Production Event.Resource Amount)`, aggregated by `$part_date`
- **Data Source**: te-analysis Event Analysis / generate-sql
- **Definition Notes**:
  - Dedup rule: No dedup; all production events are counted.
  - Time range: Filtered by `$part_date` date partition.
  - Resource type: Filtered by resource type field (e.g., `resource_type = "gold"`).

### 1.2 Daily Consumption Total

- **Definition**: The sum of resource amounts across all consumption events for a specified resource type on a specified date.
- **Formula**: `Σ(Resource Consumption Event.Resource Amount)`, aggregated by `$part_date`
- **Data Source**: te-analysis Event Analysis / generate-sql
- **Definition Notes**: Same as Daily Production Total.

### 1.3 Daily Production-Consumption Difference

- **Definition**: Daily Production Total minus Daily Consumption Total.
- **Formula**: `Daily Production Total - Daily Consumption Total`
- **Positive Meaning**: Net resource increase for the day (production exceeds consumption).
- **Negative Meaning**: Net resource decrease for the day (consumption exceeds production).
- **Use**: Monitor the daily net resource change trend.

### 1.4 Daily Production-Consumption Ratio

- **Definition**: Daily Production Total divided by Daily Consumption Total.
- **Formula**: `Daily Production Total / Daily Consumption Total`
- **Value-Domain Meaning**:
  - >1: Production exceeds consumption; net resource increase; inflation tendency.
  - =1: Production equals consumption; dynamic balance.
  - <1: Consumption exceeds production; net resource decrease; deflation tendency.
- **Special Handling**: When consumption total is 0 (edge case), the ratio is marked as "Infinity" and requires manual judgment.

### 1.5 Cumulative Production-Consumption Difference

- **Definition**: The cumulative sum of Daily Production-Consumption Differences over the analysis period.
- **Formula**: `Σ(Daily Production-Consumption Difference)`, full-period cumulative.
- **Use**: Assess the total resource change over the analysis period.

### 1.6 Cumulative Production-Consumption Ratio

- **Definition**: Total production divided by total consumption over the analysis period.
- **Formula**: `Analysis-period Total Production / Analysis-period Total Consumption`
- **Use**: Determine the overall balance status within the analysis period.

### 1.7 Baseline Period Production-Consumption Ratio

- **Definition**: The cumulative production-consumption ratio of the baseline (comparison) period.
- **Formula**: Same as Cumulative Production-Consumption Ratio, using the baseline period time range.
- **Use**: Serves as a comparison reference to judge whether the current status deviates from the historical normal level.

---

## II. Balance and Hoarding Metrics

### 2.1 Per-User Resource Balance

- **Definition**: The average amount of a specified resource held by active users.
- **Formula**: `Σ(Active Users.Resource Balance) / Active User Count`
- **Data Source**: generate-sql (User Property + balance calculation)
- **Definition Notes**:
  - Active user definition: Distinct users who triggered a login event during the analysis period.
  - Balance acquisition: Read the balance field from user properties, or compute via (Cumulative Production - Cumulative Consumption).

### 2.2 Resource Hoarding Rate

- **Definition**: The share of active users whose resource balance exceeds the hoarding threshold.
- **Formula**: `Users with Balance > Hoarding Threshold / Active User Count × 100%`
- **Hoarding Threshold Setting**:
  - Default: The P90 percentile of the server-wide balance distribution.
  - Custom: The user can set a specific value (e.g., gold balance > 1,000,000).
- **Use**: Judge the degree of resource hoarding; an excessively high value indicates severe inflation.

### 2.3 Balance Distribution Percentiles

- **Definition**: The P25/P50/P75/P90/P95 percentiles of the server-wide user resource balance.
- **Use**:
  - Determine whether the balance distribution is skewed (a few users hoarding large resource volumes).
  - During inflation monitoring, check whether the balance P90 keeps rising.

### 2.4 Non-Spender Per-User Balance

- **Definition**: The per-user resource balance of Non-Spenders (cumulative payment = 0).
- **Use**: Assess the resource acquisition difficulty for free players; too high may indicate studios/cheats; too low may indicate deflation.

---

## III. Concentration Metrics

### 3.1 Single-Source-Point Production Concentration

- **Definition**: The share of total production accounted for by the TOP3 source points with the highest production shares.
- **Formula**: `(Sum of TOP3 Source-Point Production) / Total Production × 100%`
- **Use**:
  - <40%: Production sources are dispersed; healthy.
  - 40%~60%: Moderately concentrated; normal.
  - >60%: Over-concentrated; higher risk (if a TOP3 source point goes anomalous, total production is heavily affected).

### 3.2 Single-Source-Point Consumption Concentration

- **Definition**: The share of total consumption accounted for by the TOP3 source points with the highest consumption shares.
- **Formula**: `(Sum of TOP3 Source-Point Consumption) / Total Consumption × 100%`
- **Use**: Same as Production Concentration.

### 3.3 Single-Source-Point Per-User Production Anomaly Index

- **Definition**: The ratio of a source point's per-user production to the server-wide per-user production.
- **Formula**: `Per-User Production at Source Point / Server-Wide Per-User Production`
- **Use**:
  - >2: Per-user production at this source point is abnormally high; farming behavior may exist.
  - 1~2: Within the normal range.
  - <1: Production efficiency at this source point is low.

---

## IV. Anomaly Detection Metrics

### 4.1 24h Acquisition Total Deviation

- **Definition**: The ratio of the current day's acquisition total to the average daily acquisition over the recent 7 days.
- **Formula**: `Current-Day Acquisition Total / Recent 7-Day Daily Average Acquisition`
- **Thresholds**:
  - >3: Anomalous deviation; trigger alert.
  - 1.5~3: Worth attention; may be activity-driven.
  - <1.5: Normal fluctuation range.

### 4.2 Per-User Daily Acquisition Count

- **Definition**: The total number of resource acquisition events triggered by a user on a specified date.
- **Formula**: `Σ(User.Resource Acquisition Event Count)`, daily aggregated.
- **Threshold**: Above server-wide average × 5 is anomalous.

### 4.3 Per-User Hourly Acquisition Rate

- **Definition**: The total resource amount acquired by a user within a single hour.
- **Formula**: `Σ(User.Single-Hour Resource Acquisition)`
- **Threshold**: Above server-wide P95 × 2 is anomalous.

### 4.4 Quest Completion Frequency Anomaly Index

- **Definition**: A user's daily average completion count for a specific quest/level.
- **Formula**: `Σ(User.Specific Quest Completion Count)`, daily aggregated.
- **Thresholds**:
  - >50 times/day: Highly anomalous (normal players typically clear the same level <20 times/day).
  - 30~50 times/day: Worth attention.
  - <30 times/day: Normal range.

### 4.5 Payment Contradiction Index

- **Definition**: The comparison of resource production by Non-Spenders vs. Paying Users.
- **Formula**: `Non-Spender Per-User Production / Paying User Per-User Production`
- **Thresholds**:
  - >1.5: Non-Spender production far exceeds Paying Users; severely anomalous (studio/cheat suspicion).
  - 0.8~1.5: Normal range.
  - <0.8: Non-Spender production is low; deflation tendency.

### 4.6 Trade Price Deviation

- **Definition**: The ratio of the trade event's transaction price to the market average price.
- **Formula**: `Transaction Price / Market Average Price`
- **Thresholds**:
  - <0.5: Abnormally low-price trade; likely RMT (real-money trade) or resource transfer.
  - 0.5~2.0: Normal price range.
  - >2.0: Abnormally high price; worth attention.

---

## V. Correlated Metrics

### 5.1 Production-Consumption Ratio vs. Payment Rate Correlation

- **Definition**: Monitor the correlation between the production-consumption ratio trend and the Payment Rate trend.
- **Use**:
  - Production-consumption ratio persistently >1 (inflation) + Payment Rate declining → Inflation has devalued payment; urgent intervention needed.
  - Production-consumption ratio persistently <1 (deflation) + Payment Rate declining → Resource depletion has degraded experience.

### 5.2 Production-Consumption Ratio vs. ARPU Correlation

- **Definition**: Time-series comparison of the production-consumption ratio and ARPU.
- **Use**: Determine whether economy imbalance has already affected revenue.

### 5.3 Production-Consumption Ratio vs. Retention Rate Correlation

- **Definition**: Time-series comparison of the production-consumption ratio and next-day / 7-day Retention Rate.
- **Use**: Determine whether economy imbalance has already affected user retention.

---

## VI. Metric Calculation SQL Reference

### 6.1 Daily Production-Consumption Total Calculation

```sql
-- Daily Production Total
SELECT
  $part_date AS date,
  SUM(resource_amount) AS daily_production
FROM ta.v_event_{project_id}
WHERE $part_event = 'resource_gain'
  AND resource_type = '{resource_type}'
  AND $part_date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY $part_date
ORDER BY date

-- Daily Consumption Total
SELECT
  $part_date AS date,
  SUM(resource_amount) AS daily_consumption
FROM ta.v_event_{project_id}
WHERE $part_event = 'resource_consume'
  AND resource_type = '{resource_type}'
  AND $part_date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY $part_date
ORDER BY date
```

### 6.2 Per-Source-Point Production-Consumption Details

```sql
-- Production source-point details
SELECT
  gain_reason AS point_name,
  COUNT(DISTINCT #user_id) AS gain_user_count,
  SUM(resource_amount) AS gain_total,
  SUM(resource_amount) / COUNT(DISTINCT #user_id) AS avg_per_user,
  SUM(resource_amount) / (SELECT SUM(resource_amount) FROM ... WHERE ...) AS gain_ratio
FROM ta.v_event_{project_id}
WHERE $part_event = 'resource_gain'
  AND resource_type = '{resource_type}'
  AND $part_date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY gain_reason
ORDER BY gain_total DESC
```

### 6.3 Suspicious User Filtering

```sql
-- Top production users (above P95)
SELECT
  #user_id,
  COUNT(*) AS gain_count,
  SUM(resource_amount) AS gain_total,
  AVG(resource_amount) AS avg_per_gain
FROM ta.v_event_{project_id}
WHERE $part_event = 'resource_gain'
  AND resource_type = '{resource_type}'
  AND $part_date = '{target_date}'
GROUP BY #user_id
HAVING SUM(resource_amount) > {p95_threshold}
ORDER BY gain_total DESC
LIMIT 50
```
