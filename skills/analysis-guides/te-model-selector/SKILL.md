---
name: te-model-selector
description: Recommend the most suitable AE (AgenticEngine) analysis model from 12 models and generate its configuration. Use when users are unsure which analysis model to choose, ask "which model to use / which one should I choose", ask whether a model fits a scenario (e.g. "can retention analysis do this"), ask which model to use for LTV / ROI / revenue, or want configuration guidance for a chosen model — with precise field mapping when a project is available, or a generic-example configuration for consultation when no project is provided. Do not use for simple data queries, executing a specific investigation, writing SQL/code, or configuring a model whose name is already known (route those to ae-analysis).
---

# AE Model Selection & Configuration Assistant

Based on user's data analysis requirements, intelligently recommend the most suitable AE (AgenticEngine) analysis model, and combine with actual tracking data dictionary to provide step-by-step configuration guide with precise event and property mapping.

---

## 🎯 Trigger Rules Details (Agent Must Read)

### Strong Trigger Conditions (Force trigger if any one matches)
- **Model selection question words**: "which model to use", "what model", "which one should I choose", "recommend a model", "which model should I use"
- **Model comparison hesitation**: "should I use event analysis or XX analysis", "don't know whether to use retention or funnel", "which analysis to use"
- **Configuration inquiry**: "how to configure this requirement best", "how to configure", "how should I configure"
- **Explicit model consultation**: Mentions specific model name + seeks advice (e.g., "can retention analysis do this", "is funnel suitable for this requirement")

**⚠️ Judgment Principle**: Whenever user expresses doubt or hesitation about "which model to choose", this Skill should be triggered.
**⚠️ Boundary Note**: This Skill only solves "select model + provide configuration method", and does not execute setup operations. Route execution requests such as "help me set up" or "help me configure" to the `ae-analysis` Skill, which uses current ae-cli commands.

### Exclusion Conditions (Never trigger)
1. Simple data query requests (no model selection keywords): "check XX data", "help me check XX", "statistics XX", "view XX metric" → Do not trigger
2. Explicit commands to execute specific business investigation (e.g., "check game inflation", "check High Spender profile") → Hand to business Skill
3. Direct requests to write code (e.g., "help me write SQL") → Hand to SQL/code Skill
4. Explicit requests to design tracking schema → Hand to tracking design Skill
5. Execution requests (e.g., "help me set up", "help me configure", "create a retention analysis") → Hand to `ae-analysis` for ae-cli execution; this Skill only provides configuration guidance
6. Configuration requests with known model name (e.g., "help me configure retention analysis") → If no selection hesitation, hand to `ae-analysis`

### Key Distinction Examples
| User Expression | Trigger? | Reason |
|---------|---------|------|
| "Help me check payment data" | ❌ No trigger | Pure data query, no model selection request |
| "Which model to analyze payment data" | ✅ Trigger | Has model selection intent |
| "DAU for last 7 days" | ❌ No trigger | Clear metric, no selection request |
| "Which model to analyze DAU and MAU" | ✅ Trigger | Has selection question |
| "Help me set up a retention analysis" | ❌ No trigger | Execution request, hand to `ae-analysis` |
| "How to configure retention analysis?" | ✅ Trigger | Configuration inquiry, not execution request |

---

# 🔄 Core Workflow

> ⚠️ **Requirement**: Phase 1 (metadata resolution) is required only for a *precise* configuration bound to real fields. **Model selection itself does not require a projectId** — the decision tree can always run. When no project is available or the user only wants model selection, proceed in consultation mode (generic-example configuration).

### 🚫 Prohibited Actions
- ❌ Do not fabricate real event/property names as if verified. Without project metadata, use `[to-replace: xxx]` placeholders and label them as examples, never as the project's actual fields
- ❌ Do not guess or fabricate event names/property names (e.g., writing "payment" as `pay_event` without verification)
- ❌ Do not refuse or block model-selection consultation just because no projectId was provided — offer project candidates via `ae-cli team +list-projects`, and if the user declines, proceed in consultation mode

---

## Phase 1: Metadata Query & Field Mapping【Required only for precise configuration】

### 1.1 Confirm projectId
- **If the user provided a projectId** → use it directly, go to 1.2 for field resolution.
- **If the user did NOT provide a projectId** → do NOT hard-ask. Instead:
  1. Run `ae-cli team +list-projects` to fetch the projects the current user can access.
  2. Present the choices via **AskUserQuestion**. The picker shows at most 4 options, so take the **first 3 projects** as candidates plus a fixed trailing option **"No project needed — consultation only"** (3 projects + 1 fixed option = 4). If fewer than 3 projects are available, list the actual number plus the trailing "No project needed" option. If more than 3 projects exist, tell the user only the first 3 are shown and they may reply with a specific projectId instead. If the list is empty (no accessible project), skip the picker and go straight to consultation mode.
  3. Based on the user's choice:
     - **Picks a specific project** → take its projectId, go to 1.2 for field resolution (precise mode).
     - **Picks "No project needed — consultation only"** → skip 1.2, go straight to Phase 2. In the configuration template, fill every event/property field with a `[to-replace: xxx]` placeholder, and note in the output that this is **consultation mode — project fields not verified**; providing a projectId later yields a precise configuration (see 2.3 Case D).

- **Branch contract**:
  - Picks a project → must complete 1.2 field resolution before Phase 2.
  - Picks "consultation only" → skip 1.2, go to Phase 2 and handle via 2.3 Case D.

### 1.2 Resolve Tracking Fields

For non-SQL analysis models, submit the semantic AI-facing definition first and
inspect `meta.resolved`, `meta.warnings`, and structured errors. Only after
clarification or an explicit resolution capability error, call:

```
ae-cli analysis-meta event list --project-id <id>       → Get event candidates
ae-cli analysis-meta property list --project-id <id>    → Get property candidates
ae-cli analysis user-tag list --project-id <id>         → Get user tags (optional)
ae-cli analysis user-cluster list --project-id <id>     → Get user clusters (optional)
```

#### Data Type Explanation
After querying, clearly distinguish these three data types:

| Type | Description | Example |
|------|------|------|
| **Event** | User's specific behavior | register, login, payment |
| **Event Property** | Describes specific context or value of event occurrence | pay_amount, channel |
| **User Property/Tag/Cluster** | User's own static characteristics | vip_level, total_pay_amount |

### 1.3 Field Mapping Principles
- **Exact match first**: User says "payment amount", first search properties whose propDesc contains "payment amount"
- **Ambiguity must confirm**: When event property and user property have same name/description, **must ask user which one to use**
- **Not found then explain**: If no matching event or property in project, clearly inform user and suggest supplementing tracking

---

## Phase 2: Model Determination & Configuration Generation

### 2.1 Determine Model via Decision Tree
Select the most suitable analysis model according to 【Model Decision Tree】and【AE Analysis Model System Introduction】below

### 2.2 Generate Configuration (Based on Real Fields)
After determination, output recommended model in specified format, and output configuration suggestions according to【Model Configuration Methods】.
- Fill **mapped real fields** into configuration template
- Check if required fields are complete


#### 📋 Output Format

```
## 📊 Recommended Model: [Model English Name] ([Model Identifier])

### 💡 Recommendation Reason
Concisely explain why this model was chosen, pointing out which decision rule was matched.

### 🛠️ Configuration Suggestions in AE
**(Agent Internal Instruction: Please strictly follow the structure below, converting natural language requirements to underlying fields and calculation logic. Output fields in format "Display Name (Identifier)")**
Based on the determined model, output using the configuration template below according to different model configuration methods.

**Configuration Template**: (Using event model as example, adjust dynamically based on different model configuration methods)

| **Configuration Item** | **Selection** |
| :--- | :--- |
| **Select Event** | Login (login) |
| **Calculation Method** | Triggering User Count |
| **Group By** | Channel (channel) |
| **Time Range** | Last 7 days |
| **Time Granularity** | By Day (optional, view daily trend) or Total |
| …… | …… |

### 🔄 Alternative Solution** (If applicable):
[Explain under what conditions should switch to alternative model]

### ⚠️ Notes:
[Point out common pitfalls for this scenario, or tracking data definition issues to note (e.g.: payment amount doesn't include gift portion)]
```

---

### 2.3 Exception Handling Mechanism

