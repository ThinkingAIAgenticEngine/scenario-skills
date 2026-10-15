#!/usr/bin/env bash
# Short-drama Creative Evaluation Skill - Step 3: environment and project precheck
# Usage: ./precheck.sh <PROJECT_ID>
set -euo pipefail

PID="${1:?Usage: precheck.sh <PROJECT_ID>}"

echo "== 1/5 ae-cli version =="
ae-cli --version

echo ""
echo "== 2/5 auth status =="
if ! ae-cli auth status; then
  echo "!! auth invalid: run ae-cli auth login first"
  echo "!! when unauthorized, only analysis design can be output, not real data conclusions"
  exit 1
fi

echo ""
echo "== 3/5 existing dashboards (reuse first) =="
ae-cli analysis dashboard list --project-id "$PID" --limit 200 --jq '.items[] | "\(.dashboard_id)\t\(.dashboard_name)"' || echo "(dashboard API unavailable)"

echo ""
echo "== 4/5 existing reports (verify caliber with report get before reuse) =="
ae-cli analysis report list --project-id "$PID" --limit 200 --jq '.items[] | "\(.report_id)\t\(.report_name)\t\(.report_model)"' || echo "(report API unavailable)"

echo ""
echo "== 5/5 SQL usable tables (find eventView / userView table names) =="
ae-cli analysis sql-table list --project-id "$PID" --limit 200 --usage analysis --jq '.items[] | "\(.table_ref)\t\(.table_type)"' || echo "(SQL table API unavailable)"

echo ""
echo "Precheck complete. Copy the exact event table_ref above, then run: ./metadata_scan.sh $PID <EVENT_TABLE_REF>"
