#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 4 gate - validate the detail workbook.

A workbook is the deliverable most likely to be silently wrong: a missing
sheet, a sheet that exists but is blank, or columns that drifted out of order.
None of that raises an error downstream, so it is checked here.

Usage:
    python3 validate_excel.py output/"campaign"_detail_20260914.xlsx

Exit codes:
  0  SUCCESS / EMPTY (sheets present but some blank - run continues, flagged)
  1  FATAL (file missing/unreadable, or a required sheet is absent)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402
import _env  # noqa: E402

REQUIRED_SHEETS = [
    "1-策略概览", "2-链路漏斗", "3-维度明细", "4-时序趋势",
    "5-人群分层", "6-策略与分组对比", "7-原始数据",
]


def main():
    ap = argparse.ArgumentParser(description="Step 4 gate")
    ap.add_argument("excel")
    ap.add_argument("--min-rows", type=int, default=2,
                    help="minimum non-empty rows per sheet (default 2: header + data)")
    args = ap.parse_args()

    if not os.path.exists(args.excel):
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "excel_exists", "status": "FATAL",
                             "message": "workbook not found: %s" % args.excel}]})
    size = os.path.getsize(args.excel)
    if size == 0:
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "excel_non_empty", "status": "FATAL",
                             "message": "workbook is 0 bytes"}]})

    try:
        from openpyxl import load_workbook
    except ImportError:
        # Point at the interpreter Step 0 resolved rather than just reporting a
        # missing package: on a fresh machine openpyxl usually exists somewhere,
        # it is simply not the interpreter this script was started with.
        state, detail = _env.resolve_package("openpyxl", allow_install=False)
        if state in ("available_elsewhere", "bootstrapped"):
            hint = "rerun with PY=%s" % detail
        else:
            hint = "install it with: %s" % detail
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "openpyxl", "status": "FATAL",
                             "message": "openpyxl is not available to this interpreter "
                                        "(%s) - %s" % (sys.executable, hint)}]})

    try:
        wb = load_workbook(args.excel, read_only=True, data_only=True)
    except Exception as e:
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "excel_readable", "status": "FATAL",
                             "message": "cannot open workbook: %s" % e}]})

    checks = []
    names = wb.sheetnames
    missing = [s for s in REQUIRED_SHEETS if s not in names]
    checks.append({"check": "sheets_present", "status": "FATAL" if missing else "SUCCESS",
                   "message": "missing %s" % missing if missing else
                              "all %d sheets present" % len(REQUIRED_SHEETS)})

    sheet_stats, empty, thin = {}, [], []
    for name in REQUIRED_SHEETS:
        if name not in names:
            continue
        ws = wb[name]
        non_empty_rows = 0
        for row in ws.iter_rows(values_only=True):
            if any(c is not None and str(c).strip() != "" for c in row):
                non_empty_rows += 1
        sheet_stats[name] = non_empty_rows
        if non_empty_rows == 0:
            empty.append(name)
        elif non_empty_rows < args.min_rows:
            thin.append(name)
    wb.close()

    checks.append({"check": "sheets_non_empty", "status": "FATAL" if empty else "SUCCESS",
                   "message": "blank sheets: %s" % empty if empty else
                              "every required sheet has content"})
    checks.append({"check": "sheets_have_data_rows",
                   "status": "EMPTY" if thin else "SUCCESS",
                   "message": "sheets with only a header row: %s" % thin if thin
                              else "every sheet carries at least one data row"})
    checks.append({"check": "sheet_names_unique",
                   "status": "SUCCESS" if len(names) == len(set(names)) else "FATAL",
                   "message": "%d sheet(s)" % len(names)})

    fatals = [c for c in checks if c["status"] == "FATAL"]
    empties = [c for c in checks if c["status"] == "EMPTY"]
    status = "FATAL" if fatals else ("EMPTY" if empties else "SUCCESS")
    print(json.dumps({"status": status, "file": args.excel, "bytes": size,
                      "sheet_rows": sheet_stats, "checks": checks},
                     ensure_ascii=False, indent=2))
    sys.exit(1 if fatals else 0)


if __name__ == "__main__":
    main()
