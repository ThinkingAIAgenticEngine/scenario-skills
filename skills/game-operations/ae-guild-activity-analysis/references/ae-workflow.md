# Read-only AE execution

Use this when analysis data is in AE. AE execution needs a shell-enabled host with the `ae-analysis` Skill, `ae-cli`, and authenticated read access to the confirmed project. For local files, use a host that can read and calculate from the supplied records and perform equivalent mapping, coverage and arithmetic checks. Use the confirmed project, host, events and identity for each analysis.

## Prerequisites and version handling

Before AE access, check that ae-analysis is available in the current Skill catalog and ae-cli is available through the runtime's command lookup. Reuse an already verified check in the same environment. If available, use ae-analysis as the execution entry point and follow its current project/context, metadata resolution, semantic routing and result-handling instructions. Read the operation reference before invocation. Preserve the confirmed host, project, date basis and data route. The compatibility target is releases 6.0 and 6.1; capability support must be checked on the actual deployment, and this target is not proof of dual-version testing.

If either dependency is missing, name it and direct setup through the environment's supported configuration or installation workflow; do not invent installation commands. When trustworthy supplied files meet the requested deliverable, continue locally and label that source. A local-file analysis does not verify AE connectivity or replace an explicitly requested platform operation. Otherwise return the missing dependency and the minimum data needed for the selected lens. Distinguish local dependency absence from authentication, permission or service failures. File-only analysis does not require AE dependencies.

The command patterns below were checked against available operation references. Values named GUILD_* must come from the confirmed request, metadata responses or a completed definition. They are not product defaults. Prefer structured argument arrays and JSON serialization when constructing calls; never interpolate untrusted input as shell code.

## 1. Verify the confirmed scope and map fields

