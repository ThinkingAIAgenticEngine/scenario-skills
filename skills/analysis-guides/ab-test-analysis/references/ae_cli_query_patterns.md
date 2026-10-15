# ae-cli Query Patterns for A/B Test Analysis

## Overview

All queries use the curated entry point `ae-cli analysis adhoc run`. Pass the
project, model and model definition separately with `--project-id`,
`--model-type` and `--definition`. Do not wrap them in the legacy generic
Capability Gateway `{project_id, model_type, definition}` input object.

The `model_type` is not a preference — it is the only thing that can enforce the
data caliber each test needs:

| Metric kind | Required `model_type` | Why this one and not another |
|-------------|----------------------|------------------------------|
| Conversion rate / guardrail rate (proportion) | `funnel` | Only the funnel model imposes "exposed **then** converted", which is what makes the numerator a subset of the denominator |
| Per-user value (ARPU, duration, count) | external `user_level` distribution over the exposed cohort | Welch's t-test needs one observation per exposed user, including zero contributors; an event aggregate cannot prove that population or provide its variance |
| Day-N retention | `retention` | The nested `retention` object is the only form the model reads |

### Gate every query before you run it

```bash
python scripts/check_query_definition.py {workspace}/tmp/query_{name}.json \
  --model-type event|funnel|retention \
  --kind proportion|guardrail|continuous|retention \
  --exposure-event <EXPOSURE_EVENT> --variant-field <VARIANT_FIELD>
```

Exit `0` = pass (SUCCESS/WARN), `1` = the query cannot support the declared test.
Every contract below is enforced by that script, so a query that violates one of
them fails here instead of producing plausible numbers for the wrong population.

**Before building any query**: run Step 0b (field alignment). The placeholders
below — `<VARIANT_FIELD>`, `<EXPOSURE_EVENT>`, `<SUCCESS_EVENT>` and their
`field.type` — come from `{workspace}/tmp/field_mapping.json`, not from a fresh
reading of the user's message. Alias tables, value-domain rules and the
mismatch-diagnosis table live in `references/field_mapping.md`.

## The three calibers (get these wrong and every number downstream is wrong)

### Caliber 1 — the numerator must be inside the exposed cohort, and later in time

Counting exposure users and success users as **two independent `user_count`
metrics** does not produce a conversion rate. Nothing in that query
constrains the success users to be exposed users, and nothing constrains the
success to happen *after* the exposure. The usual visible symptoms are a
conversion rate above 100%, or a rate that is quietly diluted by users who
converted for other reasons. Scenario A below is the construction that does
enforce it.

### Caliber 2 — a per-user metric needs the per-user distribution over the cohort

ARPU is `revenue / exposed users`. The temptation is to query the average and
standard deviation of the purchase amount and hand those to Welch's t-test with
`n = number of paying users`. That describes **the distribution of payers** —
it drops every exposed user who paid nothing, which in most experiments is the
large majority of the cohort. The comparison then becomes "how much do payers
pay", which is a different question and a much friendlier one. See Scenario B.

### Caliber 3 — the retention contract is nested

`initial_event` / `return_event` / `stat_type` / `unit_num` /
`rtn_rate_or_num` all live **inside** `definition.retention`. A top-level
`definition.initial_event` is not an error — it is ignored, and the query
returns a different cohort while looking perfectly well-formed. See Scenario C.

---

## Scenario A: Conversion Rate (Proportion Metric)

Two-step funnel, grouped by the variant field. Step 1 is the exposure event and
defines the denominator; step 2 is the success event and defines the numerator.

```bash
ae-cli analysis adhoc run \
  --project-id <PROJECT_ID> \
  --model-type funnel \
  --definition '{
  "time_range": {"mode": "recent", "unit": "day", "value": 7},
  "time_particle_size": "total",
  "funnel": {
    "steps": [
      {"event": "<EXPOSURE_EVENT>"},
      {"event": "<SUCCESS_EVENT>"}
    ],
    "window": {"value": 7, "unit": "day"},
    "groups": [{"field": {"name": "<VARIANT_FIELD>", "type": "event_property"}}]
  }
}'
```

- **step 1 = exposure** → its user count is `control_total` / `treatment_total`.
- **step 2 = success** → its user count is `control_success` /
  `treatment_success`, and it is by construction a subset of step 1.
- **`window`** is not optional in practice. Without it the funnel accepts a
  success at any later time, so the lift ends up measuring "more time has
  passed" rather than the change. Set it to the experiment's intended
  decision horizon, and state it in the report.
- If a user can be exposed more than once, the funnel still counts users once
  per step — that is the correct unit for a proportion test.

If the compiler reports an unresolved or ambiguous field, run the corrected
definition once with `--dry-run` and inspect `meta.compile_status`,
`meta.errors[]`, `meta.resolved` and `meta.warnings`. Do not routinely dry-run
an already complete, confirmed definition.

