---
name: cohort-retention-deep-dive
description: |-
  Diagnose why a product's retention curve rises, falls, or cliffs, and prioritize evidence-backed optimization hypotheses. Use for generic cross-vertical cohort or active-user retention diagnosis, including period-over-period changes, segment drag, inflection days, and behaviors associated with later retention.
  Do NOT use when: (1) retention numbers don't match event analysis -> retention-verification; (2) the user asks about new-user quality, acquisition-channel quality, or first-day behavior attribution -> new-user-analysis; (3) the user wants to create a retention metric or merge it into an event report -> retention-metric-to-event-report; (4) the user wants to define churned users or build a churn segment -> churn-define; (5) the diagnosis is scoped to level/chokepoint churn -> level-churn-analyzer; (6) the product is short drama -> drama-retention-analyzer; (7) the question is about repeat purchase behavior -> repeat-purchase-analysis.
---

# Cohort Retention Deep Dive

> One-liner: Explain why retention rises, falls, or cliffs at specific days or within specific segments, and rank the highest-leverage fixes.

## Core Capabilities

1. **Cohort Matrix Reading** - Distinguish "acquisition quality" (across-cohort) vs "product stickiness" (within-cohort) curve shapes
2. **Layered Attribution** - Slice retention by confirmed dimensions and separate same-window drag/lift from period-over-period rate and mix effects
3. **Inflection-Point Detection** - Locate the exact day(s) where retention cliffs, and map them to product beats (tutorial end, stamina exhaustion, first-pay window)
4. **Key-Behavior Correlation** - Identify which early behaviors (first 1-3 days) most strongly separate retained from churned users (Aha-moment candidates)
5. **Optimization Lever Ranking** - Output a prioritized list of "breakpoint x segment x behavior" fixes, hand off to ae-experiment-design for validation

---

## Boundary Routing (Read First)

This skill diagnoses **why retention is what it is**. It does not verify data correctness, build assets, or own vertical-specific diagnosis. Route accordingly:

| User is asking | Route to |
|----------------|----------|
| "Retention numbers don't match event analysis" | `retention-verification` |
| "Analyze new-user quality / acquisition channels / first-day behaviors" | `new-user-analysis` |
| "Create a retention metric / merge into event report" | `retention-metric-to-event-report` |
| "Define churned users / build a churn segment" | `churn-define` |
| "Which levels are users stuck at" | `level-churn-analyzer` |
| "Short drama retention by episode" | `drama-retention-analyzer` |
| "Repeat purchase / subscription renewal rate" | `repeat-purchase-analysis` |
| "Why does D3/D7/D30 drop, which segment drags it, what should we do" | **this skill** |

---

## Tool Priority

**ae-cli is the PRIMARY tool.** Use `ae-cli analysis adhoc run --model-type retention` for retention rates, counts, cohorts, and supported grouping. Use the event model only for event metrics, not to manufacture retention. Cross-event behavior cohorts that the retention model cannot express may use the SQL model after authorized table and column discovery. Before composing any command, read the matching reference under the `ae-analysis` skill directory; never guess command names, flags, `project_id`, event names, property names, table names, columns, or definition JSON.

Key conventions:

| Rule | Detail |
|------|--------|
| Ad-hoc entry | `ae-cli analysis adhoc run --model-type retention|event|sql ...` |
| Read before composing | The matching `ae-analysis` reference for every selected model, including SQL when needed |
| Discover metadata first | Never fabricate event/property names; use the analysis-meta / metadata commands to discover real ones |
| SQL discovery | Before SQL, use `analysis sql-table list` and `analysis sql-table columns` with `usage=analysis`; use only returned table and column names |
| Wrap JSON in single quotes | `'{"mode":"custom","start_time":"...","end_time":"..."}'` |
| Timezone | Confirm the project timezone before analysis; pass `--zone-offset` to execution or omit to use the project default |

