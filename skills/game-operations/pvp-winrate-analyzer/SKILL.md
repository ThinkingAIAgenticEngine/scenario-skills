---
name: pvp-winrate-analyzer
description: Analyze how PVP win rate relates to retention, payment, and player progression in games. Use for win-rate distribution, matchmaking-health, inverted-U checks, tier comparisons, and PVP balance recommendations backed by TE project data.
---

# PVP Win-rate Analyzer

Respond in the user's language. Separate measured facts from hypotheses and
never generate a conclusion from built-in sample data.

## Core Questions

Evaluate:

- win-rate distribution and sample size by bucket;
- D1/D7 retention by win-rate bucket;
- payer rate, ARPU, and revenue by bucket;
- whether outcomes differ by progression or power tier;
- whether an apparent inverted-U relationship remains after controlling for
  sample composition.

Core formulas:

```text
Player win rate = valid wins / valid PVP battles
Payer rate = distinct payers / valid PVP players
ARPU = total payment / valid PVP players
```

Exclude abandoned, cancelled, bot, and invalid matches only when a verified
field and value identify them.

## Required Inputs

Collect the project ID, analysis period, game/project name, PVP event, outcome
property, payment event/property, and active/return event. Names supplied by the
user are still hypotheses until the compiler resolves them.

For a non-SQL intent model, submit the semantic AI-facing definition first.
Use `analysis-meta event list`, `analysis-meta property list`, or
`analysis filter-value list` only after a structured clarification/error says an
exact name or stored value is unresolved.

Stop and explain the missing requirement if no valid PVP event, outcome field,
or stable user identifier can be resolved.

## Data Retrieval

### 1. Existing Assets

Prefer verified existing reports:

```bash
ae-cli analysis report list --project-id <project_id> --query "PVP"
ae-cli analysis dashboard list --project-id <project_id> --query "PVP"
```

Inspect with `report get` or `dashboard get`, then execute with
`report-data run` or `dashboard-report-data run`. Confirm that the asset's
definition, period, timezone, and user identity match this analysis.

### 2. Aggregate Event Checks

Use an event AI-facing definition for bounded aggregate checks:

```bash
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --definition '{
    "time_range": {"mode": "previous", "unit": "day", "value": 7},
    "time_particle_size": "day",
    "metrics": [
      {"event": "pvp_battle_end", "aggregation": "total_count"}
    ],
    "filters": [
      {
        "field": {"name": "battle_result", "type": "event_property"},
        "operator": "neq",
        "values": ["abandon"]
      }
    ]
  }'
```

The event, property, and value are examples. Check `meta.resolved`,
`meta.warnings`, timezone, actual cluster scope, and returned row counts.

### 3. User-level Win-rate Dataset

This analysis normally needs more than the synchronous preview limit and
metric-specific conditions for wins versus all valid battles. Use SQL only
after discovering an authorized physical table and its columns:

```bash
ae-cli analysis sql-table list --project-id <project_id>
ae-cli analysis-meta datatable columns-get \
  --project-id <project_id> \
  --table-ref <returned_table_ref>
```

Then use `analysis adhoc export --model-type sql` with a definition containing
verified SQL. Requirements:

- quote identifiers containing `#`, `$`, `@`, spaces, or punctuation;
- include a partition predicate on the discovered `"$part_date"` column for an
  event table;
- group by the verified stable user/entity ID;
- compute valid battles and wins with explicit verified outcome values;
- do not silently replace an account ID with a device ID;
- request the full export once; do not loop over truncated `adhoc run` previews.

Example structure, not executable SQL:

```json
{
  "sql": "SELECT <stable_user_id>, COUNT_IF(<valid_match>) AS battles, COUNT_IF(<win_match>) AS wins FROM <returned_table_ref> WHERE <verified_partition_predicate> GROUP BY <stable_user_id>"
}
```

Never invent the table, columns, or dialect-specific expression.

### 4. Retention

Use the retention model for project-level or metadata-supported group
comparisons:

```json
{
  "time_range": {"mode": "previous", "unit": "day", "value": 30},
  "time_particle_size": "day",
  "retention": {
    "initial_event": "pvp_battle_end",
    "return_event": "login",
    "stat_type": "retention",
    "unit_num": 1,
    "rtn_rate_or_num": "rate"
  }
}
```

Run with `analysis adhoc run --model-type retention`. Repeat with
`unit_num: 7` for D7. A derived Python win-rate bucket is not automatically a TE
user property; do not put it into `groups` unless it actually exists in project
metadata. For user-level retention joins, use a verified SQL/table path or an
explicitly approved persisted tag/cluster workflow.

### 5. Payment

Use an event definition for aggregate payer and revenue checks:

```json
{
  "time_range": {"mode": "previous", "unit": "day", "value": 7},
  "metrics": [
    {"event": "pay", "aggregation": "user_count"},
    {"event": "pay", "aggregation": "sum", "property": "pay_amount"}
  ]
}
```

For user-level joins to the exported win-rate dataset, use the same verified
stable identifier and the same SQL/table discovery rules.

## Data Quality Gate

Before fitting or reporting:

| Check | Minimum / handling |
|---|---|
| Valid PVP users | Prefer at least 5,000; otherwise label exploratory |
| Valid battles | Prefer at least 50,000; otherwise widen the period |
| Users per win-rate bucket | Prefer at least 1,000; exclude weaker buckets from core claims |
| Coverage | At least 7 complete days; exclude today unless completeness is verified |
| Identity join | Report matched/unmatched counts and match rate |
| Query completeness | No truncated preview used as full population |

These thresholds are quality heuristics, not proof of statistical power.
Calculate power or confidence intervals for the actual comparison.

## Analysis

1. Compute per-user win rate after excluding invalid matches.
2. Bucket win rate in 10-point bands, but merge sparse adjacent buckets.
3. Report user count, battle count, retention, payer rate, and ARPU by bucket.
4. Compare raw outcomes and confidence intervals.
5. Stratify by verified progression/power tier to test composition effects.
6. Fit linear and quadratic specifications only when sample quality supports it.
7. Treat an inverted-U result as evidence only when the quadratic term and
   turning point are stable, adequately supported, and inside the observed range.
8. State correlation, not causation, unless the data comes from a valid
   experiment or causal design.

Recommended outputs:

- win-rate distribution;
- retention and monetization by bucket with sample sizes;
- tier-stratified comparison;
- model diagnostics and uncertainty;
- actionable matchmaking hypotheses and a validation experiment.

## Write and Sharing Boundaries

Creating a tag, cluster, report, dashboard, document, or uploaded artifact is a
write operation. First show the proposed name, scope, definition, and target;
obtain user confirmation; then use the current command reference.

After a report is created, keep the exact returned ID, verify it with
`report-data run`, and obtain its URL with `analysis-meta asset url-get`.
Never claim success without a returned resource ID.

## Failure Handling

- Compilation ambiguity: show exact candidates from `meta.errors`; do not guess.
- Empty result: distinguish explicit project-no-data from command failure.
- Truncated result: switch to export.
- Missing stable identity: stop user-level joins and provide aggregate-only
  findings.
- Incomplete retention horizon: mark it unavailable rather than estimating it.
- Missing Python dependency: ask before creating an isolated virtual environment
  or downloading packages; never modify system Python.
