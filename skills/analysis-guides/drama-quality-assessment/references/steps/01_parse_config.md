# Step 1: Parse Config

## Objective

Complete the analysis configuration in two phases:

- **Phase A (business confirmation)**: first confirm "which drama + which time range", and only enter the next phase after the user confirms
- **Phase B (technical config)**: after user confirmation, load config files + map event names, then present a complete technical summary for final confirmation

## Prerequisites

- None — this is the first step. Only the user's conversation is required; no config files or ae-cli commands are touched before phase B.

## Input

- User's conversation: drama name, TE project ID, and (optionally) analysis time range, episode range, drama type, episode count, paywall position, custom weights.

## ⚠️ Core Principles

1. **The analysis target and time range must be explicitly confirmed by the user; skipping is forbidden.**
2. **The drama name must be explicitly provided by the user; auto-selection is forbidden.** Even if the project has only one drama, or the context contains hints, never infer or choose on the user's behalf. When the drama name is missing, ask the user directly.
3. **Config files (dimensions, scoring rules, query templates) are loaded only in phase B, never in phase A.** Avoid reading config or calling ae-cli before the user confirms the analysis scope.
4. **Phase A only collects information + confirms business parameters; it does not touch the filesystem or ae-cli.**

---

## Execution Instructions

---

## 🔵 Phase A: Business Confirmation (which drama + which time range)

> All prompts shown below are user-facing and MUST be translated to Chinese when presented.

### A.1 Information Collection: judge the completeness of user input

Extract the following from the user's conversation:

| Information Item | Required | Notes | Example |
|--------|:---:|------|------|
| Drama name | ✅ | The short drama being evaluated | Rebirth of the Big Shot |
| TE project ID | ✅ | ThinkingEngine project ID | 12345 |
| Analysis time range | ⚠️ | Needs confirmation: last 30 days suggested by default, but user consent is required | 2026-05-01 ~ 2026-06-10 |
| Analysis episode range | ⚠️ | Needs confirmation: all episodes recommended, but user consent is required | All / Episodes 1-10 / Episode 5 |
| Drama type | ❌ | Default: vertical mini-drama (vertical) | vertical / horizontal / private_platform |
| Total episode count | ❌ | Default: auto-inferred from data | 80 episodes |
| Paywall position | ❌ | Can be omitted for free dramas | Paywall starts at episode 11 |
| Custom weights | ❌ | Default weights used if not provided | "Set payment conversion to 20%" |

### A.2 Interaction Flow

Handle user input according to the following decision tree:

```
User input
    │
    ├── Drama name missing? → ❌ "Which short drama do you want to analyze? Please provide the drama name."
    │                    ⛔ Never list dramas from project data for the user to choose
    │                    ⛔ Never infer the drama name from context
    │                    ⛔ Even if the project has only one drama, wait for the user to state the name
    │
    ├── TE project ID missing? → ❌ "Please provide the TE project ID for this drama."
    │
    ├── Time range missing? → ⚠️ "Which time range should I analyze? For example:
    │                       • Last 7 days
    │                       • Last 30 days (recommended, better coverage)
    │                       • Since launch
    │                       • A specific range (e.g. May 1 ~ June 10)"
    │                    → Must wait for the user's reply; never directly use the default
    │
    ├── Episode range unspecified? → ⚠️ "Which episodes should I analyze? For example:
    │                       • All episodes (recommended for first-time analysis)
    │                       • First N episodes (e.g. first 10)
    │                       • A specific range (e.g. episodes 5-15)
    │                       • A single episode (e.g. episode 3)"
    │                    → Must wait for the user's reply; never directly use the default
    │
    ├── Drama type unknown? → "What type is this drama?"
    │                   If unspecified → default to "Vertical mini-drama" and note it at confirmation
    │
    ├── All above provided → enter phase A confirmation
```

**Important rules:**
- Ask only one question at a time; do not fire consecutive questions. Ask the next one after the user answers.
- **The time range must never silently use the default. Propose the default option to the user and wait for confirmation or modification.**
- **The episode range must never silently use the default. Propose the default option to the user and wait for confirmation or modification.**
- **During phase A, read no config files and call no ae-cli commands.**

