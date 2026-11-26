# Data preparation and field alignment

Use this reference before assigning business meaning to records. The concepts below are logical roles, not assumed event or column names.

## Scope card

Record the project, environment, identity unit, confirmed measures and gameplay, dates, day basis and source coverage. Add the guild namespace, affiliation, activity rounds and opportunity rules when the selected measures need them. Resolve permissions through the existing analysis workflow, not by changing identity or environment.

### Relative date boundaries

Use the requested day basis for a rolling complete-day window. By default, propose calendar days in the task time zone. Count back through N date labels from the last completed day and present the first and last labels as inclusive dates. For a complete timestamp window, use the start of the first day and an exclusive end at the start of the following day after the last included date.

Use the confirmed dates and day basis directly. Align event dates and snapshot labels for the calculation. If the records cannot support the confirmed window or day basis, explain the mismatch and ask before substituting another scope. Honor explicit dates or an explicitly included current day. Label a partial day with its data cutoff.

## Mapping contract

For each needed concept record: business meaning, source event plus subtype filter, actual field, type and sampled value domain, timestamp, identity or business-instance key, supporting definition, coverage, and permitted conclusion.

Use project event metadata and current-period records to map behaviors within the confirmed gameplay scope. Clear, verified matches can be used directly. If the available records raise a question about what counts that the confirmed measurement has yet to resolve, explain the evidence and ask which behavior to measure before computing the affected result. For example, if records describe war registration and "participation" is still ambiguous, clarify whether the user wants registration coverage or actual combat participation. When the chosen behavior lacks supporting records, report that gap. List the actual mapped behaviors in the report.

Record collection coverage by gameplay and comparison period: complete, partial, unknown or not applicable, with the observed behavior types and basis. Keep collection coverage separate from whether the activity was open. No opportunity rows do not by themselves mean no eligible members or a closed activity.

Use a trustworthy tracking/business definition or an explicitly confirmed user definition to establish whether a contribution field is a delta, settlement or cumulative snapshot, its unit and business transaction key. A plausible name, one row per round or convenient numeric pattern is not enough. If unresolved, retain the observed values as unverified evidence and withhold effective-contribution totals/shares; continue supported participation analysis. Synthetic fixtures need the same semantic dictionary, supplied separately from expected answers.

| Concept | Minimum evidence | Checks | Supports |
|---|---|---|---|
| Project player identity | Shared stable player key across login and verified gameplay records | Confirm identity grain and aligned game dates. A guild key is needed for guild breakdowns. | Project-wide gameplay reach and project-wide repeat |
| Member identity and guild | Stable character or account identifier, guild key and namespace | Distinguish account, character and person; verify whether guild IDs are global or scoped to a server | All guild-level comparisons |
| Historical membership | Daily user-table snapshots with guild affiliation for the default day-level metric. Use valid-time membership for a confirmed exact-time metric. | Snapshot dates, member and guild keys, and population coverage. Check membership intervals for exact-time analysis. | Member denominator, active base, member follow-up |
| Game activity | Genuine login, online session or gameplay records | Business time, identity and coverage; exclude automatic awards and delayed bookkeeping | Activity during affiliation and current activity of previous participants |
| War participation | Actual entry into combat or a settlement listing actual participants | Round or battle instance, participant and locked guild; registration alone is insufficient | Observed war participation |
| Task participation | Voluntary claim/start, execution or trustworthy completion | Personal task instance and period; automatic assignment is not voluntary participation | Task participation, or completion coverage when only completion is observed |
| Donation or construction | Actual player resource-input operation | Member, guild, time, transaction key, amount and unit | Independent participation and resource input |
| Eligibility and opportunity | Historical unlock/level rules, open activity windows, entry rules, lineup or slot allocations where applicable | Rules independent of eventual participation; distinguish basic eligibility from receiving a slot | Qualified coverage and interpretation of nonparticipation |
| Effective contribution | Authoritative deltas or reconciled settlements attributed to members | Incremental versus cumulative, duplicates, units, source action, reversals, resets and attribution | Contribution total, contributors and distribution |
| Goals, optional | Goal thresholds, progression, stage, deadline and rule version | Comparable stages and authoritative completion status | Operational context for contribution findings |

### Adaptation examples

A single reported event may carry war, donation and boss subtypes. Map the event plus validated subtype values to separate behaviors; do not require one physical event per business behavior. A separate contribution-change event may be an automatic result of combat, not another active behavior.

