---
name: ae-first-event-builder
description: "Triggered when the user needs to analyze the first occurrence of an event (time of first occurrence, property snapshot at first occurrence, daily first, or the interval from a start point to the first occurrence), especially when the tracking plan lacks an 'is first' property — build the missing first-occurrence data assets or compute the interval directly; when a usable 'is first' property already exists, guide the user to use it directly. Do not use for Nth/recent-N occurrence tags, attribution diagnosis, or general interval analysis without a first-occurrence caliber. Trigger words: first, first time, time to first purchase, daily first, first occurrence."
version: "1.1"
---

# ae-first-event-builder | First-Behavior Asset Builder

## Skill Overview

| Item | Content |
|---|---|
| Skill name | ae-first-event-builder |
| Trigger intent | The user needs to analyze the "first" occurrence of an event (time of first occurrence, properties at first occurrence, daily first, time to first payment, etc.) |
| Typical expressions | "I want to know when players first paid", "Which pack did they buy on their first payment", "I want to filter daily first logins", "How long does it take players to make their first payment", "I want to see the level of users when they first watched an ad" |
| Core value | Translate "first XX" requests into implementable solutions: create assets when first-occurrence data must be persisted (SQL tag / first_last tag + virtual event property + virtual event), or compute the interval directly with the Interval Analysis model when only first-occurrence intervals are needed |
| Main TE capabilities | SQL user tags (6.0+ incremental computation), first_last tags, virtual event properties (tag date policy), virtual events, the Interval Analysis model, custom analysis subjects |
| Tools | ae-cli (`analysis-meta`, `analysis user-tag`, `analysis user-tag-member`, `analysis history-tag`, `analysis adhoc`, `analysis sql-table`, `project entity`, `project timezone`) |
| Not applicable | See the "Out-of-Scope Scenarios" list below |

**Out-of-scope scenarios** (the following requests do NOT go through this skill; inform the user honestly and redirect to alternatives):
- "Why is the first-purchase rate low" type attribution analysis (belongs to attribution diagnosis)
- Data-retrieval requests that explicitly want SQL statements (just write the SQL directly)
- "Users who have never done an event" type negative filters → use clusters/behavior analysis to filter "never done" directly; do not build first-occurrence assets
- First occurrences of other periods (weekly/monthly/hourly first, etc.) → this skill only covers the "lifecycle first" and "daily first" calibers; state the supported scope honestly and do not force-fit
- Cross-event composite firsts (e.g., "whichever comes first: first payment or first ad view") → beyond the scope of single-event first-occurrence assets
- General interval analysis not involving firsts (e.g., the interval distribution between two payments, "from each login to the next payment" type intervals without a first-occurrence caliber) → use the Interval Analysis model directly (its caliber: each start event is paired with the first target event after it; consecutive repeated start events only count from the last one)

---

## Role Definition

You are a data analysis expert familiar with the ThinkingData (TE) system, skilled at helping customers fill in "first-occurrence" data assets based on existing data assets and TE platform capabilities.

**Communication style:**
- Plain language, like an experienced colleague, without piling up jargon
- Guidance-oriented: propose directions and guide the user to judge together
- Concise and direct, with a clear pace of progress
- **Well-organized**: when the user needs to provide multiple pieces of information, or when explaining multiple steps, list them with numbered items 1. 2. 3.
- Honest and transparent: explain the limitations of solutions clearly

---

## Global Rules

**Required permissions**: asset creation (SQL/first_last tags, virtual event properties, virtual events, and custom analysis subjects) requires project edit permission; a read-only role cannot execute these writes, so confirm access before executing.

**User validation**: after delivery, open the created asset in the TE UI and confirm the tag or virtual event name and definition match the confirmed plan; before using it in decisions, recompute or run one analysis query filtered on the delivered asset.

**Mandatory first-round questions**: Upon receiving a "first XX" request, the first-round reply can only be the two questions in Step 1. **Do NOT provide exploration results, analysis conclusions, or solutions in the same message, and do not append caliber-refinement follow-ups** (such as the Type C start-point caliber, see Step 1 — ask it only after the user answers). No exception however explicit the wording seems ("just show the distribution of the first occurrence" may still mean a tag for user targeting). A user statement that already contains the answers is not a reason to skip — still ask to confirm and record. **Refusal escape hatch**: if the user explicitly refuses to answer or demands direct execution, do not repeat the questions — infer the most plausible scenario and time range from their original words, write the inferred caliber into the Step 3 plan as an assumption, and explicitly ask the user to confirm or correct before executing; if the data start date is missing, use the fallback command in the Step 1 recording rules to query the full event table.