### A.3 Output Business Confirmation Summary (mandatory step)

Once all information is complete, **output only the following business-parameter confirmation** (translate to Chinese when presenting), without any technical config content:

```
📋 Analysis target confirmation:

┌─────────────────────────────────────────────┐
│                                             │
│  Drama name: 《{drama_name}》                │
│  Drama type: {drama_type_label}             │
│  TE project ID: {project_id}                │
│  Time range: {start_date} ~ {end_date}      │
│  Episode range: {episode_range_label}       │
│  Expected episode count: {episode_count}    │
│  Paywall: {payment_wall_info}               │
│                                             │
│  Weights: {default / user-customized list}  │
│                                             │
└─────────────────────────────────────────────┘

⚠️ Please confirm the above analysis scope and time range. Reply "confirm" and I will load config and prepare the data queries.
```

**Key constraints:**
- This summary must **not** contain technical details such as event-name mapping or property field names
- **Must wait for the user's explicit confirmation** (e.g. "confirm", "start", "OK", "no problem") before entering phase B
- If the user asks to adjust any config item, re-output the business confirmation summary after modification

---

## 🟢 Phase B: Technical Config (executed after user confirmation)

> **Phase B runs only after the user explicitly confirms phase A. Core principle: parallel reads, parallel ae-cli commands, no redundant output.**

### B.1 Parallel Loading (run the following two groups simultaneously)

**Group 1: read all config files in parallel (issued simultaneously, no waiting):**

```
Read simultaneously:
  - references/config/dimensions.yaml
  - references/config/scoring_rules.yaml
  - references/config/event_mapping.yaml
  - references/query_patterns.md
```

**Group 2: call ae-cli metadata commands in parallel (issued simultaneously, no waiting):**

```
Execute simultaneously:
  - ae-cli analysis-meta event list --project-id {project_id}
  - ae-cli analysis-meta property list --project-id {project_id}
```

- Group 1 and Group 2 have no dependency on each other and can all be issued in the same tool-call batch
- If the user provided custom weights, override the corresponding dimension weight values after reading dimensions.yaml

### B.2 Event Name Mapping (run after both group results return)

**Mapping order:**
1. First check the user memory for the mapping cache `drama-quality-assessment-event-mapping-{project_id}` — if hit, reuse it directly and skip matching
2. On a miss, match against the event/property catalogs using the `standard_events` / `standard_properties` candidate-name lists; on a hit, write the result to user memory (never write back to the skill file)
3. Events that still cannot be matched → immediately ask the user for the project's actual tracking event names; do not guess

The 9 standard event types to map (candidate names in event_mapping.yaml):

| Standard Event | Purpose | Dimensions Involved |
|---------|------|---------|
| `play_start` | Playback start | 1/2/3/5/6/7/8/9 |
| `play_complete` | Playback end (≈ completion) | 1/2/4/5 |
| `episode_click` | Episode click | 1 |
| `next_episode_click` | Next-episode click | 4 |
| `play_progress` | Playback progress (with progress_pct property) | 3 |
| `payment_start` | Payment trigger | 7 |
| `like` | Like | 9 |
| `comment` | Comment | 9 |
| `share` | Share | 9 |

The 5 standard property types to map (candidate names in event_mapping.yaml):

| Standard Property | Purpose |
|---------|------|
| `episode_id` | Episode identifier |
| `drama_id` | Drama identifier (see B.2.5) |
| `progress_pct` | Playback progress percentage (Dimension 3 pacing) |
| `play_duration` | Playback duration (Dimension 3 pacing fallback; may be absent) |
| `is_new_user` | Whether a new user (Dimension 8 new-user ratio) |

**If no matching event or property is found, immediately ask the user for the project's actual tracking event/property names; do not guess.**

### B.2.5 Drama-Identifier Detection and Filtering (optional implementation of the drama filter)

The drama name must be translated into a data filter. Determine whether the current project has a "drama identifier property":

