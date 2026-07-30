# Date Versions of Tags

For data condition-type tags, user tag values may differ with each calculation. When analyzing historical data, sometimes we need to use user tags from a historical moment or from when historical behavior occurred. In the system, you can use tag date versions to save tag marking situations from a historical date.

## 1. Creating Tag Date Versions

You can add version data for historical dates for tags through the following two methods:

### Method A: Automatic Backup

When creating or modifying data condition-type tags, after enabling auto-update, also enable the auto-backup switch.

After the switch is turned on, at the daily auto-update time, the system will simultaneously calculate yesterday's tag data once and save it as yesterday's date version.

**Note:** Auto-backup uses yesterday's backed up user data and user behavior data up to yesterday 23:59:59 when calculating yesterday's tags.

Besides daily single update, the system also supports multiple daily updates, weekly updates, and monthly update logic.

### Method B: Manual Addition via Version Management

Click the tag name in the user tag list to jump to the tag detail page, and add in version management.

When you need to retroactively calculate tag data for a historical date, or add a historical date version for a tag without auto-update enabled, you can add or recalculate through the version management entry.

In "Version Management", you can configure the data rules for retroactive calculation, as shown below.

| Configuration | User Data Used |
|--------------|----------------|
| Not using user historical data | Use current user data |
| Using user historical data - User data exists for a date | Use user data for that date |
| Using user historical data - User data does not exist for a date | Choose one of two strategies: |
| | • Missing date "Use current user data as replacement" |
| | • Missing date "Use relatively nearest user data as replacement" |

Since user property data is updatable, it's generally recommended to use user historical data to approximately obtain the data result of calculating that tag on that day.

## 2. Using Tag Date Versions

If the tag being used has multiple date version data, when used in analysis filtering or grouping, or when creating virtual properties, you can specify the required version:

- **Latest Version**: Calculate based on user's current tag value
- **Dynamic Matching**: Calculate based on user's tag value on the day the event occurred
- **Historical Version**: Calculate based on user's tag value on a specified date

**Note:** Currently, event analysis, retention analysis, funnel analysis, distribution analysis, path analysis, and interval analysis support tag version selection. Property analysis can only use the latest version of tags.