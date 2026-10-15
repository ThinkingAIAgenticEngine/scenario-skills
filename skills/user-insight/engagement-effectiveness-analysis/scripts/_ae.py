#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for ae-cli invocation.

Every script in this skill that talks to ae-cli imports from here so that
path discovery, request_id generation and error shaping stay in one place.

No third-party dependencies: standard library only.
"""
import json
import os
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cmdtree  # noqa: E402
import _env  # noqa: E402

# Environment variable that overrides discovery (used by tests / CI).
AE_CLI_ENV = _env.AE_CLI_ENV_KEYS[0]

DEFAULT_TIMEOUT = 120


def log(msg, prefix="ae"):
    print(f"[{prefix}] {msg}", file=sys.stderr)


def find_ae_cli(explicit=None):
    """Locate the ae-cli executable.

    Discovery is delegated to _env deliberately. Hard-coding the author's
    install path here would work on exactly one machine: this skill ships to
    other people, where ae-cli may live in a global npm prefix, Homebrew, nvm,
    or a managed runtime directory whose version component is not predictable.
    """
    return _env.find_ae_cli(explicit)


def new_request_id():
    """ae-cli ad-hoc queries require request_id in the form mcp_<32 hex chars>."""
    return "mcp_" + uuid.uuid4().hex


def _exec(ae, args, timeout=DEFAULT_TIMEOUT, check_json=True):
    """Run ae-cli verbatim and parse its JSON envelope. No translation.

    Split out from run_ae() because the ad-hoc pair is not expressible as a
    per-call translation and has to build its own argv.
    """
    cmd = [ae] + list(args) + ["--no-update-check"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("ae-cli timed out after %ss: %s" % (timeout, " ".join(args)))
    out = (proc.stdout or "").strip()
    if not out:
        # On failure ae-cli writes its error envelope to stderr and leaves
        # stdout empty, so a stdout-only read replaces the real reason (e.g.
        # "HTTP error: 500 Server Error" from the analysis gateway) with a
        # generic one. Return the envelope instead and let the caller shape
        # the error via unwrap_error.
        err = (proc.stderr or "").strip()
        if check_json and err.startswith("{"):
            try:
                return json.loads(err)
            except Exception:
                pass
        raise RuntimeError(
            "ae-cli returned empty output: %s\nstderr: %s"
            % (" ".join(args), (proc.stderr or "")[:400])
        )
    if not check_json:
        return out
    try:
        return json.loads(out)
    except Exception:
        raise RuntimeError("ae-cli returned non-JSON: %s" % out[:400])


def run_ae(args, ae=None, timeout=DEFAULT_TIMEOUT, check_json=True):
    """Run ae-cli with the given argument list and return parsed JSON.

    Callers always describe the call in the 1.x vocabulary; which major is
    installed is resolved here. A 6.x binary receives the capability form of
    the same call, and its differently-shaped response (payload wrapped in
    `result`, every field snake_case) is mapped back to the 1.x shape. That
    keeps the analysis code - the valuable part of this skill - free of any
    dependency on a CLI generation.

    Ad-hoc analysis is the exception: it is one call with a nested definition
    rather than a flag tail, so it cannot be translated one argv at a time. Use
    adhoc_run() for that.

    Raises RuntimeError on execution failure or non-JSON output.
    """
    ae = ae or find_ae_cli()
    args = list(args)
    translated = False
    if _env.detect_variant(ae) == "v6":
        mapped = _cmdtree.translate(args)
        if mapped is None:
            # Failing here, loudly, beats handing a 1.x command line to a 6.x
            # binary: that produces "unknown command", which reads like a
            # broken install rather than an unmapped call.
            raise RuntimeError(
                "ae-cli 6.x has no equivalent for `%s`.\n"
                "  6.x runs ad-hoc analysis as a single "
                "`analysis adhoc run --model-type <m> --definition <json>` call "
                "that rejects raw QP; use _ae.adhoc_run() for that."
                % " ".join(args[:2]))
        args, translated = mapped, True
    resp = _exec(ae, args, timeout=timeout, check_json=check_json)
    return _cmdtree.normalize_envelope(resp) if translated else resp


def adhoc_run(ae, project_id, model_type, time_range, params=None,
              request_id=None, timeout=DEFAULT_TIMEOUT):
    """Run one ad-hoc analysis through the unified 6.x contract.

    6.x takes an AI-facing definition directly and refuses raw QP. Callers
    describe the analysis once - model, time range, model-specific parameters -
    and get the same payload back:

        {"title": [...], "rows": [[...], ...]}

    `params` holds the model's own arguments keyed the way the definition
    schema names them (`funnel`, `metrics`, `time_particle_size`, ...).

    `time_range` may use either spelling of the start/end keys; the outgoing
    form is always snake_case (see _cmdtree.TIME_RANGE_KEYS).
    """
    ae = ae or find_ae_cli()
    params = params or {}

    if _env.detect_variant(ae) != "v6":
        raise RuntimeError(
            "ad-hoc analysis requires ae-cli 6.x: the unified "
            "`analysis adhoc run --model-type <m> --definition <json>` contract")

    argv = _cmdtree.adhoc_capability_argv(model_type, project_id, params,
                                          time_range, request_id)
    resp = _cmdtree.normalize_envelope(_exec(ae, argv, timeout=timeout))
    raise_on_error(resp, "%s analysis" % model_type)
    payload = (resp.get("data") if isinstance(resp, dict) else None) or {}
    if not isinstance(payload, dict) or "rows" not in payload:
        raise RuntimeError(
            "%s analysis returned an unexpected payload: %s"
            % (model_type, json.dumps(payload, ensure_ascii=False)[:400]))
    return payload


def unwrap(resp):
    """Unwrap the ae-cli envelope: {"ok":true,"data":{...}} -> inner data dict.

    Returns None when the call reported ok=false; the caller decides whether
    that is fatal. Error detail is available via unwrap_error().
    """
    if not isinstance(resp, dict):
        return None
    data = resp.get("data")
    if isinstance(data, dict):
        return data
    return None


def unwrap_error(resp):
    """Extract a readable error message from an ae-cli envelope.

    Handles the soft-error shape that ae-cli uses for list endpoints:
    {"ok": true, "data": {"success": false, "message": "Invalid fields: x"}}.
    That envelope looks successful at the top level, so anything that only
    checks `ok` will silently treat a rejected call as an empty result.
    """
    if not isinstance(resp, dict):
        return ""
    err = resp.get("error")
    if isinstance(err, dict):
        return err.get("message") or json.dumps(err, ensure_ascii=False)[:300]
    if isinstance(err, str):
        return err
    data = resp.get("data") or {}
    if isinstance(data, dict):
        if data.get("success") is False:
            detail = data.get("message") or "unknown soft error"
            invalid = (data.get("metadata") or {}).get("invalidFields")
            if invalid:
                detail += " (invalid fields: %s)" % ", ".join(map(str, invalid))
            return str(detail)[:300]
        meta = data.get("metadata") or {}
        inner = meta.get("response") or {}
        errs = inner.get("errors")
        if errs:
            return json.dumps(errs, ensure_ascii=False)[:400]
        if data.get("message"):
            return str(data["message"])[:300]
    return ""


def raise_on_error(resp, what="call"):
    """Raise when the envelope reports a hard failure (`ok: false`).

    Without this, a rejected query that still returns a well-formed envelope
    looks like an ordinary empty result. Soft failures (`ok: true` with
    `data.success: false`) are handled by extract_items() for list endpoints;
    callers that need the detail can still inspect the envelope themselves.
    """
    if isinstance(resp, dict) and resp.get("ok") is False:
        raise RuntimeError("%s failed: %s" % (what, unwrap_error(resp) or "unknown error"))


# 1.x wraps row lists as `data` or `data.items`; 6.x uses `items` or `events`.
# The wrapper is discovered rather than assumed, so no caller has to know which
# generation answered the call. Domain-specific row keys are listed too: they
# sit one level below whatever `data` happens to be, and a scan that stops at
# the first dict would come back empty on the payloads that matter most.
_ITEM_KEYS = ("data", "items", "list", "records", "events", "properties",
              "operationTaskDTOS", "dataList")


def as_list(node, depth=0):
    """The row list inside a list payload, whatever it happens to be called.

    Bounded in depth so a payload that never contains rows terminates instead of
    recursing through arbitrarily nested objects.
    """
    if isinstance(node, list):
        return node
    if isinstance(node, dict) and depth < 3:
        for key in _ITEM_KEYS:
            value = node.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                found = as_list(value, depth + 1)
                if found:
                    return found
    return []


def extract_items(resp, what="items"):
    """Pull the item list out of a list-endpoint response.

    Raises RuntimeError when the server reported a soft failure, so a rejected
    call is never mistaken for "no results".
    """
    if resp is None:
        raise RuntimeError("no response while fetching %s" % what)
    inner = unwrap(resp)
    if inner is None:
        raise RuntimeError("unexpected envelope while fetching %s" % what)
    if inner.get("success") is False:
        raise RuntimeError("server rejected the %s query: %s"
                           % (what, unwrap_error(resp)))
    return as_list(inner)


def die(payload, code=1):
    """Print a structured JSON result and exit with the given code."""
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(code)


def norm_date(value):
    """Normalise a date-ish string to yyyy-MM-dd.

    ae-cli rejects compact (20260701) and datetime forms, so we coerce here
    instead of relying on the caller to remember the format.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("/", "-").replace(".", "-")
    if " " in s:
        s = s.split(" ")[0]
    if "T" in s:
        s = s.split("T")[0]
    if len(s) == 8 and s.isdigit():
        return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])
    parts = s.split("-")
    if len(parts) == 3:
        try:
            return "%04d-%02d-%02d" % (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None
    return None


# --- task metadata ---------------------------------------------------------------
# A project can hold several hundred tasks and +task_list is paged, so any fixed
# "first N" slice is not a membership proof - a perfectly valid low id simply
# sits past it. Every consumer that needs one task's metadata goes through here.

TASK_LIST_PAGE_SIZE = 100
TASK_LIST_MAX_PAGES = 50


def iter_tasks(ae, project_id):
    """Yield every task row of a project, following the pagination cursor."""
    seen, page = 0, 1
    while page <= TASK_LIST_MAX_PAGES:
        resp = run_ae(["engage", "+task_list", "--project_id", str(project_id),
                       "--req", json.dumps({"pageNum": page,
                                            "pageSize": TASK_LIST_PAGE_SIZE})], ae=ae)
        data = resp.get("data") or {}
        items = data.get("operationTaskDTOS") or []
        if not items:
            return
        for t in items:
            yield t
        seen += len(items)
        total = (data.get("pagerResult") or {}).get("totalNum")
        if total and seen >= int(total):
            return
        page += 1


def find_task(ae, project_id, task_id):
    """Return one task row: point lookup first, paged scan as the fallback.

    +task_detail answers for a missing id with a *soft* error - ok=true while
    data.success=false - so that flag is read, not the exit status.
    """
    if task_id:
        try:
            resp = run_ae(["engage", "+task_detail", "--project_id", str(project_id),
                           "--task_id", str(task_id)], ae=ae)
            d = resp.get("data") or {}
            if isinstance(d, dict) and d.get("success") is not False \
                    and (d.get("taskId") or d.get("taskName")):
                return d
        except Exception:
            pass
    for t in iter_tasks(ae, project_id):
        if str(t.get("taskId")) == str(task_id):
            return t
    return None


def task_meta_block(ae, project_id, task_id):
    """Wrap one task row in the envelope that +task_list emits.

    Downstream readers already parse that envelope, so reusing its shape keeps
    them working when only a single task is needed - and skips paging the whole
    list to locate it.
    """
    t = find_task(ae, project_id, task_id)
    if not t:
        return None
    return {"ok": True,
            "data": {"operationTaskDTOS": [t],
                     "pagerResult": {"pageNum": 1, "pageSize": 1, "totalNum": 1}}}
