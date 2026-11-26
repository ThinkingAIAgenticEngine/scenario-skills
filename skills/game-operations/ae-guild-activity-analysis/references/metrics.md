# Metrics and analytical decisions

Read the needed sections for the current lens. Compute at the game member's actual identity unit, not an assumed natural-person unit.

## 1. Population and time alignment

For a guild and period:

- M: members whose verified affiliation overlaps the period.
- A: members with genuine game activity during that affiliation.
- E_b: members with independently established basic eligibility for at least one relevant opportunity of behavior b while affiliated, regardless of selection or eventual participation.
- O_b: eligible members with an established actual opportunity, such as a combat slot or an open mechanic under its rules.
- P_b: distinct members with credible actual behavior b attributed to this guild. For membership-based rates, resolve valid affiliation or competition-lock attribution first.

For the default daily snapshot roster, M is the distinct member set assigned to the guild on any snapshot date in the window. A is the subset with qualifying activity on at least one date when that date's snapshot assigns the member to the guild. Join on member and game date before deduplication by guild and member. Report the result as a daily-snapshot-based rate.

Build eligibility, opportunity and participation matches at member-activity-instance level before collapsing to a period. Let P_E be participation at an instance where eligibility is valid, and P_O participation at an instance with a validated actual opportunity. Merely appearing in both weekly E and P sets does not prove that the participation was eligible at its occurrence.

For fluctuating rules, match each member to the evidence for the relevant instance, then aggregate at the confirmed unit. A member rate counts each qualifying member once in the period. A member-opportunity rate counts each qualifying member-instance pair. Confirm a change of unit with the user before calculating it. State the unit and denominator. Sum counts at the same grain before calculating pooled rates. Use set unions for distinct player totals across dates or behaviors.

## 2. Coverage

| Measure | Definition and interpretation |
|---|---|
| Project-wide gameplay reach | `count(Login intersect Gameplay) / count(Login)`, using the project player key and one common period |
| Member activity | count(A) / count(M); roster and historical activity must be reliable |
| Observed participants | count(P_b), whether or not eligibility is fully known |
| Eligible participation | count(P_E) / count(E_b); the eligible base is not limited to selected participants |
| Opportunity coverage | count(O_b) / count(E_b); show when selection or allocation limits participation |
| Participation among opportunity holders | count(P_O) / count(O_b); show alongside opportunity coverage, never as a substitute for eligible participation |
| Active-member coverage of named behaviors | Number of A with at least one of the named observed behaviors during affiliation / count(A); describe as coverage, not willingness |

For every rate show numerator, denominator and population. A zero denominator is N/A, not zero percent. Unknown eligibility is not ineligible. Separate credible but apparently ineligible participation as a mapping/rule exception rather than altering eligibility to make the formula fit. Partial known-status rates must not be presented as full-guild estimates.

State the included gameplay and observation types beside the union coverage rate. Call it all-gameplay coverage only when the relevant gameplay and participation collection are complete. With a reliable active-member denominator and valid observed actions, incomplete gameplay collection gives an observed-coverage lower bound, not a complete absence list. Completion-only tasks also miss unfinished attempts. If the denominator is unreliable, withhold the rate rather than claim a numerical lower bound. Known observed participation still proves that a member participated in at least one activity; missing other gameplay does not erase that positive evidence. For example, 9 of 21 active members seen in war or donation establishes at least 9/21 coverage, but not that the remaining 12 skipped every guild activity.

A participant event proves observed activity, not everyone's membership. Nonparticipant lists require a trusted member or eligible roster. When only task completion is tracked, name the metric completion coverage and acknowledge unobserved incomplete participation. Battle losses still count as participation; registration does not.

Interpret current coverage against the same guild's comparable history. When comparing guilds, use similar member size, guild age, server stage, rules and opportunity schedules; if those cannot be aligned, show descriptive values without a best/worst ranking. No invented industry-wide coverage threshold or health score.

### Project-wide gameplay reach

For ①, define `Login` as distinct project players with a verified login in the confirmed game dates and `Gameplay` as distinct players with verified participation in any of the confirmed gameplay types in those dates. Match on a stable project player key. By default, the login and gameplay may happen on different days in the period. Use `Login intersect Gameplay` for the numerator and `Login` for the denominator. For gameplay breakdowns, use the matched subset for each behavior and keep the common login denominator. Use the union of gameplay sets for total reach.

Use the same population rules separately for each comparable period. When frequency or repeat is requested for the same participation population, calculate it from the matched participants for the relevant period. For ①, guild keys and roster snapshots are needed only for guild-attributed views. If their evidence is missing, report the supported project-wide result and state the limit of any requested guild view.

