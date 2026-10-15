---
name: ae-drama-creative-evaluation
description: Evaluate and diagnose the placement performance of short-drama ad creatives. Use when short-drama, mini-drama, web novel/comic drama and other content-type customers ask questions such as "how to evaluate creative quality", "which creative is worth scaling up", "why is CTR high but payment poor", "analyze creative tags, channels, audiences, lifecycle, ROAS/LTV", or when they need a creative analysis report based on ThinkingData/ThinkingEngine(AE) data. First verify the feasibility of ad platform data, attribution fields, and in-product events (graded A/B/C/D) via ae-cli, then break down creative, channel, and product conversion issues by attraction efficiency, acquisition efficiency, and value efficiency. Supports IAP, subscription, IAA, and hybrid monetization. Do not use for pure tracking-plan design, placement strategy without AE data, or report/dashboard-only creation without business diagnosis.
---

# Short-drama Creative Placement Performance Evaluation

Link the pre-conversion ad funnel and post-activation behavior through a unified creative ID. First use ae-cli to verify how deep the data can go, then distinguish creative appeal, channel traffic quality, and product conversion capability, and finally answer "which type of creative is worth scaling up, where the problem lies, and what to change next".

## Scope of Responsibility

This Skill does only one thing: **evaluate the comprehensive performance of short-drama creatives under specific placement conditions, diagnose the primary source of problems, and output an actionable analysis report.**

Two concepts must be distinguished:
- **Creative quality itself**: the impact of creativity, plot hooks, characters, cover, copywriting, editing pace, and other factors on user attention and click willingness.
- **Comprehensive placement performance**: the combined result of creative x channel x target audience x bidding strategy x landing page x product content x payment mechanism.

Do not equate high CTR directly with a good creative, and do not attribute all low ROAS to the creative. Unless a strict experimental design exists, all root-cause judgments are **evidence-based diagnostic inferences, not causal proof**.

**In scope**: requirement clarification, data feasibility verification, metric caliber design, ae-cli data retrieval, creative/channel/audience/tag/lifecycle analysis, diagnostic inference, report output.

**Out of scope**:
- Configuring placements or auto-bidding on behalf of the ad platform;
- Fabricating a complete pre-conversion funnel when ad impressions, clicks, and spend data are missing;
- Claiming a strict user-level "impression to click to payment" funnel when user-level impression/click logs are absent;
- Describing correlation as confirmed causation;
- Creating or modifying online dashboards, clusters, or tags without user confirmation.

## Trigger Scenarios

Trigger when any of the following is met:
- The user asks to evaluate the quality, placement performance, or value of short-drama ad creatives;
- The user asks why a creative has high CTR but poor activation, payment, or retention;
- The user wants to compare creatives, creativity, drama titles, genres, plot hooks, actors, editing templates, creative versions, or placement batches;
- The user wants to identify viral high-value, viral low-value, low-volume high-value, or fatigued creatives;
- The user wants to analyze viewing, payment, retention, LTV, ROAS, or ad monetization of users sourced from creatives;
- The user asks to build a creative analysis framework, report, dashboard, or alerting plan on the Shushu system.

Do not take over: pure tracking-plan design goes to the tracking plan Skill; pure placement strategy with no Shushu data need goes to the placement operations Skill; only creating reports/dashboards without business diagnosis goes to the AE analysis building Skill.

## Execution Steps (9 steps, do not skip)

### Step 1: Identify the analysis task and decision problem

| Task Type | Core Question | Default Output |
|---|---|---|
| Single-creative diagnosis | Why does this creative perform well upfront then drop, or fail to gain volume? | Three-stage funnel + control creatives + root-cause inference |
| Creative cross-evaluation | Which creatives are worth scaling, optimizing, or pausing? | Scorecard + tiering matrix |
| Tag pattern | Which genres, hooks, actors, or templates are more effective? | Tag cross-analysis + replicable patterns |
| Channel fit | Why does the same creative perform differently across channels? | Creative x channel comparison |
| Lifecycle | When does a creative enter fatigue or decline? | Days-since-launch trend + fatigue alert |
| Early prediction | Can new creatives be valued at T+0/T+1? | Correlation between early behavior and mature value |
| System building | How to evaluate creatives on Shushu long-term? | Data pipeline, metric system, dashboard, and rollout roadmap |

If the user has already specified the goal, do not re-ask; when information is insufficient, ask for all missing items at once instead of scattered multi-round questioning.

### Step 2: Confirm minimum input

Confirm before data retrieval: (1) Shushu project_id; (2) analysis target (creative ID/batch/tag/all); (3) time range and maturity window; (4) business model (IAP/subscription/IAA/hybrid); (5) channel scope; (6) attribution caliber; (7) primary decision. If the user cannot provide everything, first enter data exploration, and **do not require the user to provide event names and field names that ae-cli can look up**.

### Step 3: Environment and project precheck (automated)

```bash
scripts/precheck.sh <PROJECT_ID>                                      # version/auth/dashboard/report/authorized SQL tables
scripts/metadata_scan.sh <PROJECT_ID> <AUTHORIZED_EVENT_TABLE_REF>     # complete metadata export, cross-validated against SQL-tested event list
```

