#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 0 gate - pre-flight environment check.

Usage:
    python3 check_prerequisites.py [--project-id PID] [--workspace DIR]
                                   [--out PATH] [--ae-cli PATH] [--no-install]
                                   [--json]

Verifies, in order:
  1. python version >= 3.8
  2. ae-cli binary is discoverable and executable
  3. ae-cli session is authenticated (auth status returns true)
  4. ae-cli round-trip responds (guards against a half-broken install)
  5. openpyxl is reachable - by any interpreter, bootstrapped if absent
  6. project_id is reachable when supplied
  7. local credential store is readable and writable, and holds a credential
     for the active host
  8. tmp/ and output/ under the workspace are creatable and writable
  9. the active host answers a probe (warning only)

Portable by construction: this script ships to other machines, so it assumes no
particular install layout, no pre-installed packages and no particular platform.
Tool discovery is generic (`_env`), and a missing dependency is resolved rather
than merely reported - check 5 will build a private virtualenv when nothing on
the machine has openpyxl.

Checks 1-6 are remote-authority or interpreter facts. Checks 7-8 are the local
permissions that actually break a run halfway: a non-writable credential store
kills the token refresh, and a read-only workspace surfaces only at Step 4 after
all the fetching is already done. Both are cheaper to catch here.

Exit codes:
  0  SUCCESS  - all hard checks passed
  1  FATAL    - at least one hard check failed; do not start the skill
Output: structured JSON on stdout ({"status":..., "checks":[...]}) plus a
        `context` block. `context.resolved_python` is the interpreter that must
        run Step 4 (export_detail_excel.py); it is not necessarily the one
        running this script.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ae  # noqa: E402
import _env  # noqa: E402

MIN_PYTHON = (3, 8)

# ae-cli keeps one encrypted credential file per host here. Built with join()
# rather than a literal "~/.ae-cli" so the separator is right on Windows too.
CRED_DIR = os.path.join(os.path.expanduser("~"), ".ae-cli")
SECURE_DIR = os.path.join(CRED_DIR, "secure-tokens")


def check_ae_cli(checks, explicit=None):
    try:
        path = _ae.find_ae_cli(explicit)
    except RuntimeError as e:
        checks.append({"check": "ae_cli_binary", "status": "FATAL", "message": str(e)})
        return None
    checks.append({"check": "ae_cli_binary", "status": "SUCCESS",
                   "message": "found at %s" % path, "value": path})
    return path


def check_ae_cli_compat(checks, ae, explicit=None):
    """Confirm the binary is one this skill can actually drive.

    A binary that answers --version and auth status can still fail every single
    step, so the advertised top-level domain list is inspected up front. Both
    generations qualify now: _cmdtree translates a 1.x call into the equivalent
    6.x capability call, so the check reports *which* one it found instead of
    rejecting 6.x.

    A binary that is neither - a future major, or a half-installed one - is
    still a hard failure, because the translation table cannot describe it and
    every step would fail late and confusingly.
    """
    if not ae:
        return
    variant = _env.detect_variant(ae)
    if variant in ("v1", "v6"):
        note = ("calls are translated to capability gateway requests"
                if variant == "v6" else "native command tree")
        checks.append({"check": "ae_cli_compat", "status": "SUCCESS",
                       "message": "%s - %s" % (variant, note), "value": variant})
        return
    if variant is None:
        checks.append({"check": "ae_cli_compat", "status": "ERROR",
                       "message": "could not read the command list from %s "
                                  "(probe timed out or binary unreadable)" % ae})
        return

    found = sorted(_env.ae_cli_domains(ae) or [])
    alternatives = [c for c in _env.ae_cli_candidates()
                    if c != ae and _env.ae_cli_compat(c) is True]
    if alternatives:
        hint = (" A usable binary is present at %s - set AE_CLI_PATH to it."
                % alternatives[0])
    elif explicit:
        hint = (" Drop the override and let discovery pick, or install a "
                "supported ae-cli and point AE_CLI_PATH at it.")
    else:
        hint = (" Install a supported ae-cli (1.x or 6.x) and point "
                "AE_CLI_PATH at it.")
    checks.append({"check": "ae_cli_compat", "status": "FATAL",
                   "message": ("%s is neither a 1.x nor a 6.x ae-cli - its "
                               "command tree matches neither generation this "
                               "skill can address.%s" % (ae, hint)),
                   "domains_found": found[:40]})