### Participation frequency

For day-based activity, count distinct qualifying game dates per participant of the confirmed period. Multi-day participation is the number of period participants observed on at least two dates divided by all participants in that period. Use verified activity-instance keys for repeated round-based participation. Apply the same behavior and identity filters as the headline measure, and state the participant denominator.

## 3. Continuity and turnover

For comparable completed periods, define P0 and P1 from the same confirmed measurement. Use the same behavior and scope in both periods. For guild-level continuity match members within the same guild. For project-wide reach match users across the project.

- R = P0 intersect P1: observed repeat participants.
- `PriorOnly` = P0 minus P1: previous participants not observed in the current period.
- J = P1 minus P0: newly observed current participants, not necessarily new players or guild entrants.
- Repeat ratio = count(R) / count(P0). Keep leavers in this fixed denominator. State whether the repeat is within the same guild or within the project.
- Net participant change = count(P1) - count(P0) = count(J) - count(PriorOnly).

A conditional repeat ratio may be added for prior participants independently confirmed retained and eligible in the current round: |S intersect P1| / count(S). Show S and its exclusions; never replace the fixed-base result with this survivor-only rate.

Stable totals can coexist with large `PriorOnly` and J sets. Inspect `PriorOnly` for real game activity and other behaviors. Moving from war to donation within the same guild is behavior migration; participation for a different guild is not same-guild continuity. Do not extrapolate two observed periods into a long-term trend.

Preserve three evidence axes for previous participants: game activity (observed, not observed with complete coverage, unknown), relevant-time affiliation (retained, departed/transferred, changing, unknown), and eligibility/opportunity (eligible with opportunity, eligibility-limited, opportunity-limited, unknown). These axes overlap; do not add them as exclusive causes of decline. Event absence does not prove motive or permanent churn.

Use newcomer participation only to explain coverage or turnover. Distinguish first confirmed entry from re-entry and merely observed entry when history is incomplete. Include only entrants whose applicable eligible opportunity window has completed; show incomplete, ineligible and unknown cases separately. Do not penalize late entrants for missing earlier rounds.

## 4. Contribution structure

Choose one comparable, nonnegative, member-attributable contribution measure at a time. Use verified deltas or settlements. Deduplicate business transactions; resolve resets, reversals, refunds and duplicate member/guild reports. Never sum cumulative snapshots or backfill the current cumulative property as historical contribution.

For each guild and period:

- Effective member contribution total C = sum of reconciled member contributions for the chosen type.
- Contributors N = distinct members with a positive value.
- Top-k share = sum of the k largest positive member values / C. Default k=3 unless the user or rule specifies otherwise; always show k, N and C.
- C=0 gives N/A. When N is no greater than k, 100% is mechanical and not a risk finding.

Current Top-k and prior Top-k are separately selected sets: their shares describe distribution, not the behavior of the same people. To discuss core-member change, fix the prior Top-k set, then inspect its current contribution, participation and affiliation separately. A top contributor is an analytical cohort definition, not proof of a formal guild leadership role.

**Ties at the cutoff:** equal contributions on both sides of rank k leave the Top-k share well-defined, but its selected members non-unique. Disclose the cutoff value, tied-group size and selection rule. A stable member-ID tie-break is acceptable for a reproducible example, not proof of a uniquely important core. For longitudinal interpretation, prefer the fixed prior positive-contributor cohort or a fixed cohort that includes everyone tied at the prior cutoff plus higher contributors. Name that expanded cohort and its actual size; do not relabel its share as Top-k. Ties entirely inside the selected k do not make membership ambiguous. Never change k silently or identify a core by an arbitrary tied sample alone.

If unresolved negative member totals remain, hold the concentration calculation and report the ledger issue. If member attribution is incomplete, do not publish a full-guild share; an observed-sample share may be shown only with its scope and missing coverage explicit. Guild/system/outsider output is not silently assigned to members: reconcile or present it separately.

Resource input and effective contribution are different measures. Gold, diamonds, damage and points cannot be added. Where only reliable resource inputs exist, report input amount and, if useful, its separately labeled resource-specific distribution; do not relabel it as guild contribution points. Log rows without operation deduplication are not verified operation counts or settled amounts.

Task/war-generated contribution is output, not another independent active behavior. A verified credited amount may be useful contribution evidence without proving the member was active at credit time. Output and activity timestamps may therefore differ.

### Interpretation