A connected analysis connector is FALLBACK ONLY: use it when ae-cli has no matching command or repeatedly fails for non-parameter reasons.

---

## Interaction Flow

0. **Align the retention definition first** - Every project defines "active", "return", and "N-day retention" differently. Before composing any query, confirm and record the five definition items in `references/interaction_flow.md` Step 0: active/return events, dedup dimension, bounded vs unbounded, day-0 offset, and cohort-entry definition. If the user quotes a figure from an existing dashboard, reconcile your computed number against it before diagnosing.
1. **Define scope** - Product type (game / app / e-commerce / content), cohort or active-user retention model, and target metrics (D1 / D7 / D30, or custom N-day). Route explicitly new-user-quality, acquisition-channel, and first-day-behavior requests to `new-user-analysis`.
2. **Collect parameters** - `project_id`, time range, and a provisional churn definition if layering needs it
3. **Event & property discovery** - Confirm the events that define "active/return" and the candidate key-behavior events + segment properties
4. **Diagnose** - Run the methodology below and produce the report
5. **Hand off** - Route verification of any proposed fix to `ae-experiment-design`

Reference: `references/interaction_flow.md`

---

## Analysis Methodology

Start with Module 1, then run only the modules needed for the user's question. Module 2 is required for segment or period attribution; Module 3 for curve cliffs; Module 4 for behavior-association questions; Module 5 only when at least one preceding diagnostic module produced a supported candidate.

### 1. Cohort Matrix Reading (shape first)

Pull the retention model as a cohort matrix and classify the curve shape:

| Shape | Meaning | Next move |
|-------|---------|-----------|
| Steep across-cohort drop, flat within-cohort | **Acquisition quality** problem (new users are low-fit) | Layer by channel / campaign / creatives |
| Flat across-cohort, steep within-cohort drop | **Product stickiness** problem (users leave after onboarding) | Inflection-point + key-behavior modules |
| Uniform cliff at a specific day N | **Scheduled churn** (tutorial end, stamina, paywall, subscription trial) | Map day N to product beats |
| Gradual decay with no cliff | **Engagement ceiling** (weak loop) | Key-behavior + content/feature cadence |

Industry reference ranges (new-user retention; context only):

| Vertical | Reference D1 | Reference D7 |
|----------|--------------|--------------|
| Hyper-casual game | 30-40% | 10-15% |
| Mid-core game | 40-50% | 15-20% |
| Content / streaming | 30-40% | 15-25% |
| E-commerce (D7 return) | - | 15-25% |

These ranges are orientation references, not universal healthy thresholds or diagnosis gates. Prefer a user-approved target, a comparable historical period, or a confirmed internal benchmark. Never infer a cause or assign confidence from an external reference range alone.

### 2. Layered Attribution (who drags it)

Choose the calculation that matches the question; do not call both calculations "change attribution":

1. Slice retention by each candidate dimension: channel, version, device, new-vs-old, pay status, geo
2. For a single window, compute each slice's weighted **drag/lift versus the overall rate**. These values sum to zero and rank below- or above-baseline slices; they do not explain a period change.
3. For period-over-period questions, decompose the total change into the **within-slice rate effect** and **mix effect** using both periods' rates and denominator shares.
4. Rank material effects only after checking sample size and ensuring the slices are mutually exclusive and exhaustive.

Guardrail: a tiny segment with terrible retention often matters less than a huge segment with slightly-below-average retention. Always multiply by size.

### 3. Inflection-Point Detection (where it breaks)

1. Plot per-day retention drop rate (D1->D2, D2->D3, ... Dn->Dn+1)
2. Flag days where a positive drop exceeds both a robust relative threshold (for example, 1.5x the positive-drop median) and an agreed materiality floor. If the median is zero or unstable, use a percentile/MAD rule and label it as a heuristic.
3. Map flagged days to product beats: tutorial end, stamina/ticket exhaustion, first-pay prompt, level difficulty ramp, session-length limit
4. For each flagged day, label the hypothesized beat and confidence

