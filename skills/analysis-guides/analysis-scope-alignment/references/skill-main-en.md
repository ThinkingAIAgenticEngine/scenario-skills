## 1. Capability Metadata

This section answers three questions:
1. What is this capability
2. What problem does it solve
3. Under what circumstances should it be enabled

### 1.1 Capability Name
- Name: `analysis-scope-alignment`

### 1.2 Purpose

- This capability is used to:
  - Confirm the statistical scope of the current analysis result, dashboard, report, query, SQL, or prior agent-generated output based on a **clearly identified analysis object**;
  - Express the current scope in a way the customer can understand, and discuss and confirm it with the customer;
  - Confirm with the customer whether the current scope matches their business understanding and analytical goal;
  - When needed, further drill down into definition-layer scope details such as tags, cohorts, virtual attributes, dimension-table attributes, time, filters, grouping, calculation methods, versions, and time zones;
  - After scope confirmation, provide clear input for subsequent SQL adjustment, analysis redesign, logic reconstruction, or report generation.

- Main problems this capability solves:
  - Helping customers understand exactly what scope the current dashboard / report / query / agent-generated result is using;
  - Confirming whether the scope of the current output matches the customer’s understanding;
  - Determining whether the current scope actually answers the customer’s real question;
  - When the current scope does not match the customer’s expectation, helping identify the difference and continue discussing a more suitable new scope;
  - In cases involving tags, cohorts, virtual attributes, dimension-table attributes, complex filters, complex grouping, stage values, and calculation methods, preventing customers from mistaking “current implementation semantics” for “business definition semantics”;
  - Ensuring scope is confirmed before continuing into report generation, SQL rewriting, or analysis logic adjustment, so analysis does not proceed on the wrong definition.

- Applicable objects:
  - Analysis objects the customer can access in the current MCP or current conversation context, including:
    - Project
    - Dashboard
    - Report
    - SQL query
    - query / adhoc_query / qp
    - Tag
    - Grouping item
    - Metric
    - Existing analysis conclusions or analysis results produced in previous conversation turns
  - SQL query conditions, screenshots, links, and prior agent outputs provided in the current conversation;
  - Events, event attributes, user attributes, virtual events, virtual attributes, dimension-table attributes, tags, cohorts, grouping items, filters, time granularity, stage values, and calculation methods related to analytical scope.

### 1.3 When to Use

- Use this capability when the user wants to:
  - Align the statistical scope of a dashboard, report, metric, tag, grouping item, query, or analysis result;
  - Explain the meaning of an analysis result;
  - Explain how an analysis result was calculated;
  - Confirm “who the users are,” “how they entered the counting range,” and “how they were excluded” in a result;
  - Verify data source and definition, such as confirming what a tag, cohort, virtual attribute, or dimension-table attribute means in the current analysis;
  - Compare scope differences across different reports, queries, or analysis results;
  - Judge whether the current result already answers the customer’s real question;
  - Confirm the current scope before generating a report, continuing analysis, rewriting SQL, or proposing optimizations;
  - Discuss whether the current scope satisfies the business question, and identify which definition points need adjustment.

- Typical scenarios:
  - “Please help me align the calculation scope of this dashboard.”
  - “Tell me which users are included in this analysis.”
  - “What does the result for this tagged audience mean?”
  - “Help me see why these two reports have different metric values.”
  - “Please explain how this query / report is currently filtering, grouping, and calculating.”
  - “Check and align the calculation differences of metric XXX across different reports.”
  - “Do not generate the report yet; first help me confirm whether the scope is correct.”
  - “What rules is this retention actually using?”
  - “How is this tag value defined?”
  - “Are the people filtered by this virtual attribute really the people I want?”
  - “What role do this cohort and this tag each play here?”
  - “Before generating the report, first help me confirm the current scope.”

- Not recommended to use directly for:
  - Pure result polishing or pure wording rewrite tasks;
  - General report generation that does not involve scope confirmation;
  - Generic business consultation with no analysis object, no definition object, and no result context.

- Intent signals this capability should recognize:
  - **Identification information and analysis object**
    - project_id
    - dashboard_id
    - report_id
    - qp / adhoc_query
    - SQL query conditions
    - prior agent output text / screenshots / links
  - **Metric / feature names**
    - Such as DAU, retention, ARPU, tag values, cohorts, stage values, virtual attributes, etc.
  - **Scope object**
    - A single dashboard / single report / single query
    - Comparison between multiple dashboards / reports
    - Tags / cohorts / virtual attributes / dimension-table attributes / metrics / grouping items / filter items
  - **Time scope**
    - Daily / weekly / monthly
    - Specified date range
    - Display timezone / settlement timezone / version time
  - **Alignment target**
    - Only confirm the current implementation scope
    - Continue confirming definition-layer scope
    - Continue confirming detailed rules / boundary conditions
  - **Priority / allowed change**
    - Default to explanation and confirmation first
    - If rewriting is needed, it is limited to analysis-layer / SQL-layer adjustment
    - Direct modification of underlying database tables is strictly forbidden

### 1.4 Entry Points

- Ways this capability can be triggered:
  - Customer’s natural-language request;
  - The customer provides project_id / dashboard_id / report_id and asks for scope explanation;
  - The customer provides SQL, or the agent retrieves query / adhoc_query conditions from MCP tools, and the customer asks for explanation of the current statistical logic;
  - The customer references a previous agent-generated analysis result and asks to explain or confirm its scope;
  - The agent proactively asks whether the customer wants to align / explain analytical scope, and this capability is triggered after a positive response;
  - Before report generation, SQL rewriting, or analysis logic reconstruction, the system or execution flow determines that scope should be confirmed first;
  - The user asks about tag definition, grouping-item definition, time granularity, time range, filter conditions, stage-value aggregation, or calculation method;
  - The user explicitly inputs the fixed command `scope-alignment`
    - When this command appears, the skill must be triggered;
    - Then first confirm which object the customer wants to align, such as project, dashboard, report, query, SQL, tag, cohort, virtual attribute, metric, etc.;
  - When the conversation enters a stage of discussing whether the result matches expectation, this capability should be triggered with priority to complete scope confirmation first;
  - If the user asks about objects such as tags, cohorts, virtual attributes, or dimension-table attributes, but these are not yet tied to a specific analysis object, this capability may still be triggered in order to:
    - provide preliminary explanation;
    - attempt object identification;
    - or clearly state that the discussion can only stay at object-level general explanation / usage-layer explanation and cannot yet be treated as a concrete scope-confirmation conclusion.

- Trigger signals:
  - **Certain keywords appear**
    - scope
    - granularity
    - tag definition
    - cohort definition
    - virtual attribute
    - dimension-table attribute
    - grouping item
    - calculation method
    - stage value
    - aggregation method
    - timezone
    - version
    - statistical logic
    - time range
    - time granularity
    - retention
    - DAU
    - ARPU
    - tag value
    - audience definition
    - “who are these people”
    - “what does this result mean”
  - **Certain operations are involved**
    - creating tags
    - choosing a cohort
    - choosing a virtual attribute
    - choosing a dimension-table attribute
    - choosing a grouping item
    - choosing a time granularity
    - discussing whether analysis results match expectations
    - confirming statistical scope before generating an analysis report
  - **Input objects include**
    - SQL
    - query / qp / adhoc_query
    - dashboard / report / panel
    - tag name
    - grouping item name
    - metric name
  - **The following high-risk semantics appear and should trigger this capability with priority**
    - The customer interprets a technical field as a business state
    - The customer treats the current usage of a tag / cohort / virtual attribute as its definition
    - The customer asks “Is this the people / metric / retention / paying user I want?”
    - The customer asks “Why is this result different from what I expected?”
  - **User intent includes**
    - “Explain this result”
    - “Confirm the definition”
    - “Compare why these two results are different”
    - “Confirm the scope before continuing the analysis”
  - **Trigger-boundary supplement**
    - If the current question involves tags, cohorts, virtual attributes, or dimension-table attributes, but lacks concrete analysis-object context, this capability can still be triggered;
    - But in this case the default goal should be:
      - preliminary explanation;
      - attempt to identify the object;
      - or indicate that high-confidence concrete scope confirmation cannot yet be completed;
    - It must not pretend that scope alignment has already been completed for a specific report / query / SQL when concrete object context is missing.

