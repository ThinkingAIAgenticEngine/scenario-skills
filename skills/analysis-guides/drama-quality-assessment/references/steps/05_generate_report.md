# Step 5: Report Generation

## Objective

Integrate Step 3's score data and Step 4's diagnostic results into a structured Markdown report and output it to the user.

## Prerequisites

- `score_data` from Step 3 (scorecard, grade, heatmap).
- `diagnosis_data` from Step 4 (if deep diagnosis was run; empty if the user chose to skip it at Checkpoint 2).
- `references/templates/report_template.md` for the overall structure.

## Input

- `score_data`: total score, grade, per-dimension scores, configured/effective weights, per-episode heatmap, `missing_dimensions`, and `excluded_dimensions`.
- `diagnosis_data`: anomalies, positive signals, recommendations, narrative summary (optional, absent when Step 4 is skipped).

## Execution Instructions

### 5.1 Read the Report Template

Read `references/templates/report_template.md` to obtain the overall structural framework of the report.

### 5.2 Assemble the Report Content

#### Section 1: Comprehensive Scorecard

Fill in the variables (`{drama_name}`, `{total_score}`, `{grade}`, per-dimension score displays, effective weights, progress bars, status) according to the "1. Comprehensive Scorecard" section of `references/templates/report_template.md`.

Always list all nine dimensions. For a valid dimension, display `score/100`, its `effective_weight`, and the corresponding status. For a missing dimension, display `N/A`, `0%`, an empty progress bar (`—`), and `⚪ N/A`. For a dimension disabled in config or excluded by the user at Checkpoint 1, display `Not scored`, `0%`, `—`, and `⚪ Not scored`. Do not display a fabricated numeric score. The Weight column always means the effective weight after scope selection and missing-data reallocation, not the configured weight; displayed effective weights must sum to exactly 100% using Step 3's rounding rule.

Progress-bar generation rules:
- `██████████` = 100 points
- one `█` per 10 points, rounded
- annotate the status icon next to the score (🟢/🟡/🔴); use `⚪ N/A` for a missing dimension

#### Section 2: Per-Episode Heatmap

Fill in the variable `{episode_heatmap_rows}` according to the "2. Per-Episode Heatmap" section of `references/templates/report_template.md`.

* The composite score is the equal-weight mean of the available dimensions for that episode

Anomaly marking rules:
- score < 40 → 🔴 red highlight
- score 40-55 → 🟡 yellow attention
- score > 55 → normal display

#### Section 3: AI Diagnosis

Directly output Step 4's `diagnosis_data.narrative_summary` and the anomaly-finding list. If Step 4 was skipped (user chose direct report), retain this section and replace its body with a concise note that deep diagnosis was skipped at the user's request.

#### Section 4: Optimization Suggestions

Directly output Step 4's `diagnosis_data.recommendations` list. If Step 4 was skipped, retain this section and state that no optimization suggestions were generated because deep diagnosis was not run. This keeps the report's five-section structure stable.

### 5.3 Missing-Data Notes

If some dimensions are missing due to unavailable data, disabled in config, or excluded by the user, distinguish these cases in Data Notes:

```
⚠️ Data availability note:
The following dimensions could not be assessed due to data issues and were excluded from the total score:
- In-Episode Pacing: the project provides neither playback-progress tracking nor a playback-duration property, so pacing cannot be analyzed
- Payment Conversion: this is a free drama with no payment data

Valid dimensions: 7/9; valid dimensions' effective weights were reallocated proportionally and missing dimensions have an effective weight of 0%
Not-scored dimensions: {excluded_dimensions with each exclusion reason, or "none"}; their effective weights are also 0%
```

### 5.4 Interaction Guidance

At the end of the report, guide the user toward further interaction:

```
---
💬 You can keep asking:
• "At which exact timestamp does episode 3 see the most drop-offs?"
• "Show me the detailed data for episodes 5-8"
• "Compare this drama with drama XX from last week"
• "Export this report to a Feishu doc"
• "Create an optimization ticket in Feishu Project based on the diagnosis"
```

### 5.5 Full Report Format Example

See the complete Markdown template in `references/templates/report_template.md`.

### 5.6 Output Strategy

1. **Output directly in the conversation**: the default approach; the user can read it directly
2. **Export to a Feishu doc** (when the user explicitly requests):
   - call the `lark-doc` skill to create a Feishu document
   - write the report content into the document
3. **Export to a Feishu Base** (when the user requests structured data):
   - call the `lark-base` skill to create a Base
   - write the heatmap data into the table

Default to direct conversation output; only call Feishu export when the user explicitly requests it.

### 5.7 Completion Marker

After the report is output, tell the user:
```
✅ Assessment complete! The above is the full quality assessment report for 《{drama_name}》.

All data comes from TE project {project_id}, analysis period {start_date} ~ {end_date}.
To adjust analysis parameters or dig into a dimension, just tell me.
```

## Output

- The final Chinese Markdown report, following `references/templates/report_template.md` structure (5 sections), with all `{variables}` substituted and all prose translated to Chinese per the Language Convention.

## Verification (final independent check before output)

Run these checks independently — this is a separate final pass, distinct from Step 3's score verification and Step 4's root-cause cross-validation:

- [ ] Recomputed total score from valid dimensions = Σ(dimension score × configured weight) / Σ(valid configured weight) matches the report's `{total_score}` exactly.
- [ ] All 9 dimensions appear in the scorecard; valid scores are in 0-100, missing dimensions display `N/A`, and user-excluded dimensions display `Not scored`.
- [ ] Valid dimensions' displayed effective weights sum to exactly 100%; missing/user-excluded dimensions display 0% and are distinguished in "5. Data Notes".
- [ ] Sections 1-5 are all present; when Step 4 was skipped, Sections 3 and 4 contain explicit skip notes rather than disappearing.
- [ ] Heatmap episode count equals the actual analyzed episode count from Step 2.
- [ ] Every number in the report traces back to `raw_data` / `score_data` / `diagnosis_data` (no fabricated figures).
- [ ] No `{placeholder}` remains; all `{variables}` were substituted with real values.
- [ ] The full report is translated to Chinese; dimension names / grade labels / actions use the standard terms from the Chinese Output Glossary.
