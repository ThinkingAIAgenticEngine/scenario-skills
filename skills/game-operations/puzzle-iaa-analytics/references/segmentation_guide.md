# User Segmentation Creation Guide

> Segmentation semantics at the **analysis intent** level — "what to segment and how to compare."
> Tool invocation patterns: see `adapters/ae-cli.md` (only when ae-cli is present).

---

## Two Segmentation Approaches

### Approach 1: Define Condition-Based Segments (Clusters)
- Define conditions → create cluster → wait → compare
- Use: ad niche, content consumption (intervals refined in Step 06)

### Approach 2: Create Segments from Analysis Results
- Run analysis → drilldown → save users as cluster
- Use: reverse-engineer segments from results

---

## 1. Ad Niche Segmentation

Group by D1 ad view count (intervals data-driven):
- Zero: D1 ads = 0
- Light: 1 ~ X
- Medium: X+1 ~ Y
- Heavy: > Y

Compare: D2 retention, avg levels, D3-7 daily logins

---

## 2. Content Consumption Segmentation

Group by D1 levels completed (configured thresholds):
- Light: ≤ `{{threshold.content_light_max}}`
- Medium: `{{threshold.content_light_max}}`+1 ~ `{{threshold.content_medium_max}}`
- Heavy: `{{threshold.content_medium_max}}`+1 ~ `{{threshold.content_heavy_max}}`
- Overdraft: > `{{threshold.content_heavy_max}}`

Compare: D2, D3, D3-7 activity

---

## 3. Cluster/Tag Management

| Operation | Description |
|-----------|-------------|
| List clusters | `ae-cli analysis user-cluster list` |
| Get cluster detail | `ae-cli analysis user-cluster get` |
| Create cluster | `ae-cli analysis user-cluster create` |
| Refresh cluster | `ae-cli analysis user-cluster refresh` |
| List tags | `ae-cli analysis user-tag list` |
| Create tag | `ae-cli analysis user-tag create` |

---

## 4. Error Handling

| Scenario | Handling |
|----------|----------|
| Cluster not computed | Wait, check progress |
| Segment count <10 | Mark "insufficient sample" |
| Extreme distribution (90% zero ads) | Report truthfully, focus on non-zero |
