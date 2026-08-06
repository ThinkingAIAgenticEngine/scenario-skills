# Scope Definition Guide

## 0. Citation Rules

All citations in this guide must use a unified explicit document-reference format. Temporary placeholders and inconsistent document-name styles must not remain.

### 0.1 English Citation Format
- All document names must be written as: `filename.md`
- The preferred citation sentence format is:
  - See `filename.md` for the section on "topic".
- If the exact topic cannot be identified, use:
  - See `filename.md`.

### 0.2 Disallowed Citation Forms
The following forms must not appear in this guide:
- `:contentReference[...]`
- `oaicite`
- `《document name》`
- formal citations without the `.md` suffix
- any other temporary citation markers that cannot be formally resolved during skill execution

### 0.3 Citation Usage Principles
- The primary evidence for the current implementation layer is always the SQL / query / dashboard / report configuration of the identified object.
- Product documents are used for definition-layer explanation, rule validation, and edge-condition clarification.
- Document citations must not replace SQL facts.
- If the current implementation differs from product definition, the guide must state separately:
  - what the current implementation does
  - what the product definition normally means

### 0.4 Citation Maintenance Requirements
- Each revision of this guide must be checked for leftover temporary citation placeholders.
- Any remaining placeholders must be replaced with explicit document references before formal use.
- No citation that cannot be mapped to an actual resource may remain in the final version.

---

## 1. Objective

This guide is used to help the executor align analytical scope with the customer.

The goal of this guide is not to expand every scope detail in the first response.  
Instead, the executor should first provide a **specific enough version of the scope for confirmation**, and then actively ask whether the customer wants to continue drilling down into finer definition layers.

This guide applies to the following analytical assets and analytical objects:
- SQL
- query / qp / adhoc_query
- dashboard / report
- metrics
- events
- event attributes
- user attributes
- virtual events
- virtual attributes
- dimension-table attributes
- tags
- cohorts
- grouping items
- time range / time granularity
- filtering logic
- stage values
- calculation methods

Among them, event tables and user tables are the underlying data available for analysis. Event attributes and user attributes can be directly used for filtering and grouping. The system also contains derived analytical assets such as virtual events, virtual attributes, and dimension-table attributes. See `data-management-events-and-properties.md` for the sections on "events, event attributes, and user attributes", and `virtual-properties-and-dimension-table-properties.md` for the sections on "virtual attributes and dimension-table attributes".

In addition, **scope alignment should be based on an identified concrete analytical object whenever possible**.  
An "identified object" usually means:
- project_id
- dashboard_id
- report_id
- or SQL / qp / adhoc_query that can directly identify the object
- or previously generated analysis text / screenshots / links

If the customer has not yet provided enough information to identify the object, the first step is not to give a high-confidence scope conclusion, but to request the necessary identifying information.

---

## 2. Core Principle

Always follow this order:

**customer-provided object info / SQL first → ae-cli-assisted retrieval second → SQL-first → reference-validated → customer-confirmed**

And always follow this output strategy:

**Layered Scope Depth**

That means:
1. first request and identify the concrete analytical object from the customer;
2. if the customer cannot provide complete information, then use ae-cli commands to supplement object and query information;
3. then extract the current implementation scope from SQL / query / dashboard;
4. then validate its definition-layer semantics against product reference documents;
5. then provide the customer with a medium-granularity scope explanation;
6. then actively ask whether deeper alignment is needed.

By default, do not expand all details of tags / cohorts / virtual attributes / dimension-table attributes / versions / timezones / update modes at once.  
Only continue drilling down when the customer needs it, or when the current result does not match the customer’s understanding.

In addition, all product queries and expressions should be interpreted in **Trino syntax**, and virtual attributes are also created based on Trino SQL expressions. See `virtual-properties-and-dimension-table-properties.md` for the section on "virtual-attribute expressions", and `creating-virtual-properties-best-practices.md` for the sections on "Trino expressions and virtual-attribute usage".

---

## 3. Scope Depth Strategy

When performing scope alignment, the executor should not assume that all definition details must be expanded at once.  
Instead, the executor should use a **dynamic, layered, confirmation-based** process.

Before entering the next layer, three actions must always be completed:
1. **confirm whether the current layer already satisfies the customer**
2. **preview what finer scope elements can be aligned in the next layer**
3. **clearly request what additional information is needed, and where that information can usually be obtained**

### L1: Current Implementation Layer (default)
By default, first align "how this SQL / query / report is currently being calculated."

At this layer, priority should be given to explaining:
- what is currently being measured
- what is currently included in scope
- what filters are being applied
- what dimensions are being used for grouping
- what time range, time granularity, and calculation method are being used
- how tags / cohorts / virtual attributes / dimension-table attributes are being used in the current analysis

The goal of this layer is:  
to let the customer first confirm whether the **current implementation scope** is correct, rather than immediately entering the object's definition details.