### 4. Key-Behavior Correlation (what to amplify)

Identify Aha-moment candidates:

1. Agree the candidate behavior set with the user; do not self-select behaviors from names alone.
2. Define an exposure window that ends before the outcome window. Do not use a behavior that requires surviving into the measured outcome as a predictor of that same outcome.
3. Use retention grouping/filtering when the confirmed definition can express the cohort. Otherwise use read-only SQL after table/column discovery to build mutually exclusive exposed/non-exposed cohorts; do not create a tag or cluster without explicit approval.
4. For each behavior, compute later retention for eligible users who did vs did not perform it
5. Report the observed **association lift** and coverage. Rank only as a prioritization signal, not as causal impact.

Caveat: correlation is not causation. Present findings as candidates and route validation to `ae-experiment-design`.

### 5. Optimization Lever Ranking (what to do first)

Combine the above into a ranked table. Each row:

```
| Rank | Breakpoint day | Segment | Behavior | Opportunity index | Confidence |
```

Before an experiment, report an **opportunity index** based on affected eligible users, observed association lift, and coverage; do not label it expected causal impact. After an experiment supplies a causal effect estimate, expected incremental retained users may be estimated as eligible unexposed users x causal uplift. Confidence follows the inference rules below.

Reference: `references/methodology.md`, `references/metrics.md`

---

## Root Cause Inference Rules

Data patterns are heuristics, not proven causes. State confidence and always offer an experiment as validation.

| Data characteristic | Inferred cause | Threshold | Confidence |
|---------------------|----------------|-----------|------------|
| Across-cohort drop, within-cohort flat | Acquisition-mix or cohort-quality hypothesis | clear shape split; route explicitly new-user diagnosis to `new-user-analysis` | Medium |
| Cliff at day N matching a confirmed beat | Scheduled-churn hypothesis | beat exists at N and timing is confirmed | Medium |
| D1 low across all channels | Onboarding-friction hypothesis | below a user-approved benchmark; validate the first-session funnel | Medium |
| Retention drop concentrated in one segment | Segment-specific change | period decomposition attributes >50% of the total change and sample is sufficient | Medium |
| High association lift with low coverage | Aha-moment candidate | association lift >20pp, coverage <30% | Medium |
| Gradual decay, no cliff, no segment concentration | Weak engagement loop | all shapes flat | Medium |
| Drop only in a small segment | Segment-specific issue | material effect but limited denominator share | Low (small sample) |

Sample-size guard: for any slice with n < 100, downgrade confidence one level; n < 50, do not classify, flag for more data.

Limitations: correlation is not causation; thresholds are heuristics adjusted per vertical; external factors (events, updates, competitor actions) may not be captured. Always recommend validation.

---

## Report Output Requirements

1. **Must include**: curve-shape diagnosis plus only the modules required by the user's question. Do not emit empty or unsupported attribution, inflection, behavior, or lever sections.
2. **Must state confidence** on every inference, and flag small-sample slices
3. **Actionable**: every recommendation names the specific segment, behavior, and expected direction
4. **Must end** with the standard next-step menu below

### Standard Report Ending Format

```markdown
---

**📋 Analysis Complete - Choose Next Step:**

**1. Deep dive a segment**
   → Reply: `Analyze the {channel/version/cohort} segment in detail`

**2. Validate a lever with an experiment**
   → Reply: `Design an experiment for the {behavior} nudge`

**3. Compare periods**
   → Reply: `Compare retention {Period A} vs {Period B}`

**4. End analysis**
   → Reply: `End`

---
```

---

## References

| Topic | File |
|-------|------|
| Interaction flow | `references/interaction_flow.md` |
| Methodology detail | `references/methodology.md` |
| Metric formulas | `references/metrics.md` |
| Recommendation library | `references/recommendations.md` |
| Report template | `references/report_template.md` |

## Language Constraint

All output to the user must be in the user's language (default English; match the user's language when they write in another language).
