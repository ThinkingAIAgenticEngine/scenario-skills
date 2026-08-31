# Production Report Contract

Follow this format unless the user explicitly requests a different presentation. Omit inapplicable rows rather than inventing values.

## Output Template

Follow the global **Response Language** rule above for this report. The template below is in English for reference structure only. Replace `<RATE_TYPE>` with the scenario-specific term (retention rate / repurchase rate / conversion rate / churn rate / renewal rate / custom rate).

### Report Header (above Part 1)

A 5-line blockquote header immediately above Part 1, acting as an at-a-glance summary. One field (or one group of related fields) per line, bold key name, `｜` (full-width pipe) **only** between tightly-related fields grouped on the same line. Do NOT cram more than two fields onto one line.

The fields below intentionally overlap with Part 1's table — the header is the summary view, the table is the detail view. The duplication is by design.

```
> **Scenario**: <retention / repurchase / conversion / churn / renewal / custom>
> **Data source**: <TE project_id (project_name) ｜ event table `table_id` / uploaded file / aggregate-rate input>
> **Cohort event**: `<cohort_event>` ｜ **Outcome event**: `<outcome_event>`
> **Observation window**: N = <N> days (<exact-day / within-window>)
> **Cohort design**: `<first_occurrence / period_active / paired>` (<chosen via: user-specified / auto-inferred from "<phrasing>" / scenario default>)
```

**Format rules**:
- Each line starts with `> **<Key>**:`. Group two related fields on one line only when they form a natural pair (TE project + event table, cohort event + outcome event). For uploaded/aggregate mode, use the same Data source line without inventing project metadata.
- One field per line is fine if no natural pair exists (e.g., Observation window, Cohort design).
- Backticks around event names, design names, table IDs, and window-mode tokens; plain text for everything else.
- Cohort design line includes a parenthetical explaining how it was chosen (user-specified / auto-inferred from phrasing / scenario default). Drop the parenthetical only when the design was explicitly user-specified and unambiguous.

**Forbidden in the report header** (these are testing/debugging artifacts — if you need them for a test run, put them in a separate `test-log.md` alongside the report, never in the report itself):
- "Skill version" / "vX.Y test" markers
- `analyze.py` invocation mode (`test=auto` vs `test=z_independent` etc.)
- "This is a re-test of vX.Y" notes
- Comparison with prior runs
- Spec-implementation mismatch / bug findings

### Part 1: Data Overview

| Metric | Group A (pre) | Group B (post) |
|---|---|---|
| Time range | <A range> | <B range> |
| Cohort event | `<cohort_event>` | `<cohort_event>` |
| Outcome event | `<outcome_event>` | `<outcome_event>` |
| Observation window | N = <N> days (<exact-day / within-window>) | N = <N> days (<exact-day / within-window>) |
| Cohort design | <first_occurrence / period_active / paired> | <first_occurrence / period_active / paired> |
| Cohort users | <n_A> | <n_B> |
| Outcome users | <r_A> | <r_B> |
| <RATE_TYPE> | <p_A>% | <p_B>% |

For paired design: the **Cohort users** row in both columns should show `paired_n` (the matched sample = a+b+c+d), not `n_A_active`/`n_B_active` — putting per-period active counts in this row implies they are the McNemar sample, which is misleading. The **Outcome users** row should show the paired-subset marginal outcome counts: `r_A_paired = a + b` (paired users with A-period outcome=1), `r_B_paired = a + c` (paired users with B-period outcome=1). The `n_A_active` / `n_B_active` returned by the 2B-paired SQL are **per-period active cohort counts** (users who did the cohort event at least once in that period) and belong in Part 2 as background context (e.g., "paired_n = X out of n_A_active = Y, n_B_active = Z — paired sample represents X / min(Y, Z) ≈ P% of consistently-active users"), not in the Part 1 Cohort users row.
For paired design, also report: matched sample size (paired_n = a+b+c+d) = <paired_n> users — the same users observed in both periods; this is the McNemar sample, not an overlap-rate numerator.
For period_active design, also report: per-period active counts n_A / n_B and the cross-period overlap (users active in both A and B).

### Part 2: Independence Diagnosis

Use the field set that matches the design actually run.

**For `first_occurrence` / `period_active`:**
- Cohort design: <first_occurrence / period_active> (chosen via: <user-specified / auto-inferred from "<phrasing>" / scenario default>)
- Group A users: <n_A>
- Group B users: <n_B>
- Overlapping users: <k>  (for first_occurrence: 0 by design; for period_active: <overlap>, rate <overlap_rate>% → <low / moderate / high> independence violation level)
- Overlap rate: <overlap_rate>%
- Decision: <test name, and reason>

For `period_active`: if overlap_rate ≥ 30%, include the recommendation: "high overlap; consider rerunning with cohort_design=paired for a precise McNemar test on the same users."