- Operational boundary:
  - **Allowed**
    - Explain the current scope
    - Compare the current scope with the customer’s expectation
    - Propose new scope options
    - Provide new SQL query statements or new query-logic suggestions
  - **Strictly not allowed**
    - Make any direct modification to underlying database tables
    - Write the customer’s expectation into analysis conclusions as an established fact before scope confirmation is completed

### 1.5 Prerequisites

- Before formal scope alignment begins, the execution agent must first attempt to identify the analysis object.
- If convenient for the customer, they may first provide:
  - project_id
  - dashboard_id
  - report_id
  - SQL query conditions
- If the customer cannot provide complete information, or cannot clearly describe object context, MCP tools should be used to supplement:
  - qp
  - adhoc_query
  - related configuration or object information
- If object identification still fails:
  - the agent may only provide preliminary explanation or generalized explanation;
  - it must not output a high-confidence final scope conclusion;
  - it must clearly state which object-identification information is still missing.

### 1.6 First Action After Trigger

- First confirm which concrete analysis object the customer wants to align.
- If convenient for the customer, they may first provide:
  - project_id
  - dashboard_id
  - report_id
  - SQL query conditions
- If the customer can directly provide SQL, prioritize explaining the current implementation scope based on SQL;
- If the customer cannot provide complete object information, use system tools to identify the specific query / adhoc_query / related configuration;
- If the customer provides a previous agent-generated analysis result, first attempt object identification based on the original text, screenshot, link, or related SQL;
- Before the object is clearly identified, do not directly enter high-confidence definition-layer explanation.

### 1.7 Non-Trigger / Caution Cases

- The customer is only asking for result polishing or wording rewrite, without statistical scope confirmation;
- The customer only wants a general report generated, without checking the current analytical definition;
- The customer has not provided an analysis object, definition object, or result context, and the question is only generic business consultation;
- The real task is “create a new analysis” or “create a new scope,” rather than explain or confirm an existing scope;
- When only general product explanation can be given, the agent must not pretend that specific scope confirmation has already been completed;
- If the object has not been clearly identified, only preliminary explanation can be given, and no high-confidence final conclusion should be output;
- If the question involves tags, cohorts, virtual attributes, or dimension-table attributes, but is not yet tied to a concrete analysis object, this capability may still be cautiously triggered in order to:
  - provide preliminary explanation of the object;
  - attempt object identification;
  - or clarify that the discussion can only remain at general object explanation / usage-layer explanation;
  - but it must not pretend that concrete scope confirmation has already been completed for a specific report / query / SQL.

### 1.8 Boundary Positioning

- The core of this capability is not directly rewriting SQL, nor directly generating reports;
- The core of this capability is:
  1. First identify the object
  2. Recognize the current implementation scope
  3. Explain it in language the customer can understand
  4. Confirm with the customer whether it matches expectation
  5. If needed, continue drilling down or propose new scope options

- Therefore, it is better positioned as a prerequisite step for tasks such as:
  - SQL rewriting
  - new analysis-plan design
  - report generation
  - customer communication
  - result review

## 2. Goal & Operating Principles

This section defines the principles the agent should follow once this capability is triggered.

### 2.1 Primary Goal

- Primary goals:
  - Help the customer accurately identify the statistical scope of the current analysis result based on a **clearly identified analysis object**;
  - Express the current scope in a form that is easy for the customer to understand, discuss, and confirm;
  - Confirm with the customer whether the current scope matches their business question, business understanding, and analytical goal;
  - When necessary, continue drilling down into definition-layer details such as tags, cohorts, virtual attributes, dimension-table attributes, filters, grouping, time, timezone, version, and calculation method;
  - Complete scope confirmation before subsequent analysis, SQL rewriting, report generation, or logic reconstruction.

- Secondary goals:
  - Help the customer identify differences between “current implementation semantics” and “expected semantics”;
  - Help the customer determine whether L2 / L3 drill-down is needed;
  - When the customer’s current scope does not satisfy the business question, assist in proposing discussable new scope directions;
  - Provide clear, stable, reusable scope input for subsequent SQL adjustment, analysis reconstruction, and report writing.

- Success Criteria:

  #### A. Completion criteria the agent can judge directly
  - The analysis object has been identified; if not yet identified, the agent has clearly stated what identification information is still missing;
  - The agent has clearly stated the object or input source on which the current explanation is based, such as:
    - project / dashboard / report
    - SQL
    - query / adhoc_query
    - original text or screenshots of prior analysis results
  - The key components of the current implementation scope have been covered; if information is sufficient, this includes at least:
    - statistical object
    - statistical range
    - filter conditions
    - grouping method
    - time range / time granularity
    - calculation method
  - The agent has clearly distinguished:
    - current implementation logic
    - customer’s expected definition
  - If there is insufficient information, unclear field source, unclear granularity, or missing definition evidence, the agent has explicitly marked:
    - pending confirmation
    - inference
    - information still needed from the customer
  - If further drill-down is needed, the agent has clearly stated:
    - what can still be aligned at the next layer
    - what information is still missing
    - what materials are recommended from the customer
  - Before scope confirmation is complete, the agent has not directly produced a final analytical conclusion, final report, or final SQL plan that depends on that scope;
  - Before scope confirmation is complete, the agent has not written the customer’s expectation as if it were an already established fact.

  #### B. Confirmation criteria requiring customer feedback
  - The customer explicitly indicates one of the following:
    - the current explanation already satisfies the need; or
    - further drill-down is required; or
    - the current scope does not match expectation and needs further adjustment.

### 2.2 Priority Principles

- Default priority order:
  1. **Identify the analysis object first**
  2. **Ask the customer for information first, then consider MCP-assisted retrieval**
  3. **Confirm the current implementation scope first, then decide whether to enter the definition layer**
  4. **Ensure correctness before pursuing completeness**
  5. **Separate known, unknown, and inferred information before giving a conclusion**
  6. **Confirm whether the customer’s question has been satisfied before going into finer granularity**
  7. **Only after that, consider proposing new scope options or downstream adjustment suggestions**

- Specific priority principles:
  - **Object identification takes priority over scope explanation**
    - Before project / dashboard / report / SQL / query is identified, no high-confidence final scope conclusion should be output.
  - **Customer-provided information takes priority over system-assisted retrieval**
    - Prefer asking the customer for:
      - project_id
      - dashboard_id
      - report_id
      - SQL query conditions
    - If the customer cannot provide complete information, then use MCP tools to supplement qp, adhoc_query, or related configuration.
  - **SQL evidence takes priority over generalized understanding**
    - If the customer provides SQL, prioritize explaining the current implementation scope based on SQL.
  - **Current implementation takes priority over definition layer**
    - First explain “how this result is currently being counted,” then decide whether to expand into “how the object itself is defined.”
  - **Confirmation takes priority over expansion**
    - After each layer of explanation, first confirm whether the customer is already satisfied, instead of automatically expanding all details.
  - **Correctness takes priority over completeness**
    - If a certain part cannot yet be confirmed, it should be explicitly written as “pending confirmation” or “inference,” rather than being force-filled for completeness.
  - **Scope confirmation takes priority over downstream actions**
    - Before scope is confirmed, the agent should not directly move into:
      - report generation
      - SQL rewriting
      - finalization of analytical conclusions
      - finalization of optimization proposals

### 2.3 Style Requirements

- Output style:
  - Concise but still logical;
  - Structured;
  - Centered on “how the current result is actually produced”;
  - Prefer customer-friendly language;
  - Introduce technical terminology only when necessary.

- Explanation style:
  - First state what is being counted;
  - Then explain range, filters, grouping, time, and calculation method;
  - Then explain which definition-layer content has not yet been expanded;
  - If it differs from customer expectation, explicitly point out the difference;
  - In every round, prompt whether the customer wants further drill-down.

- Customer communication style:
  - Prefer the simplest wording when asking for information;
  - Do not assume the customer is familiar with product terminology;
  - If the customer is unfamiliar with terminology, then add term explanations or suggest searchable keywords;
  - When asking the customer to provide more information, clearly explain **why** that information is needed;
  - Avoid sounding like an interrogation by listing system fields one after another; instead explain that these fields are for accurate object identification.

