# Query Pattern Reference (ae-cli edition)

> This document defines the query template for each dimension. The Agent reads this file when executing Step 2 and builds queries with `ae-cli analysis adhoc run`.
> All `--definition` values are AI-facing JSON (field format per `references/ai_models.md` of the ae-analysis skill), not raw QP.

## Prerequisites

### Variable Placeholders
- `{project_id}` - TE project ID (provided by the user)
- `{start_date}` / `{end_date}` - analysis start/end dates (format yyyy-MM-dd)
- `{episode_property_name}` - episode-number property name (after Step 1 mapping)
- `{play_start_event}` / `{play_complete_event}` / `{episode_click_event}` / `{next_episode_click_event}` / `{play_progress_event}` / `{payment_start_event}` / `{like_event}` / `{comment_event}` / `{share_event}` - event names (after Step 1 mapping)
- `{progress_pct_property}` - play-progress property name (after Step 1 mapping)
- `{play_duration_property}` - play-duration property name (after Step 1 mapping; may be absent)
- `{is_new_user_property}` - new-user flag property name (after Step 1 mapping)
- `{drama_filter}` - drama filter condition (see "Global Drama Filter Rule"; may be empty)

### Event Name Mapping
Tracking event names may differ across platforms. The Agent has already completed the mapping in Step 1 phase B against the candidate-name lists in `references/config/event_mapping.yaml`, and cached the confirmed results into user memory (isolated by project_id). All event/property names in this document are "standard names"; the Agent replaces them with the mapped project-specific actual names at execution time.

### Global Drama Filter Rule
`drama_filter` is `{property, value}` when Step 1 found a drama identifier property, otherwise it is empty. When non-empty, every query must scope to that single drama as follows (never leave a query unfiltered when `drama_filter` is set).

**Filter shape differs by model — do not mix them up:**

- **event query**: use a `field` object — append `{"field": {"name": drama_filter.property, "type": "event_property"}, "operator": "eq", "values": [drama_filter.value]}` to each metric's `filters` or to the top-level `filters`.
- **funnel query**: funnel step filters use `event_property_name` (a plain string), NOT a `field` object. Append `{"event_property_name": drama_filter.property, "operator": "eq", "values": [drama_filter.value]}` to **every step** whose event carries the drama property (not only the first step), so a user's later events from other dramas are not miscounted. If a later step's event does not carry the drama property, keep the filter on the entry step and note this limitation in the report's "Data Notes".
- **retention query**: attach `initial_filters` and `return_filters` (event-property-only shape) inside `retention`:
  ```json
  "initial_filters": [{"event_property_name": drama_filter.property, "operator": "eq", "values": [drama_filter.value]}],
  "initial_filter_relation": "and",
  "return_filters": [{"event_property_name": drama_filter.property, "operator": "eq", "values": [drama_filter.value]}],
  "return_filter_relation": "and"
  ```
  Use `event_property_name` (a plain string), NOT a `field` object, and do NOT use top-level `filters` or `retention.filters`.
- **event-detail query**: wrap the filter in the detail shape `{"relation": "and", "items": [{"field": {"name": drama_filter.property, "type": "event_property"}, "operator": "eq", "values": [drama_filter.value]}]}` (its `items` use a `field` object, unlike funnel/retention).

When `drama_filter` is empty, no drama filter is applied — but only after Step 1 has confirmed with the user that the project contains exactly one drama (see Step 1 B.2.5). Never silently run project-wide queries on a possibly multi-drama project.

### Completion-Rate Semantics
"Completion rate" in this document is preferably determined via `play_progress` (`progress_pct = 100`) as fully watched; if the project has no progress event, fall back to approximating with the `play_complete` event and note "completion rate is approximate" in the final report.

### Common Query Flow (for every query of every dimension)
```
ae-cli analysis adhoc run \
  --project-id {project_id} \
  --model-type {event|funnel|retention} \
  --definition '<AI-facing JSON>'
```
- Returns ok:true with data → read rows / result
- Returns ok:true but data empty → query succeeded but no matching data; inform the user, do not retry
- Returns AI_QP_COMPILE_FAILED → check meta.errors / meta.resolved and follow the metadata_resolution flow of the ae-analysis skill; if necessary ask the user to clarify event/property names
- Returns other failure (ok:false) → keep error.code / error.message, report the error, do not guess parameters and retry
- Query times out or full results needed → switch to `ae-cli analysis adhoc export` (async); for playback detail use `ae-cli analysis event-detail export` (async, returns run_id/artifact_id; poll with `analysis run inspect`, download with `analysis artifact download`, or use `--output <file>` which implies wait).

