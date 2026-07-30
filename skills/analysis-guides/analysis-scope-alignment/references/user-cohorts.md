# User Cohorts

User cohorts are one of the data tools provided by the system for segmenting users. A user cohort can be understood as a user set formed by selecting a portion of users from all users. You can create a batch of users as a cohort, or create a cohort from a certain data condition (i.e., rules for selecting users), then use them in analysis and operations. Each cohort can divide users into two categories: those belonging to the cohort and those not belonging to the cohort.

Compared to user tags which mark users, user cohorts are more like selecting users. The selected user set has strong specificity. It's generally recommended to use one cohort for only one scenario. For example, cohort [Users who participated in a certain activity] can be used to analyze the activity's impact on retention, cohort [Users who earned more than 500 points in the last 3 days] is used for daily point task reward distribution, etc.

## 1. Creating User Cohorts

In Users - User Cohorts, create "Conditional Cohorts", "ID Cohorts", and "SQL Cohorts":

In the analysis result table, create "Result Cohorts":

You can create a user cohort through multiple methods. Comparison of each type is shown in the table below:

| Definition Method | Cohort Type | Description |
|------------------|-------------|-------------|
| **ID Collection Type** (Directly saves the ID set contained in the cohort as the cohort definition. Cohorts defined this way will hardly have marking range changes.) | ID Cohort | • Cohorts created by importing ID or property files. |
| | | • Commonly used for importing a set of IDs and property values obtained outside TE to create cohorts for analysis and operations targeting this segmented user set. Such as mobile numbers collected from offline marketing activities, or user lists exported from third-party systems. |
| | | • Default personal limit is 50. |
| **Data Condition Type** (Saves calculation rules as cohort definition. Each calculation based on rules uses current compliance with rules as the judgment standard for whether to add to the cohort. Default project limit is 200.) | Conditional Cohort | • Cohorts defined based on whether a user performed a certain event or event sequence, and whether properties satisfy a logical formula. |
| | | • Commonly used for user segmentation scenarios based on user actual behavior or reported user properties. |
| | SQL Cohort | • Cohorts defined based on SQL statements. |
| | | • Commonly used for complex logic to define user cohorts. Some complex data rules that cannot be configured through "Conditional Cohort" can use SQL cohorts. |
| | Result Cohort | • User cohorts created in TE analysis or operations data result tables for a certain "user count" type result data. |
| | | • Commonly used for further drill-down analysis of analysis results, or refined operations for anomalous users. For example, [Users who added to cart but didn't pay in 12.25 promotion activity] created as a cohort, used to analyze conversion effect of these users in return activities. |
| | | • Default personal limit is 50. |

### Analysis Subject

When creating cohorts, besides the cohort's ID set or data conditions, you also need to select the cohort's analysis subject and timezone.

User cohorts are a user segmentation tool, and "user" identifiers are diverse, such as Device ID, Account ID, Role ID, Platform ID, etc. In project configuration, user identifiers (properties) other than TE User ID can be added as analysis subjects. These analysis subjects can also use user cohorts for segmentation.

When creating a cohort, you must first select the cohort's analysis subject. After calculation, you get a set of this analysis subject. The cohort "user count" seen is also the count of this analysis subject.

**Note:** When the selected analysis subject is an event property, conditional cohorts cannot use "Not Done" and "Not Sequentially Done" conditions.

### Timezone

When your project has the multi-timezone switch enabled (project configuration), you also need to select the cohort's calculation timezone when creating cohorts. If event data is used in the definition of conditional cohorts and SQL cohorts, the time range in event conditions defaults to the time range under the cohort timezone. If reported events are in other timezones, they will be offset first before judging whether event conditions are met.

**Note:** When viewing dashboards and reports with different timezones during analysis, the cohort data used is pre-calculated results. The calculation timezone will not change accordingly.

## 2. Updating User Cohorts

User cohorts are pre-calculated data (as opposed to ad-hoc queries), meaning the system pre-calculates user cohorts, then uses the result data in subsequent analysis and operations, rather than calculating cohorts ad-hoc each time they're used. Pre-calculation greatly reduces calculation complexity at use time, reduces repeated calculations, and improves data use efficiency, but sacrifices data timeliness (for data condition-type defined cohorts). For most analysis scenarios, daily granularity updated cohorts can meet requirements. For operations scenarios, timeliness requirements for cohorts are higher.

Conditional cohorts and SQL cohorts are cohorts defined by data conditions. The system supports multiple update methods, described below:

| Update Method | Description |
|--------------|-------------|
| Scheduled | If you enable the auto-update switch for conditional cohorts and SQL cohorts during cohort creation or editing, the system will automatically update cohorts at the daily scheduled time. ID cohorts and result cohorts do not support this update method. |
| Manual | Conditional cohorts and SQL cohorts can be manually updated. If you need current cohort data, you can manually trigger an update. ID cohorts need to re-import new files to update. Result cohorts do not support manual update. |
| Follow Calculation | If the target users created in an operations task use this cohort, it will be calculated once before pushing. |
| System Trigger | Cohort updates triggered by other system functions. If your project has deployed the operations module, the system will automatically trigger cohort updates based on operations task configuration. |
| Create Calculation | All cohorts calculate once immediately after creation. |
| Edit Calculation | After modifying conditions or timezone for conditional cohorts and saving, calculates once immediately. |

**Note:** Since user and event data in the system is updated in real-time, you can use "Today" event conditions in cohort definitions. Cohort calculation can only use today's data up to the calculation time. If you need full day data, please use event conditions up to yesterday.

## 3. Managing User Cohorts

Cohorts created under Analysis, Operations, Users, and API modules can all be viewed in Users - User Cohorts interface. If the cohort creation module allows it to be publicly managed, you can also delete, update, and edit cohorts here.

In user cohorts, you can quickly filter cohorts created by Analysis, Operations, and API modules through creation source. The creation source of cohorts not created by the user module will also be marked after the cohort name for easy finding.

Management actions available in user cohorts are as follows. Different management actions have different requirements for cohort type, cohort settings, operator permissions, etc. See the table below:

| Management Action | Conditions to Perform Management Action |
|------------------|----------------------------------------|
| Manual Update | 1. Conditional cohort, SQL cohort; 2. Cohort supports manual update; 3. Cohort creation module allows public management; 4. Viewer has edit and delete permissions for this cohort. |
| Edit Cohort | 1. Conditional cohort (not created by operations module), SQL cohort, ID cohort; 2. Cohort creation module allows public management; 3. Viewer has edit and delete permissions for this cohort. |
| Download Import Data and Errors | 1. ID cohort; 2. Cohort creation module allows public management; 3. Viewer has edit and delete permissions for this cohort; 4. Within 7 days from data import. |
| Create Copy | 1. Conditional cohort, SQL cohort; 2. Viewer has create, edit, delete permissions for cohorts. |
| Delete Cohort | 1. Cohort creation module allows public management; 2. Viewer has edit and delete permissions for this cohort. |

Since cohorts can be used by assets such as reports, cohorts (created in operations module), and alerts, modifying or deleting cohorts may cause abnormal data fluctuations or inability to calculate for these assets. When deleting or editing a cohort that has dependent assets, the impact scope will be prompted, requiring the operator to judge the impact before proceeding with modifications.

## 4. User Cohort User List

After cohort calculation, you can view the current user count in the cohort in user cohorts. Click the user count to view the user list in the current cohort.

In the user list, you can view the cohort's condition definition (conditional cohort, SQL cohort) and user list. The table displays data for up to 1,000 rows of users. If you need more data, click the download button at the top right of the table to download up to 500,000 rows of user data.

**Note:** Clicking update at the top right of the table on the user list page only re-queries cohort result data and does not recalculate the cohort itself, but user property data for cohort users will change.

## 5. Usage Permissions

### Analysis Role Permissions

| Permission | Company Super Admin | Admin | Analyst | Regular Member |
|------------|---------------------|-------|---------|----------------|
| View cohort list | ● | ● | ● | ○ |
| Create, edit, delete self-created conditional/ID cohorts | ● | ● | △ | ○ |
| Create, edit, delete self-created SQL cohorts | ● | ● | △ | ○ |
| Create, edit, delete self-created result cohorts | ● | ▲ | ○ | ○ |
| Edit, delete others' cohorts | ● | △ | ○ | ○ |

### Operations Role Permissions

| Permission | Operations Admin | Operations | Data Engineer |
|------------|-----------------|------------|---------------|
| View cohort list | ● | ▲ | △ |
| Create, edit, delete self-created conditional/ID cohorts | ● | ▲ | △ |
| Cohort drill-down - View user list | ● | ▲ | △ |

**Permission Description:**
- ● Role must have
- ▲ Role has by default, can be removed
- △ Role doesn't have by default, can be added
- ○ Role must not have