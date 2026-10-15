#!/usr/bin/env bash
# ae_query.sh (universal edition) — ae-cli adhoc query + persisted-file validation in one step
#
# Difference from the LesPark-specific edition: project-id is read from a
# product-config environment variable, not hardcoded.
#
# Usage:
#   export AE_PROJECT_ID=<project_id>   # read from product config, MUST export first
#   ./ae_query.sh sql  <output.json> <<'SQL'
#   SELECT "$part_date" AS d, COUNT(DISTINCT "#user_id") AS uv
#   FROM {event_table}
#   WHERE "$part_event" = '{enter_event}'
#     AND "$part_date" BETWEEN '2026-09-04' AND '2026-09-06'
#   GROUP BY 1 ORDER BY 1
#   SQL
#   (SQL is fed via stdin; single/double quotes need no escaping; or read from file:
#    ./ae_query.sh sql <output.json> < query.sql)
#
# evt (event model): definition passed as a JSON object file path (validated before run):
#   ./ae_query.sh evt /tmp/spm.json /tmp/definition.json
#   (the definition file MUST contain a single JSON object, e.g. {"time_range":{...},"metrics":[...]})
#
# Features:
#   1. SQL built into definition via Python json.dumps, not shell concatenation
#   2. Results stdout persisted; stderr written to a per-output log (never mixed into JSON, never shared across concurrent runs)
#   3. Immediately validates the persisted file (file exists + data.rows non-empty); warns on has_more=true
#   4. Auto-retries up to 3 times on concurrency limit (CONCURRENCY_LIMIT_EXCEEDED)
#
# Deps: ae-cli logged in; python3; AE_PROJECT_ID env var exported

# Precondition assertions (MUST): fail fast on missing deps to avoid silent
# failure surfacing only at the parse stage
command -v ae-cli >/dev/null 2>&1 || { echo "FATAL: ae-cli not found; install it and confirm login (ae-cli config current)" >&2; exit 127; }
command -v python3 >/dev/null 2>&1 || { echo "FATAL: python3 not found; install it first" >&2; exit 127; }

# project_id MUST be read from env var (product config); error out if unset; do NOT default/hardcode
if [ -z "${AE_PROJECT_ID:-}" ]; then
  echo "FATAL: AE_PROJECT_ID env var unset. Read project_id from product config and export it:" >&2
  echo "  export AE_PROJECT_ID=<project_id>" >&2
  exit 127
fi

set -uo pipefail

PROJECT_ID="${AE_PROJECT_ID}"
TYPE="${1:-}"
OUT="${2:-}"
INPUT="${3:-}"   # sql mode: unused (SQL read from stdin); evt mode: path to a JSON-object definition file

# Per-output stderr log — one log per query, so parallel sub-agent queries cannot overwrite each other.
STDERR_LOG="${OUT}.stderr.log"

if [ "$TYPE" = "sql" ]; then
  # SQL is always read from stdin (heredoc / file redirect); no legacy direct-argument path
  SQL_INPUT="$(cat)"
elif [ "$TYPE" = "evt" ]; then
  # Validate the definition file is a single JSON object before invoking ae-cli
  if [ -z "$INPUT" ]; then
    echo "error: evt mode requires a definition JSON-object file path (arg 3)" >&2
    exit 2
  fi
  if [ ! -f "$INPUT" ]; then
    echo "error: evt definition file not found: $INPUT" >&2
    exit 2
  fi
  DEFINITION="$(python3 -c '
import json, sys
try:
    value = json.load(open(sys.argv[1]))
except Exception as e:
    print(f"error: evt definition is not valid JSON: {e}", file=sys.stderr)
    sys.exit(2)
if not isinstance(value, dict):
    print("error: evt definition must be a JSON object", file=sys.stderr)
    sys.exit(2)
print(json.dumps(value))
' "$INPUT")" || exit 2
else
  echo "error: type must be sql or evt, got '$TYPE'" >&2
  exit 2
fi

# Concurrency-limit retry: ae-cli's per-host concurrency cap throws
# CONCURRENCY_LIMIT_EXCEEDED and persists an empty file. Retry up to 3 times,
# each with a 3-second sleep to let concurrent queries pass.
MAX_ATTEMPTS="${AE_MAX_ATTEMPTS:-3}"
attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  if [ "$TYPE" = "sql" ]; then
    # build definition with Python, correctly escaping SQL quotes
    DEFINITION="$(python3 -c 'import json,sys; print(json.dumps({"sql": sys.stdin.read().strip()}))' <<<"$SQL_INPUT")"
    ae-cli analysis adhoc run --project-id "$PROJECT_ID" --model-type sql \
      --definition "$DEFINITION" \
      >"$OUT" 2>"$STDERR_LOG"
  else
    ae-cli analysis adhoc run --project-id "$PROJECT_ID" --model-type event \
      --definition "$DEFINITION" \
      >"$OUT" 2>"$STDERR_LOG"
  fi

  # judge whether concurrency-limit error (persisted empty AND stderr contains CONCURRENCY_LIMIT_EXCEEDED)
  if [ -s "$OUT" ]; then
    break
  fi
  if grep -q "CONCURRENCY_LIMIT_EXCEEDED" "$STDERR_LOG" 2>/dev/null; then
    echo "[retry] hit concurrency limit, attempt $attempt/$MAX_ATTEMPTS, retrying in 3s..." >&2
    sleep 3
    attempt=$((attempt + 1))
    continue
  fi
  break   # empty file but not a concurrency error; let the validation below report it
done

# validate the persisted file
if [ ! -s "$OUT" ]; then
  echo "[fail] $OUT is empty or not generated. stderr log:" >&2
  cat "$STDERR_LOG" >&2
  exit 1
fi

# parse & validate (skip log lines before JSON)
python3 - "$OUT" <<'PYEOF'
import json, sys
path = sys.argv[1]
raw = open(path).read()
i = raw.find('{')
if i < 0:
    print(f"[fail] {sys.argv[1]} has no valid JSON. first 200 raw chars:", file=sys.stderr)
    print(raw[:200], file=sys.stderr)
    sys.exit(1)
try:
    d = json.loads(raw[i:])
except Exception as e:
    print(f"[fail] {sys.argv[1]} JSON parse error {e}", file=sys.stderr)
    sys.exit(1)
if d.get('ok') is False:
    print(f"[fail] ae-cli returned ok=false: {d.get('error')}", file=sys.stderr)
    sys.exit(1)
rows = d.get('data', {}).get('rows', [])
has_more = d.get('data', {}).get('has_more', False)
print(f"[ok] {sys.argv[1]} rows={len(rows)} has_more={has_more}")
if has_more:
    print("  warning: result truncated (has_more=true). Judge per query-templates.md trap #7 first: check whether dates cover the full window and whether main entries' daily series are complete; only re-query when main-entry data is also missing")
PYEOF