**Model notes (ae-cli AI-facing contract):**
- Ad-hoc `time_range` modes are `recent` / `previous` / `custom` / `start_to_today` / `start_to_yesterday` (use `custom` with `start_time`/`end_time` for a fixed analysis window).
- Event-detail (`event-detail run` / `event-detail export`) uses a DIFFERENT time-range contract: `{"mode": "absolute", "start_time": "yyyy-MM-dd HH:mm:ss", "end_time": "yyyy-MM-dd HH:mm:ss"}` (or `{"mode": "relative", "relative_date_range": "0-7"}`). Do NOT pass `mode: custom` to event-detail.
- Retention supports `initial_filters` / `return_filters` (event-property filters on the initial/return events) — see the Global Drama Filter Rule above.

---

## Dimension 1: First-Episode Appeal

### Query 1.1: first-episode click-to-play conversion (funnel)

```
ae-cli analysis adhoc run --model-type funnel --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "funnel": {
    "steps": [
      {"event": "{episode_click_event}"},
      {"event": "{play_start_event}", "filters": [
        {"event_property_name": "{episode_property_name}", "operator": "eq", "values": ["1"]}
      ]}
    ],
    "window": {"value": 5, "unit": "minute"}
  }
}'
# attach the drama filter to every step that carries the drama property (Global Drama Filter Rule)
```

### Query 1.2: first-episode completion rate (event)

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "metrics": [
    {"event": "{play_complete_event}", "aggregation": "user_count", "filters": [
      {"field": {"name": "{episode_property_name}", "type": "event_property"}, "operator": "eq", "values": ["1"]}
    ]},
    {"event": "{play_start_event}", "aggregation": "user_count", "filters": [
      {"field": {"name": "{episode_property_name}", "type": "event_property"}, "operator": "eq", "values": ["1"]}
    ]}
  ]
}'
# completion rate = complete-viewer count / play_start viewer count (see "Completion-Rate Semantics" above)
```

### Query 1.3: 1→2 episode jump rate (funnel)

Episode-filtered short-window cross-episode conversion is expressed as a funnel (retention's `unit_num=1` measures next-day N+1 return, not a short within-session jump):

```
ae-cli analysis adhoc run --model-type funnel --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "funnel": {
    "steps": [
      {"event": "{play_complete_event}", "filters": [
        {"event_property_name": "{episode_property_name}", "operator": "eq", "values": ["1"]}
      ]},
      {"event": "{play_start_event}", "filters": [
        {"event_property_name": "{episode_property_name}", "operator": "eq", "values": ["2"]}
      ]}
    ],
    "window": {"value": 1, "unit": "day"}
  }
}'
# attach the drama filter to both steps (Global Drama Filter Rule)
```

---

## Dimension 2: Completion Quality

### Query 2.1: per-episode completion rate (event + groups)

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "metrics": [
    {"event": "{play_complete_event}", "aggregation": "user_count"},
    {"event": "{play_start_event}", "aggregation": "user_count"}
  ],
  "groups": [{"field": {"name": "{episode_property_name}", "type": "event_property"}}]
}'
# per-episode completion rate = that episode's complete-viewer count / that episode's play_start viewer count
```