### Required action after L1
After L1, the executor must actively ask whether the current explanation already satisfies the customer’s need.

At the same time, the executor should preview what can be aligned if L2 is entered, for example:
- what type of tag / cohort is being used
- how the virtual attribute is derived
- how the dimension-table attribute is filled
- what the analysis subject is
- what the settlement timezone is
- whether the result is precomputed
- whether version differences may exist

The executor should also explain what extra information may be needed if the customer wants to continue, such as:
- object name
- object type, if known
- definition SQL
- configuration screenshots
- source report / query / dashboard ID
- document keywords

And include the fixed confirmation question:

> Does this logic match the business scope you actually want?

### L2: Definition Interpretation Layer (on demand)
Only enter L2 if the customer explicitly indicates that L1 is not enough.

The goal of this layer is:  
to explain how the tag / cohort / virtual attribute / dimension-table attribute used in the current analysis is actually defined.

At L2, priority should be given to explaining:
- what category the object belongs to
- how the object itself is defined
- what the analysis subject is
- what the settlement timezone is
- what the update mode is
- whether it is precomputed
- whether date versions / dynamic matching are involved
- what business meaning the object actually expresses

### Required action after L2
After L2, the executor must again ask whether the current explanation already satisfies the customer.

At the same time, the executor should preview what can be aligned if L3 is entered, for example:
- boolean logic of condition tags / condition cohorts
- behavioral-sequence rules
- time windows
- associated attributes
- forbidden events
- definition SQL of SQL tags / SQL cohorts / virtual attributes
- historical versions, user history data, result origins, and similar details
- the real business meaning of a virtual-attribute expression
- whether grain is consistent

The executor should also clearly request the additional materials that may be needed, such as:
- condition-configuration screenshots
- definition SQL
- tag-version usage details
- cohort-origin results
- virtual-attribute rules
- dimension-table structure
- the exact scope point the customer wants to verify

And include the fixed confirmation question:

> Does this logic match the business scope you actually want?

### L3: Detail Validation Layer (only when necessary)
Only enter this layer when the customer explicitly asks to confirm detailed rules, or when the conclusion depends on those rules.

The goal of this layer is:  
to validate complex rules, historical scope, boundary conditions, and possible error sources in the definition layer.

This layer should only be entered when:
- the customer explicitly asks to verify detailed definitions of tags / cohorts / virtual attributes / dimension-table attributes
- the customer suspects that the object definition itself is wrong
- the current SQL usage layer seems to conflict with product definition
- historical versions / dynamic matching / settlement timezone / update mode may affect the conclusion
- the current object is an SQL tag / SQL cohort and its definition SQL must be inspected directly
- the current object is a condition tag / condition cohort and detailed checks are needed for sequences, time windows, associated attributes, forbidden events, and similar complex rules
- the current object is a virtual attribute and its expression semantics, grain, field origin, or derivation type affects interpretation

### Default Strategy
If the customer does not explicitly ask for definition-layer detail, the executor should stay at L1 by default.  
If the customer does not explicitly ask to enter L3, the executor should ask first after L2 rather than expanding automatically.

---

## 4. Evidence Priority

When scope is ambiguous, use the following priority order:

1. **explicit implementation logic in the identified object and its SQL / query / dashboard configuration**
2. **product reference documents**
3. **TE’s established product behavior**
4. **the customer’s natural-language expectation**

Notes:
- the customer’s statement defines the target of confirmation, not default fact
- if the current implementation differs from product definition, they must be explained separately
- do not mix up "what the SQL currently does" with "what the product standard semantics normally mean"
- if any definition-layer judgment depends on inference rather than clear evidence, the executor must clearly state that it is inference
- **if no concrete project / dashboard / report / query / SQL has been identified yet, only preliminary or generalized explanation is allowed, and no high-confidence scope conclusion should be given**

---

## 5. Default Workflow

### Step 0: Request object-identification information and SQL first
Before beginning scope alignment, the executor should first request information that can identify the analytical object, especially:
- project_id
- dashboard_id
- report_id
- SQL query conditions

If the customer can directly provide SQL query conditions, scope alignment may start from SQL.  
If the customer cannot provide SQL but can provide project / dashboard / report information, the executor may continue object identification based on that information.  
Only when the customer cannot provide SQL and also cannot provide complete object-identification information should the executor try ae-cli commands to retrieve qp, adhoc_query, or related configuration.

If the object still cannot be identified:
- the executor should not directly give a high-confidence scope conclusion
- instead, the executor should state that only a preliminary explanation is currently possible
- and request project_id, dashboard_id, report_id, or SQL / query / previous analysis output

### Step 1: Identify which layer the customer wants
First determine whether the customer wants:
- only confirmation of how the current query / report is calculated
- or further confirmation of how the tag / cohort / virtual attribute / dimension-table attribute itself is defined
- or even finer alignment such as versions, timezones, and update timing

If the customer does not explicitly specify, start with **L1 current implementation layer**.

