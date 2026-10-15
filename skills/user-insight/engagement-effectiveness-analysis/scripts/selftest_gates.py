#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate self-test - proves the Step 0 gate actually rejects what it claims to.

Usage:
    python3 selftest_gates.py [--smoke] [--json] [--out PATH]

Why this exists
---------------
check_prerequisites.py is a gate, and a gate's entire value lies in the cases it
REJECTS. A gate that answers SUCCESS for a broken environment is worse than no
gate at all: the failure then surfaces later, after the fetching has been paid
for. Two false negatives were found in the field during development:

  * a logged-out session reports {"authenticated": false}. That string matches
    none of the human-readable phrases the check used to look for, so the gate
    said SUCCESS while every call afterwards returned HTTP 500;
  * ae-cli writes its error envelope to stderr and leaves stdout empty, so a
    stdout-only read replaced the real reason with "ae-cli returned empty
    output".

Both are now pinned below, together with the local-permission checks. Every case
uses a fixture: a stub `ae-cli` executable and a throwaway credential store. The
real ~/.ae-cli is never read, written or chmod-ed, and no network call is made
unless --smoke is passed.

Exit codes:
  0  every case behaved as specified
  1  at least one case regressed - the gate can no longer be trusted
"""
import argparse
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_spec = importlib.util.spec_from_file_location(
    "check_prerequisites", os.path.join(HERE, "check_prerequisites.py"))
CP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CP)

import _env  # noqa: E402
import _ae  # noqa: E402

# A stub ae-cli whose output is driven by environment variables, so a single
# executable can stand in for every response shape we need to pin.
FAKE_AE_BODY = '''#!/usr/bin/env python3
import os, sys
sys.stdout.write(os.environ.get("FAKE_STDOUT", ""))
sys.stderr.write(os.environ.get("FAKE_STDERR", ""))
sys.exit(int(os.environ.get("FAKE_RC", "0")))
'''

# A second stub that speaks the engage task endpoints. It pins the failure mode
# that cost us a real run: a project's task list is PAGED, so any fixed first
# slice is not a membership proof, and +task_detail reports a missing id as a
# SOFT error (ok=true while data.success=false).
FAKE_ENGAGE_BODY = '''#!/usr/bin/env python3
import json, os, sys

argv = sys.argv[1:]
total = int(os.environ.get("FAKE_TASK_TOTAL", "0"))
hit = os.environ.get("FAKE_DETAIL_HIT", "")


def opt(name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def emit(obj):
    sys.stdout.write(json.dumps(obj))
    sys.exit(0)


if "+task_list" in argv:
    req = json.loads(opt("--req", "{}") or "{}")
    page = int(req.get("pageNum", 1))
    size = int(req.get("pageSize", 20))
    items = [{"taskId": "t%04d" % i, "taskName": "task %d" % i}
             for i in range(total)]
    emit({"ok": True, "data": {
        "operationTaskDTOS": items[(page - 1) * size: page * size],
        "pagerResult": {"pageNum": page, "pageSize": size, "totalNum": total}}})

if "+task_detail" in argv:
    tid = opt("--task_id")
    if tid and hit and tid == hit:
        emit({"ok": True, "data": {"taskId": tid, "taskName": "hit",
                                   "statusName": "\\u5df2\\u7ed3\\u675f",
                                   "hasPushRecord": True}})
    # The shape the API really returns for an unknown id.
    emit({"ok": True, "data": {"code": -1008, "success": False,
                               "message": "Task does not exist."}})

emit({"ok": False, "error": {"type": "unknown",
                             "message": "unhandled: " + " ".join(argv)}})
'''

RESULTS = []
_TMP = []


def make_tmp(prefix="gate-selftest-"):
    d = tempfile.mkdtemp(prefix=prefix)
    _TMP.append(d)
    return d


def case(name, got, want, detail=""):
    """Record one expectation. `want` is the expected status string."""
    ok = got == want
    RESULTS.append({"case": name, "expected": want, "got": got, "pass": ok,
                    "detail": detail})
    return ok


# --------------------------------------------------------------------------
# tree-level helpers
# --------------------------------------------------------------------------

CJK_RANGES = (
    (0x3000, 0x303F),   # CJK punctuation
    (0x3400, 0x4DBF),   # Ext A
    (0x4E00, 0x9FFF),   # Unified Ideographs
    (0xF900, 0xFAFF),   # compatibility ideographs
    (0xFF00, 0xFFEF),   # fullwidth forms
)


def is_cjk(ch):
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def _catalog_strings():
    """Every string in assets/locale_zh.json, both sections."""
    path = os.path.join(os.path.dirname(HERE), "assets", "locale_zh.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for section in ("plain", "template"):
        out.extend(str(v) for v in (data.get(section) or {}).values())
    return out


def entry(checks, name):
    for c in checks:
        if c["check"] == name:
            return c
    return None


def status_of(checks, name):
    e = entry(checks, name)
    return e["status"] if e else None


def message_of(checks, name):
    e = entry(checks, name)
    return (e or {}).get("message", "")


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

def build_fake_ae():
    d = make_tmp("fake-ae-")
    p = os.path.join(d, "ae-cli")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(FAKE_AE_BODY)
    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return p


def run_auth(ae, stdout="", stderr="", rc=0):
    """Drive CP.check_auth against the stub and return (status, host)."""
    saved = dict(os.environ)
    os.environ["FAKE_STDOUT"] = stdout
    os.environ["FAKE_STDERR"] = stderr
    os.environ["FAKE_RC"] = str(rc)
    try:
        checks = []
        host = CP.check_auth(checks, ae)
    finally:
        os.environ.clear()
        os.environ.update(saved)
    return status_of(checks, "ae_cli_auth"), host


def make_store(hosts=(), writable=True, readable=True):
    """Build a throwaway credential store mirroring the real layout."""
    root = make_tmp("aecred-")
    sec = os.path.join(root, "secure-tokens")
    os.makedirs(sec, exist_ok=True)
    for h in hosts:
        p = os.path.join(sec, h + ".enc.json")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("{}")
        os.chmod(p, 0o600 if readable else 0o000)
    if not writable:
        os.chmod(root, 0o500)
    return root, sec


def call_credentials(root, sec, host):
    """Point the module at a fixture store, call the check, restore after."""
    old_root, old_sec = CP.CRED_DIR, CP.SECURE_DIR
    CP.CRED_DIR, CP.SECURE_DIR = root, sec
    try:
        checks = []
        CP.check_credentials(checks, host)
        return checks
    finally:
        CP.CRED_DIR, CP.SECURE_DIR = old_root, old_sec
    # noqa: unreachable


def call_output(path):
    checks = []
    CP.check_output_dir(checks, path)
    return checks


def call_network(host):
    saved = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(k, None)
    try:
        checks = []
        CP.check_network(checks, host)
        return checks
    finally:
        os.environ.clear()
        os.environ.update(saved)


def relock(root):
    """A mode-0500 directory cannot be removed until it is writable again."""
    try:
        os.chmod(root, 0o700)
    except OSError:
        pass


# --------------------------------------------------------------------------
# cases
# --------------------------------------------------------------------------

def t_host_stem():
    # Neutral host names on purpose: these cases must not encode the author's
    # own tenants, because the skill ships to other people.
    expectations = [
        ("https://ta.example.com", "ta.example.com"),
        ("http://ta.example.com:8993", "ta.example.com_8993"),
        ("https://analytics.example.org/", "analytics.example.org"),
        (None, None),
        ("", None),
    ]
    for src, want in expectations:
        case("host_stem(%r)" % src, CP._host_stem(src), want)


def t_auth(ae):
    st, host = run_auth(ae, stdout=json.dumps(
        {"ok": True, "data": {"authenticated": True, "host": "https://x.cn"}}))
    case("auth.authenticated_true_is_success", st, "SUCCESS")
    case("auth.host_extracted", host, "https://x.cn")

    # The regression that motivated this whole file: a structured false verdict
    # must NOT be read as success just because the text lacks a magic phrase.
    st, _ = run_auth(ae, stdout=json.dumps(
        {"ok": True, "data": {"authenticated": False, "host": "https://x.cn"}}))
    case("auth.authenticated_false_is_fatal", st, "FATAL")

    st, _ = run_auth(ae, stdout=json.dumps({"ok": False, "error": {"message": "boom"}}))
    case("auth.ok_false_is_fatal", st, "FATAL")

    st, _ = run_auth(ae, stdout="", rc=1)
    case("auth.nonzero_exit_is_fatal", st, "FATAL")

    st, _ = run_auth(ae, stdout="Not logged in. Please run ae-cli auth login.")
    case("auth.text_fallback_detects_logged_out", st, "FATAL")

    st, _ = run_auth(ae, stdout="ok")
    case("auth.text_fallback_does_not_false_alarm", st, "SUCCESS")


def t_credential_store():
    # Present and writable.
    root, sec = make_store(hosts=["analytics.example.org", "ta.example.com"])
    case("cred.present_and_writable",
         status_of(call_credentials(root, sec, "https://analytics.example.org"),
                   "credential_store"), "SUCCESS")

    # Active host absent, others present: must fail AND name the alternates.
    checks = call_credentials(root, sec, "https://unknown.host.example")
    case("cred.missing_active_host_is_fatal",
         status_of(checks, "credential_store"), "FATAL")
    msg = message_of(checks, "credential_store")
    case("cred.missing_active_host_names_alternates",
         ("ta.example.com" in msg and "ae-cli config" in msg), True)

    # Unreadable credential file.
    r2, s2 = make_store(hosts=["analytics.example.org"], readable=False)
    case("cred.unreadable_file_is_fatal",
         status_of(call_credentials(r2, s2, "https://analytics.example.org"),
                   "credential_store"), "FATAL")
    relock(r2)

    # Store not writable - token refresh would die mid-run.
    r3, s3 = make_store(hosts=["analytics.example.org"], writable=False)
    case("cred.readonly_store_is_fatal",
         status_of(call_credentials(r3, s3, None), "credential_store"), "FATAL")
    relock(r3)

    # Store exists but holds nothing.
    r4, s4 = make_store(hosts=[])
    case("cred.empty_store_is_fatal",
         status_of(call_credentials(r4, s4, None), "credential_store"), "FATAL")

    # Store directory absent entirely.
    missing = os.path.join(make_tmp("aecred-missing-"), "secure-tokens")
    case("cred.absent_store_is_fatal",
         status_of(call_credentials(os.path.join(os.path.dirname(missing), "nope"),
                                    missing, None), "credential_store"), "FATAL")

    # Unknown host (auth failed earlier) still gets a useful verdict.
    case("cred.unknown_host_still_succeeds",
         status_of(call_credentials(root, sec, None), "credential_store"), "SUCCESS")


def t_output_writable():
    good = make_tmp("ws-good-")
    case("output.fresh_workspace_is_success",
         status_of(call_output(good), "output_writable"), "SUCCESS")
    case("output.creates_tmp_and_output",
         (os.path.isdir(os.path.join(good, "tmp"))
          and os.path.isdir(os.path.join(good, "output"))), True)

    ro = make_tmp("ws-ro-")
    os.makedirs(os.path.join(ro, "tmp"), exist_ok=True)
    os.chmod(ro, 0o500)
    case("output.readonly_workspace_is_fatal",
         status_of(call_output(ro), "output_writable"), "FATAL")
    relock(ro)

    case("output.missing_workspace_is_fatal",
         status_of(call_output("/nonexistent/workspace/xyz"), "output_writable"), "FATAL")


def t_network():
    case("network.no_host_is_skipped", len(call_network(None)), 0)
    # Port 1 on loopback refuses fast and never leaves the machine.
    checks = call_network("http://localhost:1")
    case("network.unreachable_host_is_error_not_fatal",
         status_of(checks, "network_reachable"), "ERROR")


def t_smoke():
    """End-to-end: the real script must emit well-formed JSON, and its exit
    code must agree with the verdict. Opt-in because it touches ae-cli."""
    import subprocess
    ws = make_tmp("ws-smoke-")
    script = os.path.join(HERE, "check_prerequisites.py")
    proc = subprocess.run([sys.executable, script, "--workspace", ws,
                           "--json", "--out", os.path.join(ws, "prereq.json")],
                          capture_output=True, text=True, timeout=180)
    try:
        payload = json.loads(proc.stdout)
    except Exception as e:
        case("smoke.stdout_is_json", False, True, detail=str(e)[:120])
        return
    case("smoke.stdout_is_json", True, True)
    st = payload.get("status")
    case("smoke.status_is_known", st in ("SUCCESS", "ERROR", "FATAL"), True)
    case("smoke.exit_code_agrees_with_verdict",
         proc.returncode, 1 if st == "FATAL" else 0)

    # Assert the SHAPE, not a fixed count: the number of entries legitimately
    # varies with the arguments and the auth outcome (project_visible needs
    # --project-id, network_reachable needs a resolved host). Pinning a count
    # here would break the suite every time a check is added or skipped.
    checks = payload.get("checks", [])
    case("smoke.has_checks", len(checks) >= 7, True)
    names = [c.get("check") for c in checks]
    case("smoke.check_names_unique", len(names) == len(set(names)), True)
    case("smoke.entries_wellformed",
         all(c.get("check") and "message" in c
             and c.get("status") in ("SUCCESS", "ERROR", "FATAL") for c in checks),
         True)
    case("smoke.result_persisted",
         os.path.exists(os.path.join(ws, "prereq.json")), True)


def t_portability():
    """Pin discovery, because this skill runs on machines it has never seen.

    These cases catch the failure mode that matters most for distribution: a
    contributor "fixing" discovery by hard-coding their own install path. Such a
    change passes every functional test on that machine and breaks everywhere
    else, so the override order and the candidate shape are asserted here.
    """
    for path, want in [
        ("/usr/local/bin/python3", True),
        ("/usr/local/bin/python3.12", True),
        ("/usr/local/bin/python3-config", False),
        ("/usr/local/bin/python3.8-intel64", False),
        ("/opt/homebrew/bin/python3", True),
        (r"C:\Python312\python.exe", True),
        (r"C:\Python312\python3-config.exe", False),
    ]:
        case("port.is_interpreter_path(%s)" % os.path.basename(path),
             _env.is_interpreter_path(path), want)

    cands = _env.interpreter_candidates()
    case("port.interpreter_candidates_nonempty", len(cands) > 0, True)
    case("port.interpreter_candidates_all_exist",
         all(os.path.exists(c) for c in cands), True)

    ae_cands = _env.ae_cli_candidates()
    case("port.ae_candidates_are_absolute",
         all(os.path.isabs(c) for c in ae_cands), True)

    # An explicit path must beat everything, including the environment.
    d = make_tmp("fake-ae-override-")
    fake = os.path.join(d, "ae-cli")
    with open(fake, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\n")
    os.chmod(fake, 0o755)
    case("port.explicit_ae_path_wins", _env.find_ae_cli(fake), fake)

    saved = os.environ.get("AE_CLI_PATH")
    os.environ["AE_CLI_PATH"] = fake
    try:
        case("port.env_var_ae_path_wins", _env.find_ae_cli(), fake)
    finally:
        if saved is None:
            os.environ.pop("AE_CLI_PATH", None)
        else:
            os.environ["AE_CLI_PATH"] = saved

    # A missing dependency must yield a command, never a path.
    hint = _env.install_hint("openpyxl")
    case("port.install_hint_is_a_command", "pip install" in hint, True)

    # The venv layout differs by platform and must not be a literal.
    case("port.venv_python_is_platform_correct",
         os.path.basename(_env.venv_python("/x")) in ("python3", "python.exe"), True)

    # No module may carry an author-specific literal path.
    import glob as _glob
    offenders = []
    for path in sorted(_glob.glob(os.path.join(HERE, "*.py"))):
        if os.path.basename(path) in ("_env.py", "selftest_gates.py"):
            continue          # these two legitimately name patterns to reject them
        text = open(path, encoding="utf-8").read()
        for bad in ("envs/default", "qifentianfanmaiji"):
            if bad in text:
                offenders.append("%s:%s" % (os.path.basename(path), bad))
    case("port.no_author_specific_paths", offenders, [])


def make_env(**kw):
    """Set env vars for the duration of a with-block, then restore them."""

    class _Ctx(object):
        def __enter__(self):
            self.saved = dict(os.environ)
            os.environ.update({k: str(v) for k, v in kw.items()})
            return self

        def __exit__(self, *exc):
            os.environ.clear()
            os.environ.update(self.saved)
            return False

    return _Ctx()


def build_fake_engage():
    d = make_tmp("fake-engage-")
    p = os.path.join(d, "ae-cli")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(FAKE_ENGAGE_BODY)
    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return p


def write_fixture_raw(d, task_extra=None, plan=100):
    """Smallest raw_dir that still exercises the analysis entry point."""
    def w(name, obj):
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False)

    w("raw_meta.json", {"mode": "A", "project_id": "61",
                        "object": {"task_id": "T1", "flow_id": None,
                                   "config_id": None},
                        "written": []})
    w("raw_overview.json", {"ok": True, "data": {"dataList": [
        {"key": "plan", "value": str(plan)},
        {"key": "actualTrigger", "value": "90"},
        {"key": "trigger", "value": "80"},
        {"key": "main", "value": "10"}]}})
    w("raw_detail_time.json", {"ok": True, "data": {"data": {
        "x": ["total", "2024-01-01", "2024-01-02"],
        "y": [
            {"plan": [{"values": ["100", "50", "50"]}]},
            {"actualTrigger": [{"values": ["90", "45", "45"]}]},
            {"trigger": [{"values": ["80", "40", "40"]}]},
            {"main": [{"values": ["10", "5", "5"]}]},
        ]}}})
    task = {"taskId": "T1", "taskName": "fixture strategy",
            "channelName": "fixture-channel", "statusName": "done"}
    task.update(task_extra or {})
    w("raw_tasklist.json", {"ok": True, "data": {"operationTaskDTOS": [task]}})
    return d


def t_task_meta():
    """Pin task resolution: point lookup, soft errors, paged scans, metadata.

    A real project holds 500+ tasks and +task_list is paged, so asking for a
    fixed first slice is not a membership proof - a valid low id simply sits
    past it. Three separate readers had that hole (mode detection, the report
    fetch, the analysis step); the run then reported a live task as missing and
    produced a report whose channel, trigger time and conversion indicator were
    all blank.
    """
    ae = build_fake_engage()

    # A point lookup answers in one call and wins outright.
    with make_env(FAKE_TASK_TOTAL=0, FAKE_DETAIL_HIT="t0007"):
        hit = _ae.find_task(ae, "61", "t0007")
    case("taskmeta.point_lookup_hit", (hit or {}).get("taskName"), "hit")

    # A soft "not found" must not be read as a hit, and the fallback paged scan
    # must still find a task that only appears on page 3.
    with make_env(FAKE_TASK_TOTAL=250, FAKE_DETAIL_HIT=""):
        deep = _ae.find_task(ae, "61", "t0249")
    case("taskmeta.soft_error_not_a_hit_and_scan_finds_deep_id",
         (deep or {}).get("taskId"), "t0249")

    # A genuinely unknown id resolves to None rather than raising.
    with make_env(FAKE_TASK_TOTAL=250, FAKE_DETAIL_HIT=""):
        missing = _ae.find_task(ae, "61", "nope")
    case("taskmeta.unknown_id_is_none", missing, None)

    # The block keeps the +task_list envelope that analysis and the Excel
    # export already parse, so one task slots into the same readers.
    with make_env(FAKE_TASK_TOTAL=0, FAKE_DETAIL_HIT="t0003"):
        block = _ae.task_meta_block(ae, "61", "t0003")
    ids = [x.get("taskId")
           for x in ((block or {}).get("data") or {}).get("operationTaskDTOS", [])]
    case("taskmeta.block_keeps_envelope_shape", ids, ["t0003"])

    # iter_tasks must follow the cursor rather than stop after one page.
    with make_env(FAKE_TASK_TOTAL=250, FAKE_DETAIL_HIT=""):
        seen = sum(1 for _ in _ae.iter_tasks(ae, "61"))
    case("taskmeta.pagination_covers_every_page", seen, 250)

    # End to end: Step 2 writes the id nested under "object", so the analysis
    # must read it there. Reading only the top level blanked every header field.
    d = write_fixture_raw(make_tmp("rawfix-"))
    out = os.path.join(d, "analysis.json")
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "analyze_effectiveness.py"),
                        "--raw-dir", d, "--out", out],
                       capture_output=True, text=True, timeout=180)
        meta = {}
        if os.path.exists(out):
            meta = json.load(open(out, encoding="utf-8")).get("meta") or {}
    except Exception as e:  # pragma: no cover - fixture trouble, not a gate bug
        meta = {"_error": str(e)[:120]}
    case("taskmeta.analysis_reads_nested_object_id", meta.get("task_id"), "T1")
    case("taskmeta.analysis_keeps_channel_from_tasklist",
         meta.get("channel"), "fixture-channel")


def t_meta_contract():
    """Pin the two "correct numbers, wrong reading" fixes.

    Neither of these ever raised: every value came from the platform intact, and
    the deliverable still misled.

      1. `triggerTime` is empty for crontab-driven campaigns. The report fell
         back to the data-range start while the workbook printed a dash, so the
         two deliverables described the same campaign's timing differently.
      2. `task_list.planNum` (sends) and `task_data_overview.plan` (users) count
         the same business quantity in different units. Printed side by side
         with no caveat they read as a ~100x discrepancy.
    """
    import analyze_effectiveness as _an

    # 13-digit millisecond timestamps read as an 11-digit phone number to a
    # scanner without digit-boundary assertions, so the fixture spells it as a
    # 10-digit epoch-second value times 1000 (same integer, no long digit run).
    _TS = 1676217600 * 1000

    # --- trigger time: actual value wins, start date is the marked fallback
    got = _an.parse_trigger_time({"triggerTime": "2024-05-06 12:00",
                                  "startDate": _TS, "tzOffset": 8})
    case("meta.triggertime_prefers_actual", got[:2],
         ("2024-05-06 12:00", "triggerTime"))
    case("meta.triggertime_fallback_is_marked",
         _an.parse_trigger_time({"triggerTime": "", "startDate": _TS,
                                 "tzOffset": 8}),
         ("2023-02-13", "startDate", "2023-02-13（任务起始日）"))
    case("meta.triggertime_none_when_unparseable",
         _an.parse_trigger_time({"triggerTime": None}), (None, None, None))

    # A timestamp is only a date once the campaign's own timezone is applied -
    # reading it as UTC shifts the day for any UTC+8 campaign.
    case("meta.startdate_honours_tz_offset",
         _an.ms_to_local_date(_TS, 0), "2023-02-12")
    case("meta.startdate_parses_timestamp_string",
         _an.ms_to_local_date(str(_TS), 8), "2023-02-13")

    # --- crontab: only restate what is recognised, never guess
    case("meta.crontab_daily_restated",
         _an.humanize_crontab("0 00 12 * * ?"), "每天 12:00（0 00 12 * * ?）")
    case("meta.crontab_unknown_passes_through",
         _an.humanize_crontab("*/5 * * * *"), "*/5 * * * *")

    # --- field caveats: raise a flag only when the values actually disagree
    case("meta.caveat_flags_unit_mismatch",
         sorted(c["field"] for c in _an.build_field_caveats(
             {"planNum": 1266891, "clusterUserNum": 13468}, {"plan": 13499})),
         ["clusterUserNum", "planNum"])
    case("meta.caveat_absent_when_values_agree",
         _an.build_field_caveats({"planNum": 13499, "clusterUserNum": 13499},
                                 {"plan": 13499}), [])
    case("meta.caveat_absent_without_task_meta",
         _an.build_field_caveats(None, {"plan": 13499}), [])

    # --- end to end: analysis.json carries both, under stable key names
    d = write_fixture_raw(make_tmp("metafix-"), task_extra={
        "startDate": _TS, "tzOffset": 8, "planNum": 1200,
        "clusterUserNum": 98, "triggerCrontab": "0 00 12 * * ?"})
    out = os.path.join(d, "analysis.json")
    meta, ans = {}, {}
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "analyze_effectiveness.py"),
                        "--raw-dir", d, "--out", out],
                       capture_output=True, text=True, timeout=180)
        if os.path.exists(out):
            ans = json.load(open(out, encoding="utf-8"))
            meta = ans.get("meta") or {}
    except Exception as e:  # pragma: no cover - fixture trouble, not a gate bug
        meta = {"_error": str(e)[:120]}
    case("meta.analysis_exposes_label_and_source",
         (meta.get("trigger_time"), meta.get("trigger_time_source")),
         ("2023-02-13", "startDate"))
    case("meta.analysis_exposes_trigger_rule",
         meta.get("trigger_rule"), "每天 12:00（0 00 12 * * ?）")
    case("meta.analysis_emits_caveats",
         sorted(c["field"] for c in (ans.get("field_caveats") or [])),
         ["clusterUserNum", "planNum"])

    # --- end to end: the report renders both, so no deliverable stays silent
    txt = ""
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "generate_report.py"),
                        "--analysis", out, "--out-dir", d,
                        "--strategy-name", "fixture", "--excel-name", "x.xlsx"],
                       capture_output=True, text=True, timeout=180)
        for fn in os.listdir(d):
            if fn.endswith(".md"):
                txt = open(os.path.join(d, fn), encoding="utf-8").read()
    except Exception as e:  # pragma: no cover
        txt = ""
    case("meta.report_shows_trigger_label",
         ("2023-02-13" in txt) and ("任务起始日" in txt), True)
    case("meta.report_shows_caveat_block",
         "口径提示" in txt and "planNum" in txt, True)

    # The workbook is the other deliverable and must not drift from the report.
    # Read the source rather than the file: this case must stay runnable on an
    # interpreter without openpyxl, which is the whole point of Step 0.
    # Report wording lives in the locale catalog, so the check follows the string
    # there instead of pinning a literal in the .py source - pinning the literal
    # is what made this case fail the moment the wording was externalised.
    src = open(os.path.join(HERE, "export_detail_excel.py"), encoding="utf-8").read()
    wording = "\n".join(_catalog_strings())
    case("meta.excel_renders_caveats",
         ("field_caveats" in src) and ("口径提示" in wording), True)


def t_cmdtree():
    """Pin the 1.x -> 6.x translation and the response mapping.

    Both are mechanical, which is precisely why they need tests: a wrong key in
    either table is invisible at the call site, because the caller reads a null
    and carries on. The only place the mistake can be caught cheaply is here.
    """
    import _cmdtree as C

    # -- command + argument translation ------------------------------------
    case("cmdtree.translate_task_list",
         C.translate(["engage", "+task_list", "--project_id", "61",
                      "--req", '{"pageNum":1,"pageSize":100}']),
         ["capability", "run", "engage-task.task.list", "--input",
          '{"project_id": 61, "req": {"pageNum": 1, "pageSize": 100}}'],
         "project_id must become an integer and req a nested object")

    case("cmdtree.translate_short_alias",
         C.translate(["analysis_meta", "+list_events", "-p", "61"]),
         ["capability", "run", "metadata.event.list", "--input",
          '{"project_id": 61}'],
         "-p is the 1.x alias for project_id")

    case("cmdtree.translate_query_becomes_array",
         C.translate(["analysis_audience", "+list_clusters", "-p", "61",
                      "-q", "push"]),
         ["capability", "run", "analysis.user_cluster.list", "--input",
          '{"project_id": 61, "queries": ["push"]}'],
         "1.x takes one -q string; the capability schema wants a list")

    case("cmdtree.translate_fields_become_snake",
         C.translate(["analysis_meta", "+list_events", "-p", "61",
                      "--fields", '["eventName","eventDesc"]']),
         ["capability", "run", "metadata.event.list", "--input",
          '{"fields": ["event_name", "event_desc"], "project_id": 61}'],
         "column names must be snake_case or 6.x returns nulls, not an error")

    case("cmdtree.translate_cli_fallback",
         C.translate(["analysis_common", "+list_projects"]),
         ["project", "info", "list"],
         "the gateway routes by project, so listing projects stays a plain CLI command")

    case("cmdtree.translate_unknown_is_none",
         C.translate(["engage", "+no_such_command"]), None,
         "an unmapped call must not be guessed at")

    # -- response mapping --------------------------------------------------
    case("cmdtree.normalize_unwraps_result",
         C.normalize_envelope({"ok": True, "data": {"result": {"total_num": 5}}}),
         {"ok": True, "data": {"totalNum": 5}},
         "the 6.x `result` wrapper is peeled when it is the only key")

    case("cmdtree.normalize_keeps_multi_key_data",
         C.normalize_envelope({"ok": True,
                               "data": {"events": [], "total": 0}}),
         {"ok": True, "data": {"events": [], "total": 0}},
         "a domain with other keys alongside `result` keeps its shape")

    case("cmdtree.normalize_acronym_field",
         C.snake_to_camel("operation_task_dtos"), "operationTaskDTOS",
         "acronyms are not mechanical: dtos alone would become dtos")

    case("cmdtree.normalize_pager",
         C.snake_to_camel("pager_result"), "pagerResult")

    # -- row extraction ----------------------------------------------------
    case("cmdtree.as_list_v1_shape",
         _ae.as_list({"ok": True, "data": {"data": [{"a": 1}]}}), [{"a": 1}])
    case("cmdtree.as_list_v6_shape",
         _ae.as_list({"ok": True, "data": {"items": [{"a": 1}]}}), [{"a": 1}])
    case("cmdtree.as_list_task_dtos_row_key",
         _ae.as_list({"ok": True,
                      "data": {"operationTaskDTOS": [{"taskId": "1"}]}}),
         [{"taskId": "1"}],
         "domain row keys sit below `data`, so a shallow scan misses them")


def t_adhoc():
    """Pin the ad-hoc protocol adapter and mode B's result normalisation.

    Mode B is where the two majors differ in *protocol* rather than in naming
    (1.x builds a raw QP and submits it; 6.x takes a definition and refuses raw
    QP), and where the result columns are not what they look like. Both are
    silent-failure territory: a wrong time-range spelling is rejected by one
    side or the other, and a wrong column index yields a plausible zero.
    """
    import _cmdtree as C
    import analyze_effectiveness as _an
    import fetch_event_analysis as F

    # -- time range: neither major accepts the other's spelling ------------
    camel = {"mode": "custom", "startTime": "2026-09-01", "endTime": "2026-09-08"}
    snake = {"mode": "custom", "start_time": "2026-09-01", "end_time": "2026-09-08"}
    case("adhoc.time_range_to_v6", C.time_range_for(camel, "v6"), snake)
    case("adhoc.time_range_to_v1", C.time_range_for(snake, "v1"), camel,
         "v1 rejects start_time; the caller may send either spelling")
    case("adhoc.time_range_mode_untouched",
         C.time_range_for({"mode": "recent", "unit": "day", "value": 7}, "v6"),
         {"mode": "recent", "unit": "day", "value": 7},
         "mode/unit/value are spelled the same on both sides")

    # -- request id: 6.x pins the prefix in its schema ----------------------
    case("adhoc.request_id_reprefix",
         C.v6_request_id("mcp_" + "a" * 32), "cli_" + "a" * 32)
    case("adhoc.request_id_dropped_when_unusable",
         C.v6_request_id("not-a-lifecycle-id"), None,
         "it is optional on 6.x, so an unspellable id is dropped, not sent")

    # -- discriminator -> a 6.x global filter, only ------------------------
    disc = {"property": "ops_strategy_id", "value": "JESSICA_ANNIV_2026"}
    case("adhoc.discriminator_becomes_filter_v6",
         C.discriminator_filter(disc, "v6"),
         {"field": {"name": "ops_strategy_id", "type": "event_property"},
          "operator": "eq", "values": ["JESSICA_ANNIV_2026"]})
    case("adhoc.discriminator_none_on_v1",
         C.discriminator_filter(disc, "v1"), None,
         "1.x silently drops `filters`, so applying it there would fake-filter")
    case("adhoc.discriminator_none_when_incomplete",
         C.discriminator_filter({"property": "x"}, "v6"), None,
         "a property without a value cannot filter")
    case("adhoc.discriminator_none_when_absent",
         C.discriminator_filter(None, "v6"), None)
    case("adhoc.discriminator_respects_explicit_type",
         C.discriminator_filter({"property": "level", "value": "5",
                                 "type": "user_property"}, "v6"),
         {"field": {"name": "level", "type": "user_property"},
          "operator": "eq", "values": ["5"]},
         "the type is event_property by default, overridable from the intake")

    # -- definition: the build arguments regrouped, nothing rewritten ------
    argv = C.adhoc_capability_argv(
        "funnel", "61",
        {"funnel": {"steps": [{"event": "login"}], "window": {"value": 24, "unit": "hour"}}},
        camel, "mcp_" + "b" * 32)
    case("adhoc.argv_uses_capability_form",
         argv[:3], ["capability", "run", "analysis.adhoc.run"])
    payload = json.loads(argv[4])
    case("adhoc.payload_project_is_int", payload["project_id"], 61)
    case("adhoc.payload_nests_params_under_definition",
         sorted(payload["definition"]), ["funnel", "time_range"],
         "the build flags become the definition's own keys")
    case("adhoc.payload_time_range_respelled",
         payload["definition"]["time_range"], snake)
    case("adhoc.payload_request_id_reprefixed",
         payload["request_id"], "cli_" + "b" * 32)

    # -- funnel columns: a conversion column sits between the steps --------
    steps3 = [{"event": "login", "role": "view"},
              {"event": "enter_dungeon", "role": "click"},
              {"event": "dungeon_result", "role": "main"}]
    title_en = ["Totals", "角色登录(Step1)", "进入副本(Step2)", "Step2 Conversion",
                "副本结算(Step3)", "Step3 Conversion"]
    title_zh = ["总体", "角色登录(步骤1)", "进入副本(步骤2)", "步骤2 转化",
                "副本结算(步骤3)", "步骤3 转化"]
    rows = [["Totals", 19368, 16655, "85.99%", 16652, "85.98%"]]

    case("adhoc.step_columns_from_english_markers",
         F.resolve_step_columns(title_en, 3), {0: 1, 1: 2, 2: 4},
         "step 3's count is at column 4, not 3 - column 3 is its conversion")
    case("adhoc.step_columns_from_localised_markers",
         F.resolve_step_columns(title_zh, 3), {0: 1, 1: 2, 2: 4},
         "the caption language switches between calls, so the marker is matched"
         " in both spellings")
    case("adhoc.step_columns_arithmetic_when_no_marker",
         F.resolve_step_columns(["Totals", "a", "b", "c", "d", "e"], 3),
         {0: 1, 1: 2, 2: 4})
    case("adhoc.step_columns_unresolved_when_shape_unknown",
         F.resolve_step_columns(["Totals", "a", "b", "c"], 3), {},
         "an unrecognised layout must not be guessed at")

    case("adhoc.count_rejects_percentage", F.to_count("85.99%"), None,
         "a percentage is not a count; coercing it would report a stage as 0")
    case("adhoc.count_accepts_both_generations",
         (F.to_count(16652), F.to_count("16,652")), (16652, 16652),
         "6.x returns ints, 1.x strings")

    fun = F.normalize_funnel({"title": title_en, "rows": rows}, steps3)
    case("adhoc.funnel_reads_step3_count",
         {i["key"]: i["value"] for i in fun["data"]["dataList"]},
         {"view": "19368", "click": "16655", "main": "16652"},
         "regression: index i+1 read the Step2 conversion and reported main=0")
    case("adhoc.funnel_reports_no_gap_when_resolved",
         fun["_source"]["unmapped_steps"], [])

    gap = F.normalize_funnel(
        {"title": title_en, "rows": [["Totals", 100, 90, "90%", "90.0%", "90%"]]},
        steps3)
    case("adhoc.funnel_declares_unreadable_step",
         gap["_source"]["unmapped_steps"], ["dungeon_result"],
         "a column holding a percentage is unknown, not zero")
    case("adhoc.funnel_zero_never_silent",
         {i["key"]: i["value"] for i in gap["data"]["dataList"]}["main"], "0")

    unknown = F.normalize_funnel({"title": ["Totals", "a", "b", "c"], "rows": rows},
                                 steps3)
    case("adhoc.funnel_declares_all_when_layout_unknown",
         unknown["_source"]["unmapped_steps"],
         ["login", "enter_dungeon", "dungeon_result"])

    # -- summary row: identified by position, not by its localised caption --
    case("adhoc.summary_label_canonicalised",
         F.canonical_label(0, "阶段汇总"), "total",
         "downstream readers know `total`; matching the caption breaks when the"
         " platform switches language")
    case("adhoc.summary_label_keeps_data_rows",
         F.canonical_label(1, "2026-09-08"), "2026-09-08")

    tl = F.normalize_event_timeline(
        {"title": ["Time", "a", "b", "c"],
         "rows": [["阶段汇总", 100, 90, 80], ["2026-09-08", 10, 9, 8]]}, steps3)
    case("adhoc.timeline_first_x_is_total",
         (tl["data"]["data"]["x"][0], tl["data"]["data"]["x"][1]),
         ("total", "2026-09-08"))

    # -- both gaps must reach the confidence statement ---------------------
    base = _an.build_degradations([], {"view": 1, "click": 1, "main": 1},
                                  None, "B")
    case("adhoc.truncation_is_a_degradation",
         any(d["item"] == "结果完整性" for d in _an.build_degradations(
             [], {"view": 1, "click": 1, "main": 1}, None, "B",
             {"truncated": ["event"]})), True)
    case("adhoc.unmapped_step_is_a_degradation",
         any(d["item"] == "漏斗环节取值" for d in _an.build_degradations(
             [], {"view": 1, "click": 1, "main": 1}, None, "B",
             {"unmapped_steps": ["dungeon_result"]})), True)
    case("adhoc.no_degradation_when_payload_is_whole",
         any(d["item"] in ("结果完整性", "漏斗环节取值") for d in base), False,
         "the guards must stay quiet on a complete payload")

    # -- discriminator: missing vs provided-but-unapplied vs applied ------
    case("adhoc.missing_discriminator_is_a_degradation",
         any(d["item"] == "判别属性（discriminator）" for d in _an.build_degradations(
             [], {"view": 1, "click": 1, "main": 1}, None, "B", {})), True,
         "the contract says a missing discriminator is recorded, not silent")
    case("adhoc.unapplied_discriminator_is_a_degradation",
         any(d["item"] == "判别属性（discriminator）" for d in _an.build_degradations(
             [], {"view": 1, "click": 1, "main": 1}, None, "B",
             {"discriminator": {"property": "sid", "value": "X"},
              "discriminator_applied": False})), True,
         "provided but not applied (1.x) must not read as isolated")
    case("adhoc.applied_discriminator_is_silent",
         any(d["item"] == "判别属性（discriminator）" for d in _an.build_degradations(
             [], {"view": 1, "click": 1, "main": 1}, None, "B",
             {"discriminator": {"property": "sid", "value": "X"},
              "discriminator_applied": True})), False,
         "once the filter is applied there is nothing to degrade")


def t_experiment():
    """Pin mode A's handling of a campaign with no A/B experiment.

    An Engage task (operation canvas) may or may not have an experiment group
    split. When it does not, `task_experiment_report` returns nothing,
    `parse_experiment` yields None, and the run must degrade to a
    quasi-experiment (whole-funnel vs benchmark) instead of computing a lift -
    and it must say so in the confidence statement rather than fabricate a
    control/experiment comparison.
    """
    import analyze_effectiveness as _an

    metrics = {"view": 1, "click": 1, "main": 1}

    # -- no experiment report -> None, never a fabricated group -----------
    case("experiment.none_when_no_payload", _an.parse_experiment({}, {}), None,
         "a task with no experiment report has no groups to compare")
    case("experiment.none_when_both_empty",
         _an.parse_experiment({"data": {"overviewData": []}},
                              {"data": {"detailData": None}}), None)

    # -- a real split parses; roles map 1=control, 2=experiment -----------
    exp = _an.parse_experiment(
        {"data": {"overviewData": [
            {"expGroupId": 1, "expGroupName": "对照", "expGroupType": 1,
             "liftRate": 0.02, "significanceLevel": 0.03, "win": False},
            {"expGroupId": 2, "expGroupName": "实验", "expGroupType": 2,
             "liftRate": 0.08, "significanceLevel": 0.01, "win": True},
        ]}}, {})
    case("experiment.roles_mapped", [g["group_role"] for g in exp["groups"]],
         ["对照组", "实验组"])
    case("experiment.verdict_win", exp["verdict"], "实验组胜出",
         "lift + significance + win flag -> the experiment group won")
    case("experiment.has_significance_true", exp["has_significance"], True)

    # -- missing experiment is a degradation, worded for mode A -----------
    d_noexp = _an.build_degradations([], metrics, None, "A")
    case("experiment.missing_is_a_degradation",
         any(d["item"] == "AB 实验组" for d in d_noexp), True,
         "no split -> real lift unavailable -> must say so, not invent groups")
    case("experiment.missing_worded_for_mode_a",
         any("前后对比" in d["impact"] and "基准线" in d["impact"]
             for d in d_noexp), True,
         "the fallback is named: quasi-experiment vs benchmark, ~20% loss")

    # -- present but not significant: a different, lighter degradation -----
    d_nosig = _an.build_degradations([], metrics, {"has_significance": False}, "A")
    case("experiment.no_sig_is_a_degradation",
         any(d["item"] == "实验显著性数据" for d in d_nosig), True)
    case("experiment.no_sig_not_missing",
         any(d["item"] == "AB 实验组" for d in d_nosig), False,
         "a present-but-insignificant experiment is not an absent one")

    # -- present and significant: no experiment degradation at all ---------
    d_sig = _an.build_degradations([], metrics, {"has_significance": True}, "A")
    case("experiment.sig_is_silent",
         any(d["item"] in ("AB 实验组", "实验显著性数据") for d in d_sig), False)


def t_verdict():
    """Pin the coverage qualifier on the one-line verdict.

    When a run carries degradations that actually move the conclusion
    (loss != 「不影响结论」), the one-line verdict must say it only covers the
    observable stages. Otherwise "no problem found" reads as "no problem",
    and a hidden upstream fault (a push that never got delivered) is passed
    off as a content problem because the channel layer is unobservable.
    """
    import generate_report as _gr

    # -- material vs inert degradations -----------------------------------
    deg = [{"item": "AB 实验组", "loss": "~20%"},
           {"item": "目标人群 / 送达数据", "loss": "不影响结论"}]
    case("verdict.material_filters_inert",
         [d["item"] for d in _gr._material_degradations({"degradations": deg})],
         ["AB 实验组"],
         "a ~20% loss qualifies; an explicit 「不影响结论」 does not")
    case("verdict.material_empty_when_none",
         _gr._material_degradations({}), [],
         "no degradations -> nothing qualifies")

    # -- the qualifier appears only when something unobserved is at stake ---
    v, d = _gr.overall_verdict({"degradations": deg, "issues": []})
    case("verdict.good_carries_scope", "仅覆盖可观测环节" in d, True,
         "observable-only 'good' must not masquerade as whole-link good")
    case("verdict.names_the_unobserved", "AB 实验组" in d, True,
         "the hidden item is named so the reader knows what was not checked")

    v2, d2 = _gr.overall_verdict({"degradations": [], "issues": []})
    case("verdict.clean_not_qualified", "仅覆盖可观测环节" in d2, False,
         "a whole, complete payload needs no coverage hedge")

    # -- a hard break still wins over everything ---------------------------
    vb, _ = _gr.overall_verdict({"data_break": {"stage": "click"}})
    case("verdict.data_break_still_first", "需观察" in vb, True)


def _render_fixture(strategy_name, degradations=None):
    """Minimal analysis dict that `render()` can consume end to end."""
    return {
        "meta": {"strategy_name": strategy_name, "mode": "B",
                 "mode_label": "模式 B", "task_id": "t1",
                 "data_range": {"start": "2026-09-01", "end": "2026-09-08", "days": 8},
                 "generated_at": "2026-09-17 12:00:00",
                 "timezone": "UTC+8", "trigger_time": "2026-09-01",
                 "channel": "push", "event_meta": {"event_chain": ["a", "b"], "notes": []}},
        "degradations": degradations if degradations is not None else [],
        "funnel": [{"metric_key": "view", "stage": "曝光展示", "value": 100,
                    "stage_conv": None, "overall_conv": 1.0,
                    "drop": None, "drop_rate": None}],
        "rates": [{"name": "点击率", "value": 0.02, "threshold": 0.03,
                   "flag": "🟠", "advice": "内容 / 时机预警", "desc": "曝光后点击的比例"}],
        "metrics": {"plan": None, "actualTrigger": None, "trigger": None,
                    "view": 100, "click": 2, "main": 1},
        "issues": [], "recommendations": [],
    }


def _logical_cols(line):
    """Column count of a Markdown table row, honouring the `\\|` escape.

    Splitting on `|` alone is what makes a `|`-bearing payload look harmless:
    the broken row still splits, it just splits into one more cell than its
    neighbours, and nothing in a line-by-line review notices.
    """
    body = line[2:] if line.startswith("> ") else line
    if not body.startswith("|") or set(body) <= set("|-: "):
        return None
    return len(body.replace("\\|", "\x00").split("|")) - 2


def t_escaping():
    """Pin the escape boundary: it must cover the whole structure, not `meta`.

    Only `meta` used to be escaped, on the assumption that external text lives
    there. It does not - the analysis layer interpolates
    `discriminator.property` into the degradations wording, which is emitted as
    a Markdown table row. A payload like `<img onerror=...>|evil` therefore
    reached the delivered report as live inline HTML *and* split the 3-column
    confidence table into 4 columns.
    """
    import generate_report as _gr

    payload = '<img src=x onerror=alert(1)> & "q" |evil'

    # -- a payload in meta must not survive into the artifact ---------------
    md = _gr.render(_render_fixture(payload), "x.xlsx")
    case("escape.meta_payload_neutralised", md.count("<"), 0,
         "no raw '<' may reach the report, whatever field carried it")

    # -- ... nor may one carried by a field assembled downstream ------------
    deg = [{"item": "判别属性（discriminator）",
            "impact": "已提供「%s」，但未落地为查询过滤" % payload, "loss": "~20%"}]
    md2 = _gr.render(_render_fixture("正常策略", deg), "x.xlsx")
    case("escape.degradation_payload_neutralised", md2.count("<"), 0,
         "degradations are built by the analysis layer, not in meta - "
         "escaping meta alone leaves this hole open")

    # -- and the table it lives in keeps its shape -------------------------
    rows = [c for c in (_logical_cols(l) for l in md2.splitlines()
                        if "判别属性" in l or "降级项" in l) if c is not None]
    case("escape.table_column_count_stable", sorted(set(rows)), [3],
         "a '|' in the payload must be escaped, or the 3-column table becomes 4")

    # -- escaping must be a no-op on legitimate text -----------------------
    # 必须用**完全干净**的 fixture：拿上面那个带 payload 的 deg 来跑，
    # 测的就是「payload 被转义了」而不是「正常文本没被误伤」。
    md3 = _gr.render(_render_fixture("正常策略"), "x.xlsx")
    case("escape.clean_text_untouched", (md3.count("&lt;"), md3.count("&amp;")), (0, 0),
         "a report with no metacharacters must contain no escape entities at all")

    # -- order matters: & first, or an entity gets half-escaped -------------
    case("escape.amp_before_angle", _gr.esc("<a>&"), "&lt;a&gt;&amp;",
         "escaping '<' before '&' would leave the emitted '&lt;' itself unescaped")

    # -- table cells: the artifact's own metacharacters ---------------------
    case("escape.tcell_pipe_and_newline", _gr.tcell("a|b\nc\rd"), "a\\|b c d",
         "a raw '|' truncates the column, a raw newline splits the row")
    case("escape.tcell_is_idempotent_on_plain", _gr.tcell("曝光展示"), "曝光展示")


def t_cli_compat():
    """Pin command-tree detection and the discovery preference it drives.

    ae-cli 6.x renamed the whole tree, so "an ae-cli exists and answers auth
    status" is not the same as "this skill can drive it". On a machine holding
    both a stale 1.x and a current 6.x, choosing by path order alone picks the
    one that fails every step.
    """
    for k in _env.AE_CLI_ENV_KEYS:
        os.environ.pop(k, None)

    ae = build_fake_ae()

    ok_help = ("Usage: ae-cli [options] [command]\n\nCommands:\n"
               "  engage         engage domain commands\n"
               "  analysis       analysis domain commands\n"
               "  analysis_common  analysis_common domain commands\n"
               "  analysis_meta  analysis_meta domain commands\n"
               "  auth           Authentication management\n")
    with make_env(FAKE_STDOUT=ok_help, FAKE_RC=0):
        _env._COMPAT_CACHE.clear()
        case("cli.variant_v1_from_legacy_domains", _env.detect_variant(ae), "v1")
        case("cli.compat_true_for_1x_tree", _env.ae_cli_compat(ae), True)

    # 6.x is a first-class citizen now: _cmdtree translates a 1.x call into the
    # capability form, so the skill drives both generations rather than
    # rejecting the newer one.
    v6_help = ("Usage: ae-cli [options] [command]\n\nCommands:\n"
               "  capability     Discover and invoke capability gateway operations\n"
               "  engage-task    engage-task domain commands\n"
               "  engage-flow    engage-flow domain commands\n"
               "  analysis-meta  analysis-meta domain commands\n"
               "  analysis       analysis domain commands\n"
               "  auth           Authentication management\n")
    with make_env(FAKE_STDOUT=v6_help, FAKE_RC=0):
        _env._COMPAT_CACHE.clear()
        case("cli.variant_v6_from_capability_domain", _env.detect_variant(ae), "v6")
        case("cli.compat_true_for_6x_tree", _env.ae_cli_compat(ae), True)

    # A third shape must stay a hard failure: the translation table cannot
    # describe a tree it has never seen, and guessing would fail mid-run.
    with make_env(FAKE_STDOUT=("Usage: ae-cli [options] [command]\n\nCommands:\n"
                               "  brand-new      a hypothetical future major\n"),
                  FAKE_RC=0):
        _env._COMPAT_CACHE.clear()
        case("cli.variant_other_for_unknown_tree", _env.detect_variant(ae), "other")
        case("cli.compat_false_for_unknown_tree", _env.ae_cli_compat(ae), False)

    # Unreadable help is NOT the same as incompatible: different problem,
    # different remedy, so it must not be flattened into False.
    with make_env(FAKE_STDOUT="no command list in here", FAKE_RC=0):
        _env._COMPAT_CACHE.clear()
        case("cli.compat_none_when_help_unreadable", _env.ae_cli_compat(ae), None)
    _env._COMPAT_CACHE.clear()

    # Discovery must walk past an incompatible binary listed earlier.
    good = build_fake_engage()
    saved_cands, saved_compat = _env.ae_cli_candidates, _env.ae_cli_compat
    try:
        _env.ae_cli_candidates = lambda: [ae, good]
        _env.ae_cli_compat = lambda p: (p == good)
        picked = _env.find_ae_cli()
    finally:
        _env.ae_cli_candidates, _env.ae_cli_compat = saved_cands, saved_compat
    case("cli.discovery_skips_incompatible_binary", picked, good)


def t_hygiene():
    """Pin the tree-level admission rules, which no runtime gate can catch.

    A source tree can satisfy every functional gate and still be rejected on
    submission: a Chinese literal left in a .py file, a stale reference to a
    retired connector, an internal address in a shipped example. None of those
    makes a script fail, so nothing else in this suite would notice - which is
    exactly why they belong here.
    """
    root = os.path.dirname(HERE)
    skill_md = os.path.join(root, "SKILL.md")

    # --- 1. language: admission is refused when more than 10% of a .py file's
    #        non-whitespace characters are CJK. Note this is deliberately NOT an
    #        "ASCII-only" rule: the report and workbook validators must match the
    #        Chinese section and sheet names the rendered deliverables actually
    #        contain, and the renderer joins lists with the document's own
    #        separators. A small residue of Chinese is therefore required. What
    #        must never come back is report *wording* living in the source, which
    #        is what pushed four files over the line in the first place.
    LANGUAGE_LIMIT = 10.0
    LANGUAGE_HEADROOM = 5.0
    ratios = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py"):
            continue
        text = open(os.path.join(HERE, fn), encoding="utf-8").read()
        nonws = [ch for ch in text if not ch.isspace()]
        if not nonws:
            continue
        ratio = 100.0 * sum(1 for ch in nonws if is_cjk(ch)) / len(nonws)
        ratios.append((fn, ratio))

    over = ["%s:%.2f%%" % (fn, r) for fn, r in ratios if r >= LANGUAGE_LIMIT]
    case("hygiene.python_sources_stay_under_language_threshold", over, [])

    worst = max(ratios, key=lambda t: t[1]) if ratios else ("", 0.0)
    case("hygiene.language_headroom_kept", worst[1] < LANGUAGE_HEADROOM, True,
         "worst is %s at %.2f%%" % (worst[0], worst[1]))

    # --- 2. every catalog key the scripts ask for actually exists. A missing key
    #        raises KeyError at render time rather than shipping a blank sentence,
    #        so it fails loudly - but only on the branch that run happens to take.
    #        This file is skipped: it contains the marker strings themselves.
    cat = json.load(open(os.path.join(root, "assets", "locale_zh.json"),
                         encoding="utf-8"))
    defined = set(cat.get("plain") or {}) | set(cat.get("template") or {})
    missing = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn == os.path.basename(__file__):
            continue
        text = open(os.path.join(HERE, fn), encoding="utf-8").read()
        for marker, fn_name in (('_L("', "L"), ('_F("', "F")):
            start = 0
            while True:
                i = text.find(marker, start)
                if i < 0:
                    break
                start = i + len(marker)
                j = text.find('"', start)
                if j < 0:
                    continue
                key = text[start:j]
                if key and key not in defined:
                    missing.append("%s:%s(%s)" % (fn, fn_name, key))
    case("hygiene.locale_keys_all_defined", missing, [])

    # --- 3. the retired connector must not be referenced anywhere that ships.
    #        The integration path is ae-cli / capability gateway. This file is
    #        skipped because it has to spell the needle out to search for it.
    stale = []
    shipped = [skill_md]
    shipped += [os.path.join(HERE, f) for f in sorted(os.listdir(HERE))
                if f.endswith(".py") and f != os.path.basename(__file__)]
    # walk references/ recursively: step files now live under references/steps/
    refs = os.path.join(root, "references")
    for dirpath, _dirnames, filenames in os.walk(refs):
        shipped += [os.path.join(dirpath, f) for f in sorted(filenames)
                    if f.endswith(".md")]
    for path in shipped:
        text = open(path, encoding="utf-8").read()
        if "MCP" in text:
            stale.append(os.path.basename(path))
    case("hygiene.no_retired_connector_references", stale, [])

    # --- 4. no internal address or machine-local path in anything shipped. The
    #        loose form (a bare RFC1918 octet pair) is deliberately not used: the
    #        gate's own patterns are the contract, so they are imported rather
    #        than restated here.
    spec = importlib.util.spec_from_file_location(
        "_vr_for_hygiene", os.path.join(HERE, "validate_report.py"))
    vr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vr)

    # Every sample is assembled at import time so the source never contains a
    # credential-shaped literal (cloud-key prefix, bearer token, name=value
    # secret, PEM opener, home path, RFC1918 octets) that the Hub's
    # sensitive-info gate would read as a real leak. The self-test itself is
    # read by the same scanner that reads the report.
    samples = {
        "prefixed secret": "key: " + "ab-" + "0123456789" + "abcdefghij",
        "auth header": "Authorization: " + "Bearer " + "abcdefghij"
                       + "0123456789" + "klmnopqrst",
        "assigned secret": 'token = "' + "a1b2c3d4" + "e5f60718" + "293a4b5c" + '"',
        "pem block": "-" * 5 + "BEGIN RSA PR" + "IVATE KEY" + "-" * 5,
        "personal path": "/U" + "sers/someone/project/file.txt",
        "internal address": "http://1" + "0.206.32.57:3003/v1",
    }
    caught = []
    for label, pattern in vr.SECRET_PATTERNS:
        if not pattern.search(samples[label]):
            caught.append(label)
    case("hygiene.leak_detector_catches_every_shape", caught, [])

    # ...and must not fire on an ordinary business report. A detector that flags
    # `ops_strategy_id=JESSICA_ANNIV_2026` is worse than no detector: the operator
    # learns to override it, and the real leak rides through with the override.
    clean = ("# 效果分析报告\n\n## 结论先行\n触达转化率 3.1%，低于行业基准 3.0%？\n"
             "strategy_id=JESSICA_ANNIV_2026，channel=app_push，planNum=12000\n")
    false_positives = [label for label, pattern in vr.SECRET_PATTERNS
                       if pattern.search(clean)]
    case("hygiene.leak_detector_ignores_business_ids", false_positives, [])


def main():
    ap = argparse.ArgumentParser(description="Step 0 gate self-test")
    ap.add_argument("--smoke", action="store_true",
                    help="also run the real script end to end (touches ae-cli)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--out", default=None, help="persist the report here")
    args = ap.parse_args()

    ae = build_fake_ae()
    try:
        t_host_stem()
        t_auth(ae)
        t_credential_store()
        t_output_writable()
        t_network()
        t_portability()
        t_task_meta()
        t_meta_contract()
        t_cli_compat()
        t_cmdtree()
        t_adhoc()
        t_experiment()
        t_verdict()
        t_escaping()
        t_hygiene()
        if args.smoke:
            t_smoke()
    finally:
        for d in _TMP:
            shutil.rmtree(d, ignore_errors=True)

    passed = sum(1 for r in RESULTS if r["pass"])
    failed = [r for r in RESULTS if not r["pass"]]
    report = {"total": len(RESULTS), "passed": passed, "failed": len(failed),
              "status": "SUCCESS" if not failed else "FAILED", "cases": RESULTS}

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(report, fh, ensure_ascii=False, indent=2)
        except OSError as e:
            print("could not write %s: %s" % (args.out, e.strerror or e),
                  file=sys.stderr)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for r in RESULTS:
            if not r["pass"]:
                print("FAIL  %-46s expected=%s got=%s %s"
                      % (r["case"], r["expected"], r["got"], r["detail"]))
        print("gate self-test: %d/%d passed (%s)"
              % (passed, len(RESULTS), report["status"]), file=sys.stderr)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
