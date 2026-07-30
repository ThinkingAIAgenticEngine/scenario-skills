# Filtering Data Through Filtering Conditions

When using analysis models, you may only want to analyze the behavior of specific groups, precisely locate events that meet certain conditions, or exclude some anomalous data to ensure analysis accuracy.

## Function Description

Filtering can help you filter corresponding data based on specified properties and conditions. Event properties, user properties, user tags, and user cohorts can all be used as filtering properties.

For example, if you want to analyze payment behavior from the App Store, you can add [Source Channel equals App Store] in the filtering condition. At this point, calculation of triggering users will only be based on payment events where the event property Source Channel is App Store.

If you also want to select users with certain characteristics, you can add a parallel condition to filter users. This condition has an "AND" relationship with [Source Channel equals App Store], meaning only events satisfying both conditions will be used to calculate triggering users.

You can modify the relationship between parallel conditions to "OR", and the resulting data will be the triggering users for events satisfying either condition. You can also flexibly set multiple groups of parallel conditions to more precisely locate the content you want to analyze.

In analysis models, you can apply filtering only to individual analysis metrics (Example 2), or configure filtering conditions effective for all analysis content through "Global Filtering" (Example 3). If the analysis metric type is a custom formula, you can also perform single-event filtering (Example 1), which only applies to partial events in the formula.

## Filtering Condition Logic

### Text Type

- **Equals**: Selected property matches any one value in the configuration
- **Not Equals**: Selected property has a value and is different from all values in the configuration
- **Contains**: Selected property has a part that exactly matches the input content

  Example: "小米应用商城" contains "小米应用商城", also contains "小米", but does not contain "小米商店"

- **Regex Match**: Custom regex matching, selected property must satisfy the matching rule

```sql
-- Some common regex matching rules
-- Starts with xxx
^.*[xxx]

-- Ends with xxx
.*[xxx]$

-- Composed only of Chinese characters
^[\u4e00-\u9fa5]{0,}$

-- Character count between x~y
^.{x,y}$
```

### List Type

- **Element Exists**: Any element in the list matches any one value in the configuration

### Time Type

- **Relative to Current Date**: The natural day difference between selected property and "today" is within the range. Negative numbers represent before, positive numbers represent after.
- **Relative to Event Occurrence Time**:
  - Interval: The time difference between selected property and event time is within the range. Negative numbers represent before, positive numbers represent after.
  - Same Day/Week/Month: Whether the selected property and event time are on the same day/week/month

When judging whether data meets conditions, "Day (Relative)" corresponds to 24 hours, not natural days. Assuming the filtering condition is between -1 to +1 day relative to event occurrence time, with event time being January 1, 2023, 17:00:00, then as long as the selected property is within December 31, 2022, 17:00:00 to January 2, 2023, 17:00:00, the event meets the condition and will not be filtered out.

::: danger Note
1. Time-type event properties will be offset to the display timezone before comparison; time-type user properties or user tags will not be offset
2. Relative to event occurrence time is also relative to the event time after timezone offset
:::

### Object Group Type

- **Object Exists That Satisfies**: Any one object in the selected property meets the requirements
- **No Object Satisfies**: All objects in the selected property do not meet the requirements
- **All Objects Satisfy**: All objects in the selected property meet the requirements

After selecting any of the above three filtering conditions, you also need to configure the requirements that object sub-properties must meet, supporting multiple parallel conditions.