- Result-expression style:
  - Distinguish three types of information:
    - confirmed
    - pending confirmation
    - inference
  - Do not write inference as fact;
  - Do not write the customer’s desired scope as if it were the current actual scope;
  - Do not write the current usage pattern as if it were the object’s own definition pattern.

### 2.4 Hard Constraints

- Must always be respected:
  - Do not output a high-confidence final scope conclusion before the analysis object is identified;
  - Do not skip object identification and directly assume the customer is referring to a specific dashboard / report / SQL;
  - Do not make high-risk inference without confirmed context;
  - Do not treat the customer’s business expectation as the current implementation fact;
  - Do not fabricate claims such as “confirmed,” “verified,” “identified,” or “retrieved”;
  - Do not pretend the definition layer has already been confirmed when information is insufficient;
  - Do not silently expand the task scope by turning “scope confirmation” into “new analysis design” or “new report output”;
  - Do not directly modify underlying database tables;
  - Do not generate final analytical conclusions that depend on an unconfirmed scope.

- Requirements for uncertainty:
  - For all uncertain content, explicitly mark:
    - this is inference
    - this is pending confirmation
    - more information is needed from the customer
  - If MCP retrieval results conflict with customer-provided information, go back to customer confirmation rather than arbitrating on the customer’s behalf.

### 2.5 Default Operating Behaviors

- By default, first do:
  1. Request object-identification information
  2. Explain the current implementation scope
  3. Ask whether further drill-down is needed

- By default, do not:
  - Automatically continue into the definition layer;
  - Automatically continue into complex-rule verification;
  - Automatically rewrite SQL;
  - Automatically generate an analysis report;
  - Automatically treat the current scope as the correct business scope.

- By default, pause deeper analysis in the following situations:
  - The object is not identified;
  - SQL is not available and MCP cannot reliably supplement it;
  - Definition SQL or configuration is missing for tags / cohorts / virtual attributes;
  - Granularity judgment or field-source judgment can only rely on guessing;
  - The customer has not clearly requested drill-down into finer layers.

### 2.6 Conflict Handling Principles

- When the following conflicts appear, they must be explicitly separated:
  - customer expectation vs current SQL implementation
  - current usage pattern vs object definition pattern
  - display timezone vs settlement timezone
  - current result-page refresh vs object recomputation
  - current query logic vs standard product semantics
  - customer statement vs MCP retrieval result

- Handling method:
  - First state both sides separately;
  - Then explain which side the current evidence supports more strongly;
  - If it still cannot be confirmed, explicitly mark it as “pending confirmation”;
  - When needed, ask the customer for:
    - SQL
    - configuration screenshots
    - version usage mode
    - dashboard / report / query source information

### 2.7 Desired End State

- Completion state the agent can perceive:
  - The analysis object has been identified, or missing identification information has been clearly stated;
  - The key components of the current implementation scope have been explained;
  - The current implementation logic and the customer’s expected definition have been clearly distinguished;
  - Pending / inferred parts have been marked;
  - It has been explained what the next layer can still verify and what information is still missing if drill-down continues;
  - The agent has proactively asked whether the current explanation satisfies the need.

- Completion state requiring customer feedback:
  - The customer clearly indicates that the current explanation is sufficient; or
  - The customer clearly indicates that further drill-down is needed; or
  - The customer clearly indicates that the current scope does not match expectation and requires adjustment.

## 3. Workflow

This section defines the order in which the agent should execute once this capability is triggered, and how decisions should be made under different information conditions.

### 3.1 Overall Flow

By default, follow this process:

1. **Recognize whether this capability should be triggered**
2. **Identify the analysis object**
3. **Collect input materials for the current implementation scope**
4. **Decide which layer the current explanation should stop at**
5. **Extract and explain the current implementation scope (L1)**
6. **Perform the fixed confirmation action after each round of scope output**
7. **Ask whether the customer wants further drill-down**
8. **Enter the definition-explanation layer as needed (L2)**
9. **Again perform the fixed confirmation action after each round of scope output**
10. **Again ask whether the customer wants further drill-down**
11. **Enter the detailed-validation layer as needed (L3)**
12. **When the current scope does not match expectation, provide recommended scope options**
13. **Produce a reusable scope-confirmation result**
14. **After scope confirmation, decide whether to continue into downstream actions**

Default overall principles:

- **customer-provided object info / SQL first**
- **MCP-assisted retrieval second**
- **SQL-first**
- **reference-validated**
- **customer-confirmed**

### 3.2 Step 1: Recognize Whether to Trigger This Capability

The agent first judges whether the current task is a “scope-confirmation task.”

#### Situations that should trigger this capability
If the current request involves any of the following goals, this capability should be triggered:
- explaining what an analysis result means
- explaining how a result is calculated
- aligning the statistical scope of a dashboard / report / query / SQL
- confirming the role of a tag / cohort / virtual attribute / dimension-table attribute in the current analysis
- comparing why two results differ
- confirming current scope before continuing analysis, writing a report, or rewriting SQL
- discussing whether the current result matches the customer’s business expectation

#### Forced trigger command
If the user explicitly inputs the fixed command `scope-alignment`, this capability must be triggered immediately, without fuzzy judgment about whether it applies.

Once triggered, immediately enter:
1. object identification
2. current implementation-scope extraction
3. layered explanation and confirmation flow

#### Situations that should not directly trigger this capability
If the current request is only:
- pure wording polishing
- general report generation without scope issues
- generic business consultation
- product-function introduction unrelated to a concrete analysis object

then the full scope-confirmation workflow should not be entered directly.

#### Default action after trigger
Once the capability is judged to apply:
- do not immediately explain the final scope;
- first enter the **object identification** step.

### 3.3 Step 2: Object Identification

Before formally explaining scope, the agent must first identify which specific analysis object the customer is referring to.

#### Information the customer may preferably provide
If convenient for the customer, they may preferably provide:
- project_id
- dashboard_id
- report_id
- SQL query conditions

#### Acceptable alternative inputs
If the customer does not have the above fields, the following are also acceptable:
- qp / adhoc_query
- dashboard / report / panel links
- report or result screenshots
- previous agent output text
- tag name / cohort name / metric name / grouping-item name (though these are usually not sufficient for independent identification)

#### System-tool usage order
- Prioritize using information the customer has already provided;
- If the customer cannot provide complete object information, then use system tools to retrieve:
  - query
  - adhoc_query
  - report configuration
  - object-related context

#### If the object still cannot be identified
If identification still fails:
- the agent may only provide **preliminary explanation / generalized explanation**
- it must clearly state what object-identification information is still missing
- it must not output a high-confidence final scope conclusion
- it must not enter high-confidence definition-layer judgment

### 3.4 Step 3: Evidence Collection for Current Implementation Scope

After the object is identified, the agent needs to collect the direct materials needed to explain the current implementation scope.

#### Priority order
1. SQL directly provided by the customer
2. query / adhoc_query / report configuration corresponding to the identified object
3. analysis results, screenshots, and original text already present in the current conversation
4. reference documents
5. existing product-behavior knowledge

#### Types of materials to collect
- SQL query conditions
- query / qp / adhoc_query
- dashboard / report configuration
- current result screenshot or raw output
- names of tags / cohorts / virtual attributes / dimension-table attributes
- the customer’s current key concern

#### Immediate judgments after collection
- whether the current material is enough to explain L1;
- whether the current material is insufficient to enter the definition layer;
- whether more information must first be requested from the customer.

### 3.5 Step 4: Layer Decision

The agent needs to decide which layer the current explanation should stop at:

#### L1: Current Implementation Layer
Applicable when:
- the customer mainly wants to know “how this result is being calculated now”
- the goal is to first explain the statistical object, range, filters, grouping, time, and calculation method
- the customer has not explicitly asked to explain the definition of tags / cohorts / virtual attributes themselves

#### L2: Definition Explanation Layer
Applicable when:
- the customer explicitly asks how a tag / cohort / virtual attribute / dimension-table attribute itself is defined
- the current result strongly depends on the definition of a certain object
- the customer suspects the current result does not match their understanding

