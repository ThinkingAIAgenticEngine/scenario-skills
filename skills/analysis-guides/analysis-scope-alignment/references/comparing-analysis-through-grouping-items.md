# Comparing Analysis Through Grouping Items

Comparison is a commonly used method in analysis, such as horizontally comparing data performance of the same date across different dimensions. In analysis models, you can implement horizontal comparison through grouping items. If you want to compare data performance across different dates, you can add comparison stages in event analysis.

## Function Description

Grouping items can help you view corresponding data results based on different grouping values. Event properties, user properties, user tags, and user cohorts can all be used as grouping items.

For example, if your selected grouping item is Source Channel, specific source channels like App Store, Huawei App Store, and Yingyongbao are the corresponding grouping values. Each grouping value has its own data result, representing the payment count for that channel.

You can also add multiple grouping items to cross-compare performance of different grouping values across multiple dimensions. Except for funnel analysis and property analysis, other models can add up to 50 grouping items.

## Grouping Methods

If the property type of your selected grouping item is numeric, list, or time, since the number of grouping values may be large, you can set grouping methods to merge different grouping values into one group before comparison.

### Numeric Type

| Grouping Method | Default Interval | Calculation Logic |
|-----------------|------------------|-------------------|
| Discrete Numbers | - | Uses actual values as groups. If grouping value count exceeds 500, divides into 12 equal intervals based on maximum and minimum values |
| Default Interval | Automatically determined based on grouping value count | If grouping value count < 20, uses actual values as groups. If grouping value count ≥ 20, divides into 12 equal intervals based on maximum and minimum values |
| Custom Interval | - | Manually divide different intervals according to needs. All intervals are left-closed and right-open |

If your selected grouping item has clear interval meanings in business, such as levels 1-12 being the beginner stage, you can choose "Custom Interval" for division. When you want to further analyze data within a certain interval range, you can choose "Discrete Numbers" for easier comparison of different grouping value performance.

### Time Type

| Grouping Method | Calculation Logic |
|-----------------|-------------------|
| Aggregate | Automatically groups data from the same day, week, month, etc. based on selected aggregation granularity |
| No Aggregation | Uses the actually reported time as groups |

Since time-type properties are in seconds or milliseconds, there are many grouping values. It's recommended to choose aggregation during analysis, such as selecting "by day" aggregation for cohort analysis when grouping by registration time. If you want to display detailed data in a flat view, you can also choose "No Aggregation".

### List Type

| Grouping Method | Calculation Logic |
|-----------------|-------------------|
| By Element | Splits the list into multiple elements. One event will be used for calculation of each element group |
| By List Whole | Treats the list as a whole. Identical lists are treated as one group |
| By Element Set | First deduplicates and sorts elements within each list to get a set, then treats identical sets as one group |

In games, multiple hero IDs on the lineup are often recorded in list properties. You can choose the appropriate grouping method based on your analysis scenario:

- If you want to compare deployment counts of different heroes, use "By Element"
- If you want to compare deployment counts of different lineups (hero combinations), choose "By List Whole" or "By Element Set" depending on whether to distinguish the same hero appearing multiple times or hero order

::: danger Note
If there are multiple list-type properties in grouping items, at most one can choose the "By Element" grouping method, unless other list-type properties are all dimension table properties of that property.
:::