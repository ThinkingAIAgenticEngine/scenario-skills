---
name: ae-guild-activity-analysis
description: Analyze guild activity and gameplay participation in card RPGs and MMORPGs. Use for weekly guild operations reviews, member activity rates, gameplay reach among players who logged in, participation across days or periods, and guild contribution. Compare periods, identify changes, and recheck flagged cohorts. Scope excludes general guild ecology, game-wide churn recall, combat tactics and full campaign ROI.
---

# Weekly Guild Operations Review

Version: 0.8.14. Skill type: analysis. Audience: game operations, designers and analysts.

The weekly decision is which guilds need attention, where participation changed, and what happened to the members flagged last week.

Use the confirmed project, population, behavior and period as the analytical scope. Guild wars, tasks, donations and construction are examples of gameplay a project may support. Reply in the user's language using business terms.

## Confirm the measurement before querying

Confirm the measurement, dates and scope in the first response. If the measures for a weekly inspection are open, propose **② member activity as primary and ③ own-guild gameplay among active members as supporting**. Offer **① project-wide gameplay reach** for project-wide questions. If a general activity question still has several plausible meanings, offer two or three relevant options, show each numerator, denominator and key data requirement, and recommend one. Obtain any missing project or guild scope in the same exchange. For scheduled guild wars, propose complete comparable rounds.