### Query 2.2: time-segmented completion trend (event + time_particle_size)

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "time_particle_size": "day",
  "metrics": [
    {"event": "{play_complete_event}", "aggregation": "user_count"},
    {"event": "{play_start_event}", "aggregation": "user_count"}
  ]
}'
# observe the overall completion-rate trend by day (no episode grouping)
```

---

## Dimension 3: In-Episode Pacing

### Query 3.1: progress retention curve (event, metric-level filters)

This depends on the event's "play progress" property (e.g. `play_progress` + `progress_pct`) to determine where users drop off.

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "metrics": [
    {"event": "{play_start_event}", "aggregation": "user_count"},
    {"event": "{play_progress_event}", "aggregation": "user_count", "filters": [
      {"field": {"name": "{progress_pct_property}", "type": "event_property"}, "operator": "gte", "values": ["25"]}
    ]},
    {"event": "{play_progress_event}", "aggregation": "user_count", "filters": [
      {"field": {"name": "{progress_pct_property}", "type": "event_property"}, "operator": "gte", "values": ["50"]}
    ]},
    {"event": "{play_progress_event}", "aggregation": "user_count", "filters": [
      {"field": {"name": "{progress_pct_property}", "type": "event_property"}, "operator": "gte", "values": ["75"]}
    ]},
    {"event": "{play_progress_event}", "aggregation": "user_count", "filters": [
      {"field": {"name": "{progress_pct_property}", "type": "event_property"}, "operator": "gte", "values": ["100"]}
    ]}
  ],
  "groups": [{"field": {"name": "{episode_property_name}", "type": "event_property"}}]
}'
# retention at each progress point = remaining viewers at that progress / play_start viewer count
```

**If the event model's metric does not support filters (compiler error)**: split into multiple independent event queries, each using the top-level `filters` to express a single bucket (one query for play_start, four queries for the four progress buckets), then compute retention rates manually.

**Simplified approach (when there is no play_progress event)**: use `analysis event-detail export` to pull playback detail (including the `{play_duration_property}` when it exists) and compute the pacing curve manually. Detail export uses `mode: absolute` (see below) and must attach the drama filter through the detail `filters` shape.

**High-churn position location (for diagnosis, not counted into scoring)**:

```
ae-cli analysis event-detail export \
  --project-id {project_id} \
  --definition '
  {
    "event": "{play_progress_event}",
    "time_range": {"mode": "absolute", "start_time": "{start_date} 00:00:00", "end_time": "{end_date} 23:59:59"},
    "filters": {"relation": "and", "items": [
      {"field": {"name": "{drama_filter.property}", "type": "event_property"}, "operator": "eq", "values": ["{drama_filter.value}"]}
    ]},
    "properties": ["#user_id", {"name": "{episode_property_name}", "type": "event_property"}, {"name": "{progress_pct_property}", "type": "event_property"}],
    "sort": [{"field": "#event_time", "order": "asc"}]
  }' \
  --artifact-format csv --output <temp file>
# omit the "filters" key when drama_filter is empty. count drop-offs per episode at each progress position.
```

**Pacing degradation rule**: if the project has neither a `play_progress` event with a progress property NOR a play-duration property on the playback detail, mark the whole In-Episode Pacing dimension as N/A with reason "no progress / duration tracking", and exclude it from scoring (its weight is reallocated per Step 3.4).

---

## Dimension 4: Cliffhanger Effect

All three metrics are computed **per episode** (loop `i` over `{target_episodes}`). They share the same funnel base: "completed episode i, then clicked the next episode within a short window".

### Query 4.1: episode-end jump rate (funnel, per episode, 10s window)

```
ae-cli analysis adhoc run --model-type funnel --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "funnel": {
    "steps": [
      {"event": "{play_complete_event}", "filters": [
        {"event_property_name": "{episode_property_name}", "operator": "eq", "values": ["{i}"]}
      ]},
      {"event": "{next_episode_click_event}"}
    ],
    "window": {"value": 10, "unit": "second"}
  }
}'
# jump = clicked next episode within 10s of completing episode i
# attach the drama filter to both steps (next_episode_click only if it carries the drama property)
```

### Query 4.2: 5s cliffhanger jump rate (funnel, per episode, 5s window)

```
ae-cli analysis adhoc run --model-type funnel --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "funnel": {
    "steps": [
      {"event": "{play_complete_event}", "filters": [
        {"event_property_name": "{episode_property_name}", "operator": "eq", "values": ["{i}"]}
      ]},
      {"event": "{next_episode_click_event}"}
    ],
    "window": {"value": 5, "unit": "second"}
  }
}'
# jump = clicked next episode within 5s of completing episode i (the strictest "hook" signal)
```