def check_auth(checks, ae):
    """Confirm the session is authenticated and report the active host.

    The host matters beyond this check: credentials are stored per host, so a
    project living on a host this machine never logged into will pass the auth
    check and still fail at fetch time. Returning it lets check_credentials
    catch that.
    """
    if not ae:
        return None
    try:
        proc = subprocess.run([ae, "auth", "status", "--no-update-check"],
                              capture_output=True, text=True, timeout=60)
    except Exception as e:
        checks.append({"check": "ae_cli_auth", "status": "FATAL",
                       "message": "auth status failed: %s" % e})
        return None
    raw_out = (proc.stdout or "").strip()
    out = (raw_out + "\n" + (proc.stderr or "")).strip()
    low = out.lower()

    # Parse the structured verdict first. A logged-out session is reported as
    # {"data": {"authenticated": false}}, which matches NONE of the
    # human-readable phrases below. Text matching alone therefore passes a dead
    # session as authenticated - a false positive observed in the field, where
    # the gate said SUCCESS while every subsequent call returned HTTP 500.
    authenticated = None
    host = None
    ok = None
    parsed = None
    for candidate in (raw_out, out):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            break
        except Exception:
            parsed = None
    if isinstance(parsed, dict):
        ok = parsed.get("ok")
        node = parsed.get("data")
        if isinstance(node, dict):
            host = node.get("host")
            if isinstance(node.get("authenticated"), bool):
                authenticated = node["authenticated"]

    if authenticated is False:
        logged_out = True
    elif authenticated is True:
        logged_out = False
    else:
        # Fall back to text only when the verdict is not machine-readable.
        logged_out = (("not logged in" in low) or ("未登录" in out)
                      or ("no credentials" in low))

    if proc.returncode != 0 or logged_out or ok is False:
        if authenticated is False:
            reason = "session reports authenticated=false"
        elif ok is False:
            reason = "auth status call itself failed"
        else:
            reason = "not authenticated"
        checks.append({"check": "ae_cli_auth", "status": "FATAL",
                       "message": "%s - run: ae-cli auth login" % reason,
                       "raw": out[:300]})
        return None

    checks.append({"check": "ae_cli_auth", "status": "SUCCESS",
                   "message": "authenticated" + (" on %s" % host if host else ""),
                   "host": host, "raw": out[:200]})
    return host


MAX_PROJECT_PAGES = 40


def _project_page(ae, offset=None):
    argv = ["analysis_common", "+list_projects"]
    if offset:
        argv += ["--offset", str(offset)]
    resp = _ae.run_ae(argv, ae=ae, timeout=90)
    return resp, _ae.as_list(resp)


def _all_projects(ae, want_id=None):
    """Every project this account can see, following the page cursor.

    6.x pages the project list (50 by default) and sets `has_more`; 1.x answers
    with the whole list at once. Reading only the first page makes "beyond page
    1" indistinguishable from "does not exist" - and the caller below turns
    that into a FATAL, so an account owning more than one page of projects
    would have its perfectly accessible project rejected. Measured on this
    machine: 6.x reported 50 of 300, 1.x reported all 301.

    `want_id` short-circuits the walk once the wanted project shows up, so the
    common case stays a single call.
    """
    projects, offset = [], None
    for _ in range(MAX_PROJECT_PAGES):
        resp, page = _project_page(ae, offset)
        if not isinstance(resp, dict) or not resp.get("ok"):
            raise RuntimeError("list_projects returned not-ok: %s"
                               % _ae.unwrap_error(resp))
        projects.extend(page)
        if want_id is not None and any(
                str(p.get("projectId")) == str(want_id) for p in page):
            return projects
        data = resp.get("data")
        more = isinstance(data, dict) and bool(
            data.get("hasMore") or data.get("has_more"))
        if not more or not page:
            return projects
        nxt = data.get("nextOffset")
        if nxt is None:
            nxt = data.get("next_offset")
        offset = int(nxt) if nxt is not None else (offset or 0) + len(page)
    return projects


