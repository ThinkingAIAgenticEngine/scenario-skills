# Calculation Method Logic Explanation

When configuring analysis metrics for event analysis, or simultaneously displaying metrics for retention or distribution analysis, you need to select appropriate calculation methods based on the analysis content. This chapter explains the logic of some methods.

## Preset Calculation Methods

- **Total Count**: How many times the event was triggered
- **Triggering Users**: How many unique users triggered the event
- **Average per User**: Total count / triggering users, the average number of times each user who triggered the event will trigger it

### Numeric Properties

| Calculation Method | Logic |
|-------------------|-------|
| Mean | Sum of property values / number of property values |
| Average per User | Sum of property values / triggering users, the average sum of property values for each user who triggered the event |
| Median | Property values sorted from largest to smallest, the value in the middle; if the number of property values is even, the median is the mean of the two middle values |

Mean reflects the average performance of data, but if there are property values significantly higher or lower than others, the median better represents the overall situation compared to the mean. Assuming 4 users triggered 7 payment events in total:

| User | Payment Amount Each Time |
|------|-------------------------|
| A | 6, 648 |
| B | 30, 30, 30 |
| C | 128 |
| D | 6 |

- Mean = 125.43
- Average per User = 219.5
- Median = 30

| Calculation Method | Logic |
|-------------------|-------|
| N-th Percentile | The property value at the N-th percentile, median is the 50th percentile |

Besides the median, N-th percentile is often used to better measure data distribution. For example, observing changes in the N-th percentile of core resource stock can help determine whether to release new items to consume resources.

| Calculation Method | Logic |
|-------------------|-------|
| Variance | First calculate the mean, then calculate the square of the difference between each property value and the mean, and finally take the average |
| Standard Deviation | The square root of variance |

Variance and standard deviation can be used to measure data fluctuation. Assuming the average payment amount per user in the experimental group is similar to the control group, but the standard deviation is significantly higher than the control group, this indicates that the experimental group's metric data is more affected by large payment orders.

### List Properties

| Calculation Method | Logic |
|-------------------|-------|
| Unique List Count | Treat the list as a whole, count how many unique lists exist |
| Unique Set Count | First deduplicate and sort elements within each list to get a set, then count how many unique sets exist |
| Unique Element Count | Extract all elements from all lists, then count how many unique elements exist |

In games, multiple hero IDs on the lineup are often recorded in list properties. If you want to analyze how many heroes have been deployed, you can use "Unique Element Count" for statistics. You can also use "Unique List Count" or "Unique Set Count" to analyze how many unique lineups exist, where the latter does not distinguish the order of heroes in the list or whether they appear multiple times.

Assuming there are 4 list properties: `[a,b,c]`, `[a,b,c,c]`, `[c,b,a]`, and `[a,b,c,d]`:

- Unique List Count = 4
- Unique Set Count = 2
- Unique Element Count = 4

### Boolean Properties

| Calculation Method | Logic |
|-------------------|-------|
| True Count, False Count | Number of events where property value is True/False |
| Null Count, Not Null Count | Number of events where property value is null/not null |