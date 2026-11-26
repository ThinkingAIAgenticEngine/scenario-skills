# Design and Delivery Document

Use the full document for in-scope implementation. For excluded inputs, follow the [scope response](../SKILL.md#scope). The user's requested medium and structure take precedence. Write the customer document in the user's preferred language.

## Step 1: Organize the document

Open with:

1. **Title:** Project | Tag: DataOps Optimization Design and Delivery.
2. **Environment:** Project, DataOps space, delivery date, and time zone in one line.
3. **Conclusion callout:** Delivered resources, key acceptance result, scheduling, and backup status.

Use six main sections:

| Section | Content and presentation |
|---|---|
| 1. Goal and calculation scope | Actual tag/input meaning, subject, dates, zones, history coverage, complete-day adaptation, and requested semantic changes; concise goal plus a rule table. |
| 2. Solution design | Analysis source to DataOps output, state, grain, partitions, initialization, daily recurrence, dependencies, and consumption; process diagram, data-layer summary, and rerun rules. |
| 3. Delivered resources | Workflow, table, tag/application identifiers, real links, grants, and actual status; inventory followed by screenshots in that order. |
| 4. Acceptance results | Same-scope reconciliation, subject differences, rerun/failure gates, real or synthetic evidence, and performance scope; conclusion, comparison table, and material limits. |
| 5. Scheduling and operations | Enablement choice, zone, time, dependencies, backups, scheduled verification, recovery, backfill, and rollback; schedule table, consumption flow when helpful, and exception handling. |
| 6. Key processing SQL | Initialization, daily calculation, cumulative merge, and actual consumption; explain purpose, parameters, and execution positions, or cross-source mappings. |

Screenshot subtitles reflect actual deployment and execution status. State how original assets and schedules were preserved; add migration progress only when requested. Distinguish effective configuration from a real scheduled run.

Before implementation, put the original meaning, processing, consumption, and acceptance design in the draft, summarize it once in chat, and continue authorized work. Add deployment evidence during execution. After manual acceptance, confirm scheduling before final delivery and record actual settings. Date retrospective writeups and their evidence scope.

## Step 2: Edit for customer readability

| Standard | Application |
|---|---|
| Clear structure | Organize scope, solution, resources, acceptance, operations, and SQL; lead with conclusions, then supporting evidence and actions. |
| Concise language | Use familiar business language, one point per paragraph, and information needed for decisions and use. |
| Integrated visuals | Explain purpose and conclusions in text, show the chain in diagrams and assets in annotated screenshots, and summarize resources/results in tables. Keep related text and visuals together. |
| Structured expression | Use consistent headings, numbered actions, parallel lists, comparison tables, and restrained emphasis. |

- Keep heading hierarchy, column widths, alignment, spacing, and line wrapping consistent.
- Use a small number of callouts for conclusions and outstanding actions; use color for status.
- Put request IDs, API errors, investigation history, raw logs, and detailed engine metrics in execution records or attachments. Explain necessary fields and parameters where used. Prefer real platform links for customer resources.
- Give each section one purpose. Explain a fact fully in its relevant section and summarize or reference it elsewhere.
- Use actual table names, fields, thresholds, and dates. Separate design intent from observed implementation results.

## Step 3: Prepare diagrams and asset screenshots

Use a process diagram when dependencies, branches, or multiple consumption layers need explanation. Separate processing and consumption when clearer. Show initialization versus daily recurrence, target date, success dependencies, failure exits, and rerun scope. Distinguish scheduled from success-triggered behavior and explain the business-day merge.

For Feishu, prefer available native editable diagrams through `lark-doc`; use `lark-whiteboard` when needed for complex diagrams. Other media use supported formats. Export a preview or inspect the page for complete nodes, clear connectors, and suitable size.

Take real screenshots from this delivery: workflows and release state, table fields and partitions, tag results and update settings. Capture delivery-status screenshots after configuration is settled and replace them when status changes. Label process/test images with their time, purpose, and stage.

- **Mark assets inside the image:** Boxes, arrows, or numbers identify resources created by this task. Match multiple assets to the inventory and distinguish existing comparison assets.
- **Match captions to the inventory:** Include figure number, asset name, purpose, and environment/status.
- **Keep evidence readable:** Filter or crop as useful while retaining project/space and page context. Place marks near targets without covering names, identifiers, or status. Retain original screenshots.
- **Verify embedded media:** Confirm diagrams and screenshots actually render in the saved document; a successful upload alone is insufficient.

## Step 4: Format SQL and supporting files

Place complete key SQL together at the end and keep it consistent with deployment. Explain each node's purpose and parameters; label pre-statements, main statements, and post-statements separately. Use SQL code blocks, line breaks, and nested indentation that remain readable at document width. Formatting changes preserve SQL semantics. Explain subject, field mappings, target date, and refresh behavior for cross-source consumers.

Show table structure through a field summary and screenshots. Keep CREATE statements, auxiliary checks, complete scripts, and detailed evidence in platform resources or delivery files for maintenance and reproduction.

## Step 5: Complete the delivery review

After writing to the requested medium and applying the schedule choice, perform the following checks. Correct defects first, then recheck affected content.

### Content review

Read as a customer seeing the solution for the first time. The opening must answer: what changed, whether results match, whether performance was verified, how to use it, and what remains. Remove repetition, separate investigation records, and retain material limitations. Put the acceptance conclusion first and detailed evidence in attachments.

### Factual review

Compare with platform and task evidence: sources, semantics, asset names/links, deployment, grants, schedules, and original-resource preservation. State manual, scheduled, migration, and performance verification scopes separately. Synchronize text, inventory, and screenshots after schedule changes.

### Rendered review

Actually inspect the final document page or a trusted rendered preview, covering the opening, body tables/visuals, and final SQL. Also read back content and links.

| Item | Passing condition |
|---|---|
| Text and tables | Clear hierarchy, concise paragraphs, sensible widths/wrapping, and legible resource names and links. |
| Diagrams | Complete, readable nodes/connectors and a chain matching the solution. |
| Asset screenshots | Task-created assets marked inside images, captions matched to inventory, names/status readable, and delivery images reflecting final configuration. |
| SQL | Correct code blocks, line breaks, indentation, execution positions, and complete code matching deployed semantics. |
| Usage and outstanding actions | Resource entry points, refresh/schedule steps, and recovery are actionable; pending items and effects are explicit. |

Keep review evidence in execution records: document version or review time, inspected scope, preview/screenshot evidence, defects, and corrections. Record a pass only after the corresponding inspection. If visual preview is restricted, follow tool recovery first. If still blocked, state completed scope, unchecked items, and recovery conditions, and label the document as a draft or pending acceptance. Final chat contains only concise results, outstanding actions, and real links.
