#!/usr/bin/env python3
"""Step 0: Pre-flight check — verify ae-cli auth, Python deps, and scipy availability.

Exit codes: 0 = SUCCESS (or WARN), 1 = FATAL.

A missing scipy is NOT fatal: the analysis engine degrades to a normal
approximation. A missing/unauthenticated ae-cli IS fatal because no data can be
queried at all.
"""
import json
import os
import subprocess
import sys
import tempfile

CHECKS = []


def _run(cmd, timeout=30):
    """Run a command; return (returncode, stdout, stderr, error). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr, None
    except FileNotFoundError:
        return None, "", "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return None, "", "", f"timed out after {timeout}s: {' '.join(cmd)}"
    except OSError as exc:
        return None, "", "", f"cannot execute {cmd[0]}: {exc}"


def _cache_dir():
    """Return the cache root used for this skill's private venv.

    Two sources, in order:

    1. `CACHE_DIR` — pin a directory explicitly. Recommended, because a pinned
       directory survives OS temp cleanup and keeps the venv warm.
    2. A per-user temporary directory. The operating system may reclaim it at
       any time; the venv is then rebuilt on the next run.

    Neither source hardcodes an absolute or OS-specific location, so the shipped
    source carries no machine-specific path.
    """
    override = os.environ.get("CACHE_DIR")
    if override:
        return override
    return os.path.join(tempfile.gettempdir(), "ab-test-analysis")


def _venv_python(cache_dir):
    if sys.platform == "win32":
        return os.path.join(cache_dir, "venv", "Scripts", "python.exe")
    return os.path.join(cache_dir, "venv", "bin", "python")


def _write_sidecar(py_bin):
    """Persist the interpreter that can import scipy, for downstream scripts."""
    sidecar = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".resolved_python")
    try:
        with open(sidecar, "w") as f:
            f.write(py_bin)
    except OSError:
        pass


def check_ae_cli_auth():
    """Check ae-cli is installed and authenticated."""
    rc, out, err, ex = _run(["ae-cli", "auth", "status"])
    if ex:
        CHECKS.append({"check": "ae_cli_auth", "status": "FATAL",
                       "message": f"ae-cli unavailable ({ex}). Install ae-cli and run "
                                  f"`ae-cli auth login` before using this skill."})
        return False
    if rc != 0:
        CHECKS.append({"check": "ae_cli_auth", "status": "FATAL",
                       "message": f"ae-cli returned exit {rc}: "
                                  f"{(err or out).strip()[:300] or 'no output'}. "
                                  f"Run `ae-cli auth login` to (re)authenticate."})
        return False
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        CHECKS.append({"check": "ae_cli_auth", "status": "FATAL",
                       "message": f"ae-cli returned non-JSON output "
                                  f"(first 120 chars: {out[:120]!r}). Check installation."})
        return False

    if not data.get("ok"):
        err_obj = data.get("error")
        detail = err_obj.get("message") if isinstance(err_obj, dict) else err_obj
        CHECKS.append({"check": "ae_cli_auth", "status": "FATAL",
                       "message": f"ae-cli returned error: {detail or 'unknown'}"})
        return False

    auth_data = data.get("data") if isinstance(data.get("data"), dict) else {}
    if auth_data.get("authenticated") is not True:
        CHECKS.append({"check": "ae_cli_auth", "status": "FATAL",
                       "message": "ae-cli has no active authenticated account. Run `ae-cli auth login`."})
        return False

    CHECKS.append({"check": "ae_cli_auth", "status": "PASS", "message": "ae-cli authenticated"})
    return True


def check_ae_cli_capability():
    """Verify the curated ad-hoc analysis command exists locally.

    Do not probe the generic Capability Gateway here. Ad-hoc analysis is
    exposed through `ae-cli analysis adhoc run`; capability inspection is only
    for a concrete schema mismatch, not a routine pre-flight step.
    """
    rc, out, err, ex = _run(["ae-cli", "analysis", "adhoc", "run", "--help"])
    if ex:
        CHECKS.append({"check": "ae_cli_capability", "status": "FATAL",
                       "message": f"Cannot load `ae-cli analysis adhoc run` ({ex})."})
        return False
    if rc != 0:
        CHECKS.append({"check": "ae_cli_capability", "status": "FATAL",
                       "message": f"Cannot load `ae-cli analysis adhoc run` (exit {rc}: "
                                  f"{(err or out).strip()[:200]}). ae-cli version may be too old."})
        return False

    required_flags = ("--project-id", "--model-type", "--definition")
    missing = [flag for flag in required_flags if flag not in out]
    if not missing:
        CHECKS.append({"check": "ae_cli_capability", "status": "PASS",
                       "message": "`ae-cli analysis adhoc run` is available"})
        return True

    CHECKS.append({"check": "ae_cli_capability", "status": "FATAL",
                   "message": "`ae-cli analysis adhoc run` is missing required flags: "
                              f"{', '.join(missing)}."})
    return False


def check_python_deps():
    """Check scipy/numpy; attempt auto-install to a private venv if missing.

    On success the scipy-capable interpreter is persisted to a sidecar file
    (next to this script) so downstream scripts (ab_test_stats.py) can reuse it
    without re-probing. The path is also printed as RESOLVED_PYTHON=... for
    shell capture.

    Missing scipy is reported as WARN, never FATAL — the engine still runs with
    a normal approximation.
    """
    try:
        import scipy  # noqa: F401
        import numpy  # noqa: F401
        _write_sidecar(sys.executable)
        CHECKS.append({"check": "python_deps", "status": "PASS",
                       "message": f"scipy {scipy.__version__} available ({sys.executable})"})
        print(f"RESOLVED_PYTHON={sys.executable}")
        return True
    except ImportError:
        pass

    CHECKS.append({"check": "python_deps", "status": "WARN",
                   "message": "scipy/numpy not found in the current interpreter. "
                              "Attempting auto-install to a private venv."})

    cache_dir = _cache_dir()
    py_bin = _venv_python(cache_dir)

    if not os.path.exists(py_bin):
        try:
            os.makedirs(cache_dir, exist_ok=True)
            subprocess.run([sys.executable, "-m", "venv", os.path.join(cache_dir, "venv")],
                           check=True, capture_output=True, text=True, timeout=180)
            subprocess.run([py_bin, "-m", "pip", "install", "--quiet", "scipy", "numpy"],
                           check=True, capture_output=True, text=True, timeout=600)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()[:300] or str(exc)
            CHECKS.append({"check": "python_deps", "status": "WARN",
                           "message": f"Could not install scipy/numpy ({detail}). "
                                      f"Continuing in normal-approximation mode "
                                      f"(p-value error ~1e-3)."})
            return False
        except (OSError, subprocess.TimeoutExpired) as exc:
            CHECKS.append({"check": "python_deps", "status": "WARN",
                           "message": f"Could not set up the private venv ({exc}). "
                                      f"Continuing in normal-approximation mode."})
            return False

    rc, out, err, ex = _run([py_bin, "-c", "import scipy; import numpy; print('ok')"], timeout=60)
    if rc == 0:
        _write_sidecar(py_bin)
        # A venv built for a different Python minor version cannot have its
        # site-packages loaded into the current interpreter, so the scipy path
        # silently degrades. Surface that instead of pretending it works.
        vrc, vout, _, _ = _run([py_bin, "-c",
                                "import sys;print('%d.%d' % sys.version_info[:2])"], timeout=30)
        venv_ver = vout.strip() if vrc == 0 else "?"
        cur_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
        if venv_ver and venv_ver != cur_ver:
            CHECKS.append({"check": "python_deps", "status": "WARN",
                           "message": f"scipy is available in the private venv ({py_bin}, "
                                      f"Python {venv_ver}) but the current interpreter is Python "
                                      f"{cur_ver}. Run the analysis with the venv interpreter to "
                                      f"get exact p-values, otherwise it degrades to the normal "
                                      f"approximation."})
        else:
            CHECKS.append({"check": "python_deps", "status": "PASS",
                           "message": f"scipy/numpy available in private venv at {py_bin}"})
        print(f"RESOLVED_PYTHON={py_bin}")
        return True

    CHECKS.append({"check": "python_deps", "status": "WARN",
                   "message": f"Private venv exists but scipy is not importable "
                              f"({ex or (err or '').strip()[:200] or f'exit {rc}'}). "
                              f"Continuing in normal-approximation mode. "
                              f"To fix: {py_bin} -m pip install scipy numpy"})
    return False


def main():
    check_ae_cli_auth()
    check_ae_cli_capability()
    check_python_deps()

    fatals = [c for c in CHECKS if c["status"] == "FATAL"]
    warns = [c for c in CHECKS if c["status"] == "WARN"]

    if fatals:
        status = "FATAL"
    elif warns:
        status = "WARN"
    else:
        status = "SUCCESS"

    result = {"status": status, "checks": CHECKS}
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if fatals:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
