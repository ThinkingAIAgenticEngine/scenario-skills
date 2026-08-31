# Final Output Format and Embedded Template

> **Mandatory before every user-facing RFM result.** This file is the single rendering authority. `assets/output_contract.yaml` defines the language-neutral result/table schema; this file defines how that schema is rendered. Do not create per-language template files.

## 1. Rendering architecture

```text
RFM analysis
  → build language-neutral result object
  → resolve output_locale once
  → choose SUCCESS / PARTIAL / FAILED
  → fill the matching embedded template
  → localize visible labels/content only
  → run final self-check
  → send
```

### 1.1 Authority split

| Resource | Responsibility | Must not do |
| --- | --- | --- |
| `assets/output_contract.yaml` | Section keys, result keys, core-table columns/order | Define language-specific wording |
| `references/output_format.md` | Rendering order, embedded templates, locale rules, self-check | Change analysis/scoring semantics |
| `references/strategy_profiles.md` | Industry strategy semantics | Define table shape |

## 2. Locale policy

### 2.1 Resolve `output_locale` once

Priority:

1. Explicit user language request
2. Language of the current user request
3. Dominant language of the conversation

### 2.2 Runtime localization rules

- Use one user-facing locale for headings, table headers, statuses, segment names, profiles, notes, and strategy text.
- Do not switch languages mid-response unless bilingual output was explicitly requested.
- References may be written in English; **translate/localize their semantic labels at render time rather than copying visible English headers**.
- Follow the natural punctuation and writing conventions of `output_locale`; do not maintain hardcoded language-family punctuation maps. For Chinese (`zh*`), this means using full-width punctuation（，。；：「」“”） in all user-facing narrative text (headings, table headers, notes, strategy text, bullet content); only exempt identifiers and technical terms keep their original English form.
- Number top-level sections with Arabic numerals (`1.`–`7.`) in every locale. The number is structural; only the heading text is localized.

### 2.3 Preserve raw identifiers

Preserve the following in their original form **only where they appear as identifiers** — i.e. in `analysis_caliber`, `rfm_scoring_rule`, `segment_quality`, SQL, and AE tag/cluster definitions where alignment with platform metadata is required:

- event/property names (e.g. `payment`, `pay_amount`, `#event_time`, `add_friend`);
- `#account_id`, `#user_id`, `account_id`;
- `M_raw`, `M_scoring`;
- SQL identifiers;
- stable AE tag/cluster names and display names;
- required product/technical acronyms such as AE, TE, RFM, LTV, KPI.

**In business narrative text** (`operational_strategy` cells, `segment_result.typical_profile`, `core_conclusion`, `next_step` bullets), do not paste raw event/property identifiers; use the localized business vocabulary derived from the event/property description (for example 「内购项目」 for `payment_name`, 「添加好友」 for `add_friend`, 「评论动态」 for `comment_feed`). Cite the raw identifier parenthetically only when it is the sole unambiguous handle needed for traceability.

## 3. Output status

| Status | Use when | Renderer |
| --- | --- | --- |
| `SUCCESS` | Valid RFM result and hard validation completed | §4 |
| `PARTIAL` | Useful analysis exists but an important/requested stage is blocked or validation is NO-GO | §5 |
| `FAILED` | No valid RFM result can be produced | §6 |

A hard-validation `NO-GO` with usable analysis is `PARTIAL`, not `SUCCESS`.

## 4. SUCCESS renderer

### 4.1 Fixed section order

Render these seven semantic sections in this exact order. Localize the visible heading text; do not rename the semantic key.

1. `core_conclusion`
2. `analysis_caliber`
3. `rfm_scoring_rule`
4. `segment_result`
5. `segment_quality`
6. `operational_strategy`
7. `next_step`

Append `ae_tags` and/or `ae_clusters` only when requested/approved or actually written. Never render empty placeholders such as `Tags: N/A`.

### 4.2 Embedded SUCCESS template

This is the only SUCCESS page skeleton. **Fill slots; do not redesign the page.**

