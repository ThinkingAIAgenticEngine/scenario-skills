# Puzzle IAA Game Analysis Methodology

> Business logic reference — analysis reasoning and judgment criteria, tool-agnostic.
> Precise metric definitions: see `metric_definitions.md`.

---

## 1. Basic Diagnostics

### 1.1 Retention Decay
- D2, D3, D7 trends; decay ratios
- Decay Ratio 2 > Decay Ratio 1 × 2 → mid-term content/goal traction insufficient

### 1.2 Play Duration
- D1/D2/D3-7 averages
- D1 >90min + D2 <20min → one-day player pattern

### 1.3 Levels Completed
- D1/D2/subsequent daily averages
- D1 >40 → consumption too fast. Moderate + stable → healthy

### 1.4 Ad Placement Breakdown
- Count by type (stamina, item, revive, boost) and scene
- Punitive high share → churn risk

### 1.5 Level Deep Dive
- L1 pass rate, IPU per 10-level stage, per-level ad cause, level retention/pass curves

---

## 2. User Path and Churn Points

### 2.1 Register → First 10 Levels Funnel
```
Registration → Enter L1 → Complete L1 → First Ad → Complete L5 → Complete L10
```
- Register→L1 churn → tech issues. Enter→Complete L1 → tutorial breakage. Post-first-ad churn → forced ad deterrence

### 2.2 Last-Session Churn Trace
- Churn = `{{threshold.churn_definition_days}}` days no login
- Trace last session: stuck level, failures, ads watched, ad-then-fail
- Frustration exit rate by level

---

## 3. User Segmentation

### 3.1 By D1 Ad Niche
- Zero / Light / Medium / Heavy (data-driven intervals)
- Compare retention, levels across segments

### 3.2 By D1 Content Consumption
- Light ≤`{{threshold.content_light_max}}` / Medium ≤`{{threshold.content_medium_max}}` / Heavy ≤`{{threshold.content_heavy_max}}` / Overdraft >`{{threshold.content_heavy_max}}`
- Find one-day player boundary

---

## 4. Data-Driven Intervals

> Core principle: Do NOT preset intervals. Probe with fine-grained data; let natural knee points define boundaries.

### 4.1 Ad Frequency-Retention Curve
- X: daily ad count, Y: retention rate
- Knee detection → healthy ad cap
- Overlay contribution share → distinguish core vs squeeze

### 4.2 Levels-Retention Curve
- X: daily levels, Y: retention
- Peak → optimal push volume. Cliff → overdraft boundary

### 4.3 Core User Identification
- Cross-ref: healthy ad interval ∩ optimal level interval → core users
- Traits: high retention, long lifecycle, steady contribution

---

## 5. Attribution and Priorities

### 5.1 Causal Chain Synthesis
```
Difficulty spike → passive ad surge → squeeze zone → frustration → retention fracture
```

### 5.2 Recommendations
- **P0**: Smooth difficulty, cap punitive ads, cap D1 content
- **P1**: Patch funnel leaks, design intervention mechanisms, expand reward-type ads

---

## Deliverables

1. Key Metrics Summary Table
2. Churn Causal Chain Diagram
3. Core User Profile and Revenue Structure
4. Prioritized Optimization Action Checklist
