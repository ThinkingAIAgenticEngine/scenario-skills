# First Purchase Analysis — ae-cli 6.0.42 Data Source

## Prerequisites

```bash
ae-cli auth status
```

Submit the semantic definition in Priority 2 first. Inspect compiler resolution
and warnings. Only after structured clarification, query `analysis-meta
event/property list` and select an exact returned candidate. Do not assume
`first_purchase` or `user_register` exists in every project.

## Priority 1: Existing assets

```bash
ae-cli analysis dashboard list \
  --project-id <project_id> \
  --queries '["<first_purchase_keyword>"]'

ae-cli analysis dashboard get \
  --project-id <project_id> \
  --dashboard-id <dashboard_id>

ae-cli analysis dashboard-report-data run \
  --project-id <project_id> \
  --dashboard-id <dashboard_id> \
  --start-time "YYYY-MM-DD" \
  --end-time "YYYY-MM-DD"

ae-cli analysis report list \
  --project-id <project_id> \
  --queries '["<first_purchase_keyword>"]'

ae-cli analysis report-data run \
  --project-id <project_id> \
  --report-ids '[<report_id>]' \
  --start-time "YYYY-MM-DD" \
  --end-time "YYYY-MM-DD"
```

## Priority 2: Direct event analysis

One event-model query can return first-time payer users and new registered users
over the same scope:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --definition '{
    "time_range":{"mode":"custom","start_time":"YYYY-MM-DD","end_time":"YYYY-MM-DD"},
    "time_particle_size":"day",
    "metrics":[
      {"event":"<first_purchase_event>","aggregation":"user_count"},
      {"event":"<registration_event>","aggregation":"user_count"}
    ]
  }'
```

Compute:

```text
first_purchase_rate = first_purchase_users / registered_users
```

Do not pass raw QP, `eventView`, `events`, internal A-codes, or removed
schema/builder output to `analysis adhoc run`.

## Priority 3: Save a verified analysis

Only create assets after explicit user approval, and only reuse a definition
that has already succeeded with `analysis adhoc run`.

```bash
ae-cli analysis report create \
  --project-id <project_id> \
  --report-name "first_purchase_rate_trend" \
  --model-type event \
  --definition '<verified_ai_definition>'

ae-cli analysis dashboard create \
  --project-id <project_id> \
  --dashboard-name "First Purchase Rate Monitoring" \
  --initial-report-id <report_id>
```

The report-create response supplies the new report ID; do not list all reports
again merely to rediscover it.

## Output and error rules

- CLI flags use kebab-case.
- AI-facing definition keys use snake_case.
- `--request-id` is optional and ae-cli generates a `cli_...` value when
  omitted.
- Use `adhoc export`, `report-data export`, or `dashboard-report-data export`
  for complete or unknown-size results.
- Treat empty data as a scope/mapping issue to investigate, not as a zero rate.