#### Case A: Field Missing
**Detection**: Required field for configuration doesn't exist in metadata
**Handling**:
1. Prompt user: `Current project lacks [field name], cannot complete configuration`
2. Provide alternatives:
   - Recommend similar field substitution
   - Suggest supplementing tracking (provide tracking design suggestion)
   - Suggest creating virtual property/user tag/user cluster

**Example**:
```
❌ Missing field: User Level (user_level)
✅ Alternatives:
  1. Use existing field vip_level as substitute
  2. Or create user tag: classify levels based on total payment amount
  3. Or supplement tracking: add user_level in user properties
```

#### Case B: Model Capability Boundary
**Detection**: User requirement exceeds selected model's capability range
**Handling**:
1. Explain model limitations
2. Provide SQL alternative (based on Trino syntax)

**Example**:
```
⚠️ Model limitation: Retention analysis cannot support hourly granularity statistics
✅ SQL Alternative:
SELECT
  date_trunc('hour', "$part_time") AS hour,
  COUNT(DISTINCT "#user_id") AS user_count
FROM ta.v_event_1
WHERE "$part_event" = 'login'
  AND "$part_date" >= '2024-01-01'
GROUP BY 1
ORDER BY 1
```
**Field Explanation**:
- `"$part_date"`: Partition date
- `"$part_event"`: Event name
- `"#user_id"`: User ID
- `"[real_property_name]"`: [property description]

#### Case C: Requires Pre-data Preparation
**Detection**: Configuration needs user tag/cluster/virtual property but not yet created
**Handling**:
1. Prompt user to create pre-data first
2. Provide creation steps and configuration suggestions

**Example**:
```
⚠️ Requires pre-preparation: High Value User Cluster
✅ Creation Steps:
  1. Go to AE → User Clusters → New Cluster
  2. Filter condition: Total payment amount >= 1000
  3. Save as "High Value Users"
  4. Use this cluster for comparison in event analysis
```

#### Case D: Consultation Mode (user chose "No project needed" in 1.1)
**Detection**: In 1.1 the user picked "No project needed — consultation only" (or no accessible project exists).
**Handling**:
1. Do NOT trigger 1.2 field resolution.
2. Still run the full decision tree and give the model recommendation + reasoning normally.
3. In the configuration template, fill every event / property field with a `[to-replace: xxx]` placeholder (e.g., `[to-replace: register event]`, `[to-replace: channel property]`).
4. In Notes, state that this is consultation mode — project fields are NOT verified — and that providing a projectId (or picking a project) enables the precise Case A / B flow with real field mapping.

**Example**:
```
ℹ️ Consultation mode — no project queried, fields not verified
- Select Event: [to-replace: registration event, e.g. register]
- Calculation Method: Triggering User Count
- Group By (optional): [to-replace: channel property, e.g. channel]
⚠️ To map real fields, provide a projectId and I'll switch to precise configuration
```

---

## AE Analysis Model System Introduction (12 Models Total)

### 1. Event Analysis (event) — Default/Most Common Model

**Core Positioning**: Perform metric statistics and trend observation on single behavior event. Most basic and core analysis model. When no clear signal points to other models, default to event analysis.

**Supported Aggregation Metrics**: Total Count, Triggering User Count (DAU/MAU), Per User Count, Cumulative Value (e.g., total revenue), Maximum/Minimum, Distinct Count, Average Per User, Average, Formula Metric (custom formula combining multiple metrics)

**Core Functions**:
- Support viewing multiple metrics simultaneously
- Support dimension grouping comparison (e.g., by channel, region, device type)
- Support multi-date comparison
- Support filter conditions (event property, user property filter)

**Strong Signal Keywords**: DAU, MAU, user count, count, amount, revenue, quantity, total, sum, statistics, query, calculation, trend, report, dashboard, payment rate (when appearing alone), first-day payment rate, active, new user, register, login, payment, revenue, ARPU, ARPPU, average per user

**Typical Questions**: DAU for last 7 days / Query revenue for last 30 days / Paying user count by different channels / ARPU analysis / Help generate dashboard for register count, login count, payment amount for last 7 days

---

### 2. Retention Analysis (retention) — Second Most Common Model

**Core Positioning**: Analyze revisit behavior of users who completed initial event in subsequent time periods. Quantify user retention and churn, measure product health. Also the carrier for LTV and ROI calculation.

**Core Concepts**:
- **Initial Event**: User's "starting" behavior (e.g., register, first login)
- **Return Event**: User's "revisit" behavior (e.g., re-login, re-payment)
- **Retention Rate**: Proportion of users revisiting on day N/week/month relative to initial users

**Retention Types**: N-day retention, N-week/N-month retention, unbounded retention, custom retention

**Extended Functions**: Can display LTV / ROI as an add-on on the retention curve. ⚠️ When LTV / ROI / payment revenue is the primary analysis goal, use the **revenue** model instead (see Model 12).

**Strong Signal Keywords**: retention, retention rate, churn, churn rate, churned users, churned count, next-day retention, N-day retention, revisit, decay, day-1 retention, day-3 retention, day-7 retention (note: LTV / ROI now route to the revenue model by default — see Model 12)

**⚠️ Core Rule: churn is always retention. LTV / ROI / payment rate now default to the revenue model (the dedicated cohort revenue & cost-recovery model); use retention for LTV/ROI only when the user explicitly wants them as an add-on on a retention curve.**

**Typical Questions**: Query user retention this month / LTV for last 7 days / 7-day ROI for last 10 days / 7-day churned users / 30-day retention for paying users

---

### 3. Funnel Analysis (funnel)

**Core Positioning**: Analyze conversion and loss at each step in multi-step process, find optimization direction.

**Core Configuration**: Supports up to 30 steps, window period 1 minute~180 days, supports ordered/unordered funnel.

**Strong Signal Keywords**: funnel, funnel analysis, conversion (multi-step context), first...then..., A→B→C, penetration rate, conversion rate (multi-step context)

**⚠️ Key Distinction**:
- "Payment rate" appearing alone → **event** (single metric)
- "First-day payment rate" → **event** (single calculated metric)
- "Penetration rate" → **funnel** (implies A to B conversion process)
- "First A then B" + no other model keywords → **funnel**
- "First A then B" + "retention" → **retention** (explicit model keyword priority)

**Typical Questions**: Funnel conversion from login to draw card to payment / Generate registration→login→payment conversion by channel / New user first-day payment penetration

---

### 4. Interval Analysis (interval)

**Core Positioning**: Analyze time interval distribution between two causally related events. Answer "how long it takes users to complete two things".

**Core Metrics**: Median, Average, Percentile (P75/P90), Duration Distribution

**Strong Signal Keywords**: interval, interval analysis, interval time, interval distribution ("interval" is strongest signal, almost 100% match)

**⚠️ Distinction from Funnel**: Funnel focuses on "how many people converted", interval analysis focuses on "how long conversion took".

**Typical Questions**: First payment interval distribution / Interval from level up to payment / Login interval for last month

---

### 5. Distribution Analysis (distribution/scatter)

**Core Positioning**: Divide metric values into intervals, get user count and proportion in each interval. Analyze user engagement depth and stickiness for specific feature.

**Distribution Dimensions**: By count distribution, by day distribution, by numeric property distribution

**Strong Signal Keywords**: distribution, distribution situation, distribution analysis, user distribution ("distribution" is almost decisive signal)

**⚠️ Distinction from Event Analysis**:
- "Payment amount trend" → **event** (time series aggregation)
- "Payment amount distribution" → **distribution** (user-level distribution)
- "Daily XX distribution" → **distribution** ("distribution" priority > "daily")

**Typical Questions**: User login count distribution / Payment amount distribution / Active days distribution / Payment count distribution trend

---

### 6. Path Analysis (path)

**Core Positioning**: Explore user behavior trajectory, generate Sankey Diagram, intuitively display behavior inflow/outflow. Suitable for discovering "unexpected behavior patterns".

**Analysis Direction**: Forward path (what did after certain event), Backward path (what did before certain event), Full path

**Strong Signal Keywords**: path, path analysis, behavior trajectory, Sankey diagram, inflow/outflow, user path, what did

**Typical Questions**: What users do after entering game / Behavior before churned users leave / Behavior path before payment

---

### 7. Composition Analysis (composition)

**Core Positioning**: Profile analysis based on user properties (not behavior events), supports dual-dimension cross analysis and crowd comparison. Answer "who are the users/what do users look like".

