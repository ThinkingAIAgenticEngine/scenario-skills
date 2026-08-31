# Final Report Template

> **Sole output format for puzzle-iaa-analytics. Step 07 sub-agents MUST fill precisely.**

## Usage Rules

1. `{{section.field}}` — replace with actual data
2. `{{#if condition}}...{{/if}}` — conditional block
3. `{{#each list}}...{{/each}}` — loop block
4. Status: `🟢Normal` / `🟡Needs Attention` / `🔴Severe`
5. Rating: `🟢Excellent` / `🟡Needs Attention` / `🔴Severe`
6. No unreplaced `{{}}` allowed

---

# {{project.game_name}} IAA Data Postmortem Report
**Period**: {{window.start}} ~ {{window.end}} | **Version**: {{project.version}}
**Generated**: {{report.generated_at}} | **Project ID**: {{project.id}}

---

## 1. Key Metrics Summary

### 1.1 Core Retention

| Metric | Value | Baseline | Status |
|--------|-------|----------|--------|
| Day 2 Retention | {{retention.d2}}% | >35% | {{retention.d2_status}} |
| Day 3 Retention | {{retention.d3}}% | >20% | {{retention.d3_status}} |
| Day 7 Retention | {{retention.d7}}% | >12% | {{retention.d7_status}} |
| D2→D3 Decay | {{retention.decay_1_2}}% | <30% | {{retention.decay_1_2_status}} |
| D3→D7 Decay | {{retention.decay_2_7}}% | <25% | {{retention.decay_2_7_status}} |

> **Status rules**: Retention ≥baseline → 🟢; baseline×0.7~baseline → 🟡; <baseline×0.7 → 🔴. Decay ≤baseline → 🟢; baseline~baseline×1.5 → 🟡; >baseline×1.5 → 🔴.

> Judgment: {{retention.judgment}} (≤80 chars)

### 1.2 Activity

| Metric | Day 1 | Day 2 | Days 3-7 | Status |
|--------|-------|-------|----------|--------|
| Avg Duration (min) | {{activity.duration_d1}} | {{activity.duration_d2}} | {{activity.duration_d3_7}} | {{activity.duration_status}} |
| Avg Levels | {{activity.levels_d1}} | {{activity.levels_d2}} | {{activity.levels_d3_7}} | {{activity.levels_status}} |

### 1.3 Levels

