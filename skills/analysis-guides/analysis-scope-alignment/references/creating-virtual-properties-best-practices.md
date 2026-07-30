# Best Practices for Creating Virtual Properties

Virtual properties are properties created through SQL expressions that perform secondary calculations on existing ingested property fields. The SQL expressions for virtual properties use Trino syntax. You can access the [Trino documentation](https://trino.io/docs/current/functions.html) to learn about Trino syntax and function usage.

## Scenario 1: Time Difference Calculation

During instrumentation, user lifecycle days are generally not collected as event properties. You can add user registration time as an event property, then obtain the user's lifecycle situation when events occur through the following method. Use the `date_diff(unit, timestamp1, timestamp2)` function to calculate the interval days between the user property "registration_time" and the event property "#event_time", generating a virtual user property "user_lifecycle_days":

```sql
date_diff('day', date("register_time"), date("#event_time"))
```

## Scenario 2: Type Conversion

During use, there may be situations where the reported property type does not match expectations. You can use the `cast(value AS type)` function for property type conversion. Note that if the property value cannot be forcibly converted to the expected type, the new property value will be null. Rule example:

```sql
cast(old_prop_string as int)
```

## Scenario 3: Timestamp Conversion

When custom properties like registration time are uploaded as numeric timestamps, you can use the `from_unixtime(unixtime)` function to convert them to time format for filtering and grouping operations in the system. Rule example:

```sql
from_unixtime("register_time")
```

## Scenario 4: Character Substring Extraction

In some cases, the content reported by a property may be a combination of multiple pieces of information. For example, if the value of the "get_reward" property is reported as a string "获得钻石300" (Got Diamonds 300), and you want to extract characters at a fixed position from this property as a new property, you can use the following expression:

```sql
cast(substring("get_reward", 5, 4) as int)
```

The function `substring(string, start, length)` is used to extract a fragment of the specified length starting from the start position, and the `cast(value AS type)` function converts the extracted fragment to a numeric type for subsequent analysis.

## Scenario 5: Combined Deduplication

In game data analysis scenarios, common event properties like account_id and server_id are often recorded. However, the system currently only provides deduplication calculations for single properties. If you need to perform combined deduplication using account_id and server_id, you can create a virtual property with the following rule:

```sql
concat(server_id, '@', account_id)
```

The function `concat(string1, ..., stringN)` can be used to concatenate multiple text-type properties.

## Scenario 6: Conditional Judgment

During game testing phases, there may be data wipes. Although user IDs remain unchanged before and after a wipe, the event data before and after are independent with no inheritance relationship, and wipe times may differ across different servers. If you want to use a property to distinguish whether a single user's events are from before or after the wipe, you can create a virtual property as follows:

```sql
case
  when "serverid" = 1 and "#event_time" > cast('2020-11-15 10:30:00.000' as timestamp) then 'after_wipe'
  when "serverid" = 2 and "#event_time" > cast('2020-11-22 10:30:00.000' as timestamp) then 'after_wipe'
  else 'before_wipe'
end
```

## Scenario 7: Constants

Using the IF function, you can create a virtual property with a constant value. For example, in a retention model where you want to simultaneously display the stage cumulative total of returning users, you can create a virtual property with a constant value of 1, then perform aggregate calculations on this property. Rule example:

```sql
if("#event_time" is not null, 1, 1)
```

Here, "#event_time" is generally set to a non-null system field.