**Strong Signal Keywords**: composition analysis, user profile, property distribution (when analyzing static user properties rather than behavior metrics)

**⚠️ Distinction from Distribution Analysis**:
- **Composition Analysis**: Analyzes static user property (level, region, device type) distribution
- **Distribution Analysis**: Analyzes behavior metric (payment count, login count, payment amount) distribution among users

**Typical Questions**: User region distribution / Age group and device brand distribution for paying users / Profile difference between VIP users and normal users

---

### 8. Attribution Analysis (attribution)

**Core Positioning**: Evaluate contribution degree of multiple touchpoints/channels to conversion target. Supports last touch, first touch, linear, position decay, time decay attribution models.

**Strong Signal Keywords**: attribution, attribution analysis, touchpoint contribution, channel contribution, contribution degree, which touchpoint, which ad slot contributes most

**⚠️ Distinction from Funnel Analysis**: Funnel looks at conversion rate of one fixed process, attribution analysis looks at contribution degree of each touchpoint in multiple paths.

**Typical Questions**: Which ad slot contributes most to payment conversion / Promotion channel contribution evaluation / Impact of multiple popups on conversion

---

### 9. Ranking (rank)

**Core Positioning**: Rank dimensions by metric value size, display Top N leaderboard, can track ranking change.

**Strong Signal Keywords**: TOP, Top N, ranking, leaderboard, which is highest (+ analysis dimension)

**⚠️ Key Distinction**:
- "Which **game** has highest payment" → **rank** (ranking object is game, can be grouping dimension)
- "Highest paying **user**" → **other** (finding specific user needs user cluster or SQL)

**Typical Questions**: Top 5 games by payment in last 7 days / Top 10 channels by revenue / Top 20 servers by activity

---

### 10. Heatmap (heatmap)

**Core Positioning**: Flexibly display user heat distribution in each area on game map or application interface. Game industry specific requirement.

**Strong Signal Keywords**: heatmap, heat map, hot area, coordinate distribution, position distribution, map heat

**Typical Questions**: Hot areas where players gather/battle/die in game map / Player distribution density in different map areas

---

### 11. Revenue Analysis (revenue)

**Core Positioning**: Track how a cohort's paid revenue, payment conversion, and cost recovery evolve over time after an initial event. Divide cohorts by an initial event, then combine payment event, revenue caliber, and cost data to observe each cohort's revenue on the initial day and subsequent observation days. This is the dedicated model for cohort LTV / ROI / payback analysis.

**Core Concepts**:
- **Initial Event**: Defines the cohort (e.g., register). Each date row = the batch of subjects who completed the initial event that day.
- **Payment Event**: Determines whether a subject paid (e.g., pay_success).
- **Revenue Caliber**: How revenue is computed — payment event + numeric property + calculation method (Sum / Per-user / Period-cumulative sum / Period-cumulative per-user); supports formula.
- **Cost Data** (optional): Cost event + numeric property + calculation method; required for ROI.
- **Observation Window**: Days to track after the initial event (e.g., 30 → shows Day 0 to Day 30).

**9 Result Metrics** (three groups):
- **Revenue**: LTV, Payment Amount, Cumulative Payment Amount
- **Payment Conversion**: Payers, Cumulative Payers, Payment Rate, Cumulative Payment Rate
- **Cost Recovery**: LTV Multiple, ROI

**Strong Signal Keywords**: LTV (cohort context), payment amount, payment rate, cumulative payment, ROI, payback / payback period, LTV multiple, Day-N LTV, D7/D30 LTV, revenue by cohort, channel ROI, cost recovery

**⚠️ Distinction from Retention Analysis**: Retention answers "did users come back" (retention rate, churn); Revenue answers "how much did users pay and did we recoup cost" (LTV, payment rate, ROI). When LTV/ROI is the primary ask, use **revenue**; when it is an add-on displayed on top of a retention curve, use retention.

**⚠️ Distinction from Event Analysis**: Event analysis aggregates a metric over calendar time (e.g., daily total revenue trend); Revenue analysis tracks a fixed cohort across observation days (Day 0, Day 7, Day N per cohort).

**Typical Questions**: D7/D30 LTV of daily new users / Payment rate and amount difference across channels / When does each channel's ROI hit target / Which cohort dates have abnormal revenue

---

### 12. SQL Query (sql)

**Core Positioning**: Directly query underlying data through SQL. "Universal fallback" of analysis system, meeting custom requirements not covered by above models.

**Applicable Scenarios**: Cross-model complex calculation, special statistical definition, temporary data exploration validation, analysis requiring JOIN of multiple tables

**Typical Questions**: Help me query users with balance > 1000 / Cross-model complex calculation / Metrics requiring special statistical definition

---
---


## Model Decision Tree (Execute by priority from high to low)

When determining, strictly check in following order, **first matched rule is final result**:

```
Step 1: Did user explicitly mention model name?
  → User says "funnel analysis" → FUNNEL
  → User says "retention analysis" → RETENTION
  → User says "interval analysis" → INTERVAL
  → User says "distribution analysis" → DISTRIBUTION
  → User says "path analysis" → PATH
  → User says "composition analysis" → COMPOSITION
  → User says "attribution analysis" → ATTRIBUTION
  (Explicit model name highest priority, use directly)

Step 2: Contains "interval" (time interval) keyword?
  → YES → INTERVAL

Step 3: Contains funnel related keywords or conversion description?
  Judgment conditions:
    - Appears "funnel", "penetration rate", "conversion rate" (multi-step context)
    - Appears "first...then...", "first...and...", "A→B→C"
  → YES → If also contains "retention" → RETENTION
          → Otherwise → FUNNEL

Step 4: Contains revenue / payment-value / payback keywords?
  Judgment conditions: Appears "LTV", "ROI", "payback", "payment rate", "payment amount",
    "cumulative payment", "LTV multiple", "Day-N LTV", "cohort revenue", "channel ROI", "cost recovery"
  → YES → Is it explicitly an add-on on a retention curve (e.g., "retention curve with LTV")?
          → YES → RETENTION
          → NO  → REVENUE

Step 5: Contains retention related keywords?
  Judgment conditions: Appears "retention", "day-1 retention", "next-day retention", "N-day retention", "churn", "decay", "revisit"
  → YES → RETENTION

Step 6: Contains heatmap related keywords?
  Judgment conditions: Appears "heatmap", "hot area", "coordinate distribution", "position distribution", "map heat"
  → YES → HEATMAP

Step 7: Contains "distribution"?
  → YES → Is analysis object static user property (level, region, age etc. inherent property)?
          → YES → COMPOSITION (composition analysis)
          → NO → DISTRIBUTION (distribution analysis)

Step 8: Contains "TOP" / "ranking" / "which is highest"?
  → YES → Is ranking object analysis dimension (game/channel/product etc.)?
          → YES → RANK
          → Is ranking object finding specific user?
          → YES → OTHER

Step 9: Contains "path" / "behavior trajectory" / "Sankey diagram" / "what did"?
  → YES → PATH

Step 10: Contains "attribution" / "touchpoint contribution" / "channel contribution degree"?
  → YES → ATTRIBUTION

Step 11: User filter/export/list requirement? Or prediction type? Or cannot classify?
  → YES → OTHER / SQL

Step 12: None of above matched?
  → EVENT (event analysis is default model)
```

---

## Edge Cases and Ambiguity Resolution Rules (Must Strictly Follow)

Core disambiguation rules summarized from 500+ real cases:

| # | Scenario | Correct Determination | Reason |
|---|------|----------|------|
| 1 | "Payment rate" appears alone | event | Single calculated metric, not multi-step conversion |
| 2 | "First-day payment rate" | event | Although "rate" implies conversion, but single metric |
| 3 | "Penetration rate" | funnel | Implies A to B conversion process |
| 4 | "Payment amount trend" | event | Time series aggregation |
| 5 | "Payment amount distribution" | distribution | User-level distribution |
| 6 | "Daily XX distribution" | distribution | "distribution" priority > "daily" |
| 7 | "Highest paying user" | other | Finding specific user, not leaderboard |
| 8 | "Highest paying game" | rank | Game is analysis dimension |
| 9 | "First A then B" + no model keyword | funnel | Sequential actions imply conversion |
| 10 | "First A then B" + "retention" | retention | Explicit model keyword priority |
| 11 | LTV (cohort/revenue context) | revenue | Dedicated cohort revenue model (Model 12) |
| 12 | Churn (any form) | retention | Churn is opposite of retention |
| 13 | ROI (any form) | revenue | ROI is a native cost-recovery metric of the revenue model |
| 14 | User list/filter/cluster requirement | other | Not analysis model scope |
| 15 | Prediction type requirement | other | AE doesn't support prediction analysis |
| 16 | "Session distribution" / "User count distribution" | distribution | "distribution" keyword determines |
| 17 | "Login user count daily distribution" | distribution | "distribution" > "daily" |
| 18 | Simply asking user count/count for certain event | event | Most basic event analysis |
| 19 | "Day-1 retention" / "Next-day retention" / "N-day retention" | retention | Retention keyword variant |
| 20 | "Position distribution" / "Coordinate distribution" / "Hot area" | heatmap | Space position related, priority over distribution |
| 21 | "Which model" + any analysis scenario | trigger skill | Force trigger word, no other condition needed |
| 22 | "Payment rate" / "payment amount" in cohort/LTV context | revenue | Native payment-conversion metric of revenue model |
| 23 | "LTV multiple" / "payback period" | revenue | Native cost-recovery metric |
| 24 | LTV/ROI explicitly as add-on on a retention curve | retention | User pins retention as the base model |
| 25 | "Payback" / "when do we recoup cost" | revenue | Cost recovery is a revenue-model goal |

---


## Model Configuration Methods

### 【Event Analysis (event) Configuration Method】

#### Pre-data Mapping Requirements (Agent Must Read):
Before configuration, must check underlying data dictionary, clearly distinguish these three data types and correctly map:
- Event: User's specific behavior (e.g., register, login).
- Event Property & Common Event Property: Describes specific context or value of event occurrence (e.g., amount, channel). Note: Common event property can be used for filtering and grouping of all events.
- User Property / User Tag / User Cluster: Describes user's own inherent static characteristics (e.g., VIP level, cumulative payment amount).

```
## Analysis Metrics (Support multi-metric combination and formula)
(For each user data requirement, configure corresponding metric line. Supports following three modes)
### Mode A: Basic Event Aggregation
Select Event: [matched real event, e.g.: Register (register)]
Calculation Method: Select [Total Count / Triggering User Count / Per User Count]
### Mode B: Event Property Aggregation (For numeric property)
Select Event: [matched real event, e.g.: Payment (payment)]
Select Property: [matched event property, e.g.: Payment Amount (pay_amount)]
Calculation Method (Different event property types provide different calculation methods):
  - If event property is numeric type, can only select one of: [Sum / Average / Average Per User / Median / Maximum / Minimum / Distinct Count / Variance / Standard Deviation / 99th Percentile / 95th Percentile / 90th Percentile / 80th Percentile / 75th Percentile / 70th Percentile / 60th Percentile / 40th Percentile / 30th Percentile / 25th Percentile / 20th Percentile / 10th Percentile / 5th Percentile]
  - If event property is text/string or time, can only select [Distinct Count]
  - If event property is boolean, can only select one of: [True Count / False Count / Empty Count / Non-empty Count / Distinct Count]
  - If event property is object/object array, can only select one of: [Empty Count / Non-empty Count / Distinct Count]
### Mode C: Composite Metric (Custom formula, supports add/subtract/multiply/divide)
Formula Logic: Use basic metrics built from above A or B modes for four arithmetic operations.
Example Configuration: [Metric A: Payment (payment) Triggering User Count] Divided by (/) [Metric B: Login (login) Triggering User Count]
Event-level Filter: Events in formula support event-level filter, filter condition 「Event Property/User Property/User Cluster/User Tag」「Logical Operator」「Specific Value」
Event-level Filter Example Configuration: [Metric A: Payment (payment) Channel = Official Website Triggering User Count] Divided by (/) [Metric B: Login (login) Triggering User Count]

📌 Filter Condition Level Explanation:
｜Filter Type｜Scope｜Use Case｜
｜Global Filter｜All metrics｜Unified filter condition applicable to all metrics｜
｜Metric-level Filter｜Current single metric｜Filter condition only for specific metric, other metrics unaffected｜
｜Event-level Filter｜Certain event in formula｜Only available in events of composite metric (custom formula)｜
Example: Query "Average gold consumption count by different device types for users in Shenzhen in last 30 days, total draw card count for V1.0 version"
Global Filter: City = Shenzhen (applicable to all metrics)
Metric-level Filter: Version = V1.0 (only applicable to draw card metric, average gold consumption count unaffected by this filter)

🔍 Metric-level Filter (Optional, can add multiple, logical relation AND/OR, only acts on current single metric):
If certain metric needs a separately setting filter condition (e.g., "Total draw card count for V1.0 version"), need to add filter separately under this metric: [Property Name] [Logical Operator, e.g.: Equals/Not Equals/Contains] [Specific Value].
🔍 Event-level Filter (Optional, can add multiple, logical relation AND/OR, only available in events of composite metric (custom formula))

## Global Filter (Optional, can add multiple, logical relation AND/OR, acts on entire chart)
(Used to define overall analysis sample range)
Select Filter Condition: [matched Event Property / Common Event Property / User Property / User Tag / User Cluster]
Select Logical Operator:
  - If filter condition is text type, can select [Equals / Not Equals / Includes / Excludes / Has Value / No Value / Regex Match / Regex Not Match]
  - If filter condition is time type, can select [In Range / Less Than or Equal / Greater Than or Equal / Relative to Current Date / Relative to Event Time / Has Value / No Value]
  - If filter condition is numeric type, can select [Equals / Not Equals / Less Than / Less Than or Equal / Greater Than / Greater Than or Equal / Has Value / No Value / Range]
  - If filter condition is boolean type, can select [Is True / Is False / Has Value / No Value]
Set Specific Value: [Specific number or string]
Example: 「Channel」「Equals」「Official Website」; 「Level」「Less Than or Equal」「100」; 「Is First Login」「Is True」

## Group By (Optional, can add multiple grouping items, used for breakdown comparison)
(Break down overall data by specific dimension, observe multiple trend lines)
Group By Dimension: Select [matched Event Property / Common Event Property / User Property / User Tag / User Cluster]
Example: Group by User Value Tier (user_value_level)

## Time Range & Granularity
Time Range: Select based on matched time range [e.g.: Last 7 days / This Month]
Time Granularity: Display by [Day / Hour / Week / Month / Minute (1min/5min/10min) / Total]
```
---

### 【Retention Analysis (retention) Configuration Method】

#### Pre-data Mapping Requirements (Agent Must Read):
Before configuring retention model, must check underlying data dictionary and strictly follow these mapping relationships:
- Initial Event and Return Event: Must map to real Events.
- Property Level Constraint: When grouping using event property, must and can only use 「Initial Event」 event property (or common event property/user property). Absolutely cannot use return event property for outer grouping!

