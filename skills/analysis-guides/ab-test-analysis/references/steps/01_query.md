# Step 1 - Query Experiment Data

> Procedure file for **Step 1** in `SKILL.md`.
> Caliber templates (Caliber 1/2/3, Scenario A/A2/B/C) and pitfalls: `references/ae_cli_query_patterns.md`.

## Goal

Retrieve group data that is **statistically defensible**: success users must be a subset of the exposed
cohort and must have converted after exposure; continuous inference must use a declared one-row-per-exposed-user
distribution rather than an aggregate or payers-only distribution; retention must follow the nested retention contract. This step has two gates -
one that inspects the query definition **before a query is spent**, and one that inspects the data
**after it comes back**.

## Input

| Source | Content |
|--------|---------|
| `{ws}/tmp/field_mapping.json` (produced by Step 0b) | Group field and its two values, exposure event, success/guardrail events, the `cohort` block |
| `references/ae_cli_query_patterns.md` | The query template matching each metric kind |
| The user | The time range and any global filters, asked once and not asked again |

## Output

| Artifact | Meaning |
|----------|---------|
| Query definition JSON | The model-specific object passed to `ae-cli analysis adhoc run --definition`; it excludes project ID and model type |
| `{ws}/tmp/query_output.json` | The raw `ae-cli` response, `{ok, data:{title, rows}}` |

## Executor

Orchestrator. Build and run the `ae-cli` commands directly.

## Validation Gate

Two gates, in order; both must pass:

```bash
# Gate 1: before the query is sent - check the caliber
python scripts/check_query_definition.py <definition.json> \
  --model-type event|funnel|retention \
  --kind proportion|guardrail|continuous|retention \
  --exposure-event {exposure_event} \
  --variant-field {variant_field} \
  [--distribution user_level]

# Gate 2: after the data returns - check the data itself
python scripts/validate_query_output.py {ws}/tmp/query_output.json {ws}/tmp/field_mapping.json
```

A complete definition with confirmed fields executes directly:

```bash
ae-cli analysis adhoc run \
  --project-id {project_id} \
  --model-type {model_type} \
  --definition '<DEFINITION_JSON>' \
  --preview-rows 100 \
  --format json > {ws}/tmp/query_output.json
```

If compilation reports a concrete metadata-resolution or complex-input issue,
run the corrected definition once with `--dry-run`. Inspect
`meta.compile_status`, `meta.errors[]`, `meta.resolved` and `meta.warnings`, then
execute that same corrected definition once. Do not routinely stack dry-run and
execution for definitions whose fields are already confirmed.

## Failure Handling

| Situation | Status | Action |
|-----------|--------|--------|
| The definition counts exposure and success as independent user counts | FATAL | Switch to the funnel model: step 1 = exposure, step 2 = success plus a conversion window |
| Continuous inference uses event aggregates (`avg`, `stddev`, or standalone `avg_per_user`) | FATAL | Supply one row per exposed user, including zero contributors, and pass `--distribution user_level`; otherwise report only a descriptive point estimate |
| Retention puts `initial_event` at the top level | FATAL | Switch to the nested `retention` object and add `stat_type` / `unit_num` / `rtn_rate_or_num` |
| Compiler `meta.resolved` or normalized `definition` disagrees with the mapping | FATAL | Stop and go back to Step 0b to fix the fields; never execute a query with unaligned fields |
| Empty result | EMPTY | Check the time range and the event names first; if there really is no data, stop and tell the user |
| Exposure-cohort sample < 100 per group | ERROR | Stop. Suggest extending the experiment or widening traffic; do not draw a conclusion |
| Numerator > denominator | ERROR | Caliber error (success is not a subset of exposure). Go back to gate 1 and fix the query |
| One arm has a zero numerator | WARN | Flag a degenerate arm and continue, but it must be disclosed in the report |
| `ae-cli` HTTP or sign-in error | FATAL | Stop and go back to Step 0 to fix the environment |

## Flow

1. Pick the template by metric kind: `proportion|guardrail -> funnel`; `continuous -> external user_level distribution`;
   `retention -> nested object`.
2. `groups[].field` must copy the field name and type from `field_mapping.json` **verbatim**.
3. Run gate 1 with the same `--model-type` that will be passed to ae-cli: `IF exit 0 -> continue; ELSE -> fix the definition and re-run`.
4. `IF compilation needs clarification -> dry-run the corrected definition once and inspect meta; ELSE -> execute directly`.
5. Run the query and redirect stdout to `{ws}/tmp/query_output.json`.
6. Run gate 2: `IF exit 0 -> continue; IF EMPTY -> fix the time range and re-query; IF ERROR/FATAL -> stop and report`.
7. Use the `detected_groups` echoed by the gate to re-confirm the group labels, then carry
   `cohort_basis: exposed_users_after_exposure` into Step 2a's input.
8. Parse: read `data.rows` (not `data.data`) and take column names from `data.title`; `row[0]` is the
   time string and is skipped, `row[1]` is the group value, and `row[2+]` are **string** metric values
   that must be converted before any arithmetic.

## Error Handling Summary

| Gate | Status | Exit code | Action |
|------|--------|-----------|--------|
| `check_query_definition.py` | SUCCESS | `0` | Execute directly unless a concrete compiler issue requires one dry run |
| `check_query_definition.py` | WARN | `0` | Relay the warning; dry-run only when it identifies a concrete compiler/input uncertainty |
| `check_query_definition.py` | ERROR / FATAL | `1` | Fix the query and re-run; never skip this gate |
| `validate_query_output.py` | SUCCESS | `0` | Proceed to Step 2 |
| `validate_query_output.py` | WARN | `0` | Proceed to Step 2, but the degenerate arm must be disclosed |
| `validate_query_output.py` | EMPTY | `1` | Fix the time range / event names and re-query |
| `validate_query_output.py` | ERROR / FATAL | `1` | Stop and report to the user |

## Notes

- The sample floor applies only to the **exposure-cohort denominator** column, identified either by an
  explicit `cohort.denominator_column` or as the single count-like column. Success numerators are
  **deliberately not floored** - a 50/55 conversion count is a small numerator, not a small sample.
- When several denominator candidates exist and none is declared, the gate reports ERROR rather than
  guessing: guessing the wrong denominator invalidates the entire conclusion.
- Row order is not guaranteed. Always use `row[1]` to decide which arm is the control.
