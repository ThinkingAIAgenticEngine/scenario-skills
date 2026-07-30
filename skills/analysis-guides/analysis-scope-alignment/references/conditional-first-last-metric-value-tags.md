# Conditional, First/Last, and Metric Value Tags

There are 4 types of tags defined by data conditions, including conditional tags, first/last occurrence tags, metric value tags, and SQL tags. For the first 3 tag types, you can complete tag definition through simple configuration in the interface.

## 1. Conditional Tags

When you need to tag users based on their behavior within a time period, you can choose conditional tags. The types of conditional tags are described below:

| Category | Condition Type | Description |
|----------|---------------|-------------|
| User Behavior | Done | Within the specified time range, the specified event occurred. |
| User Behavior | Not Done | Within the specified time range, the specified event did not occur. |
| User Property | Property Satisfied | The user's specified property satisfies or does not satisfy the configured condition. |

By configuring logical formulas for multiple conditions, you can combine marking conditions for a tag value. As shown in the diagram below:

A tag can have multiple tag values, and a user can only be marked with a unique tag value. According to the tag value order, users will be marked with the first tag value that meets the condition. The marked tag value needs to be configured together with its condition formula at creation time.

### Conditional Tags Support Behavior Sequences

You can use "sequentially done events / not sequentially done events" as conditions to define user tags in User Tags - Conditional Tags, creating tags for users with the same behavior sequence conditions.

Users can select "sequentially / not sequentially done events" as a condition, add events in order, and simultaneously set filter conditions on each event to complete the condition setting for the current step's event behavior. Time windows can also be added between events, as well as property filter conditions. When all events are set in order, the conditional tag can be generated.

**Application Scenario:**

As shown in the figure above, among users who [newly registered within the last 7 days], players who sequentially completed [registration] account, [login] account, and completed [payment] within one day after login, and did not perform [player upgrade] operation after login, are tagged with the user tag [Class A User]. This makes it easier to perform targeted analysis on the user group tagged with this tag.

## 2. First/Last Occurrence Tags

Use this tag type when you need to directly use the behavior property, behavior environment parameters, etc. from the first or last occurrence of the target behavior within a specified period as the user tag value to mark users.

The configuration of this type of tag is shown in the figure below. After selecting a behavior property (such as payment amount in the figure), the property value will be directly used as the tag value to mark users.

You can mark users based on the property when the target behavior event is first triggered. By comparing subsequent data of users with different tag values, you can select the better first trigger method based on the final conversion effect. For example, mark the ad parameters of users who first visited the site, and select the better ad strategy through user site conversion.

You can also use the property when the target behavior is last triggered as a tag to mark users, and understand the overall situation when users trigger that behavior by analyzing the property value distribution, such as the user level at the time of last activity.

**Note:** Even if the event is completed, when the selected property value is empty, the user cannot calculate the tag value, i.e., cannot be marked with this tag. If the tag's analysis subject is an event property, the event dropdown can only select events that contain that event property. Time or time-type properties all use the value offset to the selected tag timezone as the tag value.

## 3. Metric Value Tags

Use this tag type when you need to use the aggregated metric of user behavior properties within a specified period as a tag to mark users.

The configuration of this type of tag is shown below. Select a behavior property for calculation, and use the calculation result of the property as the tag value (such as the sum of payment amounts in the figure below).

Metric value tags also support tags defined by metric formulas, as shown below.

**Note:** If a user only participated in some events in the formula, the property value for unparticipated events is taken as 0, and the user can still be marked by the tag. If the divisor in the formula is 0, the user cannot calculate the tag value, i.e., cannot be marked by this tag.