An identifier stored as a string in one source and a number in another needs lossless normalization. Do not round large member identifiers, merge different namespaces, or join by display name. A field called score may hold a cumulative balance rather than a delta: inspect values and its source definition before aggregation.

The war branch needs rounds and locked affiliation when the game uses them. Tasks need personal instances and reset periods. Donations need resource types, costs and daily limits. Apply actual game rules; a card RPG does not imply unrestricted participation, and an MMORPG does not imply mandatory lineups.

## Default historical roster source

For the default historical roster, use each day's user-table snapshot directly. The recorded guild on that snapshot date defines the member's guild for that day's calculation. Join real activity to the member on the same date under the confirmed day basis.

1. Find the snapshot date, member key and guild key. Check that every required day has its snapshot and the fields needed for the denominator. Match the member identity to the activity source. Count identical member-and-guild rows on a day once. Treat unresolved conflicting guild fields for the same member-day as missing attribution.
2. Per guild, count distinct members with that guild recorded on any day in the period. Count a member as active for that guild if the member has a qualifying active event on a day when that day's snapshot assigns the member to the guild. A member recorded under different guilds on different days can contribute to each guild's period counts.
3. This calculation uses the available daily snapshots as recorded. Repeated snapshot values and differences from join, leave, removal, transfer or activity records do not require reconciliation for this metric. Inspect such records only when the user chooses an exact event-time metric or asks about membership changes.
4. If a required day's snapshot or its required fields are unavailable, tell the user which data is missing and that the confirmed snapshot-based rate is unavailable. Use a different denominator only when the user has approved that fallback.

## Historical and opportunity checks

- When the chosen metric needs exact event-time membership, join membership as half-open intervals [join, leave). Preserve same-time ambiguity, rejoining, external helpers and competition-locked affiliations.
- Resolve guild IDs appearing on multiple servers as global guilds or local IDs before grouping. Do not automatically merge them or split a cross-server guild into smaller invented guilds.
- Test eligibility and opportunity at the relevant activity instance. A later unlock cannot justify earlier participation; departure after a round cannot explain absence during that round.
- An open donation mechanic can establish opportunity through validated rules, open windows and the member's contemporaneous state. A dedicated opportunity event is not universally required. Unknown resource balance does not prove inability to donate.
- Cover late joins and early exits separately or compare similar exposure. For several rounds, retain member-round records; one missing slot does not prove that a member had no opportunity throughout the week.
- Validate collection coverage, business timestamps, delay and rule changes before interpreting missing events. Source failure or unavailable partitions are unknown, never zero.

## Minimum data and graceful limits

There is no universal member-count threshold for descriptive guild analysis. Require a validated participation definition and known collection coverage to describe participation, a valid nonzero denominator to calculate a rate, two complete comparable periods to describe continuity, and a verified contribution measure to describe its distribution. Zero observed participation is a valid result when the relevant population, activity availability and complete collection are confirmed; missing or failed collection is not zero. Small samples remain descriptive, not statistically significant by default.

| Missing or unreliable source | Still supported | Not supported |
|---|---|---|
| Historical member base | Credible observed participants by known guild; project-wide reach with verified project login and gameplay | Snapshot-based guild rates and current nonparticipant rosters |
| Eligibility/opportunity | Observed participation; coverage of named observed behaviors if the roster and activity are reliable | Full eligible participation rate or intention judgments |
| Game activity | Attributable participation and contribution | Whether nonparticipants still play |
| Comparable history | Current coverage and contribution distribution | Change, repeat participation or persistent problems |
| Complete member contribution | Credible independently reconciled guild output, if available | Full-member contribution concentration |
| Goal rules | Participation and supported contribution structure | Failure to achieve goals or reward gaps |
| Guild identity | Project-wide reach when the player key, login and gameplay are verified | Guild-specific conclusions and rankings |
| Credible participation | Independently verified member contribution, if available | Participation counts, coverage and continuity |

Partial eligibility may support an explicitly labeled known-status sample. Only report an unknown-population count when the roster can identify that population. Missing coverage must not become fabricated numerical precision-loss estimates.

For sandbox data, apply the main Skill's runtime-only boundary even if queries return plausible numbers. Do not use sandbox outputs to validate screening or operational recommendations.
