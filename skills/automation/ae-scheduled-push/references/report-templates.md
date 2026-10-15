# Analysis Report Layout Templates and Slot Specification

Templates govern **layout**, not content: data, metric definitions, sections, and analysis text are all decided by the spec (queries + outline); the template only decides "what it looks like". Select or finalize the template during the BUILD phase; during the RUN phase only results are filled into the slots.

## 1. Built-in Templates (2 sets)

| id | Best for | Layout structure (per the current implementation) |
|---|---|---|
| `daily` | Daily report | Dark banner header (report name + statistical window (the `{{window_range}}` metric definition, same source as the title) + project) → KPI metric card grid (one card per value-query column, large numbers) → chart card area (rows queries with a chart config render line/bar inline SVG, using the first 2 columns, up to 14 periods) → collapsible detail area (a data table per rows query, collapsed by default, horizontally scrollable when expanded) → sectioned analysis cards (numbering + left color bar; sections whose title contains "Risk" get an amber warning style) → footer |
| `weekly` | Weekly report / **monthly report (alias)** | Dark banner header → KPI metric card grid → sectioned analysis cards (per section: numbering + section title + analysis text + the first 5 rows of the bound data table) → chart card area → collapsible detail area → footer (sections-first suits monthly report interpretation) |

Selection rule: report has ≤2 sections and is metric-driven → daily; many sections and interpretation-driven → weekly; **monthly window → monthly (= the weekly layout, sections-first suits monthly report interpretation)**. If neither fits → rework a finalized version per user requirements (see section 2). An invalid template id string is rejected by the script (die 2).

**Trend chart config**: charts do not appear automatically — a **rows query** needs `queries[].chart` configured (`line`/`bar`, see push-spec-schema.md; value queries take the KPI-card branch, where `chart` has no effect), and the first 2 result columns must be "label column + numeric column" (e.g. `SELECT "$part_date" AS d, COUNT(...) AS v`). The "last 7 periods" data range is covered by the query window/SQL itself; the template renders all rows returned by the query (≤14 periods).

**Attribution tone discipline**: when analysis text explains "why it rose/fell" and the data cannot support a causal judgment, always use speculative tone (may / possibly / suspected) and describe phenomena first (numbers, comparisons, magnitude of change) — a customer-facing automated report must never present speculation as a definitive conclusion (LLM slot-filling in the RUN message template is under the same constraint).

**Title range**: the default title already uses `{{window_range}}` (weekly/monthly windows show the full range, preventing misreading as a single day); the custom `title_template` vocabulary is `{{task_name}}`/`{{date}}`/`{{window_range}}`.

## 2. Template Rework (BUILD phase)

When the template does not meet user requirements, rework it during the BUILD phase per user requirements (change the layout structure, add/remove blocks, adjust density); **the LLM reworks the layout, not the data**: test-render with real data during rework, and after user confirmation inline the finalized version into `spec.content.report.template` (from then on the layout is frozen at RUN time). An inlined template may be a **body fragment** (the script shell is applied automatically) or a **complete HTML document** (when it contains `<!DOCTYPE`/`<html>`, the script uses it directly without re-wrapping).

**Inlined template placeholder syntax** (replaced at RUN-phase render):

- `{{slot:<section_id>}}` — analysis text slot: replaced with the text of the corresponding section from analysis_slots.json (HTML-escaped)
- `{{data:<label>}}` — data table slot: replaced with the HTML data table of the bound query (display-layer truncated per message.preview_rows, default 100; a failed query shows `[Fetch Failed]`)
- Leftover unmatched `{{...}}` tokens render as `[Unmatched Slot]` with a stderr WARN — **during the BUILD test run, check the HTML artifact for `[Unmatched Slot]` before final confirmation**; never push a layout with unmatched slots into a real group.
- A complete-document template (containing `<!DOCTYPE`) replaces only the two slot kinds `{{slot:*}}` / `{{data:*}}` — vocabulary placeholders such as `{{task_name}}`/`{{window_range}}` are not supported in inlined report templates (they become `[Unmatched Slot]` markers); write the title and banner text directly

## 3. Slot Specification

`analysis_slots.json` (produced by the RUN-phase Agent):

```json
{
  "slots": {
    "<section_id>": "<analysis text for this section, one paragraph in the working language>",
    ...
  }
}
```

