# Step 2: Data Collection

## Objective

Based on the config confirmed in Step 1, query the data of 9 dimensions in parallel via ae-cli.

## Prerequisites

- Step 1 has completed phase B (technical config) and passed the following variables.
- `references/query_patterns.md` (per-dimension query templates) and `references/config/event_mapping.yaml` (event/property candidate names) were loaded in Step 1 and are not re-read here.

## Input

- `project_id`, `drama_name`, `drama_type`, `episode_count`
- `start_date`, `end_date`
- `episode_range` (e.g. `[1, 10]`, `[5, 5]`, or `"all"`)
- `event_mapping` (event-name mapping table), `episode_property_name`
- `drama_filter` (`{property, value}` or `null`)
- `weights`, `scoring_rules`, `payment_wall_episode` (may be absent)

## ⚠️ Key Principles

- **Do not redo Step 1's work.** Config files and event mapping are already done in phase B; use the passed-in variables directly. Do not re-read references/config/*.yaml or references/query_patterns.md, and do not call analysis-meta event list / property list again.
- **Start querying immediately upon entering Step 2; do not output progress narration.** No need to tell the user "querying dimension X"; issue queries in parallel directly.
- **Issue all queries within the same batch in parallel.** Do not execute ae-cli commands one after another.

## Execution Instructions

### 2.0 Prerequisite: Determine the Analysis Episode Range

Determine the actual episodes to analyze from the `episode_range` variable passed from Step 1, and use the passed-in variables such as `event_mapping`, `episode_property_name`, `scoring_rules` directly. No need to re-read any files.

| episode_range | Meaning | Example |
|---|---|---|
| `"all"` | All episodes | Auto-infer all episodes |
| `[start, end]` | Specified range | `[1, 10]` means episodes 1-10 |
| `[n, n]` | Single episode | `[5, 5]` means analyze only episode 5 |

**Notes:**
- If `episode_range` is a specific range, all per-episode queries (dimensions 2/3/4/5) only need to query the episodes within that range
- Overall metrics (dimensions 1/6/7/8/9) still query the full data
- For single-episode analysis, some metrics of dimension 4 (cliffhanger effect) and dimension 5 (inter-episode retention) may not apply and are auto-skipped

### 2.1 Prerequisite: Query the Episode List

Call ae-cli to get the actual episode candidate values and filter out `{target_episodes}`:

```
ae-cli analysis filter-value list \
  --project-id {project_id} \
  --property-name {episode_property_name} \
  --table-type event \
  --event-name {play_start_event}
```

---

### 2.2 Dependency-Aware Query Phases

**Core rule: a query starts only when its inputs are ready. Not all queries are independent — payment conversion needs the paywall episode inferred first, and detail exports are async. Run the three phases in order; within each phase, issue independent queries in parallel (single tool-call batch), never serialize.**

All per-episode queries run only for episodes within the `{target_episodes}` range. If the `drama_filter` passed from Step 1 is non-empty, every query attaches the drama filter per the "Global Drama Filter Rule" in references/query_patterns.md.

#### Phase A (synchronous, parallel)

The episode list (2.1) plus every query with no cross-query dependency, all in one batch:

**Query A: Dimension 1 - First-Episode Appeal**
```
Reference: references/query_patterns.md → Dimension 1
1. adhoc run --model-type funnel → first-episode click-to-play conversion
2. adhoc run --model-type event → first-episode completion rate
3. adhoc run --model-type funnel → 1→2 episode jump rate (episode-filtered)
```
The three queries run in parallel within the dimension. **If the user-specified range does not include episode 1, this dimension is auto-skipped.**

**Query B: Dimension 2 - Completion Quality**
```
Reference: references/query_patterns.md → Dimension 2
adhoc run --model-type event:
  metrics: [play_complete(user_count), play_start(user_count)]
  groups: [{field: {name: "episode_id", type: "event_property"}}]
```

**Query C: Dimension 8 - Heat Trend**
```
Reference: references/query_patterns.md → Dimension 8
adhoc run --model-type event:
  metrics: [play_start(total_count)]
  time_particle_size: "day"
```

**Query D: Dimension 9 - User Engagement**
```
Reference: references/query_patterns.md → Dimension 9
adhoc run --model-type event:
  metrics: [like(user_count), comment(user_count), share(user_count), play_start(user_count)]
```

**Query E: Dimension 5 (partial) - Next-Day Retention**
```
Reference: references/query_patterns.md → Dimension 5.1
adhoc run --model-type retention:
  retention: {initial_event: "play_start", return_event: "play_start", unit_num: 1,
              initial_filters / return_filters = drama filter when drama_filter is non-empty}
```