## Scenario A2: Guardrail Rate (Proportion, must not regress)

Same funnel shape — the guardrail event replaces the success event. Using the
**same cohort** for the guardrail and the success metric is the point: a
crash-rate computed over a different population than the conversion rate is how
reports end up saying "conversion is up and crashes are up" about two different
user sets.

```bash
ae-cli analysis adhoc run \
  --project-id <PROJECT_ID> \
  --model-type funnel \
  --definition '{
  "time_range": {"mode": "recent", "unit": "day", "value": 7},
  "time_particle_size": "total",
  "funnel": {
    "steps": [
      {"event": "<EXPOSURE_EVENT>"},
      {"event": "<CRASH_EVENT>"}
    ],
    "window": {"value": 7, "unit": "day"},
    "groups": [{"field": {"name": "<VARIANT_FIELD>", "type": "event_property"}}]
  }
}'
```

**Polarity is mandatory to get right.** Crash rate, refund rate, error rate and
latency all get WORSE when they go up, so their metric definition must carry
BOTH flags:

```python
{"name": "崩溃率", "type": "proportion", "is_guardrail": True, "lower_is_better": True,
 "control_success": ..., "control_total": ..., "treatment_success": ..., "treatment_total": ...}
```

For a guardrail that must not DROP (exposure volume, engagement depth) set
`"lower_is_better": false`. If you omit the flag on a guardrail the engine infers
it from the metric name and defaults to `true`; that default is right for harm
metrics, but declare it explicitly anyway and check the report's
"方向假设（未显式声明，请核对）" block before delivering a conclusion.

## Scenario B: Per-User Value (Continuous Metric)

The unit of observation must be the **user over the exposed cohort**.

### Descriptive only: event-model `avg_per_user`

```bash
ae-cli analysis adhoc run \
  --project-id <PROJECT_ID> \
  --model-type event \
  --definition '{
  "time_range": {"mode": "recent", "unit": "day", "value": 7},
  "metrics": [
    {"event": "<SUCCESS_EVENT>", "aggregation": "avg_per_user", "property": "<AMOUNT_PROPERTY>"}
  ],
  "groups": [{"field": {"name": "<VARIANT_FIELD>", "type": "event_property"}}]
}'
```

This query may provide a useful point estimate, but it is **not** a valid Welch
input by itself. The aggregate does not establish that exposed users who never
fired the metric event were included as zero, and it does not return the
per-user standard deviation over that same exposure cohort. Report it as
descriptive unless a user-level distribution supplies the inferential inputs.

### Rejected: the payers-only distribution

```jsonc
// ✗ DO NOT USE — this is the distribution of PAYERS, not of the cohort
"metrics": [
  {"event": "<SUCCESS_EVENT>", "aggregation": "stddev", "property": "<AMOUNT_PROPERTY>"},
  {"event": "<SUCCESS_EVENT>", "aggregation": "avg",    "property": "<AMOUNT_PROPERTY>"},
  {"event": "<SUCCESS_EVENT>", "aggregation": "user_count"}
]
```

`avg`/`stddev` here average over the events (or the users who fired them), and
`user_count` is the number of paying users. Feeding those three numbers to
Welch's t-test compares paying users with paying users and reports it as an
ARPU comparison. `scripts/check_query_definition.py --kind continuous` rejects
this shape by name.

### Accepted for inference: an external user-level distribution

Take the distribution from a user-level export (detail data / data bank /
warehouse) that carries exactly one row per exposed user, including an explicit
zero for users with no contribution. Compute mean, standard deviation and n
from those same rows in each arm, and declare it:

```bash
python scripts/check_query_definition.py {workspace}/tmp/query_arpu.json \
  --model-type event --kind continuous --distribution user_level
```

### If only aggregates are available

Do **not** run a t-test on a mean whose variance you cannot attribute to the
cohort. Report the point estimate (ARPU per arm, `sum / exposed users`) as a
descriptive comparison and state in the report that the variance needed for a
t-test was unavailable — the engine marks a continuous metric without a
defensible `n` the same way. A descriptive number with a stated limitation is
usable; a t-test on the wrong distribution is not.

## Scenario C: Retention Impact

`initial_event`, `return_event`, `stat_type`, `unit_num` and `rtn_rate_or_num`
belong to the **nested `retention` object**. The model's required keys are
`initial_event`, `return_event`, `unit_num`.