- First confirm CLI availability and valid auth; if unauthorized, stop data retrieval and clearly state "only analysis design can be output, not real data conclusions". Do not auto-install, do not guess login state, do not pass off sample data as real data.
- After finding candidate reports, verify the caliber with `ae-cli analysis report get`; reuse only when the caliber matches.
- **The metadata API defaults to 50 items per page and may lag**, so it must be pulled in full via pagination and cross-validated against the SQL-tested event list (see references/metrics-caliber.md).

### Step 4: Determine data feasibility level + confirmation gate (mandatory)

Follow references/feasibility-checklist.md to complete the five-layer check (ad platform aggregation layer / attribution layer / product behavior layer / IAA monetization layer / creative dimension-table layer), determine the A/B/C/D level, and verify the 8 high-frequency issues item by item.

**Confirmation gate (mandatory)**: fill in assets/confirm-card-template.md, present it to the user, and **stop to wait for confirmation** (use AskUserQuestion when available), covering: (1) whether field mapping is accurate (creative ID, revenue, cost, channel, and other key fields are correctly selected); (2) whether the feasibility level is accepted; (3) whether there are missing fields / existing reports / established calibers. If the user corrects fields, go back to Step 3 to re-verify and re-present the confirmation card. **Do not proceed to formal data retrieval or output conclusions before the user confirms.**

### Step 5: Unify calibers and observation windows

See references/metrics-caliber.md for caliber definitions and window rules. Output the caliber list first for user confirmation; if the user has given an explicit caliber, just restate and confirm without re-asking. Data from different maturity windows must not be mixed; immature cohorts must be labeled "under observation".

### Step 6: Design controls and sample thresholds

Preferred controls: cross-evaluation of creatives in the same channel/audience/stage; the same creative across channels; different versions of the same genre/hook; the same creative aligned by days-since-launch; prefer A/B experiments when random split-flow is available. Set a minimum sample threshold before querying: if the user has not provided one, recommend based on the project distribution, and at minimum check impressions, clicks, activations, paying users, spend, and maturity days simultaneously. When the sample is insufficient, only output "directional signals".

### Step 7: ae-cli data retrieval (templates verified)

Retrieval order: **existing reports -> standard analysis models -> SQL fallback**.

```bash
scripts/scorecard_query.sh <PROJECT_ID> <INSTALL_START> <template name> <AUTHORIZED_EVENT_TABLE_REF>
# Templates under assets/sql/: scorecard (main scorecard) / ad_channel (creative x channel) / lifecycle_week (lifecycle) / paystruct (payment structure) / content_pref (genre preference)
```

- For SQL rules and the verified pitfall list, see references/metrics-caliber.md (including boolean fields, failed-order amounts, multi-event revenue mounting, virtual properties, `$part_date` type, etc. — must read before retrieval).
- Use the exact `table_ref` returned by `ae-cli analysis sql-table list --project-id <PROJECT_ID> --usage analysis`; do not construct `v_event_<PROJECT_ID>` locally.
- For each result, record the project, time, filter conditions, group-by dimensions, metric definitions, and data source.
- When only ad aggregation data exists, use "two-layer analysis" (ad-layer aggregation + user-layer attribution + unified creative ID join), and do not pass off aggregated impressions/clicks as a user-level funnel.

### Step 8: Three-stage diagnosis and business decisions

Execute per references/diagnosis-framework.md: first diagnose (attraction efficiency / acquisition efficiency / value efficiency three stages), label evidence strength (high/medium/low, without using the term "confidence"), then classify business category (viral high-value / viral low-value / low-volume high-value / low-volume low-value). T+0/T+1 can only serve as predictive metrics; the correlation must first be validated against historically mature creatives.

### Step 9: Output report

By default, output the structured report directly in the conversation; see assets/report-template.md for the template, and references/report-standard.md for structure and quality standards. Generate the corresponding deliverable (document/table/dashboard) only when the user explicitly requests it. The report uses business language the customer can understand, does not expose internal prompts or tool-call details, and only explains the data source in the "Data Scope and Caliber" section.

## Output Standards

1. **Conclusion first**: answer the business decision on the first screen, not pile up background first;
2. **No comparison, no conclusion**: include at least one of same-condition creative, channel, time, or version comparison;
3. **Distinguish three responsibilities**: creative appeal, channel/landing-page acquisition, and product/content conversion judged separately;
4. **Metrics carry windows**: revenue, LTV, and ROAS must state D0/D1/D3/D7/L30;
5. **Cover all revenue**: hybrid monetization customers must include IAP, subscription, and IAA simultaneously;
6. **Show sample maturity**: label under-observation, decidable, and declined;
7. **Honestly state limitations**: aggregated data, missing fields, attribution bias, and insufficient samples must be disclosed;
8. **Verifiable recommendations**: each recommendation states the verification metric and observation window;
9. **Do not manufacture causation**: use "shows, supports, suggests, may", avoid "proves, inevitably leads to";
10. **Do not fabricate data**: use "not connected / unavailable" for data not retrieved, and do not fill formal reports with example numbers; randomly simulated fields (e.g., `random()` virtual properties) are forbidden in conclusions.

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