```
## Analysis Subject
Select calculation perspective: [matched real analysis subject, e.g.: User (user_id) / Role (role_id) / Visitor (distinct_id), if not found prompt user to create]

## Core Event Configuration
▶️ Initial Event (Start): Select [matched real event, e.g.: Register (register)]
🔙 Return Event (Target): Select [matched real event, e.g.: Login (login)]

## Use Simultaneous Display (Advanced optional, calculate additional behavior or LTV for retained users)
(For users who completed 「Return Event」, calculate their performance on another specified event)
- Participate Event: [matched event, e.g.: Login (login) or Payment (payment)]
- Analysis Metric (Choose one):
  1. Basic preset metric: [Total Count / Triggering User Count / Per User Count / Cumulative Sum of Total Count by Period / Cumulative Average of Total Count by Period / Cumulative Sum of Triggering User Count by Period / Cumulative Average of Triggering User Count by Period], e.g., Draw Card (draw_card) Triggering User Count / Total Count
  2. Event property metric: [matched event property, if property is numeric type, can select Sum/Average Per User/Cumulative Sum/Cumulative Average Per User; if property is boolean, can select True Count/False Count/Empty Count/Non-empty Count], e.g., Payment (payment) Is First Pay True Count, represents count of first-time payment among returning users
🔍 Metric-level Filter (Only for this display metric): Set [Event Property, e.g.: Channel (channel)] [Logic, e.g.: Equals/Not Equals/Includes/Excludes/Has Value/No Value/Regex Match/Regex Not Match] [Specific Value, e.g.: Official Website]

## Use Relation Property (Advanced optional, for extremely precise same-category return)
(Used to limit user not only to return, but return specific object must match initial action)
Match Logic: Require 【Initial Event】 [matched event property, e.g.: Activity Type] Equals 【Return Event】 [matched event property, e.g.: Activity Type] (If simultaneous display is enabled, must also equal simultaneous display's matched event property)

## Global Filter (Optional, define overall analysis scope)
Select Filter Condition: [matched Event Property / Common Event Property / User Property / User Tag / User Cluster]
Select Logic: [Has Value / No Value / Greater Than or Equal / Less Than or Equal / In Range / Equals / Not Equals / Includes / Excludes etc.]
Set Specific Value: [Specific number or string]
Example: OS (os) Equals ios

## Group By (Optional, breakdown retention curve)
(⚠️ Warning: If grouping by event property, can only extract 「Initial Event」 event property)
Group By Dimension: Select [matched Initial Event Event Property / Common Event Property / User Property / User Tag / User Cluster]
Example: Group by app_version (initial event property)

## Time Range & Granularity
Retention Period: By [Day / Week / Month] - [Current Day / Next Day / Day 7 / Day 14 / N Days]
Analysis Range: [e.g.: Yesterday / Today / Last Week / This Week / Last Month / This Month / Last 7 days etc.]
```
---

### 【Funnel Analysis (funnel) Configuration Method】

#### Pre-data Mapping Requirements (Agent Must Read):
Before configuring funnel model, must check underlying data dictionary to ensure event sequence rationality:
- Multi-step Event Mapping: Each step of funnel must map to a real Event.
- Single Event Deep Funnel: If business requirement is "gradual conversion of same behavior" (e.g., Level 1→Level 2→Level 3), need to use same event, and stack independent event property filter within each step.

```
## Analysis Subject
Select conversion tracking perspective: [matched real analysis subject, e.g.: User (user_id) / Role (role_id) / Visitor (distinct_id), if not found prompt user to create]

## Funnel Steps (Core flow configuration)
(Add must-trigger events sequentially by business logic, supports up to 30 steps)
Step 1 (Start): Select [matched real event, e.g.: Register (register)]
- Step-level Filter (Optional): Set [Property Name] [Logic] [Specific Value]
Step 2: Select [matched real event, e.g.: Login (login)]
- Step-level Filter (Optional): Set [Property Name] [Logic] [Specific Value]
Step N (End): Select [matched real event, e.g.: Level Pass (level_pass)]
- Step-level Filter (Optional): Set [matched property, e.g.: Level (vip_level)] [Logic, e.g.: Equals] [Specific Value, e.g.: 5]

## Analysis Window Period (Conversion validity)
Set time limit for user to complete entire funnel starting from triggering 「Step 1」.
Window Range: Suggest setting based on business common sense [Minimum 1 minute, Maximum 180 days. E.g.: 1 day / 2 hours / 15 minutes].

## Use Relation Property (Advanced optional, for precise product/activity/match series)
(Not only require sequential trigger, but force require certain core property value in series steps to be completely consistent, property null then exclude)
Match Logic: Require [matched core event property in each step, e.g.: Item ID (item_id) / Activity ID (activity_id)] to be completely equal.

## Global Filter (Optional, define funnel analysis scope)
Set Filter Condition: [matched Event Property / Common Event Property / User Property / User Tag / User Cluster]
Select Logic: [Has Value / No Value / Greater Than or Equal / Less Than or Equal / In Range / Equals / Not Equals / Includes / Excludes etc.]
Set Specific Value: [Specific number or string]
Example: OS (os) Equals ios

## Group By (Optional, breakdown conversion rate comparison)
(Break funnel into multiple lines by specified dimension, compare conversion capability of different crowds)
Group By Dimension: Select [matched Step 1 Event Property / Common Event Property / User Property / User Tag / User Cluster] (⚠️ Note: Select from Step 1 event property, user property, user cluster, user tag, at most one added as grouping item)
Example: Group by Channel (channel)

## Time Range
Funnel trigger start time range: [e.g.: Last Month / Last 7 days]

> Chart View: [Suggest view based on user requirement: If viewing overall loss situation select 「Conversion Chart」 / If viewing daily conversion rate fluctuation select 「Trend Chart」]
```
---

### 【Interval Analysis (interval) Configuration Method】

#### Pre-data Mapping & Calculation Rules (Agent Must Read):
- Underlying Calculation Mechanism (Must deeply understand):
  - Different events (A -> B) adopt shortest interval principle: If sequence is A1->A2->B1->B2, only calculate one interval A2->B1.
  - Same event (A -> A) adopt adjacent interval principle: If sequence is A1->A2->A3, will produce two intervals A1->A2 and A2->A3.
- Property Level Constraint (Extremely error-prone, must follow): If grouping item selects event property, must and can only use 「Start Event」 event property. Absolutely cannot use end event property for global breakdown!

```
## Analysis Subject
Select calculation perspective: [matched real analysis subject, e.g.: User (user_id) / Role (role_id) / Visitor (distinct_id), if not found prompt user to create]
 (Note: Start and end events must be triggered by same subject to count as one complete interval)

## Start Event & End Event (Support independent metric-level filter)
🟢 Start Event: Select [matched real event, e.g.: Payment (payment)]
Metric-level Filter (Optional): Set [Property Name, e.g.: Payment Amount (pay_amount)] [Logic, e.g.: Equals] [Specific Value, e.g.: 0]
🛑 End Event: Select [matched real event, e.g.: Payment (payment) or Login (login)]
Metric-level Filter (Optional): Set [Property Name, e.g.: Payment Amount (pay_amount)] [Logic, e.g.: Greater Than or Equal] [Specific Value, e.g.: 100]

## Interval Upper Limit (Exclude invalid long-tail data)
Set maximum valid calculation duration: [Set based on business common sense, minimum 1 minute, maximum 180 days. E.g.: 1 day / 2 hours] (Note: Data exceeding this upper limit will be directly excluded)

## Use Relation Property (Advanced strong constraint, for same-category/continuous action matching)
(Not only require trigger by time order, but force require certain property relation. Property null then exclude)
Regular Match: Require 【Start Event】 [matched event property, e.g.: Account ID (account_id)] Equals 【End Event】 [matched event property], both property types must be consistent.
Advanced Numeric Match (Difference calculation): If numeric property, can set deviation. E.g., require 【End Event】 [Level ID (level_id)] to be 1 greater than 【Start Event】 property (Used to exclude duplicate grinding same level interference, only see real promotion time cost).

## Global Filter (Optional, define analysis scope)
Set Filter Condition: [matched Event Property / Common Event Property / User Property / User Tag / User Cluster]
Select Logic: [Has Value / No Value / Greater Than or Equal / Less Than or Equal / In Range / Equals / Not Equals / Includes / Excludes etc.]
Set Specific Value: [Specific number or string]
Example: OS (os) Equals ios

## Group By (Optional, breakdown time cost difference of different crowds)
(⚠️ Warning: If grouping by event property, can only extract 「Start Event」 property value at that moment)
Group By Dimension: Select [matched Start Event Event Property / Common Event Property / User Property / User Tag / User Cluster]
Example: Group by Start Event's Channel (channel)

## Time Range & Granularity
Display Dimension: By [Day / Hour / Week / Month / Total]
Time Range: [e.g.: This Month / Last 7 days]

> Chart & Metric View Suggestion:
  - [If user wants to see max/min, average, median etc. aggregate statistics, suggest 「Box Plot」]
  - [If user wants to see time cost interval distribution, e.g., how many people spent 0-5 minutes, how many spent 5-10 minutes, suggest 「Histogram」, and can prompt custom interval boundaries]
```
---

### 【Distribution Analysis (distribution/scatter) Configuration Method】

#### Pre-data Mapping & Calculation Rules (Agent Must Read):
Before configuring distribution model, must check underlying data dictionary and deeply understand following nested calculation logic:
- Aggregation Property Data Type Constraint: If aggregating by event property, text property only supports 「Distinct Count」; numeric property supports 「Sum/Average/Median/Max/Min/Percentile/Variance etc.」. Absolutely cannot use sum or average on text property!
- Multi-level Filter (Extremely confusing, must strictly distinguish):
  - Event-level Filter: Mounted on specific one event (e.g.: Only calculate payment count where is_first_pay=true).
  - Metric-level Filter (Global): Mounted externally on entire complete metric or formula (e.g.: After (A/B) result calculated, overall only look at Channel=Official Website data).

