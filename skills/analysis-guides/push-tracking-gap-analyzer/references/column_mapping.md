# Output columns and presentation

Read the user-supplied template with `+workbook-info` and `+cells-get --include value,style`. Discover sheet IDs and existing labels; never hardcode a customer's identifiers. The following default layout is used only when the template does not specify another format.

## Event sheet columns

| Column | Exact header | Meaning |
|---|---|---|
| A | 排期 | Default phase label supplied by the generator |
| B | 事件标签 | Existing module tag; preserve exact spelling |
| C | 事件名 | Event name, following source conventions |
| D | 事件显示名 | Exact existing display name for patched events |
| E | 事件说明 | Trigger, purpose, new/patch status, and strategy IDs |
| F | 属性名 | Property name; preserve object prefixes and child paths |
| G | 属性显示名 | Source/template display label; blank only if required by the object template |
| H | 属性类型 | Exact type spelling from the original plan |
| I | 属性说明 | Purpose marker and field meaning |

Use `【圈人】` for selection and `【效果回收】` for attribution. Preserve per-property descriptions. Where the template explicitly uses one shared object description, place it on the object root and leave the corresponding child descriptions blank. The generator does not erase supplied child labels or descriptions.

## Merge rules

Merge A across data rows. Merge B only across **adjacent** events with the same tag; an A/B/A tag sequence must remain three groups. Merge C, D, and E separately within each event. Never merge F/G/H. Keep I unmerged so distinct property descriptions survive. Single-cell ranges need no merge.

Generate with `--header-row 2` and import at A2: annotation is row 1, header row 2, and data starts at row 3. Ranges in `merges.json` already use these destination coordinates. Do not insert a row afterward. Replace the sheet placeholder by parsing JSON before applying operations.

## Style order

Apply broad styles first and narrow overrides last. Include URL, sheet ID, and identity flags required by the installed CLI on each call.

1. Data area A3:I(last): 13-point font, vertical middle, horizontal left, wrapped text.
2. Receipt description cells: red `#f54a45`, using the actual receipt event row spans rather than fixed row numbers.
3. Header A2:I2: blue `#4e83fd`, white bold 13-point font, centered horizontally and vertically.
4. Annotation B1:I1: white background, dark `#373c43`, bold 13-point font, left aligned and wrapped. Only merge the annotation range if it contains no other values.

Default widths A through I in pixels: 100, 120, 200, 140, 280, 250, 130, 90, 380. Freeze the first two rows. Use the template's styles if they differ.

For the other three sheets, use the same data style, header blue `#3370ff`, and annotation text orange `#f76964`. Header and annotation row offsets remain consistent across sheets.

## Other sheets

- `#推送ID`: six columns for channel name, internal/external placement, channel type, push ID, presence in user properties, and user-property name. Populate from actual channel requirements; do not infer unknown device identifiers.
- `#用户数据`: six columns for schedule, property name, display name, type, update method, and description. Include only supplementary user properties.
- `推送策略`: preserve the complete original strategy content, at the end of the workbook.

The annotation should explain the two purposes in the user's language: audience-selection instrumentation needed by the strategies, and channel receipt instrumentation for arrival/click funnels. Mention receipt passthrough properties only when confirmed by the current integration specification.

## CSV and write safety

Use Python's CSV writer so commas, quotes, and newlines remain inside the correct fields. Because `+csv-put` evaluates a leading `=` as a formula, the supplied generator prefixes such text fields with an apostrophe before export. Property continuation rows have five empty cells before F. Read the CSV back and require exactly nine columns on every row. A header-only export has no data range; skip data-area formatting and merge operations.

The CSV import does not necessarily clear stale rows. Inspect the previous managed range and clear it only after confirming the destination and overwrite scope. Never clear the original tracking plan or unrelated sheets. Keep file arguments beneath the current working directory. Border definitions use separate `top`, `bottom`, `left`, and `right` keys, not an `all` key.