For a relative request such as “最近 N 天”, propose the latest N complete days under the requested day basis, or calendar days in the task time zone by default. Give the inclusive dates and day basis in the initial confirmation. For a daily analysis with no duration, propose seven complete days. Honor explicit dates or a request to include the current day. After confirmation, [apply the confirmed date window](references/data-contract.md#relative-date-boundaries) to the query. Add an earlier comparison window only when requested or confirmed.

| User's question | Measurement to offer | Key data requirement |
|---|---|---|
| How many guild members are active? | **Member activity rate.** Members who logged in or took a specified active action on a day assigned to that guild ÷ all distinct members assigned to the guild on any day in the period. | Daily user-table snapshots with guild affiliation and dated game activity. Ask which behaviors count if it matters. |
| Do active members join the selected guild gameplay? | **Guild gameplay coverage among active members.** Active members who did the named gameplay while affiliated ÷ active members of the same guild in the period. | Historical membership, game activity and verified gameplay actions. |
| Do the same participants come back? | **Same-guild repeat participation.** Prior participants who took part in both comparable periods in the same guild ÷ prior participants in that guild. | Two comparable periods and a stable guild and player key. |
| How often do this week's participants play? | **Multi-day participation.** Participants who did the selected gameplay on at least two distinct days in the period ÷ participants who did it at least once in the period. | Dated gameplay records. State the proposed day threshold. |
| Do members who get a chance to play actually take part? | **Participation among opportunity holders.** Actual participants with a verified opportunity ÷ members with a verified opportunity. Match participation and opportunity at the same round or activity before counting members. | Actual participation records and verified opportunities. Confirm a member-round denominator separately if needed. |
| How widely does guild gameplay reach the project's players? | **Project-wide gameplay reach.** Distinct project players who logged in and played the selected gameplay within the period ÷ all distinct project players who logged in within that period. | A reliable project player key, verified login and gameplay records, and a common game-day window. |

Use the measures the user confirms. Match both queries and output to that selection. If the user already supplied an unambiguous scope and measurement, restate them briefly and proceed. For contribution only, confirm the contribution measure, unit and period.

For a measure that uses guild gameplay, confirm whether to analyze specified gameplay or all guild gameplay that can be verified in the project. Include this choice with the initial measurement and period confirmation. Once the scope is clear, use verified event mappings within it and list the behaviors actually included in the results.

For an explicit restart or fresh test, use only the inputs the user supplies for that test. Propose missing dates, scope and measures afresh, confirm them before looking up assets or results, and use evidence obtained for the new test. Treat it as a first baseline unless the user supplies a previous watchlist for this test.

For selected guild-based measures, state how events are assigned to the guild. With daily snapshots, match qualifying activity and gameplay to the snapshot on each event's own day. For ③ they may occur on different days in the same period for the same member and guild. For ①, match the login and gameplay sets by project player within the confirmed period. They may occur on different days unless the user chooses a same-day measure.

**When a choice is needed, wait for the user's reply before looking up project assets or running any business-data query, including a saved report or a file-based calculation.** A saved report or convenient field can help implement a confirmed measurement. If verification shows that its required population or evidence is unavailable, explain what is missing and ask before changing the metric or denominator. Offer observed participant counts as a fallback when the gameplay record supports attribution. Use that fallback without another round of confirmation when the user included it in the original scope or already approved it.

## Run the weekly inspection

After confirmation and data verification, use this order for a weekly review:

1. Recheck the previous inspection’s named guilds or fixed cohorts where they fit the confirmed measures. Use the [weekly comparison and follow-up rules](references/metrics.md#weekly-comparison-and-follow-up). With no relevant prior inspection, mark this as the first baseline.
2. For each complete week calculate ② as active rostered members A divided by snapshot roster M when ② is confirmed. Calculate ③ as active participants in their own guild's selected gameplay P divided by A when ③ is confirmed. Use the same-day guild match for each gameplay event. Pair the results when both measures are confirmed. Compare counts and percentage points and examine member continuity for the measures selected.
3. Compare each guild with its own comparable weeks. Prioritize one or two signals by affected members, magnitude, repeated changes and evidence quality. Check rankings and ties across the confirmed scope. Choose drill-downs that explain the selected measures.
4. Deliver the [weekly report, charts and follow-up](references/report-template.md#weekly-inspection). Give the headline comparison at the declared [roll-up grain](references/metrics.md#weekly-comparison-and-follow-up), guild changes, focused findings and next checks. Link full guild details when available. If a confirmed measure lacks evidence, explain its limit and deliver other confirmed measures that are supported.

## Analyze participation beyond the headline rate

Treat questions such as "How is participation?" or "How active are guild members?" as a short diagnosis. When presenting measurement choices, say which supporting views you will include for the chosen measurement. For a broad assessment, preview the guild screening, targeted drill-down and operational follow-up in one sentence. Keep the confirmed headline numerator, denominator, scope and dates.

- **Coverage and composition.** Show the headline count and rate with its denominator. Break out the relevant gameplay types, guild segments or opportunities when supported. Name overlapping groups and use the confirmed base for comparable rates.
- **Frequency.** Show the number and share of participants active on multiple days, or repeated activity instances for a round-based question when the instance key is verified. State the participant base and time unit.
- **Change and continuity.** Use comparable complete subperiods inside the requested window when available. Show the change in counts and rates, how many prior participants also participated in the later period, and the counts observed only in each subperiod. Use the prior participant set as the repeat denominator. Match people within the confirmed scope, using the same guild for guild-level continuity and the same project for project-wide reach.
- **Screen within scope.** For guild-level work, compare each guild with its own comparable periods. For ①, screen by gameplay or player cohort and keep the project login denominator for the headline. Add guild-level views only when they fit the confirmed scope and have verified attribution. Show the base, affected count and rate together, and explain the selection.
- **Follow the evidence.** Select the strongest one or two signals using affected counts, comparable changes and evidence quality. Group guilds that need the same [signal-specific check](references/metrics.md#signal-specific-checks) and keep their results separate. For still-active members who missed the selected gameplay, verify [online-session and opportunity evidence](references/metrics.md#online-sessions-and-opportunities) before drawing timing conclusions. Complete supported checks in this review using available data or an in-scope read-only query. For each unresolved question, name the missing evidence and the conclusion it prevents. If no signal stands out, report the observed range and a comparable next check.
- **Give an operational judgment.** Apply Step 5 to each selected finding. Name the project or guild, gameplay and affected cohort, give the evidence, and specify one verification action and metric for the next comparable cycle. Contribution analysis requires a verified ledger and a contribution question or full review.

Use the supporting views that the selected data can answer. Reuse common event queries across views. If comparison needs dates outside the requested window, confirm the extra period first. For a request explicitly limited to one value, provide that value, its counts and scope.

## Verify data and run the confirmed analysis

1. Record the confirmed dates, day basis, gameplay, numerator, denominator and scope. Align source dates with the confirmed basis. Verify the identity unit and, for guild-level results, the guild namespace.
2. Read the [gameplay mapping contract](references/data-contract.md#mapping-contract). Verify actual events, subtype values, fields, samples and coverage. If a newly discovered ambiguity would change what the measure counts, clarify the intended behavior with the user before calculating the affected result.
3. Use the available ae-analysis Skill and [AE execution](references/ae-workflow.md), or trustworthy user-provided files. Preserve the confirmed environment and read-only scope.
4. Read [metric rules](references/metrics.md) before calculation. Prepare a compact scope card and mark each component as supported, limited, unknown or not applicable.

**Input prerequisites follow the measure.** For ①, use a reliable project player key, aligned game days, verified login and actual gameplay, and the [project login base](references/metrics.md#project-wide-gameplay-reach). Guild keys, affiliation snapshots and opportunity records support guild-level or opportunity claims when selected. Contribution-only questions can use a verified ledger. Two comparable periods support continuity.

**Scope and output:** use the [weekly inspection](#run-the-weekly-inspection) for weekly operations and the [diagnostic views](#analyze-participation-beyond-the-headline-rate) for general assessment. For targeted work, establish the population needed by the selected measure and use the relevant steps below. Reserve the five-step review for a requested comprehensive gameplay and contribution assessment. Report evidence, findings and follow-up for the selected scope. Do not add a universal guild health score.

## Step 1. Establish the member and opportunity base

For project-wide reach, establish the period login set using [the project player key](references/metrics.md#project-wide-gameplay-reach) and proceed to participation coverage. Apply the guild and opportunity checks below when the confirmed measures require them.

- **Metrics:** members present during the period, members active while affiliated, eligible members and unknown eligibility; distinguish late joins and early exits.
- **Data:** use each day’s user-table snapshot directly for the default [historical roster](references/data-contract.md#default-historical-roster-source). Pair it with dated game activity. Use activity schedules and qualification rules when the chosen metric requires them.
- **Judgment:** assign daily activity using the same day’s snapshot. Use valid-time membership or competition locks when the confirmed metric requires exact event-time affiliation. A selected combat lineup covers the members offered a slot.
- **Output:** name the snapshot scope and denominator. If required snapshot data is unavailable, tell the user which days or fields are missing and that the confirmed snapshot-based rate is unavailable. Use a different metric or source only with the user’s approval.

## Step 2. Analyze participation coverage

- **Metrics:** distinct participants by gameplay, eligible-member participation where supported, active-member coverage of named observed behaviors, and actual opportunity coverage when relevant. Always show numerator and denominator.
- **Data:** actual combat participation, voluntary task activity or trustworthy completion, and independent donation or construction operations. For ① intersect the verified project gameplay set with period logins. For guild-level or opportunity measures use the corresponding affiliation or opportunity base from Step 1.
- **Judgment:** for ① compare verified gameplay among period login players against comparable project periods. For guild-level measures distinguish activity, named gameplay and known opportunity limits using the guild's comparable history. Low points or a battle loss do not establish nonparticipation. Missing gameplay or completion-only tracking limits absence claims to the observed scope.
- **Output:** which activities reach which members, uncovered groups, and evidence-backed opportunity restrictions. Stable participant totals do not end this step or the remaining workflow.

## Step 3. Analyze continuity and member turnover

- **Metrics:** previous participants, repeat participants, previous participants not seen again, and newly observed participants. Match within the same project for project-wide measures and within the same guild for guild-level measures. Show the fixed-base repeat ratio and net change separately.
- **Data:** comparable periods of the same behavior; reuse membership, activity and opportunity evidence to explain changes.
- **Judgment:** stable totals can hide replacement of previous participants. Check other guild activities before calling someone absent from all guild gameplay. Separate departure, transfer, inactive observation, limited opportunity and unknown status. Newcomer or fixed-core-member views are supporting explanations only.
- **Output:** whether the participation base is sustained or changing, which previous participants changed behavior, and how much of their status is known. Without a complete comparison period, mark continuity unavailable and continue with current coverage and contribution.

## Step 4. Analyze contribution structure

- **Metrics:** effective contribution total, positive contributors, Top-k share, and changes in contributor count and total. Default k to three for description; track the previous top group separately if discussing the same core members. Add goal status only when its rules are known.
- **Data:** verified contribution deltas or final settlements, member attribution, units and rules; resource-input records are a separately labeled alternative.
- **Judgment:** concentration with fewer contributors differs from concentration with growing total output. When contributors number no more than k, a 100% Top-k share is mechanical. High share alone does not prove fatigue, unfairness or operational risk. Ties across the Top-k cutoff make the selected member group non-unique; apply the metric reference before calling it a core group.
- **Output:** who supports the observed output, whether the distribution changed, and what operational consequence is actually evidenced. Missing effective contribution cannot be replaced by combat counts or mixed resource spending.

## Step 5. Prioritize follow-up and verification

- **Metrics:** the selected findings, affected member counts, comparable history, evidence strength and any verified output or goal impact.
- **Data:** reuse completed steps; no new generic score or mandatory dataset.
- **Judgment:** prioritize confirmed participation-structure issues with an actionable next step. Unknown high-impact cases belong in evidence collection, not a confident cause ranking. If no concern is supported, say so without manufacturing a worst-guild list.
- **Output:** use the [report template](references/report-template.md). Match each project, guild or cohort finding to one concrete verification action and a comparable next observation window. Implementation remains a separate user decision.

## Decision branches and self-verification

Retain each confirmed result its evidence supports. Missing guild identity stops guild-specific conclusions. Project-wide reach can proceed with the verified project player, login and gameplay sets. Missing credible participation evidence stops participation conclusions, while a verified ledger still supports an independently requested contribution analysis. Missing history limits trend and repeat judgments. Event-collection or rule changes invalidate the affected comparisons until resolved.

Before delivery, verify set reconciliation, rate membership and time alignment, contribution units and deduplication, and the evidence behind priority labels using the metric rules. Inspect key member examples. On failure, correct the affected mapping or calculation and regenerate dependent results; if unresolved, withdraw that conclusion and show the gap. Do not repeatedly rerun successful queries.

**Sandbox boundary:** incomplete sandbox tracking supports runtime checks only: discovery, query execution, missing-data branches and report generation. Sandbox figures or lists are test artifacts, not validated business screening, customer findings or proof of useful recommendations. Synthetic known-answer cases validate rules; trustworthy business data plus operator review validate business usefulness.

## Boundaries and common questions

- Keep entry, exit, transfer, newcomer participation and opportunity analysis tied to the three lenses. Do not expand into social graphs, guild recruitment strategy, reward redesign or game-wide churn prediction.
- No decline? Continue: coverage gaps, participant replacement or concentration can exist under stable totals. No detected issue? Return supported findings and the next comparable check.
- Never equate absence with unwillingness, silence with permanent churn, low contribution with no participation, or unclaimed rewards with incomplete goals. Association is not causation.
- Use read-only analysis and necessary local artifacts. This Skill does not itself send member messages, remove members, change rewards or persist platform cohorts and dashboards.

## References

- [Data contract](references/data-contract.md) for event mapping, membership and minimum evidence.
- [Metric rules](references/metrics.md) for population, aggregation, calculations and diagnostic checks.
- [AE workflow](references/ae-workflow.md) for AE prerequisites, execution and failure handling.
- [Report template](references/report-template.md) for weekly and focused deliverables.
- [Verification cases](references/verification-cases.md) for testing scope, formulas and evidence boundaries.
