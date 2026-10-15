#!/usr/bin/env bash
#
# scaffold.sh — new project KB initialization: deterministic part (append mode)
#
# Append a project instance layer to an existing company KB directory,
# without copying company-level files and without creating a separate directory:
#   1. validate that the company KB directory (--company-layer) exists and has the 4 company-level files
#   2. generate projects/project-<N>/registry.md as an empty template (placeholders, family-agnostic)
#   3. generate projects/project-<N>/context.md as an empty template (business background)
#   4. print the follow-up ae-cli kb compile commands
#
# Agent's part: probe caliber (report get) → fill registry, context → run the printed commands.
#
# Prerequisite: this customer's company KB has been initialized by company-scaffold.sh
#   and passed "company onboarding". This script points at that company KB via --company-layer
#   and does not hardcode any company path.
#
# Usage:
#   bash scaffold.sh --project-id 5 --project-name "Acme-ProductA" --company-layer ./kb-acme
#   bash scaffold.sh --project-id 5 --project-name "Acme-ProductA" --company acme
#
set -euo pipefail

# ---- argument parsing ----
PROJECT_ID=""
PROJECT_NAME=""
COMPANY_LAYER=""
KB_NAME=""
COMPANY_SLUG=""

usage() {
  cat <<'USAGE'
Usage: scaffold.sh --project-id <N> --project-name "<name>" --company-layer <dir> [options]

  --project-id N         required, project ID
  --project-name name    required, project display name (used in registry/context titles)
  --company-layer dir    required, company KB directory (produced by company-scaffold.sh)
  --company slug         equivalent to --company-layer ./kb-<slug>
  --kb-name name         KB name, defaults to the company-layer index.md title (<CompanyName> Business Metrics Definition Library)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)    [[ $# -ge 2 ]] || { echo "error: --project-id requires a value" >&2; exit 1; }; PROJECT_ID="$2"; shift 2 ;;
    --project-name)  [[ $# -ge 2 ]] || { echo "error: --project-name requires a value" >&2; exit 1; }; PROJECT_NAME="$2"; shift 2 ;;
    --company-layer) [[ $# -ge 2 ]] || { echo "error: --company-layer requires a value" >&2; exit 1; }; COMPANY_LAYER="$2"; COMPANY_SLUG=""; shift 2 ;;
    --company)       [[ $# -ge 2 ]] || { echo "error: --company requires a value" >&2; exit 1; }; COMPANY_SLUG="$2"; shift 2 ;;
    --kb-name)       [[ $# -ge 2 ]] || { echo "error: --kb-name requires a value" >&2; exit 1; }; KB_NAME="$2"; shift 2 ;;
    -h|--help)       usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$PROJECT_ID" || -z "$PROJECT_NAME" ]]; then
  echo "error: --project-id and --project-name are required" >&2
  usage
  exit 1
fi
if [[ ! "$PROJECT_ID" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: --project-id must be a positive integer" >&2
  exit 1
fi
if [[ -n "$COMPANY_SLUG" ]]; then
  if [[ ! "$COMPANY_SLUG" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
    echo "error: --company must be a lowercase slug containing only letters, digits, and hyphens" >&2
    exit 1
  fi
  COMPANY_LAYER="./kb-$COMPANY_SLUG"
fi
if [[ -z "$COMPANY_LAYER" ]]; then
  echo "error: --company-layer is required (run company-scaffold.sh first to initialize this company's KB)" >&2
  usage
  exit 1
fi

# ---- validate the company KB directory ----
for f in index.md reference/metric-registry.md rules/caveats-checklist.md; do
  if [[ ! -f "$COMPANY_LAYER/$f" ]]; then
    echo "error: company KB missing $COMPANY_LAYER/$f" >&2
    exit 1
  fi
done
if ! ls "$COMPANY_LAYER/metrics/"*.md >/dev/null 2>&1; then
  echo "error: company KB missing $COMPANY_LAYER/metrics/*.md" >&2
  exit 1
fi

# ---- KB name default: take the company-layer index.md title; derive company name by stripping the suffix ----
if [[ -z "$KB_NAME" ]]; then
  KB_NAME="$(sed -n '1s/^# //p' "$COMPANY_LAYER/index.md" 2>/dev/null | head -n1)"
  [[ -z "$KB_NAME" ]] && KB_NAME="${PROJECT_NAME} Business Metrics Definition Library"
fi
COMPANY_NAME="${KB_NAME% Business Metrics Definition Library}"
[[ "$COMPANY_NAME" == "$KB_NAME" ]] && COMPANY_NAME="$PROJECT_NAME"

# ---- project instance layer directory + safety check ----
PROJECT_DIR="$COMPANY_LAYER/projects/project-${PROJECT_ID}"
if [[ -d "$PROJECT_DIR" ]] && [[ -n "$(ls -A "$PROJECT_DIR" 2>/dev/null)" ]]; then
  echo "error: project instance layer already exists and is non-empty: $PROJECT_DIR (this project may already be onboarded; existing files will not be overwritten)" >&2
  exit 1
fi
mkdir -p "$PROJECT_DIR"

# ---- 1. generate the project instance layer empty template ----
REGISTRY_FILE="$PROJECT_DIR/registry.md"
# Quoted heredoc keeps <...> placeholders verbatim; awk then injects the project variables.
cat > "$REGISTRY_FILE" <<'REGISTRY_EOF'
# __PROJECT_NAME__ (project_id=__PROJECT_ID__) project instance caliber

## File path

```text
projects/project-__PROJECT_ID__/registry.md
```

## Goal

This page is the **concrete instance layer** for project_id=__PROJECT_ID__: it replaces the placeholders in the company-layer [metrics/](../../metrics/) metric-family generic calibers with real event names, field names, and aggregations. Data queries go by this page — no more ad-hoc guessing of events / fields.

## Project identity

- `project_id: __PROJECT_ID__`, project name "__PROJECT_NAME__"
- value field: <value field, e.g. #vp@pay_price / pay_amount> (number), aggregation is always `sum`
- analysis subject: <account/device/role/user, default to the company-layer metric default subject>

## Key instantiation conventions

<this project's model→metric-family instantiation; ratio metrics (pay rate / ARPU / ARPPU) with no standalone model use the event model + denominator to carry numerator/denominator, see the company-layer metrics/event.md instantiation notes>

## Linked reports

> Fill from actual `ae-cli analysis report get` readings; never reuse another project's report IDs.

| report_id | report name | metric family | metric | caliber summary |
| --- | --- | --- | --- | --- |
| <id> | <name> | <family> | <metric_id> | <event/field/aggregation/grouping summary> |

## Core events

- <register/login event>
- <payment event>
- <other core behavior events>

## Core fields

- amount: <field>(number)
- lifecycle / paid flag: <field>(number/bool)
- user identity: <#account_id / #user_id / #distinct_id>

## Metric instances (fill per the company-layer metrics/*.md family skeletons)

Each metric_id's YAML skeleton follows the "recommended machine-readable definition" in the company-layer `metrics/<family>.md`; two generic examples are given below (event family + retention family); for the other families follow the company-layer skeleton.

### Event metric example (event family)

```yaml
schema_version: "1.0"
scope: project_instance
metric_registry_type: analysis_metric_registry
owner_team: <team>
updated_at: "<YYYY-MM-DD>"
metrics:
  - metric_id: <stable_metric_id>
    metric_name: <display_name>
    metric_family: event
    model: event
    analysis_subject: <account/device/role/user>
    event: <stat_event_name>
    value_field: <numeric_field_name>      # required for sum/avg, leave empty for count
    value_aggregation: user_count          # total_count|user_count|per_user_count|sum|avg|max|min|distinct_count
    value_formula: UNIQUE(users)           # or SUM(<field>), SUM(<field>)/UNIQUE(users)
    filters: []
    group_by: []
    source_report_id: <id>
    caveats: []
```

### Retention metric example (retention family)

```yaml
schema_version: "1.0"
scope: project_instance
metric_registry_type: analysis_metric_registry
owner_team: <team>
updated_at: "<YYYY-MM-DD>"
metrics:
  - metric_id: <stable_metric_id>
    metric_name: <display_name>
    metric_family: retention
    model: retention
    analysis_subject: <account/device/role/user>
    initial_event: <initial_event_name>
    return_event: <return_event_name>
    value_aggregation: ratio
    value_formula: UNIQUE(return_event_users) / UNIQUE(initial_event_users)
    denominator:
      metric: USER_COUNT
      mode: unique
    filters: []
    observation_window:
      unit: day
      length: <n>
      is_metric_definition: true
    default_query_date_range:
      type: runtime_parameter
      value: user_request
      is_metric_definition: false
    granularity: day
    group_by: []
    source_report_id: <id>
    caveats: []
```

## Call example (ae-cli adhoc)

```bash
ae-cli analysis adhoc run \
  --project-id __PROJECT_ID__ \
  --model-type <model> \
  --definition '<JSON>' \
  --preview-rows 200
```

## Maintenance requirements

- Field names must map to real events or properties in the data assets.
- The same `metric_id` must not be reused for different calculation formulas.
- Project-private report IDs, dashboard IDs, and tag IDs stay in this project-level registry, never in company-level files.
- Every time the calculation formula, analysis subject, core events, or filters change, update `updated_at` and record the reason.

## Changelog

- <YYYY-MM-DD>: filled initial event / return event / value field / aggregation / filters / grouping / report ID from actual `ae-cli analysis report get` readings.
REGISTRY_EOF
awk -v pid="$PROJECT_ID" -v pname="$PROJECT_NAME" '
  function replace_literal(text, needle, replacement, pos) {
    while ((pos = index(text, needle)) > 0) {
      text = substr(text, 1, pos - 1) replacement substr(text, pos + length(needle))
    }
    return text
  }
  { print replace_literal(replace_literal($0, "__PROJECT_ID__", pid), "__PROJECT_NAME__", pname) }
' \
  "$REGISTRY_FILE" > "$REGISTRY_FILE.tmp" && mv "$REGISTRY_FILE.tmp" "$REGISTRY_FILE"

# ---- 2. generate the project business background empty template ----
CONTEXT_FILE="$PROJECT_DIR/context.md"
cat > "$CONTEXT_FILE" <<'CONTEXT_EOF'
# __PROJECT_NAME__ (project_id=__PROJECT_ID__) business background and data availability boundaries

## File path

```text
projects/project-__PROJECT_ID__/context.md
```

## Goal

This page records project_id=__PROJECT_ID__'s business background, data availability boundaries, and out-of-scope notes. These do not change the metric calculation caliber (see the sibling registry.md), but they determine which date ranges of data are valid and comparable. Read this page before querying data.

## Business background timeline

| date | event | impact |
| --- | --- | --- |
| <YYYY-MM-DD> | <business event, e.g. ban/version launch/channel migration> | <impact on data> |

## Data availability boundaries

- <data is valid from a certain date, or a certain range is not comparable and why>

## Out-of-scope notes

- <conventions that are not part of the caliber but affect readings, e.g. analysis subject, value field semantics>
CONTEXT_EOF
awk -v pid="$PROJECT_ID" -v pname="$PROJECT_NAME" '
  function replace_literal(text, needle, replacement, pos) {
    while ((pos = index(text, needle)) > 0) {
      text = substr(text, 1, pos - 1) replacement substr(text, pos + length(needle))
    }
    return text
  }
  { print replace_literal(replace_literal($0, "__PROJECT_ID__", pid), "__PROJECT_NAME__", pname) }
' \
  "$CONTEXT_FILE" > "$CONTEXT_FILE.tmp" && mv "$CONTEXT_FILE.tmp" "$CONTEXT_FILE"

# ---- 3. print the compile commands ----
echo
echo "========== project instance layer appended to the company KB =========="
echo "company KB directory: $COMPANY_LAYER"
echo "project instance layer to fill: $REGISTRY_FILE"
echo "business background template to fill: $CONTEXT_FILE"
echo
echo "Next the agent probes the caliber, fills registry and context, then runs in order:"
echo
cat <<EOF
# +new runs only once, when onboarding the customer's FIRST project, to create the KB:
ae-cli kb +new --scope company --name "${KB_NAME}" --project-id ${PROJECT_ID} --project-name "${COMPANY_NAME:-${PROJECT_NAME}}"
# Run for every project (incremental append). projects/ is a directory containing only the
# project-<N>/ subdirectory, and --files uploads non-recursively, so it must point at
# projects/project-${PROJECT_ID} (which directly contains registry.md+context.md);
# do not pass projects/ itself (it would fail with "No supported files found").
ae-cli kb +add --scope company --name "${KB_NAME}" --files '["${COMPANY_LAYER}/index.md","${COMPANY_LAYER}/reference","${COMPANY_LAYER}/metrics","${COMPANY_LAYER}/rules","${COMPANY_LAYER}/projects/project-${PROJECT_ID}"]'
# +schema is async: it returns status=generating; poll kb +status until schemaStatus=generated
# before compiling, otherwise +compile fails immediately with "Schema has not been generated".
ae-cli kb +schema --scope company --name "${KB_NAME}"
ae-cli kb +status --scope company --name "${KB_NAME}"   # wait until schemaStatus: generated
# Compile is also async: it returns status=queued; poll until buildStatus=compiled to finish.
ae-cli kb +compile --scope company --name "${KB_NAME}" --mode incremental
ae-cli kb +status --scope company --name "${KB_NAME}"   # wait until buildStatus: compiled
EOF