### Step 2: Extract current implementation scope
Extract from SQL / query:
- data sources
- statistical object
- event scope
- time range
- time granularity
- filtering structure
- grouping structure
- calculation method
- special handling
- output structure

### Step 3: Trigger deeper checks conditionally
If the following can be judged quickly, further check:
- what category the key fields belong to
- whether grain is consistent
- what business meaning the virtual-attribute expression actually expresses

If these cannot be judged quickly:
- do not force a deep dive
- first ask whether the customer wants alignment at this level of detail
- if the customer agrees, request additional origin/configuration information
- if the customer cannot provide it, then perform deeper checking
- if the final judgment still depends on inference, explicitly mark it as inference

### Step 4: Output a version that is sufficient for confirmation
Use business language to explain:
- what is currently being measured
- within what scope it is being measured
- what filtering is used
- how it is split by dimensions
- how tags / cohorts / virtual attributes / dimension-table attributes are being used

### Step 5: Ask actively whether deeper drill-down is needed
After the first explanation, the executor must actively ask whether further expansion is needed. For example:
- do you only want to confirm how the current query is filtered, grouped, and calculated?
- or do you also want to confirm how this tag / cohort / virtual attribute / dimension-table attribute itself is defined?
- do you want to continue aligning at the level of version, timezone, and update mode?
- does this logic match the business scope you actually want?

If the customer is not familiar with the product, use the simplest possible language first.  
If needed, then add terminology explanation and suggest searchable keywords such as:
- virtual attribute
- dimension-table attribute
- tag
- cohort
- timezone
- date version

### Step 6: Enter finer layers on demand
Only continue into L2 / L3 when the customer explicitly needs it, or when there is a mismatch in understanding.  
If information is still missing before deeper expansion, the executor should first explain the gap and request the missing information rather than directly assuming a definition-layer conclusion.

---

## 6. SQL Parsing Checklist

Do not explain scope based on partial SQL only.  
The following must be checked completely: subqueries, joins, derived fields, where/filter clauses, group by, aggregation logic, and output structure.

### 6.1 Data Sources
Identify:
- source tables
- event tables / user tables / derived tables
- whether exchange-rate tables, mapping tables, tag / cohort result tables, or dimension tables are joined

Questions to answer:
- what category of data source is the result based on?
- is the current result event-level, user-level, record-level, or amount-level?

### 6.2 Statistical Object
Identify the true statistical object:
- event count
- distinct user count
- attribute value
- amount
- per-user value
- stage value
- list-type result
- boolean result
- other aggregated results

Do not guess based only on metric name.

### 6.3 Event Scope
Identify:
- which events are included
- which events are excluded
- whether this is a single-event or multi-event set
- whether this is a formula-type object

### 6.4 Time Range and Time Granularity
Identify:
- partition-filter time
- real business event time
- display timezone / timezone-offset logic
- aggregation granularity (day / week / month / raw time)
- whether stage-window completeness is involved

Rules:
- partition filters must not be treated as final business time range
- performance-layer partition pruning must be separated from business-layer statistical time
- if time has already been shifted into display timezone, business time should be explained using display timezone
- if stage values are involved, incomplete data exclusion must be checked
- if the object depends on a "timezone" mark on an event attribute, that attribute may be part of the timezone-shift logic. See `filtering-data-through-filtering-conditions.md` for the section on "time-based event attributes and timezone shifting".

### 6.5 Filtering Structure
Identify:
- event-attribute filtering
- user-attribute filtering
- tag filtering
- cohort filtering
- virtual-attribute filtering
- dimension-table-attribute filtering
- condition relations (AND / OR)
- filter scope (global / local)
- whether relative time, relative event time, or object-group filtering exists

Interpretation rules:
- filtering determines **which data is included in calculation**. See `filtering-data-through-filtering-conditions.md` for the section on "filtering determines included data scope".
- filtering must not be confused with grouping
- time-based event attributes are compared after shifting to display timezone. See `filtering-data-through-filtering-conditions.md` for the section on "timezone shift of time-based event attributes".
- time-based user attributes and user tags are not shifted. See `filtering-data-through-filtering-conditions.md` for the section on "time handling of user attributes and user tags".
- "days (relative)" in relative event time means 24 hours, not natural calendar days. See `filtering-data-through-filtering-conditions.md` for the section on "relative time".
- if multiple parallel conditions exist, they must be explained as AND or OR. See `filtering-data-through-filtering-conditions.md` for the section on "condition relations".
- if filtering only applies to part of a metric or formula, it must not be described as a global scope. See `filtering-data-through-filtering-conditions.md` for the section on "global / local filtering".

### 6.6 Grouping Structure
Identify:
- grouping-field origin
- single grouping vs cross grouping
- numeric buckets / time grouping / list grouping methods
- whether tags / cohorts / virtual attributes / dimension-table attributes are used for grouping

