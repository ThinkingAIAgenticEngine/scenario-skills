# Drama Quality Assessment Report Template

> This template is for the Agent to use when generating the report in Step 5.
> `{variables}` are replaced by actual data.
> **When producing the final report, translate all headings and prose into Chinese (use the standard terms in SKILL.md "Chinese Output Glossary"), keeping numbers, tables, and overall structure unchanged.**

---

# 📊 Drama Quality Assessment Report: 《{drama_name}》

**Assessment time**: {current_date}  
**TE project ID**: {project_id} | **Type**: {drama_type_label} | **Analysis period**: {start_date} ~ {end_date}

---

## 1. Comprehensive Scorecard

> **Total score: {total_score}/100　⭐ Grade {grade} — {grade_label}**
> Recommended action: {grade_action}

| Dimension | Score | Weight | Progress Bar | Status |
|------|:---:|:---:|--------|:---:|
| First-Episode Appeal | {d1_display} | {w1_effective}% | {bar1} | {status1} |
| Completion Quality | {d2_display} | {w2_effective}% | {bar2} | {status2} |
| In-Episode Pacing | {d3_display} | {w3_effective}% | {bar3} | {status3} |
| Cliffhanger Effect | {d4_display} | {w4_effective}% | {bar4} | {status4} |
| Inter-Episode Retention | {d5_display} | {w5_effective}% | {bar5} | {status5} |
| Binge Depth | {d6_display} | {w6_effective}% | {bar6} | {status6} |
| Payment Conversion | {d7_display} | {w7_effective}% | {bar7} | {status7} |
| Heat Trend | {d8_display} | {w8_effective}% | {bar8} | {status8} |
| User Engagement | {d9_display} | {w9_effective}% | {bar9} | {status9} |

> The Weight column shows effective weights after scope selection and missing-data reallocation; displayed effective weights sum to 100%. For a missing dimension, use `N/A`, `0%`, `—`, and `⚪ N/A`. For a dimension disabled in config or excluded by the user, use `Not scored`, `0%`, `—`, and `⚪ Not scored`.

---

## 2. Per-Episode Heatmap

> 🔴 = anomaly (<40)　🟡 = watch (40-55)　🟢 = normal (>55)

| Episode | Completion Quality | In-Episode Pacing | Cliffhanger Effect | Inter-Episode Retention | Composite* | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
{episode_heatmap_rows}

\* Composite is the equal-weight mean of the dimensions available for that episode.

---

## 3. AI Diagnosis

> If deep diagnosis was skipped, keep this section and replace the subsections below with: "Deep diagnosis was skipped at the user's request."

### 📋 Overall Assessment
{narrative_summary}

### ⚠️ Issues Found (if any)
{anomaly_findings}

### 🌟 Positive Signals (if any)
{positive_signals}

---

## 4. Optimization Suggestions

{recommendations}

> If deep diagnosis was skipped, replace `{recommendations}` with: "No optimization suggestions were generated because deep diagnosis was not run."

---

## 5. Data Notes

- Data source: TE project {project_id}
- Analysis period: {start_date} ~ {end_date}
- Valid dimensions: {valid_count}/9
{missing_dimensions_note}
{excluded_dimensions_note}

---

> 💬 **You can keep asking:**
> • "At which exact timestamp does episode X see the most drop-offs?"
> • "Show me the detailed data for episodes X-Y"
> • "Compare this drama with drama XX from last week"
> • "Export this report to a Feishu doc"
> • "Create an optimization ticket in Feishu Project based on the diagnosis"