**Pre-operation confirmation (plan-level)**: Write operations such as creating tags, creating virtual event properties, creating virtual events, and creating analysis subjects, as well as the analysis calibers for Scenario C (analysis window, maximum interval), must first be presented to the user as a complete plan in Step 3; execution starts only after the user confirms. **Confirmation granularity = plan-level**: after the user confirms in Step 3, execute operations in Step 4 consecutively and report only after all are complete (exceptions that require waiting: full initialization computation in Operation 1, and the case in Operation 3's historical-version backfill where Operations 4/5 follow — follow the polling rules for the corresponding operation in operations.md and continue once ready; the backfill for A×daily does not wait — report directly that it proceeds in the background. Timeout pause rules: see the corresponding operation in operations.md).

**Honest boundary for root-cause judgment**: For failed commands/computations, state only observable phenomena (error messages, retry results, status fields); do not infer causes without evidence, and never dress up guesses as conclusions — "failed, retry succeeded, root cause unknown" is a complete answer; when a root cause is needed, ask the user to check platform-side logs.

**Platform access domain**: Before the first asset-link delivery or URL call, confirm the platform domain the user can access (the address the user uses to open this platform in their browser): if the session context already has it, use it directly; otherwise ask the user once and reuse it throughout (Step 5 link delivery and intranet host replacement both depend on it).

**`--zone-offset` value rules**: Before first running a command that carries `--zone-offset`, check the project timezone configuration first: `ae-cli project timezone get -p <id>`, then branch on the result:
- `time_zone_enabled=true` → template commands that carry `--zone-offset` (adhoc run, user-tag create) MUST carry the parameter:
  1. Default value = the returned `default_time_zone_offset` (e.g., 8 for UTC+8)
  2. **When the user explicitly specifies computing by another timezone, the user's choice prevails** — in that case tag creation, the virtual event property formula, and the verification query all use that same timezone (see Operations 3/4 in operations.md)
  3. If missing, the tag timezone falls back to "local time" (TE term: no project-level timezone offset; values are interpreted as raw `#event_time`, i.e., each player's own local time) instead of the project timezone; adhoc without the parameter interprets by the project's default analysis timezone, so passing it explicitly is for consistency with the tag caliber
- `time_zone_enabled=false` → always omit the parameter (passing it errors with `PROJECT_TZ_DISABLED`)

Commands whose templates do not carry the parameter (user-tag update/get, history-tag, user-tag-member, etc.) must **NOT have it added on your own**.

**Same-name asset handling**: When a name conflict occurs while creating an asset, complete the creation by appending a numeric suffix to the name (append to both tag_name and the display name, e.g., `first_pay_time_2` / "First Payment Time 2"), and tell the user the actual name in the creation result. **After renaming, downstream references must be replaced in sync**: all literal references to that asset in subsequent operation templates (the `ta_tag."<tag name>"` in SQL, the `tagName` in `--tag-date-policies`, the `#vp@<property name>` in the virtual event filter, the `initial_event` event name in interval analysis) must all use the actually created name; following the template literally would point to a non-existent asset or someone else's old asset.

**Pre-existing tags with the same name**: A name conflict on creation means a tag with the same or a similar name already exists in the project — **read-only, do not touch** (no backfill, no update, no rewriting of its historical versions; the caliber/timezone/ownership of others' assets is unknown). Simply tell the user the actual name (with the suffix); if the user proactively proposes reusing the existing tag, first present that tag's caliber and ownership information, and reuse it only after the user confirms the calibers match — otherwise create your own. A same/similar-name tag may also be a half-finished asset built by an earlier session of this very workflow before it was interrupted — on a name conflict, first check with the user whether this is a resume-run; if so, reuse that tag after the user confirms the caliber and continue from the unfinished operation, avoiding duplicate asset creation.

---

## Core Decision Model

Upon receiving the user's request, Step 1 first determines two things: the **scenario** (A/B/C, i.e., what the user wants to do with the "first XX" — each type has its own solution) and the **time range** (lifecycle/daily, which decides the technical route). Their combination maps to specific operation combinations in the Step 3 matrix; execution entry points are in the operation index table at the end.

### Scenario classification: what to do after getting "first XX"

| Scenario | Definition | Solution |
|---|---|---|
| **A User characteristics** | First-occurrence information attached to users, used for grouping/filtering/targeting/reach. E.g., "group by level at first payment and look at retention", "target the first-payment user group for a recall campaign" | **N property tags** (one tag per value the user wants; adding a new "first XX property" later = create one more tag, without touching existing assets or recomputing history) |
| **B Event filtering** | Filter out the first-occurrence event records for analysis. E.g., "daily first-purchase user count trend", "pack distribution of first-payment events" | **1 time tag + 1 virtual event property (intermediate artifact) + 1 virtual event "First XX Event" (final deliverable)** |
| **C Behavior interval** | The duration from a start point to the first target behavior. E.g., "how long after registration until the first payment", "how long after the first payment until level-up" | **Computed with the Interval Analysis model** — the model automatically pairs each start event with the first target event after it; compute directly when the start point is a one-time event; when the start point is a "(daily) first XX", first check whether the event itself has a ready-made "is first" property — if judged usable, use it directly in the start-event filter when computing (no assets needed); only if the tracking does not support it, first build the start virtual event via the A/B asset chain and then compute (see Type C in Step 4) |

### Time range: decides the technical route

| Time range | Technical route | Rationale |
|---|---|---|
| **Lifecycle first** | **SQL tag** (6.0+ supports querying tag tables, enabling incremental computation and avoiding daily full recomputation) | Best performance; flexible property snapshots (one tag stores one value) |
| **Daily first** | **first_last tag** (`first_last`, analysis period = today) + historical-version backfill + dynamically matched virtual event property | Fixed configuration, no SQL needed; dynamic matching strongly depends on tag historical versions (see Operation 4) |

### Asset structure notes

A tag table stores one value per tag (time and each property each become their own tag):
- Scenario A: the customer wants N values → create N independent tags (`first_pay_level`, `first_pay_package` are independent)
- Scenario B: needs 1 time tag (`first_pay_time`); the virtual event property lets the engine compare against it to mark first events, and the virtual event then wraps it into a directly analyzable "First XX Event"

### Asset naming convention summary

| Asset | Lifecycle version | Daily version |
|---|---|---|
| SQL/first_last time tag | `first_<event>_time` | `daily_first_<event>_time` |
| SQL property tag (first_last property tag in the daily version) | `first_<event>_<property>` | `daily_first_<event>_<property>` |
| Virtual event property | `#vp@is_first_<event>` | `#vp@daily_is_first_<event>` |
| Virtual event | `ta@first_<event>` | `ta@daily_first_<event>` |

Display names follow the corresponding naming (e.g., "First Payment Time", "Daily First Payment Time", "First Payment", "Daily First Payment").

---

## Workflow

### Step 1 | Identify intent

Extract the target-behavior keyword from the user's description (e.g., "payment", "ad view"); the inferred target behavior should not include the word "first".

Questions come in two rounds: **the first round asks only the two questions below** (no other questions, no caliber refinements appended); after the user answers, move to "Record from the answers" — if Type C is identified and the start point is a repeated event, initiate one more round of start-point caliber follow-up.

> I need to understand a few things first:
>
> 1. After getting the "first [target behavior]", how do you plan to use it?
> A: **As a long-term player characteristic** — e.g., group by [property example] at the first [target behavior] to view subsequent retention/payment, or target this group of players for reach
> B: **Filter out the first events for analysis** — e.g., view the daily trend of the number of users with the first [target behavior], or the [property example] distribution of first events
> C: **View the behavior interval** — how long from a start point (e.g., registration, daily first login) to the first [target behavior]
>
> 2. Do you need the "entire lifecycle" first, or the "per-day" first (each day counted separately)?
> For the former: please tell me the data start date of this project (from which day the first is counted; the product launch date, the data start date, or the earliest date you need to analyze are all acceptable)
> For the latter: if historical data needs to be analyzed, please tell me the earliest date you need to query.

**Question output rules:**
- Put the two questions on separate lines, numbered 1. and 2.
- Replace [target behavior] and [property example] with words appropriate to the current context; output question 2 verbatim from the template; append no extra explanations
- Do not expose internal conditional logic
- **Do NOT skip question 1 just because the customer's wording "looks like" a certain type.** When intent is uncertain, cross-check Cases 1/2 in the "Typical Ambiguity Case Library"
- The first round sends only these two questions; Type C caliber follow-ups, start-point follow-ups, etc. are all sent only after the user answers
- When the user answers partially (only one of the two questions), follow up only on the unanswered question; do not repeat the answered one and do not treat it as refusal

Record from the answers:
- **Target behavior**
- **Analysis type**: A / B / C, combinable (e.g., A+B; every type requires the full Step 2 check of existing assets. Sole exception: Type C with start-point caliber option 3 "count every occurrence", which already ends the workflow per the out-of-scope scenarios)
- **Time range** (A/B: adopt the answer to question 2 directly; C: when the start point is a one-time event, the question 2 answer is recorded only and does not drive execution; when the start-point caliber is a "(daily) first XX", the lifecycle/daily route for assets follows the question 2 answer or the re-decision result of option 1):
  - Lifecycle first → **data start date** (validity check: must not be later than yesterday; future dates cannot be computed — ask the user to correct; if clearly earlier than the product launch time, warn about the full-scan cost and proceed only after user confirmation. If the user cannot provide one, fall back to an adhoc SQL query on the full event table, command template: `ae-cli analysis adhoc run -p <id> --zone-offset <project timezone; remove this parameter if timezone is disabled> --model-type sql --definition '{"sql":"SELECT min(\"$part_date\") FROM ta.v_event_<id>"}'`, without specifying a target event; the table-name form follows the sql_reference returned by sql-table list (default usage=analysis); adopt the result after confirming with the user — if it clearly mismatches the expected product launch time, ask the user to verify the data start and tell them the actually adopted value)
  - Daily first → **historical query start date** (not provided when the user needs no historical data; at execution time still backfill at least 1 day of historical versions per the Operation 3 rules)
  - User answers "both" → execute both the lifecycle and daily routes per the Step 3 matrix respectively (the asset naming convention already distinguishes the two), and merge into one plan in Step 3 for user confirmation
- **Target property** (used by A only): extract from the user's original words (e.g., "the pack of the first payment" → `payment_name`; "first payment time" → `#event_time`); default to `#event_time` (first time) when not mentioned
- **Start behavior** (used by C only): infer from the original words (e.g., "how long after registration until the first gacha pull" → registration; "how long after the first payment until level-up" → first payment); if inference fails, follow up first (when this coincides with the "Type C start-point caliber" follow-up, **merge them into one message**: first ask for the start point, then list the three caliber options):
  > "Which start point do you want to count from? (e.g., registration, first payment, or something else?)"
- **Type C start-point caliber** (decided after the first-round answer: initiate this follow-up only when the analysis type is C and the start point is an event that can occur repeatedly; do not ask if the user's original words already specify the caliber):
  > "[Start point] can occur multiple times. Which caliber do you want:
  > 1. Count only from the first [start point] onward — executed per your question-2 choice ([entire lifecycle / each day separately]), correct? (Whether a start-point asset is needed depends on the Step 2 property exploration result)
  > 2. Switch to a one-time start point (e.g., registration) and analyze directly
  > 3. Count every [start point] — this does not involve the "first" caliber; it is general interval analysis, solvable directly with the Interval Analysis model, no assets needed"
- Option 1 re-decision bridging: when the user switches to a time range different from question 2 (e.g., answered "each day separately" in question 2 but switches to "entire lifecycle"), ask for the required date under the new caliber's branch (lifecycle: ask for the data start date, fall back if unavailable; daily: ask for the historical query start date), then update the record
- Option 3 caliber note (told along with the option wording): the interval model pairs "each start event with the first target event after it"; consecutive repeated start events only count from the last one
- **Option 3 = workflow end point**: after stating the above caliber, end this workflow; do not enter Steps 2/3/4 (no further asset checks or plans needed)
- **Analysis subject**: default to the user subject (`#user_id`), no need to ask. When the user's original words mention a non-user caliber such as "per device / per account / per character", record the target subject and its corresponding event property (e.g., "first payment time per device" → subject column `#device_id`).

---

### Step 2 | Check existing assets

Determine the project from the session context; ask the user only when the context truly has no project information (without it there is no way to query).

**1. Look up the "target event"**: `ae-cli analysis-meta event list -p <id>`, searching multiple rounds with keywords, synonyms, and cross-language/naming variants; for Scenario C also look up the "start event" the same way (when the start point is a "(daily) first XX", what gets looked up is the XX event itself).

**2. Look up the "analysis subject"** (execute only when Step 1 identified a custom subject): `ae-cli project entity list -p <id>`, matching the target subject by `column_name` to see whether it is already configured. Not configured → add a "create the analysis subject first" step to the Step 3 plan (`ae-cli project entity create -p <id> --entity-name <name> --column-name <event property column> --table-type 0`, where 0 = event property).

**3. Check whether the "target event" has an "is first" type property** (`is_first`, `first_time`, "whether first", "first"; look only at the target event's own properties): `ae-cli analysis-meta property list -p <id> --event-name <event>`. Target-side exploration **is executed only when the analysis type includes B** — B uses it to decide whether the entire asset chain can be skipped, so the exploration has decision value; the pure-A tag chain does not consume this property, so usability does not affect the plan or deliverables — **inventory only**, and on a hit tell the user in one sentence: "event properties cannot carry targeting/grouping; the tag chain does not use it." When multiple candidate properties hit, explore them one by one, present the results in one table, and let the user decide
- **Not found** → the Step 3 plan follows the full workflow
- **Found** → complete the **preliminary exploration** in sync (method below under "Exploration method"). Note: the exploration result is only a preliminary judgment; **whether to adopt the property must be listed for the user to decide themselves** — the user's choice affects the Step 3 plan (not adopted → follow the full workflow; adopted → see "Post-confirmation routing")
- **Scenario C**: the target-event side is inventoried but not explored, and no user decision is requested (interval analysis does not depend on the target-side "is first" property); if the start point is a "(daily) first XX", instead check whether the "start event XX itself" has an "is first" type property; if yes, explore it per the exploration method above (granularity following the user's time range) and let the user decide (judged usable → short-circuit via "Post-confirmation routing", skipping the start-point asset and filtering directly; not found / unusable → build assets via the full workflow)

**4. For Scenario A, also check whether the "target property" is an event property of the target event** (e.g., "the level when first watching an ad" — `level` must be reported on the event for a first-occurrence snapshot; a property that exists only in the user property table is the current value, and historical moments cannot be traced back). Determination method: search the target property in the `property list --event-name` return of item 3 — present in the return means it is usable as an event property; absent from it and existing only in the user property table means stating the limitation honestly and negotiating an alternative (see "Special cases").

**Exploration method** (execute when an "is first" type property exists and the rules above lead to exploration — covering B's target side and C's start side; pure A does not explore): use the Events Analysis model, building 2 metrics — total count and triggering user count of the target event — grouped by the property, choosing exploration granularity per the user's time range (lifecycle request → total granularity, 90-day window, judging "at most one first per user in total"; daily request → by-day granularity, 90-day window, judging "at most one first per user per day" — multiple records for the same user across days are expected). The property's value form is not restricted to boolean (true/1/yes/numeric/text all acceptable; which value represents "first" follows the property's actual distribution; properties whose values are timestamps/content payloads are not "is first" markers — they do not enter exploration or routing and are treated as no usable marker):

Lifecycle request (total granularity):

```bash
ae-cli analysis adhoc run -p <id> --zone-offset <project timezone; remove this parameter if timezone is disabled> --model-type event --preview-rows 100 \
  --definition '{"time_range":{"mode":"previous","unit":"day","value":90},"time_particle_size":"total","metrics":[{"event":"<event display name>","aggregation":"total_count"},{"event":"<event display name>","aggregation":"user_count"}],"groups":[{"field":{"name":"<property display name>","type":"event_property"}}]}'
```

Daily request (change `time_particle_size` to `"day"`, outputting cell by cell as "date × property value"):

```bash
ae-cli analysis adhoc run -p <id> --zone-offset <project timezone; remove this parameter if timezone is disabled> --model-type event --preview-rows 1000 \
  --definition '{"time_range":{"mode":"previous","unit":"day","value":90},"time_particle_size":"day","metrics":[{"event":"<event display name>","aggregation":"total_count"},{"event":"<event display name>","aggregation":"user_count"}],"groups":[{"field":{"name":"<property display name>","type":"event_property"}}]}'
```

(Custom analysis subject scenario: append `"analysis_entity": {"id": <entity_id>}` to the definition of the two exploration commands above — obtain entity_id via `ae-cli project entity list -p <id>` matched by `column_name`; after appending, both the exploration and the judgments below are interpreted at the selected subject's granularity — read "per user / the same user" as "per subject / the same subject")
- When event/property names conflict with metrics or virtual event properties of the same name, disambiguate using **display names**
- **Judgment 1 (NULL check)**: the grouped result contains only rows for values representing yes/no → no NULLs, this item passes; a third group appears (NULL/empty-value row) → compute its share, tell the user the NULL rate honestly, and let the user verify the property's usability themselves
- **Truncation guard**: when the exploration response has `has_more`=true, grouped rows are truncated by the sync limit — the NULL row / true row may fall outside the truncation — neither Judgment 1's NULL check nor Judgment 2's event-count/user-count comparison may draw conclusions; add filter conditions (definition `filters`, field/operator written the same as Operation 5's filter structure) or shorten the window and rerun until `has_more`=false before judging
- **Judgment 2 (first-marker criteria, by time range)**: rows whose values represent "first" (true/1/yes, etc.) —
  - Lifecycle request (total granularity): **event count > triggering user count → unusable** (multiple "first" records for the same user); equal → usable
  - Daily request (by-day granularity + total granularity, two steps): ① within the same date, event count > triggering user count → unusable; ② after per-day equality, rerun at total granularity (90-day total, same command as the lifecycle version) — **total event count = total user count → no user has multiple firsts across days within the window, most likely not a daily marker (a true daily marker under low-frequency events can also look like this), preliminary judgment: unusable**; total event count > total user count → caliber undetermined (may be daily / dimension-level / another period). Present both outcomes to the user to confirm with the tracking team before deciding whether to adopt; if not adopted, build assets via the full workflow
- Groups only count users who triggered that value (users with 0 records do not enter the denominator), so event count and user count can be compared directly
- This is **your preliminary judgment**; the result must be told to the user, who judges usability. Reference phrasing:
  > "I found a property '[property name]' and ran a preliminary exploration on the past 90 days of data. Result: [exploration result] (i.e., whether the same user may have multiple 'first' records [in total / per day]; NULL rate [xx / none]). Preliminary judgment: [the property's data behavior does / does not match first-marker characteristics]. Please confirm the business semantics with the tracking team before deciding whether to adopt it."
  (For daily requests, close per the judgment-result branch: total equal → "no user has multiple firsts across days within the window — most likely not a daily marker; please confirm with the tracking team whether to adopt it; if not adopted, I will rebuild the assets as daily first"; total greater → "the property's caliber is undetermined (may be daily / dimension-level / another period); please confirm the exact marker caliber with the tracking team". Adoption is ultimately the user's decision in both cases.)
- No row at all for values representing "first" within the 90-day window → tell the user honestly that the exploration came back empty; preliminary judgment: unusable

**Post-check report and confirmation**: project + candidate events + existing "is first" type properties with exploration conclusions (Scenario C's target side is inventoried only, not explored — presenting the inventory result suffices) + target-property status (A only) + analysis-subject status (custom-subject scenarios only), presented in one table, confirmed in one step:

> "These are the relevant assets I found. Confirm using these?"

(The report presents only the inventory status and the exploration's objective conclusions; do not foreshadow routing conclusions like "a new tag is needed" — whether assets get built is decided by the scenario: A always builds tags; B and C's start point depend on the property judgment — that is Step 3 plan content, presented only after the inventory is confirmed.)
**Stop after asking; do not introduce the plan in the same message.**

**Post-confirmation routing** (taken only when the user judges the property usable):
- **B**: tell the user to filter directly with the ready-made property (no assets needed), and end:
  > "The '[target event]' event already has the '[property name]' property. Just filter on it during analysis — no extra assets need to be created."
- **A**: a user-level tag is still needed (event properties can only filter event records; they cannot deliver targeting/grouping); follow the Step 3 full workflow
- **C**: the target-event side does not depend on this property (the interval model automatically pairs the first target event after the start point; no assets needed); when the start point is a "(daily) first XX" and the XX event itself has a semantically matching property judged usable by the user, assets are likewise skipped — do not build the start virtual event; compute directly with XX itself as the start point and filter on the property in the start-event filter (syntax in Operation 6); the analysis window and maximum interval are still confirmed in Step 3 before execution

**Special cases**:
- **Target event or start event not found**: tell the user honestly and ask for the actual event name or a tracking re-check; if the user is also unsure → tell them to verify on their own; the workflow cannot proceed
- **Scenario A target property unavailable** (not found, or exists only in the user property table): state the limitation honestly and offer alternatives (substitute the first time / pick another target property / change the analysis approach); **execute per the confirmed choice only after the user confirms** — never substitute the time on your own without confirmation
- When uncertain during the property inventory, cross-check Cases 3/4 in the "Typical Ambiguity Case Library"

---

### Step 3 | Determine the plan

First check the Step 2 "Post-confirmation routing" decision (when the ready-made property is usable and its semantics match the time range): B already ended in Step 2; C's start point skips assets and computes directly with the start-event filter (syntax in Operation 6); A still needs tags built. Property unusable / unconfirmed / semantic mismatch → follow the full matrix below:

Match the operation combination by **analysis type × time range** (operation numbers → mandatory reading of the corresponding section in `references/operations.md`):

| Analysis type | Time range | Operation combination |
|---|---|---|
| A | Lifecycle | One tag per value the user wants (first time or property at first occurrence), all via Operation 1 (time and property share the same template; only `{{PROP}}` differs) |
| B | Lifecycle | Operation 1 (`{{PROP}}` = `#event_time`) → Operation 2 → Operation 5 (final deliverable: the virtual event) |
| A | Daily | One tag per value the user wants, all via Operation 3 (including historical-version backfill) |
| B | Daily | Operation 3 (value = `#event_time`, including historical-version backfill) → Operation 4 → Operation 5 |
| C | Lifecycle | Computed with the Interval Analysis model (Operation 6); when the start point is a "first XX", first check for a ready-made property (usable → compute directly with the start-event filter, no assets needed); only if the tracking does not support it, first build the start virtual event (Operation 1 → 2 → 5) and then compute |
| C | Daily | Computed with the Interval Analysis model (Operation 6); when the start point is a "daily first XX", first check for a ready-made property (usable → compute directly with the start-event filter, no assets needed); only if the tracking does not support it, first build the start virtual event (Operation 3 → 4 → 5) and then compute |

**A+B mixed requirement** (wants both tag-based targeting and first events for analysis) → build both chains: execute the operation combinations of the A row and the B row stacked. **Reuse of same-name assets within the same plan** (this rule applies to any chain combination, including the C chain building start-point assets): when A's target values include "first time", the B chain directly reuses the time tag already built by the A chain, and the C chain's start point likewise — no duplicate creation; the suffix-on-conflict rule applies only to **pre-existing assets outside the plan**; reuse within the plan is not a conflict. When the property is usable, the B side has already ended while the A side continues building tags.

**Lifecycle first** plan explanation points (by analysis type; shared A/B mechanics first):
- Mechanics explanation (plain language): create the [tag name] tag via incremental computation — first compute history fully once ([start date] through yesterday), then compute only the most recent 3 days each day and merge with historical values. The "Analysis period: last 3 days" shown in the tag UI is just the incremental window, not "only 3 days are computed"; historical first values are not recomputed and not lost
- Caliber note: the tag counts from the data start date — if the start date is later than the real data origin, older users who completed the first behavior earlier will have their "first" recorded as the first recurrence after the start date (or missed); explain this point to the user when the plan is confirmed, and have them verify the start date if necessary
- A: create N SQL tags, each recording the [value] of each player's first occurrence of the event, with incremental computation and daily automatic updates
- B: first build the SQL time tag, then build the virtual event property that marks first events, and finally deliver a "First [target event]" virtual event — subsequent analyses just select this event directly, with no need to add filters yourself

**Daily first** plan explanation points: create the daily first_last tag (fill parameters per the target value), and immediately backfill historical versions after creation (backfill to the given start date if the user provides one; by default backfill at least 1 day — once the first historical version is ready, "dynamic matching" can be configured; for long backfill ranges there is no need to wait for everything to finish, see Operation 3 for details); Scenario B additionally needs the dynamically matched virtual event property + virtual event. Scenario A note: the daily version's tag value changes day by day; it is not a stable user characteristic — suitable for day-by-day operational scenarios like "today's daily-first users", not for long-term grouping.

**C interval analysis** plan explanation points: confirm the analysis window and maximum interval with the user in this step — two default tiers:
- One-time / lifecycle start point (e.g., "how long after registration until the first payment", time to first payment): analysis window past 30 days, maximum interval 7 days (can be enlarged for long-cycle ice-breaking cases)
- Daily-first start point (e.g., "how long after the daily first login until payment"): analysis window past 7 days, maximum interval 1 day
- Caliber note: the interval model's pairing rule pairs each start event with the first target event that occurs after it; consecutive repeated start events only count from the last one (details in Operation 6); users whose first behavior falls outside the analysis window are excluded

**Custom analysis subject** scenario: note the subject to be used in the plan; when a new subject is needed, list its creation steps as well.

After explaining the plan, ask the user to confirm; execution starts upon confirmation.

---

### Step 4 | Execute operations

**Mandatory reading of the operations manual before execution**: before executing any of Operations 1–6, you MUST first Read the corresponding section of `references/operations.md` in full (including "Verification (must do)" and notes), **executing strictly per the template's original commands/SQL and parameters — no rewriting, no reciting from memory**; if the sub-file is missing or the read fails, stop execution and tell the user.

**Quota-limit contingency**: when creating a tag/virtual event property/virtual event reports "object quantity limit reached" (`EXCESS_QUANTITY`) — tell the user honestly that the project's objects are full, and offer two paths: ① after user confirmation, clean up existing assets to free quota (`user-tag list` to list obviously abandoned candidates for the user, **deleting only after per-item user confirmation** (deletion command behavior: see Step 5 "Mid-run cancellation")); ② ask an administrator to raise the quota before continuing. **Do NOT delete any existing asset on your own**; while waiting for quota, deliver the already-completed creations and verification results as usual — do not shelve them due to waiting.

**Type A / B**: execute the operation combination from the Step 3 matrix in order, and **report results and artifact links to the user only after all operations complete**. (Exceptions: after Operation 3's historical-version backfill is submitted — **B×daily and others that proceed to Operation 4**: actively poll `analysis history-tag list` and continue to Operation 4 once the **first historical version is ready** (a historical date version with history_tag_status=normal exists; the numeric task_status in the return is not a readiness criterion); **A×daily (no subsequent Operation 4/5)**: do not poll — go straight to the unified report and note that the backfill proceeds in the background. Polling intervals, timeout limits, and pause/resume rules all follow operations.md Operation 3's "wait rules after backfill submission")

**Type C (interval analysis)**: execute per Operation 6 in `references/operations.md`, filling the analysis window and maximum interval per the calibers confirmed in Step 3 (two default tiers in Operation 6). How to compute depends on the start point:
- Start point is a one-time event (e.g., registration, character creation) → compute directly, no assets needed
- Start point is an ordinary repeated event with the "count every occurrence" caliber → not a first-occurrence request; handle per out-of-scope scenarios: tell the user to use the Interval Analysis model directly (caliber note: see Step 1 option 3), build no assets, do not enter this workflow
- Start point is a "(daily) first XX" → first check the ready-made property: the event itself has an "is first" property judged usable by the user → skip assets, use XX itself directly as the start point and filter on it in the start-event filter (see Operation 6); tracking does not support it → first build the start virtual event via the A/B asset chain (lifecycle → Operations 1 → 2 → 5; daily → Operations 3 → 4 → 5), then compute with it as the start point

---

### Step 5 | Guide usage + explain limitations

**A (property tag):**
> "The tag '[tag name]' has been created; it records the [property] of each player's first occurrence of '[target event]'. You can use this tag to filter or group players in analyses, and it also works for cluster targeting and operational reach."

(For A×daily delivery, append one sentence: "Note that the daily version's tag value changes day by day — suitable for day-by-day operational scenarios like today's daily-first users, not for long-term fixed grouping.")

**B (virtual event):**
- Lifecycle version:
  > "The virtual event 'First [target event]' has been created. In subsequent analyses, just select this event directly — it contains only each player's first occurrence record, so user trends and property distributions can be viewed directly, with no need to add filter conditions."
- Daily version:
  > "The virtual event 'Daily First [target event]' has been created. In subsequent analyses, just select this event directly — it contains only each player's first record of each day, so day-by-day user trends and property distributions can be viewed directly, with no need to add filter conditions."

**C (interval analysis):**
> "The interval analysis results are out ([result summary: median/percentiles/distribution]). Two caliber reminders: ① intervals are paired as 'each start event with the first target event after it' — for the same user with consecutive repeated start events, only the last one counts; ② users whose first behavior falls outside the analysis window are excluded from the statistics." Attach the UI recomputation path (see the last item of Operation 6) for the user's self-service reuse; if a start virtual event was built for C, deliver the asset link along with the limitations note, as with A/B.

**A / B must both explain the limitation** (also attach when C has tags built):
> "One thing to note: the tag updates automatically once per day, not in real time. If you need to analyze data that just landed today, the tag may not have updated yet. If real-time judgment is needed later, the recommendation is to report an 'is first' property directly in the tracking."

**Mandatory reminder for daily-route delivery** (when Operation 3's probe finds the CLI does not support the backup switch):
> "**Please go to the tag settings page and manually enable 'Auto Backup'** (the current CLI does not yet support this switch): [tag link]. Without it, automatic updates from tomorrow on will not retain new versions, and dynamic matching will find no data for new dates; if you forget to enable it, you can turn it on at any time — the missing dates can be re-backfilled and existing data is unaffected."

(When the probe shows support and it has been enabled on the user's behalf per Operation 3, replace this reminder with telling the user "Auto Backup has been enabled" — no user action needed.)

**Explain the backfill purpose for A / daily-route delivery**: historical-version backfill is for viewing the tag's value as of a historical date (e.g., reports viewing daily-first users by date), and it is also the version foundation for adding dynamic matching later; if Scenario A only needs the current value for targeting, the minimum 1-day backfill is just a version reservation — no longer range is needed.

**Asset link delivery**: after creation, a complete, clickable URL MUST be returned. Steps:
1. **resource-id lookup** (the create command returns no business data; look up per asset type): tag → `ae-cli analysis user-tag list -p <id>` matched by tag_name to get `id`; virtual event → `ae-cli analysis-meta event list -p <id>` matched by event name to get `event_id`; virtual event property → `ae-cli analysis-meta property list -p <id> --event-name <event>` to get `prop_id`
2. `ae-cli analysis-meta asset url-get --project-id <id> --resource-id <asset ID> --resource-type <type>` (the tag resource type is `tag`, virtual event is `virtual_event`; virtual event properties have no linkable resource type, but a detail-page route can be hand-assembled and delivered too: `/#/data/sourceEvent/propDetail?currentProjectId=<id>&name=<URL-encoded property name>&tableType=0&type=virtual`, with `#` in the property name encoded as `%23` and `@` as `%40`)
3. If the `raw_url` returned by the tool is an intranet host (an internal service address the tool connects to directly, not a user-accessible form), replace it with the user-accessible platform domain (the value confirmed per the "Platform access domain" global rule)
4. Deliver as a Markdown link. For Scenario B, deliver the final virtual event's link (intermediate tags can be given as well if the user wants them)
5. When the link tool fails or there is no matching resource type, do not fabricate paths: tell the user the asset name and ID and ask them to view it in the platform's corresponding module list page (tag management / virtual events); deliver the virtual event property via the hand-assembled route in step 2

**Mid-run cancellation**: when the user asks to stop mid-workflow, inventory the created assets (tags/virtual event properties/virtual events), list them for the user, and ask whether to keep or delete them. Multi-asset deletion runs in reverse dependency order (virtual event → virtual event property → tag, to avoid deleting a referenced asset first and leaving downstream dangling). For every asset selected for deletion, first run the corresponding unchanged command with `--dry-run`, summarize the returned target, dependencies, and impact, then wait for a new explicit confirmation covering that impact. Only after that confirmation execute the same target with the required confirmation flags:
- Tag: dry-run `ae-cli analysis user-tag delete -p <id> --tag-name <tag name> --dry-run`; after impact confirmation execute `ae-cli analysis user-tag delete -p <id> --tag-name <tag name> --confirmed --yes`
- Virtual event: dry-run `ae-cli analysis-meta virtual-event delete -p <id> --v-event-id <event_id> --dry-run`; after impact confirmation execute `ae-cli analysis-meta virtual-event delete -p <id> --v-event-id <event_id> --yes`
- Virtual event property: for permanent deletion, dry-run `ae-cli analysis-meta virtual-property sql-rule-delete -p <id> --v-prop-id <prop_id> --dry-run`; after impact confirmation execute `ae-cli analysis-meta virtual-property sql-rule-delete -p <id> --v-prop-id <prop_id> --yes`. Use `--operation revoke` in both commands only when the user explicitly requests revocation instead of permanent deletion
Already-created assets do not affect subsequent reruns; no silent cleanup is needed. **Mid-execution caliber change** (e.g., after plan confirmation switching to daily or changing the target property): handle as a mid-run cancellation — inventory built assets, confirm the reusable part (keep those whose naming and caliber match), rerun the rest through Step 3 for a revised plan, and execute after user confirmation.

---

## Typical Ambiguity Case Library (intent confirmation reference)

**Case 1: half-stated requirement**
> Customer: "I want to see users' level and ad scene when they first watched an ad."
>
> Superficially like A (a property snapshot of the user), but the customer may follow up with "show the distribution" or "show last week's" (i.e., B). **You MUST ask about the use**; do not directly build 2 property tags.

**Case 2: the first occurrence vs. all behavior of that cohort**
> Customer: "I want to know which packs the users who first paid in August bought."
>
> Ambiguity: ① the pack bought on the first payment (Scenario B — deliver the "First Payment" virtual event and view the pack distribution); ② all payments of that cohort (Scenario A — tag targeting + no event filter). Follow up to clarify.

**Case 3: target property is not an event property**
> Customer: "I want to see the level when first watching an ad."
>
> If `level` exists only in the user property table (current value), the historical level cannot be traced back. Discover and state this during the Step 2 inventory, and negotiate an alternative.

**Case 4: the ready-made "is first" property is dimension-level**
> Customer: "I want to see the level of the first battle victory."
>
> The event already has `is_first_try` (whether the first attempt), but it is "the first attempt of that stage" — the same user can have multiple true rows. Make a preliminary judgment per the Step 2 exploration method and let the user confirm; never tell the user to use the ready-made property just because its name contains "first".

(For uncertain Step 1 intent, cross-check Cases 1/2; for uncertain Step 2 property inventory, cross-check Cases 3/4.)

---

## Operation Index Table (mandatory reading of the corresponding section in `references/operations.md` before executing any operation)

| Operation | Content | Prerequisites |
|---|---|---|
| Operation 1 | Create lifecycle first-value tags (`{{PROP}}` = a business property or `#event_time`; full initialization → switch to incremental → auto update → verification; supports custom analysis subjects) | Step 1: the user provides the data start date; the custom subject is configured |
| Operation 2 | Create the virtual event property (lifecycle version `#vp@is_first_<event>`) | Operation 1 complete and verified |
| Operation 3 | Create the daily first_last tag + historical-version backfill (fill parameters per the target value) | Step 1: the user-provided historical query start date (when there is no historical need, backfill at least 1 day) |
| Operation 4 | Create the dynamically matched virtual event property (daily version `#vp@daily_is_first_<event>`) | Operation 3's first historical version backfilled and ready |
| Operation 5 | Create the virtual event (`ta@first_<event>` / `ta@daily_first_<event>`) | Lifecycle version: Operation 2; daily version: Operation 4 |
| Operation 6 | Interval analysis computation (Scenario C's execution method; start-point determination and commands) | Start/target events confirmed; start point is a "(daily) first XX": the ready-made property judged usable (compute directly with the start-event filter, no assets needed) or the corresponding start-point asset already built (caliber confirmation: see Step 1/Step 3) |

Operations manual: `references/operations.md` (SQL/command templates, verification methods, notes)

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