Interpretation rules:
- grouping determines **how results are split for comparison**. See `comparing-analysis-through-grouping-items.md` for the section on "grouping as result comparison split".
- grouping must not be confused with filtering
- multiple grouping dimensions produce cross-granularity results. See `comparing-analysis-through-grouping-items.md` for the section on "multi-group / cross analysis".

#### Numeric Grouping
Determine whether it is:
- default interval
- discrete number
- custom interval

Important rules:
- default intervals may automatically switch to 12 intervals depending on the number of values
- custom intervals are left-closed and right-open. See `comparing-analysis-through-grouping-items.md` for the section on "numeric grouping interval rules".

#### Time Grouping
Determine whether it is:
- grouped by selected granularity
- not aggregated, but grouped directly by reported time

It is not enough to say "grouped by time"; it must be stated whether it is:
- grouped by day / week / month, etc.
- or grouped directly by raw time values. See `comparing-analysis-through-grouping-items.md` for the section on "time grouping".

#### List Grouping
Determine whether it is:
- by element
- by whole list
- by set of elements

Important rules:
- by element: one record may participate in multiple groups
- by whole list: order and repetition may matter
- by set of elements: deduplicate and sort first, then group by set. See `comparing-analysis-through-grouping-items.md` for the section on "list-type grouping".

### 6.7 Calculation Methods
Identify the exact calculation method.

#### Built-in Basic Methods
- total count
- triggered-user count
- average per user

Important rules:
- total count means event count. See `calculation-method-logic-explanation.md` for the section on "total count".
- triggered-user count means distinct user count. See `calculation-method-logic-explanation.md` for the section on "triggered-user count".
- average per user = total count / triggered-user count. See `calculation-method-logic-explanation.md` for the section on "average per user".

#### Numeric Attribute Methods
Determine whether it is:
- mean
- per-user mean
- median
- Nth percentile
- variance
- standard deviation

Important rules:
- mean = total attribute value / number of attribute values. See `calculation-method-logic-explanation.md` for the section on "mean".
- per-user mean = total attribute value / triggered-user count. See `calculation-method-logic-explanation.md` for the section on "per-user mean".
- median is a positional statistic, not an average. See `calculation-method-logic-explanation.md` for the section on "median".
- percentile reflects distribution position, not mean. See `calculation-method-logic-explanation.md` for the section on "percentile".
- variance / standard deviation reflect fluctuation, not central level. See `calculation-method-logic-explanation.md` for the section on "variance / standard deviation".

#### List-Type Attribute Methods
Determine whether it is:
- list deduplication count
- set deduplication count
- element deduplication count

Important rules:
- whole-list deduplication ≠ set deduplication. See `calculation-method-logic-explanation.md` for the section on "list deduplication vs set deduplication".
- set deduplication ignores order and repetition. See `calculation-method-logic-explanation.md` for the section on "set deduplication".
- element deduplication counts distinct elements across all lists. See `calculation-method-logic-explanation.md` for the section on "element deduplication".

#### Boolean Attribute Methods
Determine whether it is:
- true count
- false count
- null count
- non-null count

Important rules:
- these are event-count scope by default unless the SQL explicitly changes them to user-level. See `calculation-method-logic-explanation.md` for the section on "boolean-attribute counting".

### 6.8 Stage Value Logic
If query or report involves stage values in retention / distribution analysis, the executor must validate the stage-value explanation.

Important rules:
- a stage value is an aggregation over a period, not a single-day value. See `stage-value-logic-explanation.md` for the section on "stage values are not single-day values".
- people-type metrics usually default to stage sum. See `stage-value-logic-explanation.md` for the section on "people-type stage sum".
- rate-type metrics usually default to weighted average, not simple average of daily rates. See `stage-value-logic-explanation.md` for the section on "weighted average for rates".
- simultaneously displayed metrics may follow different logic depending on calculation method and formula form. See `stage-value-logic-explanation.md` for the section on "simultaneously displayed metrics".
- incomplete data may be excluded. See `stage-value-logic-explanation.md` for the section on "incomplete-data exclusion".

Unless there is explicit evidence, stage values must not be explained as "simple average."

### 6.9 Special Handling
Identify:
- timezone shifts
- currency conversion
- null handling
- non-finite-value filtering
- deduplication
- lookup / mapping joins
- local formula logic
- stage-window completeness filtering
- type conversion
- timestamp conversion
- string extraction
- union deduplication
- constant construction

### 6.10 Output Structure
Identify:
- whether the output is detailed or aggregated
- whether it is grouped
- whether it outputs both sequences and totals
- whether it is stage-value output, raw-value output, or grouping output

### 6.11 Field-Origin Type Check (conditional)
When it can be judged quickly, the executor should identify which category each key field belongs to:
- raw event attribute
- raw user attribute
- virtual event attribute
- virtual user attribute
- dimension-table attribute
- tag-result field
- cohort-result field
- other lookup / mapping fields

