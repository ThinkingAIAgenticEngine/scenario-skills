# Mode B - Ad-hoc Analysis Command Reference

Mode B reconstructs campaign performance from tracking events when the customer
sent through their own platform. There is no canvas id, so the chain is:
resolve event names -> build one AI-facing definition -> run it.

## One call site, one protocol

ae-cli 6.x runs an ad-hoc analysis as a single unified call, so
`scripts/fetch_event_analysis.py` never calls it directly - it calls
`_ae.adhoc_run(ae, project_id, model_type, time_range, params)` and gets
`{"title", "rows"}` back.

| | unified 6.x contract |
|---|---|
| protocol | **one call** |
| shape | `analysis adhoc run --model-type <m> --definition <json>` (capability `analysis.adhoc.run`) |
| raw QP | **rejected outright** |
| returns | `data.{title,rows}`, plus `has_more` / `query_context_id` |

The definition is not a new payload format to learn: it is the model's own
arguments collected under one object, plus the time range respelled. So
`--funnel <json>` becomes `definition.funnel`, `--metrics <json>` becomes
`definition.metrics`, and so on - the parameter names are identical.

```bash
ae-cli capability run analysis.adhoc.run --input '{
  "project_id": <PID>, "model_type": "funnel",
  "definition": {"time_range": <TR-snake>, "funnel": <FUNNEL>},
  "request_id": "cli_<32 hex>" }'                          # -> rows
```

The equivalent CLI form is
`ae-cli analysis adhoc run -p <PID> --model-type funnel --definition '<json>'`;
agents should normally pass `--preview-rows 100` and fall back to
`analysis adhoc export` for full, unknown-size, timed-out, or long-running data.

### Fields whose spelling is pinned by the contract

A misspelled field is **rejected**, not normalised, so spelling is a hard
constraint rather than a style choice.

| field | required spelling |
|---|---|
| time range start | `start_time` |
| time range end | `end_time` |
| lifecycle id | `cli_<32 hex>` (`^cli_[0-9a-f]{32}$`), optional |

`mode` / `unit` / `value` inside the time range are passed through unchanged.
`--time-range` on `fetch_event_analysis.py` accepts either the camelCase or the
snake_case spelling of the start/end keys and respells it to snake_case before
sending.

### The result columns are not `index + 1`

The funnel result interleaves a conversion column after every step but the
first:

```
[Totals, Step1, Step2, Conv2, Step3, Conv3, Step4, Conv4, ...]   len == 2 * steps
```

So for a 3-step funnel the counts are at columns 1, 2 and **4** - column 3 is
the second step's conversion. Reading positionally lands on `"85.99%"`; the
`int()` conversion throws, and the stage reports `0`, which is indistinguishable
from a real zero. Verified for 2..5 steps against a real project.

`fetch_event_analysis.resolve_step_columns()` resolves them from the header's
parenthesised step marker (`(Step1)` / `(步骤1)`), falls back to the
`len(title) == 2 * steps` layout when no marker is present, and reports the step
as *unknown* when neither reading agrees.

### The summary row's caption is not stable

Row 0 is the platform's summary row, but it is rendered in the caller's
language and the language **switches between calls on the same host** - one
`Overview`, the next `阶段汇总`. `canonical_label()` relabels row 0 to `total`,
which is the token `parse_time_series()` and `timeline_days()` already look for;
matching on the caption instead would score it as an extra day in the trend and
let a total row masquerade as a date.

### Truncation

The synchronous preview sets `has_more`, whose row budget is fixed
(`preview_rows`, and a `timeout_seconds` cap). `adhoc_run()` returns it as
`hasMore`; the fetch step records it in `meta.truncated`, which becomes a
`结果完整性` degradation. For long windows or unknown-size results use
`analysis adhoc export` instead of `run`.

## `--time_range`

```json
{"mode": "custom", "start_time": "2026-08-01", "end_time": "2026-09-14"}
```

`mode` accepts `recent`, `previous`, `custom`, `start_to_today`,
`start_to_yesterday`. Use `custom` whenever the campaign window is known.

The start/end keys must be `start_time` / `end_time` (snake_case); the
camelCase spelling is rejected. `--time-range` on `fetch_event_analysis.py`
accepts either and respells it.

`request_id` is **not** an asynchronous handle. It is optional and, when
supplied, must match `cli_` + 32 lowercase hex. Generate one per call:

```python
"cli_" + uuid.uuid4().hex
```

`_cmdtree.v6_request_id()` reprefixes an `mcp_`-style id if one is handed in,
and drops an id it cannot respell.

## `--model_type` values

`event`, `retention`, `funnel`, `distribution`, `attribution`, `heat_map`,
`interval`, `path`, `rank_list`, `prop_analysis`, `sql`, `revenue` - 12
AI-facing models (9 common + `heat_map` / `rank_list` / `revenue`). Tags and
cohorts/clusters are separate capabilities, not `model_type` values.

## Funnel builder