| Observed combination | Supported interpretation | Follow-up |
|---|---|---|
| Fewer contributors, higher Top-k share, lower total | Distribution narrowed while output fell | Verify ordinary contributors' activity, affiliation and opportunities |
| Similar coverage and continuity, higher Top-k share, higher total | Output growth is more concentrated | Check rules and the fixed prior/current top groups before judging a problem |
| Stable total participants but fewer repeat participants | Participant replacement is hidden by the total | Inspect `PriorOnly` and J, including entry/exit and behavior migration |
| Eligible base large but actual opportunity base small | Opportunities constrain observed reach | Verify allocation or activity availability |
| Goal achieved despite fewer participants | No demonstrated goal shortfall | Do not automatically demand more participation or spend |

Higher concentration alone does not establish fatigue, unfairness, dependency risk or future collapse. If goals are available, compare the same stage and rules; goal gap for a simple positive target is max(target - effective progress, 0). Unknown goals remain unknown. Unclaimed rewards are not failed goals; ongoing activities are not final failures. Co-movement of participation and output is not causal attribution.

## 5. Follow-up and verification

### Weekly comparison and follow-up

Use complete game weeks or equally long consecutive day windows agreed with the operator. Keep the confirmed day basis, weekday mix, collection rules and activity schedules comparable where they affect the measure. For each guild compare the counts and rates needed by the confirmed measures. With several comparable prior weeks, show their observed range, how often a similar change occurred and its size in members. With one prior week report the week-to-week change. With none report the current level. State known changes that limit comparisons. Require confirmation for extra history outside the approved period.

For a weekly roll-up of individual guild results, default to distinct `(guild key, member key)` pairs for each required population (M, A or P). Sum the population counts across the same guild scope before calculating the confirmed rates. A member observed in two guilds can contribute a pair to each. If the requested roll-up is unique project members across those guilds, take the union of member keys for each required population after applying its guild criteria and label it as a player-level roll-up. This population uses the member and gameplay rules of the underlying guild measure. ① uses the separate period login denominator. State the roll-up grain and use it consistently across periods.

Read the latest relevant prior inspection from the conversation or a supplied report when it fits the current scope and selected measures. For a fresh test use the prior watchlist only when the user supplies it for that test. Verify project, guild key, cohort rule or member keys, original dates, baseline count and definitions. Hold the cohort fixed when checking later weeks and recheck its outcomes within the confirmed measures. Reconstruct from original dates only when those data are available and within scope. A guild-level baseline supports a guild-level recheck. If cohort identity or its original definition is unavailable, name the gap and continue screening this week.

For a fixed cohort report its original count and the relevant observed outcomes in the target week. This may include current roster, in-guild activity, login or named gameplay for a confirmed measure. Use disjoint categories when adding counts. Describe change against the prior concern to the extent supported. In a backtest with no prior list, a labeled replay may freeze a cohort using evidence available by the earlier cutoff, then open the later window to test its follow-up.

### Signal-specific checks

Screen with each guild’s own baseline where available. Show absolute counts beside rates, including the comparison base for small guilds. For cross-guild rate comparisons, use peers with comparable size, age, server stage and gameplay availability. If peer context is missing, counts can still identify where the most observed members are affected. For each ranking claim, verify the metric, direction and all ties at the stated rank or cutoff against the full comparable guild set using unrounded values. State the tie and explain why any subset was selected for follow-up. Use a detail link for long tie lists.

Group guilds when the same diagnostic question can be answered with compatible records, date windows and rules. Reuse existing results first and batch any missing read-only checks that fit the confirmed scope. Keep each guild's cohort, counts, denominator and result visible. Run a separate check for a distinct signal or when the required records or rules differ.

Use verified fields and coverage to answer the next question during the current review. If a check is limited, report the supported result and name the smallest missing record or rule, the affected cohort or round, and what remains unresolved. For example, when login and play are observed but opportunity is unknown, name the opening schedule or member eligibility record needed for the relevant round. Permission, additional periods and changes to the confirmed metric follow the existing scope rules.