def check_schema(checks, ae):
    if not ae:
        return
    try:
        resp, projects = _project_page(ae)
    except Exception as e:
        checks.append({"check": "ae_cli_roundtrip", "status": "ERROR",
                       "message": "list_projects failed: %s" % str(e)[:200]})
        return
    if not isinstance(resp, dict) or not resp.get("ok"):
        checks.append({"check": "ae_cli_roundtrip", "status": "ERROR",
                       "message": "list_projects returned not-ok: %s" % _ae.unwrap_error(resp)})
        return
    # The row count is a page, not a total, whenever the generation pages its
    # list. Quoting it as "N projects visible" overstates what was read.
    data = resp.get("data")
    total = data.get("total") if isinstance(data, dict) else None
    if isinstance(total, int) and total > len(projects):
        detail = "%d projects visible (page 1 of %d)" % (len(projects), total)
    else:
        detail = "%d projects visible" % len(projects)
    checks.append({"check": "ae_cli_roundtrip", "status": "SUCCESS",
                   "message": "ae-cli round-trip ok, " + detail})


def check_openpyxl(checks, allow_install=True):
    """openpyxl must be importable by SOME interpreter the skill can use.

    A missing openpyxl is not a dead end. Naming a specific virtualenv - the
    author's - only helps on the author's machine, so instead the package is
    resolved generically and, when it is nowhere to be found, bootstrapped into
    a private virtualenv. That keeps the skill working on a machine that has
    nothing but a python3.

    Returns the interpreter that should run the XLSX step, or None.
    """
    state, detail = _env.resolve_package(
        "openpyxl", allow_install=allow_install,
        slug="engagement-effectiveness-analysis")

    if state in ("present", "available_elsewhere", "bootstrapped"):
        version = _env.package_version(detail, "openpyxl")
        where = {
            "present": "current interpreter",
            "available_elsewhere": "existing interpreter",
            "bootstrapped": "private virtualenv created by this check",
        }[state]
        extra = ""
        if detail != sys.executable:
            extra = " - run the XLSX step with PY=%s" % detail
        checks.append({
            "check": "openpyxl", "status": "SUCCESS",
            "message": "openpyxl %s via %s%s" % (version or "?", where, extra),
            "interpreter": detail,
            "resolution": state,
        })
        return detail

    # Nothing anywhere, and bootstrapping was disabled or failed. Hand over a
    # command that matches the platform rather than a bare package name.
    checks.append({
        "check": "openpyxl", "status": "FATAL",
        "message": "openpyxl unavailable and could not be bootstrapped (offline, "
                   "no venv module, or an externally managed python). Install it "
                   "with: %s" % detail,
        "interpreter": sys.executable,
        "resolution": "missing",
        "remediation": detail,
    })
    return None


def check_python(checks):
    if sys.version_info < MIN_PYTHON:
        checks.append({"check": "python_version", "status": "FATAL",
                       "message": "python %s < required %s"
                                  % (".".join(map(str, sys.version_info[:3])),
                                     ".".join(map(str, MIN_PYTHON)))})
    else:
        checks.append({"check": "python_version", "status": "SUCCESS",
                       "message": "python %s" % ".".join(map(str, sys.version_info[:3]))})


def _stored_hosts():
    """Hosts this machine holds a credential file for, in stem form."""
    try:
        return sorted(f[:-9] for f in os.listdir(SECURE_DIR) if f.endswith(".enc.json"))
    except OSError:
        return []


def check_project(checks, ae, project_id):
    """Confirm the requested project is visible to this account.

    Walks the whole list rather than the first page: on 6.x the list is paged,
    so "not on page 1" is not evidence that the project is missing. Before this
    followed the cursor, a project on page 5 was reported FATAL - blocking a run
    that would have worked.
    """
    if not project_id or not ae:
        return
    try:
        projects = _all_projects(ae, want_id=project_id)
    except Exception as e:
        checks.append({"check": "project_visible", "status": "ERROR",
                       "message": "could not list projects: %s" % str(e)[:200]})
        return
    ids = {str(p.get("projectId")) for p in projects}
    if str(project_id) in ids:
        checks.append({"check": "project_visible", "status": "SUCCESS",
                       "message": "project %s is accessible" % project_id})
        return
    # list_projects only speaks for the ACTIVE host. A project living on another
    # host looks exactly like a project that does not exist, so name that
    # possibility when this machine holds credentials elsewhere.
    hosts = _stored_hosts()
    extra = ""
    if len(hosts) > 1:
        extra = (" - this machine also holds credentials for %s; the project may live on "
                 "another host (switch with 'ae-cli config')" % ", ".join(hosts))
    checks.append({"check": "project_visible", "status": "FATAL",
                   "message": "project %s not found among %d accessible projects%s"
                              % (project_id, len(ids), extra)})