If it cannot be judged quickly:
- do not force deeper analysis
- first ask whether the customer wants alignment at this layer
- if the customer cannot provide origin information, then inspect further or infer
- if the final judgment is inference, it must be explicitly marked

### 6.12 Grain Consistency Check (conditional)
When it can be judged quickly, the executor should check:
- whether event-level and user-level fields are mixed
- whether the current expression is judging "whether an event satisfies a condition" or "whether a user has a state"
- whether the current distinct key equals what the customer refers to as "people / users / subjects"

If it cannot be judged quickly:
- first ask whether the customer wants to continue alignment at this layer
- if the customer cannot add more information, then inspect further
- if the final judgment still depends on inference, it must be explicitly marked in output

### 6.13 Virtual-Attribute Expression Semantics Check (conditional)
When the key field is a virtual attribute, and when necessary, the executor should determine which expression category it most resembles:
- computational
- type-conversion
- time-conversion
- string-extraction
- concatenation
- condition-judgment
- constant
- dimension-table supplement

Then further determine what it expresses in business meaning:
- event-level condition
- user-level state
- subject-level mapping
- deduplication key
- grouping key
- time-helper field
- other derived semantics

If this cannot be judged quickly, the executor should ask whether the customer wants alignment at this layer.

---

## 7. Usage-Layer Interpretation of Tags, Cohorts, Virtual Attributes, and Dimension-table Attributes

### 7.1 Tags and Cohorts
At the analytical execution layer, tags and cohorts may first be understood abstractly as a type of derived asset of "subject → marked result":

- first column: analysis subject
- second column: marking result

Among them:
- a tag is more like: `subject -> tag value`
- a cohort is more like: `subject -> whether the subject belongs to the cohort`

Therefore, at L1, the executor does not need to expand the definition of the tag / cohort immediately.  
Instead, the executor should first explain:
- which tag / cohort is used in the current query
- whether it is used for filtering or grouping
- which analysis subject it corresponds to
- what impact it has on the current statistical result

A tag is essentially a value assignment to a subject; a cohort is essentially a selected subject set. See `user-tags.md` for the sections on "tags", and `user-cohorts.md` for the sections on "cohorts".

### 7.2 Virtual Attributes
At the usage layer, virtual attributes may first be understood as:
- a derived column added to the event table or user table

Virtual attributes may be created by secondary calculation over event attributes, user attributes, user tags, and similar fields through Trino expressions, and may be used for filtering, grouping, or auxiliary calculation. See `virtual-properties-and-dimension-table-properties.md` for the sections on "virtual attributes", and `creating-virtual-properties-best-practices.md` for the sections on "virtual-attribute expressions".

Therefore, at L1, the executor should first explain:
- which virtual attribute is used in the current query
- whether it is used in filtering, grouping, or calculation
- whether it behaves more like an event-level field or a user-level field
- what the current expression appears to be judging

### 7.3 Dimension-table Attributes
At the usage layer, dimension-table attributes may first be understood as:
- business-information columns automatically supplemented by joining a dimension table using a key-type attribute

Dimension-table attributes may participate in analysis as event attributes or user attributes. See `virtual-properties-and-dimension-table-properties.md` for the sections on "dimension-table attributes".

Therefore, at L1, the executor should first explain:
- which dimension-table attribute is used
- which key-type attribute it is derived from
- whether it is used in filtering, grouping, or explanation of the result

---

## 8. Definition-Layer Drill-down Rules for Tags and Cohorts

When the customer wants to further confirm the definition-level scope of tags / cohorts, the executor should enter the definition layer from the usage layer.

### 8.1 When to Enter the Definition Layer
Continue only in the following cases:
- the customer explicitly asks "how is this tag / cohort defined?"
- the customer suspects the current result differs from their understanding
- the current analytical conclusion highly depends on tag / cohort definition
- the current result involves historical versions / dynamic matching / settlement timezone / update mode
- the current object is an SQL tag / SQL cohort
- the current object is a condition tag / condition cohort and the customer wants complex-rule confirmation

### 8.2 Required actions before entering the definition layer
Before entering the definition layer, the executor must first explain:
1. that only the **usage mode** of the tag / cohort in the current query can be confirmed at present
2. what further items can be aligned if definition-layer analysis continues
3. what additional information is needed, and where it is usually obtained

For example:
- if it is an SQL tag / SQL cohort, definition SQL is needed, usually from the tag/cohort configuration page or creator
- if it is a condition tag / condition cohort, configuration screenshots are needed, usually from the product configuration page
- if it is a result cohort, source report / query / dashboard information is needed
- if historical versions are involved, version-usage details or version date information are needed

### 8.3 What must be confirmed for tag definition
To continue confirming tag definition, at least the following should be confirmed:
- tag type
- tag analysis subject
- tag settlement timezone
- tag update mode and precomputation
- tag version
- further rules for condition / first-last / metric-value tags. Relevant rules are described in `user-tags.md`, `conditional-first-last-metric-value-tags.md`, and `date-versions-of-tags.md`.