| Observed signal | Drill-down within the confirmed period | Operational check |
|---|---|---|
| In-guild login falls and previous login members still appear on the roster | Check project login for those members in the same period. Match login dates to the daily roster to distinguish no observed project login, login while assigned to another guild, login while recorded as unaffiliated, and login with unknown guild assignment. Report any overlap in the member counts. | Where evidence is incomplete, identify the missing login or snapshot coverage. Track the same cohort's in-guild login and gameplay in the next comparable cycle. |
| Prior participants do not return, even when totals hold steady | Compare previous-only, returning and later-only participants in the same guild. Among previous-only members, count those still active in that guild and inspect which gameplay they previously played and whether they switched activities. Use dated snapshots for affiliation. For still-active members, check [online sessions and opportunities](#online-sessions-and-opportunities). | Identify any missing opportunity evidence and recheck same-guild repeat with the prior participant base fixed. |
| Many active members have no observed guild gameplay | Locate the largest uncovered groups, then break out coverage by named gameplay. With independent records, check activity opening, eligibility, allocated opportunities and actual play for the same instance. | Verify the first unresolved condition. Apply ticket rules separately to entry and scoring when fighting without tickets is possible. |
| Newly observed members participate less | Build a cohort by verified join date, or label it “first seen in the available snapshots.” Compare first and repeat play only among members with the same follow-up time and comparable available rounds. | Recheck participation after the same number of complete opportunities. Snapshot first appearance alone cannot establish a new join. |
| Contribution concentrates in a full review or contribution question | Reconcile the ledger, compare total output, number of contributors and Top-k share. Track the fixed prior contributors and check any goal change. | Recheck contributors and output together in the next comparable round. |

Use snapshot changes to describe observed guild changes. Claims about an exact exit, transfer or rejoin require evidence at the claimed time. If a requested snapshot date or key is missing, follow Step 1 before reporting rates.

Prioritize supported structural findings using magnitude, comparable persistence, verified impact and actionability. Do not equate missing data with good health or severe risk. Relation unknown -> verify the roster; opportunity limited -> verify schedules or allocation; confirmed eligible and active with opportunity but no participation -> verify entry points, timing or organization. Game activity somewhere in the week does not prove presence during the event.

Recheck after a complete comparable cycle using the same cohort, eligibility, definitions and units. For opportunity changes, report eligible base, allocated opportunities and actual participants together. For concentration concerns, report contributor count, total and share together. Record rule changes and other interventions; do not promise an improvement percentage or causal effect without evidence.

Before output:

1. Reconcile `P0 = R union PriorOnly` and `P1 = R union J`. The component sets are disjoint, and the net change equals `count(J) - count(PriorOnly)`.
2. Verify rate numerators are valid members of their stated denominators at relevant opportunities. Show unknown counts only when enumerable.
3. Check membership at the precision required by the selected measure. Daily snapshot rates use the snapshot on the activity date. Check exact membership or competition locks only for a measure that needs them. Verify entrant exposure for newcomer comparisons and use a consistent identity namespace.
4. Reconcile contribution units, nonnegative member values, totals and Top-k; manually inspect a few material records and fixed-core examples, including cutoff ties and whether the reported coverage matches the collected gameplay.
5. Confirm lists are complete or clearly sampled, examples trace to source evidence, and every recommendation distinguishes fact from hypothesis.
6. Correct affected calculations and dependent conclusions if a check fails. If evidence cannot resolve the failure, omit the unsupported result and retain a precise gap; do not report a successful verification.

### Online sessions and opportunities

For a selected cohort that still logs in but misses the gameplay, first verify whether session intervals are usable for that cohort and period. Check the source definition, member key, timestamp timezone, and duration units. Inspect bounded records for coverage and plausible intervals. Use verified start and end records or a defined start with session-level duration. A login timestamp supports a point in time, and an aggregate online duration supports time spent. Both lack the information needed to construct a session interval by themselves.

Run the supported comparisons within the confirmed scope in this review. With usable sessions, compare online intervals against verified activity windows. If the schedule is missing, compare against observed timestamps of the same guild's verified gameplay when useful, and describe the overlap as an observation at those timestamps. For members with insufficient session evidence, report any login and gameplay co-occurrence supported by timestamps or game days and name the incomplete coverage. Verify eligibility, roster locks and allocated slots from independent evidence at the relevant round when available.

Report the cohort size and how many members had usable session evidence. Classify overlap status as observed overlap, verified non-overlap or unknown. Use verified non-overlap only with sufficient session coverage for that member and a verified activity window. Same-day login or aggregate duration alone leaves overlap unknown. Report same-day evidence and eligibility or slot evidence separately, with their own coverage. Name the missing evidence for each unresolved question.

## Synthetic reasoning example

In this synthetic example, a guild has prior task participants {a,b,c} and current participants {b,c,d}. Both periods have three participants. The fixed-base repeat ratio is 2/3, `PriorOnly = {a}` and `J = {d}`. The participant mix changed while the total stayed flat. Current affiliation, activity and opportunity evidence are needed to explain a's absence. The records first show d in the current period. If only two members have positive contribution, a Top-3 share of 100% follows from the contributor count.