**Query F: Dimension 3 - In-Episode Pacing**
```
Reference: references/query_patterns.md → Dimension 3
adhoc run --model-type event:
  metrics: count by progress_pct >= 25/50/75/100 respectively
  groups: [{field: {name: "episode_id", type: "event_property"}}]
(no progress event → defer to Phase B detail export, or mark the dimension N/A when neither progress nor duration is tracked)
```

**Query G: Dimension 4 - Cliffhanger Effect (per episode, three metrics)**
```
Reference: references/query_patterns.md → Dimension 4
For each episode i run:
  1. adhoc run --model-type funnel: [play_complete(i) → next_episode_click], window 10s   (episode-end jump)
  2. adhoc run --model-type funnel: [play_complete(i) → next_episode_click], window 5s    (5s cliffhanger jump)
  3. adhoc run --model-type event: play_complete(i) user_count                            (for failure ratio)
```

**Query H: Dimension 5 (full) - Inter-Episode Retention**
```
Reference: references/query_patterns.md → Dimension 5.2
For each adjacent pair i→i+1 run adhoc run --model-type funnel (episode-filtered on both steps)
```

**Query I: Dimension 6 - Binge Depth (Option B)**
```
Reference: references/query_patterns.md → Dimension 6 Option B
adhoc run --model-type event, grouped by user_id, counting distinct episode_id
(Option A detail export is submitted in Phase B)
```

**Query K: Paywall Inference**
```
adhoc run --model-type event:
  metrics: [payment_start(user_count)]
  groups: [{field: {name: "episode_id", type: "event_property"}}]
# smallest episode with a payment event = {paywall_episode}; noted in Checkpoint 1 for user confirmation.
# no payment events → skip Dimension 7 entirely.
```

**Query L: Dimension 7.2 - Post-Payment Watch Rate (funnel)**
```
Reference: references/query_patterns.md → Dimension 7.2
adhoc run --model-type funnel: [payment_start → play_start], window 1 day
```

#### Phase B (after Phase A)

- **Query J: Dimension 7.1 - Payment Trigger Rate** — funnel `[play_start(paywall episode) → payment_start]`, window 30 min; needs `{paywall_episode}` inferred in Phase A.
- Submit the async detail exports in parallel: Dimension 3 pacing fallback / Dimension 6 Option A / churn location (`ae-cli analysis event-detail export ... --output <file>`).

#### Phase C

Poll and download the async detail artifacts: `ae-cli analysis run inspect --run-id <run_id>`, or `ae-cli analysis run wait --run-id <run_id> --output <file>` (already implied by `--output` on export).

---

### 2.3 Correct ae-cli Invocation Flow

**Every query is uniformly executed with `ae-cli analysis adhoc run`:**

```
1. Run ae-cli analysis adhoc run --project-id {project_id} --model-type {event|funnel|retention} --definition '<AI-facing JSON>'

2. Check the result:
   - Returns ok:true with data → read rows / result
   - Returns ok:true but data empty → query succeeded but no matching data; tell the user "query succeeded but no matching data", do not retry
   - Returns AI_QP_COMPILE_FAILED → check meta.errors / meta.resolved and follow the ae-analysis skill's metadata_resolution flow; if necessary ask the user to clarify event/property names
   - Returns other failure (ok:false) → keep error.code / error.message, report the error, do not guess parameters and retry
```

**Important notes:**
- The definition's `time_range` uses `{"mode": "custom", "start_time": "{start_date}", "end_time": "{end_date}"}` and must use the time range confirmed in Step 1
- Do not use defaults like "recent 7 days" for a missing time range
- Query times out or full results needed → switch to `ae-cli analysis adhoc export` (async, returns an artifact); for playback detail use `ae-cli analysis event-detail export`
- Request id uses `--request-id cli_<32 lowercase hex>` (when omitted, ae-cli auto-generates it and prints it to stderr)

---

### 2.4 Data Storage

Store the raw result of each query into an intermediate data structure:

```
raw_data:
  dimension_1:
    first_episode_click_to_play_rate: {raw value}
    first_episode_completion_rate: {raw value}
    ep1_to_ep2_rate: {raw value}
  dimension_2:
    per_episode:
      episode_1: {completion_rate: XX, play_count: XX}
      episode_2: {completion_rate: XX, play_count: XX}
      ...
  dimension_3:
    per_episode:
      episode_1: {retention_25: XX, retention_50: XX, retention_75: XX, retention_100: XX}
      ...
  dimension_4:
    per_episode:
      episode_1: {end_jump_rate: XX, cliffhanger_5s: XX, failure_rate: XX}
      ...
  dimension_5:
    next_day_retention: XX
    per_transition:
      ep1_to_ep2: XX
      ep2_to_ep3: XX
      ...
    churn_distribution: {episode_N: count, ...}
  dimension_6:
    binge_3plus_rate: XX
    binge_median_episodes: XX
  dimension_7:
    payment_trigger_rate: XX
    post_payment_watch_rate: XX
  dimension_8:
    daily_avg_play_count: XX
    new_user_ratio: XX
    play_peak_count: XX
  dimension_9:
    like_rate: XX
    comment_rate: XX
    share_rate: XX
```