#### Tag types
- ID tag
- condition tag
- first-last tag
- metric-value tag
- SQL tag. See `user-tags.md` for the section on "tag types", and `conditional-first-last-metric-value-tags.md` for the section on "condition / first-last / metric-value tags".

#### Tag analysis subject
The "people" in a tag result is not naturally the number of users, but the number of analysis subjects such as `#user_id`, `#account_id`, `#distinct_id`, and so on. See `user-tags.md` for the section on "analysis subject".

#### Tag settlement timezone
If event data is used in tag definition, event time is judged under the tag’s settlement timezone; switching display timezone during analysis does not recompute tag results. See `user-tags.md` for the section on "tag settlement timezone".

#### Tag update mode and precomputation
Tags are precomputed data, not ad hoc computations each time they are used. Their results may be affected by automatic update, manual update, create/edit recalculation, and similar operations. See `user-tags.md` for the section on "update mode and precomputation".

#### Tag version
For data-condition tags, tag values may change with each calculation; historical analysis requires confirmation of whether the latest version, dynamic matching, or a historical version is being used. See `date-versions-of-tags.md` for the section on "tag date version".

#### Further details for condition / first-last / metric-value tags
- condition tag: confirm condition type, boolean combination, tag-value priority order, and whether behavioral sequence is involved. See `conditional-first-last-metric-value-tags.md` for the section on "condition tags".
- first-last tag: confirm whether it uses first or last occurrence, which attribute value is taken, and whether an empty attribute prevents tagging. See `conditional-first-last-metric-value-tags.md` for the section on "first-last tags".
- metric-value tag: confirm time period, attribute, aggregation method, whether formulas are used, and how formula calculation failure is handled. See `conditional-first-last-metric-value-tags.md` for the section on "metric-value tags".

### 8.4 What must be confirmed for cohort definition
To continue confirming cohort definition, at least the following should be confirmed:
- cohort type
- cohort origin
- cohort analysis subject
- cohort settlement timezone
- cohort update mode and precomputation
- further rules of condition cohorts. Relevant rules are described in `user-cohorts.md` and `conditional-cohorts.md`.

#### Cohort types
- ID cohort
- result cohort
- condition cohort
- SQL cohort. See `user-cohorts.md` for the section on "cohort types".

#### Cohort origin
If it is a result cohort, further trace which analytical result and which "people-type result" it comes from. See `user-cohorts.md` for the section on "result cohort origin".

#### Cohort analysis subject
The "people" in a cohort is also the number of analysis subjects, not naturally the number of users. See `user-cohorts.md` for the section on "analysis subject".

#### Cohort settlement timezone
If event data is used in condition cohorts / SQL cohorts, time conditions are judged using the cohort settlement timezone; switching display timezone does not recompute cohort results. See `user-cohorts.md` for the section on "cohort settlement timezone".

#### Cohort update mode and precomputation
Cohorts are precomputed data and may be updated by schedule, manually, following recalculation, system trigger, create calculation, edit calculation, and similar mechanisms. See `user-cohorts.md` for the section on "update mode and precomputation".

#### Further details of condition cohorts
If the cohort is a condition cohort and the customer wants further rule confirmation, the following should be confirmed:
- condition type (did / did not / did in sequence / did not in sequence / attribute satisfied)
- how conditions are combined
- whether the behavioral sequence is strictly ordered
- whether all steps must fall within the time range
- whether associated attributes exist
- whether forbidden events between steps exist
- whether the time window is judged in 24 hours
- whether special sequence cases are triggered. See `conditional-cohorts.md` for the sections on "condition types, sequence, time windows, associated attributes, and forbidden events".

### 8.5 Rules for SQL tags / SQL cohorts
If the customer asks to confirm the definition-level scope of an SQL tag / SQL cohort but its definition SQL is not provided in the current conversation, the executor should clearly state:
- only its usage in the current query can be explained
- definition SQL or configuration screenshots are required to confirm the definition-layer scope

The executor should not infer the definition logic of an SQL tag / SQL cohort without its definition SQL.

### 8.6 Virtual-Attribute Definition Layer
To continue confirming virtual-attribute definition, at least the following should be confirmed:
- whether it is a virtual user attribute or a virtual event attribute
- what its expression rule is
- which original fields / tags / attributes it depends on
- what its data type is
- whether it is used in filtering, grouping, or calculation
- what business meaning it expresses
- whether it is closer to an event-level condition or a user-level state
- whether failed type conversion to null, time conversion, union deduplication, condition judgment, and similar situations are involved. See `virtual-properties-and-dimension-table-properties.md` for the sections on "virtual-attribute types and field dependency", and `creating-virtual-properties-best-practices.md` for the sections on "expression semantics and common pitfalls".

