# Conditional Cohorts

Conditional cohorts are mainly used for user segmentation scenarios where users are selected based on user behavior. You can use data assets already created in the system and generate cohorts through simple interface configuration.

## 1. Condition Types

Conditional cohorts have the following condition types:

| Category | Condition Type | Description |
|----------|---------------|-------------|
| User Behavior | Done | Within the specified time range, the specified event occurred. |
| User Behavior | Not Done | Within the specified time range, the specified event did not occur. |
| User Behavior | Sequentially Done | Within the specified time range, a series of specified events occurred in order. |
| User Behavior | Not Sequentially Done | Within the specified time range, a series of specified events did not occur in order. The specified event not occurring, or not occurring in order both count as meeting the condition. |
| User Property | Property Satisfied | The user's specified property satisfies or does not satisfy the configured condition. |

Through logical formulas of multiple conditions, you can combine the conditions for a cohort. When actually combining, conditions of the same category are first connected by "AND" or "OR", and then the logical results of the two categories are connected by "AND" or "OR", as shown in the figure below.

## 2. "Sequentially Done" Condition

"Sequentially Done" / "Not Sequentially Done" conditions are relatively complex. They are condition types that select users by defining the occurrence pattern of a series of specified events (such as order, interval, same-value properties, etc.). The configuration effect is shown in the figure below.

| Pattern Definition Item | Description |
|------------------------|-------------|
| Step Events | The order of step events within the sequence is strict sequential order, i.e., simultaneous occurrence does not count as sequential occurrence. |
| | Only focuses on the order between configured events in the sequence; whether unconfigured events occur does not affect the judgment result. |
| | The same event is allowed to occur multiple times consecutively, as long as it conforms to the relative order of step events. |
| Time Range | All step events in the sequence must occur within the selected time range. Note this is different from funnel analysis where the first step occurs within the time range. |
| Associated Properties | This property has non-null and identical property values across all events in the sequence. Note that all events here include sequentially occurring step events and events defined as "not done" between steps. |
| Time Window | The time interval between two events in the sequence. |
| | Can configure interval upper limit; when time interval "<=" time window, it's considered to meet the condition. |
| | Day interval is not judged by natural days; it's actually judged with 24 hours as 1 day. |
| Not Done Between Steps | Events that cannot occur between two events. If the user performs this event between step events, it's considered not meeting the defined pattern. |

### More Special Case Explanations:

- **When you select completely identical events for adjacent steps in the sequence**, it's considered that the event needs to occur at least 2 times consecutively.

  Example: A 4-step pattern of `User Registration - User Claim Reward - User Claim Reward - User Payment`, where events in steps 2 and 3 are completely identical. The actual judgment is that the user triggers `User Claim Reward` at least twice between `User Registration` and `User Payment`.

- **When you select an event and a virtual event defined using that event for adjacent steps in the sequence**, it's considered that the event needs to occur at least 2 times consecutively, once as the event and once as the virtual event.

  Example: A 4-step pattern of `User Registration - User Claim Reward - User Claim Reward or Coupon (Virtual Event) - User Payment`, where the event `User Claim Reward` in step 2 is used for the virtual event definition in step 3. The actual judgment is that if the user triggers `User Claim Reward` 2 or more times between `User Registration` and `User Payment`, it's considered to meet the pattern; if only 1 `User Claim Reward` occurs and no other events in the `User Claim Reward or Coupon` definition occurred, it's considered not to meet the pattern.

- **When the "not done" event configured between sequence steps is the same as its adjacent step events**, it's considered that the event can only occur once.

  Example: A 3-step pattern of `User Registration - User Claim Reward - (Not Done: User Claim Reward) - User Payment`, where between events in steps 2 and 3, a "not done" event is defined which is also `User Claim Reward`, the same as step 2. The actual judgment is that if the user triggers `User Claim Reward` 2 or more times between `User Registration` and `User Payment`, it's considered not to meet the pattern; only 1 occurrence is considered to meet the pattern.