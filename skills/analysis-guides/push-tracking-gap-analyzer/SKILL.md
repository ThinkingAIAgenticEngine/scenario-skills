---
name: push-tracking-gap-analyzer
version: 2.1.0
description: Compare an existing tracking-plan Excel workbook with push notification strategies to identify missing events and properties, then produce a deduplicated gap matrix and a template-aligned supplementary Feishu spreadsheet after user confirmation. Use when the goal is tracking coverage or instrumentation supplementation. Do not use to measure a completed campaign's delivery, opens, clicks, conversions, lift, or fatigue; use engagement-effectiveness-analysis for post-execution performance analysis. Not for sending notifications, implementing SDK code, or modifying the original tracking plan.
agent_created: true
triggers:
  - 推送埋点覆盖
  - 运营埋点缺口
  - 埋点覆盖度分析
  - push tracking gap
metadata:
  domain: analytics
  methodology: tracking-plan-gap-analysis
---

# Push Tracking Gap Analyzer

Help operations and solution teams turn push strategies into a reviewable, minimal tracking supplement. Preserve the original tracking plan. Read Chinese business labels verbatim and respond in the user's language.

## Resources and prerequisites

Use Python 3.8+ with `openpyxl` for Excel reading. Feishu output additionally requires authenticated `lark-cli sheets` access. The analysis and local CSV do not require an online destination. No other skill is required.

Resolve script paths relative to this skill directory, represented below by `$SKILL_DIR`. Run from a task workspace and put intermediate files in `work/`. Local input paths must be supplied by the user or discovered from their attachments.

| Resource | When to use |
|---|---|
| `scripts/read_tracking_excel.py` | Read the entire workbook, including property continuation rows |
| `scripts/check_property_duplicates.py` | Check proposed properties against event and common properties |
| `scripts/generate_output_csv.py` | Generate correctly escaped CSV and single-column merge operations |
| [Analysis methodology](references/analysis_methodology.md) | Map each strategy to evidence before proposing additions |
| [Column mapping](references/column_mapping.md) | Build the output sheets and apply template styles |
| [Pitfalls](references/pitfalls.md) | Diagnose missing records, alignment errors, or inconsistent fields |

## Essential constraints

- Prefer a complete Excel export. A `.base` schema is not evidence of actual records. If using an API instead, exhaust pagination before declaring an event absent.
- Reuse exact existing event/property names, display names, tags, and types. Search equivalent semantics as well as exact names; the duplicate checker cannot infer semantic equivalence.
- Always assess `ops_view` and `ops_click` receipt coverage. Add only missing events or properties; do not duplicate existing receipt instrumentation. Obtain receipt fields from the user's current template or integration specification.
- Label property purposes with `【圈人】` (audience selection) or `【效果回收】` (conversion attribution).
- Use the supplied CSV generator. Merge each column independently and preserve all distinct descriptions. Never merge a rectangle spanning C through E.
- Present the complete proposed supplement for confirmation before writing to Feishu. Confirm the destination and overwrite range; never clear unrelated sheets or the source workbook.

## Workflow and validation gates

| Step | Input | Output | Validation gate |
|---|---|---|---|
| 0. Preflight | Excel and strategies | Available inputs and destination scope | Input exists; Python imports openpyxl |
| 1. Read | Source workbook | `work/tracking_data.json` | Successful parse; event count reconciles with source |
| 2. Map | Strategies and parsed events | Strategy-to-event matrix | Every supplied strategy has an evidence-backed result |
| 3. Check | Proposed additions | `work/gap_list.json`, duplicate report | Conflicts resolved; strategy ID union equals input IDs |
| 3.5. Review | Matrix and supplement | User confirmation | Destination and proposed write scope accepted |
| 4. Export/write | Confirmed gap list | CSV, merges, four destination sheets | Nine event columns; merges match actual row positions |
| 5. Verify | Destination readback | Result URL and coverage summary | Full data range and merged values match the export |

### Step 0: Preflight

Obtain the complete Excel file and strategy text. If a strategy is supplied as a link, read it using an available authorized tool; if inaccessible, request its contents. Do not substitute guessed scenarios. For Feishu delivery obtain the target URL, inspect its sheets/template, and run `lark-cli auth status`. Inspect `lark-cli sheets --help` and the relevant shortcut help before using write commands; installed CLI versions can differ.

```bash
mkdir -p work
python3 -c "import openpyxl"
```

Missing input or dependency blocks the affected step. Authentication failure blocks online writes but does not block local analysis. Report missing strategy sections and keep their coverage unresolved.

### Step 1: Read the source workbook

```bash
python3 "$SKILL_DIR/scripts/read_tracking_excel.py" \
  --input "<excel_path>" --output work/tracking_data.json
```

The reader returns `events`, `event_count`, `all_property_names`, `tag_distribution`, `public_props`, and `user_props`. Header matching supports a leading annotation row and reordered columns. Event continuation rows belong to the last named event. Check workbook row counts and sample nested properties. Zero events requires investigation; small valid plans are acceptable. On nonzero exit, fix the reported input error before mapping strategies.

### Step 2: Map all supplied strategies