#### L3: Detailed Validation Layer
Applicable when:
- the customer explicitly requests confirmation of complex rules
- the current conclusion depends on complex boundary conditions
- the current object involves version, dynamic matching, complex condition logic, sequence rules, time windows, granularity conflicts, etc.

#### Default principle
- Default to starting from **L1**;
- Only enter L2 / L3 when the customer clearly requests it, or when the current conclusion obviously depends on the definition layer / detail layer.

### 3.6 Step 5: Extract and Explain Current Implementation Scope (L1 Execution)

In L1, the agent should prioritize explaining the current implementation layer rather than expanding the definition layer from the start.

#### Content that should be covered first
If information is sufficient, at least the following should be covered:
- what is being counted
- what the counting range is
- what the filter conditions are
- what the grouping method is
- what the time range / time granularity is
- what the calculation method is
- how tags / cohorts / virtual attributes / dimension-table attributes are being used here

#### Suggested explanation order
1. What is currently being counted
2. What the statistical range is
3. What filters are currently being used
4. How the result is grouped
5. How it is calculated
6. Which definition-layer content has not yet been expanded

#### If a mismatch with customer expectation may exist
The agent should explicitly state:
- what the current implementation logic is actually closer to judging
- which business state in the customer’s wording it does not fully equal
- and ask the customer to confirm:

> Does this current logic match the business scope you actually want?

### 3.6A Per-Round Confirmation After Scope Output

As long as the agent has already produced one round of **scope explanation**, one fixed confirmation action must be performed.

#### The fixed confirmation action includes
1. Confirm whether the customer thinks the current version of scope explanation already matches expectation;
2. If not, confirm what kind of issue the difference mainly falls into, such as:
   - statistical object
   - statistical range
   - filter logic
   - grouping method
   - time scope
   - calculation method
   - tag / cohort / virtual attribute / dimension-table attribute definition
3. Confirm whether further drill-down into the next layer is needed.

#### Applicability boundary
- This confirmation action should only be executed after the agent **has already output scope explanation**;
- If the agent is still in object-identification or material-collection stage and no scope explanation has yet been formed, this action should not be executed.

#### Hard requirement
- The agent must not assume that the customer has accepted the scope explanation just because it has been stated;
- The agent must not directly treat the current scope as established input for downstream analysis before confirming whether the customer accepts it.

### 3.7 Step 6: Post-L1 Confirmation

After L1 is completed, the agent must proactively ask the customer, rather than automatically moving to the next layer.

#### Three required actions
1. Confirm whether the current layer already satisfies the customer
2. Preview what can still be aligned at the next layer
3. Request the information needed for further drill-down

#### What should be stated after L1
For example:
- if continuing, the agent can explain what type the tag / cohort belongs to
- it can explain how the virtual attribute / dimension-table attribute is derived
- it can continue explaining analysis subject, settlement timezone, update mode, and version scope
- if continuing, the following may be needed:
  - definition SQL
  - configuration screenshots
  - version usage mode
  - source report / query / dashboard information

#### Cost notice before drill-down
If continuing drill-down is expected to significantly increase context consumption, history backtracking length, material-reading volume, or token usage, the agent should first remind the customer:
- continuing drill-down will consume more context / tokens;
- if the customer wants to continue, it is recommended to first provide the most critical SQL, configuration screenshots, original historical result text, or relevant excerpts;
- if the customer does not currently want to spend too much context budget, it is acceptable to stop at the current layer.

The agent does not need to calculate tokens precisely, but should proactively warn when high consumption is obviously likely.

### 3.8 Step 7: Enter Definition Explanation Layer (L2 Execution)

Only enter L2 when the customer explicitly indicates that L1 is insufficient, or the current conclusion clearly depends on object definition.

#### Content L2 should explain first
- what type of object it is
- how the object itself is defined
- what the analysis subject is
- what the settlement timezone is
- what the update mode is
- whether it is a precomputed result
- whether version / dynamic matching is involved
- what business meaning the object truly expresses

#### Object types include but are not limited to
- tags
- cohorts
- virtual attributes
- dimension-table attributes
- SQL tags / SQL cohorts
- condition tags / condition cohorts
- metric-value tags
- first/last tags

#### If information is insufficient
If the following are missing:
- definition SQL
- configuration screenshots
- version information
- source-object information

then the agent must clearly tell the customer:
- currently only the way the object is used in this query can be explained;
- its definition-layer scope still cannot be explained with high confidence.

### 3.9 Step 8: Post-L2 Confirmation

After L2 is completed, L3 still must not be entered automatically.

#### Required second confirmation
- whether the current explanation already satisfies the customer;
- whether more detailed rules still need to be checked;
- what material is still missing if continuing.

#### What can be previewed after L2
For example:
- boolean logic of condition tags / condition cohorts
- sequence rules
- time windows
- associated attributes
- “did not do” events
- version differences
- dynamic matching
- granularity consistency
- virtual-attribute expression semantics

#### Cost notice before deeper drill-down
If continuing into L3 is expected to significantly increase context consumption, history backtracking length, material-reading volume, or token usage, the agent should remind the customer again:
- more detailed-layer verification usually consumes more context / tokens;
- if continuing, it is recommended to first provide the most critical definition SQL, configuration screenshots, historical-result excerpts, or related rule descriptions;
- if the customer does not currently want to spend too much context budget, it is acceptable to stop at the current-layer conclusion.

### 3.10 Step 9: Enter Detailed Validation Layer (L3 Execution)

Only enter L3 when the customer explicitly requests it, or the current conclusion depends on complex rules.

#### What L3 focuses on
- complex rules
- boundary conditions
- historical versions
- dynamic matching
- time windows
- sequence logic
- associated attributes
- “did not do” events
- granularity conflicts
- field-source conflicts
- virtual-attribute expression-semantic conflicts

#### L3 working requirements
- High-confidence judgments may only be made when evidence is sufficient;
- If uncertainty still remains, it must be clearly marked as:
  - inference
  - pending confirmation
- If the current judgment requires more definition materials, the flow must return to requesting supplementation from the customer.

### 3.11 Step 10: Recommendation-Style Confirmation When Current Scope Does Not Match Expectation

When the customer indicates that the current scope **does not match expectation**, the agent should not directly ask back:

- “Then what kind of scope do you want?”
- “Please define the scope you want yourself.”

Instead, based on the expectation information the customer has already expressed, the agent should proactively provide **several recommended scope options** to help the customer confirm which one is closer.

#### Default handling order
1. First summarize the expectation the customer has already expressed;
2. Clearly point out the main difference between the current implementation scope and the customer’s expectation;
3. Based on current information, provide 2–3 recommended scope options;
4. Explain the main differences among these options;
5. Ask the customer to confirm which one is closer to the real need;
6. If none of these options fit, continue refining.

#### How recommended options are typically organized
Recommended scope options are usually built around differences such as:
- different statistical object
- different inclusion range
- different exclusion logic
- different time scope
- different subject granularity
- current implementation scope vs business-state scope

#### Recommended expression style
The agent should describe options in customer-friendly language, rather than simply piling up product terminology.

For example:
- Option A: continue using the current implementation logic
- Option B: count “people who have ever satisfied a condition”
- Option C: count “people who first satisfied the condition within a specified time range”

#### Hard requirements
- Do not directly ask the customer to fully define the target scope;
- If the expectation information given by the customer is still insufficient to form recommended options, then request more concrete information;
- Recommended options must be grounded in current evidence and customer statements, and must not be invented arbitrarily.

### 3.12 Step 11: Produce Reusable Scope Output

When the current round of scope confirmation reaches a state where it can be concluded, the agent should try to output a scope conclusion that can be directly reused in later analysis.

#### This output should include as much as possible
- the identified analysis object
- the current statistical object
- the current statistical range
- the current filter conditions
- the current grouping method
- the current time range / time granularity
- the current calculation method
- the usage pattern of key definition objects (such as tags / cohorts / virtual attributes)
- confirmed items
- pending items
- if already confirmed, a statement such as “subsequent analysis may proceed by default using this scope”

#### Output requirements
- This output should not be only a generic explanation;
- It should be usable as input for downstream tasks;
- It should be as structured as possible for easier later reference, rewriting, or reuse.

