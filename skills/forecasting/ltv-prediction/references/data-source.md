# LTV Prediction — ae-cli 6.0.42 Data Source

## Command contract

- CLI command segments and flags use kebab-case.
- `analysis adhoc run` accepts an AI-facing `--definition`; never pass raw QP,
  `eventView`, internal A-codes, or removed builder/schema output.
- AI-facing definition keys use snake_case and semantic aggregations such as
  `sum`, `user_count`, and `avg_per_user`.
- Use synchronous `run` only for at most 1000 inline rows. Use the corresponding
  `export` command for complete or unknown-size data.

## Three-path priority

### 1. Reuse an existing report or dashboard

```bash
ae-cli analysis report list \
  --project-id <project_id> \
  --queries '["LTV"]'

ae-cli analysis dashboard list \
  --project-id <project_id> \
  --queries '["LTV"]'

ae-cli analysis report-data run \
  --project-id <project_id> \
  --report-ids '[<report_id>]' \
  --start-time "YYYY-MM-DD" \
  --end-time "YYYY-MM-DD"

ae-cli analysis dashboard get \
  --project-id <project_id> \
  --dashboard-id <dashboard_id>

ae-cli analysis dashboard-report-data run \
  --project-id <project_id> \
  --dashboard-id <dashboard_id> \
  --start-time "YYYY-MM-DD" \
  --end-time "YYYY-MM-DD"
```

Inspect a report with `analysis report get` before applying overrides. SQL
reports use saved `--sql-params`; the generic time overrides above are for
non-SQL analysis reports.

### 2. Run an ad-hoc revenue analysis

Submit the semantic definition first. If compilation returns structured
clarification candidates or an explicit resolution capability error, inspect
metadata:

```bash
ae-cli analysis-meta event list \
  --project-id <project_id> \
  --queries '["<payment_keyword>"]'

ae-cli analysis-meta property list \
  --project-id <project_id> \
  --scope event \
  --event-name "<payment_event>"
```

Query cohort LTV and cumulative revenue:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type revenue \
  --definition '{
    "time_range":{"mode":"custom","start_time":"YYYY-MM-DD","end_time":"YYYY-MM-DD"},
    "initial_event":{"event":"<cohort_event>"},
    "pay_event":{"event":"<payment_event>"},
    "revenue_metric":{"event":"<payment_event>","aggregation":"sum","property":"<amount_property>"},
    "observation_days":30,
    "selected_metrics":["payAmount","cumPayAmount","ltv"]
  }'
```

Query LTV by VIP level:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type revenue \
  --definition '{
    "time_range":{"mode":"custom","start_time":"YYYY-MM-DD","end_time":"YYYY-MM-DD"},
    "initial_event":{"event":"<cohort_event>"},
    "pay_event":{"event":"<payment_event>"},
    "revenue_metric":{"event":"<payment_event>","aggregation":"sum","property":"<amount_property>"},
    "observation_days":30,
    "selected_metrics":["payAmount","cumPayAmount","ltv"],
    "groups":[
      {"field":{"name":"<vip_property>","type":"user_property"}}
    ]
  }'
```

Query one RFM/tag segment:

```bash
ae-cli analysis user-tag list \
  --project-id <project_id> \
  --queries '["<rfm_keyword>"]'

ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type revenue \
  --definition '{
    "time_range":{"mode":"custom","start_time":"YYYY-MM-DD","end_time":"YYYY-MM-DD"},
    "initial_event":{"event":"<cohort_event>"},
    "pay_event":{"event":"<payment_event>"},
    "revenue_metric":{"event":"<payment_event>","aggregation":"sum","property":"<amount_property>"},
    "observation_days":30,
    "selected_metrics":["payAmount","cumPayAmount","ltv"],
    "groups":[
      {"field":{"name":"<rfm_tag>","type":"tag"}}
    ]
  }'
```

### 3. Save a verified analysis

Only write assets when the user explicitly asks. Reuse the exact AI-facing
definition that was successfully queried.

```bash
ae-cli analysis report create \
  --project-id <project_id> \
  --report-name "<report_name>" \
  --model-type revenue \
  --definition '<verified_ai_definition>'

ae-cli analysis dashboard create \
  --project-id <project_id> \
  --dashboard-name "<dashboard_name>" \
  --initial-report-id <report_id>
```

## Python curve fitting

Use the packaged requirements in an isolated environment. Resolve `SKILL_DIR`
from the installed Skill location; never hardcode a user home directory.

```bash
python3 -m venv "$SKILL_DIR/.venv"
"$SKILL_DIR/.venv/bin/python" -m pip install \
  -r "$SKILL_DIR/scripts/requirements.txt"
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/fit_ltv.py" --help
```

Ask before installing dependencies. Never pass `--break-system-packages`.
