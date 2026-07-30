---
name: new-hero-insight
description: Analyzes new hero/card launch impact including acquisition rate, gacha cost, payment impact, progression depth, battle performance, clear efficiency, and ecosystem health, providing strength ratings (T0-T4), balance recommendations, and operational strategies. Use when users need to analyze the impact of a new hero or card launch — such as acquisition rate, gacha cost, payment impact, or balance issues.
---

# New Hero Launch Full-Chain Data Analysis Skill

**Skill Full Name**

Card/Battle Game New Hero: Acquisition - Gacha - Progression - Battle - Clear - Ecosystem - Monetization Full-Dimensional Expert Analysis Skill (Deeply Adapted to ThinkingData Analysis System)

**Skill Positioning**

A strictly rule-based, comprehensive, reproducible, zero-subjective-bias professional-grade analysis capability designed for game numerical designers, version operators, business analysts, and data analysts. Strictly follows industry standards for game data analysis, deeply adapts to TE analysis system table structure and event tracking logic, completes field validation through standardized two-step interactions, executes full-chain analysis according to fixed statistical calibrations, quantified thresholds, and comparison rules, and outputs professional-grade analysis reports directly usable for version reviews, balance adjustments, and operational decisions. Even less capable AI can execute strictly according to rules 1:1 without skipping steps, omissions, or subjective speculation.

**Applicable Scope**

Card turn-based, MOBA, RPG, tower defense and other games with hero/card progression and PVP/PVE gameplay; full-cycle data monitoring for new hero launches, strength assessment, ecosystem impact analysis, balance adjustment support, and operational strategy formulation.

---

## I. Pre-execution Mandatory Rules (Iron Laws, AI Must 100% Comply, Cannot Modify or Skip)

1. **Interaction Flow Cannot Be Bypassed**: Must strictly follow the flow of "Requirement Parsing → Full Metadata Retrieval → Field Matching Confirmation → Data Compliance Validation → Full Module Analysis Execution → Report Output". Before field confirmation is complete, absolutely prohibited from executing any analysis, generating any SQL, or outputting any data conclusions.
2. **Statistical Calibration Absolute Unity**: All indicator calculation formulas, statistical ranges, deduplication rules, and time windows are fixed. AI cannot modify, simplify, or replace calibrations on its own.
3. **Data Validation Mandatory Execution**: All analyses must complete sample size validation, outlier removal, and deduplication validation before proceeding. When sample size is insufficient, must clearly annotate, cannot output definitive conclusions.
4. **Comparison Logic Strict Control**: All inter-group comparisons must control variables (same time window, same level/rank, same power range, same user tier). Cannot perform illogical cross-dimensional comparisons.
5. **Conclusions Must Be Quantifiable and Traceable**: All qualitative conclusions must have quantitative data support. Cannot use vague expressions like "win rate is very high" or "performance is very poor". Must annotate specific values, magnitude above/below baseline, and corresponding quantified thresholds.
6. **TE System Deep Adaptation**: All analyses are based on TE system standard event table ta.v_event_projectID and user table ta.v_user_projectID, joined via #user_id; when querying event table, SQL must include $part_date (date partition) and $part_event (event partition) dual partition filters; all TE preset properties start with #, strictly following official field type specifications.

---

## II. Step 1: Requirement Parsing and Field Matching Full Process (Expert-Level Refinement, Cannot Skip)

### 2.1 Requirement Information Extraction (Must Complete First, Missing Items Directly Ask User)

**[Required Fields, Missing One Terminates Flow and Directly Asks User to Supplement]**