```
## Analysis Subject
Select calculation underlying perspective: [matched real analysis subject, e.g.: User (user_id) / Role (role_id)] (Note: All subsequent frequency and numeric values will be summarized based on this subject)

## Participate Event (Stratification basis / Core metric construction)
(Supports following three modes to construct stratification basis, and supports independent 「Event Filter」 on each event)
### Mode A: Stratify based on behavior frequency
Select [matched real event, e.g.: Login (login)]
Metric-level Filter (Optional): [matched Event Property / Common Event Property / User Property / User Tag / User Cluster, e.g.: Is First Login] [Logic] [Specific Value, e.g.: Is True]
Aggregation Granularity: [Count / Days / Hours]
### Mode B: Stratify based on event property calculation
Select [matched real event, e.g.: Payment (payment)]
Select [matched event property]. (If text type, only 「Distinct Count」; if numeric type, can select 「Sum/Average/Median/Maximum/Minimum/Variance/Standard Deviation/Percentile etc.」)
Metric-level Filter (Optional): Same as above
Aggregation Granularity: [Count / Days / Hours]
### Mode C: Stratify based on formula advanced calculation
Use basic event combination formula, e.g.: [Event A Aggregation Granularity] / [Event B Aggregation Granularity]. Each event can have independent event-level filter.
Event-level Filter (Optional): [matched property, e.g.: Is First Login] [Logic] [Specific Value, e.g.: Is True]

## Interval Division (Bucketing rule)
Set data intervals based on calculated metric distribution, supports default interval, discrete number and custom interval. [e.g.: Interval boundaries inferred by common sense, like 0-1, 1-5, 5-10, Greater than 10]

## Use Simultaneous Display (Advanced optional, to examine specific interval crowd's value)
(After interval division complete, further look at other performance of crowd falling into that interval)
Participate Event: [matched value event, e.g.: Payment (payment)]
Analysis Metric: [Total Count / Triggering User Count / Per User Count / Event property numeric aggregation etc.]. Can also use basic event combination advanced formula, same as Mode C above.
Event-level Filter (Optional): [matched property, e.g.: Is First Login] [Logic] [Specific Value, e.g.: Is True]
Metric-level Filter (Only for this display metric): Set [Property Name] [Logic] [Specific Value]

## Group By (Optional, breakdown distribution structure of different dimensions)
Break down interval structure by dimension: Select [matched Event Property / Common Event Property / User Property / User Tag / User Cluster]

## Time Range & Display Form
Time Display Granularity: By [Day / Week / Month / Total]
Time Analysis Range: [e.g.: This Month / Last 7 days etc.]

> Chart & View Suggestion:
  - [If need to see most detailed data comparison (or have grouping item), suggest first view 「Table」]
  - [If need to see overall static distribution, suggest 「Histogram / Bar Chart」]
  - [If need to see distribution structure change trend over time, suggest 「Percentage Distribution / Numeric Distribution」]
```
---

### 【Path Analysis (path) Configuration Method】

#### Pre-data Mapping & Strict Constraints (Agent Must Read):
Before configuring path model, must check underlying data dictionary and firmly remember these two red line rules:
- Absolutely Prohibit Event-level Filter: Selected participate events cannot attach any filter condition (e.g.: Cannot only look at payment where pay_amount>0, must bring entire payment in).
- Filter Dimension's Dimensionality Reduction Strike: This model's global filter is called 「User Filter」, only accepts fields from user table (user property/cluster/tag). Absolutely cannot use any event property (including common event property) for filtering!

```
## Events Participating in Analysis (Basic nodes constructing trajectory)
Select candidate action set for constructing behavior trajectory (Maximum 30 meta events).
Selected Range: [matched core event list, e.g.: Login (login), Level Up (level_up), Draw Card (draw_card), Logout (logout) etc.]
(⚠️ Warning: Here only select event name, absolutely cannot attach any filter condition!)

## Event Split (Advanced optional, for refining specific flow of same-type actions)
(Split same event into multiple different nodes on Sankey diagram based on certain property value)
Split Target: Select [one event from above selected list, e.g.: Level Up (level_up)]
Split Basis: By [matched event property of that event, e.g.: Level (level)] split.
(Display effect: Originally single "Level Up" node on chart will split into independent nodes like "Level Up(level=1)", "Level Up(level=2)".)

## Analysis Path Start/End Point (Determine exploration direction)
(Set one of two based on business requirement)
Forward Exploration (Look at flow after certain action): Select [matched specific event, e.g.: Login (login)] as 「Initial Event」. System will trace forward.
Backward Tracing (Look at behavior before churn or conversion): Select [matched specific event, e.g.: Logout (logout)] as 「End Event」. System will trace backward.

## Session Interval Duration (Session cutter)
(Set maximum timeout time for adjacent two actions to be considered same continuous session)
Interval Upper Limit: Suggest [Based on business inference, minimum 1 second, maximum 24 hours. E.g.: 30 minutes / 2 hours].
(Note: If no next selected event occurs after this interval, consider this session interrupted, trajectory ends.)

## User Filter (Global filter scope)
(⚠️ Warning: Can only select from user property, user tag, user cluster! Does not support single event property filter)
Set User Filter Condition: [matched User Property / User Tag] [Logic] [Specific Value]; Or [matched User Cluster] [Belongs to Cluster/Not Belongs to Cluster].
Example: Mid Spender Belongs to Cluster.

## Time Range
User trajectory analysis time window: [e.g.: Last 7 days / Last Month]

> Chart Interpretation Suggestion:
  - Prompt user to view generated **Sankey Diagram**
  - Rectangle block height represents flow size, connection line represents flow ratio. Click specific node to highlight view exclusive trajectory flowing through that node
```
---

### 【Composition Analysis (composition) Configuration Method】

#### Pre-data Mapping & Strict Red Lines (Agent Must Read):
Before configuring composition model, must check underlying data dictionary and firmly remember these three red lines:

- Absolute Prohibited Zone: **Strictly prohibit using any 「Event」 or 「Event Property / Common Event Property」**! This model can only query data in user dictionary (user property, user tag, user cluster).
- Timezone & Version Independence: User property has no timezone concept (cannot select display timezone); user tag forcibly uses system latest version for calculation.
- Aggregation Type Strong Dependency: When as metric analysis, calculation formula strictly limited by user property's data type (see below configuration steps for details).

```
## Analysis Metric (Profile evaluation basis)
(Choose one of following configurations based on requirement evaluation basis, note analysis metric can only have one, cannot add multiple metrics)
Default Option: Select [User Count] (i.e., matching #user_id distinct count).
Advanced Option: Calculate based on user property/tag:
Select [matched User Property / User Tag, e.g.: Total Payment Amount (total_pay_amount)], and select legal calculation granularity based on its data type:
  - Numeric type: [Sum / Average / Average Per User / Median / Maximum / Minimum / Distinct Count / Variance / Standard Deviation]
  - Text/Time type: [Distinct Count]
  - Boolean type (Property only): [True Count / False Count / Empty Count / Non-empty Count / Distinct Count]
  - List type (Property only): [List Distinct Count / Set Distinct Count / Element Distinct Count]
  - Object/Object Array type (Property only): [Distinct Count / Empty Count / Non-empty Count]

## Global Filter (Define overall profile pool)
(⚠️ Warning: Only use user property/user tag/user cluster fields, cannot use event property)
Set User Filter Condition:
- Select User Property/User Tag: [matched User Property/Tag] [Logic] [Specific Value / String]
- Select User Cluster: [matched User Cluster, e.g.: Mid Spender] [Logic: Belongs to Cluster / Not Belongs to Cluster]

## Group Statistics (Dual mode profile breakdown, choose one)
(Choose grouping mode based on whether business wants "view internal composition" or "view external comparison")
【Mode A: Group Statistics by 「Property」】(View overall internal composition and cross)
Select 1 to 2 [matched User Property / User Tag / User Cluster].
(Agent Hint: If select 1, intuitively display distribution ratio; if select 2, display as stacked bar chart or multi-dimensional cross table.)
Example: Group by Province (province).
【Mode B: Group Statistics by 「Crowd」】(View characteristic comparison of different customer groups)
Custom define up to 10 groups of crowds for horizontal comparison.
Group 1: [e.g.: All Users (as comparison baseline)]
Group 2: Set [matched User Property/User Tag/User Cluster] condition to define crowd [e.g.: High Value Churn Warning Cluster]
Group 3: Set ... condition to define crowd.

> Chart Interpretation Suggestion:
  - [If need to see absolute value difference of different dimensions, suggest 「Bar Distribution」]
  - [If need to see proportion of each part in overall, suggest 「Pie Distribution」]
  - [If configured two grouping items, suggest directly view 「Table」 to get multi-dimensional cross data]
  - ⚠️ Note: Composition analysis targets user static profile (user table), no timezone concept, and cannot analyze specific dynamic behavior events (e.g., "yesterday payment" please use event analysis).
```
---

