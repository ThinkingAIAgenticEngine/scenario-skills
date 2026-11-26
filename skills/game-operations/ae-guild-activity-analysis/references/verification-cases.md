# Verification cases

Use these synthetic cases to verify the decisions, output and query scope of changes to this skill. The evidence described in each row defines the fixture.

| Case | Input or evidence | Expected behavior |
|---|---|---|
| Initial confirmation | On October 12 at 09:00 UTC+8, the user says "最近 14 天全项目公会玩法参与情况". Project and day basis are unspecified | Propose September 28–October 11 as 14 complete UTC+8 calendar days. Confirm the project, period, login reach definition and gameplay scope together. Apply the dates once confirmed. |
| User-specified day basis | At 09:00 on October 12, the user requests 14 complete game days using 10:00 UTC+8 boundaries and labels each game day by its start date | Propose September 27–October 10, because the October 11 game day is still in progress. Use that basis after the user confirms. |
| Specified gameplay | The project, dates and metrics are confirmed, and only donation gameplay is selected | Proceed to verify donation and the selected population. Ask only if a material ambiguity remains. Use only the selected gameplay in the results. |
| Registration and combat | All verifiable gameplay is selected. There are 30 registrants and 18 verified combat participants | For confirmed actual gameplay participation, use the 18 combat participants. Clarify the behavior if the requested measure still leaves registration versus actual participation open. |
| Weekly ② only | Project and weeks are confirmed. The user requests member activity with login as the qualifying behavior. A prior watchlist contains play and login outcomes | Query roster and login data, recheck relevant roster and login outcomes, and report ②. The play outcome is outside the selected measures. |
| Weekly ③ only | Project, weeks, qualifying activity and own-guild war participation are confirmed. The user requests ③ | Use the active member and participation populations. The roster supports affiliation matching. Report P/A and its counts. |
| Project reach with missing guild keys | Login set has 100 players. There are 20 players with both login and verified gameplay, plus 5 gameplay-only players. Guild keys are missing | Report 20/100 project-wide reach. Any requested guild breakdown is limited by the missing guild key. |
| Zero login denominator for ① | Reliable login coverage shows zero login players. Verified gameplay records exist | The matched player count is zero and project-wide reach is `N/A`. |
| Member transfer | G1 has M/A/P sets `{a}/{a}/{a}`. G2 has `{a,b,c}/{a,b}/{}`. Member `a` qualified in each guild on different days | Default weekly roll-up has M/A/P counts of 4/3/1, activity of 75% and gameplay coverage of 33.33%. A requested unique-member roll-up has counts of 3/2/1 and rates of 66.67% and 50%. Label the grain and keep it consistent across periods. |
| Ranking tie | Three comparable guilds decline by 12.0, 10.4 and 10.4 percentage points at full precision. The user requests the top two declines | Show the joint second rank. If one of the tied guilds is prioritized for follow-up, explain that choice. |
| Member versus member-round rate | Member `a` has a verified opportunity in two rounds, and participates in one. Member `b` has an opportunity in one round and misses it | The member rate is 1/2. An independently confirmed member-round rate is 1/3. Match each observation to its round and use the confirmed denominator. |

## Member activity only

Use the [AE worked example](ae-workflow.md#worked-example-of-member-activity-only) for the full request, query and response. In the synthetic source, use the same member and game-day key in both tables.

- Each snapshot day from October 5 to 11 records members 1, 2 and 3 in guild 7, except that member 3 is in guild 8 on October 11. Include a duplicate snapshot for member 2 on October 8.
- Member 1 logs in twice at the start boundary on October 5. Member 2 logs in at 23:59:59 on October 11. Member 3 has a gameplay event on October 10, a login while assigned to guild 8 on October 11 and a login at the exclusive end boundary on October 12.

The query returns 3 rostered members, 2 qualifying active members, 7 snapshot days and 0 unresolved member-days. Report `2/3 (66.67%)`. Re-run the following variants to test the report boundary.

| Variant | Expected result |
|---|---|
| All login records removed, gameplay retained and login coverage verified | 0/3 (0%) |
| All guild 7 assignments moved to guild 8, with the seven snapshot days complete | 0/0, `N/A` |
| Snapshot day October 10 removed | Rate unavailable due to missing snapshot coverage |
| Add a guild 7 snapshot for member 3 on October 11 while retaining the guild 8 snapshot | Counts from resolved days remain 3 rostered and 2 active; the query shows 7 snapshot days and 1 unresolved member-day. Do not count the disputed login in guild 7 or publish a full rate. |
| Add a snapshot with a missing guild value for member 2 on October 11 while retaining the guild 7 snapshot | The disputed login is not attributed to guild 7. Counts from resolved days are 3 rostered and 1 active, with 1 unresolved member-day; the full rate is unavailable. |

## Partial session coverage

A verified war window is 20:00–20:15 in the project time zone. Four selected members have the evidence below. The only supplied eligibility records confirm `a` and `d`.

| Member | Available session evidence | Expected overlap status |
|---|---|---|
| `a` | Verified interval 20:03–20:12 | Observed overlap |
| `b` | Same-day login at 19:58 with no session end or elapsed session time | Unknown, with same-day login observed |
| `c` | Aggregate online duration of 35 minutes | Unknown, with no usable interval |
| `d` | Verified interval 19:05–19:55 and complete session coverage for the verified activity window | Verified non-overlap |

Report 2/4 with usable session intervals. The overlap buckets are one observed overlap, one verified non-overlap and two unknown. Eligibility is known for two and unknown for two. If the activity window becomes unavailable, a verified same-guild play timestamp inside `a`'s interval can still support an overlap observation at that timestamp. The evidence no longer supports verified non-overlap for `d`.
