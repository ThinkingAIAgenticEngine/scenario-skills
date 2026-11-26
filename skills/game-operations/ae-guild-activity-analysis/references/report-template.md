# Participation analysis report

Respond in the user's language. Use the weekly report structure for weekly inspections and the five-step structure below for full participation and contribution reviews. For a general or targeted assessment, lead with the confirmed rate and its counts, then show the strongest supported findings and relevant follow-up. List the gameplay actually counted next to the gameplay results. Keep detailed guild results accessible. Within the selected scope, report actual data gaps without filling them with zeros.

## Weekly inspection

Build the weekly report around the decisions the operator needs to make.

1. **Weekly summary and scope.** Give the dates, confirmed measures and one operational takeaway. Show how last week's focus cohorts changed or identify this as the first baseline.
2. **Overall comparison.** Show only the confirmed weekly rates and their required counts. If both are confirmed, pair them. Label the [roll-up grain](metrics.md#weekly-comparison-and-follow-up) as guild-member pairs by default or unique project members when requested. Apply the same grain to both periods. Explain changes in counts and denominators and include the rising, flat and falling guilds when the full comparison supports it.
3. **Guild screening and focused findings.** Show the most meaningful changes with ties, then present what the shared checks established for each selected guild. When supported, include gameplay composition, multi-day participation or prior-only, returning and current-only members to explain the finding.
4. **Diagnostic follow-up.** For each selected signal, say which question is still open, what record or rule to check next and how the result would change the diagnosis. Reuse verified findings. Complete in-scope checks in this review, then carry forward the remaining evidence gaps and fixed-cohort rechecks.

Deliver the report in Markdown. Use charts where the client supports them and they clarify the decision. With two comparable weeks, use paired bars or a two-period table for counts and rates. Use a ranked change bar or distribution for guild screening. A gameplay comparison or cohort breakdown helps when the aggregate hides a change in mix or membership. Use a time-series line when there are enough comparable time points to show its shape. Label periods, units, denominators and any incomplete coverage. Provide the key values in text or an accessible table, and link the full guild detail.

Close with a reusable row for each next-week cohort: project and guild key, exact baseline dates, membership/behavior filters, fixed baseline count, and the metric and dates for the next complete week. A reproducible selection rule can stand in for member IDs. Include a source reference so the next reviewer can reproduce the cohort before measuring return. Computing outcomes after the approved cutoff belongs to the next review.

## Project-wide gameplay reach

Show the period login count, matched gameplay count and rate, along with the gameplay actually included. For comparisons, use the same [project player population rules](metrics.md#project-wide-gameplay-reach) in each period and report any confirmed frequency or repeat measures from those sets. Keep guild roll-ups as separately labeled views when requested and supported.

## 1. Decision summary and scope

Lead with the strongest supported finding about coverage, continuity or contribution, the guild/gameplay involved, and the next useful action. If no concern is supported, say so. A flat participant count is not a stopping condition.

Scope includes project and environment, guild namespace, identity unit, behaviors, confirmed dates and day basis, data cutoff, key rules and missing components. Add one compact line naming the included gameplay, observed behavior types and collection completeness in each period. Describe collection gaps and activity availability separately. Explicitly distinguish business analysis from sandbox runtime verification. For sandbox verification, use pass/limited/unavailable execution states and test artifacts; do not issue a validated operational shortlist.

## 2. Five-step results

| Step | Show | Interpret |
|---|---|---|
| Member and opportunity base | Historical members, active members, eligible members, opportunity limits and unknowns | Which denominator and comparisons are credible |
| Coverage | Behavior participants and qualified rates; active-member coverage with its named observed scope | Which members participate or lack opportunity; distinguish inactivity from guild-specific absence |
| Continuity | Prior/current participants, R, `PriorOnly`, J, fixed-base repeat ratio, optional retained-eligible view | Stable base, replacement, behavior migration or unknown status |
| Contribution structure | Type/unit, total, contributors, k and Top-k share; disclose cutoff ties and any fixed prior cohort | Distribution changes with absolute output; limitations and optional goal context |
| Follow-up | Supported issue, affected scope, evidence, one action and verification metric | Who merits attention and what should be checked first |

Compare within the same guild and comparable periods first. Cross-guild comparisons need similar size, age, server stage and opportunities. Do not turn descriptive differences into unsupported rankings or a universal health grade.

## 3. Guild and member tables

Guild table:

| Guild / gameplay | Coverage | Continuity | Contribution structure | Supported finding / limit | Next action |
|---|---|---|---|---|---|
| Verified guild key | Numerator/denominator or count only | R/P0, `PriorOnly` and J when available | Type, C, N, k, share | Fact; hypothesis separate | One specific verification |

Member table, only for necessary evidence-backed follow-up:

| Member / relevant guild | Game activity | Guild behavior | Affiliation at activity time | Eligibility / opportunity | Continuity / contribution evidence | Follow-up |
|---|---|---|---|---|---|---|
| Stable identity and namespace | Observed / not observed / unknown | Actual records or qualified absence | Verified state or unknown | Known limit or unknown | Prior/current or fixed-core observation | Evidence-matched action |

For incomplete gameplay collection, label the coverage as observed behavior coverage and state its lower-bound condition; do not call unobserved members absent from every guild activity. With Top-k cutoff ties, distinguish a reproducible selected sample from an expanded tied cohort or the full prior contributor cohort; include the cohort size when interpreting changes.

A current nonparticipant list must originate from a reliable member/eligible roster. A prior-participant list can originate from P0 but must not claim current membership without evidence. Do not export unrelated members or personal information. State any sample limit and keep complete necessary detail in a separate accessible artifact.

## 4. Action and recheck

For a broad assessment, state the scope screened, any ties at the reported rank and the reasons for prioritizing selected guilds. Show a shared check together with each guild's result and affected count. Use guild keys where names are unavailable. For timing checks, give the cohort size, usable session count and overlap status counts. Show eligibility and slot evidence separately when relevant. Include results verified in this review and specify the missing evidence and open question for any incomplete check.

| Signal and affected guild cohorts | Checks completed and results by guild | Next diagnostic check and how to interpret it | Next comparable cycle |
|---|---|---|---|
| Identify each guild, relevant gameplay and cohort size | Show counts, base, rate, change and what the check established | Name the open question, the source or rule needed, and what a supported result would clarify | Specify the cohort, metric and window to recheck |

For a sandbox test, label the rows as examples of how the screening works. When no finding warrants follow-up, summarize the evidence and the next comparable check.

- Coverage restricted by opportunity: verify rules/allocation; recheck eligible members, actual opportunities and participants together.
- Stable totals with participant replacement: inspect prior participants' affiliation/activity and entry timing; recheck fixed cohorts and overall coverage.
- Narrower contribution base with lower output: verify ordinary contributors and prior core members; recheck contributor count, total and share together.
- Incomplete evidence: obtain the smallest missing roster, rule or ledger segment before proposing member intervention.

These are action hypotheses, not automatic interventions or promised improvements. A successful follow-up check confirms whether the intended state/metric changed; causality requires further evidence when other conditions also changed.

## 5. Evidence and self-check receipt

Record source/definition identifiers or file links, actual event/subtype mapping, windows, rules, identity and deduplication units, completeness and performed self-checks. Include failures and corrected dependent results where material. Do not claim source-code uniqueness, dual-version compatibility, business validation or operational impact without corresponding evidence.

For runtime-only work, close with discovery/query status, supported and missing branches, output checks, and remaining business-validation requirements. Never repurpose test figures as customer results.


## Compact filled example

This synthetic example answers "Review this guild's participation across two complete comparable war rounds."

Guild Sample has the same five members `a`, `b`, `c`, `d` and `e` in both rounds. All five are active while affiliated, eligible and independently confirmed to have an opportunity. Actual combat collection is complete. Prior participants are `a`, `b`, `c` and `d`. Current participants are `b`, `c`, `d` and `e`.

Example answer:

"Four members fought in each round. Three returned from the previous round, and one played only in the current round."

| Step | Result | Interpretation or limit |
|---|---|---|
| Base | Five members, active members, eligible members and opportunity holders in each round | Same verified scope and complete war rounds |
| Coverage | Prior and current war coverage: 4/5=80%; opportunity coverage: 5/5=100% | War is observed; all-gameplay absence cannot be established |
| Continuity | R=3, `PriorOnly={a}`, J={e}, repeat=3/4=75%, net change=0 | e first appears in the current war records |
| Follow-up | a remains affiliated, active and eligible with opportunity, but has no current combat record | Check event-time availability and other gameplay; next comparable round, recheck a and the fixed prior participant group |

Reconcile the previous and current participant sets with the returning and period-only groups. Verify that all rate numerators belong to their denominators.