### 【Attribution Analysis (attribution) Configuration Method】

#### Pre-data Mapping & Strict Red Lines (Agent Must Read):
Before configuring attribution model, must check underlying data dictionary and firmly remember these calculation red lines:
- Target Event Aggregation Limit: Conversion value can only be two granularities: Event **「Total Count」, or **「Sum」** of certain numeric property of that event. Absolutely cannot use distinct count, average etc. logic!
- Grouping Object Isolation Mechanism:
  - Target Event Grouping: Breaks down overall conversion total amount (e.g.: Group by region, see payment amount of each region attributed to whom).
  - Attribution Event Grouping: Breaks down touchpoints (e.g.: Group by channel, see which channel specific activity slot contributed).

```
## Analysis Subject
Select unique identifier spanning touchpoint and conversion: [matched real analysis subject, e.g.: User (user_id) / Visitor (distinct_id), if not found prompt user to create]

## Attribution Method (Choose distribution logic based on business goal):
[First Touch Attribution]: 100% credit to first touchpoint in window (Suitable for evaluating acquisition/ice-breaking).
[Last Touch Attribution]: 100% credit to last touchpoint in window (Suitable for evaluating final push for conversion).
[Linear Attribution]: All valid touchpoints in window equally share credit (Suitable for evaluating long-term seeding).

## Window Period (Touchpoint Validity Period, set time range to trace touchpoints backward from target event):
[Today]: Trace back to 0:00 of target event occurrence day.
[Custom]: [Set fixed duration based on business inference, e.g.: 1 hour / 3 days].

## Target Event (Define total bonus pool)
(What value do we distribute?)
- Conversion Event: Select [matched final conversion event, e.g.: Payment (payment)]
- Conversion Value (Strict constraint): [Total Count] or [matched numeric Event Property, e.g.: Payment Amount (pay_amount) Sum]
- Event-level Filter (Optional): Set [Event Property] [Logic] [Specific Value/String]
- Target Event Group By (Optional): Group by [matched property, e.g.: Province (province)], to separately view contribution total pool from different groups.
- Direct Conversion Participate Attribution Calculation
[Agent Strongly Suggest Check]: If target event cannot find any attribution event in window period, that conversion value will be counted in 「Direct Conversion」 (i.e., natural traffic/no explicit touchpoint conversion), avoid blindly exaggerating existing touchpoint contribution.

## Attribution Event (Define touchpoints competing for bonus, can add multiple)
(Who shares the credit?)
Touchpoint 1: Select [matched touchpoint event, e.g.: Click Banner (click_banner)]
- Event-level Filter (Optional): Same as above.
- Attribution Event Group By (Optional): Group by [matched touchpoint event property, e.g.: Registration Channel (channel)].
Touchpoint 2: Select [matched touchpoint event, e.g.: Click Recharge Icon (click_recharge_icon)]...
- Relation Property (Advanced strong constraint, for precise touchpoint matching)
(Ensure touched object and purchased object are same thing, property null then exclude)
  Match Logic: Require 【Attribution Event】 [matched core event property, e.g.: Item ID (item_id)] Equals 【Target Event】 corresponding property.

## Global Filter (Define analysis scope)
Set Filter Condition: [matched Event Property / User Property / User Tag / User Cluster] [Logic] [Specific Value]
Example: User Region Has Value.

## Time Range
Target event occurrence time window: [e.g.: Last 7 days / This Month]

> Core Metric Interpretation: Focus on each touchpoint's [Contribution Value to Target Event (Absolute)] and [Contribution Degree (Percentage)], and [Valid Trigger Rate].
```
---

### 【Ranking (rank) Configuration Method】

#### Pre-data Mapping & Strict Red Lines (Agent Must Read):
Before configuring ranking model, must check underlying data dictionary and firmly remember these red lines:
- Data Association Iron Law: Events as 「Ranking Metric」 and 「Simultaneous Display Metric」 must contain corresponding property field for selected 「Ranking Subject」! Otherwise cannot perform data aggregation.
- Ranking Handling SQL Mapping: Must accurately map underlying three sorting logics (rank, dense_rank, row_number) based on business tolerance for "same score".

```
## Ranking Subject (Rank whom)
(This is core dimension of ranking, default is Account ID)
Select Dimension: [matched User Property / Event Property, e.g.: Account ID (#account_id) / Level ID (level_id) / Topic (topic)]

## Ranking Metric (Numerical basis for ranking)
(Construct sorting core score based on events related to ranking subject)
Participate Event: [matched real event, e.g.: Payment (payment)]
Aggregation Granularity:
  - Preset Granularity: [Total Count / Triggering User Count / Per User Count]
  - Numeric Property Granularity: Select [matched numeric event property] [Sum / Average / Maximum / Minimum etc.]
Sort Direction: [Descending (Desc, Default) / Ascending (Asc)]

## Tie Handling (Arbitration rule when same score)
(Strictly choose one of three based on business scenario)
- [Tie and Skip (rank)]: Supports tie, subsequent ranking gaps (e.g.: 1, 2, 2, 4).
- [Tie No Skip (dense_rank)]: Supports tie, subsequent ranking consecutive (e.g.: 1, 2, 2, 3).
- [By Default Sort (row_number)]: Does not support tie, force order (e.g.: 1, 2, 3, 4. Note: Underlying uses dictionary order auxiliary sort).

## Simultaneous Display Metric (Advanced optional, supplement ranking subject's other performance)
(Does not participate in sorting, but displays parallel to ranking. Supports formula and multi-level filter)
Participate Event & Granularity: [matched event and calculation method, same as above]
Custom Formula: Supports four arithmetic operations of basic metrics.
Event-level Filter: Set [Property Name] [Logic] [Specific Value] (Only acts on events in formula).
Metric-level Filter: Set [Property Name] [Logic] [Specific Value] (Acts on entire display metric).

## Global Filter (Optional, define scope for generating ranking)
Set Filter Condition: [matched Event Property / User Property / User Tag / User Cluster] [Logic] [Specific Value]

## Ranking Period & Comparison (Required for viewing rise/fall)
Current Time Range: [e.g.: Last 7 days / This Week]
Comparison Period (Optional): If need to calculate "ranking float (e.g., up 2 ranks, down 3 ranks)", need to set comparison baseline. [e.g.: Previous Period]

> Chart Interpretation Suggestion: Prompt user to focus on **Ranking Change Arrow (↑/↓)** after enabling 「Comparison Period」, to quickly locate business subjects rising or falling fastest.
```
---

### 【Heatmap (heatmap) Configuration Method】

#### Pre-data Mapping & Strict Red Lines (Agent Must Read):
Before configuring heatmap model, must check underlying data dictionary and firmly remember these red lines:
- Coordinate Property Strict Dependency: Selected heat event (or user associated with that event) must have numeric properties representing X axis and Y axis coordinates, otherwise absolutely cannot generate map!
- Extreme/First/Last Filter "Single User" Principle: First/Last filter is dimensionality reduction strike for "each #user_id", ensuring each player only contributes 1 data point in selected window period (first/last/max/min), prevent single point volume inflation interfering overall heat distribution.
- Data Type Determines Filter Logic: Event filter operator strictly limited by property type (e.g., text type supports regex, object array supports set judgment).

