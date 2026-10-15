---
name: nth-event-tag-builder
description: Build a SQL user tag for "the Nth time a user triggered an event" (e.g. 3rd payment) or "the most recent N within a window" (e.g. average score over the last 30 games). Triggered when the user asks "which Nth payment/draw", "the Nth time since registration/launch", or "average over the last N games". Takes project ID, event(s), scenario (Nth vs recent-N), user ID, timezone; returns a ready-to-paste SQL tag definition plus the tag link. Ask for project ID, never guess. N is set at analysis time, not build time. Not for first-event attribution / retention / funnel / tag-system design.
version: 3.0.2
compatibility: ae-cli >= 6.0.49 (auto path); manual UI path needs no CLI
---

# Nth Event Tag Builder

Computes "which Nth time a user triggered an event" as a SQL tag, then filters by that tag in event analysis / distribution analysis to answer two business questions:

| Scenario | Business question | Ordering | Time policy |
|---|---|---|---|
| **Scenario 1: Nth occurrence** | Which Nth time (since launch) a user triggered an event — e.g. time-to-reach distribution of 1st/2nd/3rd payment, lifecycle distribution of the 3rd payment | ascending (`ORDER BY #event_time ASC`) | static (launch → today) |
| **Scenario 2: Recent N** | The most recent N occurrences within the last x days — e.g. average score over the last 30 games, win rate over the last N games | descending (`ORDER BY #event_time DESC`) | dynamic (last x days) |

Source: Feishu doc《用户第几次触发xx事件》(docx: doxcnIJhFiUgKTqPrmnfc4ycGyh). This skill turns that doc's manual flow into an executable protocol and fills in the gaps the doc omits (view name, ID choice, timezone, entity reuse).

---

## Decision Tree (confirm before acting)

Example inputs that trigger this skill: "第3次付费" (3rd payment), "最近30场场均分" (average score over the last 30 games), "第几次抽卡" (which draw).

```
User request
├── Nth occurrence ("which Nth payment", "the Nth time since registration")
│   └── Scenario 1 → ascending row_number + static time since launch
├── Recent N ("last N games", "most recent N within x days")
│   └── Scenario 2 → descending row_number + dynamic time (last x days)
└── unclear → ask: "Do you want the cumulative Nth since launch, or the most recent N within x days?"
```

**7 things to confirm with the user** (all mandatory, never guess):

1. **Project ID** — which project to build the tag in. **If the user did not provide a project ID, ask them directly** — do NOT guess, do NOT enumerate all accessible projects hunting for the event. **Exception**: if the user *named* the project (e.g. "休闲游戏demo", "游戏DEMO") but gave no numeric ID, resolve it once via `ae-cli project info list` — if exactly one name matches, use it; if several match or none matches, ask the user which one (show the candidate list).
2. **Event name** — which event(s) to count (can enumerate several, e.g. `payment`, `order_init`; see Pitfall 3)
3. **Scenario type** — Nth occurrence or Recent N?
4. **Start date (Scenario 1 only)** — the launch/start date for "since X → today". **Ask the user for the exact date**; do NOT guess it from the project's data or hardcode an arbitrary date. Used as the anchor in `recent_day: "<date> 00:00:00@@0"`.
5. **User ID** — which ID to count by? Offer common candidates (`#account_id` account / `#user_id` user / `#device_id` device / `#distinct_id` visitor) or let the user type their own (may be any event or user property), never guess; see Pitfall 2
6. **Timezone** — which timezone slices the window (last x days / launch→today)? **MUST confirm, never assume the default.** `ae-cli project timezone get -p <project_id>` returns both `default_time_zone_offset` (the project default, NOT a confirmed choice) and `available_time_zones` (the list the project actually allows). Present the options as `UTC±n` for **every** value in `available_time_zones`, marking `default_time_zone_offset` with a "(project default)" tag rather than auto-selecting it. **Do NOT collapse into a "+8 / other" binary and do NOT add an "other" catch-all** (the user would just re-enter a value you already have). The default is only a suggestion — a cross-timezone business may need a different offset, and picking the wrong one shifts the day-slice boundary. See Pitfall 7.<br><br>**Option-count limit**: the question UI caps each question at 4 options. If `available_time_zones` has more than 4 values, list the full set **in the question text** (e.g. "可选：-10/-9/-8/-7/0/+8/+12/+14") and offer the top candidates (project default + the offsets most relevant to the business, e.g. the local-market offset) as the 4 clickable options. The user can type any other offset via the free-text field.
7. **Auto-refresh schedule** — frequency + daily run time (e.g. daily 01:01, weekly Monday 03:00). **Confirm with the user, do NOT hardcode a time.** Only asked if auto-refresh is enabled (which it should be — see Step 5).

