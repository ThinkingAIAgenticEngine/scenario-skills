#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 2a - fetch native Engage reports (mode A).

Wraps the ae-cli engage commands and writes raw payloads into --out-dir using
the same file names the shared analysis stage expects. Partial failures are
non-fatal: each missing block becomes a recorded degradation rather than an
aborted run, because a campaign with no experiment report is still worth
analysing.

Objects supported:
    --task-id    Engage operation task   (task_data_overview / detail / experiment)
    --flow-id    journey canvas          (flow_detail / node reports)
    --config-id  configuration item      (config_item_list / trigger report)

Usage:
    python3 fetch_engage_reports.py --project-id 61 --task-id 0822 \\
        --start-time 2024-02-01 --end-time 2024-12-31 --out-dir tmp

Exit codes:
  0  SUCCESS or EMPTY (payload written, possibly with degradations)
  1  FATAL (ae-cli unusable, or no block could be retrieved at all)
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402
import _cmdtree  # noqa: E402


def write(out_dir, name, obj):
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return path


def note_missing_task_fields(tasklist_block, degradations):
    """Record task-row fields the installed ae-cli generation failed to return.

    6.x trims the paged list endpoint hard (72 fields to 34), while the per-task
    lookup this skill relies on stays nearly complete. Which of the fields listed
    in _cmdtree.V6_TASK_ROW_FIELDS_AT_RISK are actually absent is therefore
    measured from the payload, not assumed from the version.

    Absent and null read identically at the call site, so a conclusion that used
    to rest on `planNum` would quietly thin out instead of announcing itself.
    Declaring the gap here, while the payload is still in hand, keeps it visible
    in both the report and the workbook.
    """
    rows = _ae.as_list(tasklist_block)
    if not rows:
        return
    row = rows[0]
    for field in sorted(_cmdtree.V6_TASK_ROW_FIELDS_AT_RISK):
        if field in row:
            continue
        degradations.append({
            "block": "field_%s" % field,
            "reason": "the installed ae-cli did not return `%s` - %s"
                      % (field, _cmdtree.V6_TASK_ROW_FIELDS_AT_RISK[field]),
            "impact": "conclusions resting on `%s` are unavailable on this "
                      "ae-cli generation" % field})


def try_call(ae, args, label, degradations, required=False):
    """Run an engage command. Returns parsed JSON or None.

    Failures are recorded as degradations unless `required` is set, in which
    case they raise so the caller can decide the run is impossible.
    """
    try:
        resp = _ae.run_ae(args, ae=ae)
    except Exception as e:
        msg = str(e)[:220]
        degradations.append({"block": label, "reason": msg,
                             "impact": "corresponding analysis block is skipped"})
        _ae.log("failed: %s - %s" % (label, msg), prefix="fetch-a")
        if required:
            raise
        return None
    if isinstance(resp, dict) and resp.get("ok") is False:
        msg = _ae.unwrap_error(resp) or "ok=false"
        degradations.append({"block": label, "reason": msg,
                             "impact": "corresponding analysis block is skipped"})
        _ae.log("not-ok: %s - %s" % (label, msg), prefix="fetch-a")
        if required:
            raise RuntimeError("%s: %s" % (label, msg))
        return None
    return resp


def has_payload(resp):
    if not resp:
        return False
    data = resp.get("data")
    return bool(data)