def _host_stem(host):
    """Normalise a host URL to the secure-tokens filename stem.

    Observed mapping: https://ta.example.com        -> ta.example.com
                      http://ta.example.com:8993    -> ta.example.com_8993
    The port separator becomes an underscore, not a colon.
    """
    if not host:
        return None
    h = str(host).strip()
    for scheme in ("https://", "http://"):
        if h.startswith(scheme):
            h = h[len(scheme):]
    h = h.rstrip("/")
    if not h:
        return None
    return h.replace(":", "_")


def check_credentials(checks, host):
    """Local credential store must be readable, writable, and cover the host.

    Two distinct failures matter, and they are easy to confuse:

      - the store is not writable -> the ~2h access-token refresh cannot
        persist, so a long run dies partway through with a confusing 401;
      - the active host has no credential file -> the project lives on a host
        this machine has never logged into. Auth still reports success because
        it only speaks for the active host.

    Neither is fixable by the skill, so both are FATAL.
    """
    if not os.path.isdir(CRED_DIR):
        checks.append({"check": "credential_store", "status": "FATAL",
                       "message": "%s not found - run: ae-cli auth login" % CRED_DIR})
        return
    if not os.access(CRED_DIR, os.W_OK):
        checks.append({"check": "credential_store", "status": "FATAL",
                       "message": "%s is not writable - token refresh will fail mid-run"
                                  % CRED_DIR})
        return
    if not os.path.isdir(SECURE_DIR):
        checks.append({"check": "credential_store", "status": "FATAL",
                       "message": "%s missing - run: ae-cli auth login" % SECURE_DIR})
        return

    try:
        stored = [f for f in os.listdir(SECURE_DIR) if f.endswith(".enc.json")]
    except OSError as e:
        checks.append({"check": "credential_store", "status": "FATAL",
                       "message": "cannot list %s: %s" % (SECURE_DIR, e.strerror or e)})
        return
    if not stored:
        checks.append({"check": "credential_store", "status": "FATAL",
                       "message": "no credentials under %s - run: ae-cli auth login"
                                  % SECURE_DIR})
        return

    stem = _host_stem(host)
    if stem:
        target = stem + ".enc.json"
        if target in stored:
            path = os.path.join(SECURE_DIR, target)
            if os.access(path, os.R_OK):
                checks.append({"check": "credential_store", "status": "SUCCESS",
                               "message": "writable store, credential for %s present"
                                          % stem})
            else:
                checks.append({"check": "credential_store", "status": "FATAL",
                               "message": "credential for %s is not readable (check file "
                                          "mode on %s)" % (stem, path)})
            return
        checks.append({"check": "credential_store", "status": "FATAL",
                       "message": "no credential for active host %s - this machine has "
                                  "logged into: %s. Switch host with 'ae-cli config', "
                                  "then run 'ae-cli auth login'"
                                  % (stem, ", ".join(sorted(f[:-9] for f in stored)))})
        return

    checks.append({"check": "credential_store", "status": "SUCCESS",
                   "message": "writable store, %d credential(s): %s"
                              % (len(stored), ", ".join(sorted(f[:-9] for f in stored)))})


