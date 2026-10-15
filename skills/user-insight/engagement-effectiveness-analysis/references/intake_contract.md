# Mode B Intake Contract

Mode B has no canvas id to look up, so the campaign has to be described before
anything can be measured. This contract is the **entry gate**: the run does not
start until every REQUIRED item is answered.

Render it with `scripts/collect_intake.py --show`, fill it, then gate it with
`scripts/validate_intake.py`.

## Ask all of it at once

Present the whole table in a single turn. Drip-feeding questions across turns
wastes the user's time and invites them to abandon the request midway.

Where the user does not know an answer, resolve it **for** them:

| User says | What to do |
|---|---|
| "I don't know the event name" | Search `analysis_meta +list_events -q <keyword>` and show the candidates with their descriptions |
| "I don't know if there's a property" | Search `analysis_meta +list_properties -q strategy` / `-q campaign` / `-q push` |
| "It was just last week's campaign" | Narrow by time window and channel, search events, present candidates for confirmation |
| "We use our own push system" | Check for `ops_view` / `ops_click` and `ops_receipt_properties.ops_strategy_id` first |

The user only needs to understand their own business. The platform vocabulary is
supplied by the search helpers and confirmed by the user - never chosen silently.

## The 11 items

### REQUIRED - the run is blocked without these

| # | Key | Question | Why it blocks |
|---|---|---|---|
| 1 | `strategy_name` | What is this campaign called, and does it have an id? | Names the deliverables; keeps data isolated |
| 2 | `channel` | push / in-app / popup / SMS / EDM / phone / mixed? | Determines which benchmarks apply |
| 3 | `time_window` | When was it sent? Start and end date. | Everything is scoped to this window; must span >= 3 days |
| 4 | `target_audience` | Who received it - all users / a tag / a cluster? | Needed to interpret the denominator; searchable via `+list_clusters` / `+list_tags` |
| 8 | `click_event` | Which event means the user clicked or opened it? | Without an observable click there is no conversion path at all |
| 10 | `attribution_window` | How long after the click still counts as credit? | Determines which conversions are attributed to this send |

### CRITICAL - always ask, never skip

| # | Key | Question | Consequence of absence |
|---|---|---|---|
| 5 | `discriminator` | Is there a property that marks this specific send - `strategy_id`, `campaign`, `channel`? | The audience is approximated by the time window only, so overlapping sends contaminate each other. Precision drops ~20%. |

This item is the single largest determinant of mode B accuracy. Ask it every
time, even when the user has not volunteered anything about identifiers.

### OPTIONAL - degrade gracefully

| # | Key | Question | If missing |
|---|---|---|---|
| 6 | `grouping` | Was there an A/B split? Group property name? | Real lift is unavailable; falls back to a quasi-experiment (~25% loss) |
| 7 | `view_event` | Which event means it was displayed? | The funnel starts from the earliest observable stage, so impression-to-click CTR cannot be computed (~25% loss) |
| 9 | `conversion_event` | Which event means the goal was achieved? | Click rate and next-day retention stand in as proxies (~20% loss) |
| 11 | `exclusions` | Anyone to exclude - already paid, unsubscribed, test accounts? | Results carry a small contamination risk (~5% loss) |

## Validating an answer

`scripts/validate_intake.py` rejects an item when it is present but unusable:

* an event field containing Chinese characters, spaces, or anything that is not a
  machine identifier is treated as an unresolved description, not a name
* a `time_window` shorter than 3 days is flagged
* product names, channel labels and campaign names are accepted as free text

A missing `discriminator` does not block the run, but it is reported as a
degradation so the confidence statement in the report can carry it.

## Minimum viable input for mode B

```
project_id + click_event + time_window (>= 3 days)
```

Everything else improves precision but is not a precondition.
