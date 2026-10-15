#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Translate ae-cli 1.x command lines into 6.x capability calls, and map the
6.x response back into the shape 1.x callers already parse.

Why this module exists
----------------------
Two ae-cli majors coexist on real machines and they are not compatible:

* 1.x hard-codes a command per backend tool (`engage +task_list`).
* 6.x is a thin shell over a capability gateway: the capability list is pulled
  from the server, so `--help` cannot reveal it and the old command names are
  gone. The equivalent call is
  `capability run engage-task.task.list --input '{"project_id":61,...}'`.

The 6.x response also differs in shape, not just in naming: the payload is
wrapped in `result` and every field is snake_case, while 1.x returned it
unwrapped and camelCase.

Keeping both adaptations here - in front of `_ae.run_ae` - means the twenty
scripts that drive ae-cli never learn which major they are talking to. That is
deliberate: the analysis logic is the valuable part of this skill and it should
not be coupled to a CLI generation.

No third-party dependencies: standard library only.
"""
import json
import os
import re

# ---------------------------------------------------------------------------
# command mapping
# ---------------------------------------------------------------------------
# Capability ids are the stable name of a backend operation. They are a better
# thing to bind to than the CLI command names, which 6.x reorganises freely.
#
# Naming is not uniform across domains - `engage-*` domains use kebab-case
# while `analysis` / `metadata` use snake_case in the id itself. That is the
# server's choice, so it is reproduced verbatim here.
CAPABILITY = {
    ("engage", "+task_list"): "engage-task.task.list",
    ("engage", "+task_detail"): "engage-task.task.get",
    ("engage", "+task_data_overview"): "engage-task.task-data.overview",
    ("engage", "+task_data_detail"): "engage-task.task-data.detail",
    ("engage", "+task_experiment_report"): "engage-task.task-data.experiment-report",
    ("engage", "+flow_list"): "engage-flow.flow.list",
    ("engage", "+flow_detail"): "engage-flow.flow.get",
    ("engage", "+flow_node_overview_report"): "engage-flow.report.node-overview",
    ("engage", "+flow_node_detail_report"): "engage-flow.report.node-detail",
    ("engage", "+flow_process_report"): "engage-flow.report.process",
    ("engage", "+flow_ab_split_node_report"): "engage-flow.report.ab-split-node",
    ("engage", "+config_item_list"): "engage-scene.config-item.list",
    ("engage", "+config_item_trigger_report"): "engage-scene.report.config-item-trigger",
    ("engage", "+config_item_strategy_comparison"): "engage-scene.report.config-item-analysis",
    ("analysis_meta", "+list_events"): "metadata.event.list",
    ("analysis_meta", "+list_properties"): "metadata.property.list",
    ("analysis_audience", "+list_clusters"): "analysis.user_cluster.list",
    ("analysis_audience", "+list_tags"): "analysis.user_tag.list",
}

# Commands with no capability equivalent. The gateway routes by project, so
# "which projects can I see" cannot itself be a capability - 6.x keeps it as a
# plain CLI command.
CLI_FALLBACK = {
    ("analysis_common", "+list_projects"): ["project", "info", "list"],
}

# ---------------------------------------------------------------------------
# argument mapping
# ---------------------------------------------------------------------------
# Capability input is a JSON object whose keys are the 1.x flag names verbatim,
# which is what makes this translation mechanical rather than a rewrite. Only
# the short aliases and a few scalar-vs-array shapes differ.
FLAG_ALIAS = {
    "-p": "project_id",
    "--project-id": "project_id",
    "--project_id": "project_id",
    "-q": "queries",
    "--q": "queries",
    "--limit": "limit",
    "--fields": "fields",
    "--offset": "offset",
}

INT_KEYS = frozenset((
    "project_id", "limit", "offset", "data_view_type", "preview_rows",
    "timeout_seconds", "page_num", "page_size", "show_time_zone",
))

BOOL_KEYS = frozenset((
    "authenticated_only", "use_cache", "analyze_report_internal_query",
))

# 1.x passes these as a JSON *string* on the command line; capability input
# wants the parsed value.
JSON_KEYS = frozenset((
    "req", "fields", "queries", "resolutions", "definition", "qp",
    "template_id_list", "strategy_id_list",
))

# Flags that carry a single scalar in 1.x but an array in the capability schema.
ARRAY_KEYS = frozenset(("queries", "template_id_list", "strategy_id_list"))

# `--fields '["eventName"]'` names *columns*, and 6.x spells columns the way
# the server does - snake_case. Passing the 1.x camelCase spelling does not
# raise; the response comes back with every requested column null, which is the
# worst failure mode available here: structurally valid, semantically empty.
FIELD_VALUE_KEYS = frozenset(("fields",))


def _split_flag(token):
    """`--key=value` -> ("--key", "value"); `--key` -> ("--key", None)."""
    if token.startswith("--") and "=" in token:
        name, value = token.split("=", 1)
        return name, value
    return token, None


def camel_to_snake(name):
    """`eventName` -> `event_name`, the spelling 6.x column lists expect."""
    return re.sub(r"([A-Z])", lambda m: "_" + m.group(1).lower(), name)


def _coerce(key, raw):
    if raw is None:
        return True
    if key in JSON_KEYS:
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            parsed = raw
        if key in ARRAY_KEYS and not isinstance(parsed, list):
            parsed = [parsed]
        if key in FIELD_VALUE_KEYS and isinstance(parsed, list):
            parsed = [camel_to_snake(str(x)) for x in parsed]
        return parsed
    if key in INT_KEYS:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw
    if key in BOOL_KEYS:
        return str(raw).lower() in ("1", "true", "yes")
    return raw


def parse_flags(args):
    """Turn a 1.x tail (`["--project_id","61","--task_id","0027"]`) into a dict.

    Flags may be `--key value`, `--key=value` or a bare switch. Values that
    merely look like they start with "-" are kept: ids and dates do not, but a
    negative offset would.
    """
    out = {}
    i = 0
    while i < len(args):
        token = args[i]
        if not token.startswith("-"):
            i += 1
            continue
        name, inline = _split_flag(token)
        name = FLAG_ALIAS.get(name, name.lstrip("-").replace("-", "_"))
        if inline is not None:
            out[name] = _coerce(name, inline)
        elif i + 1 < len(args) and not args[i + 1].startswith("--"):
            out[name] = _coerce(name, args[i + 1])
            i += 1
        else:
            out[name] = _coerce(name, None)
        i += 1
    return out


def command_key(args):
    """First two tokens of a 1.x invocation, or None when it is not one."""
    if len(args) >= 2 and args[1].startswith("+"):
        return (args[0], args[1])
    return None


def _cli_flags(tail):
    """1.x flag tail -> flags for a plain 6.x CLI command.

    6.x spells its flags kebab-case (`--offset`, `--limit`, `--page-size`) where
    1.x writes some of them with underscores; values pass through untouched.
    A fallback command used to drop the tail wholesale, which silently turned
    `+list_projects --offset 50` into page 1 - so paging was impossible and the
    caller could not tell a truncated list from a short one.
    """
    out, i = [], 0
    while i < len(tail):
        name, inline = _split_flag(tail[i])
        if name.startswith("--"):
            flag = "--" + name[2:].replace("_", "-")
            if inline is not None:
                out.append(flag + "=" + inline)
            elif i + 1 < len(tail) and not tail[i + 1].startswith("-"):
                out.extend([flag, tail[i + 1]])
                i += 1
            else:
                out.append(flag)
        else:
            out.append(tail[i])
        i += 1
    return out


def translate(args):
    """1.x argv -> 6.x argv; None when the call has no 6.x equivalent.

    Returning None (rather than raising) lets `_ae.run_ae` fall back to the
    original argv, so a command this table has not learned yet degrades to the
    old behaviour instead of breaking outright.
    """
    key = command_key(args)
    if key is None:
        return None
    if key in CLI_FALLBACK:
        return list(CLI_FALLBACK[key]) + _cli_flags(list(args)[2:])
    cap = CAPABILITY.get(key)
    if not cap:
        return None
    payload = parse_flags(list(args)[2:])
    return ["capability", "run", cap, "--input",
            json.dumps(payload, ensure_ascii=False, sort_keys=True)]


# ---------------------------------------------------------------------------
# response mapping
# ---------------------------------------------------------------------------
# 6.x renames every field to snake_case and wraps some payloads in `result`.
# The rename is mechanical apart from a handful of acronyms, which are listed
# explicitly: guessing them would silently hand callers a None where a value
# used to be, which is exactly the failure mode this skill is built to avoid.
FIELD_SPECIAL = {
    "operation_task_dtos": "operationTaskDTOS",
    "dtos": "DTOS",
    "qp": "QP",
    "id": "id",
}

_CAMEL_RE = re.compile(r"_([a-z0-9])")


def snake_to_camel(name):
    """`operation_task_dtos` -> `operationTaskDtos` (see FIELD_SPECIAL)."""
    if name in FIELD_SPECIAL:
        return FIELD_SPECIAL[name]
    if "_" not in name:
        return name
    return _CAMEL_RE.sub(lambda m: m.group(1).upper(), name)


def normalize(value):
    """Recursively rename snake_case keys to the camelCase 1.x names."""
    if isinstance(value, dict):
        return {snake_to_camel(k): normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def unwrap_result(data):
    """Peel the 6.x `result` wrapper when it is the payload's only key.

    Some domains wrap (`{"result": {...}}`), others do not (`{"events": [...]}`),
    so the wrapper is detected rather than assumed - a domain that happens to
    have a legitimate `result` field alongside others keeps its shape.
    """
    if isinstance(data, dict) and len(data) == 1 and "result" in data:
        inner = data["result"]
        return inner if isinstance(inner, dict) else data
    return data


def normalize_envelope(resp):
    """Map a 6.x envelope onto the shape 1.x callers already parse."""
    if not isinstance(resp, dict):
        return resp
    data = resp.get("data")
    if not isinstance(data, dict):
        return resp
    out = dict(resp)
    out["data"] = normalize(unwrap_result(data))
    return out


# ---------------------------------------------------------------------------
# ad-hoc analysis: the unified 6.x contract
# ---------------------------------------------------------------------------
# Mode B needs an ad-hoc analysis, and 6.x exposes exactly one way to run it:
#
#   analysis adhoc run --model-type <m> --definition <json>
#
# There is no intermediate query-payload step: raw QP is rejected outright, and
# an argv-per-command translation cannot express the call because the
# definition is a nested object rather than a flag tail. That is why this lives
# in a dedicated builder instead of in `translate()`.
#
# The definition is not a new payload format to learn: it is the model's own
# arguments collected under a single object, plus the time range respelled.
# Established by running the protocol against a live host and comparing the
# returned rows, not by reading the schema.
ADHOC_CAPABILITY = "analysis.adhoc.run"

# `--time_range` inner keys. 6.x accepts only the snake_case spelling; a caller
# may still hand in the camelCase one, so it is respelled on the way in:
#
#   {"startTime": "..."} -> {"start_time": "..."}
#
# `mode` / `unit` / `value` are passed through unchanged. A caller may supply
# either spelling; the outgoing form is always snake_case.
TIME_RANGE_KEYS = {
    "v1": {"start_time": "startTime", "end_time": "endTime"},
    "v6": {"startTime": "start_time", "endTime": "end_time"},
}


def time_range_for(time_range, variant):
    """Respell a time range for the target generation.

    Both spellings are accepted on the way in, so a caller never has to know
    which major it is talking to.
    """
    if not isinstance(time_range, dict):
        return time_range
    mapping = TIME_RANGE_KEYS.get(variant) or {}
    return {mapping.get(k, k): v for k, v in time_range.items()}


def discriminator_filter(discriminator, variant):
    """intake `discriminator` -> a global FilterRequest, for 6.x only.

    The discriminator is the property that marks this specific send
    (`strategy_id` / `campaign` / `channel`). Turning it into a query filter is
    what isolates this campaign's events from overlapping sends inside the same
    time window - without it the audience is approximated by the window alone.

    The FilterRequest shape (`field` + `operator` + `values`) is the 6.x
    AI-facing contract. A runtime that is not 6.x gets None back, so the
    "not applied" state is recorded in meta rather than a filter that
    silently matches nothing.
    """
    if variant != "v6" or not isinstance(discriminator, dict):
        return None
    prop = discriminator.get("property")
    value = discriminator.get("value")
    if not prop or value is None:
        return None
    field_type = discriminator.get("type") or "event_property"
    return {
        "field": {"name": str(prop), "type": field_type},
        "operator": "eq",
        "values": [str(value)],
    }


def v6_request_id(request_id):
    """`mcp_<32 hex>` -> `cli_<32 hex>`, or None when it does not fit.

    6.x pins the prefix in its input schema (`^cli_[0-9a-f]{32}$`), so a 1.x
    style id would be rejected rather than ignored. The lifecycle id is
    optional there, so an id that cannot be respelled is dropped instead of
    being sent in a form the server refuses.
    """
    if not request_id:
        return None
    core = request_id.split("_", 1)[1] if "_" in request_id else request_id
    if re.fullmatch(r"[0-9a-f]{32}", core):
        return "cli_" + core
    return None


def adhoc_definition(params, time_range):
    """1.x build arguments -> 6.x AI-facing definition.

    Every build argument keeps its own name and value; only the time range is
    respelled. Unknown keys are passed through rather than filtered: the
    definition schema rejects them explicitly, and a silent drop here would
    turn a rejected field into a query that quietly answers a different
    question.
    """
    definition = {"time_range": time_range_for(time_range, "v6")}
    for key, value in (params or {}).items():
        definition[key] = value
    return definition


def adhoc_capability_argv(model_type, project_id, params, time_range,
                          request_id=None):
    """The 6.x form of one ad-hoc analysis, as an argv tail."""
    payload = {
        "project_id": int(project_id),
        "model_type": model_type,
        "definition": adhoc_definition(params, time_range),
    }
    rid = v6_request_id(request_id)
    if rid:
        payload["request_id"] = rid
    return ["capability", "run", ADHOC_CAPABILITY, "--input",
            json.dumps(payload, ensure_ascii=False, sort_keys=True)]


# ---------------------------------------------------------------------------
# task-row fields
# ---------------------------------------------------------------------------
# 6.x trims task rows, and by a lot on the paged list endpoint: 72 fields under
# 1.x become 34, dropping `planNum`, `clusterUserNum`, `groupContentList` and
# more. The per-task endpoint keeps far more (72 -> 50) and retains every field
# this skill reads, which is why metadata lookups go through _ae.find_task() -
# point lookup first, list scan only as a fallback.
#
# Verified on the same host with the same credentials and the same task, so the
# list-scan path is the one to be careful with, not the normal one.
#
# Nothing here needs a caveat today. The guard exists because an absent field is
# indistinguishable from a null one at the call site: should a future build trim
# task.get as well, fetch_engage_reports.note_missing_task_fields() turns that
# into a recorded degradation rather than a silently blank report.
V6_TASK_ROW_FIELDS_AT_RISK = {
    "planNum": "cross-day cumulative plan count; compared against the per-user "
               "`plan` in the caveat block",
    "clusterUserNum": "audience size recorded on the task row",
    "groupContentList": "task group membership",
    "triggerCrontab": "cron expression, rendered as 触发规则",
}

# The variant probe lives in _env rather than here: which generation is
# installed is an environment question, not a translation one.