def check_output_dir(checks, workspace):
    """tmp/ and output/ under the workspace must be creatable and writable.

    Probed by actually creating and writing, because a read-only workspace does
    not surface until Step 4 - after every fetch has already been paid for.
    """
    root = workspace or os.getcwd()
    if not os.path.isdir(root):
        checks.append({"check": "output_writable", "status": "FATAL",
                       "message": "workspace %s is not an existing directory" % root})
        return
    bad, good = [], []
    for sub in ("tmp", "output"):
        d = os.path.join(root, sub)
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".write_probe")
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
            good.append(sub)
        except OSError as e:
            bad.append("%s (%s)" % (sub, e.strerror or e))
    if bad:
        checks.append({"check": "output_writable", "status": "FATAL",
                       "message": "not writable under %s: %s" % (root, "; ".join(bad))})
    else:
        checks.append({"check": "output_writable", "status": "SUCCESS",
                       "message": "tmp/ and output/ writable under %s" % root})


def check_network(checks, host):
    """Short reachability probe against the active host. Warning only.

    Deliberately ERROR, not FATAL: ae-cli fails loudly on its own when the host
    is unreachable, and this probe does not share ae-cli's proxy/VPN path, so a
    probe failure is not proof of a real problem. It is an early signal.
    """
    if not host:
        return
    import urllib.request
    url = host if str(host).startswith("http") else "https://" + str(host)
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
        checks.append({"check": "network_reachable", "status": "SUCCESS",
                       "message": "%s reachable (HTTP %s)" % (url, code)})
    except Exception as e:
        checks.append({"check": "network_reachable", "status": "ERROR",
                       "message": "probe of %s failed: %s - proxy/VPN related is likely; "
                                  "ae-cli will confirm" % (url, str(e)[:160])})


def main():
    ap = argparse.ArgumentParser(description="Step 0 pre-flight check")
    ap.add_argument("--project-id", default=None)
    ap.add_argument("--ae-cli", default=None,
                    help="explicit path to ae-cli, overriding discovery")
    ap.add_argument("--workspace", default=None,
                    help="skill working directory holding tmp/ and output/ "
                         "(defaults to the current directory)")
    ap.add_argument("--out", default=None,
                    help="persist the result JSON here (e.g. tmp/prereq.json) so the "
                         "run can be audited after the fact")
    ap.add_argument("--no-install", action="store_true",
                    help="do not bootstrap a missing dependency into a private "
                         "virtualenv; report it as fatal instead")
    ap.add_argument("--json", action="store_true", help="suppress human summary")
    args = ap.parse_args()

    checks = []
    check_python(checks)
    ae = check_ae_cli(checks, args.ae_cli)
    check_ae_cli_compat(checks, ae, args.ae_cli)
    host = check_auth(checks, ae)
    check_schema(checks, ae)
    # The interpreter reported here is the one the XLSX step must use, which is
    # not necessarily the interpreter running this script.
    py_for_excel = check_openpyxl(checks, allow_install=not args.no_install)
    check_project(checks, ae, args.project_id)
    check_credentials(checks, host)
    check_output_dir(checks, args.workspace)
    check_network(checks, host)

    fatals = [c for c in checks if c["status"] == "FATAL"]
    errors = [c for c in checks if c["status"] == "ERROR"]
    status = "FATAL" if fatals else ("ERROR" if errors else "SUCCESS")
    result = {"status": status, "checks": checks,
              "context": {"workspace": args.workspace or os.getcwd(),
                          "project_id": args.project_id, "host": host,
                          "interpreter": sys.executable,
                          "resolved_python": py_for_excel or sys.executable,
                          "ae_cli": ae,
                          "platform": _env.platform_tag()}}
    # Persist BEFORE printing so that stdout and the file agree on the verdict.
    # Failures are downgraded rather than fatal: a read-only workspace is
    # already reported by check_output_dir, and the verdict itself stands.
    if args.out:
        try:
            parent = os.path.dirname(os.path.abspath(args.out))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
            _ae.log("result written to %s" % args.out, prefix="check")
        except OSError as e:
            detail = e.strerror or str(e)
            _ae.log("could not write %s: %s" % (args.out, detail), prefix="check")
            checks.append({"check": "result_persisted", "status": "ERROR",
                           "message": "could not write %s: %s" % (args.out, detail)})
            if result["status"] == "SUCCESS":
                result["status"] = "ERROR"

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.json:
        _ae.log("pre-flight %s (%d fatal, %d error)" % (status, len(fatals), len(errors)),
                prefix="check")
    sys.exit(1 if fatals else 0)


if __name__ == "__main__":
    main()