> **No N in this list on purpose** — N is not a tag-build input. The tag SQL only encodes the window (x days) + ordering (asc/desc); the `rowid <= N` / `rnk = N` cutoff is applied later, at analysis time (Step 4). Only ask for the **window** (Scenario 2's x days).

### Quick Start (new-user entry point)

The whole build is 5 steps. If you are new to this, follow them in order and ask the user for any missing requirement instead of guessing.

1. **Confirm the 7 requirements** (project ID, event, scenario, start date / window, user ID, timezone, auto-refresh schedule) — see the list above.
2. **Check for an existing entity** (`project entity list`) and reuse it if the ID caliber matches; otherwise build a "user+event+time" virtual property + entity.
3. **Create the SQL tag** with the scenario's ordering + time policy.
4. **Filter by the tag in analysis** (e.g. "Nth trigger = 3") to get the distribution.
5. **Enable auto-refresh** so the tag stays current.

**FAQ:**

- **"Do I write N into the tag?"** No. The tag numbers every occurrence `1..K`; you pick N later at analysis time as a filter (`rnk = N` / `rowid <= N`).
- **"Which ID should I count by?"** `#account_id` if login is required; `#device_id`/`#distinct_id` for anonymous play. Pick the one that best represents the "user" you care about — never guess.
- **"Nth (Scenario 1) or recent N (Scenario 2)?"** Scenario 1 = cumulative since a start date (1st/2nd/3rd ever). Scenario 2 = most recent N within a rolling window (last-30-games average).
- **"What timezone does the window use?"** Ask the user; the project default is only a suggestion. The wrong offset shifts the day-slice boundary.
- **"My tag shows 0 users / wrong numbers."** Walk the Debug flow in `references/pitfalls.md` — the first two pitfalls (wrong view name, wrong user ID) account for most issues.

---

## Workflow (Step 0 + 4 steps, across 3 modules)

> Two execution paths: **① ae-cli direct** (when the Agent has ae-cli; commands below) **② platform manual guidance** (no ae-cli; guide the client through the UI). The SQL is identical on both paths.

### Step 0 (env check): is ae-cli available?

```bash
which ae-cli
```

- **Present → use the ae-cli direct path** (Steps 0b–3 below).
- **Missing → switch to the manual guidance path** (see Output Contract, "Without ae-cli"), and do NOT attempt the CLI commands.

### Step 0b (pre-check): is there already a usable "user+event+time" entity?

**Must check before building any virtual property**, to avoid duplicates:

```bash
ae-cli project entity list -p <project_id>
```

- Look for an entity bound to a "userID + event name + event time" concatenation virtual property (column_name like `#vp@xxx`, entity_name containing "event time"/"concat")
- **Usable entity exists → skip Step 1+2**, take its `entity_id` straight to Step 3
- ⚠️ **Before reusing, verify the entity's ID caliber matches** — run `ae-cli analysis-meta property get -p <project_id> --table-type event --prop-name '<column_name>'` and read `vir_prop_column_rule`. An entity built on `#user_id` cannot serve a `#distinct_id` request (and vice versa); if the IDs differ, build a fresh property+entity for the requested ID (Pitfall 11).
- **None → build via Step 1+2**
- A "account + event time" legacy entity that is **missing the event-name dimension** cannot be reused — build the full triple concatenation

### Step 1: create virtual event property "userID + event name + event time"

**ae-cli**:

```bash
ae-cli analysis-meta virtual-property create --project-id <project_id> \
  --property-name '#vp@id_event_time' --table-type event --select-type string \
  --sql-expression 'cast("<userID>" as varchar)||"#event_name"||cast("#event_time" as varchar)' \
  --sql-event-relation-type relation_default
```

Fill `<userID>` per question 5 (`#account_id` / `#user_id` / `#device_id` / `#distinct_id`, or a user-supplied event/user property).

⚠️ **`<userID>` must be `cast("<userID>" as varchar)` in this expression** — never the raw column (numeric IDs break `concat`). The type is validated **asynchronously**, so a raw `bigint` fails silently later and the bound entity/tag breaks. Cast here AND in the Step-3 tag SQL. See Pitfall 10.

**Manual**: Metadata → Event properties → +virtual event property, type text, same SQL.

Purpose: give each event a unique "user × event × time" identifier as the source for the next multi-analysis entity.

### Step 2: add multi-analysis entity "user+event+time"

**ae-cli**:

```bash
ae-cli project entity create --project-id <project_id> \
  --entity-name 'user+event+time' --column-name '#vp@id_event_time' --table-type 0
```

`--table-type 0` = event property (1 = user property). Record the returned `entity_id` for Step 3.

**Manual**: Project management → Analysis config → Entity config, add an entity from Step 1's virtual property.

Purpose: let the tag be built on the "user+event+time" granularity (default entity is user only).

### Step 3: create the SQL tag (core; pick one scenario)

⚠️ **Never guess or construct the event-table name.** Run `ae-cli analysis sql-table list -p <project_id> --usage tag_cluster`, select the exact server-authorized `table_ref` for the event view, and reuse that value in both `sql-table columns` and the tag SQL. The SQL `id` column is written as an inline concatenation expression — do NOT reference the virtual property column (event views have no `#vp@` columns).

The two scenarios differ **only in ordering and time policy**; the `id` concatenation, `$part_event` enumeration, and `PARTITION BY "<userID>","#event_name"` double grouping are identical:

| Difference | Scenario 1 (Nth) | Scenario 2 (Recent N) |
|---|---|---|
| Ordering | `asc` (rnk=1 is first) | `desc` (rowid=1 is most recent) |
| Time policy | anchored `recent_day: "<launch_date> 00:00:00@@0"` (fixed start → today, end rolls daily) | relative `recent_day: "0-x"` (last x days) |

> The SQL numbers every occurrence in the window (`1..K`) — the cutoff `rowid <= N` / `rnk = N` is applied at analysis time (Step 4), never written into the tag. Full SQL templates + ae-cli commands + `recent_day` encoding: [references/recipes-and-cli.md](references/recipes-and-cli.md).

### Step 4: filter by the tag in an analysis model

- **Scenario 1 example**: Event analysis → metric "completed-order unique users" → filter "Nth trigger = 3" → group by "lifecycle days" → lifecycle distribution of the 3rd payment
- **Scenario 2 example**: Event analysis → metric "average settlement score" → filter "recent Nth game ≤ 30" → average score over the last 30 games

(lifecycle days is a separate virtual property — see Pitfall 5)

### Step 5: enable auto-refresh (MUST do; prefer the CLI, fall back to a UI reminder)

The tag is created with `enable_auto_refresh: 0` (auto-refresh OFF) unless you explicitly enable it. **Confirm the schedule with the user — frequency and time — do NOT hardcode `01:01`.** Ask once (e.g. "自动更新频率和每天几点跑？"), or offer candidates (daily 01:01 / daily 02:30 / weekly Monday 03:00). Two paths to apply it:

1. **CLI (preferred, ae-cli ≥ 6.0.49)** — enable it at build time or later:
   - On `create`: add `--enable-auto-refresh true --auto-refresh-schedule '{"frequency":"daily","time":"<HH:MM>"}'` (or `--auto-refresh-cron` for a custom Quartz cron).
   - On an existing tag: `ae-cli analysis user-tag update -p <project_id> --tag-name <tag_name> --enable-auto-refresh true --auto-refresh-schedule '{"frequency":"daily","time":"<HH:MM>"}'`.
   - `--auto-refresh-schedule` takes `frequency` (daily|weekly|monthly), `time` HH:mm, and for weekly `weekdays` (ISO 1=Mon…7=Sun) / for monthly `month_days` (1–31). `--auto-refresh-cron` and `--auto-refresh-schedule` are mutually exclusive.
   - Verify with `user-tag get`: `enable_auto_refresh` becomes `1` and `scheduler_ui_config` is populated (e.g. `{"schedule_type":"DAY","hours":"1","minutes":"1"}`).
2. **UI (fallback, older ae-cli)** — if the CLI lacks these flags, remind the user to enable it in the tag detail page. **Keep the reminder to one line — do not list step-by-step click instructions.**

The refresh semantic by scenario: Scenario 1 (Nth, anchored `@@0`) re-runs daily and only appends larger Ns (existing Nth numbering never changes); Scenario 2 (recent-N, `0-x`) rolls daily so the window shifts. Either way, without auto-refresh the tag freezes at build time.

---

## Analysis Framework (4 lenses)

The Nth-occurrence tag answers four distinct operator questions that DAU/retention cannot. Apply the tag through each lens to get a complete picture:

1. **Time-to-Nth (conversion bottleneck).** How long after registration/launch does a user reach their 1st/2nd/3rd payment? Build Scenario 1, then group by "days since registration" to find where the funnel stalls. A long gap to the 2nd payment signals weak re-purchase incentive — the classic fix target.
2. **Lifecycle at Nth (habit formation).** At what lifecycle stage does the 3rd payment (or 3rd draw) happen? Cross the tag with lifecycle-day segments to judge whether paying is becoming a habit or stays a one-off.
3. **Value stratification (targeted ops).** Segment users by their current Nth count (1×/2×/3× buyer) and run differentiated campaigns — first-time buyers get retention nudges, high-N buyers get loyalty offers.
4. **Recent-N behavior (current-state vs history).** For repeatable loops (battle, gacha, spin), Scenario 2 tracks a user's last-N results — e.g. average score or win rate over the last 30 games — to flag players who are currently underperforming their own baseline.

| Industry | Concrete question | Lens + tag used |
|---|---|---|
| Gaming — monetization | When does the 2nd/3rd payment happen, and at what lifecycle stage? | Lens 1+2, Nth of `payment` |
| Gaming — gacha | How many draws before the distribution levels off? | Lens 3, Nth / recent-N of `draw_card` |
| Gaming — battle/PVP | A player's average score over the most recent 30 games? | Lens 4, recent N of `battle_win` / game-over |
| Casino/slots | When does the Nth spin happen relative to registration? | Lens 1, Nth of `spin` |

The tag answers "the Nth time" precisely, which generic DAU/retention metrics cannot.

---

## Boundary Statement

This skill is NOT applicable when:

1. You need **first-event attribution** (ice-breaking time, first payment time, first occurrence) — not covered here (no dedicated sibling skill yet; handle manually or via a first-event virtual property).
2. **Data volume < ~1,000 users** — occurrence-order statistics are unstable and not statistically meaningful.
3. The project tracks **no ID field at all** and no usable entity can be built — there is nothing to partition by.
4. You need **overall tag-system design** (naming, hierarchy, governance) — not covered here (no dedicated sibling skill yet; this skill only builds one occurrence-order tag).

---

## Degradation Strategy

| Missing / degraded condition | Fallback | Precision impact |
|---|---|---|
| No `#account_id` (no login) | use `#distinct_id` or `#device_id` | counts per visitor/device instead of per account |
| `#account_id` low coverage on some platforms | use `#device_id` for those platforms, or ask client to check coverage | cross-device users may be split |
| `lifecycle days` virtual property missing (Scenario 1 grouping) | group by event time (by day/week) instead | loses "days since registration" view |
| Data volume small | widen the time window, or switch to Nth (cumulative) instead of recent-N | fewer samples, larger confidence interval |

---

## Pitfalls (doc-omitted, Agent-must-know; details in references/pitfalls.md)

| # | Pitfall | Correct handling |
|---|---|---|
| 1 | guessing or copying an event-table name | copy the exact event-view `table_ref` from `analysis sql-table list --usage tag_cluster`; write the `id` column inline, no virtual-property reference |
| 2 | wrong user ID | confirm with user which ID to count by (candidates + user self-input), never guess |
| 3 | event enumeration | enumerate target events via `$part_event in (...)`; PARTITION by `"<userID>","#event_name"` for per-event independent counting |
| 4 | ascending/descending swapped | `asc` = first occurrence (Scenario 1); `desc` = most recent (Scenario 2) |
| 5 | lifecycle-days property missing | Scenario 1's lifecycle grouping depends on a separate virtual property; guide creation first |
| 6 | tag refresh policy unclear | Scenario 1 static (values only grow); Scenario 2 dynamic (rolls daily); inform the client. **Also: tag is created with auto-refresh OFF — enable it via `--enable-auto-refresh true --auto-refresh-schedule ...` (ae-cli ≥ 6.0.49), or remind the user to turn it on in the UI on older versions (Step 5)** |
| 7 | timezone unconfirmed | slice boundary depends on timezone; pass `--zone-offset`; otherwise `zone_offset=99` (unbound) and slices by raw `#event_time`. Ask with `available_time_zones` enumerated as `UTC±n` options; if >4 values, list them all in the question text and offer 4 clickable candidates (default + top business-relevant offsets) |
| 8 | didn't check existing entity | check `entity list` first; reuse a full "user+event+time" entity, don't rebuild |
| 11 | existing entity uses a different ID | before reusing, verify the bound virtual property's `vir_prop_column_rule` via `property get --prop-name '#vp@xxx'` — an entity built on `#user_id` cannot serve a `#distinct_id` request; build a fresh property+entity for the requested ID |
| 9 | "自某日至今"写错 | 用 `recent_day: "<date> 00:00:00@@0"`（固定起点+动态终点，`@@0`=含今天）；`end_time:"today"` 被后端拒绝、`end_time:"2099-12-31"` 是终点不滚的静态 hack，都别用 |
| 10 | numeric user ID breaks concat | cast `"<userID>" as varchar` in the `id` column when it's `bigint` (e.g. `#user_id`); PARTITION keeps raw column |

---

## Output Contract

**With ae-cli (preferred, fully automatic)**: confirm requirements → Step 0 env check → Step 0b check existing entity → Step 1/2 build property+entity → Step 3 build tag → wait for completion → **deliver the tag link → enable auto-refresh (Step 5, CLI preferred)**.

**Without ae-cli (manual guidance)**: never dump all steps at once; guide step by step:

1. Confirm requirements: project ID, event(s), scenario, window (Scenario 2's x days), start date (Scenario 1), user ID, timezone, auto-refresh schedule (7 questions; project ID, start date, and refresh schedule must be asked if missing — N is NOT asked here, it's applied at Step 4's analysis filter)
2. Output Step 1+2 config; wait for client confirmation
3. Confirm the exact event-view `table_ref` returned by `analysis sql-table list --usage tag_cluster`
4. Output Step 3 SQL + time policy
5. Output Step 4 analysis config
6. Deliver the tag link: `ae-cli analysis-meta asset url-get --resource-type tag --resource-id <tag_id>` (resource type must be `tag`, not `user_tag`)
7. Enable auto-refresh via CLI (Step 5) using the user-confirmed schedule: `--enable-auto-refresh true --auto-refresh-schedule '{"frequency":"<freq>","time":"<HH:MM>"}'`; on older ae-cli, remind the user to enable it in the UI

Wait for the client's "done" after each step. Debug via pitfalls.md on errors.

---

## Skill Boundaries

| Need | Use |
|---|---|
| First occurrence (ice-breaking, first payment, first time) | (no dedicated skill yet — handle manually or via first-event virtual property) |
| **Nth occurrence / recent N** | **this skill** |
| New/returning user definition & property | (in development) |
| Overall tag-system design | (no dedicated skill yet — this skill only builds one occurrence-order tag) |
| Tracking plan / event design | ae-generate-tracking-plan |

---

## References

| File | Purpose | When to read |
|---|---|---|
| [references/recipes-and-cli.md](references/recipes-and-cli.md) | Full command sequence + SQL templates + `recent_day` encoding | Step 3 (build tag) — the authoritative command/SQL source |
| [references/pitfalls.md](references/pitfalls.md) | 11 pitfalls with symptom/cause/fix + Debug flow | On any build error or "numbers are wrong" report |

## Prerequisites (data & environment)

**Event tracking (required).** You need at least one reportable event that fires each time the counted action happens, e.g. `payment`, `draw_card`, `battle_win`, `spin`, `shop_buy`. The event must carry a usable `#event_time` (always present on real-time reported events) and be partitioned by `$part_event`/`$part_date` for fast filtering.

**ID field (required).** The project must track at least one ID to partition by — `#user_id` (user), `#account_id` (account), `#device_id` (device), or `#distinct_id` (visitor). No ID field at all → nothing to partition by, this skill cannot run (see Boundary Statement).

**Data volume (minimum).** At least ~1,000 users, otherwise occurrence-order statistics are unstable and not statistically meaningful. Below this, widen the window or fall back to a coarser ID caliber rather than trusting a noisy Nth distribution.

**Environment (ae-cli).** The automated path requires ae-cli (`npm i -g ae-cli`, ≥ 6.0.49 for auto-refresh flags). Run `which ae-cli` first (Step 0) — if absent, use the manual guidance path, which needs no CLI.

**Permissions (required).** Building this tag writes project metadata — the operator (or the ae-cli identity) must hold **project edit permission**, specifically: (1) `virtual-property create` on event properties (Step 1), (2) `entity create` for multi-analysis entities (Step 2), and (3) `user-tag create`/`user-tag update` for the SQL tag and its auto-refresh schedule (Step 3/5). A read-only role cannot complete the build — it fails on the first create call with a permission error. If the operator lacks edit permission, ask the project owner to either grant temporary edit access or run the build on their behalf.

**Preflight check (verify data before building).** Before Step 0b, confirm the project actually satisfies the above requirements instead of assuming:
```bash
ae-cli analysis-meta event list -p <project_id> \
  --queries '["<event_name>"]' --fields '["event_name","event_desc"]'
ae-cli analysis sql-table list -p <project_id> --usage tag_cluster
ae-cli analysis sql-table columns -p <project_id> \
  --table-ref '<event_table_ref>' --usage tag_cluster
```
- Confirm `event list` contains an exact `event_name` match; a fuzzy description-only match is not enough.
- Copy `<event_table_ref>` from the selected event-view row returned by `sql-table list`; do not construct it from the project ID.
- Confirm the selected table contains `#event_time`, `$part_event`, and the chosen ID field.
- Confirm the chosen ID field (`#account_id` / `#user_id` / `#device_id` / `#distinct_id`) has non-empty coverage (see Pitfall 2).
- If any requirement is missing, stop and tell the user which one — do not build a tag that will silently produce wrong counts.

## Verification (closed loop)

After the tag is built and analyzed, verify the result is trustworthy before acting on it:

1. **Progress gate.** Follow the exact `next_action`, `next_capability_id`, and `next_input` returned by `user-tag get`. After creation, the tag is usable only when `progress=100` and `refresh_time` is present; before then, do not read `users_num` as a completed result.
2. **Count sanity check.** The total `users_num` should be in a plausible band for the event's `last_day_count`. A wildly off number (e.g. 1,000× the daily trigger count) means the ID caliber or the event enumeration is wrong — re-check Pitfalls 2 and 3.
3. **Spot-check rnk/rowid.** Preview the tag members and confirm the `rnk=1` / `rowid=1` row is the expected occurrence (first vs most recent). If the meaning looks inverted, the ascending/descending order is swapped (Pitfall 4).
4. **Compare before/after.** For a Scenario 1 "Nth" fix (e.g. boosting the 2nd payment), compare the time-to-2nd-payment distribution across 30 days before vs 30 days after the campaign to validate the intervention.
