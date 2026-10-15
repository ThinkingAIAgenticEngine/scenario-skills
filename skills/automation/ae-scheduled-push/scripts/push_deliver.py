#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scheduled-push :: push_deliver.py (data pipeline × message template × slots)
Sole script asset (automation path). Reads push_spec.json -> fetch data (run/export dual pipelines) ->
summary aggregation -> template fill -> delivery via delivery.mechanisms (IM CLI / webhook).

Usage:
  python3 ./push_deliver.py <push_spec.json> [--push]             # data task, full pipeline
  python3 ./push_deliver.py <push_spec.json> --check-spec         # pure static validation (no fetch, no push; review/release gate)
  python3 ./push_deliver.py <push_spec.json> --stage data         # report task: data stage
  python3 ./push_deliver.py <push_spec.json> --stage render       # report task: render & delivery stage
    --push    force real push (RUN message templates carry it; spec.auto_push is the BUILD-phase safety net; either one takes effect)
    A report task run without --stage runs the full pipeline (BUILD trial run): fetch -> placeholder analysis -> render preview, no push;
    the first real push of a report task uses the two-stage flow (--stage data -> write analysis -> --stage render --push),
    full pipeline + --push is rejected (avoids pushing placeholder analysis text into a real group)
Environment variables:
  SCHEDULED_PUSH_DRY_RUN=1   suppress all real pushes (overrides auto_push/--push)

Message template system (authoritative definition in push-spec-schema.md "Message Templates" section):
  message.template = built-in template name (builtin:plain/rich/card_chart/card_table) or inline custom template
  (text skeleton string / card 2.0 JSON skeleton). The fill engine fills query outputs into placeholders:
  {{q.<label>.rows|.long|.n|.v.<column>}}, {{agg.<name>}} (computed by summary), {{task_name}}/{{date}}, etc.
  The placeholder vocabulary is a closed set (of data transforms) — the template-structure dimension is open; adding to the data-transform dimension requires changing this script.
  Static validation: template references a nonexistent label/agg name -> exit code 2.
  Card delivery: im_cli (lark-cli --content) and feishu webhook are implemented; other channels degrade to plain text + WARNING.

Timezone model:
  multi_tz=true  -> windows split days by timezone.offset (settlement timezone); SQL conversion is the template's responsibility
  multi_tz=false -> no timezone concept: windows split days by server calendar (+list-automations scheduleTimeZone
                    read authoritatively; on failure WARN and fall back to +8; the sandbox date is the container clock, never use it as a basis)

Data-fetch pipeline (two-layer structure; authoritative definition in push-spec-schema.md "Data Pipeline" section):
  At BUILD time queries[].fetch is locked to run | export per user scenario (bounded message body -> run;
  large table / detail-row export -> export; the file section detail_query is naturally export).
  RUN-time fallback: a query locked to run that hits has_more / QUERY_TIMEOUT (2 retries) switches to export;
  deterministic failures (syntax / table missing) do not switch (placeholder + exit 1).
  export execution: submit -> --wait --wait-timeout-seconds 300 -> deliver once complete;
  timeout (ASYNC_WAIT_TIMEOUT) is not a failure -> analysis run wait --run-id resumes (short-window polling).

summary aggregation (decision point a): summary numbers are computed by the engine over all detail rows (sum/count/count_distinct,
declared in queries[].summary) — same batch of rows, so the summary and the detail rows share the same metric definition by construction; no separate summary SQL.