### 8.7 Dimension-table-Attribute Definition Layer
To continue confirming dimension-table-attribute definition, at least the following should be confirmed:
- which original key-type attribute it depends on
- whether the dimension-table primary key matches the source-attribute type
- whether the supplemented value is a display name or business information
- whether it comes from list / time / text / numeric / boolean attributes
- whether there are constraints such as object / object-group fields not being directly attachable to dimension tables. See `virtual-properties-and-dimension-table-properties.md` for the sections on "dimension-table attributes".

### 8.8 Rules for SQL tags / SQL cohorts / complex virtual attributes
If the customer asks to confirm the definition-level scope of an SQL tag / SQL cohort / complex virtual attribute, but no definition SQL or configuration is provided, the executor should clearly state:
- only its usage in the current query can be explained
- definition SQL or configuration screenshots are required to confirm its definition-layer scope

The executor should not infer its definition logic without definition SQL or configuration.

---

## 9. Further Rules for Condition-Type Tags / Cohorts (expand only when needed)

### 9.1 Condition Tags
Condition tags support:
- did
- did not
- attribute satisfied
- behavioral sequence conditions. See `conditional-first-last-metric-value-tags.md` for the section on "condition tags".

A tag may contain multiple tag values, but one subject can hit only one tag value, following tag-value priority order. See `conditional-first-last-metric-value-tags.md` for the section on "tag-value priority order".

### 9.2 First/Last Tags
First/last tags take the attribute value at the first/last target behavior occurrence, rather than a period-level aggregated value. If the selected attribute is empty, the tag value cannot be obtained. Time-based attributes are taken after timezone adjustment under the tag timezone. See `conditional-first-last-metric-value-tags.md` for the section on "first-last tags".

### 9.3 Metric-Value Tags
Metric-value tags use the aggregated attribute result within a specified period as the tag value, and also support formula-based definition. If some events are absent from the formula, their missing part is treated as 0; if the formula cannot be calculated, such as division by zero, the tag cannot be assigned. See `conditional-first-last-metric-value-tags.md` for the section on "metric-value tags".

### 9.4 Condition Cohorts
Condition cohorts support:
- did
- did not
- did in sequence
- did not in sequence
- attribute satisfied. See `conditional-cohorts.md` for the section on "condition types".

Condition combinations in condition cohorts are not simple flat combinations; conditions of the same type are combined first, and then logic is applied across major groups. See `conditional-cohorts.md` for the section on "condition combination logic".

### 9.5 Sequence-Type Condition Cohorts
If the cohort is "did in sequence" / "did not in sequence", the following still need to be confirmed:
- whether the order is strict
- whether all steps are within the time range
- whether associated attributes exist
- whether forbidden events between steps exist
- whether "days" in the time window means 24-hour windows
- whether special cases are triggered, such as repeated events, virtual events, or overlap between forbidden events and step events. See `conditional-cohorts.md` for the section on "behavior sequence and time windows".

---

## 10. Reference Mapping

### Stage-value issues
Check `stage-value-logic-explanation.md` for:
- stage values are aggregated over a period, not single-day values
- people-type metrics usually default to stage sum
- rate-type metrics usually default to weighted average
- incomplete data may be excluded

### Filtering issues
Check `filtering-data-through-filtering-conditions.md` for:
- event-attribute / user-attribute / tag / cohort filtering
- condition relations
- global / local filtering
- relative time and timezone rules

### Grouping issues
Check `comparing-analysis-through-grouping-items.md` for:
- grouping splits results, not filtering
- multiple groupings form cross-granularity
- numeric intervals, time grouping, and list grouping

### Calculation-method issues
Check `calculation-method-logic-explanation.md` for:
- count / users / per-user metrics
- mean / per-user mean / median / percentile
- variance / standard deviation
- list deduplication
- boolean counting

### Tag issues
Check `user-tags.md`, `conditional-first-last-metric-value-tags.md`, and `date-versions-of-tags.md`.

### Cohort issues
Check `user-cohorts.md` and `conditional-cohorts.md`.

### Event / attribute / virtual event / virtual attribute / dimension-table-attribute issues
Check `data-management-events-and-properties.md`, `virtual-properties-and-dimension-table-properties.md`, and `creating-virtual-properties-best-practices.md`.

---

## 11. Default Output Template for Customer-Facing Replies

The default output should follow a "coarse first, then finer" structure, and should try to achieve the following in complex cases:
- conclusion first
- evidence second
- items still to be confirmed third
- clear ordering, avoiding mixing filtering, grouping, calculation method, and object definition

### 11.0 Default handling when the object is not yet identified
If the customer has not yet provided enough information to identify the analytical object, the executor should first request identification information rather than directly giving a high-confidence scope conclusion.

Request first:
- project_id
- dashboard_id
- report_id
- SQL query conditions

If these are unavailable, request:
- qp / adhoc_query
- previously generated output text
- report / dashboard links or screenshots