- The key set = the `section_id` of each section in `spec.content.report.outline`, **exactly matching, no extras, no omissions** (strictly validated at the render stage; mismatch exits with code 2)
- Analysis text only describes and interprets (trends/changes/anomalies); numbers must always cite actual values from `data.json` (at render time the script loosely compares the numbers in the slot text against the data.json value set; a miss records a WARN + run_result — transcription must be accurate); when a section contains `rows_truncated_to`, honestly state "based on the first N rows"; a section whose data failed uses the placeholder text `[Data fetch failed: <summary>]` (the summary is a plain short sentence, e.g. "Data fetch failed; will retry automatically next period" — DO NOT copy the technical original text of the data.json section's error field; if omitted, a data-anomaly notice is automatically appended to the message tail)
- The LLM only produces this text; data, metric definitions, outline, and layout all come from the spec

## 4. HTML Delivery Specification

The rendered artifact is a **single-file self-contained HTML** (aligned with the platform delivery specification):

- All styles inline (`<style>` or element-level style), no external resources loaded; fonts use the system stack
- Both chart implementations are allowed: ① **inline SVG** written directly in the markup (the built-in templates take this path — generated statically at the render stage from data.json and queries[].chart); ② **in-page script rendering** (custom templates may take this path — for complex charts such as multi-channel multi-series/adaptive that exceed the built-in SVG generator's capability). Prerequisites for ②: **each chart's data must be presented in a same-page data table** (chart and table share the same source; the table remains when JS is unavailable) + **graceful degradation** (when the script detects rendering failure or being disabled, the chart container is hidden — no empty frame)
- Each chart's data is presented in the same data table (chart and table share the same source data); the data table is display-layer truncated per `message.preview_rows` (default 100) and annotated "X rows total, first N rows shown in the table"
- No size validation on the script side — inspect the rendered artifact size during the BUILD test run (IM attachment size has per-channel limits, not individually tested — if over the limit, reduce detail rows / chart periods first)

## 5. Text Report Form (non-HTML)

- `report.template = "text"` (or default): text report — the body is rendered by the script's `render_text_report` (section `▍` markers + a per-section summary of the bound data segment), sent as plain text; the text report is constrained by `content.max_message_kb`, truncated when over ("… (report over length, truncated)"); the per-section bound data table always shows the first 5 rows (same metric definition as the HTML per-section bound table, not controlled by `preview_rows` — `preview_rows` only governs HTML/card data tables)
- Report HTML attachment file name: `content.file.name_template` (supports `{date}`, = window start date), defaulting back to `delivery.file_name`

## 6. Report Card Form (`report.template = "card"`)

In-group chart card — report data + LLM analysis text delivered as a single Feishu Card 2.0 message, no attachment. Suited to monthly/weekly report scenarios where "charts are laid out directly in the group" (blueprint = the monthly-report acceptance-tested card).

**Card skeleton** (full field mapping, no new spec fields):

1. header: `title_template` (default `[Report]{task_name} {window_range}`)
2. statistical window row (markdown)
3. data segments (in queries declaration order): value query → KPI markdown row (per column `**label**: value`); rows + `chart` query → VChart chart component (`line`/`bar`, long-table first column as the X axis, each numeric column as one line — long-table field names are fixed as `date` (first column)/`metric` (column name)/`value` (numeric); VChart xField/yField/seriesField follow this); rows without `chart` → table component (`display_name` header, `preview_rows` display-layer truncation + "first N rows shown in the card")
4. sectioned analysis (in outline order): `**▍{title}**` marker + slot-text markdown paragraph
5. footer: `# Data auto-generated by scheduled-push`; ⚠ annotations for failed fetch segments / SQL hitting the LIMIT are inserted before the footer (same wording as the text report)

**Delivery and degradation**: requires at least one im_cli or Feishu webhook mechanism (intercepted by static validation); if the card cannot be sent → degrade to the **full text report** delivered as plain text (R5 delivery first, WARNING logged). The card form produces no HTML attachment and is not subject to the file_ok gate. In dry-run (`--stage render` without `--push`), stdout prints the degraded text preview; the card structure itself is recorded in the `card` field of `run_result.json` in the same directory — check that file during the BUILD phase to review the card structure.

**Layout boundary**: the built-in card governs structure, not visuals — no KPI card grid / amber warning sections or other visual systems (that is the HTML template's territory); for visual customization use an inlined HTML template. Data segment order = queries declaration order, analysis section order = outline order — deterministic rendering.