Start here after the [initial measurement confirmation](../SKILL.md#confirm-the-measurement-before-querying). Reuse a verified project or resolve it through the current project-list contract. Read project identity when needed for the confirmed scope.

```bash
ae-cli --host "$GUILD_HOST" project info get --project-id "$GUILD_PROJECT_ID"
```

Inspect relevant existing reports and their saved definitions first when available. Discover only the missing events and properties.

```bash
ae-cli --host "$GUILD_HOST" analysis-meta event list --project-id "$GUILD_PROJECT_ID" --queries "$GUILD_EVENT_SEARCH_JSON" --limit 50 --offset 0
ae-cli --host "$GUILD_HOST" analysis-meta property list --project-id "$GUILD_PROJECT_ID" --scope event --event-name "$GUILD_EVENT_NAME" --limit 50 --offset 0
```

Event results use data.items; property results use data.properties. Read machine names, types and descriptions. If has_more is true and more discovery is needed, follow the returned next_offset; use the documented export capability for complete catalogs. Metadata is not proof that the event was collected during the analysis window. Inspect needed subtype values and bounded samples through supported analysis operations.

Map real fields to member, guild, event time, behavior, activity instance, affiliation, eligibility, opportunity and contribution. Confirm unresolved meanings through the analysis Skill's resolution workflow; reuse already confirmed mappings. Do not infer contribution units or eligibility from labels alone.

If the confirmed metric uses the daily historical roster, find the project's daily user-table snapshot through the authorized table and column discovery below. Use the recorded guild directly on each snapshot date and follow the [daily snapshot roster rules](data-contract.md#default-historical-roster-source). If any required snapshot data is unavailable, explain the gap to the user.

## 2. Obtain compatible analysis results

Use saved reports when definitions support the requested metrics and periods. Use an ad-hoc model for custom metrics and SQL for temporal membership or fixed-cohort joins when needed. Before SQL, inspect the authorized table and columns:

```bash
ae-cli --host "$GUILD_HOST" analysis sql-table list --project-id "$GUILD_PROJECT_ID"
ae-cli --host "$GUILD_HOST" analysis sql-table columns --project-id "$GUILD_PROJECT_ID" --table-ref "$GUILD_TABLE_REF" --usage analysis
```

Copy returned sql_reference and discovered column names, preserving types and identifier quoting. If the event table exposes a date partition, include its required partition predicate plus the exact business-time window. Apply timezone conversion only according to actual storage semantics; compare a bounded result with a compatible native report where available.

Build a definition using the current selected-model contract. For SQL, serialize an object with a `sql` field containing the completed query. For project-wide reach, use project login and verified gameplay with a shared player key. For a single weekly measure, query only its required populations and events. For a full review, select the following components as confirmed and reuse available results.

1. Historical member and opportunity base for each relevant period.
2. Distinct participation sets per guild and behavior, with any overall totals at the confirmed roll-up grain.
3. Fixed prior/current cohort intersections and differences; join activity and affiliation evidence without multiplying members.
4. Reconciled per-member contribution totals, ranked shares and fixed prior-core follow-up when requested.

```bash
ae-cli --host "$GUILD_HOST" analysis adhoc run --project-id "$GUILD_PROJECT_ID" --model-type sql --definition "$GUILD_DEFINITION_JSON" --zone-offset "$GUILD_ZONE_OFFSET" --preview-rows 100
```

Include the requested periods, filters, namespace and grouping in the definition, not only in the report text; add a comparison period only when the requested calculation needs it. An explicit zone offset does not excuse an incorrect SQL timestamp expression. Omit physical route overrides for current-self scope; discover permission and support before another route. SQL does not support a global route.

Read data.title with rows, returned_rows, has_more, normalized definition, effective timezone and actual route when returned. Preserve enough request/invocation evidence to reproduce material results. A report overview may sum daily unique values; verify period_values rather than treating it as a whole-period distinct count.

### Worked example of project-wide reach

This synthetic example illustrates the [project-wide reach calculation](metrics.md#project-wide-gameplay-reach). Use verified values from the deployment for a real query.

| Parameter | Verified example source |
|---|---|
| Host and project | `GUILD_HOST` is the confirmed authenticated host. The example user confirmed project 42. |
| Period and day basis | The user confirmed October 5–11, 2026, inclusive, using UTC+8 calendar days. The example's stored event times and partition labels use that basis. |
| Table and fields | SQL discovery returned `"hive"."ta"."v_event_42"` with `#user_id`, `#event_time`, `$part_event` and `$part_date`. |
| Events | Definitions and in-window rows verify `login` and `guild_war_enter`, the latter recording actual combat entry. The user selected guild war. |

After the prerequisite checks, serialize the example SQL with `jq` or an equivalent JSON serializer and run the one-row query.

```bash
GUILD_DEFINITION_JSON=$(jq -Rs '{sql: .}' <<'SQL'
WITH players AS (
    SELECT "#user_id" AS player,
           max(CASE WHEN "$part_event" = 'login' THEN 1 ELSE 0 END) AS logged_in,
           max(CASE WHEN "$part_event" = 'guild_war_enter' THEN 1 ELSE 0 END) AS played
    FROM "hive"."ta"."v_event_42"
    WHERE "$part_date" BETWEEN '2026-10-05' AND '2026-10-11'
      AND "#event_time" >= TIMESTAMP '2026-10-05 00:00:00'
      AND "#event_time" < TIMESTAMP '2026-10-12 00:00:00'
      AND "$part_event" IN ('login', 'guild_war_enter')
      AND "#user_id" IS NOT NULL
    GROUP BY "#user_id"
)
SELECT count(CASE WHEN logged_in = 1 THEN 1 END) AS login_players,
       count(CASE WHEN logged_in = 1 AND played = 1 THEN 1 END) AS matched_players
FROM players
SQL
)

ae-cli --host "$GUILD_HOST" analysis adhoc run --project-id 42 --model-type sql \
  --definition "$GUILD_DEFINITION_JSON" --zone-offset 8 --preview-rows 1
```

For a successful complete response with `data.title` of `["login_players", "matched_players"]`, `data.rows` of `[["100", "20"]]` and `data.has_more` false, report 20/100 (20%) and name guild war as the gameplay included. A verified zero login count gives `N/A`. Incomplete login evidence leaves the denominator unavailable. Check the response status and scope and retain the invocation reference for reproducibility.

### Worked example of member activity only

The user requests “最近 7 天只看 7 号公会的在会活跃率，活跃按登录算” for synthetic project 42. At 09:00 on October 12, propose October 5–11, 2026, inclusive, using UTC+8 calendar days. After the user confirms, apply those dates to the snapshot and login sources below. The [local fixture](verification-cases.md#member-activity-only) defines the expected records and results.

| Input | Verified example source |
|---|---|
| Project and guild | Confirmed project 42, guild 7, and `GUILD_HOST` from the authenticated environment. |
| Membership | Authorized snapshot table `"hive"."ta"."user_day_serial_42"`, with `$pt` as the game date, `#user_id` as member key and `guild_id` as guild key. Snapshot coverage, required keys and member-day consistency are checked before interpreting the rate. |
| Login | Authorized event table `"hive"."ta"."v_event_42"`. Event metadata and sample records verify `login` and the shared `#user_id`. The partition date and `#event_time` use the project's game-day basis in this example. |

Check all snapshot rows for each member-day before filtering to guild 7. Identical assignments collapse to one. A member-day with multiple guilds or a mix of a known guild and a missing guild value is unresolved in this example.

```bash
GUILD_DEFINITION_JSON=$(jq -Rs '{sql: .}' <<'SQL'
WITH snapshots AS (
    SELECT "$pt" AS game_day, "#user_id" AS member_id, guild_id
    FROM "hive"."ta"."user_day_serial_42"
    WHERE "$pt" BETWEEN '2026-10-05' AND '2026-10-11'
), member_day_affiliation AS (
    SELECT game_day, member_id,
           min(guild_id) AS guild_id,
           count(DISTINCT guild_id) = 1 AND count(guild_id) = count(*) AS has_known_guild,
           count(CASE WHEN guild_id = 7 THEN 1 END) > 0 AS has_target_guild
    FROM snapshots
    WHERE member_id IS NOT NULL
    GROUP BY game_day, member_id
), roster AS (
    SELECT game_day, member_id
    FROM member_day_affiliation
    WHERE has_known_guild AND guild_id = 7
), login_days AS (
    SELECT DISTINCT CAST(date("#event_time") AS varchar) AS game_day,
           "#user_id" AS member_id
    FROM "hive"."ta"."v_event_42"
    WHERE "$part_date" BETWEEN '2026-10-05' AND '2026-10-11'
      AND "#event_time" >= TIMESTAMP '2026-10-05 00:00:00'
      AND "#event_time" < TIMESTAMP '2026-10-12 00:00:00'
      AND "$part_event" = 'login'
      AND "#user_id" IS NOT NULL
), member_counts AS (
    SELECT count(DISTINCT roster.member_id) AS roster_members,
           count(DISTINCT login_days.member_id) AS active_members
    FROM roster
    LEFT JOIN login_days ON roster.member_id = login_days.member_id
        AND roster.game_day = login_days.game_day
), snapshot_coverage AS (
    SELECT count(DISTINCT game_day) AS snapshot_days FROM snapshots
), affiliation_quality AS (
    SELECT count(*) AS unresolved_member_days
    FROM member_day_affiliation
    WHERE has_target_guild AND NOT has_known_guild
)
SELECT roster_members, active_members, snapshot_days, unresolved_member_days
FROM member_counts CROSS JOIN snapshot_coverage CROSS JOIN affiliation_quality
SQL
)

ae-cli --host "$GUILD_HOST" analysis adhoc run --project-id 42 --model-type sql \
  --definition "$GUILD_DEFINITION_JSON" --zone-offset 8 --preview-rows 1
```

Read the returned `data.title` and `data.rows` after checking success and completeness. In this fixture `data.title` is `["roster_members", "active_members", "snapshot_days", "unresolved_member_days"]` and `data.rows` is `[["3", "2", "7", "0"]]`. With verified source coverage, report **guild 7 member activity of 2/3 (66.67%) on October 5–11**, with login as the qualifying behavior. With a complete roster and zero qualifying logins, report 0%. A verified empty guild roster gives `N/A`. Seven snapshot days alone do not establish a complete roster. If the query finds unresolved member-days involving guild 7, report the gap and withhold the full rate until the affiliation is resolved. Also withhold the rate if required snapshot dates, keys or login coverage are missing.

## 3. Full lists and failure handling

For a full or unknown-size member list, choose export directly instead of paging previews:

```bash
ae-cli --host "$GUILD_HOST" analysis adhoc export --project-id "$GUILD_PROJECT_ID" --model-type sql --definition "$GUILD_DEFINITION_JSON" --zone-offset "$GUILD_ZONE_OFFSET" --artifact-format csv --output "$GUILD_OUTPUT_FILE"
```

Read the current export reference first. Retain the returned run/artifact pair; require SUCCEEDED and COMPLETED before reading the downloaded artifact. Respect returned compression and format, preserve large IDs as strings, and validate row count and uniqueness. Resume an existing run through its documented wait operation after a local interruption; do not submit the same export again just to poll.

| Condition | Response |
|---|---|
| Compiler error at a field or argument | Resolve the specific reported path against the current contract; preserve other scope choices |
| Ambiguous business mapping | Resolve with definitions or obtain the missing business clarification; do not guess |
| Permission, authentication or unavailable capability | Report the unavailable component; do not switch host or identity to bypass it |
| Query failure or unknown completeness | Keep values unknown; do not manufacture zero or use a partial list as all members |
| Missing history, eligibility or contribution | Apply the corresponding analytical limitation and continue independent supported lenses |
| Failed output self-check | Repair affected definitions/calculations once evidence supports the repair; withdraw unresolved conclusions |

The installed analysis Skill's explicit retry and failure rules remain authoritative. Reuse successful results, avoid speculative retries, and state which deployment/version checks actually ran. Runtime completion, business correctness and operational usefulness are separate claims.