1. Target hero unique identifier: Hero name / Hero ID
2. Hero official launch date
3. Analysis end date (defaults to user's query date, user can customize)

**[Optional Fields, Provided Then Automatically Enables Corresponding Analysis]**

1. Comparison hero list and corresponding launch dates (for multi-hero same-period effect comparison)
2. Payment tier thresholds (for user segmentation analysis, use default thresholds if not provided)
3. Rank/level division rules (for dimensional analysis, use generic division rules if not provided)
4. Gacha pity mechanism rules (for pity analysis, use generic small pity/big pity determination rules if not provided)

### 2.2 Database Metadata Full Automatic Retrieval (Must Cover All Events and Properties)

AI must fully scan all event names, property names, and field types in TE database's event table and user table. Complete matching in the following priority order: first match user custom event tracking, then match TE official preset properties. Matching results must be fully recorded. Unmatched items must be clearly annotated.

```markdown
| Event Category | Event Search Keywords | Required Properties (★ Required) | Field Purpose |
|----------------|----------------------|----------------------------------|---------------|
| Gacha Event (★ Required) | gacha, draw, summon, recruit, ten-pull, single-pull | ★Gacha type field (distinguish single-pull/ten-pull/limited pool)<br>★Obtained hero list field (JSON/array, containing hero ID/name)<br>★Pity flag field (whether triggered small pity/big pity)<br>★Gacha count field (pulls consumed this time/accumulated pity pulls)<br>User unique identifier #user_id | Hero acquisition rate, gacha cost, pity distribution analysis |
| Login/Active Event (★ Required) | login, start, ta_app_start, active | ★User unique identifier #user_id<br>Event time #event_time | Active user count, ownership rate, user activity tier calculation |
| Hero Progression Event | level_up, star_up, breakthrough, advancement, skill_upgrade | ★Hero ID/name field<br>★Level field (level)<br>★Star field (star/star_level)<br>★Power field (power/fight_power)<br>User unique identifier #user_id<br>Event time #event_time | Hero progression progress, resource investment, bottleneck node analysis |
| Battle/Settlement Event (★ Required) | battle, fight, match, settlement, clear | ★Deployed lineup field (JSON object group/array, storing heroes deployed this match)<br>★Match win/lose result field (win/lose/1/0)<br>★Level/rank field<br>★Clear duration field<br>★Clear attempts field<br>★Three-star achievement flag field<br>★Block flag field<br>User unique identifier #user_id | Pick rate, win rate, clear efficiency, lineup ecosystem analysis |
| Payment Event | recharge, pay, payment, order, purchase | ★Payment amount field<br>★Payment item/type field<br>User unique identifier #user_id<br>Event time #event_time | Payment pull effect, payment tier analysis |
| Ban/Disable Event | ban, disable, banned_hero | ★Banned hero ID/name field<br>Match unique identifier<br>User unique identifier #user_id | Ban rate, non-ban must-pick determination |
```

### 2.3 Fixed Output: Field Matching Confirmation Checklist (Expert Edition Standard Format)

Before receiving user's "Confirm" reply, absolutely do not enter analysis phase.

**[New Hero Analysis Field Matching Confirmation Checklist]**

**▌Confirmed Requirement Information**
- Target hero: {{Hero Name/Hero ID}}
- Launch time: {{YYYY-MM-DD}}
- Analysis time range: {{Launch Time}} to {{Analysis End Time}}
- Comparison hero (if any): {{Hero Name + Launch Time}}

**▌Automatic Retrieval Matching Results (Please Confirm Item by Item)**

1. ★Gacha Core Event
   Matched event name: {{event_name}}
   - Gacha type field (single-pull/ten-pull distinction): {{field_name}} | Match status: Matched/Not Matched
   - Obtained hero list field: {{field_name}} | Match status: Matched/Not Matched
   - Pity flag field (small pity/big pity): {{field_name}} | Match status: Matched/Not Matched
   - Gacha count field: {{field_name}} | Match status: Matched/Not Matched
   - User unique identifier: {{field_name}} | Match status: Matched/Not Matched

2. ★Login/Active Core Event
   Matched event name: {{event_name}}
   - User unique identifier: {{field_name}} | Match status: Matched/Not Matched
   - Event time field: {{field_name}} | Match status: Matched/Not Matched

3. Hero Progression Event
   Matched event name: {{event_name}}
   - Hero ID/name field: {{field_name}} | Match status: Matched/Not Matched
   - Level field level: {{field_name}} | Match status: Matched/Not Matched
   - Star field star: {{field_name}} | Match status: Matched/Not Matched
   - Power field power: {{field_name}} | Match status: Matched/Not Matched
   - User unique identifier: {{field_name}} | Match status: Matched/Not Matched

4. ★Battle/Settlement Core Event
   Matched event name: {{event_name}}
   - Deployed lineup JSON field: {{field_name}} | Match status: Matched/Not Matched
   - Match win/lose result field: {{field_name}} | Match status: Matched/Not Matched
   - Level/rank field: {{field_name}} | Match status: Matched/Not Matched
   - Clear duration field: {{field_name}} | Match status: Matched/Not Matched
   - Clear attempts field: {{field_name}} | Match status: Matched/Not Matched
   - Three-star achievement field: {{field_name}} | Match status: Matched/Not Matched
   - Block flag field: {{field_name}} | Match status: Matched/Not Matched
   - User unique identifier: {{field_name}} | Match status: Matched/Not Matched

5. Payment Event
   Matched event name: {{event_name}}
   - Payment amount field: {{field_name}} | Match status: Matched/Not Matched
   - Payment item field: {{field_name}} | Match status: Matched/Not Matched
   - User unique identifier: {{field_name}} | Match status: Matched/Not Matched

6. Ban/Disable Event
   Matched event name: {{event_name}}
   - Banned hero field: {{field_name}} | Match status: Matched/Not Matched
   - User unique identifier: {{field_name}} | Match status: Matched/Not Matched

**▌Confirmation Rules**

1. All matched correctly: Please reply "Confirm" directly
2. Matched incorrectly: Please reply "[Modify] indicator name + correct field name", example: [Modify] gacha type field + gacha_type
3. Field missing: Please reply "[Supplement] missing indicator name + custom field name + field type"
4. Required field missing: Will be unable to execute corresponding core module analysis, please supplement and confirm

---

## III. Step 2: After User Confirmation, Full Module Expert-Level Analysis Execution (100% Coverage, No Weakening, Execute Item by Item)

### General Pre-execution Rules

1. **Time Range**: Strictly limited to "Hero launch date - Analysis end date", all data is calculated within this window
2. **Deduplication Rules**: User dimension indicators use #distinct_id/#user_id deduplication, match dimension indicators use match unique ID deduplication
3. **Outlier Handling**: Remove test accounts, invalid matches with duration <10s, gacha count exceeding big pity threshold 3x
4. **Sample Size Validation**: When single module analysis sample size <100, annotate "Insufficient sample size, conclusions for reference only"; when core match sample size <500, cannot output strength definitive conclusions
5. **Payment Tier Default Thresholds**: Non-payer (cumulative payment 0), Low Spender (1-100), Mid Spender (101-1000), High Spender (1001+), use user-provided custom thresholds if provided
6. **Rank Default Division**: Low rank (server-wide bottom 50%), Mid rank (server-wide 50%-90%), High rank (server-wide 90%-99%), Top rank (server-wide top 1%)

---

### Module 1: Hero Acquisition Rate and Gacha Cost Deep Analysis (Requirement Core Point 1, Full Refinement Execution)

#### 1.1 Core Basic Indicator Calculation (Fixed Calibration, Cannot Modify)

```markdown
| Indicator Name | Fixed Calculation Formula | Output Requirements |
|----------------|--------------------------|---------------------|
| Total gacha user count | Deduplicated user count triggering gacha events within time range | Absolute value + ratio of active users |
| Hero obtained user count | Deduplicated user count with target hero in obtained hero list within gacha events | Absolute value + ratio of gacha users |
| Hero acquisition rate | (Hero obtained user count ÷ Gacha user count) × 100% | Percentage, keep 2 decimal places |
| Server-wide active user count | Deduplicated user count triggering login events within time range | Absolute value |
| Hero server-wide ownership rate | (Hero obtained user count ÷ Server-wide active user count) × 100% | Percentage, keep 2 decimal places |
| Payment tier ownership rate | Within each payment tier, (Hero obtained user count ÷ Tier active user count) × 100% | Output by Non-payer/Low Spender/Mid Spender/High Spender |
```

#### 1.2 Gacha Type Segmented Analysis (Strictly Distinguish Single-pull/Ten-pull)

1. Based on gacha type field, split into single-pull event pool, ten-pull event pool
2. Calculate separately: Probability of single-pull outputting target hero, probability of ten-pull outputting target hero
3. Calculate separately: Average pulls for single-pull hero acquisition, average pulls for ten-pull hero acquisition
4. Compare output efficiency difference between single-pull and ten-pull, determine if there is gacha type probability bias

#### 1.3 Pity Mechanism and Extreme User Analysis

1. Pity distribution statistics: User count & ratio of small pity hero output, user count & ratio of big pity hero output, user count & ratio of non-pity hero output
2. Extreme "black account" user determination: Satisfying any of the following conditions marks as extreme user
   - Triggered big pity 2+ times consecutively before obtaining target hero
   - Pulls for hero acquisition exceed official big pity threshold 1.5x
3. Output extreme user count, ratio of total hero obtained user count, average pull extreme value, determine if pity mechanism abnormality exists

#### 1.4 Card Output Cost Full Statistics

1. Full user hero acquisition pull statistics: Average, median, P25/P75/P90/P95 percentile values, minimum pulls, maximum pulls
2. Output average pull count and median pull count by payment tier, determine if payment tier affects card output cost
3. Output pull distribution histogram core data, clarify most users' card output cost range

---

### Module 2: Gacha Payment Pull Effect Analysis (Requirement Core Point 2, Full Refinement Execution)

#### 2.1 Launch Period Payment Core Indicator Changes

1. Daily time series statistics: After hero launch, daily total payment amount, paying user count, payment rate, ARPU, ARPPU
2. Sequential comparison: Compare with daily average 7 days before hero launch, calculate sequential increase/decrease magnitude for each indicator
3. Core association analysis: Time matching degree between payment amount peak and gacha user count peak, determine if payment growth is driven by new hero gacha

#### 2.2 Gacha and Payment Correlation Analysis

1. Paying user gacha penetration rate: (Paying users participating in gacha ÷ Total paying users) × 100%
2. Gacha user payment conversion rate: (Gacha users with payment behavior ÷ Total gacha users) × 100%
3. Payment amount and gacha count correlation coefficient, determine gacha behavior's driving strength for payment
4. New paying user ratio: After hero launch, ratio of first-time paying users whose first payment purpose was gacha

#### 2.3 Historical Hero Same-Period Comparison Analysis (Must Execute When User Provides Comparison Hero)

1. Strictly control time window: Compare data from same number of days after hero launch (e.g., 7 days after launch)
2. Comparison dimensions:
   - Gacha core indicators: Gacha user count, acquisition rate, ownership rate, average card output pulls
   - Payment core indicators: Total payment, paying user count, payment rate, ARPU increase
   - User coverage: Active user penetration rate, payment tier participation
3. Output this new hero vs historical hero effect difference, determine this new hero's payment pull capability strength

#### 2.4 Payment Tier Refinement Analysis

1. Each payment tier's gacha participation rate, average gacha count, hero acquisition rate
2. Each payment tier's payment amount increase and payment frequency change after hero launch
3. High Spender core contribution: High Spender payment amount ratio of total gacha-related payment
4. Non-payer acquisition situation: Non-payer hero obtained user count, ratio, average card output pulls

---

### Module 3: Hero Progression Deep Analysis (Requirement Core Point 3, Full Refinement Execution)

#### 3.1 Server-wide Progression Dimension Full Statistics

1. For all users who obtained this hero, output the following indicators:
   - Hero level: Distribution data, average, median, P25/P75/P90 percentile values, highest level, max-level user ratio
   - Hero star: Distribution data, average, median, each star user ratio, max-star user ratio
   - Hero power: Distribution data, average, median, P25/P75/P90 percentile values, highest power, server-wide top 10% power threshold
2. Output average level, star, power by payment tier, determine payment's impact on progression progress

#### 3.2 User Progression Time Series Analysis

1. Time window split: 24h, 48h, 72h, 7 days after hero acquisition, four nodes
2. Statistics for each time node: User average level increase magnitude, star increase magnitude, resource investment speed
3. Output server-wide progression progress TOP10% user characteristics: Payment tier, active days, gacha count
4. Analyze whether users quickly maxed progression within 72h after hero acquisition, determine hero's driving capability for user resource investment

#### 3.3 Progression Bottleneck Node Identification

1. Define bottleneck node: User stagnation duration at a certain level/star exceeds 48h, and that node stagnation user ratio ≥30%
2. Output all identified progression bottleneck nodes, stagnation user ratio, stagnation average duration
3. Determine if progression interruption is caused by upgrade/star-up resource shortage, output resource scarcity node conclusion

#### 3.4 Progression and Battle Performance Association Analysis

1. Analyze hero level/star/power correlation with win rate, determine progression degree's impact on hero strength
2. Output win rate differences across different progression degree ranges, determine if "low progression cannot deploy, high progression brainless strong" problem exists

---

### Module 4: Hero Deployment and Core Battle Performance Analysis (Requirement Core Point 4, Full Refinement Execution)

#### 4.1 Lineup JSON Parsing Fixed Rules

1. Traverse JSON object group/array in lineup field within battle event, extract all deployed hero IDs/names for each match
2. Match target hero ID/name, mark that match as "Target hero deployed match (Experiment Group)", otherwise mark as "Non-deployed match (Control Group)"
3. Parsing results must be deduplicated, when single match triggers settlement event multiple times, only count 1 time

#### 4.2 Core Pick Indicator Calculation (Fixed Calibration)

```markdown
| Indicator Name | Fixed Calculation Formula | Output Requirements |
|----------------|--------------------------|---------------------|
| Total pick rate | (Target hero deployed match count ÷ Total valid match count) × 100% | Percentage, keep 2 decimal places |
| Mode-segmented pick rate | Calculate pick rate separately for PVP, PVE modes | Output by mode |
| Rank-segmented pick rate | Calculate pick rate separately for Low/Mid/High/Top rank | Output by rank |
| Pick order ratio | Ratio of matches with first-pick/second-pick/late-pick target hero | Percentage, annotate core pick order |
| Ban rate (if available) | (Target hero banned match count ÷ Total valid ban/pick match count) × 100% | Percentage, keep 2 decimal places |
```

#### 4.3 Win Rate Core Indicator Calculation (Fixed Calibration)

```markdown
| Indicator Name | Fixed Calculation Formula | Output Requirements |
|----------------|--------------------------|---------------------|
| Overall win rate | (Target hero deployed winning match count ÷ Target hero deployed total match count) × 100% | Percentage, keep 2 decimal places |
| Mode-segmented win rate | Win rate in PVP, PVE modes, compare with all-hero same-mode average | Output absolute value + difference from baseline |
| Match count proficiency win rate | Win rate for debut matches (1-3), proficient matches (4-20), master matches (20+) | Output by range, determine proficiency's impact on win rate |
| Rank-segmented win rate | Win rate in Low/Mid/High/Top rank, compare with all-hero same-rank average | Output by rank, top rank win rate is strength core determination basis |
| Progression degree win rate | Win rate across different level/star/power ranges | Output by range, determine progression degree's impact on win rate |
```

#### 4.4 Strength Rating Quantified Thresholds (Fixed, AI Cannot Modify)

```markdown
| Strength Rating | Quantified Judgment Standard (Core Conditions Must All Be Met) |
|------------------|----------------------------------------------------------------|
| Overpowered (T0) | Core condition: Top rank win rate ≥58%, and exceeds all-hero same-rank average ≥10 percentage points;<br>Secondary condition: Pick rate ≥40% OR Ban rate ≥40% |
| Strong (T1) | Core condition: Top rank win rate 54%-57.9%, exceeds all-hero same-rank average 5-9.9 percentage points |
| Balanced (T2) | Core condition: Top rank win rate 48%-53.9%, difference from all-hero same-rank average within ±5 percentage points |
| Weak (T3) | Core condition: Top rank win rate 43%-47.9%, below all-hero same-rank average 5-9.9 percentage points |
| Bottom-tier (T4) | Core condition: Top rank win rate <43%, below all-hero same-rank average ≥10 percentage points;<br>Secondary condition: Pick rate <5% |
```

---

### Module 5: New Hero Match Clear Efficiency Impact Analysis (Requirement Core Point 5, Full Refinement Execution)

#### 5.1 Strict Control Group Setup Rules (Must Control Variables, AI Cannot Modify)

1. Experiment Group: Valid matches carrying target hero
2. Control Group: Same time window, same level/rank, same player power range (±10%), valid matches without target hero
3. Remove extreme outlier matches, ensure both group sample size difference no more than 50%, guarantee comparison validity

#### 5.2 Core Efficiency Indicator Inter-group Comparison (Fixed Calibration, Must Output All)

```markdown
| Comparison Indicator | Calculation Rule | Output Requirements |
|----------------------|------------------|---------------------|
| Match win rate | Experiment group win rate vs Control group win rate | Absolute value + increase/decrease percentage points |
| Level clear rate | Experiment group clear rate vs Control group clear rate | Absolute value + increase/decrease percentage points |
| Average clear attempts | Experiment group average clear attempts vs Control group | Absolute value + decrease/increase count |
| Average clear duration | Experiment group average clear duration vs Control group | Absolute value + decrease/increase duration |
| Three-star achievement rate | Experiment group three-star rate vs Control group | Absolute value + increase/decrease percentage points |
| Block rate | Experiment group block rate vs Control group | Absolute value + decrease/increase percentage points |
```

#### 5.3 Level-by-level Deep Breakdown

1. Statistics separately for normal level, elite level, event BOSS level, tower climb level efficiency differences
2. Output best-performing level scenario, worst-performing level scenario
3. Key hero dependency determination: Without this hero, level clear rate decrease ≥30%, determined as "Clear essential core card", annotate affected level range

#### 5.4 New User Progression Impact Analysis

1. For users with registration time ≤30 days, separately compare progression clear efficiency with/without this hero
2. Determine if this hero significantly impacts new user progression progress, if new player friendliness issues exist

---

### Module 6: Lineup Ecosystem and Hero Combination Diversity Analysis (Requirement Core Point 6, Full Refinement Execution)

#### 6.1 Hero Partner Association Degree Calculation

1. Extract all match lineups carrying target hero, count other heroes' co-deployment count with target hero
2. Calculate co-deployment rate: (Co-deployment match count with target hero ÷ Target hero total deployment match count) × 100%
3. Output best partners TOP10, annotate co-deployment rate, combination match win rate
4. Output countered heroes TOP5: Heroes with win rate decrease ≥15% when target hero deployed
5. Output counter heroes TOP5: Heroes with win rate ≥60% when facing target hero

#### 6.2 Lineup Similarity Quantified Calculation

1. Use Jaccard similarity algorithm, calculate overlap degree between all lineups carrying target hero pairwise
2. Output full lineup average similarity, determine lineup rigidity degree by following thresholds:
   - Average similarity <30%: Highly diverse, combination diversity extremely strong
   - Average similarity 30%-59%: Light convergence, mainstream combinations exist but diversity sufficient
   - Average similarity 60%-79%: High convergence, lineup rigid, mainstream combinations absolutely dominant
   - Average similarity ≥80%: Complete monopoly, only 1-2 fixed lineups exist, no diversity

#### 6.3 Match Ecosystem Health Degree Determination (Fixed Quantified Thresholds)

1. Pick rate thresholds:
   - <10%: Unpopular hero, no ecosystem impact
   - 10%-30%: Healthy range, popular but not monopolizing
   - 30%-40%: Super popular, ecosystem squeeze risk exists
   - >40%: Monopoly level, severely squeezes other hero deployment space
2. Ban rate thresholds:
   - <5%: No ban pressure, ecosystem healthy
   - 5%-20%: Reasonable ban range
   - 20%-40%: High ban, non-ban must-pick risk exists
   - >40%: Complete non-ban must-pick, severely disrupts match ecosystem
3. Final ecosystem conclusion: Combining pick rate, ban rate, lineup similarity, output "Healthy/Average/Unhealthy/Severely Disrupted" final determination, clearly annotate core issues.

---

## IV. Final Output Report (Fixed Complete Structure, Directly Usable for Version Review)

**[Expert Edition] New Hero "{{Hero Name}}" Full-Dimensional Data Analysis Report**

### Report Summary

1. Analysis time window: {{Launch Time}}-{{Analysis End Time}}, cumulative {{X}} days
2. Core strength rating: {{Overpowered/Strong/Balanced/Weak/Bottom-tier}}
3. Match ecosystem rating: {{Healthy/Average/Unhealthy/Severely Disrupted}}
4. Core conclusion: Within 3 sentences summarize core performance, core issues, core recommendations
5. Data sample description: Total match count {{X}}, valid user count {{X}}, sample size validation result

### I. Hero Acquisition and Gacha Cost Analysis

1. Core indicators: Acquisition rate, ownership rate, payment tier ownership situation
2. Card output cost: Average pulls, median, pity distribution, extreme user situation
3. Single-pull/ten-pull efficiency comparison
4. This module core insights

### II. Gacha Payment Pull Effect Analysis

1. Launch period payment indicator changes and sequential increase magnitude
2. Gacha-payment correlation analysis
3. Historical hero same-period comparison (if available)
4. Payment tier refinement performance
5. This module core insights

### III. Hero Progression Progress Analysis

1. Server-wide progression distribution: Level, star, power core indicators
2. Progression time series progress and resource investment speed
3. Progression bottleneck node identification
4. Progression degree and battle performance correlation
5. This module core insights

### IV. Hero Core Battle Performance and Strength Rating

1. Pick and Ban core indicators
2. Full-dimensional win rate performance: By mode, by rank, by proficiency, by progression degree
3. Final strength rating and determination basis
4. This module core insights

### V. Match Clear Efficiency Impact Analysis

1. Experiment group vs control group core indicator comparison
2. Level scenario performance breakdown
3. New user progression impact analysis
4. Key hero dependency determination
5. This module core insights

### VI. Lineup Ecosystem and Combination Diversity Analysis

1. Best partners TOP5 and counter relationships
2. Lineup similarity and rigidity degree determination
3. Match ecosystem health degree final determination
4. Impact on other hero deployment space
5. This module core insights

### VII. Core Issue Localization

1. Numerical balance issues: Core reasons for overpowered/weak
2. Mechanism issues: Whether mechanism monopoly/mechanism defect exists
3. Ecosystem issues: Whether disrupts match environment
4. Operational issues: Core issues in gacha, progression, payment phases

### VIII. Numerical Balance Adjustment Recommendations (For Designers, Directly Actionable)

1. Numerical adjustment recommendations: Damage, multiplier, cooldown, attributes, progression cost, etc.
2. Mechanism adjustment recommendations: Skill logic, trigger conditions, combination effects, etc.
3. Adjustment priority and risk warnings

### IX. Operational Strategy Recommendations (For Operations, Directly Actionable)

1. Gacha operations: UP pool rhythm, pity mechanism optimization, welfare distribution recommendations
2. Progression operations: Resource distribution, bottleneck node optimization, progression pack design
3. Content operations: Hero guides, lineup combination guidance, tournament/activity adaptation
4. Tiered operations: Differentiated reach strategies for non-payer/paying users

### X. Risk Warning and Follow-up Analysis Recommendations

1. Version risk warning: Environmental disruption risk from overpowered heroes, player reputation risk from weak heroes
2. Follow-up monitoring recommendations: Core indicators to continuously track, time nodes
3. Deep analysis directions: Analysis dimensions that can be further broken down

### Appendix: Statistical Calibration Explanation

Detailed explanation of all indicator calculation formulas, deduplication rules, time windows, tier thresholds, ensuring report reproducibility and traceability.

---

## V. Exception and Boundary Case Handling Rules (Required)

1. Required field missing: Gacha/Login/Battle core event missing, directly inform user "Missing XX core event, cannot execute this analysis, please supplement corresponding field information"
2. Insufficient sample size: Core match sample size <500, annotate all strength conclusions in report as "Insufficient sample size, conclusions for reference only, recommend re-analyze after accumulating more data"
3. Lineup JSON parsing failure: Clearly inform user "Lineup field format cannot be parsed, please confirm field type and structure, supplement parsing rules and re-execute"
4. Time range conflict: Analysis end time earlier than hero launch time, directly ask user to correct time range
5. Hero ID duplicate: Multiple heroes with same name matched, directly ask user to confirm unique hero ID/name
6. Data abnormal fluctuation: Single-day indicator fluctuation exceeds 100%, automatically remove outlier data and clearly annotate in report

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.