```bash
# one call; the model's own objects, grouped under `definition`
ae-cli capability run analysis.adhoc.run --input '{
  "project_id": <PID>, "model_type": "funnel",
  "definition": {
    "time_range": {"mode":"custom","start_time":"2026-08-01","end_time":"2026-09-14"},
    "funnel": {"steps":[{"event":"ops_view"},{"event":"ops_click"}],
               "window":{"value":24,"unit":"hour"}}}}'
```

Build notes:

* the step field is `event` - `eventName` is rejected
* `window` is the attribution window and becomes `windows_gap_ms` +
  `windows_gap_tu` in the generated query
* `unit` accepts `hour`, `day`, `minute`
* funnel step filters use `event_property_name` (not `field`) and
  string-array values, including `"true"`/`"false"` for boolean properties

**Event names are resolved server-side.** Passing `push_view` yields the display
name `push到达` in the returned `title`. Approximate names are acceptable, but a
name that matches nothing returns empty rows rather than an error, so the
name must still be confirmed with the user.

## Event builder

```bash
ae-cli capability run analysis.adhoc.run --input '{
  "project_id": <PID>, "model_type": "event",
  "definition": {"time_range": {...},
                 "metrics": [{"event":"ops_view","aggregation":"user_count"}],
                 "time_particle_size": "day"}}'
```

* `aggregation` is required on a plain event metric (a formula metric may omit
  it). `count`, `uv` and `event_count` are all rejected; `user_count` works.
* `time_particle_size day` produces the per-day rows used for the trend sheet.
* `groups` adds a grouping dimension, used for segment and strategy comparison.

## Return shape

```json
{
  "title": ["Time", "到达", "点击", "商城购买"],
  "rows": [
    ["Overview", "52000", "1870", "214"],
    ["2026-09-14", "5000", "190", "19"]
  ]
}
```

`rows[0]` is the summary row; the remaining rows are per-period. Its caption is
rendered in the caller's language and **switches between calls** - `Overview` on
one, `阶段汇总` on the next, same host, same credentials - so it is identified
by position, never by text. Counts come back as ints.

`fetch_event_analysis.py` normalises this into the same shape mode A produces,
which is what lets stages 3-5 run with zero branching.

For a funnel the title interleaves a conversion column after every step but the
first, so the counts are not at `index + 1` - for three steps they are at
columns 1, 2 and **4**:

```json
["Totals", "到达(Step1)", "点击(Step2)", "Step2 Conversion", "购买(Step3)", "Step3 Conversion"]
```

`len(title) == 2 * steps` holds for every funnel size checked (2..5). See
`resolve_step_columns()`. The response also carries `has_more` alongside the
rows; a truncated result that is not declared reads exactly like a complete one.

## Metadata search

The 6.x CLI forms are the ones below; the skill's scripts describe the same
lookups through `_ae.run_ae()` and `_cmdtree.py` maps them onto the equivalent
capability calls (`metadata.event.list`, `metadata.property.list`,
`analysis.user_cluster.list`, `analysis.user_tag.list`). `--fields` takes
**snake_case** column names; a camelCase spelling does not raise, it comes back
with every requested column null.

### Events
```bash
ae-cli analysis-meta event list -p <PID> --queries '["push"]' \
  -f '["event_name","event_desc"]' --limit 50
```
Fuzzy-matches the event name and description server-side.
The returned `event_desc` is a human label in the project's own language - show
it to the user rather than the raw name.

> `ai_remark` is advertised as a returnable field in `--help` but the server
> rejects it with `INVALID_FIELDS`. Request only `event_name` and `event_desc`.

### Properties
```bash
ae-cli analysis-meta property list -p <PID> --queries '["strategy"]' \
  --scope event -f '["prop_name","prop_desc"]' --limit 50
```
`--scope` is `event` or `user`. Event properties are returned with the
`#<table>.` prefix, e.g. `#ops_receipt_properties.ops_strategy_id`.

### Audiences
```bash
ae-cli analysis user-cluster list -p <PID> --limit 50
ae-cli analysis user-tag list     -p <PID> --limit 50
```
Both take `-l` / `--limit` and `-o` / `--offset`, like `analysis-meta`.
Returned tag identifiers use the canonical `tag_name`.

Cluster names generated by Engage look like `engage_<taskId>_<ts>_cohort`,
which is useful for cross-checking that a described campaign matches a real one.

## Response envelope trap

List endpoints wrap items two levels deep - `data.data.items` - and they report
validation failures **softly**:

```json
{"ok": true, "data": {"success": false, "message": "Invalid fields: ai_remark"}}
```

`ok: true` here does **not** mean success. Anything that only checks `ok` will
read a rejected call as "no results". `scripts/_ae.py` handles this in
`extract_items()`, which raises on `success: false`.

## Conventional ThinkingData event names

When a customer uses ThinkingData SDK but sends through their own platform,
these names are the most likely match for touchpoints:

| Name | Meaning |
|---|---|
| `ops_view` / `ops_push_view` | impression / arrival |
| `ops_click` / `ops_push_click` | click / open |
| `hermes_push_click` | click via the Hermes push channel |
| `sms_push_activity` | SMS activity entry |

`ops_receipt_properties.*` carries channel receipts, including
`ops_strategy_id` - the single most valuable property for isolating one send.