#### Downstream tasks this output can support
- SQL rewriting
- report generation
- conclusion review
- new analysis design
- follow-up customer communication

### 3.13 Step 12: Downstream Gate

Only after scope confirmation is completed can the agent decide whether to enter downstream actions.

#### Conditions for entering downstream actions
At least one of the following should be satisfied:
- the customer explicitly indicates that the current explanation is sufficient;
- the customer explicitly confirms that the current logic matches the intended business scope;
- both sides have already clarified the mismatch point and confirmed which new scope should be used going forward.

#### Downstream actions include
- SQL rewriting
- new analysis design
- report generation
- conclusion organization
- optimization recommendation output

#### If not yet confirmed
If the current scope is still not confirmed:
- do not directly output a final report that depends on this scope;
- do not directly freeze final analytical conclusions;
- do not write the customer’s expectation as if it were already an established fact.

### 3.14 Insufficient Information Handling

When information is insufficient to support judgment or explanation at the current layer, the agent **must first request supplementary information from the customer**, rather than continuing forward based on guesswork.

#### Default handling order
1. First judge what kind of information is missing:
   - object-identification information
   - SQL / query
   - definition-layer material
   - customer intent layer
2. **Prioritize asking the customer for supplementary information**
3. If the customer cannot provide it, cannot access it, or cannot clearly describe it, then **attempt MCP-assisted retrieval**:
   - query
   - adhoc_query
   - report / dashboard configuration
   - object-related context
   - other materials usable for explaining current scope
4. If both the customer and MCP still cannot provide enough information, then output only:
   - preliminary explanation
   - pending items
   - inferred items
   - suggested additional information

#### Hard requirements
- Do not pretend that high-confidence scope confirmation has been completed when information is insufficient;
- Do not write inference as fact before enough evidence has been obtained;
- If the customer cannot provide further information and MCP also cannot reliably supplement it, clearly state that the current result can only remain at a “preliminary explanation / pending confirmation” state.

### 3.15 Conflict Resolution in Workflow

If conflicts appear during the workflow, they must be explicitly separated:

- customer expectation vs current SQL implementation
- current usage pattern vs definition pattern
- display timezone vs settlement timezone
- current result-page refresh vs object recomputation
- current query logic vs standard product semantics
- customer statement vs MCP retrieval result

Handling steps:
1. State both sides separately
2. Explain which side current evidence supports
3. If it still cannot be confirmed, mark it as pending confirmation
4. Ask the customer for the necessary supplementary materials

### 3.16 Default Exit Conditions

The current workflow round may be considered complete when any of the following is satisfied:

- the customer explicitly indicates the current explanation is sufficient;
- the customer explicitly requests entry into the next layer;
- the agent has clearly explained what information is still missing and is waiting for the customer to supplement it;
- only preliminary explanation can currently be given, and the agent has clearly stated that no final conclusion can be made;
- a reusable scope-confirmation result for downstream analysis has been produced;
- the scope has been confirmed and the task moves into a downstream stage (such as SQL rewriting / report generation / new-plan design).

## 4. Resources

The resources currently relied on by this capability are divided into two categories:

1. **Core guide**
2. **Product reference documents**

The current version does not assume an example library, template library, or script library by default.

### 4.1 Core Guide

- `scope-definition-guide-en.md`

This is the core guide for the capability.  
Its job is to define the execution framework of the capability, not to carry all product-knowledge body text itself.

The agent should use this guide first to determine:
- layered explanation strategy (L1 / L2 / L3)
- the execution sequence of SQL-first, reference-validated, customer-confirmed
- object identification first, customer request first, MCP supplementation second
- hard rules for insufficient information
- the fixed confirmation action after each round of scope explanation
- the logic for recommended scope options when the current scope does not match expectation
- how the final output should be crystallized into reusable input for the next analysis step

### 4.2 Product Reference Documents

The following product reference documents provide the basis for definition-layer rules and product-semantic interpretation:

- `calculation-method-logic-explanation.md`
- `comparing-analysis-through-grouping-items.md`
- `filtering-data-through-filtering-conditions.md`
- `stage-value-logic-explanation.md`
- `user-tags.md`
- `conditional-first-last-metric-value-tags.md`
- `date-versions-of-tags.md`
- `user-cohorts.md`
- `conditional-cohorts.md`
- `data-management-events-and-properties.md`
- `virtual-properties-and-dimension-table-properties.md`
- `creating-virtual-properties-best-practices.md`

These documents are not meant to replace SQL, nor replace `scope-definition-guide-en.md`.  
They are used to:
- verify whether the current implementation scope matches product definitions;
- explain the established product rules for tags, cohorts, virtual attributes, dimension-table attributes, filtering, grouping, stage values, and calculation methods;
- when the customer questions the meaning of a result, help distinguish:
  - current implementation logic
  - product-definition semantics
  - customer business expectation

### 4.3 Document Responsibility Mapping

#### 4.3.1 Scope-rule documents
The following documents mainly support comparison between the current implementation scope and product rules:

- `calculation-method-logic-explanation.md`
  - Used to explain:
    - count / users / per-user
    - mean / per-user mean / median / percentile
    - variance / standard deviation
    - list deduplication
    - boolean counting

- `comparing-analysis-through-grouping-items.md`
  - Used to explain:
    - grouping-item semantics
    - cross grouping
    - numeric / time / list grouping

- `filtering-data-through-filtering-conditions.md`
  - Used to explain:
    - event-attribute filtering
    - user-attribute filtering
    - tag / cohort filtering
    - global / local filtering
    - relative time, timezone, and condition combination

- `stage-value-logic-explanation.md`
  - Used to explain:
    - stage values
    - stage sum
    - weighted average
    - incomplete-data exclusion

#### 4.3.2 Tag-related documents
The following documents mainly support tag definition-layer explanation and version-scope judgment:

- `user-tags.md`
  - Used to explain:
    - tag definition
    - tag analysis subject
    - tag settlement timezone
    - tag update mode

- `conditional-first-last-metric-value-tags.md`
  - Used to explain:
    - condition tags
    - first/last tags
    - metric-value tags
    - differences among tag types

- `date-versions-of-tags.md`
  - Used to explain:
    - tag version
    - dynamic matching
    - historical change of tag values in historical analysis

#### 4.3.3 Cohort-related documents
The following documents mainly support cohort definition-layer explanation and complex-rule judgment:

- `user-cohorts.md`
  - Used to explain:
    - cohort definition
    - cohort analysis subject
    - cohort source
    - cohort update mode

- `conditional-cohorts.md`
  - Used to explain:
    - condition cohorts
    - behavior sequence
    - time windows
    - associated attributes
    - “did not do” events
    - condition-combination logic

#### 4.3.4 Event / attribute / virtual-attribute / dimension-table-attribute documents
The following documents mainly support field-source judgment, granularity judgment, and definition-layer explanation of virtual attributes and dimension-table attributes:

- `data-management-events-and-properties.md`
  - Used to explain:
    - events
    - event attributes
    - user attributes
    - basic data structure

- `virtual-properties-and-dimension-table-properties.md`
  - Used to explain:
    - virtual user attributes
    - virtual event attributes
    - dimension-table attributes
    - field derivation patterns

- `creating-virtual-properties-best-practices.md`
  - Used to explain:
    - virtual-attribute expressions
    - common usage patterns
    - common pitfalls
    - the gap between expression semantics and business semantics

### 4.4 Resource Calling Order

When this capability is triggered, resources should be consulted in the following order:

1. **Look at current task inputs first**
   - project_id / dashboard_id / report_id
   - SQL
   - query / adhoc_query
   - screenshots
   - original historical analysis results

2. **If information is insufficient, then use MCP supplementation**
   - query
   - adhoc_query
   - report / dashboard configuration
   - object-related context

3. **Explain the current implementation scope first**
   - Prioritize SQL / query / report configuration

4. **When layered rules are needed, consult `scope-definition-guide-en.md` first**

5. **Only when definition-layer judgment or rule verification is needed, consult the corresponding product reference documents**
   - filtering issues → `filtering-data-through-filtering-conditions.md`
   - grouping issues → `comparing-analysis-through-grouping-items.md`
   - calculation-method issues → `calculation-method-logic-explanation.md`
   - stage-value issues → `stage-value-logic-explanation.md`
   - tag issues → tag-related documents
   - cohort issues → cohort-related documents
   - virtual-attribute / dimension-table-attribute issues → attribute-related documents