**For `paired`:**
- Cohort design: `paired` (chosen via: <user-specified / auto-inferred from "<phrasing>" / scenario default / explicit same-run rerun / test-audit secondary path>)
- Matched sample users (`paired_n`): <a+b+c+d>
- Discordance cells: b = <b>, c = <c>
- Decision: McNemar matched-pairs test, because the same users are observed in both periods

Do **not** report `Group A users`, `Group B users`, `Overlapping users`, or `overlap_rate` as Part 2 fields for paired design. If you also want to provide the broader per-period active counts for context, put them in Part 5 as background context only, not as the paired design's Part 2 sample definition.

### Part 3: Statistical Test

Part 3 has one sub-section per design that was actually run. The primary design (chosen in Step 1 / auto-inferred) is always **3a**. A secondary design may appear in **3b** only when it was actually run **and** one of these is true: (a) the user explicitly asked for both views in the same deliverable; (b) the current task is a skill test / regression audit / spec verification; or (c) `analyze.py` emitted `recommended_rerun: "paired"` (period_active with overlap_rate ≥ 30%), which per the Step 4 period_active overlap rule triggers an auto-run of 2B-paired. In a normal user run with low overlap and none of these conditions met, do **not** include 3b — even when the report recommends rerunning with another design later.

#### Part 3a: Statistical Test — primary design (<design name>)

