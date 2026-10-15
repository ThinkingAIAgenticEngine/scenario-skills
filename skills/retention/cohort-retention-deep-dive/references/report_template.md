# Cohort Retention Deep Dive - Report Template

Use this skeleton for every report. Fill all required sections; drop optional sections when a module was not run. Match the user's language.

```markdown
# Retention Deep Dive Report

## 1. Curve Shape Diagnosis

- Model: {generic cohort | active-user}, metric: {D1/D7/D30}, window: {dates}
- Shape: {across-cohort drop | within-cohort drop | scheduled cliff at D{N} | gradual decay}
- Confidence: {High | Medium | Low} + one-line reason

## 2. Layered Attribution

For a single-window comparison:

| Dimension | Slice | Retention | Share | Drag/lift vs overall | Confidence |
|-----------|-------|-----------|-------|----------------------|------------|

- State: drag/lift values sum to zero and do not explain a period change.

For a period-over-period question:

| Dimension | Slice | Baseline rate/share | Current rate/share | Rate effect | Mix effect | Total effect | Confidence |
|-----------|-------|---------------------|--------------------|-------------|------------|--------------|------------|

- Top driver: {slice} contributes {X}pp of the {total change}, split into {rate effect} and {mix effect}.
- (Flag any n < 50 slice as unclassified)

## 3. Inflection Points

| Day | Drop rate | Beat (confirmed?) | Confidence |
|-----|-----------|-------------------|------------|

## 4. Key-Behavior Correlation

| Behavior | Exposure window | Outcome window | Association lift (pp) | Coverage | Priority signal | Reading |
|----------|-----------------|----------------|-----------------------|----------|-----------------|---------|

- Top Aha-moment candidate: {behavior} (association lift {X}pp, coverage {Y}%); causal impact is unproven.

## 5. Optimization Lever Ranking

| Rank | Breakpoint day | Segment | Behavior | Opportunity index | Confidence |
|------|----------------|---------|----------|-------------------|------------|

## 6. Caveats

- Correlation is not causation; every inference above is a heuristic
- Sample-size guardrails applied per `metrics.md`
- External factors (events, updates, competitors) may not be captured
```

Then append the standard ending menu from SKILL.md.