Read [analysis_methodology.md](references/analysis_methodology.md). Assign each strategy a stable ID. Search event names, display labels, descriptions, property names, and documented enum values. Prefer direct evidence, then a suitable existing property value. Indirect behavior is a proxy and must retain its limitation.

Present one row per strategy: ID, audience condition, desired conversion, candidate event, matching evidence, missing fields, and coverage status. Include time windows, frequency thresholds, exclusions, and receipt/attribution needs. Do not assume a fixed number of strategies.

### Step 3: Deduplicate and prepare the supplement

Create `work/additions.json`, a JSON array of proposed properties. Each item contains `event`, `prop`, `display`, and `type` strings. Example with synthetic names:

```json
[{"event":"example_event","prop":"source","display":"Source","type":"string"}]
```

```bash
python3 "$SKILL_DIR/scripts/check_property_duplicates.py" \
  --tracking-data work/tracking_data.json \
  --additions @work/additions.json --output work/check_result.json
```

Interpret `duplicate_on_event` and `public_prop` as already covered, `exists_elsewhere` as a naming convention to reuse, `duplicate_in_additions` as a repeated proposal to remove, and `conflict` as requiring reconciliation. The checker evaluates all occurrences and repeated proposal keys; a matching first occurrence does not hide a later conflict. Exit 1 requires revising the additions and rerunning the check. Also search semantic equivalents manually.

Write `work/gap_list.json` with arrays `ops_events`, `new_events`, and `patch_events`. Each event has `name`, `display`, `tag`, `desc`, and `props`; each property has `name`, `display`, `type`, and `desc`. Include only missing properties on patched events. Consolidate repeated event references and record strategy IDs in descriptions. Covered strategies remain in the matrix even if they contribute no CSV rows.

Validate the **set union** of strategy IDs across new, patched, covered, and unresolved results against all input IDs. Counting category totals can hide an omitted strategy. Resolve material uncertainties before claiming complete coverage.

### Step 3.5: Review gate

Show the complete matrix, proposed additions, naming conflicts, and unresolved assumptions. Ask the user to confirm the supplement and destination write scope. If changes are requested, revise and recheck. Do not treat silence as confirmation. Local export may be prepared for review before approval.

### Step 4: Generate and write

```bash
python3 "$SKILL_DIR/scripts/generate_output_csv.py" \
  --gap-list @work/gap_list.json \
  --output-csv work/events.csv --output-merges work/merges.json \
  --header-row 2
```

`--header-row 2` reserves destination row 1 for the annotation, so import CSV at A2. The CSV itself begins with its header; merge ranges are already offset to row 3 onward. Do not insert another row after generating these ranges. Use `--header-row 1` only when importing at A1 without an annotation.

If all strategies are already covered, the generator emits a header-only CSV, no merge operations, and `data_rows: null`. Skip data-area styling and merging in that case; still preserve the complete coverage matrix and report that no event/property supplement is required.

Read [column_mapping.md](references/column_mapping.md). Discover actual sheet IDs using `+workbook-info`. For an existing destination, read and bound the old output range, then clear only the confirmed managed area so shorter replacements leave no stale rows. Stop if that would touch unrelated content.

Example command shapes (verify against installed help):

```bash
lark-cli sheets +cells-clear --url "<output_url>" --sheet-id "<sheet_id>" --range "A1:I<old_last_row>" --scope all --as user --yes
lark-cli sheets +csv-put --url "<output_url>" --sheet-id "<sheet_id>" --start-cell A2 --as user --csv @work/events.csv
```

Replace `{SHEET_ID}` in merge JSON with the discovered ID using JSON parsing, then run `+batch-update --operations @work/merges-resolved.json`. Keep referenced files beneath the current working directory. Add the annotation at row 1 and apply styles in the documented order. Populate the push identifier and user-property sheets from confirmed channel requirements, and preserve the complete supplied strategies in the last sheet. Leave unknown identifiers unresolved instead of inventing them.

On write failure, stop, report the affected sheet/range and partial state, and read back before retrying. Do not blindly repeat sheet creation or destructive clearing.

### Step 5: Verify and deliver

Read back the full populated ranges with `+csv-get` or `+cells-get`, not just the first five rows. Reconcile event/property counts, tags, exact F-column property names, D/E descriptions, object children, merge ranges, and the strategy ID set. Check sheet order and styling. Fix mismatches within the confirmed scope and verify again.

Deliver the destination URL, counts of new events and patched properties, covered/unresolved strategy counts, and any remaining limitations. If online delivery is blocked, report that explicitly and provide the local CSV for review; do not claim a completed Feishu write. Keep review artifacts until delivery is accepted.

## Output contract

The supplementary Feishu workbook contains four sheets, using the user's template where available:

| Sheet | Columns / content |
|---|---|
| `#事件数据` | Nine columns described in the column mapping |
| `#推送ID` | Channel name, internal/external, channel type, push ID, user-property presence, user-property name |
| `#用户数据` | Schedule, property name, display name, type, update method, description |
| `推送策略` | Complete original strategy content |

Measure completeness by reviewed strategy IDs and deduplicated additions. Do not promise an unsupported time saving. The original tracking workbook remains unchanged.