```bash
ae-cli analysis adhoc run \
  --project-id <PROJECT_ID> \
  --model-type retention \
  --definition '{
  "time_range": {"mode": "recent", "unit": "day", "value": 21},
  "time_particle_size": "total",
  "retention": {
    "initial_event": "<EXPOSURE_EVENT>",
    "initial_filters": [],
    "return_event": "<LOGIN_EVENT>",
    "groups": [{"field": {"name": "<VARIANT_FIELD>", "type": "event_property"}}],
    "unit_num": 7,
    "stat_type": "retention",
    "rtn_rate_or_num": "rate"
  }
}'
```

| Field | Required | Meaning / accepted values |
|-------|----------|---------------------------|
| `initial_event` | yes | The event that forms the cohort. Use the exposure event so the retention cohort is the experiment cohort. |
| `return_event` | yes | The event that counts as "came back" (usually `$app_start` / `login`). |
| `unit_num` | yes | Interval size: `1` = D1, `7` = D7 (`14` = D14). Integer ≥ 1. |
| `stat_type` | declare explicitly | `retention` = users who came back; `lost` = users who did not. Opposite-signed numbers that look equally valid downstream, so it has no safe implicit reading. |
| `rtn_rate_or_num` | declare explicitly | Rate forms `R0` / `rate` / `retention`; count forms `R1` / `number` / `count` (defaults to `R0`). **This skill needs the rate** — a count would have to be divided by a cohort size you did not query. |
| `initial_filters` | optional | Event-only filters, `[{"event_property_name": ..., "operator": "eq", "values": [...]}]`. This is where cohort filters go. |
| `groups` | needed for A/B | Include the variant field, otherwise the result cannot be split into control/treatment. |

**Two keys that look harmless and are not** (they are valid on other models, so
they read as fine here and simply change nothing):

- `definition.filters` — not supported by the retention model; use
  `retention.initial_filters`.
- `definition.time_granularity` — not supported; use `time_particle_size`.

**The flat form is worse than wrong, it is silently wrong:**

```jsonc
// ✗ DO NOT USE — the model ignores these keys and returns the wrong cohort
"definition": {
  "time_range": {"mode": "recent", "unit": "day", "value": 14},
  "initial_event": "<EXPOSURE_EVENT>",
  "return_event": "<LOGIN_EVENT>",
  "retention_type": "retention",
  "retention_window": [7]
}
```

Retention rate is returned **per group**; the value is a proportion, so it feeds
the two-proportion z-test. The denominator is the cohort size, which the
retention model already uses for the rate — read it, do not substitute the
success count.

## Adding Global Filters

Event-model and funnel queries accept definition-level filters:

```json
{
  "filters": [
    {"field": {"name": "platform", "type": "event_property"}, "operator": "eq", "values": ["ios"]}
  ]
}
```

Retention queries do not — see the two unsupported keys above.

## User Property as Variant

If the variant assignment is stored as a user property (not an event property):

```json
{
  "groups": [
    {"field": {"name": "<VARIANT_FIELD>", "type": "user_property"}}
  ]
}
```

## Time Range Modes

| Mode | Meaning | Example |
|------|---------|---------|
| `recent` | Last N units including today (data for today may be partial) | recent 7 days = today + past 6 days |
| `previous` | Last N completed units excluding today | previous 7 days = past 7 days |
| `custom` | Explicit start/end | 2026-01-01 to 2026-01-14 |
| `start_to_today` | Fixed start through today | 2026-01-01 to today |
| `start_to_yesterday` | Fixed start through yesterday | 2026-01-01 to yesterday |

State which mode was used in the report. `recent` including today is the most
common cause of a "the numbers moved" scare that is really just an incomplete
last day.

## Conditional Dry-Run Validation

```bash
ae-cli analysis adhoc run \
  --project-id <PROJECT_ID> \
  --model-type <MODEL_TYPE> \
  --definition '<DEFINITION_JSON>' \
  --dry-run
```

Use this only when a concrete complex-input or metadata-resolution problem
needs a preflight. On `AI_QP_COMPILE_FAILED`, inspect `meta.compile_status`,
`meta.errors[]`, `meta.resolved` and `meta.warnings`, correct the reported paths,
then execute the same corrected definition once. A complete definition with
confirmed fields should execute directly.

## Output Structure

```json
{
  "ok": true,
  "data": {
    "title": ["时间", "<group_field_name>", "<metric1_name>", "<metric2_name>", ...],
    "rows": [
      ["<time_range>", "<group_value>", "<metric1_value>", "<metric2_value>", ...],
      ["<time_range>", "<group_value>", "<metric1_value>", "<metric2_value>", ...]
    ],
    "returned_rows": 2,
    "has_more": false,
    "request_id": "...",
    "model_type": "funnel",
    "effective_zone_offset": 99,
    "query_context_id": "...",
    "sources": [...],
    "definition": {...}
  }
}
```