1. From the property-catalog results, look up the `standard_properties.drama_id` candidate names (`drama_id` / `drama_name` / `drama_title` / `show_id`).
2. **Drama identifier property hit**:
   - Call `ae-cli analysis filter-value list --project-id {project_id} --property-name {property name} --table-type event` to get the candidate values of that property.
   - If the property value is text (e.g. `drama_name`) and the candidate values contain the user-provided drama name → generate `drama_filter = {property: property name, value: "drama name"}`.
   - If the property value is a numeric ID (e.g. `drama_id`) → first check whether a text drama-name property exists (e.g. `drama_name`) to build the name→ID mapping; if the project only has an ID property and the ID cannot be reverse-looked-up from the name, ask the user directly for the drama ID and generate `drama_filter = {property: "drama_id", value: drama ID}`.
3. **No drama identifier property hit**: do NOT silently set `drama_filter = null`. Pause and ask the user to confirm one of:
   - "This project tracks only one drama, so project-wide queries are safe" → `drama_filter = null` and note it in the technical summary.
   - "The drama is distinguished by another property" → ask the user to name that property (or the drama ID), then rebuild `drama_filter = {property, value}`.
   Only enter Step 2 after the user confirms one option. Never assume single-drama from data volume, event names, or context.

`drama_filter` is passed as a variable to Step 2, and all Step 2 queries attach this filter uniformly.

### B.3 Output Technical Config Summary

After loading completes, output the full technical config summary (translate to Chinese when presenting). **If all event mappings matched automatically, present the summary directly and auto-enter Step 2 without waiting for confirmation again.** Only pause for user confirmation when the event mapping has ambiguity or gaps.

```
📋 Technical config loaded:

  ✅ Dimension weights: loaded 9 dimensions (from dimensions.yaml)
  ✅ Scoring rules: loaded {drama_type_label} thresholds (from scoring_rules.yaml)
  ✅ Query templates: loaded 9 dimension query templates (from references/query_patterns.md)
  ✅ Event mapping: loaded candidate-name list (from event_mapping.yaml)

  Event mapping result:
    Play start    → {play_start_event}          ✅
    Play complete → {play_complete_event}       ✅
    Episode click → {episode_click_event}       ✅
    Next episode  → {next_episode_click_event}  ✅
    Play progress → {play_progress_event}       ✅
    Payment       → {payment_event}            {'✅' if found else '⚠️ not found'}
    Like          → {like_event}                ✅
    Comment       → {comment_event}             ✅
    Share         → {share_event}               ✅

  Episode identifier: {episode_property_name}
  Drama filter: {drama_filter description or "none (assess all data)"}

  🔄 Starting data collection...
```

**Rules:**
- All events mapped successfully → auto-enter Step 2, no waiting
- Any event has ⚠️ or ❌ → pause and ask the user to confirm before entering Step 2

### B.4 Pass to Step 2

Pass the following variables to Step 2:
- `project_id`, `drama_name`, `drama_type`, `episode_count`
- `start_date`, `end_date`
- `episode_range` (analysis episode range, e.g. `[1, 10]`, `[5, 5]`, or `"all"`)
- `event_mapping` (event-name mapping table)
- `episode_property_name` (episode-number property name)
- `play_duration_property` (play-duration property name; may be null)
- `drama_filter` (drama filter condition, `{property, value}` or `null`)
- `weights` (dimension weight table)
- `scoring_rules` (scoring rules)
- `payment_wall_episode` (paywall episode, if provided; Step 2 auto-infers when absent)

## Output

- The Step-2 input variables listed in B.4, with business parameters confirmed by the user and technical config (event mapping, drama filter) resolved.

## Verification

- [ ] Drama name and TE project ID are explicitly provided by the user (never inferred or auto-selected).
- [ ] Time range and episode range were confirmed by the user (never defaulted silently).
- [ ] All 9 standard events and 5 standard properties are mapped, or explicitly pending user clarification.
- [ ] `drama_filter` is resolved: a concrete `{property, value}`, or `null` only after the user confirmed the project is single-drama.
- [ ] `play_duration_property` is either mapped or explicitly `null` (Dimension 3 fallback degrades to N/A when both progress and duration are absent).
- [ ] No config files or ae-cli commands were touched during phase A (only after user confirmation).