```markdown
# {{report_title}}

## 1. {{heading.core_conclusion}}
{{core_conclusion}}

## 2. {{heading.analysis_caliber}}
{{table.analysis_caliber}}

## 3. {{heading.rfm_scoring_rule}}
{{scoring_explanation}}
{{table.selected_scoring_schema}}

## 4. {{heading.segment_result}}
{{table.segment_result}}
{{optional.segment_result_note}}
{{optional.table.supplementary_segment_metrics}}

## 5. {{heading.segment_quality}}
{{table.segment_quality}}
{{optional.quality_diagnostics}}

## 6. {{heading.operational_strategy}}
{{table.operational_strategy}}

## 7. {{heading.next_step}}
{{next_step}}

{{optional.table.ae_tags}}
{{optional.table.ae_clusters}}
```

### 4.3 `core_conclusion`

Use **1–4 concise bullets** (preferred) or one short paragraph. Include only material findings:

- users covered;
- scoring/segmentation mode and runtime band profile when relevant;
- number of actual segments produced;
- most important business finding;
- GO / NO-GO for operationalization.

Do not turn this section into an execution log or add filler to reach a fixed bullet count.

### 4.4 `analysis_caliber`

Use the `analysis_caliber` schema exactly:

```text
item | definition
```

Render the required semantic rows from `output_contract.yaml` in the declared order. When a row is genuinely not applicable, render a localized dash/`N/A` equivalent rather than deleting the row.

**MMO requirement:** when TE `#account_id` is role-granular, explicitly state that role granularity and identify the custom person-level `account_id` (or equivalent field) used for person-level RFM.

### 4.5 `rfm_scoring_rule`

1. Give one concise localized explanation of the requested granularity, per-metric tie/resolution outcome, and runtime `band_profile` (for example `R5-F3-M5`).
2. Render exactly one schema:

| Runtime mode | Schema |
| --- | --- |
| Any rule-based RFM (uniform or mixed-band) | `scoring_rule` |
| Clustering | `clustering_profile` |

For rule-based RFM, use the long-form scoring table exactly:

```text
metric | requested_bands | effective_bands | score | semantic_level | value_rule
```

Rules:

- Group rows in the stable order R → F → `M_scoring`; within each metric, order `score` ascending.
- Render one row for every actual raw score band. The row count is dynamic by design.
- `requested_bands` and `effective_bands` must be repeated on that metric's rows so mixed profiles are self-explanatory.
- `semantic_level` is the Low/Mid/High lifecycle level defined in `scoring_standards.md` §2.4; localize its visible text.
- `value_rule` is the actual runtime boundary/range for that score and must preserve same-value-same-band.
- When `effective_bands < requested_bands`, explain the metric-level adjustment once above the table (for example ties collapsed F from 5 to 3).
- If `M_scoring != M_raw`, state the transformation and state that revenue reporting still uses `M_raw`.
- Clustering reports cluster profiles directly; do not invent RFM score cutoffs from cluster centres.

### 4.6 `segment_result`

Use exactly these five columns, in order:

```text
segment | user_count | user_share | revenue_share | typical_profile
```

**Row rule**

- Data-row count is **dynamic** and equals the actual segments produced.
- Default 3-level lifecycle mapping normally produces 7 rows.
- The optional 5-band-native extension may produce additional split cohorts only when R/F/M all have five effective bands; it must preserve the default seven lifecycle boundaries.
- Custom rule-based segmentation and clustering use their actual segment/cluster count.
- Never invent or pad rows to reach a fixed count.
- Append exactly one total row.

**Revenue rule**

- Use `M_raw`.
- If total `M_raw > 0`, compute segment revenue shares and total = 100%.
- If total `M_raw <= 0` or undefined, render a localized dash for revenue share and explain once below the table; never fabricate 100%.

**Optional supplementary metrics**

When median R/F/M materially improves interpretation, render the separate `supplementary_segment_metrics` table. Never add those columns to the main table.

**Chart**

Not part of the core contract. Omit by default.

### 4.7 `segment_quality`

Use exactly:

```text
check_item | result
```

Render the required checks from `output_contract.yaml`. Use clear localized statuses such as pass/warning/not assessed. Put business-shape diagnostics in a short note below the table, not in extra columns.

### 4.8 `operational_strategy`

Use exactly:

