# churn-define | ae-cli 6.0.42 Asset Guide

Use this reference when the user wants to turn a churn definition into
queryable or persisted TE assets. Read the matching current `ae-analysis`
reference before every write command.

## 1. Resolve Real Fields

For virtual-property SQL, discovery is mandatory:

```bash
ae-cli analysis-meta property list --project-id <project_id>
ae-cli analysis-meta event list --project-id <project_id>
```

Do not invent event tables, last-active fields, payment properties, or SQL
identifiers. Quote Trino identifiers containing `#`, `$`, or `@`.

## 2. Create a Days-since-last-active Virtual Property

Creating metadata is a write operation. Explain the proposed property name,
source field, expression, and target project before execution.

```bash
ae-cli analysis-meta virtual-property create \
  --project-id <project_id> \
  --property-name '#vp@last_active_days' \
  --property-desc 'Days Since Last Active' \
  --table-type user \
  --select-type number \
  --sql-expression '<metadata-verified SQL expression>' \
  --sql-event-relation-type relation_default
```

Validate the expression against the discovered metadata before the real create.
Never copy a machine-specific SQL expression from an example into another
project.

## 3. Optional First/Last Tag

Use `analysis user-tag create` only when the churn definition truly requires a
persisted first/last-derived tag. Read `user_tag_models.md` and build its
`--definition-request` from real metadata. A successful create starts
computation; follow the returned `next_action` and poll `user-tag get` until the
result is fresh. Do not call refresh immediately after create.

## 4. Validate the Segmentation with Property Analysis

Run the query before saving a report:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type prop_analysis \
  --definition '{
    "prop_analysis": {
      "metric": {"aggregation": "user_count"},
      "groups": [
        {"field": {"name": "#vp@last_active_days", "type": "user_property"}}
      ],
      "filters": [
        {
          "field": {"name": "#vp@last_active_days", "type": "user_property"},
          "operator": "between",
          "values": [7, 30]
        }
      ]
    }
  }'
```

The definition is AI-facing. Do not pass raw QP, frontend DTOs, internal
aggregation codes, or a project ID inside it. Check `meta.resolved`,
`meta.warnings`, timezone, and actual cluster scope.

## 5. Save the Verified Report

Only after the ad-hoc query succeeds and the user confirms the asset name:

```bash
ae-cli analysis report create \
  --project-id <project_id> \
  --report-name "Churned User Days Distribution" \
  --model-type prop_analysis \
  --definition '<same verified definition>'
```

Keep the exact `report_id` returned by this command. Verify it with:

```bash
ae-cli analysis report-data run \
  --project-id <project_id> \
  --report-ids '[<report_id>]'
```

## 6. Create a Dashboard

After user confirmation:

```bash
ae-cli analysis dashboard create \
  --project-id <project_id> \
  --dashboard-name "Churn Monitoring" \
  --initial-report-id <report_id>
```

Use the returned dashboard ID. If more report attachment or dashboard settings
are needed, read the current `dashboard update` reference rather than guessing
an operation payload.

## Error Handling

- Compilation failure: inspect `meta.errors`, exact candidates, `resolved`, and
  warnings; select a returned candidate or ask the user.
- Empty business result: distinguish an explicit project-no-data response from
  a failed command or generic empty object.
- Tag still computing: continue polling the returned next action; do not use
  stale membership counts.
- Write failure: report the request ID and error. Never claim that an asset was
  created without a returned ID.
