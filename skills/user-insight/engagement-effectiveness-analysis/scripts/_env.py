#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Portable environment discovery and dependency bootstrap.

This skill ships to machines the author has never seen, so nothing in it may
assume the author's layout. Every probe here is generic:

  * no hard-coded virtualenv path - the author's `envs/default` does not exist
    on the recipient's machine, and naming it only produces a confusing FATAL;
  * no hard-coded ae-cli location - it may come from PATH, a global npm prefix,
    Homebrew, nvm, or the WorkBuddy managed runtime, and the version directory
    in any of those is not predictable;
  * no assumption that openpyxl is installed - it is bootstrapped instead;
  * no assumption that the platform is macOS.

Standard library only, so that importing this module never fails. Anything that
needs a third-party package must go through `ensure_package()`, which can build a
private virtualenv rather than mutating the user's site-packages.

Discovery order for every external tool is the same three steps: an explicit
override (argument or environment variable), then PATH, then a bounded scan of
conventional install locations. A failure always carries a remediation command
for the platform it is running on.
"""
import glob
import os
import re
import shutil
import subprocess
import sys

# Environment overrides. Both spellings are accepted so that a host can use
# whichever is natural for it.
AE_CLI_ENV_KEYS = ("AE_CLI_PATH", "AE_CLI")
PY_ENV_KEYS = ("AE_PY", "SKILL_PY")

INSTALL_TIMEOUT = 300


def log(msg, prefix="env"):
    print("[%s] %s" % (prefix, msg), file=sys.stderr)


# --------------------------------------------------------------------------
# platform
# --------------------------------------------------------------------------

def is_windows():
    return os.name == "nt" or sys.platform.startswith("win")


def platform_tag():
    if is_windows():
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def executable_names(stem):
    """Candidate file names for an executable on this platform."""
    if is_windows():
        return [stem + ext for ext in (".cmd", ".exe", ".bat", "")]
    return [stem]


def cache_root():
    """A per-user cache directory that exists on every supported platform."""
    env = os.environ.get("AE_SKILL_CACHE")
    if env:
        return env
    if is_windows():
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
        return os.path.join(base, "ae-skill-cache")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Caches/ae-skill-cache")
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "ae-skill-cache")


def _first_env(keys):
    for k in keys:
        v = os.environ.get(k)
        if v and os.path.exists(os.path.expanduser(v)):
            return os.path.expanduser(v)
    return None


# --------------------------------------------------------------------------
# ae-cli discovery
# --------------------------------------------------------------------------

def _ae_cli_glob_patterns():
    """Conventional locations, with version directories left as wildcards."""
    home = os.path.expanduser("~")
    pats = [
        # WorkBuddy managed runtime - the version component varies.
        os.path.join(home, ".workbuddy", "binaries", "node", "*",
                     "node_modules", ".bin", "ae-cli"),
        # Node version managers.
        os.path.join(home, ".nvm", "versions", "node", "*", "bin", "ae-cli"),
        os.path.join(home, ".volta", "bin", "ae-cli"),
        # Per-user and system prefixes.
        os.path.join(home, ".local", "bin", "ae-cli"),
        os.path.join(home, ".npm-global", "bin", "ae-cli"),
        os.path.join(home, "node_modules", ".bin", "ae-cli"),
        "/usr/local/bin/ae-cli",
        "/opt/homebrew/bin/ae-cli",
        "/usr/bin/ae-cli",
    ]
    if is_windows():
        appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        pats.append(os.path.join(appdata, "npm", "ae-cli"))
        pats.append(os.path.join(home, "AppData", "Roaming", "npm", "ae-cli"))
    return pats


def ae_cli_candidates():
    """Ordered candidates for the ae-cli executable. No existence guarantee."""
    out = []
    for name in executable_names("ae-cli"):
        which = shutil.which("ae-cli" if not is_windows() else name)
        if which:
            out.append(which)
    for pattern in _ae_cli_glob_patterns():
        for name in executable_names(pattern):
            out.extend(sorted(glob.glob(name)))
    seen, uniq = set(), []
    for c in out:
        key = os.path.normcase(os.path.abspath(c))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def find_ae_cli(explicit=None, prefer_compatible=True):
    """Locate ae-cli. Raises RuntimeError with platform-specific guidance.

    With prefer_compatible (the default), a binary that actually advertises the
    domains this skill drives beats one that merely sits earlier on PATH. Two
    majors coexist on real machines: 6.x renamed the entire command tree
    (`engage +task_list` -> `engage-task task list`), so the newest or
    first-listed binary is not necessarily the usable one.

    Among several *usable* binaries, 6.x wins. Both generations work, so this is
    a tie-break rather than a correctness fix - but without it the winner is
    decided by the alphabetical order of a directory name (`ae-cli-v1` sorts
    before `workspace` under the WorkBuddy managed runtime), which is arbitrary
    and silently sends the run down the legacy path. 6.x is the documented
    preference and the direction of travel, so make that explicit.
    """
    if explicit:
        if os.path.exists(explicit):
            return explicit
        raise RuntimeError("ae-cli not found at the path given: %s" % explicit)
    env_hit = _first_env(AE_CLI_ENV_KEYS)
    if env_hit:
        return env_hit
    usable = [c for c in ae_cli_candidates()
              if os.path.isfile(c) and os.access(c, os.X_OK)]
    if prefer_compatible:
        compatible = [c for c in usable if ae_cli_compat(c) is True]
        for cand in compatible:
            if detect_variant(cand) == "v6":
                return cand
        if compatible:
            return compatible[0]
    if usable:
        return usable[0]
    raise RuntimeError(
        "ae-cli not found. Install it (npm package @thinkingai/ae-cli, per your "
        "team's distribution channel), then either put it on PATH or point "
        "%s at the executable.\n  Searched: %s"
        % (AE_CLI_ENV_KEYS[0], ", ".join(ae_cli_candidates()) or "(nothing)")
    )


# ae-cli 6.x renamed the whole command tree, so a binary that answers --version
# happily can still be unable to run a single step of this skill. The advertised
# domain list is the cheapest honest test, and it is read once per path.

# The domains the skill drives on ae-cli 1.x. 6.x reorganised the tree - the
# single `engage` domain became `engage-task` / `engage-flow` / `engage-scene`,
# and the `analysis_*` domains moved under `analysis` / `metadata` - so this
# list now identifies a 1.x binary rather than stating a requirement. What the
# skill needs is *either* major; which one it finds decides the command
# vocabulary that _cmdtree translates into.
SKILL_REQUIRED_DOMAINS_V1 = ("engage", "analysis_common", "analysis_meta",
                             "analysis")

# The one domain only 6.x has, and the cheapest way to recognise it.
V6_MARKER_DOMAIN = "capability"

# Legacy alias: callers and tests written before 6.x support exist still ask
# "does this binary speak the domains we drive".
SKILL_REQUIRED_DOMAINS = SKILL_REQUIRED_DOMAINS_V1

_COMPAT_CACHE = {}


def ae_cli_domains(ae, timeout=40):
    """Top-level domains the binary advertises, or None when unreadable."""
    key = os.path.normcase(os.path.abspath(ae))
    if key in _COMPAT_CACHE:
        return _COMPAT_CACHE[key]
    domains = None
    try:
        proc = subprocess.run([ae, "--help", "--no-update-check"],
                              capture_output=True, text=True, timeout=timeout)
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if "Commands:" in text:
            block = text.split("Commands:", 1)[1]
            names = set()
            for line in block.splitlines():
                stripped = line.strip()
                if stripped:
                    names.add(stripped.split()[0])
            domains = names
    except Exception:
        domains = None
    _COMPAT_CACHE[key] = domains
    return domains


def detect_variant(ae):
    """"v1" / "v6" / "other" / None - which ae-cli generation is this binary?

    The two majors advertise disjoint top-level domains, which is the cheapest
    honest test: `--version` and `auth status` answer happily on both, so a
    version string cannot be trusted to say whether this skill can drive it.

    None means the probe could not read the binary at all, which must not be
    reported as "incompatible": an unreadable binary is a different problem
    with a different fix.
    """
    domains = ae_cli_domains(ae)
    if domains is None:
        return None
    if V6_MARKER_DOMAIN in domains:
        return "v6"
    if all(d in domains for d in SKILL_REQUIRED_DOMAINS_V1):
        return "v1"
    return "other"


def ae_cli_compat(ae):
    """True / False / None - can this binary drive the skill at all?

    Both majors qualify. Compatibility stopped meaning "speaks 1.x" once
    _cmdtree learned to translate a 1.x call into a 6.x capability call, so a
    6.x binary is now as good as a 1.x one rather than something to reject.
    """
    variant = detect_variant(ae)
    if variant is None:
        return None
    return variant in ("v1", "v6")


# --------------------------------------------------------------------------
# interpreter discovery
# --------------------------------------------------------------------------

_INTERPRETER_RE = re.compile(r"^python3?(\.\d+)?$")


def is_interpreter_path(path):
    """Reject packaging artefacts that match a `python3*` glob.

    A Homebrew or distro prefix contains python3-config, python3.8-config and
    similarly named helpers next to the real interpreter. Probing each of them
    with a subprocess costs time and can never succeed, so filter by name.

    Both separators are split on: on Windows a path can arrive with forward
    slashes (git-bash, msys, a config file) while `os.path.basename` only knows
    about backslashes there.
    """
    stem = re.split(r"[\\/]", str(path))[-1].lower()
    if stem.endswith(".exe"):
        stem = stem[:-4]
    return _INTERPRETER_RE.match(stem) is not None


def interpreter_candidates():
    """Ordered python interpreters to consider, most specific first."""
    out = []
    env_hit = _first_env(PY_ENV_KEYS)
    if env_hit:
        out.append(env_hit)
    if sys.executable:
        out.append(sys.executable)
    for stem in (["py", "python", "python3"] if is_windows()
                 else ["python3", "python"]):
        which = shutil.which(stem)
        if which:
            out.append(which)
    home = os.path.expanduser("~")
    patterns = [
        os.path.join(home, ".workbuddy", "binaries", "python", "envs", "*", "bin", "python3"),
        os.path.join(home, ".workbuddy", "binaries", "python", "versions", "*", "bin", "python3"),
        "/opt/homebrew/bin/python3*",
        "/usr/local/bin/python3*",
    ]
    if is_windows():
        patterns = [p.replace("/bin/python3", "/Scripts/python.exe") for p in patterns[:2]]
    for pattern in patterns:
        out.extend(sorted(glob.glob(pattern), reverse=True))
    seen, uniq = set(), []
    for c in out:
        if not c or not is_interpreter_path(c):
            continue
        key = os.path.normcase(os.path.abspath(c))
        if key not in seen and os.path.exists(c):
            seen.add(key)
            uniq.append(c)
    return uniq


def has_package(python, package):
    """True when `python` can import `package`. Never raises."""
    try:
        proc = subprocess.run([python, "-c", "import %s" % package],
                              capture_output=True, text=True, timeout=60)
    except Exception:
        return False
    return proc.returncode == 0


def package_version(python, package):
    """Version string of `package` as seen by `python`, or None. Never raises."""
    expr = ("import %s, sys; sys.stdout.write(str(getattr(%s, '__version__', '?')))"
            % (package, package))
    try:
        proc = subprocess.run([python, "-c", expr],
                              capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def find_interpreter_with(package):
    """First candidate interpreter that can import `package`, else None."""
    for cand in interpreter_candidates():
        if has_package(cand, package):
            return cand
    return None


# --------------------------------------------------------------------------
# dependency bootstrap
# --------------------------------------------------------------------------

def venv_python(venv_dir):
    if is_windows():
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python3")


def bootstrap_venv(packages, slug="engagement-effectiveness-analysis",
                   base_dir=None):
    """Create (or reuse) a private virtualenv holding `packages`.

    Returns the interpreter path, or None when bootstrapping is not possible.
    A private venv is preferred over `pip install --user` because the
    recipient's site-packages may be externally managed (PEP 668) and because
    mutating a user's environment is not this skill's business.
    """
    root = base_dir or os.environ.get("AE_SKILL_VENV_ROOT") or cache_root()
    venv_dir = os.path.join(root, slug, "venv")
    py = venv_python(venv_dir)

    if os.path.exists(py) and all(has_package(py, p) for p in packages):
        return py

    try:
        os.makedirs(os.path.dirname(venv_dir), exist_ok=True)
    except OSError as e:
        log("cannot create %s: %s" % (os.path.dirname(venv_dir), e.strerror or e))
        return None

    if not os.path.exists(py):
        try:
            proc = subprocess.run([sys.executable, "-m", "venv", venv_dir],
                                  capture_output=True, text=True, timeout=INSTALL_TIMEOUT)
        except Exception as e:
            log("venv creation failed: %s" % str(e)[:200])
            return None
        if proc.returncode != 0:
            # Debian splits python3-venv out of the base package; surface the
            # real reason instead of a generic failure.
            log("venv creation failed: %s"
                % ((proc.stderr or proc.stdout or "").strip()[:300]))
            return None

    try:
        proc = subprocess.run([py, "-m", "pip", "install", "--quiet"]
                              + list(packages),
                              capture_output=True, text=True, timeout=INSTALL_TIMEOUT)
    except Exception as e:
        log("pip install failed: %s" % str(e)[:200])
        return None
    if proc.returncode != 0:
        log("pip install failed: %s"
            % ((proc.stderr or proc.stdout or "").strip()[:300]))
        return None
    return py if all(has_package(py, p) for p in packages) else None


def die_missing_package(package, consumer, allow_install=True):
    """Print actionable guidance and exit, instead of a bare ImportError.

    A bare ImportError tells the recipient nothing and reads like a bug in the
    skill. This is reached only after the import has already failed, so the two
    useful answers are "run it with the interpreter Step 0 resolved" and
    "install it here" - and the second one may still be solved by bootstrapping.
    """
    state, detail = resolve_package(package, allow_install=allow_install,
                                    slug="engagement-effectiveness-analysis")
    if state in ("present", "available_elsewhere", "bootstrapped"):
        msg = ("%s requires %s, which this interpreter does not have.\n"
               "  running: %s\n"
               "  use:     %s\n"
               "Step 0 resolves this automatically - read context.resolved_python "
               "from its output (persisted to tmp/prereq.json with --out)."
               % (consumer, package, sys.executable, detail))
    else:
        msg = ("%s requires %s, which is not available on this machine.\n"
               "Install it with: %s" % (consumer, package, detail))
    sys.exit(msg)


def install_hint(package):
    """A copy-pasteable install command for this platform."""
    if is_windows():
        return "py -m pip install %s" % package
    return "python3 -m pip install --user %s" % package


def resolve_package(package, allow_install=True, slug=None):
    """Decide how `package` is going to be available.

    Returns (state, detail) where state is one of:
      "present"           - importable by the current interpreter
      "available_elsewhere" - detail is an interpreter path that has it
      "bootstrapped"      - detail is a freshly built interpreter path
      "missing"           - detail is an install command to run
    """
    if has_package(sys.executable, package):
        return "present", sys.executable
    alt = find_interpreter_with(package)
    if alt:
        return "available_elsewhere", alt
    if allow_install:
        built = bootstrap_venv([package], slug=slug or package)
        if built:
            return "bootstrapped", built
    return "missing", install_hint(package)
