# Implementation Steps

Use this sequence for in-scope tasks. Each step has an input, an action, and an observable completion condition. Authentication or resource access can be resolved when needed; continue independent work while waiting.

## Step 1: Inspect the original tag

**Input:** Platform environment, analysis project, and tag name, ID, or link.

**Actions:**

1. Ask directly for missing project or tag identifiers; resolve ambiguous matches with metadata first.
2. Read asset type, owner, subject, saved SQL or model definition, direct and transitive references, date parameters, calculation and refresh time zones, historical start, filters, value type, and update settings.
3. Resolve actual inputs and physical source references in the original analysis project using [source discovery](../source-discovery.md). Inspect referenced definitions when needed.
4. Establish NULL, zero, negative-value, precision, join-grain, tie, and historical-coverage semantics. Inherit the original date basis and time conversion.
5. If a cross-source tag or actual cross-source input is confirmed, give the scope response in [SKILL.md](../../SKILL.md#scope) and end this workflow. Resolve unknown source types before proceeding.
6. After the scope check, resolve the target DataOps space from current-task information or ask for its name or ID.

**Completion condition:** Scope is established, original semantics have analysis-side evidence, and the target space is identified. Unavailable critical definitions are explicit blockers, not guessed values.

## Step 2: Design and summarize the solution

**Input:** Verified original definition, source references, and target space.

**Actions:**

1. Before implementation code, record the design in the delivery draft:
   - Original subject, core rule, date range, and time zone.
   - Reusable state, grain, complete-day partitions, historical initialization, and daily recurrence.
   - A new tag or consumer that reads the target-day result while preserving the original assets.
   - Same-scope acceptance, deliverable resources, documentation, and the final scheduling choice.
2. If the original range includes today, adapt it to completed days ending yesterday and explain the change.
3. Briefly summarize these points once in chat, in the user's preferred language. Continue authorized implementation directly. Route actual decisions or grants through the relevant authorization rule.
4. Put field bindings, scan boundaries, dependencies, and recovery details in the document or execution evidence as appropriate.

**Completion condition:** The design precedes code, the user has received a concise plan, and implementation can proceed without a separate routine plan-approval gate.

## Step 3: Build DataOps tables and workflows

**Input:** State design and verified source bindings.

**Actions:**

1. Read [SQL design](../sql-design.md) before adapting templates. Verify DataOps can read the already-identified source and check target naming collisions.
2. Create date-partitioned daily state and cumulative snapshots. Retain historical partitions. Preserve finer grain when sequences, sets, or windows require it.
3. Initialize a completed baseline B and reconcile it against an independent full calculation.
4. Wire daily processing as successful dependencies: completed-day check, D-day statistics, daily validation, prior-run success and D-1 receipt/count validation, D snapshot merge, cumulative validation, and acceptance receipt publication. Publish a receipt after baseline acceptance as well.
5. Place D-only cleanup inside the corresponding gated write node. A failed upstream step blocks the cumulative write and its cleanup, preserving D-1.
6. Confirm a source-empty day was processed successfully before carrying D-1 forward. Test write visibility and consumer controls for DELETE plus INSERT; use atomic replacement only when verified on the platform.
7. Rebuild D from D-1 and D, rather than adding to an existing D result. Run dependent dates serially and propagate historical corrections forward.
8. Save, perform necessary releases, run manually, and record resource and operation IDs. Keep recurring schedules disabled at this stage.

**Completion condition:** Deployed resources support bounded, repeatable complete-day processing; baseline and daily runs have actual execution evidence and gated failure behavior.

## Step 4: Create the analysis application

**Input:** Validated PROD outputs and the chosen application type.

**Actions:**

1. Create a new tag or application by default. Check permissions for an explicitly requested original-asset edit.
2. For a SQL tag, read the target-day cumulative output; keep business filters and classification at the application layer. Save the native date parameter through the UI's Add time parameter / Yesterday controls and read back its stored definition. See [date parameter handling](../sql-design.md#step-5-configure-the-native-yesterday-parameter).
3. For a cross-source tag, map the target-day subject and value. For a cross-source event table, retain subject, date, and snapshot grain.
4. Limit new grants to the required PROD resources. State the target project, resources, and minimum permission before requesting a grant decision, or reuse a specific authorization already given for this task.
5. Preview, save, and read back the asset ID, subject, key, value type, date expansion, and actual read access.
6. Fix consumption to the target date. Establish behavior for missing partitions, partial writes, and failed validation; combine any remaining consumer-policy choice with the final scheduling question.

**Completion condition:** The actual saved consumer reads the intended complete-day output with matching subject, type, date, and access scope.

## Step 5: Validate results and any requested migration

**Input:** Executed DataOps outputs and the actual saved consumer.

**Actions:**

1. Complete the daily/detail, cumulative recurrence, independent full-history, and actual-consumer comparisons in [validation and recovery](../validation-and-recovery.md).
2. Use NULL-safe comparisons with original precision and tolerance; record missing, extra, duplicate, and differing subjects and the coverage actually tested.
3. Investigate historical differences from original definitions and source evidence before asking about a genuinely unresolved gap.
4. If migration was explicitly requested, inventory downstream references, replace only authorized dependencies, verify each, and then handle the old schedule. Record discovery limitations, remaining work, and rollback evidence.

**Completion condition:** Acceptance results and limitations are supported by evidence. Existing downstream assets remain unchanged unless the user explicitly authorized migration.

## Step 6: Confirm recurring execution

**Input:** Created and released resources, completed manual acceptance, and a prepared handover document.

**Actions:**

1. Just before final delivery, ask whether to enable the daily DataOps schedule and new-tag auto-refresh. State proposed times, time zones, source-arrival evidence, processing and retry margin, dependencies, and abnormal-consumption behavior. Reuse an explicit current-task decision.
2. If enabled, save and release as needed, then read back switches, frequency, time, time zone, parameters, backups, and dependencies.
3. If left disabled, record that choice and provide suggested times, resource links, and manual enablement steps.
4. Distinguish success-triggered consumption from independent fixed-time schedules. The former waits for validated output; the latter needs an interval and an explicit exception policy.
5. Verify effective configuration separately from the first real scheduled run. Historical initialization remains an on-demand operation.

**Completion condition:** Actual settings match the user's choice; scheduled-run verification is reported separately from configuration readback.

## Step 7: Review and deliver

**Input:** Platform resources, acceptance evidence, schedule decisions, and the delivery draft.

**Actions:**

1. Complete the six-part document in [delivery standards](../delivery-document.md), using the user's preferred language and requested medium.
2. Separate customer explanation from exploration logs. Mark newly created assets in real screenshots, match captions to the inventory, and format complete key SQL at the end.
3. Perform content review, factual reconciliation, and actual page or trusted-render inspection. Correct defects and recheck affected content. Keep the review evidence in execution records.
4. Read back the saved document, SQL, links, attachments, and actual status. Label any unresolved review step and its recovery condition accurately.
5. Return the real document link, concise completion status, and outstanding actions. Distinguish deployment, manual validation, scheduled verification, migration, and performance evidence.

**Completion condition:** Customer-facing resources and documentation are reviewable, accurate, visually inspected, and linked; unresolved work is explicit.