- Test method: <Z-test / McNemar / Fisher>
- Test statistic: <value>
- p-value: <value>
- 95% CI of difference: [<low>, <high>]  (for McNemar: paired Edwards-form CI of the marginal difference — `ci_95` field)
- Relative uplift: <value>%  (for McNemar: `(marginal_p_B - marginal_p_A) / marginal_p_A` — `relative_uplift` field)
- Effect size (Cohen's h): <value> (<negligible / small / medium / large>)  (for McNemar: computed on marginal proportions — `cohen_h` field)
- `analyze.py` JSON output `warnings` array (only if non-empty): paste each warning verbatim with a one-line plain-language gloss
- `analyze.py` JSON `srm_decision` (independent designs only): paste `decision` + `reason` verbatim
- **If the primary test is McNemar**: include the a/b/c/d discordance cell table here (same format as Part 3b's cell table below). A single-design paired run has no 3b, so the cell table must appear in 3a. Also report `marginal_p_A`, `marginal_p_B`, `observed_diff` (all returned by the script).
- **If the primary test is Fisher's exact** (small expected cell count fallback): the script auto-builds the 2×2 table from `group_A`/`group_B` for independent designs (`a=r_A, b=n_A-r_A, c=r_B, d=n_B-r_B`) — paste the four cell counts and the `odds_ratio` field returned by the script alongside the p-value, since Fisher's p without an effect-size estimate is hard to interpret. Fisher is **independent-samples only**. Never present a paired Fisher path. The script returns `marginal_p_A` / `marginal_p_B` for Fisher; use them to fill the Part 1 rate row and Part 2 difference row. Report `odds_ratio` with `odds_ratio_direction=B_vs_A`; if the ratio is null because of zero cells, say it is not finite/defined rather than reversing the direction silently.

#### Part 3b: Statistical Test — secondary design (<design name>)  *(omit if not run)*

Same field set as 3a. For McNemar, also include the a/b/c/d discordance cell table:

| Cell | Count | Meaning |
|---|---|---|
| a | <a> | outcome in both A and B |
| b | <b> | outcome in A only (discordant) |
| c | <c> | outcome in B only (discordant) |
| d | <d> | outcome in neither (discordant) |
| paired_n | <a+b+c+d> | matched sample size used by McNemar (= a+b+c+d) |

### Part 4: Conclusion

If only one design was run (single Part 3a):

- <Significant / Not significant> at α = 0.05
- One-line plain-language conclusion

If two designs were run (Part 3a + 3b), use a side-by-side comparison table followed by a one-line synthesis:

| Design | p_A | p_B | Difference | p-value | Conclusion (α=0.05) |
|---|---|---|---|---|---|
| <3a design> | <p_A> | <p_B> | <diff> | <p> | <A higher / B higher / not significant> |
| <3b design> | <p_A> | <p_B> | <diff> | <p> | <A higher / B higher / not significant> |

**One-line synthesis conclusion**: if the two designs agree in direction → state the shared conclusion; if they disagree → explicitly call out the discrepancy and attribute it to user-composition vs within-user-change (see Part 5 caveats). Do NOT paper over a discrepancy with a single conclusion.

### Part 5: Business Interpretation

Use the scenario-specific caveats from the **Scenario Presets** table:

- **Retention**: pair with 7-day/30-day retention, payment, LTV before declaring version success
- **Repurchase**: pair with AOV, repurchase cycle, LTV; check cohort bias (first-time vs returning buyers)
- **Conversion**: pair with funnel upstream/downstream metrics; check segment balance
- **Renewal**: pair with AOV, LTV, churn downstream; check subscription tier mix; the paired design captures only users active in both periods — new subscribers acquired during period B are excluded
- **Custom**: use the user-supplied caveats

Always include the caveat: significance ≠ business importance.

> **Confounding caveat (always include for pre/post designs).** This skill compares two **sequential time windows**, not concurrent randomized variants. A statistically significant difference does not by itself prove the version/campaign *caused* the change — anything else that varied between the two windows (seasonality, holidays, marketing spend, other concurrent feature releases, day-of-week composition if the windows don't cover matched full weeks, external events) is a possible alternative explanation. State this explicitly rather than implying causality from the test result alone. If group A and group B differ in length or don't both start on the same weekday, additionally flag: "day-of-week composition differs between periods; rates that vary by weekday may bias this comparison."

> **Paired-design survivorship caveat (always include for paired design).** The paired design includes only users who were active in **both** periods. This subset is not representative of the full user base — it skews toward more engaged, more loyal users. A significant change in this subset may not generalize to the broader population (new users, churned users, irregularly-active users). State this explicitly: "the paired sample reflects the consistently-active subset; effects on new or churned users are not captured."

> **Period_active-design independence caveat (always include for period_active design).** The period_active design treats A-period and B-period samples as independent, but users active in both periods are counted in both groups. The result reflects period-level rate differences, NOT within-user change. If the overlap rate is high (≥ 30%), the independence assumption is materially violated; recommend rerunning with `cohort_design=paired` for a precise McNemar test on the same users.

### Part 6: Power and Sample Size

- **For Z-test (independent)**: Minimum detectable difference at 80% power, current sample: <`mdd_80pct_power`> percentage points; observed difference: <`observed_diff`> percentage points. If observed < minimum detectable: "current sample insufficient to reach 80% power; need ~<`extra_needed_per_group`> more users per group".
- **For McNemar (paired)**: `mdd_80pct_power` and `n_needed_per_group` are `null` — McNemar power depends on the discordant-pair structure, not n alone. Instead report: effective sample = `n_discordant` = <b+c>; `discordant_pairs_needed_for_80pct` = <value> (the discordant count required to detect the observed asymmetry ψ = |b−c|/(b+c) at 80% power). If `n_discordant` < that value, note "current discordant count insufficient to reach 80% power for the observed asymmetry".
- **For Fisher exact**: this calculator does not provide exact Fisher power/MDD. State that exact power is not computed for this path; do not reuse the independent Z-test power fields. For future planning, choose a business-relevant minimum effect and calculate sample size with a method appropriate to the anticipated proportions.
- Recommended observation window or sample target

> **Post-hoc power caveat.** The "sample needed per group to detect the observed difference" is computed from the observed effect size, which is **post-hoc power**. Post-hoc power is statistically controversial — it is mathematically coupled to the p-value and conveys no new information beyond the CI. Use it only as a rough planning hint for **the next** experiment, not as evidence for the current one. For pre-experiment sample-size planning, base the calculation on the **minimum effect size the business cares about** (e.g., "we need to detect a 1pp drop"), not on the observed difference.

### Part 7: Charts

Embed the two `chart` code-fences produced in Step 7 directly here. Do **not** reference PNG paths — the chart code-fence is the rendered chart.

### Final language check (before saving)

Before writing `report.md` to disk, run this one-pass audit on the draft:

1. **User language**: re-read the user's most recent message. Identify its dominant language (Chinese / English / Japanese / …). The report's prose, table headers, caveat labels, conclusion line, and chart titles/axis labels MUST be in that language.
2. **Untranslated-English scan**: scan the draft for prose fragments, table headers, or caveat labels still in English when the user's language is not English. Allowed to stay in English: SQL identifiers (`#user_id`, `$part_date`, `$part_event`), event names (`login`, `register`), statistical terminology that has no clean translation in the user's language (`Z-test`, `McNemar`, `Fisher's exact`, `Cohen's h`, `p-value`, `CI`, `power`, `MDD`, `SRM`), and code fences.
3. **Fix or fail**: rewrite every offending fragment in the user's language. If after this scan any non-allowed English prose remains in a non-English report, you have not completed Step 7 — go back and rewrite.

This step exists because the first real-data test of this skill produced an English report for a Chinese-language question. The global **Response Language** rule above already mandates this; the check is here to enforce it at the point of file output.

### Test-log separation (when running end-to-end skill tests)

If you are running this skill as a **test** (regression check, version bump verification, spec-health audit), keep all testing artifacts out of the user-facing `report.md`. Testing artifacts include:

- "vX.Y fix verification" sections
- "key numbers summary" duplicating Part 1 + Part 3 numbers
- "comparison with prior run" tables
- "spec-implementation mismatch / new bug found" sections
- "Skill version" / "analyze.py invocation mode" notes in the report header

Save these in a separate `test-log.md` alongside `report.md` instead. The `report.md` file produced during a test must be byte-structure-identical to one produced during a normal user run — same 7 Parts, same header format, no extra sections. The only thing that differs in a test run is that a `test-log.md` also exists.