def main():
    ap = argparse.ArgumentParser(description="Step 2a fetch Engage reports")
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--task-id", default=None)
    ap.add_argument("--flow-id", default=None)
    ap.add_argument("--config-id", default=None)
    ap.add_argument("--start-time", default=None)
    ap.add_argument("--end-time", default=None)
    ap.add_argument("--out-dir", default="tmp")
    ap.add_argument("--ae-cli", default=None)
    args = ap.parse_args()

    if not any([args.task_id, args.flow_id, args.config_id]):
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "native_object", "status": "FATAL",
                             "message": "one of --task-id / --flow-id / --config-id is required "
                                        "for mode A"}]})

    ae = args.ae_cli or _ae.find_ae_cli()
    os.makedirs(args.out_dir, exist_ok=True)
    pid = str(args.project_id)
    degradations, written = [], []

    start = _ae.norm_date(args.start_time) or (date.today().replace(day=1).isoformat())
    end = _ae.norm_date(args.end_time) or date.today().isoformat()

    # --no-update-check is appended by _ae.run_ae, so it is omitted here.
    window = ["--start_time", start, "--end_time", end]

    if args.task_id:
        tid = str(args.task_id)
        base = ["engage", "+task_data_overview", "--project_id", pid, "--task_id", tid]
        ov = try_call(ae, base, "task_data_overview", degradations, required=True)
        if ov:
            written.append(write(args.out_dir, "raw_overview.json", ov))

        detail_args = {
            "time": ["engage", "+task_data_detail", "--project_id", pid, "--task_id", tid,
                     "--detail_type", "time"] + window,
            "instance": ["engage", "+task_data_detail", "--project_id", pid, "--task_id", tid,
                         "--detail_type", "instance"] + window,
        }
        for label, cmdline in detail_args.items():
            r = try_call(ae, cmdline, "task_data_detail:%s" % label, degradations)
            if r:
                written.append(write(args.out_dir, "raw_detail_%s.json" % label, r))

        for rt in ("overview", "detail"):
            r = try_call(ae,
                         ["engage", "+task_experiment_report", "--project_id", pid,
                          "--task_id", tid, "--report_type", rt] + window,
                         "task_experiment_report:%s" % rt, degradations)
            if r:
                written.append(write(args.out_dir, "raw_exp_%s.json" % rt, r))

        # Only this one task's metadata is needed, and +task_list is paged (real
        # projects hold 500+ rows), so resolve the task directly rather than
        # requesting a fixed first page - a valid low id silently falls outside
        # it, and every header field in the report then comes out blank.
        try:
            tl = _ae.task_meta_block(ae, pid, tid)
            err = None
        except Exception as e:
            tl, err = None, str(e)[:220]
        if tl:
            written.append(write(args.out_dir, "raw_tasklist.json", tl))
            note_missing_task_fields(tl, degradations)
        else:
            degradations.append({"block": "task_list",
                                 "reason": err or ("task %s metadata not found" % tid),
                                 "impact": "channel / trigger time / conversion "
                                           "indicator metadata is missing"})
            _ae.log("task %s metadata not found - header fields will be blank" % tid,
                    prefix="fetch-a")

        # instance_daily needs a concrete task_instance_id, which only exists
        # once the instance detail has been fetched; it is therefore skipped
        # here and produced on demand by a follow-up call.
        _ae.log("note: instance_daily detail requires --task_instance_id and is "
                "fetched separately when hourly granularity is requested", prefix="fetch-a")

    elif args.flow_id:
        fid = str(args.flow_id)
        flows = try_call(ae, ["engage", "+flow_list", "--project_id", pid],
                         "flow_list", degradations, required=True)
        if flows:
            written.append(write(args.out_dir, "raw_flowlist.json", flows))
        items = _ae.as_list(flows)
        match = None
        for f in items:
            if str(f.get("flowId")) == fid:
                match = f
                break
        if not match:
            _ae.log("flow %s not found in flow_list; reports will likely be empty" % fid,
                    prefix="fetch-a")
            degradations.append({"block": "flow_lookup", "reason": "flow %s not found" % fid,
                                 "impact": "canvas metrics unavailable"})
            uuid_val = None
        else:
            uuid_val = match.get("flowUuid")
            if not match.get("hasData"):
                degradations.append({
                    "block": "flow_data", "reason": "hasData=false for flow %s" % fid,
                    "impact": "canvas has no execution records; node reports will be empty"})

        if uuid_val:
            r = try_call(ae, ["engage", "+flow_detail", "--project_id", pid,
                              "--flow_uuid", uuid_val], "flow_detail", degradations)
            if r:
                written.append(write(args.out_dir, "raw_flow_detail.json", r))
            r = try_call(ae, ["engage", "+flow_node_overview_report", "--project_id", pid,
                              "--flow_uuid", uuid_val] + window,
                         "flow_node_overview_report", degradations)
            if r:
                written.append(write(args.out_dir, "raw_flow_nodes.json", r))
                dl = ((r.get("data") or {}).get("dataList"))
                if not dl:
                    degradations.append({
                        "block": "flow_node_overview",
                        "reason": "dataList is null for flow %s" % fid,
                        "impact": "canvas has no metric records in this window "
                                  "(common in sandbox environments, not a call error)"})

    else:
        cid = str(args.config_id)
        items_resp = try_call(ae, ["engage", "+config_item_list", "--project_id", pid],
                              "config_item_list", degradations, required=True)
        if items_resp:
            written.append(write(args.out_dir, "raw_config_list.json", items_resp))
        trig = try_call(ae, ["engage", "+config_item_trigger_report", "--project_id", pid,
                             "--config_id", cid] + window,
                        "config_item_trigger_report", degradations, required=True)
        if trig:
            written.append(write(args.out_dir, "raw_config_trigger.json", trig))

    meta = {
        "mode": "A",
        "project_id": pid,
        "object": {"task_id": args.task_id, "flow_id": args.flow_id,
                   "config_id": args.config_id},
        "window": {"start": start, "end": end},
        "source": "ae-cli engage",
        "written": [os.path.basename(p) for p in written],
        "degradations": degradations,
    }
    written.append(write(args.out_dir, "raw_meta.json", meta))

    status = "SUCCESS" if any(os.path.basename(p).startswith("raw_overview") for p in written) \
        else ("EMPTY" if written else "FATAL")
    payload = {"status": status, "out_dir": os.path.abspath(args.out_dir),
               "written": meta["written"], "degradations": degradations,
               "attribution_note": "window used for every report call: %s .. %s" % (start, end)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(1 if status == "FATAL" else 0)


if __name__ == "__main__":
    main()