### Query 4.3: cliffhanger failure ratio (event, per episode)

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "metrics": [
    {"event": "{play_complete_event}", "aggregation": "user_count", "filters": [
      {"field": {"name": "{episode_property_name}", "type": "event_property"}, "operator": "eq", "values": ["{i}"]}
    ]}
  ]
}'
# failure users(i) = complete users(i) - 10s jump users(i)   (jump users from Query 4.1)
# cliffhanger_failure_rate(i) = failure users(i) / complete users(i)
```

**Fallback (no next_episode_click event)**: use `{play_start_event}` filtered by `{episode_property_name} = i+1` as step 2 of both funnels, with the same 10s/5s windows.

**Per-episode loop note**: run Query 4.1 / 4.2 / 4.3 for each episode `i` in `{target_episodes}`; episode `i` without an `i+1` (last episode) has no jump metric and contributes only the failure ratio, or is skipped if it is also the only episode in range.

---

## Dimension 5: Inter-Episode Retention

### Query 5.1: next-day retention (retention, with initial/return filters)

```
ae-cli analysis adhoc run --model-type retention --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "time_particle_size": "day",
  "retention": {
    "initial_event": "{play_start_event}",
    "initial_filters": [
      {"event_property_name": "{drama_filter.property}", "operator": "eq", "values": ["{drama_filter.value}"]}
    ],
    "initial_filter_relation": "and",
    "return_event": "{play_start_event}",
    "return_filters": [
      {"event_property_name": "{drama_filter.property}", "operator": "eq", "values": ["{drama_filter.value}"]}
    ],
    "return_filter_relation": "and",
    "stat_type": "retention",
    "unit_num": 1,
    "rtn_rate_or_num": "rate"
  }
}'
# single-drama next-day retention: users who started this drama on day X and started it again on day X+1.
# when drama_filter is empty (single-drama project), omit initial_filters/return_filters/initial_filter_relation/return_filter_relation entirely.
```

### Query 5.2: inter-episode jump rate (per episode, funnel)

Execute for each episode i → i+1 (episode-filtered, expressed as a funnel):

```
ae-cli analysis adhoc run --model-type funnel --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "funnel": {
    "steps": [
      {"event": "{play_complete_event}", "filters": [
        {"event_property_name": "{episode_property_name}", "operator": "eq", "values": ["{i}"]}
      ]},
      {"event": "{play_start_event}", "filters": [
        {"event_property_name": "{episode_property_name}", "operator": "eq", "values": ["{i+1}"]}
      ]}
    ],
    "window": {"value": 1, "unit": "day"}
  }
}'
# attach the drama filter to both steps (Global Drama Filter Rule)
```

### Query 5.3: churn point distribution (event + groups)

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "metrics": [
    {"event": "{play_complete_event}", "aggregation": "user_count"}
  ],
  "groups": [{"field": {"name": "{episode_property_name}", "type": "event_property"}}]
}'
# observe the per-episode complete-viewer count trend; a sharp drop marks the churn point
# churn_point_distribution = max(episode complete count) / sum(all episode complete counts)
```

---

## Dimension 6: Binge Depth

### Query 6.1: binge ≥3 episodes ratio + binge median

Group by session or user and count the episodes watched consecutively within a single session.

**Option A: pull detail via `analysis event-detail export`** (recommended; async, `mode: absolute`)

```
ae-cli analysis event-detail export \
  --project-id {project_id} \
  --definition '
  {
    "event": "{play_start_event}",
    "time_range": {"mode": "absolute", "start_time": "{start_date} 00:00:00", "end_time": "{end_date} 23:59:59"},
    "filters": {"relation": "and", "items": [
      {"field": {"name": "{drama_filter.property}", "type": "event_property"}, "operator": "eq", "values": ["{drama_filter.value}"]}
    ]},
    "properties": ["#user_id", {"name": "{episode_property_name}", "type": "event_property"}, "#event_time"],
    "sort": [{"field": "#event_time", "order": "asc"}]
  }' \
  --artifact-format csv --output <temp file>
# the Agent computes binge depth from the detail data (consecutive episodes per session per user).
# omit the "filters" key when drama_filter is empty.
```