### 2.5 Error Handling

- A dimension query failure does not affect other dimensions
- Record the failure reason (event missing, empty data, timeout, etc.)
- Mark in the final report "this dimension was not collected due to XX and has been skipped"
- Uncollected dimensions score N/A, do not participate in the total score, and weights are reallocated proportionally

### 2.6 Minimum Data Volume & Degradation

Before scoring, check each dimension's sample size against the minimum thresholds:

| Condition | Handling |
|---|---|
| Per-episode play sample < 10 | Mark that episode's metric as "insufficient data" and exclude it from scoring |
| Per-episode play sample 10-49 | Mark "low confidence" — score is computed but flagged ⚠️ in the report |
| One sub-metric of a dimension is missing | Drop that sub-metric and re-normalize the remaining sub-metric weights proportionally (see below); mark the dropped sub-metric N/A in the report |
| An entire dimension has no data | Mark the dimension as N/A, exclude it from the total score, reallocate its weight proportionally |

**Degradation strategy:**
- An insufficient-data dimension does not block other dimensions (already guaranteed by 2.5).
- Low-confidence dimensions are scored but annotated; they must never be silently treated as normal-confidence results.
- **Single sub-metric missing (intra-dimension)**: the dimension is still scored from its remaining sub-metrics. Each sub-metric has a weight from `references/dimension_details.md` (e.g. Dimension 4: 0.4 / 0.4 / 0.2). When one is dropped, divide each remaining weight by the sum of the remaining weights so they add up to 1, then compute the dimension score. Only when ALL sub-metrics of a dimension are missing is the whole dimension marked N/A (dimension-level weight reallocation applies).
- When sample sizes are low across the board, state in the Checkpoint 1 summary that "the data volume is limited and results may be unstable" so the user can decide whether to widen the time range before scoring.

### 2.7 Data Collection Complete → Interaction Checkpoint (mandatory)

**After all queries complete, pause and report the collection results to the user, waiting for the user to decide the next step.**

Output the data-collection summary to the user (translate to Chinese per the Language Convention):

```
✅ Data collection complete!

┌────────────────────────────────────────────┐
│                                            │
│  Drama: 《{drama_name}》                      │
│  Period: {start_date} ~ {end_date}         │
│  Episode range: {episode_range_label}        │
│  Drama filter: {drama_filter description or "none"} │
│                                            │
│  Collected: {success_count}/9 dimensions   │
│                                            │
│  ✅ First-Episode Appeal  ✅ Completion Quality │
│  ✅ In-Episode Pacing     ✅ Cliffhanger Effect │
│  ✅ Inter-Episode Retention ✅ Binge Depth      │
│  ✅ Payment Conversion    ✅ Heat Trend         │
│  ✅ User Engagement                            │
│                                            │
│  {if any missing:}                          │
│  ⚠️  Missing dimensions: {missing_list}      │
│     - {dimension name}: {reason}            │
│                                            │
│  {if low data volume:}                      │
│  ⚠️  Data volume is limited; results may be unstable. Consider widening the time range. │
│                                            │
│  ⏱️  Query time: {elapsed_time}              │
│                                            │
└────────────────────────────────────────────┘

Next:
A) 📊 Full scoring — score all successfully collected dimensions (recommended)
B) 🎯 Skip some dimensions — pick the dimensions you care about
C) ❌ Stop — the data is not ideal, do not continue

Which one?
```

**Interaction rules:**
- If all 9 dimensions are collected successfully, recommend option A by default, which can be confirmed directly
- If any dimension is missing, guide the user to decide whether to adjust query conditions and re-collect
- When the user chooses B, list all dimensions and let the user check which ones to score
- When the user chooses C, terminate the flow and tell the user they can restart anytime
- **Must wait for the user's explicit choice before entering Step 3**

## Output

- `raw_data`: the per-dimension raw result structure defined in 2.4, with each metric labeled normal / low-confidence / insufficient-data per 2.6.

## Verification

- [ ] Every dimension returned a result or a recorded failure reason — no dimension was silently dropped.
- [ ] The episode count in `{target_episodes}` matches the queried episode list.
- [ ] The data-volume check (2.6) was applied to every metric; low-confidence / insufficient-data metrics are labeled.
- [ ] Every query used the Step-1-confirmed `{start_date}` ~ `{end_date}`; no "recent 7 days" default crept in.
- [ ] `drama_filter` was attached uniformly to every query when non-empty.
