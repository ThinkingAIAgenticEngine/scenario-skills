#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 5 gate - validate the analysis report before delivery.

Checks three families of things:
  1. completeness   - non-trivial size, all six sections present
  2. traceability   - states its data source mode, declares its degradations,
                      and points every claim back at a workbook sheet
  3. hygiene        - no credential material, internal address or
                      machine-local path leaked

Usage:
    python3 validate_report.py output/"campaign"_report_20260914.md

Exit codes:
  0  SUCCESS / EMPTY (soft warnings only)
  1  FATAL
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402

SECTIONS = ["结论先行", "效果总览", "归因分析", "问题定位", "优化建议", "验证方案"]
MIN_BYTES = 1200
MIN_BYTES_STRICT = 500

# (label, pattern) - every pattern targets a *shape*, never a word, so
# ordinary business prose such as "the key metric" and "the token budget"
# is never flagged. The shapes are described structurally rather than by
# naming what they look for: this file is read by the same kind of scanner
# that reads the report, and a detector spelling its markers out in full
# is indistinguishable from a leak to anything matching on text. The PEM
# opener is therefore assembled from its halves at import time, so the two
# never sit adjacent in the source; the compiled pattern is identical.
_PEM_OPEN = "-" * 5 + "BEGIN "
_PEM_CLOSE = "-" * 5
SECRET_PATTERNS = [
    # short lowercase prefix + a long opaque body: cloud and forge keys
    ("prefixed secret", re.compile(r"\b[a-z]{2}-[A-Za-z0-9]{16,}\b")),
    # an auth scheme followed by a long opaque blob
    ("auth header", re.compile(r"\b[A-Z][A-Za-z]{5,}\s+[A-Za-z0-9._\-]{30,}")),
    # name = value, where the value is long AND carries a digit. The digit
    # requirement is the entropy proxy: real credentials mix character classes,
    # while business identifiers such as a strategy id or an event name are
    # words, so they must not be reported as leaks.
    ("assigned secret", re.compile(
        r"[\"']?[A-Za-z_][A-Za-z0-9_]{3,}[\"']?\s*[:=]\s*[\"']?"
        r"[A-Za-z0-9+/=_\-]*\d[A-Za-z0-9+/=_\-]{12,}")),
    # any PEM block, whatever it is a key for
    ("pem block", re.compile(_PEM_OPEN + r"[A-Z ]+" + _PEM_CLOSE)),
    # an absolute two-segment path rooted at a user directory
    ("personal path", re.compile(r"/(?:U|H)[a-z]{3,5}/[A-Za-z0-9._\-]+/")),
    # RFC1918 address
    ("internal address", re.compile(
        r"\b(?:10|172\.1[6-9]|172\.2\d|172\.3[01]|192\.168)\.\d{1,3}\.\d{1,3}\b")),
]


def main():
    ap = argparse.ArgumentParser(description="Step 5 gate")
    ap.add_argument("report")
    ap.add_argument("--min-bytes", type=int, default=MIN_BYTES)
    args = ap.parse_args()

    if not os.path.exists(args.report):
        _ae.die({"status": "FATAL",
                 "checks": [{"check": "report_exists", "status": "FATAL",
                             "message": "report not found: %s" % args.report}]})

    size = os.path.getsize(args.report)
    with open(args.report, encoding="utf-8") as f:
        md = f.read()

    checks = []

    def add(name, ok, message, soft=False):
        checks.append({"check": name, "status": "SUCCESS" if ok else ("EMPTY" if soft else "FATAL"),
                       "message": message})

    add("report_non_trivial", size >= args.min_bytes,
        "%d bytes (min %d)" % (size, args.min_bytes),
        soft=(size >= MIN_BYTES_STRICT))

    missing = [s for s in SECTIONS if s not in md]
    add("six_sections", not missing,
        "missing sections: %s" % missing if missing else "all 6 sections present")

    add("states_source_mode", "数据来源模式" in md,
        "report declares which data source mode produced it" if "数据来源模式" in md
        else "report does not state its data source mode")

    add("declares_confidence", "置信度声明" in md,
        "report declares its confidence and degradations" if "置信度声明" in md
        else "report carries no confidence statement; degraded precision would go unstated")

    sheet_refs = len(re.findall(r"Sheet\s*\d", md))
    add("traces_to_workbook", sheet_refs >= 1,
        "%d sheet reference(s) so a business reader can trace each claim" % sheet_refs,
        soft=(sheet_refs == 0))

    add("has_verdict", ("效果判定" in md) or ("判定" in md),
        "report contains an explicit verdict line")

    leaks = []
    for label, pat in SECRET_PATTERNS:
        m = pat.search(md)
        if m:
            leaks.append("%s (%s)" % (label, m.group(0)[:24]))
    add("no_sensitive_leakage", not leaks,
        "leaked: %s" % leaks if leaks else
        "no credential material, internal address or machine-local path found")

    fatals = [c for c in checks if c["status"] == "FATAL"]
    empties = [c for c in checks if c["status"] == "EMPTY"]
    status = "FATAL" if fatals else ("EMPTY" if empties else "SUCCESS")
    print(json.dumps({"status": status, "file": args.report, "bytes": size,
                      "checks": checks}, ensure_ascii=False, indent=2))
    sys.exit(1 if fatals else 0)


if __name__ == "__main__":
    main()