```text
segment | objective | recommended_actions | kpi
```

Rules:

- Exactly one row per displayed operational segment. Never merge segment rows in the core strategy table; discuss shared treatment in prose only if useful.
- Segment display names must exactly match `segment_result`.
- Generate the per-segment objective / actions / KPI dynamically per `references/dynamic_strategy.md`, grounded in the project's real event/property metadata gathered in Stage 1. Use `references/strategy_profiles.md` only as a completeness/direction guardrail and fallback when project metadata is insufficient; in that case state the fallback in the quality note.
- Vocabulary must match the project archetype resolved from evidence (e.g. `用户` for social / e-commerce / SaaS / hybrid; `玩家` only for game/MMO). Never name project features that the project's event metadata does not contain.
- Feature references in `recommended_actions` must use localized business names (from `event_desc` / property descriptions), not raw event/property identifiers. Reserve raw identifiers for the caliber / scoring / SQL / tag-cluster contexts where platform-metadata alignment is required.
- Keep each row concise: one objective, 1–3 actions, 1–3 KPIs.

### 4.9 `next_step`

Offer **1–4 relevant actions**, not a fixed quota. Examples:

- create AE tags/clusters when GO;
- export user-level assignments;
- LTV by segment;
- retention by segment;
- campaign effect;
- temporal migration analysis.

Use bullets or a compact action table, not both.

When rendering bullets, bold the leading action name of every bullet (for example `**创建 AE 用户标签**: …` / `**Create AE tags**: …`). Apply this consistently across all locales.

## 5. PARTIAL renderer

Use this fixed semantic order:

1. `partial_result`
2. `completed_analysis`
3. `blocking_issue`
4. `impact`
5. `required_correction`
6. `not_performed`

Embedded template:

```markdown
# {{report_title}}

## 1. {{heading.partial_result}}
{{partial_result}}

## 2. {{heading.completed_analysis}}
{{completed_analysis}}
{{optional.table.segment_result}}

## 3. {{heading.blocking_issue}}
{{blocking_issue}}

## 4. {{heading.impact}}
{{impact}}

## 5. {{heading.required_correction}}
{{required_correction}}

## 6. {{heading.not_performed}}
{{not_performed}}
```

If a valid segment table exists, use the same five-column `segment_result` schema and total-row rule as SUCCESS.

## 6. FAILED renderer

Use this fixed semantic order:

1. `stopped_at`
2. `evidence`
3. `required_input_or_correction`
4. `not_performed`

Embedded template:

```markdown
# {{report_title}}

## 1. {{heading.stopped_at}}
{{stopped_at}}

## 2. {{heading.evidence}}
{{evidence}}

## 3. {{heading.required_input_or_correction}}
{{required_input_or_correction}}

## 4. {{heading.not_performed}}
{{not_performed}}
```

Do not render empty SUCCESS sections in FAILED output.

## 7. Segment display names

### 7.1 Stable analytical keys

Default lifecycle keys:

```text
champions
lost_high_value
loyal
potential
promising
hibernating
at_risk
```

Optional 5-band-native extended keys may additionally include:

```text
champions_elite
loyal_premium
```

Custom/clustering keys follow their approved runtime definitions.

### 7.2 Localization procedure

For each run:

1. Localize each analytical key once to `output_locale` using business meaning.
2. Store that display name in the result object.
3. Reuse it unchanged in the segment table, quality commentary, strategy, migration discussion, and tag/cluster preview.
4. Hide raw keys in normal business output unless technical detail is requested.
5. Do not alternate localized, English, and bilingual labels within one run unless bilingual output was explicitly requested.

Persistent AE names come from `assets/rfm_tag_names.yaml` and are not localized per conversation.

### 7.3 Default zh-CN display names

When `output_locale` is Chinese (`zh`, `zh-CN`, `zh-Hans`, or any `zh*`), apply this default lifecycle-key → display-name mapping at the §7.2 localization step. This is the platform default for Chinese business output; a business-approved alternative overrides it.

Default lifecycle keys:

| Analytical key | zh-CN display name |
| --- | --- |
| `champions` | 重要价值用户 |
| `lost_high_value` | 高价值流失用户 |
| `loyal` | 重要保持用户 |
| `potential` | 重要发展用户 |
| `promising` | 一般发展用户 |
| `hibernating` | 沉睡用户 |
| `at_risk` | 流失风险用户 |

Optional 5-band-native extended keys:

| Analytical key | zh-CN display name |
| --- | --- |
| `champions_elite` | 顶级重要价值用户 |
| `loyal_premium` | 重要保持进阶用户 |

Rules:

- Reuse the chosen display name everywhere in the run: segment table, quality commentary, strategy, migration discussion, and tag/cluster preview.
- A business-approved alternative mapping overrides this default; record the override and reuse it consistently in reports, tag SQL, cluster SQL, and downstream analysis.
- These display names are conversational labels only; persistent AE tag/cluster names still come from `assets/rfm_tag_names.yaml` and are not localized.

## 8. Conditional AE operationalization tables

### 8.1 AE tags

Render only when tag creation was requested/approved or completed. The RFM tag is one multi-value tag `rfm_segment`; render one row per `tag_value` (lifecycle segment), reusing the localized segment display name from §7 as the row label where useful. Use exactly:

```text
tag_name | tag_value | tag_display_name | analytical_count | platform_count | analytical_difference | link
```

### 8.2 AE clusters

Render only when cluster creation was requested/approved or completed. Use exactly:

```text
cluster_name | cluster_display_name | analytical_count | platform_count | member_difference | link
```

If a resource ID/link is unavailable, state that explicitly rather than fabricating a link.

## 9. Visual style

- Keep formatting business-readable and restrained.
- Section headings: Arabic ordinal + localized heading, e.g. `## 1. {{localized heading}}`.
- Do not use emojis in headings or core tables.
- Optional leading emoji may be used sparingly in `core_conclusion` or `next_step` bullets only.
- Do not bold entire rows/columns/paragraphs.
- Do not translate raw identifiers.
- Do not embed file links inside core table cells; place them in `next_step` or conditional operationalization output.

## 10. Final self-check — mandatory

### 10.1 Locale

- [ ] Exactly one `output_locale` is active unless bilingual output was explicitly requested.
- [ ] All user-facing headings, table headers, statuses, segment names, profiles, notes, and strategy text use that locale.
- [ ] Only allowed identifiers/acronyms/persistent AE names remain untranslated, and only in technical contexts (caliber, scoring, quality, SQL, tag/cluster definitions). Business narrative text (strategy cells, typical profile, conclusion, next-step bullets) uses localized business vocabulary instead of raw event/property names.
- [ ] When `output_locale` is Chinese (`zh*`), all user-facing narrative text (headings, table headers, notes, strategy text, bullet content) uses Chinese full-width punctuation（，。；：「」“”）, while exempt identifiers and technical terms keep their original English form.

### 10.2 Structure

- [ ] Status is `SUCCESS`, `PARTIAL`, or `FAILED`.
- [ ] The matching embedded template was used.
- [ ] Required section order is preserved.
- [ ] No irrelevant empty section was added.

### 10.3 Tables

- [ ] Every core table uses the exact semantic columns/order from `output_contract.yaml`.
- [ ] Main segment table has exactly 5 columns and one total row.
- [ ] Segment data-row count equals the actual segmentation result; no fixed row count was invented.
- [ ] Strategy table has exactly 4 columns.
- [ ] Quality table has exactly 2 columns.
- [ ] Rule-based scoring uses the 6-column long-form `scoring_rule` schema; no ad-hoc 3-band/5-band table was invented.
- [ ] `requested_bands`, `effective_bands`, and the runtime band profile agree with the scoring analysis.
- [ ] Exactly one scoring schema was rendered (`scoring_rule` for any rule-based profile, including mixed-band; `clustering_profile` for clustering).
- [ ] Optional metrics were not inserted into a core table.
- [ ] Revenue-share zero/undefined rule was followed.

### 10.4 Naming

- [ ] Every runtime segment has one localized display name.
- [ ] The same display name is reused everywhere.
- [ ] Persistent AE names remain unchanged.

### 10.5 Correction gate

If any check fails, correct the render and re-check before sending.