| Metric | Value | Status |
|--------|-------|--------|
| First Level Pass Rate | {{level.pass_rate_l1}}% | {{level.pass_rate_l1_status}} |
| Total Levels | {{level.total_count}} | — |
{{#if level.first_below_80}}| First <80% | Level {{level.first_below_80}} | — |{{/if}}

### 1.4 Ads

| Ad Type | Impressions | Share | User Share |
|---------|------------|-------|------------|
{{#each ad.types}}| {{type_name}} | {{impressions}} | {{share}}% | {{user_share}}% |
{{/each}}

| Ad Scene | Impressions | Share | Judgment |
|----------|------------|-------|----------|
{{#each ad.scenes}}| {{scene_name}} | {{impressions}} | {{share}}% | {{judgment}} |
{{/each}}

- Overall IPU ≈ {{ad.overall_ipu}}×/user

### 1.5 User Structure

| User Type | Share | D2 | D7 | IPU Contribution |
|-----------|-------|-----|-----|-----------------|
| Pure Content (0 ads) | {{seg.zero_ad_pct}}% | {{seg.zero_ad_d2}}% | {{seg.zero_ad_d7}}% | 0% |
| Core Users | {{seg.core_pct}}% | {{seg.core_d2}}% | {{seg.core_d7}}% | {{seg.core_ipu}}% |
| Squeeze Users | {{seg.squeeze_pct}}% | {{seg.squeeze_d2}}% | {{seg.squeeze_d7}}% | {{seg.squeeze_ipu}}% |

### 1.6 Overall Rating

**{{rating.level}}**

> Rating: all 5 🟢 = Excellent; 1-2 🟡 or 1 🔴 = Needs Attention; ≥3 🔴 = Severe.

**Most Critical Issue**: {{rating.one_line_problem}}

---

## 2. Churn Causal Chain

### 2.1 Overview

```
Root ① → Intermediate ② → Symptom ③ → Outcome ④
```

{{#if chain2}}
### Chain 1: [{{chain1.type}} — {{chain1.summary}}]
**Facts**:
{{#each chain1.facts}}- {{description}} (Step {{step}})
{{/each}}
**Reasoning**: {{chain1.reasoning}}
**Severity**: {{chain1.severity}} | **Impact**: ~{{chain1.affected_pct}}% of {{chain1.affected_group}}

### Chain 2: [{{chain2.type}} — {{chain2.summary}}]
(Same structure)
{{/if}}

### 2.2 Composite Causal Diagram

```
         ┌──────────┐
         │ {{causal_tree.root}} │
         └─────┬────┘
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐
│{{mid_1}}│ │{{mid_2}}│ │{{mid_3}}│
└──┬───┘ └──┬───┘ └──┬───┘
   └────────┼────────┘
            ▼
     ┌────────────┐
     │{{causal_tree.symptom}}│
     └────────────┘
```

### 2.3 Key Data Support

| Finding | Metric | Value | Baseline | Diff | Severity |
|---------|--------|-------|----------|------|----------|
{{#each data_support}}| {{finding}} | {{metric}} | {{value}} | {{benchmark}} | {{diff}} | {{severity}} |
{{/each}}

---

## 3. Core User Profile and Revenue Structure

### 3.1 User Tier Overview

| Type | Definition | Share | D2 | D7 | IPU |
|------|-----------|-------|-----|-----|-----|
| Core | Ads {{seg.core_ad_min}}-{{seg.core_ad_max}}× ∩ Levels {{seg.core_level_min}}-{{seg.core_level_max}}/D1 | {{seg.core_pct}}% | {{seg.core_d2}}% | {{seg.core_d7}}% | {{seg.core_ipu}}% |
| Squeeze | Ads ≥{{seg.squeeze_ad_min}}× ∩ D7<baseline | {{seg.squeeze_pct}}% | {{seg.squeeze_d2}}% | {{seg.squeeze_d7}}% | {{seg.squeeze_ipu}}% |
| Pure Content | Zero ads ∩ Retention≥baseline | {{seg.content_pct}}% | {{seg.content_d2}}% | {{seg.content_d7}}% | 0% |

### 3.2 Core User Profile

- Ads: {{profile.core_ad_range}}×/day. Levels: {{profile.core_level_range}} (optimal ~{{profile.core_optimal_level}})
- D2 {{profile.core_d2}}% / D7 {{profile.core_d7}}% — **{{profile.core_vs_overall_label}}** overall
- IPU Efficiency: {{profile.core_efficiency}}x — {{profile.core_efficiency_label}}

### 3.3 Squeeze User Profile

{{#if seg.squeeze_pct > 0}}
- Ads: ≥{{profile.squeeze_ad_min}}×/day. Path: Fail → Ad → Still fail → Churn
- D7 = {{profile.squeeze_d7}}% ({{profile.squeeze_d7_label}})
- {{#if profile.squeeze_ipu_share > 40}}⚠️ Revenue over-dependent ({{profile.squeeze_ipu_share}}% > 40%){{/if}}
{{/if}}

### 3.4 Revenue Health

| Metric | Value | Healthy | Status |
|--------|-------|---------|--------|
| Core IPU Contribution | {{health.core_ipu_pct}}% | >50% | {{health.core_ipu_status}} |
| Squeeze IPU Contribution | {{health.squeeze_ipu_pct}}% | <30% | {{health.squeeze_ipu_status}} |
| Revenue Concentration | {{health.concentration}}% | <50% | {{health.concentration_status}} |
| Ad Penetration | {{health.penetration}}% | >50% | {{health.penetration_status}} |

**Diagnosis**: {{#if health.core_ipu_pct >= 50}}🟢 Healthy{{else if health.squeeze_ipu_pct > 40}}🔴 Unhealthy — squeeze dependent{{else if health.penetration < 30}}⚠️ Under-penetration{{else}}🟡 Needs optimization{{/if}}

---

## 4. Optimization Action Checklist

### 4.1 Priority

| Level | Meaning | Impact | Timeline |
|-------|---------|--------|----------|
| 🔴 P0 | Urgent — core retention & revenue | D2 +3-5% | This week |
| 🟡 P1 | Important — mid-term balance | D7 +2-3% | Next version |
| 🟢 P2 | Optimization — long-term | D30 +1-2% | Future |

{{#each actions.p0}}
### 🔴 P0-{{index}}: {{title}}
**Data Basis**: {{#each findings}}- {{description}} (Step {{step}}){{/each}}
**Measures**: {{#each measures}}{{number}}. {{description}}{{/each}}
**Expected**: {{expected_effect}} | **KPIs**: {{kpi_list}}
{{/each}}

### 4.2 Impact Estimation

| Action | Priority | D2 Lift | D7 Lift | IPU Impact | Cost |
|--------|----------|---------|---------|------------|------|
{{#each impact_estimates}}| {{name}} | {{priority}} | +{{d2_lift}}% | +{{d7_lift}}% | {{ipu_impact}} | {{cost}} |
{{/each}}

### 4.3 Version Plan

{{#each version_plan.next_version}}
- [ ] {{priority_label}}: {{short_desc}}
{{/each}}

{{#if ab_test}}
### 4.4 AB Test
- Experiment: {{ab_test.experiment_desc}} | Control: current
- Metrics: {{ab_test.core_metrics}} | Sample: ≥{{ab_test.sample_size}}/group | Duration: ≥{{ab_test.min_days}}d
{{/if}}

---

## 5. Detailed Analysis Data

### 5.1 Core Diagnostics (Step 02)
{{core_diagnostics.content}}
### 5.2 Level Deep Dive (Step 03)
{{level_analysis.content}}
### 5.3 User Path (Step 04)
{{user_path_analysis.content}}
### 5.4 Segmentation (Step 05)
{{segmentation_report.content}}
### 5.5 Data-Driven Intervals (Step 06)
{{interval_analysis.content}}

---

## Appendix: Data Integrity

- **Modules**: {{appendix.success_count}}/5 succeeded{{#if appendix.degraded_count}} ({{appendix.degraded_count}} degraded){{/if}}
- **Limitations**: {{#each appendix.limitations}}{{index}}. {{description}}{{/each}}
{{#if appendix.small_sample_warning}}- ⚠️ Small sample (n={{appendix.small_sample_n}}) — directional only{{/if}}

---

*Generated by puzzle-iaa-analytics skill. Window: {{window.start}} ~ {{window.end}}.*