6. **If the customer does not accept the current scope**
   - Based on the customer’s already expressed expectation, output recommended scope options

7. **Finally produce a reusable scope-confirmation result**
   - This result should be usable as input for the next analysis step, SQL rewriting, report generation, or conclusion review

### 4.5 Resources That Should Not Be Assumed to Exist by Default

The current version should not assume the following resources already exist:

- a preorganized example library
- preorganized original output-template text
- preorganized recommended-scope-option template text
- SQL auto-parsing scripts
- structured scope-output scripts
- missing-information checking scripts

If these resources are added in the future, this section may be extended, but in the current version they must not be written as required dependencies.

### 4.6 Citation Rules

- In `scope-definition-guide-en.md` and other resource files, **temporary citation placeholders left over from the conversation must not remain**, including but not limited to:
  - `:contentReference[...]`
  - `oaicite`
  - any other temporary citation markers that cannot be formally resolved at skill runtime
- All citations must be rewritten as **explicit document references that are readable and locatable by the agent**.
- At minimum, an explicit citation should state the document name, for example:
  - `See user-cohorts.md`
  - `See conditional-cohorts.md`
  - `See filtering-data-through-filtering-conditions.md`
- When necessary, it may further specify the topic, for example:
  - `See user-cohorts.md for the section on “cohort settlement timezone”`
  - `See conditional-cohorts.md for the section on “behavior sequence and time windows”`
- Unmapped temporary citation placeholders must not remain in the guide.

### 4.7 Hard Rules for Resource Design

- `scope-definition-guide-en.md` is the core guide for this capability and must be used first.
- SQL / query / report configuration is always the primary evidence for the current implementation layer.
- Product reference documents are the basis for definition-layer explanation and rule verification.
- Product reference documents must not replace SQL, and definition-layer explanation must not override current implementation-layer facts in reverse.
- Scripts / templates / examples that do not currently exist must not be described as existing dependencies.
- Citations in the guide and other resource files must use explicit document references and must not retain temporary citation placeholders.
- The final scope-confirmation result must be reusable for the next analysis step.

## 5. I/O Contract

This section defines the minimum requirements for inputs, default handling, insufficient-input handling, and output delivery.  
The output of this capability must not only help the customer understand the current scope, but also serve as reusable input for the next analysis step, SQL rewriting, report generation, or result review.

### 5.1 Required Inputs

The inputs for this capability are divided into two layers:

#### A. Identification inputs
Used to determine which concrete analysis object is being aligned. Acceptable inputs include:

- `project_id`
- `dashboard_id`
- `report_id`
- `SQL`
- `query / qp / adhoc_query`
- original text / screenshots / links of historical analysis results

#### B. Explanation inputs
Used to determine what exactly needs to be aligned. Acceptable inputs include:

- the object the customer wants to confirm
- the issue the customer cares about most
- whether the request is only about current implementation, or also requires definition-layer drill-down

#### 5.1.1 Minimum requirement for required inputs
If any one of the following categories of information is already available, scope alignment can begin:

- SQL / query / qp / adhoc_query that can locate the object
- `project_id / dashboard_id / report_id` that can locate the object
- original text / screenshots / links of historical analysis results that are sufficient to help the system further locate the object

If none of the above is available, no high-confidence final scope conclusion may be given, and the agent may only first request identification information.

#### 5.1.2 What it means for the task to have “started”
This capability may begin even when input is incomplete, but once it starts, output depth must be controlled based on the current evidence layer:

- If the object is identified and the SQL / query logic is readable, L1 current-implementation explanation may begin;
- If the object is not fully identified, only preliminary explanation is allowed, and the agent must not pretend that scope confirmation has already been completed.

### 5.2 Optional Inputs and Defaults

When optional inputs are missing, the executor should try to move forward as far as possible using existing information to the “currently confirmable layer”;  
only when further progress would significantly affect scope judgment should additional information be proactively requested.

#### 5.2.1 Default handling when object-identification inputs are missing
- If the customer directly provides `SQL`, default to explaining the current implementation scope based on SQL first.
- If the customer does not provide SQL but does provide `project_id / dashboard_id / report_id`, default to retrieving the corresponding query / adhoc_query / configuration through the system first.
- If the customer does not provide complete identification information but does provide original text / screenshots / links of historical analysis results, default to attempting object identification first, or giving preliminary explanation based on existing content.
- If the object still cannot be identified, then only the following may be output:
  - currently confirmable content
  - pending content
  - inferred content

#### 5.2.2 Default handling when alignment depth is unspecified
- If the customer does not specify how detailed the alignment should be, default to outputting only **L1 current implementation layer**.
- Do not automatically enter:
  - definition layer for tags / cohorts / virtual attributes / dimension-table attributes
  - version / timezone / update mode
  - condition details / sequence rules / historical versions

#### 5.2.3 Default handling when key concern is unspecified
If the customer does not clearly state what they care about most, default to explaining first:

- statistical object
- statistical range
- filters
- grouping
- time
- calculation method
- how the current object is used in this query

Then, after the first round of output, ask whether further drill-down is needed.

#### 5.2.4 Default handling when SQL is provided
- If the customer provides SQL, default to first explaining **the current statistical logic expressed by the SQL**.
- However, do not automatically assume that:
  - the final output structure of the SQL
  - the final front-end displayed result
  - the chart / card / report presentation the customer sees  
  are fully equivalent.

Only under the following conditions should the extra layer of “final front-end displayed result” be explicitly confirmed:
- the customer explicitly mentions that the front-end displayed result does not match expectation;
- the customer’s question is clearly asking:
  - why the front end shows this result
  - why the chart / card / report presentation does not match the customer’s understanding
  - why the front end seems inconsistent with the SQL logic

#### 5.2.5 Default supplementation handling for system context
- `dashboard / report / query` context should not be treated as information that is requested from the customer by default.
- By default, customers usually cannot directly provide this kind of context.
- This kind of information should first be supplemented via MCP by the system.
- If the system can retrieve it, continue the explanation based on the retrieved result.
- If the system cannot retrieve enough information, then first output what is confirmable based on currently obtained information, and clearly mark which parts are inferred.

#### 5.2.6 Conditional trigger rules for result samples and front-end screenshots
- Query-result samples are not default required inputs.
- Front-end screenshots are not default required inputs.
- They should only be requested under the following conditions:
  - the SQL cannot explain the final front-end result shape;
  - the customer explicitly questions the front-end displayed result;
  - the disputed point is in the presentation layer rather than the underlying statistical logic.

### 5.3 Behavior Under Insufficient Input

When information is insufficient to support high-confidence scope judgment, the executor must downgrade into an output mode of “confirmed part + pending part + inferred part,” and must not pretend to have produced a complete confirmed conclusion.

#### 5.3.1 What counts as insufficient information
Any of the following situations counts as insufficient information:

1. **The object is not sufficiently identified**
   - there is no SQL
   - there is no `project_id / dashboard_id / report_id` sufficient to locate the object
   - system retrieval still does not produce enough object context
   - the customer only gives a vague question without a clear analysis object

2. **The current implementation is readable, but definition-layer evidence is insufficient**
   - the SQL is understandable as current statistical logic
   - but the customer is asking about the definition of the tag / cohort / virtual attribute / dimension-table attribute itself
   - currently there is no definition SQL, configuration screenshot, version information, or similar evidence

3. **A key judgment depends on additional information**
   - whether granularity is consistent
   - whether the front-end result fully corresponds to the SQL
   - whether a virtual attribute expresses an event-level condition or a user-level state
   - whether a tag / cohort is using dynamic matching or historical versions

#### 5.3.2 Forbidden behaviors under insufficient information
When information is insufficient, the executor must not:

- write inference as confirmed fact
- directly equate current implementation logic with the customer’s expected business definition
- assume that front-end results fully match SQL just because the customer provided SQL
- output nothing confirmable at all merely because information is insufficient

#### 5.3.3 Handling order under insufficient information
When information is insufficient, proceed in the following order:

1. First judge what type of information is missing:
   - object-identification information
   - definition-layer information
   - output-structure information
   - version / timezone / configuration details

2. Judge how far the current evidence can support explanation:
   - at least whether L1 current implementation layer can be confirmed
   - or whether only a more preliminary explanation is possible

3. Request more information from the customer only when necessary

4. If the customer cannot provide it, use system-side MCP supplementation

5. If still insufficient, output a downgraded conclusion:
   - currently confirmed content
   - currently pending content
   - currently inferred content
   - what is still needed if confirmation is to continue

#### 5.3.4 Output format under insufficient information
When information is insufficient, the output should include at least:

- **Currently Confirmed**
- **Currently Unconfirmed**
- **Current Inference**
- **What Is Needed to Continue Confirmation**

#### 5.3.5 Inference marking rules
Whenever any of the following applies, the agent must explicitly write “this is inference” or equivalent wording:

- the object is not yet fully identified
- definition-layer rules are missing
- system retrieval still does not produce enough evidence
- the current judgment depends on experience-based reasoning rather than explicit SQL / configuration / reference evidence
- the front-end result shape cannot be directly reconstructed from SQL

#### 5.3.6 Minimum allowed level of downgraded output
- As long as the statistical logic of the current SQL / query can be located, **partial L1** output is allowed;
- But the executor must not pretend to have already entered L2 / L3;
- If even L1 cannot be confirmed, only object-level preliminary explanation and pending items may be output.

### 5.4 Output Contract

The output must satisfy two goals simultaneously:

1. **Readable to the customer**
2. **Reusable for downstream tasks**

#### 5.4.1 Output-layer requirements
- **L1**: explains the current implementation layer; must not pretend that L2 / L3 has already been entered.
- **L2**: explains definition-layer origin; must not pretend that all detail rules have already been verified.
- **L3**: explains complex rules and boundary conditions; may go into rule-level detail.

The output layer must match the current evidence layer.

#### 5.4.2 Output-content requirements
L1 current-implementation output should cover the predefined key scope items, including but not limited to:

- statistical object
- statistical range
- filter conditions
- grouping method
- time logic
- calculation method
- how tags / cohorts / virtual attributes / dimension-table attributes are used in the current query

However, not every round will necessarily be able to provide positive scope content for every item.  
For each item, the executor must explicitly output one of the following three states:

1. **Confirmed**
   - current information is sufficient to explain this scope item;
2. **Not used in the current implementation**
   - this item is simply not used in the current SQL / query / report;
3. **Cannot yet be confirmed**
   - current information is insufficient to determine this item.

The executor must not confuse:
- not used in the current implementation
- cannot yet be confirmed because information is insufficient

In other words, no key scope item may be silently skipped in output.

#### 5.4.3 Output classification requirements
The output must clearly distinguish the following four categories of information:

- **Confirmed**
- **Pending Confirmation**
- **Inference**
- **Next-Step Suggestion**

#### 5.4.4 Output confirmation requirements
As long as the current round already contains scope explanation, a confirmation action must be appended, including:

- whether the current explanation matches customer expectation
- if not, whether finer alignment is needed
- what additional information is needed for further drill-down
- if the current scope does not match expectation, recommended scope options may be provided

The executor must not only ask back “What scope do you want?”  
Instead, it should first provide the current explanation, then provide recommended options.

#### 5.4.5 Output reusability requirements
The output must not be only a one-time explanation. It must be usable as input for the next analytical task.  
At minimum, it should preserve the following kinds of information:

- current confirmed scope
- current unconfirmed scope
- current disputed points
- recommended next steps

These should later connect directly into:
- SQL rewriting
- new analysis-plan design
- report generation
- result review
- further customer confirmation

#### 5.4.6 Output form requirements
- Output must be structurally clear;
- But wording may flex according to:
  - current layer
  - customer familiarity
  - problem complexity
- Content structure should remain strongly constrained, while surface phrasing may stay moderately flexible.

### 5.5 Hard Constraints

- If there is no identification information and no SQL / query / report context, no high-confidence scope conclusion may be given.
- If the customer does not state how deep the alignment should go, default to only L1 current implementation layer.
- If input is insufficient, request supplementation first; if the customer cannot provide it, then use system-side MCP supplementation.
- After every round of scope explanation, the customer must be asked whether the explanation matches expectation.
- If the customer thinks the current scope does not match expectation, recommended scope options should be given instead of only asking the customer back.
- The final output must be reusable as input for the next analysis step.
- The output must clearly distinguish:
  - not used in the current implementation
  - cannot yet be confirmed
  - confirmed
- Any judgment that depends on incomplete evidence must be explicitly marked as “this is inference” or equivalent wording.

## 6. Rules & Boundaries

This section defines the rules, prohibited behaviors, high-risk scope triggers, and downstream-task boundaries that must be respected during execution.  
Earlier sections mainly describe what should be done; this section mainly describes what must never be done, when extra caution is required, and which boundaries must not be crossed.

### 6.1 Hard Rules

#### 6.1.1 Identify the object before explaining the scope
Before the object is clearly identified, only preliminary explanation is allowed; no high-confidence final scope conclusion may be given.  
Object identification normally prioritizes:

- `SQL`
- `query / qp / adhoc_query`
- `project_id / dashboard_id / report_id`
- or historical analysis result text / screenshots / links sufficient for the system to continue identification

#### 6.1.2 Explain the current implementation layer first, then decide whether drill-down is needed
By default, **L1 current implementation layer** should be explained first.  
Do not automatically enter from the start into:

- tag / cohort / virtual-attribute / dimension-table-attribute definition layer
- version layer
- timezone layer
- condition-rule layer
- historical-version layer

#### 6.1.3 SQL-first, but not SQL-only
`SQL` is the first evidence for the current implementation layer.  
However, when the question involves the following, SQL alone is not enough and must be combined with reference documents and other evidence:

- tag / cohort / virtual-attribute / dimension-table-attribute definitions
- versions
- timezones
- update modes
- stage-value rules
- complex rules of condition-type objects

#### 6.1.4 Three states must always be distinguished
When explaining key scope items, the following three states must always be clearly distinguished:

1. **Confirmed**
2. **Not used in the current implementation**
3. **Cannot yet be confirmed**

The executor must not confuse:
- the item is not used in the current implementation
- the item cannot yet be confirmed due to insufficient current information

#### 6.1.5 After every round of scope explanation, confirmation is required
As long as the current round already contains scope explanation, a confirmation action must be added, including:

- whether the current explanation matches customer expectation
- whether further drill-down is needed
- what information is still missing if drill-down continues

#### 6.1.6 If the current logic may differ from the customer’s expectation, explicitly state what it is actually closer to judging
When the current implementation logic may not fully match the customer’s business-language understanding, the executor must explicitly state:

- what the current logic is actually closer to judging
- what business state in the customer’s wording it does not fully equal
- whether finer definition alignment is needed

#### 6.1.7 Output must be reusable for the next analysis step
The output must not be only a one-time explanation.  
It must be reusable in downstream tasks, including:

- SQL rewriting
- new analysis-plan design
- report generation
- result review
- further customer confirmation

### 6.2 Prohibited Behaviors

#### 6.2.1 Do not write inference as confirmed fact
As long as a judgment depends on incomplete evidence, it must not be written as confirmed fact.  
Equivalent expressions such as the following must be used:

- based on the current information, it is more likely that…
- this still remains to be confirmed…
- if the current logic is…, then it is more likely that…

#### 6.2.2 Do not give high-confidence conclusions before the object is clearly identified
When sufficient object-identification information is missing, no high-confidence final scope conclusion may be directly given.  
Only the following may be output:

- currently confirmable content
- currently pending content
- current inference

#### 6.2.3 Do not directly equate current implementation logic with the customer’s expected business definition
When the customer asks in business language, for example:

- Is this a paying user?
- Is this a retained user?
- Is this the audience I actually want?

if the definition layer has not yet been confirmed, the executor must not simply answer “yes” by following the customer’s wording.

#### 6.2.4 Do not treat the way an object is used in the current query as the way the object itself is defined
The way an object is used in the current query must not be mistaken for the object’s own definition.  
This is especially important for:

