# Ad Delivery Analysis — AI-facing Definitions

Pass these structures to:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type <model_type> \
  --definition '<json>'
```

All event and property names below are examples. Replace them only with exact
names returned by metadata, compiler candidates, or user confirmation. Never
pass raw QP, frontend DTO fields, internal aggregation codes, or project IDs
inside `--definition`.

## Core Metrics by Channel

```json
{
  "time_range": {"mode": "previous", "unit": "day", "value": 7},
  "time_particle_size": "day",
  "metrics": [
    {"event": "ad_impression", "aggregation": "total_count"},
    {"event": "ad_click", "aggregation": "total_count"},
    {"event": "app_install", "aggregation": "user_count"},
    {"event": "register", "aggregation": "user_count"},
    {"event": "payment", "aggregation": "sum", "property": "amount"}
  ],
  "groups": [
    {"field": {"name": "channel", "type": "user_property"}}
  ]
}
```

## Ad Conversion Funnel

```json
{
  "time_range": {"mode": "previous", "unit": "day", "value": 7},
  "time_particle_size": "day",
  "funnel": {
    "steps": [
      {"event": "ad_click"},
      {"event": "app_install"},
      {"event": "register"},
      {"event": "payment"}
    ],
    "window": {"value": 7, "unit": "day"},
    "groups": [
      {"field": {"name": "channel", "type": "user_property"}}
    ]
  }
}
```

Use a one-day window for strict click-to-install analysis and a longer window
only when the business conversion cycle justifies it.

## Last-touch Attribution

```json
{
  "time_range": {"mode": "previous", "unit": "day", "value": 14},
  "attribution": {
    "target_event": "payment",
    "target_aggregation": "user_count",
    "attribution_events": [
      {"event": "ad_impression"},
      {"event": "ad_click"}
    ],
    "attribution_model": "last",
    "window": {"value": 7, "unit": "day"},
    "direct_conversion": true
  }
}
```

`attribution_model` accepts `first`, `last`, or `linear`.

## Channel Retention

```json
{
  "time_range": {"mode": "previous", "unit": "day", "value": 30},
  "time_particle_size": "day",
  "retention": {
    "initial_event": "register",
    "return_event": "login",
    "stat_type": "retention",
    "unit_num": 7,
    "rtn_rate_or_num": "rate",
    "groups": [
      {"field": {"name": "channel", "type": "user_property"}}
    ]
  }
}
```

Use `stat_type: "lost"` for lost users and `rtn_rate_or_num: "count"` when
counts, rather than rates, are requested.

## Formula Metric

```json
{
  "time_range": {"mode": "previous", "unit": "day", "value": 7},
  "time_particle_size": "day",
  "metrics": [
    {
      "formula": "clicks / impressions",
      "dependencies": [
        {"alias": "clicks", "event": "ad_click", "aggregation": "total_count"},
        {"alias": "impressions", "event": "ad_impression", "aggregation": "total_count"}
      ]
    }
  ],
  "groups": [
    {"field": {"name": "channel", "type": "user_property"}}
  ]
}
```

Use bare aliases in `formula`. Never write internal A-codes.

## Filters

Attach filters at the top level of an event definition:

```json
{
  "filters": [
    {
      "field": {"name": "channel", "type": "user_property"},
      "operator": "eq",
      "values": ["douyin"]
    },
    {
      "field": {"name": "amount", "type": "event_property"},
      "operator": "between",
      "values": [10, 1000]
    }
  ],
  "relation": "and"
}
```

Use `analysis filter-value list` when the exact stored filter value is unknown.
