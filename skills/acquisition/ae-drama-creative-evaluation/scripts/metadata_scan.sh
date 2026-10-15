#!/usr/bin/env bash
# Short-drama Creative Evaluation Skill - Step 3/4: complete metadata export + SQL-tested event cross-validation
# Background (rules verified in practice):
#   1. use analysis-meta event/property export for complete metadata; do not rebuild exports with list pagination
#   2. preset events (ta_app_install, etc.) and some custom events may not appear in the metadata list -> cross-validate with SQL tested queries
#   3. metadata last_day_count may lag and cannot be used as the data freshness basis
# Usage: ./metadata_scan.sh <PROJECT_ID> <EVENT_TABLE_REF> [OUT_DIR]
# Outputs: events.tsv / properties.tsv / events_actual.tsv (event counts tested over the last 7 days) + attribution field probe summary
set -euo pipefail

PID="${1:?Usage: metadata_scan.sh <PROJECT_ID> <EVENT_TABLE_REF> [OUT_DIR]}"
EVENT_TABLE="${2:?missing EVENT_TABLE_REF from: ae-cli analysis sql-table list --project-id <PROJECT_ID> --usage analysis}"
OUT="${3:-${TMPDIR:-/tmp}/metadata_scan_${PID}}"
mkdir -p "$OUT"

PID="$PID" EVENT_TABLE="$EVENT_TABLE" OUT="$OUT" python3 - <<'PY'
import datetime
import gzip
import json
import os
import pathlib
import subprocess
import sys
import tempfile

pid = int(os.environ["PID"])
event_table = os.environ["EVENT_TABLE"]
out = pathlib.Path(os.environ["OUT"])

def cli(*args):
    r = subprocess.run(["ae-cli", *args], capture_output=True, text=True)
    try:
        payload = json.loads(r.stdout)
    except Exception:
        print("!! ae-cli output is not JSON:", r.stdout[:500], r.stderr[:300])
        sys.exit(1)
    if r.returncode != 0 or not payload.get("ok"):
        print(f"!! ae-cli command failed: {' '.join(args)}")
        print(payload.get("error") or r.stderr[:500])
        sys.exit(1)
    return payload

def export_metadata(resource, destination):
    cli(
        "analysis-meta", resource, "export",
        "--project-id", str(pid),
        "--output", str(destination),
    )
    try:
        rows = json.loads(destination.read_text())
    except Exception as exc:
        print(f"!! invalid {resource} export: {exc}")
        sys.exit(1)
    if not isinstance(rows, list):
        print(f"!! invalid {resource} export: expected a JSON array")
        sys.exit(1)
    return rows

with tempfile.TemporaryDirectory(prefix="ae-creative-metadata-") as tmp:
    tmpdir = pathlib.Path(tmp)
    events = export_metadata("event", tmpdir / "events.json")
    props = export_metadata("property", tmpdir / "properties.json")

# ---- 1. complete event metadata ----
with open(out / "events.tsv", "w") as f:
    f.write("event_name\tevent_desc\n")
    for e in events: f.write(f"{e.get('event_name','')}\t{e.get('event_desc','')}\n")
print(f"[1/4] event metadata: {len(events)} items -> {out/'events.tsv'}")

# ---- 2. complete property metadata ----
with open(out / "properties.tsv", "w") as f:
    f.write("prop_name\tprop_desc\ttable_type\tselect_type\n")
    for p in props:
        f.write(f"{p.get('prop_name','')}\t{p.get('prop_desc','')}\t{p.get('table_type','')}\t{p.get('select_type','')}\n")
print(f"[2/4] property metadata: {len(props)} items -> {out/'properties.tsv'}")

# ---- 3. SQL-tested event list (cross-validate metadata omissions) ----
since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
sql = (f'select "#event_name" ev, count(*) cnt from {event_table} '
       f'where "$part_date" >= \'{since}\' group by 1 order by cnt desc')
with tempfile.TemporaryDirectory(prefix="ae-creative-events-") as tmp:
    export_path = pathlib.Path(tmp) / "events_actual.jsonl.gz"
    cli(
        "analysis", "adhoc", "export",
        "--project-id", str(pid),
        "--model-type", "sql",
        "--definition", json.dumps({"sql": sql}),
        "--artifact-format", "jsonl",
        "--output", str(export_path),
    )
    rows = []
    with gzip.open(export_path, "rt") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append([item.get("ev"), item.get("cnt")])
            elif isinstance(item, list) and len(item) >= 2:
                rows.append(item[:2])
            else:
                print(f"!! unexpected SQL export row: {item}")
                sys.exit(1)
if any(r[0] is None or r[1] is None for r in rows):
    print("!! SQL export is missing the ev/cnt columns")
    sys.exit(1)
with open(out / "events_actual.tsv", "w") as f:
    f.write(f"event_name\tcnt_since_{since}\n")
    for r in rows: f.write(f"{r[0]}\t{r[1]}\n")
meta_names = {e.get("event_name") for e in events}
missing = [r[0] for r in rows if r[0] not in meta_names]
print(f"[3/4] tested events: {len(rows)} kinds -> {out/'events_actual.tsv'}")
if missing:
    print(f"      !! metadata export omitted {len(missing)} tested events (tested results prevail): {', '.join(missing[:20])}")

# ---- 4. attribution/revenue key field probe summary ----
keys = ["media_source", "campaign", "ad_id", "creative", "material",
        "pay_amount", "ad_income", "cost", "spend", "is_register", "is_success",
        "channel", "is_from_channel", "video_id", "first_category"]
hits = [p for p in props if any(k in (p.get("prop_name") or "") or k in (p.get("prop_desc") or "") for k in keys)]
vps  = [p for p in props if (p.get("prop_name") or "").startswith("#vp@")]
print(f"[4/4] key fields hit {len(hits)} (see properties.tsv for details); virtual properties {len(vps)}:")
for p in vps:
    print(
        f"      - {p['prop_name']} ({p.get('prop_desc','')})"
        " <- inspect with: ae-cli analysis-meta property get"
        f" --project-id {pid} --table-type {p.get('table_type','event')}"
        f" --prop-name {p['prop_name']};"
        " if vir_prop_column_rule contains random(), it is forbidden for conclusions"
    )
print("")
print("Scan complete. Please fill assets/confirm-card-template.md accordingly and confirm with the user before data retrieval.")
PY