- tags
- cohorts
- virtual attributes
- dimension-table attributes

The current query can only explain how these objects are being used in the present analysis;  
if their own definition needs to be confirmed, the executor must enter the definition layer and rely on additional evidence.  
The executor must not conclude that because an object is currently being used for filtering, grouping, or calculation, that this is the full definition semantics of the object itself.

#### 6.2.5 Do not directly equate the current SQL output shape with the final front-end displayed result
Even when the customer provides SQL, the executor must not automatically assume that:

- the final SQL output structure
- the final front-end displayed result
- the chart / card / report presentation seen by the customer

are fully identical.

#### 6.2.6 Do not silently skip key scope items
For predefined key scope items, the executor must not skip an item just because it has no explicit content.  
Each item must always be explicitly marked as:

- confirmed
- not used in the current implementation
- cannot yet be confirmed

#### 6.2.7 Do not confuse “not used in the current implementation” with “cannot yet be confirmed”
The executor must not merge the following two situations into one generic “not present” statement:

- the item truly does not exist in the current implementation
- the current information is insufficient to confirm the item

#### 6.2.8 Do not over-request supplementary materials at the very beginning
The executor must not start by asking the customer for a large number of supplementary materials all at once, such as:

- SQL
- project_id
- dashboard_id
- report_id
- query configuration
- result samples
- front-end screenshots
- definition SQL
- rule screenshots

Instead, it should first move forward to the currently confirmable layer based on existing information, and only request supplementary materials in a minimized way when progress is clearly blocked.

#### 6.2.9 Do not respond only with “please provide more information” without first outputting currently confirmable content
Even when information is insufficient, the executor should first output what can already be confirmed, then explain the gaps, instead of only sending a supplementation request.

#### 6.2.10 Do not directly push downstream-task conclusions before scope is confirmed
Before the current scope is confirmed, the executor must not directly:

- generate the final analysis report
- output a high-confidence SQL rewriting conclusion
- write the current result as a final business conclusion
- write inferred definitions into formal analytical conclusions

#### 6.2.11 Do not make any direct modification to database data or data assets
This capability is limited to:

- querying and interpreting current data logic
- aligning statistical scope
- proposing new scope options
- giving query-level / SQL-level adjustment suggestions

It must not directly modify any of the following:

- underlying database data
- result tables
- tag results
- cohort results
- dimension tables
- other data assets

Even if the customer expresses an intention to modify data, this capability must not perform direct data modification as part of scope alignment.

### 6.3 Handling Uncertainty and Inference

#### 6.3.1 Situations where inference is allowed
Inference is only allowed when all of the following are true:

- existing SQL / query / object information is sufficient to support partial judgment
- some definition-layer or presentation-layer evidence is still missing
- the customer currently wants an initial direction first

#### 6.3.2 How inference must be expressed
Inference must always be expressed explicitly and must not be disguised as confirmed fact.  
Recommended wording includes:

- based on the current information, it is more likely that…
- this still remains to be confirmed, but it is roughly likely that…
- if the current object uses … logic, then the result is more likely to mean…

#### 6.3.3 Situations where inference is not allowed
If any of the following applies, no concrete inference should be given; only inability to judge and the required information should be stated:

- the object has not even been identified
- the current implementation layer itself cannot be read
- the current evidence does not support even partial L1 explanation

### 6.4 Out-of-Scope Handling

#### 6.4.1 Core scope of this capability
The core scope of this capability includes:

- aligning statistical scope
- explaining the current implementation
- distinguishing implementation layer from definition layer
- identifying the difference between customer expectation and current logic
- proposing recommended scope directions
- providing reusable scope input for downstream tasks

#### 6.4.2 Tasks that are not in the core scope of this capability
The following are not core responsibilities of this capability:

- directly modifying underlying data
- executing database writes / updates / deletes
- generating final analytical conclusions before scope confirmation
- pure wording polishing
- generic business consultation not grounded in objects and scope

#### 6.4.3 How to handle out-of-scope requests
When the customer requests something outside the responsibility of this capability, the executor should:

- clearly state that the request is outside the current scope-alignment responsibility
- if it is still related to scope, first complete scope confirmation and then connect to the downstream task
- if it is completely unrelated, do not force this capability onto it

### 6.5 High-Risk Scope Triggers

When any of the following high-risk scope triggers appear, the executor should default to a more conservative explanation strategy, including but not limited to:

- separating current implementation from definition-layer semantics more explicitly
- separating confirmed content from inference more explicitly
- judging more carefully whether customer expectation matches current logic
- proactively asking whether deeper drill-down is needed when necessary

#### 6.5.1 Confusion between usage layer and definition layer of tags / cohorts
Why it is high-risk:
- the way a tag / cohort is used in the current query is not equal to how the object itself is defined;
- customers easily misread “how it is used now” as “how it is defined.”

When this appears, priority should be:
- explain current usage first
- then state that this is not the same as definition
- only if the customer continues asking about definition should the executor enter the definition layer

#### 6.5.2 Virtual-attribute expression semantics
Why it is high-risk:
- technically, a virtual attribute may only be an expression result;
- but customers easily interpret it as a complete business state.

Especially cautious handling is needed in cases involving:

- boolean judgments
- time comparisons
- first / last
- whether an action has been completed
- user state vs event condition

#### 6.5.3 Mixed use of event-level and user-level fields
Why it is high-risk:
- mixing event-level and user-level fields directly affects:
  - people counts
  - subject counts
  - state judgments
  - deduplication scope

When this appears, the executor should explicitly state:
- whether the current judgment is about events or subjects
- what the current distinct key is
- whether there is a granularity inconsistency risk

#### 6.5.4 Difference between packaged SQL and front-end displayed result
Why it is high-risk:
- SQL may represent raw logic, an intermediate-layer result, or packaged output;
- the front-end chart / card / report may still have undergone further processing.

When this appears, the executor should:
- explain the current statistical logic first
- avoid assuming the final front-end result shape by default
- only ask whether front-end presentation alignment is needed when the customer explicitly mentions mismatch with front-end results

#### 6.5.5 Version / timezone / update mode
Why it is high-risk:
- the following directly affect scope once they are relevant to the customer’s question:
  - tag date version
  - dynamic matching
  - historical version
  - settlement timezone
  - display timezone
  - automatic / manual / edit-triggered update mode

Whenever the customer asks things like “why is this different from before” or “why do the times not match,” caution must automatically increase.

#### 6.5.6 Stage values
Why it is high-risk:
- stage values are easily misread as:
  - daily average
  - simple average
  - daily sum
- while they may actually be:
  - stage sum
  - weighted average
  - values after incomplete-data exclusion

When stage values are involved, priority should be given to:
- `stage-value-logic-explanation.md`

#### 6.5.7 What kind of “not present” is it
Why it is high-risk:
- it is easy to miswrite “not used in the current implementation” as “cannot yet be confirmed”
- or miswrite “cannot yet be confirmed” as “not present”

Whenever something appears to be “not there,” the executor should first determine:
- whether it is absent in the implementation
- or whether evidence is insufficient

#### 6.5.8 The customer treats a technical field as a business state
Why it is high-risk:
- customers often directly interpret technical objects as business objects, for example:
  - a virtual attribute = a user category
  - a tag value = high-value users
  - cohort membership = a business state has been established

When this appears, the executor should:
- first explain what the current logic is actually closer to judging
- then ask whether that matches the customer’s intended business scope
- and when needed, provide recommended scope options instead of directly accepting the customer’s wording

### 6.6 Boundary with Downstream Tasks

#### 6.6.1 This capability is usually a prerequisite for downstream tasks
This capability usually serves as a prerequisite for the following tasks:

- SQL rewriting
- new analysis-plan design
- report generation
- result review
- further customer communication

#### 6.6.2 Requirements before entering downstream tasks
If the current scope is still not clearly confirmed, then:

- final analytical conclusions should not be generated directly
- high-confidence SQL rewriting suggestions should not be given directly
- inferred definitions should not be written into the main body of a report

#### 6.6.3 Proper handoff pattern
After this capability is completed, its result may be preserved as:

- current confirmed scope
- current unconfirmed points
- recommended new scope direction
- additional information required for the next step

Only then should it be handed over to downstream tasks.