```
## Heat Metric (Locate action and determine heat value)
Heat Event: Select [matched spatial interaction event, e.g.: Player Dead (player_dead) or Open Chest (open_chest)].
Event Filter (Optional): Supports multiple conditions and set [AND / OR] relation. Based on filter property type, operator must follow underlying type constraint:
  - Text type: [Equals / Not Equals / Includes / Excludes / Has Value / No Value / Regex Match / Regex Not Match]
  - Time type: [In Range]
  - Numeric type: [Equals / Not Equals / Less Than / Greater Than etc.]
  - Object type (Object): [Has Value / No Value]
  - Object Array type (Object Array): [Exists Object Satisfies / No Object Satisfies / All Objects Satisfy / Has Value / No Value]
Calculation Method: (Determines color depth):
  - If viewing frequency/user count: Select [Total Count / Triggering User Count / Per User Count].
  - If viewing specific value: Select [matched numeric property, e.g.: Resource Get Amount (resource_amount)] [Sum / Average / Maximum / Minimum / Distinct Count etc.].
First/Last Filter (Advanced optional, for eliminating single player repeated volume inflation or locating extreme value)
(After enabling, each user only keeps 1 event participating in heat calculation in entire time window)
Set to only keep each user's [First / Last / Certain Property Maximum / Certain Property Minimum] record in this time window for rendering.
Filter Method (Choose one of four):
  - [First / Last]: Keep first or last record of this user in time window.
  - [Maximum / Minimum]: Select certain [numeric or time type property], keep record where that property reaches extreme value.

## Event Coordinates (Soul binding)
X-axis Property: Must bind matched [numeric coordinate property in dictionary, e.g.: pos_x or screen_width].
Y-axis Property: Must bind matched [numeric coordinate property in dictionary, e.g.: pos_y or screen_height].
(Note: Can use event property or user property)

## Map File
Please select existing map or upload new map (⚠️ Note: If uploading new map, need to remind user to input real extreme coordinate points at bottom-left and top-right of that map for base map calibration).

## Multi-group Comparison (If comparison needed, optional, 2-4 groups): For left-right tile comparison of heat difference between different crowds.
Group 1: [e.g.: Empty condition, represents all data]
Group 2: Set filter condition [e.g.: User Cluster = High Tier Players].
(🔥 Hidden Advanced Technique: If need to compare different time periods (e.g., last week vs this week), can use #event_time (Event Time) in each group's filter condition to separately limit!)

## Time Range
Set global analysis window: [e.g.: Last 7 days / This Month]

## Chart Interaction Suggestion:
  - Prompt user can use bottom-right corner control to adjust 「Heat Radius」 and 「Transparency」 to prevent heat points from blurring together.
  - If enabled multi-group comparison, strongly suggest remind user to check 「Sync Zoom」, so as to align view specific local map difference (e.g., certain specific bush/BOSS room).
```
---

### 【Revenue Analysis (revenue) Configuration Method】

#### Pre-data Mapping Requirements (Agent Must Read):
- **Initial Event & Payment Event**: Must map to real Events.
- **Revenue Caliber**: Must map the payment event's numeric property (e.g., pay_amount) + calculation method.
- **Cost Data** (for ROI): Must map a cost event + numeric property; if absent, ROI cannot be computed — inform the user.
- **Grouping constraint**: Same as retention — when grouping by event property, can only use the **Initial Event** property.

```
## Analysis Subject
Select calculation perspective: [matched real analysis subject, e.g.: User (user_id) / Role (role_id) / Visitor (distinct_id), if not found prompt user to create]

## Cohort Initial Event
Initial Event: [matched real event, e.g.: Register (register)] — each date row = cohort that completed this event that day

## Payment Behavior
Payment Event: [matched real event, e.g.: pay_success], used to determine whether the analysis subject made a payment
Revenue Metric: Composed of the payment event, a numeric property, and a calculation method. [Matched payment event + numeric event property + calculation method, e.g.: "Sum" of "Pay Amount (pay_amount)" of "Payment (payment)"]
  Calculation Method: [Sum / Per-user / Period-cumulative sum / Period-cumulative per-user] (or custom formula)

## Cost Data (Optional, required for ROI)
When enabled, configure: Cost Event [matched event] + Numeric Property [matched numeric property] + Calculation Method [Sum / Average Per User, etc.]
(Cost data is used only for ROI and LTV multiplier metrics; if not enabled, these two metrics are unavailable)

## Observation Duration
Set the number of days to track after the initial event occurs: [e.g.: 30] (The result table will display from "Day 0" through "Day 30")
⚠️ Newer cohorts have not yet completed the full observation cycle, so later dates may temporarily have no data (e.g., a cohort formed today has no Day 7 / Day 30 results)


## Global Filter (Optional; defines the overall analysis sample scope)
Select Filter: [Matched Event Property / Common Event Property / User Property / User Tag / User Cluster]
Select Logic: [Equals / Not Equals / Greater Than or Equal / Less Than or Equal / Range / Has Value / No Value, etc.]
Set Value: [Specific numeric value or string]
Example: Source Channel (channel) Equals Official Website

## Group By (Optional; ⚠️ initial-event property only)
Group By Dimension: [matched Initial Event property / User Property / User Tag / User Cluster]
Example: Group by channel (initial event property)

## Time Range
Cohort initial-event date range: [e.g.: Last 30 Days / This Month]
(Available values: Yesterday, Today, Last Week, This Week, Last Month, This Month, Past 7 Days, Recent 7 Days, Past 30 Days, Recent 30 Days, Since a Specific Date, Custom, etc.)

## Result Metrics (Choose from the 9 below as needed; multi-select allowed)
- Revenue Metrics: LTV / Payment Amount / Cumulative Payment Amount
- Payment Conversion Metrics: Paying Users / Cumulative Paying Users / Payment Rate / Cumulative Payment Rate
- Cost Recovery Metrics: LTV Multiplier / ROI (depend on cost data)
```

> Chart interpretation tips:
  - To analyze revenue growth / cost recovery trends → read horizontally across the same cohort on different observation days
  - To compare user quality across different acquisition dates → compare vertically across different date rows
  - After configuring a Group By, click the plus sign at the start of a date row to expand and view the performance of different group values under that date

> **ae-cli mapping**: `analysis adhoc run --model-type revenue`; the AI-facing definition uses
> `initial_event` / `pay_event` / `revenue_metric` / `observation_days` / `selected_metrics`.
> Route actual execution to `ae-analysis`; this Skill only provides the configuration guide.

---

### 【SQL Query (sql) Method】

- 🎯 **Query Goal**: Briefly explain what complex logic this SQL solves that other models cannot (e.g.: Cross-project query / Complex multi-table JOIN / Special custom statistical scope).
- 📝 **SQL Statement**:
(Agent Internal Instruction: Based on underlying data dictionary, output Trino SQL that can run directly in AE. Must strictly follow: Field names containing special symbols like $ or # must use double quotes `""`, string values must use single quotes `''`. Default event table is `ta.v_event_1`, user table is `ta.v_user_1`, unless other project ID specified.)

```sql
-- Example format:
SELECT
  "$part_date",
  COUNT(DISTINCT "#user_id") AS "user_count"
FROM ta.v_event_1
WHERE "$part_event" = '[matched_event_name]'
  AND "[matched_property_name]" = 'specific_value'
GROUP BY "$part_date"
ORDER BY "$part_date" ASC
```

---

## Multi-model Combination Suggestions

In actual work, complex analysis scenarios often require multiple model combinations. When encountering complex problems, can suggest model combination solutions:

**Example — Analyze "Next-day Retention Rate Drop"**:
1. **Retention Analysis** → First confirm drop magnitude and time point of day-1 retention rate
2. **Event Analysis** → Compare key behavior metric difference between retained and churned users
3. **Funnel Analysis** → Check if onboarding tutorial conversion rate dropped
4. **Path Analysis** → Explore behavior path before churned users leave
5. **Distribution Analysis** → View online duration/usage count distribution of churned users

**Example — Analyze "Payment Conversion Optimization"**:
1. **Funnel Analysis** → Find step with largest loss in payment process
2. **Interval Analysis** → Understand user decision duration from browsing to payment
3. **Path Analysis** → Discover typical behavior path of paying users
4. **Attribution Analysis** → Evaluate contribution of different touchpoints to payment

---

## Language Policy

**CRITICAL**: Always respond in the user's language.
- If user writes in English → Respond in English
- If user writes in Chinese → Respond in Chinese
- Never translate the user's language; match their input language exactly