**Key details**:
- `data.title[0]` is always the time dimension column ("时间")
- `data.title[1]` is the group field name (e.g., "ab_group")
- `data.title[2+]` are metric column names (may be display names, not raw field names)
- `data.rows[i][0]` is the time range string (e.g., "2026-09-09至2026-09-15")
- `data.rows[i][1]` is the group value (e.g., "control" or "treatment")
- `data.rows[i][2+]` are metric values — **all returned as STRINGS, not numbers**
- `data.has_more` — whether pagination is needed; a truncated result silently
  becomes a smaller sample, so check it

## The next gate: `validate_query_output.py`

```bash
python scripts/validate_query_output.py {workspace}/tmp/query_output.json \
  {workspace}/tmp/field_mapping.json
```

Pass the field mapping so the gate knows **which returned column is the exposed
cohort** (from `cohort.denominator_column`) instead of guessing from column
names. With it, the gate:

- applies the `MIN_SAMPLE` floor to the **denominator only** — the exposed
  cohort is what has to be large enough; a small success count inside a large
  cohort is a low conversion rate, not an insufficient sample;
- requires every numerator cell to be ≤ its denominator (catches a success
  count that was not restricted to the cohort);
- flags a zero numerator as a degenerate arm rather than passing it silently;
- refuses to guess the denominator when more than one column looks like a user
  count, so a numerator (e.g. 付费用户数) can never be mistaken for the sample
  size.

It reports a new status: `SUCCESS`, `WARN` (proceeds, with something to confirm),
`EMPTY`, `ERROR`, `FATAL`. Only `SUCCESS` and `WARN` exit 0.

## From Query Output to Analysis Input

`ab_test_stats.py` does NOT consume ae-cli output directly. The orchestrator
converts `data.rows` into a `{metrics: [...]}` object (see SKILL.md Step 2a).

**Proportion metric** (from Scenario A / A2 — funnel output):

```python
# row = [time, group, exposed_users, success_users]  (strings)
# column indices come from data.title, not from position guessing
for row in rows:
    group = row[1]
    exposed = int(row[2])
    success = int(row[3])
    if group == control_value:
        control_total, control_success = exposed, success
    else:
        treatment_total, treatment_success = exposed, success
# → {"type": "proportion", "control_success": ..., "control_total": ...,
#    "treatment_success": ..., "treatment_total": ...}
```

**Continuous metric** (from Scenario B per-user rollup):

```python
# mean, std and n must be computed from the same external user-level dataset;
# it has one row per exposed user and includes zero contributors.
# → {"type": "continuous", "control_mean": ..., "control_std": ..., "control_n": <exposed users>,
#    "treatment_mean": ..., "treatment_std": ..., "treatment_n": <exposed users>}
```

**Retention metric** (from Scenario C):

```python
# the retention model returns a rate per group; the cohort size is the model's
# own denominator. Convert the rate to a count only if the cohort size is returned.
# → {"type": "proportion", "control_success": ..., "control_total": ...,
#    "treatment_success": ..., "treatment_total": ...}
```

**Always fill experiment metadata** in the assembled object (used verbatim in
the report): `experiment_name`, `control_name`, `treatment_name`, `time_range`,
`hypothesis`, `group_field`, `group_field_type`, `project_name`, `project_id`,
and `cohort_basis` (copy `cohort.basis` from the mapping).

Also propagate the two optional flags when the metric comes from a guardrail query:

| Flag | When | Effect |
|------|------|--------|
| `is_guardrail` | Metric must not regress | Drives the guardrail verdict and the overall "stop" recommendation |
| `lower_is_better` | Smaller value = better outcome | Flips verdict, business significance, Bayesian probability, risk ladder and the guardrail check. `true` for crash/refund/error/latency; `false` for retention/GMV/exposure |

Both flags are also part of the Bonferroni family (default `family: "all"`), so
guardrail metrics are subject to the same corrected threshold as success metrics
— see SKILL.md → "Multiple comparisons".

## Common Pitfalls

1. **All metric values are strings** — convert with `int()` / `float()` before arithmetic.
2. **First column is always time** — skip `row[0]` when extracting group values.
3. **Group order is NOT guaranteed** — read `row[1]` to determine control vs treatment.
4. **Column names may be display names** — e.g. "充值成功" instead of `payment.user_count`; map by name, not by index.
5. **`data.data` does NOT exist** — use `data.rows` and `data.title`.
6. **`has_more: true`** — the result is truncated; page it or the sample size is silently wrong.
7. **A rate column is not a count** — if the query returns only a pre-computed rate, the gate cannot build a z-test input from it; re-query with the counts.
8. **Two independent `user_count` metrics are not a conversion rate** — see Caliber 1.
9. **`avg`/`stddev` of the purchase event is not ARPU** — see Caliber 2.
10. **A flat `initial_event` is ignored, not rejected** — see Caliber 3.
