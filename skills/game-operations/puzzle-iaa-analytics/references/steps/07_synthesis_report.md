# Step 07: Synthesis Report

> ## ⛔ Mandatory Gate
> Output format uniquely locked by [../templates/final_report_template.md](../templates/final_report_template.md).
> Every `{{}}` placeholder MUST be replaced. 3 sub-agents fill the template.
> Sub-agents are data fillers, not writers.

## Objective

Aggregate Steps 02-06 results. 3 sub-agents fill the template → mechanical assembly → final report.

## Input / Output

Input: All step outputs + [../templates/final_report_template.md](../templates/final_report_template.md)
Output: `{{workspace_dir}}/final_report.md`

### 7.0 Prerequisite Check

Steps 02-06 successful modules < 3 → FATAL.

### 7.1 Batch Read

Read all step outputs + the final report template.

### 7.2 Sub-Agent A: Chapters 1+2 (Key Metrics + Causal Chain)

Read: template (full) + 5 analysis files.
Output: `chapters_1_2.md`

Fill rules: tables use actual data (2 decimals), status from template rules, causal chains ≥2 (4-segment each, ≥3 facts), ≤80 chars per judgment.

### 7.3 Sub-Agent B: Chapter 4 (Optimization Actions)

Read: template + analysis files + chapters_1_2.md.
Output: `chapter_4.md`

Fill rules: P0 ≥2, P1 ≥1, P2 0-2. Each: data basis (≥2), measures (≥2), expected effect (≤80 chars with numbers), verification metrics.
Cost: Low/Medium/High. IPU impact: Revenue optimization / +10-15% / Neutral / Short-term decline.

### 7.4 Sub-Agent C: Chapter 3 (User Profile + Revenue Structure)

Read: template + segmentation + interval + core diagnostics.
Output: `chapter_3.md`

Fill rules: 3.1 table 4 rows locked. IPU efficiency = contribution/user share (1 decimal). Conditional blocks per template. 3.4 table 4 rows locked.

### 7.5 Mechanical Assembly

Concatenate: header → chapters_1_2 → chapter_3 → chapter_4 → raw data chapter → appendix.

### 7.6 Display and Confirm

Show final_report.md. Ask: complete? publish?

## Sub-Agent Universal Constraints

1. Do not add/remove table rows. 2. No self-judgment. 3. 100% placeholder fill. 4. Conditional blocks per rules. 5. 2 decimal places. 6. "—" when data missing.

## Status Output

- `STEP_SUCCESS` — Report complete, all placeholders filled
- `STEP_ERROR` — Partial chapters empty
- `STEP_FATAL` — Insufficient data or template missing
