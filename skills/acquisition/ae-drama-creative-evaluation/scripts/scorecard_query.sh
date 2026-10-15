#!/usr/bin/env bash
# Short-drama Creative Evaluation Skill - Step 7: scorecard SQL template rendering and execution
# Usage: ./scorecard_query.sh <PROJECT_ID> <INSTALL_START> <template name> <EVENT_TABLE_REF>
#   INSTALL_START  attribution/activation data start point (yyyy-MM-dd), must not be earlier than the real data start point
#   template name  scorecard | ad_channel | lifecycle_week | paystruct | content_pref
#   EVENT_TABLE_REF exact authorized table_ref returned by analysis sql-table list
# Rules:
#   - MATURE_END auto = today-7 (D7 maturity line); OBS_END = today
#   - event/field names in templates are DEMO default values; must test and adjust per references/metrics-caliber.md before formal use
#   - complete results exported to <OUT_DIR>/<template name>_<cohort>_<timestamp>.jsonl.gz
set -euo pipefail

PID="${1:?Usage: scorecard_query.sh <PROJECT_ID> <INSTALL_START> <template name> <EVENT_TABLE_REF>}"
INSTALL_START="${2:?missing INSTALL_START (yyyy-MM-dd)}"
TPL="${3:?missing template name: scorecard | ad_channel | lifecycle_week | paystruct | content_pref}"
EVENT_TABLE="${4:?missing EVENT_TABLE_REF from: ae-cli analysis sql-table list --project-id <PROJECT_ID> --usage analysis}"

case "$TPL" in
  scorecard|ad_channel|lifecycle_week|paystruct|content_pref) ;;
  *) echo "!! unsupported template: $TPL"; exit 1 ;;
esac

if [[ ! "$INSTALL_START" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "!! INSTALL_START must use yyyy-MM-dd"
  exit 1
fi

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TPL_FILE="$SKILL_DIR/assets/sql/${TPL}.sql.tmpl"
[ -f "$TPL_FILE" ] || { echo "!! template not found: $TPL_FILE"; ls "$SKILL_DIR/assets/sql/"; exit 1; }

TODAY=$(date +%F)
# GNU date supports "-d"; macOS BSD date needs "-v-7d". Detect and fall back.
if date -d "$TODAY -7 days" +%F >/dev/null 2>&1; then
  MATURE_END=$(date -d "$TODAY -7 days" +%F)
else
  MATURE_END=$(date -v-7d +%F)
fi
OBS_END="$TODAY"

echo "cohort: $INSTALL_START ~ $MATURE_END (D7 mature) | behavior observed through $OBS_END | table $EVENT_TABLE"

SQL=$(sed -e "s|{{EVENT_TABLE}}|${EVENT_TABLE}|g" \
          -e "s|{{INSTALL_START}}|${INSTALL_START}|g" \
          -e "s|{{MATURE_END}}|${MATURE_END}|g" \
          -e "s|{{OBS_END}}|${OBS_END}|g" "$TPL_FILE")

# use python to safely construct the definition JSON, avoid shell-escaping breaking the query
DEF_FILE=$(mktemp "${TMPDIR:-/tmp}/ae-creative-definition.XXXXXX")
trap 'rm -f "$DEF_FILE"' EXIT
SQL="$SQL" DEF_FILE="$DEF_FILE" python3 - <<'PY'
import json, os
with open(os.environ["DEF_FILE"], "w") as f:
    json.dump({"sql": os.environ["SQL"]}, f, ensure_ascii=False)
PY

OUT_DIR="${OUT_DIR:-${TMPDIR:-/tmp}/material_eval_${PID}}"
mkdir -p "$OUT_DIR"
RUN_STAMP=$(date +%Y%m%dT%H%M%S)
OUT_FILE="$OUT_DIR/${TPL}_${INSTALL_START}_${MATURE_END}_${RUN_STAMP}.jsonl.gz"

ae-cli analysis adhoc export --project-id "$PID" --model-type sql \
  --definition "$(cat "$DEF_FILE")" --artifact-format jsonl --output "$OUT_FILE"

echo ""
echo "complete result saved to: $OUT_FILE"
echo "reminder: this result uses the $(date +%F) caliber; verify the success-status filters for payment/registration/ad revenue against references/metrics-caliber.md."