Only if the customer still cannot provide complete information should the executor use ae-cli commands to retrieve query, adhoc_query, or configuration information.

Suggested wording:

> To align the scope accurately, the first step is to identify which analytical object you are referring to.  
> You may first provide:
> - project_id
> - dashboard_id
> - report_id
> - or the SQL query conditions for this analysis
>
> If you do not have these, you may also send the report / dashboard link, screenshots, or previous generated output text.  
> If none of these are available for now, the next step is to try retrieving the relevant information through system tools.  
> Before the object is clearly identified, only a preliminary explanation can be given, not a final scope confirmation.

### First-round default output (L1)
The following order is recommended:

#### A. What is currently being measured
- statistical object
- metric meaning
- statistical subject

#### B. What is the current analytical scope
- event scope
- time range
- time granularity

#### C. What restrictions are currently applied
- filtering conditions
- whether tags / cohorts / virtual attributes / dimension-table attributes / attribute restrictions are used
- whether the condition is global or local

#### D. How the result is split
- grouping dimensions
- whether the object is used for filtering or grouping here

#### E. How the result is calculated
- count / distinct count / sum / avg / stage value, etc.
- whether special handling exists, such as timezone, exchange rate, deduplication, invalid-value filtering, or expression-derived logic

#### F. What has not yet been expanded
- whether the object’s own definition has not yet been expanded
- whether version / timezone / update-mode definition-layer information has not yet been expanded

#### G. If the current scope may differ from customer expectation
Point it out directly, for example:
- what the current logic is more like
- which business state in the customer’s wording it does not fully equal
- ask the customer whether this matches expectation

For example:

> The current logic is closer to judging **[current implementation semantics]**,  
> rather than exactly **[customer’s natural-language expectation]**.  
> Does this logic match the business scope you actually want?

### Fixed follow-up after the first round
After the first-round explanation, the executor must actively ask whether the customer’s need has been met, and must also complete:
1. confirm whether the current layer is sufficient
2. preview what can still be aligned at the next layer
3. request the information needed for further drill-down

Suggested wording:

> What has been aligned first is “how this query / report is currently filtered, grouped, and calculated.”  
> If this level already answers your question, it can stop here.  
> If needed, further alignment can continue, for example:
> - what type of tag / cohort / virtual attribute / dimension-table attribute this object belongs to
> - how it is actually defined
> - what its analysis subject, settlement timezone, update mode, and version logic are
>
> If you want to continue drilling down, please state which point you most want to confirm next.  
> For SQL tags / SQL cohorts / complex virtual attributes, definition SQL is needed.  
> For condition-type objects, configuration screenshots or rule descriptions are needed.  
> For result cohorts, source report / query / dashboard information is needed.

### Second-round output (L2)
If the customer chooses to continue with definition-layer confirmation, then the second round should add:
- object type
- analysis subject
- settlement timezone
- update mode
- whether it is precomputed
- date version / dynamic matching
- whether definition SQL / rule configuration is required

After the second round, ask again whether further detail is needed, and preview:
- what finer rules can still be checked
- what additional materials are still needed

### Third-round output (L3)
If the customer continues to request finer validation, then the third round should expand:
- boolean logic of condition tags / condition cohorts
- sequence rules
- time windows
- associated attributes
- special edge conditions
- historical version / user history data / result-origin details
- virtual-attribute expression semantics
- grain-consistency issues

### Long conversation / high token-cost handling
If the conversation is too long and backtracking history becomes costly, request the customer to provide:
- reminders of previous analysis results
- or the original text
- or relevant SQL / query / report screenshots

And clearly explain that this is to avoid scope misjudgment based on incomplete context.

---

## 12. Common Pitfalls

- do not assume that all details should be explained at once
- do not confuse tags and cohorts
- do not treat the current usage mode of an object as its definition mode
- do not confuse display timezone with tag / cohort settlement timezone
- do not confuse result-page refresh with object recomputation
- do not treat partition filtering as business time range directly
- do not default to explaining stage values as simple averages
- do not treat relative-day / time-window days as natural calendar days
- do not directly treat the result of a virtual-attribute expression as the customer’s intended business state
- do not ignore semantic bias caused by mixing event-level and user-level fields
- do not pretend to know the definition logic of complex objects when definition SQL / configuration is missing
- do not give a high-confidence final scope conclusion before the analytical object is identified

---

## 13. Completion Standard

### If the target is L1
The following must be made clear:
- statistical object
- analytical scope
- filtering
- grouping
- time logic
- calculation method
- how tags / cohorts / virtual attributes / dimension-table attributes are used in the current query
- whether the current logic matches the business scope the customer wants, and if uncertain, confirmation must be requested

### If the target is L2 / L3
The following must also be made clear:
- object type
- analysis subject
- settlement timezone
- update mode
- whether it is precomputed
- whether date versions / dynamic matching are used
- whether definition SQL / configuration must be checked
- if any key judgment depends on inference, it must be explicitly stated as inference