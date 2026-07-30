# User Tags

User tags are one of the data tools provided by the system for segmenting users. A user tag can be considered as a certain characteristic used when describing users, such as [Gender], [Age], [Account Balance], etc. In daily use, multiple characteristics can be used to describe a user, such as [Gender: Male], [Age: 40-50], [Account Balance: Above 5000], etc. In the system, you can use user tag values to mark users, and then use these tags to filter users or perform user grouping statistics during analysis.

Different tag values of the same tag can divide users into multiple categories, each marked by a tag value. For example, under the tag [Gender], users are marked with tag values [Gender: Male] and [Gender: Female] respectively. If there is a hierarchical or numerical progressive relationship between tag values, the tag can also be considered as user stratification from a certain angle, such as [Days Since Last Payment: 1 day / 1-3 days / 3-7 days / ...].

Compared to user cohorts for selecting users, user tags are more like marking users. This marking has strong reusability. It's generally recommended to create a certain abstract user characteristic as a tag, such as tag [Payment Ability: Low/Medium/High], tag [Active Period: 11-1 o'clock / 2-4 o'clock / ...]. At the same time, the definition rules and naming of tag values should尽可能 conform to unified understanding within the enterprise. Tags can be reused in multiple scenarios after creation.

## 1. Creating User Tags

In Users - User Tags, you can create a tag through multiple methods. Detailed descriptions are in the table below:

| Definition Method | Type | Description |
|------------------|------|-------------|
| **ID Collection Type** (Saves the marking relationship between users and tag values as the tag definition. Tags defined this way will hardly have marking range changes) | ID Tag | • Tags created by importing files. Files contain the marking relationship between IDs or properties and tag values. |
| | | • Commonly used for: Importing a set of IDs or property values and their marking relationship with tag values into the system to create tags. Such as mobile numbers collected from offline marketing activities and user interest categories, or user lists exported from third-party systems and user points, etc. |
| | | • Default personal limit is 50. |
| **Data Condition Type** (Saves the calculation rules for marking users and tag values as the tag. Each calculation based on rules uses current compliance with rules as the judgment standard for marking. Default project limit is 200) | Conditional Tag | • Defines whether to mark users based on whether a user performed a certain event or sequentially performed a set of events. |
| | | • Commonly used for: User segmentation scenarios based on user behavior or reported user properties. Since each tag value has separate rule configuration, multiple behaviors or properties can be combined to define tags. For example, defining tag [Important User]: [Important User: Recent payment above 500 yuan], [Important User: Recent activity above 80%]. The former tag value is defined by user payment events, the latter by user activity behavior. |
| | First/Last Tag | • Uses the value of a certain event property when the user first or last performs a specified event as the tag value for that user. |
| | | • Commonly used for: Marking user characteristics or environmental state during first target behavior, such as product and payment amount at first payment; or marking user characteristics or environmental state during last target behavior, such as level at last activity. |
| | Metric Value Tag | • Performs aggregation calculation on user event properties within a certain time range, and marks the aggregation result as the user's tag value. |
| | | • Commonly used for: Marking user periodic behavior settlements, such as yesterday's active duration, last 30 days payment amount, etc. |
| | SQL Tag | • Defines user and tag value marking relationship based on SQL statements. |
| | | • Commonly used for: Complex logic to define user tags. Some complex data rules that cannot be configured through "Conditional Tag", "First/Last Tag", and "Metric Value Tag" can use SQL tags. |

### Analysis Subject

When creating tags, besides tag conditions, you also need to select the tag's analysis subject and timezone.

User tags are a user segmentation tool, and "user" identifiers are diverse, such as Device ID, Account ID, Role ID, Platform ID, etc. In project configuration, user identifiers (properties) other than TE User ID can be added as analysis subjects. These analysis subjects can also use user tags for segmentation.

When creating a tag, you must first select the tag's analysis subject. After calculation, you get the marking relationship between this analysis subject and tag values. The tag "user count" seen is also the count of this analysis subject.

**Note:** When the selected analysis subject is an event property, conditional tags cannot use the "Not Done" condition.

### Timezone

When your project has the multi-timezone switch enabled (configured in [Project Configuration]), you also need to select the tag's calculation timezone when creating tags. When event data is used in the definition of "Conditional Tag", "First/Last Tag", "Metric Value Tag", and "SQL Tag", the time range in event conditions defaults to the time range under the tag timezone. If reported events are in other timezones, event timezone will be converted first before judging whether conditions are met. For example, if display timezone is UTC+10 and the defined condition is payment occurred yesterday, we will first convert payment behavior time to UTC+10, then judge if it occurred yesterday.

**Note:** When viewing dashboards and reports with different display timezones during analysis, the tag data used is the original timezone result. The calculation timezone will not change accordingly.

## 2. Updating User Tags

User tags are pre-calculated data (as opposed to ad-hoc queries), meaning the system pre-calculates user tags, then uses the result data in subsequent analysis and operations, rather than recalculating tags each time they're used. Pre-calculation greatly reduces calculation complexity at use time, reduces repeated calculations, and improves data use efficiency, but sacrifices data timeliness. For most analysis scenarios, daily granularity updated cohorts can meet requirements.

Tags defined by data conditions support multiple update methods, described below:

| Update Method | Description |
|--------------|-------------|
| Automatic | When creating or editing tags, if you enable the auto-update switch for conditional tags, first/last tags, metric value tags, and SQL tags, the system will automatically update tags at the daily scheduled time. ID tags do not support this update method. |
| Manual | Conditional tags, first/last tags, metric value tags, and SQL tags can be manually updated. If you need current state tag data, you can manually trigger an update. ID tags need to re-import new files to update. |
| Create Calculation | All tags calculate once immediately after creation. |
| Edit Calculation | After modifying conditions or timezone and saving, calculates once immediately. |

**Note:** Since user and event data in the system is updated in real-time, you can use "Today" event conditions in tag definitions. Tag calculation can only use today's data up to the calculation time. If you need full day data, please use event conditions up to yesterday.

When analyzing historical data, you may need to use user tag values from a historical moment. Tags use "Date Version" to save user tag values under that tag for a certain date. See [Date Versions of Tags](./date-versions-of-tags.md) for detailed introduction.

## 3. Managing User Tags

In the user tag interface, you can perform management operations such as edit, delete, download (ID tags only), update, and version management for created tags. See [Date Versions of Tags](./date-versions-of-tags.md) for tag version management details.

Since tags can be used by assets such as virtual properties, reports, cohorts (created in operations module), and alerts, editing or deleting tags may cause abnormal data fluctuations or inability to calculate for these assets. When deleting or editing a tag that has dependent assets, the system will prompt its impact scope, requiring the operator to judge the impact before proceeding with modifications.

## 4. User Tag Details

Click the user tag name to view tag details. Tag details are divided into two parts: tag definition and tag data. As shown below:

Click the user count in the data table to drill down to the user list marked with that tag value for the corresponding date.

The table displays data for up to 1,000 rows of users. If you need more data, click the download button at the top right of the table to download up to 500,000 rows of user data.

**Note:** Clicking update at the top right of the table on the user list page only queries tag result data again and does not recalculate the tag itself, but user property data for tag value users will be updated.