Delivery mechanism semantics (push-spec-schema.md is authoritative; this is a summary):
  mechanisms[] execute in order; for the same delivery target the first success wins (later entries for the same target = backup, skipped;
  backup entries are configured only when the user explicitly asks for cross-channel fallback). Target identification: explicit group field takes priority
  (same group = cross-channel primary/backup group, e.g. two mechanisms share one group for "if Feishu fails, send via WeCom"; when unset,
  grouping follows each mechanism's own target key — cross-channel is always a different target = broadcast double-send). Different targets are delivered independently (broadcast).
  If any target's text or file is not delivered -> exit code 3.
  Degradation happens within a channel: when the card form cannot be sent -> degrade to plain text + WARNING in the same channel (delivery first);
  form_ok/file_ok are BUILD-phase test-delivery records and are not consumed at RUN time.

Design decision execution semantics (numbered R1~R5; authoritative definition in push-spec-schema.md):
  R1 partial push: single query failure -> other sections push normally, the failed section marked [fetch failed] (technical detail stays in run_result/stderr, never goes to the group), exit code 1
  R2 no data:   on_empty=push (default) pushes a "no data this period" placeholder; if all sections skip with 0 rows the whole message is not pushed
  R3 fetch failure: all failed -> whole-message placeholder + exit code 1 (fail loud on both channels)
  R4 size truncation: when the message > max_message_kb, row-set sections are truncated first (with annotation), summary sections preserved as much as possible, last-resort row-level trimming as the fallback
  R5 push retry: network-class failures (including HTTP 429/5xx transient failures) retry 3 times with 2/4/8s backoff;
               deterministic failures (other HTTP non-2xx / nonzero business code / CLI missing / unparseable output) are not retried
  Two-stage report: --stage data produces data.json (deterministic); --stage render validates
              analysis_slots.json slot keys = outline sections (missing/extra -> exit code 2), then renders and delivers
  BUILD-only semantics: in a full-pipeline trial run of a report task (without --stage), all queries failing blocks with exit code 2
                    (prevents registering a broken spec as an automation), unlike RUN-time R3 placeholder + exit 1
Exit codes (authoritative table in push-spec-schema.md): 0 normal / 1 fetch failure / 2 spec missing, placeholder reference validation
  failure or slot validation failure / 3 push failure. Note: see above for the meaning of 1 vs 2 in the BUILD full-pipeline trial-run context.
"""
import csv
import datetime
import gzip
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib import request as urlrequest

MB = 1024 * 1024
QUERY_TIMEOUT_SECONDS = 300          # run pipeline subprocess fallback timeout (CLI internal 180s triggers first)
RUN_QUERY_TIMEOUT_FLAG = 180         # adhoc run explicit --timeout-seconds (CLI upper limit)
QUERY_TIMEOUT_CODE = "QUERY_TIMEOUT"
QUERY_TIMEOUT_MAX_RETRIES = 2        # run timeout retries (2 retries total before switching to export)
PREVIEW_ROWS = 1000                  # (1) run pipeline requested rows (fetch request parameter; cluster sync cap varies per customer)
DASHBOARD_PREVIEW_ROWS_DEFAULT = 100   # (2) dashboard_report source requested rows (this pipeline always yields 100 rows)
SAMPLE_ROWS = 5                      # sample rows shown in the BUILD trial run
PREVIEW_ROWS_DEFAULT = 100           # (3) row-set display cap inside a message (render-layer truncation; different duty from (1)/(2), do not confuse)
# (1)/(2) are fetch request parameters (how many rows to ask the platform for); (3) is render-layer truncation (how many rows show in the message) — full row sets come from the export pipeline
PUSH_MAX_RETRIES = 3                 # network-layer retries (2/4/8s backoff)
PUSH_RETRY_BASE_DELAY = 2
RETRYABLE_ERRS = {"network", "timeout"}   # only network-class errors retry; biz/http/cli_missing/parse are deterministic failures passed through
LARK_TIMEOUT_SECONDS = 60
EXPORT_WAIT_SECONDS = 300            # export --wait short window (timeout goes to the run wait resume, not a failure)
EXPORT_MAX_RESUME_ROUNDS = 20        # run wait resume round cap (300s per round, ~100 minutes total)
DATA_JSON = "data.json"
REPORT_ROWS_CAP = 200               # per-section row cap persisted to data.json (protects the RUN-time Agent's whole-read context; full row sets stay in the render layer and never enter LLM view)
SLOTS_JSON = "analysis_slots.json"

DRY_RUN = os.environ.get("SCHEDULED_PUSH_DRY_RUN", "0") == "1"
RUN_RESULT_NAME = "run_result.json"   # written next to the spec
PLACEHOLDER_RESIDUE_RE = re.compile(r"\{\{[^{}]+\}\}")
INT_STR_RE = re.compile(r"-?\d+")

# Message template placeholders (closed vocabulary; authoritative definition in push-spec-schema.md "Placeholder Vocabulary")
PLACEHOLDER_RE = re.compile(
    r"\{\{(q\.[^{}]+?|agg\.[^{}]+?|task_name|date|window_range|window_start|window_end)\}\}")
BUILTIN_TEMPLATES = ("builtin:plain", "builtin:rich", "builtin:card_chart", "builtin:card_table")
AGG_KINDS = ("sum", "count", "count_distinct")
# Common English column names returned by channels -> display names (display-layer mapping only, data untouched)
COLNAME_DISPLAY_MAP = {"Time": "Time", "time": "Time", "Date": "Date", "date": "Date"}

# Spec field reconciliation list (for schema↔script reconciliation: load_spec WARNs on fields outside the list, preventing multi-source drift).
# Semantics = "fields the script knows about": truly consumed fields plus informational fields (schedule_hint/projects etc. are not
# read at RUN time but are legitimate spec components — informational fields do not warn; real dead fields are not listed, listing them would create false negatives).
# Maintenance discipline: when field tables in push-spec-schema.md add/remove fields, this list must be synced (two-way reconciliation to prevent doc-script drift).
_KNOWN_TOP = {"task_name", "project_id", "project_name", "projects", "content",
              "schedule_hint", "delivery", "timezone", "cli_version", "auto_push",
              "env", "cli"}
_KNOWN_CONTENT = {"kind", "queries", "window_freq", "message", "file", "on_empty",
                  "max_message_kb", "report", "title_template"}
_KNOWN_QUERY = {"label", "source", "sql_template", "dashboard_id", "report_ids",
                "mode", "on_empty", "project_id", "chart", "fetch",
                "summary"}
_KNOWN_REPORT = {"outline", "template"}
_KNOWN_MECH = {"mechanism", "tool", "target", "webhook_url", "webhook_kind",
               "file_ok", "form_ok", "group", "send_template", "send_file_template",
               "success"}
_KNOWN_DELIVERY = {"mechanisms", "file_name"}
_KNOWN_TZ = {"multi_tz", "offset", "offset_source", "zone_offset_column", "server_tz"}
# SQL placeholder closed vocabulary (window placeholders actually consumed by render_sql — all other {{...}} must be replaced at BUILD time)
SQL_PLACEHOLDER_VOCAB = {"date", "window_start", "window_end",
                         "month_start", "month_end", "week_start", "week_end"}


def log(*a):
    print("[push_deliver]", *a, file=sys.stderr, flush=True)


def die(msg, code=1):
    print(f"[FATAL] {msg}", file=sys.stderr)
    sys.exit(code)


def sep_line():
    return "─" * 12


def _display_col(c):
    """Display-layer column-name mapping (Time etc.); render only, does not touch data or placeholder references"""
    return COLNAME_DISPLAY_MAP.get(c, c)


# ---------- spec ----------
# ---------- im_cli command templates (custom channel CLI adapter, locked into spec at BUILD time) ----------
# An im_cli without send_template = the lark-cli default form (im +messages-send --chat-id/--user-id
# --as user). With a template = a direct-send adapter for any channel CLI: after placeholder substitution the argv elements
# execute one by one, with no shell concatenation; success is judged by the success field (default exit code 0).
CMD_TPL_PLACEHOLDERS = {
    "{tool}": "tool", "{target_id}": "target_id", "{target_type}": "target_type",
    "{text}": "text", "{file}": "file", "{display_name}": "display_name",
}
_CMD_TPL_RE = re.compile(r"\{[a-z][a-z_]*\}")   # tight match: only {lowercase/underscore} counts as a placeholder candidate
_CMD_TPL_WIDE_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_-]*\}")  # wide match (validation only): also catches near-miss typos like {Text}/{text2}; does not hit JSON payloads ({"key":...} is not identifier-shaped, no match)
_CMD_TPL_SUB_RE = re.compile("|".join(re.escape(t) for t in CMD_TPL_PLACEHOLDERS))  # for single-pass substitution
_SAFE_CLI_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*-cli$")


def _validate_cli_tool(tool, i):
    """Custom adapters may invoke only a PATH-resolved channel CLI name, never a path, shell, or interpreter."""
    if not isinstance(tool, str) or not _SAFE_CLI_NAME_RE.fullmatch(tool):
        die(f"mechanisms[{i}].tool must be a bare channel CLI executable name ending in '-cli' "
            "(for example lark-cli); paths, shells, interpreters, and generic executables are forbidden", 2)


def _validate_cmd_templates(m, i):
    """Static validation of command templates (im_cli only). Hard rules on the argv array + placeholder whitelist +
    per-template subsets + success structure — all die 2 (config typos fail earliest)."""
    has_text_tpl = m.get("send_template") is not None
    has_file_tpl = m.get("send_file_template") is not None
    if m.get("success") is not None and not (has_text_tpl or has_file_tpl):
        die(f"mechanisms[{i}] has success but no send_template/send_file_template — "
            "success is consumed together with the command-template mechanism; an im_cli without templates is invoked in the lark-cli default form, "
            "which carries its own JSON envelope check and does not consume the success field (config typo, please remove)", 2)
    if not has_text_tpl and not has_file_tpl:
        return
    for field, allowed in (("send_template", {"{tool}", "{target_id}", "{target_type}", "{text}"}),
                           ("send_file_template", {"{tool}", "{target_id}", "{target_type}", "{file}", "{display_name}"})):
        tpl = m.get(field)
        if tpl is None:
            continue
        if not isinstance(tpl, list) or not tpl or not all(isinstance(x, str) for x in tpl):
            die(f"mechanisms[{i}].{field} must be a non-empty array of strings (one argv element each) — "
                "the string form has a shell injection surface and message text with spaces/newlines would shatter; one element per argument, "
                "{text}/{file} occupies one whole element", 2)
        if tpl[0] != "{tool}":
            die(f"mechanisms[{i}].{field}[0] must be exactly {{tool}} — the locked channel CLI is the only executable; "
                "templates cannot select another program, shell, or interpreter", 2)
        for el in tpl:
            for tok in _CMD_TPL_WIDE_RE.findall(el):
                if tok not in CMD_TPL_PLACEHOLDERS:
                    die(f"mechanisms[{i}].{field} contains unknown placeholder {tok} (closed vocabulary: "
                        f"{'/'.join(sorted(allowed))}) — near-miss typos and unknown tokens are both rejected "
                        "(nothing to fill at RUN time; passed literally to the CLI)", 2)
                if tok not in allowed:
                    die(f"mechanisms[{i}].{field} placeholder {tok} does not belong to this template ({field} "
                        f"only allows {'/'.join(sorted(allowed))})", 2)
    scs = m.get("success")
    if (has_text_tpl or has_file_tpl) and scs is not None:
        if not isinstance(scs, dict) or scs.get("type") not in ("exit_code", "stdout_json"):
            got = scs.get("type") if isinstance(scs, dict) else repr(scs)[:60]
            die(f"mechanisms[{i}].success.type invalid: {got} (success must be an object; options are exit_code / stdout_json)", 2)
        if scs.get("type") == "stdout_json":
            if not scs.get("field"):
                die(f"mechanisms[{i}].success.type=stdout_json requires field (the field name in the stdout JSON "
                    "envelope that indicates success, e.g. errcode)", 2)
            # value must be given explicitly: if omitted, a missing field (None==None) would be misjudged as success — silent false success
            if scs.get("value") is None:
                die(f"mechanisms[{i}].success.type=stdout_json requires value (the success value of that field, "
                    "e.g. 0) — if omitted, CLI output missing the field would pass None==None and be misjudged as success", 2)


def _render_cmd_template(mech, field, text=None, file_name=None, display_name=None):
    """Template + mechanism params -> argv (placeholders substituted in one pass with no re-scan; {xxx} inside message text is never expanded twice)."""
    tpl = mech[field]
    vals = {
        "tool": mech["tool"],
        "target_id": mech["target"]["id"],
        "target_type": mech["target"].get("type", ""),
        "text": text if text is not None else "",
        "file": file_name if file_name is not None else "",
        "display_name": display_name if display_name is not None else "",
    }
    out = []
    for el in tpl:
        # Single-pass regex substitution: scan each original element once, never re-scan the substituted output —
        # {file}/{display_name} literals inside message text are not wiped by later token rounds
        out.append(_CMD_TPL_SUB_RE.sub(lambda m: str(vals[CMD_TPL_PLACEHOLDERS[m.group(0)]]), el))
    return out


def _run_cmd_with_success(mech, cmd, cwd=None):
    """Command template execution + success check. A non-zero exit code (exit_code type matches by value) always fails;
    a timeout counts as a network-class retry; other deterministic failures do not retry."""
    scs = mech.get("success") or {"type": "exit_code", "value": 0}

    def _try():
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=LARK_TIMEOUT_SECONDS, check=False, cwd=cwd)
        except FileNotFoundError:
            return ({"status": "error", "error": f"CLI missing: {mech['tool']}"
                     " (this mechanism is unavailable when the RUN sandbox lacks the CLI)"}), "cli_missing"
        except subprocess.TimeoutExpired:
            return ({"status": "error", "error": "CLI send timeout"}), "timeout"
        out = (proc.stdout or "")
        if scs["type"] == "exit_code":
            if proc.returncode == scs.get("value", 0):
                return {"status": "ok"}, None
            return ({"status": "error",
                     "error": f"CLI exit code {proc.returncode} ≠ {scs.get('value', 0)}: "
                              f"{(proc.stderr or out)[:300]}"}), "cli"
        # stdout_json: assuming exit code 0, the given field in the stdout JSON == value
        if proc.returncode != 0:
            return ({"status": "error", "error": f"CLI exit code {proc.returncode}: "
                     f"{(proc.stderr or out)[:300]}"}), "cli"
        js = out.find("{")
        if js < 0:
            return ({"status": "error", "error": f"CLI output is not JSON: {out[:200]}"}), "parse"
        try:
            payload = json.loads(out[js:])
        except json.JSONDecodeError:
            return ({"status": "error", "error": f"CLI output is invalid JSON: {out[:200]}"}), "parse"
        got = payload.get(scs["field"])
        if got == scs.get("value"):
            return {"status": "ok"}, None
        return ({"status": "error", "error": f"CLI envelope {scs['field']}={got!r} ≠ {scs.get('value')!r}: "
                 f"{out[:300]}"}), "biz"

    result, _err = _with_retry(_try, f"im_cli[{mech['tool']}]")
    return result


def load_spec(path):
    if not os.path.exists(path):
        die(f"spec not found: {path}", 2)
    with open(path, encoding="utf-8") as f:
        s = json.load(f)
    for k in ("task_name", "project_id", "project_name", "content", "delivery", "timezone"):
        if k not in s:
            die(f"spec missing required field: {k}", 2)
    c = s["content"]
    has_report = c.get("report") is not None
    kind = c.get("kind") or ("report" if has_report else "data")
    if kind not in ("data", "report"):
        die(f"content.kind invalid: {kind} (options are data / report)", 2)
    c["kind"] = kind
    if kind == "report":
        if not has_report:
            die("kind=report requires content.report (outline + template)", 2)
        # report.template vocabulary defines only string ids — non-strings (dict/int) should not silently degrade to a text report;
        # a default of None is legal (the later default is text; the doc promises "omitted means text report")
        if not isinstance(c["report"], dict) or \
                (c["report"].get("template") is not None
                 and not isinstance(c["report"].get("template"), str)):
            die("content.report.template must be a string (text/card/daily/weekly/monthly or inline HTML starting with <)", 2)
        # Static cap observation on LIMIT in report rows queries — a large LIMIT means feeding detail rows instead of aggregates,
        # data.json persistence would be truncated; BUILD time should guide a switch to the aggregate style (WARN not die — legitimate large-window trend queries are not punished)
        for i, q in enumerate(c.get("queries") or []):
            if q.get("mode") == "rows" and isinstance(q.get("sql_template"), str):
                mm = list(re.finditer(r"\bLIMIT\s+(\d+)", q["sql_template"], re.IGNORECASE))
                if mm and int(mm[-1].group(1)) > 5000:
                    log(f"[WARN] queries[{i}] ({q.get('label')}) LIMIT {mm[-1].group(1)} > 5000 — a report rows query "
                        f"feeding excessive detail rows; data.json will be truncated to {REPORT_ROWS_CAP} rows on persist; fix properly by switching to the aggregate style")
        # Report tasks consume content.message's preview_rows/max_message_kb — type validation cannot be waived
        # (a string message would raise a raw traceback AttributeError at render time, violating the die-2-no-raw-raise discipline)
        msg = c.get("message")
        if msg is not None and not isinstance(msg, dict):
            die("content.message must be an object {preview_rows?, max_message_kb?} (report tasks do not consume template, "
                "but they do consume preview_rows/max_message_kb — a string/number is a config typo)", 2)
        if isinstance(msg, dict):
            pr = msg.get("preview_rows")
            if pr is not None and (not isinstance(pr, int) or isinstance(pr, bool) or pr < 1):
                die(f"content.message.preview_rows invalid: {pr!r} (positive integer, default {PREVIEW_ROWS_DEFAULT})", 2)
    else:
        if has_report:
            die("kind=data must not configure content.report (report scenarios use kind=report)", 2)
        _validate_message(c)
        _validate_file(c)
    if not isinstance(c.get("queries"), list) or not c["queries"]:
        die("content.queries must be a non-empty array", 2)
    labels = []
    for i, q in enumerate(c["queries"]):
        if "label" not in q:
            die(f"content.queries[{i}] missing field: label", 2)
        lbl = q["label"]
        if lbl in labels:
            die(f"content.queries[{i}].label duplicate: {lbl} (placeholders are referenced by label and must be unique)", 2)
        if "." in str(lbl) or "{{" in str(lbl):
            die(f"content.queries[{i}].label must not contain '.' or '{{' (breaks placeholder parsing): {lbl}", 2)
        labels.append(lbl)
        q.setdefault("source", "sql")
        if q["source"] == "sql":
            if "sql_template" not in q:
                die(f"content.queries[{i}] source=sql missing field: sql_template", 2)
            # The SQL placeholder vocabulary is closed: {{...}} outside the vocabulary = an unsubstituted business placeholder (recipes template variables
            # such as {{aggregate_expr}}/{{project_id}}/{{filters}}/{{settle_tz}} must be substituted at BUILD time) —
            # a missed substitution would run empty daily and exit 1 at RUN time; caught statically (vocabulary = window placeholders actually consumed by render_sql)
            _sql_toks = set(re.findall(r"\{\{([a-z_]+)\}\}", q["sql_template"]))
            _bad_toks = _sql_toks - SQL_PLACEHOLDER_VOCAB
            if _bad_toks:
                die(f"content.queries[{i}].sql_template contains unsubstituted business placeholders: "
                    f"{{{{{'/'.join(sorted(_bad_toks))}}}}} — recipes template variables ({{aggregate_expr}}/"
                    f"{{project_id}}/{{filters}}/{{settle_tz}} etc.) must be replaced with actual values before locking the spec", 2)
        elif q["source"] == "dashboard_report":
            if "dashboard_id" not in q:
                die(f"content.queries[{i}] source=dashboard_report missing field: dashboard_id", 2)
            # value queries must name a unique report_id (otherwise the whole board is read with multiple reports merged, and v.<column> takes the first merged row — a wrong-data path)
            if q.get("mode", "value") == "value":
                rids = q.get("report_ids")
                if not isinstance(rids, list) or len(rids) != 1:
                    die(f"content.queries[{i}] source=dashboard_report with mode=value requires report_ids=[<unique report id>]"
                        "(value takes a single row from a single report; when merged reports yield >1 rows the first row is taken = wrong data)", 2)
        else:
            die(f"content.queries[{i}].source invalid: {q['source']}", 2)
        q.setdefault("mode", "value")   # default is value (the schema marks it optional)
        if q["mode"] not in ("value", "rows"):
            die(f"content.queries[{i}].mode invalid: {q['mode']} (options are value / rows)", 2)
        # chart enum validation (the schema declares line/bar) — invalid values previously rendered silently as line
        if q.get("chart") is not None and q.get("chart") not in ("line", "bar"):
            die(f"content.queries[{i}].chart invalid: {q['chart']} (options are line / bar)", 2)
        q.setdefault("on_empty", c.get("on_empty", "push"))
        q.setdefault("project_id", s["project_id"])
        file_detail = (c.get("file") or {}).get("detail_query") if isinstance(c.get("file"), dict) else None
        q.setdefault("fetch", "export" if file_detail == lbl else "run")
        if q["fetch"] not in ("run", "export"):
            die(f"content.queries[{i}].fetch invalid: {q['fetch']} (options are run / export)", 2)
        if file_detail == lbl and q["source"] != "sql":
            die(f"content.file.detail_query={lbl} only supports source=sql (file export goes through the SQL engine)", 2)
        if file_detail == lbl and q["mode"] != "rows":
            die(f"content.file.detail_query={lbl} must be mode=rows", 2)
        # summary aggregation declaration (decision point a: computed by the engine over all detail rows)
        sm = q.get("summary")
        if sm is not None:
            if not isinstance(sm, list) or not sm:
                die(f"content.queries[{i}].summary must be a non-empty array [{column, agg, name}]", 2)
            seen_names = set()
            for j, e in enumerate(sm):
                if not isinstance(e, dict) or "agg" not in e or "name" not in e:
                    die(f"content.queries[{i}].summary[{j}] missing fields: agg / name", 2)
                if e["agg"] not in AGG_KINDS:
                    die(f"content.queries[{i}].summary[{j}].agg invalid: {e['agg']} (options are {AGG_KINDS})", 2)
                if e["agg"] != "count" and not e.get("column"):
                    die(f"content.queries[{i}].summary[{j}] agg={e['agg']} requires column (the detail column name)", 2)
                if e["name"] in seen_names:
                    die(f"content.queries[{i}].summary[{j}].name duplicate: {e['name']}", 2)
                seen_names.add(e["name"])
    # Cross-query agg-name dedup: same-name aggregates silently shadow earlier ones -> global dedup, fail loud
    global_agg_names = {}
    for i, q in enumerate(c["queries"]):
        for e in q.get("summary") or []:
            nm = e["name"]
            if nm in global_agg_names:
                first = global_agg_names[nm]
                die(f"Agg name duplicated across queries: {nm} (queries[{first}] and queries[{i}]"
                    " — placeholders are referenced by name; a duplicate name silently shadows)", 2)
            global_agg_names[nm] = i
    # Window frequency (authoritative field: decides data-window splitting; at BUILD time it must match the automation schedule)
    # rolling:N rolling window (the last N complete days up to yesterday) — a first-class expression for "push the last 7 days of data daily" scenarios:
    # the stats window/title shows the full range (09-30~10-06); SQL uses {{window_start}}/{{window_end}} instead of hand-built dates
    _wf = c.get("window_freq")
    if _wf in ("daily", "weekly", "hourly", "monthly"):
        pass
    elif isinstance(_wf, str) and re.fullmatch(r"rolling:(\d+)", _wf):
        if not (2 <= int(_wf.split(":")[1]) <= 90):
            die(f"content.window_freq invalid: {_wf} (rolling:N takes 2~90 complete days — longer spans use monthly aggregation)", 2)
    else:
        die("content.window_freq is required and must be daily/weekly/hourly/monthly/rolling:N"
            "(daily=yesterday / weekly=last week / hourly=previous hour / monthly=last month / rolling:N=the last N complete days up to yesterday)", 2)
    # rolling-window SQL must contain {{window_start}}/{{window_end}} (same shape as the weekly/monthly guard —
    # misusing {{date}} only counts the window's start day, silently turning 7 days into 1; only sql-source queries are constrained, dashboard sources manage their own date params)
    if isinstance(_wf, str) and re.fullmatch(r"rolling:(\d+)", _wf):
        for i, q in enumerate(c.get("queries") or []):
            sqlt = q.get("sql_template") or ""
            if q.get("source", "sql") == "sql" and \
                    ("{{window_start}}" not in sqlt or "{{window_end}}" not in sqlt):
                die(f"queries[{i}].sql_template: a rolling window requires {{{{window_start}}}}/{{{{window_end}}}}"
                    "(start/end of the last N days — misusing {{{{date}}}} only counts the window's start day)", 2)
    # Report section
    rep = c.get("report")
    if rep is not None:
        if not isinstance(rep.get("outline"), list) or not rep["outline"]:
            die("content.report.outline must be a non-empty array", 2)
        seen_sids = set()
        labels = [q["label"] for q in c.get("queries") or []]
        for i, sec in enumerate(rep["outline"]):
            for k in ("section_id", "title"):
                if k not in sec:
                    die(f"content.report.outline[{i}] missing field: {k}", 2)
            # section_id dedup (slots align by it; duplicates silently shadow each other) +
            # data_labels reference validation (a reference to a nonexistent label is silently skipped at render — same standard as the
            # inline-template {{data:*}} static validation; typos are caught at BUILD time instead of silently missing a table at render)
            sid = str(sec["section_id"])
            if sid in seen_sids:
                die(f"content.report.outline[{i}].section_id duplicate: {sid} (slot keys align by it and must be unique)", 2)
            seen_sids.add(sid)
            for lbl in sec.get("data_labels") or []:
                if lbl not in labels:
                    die(f"content.report.outline[{i}].data_labels references a nonexistent query section: {lbl}"
                        f"(existing labels: {sorted(labels)} — this section would render without a data table; caught statically)", 2)
        tpl = rep.get("template")
        if tpl is None:
            rep["template"] = "text"   # text report: template default = text
        elif isinstance(tpl, str) and tpl not in ("text", "card", "daily", "weekly", "monthly") \
                and not tpl.strip().startswith("<"):
            die(f"content.report.template invalid: {tpl[:60]} (text / card / daily / weekly / monthly, or an inline template starting with '<')", 2)
    # Delivery mechanism section
    if kind == "report" and c.get("file") is not None:
        if not isinstance(c["file"], dict):
            die("content.file must be an object {name_template} for HTML report attachments", 2)
        if c["file"].get("name_template") is not None:
            _validate_artifact_name(c["file"]["name_template"], "content.file.name_template")
    d = s["delivery"]
    if d.get("file_name") is not None:
        _validate_artifact_name(d["file_name"], "delivery.file_name")
    mechs = d.get("mechanisms")
    if not isinstance(mechs, list) or not mechs:
        die("delivery.mechanisms must be a non-empty array", 2)
    file_capable = 0
    card_capable = 0
    for i, m in enumerate(mechs):
        kindm = m.get("mechanism")
        # Cross-channel backup group identifier — a non-empty string (same group: first success wins; across groups: broadcast).
        # Leading/trailing whitespace is normalized at lock time — without normalization " g1 " and "g1" would be two group keys (silently becoming broadcast double-send)
        if "group" in m:
            if not isinstance(m.get("group"), str) or not str(m.get("group")).strip():
                die(f"mechanisms[{i}].group must be a non-empty string (cross-channel backup group: same-group mechanisms back each other up; first success wins)", 2)
            m["group"] = m["group"].strip()
        # Sender identity = an inherent property of the mechanism (im_cli is always the user identity, webhook is the bot identity), not configured separately —
        # the mechanisms[].as field is deprecated (removed from schema/script/example in sync); this rule applies uniformly before the mechanism branches:
        # any mechanism entry containing as is rejected (previously only the im_cli branch caught it, webhook leftovers only fell to a field-reconciliation WARN — misaligned with the schema's "present means invalid")
        if "as" in m:
            die(f"mechanisms[{i}].as is deprecated (sender identity follows the mechanism: im_cli=user identity always user, webhook=bot identity, not configured separately)", 2)
        if kindm == "im_cli":
            if not m.get("tool") or not isinstance(m.get("target"), dict) \
                    or not m["target"].get("id") or m["target"].get("type") not in ("chat", "user"):
                die(f"mechanisms[{i}] im_cli requires tool + target{{type: chat|user, id}}", 2)
            _validate_cli_tool(m.get("tool"), i)
            _validate_cmd_templates(m, i)
            _tpl = m.get("send_template") is not None
            if m.get("file_ok"):
                if _tpl and m.get("send_file_template") is None:
                    log(f"[WARN] mechanisms[{i}] has send_template but no send_file_template — "
                        "file delivery cannot run (file_ok invalidated; this mechanism does not count toward file capability)")
                    m["file_ok"] = False  # invalid means invalid: keeping the field would invoke a custom CLI in lark form at RUN time and fail every period
                else:
                    file_capable += 1
            if not _tpl:
                card_capable += 1  # cards are implemented only for the lark-cli default form (the command-template mechanism covers only text+file)
                if m.get("tool") != "lark-cli":
                    die(f"mechanisms[{i}].tool={m.get('tool')} is not lark-cli and has no send_template — "
                        "only lark-cli supports the built-in argument form; configure a command template for another channel CLI", 2)
        elif kindm == "webhook":
            if m.get("webhook_kind") not in ("wecom", "dingtalk", "feishu", "custom_webhook"):
                die(f"mechanisms[{i}].webhook_kind invalid: {m.get('webhook_kind')}", 2)
            if not m.get("webhook_url"):
                die(f"mechanisms[{i}] webhook missing webhook_url", 2)
            # Command-template fields are consumed only by im_cli — presence in the webhook branch is a config typo (fail earliest;
            # silently passing it would make the Agent believe the template is in effect while delivery actually goes through a direct webhook send)
            for fld in ("send_template", "send_file_template", "success"):
                if m.get(fld) is not None:
                    die(f"mechanisms[{i}].{fld} is consumed only by the im_cli mechanism (command-template mechanism) — "
                        "webhook delivery does not go through a CLI invocation; config typo, please remove", 2)
            if m.get("webhook_kind") == "wecom" and m.get("file_ok"):
                file_capable += 1
            elif m.get("webhook_kind") != "wecom" and m.get("file_ok"):
                # Non-wecom webhook file paths are always rejected at RUN time as "file capability unverified" — caught statically,
                # otherwise every period the text is delivered and then a file failure is recorded, exiting 3 (a dead-loop failure released to RUN)
                die(f"mechanisms[{i}] webhook_kind={m.get('webhook_kind')} has no file capability"
                    "(attachment delivery is verified only for wecom upload_media) — remove file_ok=true", 2)
            if m.get("webhook_kind") == "feishu":
                card_capable += 1  # card 2.0 + VChart/table components verified in practice
        else:
            die(f"mechanisms[{i}].mechanism invalid: {kindm} (options are im_cli / webhook)", 2)
    # File tasks / HTML reports: at least one file_ok mechanism (attachment delivery currently implements only the im_cli / wecom webhook paths)
    # HTML report attachments are always produced — if the message previews "see attachment" but there is no file_ok mechanism, a real push would send the message first and then fail to deliver the attachment, exiting 3 (dangling); caught statically
    # text/card reports produce no attachments — content.file is valid in report tasks only for HTML templates (attachment naming),
    # a leftover file section + a text/card template = a config typo (e.g. copied from an HTML report spec and not fully deleted); caught precisely at static time (fail earliest)
    html_report = (kind == "report" and c.get("report") is not None
                   and (c["report"].get("template", "text") in ("daily", "weekly", "monthly")
                        or str(c["report"].get("template", "")).strip().startswith("<")))
    if kind == "report" and not html_report and isinstance(c.get("file"), dict):
        die("report tasks with template=text/card must not configure content.file (this field is valid only for kind=data (file delivery) and "
            "HTML reports (attachment naming) — remove the extra section; for the attachment form switch to daily/weekly/monthly or an inline HTML template)", 2)
    if (isinstance(c.get("file"), dict) or html_report) and file_capable == 0:
        die("At least one mechanism with file_ok=true is required: " + ("file task" if isinstance(c.get("file"), dict) else "HTML report (attachments always produced)")
            + ". Note: webhook file delivery currently implements only wecom — configure an im_cli mechanism (BUILD-time file test delivery) or a wecom webhook"
            + " (text/card reports produce no attachments and are exempt)", 2)
    # Card template: at least one card-capable mechanism (an implementation-capability check, not a channel capability matrix)
    tpl_obj = (c.get("message") or {}).get("template") if kind == "data" else None
    is_card_tpl = isinstance(tpl_obj, dict) or tpl_obj in ("builtin:card_chart", "builtin:card_table")
    # The report card template (report.template="card") likewise requires a card-capable mechanism — the message body itself is a card, with no attachment form
    if kind == "report" and c.get("report", {}).get("template") == "card":
        is_card_tpl = True
    if is_card_tpl and card_capable == 0:
        die("Card templates require at least one im_cli or feishu webhook mechanism (cards are not implemented on other channels; switch to the text form at BUILD time)", 2)
    s.setdefault("auto_push", False)
    c.setdefault("max_message_kb", 8)
    if not isinstance(c.get("max_message_kb"), (int, float)) or c["max_message_kb"] <= 0:
        die(f"content.max_message_kb invalid: {c.get('max_message_kb')!r} (positive number, unit KB, default 8 — "
            f"0/negative would trim the message down to just the footer)", 2)
    s.setdefault("cli", "ae-cli")
    s.setdefault("env", {})
    # timezone (multi_tz gate; true requires offset, false means no timezone concept)
    tz = s["timezone"]
    if "multi_tz" not in tz or not isinstance(tz.get("multi_tz"), bool):
        die("timezone.multi_tz is required and must be bool (= project info get → time_zone_enabled)", 2)
    if tz.get("multi_tz"):
        off = tz.get("offset")
        if off is None:
            die("with multi_tz=true, timezone.offset is required (settlement timezone; user-confirmed or the project default default_time_zone_offset)", 2)
        if not isinstance(off, (int, float)) or isinstance(off, bool):
            die(f"timezone.offset must be a numeric UTC hour offset (e.g. 8 / 5.5), got: {off!r}", 2)
        if not (-12 <= off <= 14):
            die(f"timezone.offset must be a UTC hour offset in -12~14 (real-world timezone extremes), got: {off!r}", 2)
    else:
        tz.pop("offset", None)   # offset is not consumed when false (no timezone concept)
        # server_tz = the server timezone locked at BUILD time (numeric hour offset); RUN time prefers the spec value for day splitting
        stz = tz.get("server_tz")
        if stz is not None and (not isinstance(stz, (int, float)) or isinstance(stz, bool) or not (-12 <= stz <= 14)):
            die(f"timezone.server_tz must be a numeric UTC hour offset in -12~14 (locked at BUILD time from the +list-automations "
                f"scheduleTimeZone conversion), got: {stz!r}", 2)
    # title_template (report title) closed vocabulary: the consumption point substitutes {{task_name}}/{{date}}/{{window_range}}; other tokens pass through literally (see the placeholder row in the schema).
    # Validated only for kind=report — data tasks do not consume this field (the rendered title is hardcoded); if filled it is an informational slot (validation must align with consumption)
    tt = c.get("title_template")
    if tt and kind == "report":
        for m in PLACEHOLDER_RESIDUE_RE.finditer(tt):
            if m.group(0) not in ("{{task_name}}", "{{date}}", "{{window_range}}"):
                die(f"title_template contains an out-of-vocabulary placeholder {m.group(0)}"
                    "(the title vocabulary is only {{{{task_name}}}} / {{{{date}}}} / {{{{window_range}}}})", 2)
    # Static placeholder reference validation (reference existence, exit code 2; channel feasibility relies on BUILD-time test-delivery flags and is not validated here)
    if kind == "data":
        _validate_template_refs(c)
    else:
        # Inline HTML report template {{slot:*}}/{{data:*}} references are also validated statically —
        # previously caught only at render time via [unmatched slot]+WARN (exposed only after the artifact was generated); --check-spec now catches it at BUILD time
        _validate_report_template_refs(c)
    # Spec field consumption reconciliation: fields outside the list get a WARN (an early-warning surface for doc-script drift)
    _audit_spec_fields(s)
    return s


def _validate_message(c):
    msg = c.get("message")
    if not isinstance(msg, dict):
        die("content.message is required: {template: <built-in name|inline template>, preview_rows?}", 2)
    tpl = msg.get("template")
    if tpl is None:
        die("content.message.template is required (built-in name builtin:plain/rich/card_chart/card_table, "
            "or an inline custom template: text skeleton string / card {kind: card_2.0, ...})", 2)
    if isinstance(tpl, str):
        if tpl not in BUILTIN_TEMPLATES and len(tpl.strip()) == 0:
            die("content.message.template is an empty string (built-in name or non-empty text skeleton)", 2)
        if tpl.startswith("builtin:") and tpl not in BUILTIN_TEMPLATES:
            die(f"Built-in template name misspelled: {tpl} (available: {BUILTIN_TEMPLATES}; the report form uses content.kind=report, "
                "not message.template)", 2)
    elif isinstance(tpl, dict):
        if tpl.get("kind") != "card_2.0":
            die(f"Inline template kind invalid: {tpl.get('kind')} (currently supports card_2.0; for a plain-text custom template use a string skeleton directly)", 2)
    else:
        die(f"content.message.template type invalid: {type(tpl).__name__} (string built-in name/text skeleton, or object card skeleton)", 2)
    pr = msg.get("preview_rows")
    if pr is not None and (not isinstance(pr, int) or isinstance(pr, bool) or pr < 1):
        die(f"content.message.preview_rows invalid: {pr!r} (positive integer, default {PREVIEW_ROWS_DEFAULT})", 2)


def _validate_artifact_name(name, field):
    """Artifact names are leaf filenames. Reject paths early; _safe_output_path repeats the boundary check at write time."""
    if not isinstance(name, str) or not name.strip():
        die(f"{field} must be a non-empty filename", 2)
    if name in (".", "..") or os.path.basename(name) != name or "/" in name or "\\" in name or "\x00" in name:
        die(f"{field} must be a filename in the task working directory, not an absolute or relative path: {name!r}", 2)


def _safe_output_path(base_dir, name, field):
    """Resolve one artifact below base_dir and reject traversal/symlink escapes before opening it."""
    _validate_artifact_name(name, field)
    base_real = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base_real, name))
    try:
        inside = os.path.commonpath((base_real, candidate)) == base_real
    except ValueError:
        inside = False
    if not inside or candidate == base_real:
        die(f"{field} resolves outside the task working directory: {name!r}", 2)
    return candidate


def _default_report_filename(task_name, date_str):
    safe_task = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(task_name)).strip(" ._") or "report"
    return f"{safe_task}_{date_str}.html"


def _validate_file(c):
    f = c.get("file")
    if f is None:
        return
    if not isinstance(f, dict):
        die("content.file must be an object {name_template, detail_query}", 2)
    if not f.get("name_template"):
        die("content.file.name_template is required (supports the {date} placeholder = window start date)", 2)
    _validate_artifact_name(f["name_template"], "content.file.name_template")
    if not f.get("detail_query"):
        die("content.file.detail_query is required (points to the label of one mode=rows sql query)", 2)
    labels = [q["label"] for q in c.get("queries") or []]
    if f["detail_query"] not in labels:
        die(f"content.file.detail_query={f['detail_query']} does not appear among the queries labels (static validation)", 2)


def _validate_template_refs(c):
    """Static validation (reference existence + closed vocabulary): the query labels / summary agg names referenced by
    template placeholders must exist in the spec; out-of-vocabulary placeholders ({{...}} tokens PLACEHOLDER_RE cannot match)
    always die 2 — prevents mistakenly filling SQL-only placeholders such as {{week_start}} that would pass literally
    (see the schema placeholder row). Column-level references (v.<column>) are run-time only; failure -> exit code 2. (title_template vocabulary is validated in load_spec — report tasks skip this function.)"""
    tpl = c["message"]["template"]
    strings = []
    if isinstance(tpl, str):
        if tpl in BUILTIN_TEMPLATES:
            return   # built-in templates consume all queries, no reference issues
        strings = [tpl]
    else:
        def _walk(node):
            if isinstance(node, dict):
                for v in node.values():
                    _walk(v)
            elif isinstance(node, list):
                for v in node:
                    _walk(v)
            elif isinstance(node, str):
                strings.append(node)
        _walk(tpl)
    labels = {q["label"] for q in c["queries"]}
    agg_names = set()
    for q in c["queries"]:
        for e in q.get("summary") or []:
            agg_names.add(e["name"])
    for s_ in strings:
        for m in PLACEHOLDER_RESIDUE_RE.finditer(s_):
            if not PLACEHOLDER_RE.fullmatch(m.group(0)):
                die(f"message template contains an out-of-vocabulary placeholder {m.group(0)}"
                    "(closed vocabulary in push-spec-schema.md \"Placeholder Vocabulary\" — week/month placeholders are for SQL templates only)", 2)
        for m in PLACEHOLDER_RE.finditer(s_):
            key = m.group(1)
            if key.startswith("q."):
                rest = key[2:]
                label, _, tail = rest.partition(".")
                if label not in labels:
                    die(f"template placeholder references a nonexistent query section: {{{{{key}}}}} (queries labels: {sorted(labels)})", 2)
                if tail not in ("rows", "long", "n") and not tail.startswith("v."):
                    die(f"template placeholder data binding invalid: {{{{{key}}}}} (available: .rows / .long / .n / .v.<column name>)", 2)
            elif key.startswith("agg."):
                name = key[4:]
                if name not in agg_names:
                    die(f"template placeholder references a nonexistent agg name: {{{{{key}}}}} (names declared in summary: {sorted(agg_names)})", 2)


def _validate_report_template_refs(c):
    """Static reference validation for the report inline HTML template (symmetric to the data task's _validate_template_refs):
    {{slot:<section_id>}} must be in the outline sections and {{data:<label>}} must be in the queries labels —
    a nonexistent reference -> die 2. Full document template titles/banners may contain other {{...}} vocabulary
    (render-time [unmatched slot]+WARN as fallback); this validation only governs the two structural reference kinds slot/data (a wrong reference = a wrong outline/data binding, i.e. an invalid configuration)."""
    rep = c["report"]
    tpl = rep.get("template")
    if not (isinstance(tpl, str) and tpl.strip().startswith("<")):
        return
    section_ids = {sec["section_id"] for sec in rep.get("outline") or []}
    labels = {q["label"] for q in c.get("queries") or []}
    for m in re.finditer(r"\{\{slot:([^{}]+)\}\}", tpl):
        # Exact raw-text comparison (no strip) — render replaces "{{slot:<id>}}" exactly; whitespace after the colon
        # would pass statically and land on [unmatched slot] at render; static and render share the same standard, whitespace is caught at BUILD time
        if m.group(1) not in section_ids:
            die(f"report template {{{{slot:{m.group(1)}}}}} references a nonexistent outline section_id (existing: {sorted(section_ids)}; "
                "no whitespace allowed after the placeholder colon — render matches the raw text exactly)", 2)
    for m in re.finditer(r"\{\{data:([^{}]+)\}\}", tpl):
        if m.group(1) not in labels:
            die(f"report template {{{{data:{m.group(1)}}}}} references a nonexistent query section label (existing: {sorted(labels)}; "
                "no whitespace allowed after the placeholder colon — render matches the raw text exactly)", 2)


def _audit_spec_fields(s):
    """Fields present in the spec but unknown to the script (not registered) -> WARN (reconciliation lists in _KNOWN_*)"""
    unknown = []
    for k in s:
        if k not in _KNOWN_TOP:
            unknown.append(k)
    c = s["content"]
    for k in c:
        if k not in _KNOWN_CONTENT:
            unknown.append(f"content.{k}")
    for i, q in enumerate(c["queries"]):
        for k in q:
            if k not in _KNOWN_QUERY:
                unknown.append(f"content.queries[{i}].{k}")
    rep = c.get("report")
    if isinstance(rep, dict):
        for k in rep:
            if k not in _KNOWN_REPORT:
                unknown.append(f"content.report.{k}")
    for i, m in enumerate(s["delivery"]["mechanisms"]):
        for k in m:
            if k not in _KNOWN_MECH:
                unknown.append(f"delivery.mechanisms[{i}].{k}")
    for k in s["delivery"]:
        if k not in _KNOWN_DELIVERY:
            unknown.append(f"delivery.{k}")
    for k in s["timezone"]:
        if k not in _KNOWN_TZ:
            unknown.append(f"timezone.{k}")
    if unknown:
        log(f"[WARN] spec contains fields not registered in the script (check the field tables in push-spec-schema.md): {', '.join(unknown)}")


# ---------- Window computation (push side: the last complete period; no today_to_now; timezone model) ----------
_COMMON_TZ_OFFSETS = {"Asia/Shanghai": 8, "UTC": 0, "Asia/Tokyo": 9, "Asia/Hong_Kong": 8,
                      "Asia/Singapore": 8, "America/New_York": -5, "Europe/London": 0,
                      "Asia/Seoul": 9, "Asia/Taipei": 8, "Asia/Macau": 8, "Asia/Bangkok": 7,
                      "Asia/Kolkata": 5.5, "Asia/Dubai": 4, "Asia/Karachi": 5,
                      "Europe/Berlin": 1, "Europe/Paris": 1, "Europe/Moscow": 3,
                      "America/Los_Angeles": -8, "America/Chicago": -6, "America/Sao_Paulo": -3,
                      "Australia/Sydney": 10, "Australia/Perth": 8, "Pacific/Auckland": 12}


def _server_tz_offset_hours(spec):
    """Server timezone (the day-splitting basis when multi_tz=false = the scheduling calendar).
    Authoritative read: +list-automations → serverUtcOffset (a platform field shaped like "UTC+08:00" —
    more direct than scheduleTimeZone+ZoneInfo parsing, and it unifies UTC-offset semantics, removing the IANA-name/DST parsing layer);
    when serverUtcOffset is missing, fall back to scheduleTimeZone+static mapping; on failure WARN and fall back to +8.
    The sandbox container's date is UTC; never use it as a basis (lesson from practice)."""
    cli = _cli_path(spec)
    try:
        out = _run_cli([cli, "agent", "+list-automations", "--limit", "1", "--format", "json"],
                       30, "reading server timezone")
        payload = _parse_cli_json(out, "reading server timezone")
        items = (payload.get("data") or {}).get("items") or []
        it = items[0] if items else {}
        s_off = it.get("serverUtcOffset")
        if isinstance(s_off, str):
            # Relaxed shape (UTC+8 without minutes / UTC+08 / GMT prefix — the strict two-digit-colon version
            # would silently fall back on non-canonical shapes; only UTC+08:00 has been seen in this environment, coverage relies on the relaxed fallback)
            m = re.match(r"(?:UTC|GMT)([+-])(\d{1,2})(?::(\d{2}))?", s_off.strip())
            if m:
                sign = 1 if m.group(1) == "+" else -1
                mins = int(m.group(3)) if m.group(3) else 0
                return sign * (int(m.group(2)) + mins / 60.0), s_off.strip()
            log(f"[WARN] serverUtcOffset has an unexpected shape: {s_off} — falling back to the scheduleTimeZone mapping")
        name = it.get("scheduleTimeZone")
        if name in _COMMON_TZ_OFFSETS:
            return _COMMON_TZ_OFFSETS[name], name
        log(f"[WARN] server timezone read is empty or unparseable (serverUtcOffset/scheduleTimeZone: "
            f"{s_off!r}/{name!r}) — falling back to UTC+8 for day splitting")
    except Exception as e:
        log(f"[WARN] server timezone read failed ({e}) — falling back to UTC+8 for day splitting")
    return 8, None


def _window_range_str(freq, window_str):
    """Window-range display string (used for titles/stats-window rows — weekly/monthly show the full "start~end" range,
    not just the start day — avoids being misread as single-day data; daily = a single day, same value as {{date}}; hourly = a time window).
    Parsed from the canonical window_str form "YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM"; a single source consumed in two places (Ctx / report title)."""
    a, _, b = window_str.partition("~")
    a, b = a.strip(), b.strip()
    if not b:
        return a.split(" ")[0]
    if freq == "hourly":
        # A window crossing midnight (b date != a date) must carry b's date — "23:00~00:00" alone cannot tell whether it ends at 24:00 of the same day or 00:00 of the next day
        b_d, _, b_t = b.partition(" ")
        if not b_t:
            return f"{a}~{b}"
        if b_d and b_d != a.split(" ")[0]:
            return f"{a}~{b}"
        return f"{a}~{b_t}"
    if freq in ("weekly", "monthly", "rolling") or (
            isinstance(freq, str) and re.fullmatch(r"rolling:(\d+)", freq)):
        # weekly/monthly/rolling: show the full "start~end" range (against misreading; end = the day before the exclusive boundary = the last day included)
        # rolling tolerates a bare "rolling" string (the canonical value is rolling:N; the defensive fallback takes the same branch)
        bd = b.split(" ")[0]
        try:
            end_last = (datetime.datetime.strptime(bd, "%Y-%m-%d") - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            end_last = bd
        return f"{a.split(' ')[0]}~{end_last}"
    return a.split(" ")[0]


def compute_window(spec, anchor_date=None):
    """Compute the window by window_freq. anchor_date (--window-date backfill anchor, optional) = recompute the
    "last complete period" from that day's 00:00 viewpoint — backfilling yesterday's daily report by passing today,
    daily/hourly always holds; weekly/monthly/rolling backtrack by the same rule with the anchor day as now (hourly = the previous whole hour
    from the anchor day's 00:00 viewpoint = the previous day's 23:00~24:00, the same mental model as daily's "backfill yesterday, pass today", and any anchor is always a completed window)."""
    tz = spec["timezone"]
    if tz.get("multi_tz"):
        off = float(tz["offset"])
    elif tz.get("server_tz") is not None:
        # Server timezone locked at BUILD time (hour offset) — RUN time does not read +list-automations,
        # removing the "cannot read, fall back to +8 -> silently wrong window on overseas deployments" dependency
        off = float(tz["server_tz"])
        log(f"window day-splitting frame = server timezone locked in spec UTC{off:+g} (read at BUILD time; RUN time does not depend on runtime)")
    else:
        # old spec compatibility: no server_tz field -> read at runtime (on failure WARN and fall back to +8 — correct only when the cluster is +8)
        off, tzname = _server_tz_offset_hours(spec)
        log(f"window day-splitting frame = server calendar (multi_tz=false, tz={tzname or 'UTC+8 fallback'} — "
            f"spec does not lock server_tz; new BUILDs should lock this field)")
    freq = spec["content"]["window_freq"]
    try:
        tzinfo = datetime.timezone(datetime.timedelta(hours=off))
    except Exception:
        die(f"window timezone offset invalid: {off}", 2)
    now = datetime.datetime.now(tzinfo)
    if anchor_date is not None:
        # Backfill anchor: recompute from the anchor day's 00:00 viewpoint (hourly = the previous day's 23:00~24:00 — backfill
        # the last period of last evening by passing today, same mental model as daily; all non-hourly frequencies floor to the day boundary, and the 00:00 viewpoint equals the 23:59:59 viewpoint)
        now = datetime.datetime.combine(anchor_date, datetime.time(0, 0, 0), tzinfo=tzinfo)
    if freq == "hourly":
        # previous whole hour: end = the current whole hour (minutes/seconds zeroed), start = 1h back — depends on the run moment,
        # mistakenly writing now.replace(hour=0) would always take "yesterday 23:00~24:00" regardless of the time of day
        end = now.replace(minute=0, second=0, microsecond=0)
        start = end - datetime.timedelta(hours=1)
    elif freq == "weekly":
        days_since_monday = now.weekday()
        end = (now - datetime.timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - datetime.timedelta(days=7)
    elif freq == "monthly":
        # monthly window = the last complete calendar month (the 1st 00:00 ~ this month's 1st 00:00)
        first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = first_this_month
        start = (first_this_month - datetime.timedelta(days=1)).replace(day=1)
    elif isinstance(freq, str) and re.fullmatch(r"rolling:(\d+)", freq):
        # rolling window = the last N complete days up to yesterday (end = today's 00:00 exclusive boundary, start = end - N days)
        # "push the last 7 days daily" scenarios: the window rolls with the daily schedule; the stats window/title show the full range via _window_range_str
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - datetime.timedelta(days=int(freq.split(":")[1]))
    else:  # daily
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - datetime.timedelta(days=1)
    target_date = start.strftime("%Y-%m-%d")
    return start, end, target_date


def _strip_sql_comments(sql):
    """Strip SQL comments (`--` line comments / `/*...*/` block comments; quoted text untouched).
    Used for per-branch UNION splitting — a UNION inside a comment would split wrongly (valid SQL falsely reported as die 2),
    and unpaired parentheses inside a comment would drive the depth count negative (a real UNION missed -> per-branch checks fail)."""
    out = []
    i, n = 0, len(sql)
    in_str = None
    while i < n:
        ch = sql[i]
        if in_str:
            out.append(ch)
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"', '`'):
            in_str = ch
            out.append(ch)
            i += 1
            continue
        if ch == '-' and sql[i:i + 2] == '--':
            j = sql.find("\n", i)
            i = n if j < 0 else j   # strip to end of line (keep the newline)
            continue
        if ch == '/' and sql[i:i + 2] == '/*':
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split_union_segments(sql):
    """Top-level UNION splitting (paren depth + quote scanning) — a UNION inside a nested subquery is internal structure of a single branch, not split.
    Used for the $part_date per-branch check (verified in practice: the platform only checks whether the whole SQL contains $part_date and does not block a single missing branch — this script blocks it here)."""
    segs, start, depth = [], 0, 0
    i, n = 0, len(sql)
    in_str = None
    while i < n:
        ch = sql[i]
        if in_str:
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"', '`'):
            in_str = ch
            i += 1
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif depth == 0:
            m = re.match(r"UNION\s+(ALL\s+)?(DISTINCT\s+)?", sql[i:], re.IGNORECASE)
            if m:
                segs.append(sql[start:i])
                i += len(m.group(0))
                start = i
                continue
        i += 1
    segs.append(sql[start:])
    return segs


def render_sql(sql_template, start, end, target_date, is_weekly, is_monthly=False):
    sql = sql_template
    if is_weekly and ("{{week_start}}" not in sql or "{{week_end}}" not in sql) \
            and ("{{window_start}}" not in sql or "{{window_end}}" not in sql):
        die("weekly window requires sql_template to contain {{week_start}}/{{week_end}} or {{window_start}}/{{window_end}}"
            "(timestamp-column scenario, symmetric with monthly; misusing {{date}} only counts last Monday)", 2)
    if not is_weekly and ("{{week_start}}" in sql or "{{week_end}}" in sql):
        die("sql_template contains {{week_start}}/{{week_end}} but window_freq is not weekly (week placeholders are for week windows only, preventing a silently wrong window)", 2)
    # Two-way month placeholder guard (same shape as the week guard — missing any month placeholder with no window alternative means die 2;
    # the old and-combination only errored when all four placeholders were missing, a missing {{month_end}} would silently allow an unbounded scan)
    if is_monthly and ("{{month_start}}" not in sql or "{{month_end}}" not in sql) \
            and ("{{window_start}}" not in sql or "{{window_end}}" not in sql):
        die("monthly window requires sql_template to contain {{month_start}}/{{month_end}} or {{window_start}}/{{window_end}}"
            "(same shape as the week guard — misusing {{date}} or omitting the month upper bound only counts the 1st of last month / scans without an upper bound)", 2)
    if ("{{month_start}}" in sql or "{{month_end}}" in sql) and not is_monthly:
        die("sql_template contains {{month_start}}/{{month_end}} but window_freq is not monthly (month placeholders are for month windows only, preventing a silently wrong window)", 2)
    sql = sql.replace("{{date}}", target_date)
    sql = sql.replace("{{window_start}}", start.strftime("%Y-%m-%d %H:%M:%S"))
    sql = sql.replace("{{window_end}}", end.strftime("%Y-%m-%d %H:%M:%S"))
    sql = sql.replace("{{month_start}}", start.strftime("%Y-%m-%d"))
    sql = sql.replace("{{month_end}}", (end - datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
    if is_weekly:
        sql = sql.replace("{{week_start}}", start.strftime("%Y-%m-%d"))
        sql = sql.replace("{{week_end}}", (end - datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
    residue = PLACEHOLDER_RESIDUE_RE.search(sql)
    if residue:
        die(f"SQL template has a residual unsubstituted placeholder: {residue.group(0)}", 2)
    # SQL key rules intercepted before execution (previously only a doc convention relying on the Agent — $part_date is now platform-enforced,
    # SELECT * and event tables missing $part_date (including per-UNION-branch) are backstopped by the script; LIMIT truncation risk WARNs on both the run/export paths)
    if re.search(r"\bSELECT\s+\*", sql, re.IGNORECASE):
        die("SQL contains SELECT * (banned by core rule (3) — columns not declared explicitly, output column names are unpredictable, template v.<column>/summary.column cannot be reconciled)", 2)
    # Verified in practice: the platform's $part_date enforcement only checks whether the whole SQL contains it; a single UNION branch missing it is silently allowed (full table scan + wrong metric definition) —
    # intercepted here per branch: after top-level UNION splitting, every branch containing an event table must carry its own $part_date predicate
    # The per-branch check runs on the comment-stripped SQL — a UNION inside a comment would split wrongly, unpaired parentheses inside a comment would miss a split;
    # the check uses the stripped version, while what actually executes is still the original SQL (comments are harmless to the platform)
    for si, seg in enumerate(_split_union_segments(_strip_sql_comments(sql)), 1):
        if "ta.v_event" in seg and "$part_date" not in seg:
            die(f"SQL UNION branch {si} contains an event table but is missing the $part_date predicate (the platform only checks the whole SQL; a single branch missing it causes a full table scan "
                "and silently wrong counts — core rule (1) intercepted per branch)", 2)
    if "ta.v_event" in sql and "$part_date" not in sql:
        die("event table query missing the $part_date predicate (core rule (1) — the platform enforces date filtering on event tables; missing it is always rejected)", 2)
    if not re.search(r"\bLIMIT\s+\d", sql, re.IGNORECASE):
        log("[WARN] SQL has no LIMIT (core rule (4)) — the run pipeline truncates at the requested row count, the export pipeline has no cap "
            "(confirm the magnitude before full exports of large tables; file sections go through the SQL engine, an explicit LIMIT guardrail is recommended)")
    # Heuristic check for window-level unconditional COUNT (rule (6) — whole-window counts should wrap NULLIF(count(...),0); WARN not die).
    # Each count( is checked for a directly preceding nullif( — an existence check would miss partial wrapping (NULLIF(count(a),0)+count(b)).
    # Conditional counts (count(CASE WHEN...)) do not apply: 0 is a true value in a window with data; wrapping NULLIF would turn a true 0 into "no data"
    _counts = [m for m in re.finditer(r"\bcount\s*\(", sql, re.IGNORECASE)
               if not re.search(r"(?i)case\s+when", sql[m.end():m.end() + 200].split(")", 1)[0] if ")" in sql[m.end():m.end() + 200] else "")]
    if _counts and any(
            not re.search(r"nullif\s*\(\s*$", sql[:m.start()], re.IGNORECASE) for m in _counts):
        log("[WARN] SQL has window-level COUNT aggregates not wrapped in NULLIF (core rule (6) — on empty-data days whole-window counts return 0 mixed with SUM "
            "nulls under the same symbol; a window-level count should be written NULLIF(count(...), 0). The 0 of a conditional count count(CASE WHEN...) is a "
            "true value and is not wrapped; this warning skips it automatically)")
    return sql


# ---------- Data-fetch pipelines (two-layer structure: BUILD locks fetch=run|export per scenario; RUN switches to export on run-pipeline signals as fallback) ----------
def _cli_path(spec):
    return spec.get("env", {}).get("ae_cli_path") or spec["cli"]


class QueryError(RuntimeError):
    """Query/export failure. code carries the platform error code (QUERY_TIMEOUT is retryable; ASYNC_WAIT_TIMEOUT is a wait timeout that can be resumed)"""
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _parse_cli_json(out, what):
    """ae-cli stdout -> payload dict (tolerates prefix noise); on failure raises QueryError (with error code)"""
    json_start = out.find("{")
    if json_start < 0:
        raise QueryError(None, f"{what} returned non-JSON: {out[:200]}")
    try:
        payload = json.loads(out[json_start:])
    except json.JSONDecodeError:
        raise QueryError(None, f"{what} returned invalid JSON: {out[:200]}")
    if not payload.get("ok"):
        err = payload.get("error", {})
        raise QueryError(err.get("code"), f"{what} failed[{err.get('code')}]: {err.get('message', 'unknown error')}")
    return payload


def _extract_error_payload(text):
    """Extract the JSON envelope from stdout/stderr text (when the CLI exit code is non-zero the error JSON may land in either)"""
    js = (text or "").find("{")
    if js < 0:
        return None
    try:
        return json.loads(text[js:])
    except json.JSONDecodeError:
        return None


def _run_cli(cmd, timeout, what):
    """Run one ae-cli command; on non-zero extract the error envelope from stdout/stderr and purify it into message (without dispatch prefix noise)"""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError:
        raise QueryError(None, f"ae-cli missing: {cmd[0]} (env.ae_cli_path / spec.cli configure the execution path)")
    except subprocess.TimeoutExpired:
        raise QueryError("CLI_SUBPROCESS_TIMEOUT", f"{what} timed out ({timeout}s)")
    if proc.returncode != 0:
        for src in (proc.stdout, proc.stderr):
            payload = _extract_error_payload(src)
            if payload and not payload.get("ok"):
                err = payload.get("error", {})
                raise QueryError(err.get("code"),
                                 f"{what} failed[{err.get('code')}]: {err.get('message', '')[:250]}")
        raise QueryError(None, f"{what}: ae-cli exit code {proc.returncode}: {(proc.stderr or proc.stdout)[:300]}")
    return proc.stdout


def _rows_from_inner(inner, what):
    """{title, rows} inner layer -> [{col: val}] (array rows zipped with the title column names)"""
    if "rows" not in inner:
        raise QueryError(None, f"{what} response missing the rows field: {str(inner)[:200]}")
    rows = inner.get("rows") or []
    titles = inner.get("title") or []
    if rows and isinstance(rows[0], (list, tuple)):
        if not titles:
            raise QueryError(None, f"{what} rows are arrays but the title column names are missing, cannot locate columns")
        if len(titles) != len(rows[0]):
            raise QueryError(None, f"{what} title length {len(titles)} != row length {len(rows[0])}, cannot map columns")
        rows = [dict(zip(titles, row)) for row in rows]
    return rows


# ---------- run pipeline (synchronous, bounded) ----------
def _run_sql_once(sql, spec, project_id):
    """One synchronous SQL query -> (rows, has_more). A timeout raises QueryError(QUERY_TIMEOUT) (retryable)"""
    cli = _cli_path(spec)
    cmd = [cli, "analysis", "adhoc", "run", "-p", str(project_id),
           "--model-type", "sql", "--definition", json.dumps({"sql": sql}),
           "--preview-rows", str(PREVIEW_ROWS),
           "--timeout-seconds", str(RUN_QUERY_TIMEOUT_FLAG),
           "--format", "json"]
    out = _run_cli(cmd, QUERY_TIMEOUT_SECONDS, "query")
    payload = _parse_cli_json(out, "query")
    data = payload.get("data", {})
    inner = data.get("data", data)
    rows = _rows_from_inner(inner, "query")
    return rows, bool(inner.get("has_more"))


def _wanted_report_ids(q):
    rids = q.get("report_ids")
    if rids is None:
        return None
    if not isinstance(rids, list):
        rids = [rids]
    return [int(r) for r in rids]


def _drop_total_rows(rows, inner):
    """Strip total rows from board reports: rows marked scope=total in row_metadata, or rows whose first column is a total marker
    (total values mixed into data rows pollute TopN/charts/statistics; row counts are likewise distorted).
    First-column marker recognition: Overview/Total (English, case-insensitive) + Grand total/Subtotal markers —
    export fallback-path artifacts have no row_metadata, so only the first-column heuristic applies (aligned with the run path's metric definition)."""
    meta = inner.get("row_metadata") or []
    out = []
    for i, r in enumerate(rows):
        if i < len(meta) and isinstance(meta[i], dict) and str(meta[i].get("scope", "")).lower() == "total":
            continue
        first = next(iter(r.values()), None) if isinstance(r, dict) else (r[0] if r else None)
        s = str(first).strip()
        if s.lower() in ("overview", "total") or s in ("Grand total", "Subtotal"):
            continue
        out.append(r)
    dropped = len(rows) - len(out)
    if dropped:
        log(f"Stripped {dropped} total row(s) (Overview/Total/Grand total/Subtotal)")
    # C1: the dropped count is exposed via the return value (the caller writes it to run_result / annotates the message preview — no longer stderr only)
    return out, dropped


def _run_dashboard_once(q, spec):
    """One synchronous board-report query -> (rows, has_more_any, truncated_reports).
    Envelope data.report_data_list[] per report: return_code check and per-report has_more check;
    --report-ids takes a JSON array (a comma string is rejected by the CLI). This pipeline is always capped at 100 rows/report."""
    cli = _cli_path(spec)
    cmd = [cli, "analysis", "dashboard-report-data", "run", "-p", str(q["project_id"]),
           "--dashboard-id", str(q["dashboard_id"]),
           "--preview-rows", str(DASHBOARD_PREVIEW_ROWS_DEFAULT),
           "--format", "json"]
    wanted = _wanted_report_ids(q)
    if wanted is not None:
        cmd += ["--report-ids", json.dumps(wanted)]
    out = _run_cli(cmd, QUERY_TIMEOUT_SECONDS, "board report query")
    payload = _parse_cli_json(out, "board report query")
    data = payload.get("data", {})
    rl = data.get("report_data_list")
    if rl is None:
        raise QueryError(None, f"board report query response missing the report_data_list field: {str(data)[:200]}")
    wanted_str = {str(r) for r in wanted} if wanted is not None else None
    rows_all, truncated_reports, total_dropped = [], [], 0
    for el in rl:
        if wanted_str is not None and str(el.get("report_id")) not in wanted_str:
            continue
        rc = el.get("return_code")
        if rc not in (0, None):
            raise QueryError(None, f"board report [{el.get('report_name')}] query failed"
                             f" (return_code={rc}): {str(el.get('return_message'))[:200]}")
        inner = el.get("data") or {}
        rows = _rows_from_inner(inner, f"report[{el.get('report_name')}] ")
        rows, n_drop = _drop_total_rows(rows, inner)
        total_dropped += n_drop
        rows_all.extend(rows)
        if inner.get("has_more"):
            truncated_reports.append(str(el.get("report_name") or el.get("report_id")))
    if wanted_str is not None:
        found = {str(el.get("report_id")) for el in rl}
        missing = wanted_str - found
        if missing:
            raise QueryError(None, f"the board does not contain the specified report report_id={sorted(missing)} (existing: {sorted(found)})")
    if total_dropped:
        # C1: the dropped count is attached to q (_run_data_task writes it into detail — visible in a template B trial run)
        q["_total_dropped"] = total_dropped
    return rows_all, bool(truncated_reports), truncated_reports


# ---------- export pipeline (asynchronous, full data; short-window wait + run wait resume) ----------
def _export_wait_download(spec, cmd_base, out_path):
    """export submit + short-window wait + resume polling; the artifact lands atomically at out_path -> run_id.
    ASYNC_WAIT_TIMEOUT is not a failure (the remote task is not cancelled) -> analysis run wait --run-id resumes,
    each round EXPORT_WAIT_SECONDS; a real failure raises QueryError (with run_id for manual follow-up)."""
    cli = _cli_path(spec)
    cmd = cmd_base + ["--wait", "--wait-timeout-seconds", str(EXPORT_WAIT_SECONDS),
                      "--output", out_path, "--force", "--format", "json"]
    run_id = None
    total_rounds = 1 + EXPORT_MAX_RESUME_ROUNDS
    for round_i in range(total_rounds):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=EXPORT_WAIT_SECONDS + 120, check=False)
        except FileNotFoundError:
            raise QueryError(None, f"ae-cli missing: {cli} (env.ae_cli_path / spec.cli configure the execution path)")
        except subprocess.TimeoutExpired:
            raise QueryError("CLI_SUBPROCESS_TIMEOUT",
                             f"export command timed out (CLI layer {EXPORT_WAIT_SECONDS + 120}s)")
        payload = None
        for src in (proc.stdout, proc.stderr):
            payload = _extract_error_payload(src)
            if payload is not None:
                break
        if payload:
            rid = (payload.get("data") or {}).get("run_id") \
                  or (payload.get("meta") or {}).get("run_id")
            if rid:
                run_id = rid
        if proc.returncode == 0 and payload is not None and payload.get("ok"):
            return run_id
        code = (payload or {}).get("error", {}).get("code") if payload else None
        if code == "ASYNC_WAIT_TIMEOUT":
            if run_id is None:
                raise QueryError(code, "export wait timed out but the envelope is missing run_id, cannot resume")
            log(f"export wait timed out (the remote task is still running, run_id={run_id}) -> run wait resume "
                f"(round {round_i + 1}/{total_rounds}, {EXPORT_WAIT_SECONDS}s per round)")
            cmd = [cli, "analysis", "run", "wait", "--run-id", run_id,
                   "--wait-timeout-seconds", str(EXPORT_WAIT_SECONDS),
                   "--output", out_path, "--force", "--format", "json"]
            continue
        err = (payload or {}).get("error", {}) if payload else {}
        msg = err.get("message") or (proc.stderr or proc.stdout or "")[:200]
        raise QueryError(err.get("code"), f"export failed[{err.get('code')}]: {msg}"
                         + (f" (run_id={run_id}, manual follow-up: analysis run wait --run-id {run_id})"
                            if run_id else ""))
    raise QueryError("EXPORT_WAIT_EXHAUSTED",
                     f"export wait timed out ({total_rounds} rounds × {EXPORT_WAIT_SECONDS}s total, run_id={run_id})"
                     f" — the remote task is still running; manual resume: analysis run wait --run-id {run_id}")


def _sniff_gzip(path):
    """When the artifact has no compression info, sniff by magic number (gzip = 1f 8b)"""
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"\x1f\x8b"
    except OSError:
        return False


def _read_export_text(path):
    """Unified artifact reading: gzip sniff + decompress + BOM removal"""
    if _sniff_gzip(path):
        with gzip.open(path, "rb") as f:
            return f.read().decode("utf-8-sig", "ignore")
    with open(path, "rb") as f:
        return f.read().decode("utf-8-sig", "ignore")


def _read_export_csv_rows(path):
    """adhoc export artifact (gzip CSV, header on the first line) -> [{col: val}]"""
    text = _read_export_text(path)
    reader = csv.reader(text.splitlines())
    header = next(reader, None)
    if not header:
        return []
    return [dict(zip(header, row)) for row in reader if row]


def _read_export_jsonl_rows(path, wanted_report_ids=None):
    """dashboard export artifact (gzip JSONL: first line schema, then {type:row, data:{...}, report_id})"""
    rows = []
    bad_lines = 0
    for line in _read_export_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            bad_lines += 1
            continue
        if rec.get("type") != "row":
            continue   # non-row records such as the schema line
        if not isinstance(rec.get("data"), dict):
            bad_lines += 1   # row record with an invalid payload = a corrupted row, fail loud together with JSONDecodeError
            continue
        if wanted_report_ids is not None \
                and str(rec.get("report_id")) not in {str(r) for r in wanted_report_ids}:
            continue
        rows.append(rec["data"])
    if bad_lines:
        # Data delivery does not tolerate silently dropped rows (fail loud — corrupted artifacts are treated as section-level failure, exit 1)
        raise QueryError(None, f"dashboard export artifact contains {bad_lines} rows of unparseable corrupted data"
                                f" ({path}) — the row set is incomplete; silent delivery is refused")
    return rows


def export_query_rows(q, spec, sql=None):
    """export pipeline full-data fetch (fetch=export locked at BUILD time, or entered via the run fallback switch)"""
    cli = _cli_path(spec)
    tmp = tempfile.mkdtemp(prefix="sp_fetch_")
    try:
        out_path = os.path.join(tmp, "fetch.out")
        wanted = _wanted_report_ids(q)
        if q.get("source", "sql") == "dashboard_report":
            cmd = [cli, "analysis", "dashboard-report-data", "export",
                   "-p", str(q["project_id"]), "--dashboard-id", str(q["dashboard_id"])]
            if wanted is not None:
                cmd += ["--report-ids", json.dumps(wanted)]
            run_id = _export_wait_download(spec, cmd, out_path)
            rows = _read_export_jsonl_rows(out_path, wanted)
            # The export fallback path also strips total rows (JSONL has no row_metadata; first-column heuristic) —
            # aligned with the run path's metric definition, preventing "small data: run strips / large data: export does not" drift
            rows, n_drop = _drop_total_rows(rows, {})
            if n_drop:
                q["_total_dropped"] = n_drop   # C1: same as the run path
        else:
            if sql is None:
                sql = q["sql_template"]
            cmd = [cli, "analysis", "adhoc", "export",
                   "-p", str(q.get("project_id", spec["project_id"])),
                   "--model-type", "sql", "--definition", json.dumps({"sql": sql}),
                   "--artifact-format", "csv"]
            run_id = _export_wait_download(spec, cmd, out_path)
            rows = _read_export_csv_rows(out_path)
            # export executes SQL with a LIMIT; a row count exactly at LIMIT = possibly truncated (the file claims full data / summaries are computed over full data).
            # Takes the last LIMIT match (the outer LIMIT usually comes last — an inner subquery LIMIT appearing first would take the wrong value)
            ms = list(re.finditer(r"\bLIMIT\s+(\d+)\b", sql, re.IGNORECASE))
            m = ms[-1] if ms else None
            # value sections are exempt (symmetric with the run path — an aggregate single row is always 1 row; LIMIT 1 is not truncation evidence)
            if m and q.get("mode") != "value" and len(rows) >= int(m.group(1)):
                log(f"[WARN] section {q['label']}: export returned {len(rows)} rows == SQL LIMIT {m.group(1)}"
                    f" — suspected truncation (incomplete detail/summary). The export query's LIMIT should be >= the BUILD-time row estimate cap")
                q["_limit_hit"] = int(m.group(1))   # in-message annotation signal (same as the run path)
        log(f"export full-data fetch done: section {q['label']} -> {len(rows)} rows (run_id={run_id})")
        return rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_query(q, spec, start, end, target_date, is_weekly, is_monthly=False):
    """Unified data-fetch entry (two-layer structure).
    BUILD locks queries[].fetch: run (bounded message-body scenarios) / export (large-table detail rows; the file section is naturally export).
    RUN fallback: a query locked to run that hits has_more or QUERY_TIMEOUT (2 retries) -> switch to export;
    deterministic failures (syntax / table missing) do not switch and raise directly (R1/R3 fail loud)."""
    label = q["label"]
    is_dashboard = q.get("source", "sql") == "dashboard_report"
    sql = None
    if not is_dashboard:
        sql = render_sql(q["sql_template"], start, end, target_date, is_weekly, is_monthly)
    if q.get("fetch", "run") == "export":
        return export_query_rows(q, spec, sql)
    attempts = 1 + QUERY_TIMEOUT_MAX_RETRIES
    for attempt in range(1, attempts + 1):
        try:
            if is_dashboard:
                rows, has_more_any, trunc_reports = _run_dashboard_once(q, spec)
                if has_more_any:
                    log(f"section {label}: board reports {trunc_reports} returned has_more "
                        f"(the run pipeline is always capped at 100 rows/report, data is not complete) -> fallback switch to export")
                    return export_query_rows(q, spec)
                return rows
            rows, has_more = _run_sql_once(sql, spec, q.get("project_id", spec["project_id"]))
            if has_more:
                log(f"section {label}: run returned has_more (exceeds the requested row count {PREVIEW_ROWS}) "
                    f"-> fallback switch to export for full data")
                return export_query_rows(q, spec, sql)
            # The run path also WARNs when the row count hits the SQL's own LIMIT (symmetric with the export path) —
            # hitting LIMIT without has_more means the data may already be LIMIT-truncated (when LIMIT <= the requested 1000 rows),
            # and detail/summary are computed over the truncated row set; BUILD time should check the LIMIT against the estimated cap.
            # value sections are exempt — an aggregate single row is always 1 row; a trailing LIMIT 1 in SQL is a template convention, not truncation evidence;
            # a false positive would go straight into the user message as a ⚠ integrity note (lesson from practice).
            # Takes the last LIMIT match (the outer LIMIT usually comes last — an inner LIMIT appearing first would take the wrong value)
            ms = list(re.finditer(r"\bLIMIT\s+(\d+)\b", sql or "", re.IGNORECASE))
            m = ms[-1] if ms else None
            if m and q.get("mode") != "value" and len(rows) >= int(m.group(1)):
                log(f"[WARN] section {label}: run returned {len(rows)} rows == SQL LIMIT {m.group(1)} (no has_more)"
                    f" — suspected truncation; detail/summary may be incomplete. The SQL LIMIT should be >= the BUILD-time row estimate cap")
                # The hit signal is attached to that section's q,
                # and the render layer appends a user-visible annotation in the message body based on it (no longer stderr only, where nobody looks)
                q["_limit_hit"] = int(m.group(1))
            return rows
        except QueryError as e:
            if e.code == QUERY_TIMEOUT_CODE:
                if attempt < attempts:
                    log(f"section {label}: query timed out (QUERY_TIMEOUT, attempt {attempt}/{attempts}) "
                        f"-> retrying (if it still times out, switch to export)")
                    continue
                log(f"section {label}: query timed out repeatedly ({attempts} times) -> fallback switch to export (the async pipeline has no synchronous timeout limit)")
                return export_query_rows(q, spec, sql)
            raise


# ---------- summary aggregation (decision point a: computed by the engine over all detail rows — same batch of rows, same metric definition by construction) ----------
def _to_float(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not INT_STR_RE.fullmatch(s) and not re.fullmatch(r"-?\d+\.\d+", s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def compute_summaries(q, rows):
    """queries[].summary declarations -> {name: numeric value}. count needs no column (= row count).
    Column-level validation: with a non-empty row set, a referenced missing column -> QueryError, an R1 section-level failure
    (a missing column = a config typo; silently producing 0 would push wrong numbers daily — fail loud).
    With 0 rows the aggregate yields None -> rendered as `-` (same symbol as empty data, preventing "no data" and "true 0" from mixing)."""
    out = {}
    if rows and isinstance(rows[0], dict):
        cols = set(rows[0].keys())
        for e in q.get("summary") or []:
            col = e.get("column")
            if col is not None and col not in cols:
                raise QueryError(None, f"summary references column {col} which is not among the query result columns"
                                       f" (actual columns: {sorted(cols)[:10]}) — a BUILD-time column-name typo")
    for e in q.get("summary") or []:
        agg, name = e["agg"], e["name"]
        if agg == "count":
            out[name] = len(rows) if rows else None
        elif agg == "count_distinct":
            col = e["column"]
            out[name] = len({str(r.get(col)) for r in rows if r.get(col) is not None}) \
                if rows and isinstance(rows[0], dict) else None
        elif agg == "sum":
            col = e["column"]
            vals = [_to_float(r.get(col)) for r in rows]
            # Unparseable values = data anomalies (field format changes / dirty values); silently ignoring them would push an under-counted summary as a normal result into the customer group
            # (a RUN-time WARN only goes to stderr where nobody sees it) — same nature as bad rows, escalated to a section-level failure, fail loud
            non_null_unparsed = sum(1 for r in rows if r.get(col) is not None and _to_float(r.get(col)) is None)
            if non_null_unparsed:
                raise QueryError(None, f"summary column {col} has {non_null_unparsed} values that cannot be parsed as numbers"
                                       f" (currency symbols/units/abnormal formats — sum would be silently under-counted): the section is treated as failed; "
                                       f"the data column contains unparseable values")
            vals = [v for v in vals if v is not None]
            # float binary error accumulation (0.1x3=0.30000000000000004) — summed exactly with Decimal
            # and cast back to float (no tail digits leak through the display layer's thousands separators); when the inputs are platform-returned floats, convert via the repr string to Decimal to keep the shortest representation
            if vals:
                from decimal import Decimal
                total = sum(Decimal(repr(v)) for v in vals)
                out[name] = float(total)
            else:
                out[name] = None
    return out


# ---------- Message template fill engine (core: built-in templates + inline templates -> unified placeholder filling) ----------
def _fmt_value(v, plain=False):
    """Value -> message display string. Thousands separators apply only to numeric positions (value sections / {{agg.*}}) — row-set cells (plain=True)
    pass through as-is: 11~14-digit phone/order numbers are identifiers, not numbers; adding separators makes them non-copyable and inconsistent with the CSV attachment
    (>15 digits and leading zeros were already exempt; whole row-set columns are exempt on the same basis)"""
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v)
    if plain:
        return str(v)
    if isinstance(v, float) and v == int(v):
        return f"{int(v):,}"
    if isinstance(v, (int,)):
        return f"{v:,}"
    if isinstance(v, float):
        return f"{v:,}"          # floats also get thousands separators (1234567.89 -> 1,234,567.89)
    # Platform query values are often numeric strings — pure-numeric strings are formatted as numbers (thousands separators).
    # Pure-numeric strings over 15 digits exceed the float safe-integer range (2^53≈9.0e15): mostly identifiers (user IDs etc.),
    # and a float round-trip would corrupt the trailing digits (an 18-digit ID showed trailing-digit drift in practice — message value ≠ real value) — pass through as-is, no numeric formatting
    if isinstance(v, str) and INT_STR_RE.fullmatch(v.strip()):
        s_ = v.strip()
        digits = s_.lstrip("-")
        # A pure-numeric string with leading zeros = an identifier/serial (month, serial number, zero-padded ID) — numeric conversion would strip the leading zeros (message value ≠ real value);
        # long IDs follow the same rule: pass through as-is
        if len(digits) > 1 and digits.startswith("0"):
            return str(v)
        if len(digits) <= 15:
            try:
                f = float(s_)
                return f"{int(f):,}" if f == int(f) else f"{f:,}"
            except ValueError:
                pass
    return str(v)


def _value_row0(r):
    """value sections are single-row by convention (schema convention) — when multiple rows come back, taking the first is not the user's metric definition, so WARN.
    A shared helper on the same basis as the v.<column> path (previously only that path had a WARN; the built-in/report renderers
    silently took row0 for multi-row value with dropped rows and no signal); the LIMIT exemption stays unchanged"""
    rows = r.get("rows") or []
    if len(rows) > 1:
        log(f"[WARN] query section {r.get('label')} mode=value returned {len(rows)} rows (single row, single value by convention), "
            f"rendering takes the first row — please check whether the query is missing a filter/aggregation")
    return rows[0] if rows else {}


def _integrity_note(limit_hits):
    """The three user-facing integrity notes (data task / report stage_render / card fallback text) share one copy;
    extracted into a single implementation to prevent drift. Plain-language framing: "SQL cap/LIMIT" is a BUILD-time engineering concept,
    the user message only says "data may be incomplete"; engineering admonitions stay in the fetch layer's stderr WARN"""
    return ("⚠ Data integrity: the following data sections may be incomplete this period (results reached the query cap — if this recurs, contact the task owner to check):"
            + "; ".join(
        f"section \"{lbl}\" contains only the first {n} rows, not the full set" for lbl, n in limit_hits))


def _rows_to_long(rows):
    """Wide row set -> VChart long format [{date, metric, value}] (first column as the axis; each remaining numeric column becomes a line).
    Directly usable by the chart component's data[].values; seriesField=metric automatically splits multiple lines + legend."""
    long_rows = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        ks = list(r.keys())
        if not ks:
            continue
        axis = str(r[ks[0]])
        for k in ks[1:]:
            v = _to_float(r.get(k))
            if v is None:
                continue
            long_rows.append({"date": axis, "metric": _display_col(str(k)), "value": v})
    return long_rows


class _Context:
    """Runtime context of the fill engine: spec + query outputs + aggregate outputs + window."""

    def __init__(self, spec, results, window_str, start, end):
        self.spec = spec
        self.by_label = {r["label"]: r for r in results}   # r: {label, mode, rows, summary, error, ...}
        self.agg = {}
        for r in results:
            self.agg.update(r.get("summary") or {})
        self.window_str = window_str
        self.range_str = _window_range_str(self.spec["content"].get("window_freq", "daily"), window_str)
        self.start = start
        self.end = end

    def resolve(self, key):
        """Placeholder key (e.g. q.<label>.rows / agg.<name> / task_name / date) -> output (str or structured data).
        A nonexistent reference -> QueryError (static validation already blocks label/agg names; column names are a run-time backstop)."""
        if key == "task_name":
            return self.spec["task_name"]
        if key == "date":
            return self.window_str.split(" ")[0]
        if key == "window_range":
            return self.range_str
        if key == "window_start":
            return self.start.strftime("%Y-%m-%d %H:%M:%S")
        if key == "window_end":
            return self.end.strftime("%Y-%m-%d %H:%M:%S")
        if key.startswith("agg."):
            name = key[4:]
            if name in self.agg:
                # a None value = 0-row output (displayed as '-'); a failed section produces no summary, so the name never enters ctx.agg and falls to the declared-set branch below
                return _fmt_value(self.agg[name])
            # name not in this period's outputs: declared (spec summary) → the section's fetch failed, R1 placeholder; undeclared → invalid configuration, die 2
            declared = {e.get("name") for q in self.spec["content"].get("queries") or []
                        for e in (q.get("summary") or [])}
            if name in declared:
                return "[fetch failed]"
            raise QueryError(None, f"placeholder references a nonexistent agg name: {{{{{key}}}}}")
        if key.startswith("q."):
            rest = key[2:]
            label, _, tail = rest.partition(".")
            r = self.by_label.get(label)
            if r is None:
                raise QueryError(None, f"placeholder references a nonexistent query section: {{{{{key}}}}}")
            if r.get("error"):
                # The section is in the spec but its fetch failed this period = a RUN-time fault; render the R1 placeholder (inline and built-in templates share the same contract) —
                # only "referencing a nonexistent section/agg name" is an invalid configuration (die 2, guaranteed by static validation and the branch above)
                if tail in ("rows", "long"):
                    log(f"[WARN] query section {label} fetch failed; row-set slot {{{{q.{label}.{tail}}}}} is empty "
                        " — the group's table/chart is empty; see run_result for details")
                    return []
                return "[fetch failed]"
            rows = r.get("rows") or []
            if tail == "n":
                return len(rows)
            if tail == "rows":
                # Structured row set (consumed directly by the card table component etc.): truncated to preview_rows, no annotation rows mixed in
                # (the truncation annotation is added by the template/built-in render layer itself, not polluting data rows).
                # Key names keep the original column names — inline templates just write columns[].name using the query's actual column names;
                # the column-name display mapping happens only in the built-in template render layer and does not change the data structure
                return [{k: _fmt_value(v, plain=True) for k, v in row.items()}
                        for row in rows[:_preview_rows(self.spec)]]
            if tail == "long":
                return _rows_to_long(rows[:_preview_rows(self.spec)])
            if tail.startswith("v."):
                col = tail[2:]
                # value sections are single-row by convention (the schema already limits to a single report) — when multiple rows come back, taking the first is not the user's metric definition, so WARN
                if len(rows) > 1:
                    log(f"[WARN] query section {label} mode=value returned {len(rows)} rows (single row, single value by convention), "
                        f"v.<column> takes the first row — please check whether the query is missing a filter/aggregation")
                row0 = rows[0] if rows else {}
                if not row0:
                    # 0-row value section: empty window / no data → same symbol as empty data, '-'
                    # (a GROUP BY value query / an empty board window can legitimately produce 0 rows; a die-2 refusal would treat an empty window as a fault)
                    return _fmt_value(None)
                if col not in row0:
                    raise QueryError(None, f"query section {label} has no column {col} (actual columns: {list(row0.keys())[:8]})")
                return _fmt_value(row0.get(col))
        raise QueryError(None, "invalid placeholder vocabulary: {{" + key + "}}")


def _preview_rows(spec):
    msg = spec["content"].get("message") or {}
    return int(msg.get("preview_rows", PREVIEW_ROWS_DEFAULT))


def _fill_text(text, ctx):
    """Placeholders embedded in text -> scalar strings (rows/long render as a row-count hint in text)."""
    def _sub(m):
        key = m.group(1)
        v = ctx.resolve(key)
        if isinstance(v, str):
            return v
        if isinstance(v, (int, float)):
            return _fmt_value(v)
        if isinstance(v, list):
            # empty row set + the owning section's fetch failed → put a failure marker at the text position (failed sections are visible in the group)
            if not v and key.startswith("q."):
                lbl = key[2:].partition(".")[0]
                r = ctx.by_label.get(lbl)
                if r and r.get("error"):
                    return "[fetch failed]"
            return f"(row-set data, first {len(v)} items — use it in the corresponding card template field; text messages do not expand row sets)"
        return str(v)
    return PLACEHOLDER_RE.sub(_sub, text)


def _fill_json(node, ctx):
    """Recursive fill of the card skeleton: whole-value placeholders (value == "{{q.x.rows}}") get structured data; embedded text gets scalars."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if isinstance(v, str) and PLACEHOLDER_RE.fullmatch(v.strip()):
                key = PLACEHOLDER_RE.fullmatch(v.strip()).group(1)
                prod = ctx.resolve(key)
                out[k] = prod if isinstance(prod, (list, dict)) else _fill_text(v, ctx)
            else:
                out[k] = _fill_json(v, ctx)
        return out
    if isinstance(node, list):
        return [_fill_json(x, ctx) for x in node]
    if isinstance(node, str):
        return _fill_text(node, ctx)
    return node


# ---------- Built-in template rendering (factory reference for the five forms; placeholders consume all queries) ----------
def _builtin_plain_body(spec, ctx, with_file=None):
    """Conditionally assembled text skeleton: title / value sections / row-set sections / file block."""
    c = spec["content"]
    lines = [f"[Push] {spec['task_name']} {ctx.range_str}", sep_line(), f"Stats window: {ctx.range_str}"]
    for r in ctx.by_label.values():
        lbl = r["label"]
        if r.get("error"):
            lines.append(f"{lbl}: [fetch failed]")
        elif r.get("mode") == "value":
            row0 = _value_row0(r)
            parts = [f"{_display_col(k)}: {_fmt_value(v)}" for k, v in (row0 or {}).items()]
            lines.append(f"{lbl}: " + (" / ".join(parts) if parts else "-"))
        else:
            rows = r.get("rows") or []
            if not rows:
                lines.append(f"{lbl}: no data this period")
            else:
                lines.append(_render_rows_segment_plain(lbl, rows, _preview_rows(spec)))
    agg = ctx.agg
    if agg:
        parts = [f"{k}: {_fmt_value(v)}" for k, v in agg.items()]
        lines.append("Summary: " + " / ".join(parts))
    if with_file:
        lines.append(sep_line())
        lines.append(f"Total {with_file['n']} rows; file {with_file['name']} generated")
    lines += [sep_line(), "# Data generated automatically by scheduled-push"]
    return "\n".join(lines)


def _render_rows_segment_plain(label, rows, limit):
    total = len(rows)
    lines = [f"{label} ({total} rows):"]
    shown = rows[:limit]
    for i, r in enumerate(shown, 1):
        cells = ", ".join(f"{_display_col(k)}={_fmt_value(v, plain=True)}" for k, v in list(r.items())[:6])
        lines.append(f"{i}. {cells}" if total > 1 else cells)
    if total > limit:
        lines.append(f"Total {total} rows; showing the first {limit} rows this time")
    return "\n".join(lines)


def _builtin_card_table_body(spec, ctx, file_info=None):
    """Table card: one table component per rows query (display_name as the header); value queries go into markdown under the header.
    file_info: the actually generated attachment (None when the file section fails / has 0 rows) — the "full data in the attachment" annotation is gated on it,
    and is applied only to the section the file section's detail_query points to (the attachment contains only that section's data),
    not to the mere presence of spec.content.file (if no file was generated, we must not claim it is in the attachment)."""
    f_sect = spec["content"].get("file") or {}
    dq_label = f_sect.get("detail_query")
    els = [{"tag": "markdown", "content": f"Stats window: {ctx.range_str}"}]
    first_rows = None
    for r in ctx.by_label.values():
        lbl = r["label"]
        if r.get("error"):
            els.append({"tag": "markdown", "content": f"**{lbl}**: [fetch failed]"})
        elif r.get("mode") == "value":
            row0 = _value_row0(r)
            parts = [f"**{_display_col(k)}**: {_fmt_value(v)}" for k, v in (row0 or {}).items()]
            els.append({"tag": "markdown", "content": f"**{lbl}**: " + (" / ".join(parts) if parts else "-")})
        else:
            rows = r.get("rows") or []
            if not rows:
                els.append({"tag": "markdown", "content": f"**{lbl}**: no data this period"})
                continue
            cols = list(rows[0].keys())
            columns = [{"name": str(c), "display_name": _display_col(str(c))} for c in cols]
            shown = rows[:_preview_rows(spec)]
            tbl_rows = [dict((str(k), _fmt_value(v, plain=True)) for k, v in row.items()) for row in shown]
            els.append({"tag": "markdown", "content": f"**{lbl}** ({len(rows)} rows)"})
            els.append({"tag": "table", "columns": columns, "rows": tbl_rows})
            if len(rows) > _preview_rows(spec):
                tail = f"Total {len(rows)} rows; showing the first {_preview_rows(spec)} rows in the message"
                # "see attachment" is annotated only on the detail_query section — the attachment contains only the data of the query the file section points to;
                # annotating other over-limit rows sections would mislead (that section's data is not in the attachment)
                if file_info and lbl == dq_label:
                    tail += " (full data in the attachment)"
                els.append({"tag": "markdown", "content": tail})
            if first_rows is None:
                first_rows = rows
    if ctx.agg:
        parts = [f"**{k}**: {_fmt_value(v)}" for k, v in ctx.agg.items()]
        els.append({"tag": "markdown", "content": "Summary: " + " / ".join(parts)})
    card = {
        "schema": "2.0",
        "config": {},
        "header": {"title": {"tag": "plain_text",
                              "content": f"[Push] {spec['task_name']} {ctx.range_str}"}},
        "body": {"direction": "vertical", "elements": els + [
            {"tag": "markdown", "content": "# Data generated automatically by scheduled-push"}]},
    }
    return card


def _builtin_card_chart_body(spec, ctx):
    """Chart card: one chart component per rows query (VChart long format) + summary markdown."""
    # the stats-window row is always present (backfill)
    els = [{"tag": "markdown", "content": f"Stats window: {ctx.range_str}"}]
    for r in ctx.by_label.values():
        lbl = r["label"]
        if r.get("error"):
            els.append({"tag": "markdown", "content": f"**{lbl}**: [fetch failed]"})
        elif r.get("mode") == "value":
            row0 = _value_row0(r)
            parts = [f"**{_display_col(k)}**: {_fmt_value(v)}" for k, v in (row0 or {}).items()]
            els.append({"tag": "markdown", "content": f"**{lbl}**: " + (" / ".join(parts) if parts else "-")})
        else:
            rows = r.get("rows") or []
            if not rows:
                els.append({"tag": "markdown", "content": f"**{lbl}**: no data this period"})
                continue
            els.append({"tag": "markdown", "content": f"**{lbl}** ({len(rows)} rows)"})
            # The chart field is also consumed by data tasks (builtin:card_chart chart type, default line;
            # enum validation already blocks invalid values in load_spec — the report card follows the same rule around line 2687)
            chart = {q["label"]: q for q in spec["content"].get("queries", [])}.get(lbl, {}).get("chart") or "line"
            els.append({"tag": "chart", "chart_spec": {
                "type": chart,
                "data": [{"id": "data", "values": _rows_to_long(rows[:_preview_rows(spec)])}],
                "xField": "date", "yField": "value", "seriesField": "metric",
                "legends": {"visible": True, "orient": "top"},
            }})
    if ctx.agg:
        parts = [f"**{k}**: {_fmt_value(v)}" for k, v in ctx.agg.items()]
        els.append({"tag": "markdown", "content": "Summary: " + " / ".join(parts)})
    card = {
        "schema": "2.0",
        "config": {},
        "header": {"title": {"tag": "plain_text",
                              "content": f"[Push] {spec['task_name']} {ctx.range_str}"}},
        "body": {"direction": "vertical", "elements": els + [
            {"tag": "markdown", "content": "# Data generated automatically by scheduled-push"}]},
    }
    return card


def _file_block_elements(file_info):
    if not file_info:
        return []
    return [f"Total {file_info['n']} rows; file {file_info['name']} generated"]


def render_message(spec, ctx, file_info=None):
    """Main message-rendering entry. Returns (message_body, form) — form: text / rich / card.
    When card=True, message_body is a card dict and the delivery layer wraps the interactive shell per channel; text templates return a string.
    file_info (file-section tasks): text templates append the file line before the footer; card templates insert a file element before the footer element."""
    c = spec["content"]
    msg = c["message"]
    tpl = msg["template"]
    if isinstance(tpl, str):
        if tpl == "builtin:plain" or tpl == "builtin:rich":
            body = _builtin_plain_body(spec, ctx, with_file=file_info)
            return body, "text" if tpl == "builtin:plain" else "rich"
        if tpl == "builtin:card_table":
            card = _builtin_card_table_body(spec, ctx, file_info=file_info)
            _card_insert_file(card, file_info)
            return card, "card"
        if tpl == "builtin:card_chart":
            card = _builtin_card_chart_body(spec, ctx)
            _card_insert_file(card, file_info)
            return card, "card"
        # inline text skeleton: append the file block uniformly after filling
        body = _fill_text(tpl, ctx)
        fb = _file_block_elements(file_info)
        if fb:
            body += "\n" + sep_line() + "\n" + "\n".join(fb)
        return body, "text"
    # Inline card skeleton (kind=card_2.0): insert the file element before the footer element after filling.
    # Normalized before sending: inject schema="2.0" and strip the internal kind key — skeletons written per the schema/recipes examples
    # do not carry the schema field, and sending directly would make Feishu parse them as v1; kind is stripped because it is not a card 2.0 protocol field
    card = _fill_json(tpl, ctx)
    card.pop("kind", None)
    card.setdefault("schema", "2.0")
    _card_insert_file(card, file_info)
    return card, "card"


def _card_insert_file(card, file_info):
    if not file_info or not isinstance(card, dict):
        return
    body = card.get("body") or {}
    els = body.get("elements") or []
    for line in _file_block_elements(file_info):
        els.insert(max(len(els) - 1, 0), {"tag": "markdown", "content": line})
    body["elements"] = els


# ---------- Delivery mechanism layer (im_cli direct send / webhook; same target: first success wins; card/text/file routed by capability) ----------
def _post_webhook(url, data):
    req = urlrequest.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlrequest.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", "ignore"), None
    except urlrequest.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", "ignore")
        except Exception:
            err_body = ""
        return e.code, err_body, None
    except Exception as e:
        return None, "", str(e)


def _with_retry(fn, label):
    """R5 retry semantics: network-class errors (network/timeout, including HTTP 429/5xx transient failures) retry with 2/4/8s backoff;
    deterministic failures (biz / http 4xx except 429 / cli_missing / parse) do not retry and return directly.
    fn returns (result, err)."""
    attempt = 0
    while True:
        attempt += 1
        result, err = fn()
        if err is None:
            return result, None
        if err not in RETRYABLE_ERRS:
            return result, err
        if attempt <= PUSH_MAX_RETRIES:
            delay = PUSH_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            log(f"{label} failed on attempt {attempt} ({err}), retrying in {delay}s")
            time.sleep(delay)
        else:
            return result, err


def push_text_webhook(mech, message, card=None):
    """webhook text/card delivery. Passing card = a card task (feishu kind wraps the interactive shell).
    Success is normalized to status="ok" (the old version returned an HTTP int, which never matched the checker's 'ok')."""
    kind, url = mech["webhook_kind"], mech["webhook_url"]
    if card is not None:
        if kind != "feishu":
            # cards not implemented for this channel -> the fallback semantics are decided by _deliver_all (here we only report insufficient capability)
            return {"status": "error", "error": f"card delivery is not implemented for webhook kind={kind} (switch to the text form or an im_cli mechanism at BUILD time)"}
        payload = {"msg_type": "interactive", "card": card}
    elif kind in ("wecom", "dingtalk"):
        payload = {"msgtype": "text", "text": {"content": message}}
    elif kind == "feishu":
        payload = {"msg_type": "text", "content": {"text": message}}
    else:
        payload = {"text": message}
    data = json.dumps(payload).encode("utf-8")

    def _try():
        status, body, err = _post_webhook(url, data)
        if err is not None:
            # both err/body go through redaction: some gateways/proxies echo the request URL (with the key) in error messages — storing them raw in run_result would leak credentials
            return ({"status": "error", "error": f"push failed: {_redact_creds(err)}"}), "network"
        if status is None or not 200 <= status < 300:
            # 429/5xx = transient failure (rate limit / gateway jitter / upstream overload), classified network and retried per R5; other non-2xx are deterministic failures
            if status in (429, 500, 502, 503, 504):
                return ({"status": "error", "error": f"webhook returned HTTP {status} (transient): {_redact_creds(body[:300])}"}), "network"
            return ({"status": "error", "error": f"webhook returned HTTP {status}: {_redact_creds(body[:300])}"}), "http"
        if kind == "custom_webhook":
            return ({"status": "ok", "http_status": status, "body": _redact_creds(body[:200])}), None
        try:
            resp_json = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return ({"status": "error", "error": f"webhook returned non-JSON: {_redact_creds(body[:300])}"}), "parse"
        biz_code = resp_json.get("errcode", resp_json.get("code"))
        if biz_code is not None and biz_code != 0:
            return ({"status": "error", "error": f"webhook rejected: {_redact_creds(body[:300])}"}), "biz"
        return ({"status": "ok", "http_status": status, "body": _redact_creds(body[:200])}), None

    result, err = _with_retry(_try, f"webhook[{kind}]")
    return result


def _lark_build_cmd(mech, extra_args):
    tool = mech["tool"]
    cmd = [tool, "im", "+messages-send"]
    tgt = mech["target"]
    cmd += ["--chat-id", tgt["id"]] if tgt["type"] == "chat" else ["--user-id", tgt["id"]]
    cmd += ["--as", "user"] + extra_args
    return cmd


def lark_run(mech, extra_args, cwd=None):
    """Execute the channel CLI send; returns {"status": "ok"} or {"status": "error", "error": ...}"""
    cmd = _lark_build_cmd(mech, extra_args)

    def _try():
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=LARK_TIMEOUT_SECONDS, check=False, cwd=cwd)
        except FileNotFoundError:
            return ({"status": "error", "error": f"CLI missing: {mech['tool']}"}), "cli_missing"
        except subprocess.TimeoutExpired:
            return ({"status": "error", "error": "CLI send timeout"}), "timeout"
        if proc.returncode != 0:
            return ({"status": "error", "error": f"CLI exit code {proc.returncode}: {(proc.stderr or proc.stdout)[:300]}"}), "cli"
        out = proc.stdout
        js = out.find("{")
        if js < 0:
            return ({"status": "error", "error": f"CLI returned non-JSON: {out[:200]}"}), "parse"
        try:
            payload = json.loads(out[js:])
        except json.JSONDecodeError:
            return ({"status": "error", "error": f"CLI returned invalid JSON: {out[:200]}"}), "parse"
        if not payload.get("ok"):
            return ({"status": "error", "error": f"CLI reported failure: {out[:300]}"}), "biz"
        return ({"status": "ok", "message_id": (payload.get("data") or {}).get("message_id")}), None

    result, err = _with_retry(_try, f"im_cli[{mech['tool']}]")
    if result.get("status") == "error" and err == "cli_missing":
        result["error"] = f"CLI missing: {mech['tool']} (this mechanism is unavailable when the RUN sandbox lacks the CLI)"
    return result


def push_text_mech(mech, message, presentation="text", card=None):
    """Text/rich text/card delivery. presentation: text / rich (im_cli --markdown); passing card = a card task.
    Channels with cards implemented: the im_cli default form (lark-cli --content interactive) + feishu webhook; other channels report insufficient capability.
    An im_cli with send_template = direct send via the command template (any channel CLI; rich and text share one template, rendering effect decided by test delivery;
    the command-template mechanism does not support cards — already blocked by the static gate; here the fallback reports insufficient capability, triggering R5 degradation)."""
    if mech["mechanism"] == "webhook":
        return push_text_webhook(mech, message, card)
    if mech.get("send_template") is not None:
        if card is not None:
            return {"status": "error",
                    "error": "the command-template mechanism does not support cards (cards only via the lark-cli default form / Feishu webhook) — degrading to plain text"}
        cmd = _render_cmd_template(mech, "send_template", text=message)
        return _run_cmd_with_success(mech, cmd)
    if card is not None:
        return lark_run(mech, ["--content", json.dumps(card, ensure_ascii=False), "--msg-type", "interactive"])
    if presentation == "rich":
        return lark_run(mech, ["--markdown", message])
    return lark_run(mech, ["--text", message])


def _curl(args, timeout, action):
    try:
        r = subprocess.run(["curl", *args], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        # curl missing = a deterministic failure (biz class, no retry) — honoring the dm "RUN sandbox dependency list" promise of exit 3
        raise RuntimeError(f"{action} curl missing (the RUN sandbox lacks curl; wecom file delivery depends on it)")
    except subprocess.TimeoutExpired:
        # timeout = network class (messages containing "curl failed" go through R5 retry)
        raise RuntimeError(f"{action} curl failed: timeout ({timeout}s)")
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"{action} curl failed: returncode={r.returncode} {(r.stderr or '')[:200]}")
    return r.stdout


def wecom_check(resp_text, action):
    try:
        d = json.loads(resp_text)
    except Exception:
        raise RuntimeError(f"{action} returned non-JSON: {resp_text[:300]}")
    if d.get("errcode") != 0:
        raise RuntimeError(f"{action} failed: {resp_text[:300]}")


def wecom_push_file(url, path, display_name):
    key = url.split("key=")[-1]
    out = _curl(["-s", f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type=file",
                 "-F", f"media=@{path};filename={display_name}"], 120, "upload_media")
    wecom_check(out, "upload_media")
    media_id = json.loads(out)["media_id"]
    body = json.dumps({"msgtype": "file", "file": {"media_id": media_id}})
    out = _curl(["-s", url, "-H", "Content-Type: application/json", "-d", body], 60, "send_file")
    wecom_check(out, "send_file")
    return out


def push_file_mech(mech, path, display_name):
    """File delivery. im_cli (file_ok) goes through CLI --file (cwd-relative path); among webhooks only wecom upload_media is verified.
    The wecom two-step delivery also goes through R5 retry (curl-layer failure = network class, retried; business errcode = biz class, not retried)."""
    if mech["mechanism"] == "webhook":
        if mech.get("webhook_kind") != "wecom":
            return {"status": "error",
                    "error": f"file capability unverified for webhook kind={mech.get('webhook_kind')} (the BUILD-time test delivery should have set file_ok)"}

        def _try():
            try:
                wecom_push_file(mech["webhook_url"], path, display_name)
                return {"status": "ok"}, None
            except RuntimeError as e:
                # "curl failed" = network class (retryable); a business errcode failure = deterministic (no retry)
                msg = str(e)
                err = "network" if "curl failed" in msg else "biz"
                return {"status": "error", "error": msg}, err

        result, _err = _with_retry(_try, "wecom_file")
        return result
    if not mech.get("file_ok"):
        return {"status": "error", "error": "this mechanism has file_ok=false (the BUILD-time file test delivery did not pass)"}
    if mech.get("send_file_template") is not None:
        # command-template file delivery: {file} = relative file name, cwd = the file's directory (same as the lark convention — some CLIs reject absolute paths)
        cmd = _render_cmd_template(mech, "send_file_template",
                                   file_name=os.path.basename(path), display_name=display_name)
        return _run_cmd_with_success(mech, cmd, cwd=os.path.dirname(os.path.abspath(path)))
    return lark_run(mech, ["--file", os.path.basename(path)], cwd=os.path.dirname(os.path.abspath(path)))


_REDACT_CRED_RE = re.compile(r"([?&](?:key|access_token)=)([^&\s]{0,300})")


def _redact_creds(s):
    """Credential redaction for failure text/response bodies (key/access_token keep only the first 4 chars) — mask only, never truncate,
    so diagnostic length is unaffected. Some gateways/proxies echo the request URL (with the key) in errors, and the server may also return it."""
    return _REDACT_CRED_RE.sub(lambda m: f"{m.group(1)}{m.group(2)[:4]}***", str(s or ""))


def _redact_webhook_url(url):
    """Webhook URL credential redaction (the key parameter keeps only the first 4 chars) — run_result/failure text/session records all pass through this,
    preventing credentials from landing on disk in the clear (the full URL is used only during delivery execution and is never persisted to any artifact)."""
    s = str(url or "")
    if "key=" not in s and "access_token=" not in s:
        return s[:60]
    return _redact_creds(s)


def _mech_target_key(mech):
    # Cross-channel primary/backup groups — mechanisms in the same group share one delivery-target semantics (first success wins); different targets broadcast.
    # Without a group, grouping follows each mechanism's own target key (legacy semantics: cross-channel is always a different target = broadcast)
    grp = mech.get("group")
    if grp:
        return f"group:{grp}"
    if mech["mechanism"] == "im_cli":
        return f"im:{mech['target']['type']}:{mech['target']['id']}"
    return f"wh:{_redact_webhook_url(mech.get('webhook_url'))}"


def _mech_disp(mech):
    """Human-readable mechanism summary (used in delivery-failure/alert copy). A group is only a grouping key — a bare group:xxx tells the user nothing about
    which channel/target failed, so failure info must land on the actual mechanism (in the group case the caller combines the group name + the last mechanism summary)."""
    if mech["mechanism"] == "im_cli":
        return f"im:{mech['target'].get('type')}:{mech['target'].get('id')}"
    return f"wh:{mech.get('webhook_kind')}:{_redact_webhook_url(mech.get('webhook_url'))}"


def _key_disp(key, mech):
    """Group key -> display string for failure/alert copy: group keys carry a mechanism summary; natural keys as-is"""
    if key.startswith("group:") and mech is not None:
        return f"{key}·{_mech_disp(mech)}"
    return key[:40]


def deliver(spec, message, presentation="text", file_path=None, display_name=None, card=None):
    """Deliver in order: for the same delivery target, text and file each take the first success (later entries for the same target = backup); different targets are delivered independently (broadcast).
    Target identification: the mechanism's explicit group field takes priority (same group = cross-channel primary/backup group — first success wins, failures switch in order;
    without a group, each mechanism's own target key applies; cross-channel = different targets = broadcast).
    Failure is judged by "whether the target was finally delivered": the primary mechanism failing but a same-target backup delivering → not a failure (recorded as a warning).
    Card task degradation semantics: primary mechanism card failure or backup card capability insufficient → degrade to a plain-text summary + WARNING (delivery first).
    Returns (failures, results): non-empty failures => exit code 3."""
    mechs = spec["delivery"]["mechanisms"]
    text_done, file_done = {}, {}
    text_last_err, file_last_err, text_last_disp, file_last_disp = {}, {}, {}, {}
    results, warnings = [], []
    for mech in mechs:
        key = _mech_target_key(mech)
        tag = f"{mech['mechanism']}:{_key_disp(key, mech)}"
        if not text_done.get(key):
            pr = push_text_mech(mech, message, presentation, card=card)
            results.append({"mechanism": mech["mechanism"], "target": key, "kind": "text", **pr})
            if pr.get("status") == "ok":
                if key in text_last_err:
                    warnings.append(f"text@{tag}: the primary mechanism failed but a backup delivered ({text_last_err.pop(key)})")
                text_done[key] = True
            elif card is not None:
                # the card task's primary form was not delivered (channel capability insufficient or failed) -> degrade to plain text (delivery first), record WARNING
                fallback = push_text_mech(mech, message, "text", card=None)
                results.append({"mechanism": mech["mechanism"], "target": key,
                                "kind": "text_fallback", "fallback_reason": pr.get("error"), **fallback})
                if fallback.get("status") == "ok":
                    if key in text_last_err:
                        warnings.append(f"text@{tag}: the primary mechanism failed but a backup delivered ({text_last_err.pop(key)})")
                    warnings.append(f"text@{tag}: the card was not delivered, degraded to plain text ({pr.get('error')})")
                    text_done[key] = True
                else:
                    text_last_err[key] = fallback.get("error")
                    text_last_disp[key] = tag
                    # A double failure of card+fallback likewise does not skip this mechanism's file delivery —
                    # same semantics as the non-card branch below; falls through to the file block
            else:
                text_last_err[key] = pr.get("error")
                text_last_disp[key] = tag
                # A text failure does not skip this mechanism's file delivery: the file and the text are two separate deliverables,
                # and the file can still be attempted when the mechanism's text fails — continuing directly on primary text failure would
                # silently leave the file to same-target backups without file_ok (which cannot catch it), while the final backstop would
                # misjudge "a file_ok mechanism exists" as passing -> the file is lost with exit code 0
        if file_path and not file_done.get(key):
            if not mech.get("file_ok"):
                log(f"[WARN] mechanism {tag} has no file capability (file_ok unverified), skipping file delivery"
                    " — later file_ok mechanisms for the same target back it up")
                continue  # this mechanism's file capability is unverified; skipped (later file_ok mechanisms for the same target back it up)
            fr = push_file_mech(mech, file_path, display_name)
            results.append({"mechanism": mech["mechanism"], "target": key, "kind": "file", **fr})
            if fr.get("status") == "ok":
                if key in file_last_err:
                    warnings.append(f"file@{tag}: the primary mechanism failed but a backup delivered ({file_last_err.pop(key)})")
                file_done[key] = True
            else:
                file_last_err[key] = fr.get("error")
                file_last_disp[key] = tag
    failures = []
    for key, err in text_last_err.items():
        if not text_done.get(key):
            failures.append(f"text@{text_last_disp.get(key) or key[:40]}: {err}")
    for key, err in file_last_err.items():
        if not file_done.get(key):
            failures.append(f"file@{file_last_disp.get(key) or key[:40]}: {err}")
    # File-type tasks: every target that got the text delivered must also actually receive the file, otherwise record a failure
    # (judge by actually-delivered file_done — "a file_ok mechanism exists" does not mean the file really went out:
    # when the primary mechanism's text failed, its file delivery may not have run; the backstop only trusts file_done)
    if file_path:
        for key in [k for k, v in text_done.items() if v]:
            if not file_done.get(key):
                failures.append(f"file@{key[:40]}: text delivered but the file was not delivered successfully")
    if warnings:
        log(f"[WARN] delivery degradation/failover records: {'; '.join(warnings)}")
    return failures, results


def _trim_to_kb(message, max_kb, tail_note="…(message size over the limit, preview truncated — see the file for full content)"):
    """Row-level trimming into the size guardrail (with a trailing note); shared by the report/preview paths and the R4 last-resort fallback.
    Structural-tail protection — first peel the "summary/file/footer" structural lines off the tail (back to front, stopping at the first
    body line containing row-set data), trimming only the mid-section row-set lines, so summary and "file generated" promise lines are never cut (truncation does not change section semantics,
    implementing "preserve numeric sections as much as possible")."""
    limit = max_kb * 1024
    if len(message.encode("utf-8")) <= limit:
        return message, False
    lines = message.split("\n")
    # Identify the structural tail back to front: separator lines/footer/file lines/summary lines (starting with "Summary:") — the first line outside these is where the row-set mid-section starts.
    # Known false-positive surface: coarse heuristic matching — data rows that happen to start with "Total " or end with "generated"
    # would be wrongly protected (multi-row pasted tables have numbered prefixes in the way; a single row with total==1 is very unlikely); the consequence of wrong protection is only a few untrimmed lines,
    # and the hard size constraint is guaranteed by the later fallback trimming, introducing no correctness problem
    tail_struct = []
    while lines:
        last = lines[-1].strip()
        if (not last or last.startswith("─") or last.startswith("#")
                or last.startswith("Total ") or last.startswith("Summary: ")
                or last.startswith("…") or last.endswith("generated")):
            tail_struct.insert(0, lines.pop())
        else:
            break
    # dynamic tail-note buffer (tail_note measured 71B > the hardcoded 60 — extreme scenarios overflow by 11B)
    tail_budget = len(tail_note.encode("utf-8")) + 1
    while lines and len(("\n".join(lines + tail_struct)).encode("utf-8")) + tail_budget > limit:
        lines.pop()
    # Still over the limit after the row-set lines are exhausted (extremely small guardrail): allow cutting some structural lines — the size guardrail takes priority over structural protection (not exceeding the limit is a hard constraint).
    # Drop order inverted — drop low-information-density lines first (separators/footer), semantically key lines (summary / "file generated") last
    # (the old pop(0) dropped the summary line first, confirmed by measurement)
    def _struct_density(s):
        s2 = s.strip()
        if s2.startswith("─") or s2.startswith("#"):
            return 0   # separators/footer — decoration and attribution, dropped first
        if s2.startswith("Summary") or s2.endswith("generated"):
            return 2   # semantically key lines, dropped last
        return 1        # the rest ("Total X rows" annotations etc.)
    while tail_struct and len(("\n".join(lines + tail_struct)).encode("utf-8")) + tail_budget > limit:
        order = sorted(range(len(tail_struct)), key=lambda i: _struct_density(tail_struct[i]))
        tail_struct.pop(order[0])
    lines.append(tail_note)
    return "\n".join(lines + tail_struct), True


def write_run_result(result, base_dir):
    path = os.path.join(base_dir, RUN_RESULT_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return path


# ---------- CSV file materialization (file section: row set written locally; full data, no truncation) ----------
# The file does not go through a second export — queries with fetch=export have already fetched the full row set; write the CSV locally
# (_write_rows_csv: utf-8-sig BOM + header on the first line, same shape as the adhoc export artifact).


# ---------- Report rendering (kind=report: built-in HTML templates / inline templates + slots; the LLM fills slots, isomorphic to the data task's engine fill) ----------
def _esc(v):
    return html.escape(str(v), quote=True)


def _esc_multiline(text):
    """HTML semantic escaping + newline preservation (\n -> <br>) — analysis text is multi-line bulleted short sentences; browsers collapse bare \n into spaces
    and a bulleted report would smear into one long paragraph. Consumed in two places: built-in sections and inline template slots."""
    return _esc(text).replace("\n", "<br>")


def _svg_line(rows, title):
    """rows: [(label, float)] -> inline SVG line chart (the data-table fallback is placed by the caller)"""
    if not rows:
        return ""
    w, h, left, top, bottom = 600, 170, 40, 24, 140
    vals = [float(v) for _, v in rows]
    vmax, vmin = max(vals), min(vals)
    span = (vmax - vmin) or 1
    n = len(rows)
    xs = [left + int((w - left - 12) * i / max(n - 1, 1)) for i in range(n)]
    ys = [bottom - int((bottom - top) * (v - vmin) / span) for v in vals]
    pts = " ".join(f"{x},{y}" for x, y in zip(xs, ys))
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="#4c8cff"/>' for x, y in zip(xs, ys))
    xlabels = ""
    for i in range(0, n, max(1, n // 4)):
        xlabels += f'<text x="{xs[i]}" y="158" font-size="10" fill="#8f959e">{_esc(rows[i][0])}</text>'
    return (f'<svg viewBox="0 0 600 170" width="100%" height="170" role="img" aria-label="{_esc(title)}">'
            f'<line x1="{left}" y1="{bottom}" x2="{w - 8}" y2="{bottom}" stroke="#eee"/>'
            f'<text x="{left - 4}" y="{top - 6}" font-size="10" fill="#646a73" text-anchor="start">{_esc(title)}</text>'
            f'<polyline points="{pts}" fill="none" stroke="#4c8cff" stroke-width="3"/>{dots}{xlabels}</svg>')


def _svg_bar(rows, title):
    if not rows:
        return ""
    w, h, left, top, bottom = 600, 170, 40, 24, 140
    vals = [float(v) for _, v in rows]
    vmax = max(vals) or 1
    n = len(rows)
    bw = int((w - left - 12) / max(n, 1) * 0.6)
    bars = ""
    for i, (label, v) in enumerate(rows):
        x = left + int((w - left - 12) * i / max(n, 1))
        bh = int((bottom - top) * (v / vmax))
        bars += (f'<rect x="{x}" y="{bottom - bh}" width="{bw}" height="{bh}" fill="#4c8cff" rx="2"/>'
                 f'<text x="{x}" y="158" font-size="10" fill="#8f959e">{_esc(label)}</text>')
    return (f'<svg viewBox="0 0 600 170" width="100%" height="170" role="img" aria-label="{_esc(title)}">'
            f'<line x1="{left}" y1="{bottom}" x2="{w - 8}" y2="{bottom}" stroke="#eee"/>'
            f'<text x="{left - 4}" y="{top - 6}" font-size="10" fill="#646a73">{_esc(title)}</text>{bars}</svg>')


def _html_table(rows, columns=None, render_limit=None, total_rows=None):
    if not rows:
        return "<p>(no data)</p>"
    shown = rows if render_limit is None else rows[:render_limit]
    cols = columns or list(rows[0].keys())
    head = "".join(f"<th>{_esc(_display_col(c))}</th>" for c in cols)
    body = ""
    for r in shown:
        body += "<tr>" + "".join(f"<td>{_esc(_fmt_value(r.get(c), plain=True))}</td>" for c in cols) + "</tr>"
    tail = ""
    if render_limit is not None and len(rows) > render_limit:
        # total_rows takes priority (rows may already be truncated by the data.json cap — len is not the real row count)
        total_n = total_rows if total_rows is not None else len(rows)
        tail = f'<p class="note">Total {total_n} rows; showing the first {render_limit} rows in the table</p>'
    return f'<table><tr>{head}</tr>{body}</table>{tail}'


_HTML_SHELL = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:-apple-system,'PingFang SC',sans-serif;background:#f5f6f7;margin:0;padding:24px;color:#1f2329}}
.wrap{{max-width:860px;margin:0 auto}}
.banner{{background:#1f2a44;color:#fff;border-radius:12px;padding:22px 26px;margin-bottom:16px}}
.banner h1{{font-size:20px;margin:0 0 6px}}.banner .sub{{color:#aab4cf;font-size:12px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}}
.kpi{{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.05)}}
.kpi .v{{font-size:24px;font-weight:600;color:#1f2a44}}.kpi .l{{font-size:12px;color:#646a73;margin-top:2px}}
.chartcard{{background:#fff;border-radius:10px;padding:16px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.05)}}
.chartcard h2{{font-size:14px;margin:0 0 10px;color:#1f2a44}}
.tblwrap{{overflow-x:auto;background:#fff;border-radius:10px;padding:12px 16px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.05)}}
.tblwrap h2{{font-size:14px;margin:0 0 10px;color:#1f2a44}}
table{{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}}
th,td{{padding:6px 10px;border-bottom:1px solid #eee;text-align:left}}
th{{color:#646a73;font-weight:500}}td{{font-variant-numeric:tabular-nums}}
details{{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.05);margin-bottom:16px}}
details summary{{cursor:pointer;padding:12px 16px;font-size:13px;color:#4c8cff}}
details .inner{{padding:0 16px 12px}}
.sec{{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.05);border-left:4px solid #4c8cff;padding:14px 18px;margin-bottom:16px}}
.sec.risk{{border-left-color:#e6a23c;background:#fdf7ef}}
.sec .no{{font-size:11px;color:#8f959e;letter-spacing:1px}}
.sec h2{{font-size:15px;margin:2px 0 8px}}
.sec .analysis{{font-size:13px;line-height:1.8;color:#1f2329}}
.note{{font-size:11px;color:#8f959e;margin-top:16px}}
</style></head><body><div class="wrap">
<div class="banner"><h1>{title}</h1><div class="sub">{sub}</div></div>
{body}
<div class="note"># Data generated automatically by scheduled-push</div>
</div></body></html>"""


def _chart_rows(rows):
    """dict rows -> [(first-column value, second-column number)] (takes the first 2 columns)"""
    out = []
    for r in rows[:14]:
        if isinstance(r, dict):
            ks = list(r.keys())
            if len(ks) < 2:
                continue
            try:
                out.append((str(r[ks[0]]), float(r[ks[1]])))
            except (TypeError, ValueError):
                continue
    return out


def render_html_report(spec, data, slots, window_str):
    rep = spec["content"]["report"]
    tpl = rep.get("template")
    queries = {q["label"]: q for q in spec["content"]["queries"]}
    data_by_label = {d["label"]: d for d in data["queries"]}
    range_str = _window_range_str(spec["content"].get("window_freq", "daily"), window_str)
    title = (spec["content"].get("title_template") or "[Report] {{task_name}} {{window_range}}") \
        .replace("{{task_name}}", spec["task_name"]).replace("{{window_range}}", range_str) \
        .replace("{{date}}", window_str.split(" ")[0])

    if isinstance(tpl, str) and tpl.strip().startswith("<"):
        # Inline template: {{slot:<section_id>}} text slots + {{data:<label>}} data-table slots
        # A finalized template containing full-document markers (<!DOCTYPE/<html) is used directly as the artifact (slot replacement only);
        # only body-fragment templates get the _HTML_SHELL shell. Data tables are truncated at the display layer by preview_rows.
        is_full_doc = bool(re.search(r"<!doctype\s+html|<html[\s>]", tpl, re.IGNORECASE))
        render_limit = int((spec["content"].get("message") or {}).get("preview_rows", PREVIEW_ROWS_DEFAULT))
        body = tpl
        for sec in rep["outline"]:
            body = body.replace("{{slot:" + sec["section_id"] + "}}",
                                _esc_multiline(slots.get(sec["section_id"], "[missing slot]")))
        for label, d in data_by_label.items():
            if d.get("error"):
                body = body.replace("{{data:" + label + "}}",
                                    f"<p>[fetch failed]</p>")
            else:
                body = body.replace("{{data:" + label + "}}",
                                    _html_table(d.get("rows") or [], render_limit=render_limit,
                                                total_rows=d.get("total_rows")))
        body = PLACEHOLDER_RESIDUE_RE.sub("[unmatched slot]", body)
        if re.search(r"\[unmatched slot\]", body):
            log("[WARN] the report template has unmatched slots ({{slot:*}} / {{data:*}} keys do not correspond to outline/queries; "
                "full-document template titles/banner text carry no slot semantics — other {{{{...}}}} vocabulary placeholders are likewise stamped with this marker; "
                "please hardcode the text) — check the artifact in the BUILD trial run; do not push a layout with unmatched slots into a real group")
        if is_full_doc:
            return body
        return _HTML_SHELL.format(title=_esc(title), sub=_esc(f"{range_str} · {spec['project_name']}"), body=body)

    # built-in templates: daily / weekly (the monthly window reuses the weekly layout — sections-first suits monthly report reading)
    if tpl == "monthly":
        tpl = "weekly"
    if tpl not in ("daily", "weekly"):
        die(f"report.template invalid: {str(tpl)[:60]} (built-in ids: daily / weekly / monthly=weekly layout; "
            "for a custom template inline the full content, starting with '<')", 2)
    render_limit = int((spec["content"].get("message") or {}).get("preview_rows", PREVIEW_ROWS_DEFAULT))
    kpis, charts, tables = [], [], []
    for label, d in data_by_label.items():
        if d.get("error"):
            continue
        q = queries.get(label, {})
        if q.get("mode") == "value":
            # one KPI card per column of the value row (one query with multiple metrics -> multiple cards; layout redone)
            row = _value_row0(d)
            for k, v in (row or {}).items():
                kpis.append(f'<div class="kpi"><div class="v">{_esc(_fmt_value(v))}</div>'
                            f'<div class="l">{_esc(_display_col(k))}</div></div>')
        else:
            rows = d.get("rows") or []
            chart = q.get("chart")
            if chart and rows:
                cr = _chart_rows(rows)
                svg = _svg_line(cr, label) if chart == "line" else _svg_bar(cr, label)
                charts.append(f'<div class="chartcard"><h2>{_esc(label)}</h2>{svg}</div>')
            # Detail tables go into collapsible sections (collapsed by default, horizontally scrollable when expanded — layout redone: charts/KPIs are the primary data expression; tables are no longer laid out flat)
            # Row counts use total_rows (after the data.json cap, len(rows) is only the truncated count at the 200 cap;
            # the real row count is the total_rows written by _dump_report_data_json — showing the truncated count would mislead as "Total 200 rows")
            total_n = d.get("total_rows", len(rows))
            tables.append(
                f'<details><summary>View detail table · {label} (Total {total_n} rows)</summary>'
                f'<div class="inner">' + _html_table(rows, render_limit=render_limit, total_rows=total_n) + "</div></details>")
    kpi_html = f'<div class="kpis">{"".join(kpis)}</div>' if kpis else ""
    chart_html = "".join(charts)
    sections = ""
    for i, sec in enumerate(rep["outline"], 1):
        text = slots.get(sec["section_id"], "")
        risk = " risk" if ("risk" in sec.get("title", "").lower() or "risk" in str(sec.get("section_id", "")).lower()) else ""
        sec_html = (f'<div class="sec{risk}"><div class="no">SECTION {i:02d}</div>'
                    f'<h2>{_esc(sec["title"])}</h2><div class="analysis">{_esc_multiline(text)}</div></div>')
        bound_tables = ""
        for lbl in sec.get("data_labels", []):
            d = data_by_label.get(lbl)
            if d and not d.get("error") and d.get("rows"):
                bound_tables += '<div class="tblwrap">' + _html_table(d["rows"][:5]) + "</div>"
        sections += sec_html + bound_tables
    if tpl == "weekly":
        # weekly: sections first (metric cards up front, collapsed detail tables at the back)
        body = kpi_html + sections + chart_html + "".join(tables)
    else:
        body = kpi_html + chart_html + "".join(tables) + sections
    # the banner subtitle uses the same window_range framing as the title (a half-open interval with time-of-day reads easily as an end boundary)
    return _HTML_SHELL.format(title=_esc(title), sub=_esc(f"{range_str} · {spec['project_name']}"), body=body)


def render_text_report(spec, data, slots, window_str):
    rep = spec["content"]["report"]
    data_by_label = {d["label"]: d for d in data["queries"]}
    range_str = _window_range_str(spec["content"].get("window_freq", "daily"), window_str)
    title = (spec["content"].get("title_template") or "[Report] {{task_name}} {{window_range}}") \
        .replace("{{task_name}}", spec["task_name"]).replace("{{window_range}}", range_str) \
        .replace("{{date}}", window_str.split(" ")[0])
    lines = [title, sep_line()]
    for sec in rep["outline"]:
        # section titles use a plain-text marker (webhook channels do not render Markdown; bare ## is noise)
        lines.append(f"▍{sec['title']}")
        text = slots.get(sec["section_id"], "")
        if text:
            lines.append(text)
        for lbl in sec.get("data_labels", []):
            d = data_by_label.get(lbl)
            if d is None:
                continue
            if d.get("error"):
                lines.append(f"{lbl}: [fetch failed]")
            elif d.get("mode") == "value":
                # value sections render per column: a multi-column value query yields one line per column "- {column}: {value}",
                # column names mapped via _display_col, lines prefixed with the query label — aligned with the card/HTML paths;
                # a single column degrades naturally to one line (same as the old output); 0 rows (empty window) render as '-'
                row = _value_row0(d)
                if not row:
                    lines.append(f"- {lbl}: -")
                else:
                    for col in row:
                        lines.append(f"- {lbl}·{_display_col(col)}: {_fmt_value(row[col])}")
            else:
                # section-bound tables match the HTML layout: show the first 5 rows (HTML section-bound tables are also [:5])
                lines.append(_render_rows_segment_plain(lbl, d.get("rows") or [], 5))
        lines.append("")
    lines += [sep_line(), "# Data generated automatically by scheduled-push"]
    return "\n".join(lines)


# ---------- Two-stage report ----------
def _dump_report_data_json(data, base_dir, spec=None):
    """Persist data.json — rows are truncated per section to REPORT_ROWS_CAP rows (the RUN-time executing Agent must read
    data.json whole to write the analysis; huge row sets would overflow the context or be read only partially, producing analysis based on partial data with no warning;
    summary is kept in full). Truncation info is recorded per section (rows_truncated_to / total_rows), visible and reportable to the LLM.
    The SQL LIMIT hit signal (_limit_hit on the spec query object) is passed through per section as limit_hit — the two-stage flow
    crosses processes, and data.json is the only transfer channel (stage_render and the writing Agent read only it)."""
    spec_q = {q["label"]: q for q in (spec or {}).get("content", {}).get("queries") or []}
    for q in data.get("queries", []):
        rows = q.get("rows")
        if isinstance(rows, list) and len(rows) > REPORT_ROWS_CAP:
            q["total_rows"] = len(rows)
            q["rows"] = rows[:REPORT_ROWS_CAP]
            q["rows_truncated_to"] = REPORT_ROWS_CAP
            log(f"[WARN] section {q.get('label')}: data.json truncated to {REPORT_ROWS_CAP} rows on persist (total {q['total_rows']} rows)"
                f" — the report analysis is based on the first {REPORT_ROWS_CAP} rows; fix properly by switching to the aggregate style (AI analysis relies on aggregate results, not piled-up detail rows)")
        lh = spec_q.get(q.get("label"), {}).get("_limit_hit")
        if lh:
            q["limit_hit"] = lh
    data_path = os.path.join(base_dir, DATA_JSON)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data_path


def _r3_failure_message(spec):
    """R3 all-failed placeholder — plain language for the group message + action guidance (technical text goes only to run_result/stderr, never to the customer group)."""
    return (f"[Report] {spec['task_name']}\n{sep_line()}\n"
            "Data fetch failed this period; the report could not be generated — see the task execution log (run_result.json) for details; "
            "automatic retry next period; if this recurs, contact the task owner.")


def stage_data(spec, base_dir, window_str, start, end, target_date, is_weekly, is_monthly, push):
    results = []
    all_failed = True
    for q in spec["content"]["queries"]:
        entry = {"label": q["label"], "mode": q.get("mode", "value"), "source": q.get("source", "sql")}
        try:
            entry["rows"] = run_query(q, spec, start, end, target_date, is_weekly, is_monthly)
            entry["summary"] = compute_summaries(q, entry["rows"])
            all_failed = False
        except Exception as e:
            entry["error"] = str(e)
            log(f"section {q['label']} query failed: {e}")
        results.append(entry)
    data = {"window": window_str, "queries": results}
    data_path = _dump_report_data_json(data, base_dir, spec)
    log(f"data stage done: {len(results)} queries, {sum(1 for r in results if r.get('error'))} failed -> {data_path}")
    if all_failed:
        # R3: all failed -> whole-message fetch-failure placeholder (push if possible)
        message = _r3_failure_message(spec)
        write_run_result({"window": window_str, "stage": "data", "all_failed": True, "message": message,
                          "error_detail": results[0].get('error', '')[:400]}, base_dir)
        print(message)
        if push:
            failures, _ = deliver(spec, message)
            if failures:
                sys.exit(3)
        sys.exit(1)
    write_run_result({"window": window_str, "stage": "data",
                      "failed": [r["label"] for r in results if r.get("error")], "data_file": data_path}, base_dir)
    sys.exit(0)


def _check_slot_numbers(slots, data, spec):
    """Loose comparison of number tokens in slot analysis text vs actual values in data.json.
    Hit forms: raw value / thousands-separated / decimal stripped / rounded to 1~2 places / percentage (value*100 rounded) / wan-scaled (/10000).
    Returns the list of unmatched (section_id, number string) — WARN only, no blocking (legitimately derived numbers such as period-over-period deltas are not
    raw values in data.json; the WARN is observation, not conviction).
    Strip patterns (non-data tokens are not compared): dates/month-days (Oct 6, 2026-10-06), the N in "last N days/TopN/Nth",
    plain ordinals — hits on these would only drown the real hallucination signal."""
    import re as _re
    # value pool: all numeric values in query row sets + summary aggregate values (None excluded)
    pool = set()
    for q in data.get("queries", []):
        for r in q.get("rows") or []:
            if not isinstance(r, dict):
                continue
            for v in r.values():
                f = _to_float(v)
                if f is not None:
                    pool.add(round(f, 4))
        # summary aggregate values enter the pool — the docstring claimed "+ summary aggregates" while the implementation only iterated rows,
        # so an LLM transcribing summary numbers per spec (sum products like 223,466, not in any single-row cell) would all be false positives,
        # dulling the observation surface with noise
        for v in (q.get("summary") or {}).values():
            f = _to_float(v)
            if f is not None:
                pool.add(round(f, 4))
    # normalize number strings -> floats (strip thousands-separator commas/percent signs)
    def _norm(tok):
        t = tok.replace(",", "").rstrip("%")
        try:
            return float(t)
        except ValueError:
            return None
    def _hit(f):
        if f is None:
            return True
        cands = {round(f, 4), round(f * 100, 2), round(f / 10000, 2), round(f / 100, 4)}
        for c in list(cands):
            cands.add(round(c, 1))
            cands.add(round(c))
        return any(c in pool for c in cands if c is not None)
    unmatched = []
    for sid, text in (slots or {}).items():
        t = str(text)
        # strip non-data tokens (strip first, then extract; stripped positions produce no more numbers):
        t = _re.sub(r"\d{4}[-/.]\s*\d{1,2}[-/.]\s*\d{1,2}", " ", t)   # dates
        t = _re.sub(r"(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\b", " ", t)   # month-day
        t = _re.sub(r"(?i)\b(last|past|prev(?:ious)?|prior)\s*\d+\s*(day|week|month|hour|time)s?\b", " ", t)   # the N in "last N days/past N weeks"
        t = _re.sub(r"(?i)(top|rank)\s*_?\s*\d+", " ", t)                    # TopN
        t = _re.sub(r"(?i)\b\d+\s*(st|nd|rd|th)\b", " ", t)                # ordinals (Nth)
        for m2 in _re.finditer(r"-?\d[\d,]*(?:\.\d+)?%?", t):
            f = _norm(m2.group(0))
            if f is not None and not _hit(f):
                unmatched.append((sid, m2.group(0)))
    return unmatched


def stage_render(spec, base_dir, window_str, push, sample_slots=False):
    data_path = os.path.join(base_dir, DATA_JSON)
    slots_path = os.path.join(base_dir, SLOTS_JSON)
    if not os.path.exists(data_path):
        die(f"data.json not found (run --stage data first): {data_path}", 2)
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    rep = spec["content"]["report"]
    # dual-spec dual-form guard — when the second spec's queries disagree with data.json sections (label drift),
    # the render layer's data_by_label.get→None silently skips sections (the report quietly loses data sections with no signal). Compliant flows
    # (single spec / dual specs constrained to "queries exactly identical") are always equal; this validation has no false-positive surface
    spec_labels = [q["label"] for q in spec["content"]["queries"]]
    data_labels = [d["label"] for d in data["queries"]]
    if sorted(spec_labels) != sorted(data_labels):
        missing = [l for l in spec_labels if l not in data_labels]
        extra = [l for l in data_labels if l not in spec_labels]
        die(f"spec queries do not match data.json sections: missing {missing} / extra {extra}"
            f" (data.json is produced by --stage data — with dual specs in dual forms, both specs' queries must be exactly identical; "
            f"label drift causes the render to silently drop sections)", 2)
    outline_ids = [sec["section_id"] for sec in rep["outline"]]
    if sample_slots:
        slots = {sid: "(analysis text placeholder — at RUN time the LLM generates the actual interpretation per the locked outline)" for sid in outline_ids}
    else:
        if not os.path.exists(slots_path):
            die(f"analysis_slots.json not found (retry after the Agent generates it per the outline): {slots_path}", 2)
        with open(slots_path, encoding="utf-8") as f:
            slots = json.load(f).get("slots", {})
    slot_ids = list(slots.keys())
    if sorted(slot_ids) != sorted(outline_ids):
        missing = [i for i in outline_ids if i not in slots]
        extra = [i for i in slot_ids if i not in outline_ids]
        die(f"slot validation failed: missing {missing} / extra {extra} (keys must match the outline sections)", 2)

    window_str = data.get("window") or window_str
    any_failed = any(q.get("error") for q in data["queries"])
    # failed-section slot text discipline — a data.json section with error whose slot lacks a failure placeholder → WARN (a backstop observation on LLM diligence)
    if any_failed:
        err_labels = {q["label"] for q in data["queries"] if q.get("error")}
        for sec in rep["outline"]:
            bound = [l for l in sec.get("data_labels", []) if l in err_labels]
            if bound:
                text = slots.get(sec["section_id"], "")
                if "fetch failed" not in text and "data fetch failed" not in text:
                    log(f"[WARN] section [{sec['title']}] has bound query sections {bound} that failed to fetch, "
                    f"but the analysis text shows no failure placeholder — please check whether analysis_slots marks it faithfully")

    tpl = rep.get("template")
    if tpl == "card":
        # report card template — the message body itself is the card (no attachment); the fallback text is the full render_text_report output
        # (when the delivery layer cannot send the card it delivers as plain text, R5 delivery first; the ⚠ annotation chain applies to both card and fallback-text forms)
        card = render_card_report(spec, data, slots, window_str)
        fallback_text = render_text_report(spec, data, slots, window_str)
        result = {"window": window_str, "stage": "render", "form": "card", "slots": len(slots), "card": card}
        message_body, file_path, display_name = card, None, None
    elif isinstance(tpl, str) and (tpl.strip().startswith("<") or tpl in ("daily", "weekly", "monthly")):
        html_text = render_html_report(spec, data, slots, window_str)
        date_str = (window_str.split(" ")[0]).replace("-", "")
        file_sect = spec["content"].get("file") or {}
        file_name = (file_sect.get("name_template") or spec["delivery"].get("file_name")
                     or _default_report_filename(spec["task_name"], date_str)).replace("{date}", date_str)
        out_path = _safe_output_path(base_dir, file_name, "report output filename")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_text)
        size_kb = os.path.getsize(out_path) / 1024
        log(f"HTML rendering done: {out_path} ({size_kb:.1f} KB)")
        # the preview uses the full window range (a weekly/monthly report showing only the start date would be misread as single-day data)
        range_str = _window_range_str(spec["content"].get("window_freq", "daily"), window_str)
        preview = f"[Report] {spec['task_name']} ({range_str}) generated; see the attachment {file_name} ({size_kb:.0f} KB)"
        result = {"window": window_str, "stage": "render", "file": out_path, "slots": len(slots)}
        message_body = preview
        file_path, display_name = out_path, file_name
        card, fallback_text = None, None
    else:
        message_body = render_text_report(spec, data, slots, window_str)
        message_body, _ = _trim_to_kb(message_body, int(spec["content"]["max_message_kb"]),
                                      tail_note="…(report over length, truncated)")
        file_path, display_name = None, None
        result = {"window": window_str, "stage": "render", "message": message_body}
        card, fallback_text = None, None
    # form normalization: for the card form, "message" = the fallback text (used by the delivery layer's text backstop); for text/HTML forms, message = the message body itself
    message = fallback_text if card is not None else message_body

    # report number-consistency observation — number tokens in slot text loosely compared against actual values in data.json
    # (thousands separators/percentages/rounding/deltas all count as hits); unmatched numbers only WARN + go to run_result (the LLM transcription hallucination surface,
    # not blocking the push — report text contains legitimately derived numbers, die would kill them wrongly).
    # HTML reports are compared too (slot text is independent of file_path — the analysis numbers in the HTML attachment are what
    # the user actually reads; the previous whole-path exemption = zero observation; the value pool includes summary aggregates).
    unmatched_numbers = _check_slot_numbers(slots, data, spec)
    if unmatched_numbers:
        result["unmatched_numbers"] = unmatched_numbers
        log(f"[WARN] slot text contains {len(unmatched_numbers)} numbers not matching any data.json value"
            f" ({unmatched_numbers[:5]}... — LLM transcription observation; legitimately derived numbers also hit this warning, "
            f"decide after manual review; handling hallucinated numbers is the task owner's/ops' responsibility)")
    # report task SQL LIMIT hit → append the user-visible ⚠ to the tail of the message (preview line/text report)
    # (same standard as the data task's _run_data_task — reports previously never consumed limit_hit)
    limit_hits = [(q.get("label"), q.get("limit_hit")) for q in data.get("queries") or []
                  if q.get("limit_hit")]
    if limit_hits:
        # plain language for the user — "SQL cap/LIMIT" is a BUILD-time engineering concept; the user message only says "data may be incomplete";
        # the engineering admonition (LIMIT should be >= the row estimate cap) stays in stderr, already covered by the fetch layer's WARN.
        note = _integrity_note(limit_hits)   # shared implementation in three places (copy unchanged)
        message = message + "\n" + note
        result["limit_note"] = note
        if card is not None:
            # card form: the ⚠ also goes into a card element (inserted before the footer — aligned with the data task card standard)
            els = card.get("body", {}).get("elements") or []
            els.insert(max(len(els) - 1, 0), {"tag": "markdown", "content": note})
            result["card"] = card
    # a failed section whose slot text lacks a failure placeholder → automatically append a user-visible marker to the message tail
    # (the stderr WARN upgraded to message-visible, no die — compliant wording like "data unavailable" lacks the keyword and is not wrongly killed)
    if any_failed:
        silent_secs = []
        for sec in rep["outline"]:
            bound = [l for l in sec.get("data_labels", []) if l in err_labels]
            if bound:
                text = slots.get(sec["section_id"], "")
                if "fetch failed" not in text and "data fetch failed" not in text:
                    silent_secs.append(sec["title"])
        if silent_secs:
            note = (f"⚠ Data anomaly notice: the data sections bound to {', '.join(silent_secs)} failed to fetch this period; "
                    f"the corresponding analysis is based on incomplete data (automatic retry next period; if this recurs, contact the task owner)")
            message = message + "\n" + note
            result["failed_section_note"] = note
            if card is not None:
                els = card.get("body", {}).get("elements") or []
                els.insert(max(len(els) - 1, 0), {"tag": "markdown", "content": note})
                result["card"] = card

    if not push:
        result["dry_run"] = True
        write_run_result(result, base_dir)
        if card is not None:
            log("card message rendering done (structure recorded in run_result.json); fallback-text preview below")
        print(message if file_path is None else message + "\n(dry-run, not pushed)")
        sys.exit(1 if any_failed else 0)

    failures, push_results = deliver(spec, message, "text", file_path, display_name, card=card)
    result["push"] = push_results
    write_run_result(result, base_dir)
    if card is not None:
        log("card message delivered (structure recorded in run_result.json); fallback text: ")
    print(message)
    if failures:
        print(f"PUSH FAILED: {'; '.join(failures)}", file=sys.stderr)
        sys.exit(3)
    sys.exit(1 if any_failed else 0)


def _collect_report_data(spec, base_dir, window_str, start, end, target_date, is_weekly, is_monthly):
    """Report-task data fetch (one shared implementation for stage data and the BUILD full-pipeline trial run).
    In the BUILD full-pipeline context, all queries failing blocks with exit code 2 (prevents registering a broken spec as an automation)."""
    results = []
    for q in spec["content"]["queries"]:
        entry = {"label": q["label"], "mode": q.get("mode", "value"), "source": q.get("source", "sql")}
        try:
            entry["rows"] = run_query(q, spec, start, end, target_date, is_weekly, is_monthly)
            entry["summary"] = compute_summaries(q, entry["rows"])
        except Exception as e:
            entry["error"] = str(e)
            log(f"section {q['label']} query failed: {e}")
        results.append(entry)
    if all(r.get("error") for r in results):
        die(f"BUILD time: all queries failed: {results[0].get('error', '')}", 2)
    data = {"window": window_str, "queries": results}
    _dump_report_data_json(data, base_dir, spec)


# ---------- main ----------
def _csv_safe(v):
    """CSV formula-injection protection — values starting with = + - @ \t get a \' prefix (Excel will not execute the formula when opened).
    Numeric values are not prefixed (negative/signed numbers are data, not formulas — a prefix would make Excel treat them as text
    and the customer's secondary aggregation would compute wrong; a real formula string does not parse as a number, so it gets the prefix)"""
    s = str(v) if v is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t"):
        try:
            float(s)
            return s          # parses as a number → no injection surface, as-is
        except ValueError:
            pass
        return "'" + s
    return s


def _write_rows_csv(rows, out_csv):
    """Row set -> CSV file (utf-8-sig BOM + header on the first line, same shape as the adhoc export artifact)."""
    cols = []
    for r in rows:
        for k in r.keys():
            if k not in cols:
                cols.append(k)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([_csv_safe(r.get(c)) for c in cols])
    return out_csv


def _run_data_task(spec, base_dir, window_str, start, end, target_date, is_weekly, is_monthly, push):
    """data task main flow: fetch -> summary computed on the fly -> template fill -> (file section: row set to CSV) -> delivery."""
    content = spec["content"]
    results = []
    failed_any = False
    query_details = []
    for q in content["queries"]:
        entry = {"label": q["label"], "mode": q["mode"], "on_empty": q.get("on_empty", "push")}
        detail = {"label": q["label"]}
        try:
            if q.get("source", "sql") == "sql":
                detail["rendered_sql"] = render_sql(q["sql_template"], start, end, target_date, is_weekly, is_monthly)
            rows = run_query(q, spec, start, end, target_date, is_weekly, is_monthly)
            entry["rows"] = rows
            entry["summary"] = compute_summaries(q, rows)
            detail["row_count"] = len(rows)
            detail["sample_rows"] = rows[:SAMPLE_ROWS]
            if entry["summary"]:
                detail["summary"] = entry["summary"]
        except Exception as e:
            failed_any = True
            entry["error"] = str(e)
            detail["error"] = str(e)[:200]
            log(f"section {q['label']} query failed: {e}")
        results.append(entry)
        query_details.append(detail)

    # R3: all failed -> whole-message fetch-failure placeholder (push if possible), exit code 1
    if all(r.get("error") for r in results):
        message = (f"[Push] {spec['task_name']}\n{sep_line()}\n"
                   "Data fetch failed — see the task execution log (run_result.json) for details; automatic retry next period; if this recurs, contact the task owner.")
        write_run_result({"window": window_str, "message": message, "failed_any": True,
                          "dry_run": not push, "queries": query_details,
                          "error_detail": results[0].get('error', '')[:400]}, base_dir)
        print(message)
        if not push:
            sys.exit(1)
        failures, push_results = deliver(spec, message)
        # second write (R2 fix): restore error_detail/dry_run from the first write — the whole file is overwritten,
        # and dropping keys would void the "see run_result.json for details" pointer (the technical text would only remain as truncated queries[].error)
        write_run_result({"window": window_str, "message": message, "failed_any": True,
                          "dry_run": not push, "push": push_results, "queries": query_details,
                          "error_detail": results[0].get('error', '')[:400]}, base_dir)
        if failures:
            print(f"PUSH FAILED: {'; '.join(failures)}", file=sys.stderr)
            sys.exit(3)
        sys.exit(1)

    # R2: all sections skip with 0 rows (no failed sections) -> do not push an empty-shell message, exit code 0
    if all((not r.get("error")) and (not r.get("rows")) and r.get("on_empty") == "skip" for r in results):
        log("all sections on_empty=skip with 0 rows: not pushing")
        write_run_result({"window": window_str, "all_skipped": True, "dry_run": not push,
                          "queries": query_details}, base_dir)
        sys.exit(0)

    ctx = _Context(spec, results, window_str, start, end)

    # file section: row set to CSV (fetch=export already fetched in full, written locally; full data, no truncation)
    file_path, file_name, file_info = None, None, None
    f_sect = content.get("file")
    if f_sect:
        dq_label = f_sect["detail_query"]
        r = ctx.by_label.get(dq_label) or {}
        if r.get("error"):
            log(f"file section {dq_label} fetch failed: no file generated (message marks the failed section per R1)")
        elif not r.get("rows"):
            log(f"file section {dq_label} has 0 rows: no file generated (message follows on_empty semantics)")
        else:
            # {date} = window start date (YYYYMMDD; the file-name date aligns with the data window —
            # daily=yesterday, weekly=last Monday, monthly=the 1st of last month; range data (weekly/monthly) lands on the window start)
            date_str = start.strftime("%Y%m%d")
            file_name = f_sect["name_template"].replace("{date}", date_str)
            file_path = _safe_output_path(base_dir, file_name, "content.file.name_template")
            _write_rows_csv(r["rows"], file_path)
            file_info = {"n": len(r["rows"]), "name": file_name}
            log(f"file section done: {file_path} ({file_info['n']} rows, {os.path.getsize(file_path) / MB:.2f} MB)")

    # rendering (template fill) + R4 size guardrail (text path: halve the row set and re-render -> last-resort row-level trimming)
    # render-time exceptions (e.g. v.<column> referencing a nonexistent column) = invalid configuration: die 2, no bare traceback.
    # RUN-time run_result.json is already written above (fetch details inspectable); no delivery happens.
    try:
        message_body, form = render_message(spec, ctx, file_info)
    except QueryError as e:
        write_run_result({"window": window_str, "failed_any": failed_any, "dry_run": not push,
                          "queries": query_details, "render_error": str(e)}, base_dir)
        die(f"template rendering failed (invalid configuration): {e}", 2)
    except Exception as e:   # unexpected render-time exceptions also die 2 — prevents a bare traceback exiting 1 while masquerading as a fetch failure
        write_run_result({"window": window_str, "failed_any": failed_any, "dry_run": not push,
                          "queries": query_details,
                          "render_error": f"{type(e).__name__}: {e}"}, base_dir)
        die(f"template rendering failed (unexpected exception): {type(e).__name__}: {e}", 2)
    # sections that hit the SQL LIMIT get a user-visible annotation appended to the message body —
    # deliverable-integrity problems must not go only to the RUN sandbox's stderr (nobody looks); "Total X rows" and {{agg.*}} are computed over the
    # truncated row set, and the user must see the metric definition (does not block the push; exit code unchanged)
    for q in content["queries"]:
        if q.get("_total_dropped"):
            for d in query_details:
                if d["label"] == q["label"]:
                    d["total_rows_dropped"] = q["_total_dropped"]
    truncated = False
    if form in ("text", "rich"):
        limit = int(content["max_message_kb"])
        guard = 0
        try:
            while len(str(message_body).encode("utf-8")) > limit * 1024 and guard < 4:
                spec["content"]["message"]["preview_rows"] = max(5, _preview_rows(spec) // 2)
                message_body, form = render_message(spec, ctx, file_info)
                truncated = True
                guard += 1
        except Exception as e:   # the R4 size-guardrail re-render gets the same protection
            write_run_result({"window": window_str, "failed_any": failed_any, "dry_run": not push,
                              "queries": query_details,
                              "render_error": f"{type(e).__name__}: {e}"}, base_dir)
            die(f"template rendering failed (R4 re-render): {type(e).__name__}: {e}", 2)
        if len(str(message_body).encode("utf-8")) > limit * 1024:
            message_body, _ = _trim_to_kb(message_body, limit)
            truncated = True
        if truncated:
            log("message triggered R4 layered truncation")
    # the ⚠ integrity note is appended **after** truncation — previously appended before R4,
    # so once the text path triggered re-render/last-resort trimming, the note was lost with the message_body overwrite (hitting LIMIT + message over size
    # is exactly the common combination for large detail tasks — the very scenario where the note matters most was losing it)
    limit_hits = [(q["label"], q["_limit_hit"]) for q in content["queries"] if q.get("_limit_hit")]
    if limit_hits:
        # plain language for the user (same copy in three places: report path / card fallback) — engineering concepts stay out of user messages
        note = _integrity_note(limit_hits)   # shared implementation in three places (copy unchanged)
        if form in ("text", "rich"):
            message_body = message_body + "\n" + note
        elif isinstance(message_body, dict):
            body = message_body.get("body") or {}
            els = body.get("elements") or []
            els.insert(max(len(els) - 1, 0), {"tag": "markdown", "content": note})
            body["elements"] = els
        result_limit_note = note
    else:
        result_limit_note = None
    result = {"window": window_str, "failed_any": failed_any, "dry_run": not push,
              "queries": query_details, "form": form,
              "message": message_body if form in ("text", "rich") else "(card message; see run_result for the structure)"}
    if result_limit_note:
        result["limit_note"] = result_limit_note
    if form == "card":
        result["card"] = message_body
    if file_path:
        result["file"] = file_path
    write_run_result(result, base_dir)
    if form == "card":
        log("card message rendering done (structure recorded in run_result.json)")
    else:
        print(message_body)
    print(f"window: {window_str} | sections: {len(results)} | failed sections: {sum(1 for r in results if r.get('error'))}",
          file=sys.stderr)

    if not push:
        log("not pushed (--push / auto_push both disabled or DRY_RUN=1): message and run_result.json generated")
        sys.exit(1 if failed_any else 0)

    presentation = "rich" if form == "rich" else "text"
    card = message_body if form == "card" else None
    failures, push_results = deliver(spec, str(message_body) if card is None else _card_fallback_text(ctx, file_info),
                                     presentation, file_path, file_name, card=card)
    result["push"] = push_results
    write_run_result(result, base_dir)
    if failures:
        print(f"PUSH FAILED: {'; '.join(failures)}", file=sys.stderr)
        sys.exit(3)
    sys.exit(1 if failed_any else 0)  # R1: even if the placeholder push succeeds, a fetch failure still exits 1


def _card_fallback_text(ctx, file_info):
    """Fallback/text backstop message for card tasks (delivery first, R5 degradation semantics).
    Failed sections are likewise visible — failure placeholders also show in the fallback text (consistent with the built-in card rendering's R1 contract; no silent section drops)."""
    lines = [f"[Push] {ctx.spec['task_name']} {ctx.range_str}", sep_line()]
    for r in ctx.by_label.values():
        if r.get("error"):
            lines.append(f"{r['label']}: [fetch failed]")   # failure-section truncation length unified with the built-in templates (120)
            continue
        if r.get("mode") == "value":
            row0 = _value_row0(r)
            parts = [f"{_display_col(k)}: {_fmt_value(v)}" for k, v in (row0 or {}).items()]
            if parts:
                lines.append(f"{r['label']}: " + " / ".join(parts))
        elif r.get("rows"):
            lines.append(f"{r['label']} ({len(r['rows'])} rows)")
    if ctx.agg:
        lines.append("Summary: " + " / ".join(f"{k}: {_fmt_value(v)}" for k, v in ctx.agg.items()))
    if file_info:
        lines.append(f"Total {file_info['n']} rows; file {file_info['name']} generated")
    # the fallback text also carries the ⚠ integrity note — the fallback scenario is "what the user finally sees",
    # precisely where the metric-definition annotation must not be lost
    limit_hits = [(q["label"], q["_limit_hit"])
                  for q in (ctx.spec.get("content") or {}).get("queries") or [] if q.get("_limit_hit")]
    if limit_hits:
        # plain language for the user (same copy in three places)
        lines.append(_integrity_note(limit_hits))   # shared implementation in three places (copy unchanged)
    lines += [sep_line(), "# Data generated automatically by scheduled-push"]
    return "\n".join(lines)


def render_card_report(spec, data, slots, window_str):
    """Report card template: an in-group Feishu card 2.0 — KPI rows (value queries) + VChart charts (rows+chart queries)
    + detail tables (rows queries without chart, preview_rows display-layer truncation + total row count) + section analysis (slot text, outline order).
    Blueprint = the monthly-report card verified in practice (the user-accepted form). Data sections follow the queries declaration order; analysis sections follow the outline order — deterministic.
    No attachment (the message body itself is the card); when the card cannot be sent, the delivery layer degrades to the text report passed in by the caller (delivery first, R5).
    Plain layout: none of the HTML template's KPI-card grid / risk-section amber visual system — card markdown/table/chart components laid out flat;
    layout customization belongs to the inline HTML template domain (built-in templates own structure, not visual flourish)."""
    rep = spec["content"]["report"]
    queries = {q["label"]: q for q in spec["content"]["queries"]}
    data_by_label = {d["label"]: d for d in data["queries"]}
    range_str = _window_range_str(spec["content"].get("window_freq", "daily"), window_str)
    title = (spec["content"].get("title_template") or "[Report] {{task_name}} {{window_range}}") \
        .replace("{{task_name}}", spec["task_name"]).replace("{{window_range}}", range_str) \
        .replace("{{date}}", window_str.split(" ")[0])
    els = [{"tag": "markdown", "content": f"Stats window: {range_str}"}]
    # data sections: value → KPI row; rows+chart → VChart; rows without chart → table component
    for q in spec["content"]["queries"]:
        lbl = q["label"]
        d = data_by_label.get(lbl)
        if d is None:
            continue
        if d.get("error"):
            els.append({"tag": "markdown", "content": f"**{lbl}**: [fetch failed]"})
            continue
        if d.get("mode") == "value":
            row0 = _value_row0(d)
            parts = [f"**{_display_col(k)}**: {_fmt_value(v)}" for k, v in (row0 or {}).items()]
            els.append({"tag": "markdown", "content": f"**{lbl}**: " + (" / ".join(parts) if parts else "-")})
        else:
            rows = d.get("rows") or []
            if not rows:
                els.append({"tag": "markdown", "content": f"**{lbl}**: no data this period"})
                continue
            # row count uses total_rows (after the data.json cap, len(rows) is only the truncated count)
            total_n = d.get("total_rows", len(rows))
            els.append({"tag": "markdown", "content": f"**{lbl}** (Total {total_n} rows)"})
            shown = rows[:_preview_rows(spec)]
            chart = q.get("chart")
            if chart:
                els.append({"tag": "chart", "chart_spec": {
                    "type": "bar" if chart == "bar" else "line",
                    "data": [{"id": "data", "values": _rows_to_long(shown)}],
                    "xField": "date", "yField": "value", "seriesField": "metric",
                    "legends": {"visible": True, "orient": "top"},
                }})
            else:
                cols = list(rows[0].keys())
                columns = [{"name": str(c), "display_name": _display_col(str(c))} for c in cols]
                tbl_rows = [dict((str(k), _fmt_value(v, plain=True)) for k, v in row.items()) for row in shown]
                els.append({"tag": "table", "columns": columns, "rows": tbl_rows})
            if total_n > _preview_rows(spec):
                els.append({"tag": "markdown",
                            "content": f"showing the first {_preview_rows(spec)} rows in the card"})
    # section analysis: slot text = bulleted short sentences (writing-spec constraint), carried directly by markdown components
    for sec in rep["outline"]:
        els.append({"tag": "markdown", "content": f"**▍{sec['title']}**"})
        text = slots.get(sec["section_id"], "")
        if text:
            els.append({"tag": "markdown", "content": text})
    card = {
        "schema": "2.0",
        "config": {},
        "header": {"title": {"tag": "plain_text", "content": title}},
        "body": {"direction": "vertical", "elements": els + [
            {"tag": "markdown", "content": "# Data generated automatically by scheduled-push"}]},
    }
    return card


def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        print(__doc__.strip() if __doc__ else "scheduled-push push_deliver.py")
        print("Usage: python3 push_deliver.py <push_spec.json> [--push] | --check-spec | --stage data|render")
        sys.exit(0)
    if "--check-spec" in args:
        # pure static validation: runs only load_spec (structure/enums/placeholder reference existence/WARN reconciliation),
        # no fetch, no push, no network — the review and release gate (all five forms passing the self-check spec = no drift)
        args = [a for a in args if a != "--check-spec"]
        args = [a for a in args if not a.startswith("-")] or []
        if not args:
            die("Usage: python3 push_deliver.py <push_spec.json> --check-spec (spec path missing)", 2)
        spec = load_spec(args[0])
        print(f"[push_deliver] SPEC OK: {args[0]} (static validation passed — structure/enums/placeholder references/field reconciliation)")
        sys.exit(0)
    stage = None
    if "--stage" in sys.argv:
        i = sys.argv.index("--stage")
        if i + 1 >= len(sys.argv) or sys.argv[i + 1] not in ("data", "render"):
            die("--stage value must be data or render", 2)
        stage = sys.argv[i + 1]
    push_flag = "--push" in sys.argv
    # backfill window override (--window-date YYYY-MM-DD): recompute the last complete period anchored to "that day's 00:00 viewpoint" —
    # to backfill yesterday's daily report after a missed run/failure, use --window-date today; a bare rerun the next day would push the new last period (original behavior)
    anchor_date = None
    argv_rest = list(sys.argv[1:])
    if "--window-date" in argv_rest:
        i = argv_rest.index("--window-date")
        if i + 1 >= len(argv_rest):
            die("Usage: --window-date YYYY-MM-DD (date value missing)", 2)
        try:
            anchor_date = datetime.datetime.strptime(argv_rest[i + 1], "%Y-%m-%d").date()
        except ValueError:
            die(f"--window-date date format invalid: {argv_rest[i + 1]} (expected YYYY-MM-DD)", 2)
        del argv_rest[i:i + 2]
    spec_args = [a for a in argv_rest if not a.startswith("-")]
    if not spec_args:
        die(f"Usage: python3 push_deliver.py <push_spec.json> [--push] [--window-date YYYY-MM-DD]"
            f" | --check-spec | --stage data|render (spec path missing; received: "
            f"{' '.join(sys.argv[1:]) or '(empty)'})", 2)
    spec = load_spec(spec_args[0])
    spec_path = spec_args[0]
    base_dir = os.path.dirname(os.path.abspath(spec_path)) or "."

    cli = _cli_path(spec)
    # SCHEDULED_PUSH_DRY_RUN=1 suppresses all real pushes (including auto_push/--push) — the safety net for BUILD reruns
    push = (spec.get("auto_push", False) or push_flag) and not DRY_RUN
    if DRY_RUN and (spec.get("auto_push", False) or push_flag):
        log("[DRY_RUN] SCHEDULED_PUSH_DRY_RUN=1 has suppressed the push (auto_push/--push take no effect)")
    if anchor_date is not None:
        if stage == "render":
            die("--window-date and --stage render cannot be combined (render reads the window from data.json; "
                "a backfill must run the full two stages starting from --stage data)", 2)
        log(f"[backfill] window recomputed anchored to the {anchor_date} viewpoint (not rolling by the current moment)")

    try:
        cur_ver = subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except FileNotFoundError:
        die(f"ae-cli missing: {cli} (env.ae_cli_path / spec.cli configure the execution path)", 1)
    except subprocess.TimeoutExpired:
        cur_ver = ""
    if spec.get("cli_version") and cur_ver != spec["cli_version"]:
        log(f"[WARN] ae-cli version drift: BUILD={spec['cli_version']} / RUN={cur_ver} (warning only)")

    start, end, target_date = compute_window(spec, anchor_date=anchor_date)
    is_weekly = spec["content"]["window_freq"] == "weekly"
    is_monthly = spec["content"]["window_freq"] == "monthly"
    window_str = f"{start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%Y-%m-%d %H:%M')}"
    log(f"window: {window_str}")

    is_report = spec["content"]["kind"] == "report"
    if stage == "data":
        if not is_report:
            die("--stage is for report tasks only (content.kind=report)", 2)
        stage_data(spec, base_dir, window_str, start, end, target_date, is_weekly, is_monthly, push)
    if stage == "render":
        if not is_report:
            die("--stage is for report tasks only (content.kind=report)", 2)
        stage_render(spec, base_dir, window_str, push)
    if is_report:
        # BUILD trial-run full pipeline: data -> placeholder slots -> render preview (no push).
        # a report task's first real push uses the two-stage flow (--stage data -> write analysis -> --stage render --push);
        # full pipeline + --push is rejected (prevents pushing placeholder analysis text into a real group).
        if push_flag or spec.get("auto_push"):
            if not DRY_RUN:
                die("report tasks cannot use full-pipeline --push for the first push (it would push placeholder analysis text). "
                    "First push goes two-stage: --stage data -> write analysis_slots.json -> --stage render --push", 2)
        log("report task full-pipeline trial run: data + placeholder analysis + render preview")
        _collect_report_data(spec, base_dir, window_str, start, end, target_date, is_weekly, is_monthly)
        stage_render(spec, base_dir, window_str, push=False, sample_slots=True)

    _run_data_task(spec, base_dir, window_str, start, end, target_date, is_weekly, is_monthly, push)


if __name__ == "__main__":
    main()
