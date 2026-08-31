# Churn Causal Chain

> Connect Steps 02-06 findings into causal chains from symptom to root cause.

## Overview

```
Root ① → Mid ② → Mid ③ → Symptom ④ → Outcome ⑤
  {{root}}  →  {{mid_1}}  →  {{mid_2}}  →  {{symptom}}  →  {{outcome}}
```

## Chain 1: [{{chain_1_name}}]

**Data Facts**:
- {{fact_1}} (Step {{step_num_1}})
- {{fact_2}} (Step {{step_num_2}})

**Causal Reasoning**: {{fact_1}} → {{intermediate}} → {{final_symptom}}

**Severity**: 🔴High / 🟡Medium / 🟢Low | **Impact**: ~{{affected_pct}}%

---

## Chain 2: [{{chain_2_name}}]

(Same structure)

---

## Composite Causal Diagram

```
         ┌──────────────┐
         │{{upstream_root}}│
         └──────┬───────┘
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌──────┐  ┌──────┐  ┌──────┐
│{{mid_1}}│  │{{mid_2}}│  │{{mid_3}}│
└──┬───┘  └──┬───┘  └──┬───┘
   └─────────┼─────────┘
             ▼
      ┌────────────┐
      │{{final_symptom}}│
      └────────────┘
```

## Key Data Support

| Finding | Metric | Value | Baseline | Diff |
|---------|--------|-------|----------|------|
| {{finding_1}} | {{metric_1}} | {{value_1}} | {{benchmark_1}} | {{diff_1}} |
| {{finding_2}} | {{metric_2}} | {{value_2}} | {{benchmark_2}} | {{diff_2}} |
| {{finding_3}} | {{metric_3}} | {{value_3}} | {{benchmark_3}} | {{diff_3}} |