**Option B: approximate via event query grouped by user**

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "metrics": [
    {"event": "{play_start_event}", "aggregation": "distinct_count", "property": "{episode_property_name}"}
  ],
  "groups": [{"field": {"name": "#user_id", "type": "user_property"}}]
}'
# count the distinct episodes watched per user, approximating binge depth
```

---

## Dimension 7: Payment Conversion

### Query 7.1: payment trigger rate (funnel; needs the inferred paywall episode)

```
ae-cli analysis adhoc run --model-type funnel --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "funnel": {
    "steps": [
      {"event": "{play_start_event}", "filters": [
        {"event_property_name": "{episode_property_name}", "operator": "eq", "values": ["{paywall_episode}"]}
      ]},
      {"event": "{payment_start_event}"}
    ],
    "window": {"value": 30, "unit": "minute"}
  }
}'
# attach the drama filter to both steps (Global Drama Filter Rule)
```

**Paywall episode inference (runs in Step 2 Phase A, before this query)**: query `{payment_start_event}` grouped by `{episode_property_name}` (`aggregation: user_count`, groups by episode), take the smallest episode that has a payment event as `{paywall_episode}`. Note the inferred value in the Checkpoint 1 summary for user confirmation. If the drama has no payment events, skip Dimension 7 entirely.

### Query 7.2: post-payment watch rate (funnel)

Expressed as a funnel (short-window conversion after payment):

```
ae-cli analysis adhoc run --model-type funnel --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "funnel": {
    "steps": [
      {"event": "{payment_start_event}"},
      {"event": "{play_start_event}"}
    ],
    "window": {"value": 1, "unit": "day"}
  }
}'
# attach the drama filter to both steps (Global Drama Filter Rule)
```

---

## Dimension 8: Heat Trend

### Query 8.1: daily average plays + play peak (event + time_particle_size)

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "time_particle_size": "day",
  "metrics": [
    {"event": "{play_start_event}", "aggregation": "total_count"}
  ]
}'
# result shows the play trend by day; mean = daily average plays, max = play peak
```

New-user ratio, extra query:

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "metrics": [
    {"event": "{play_start_event}", "aggregation": "user_count", "filters": [
      {"field": {"name": "{is_new_user_property}", "type": "user_property"}, "operator": "eq", "values": ["true"]}
    ]},
    {"event": "{play_start_event}", "aggregation": "user_count"}
  ]
}'
# new-user ratio = new-user count / total viewer count
# NOTE: set the filter's "type" to the property's actual table_type from the property catalog —
#       event_property for a per-event flag (e.g. is_register), user_property for a user-level flag.
#       Adjust the boolean value to the project's actual convention (true/false or 1/0).
```

---

## Dimension 9: User Engagement

### Query 9.1: like rate, comment rate, share rate (event, single query)

```
ae-cli analysis adhoc run --model-type event --definition '
{
  "time_range": {"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"},
  "metrics": [
    {"event": "{like_event}", "aggregation": "user_count"},
    {"event": "{comment_event}", "aggregation": "user_count"},
    {"event": "{share_event}", "aggregation": "user_count"},
    {"event": "{play_start_event}", "aggregation": "user_count"}
  ]
}'
# each interaction rate = interaction viewer count / viewer count
```

---

## Parallel Execution Notes (dependency-aware)

Step 2 runs in three phases; a query starts only when its inputs are ready.

- **Phase A (synchronous, parallel)**: episode list (2.1) + all queries with no cross-query dependency — Dimensions 1/2/8/9, Dimension 3 event query, Dimension 4 per-episode funnels + event, Dimension 5.1 retention + 5.2 per-episode funnels + 5.3 event, Dimension 6 Option B, Dimension 7.2 funnel, and the **paywall-inference query** (payment_start grouped by episode).
- **Phase B (after Phase A)**: Dimension 7.1 funnel (needs the inferred `{paywall_episode}`); submit the async detail exports (Dimension 3 pacing fallback / Dimension 6 Option A / churn location) in parallel.
- **Phase C**: poll and download the async detail artifacts (`analysis run inspect` / `analysis run wait --run-id ... --output <file>`).

Per-episode loops (Dimensions 3/4/5) run only for episodes within `{target_episodes}`.
