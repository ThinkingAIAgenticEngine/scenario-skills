# Phase 3: Root Cause Analysis & Recommendations

## Root Cause Analysis Framework

### Four Dimensions

| Dimension | Key Questions | Data Indicators |
|-----------|---------------|-----------------|
| User Quality | Are new users high quality? Right targeting? | Registration source, device, IP distribution |
| Product Experience | Is the game engaging enough? | Day 1/3/7 retention rates |
| Pricing Strategy | Is the price point appropriate? | Price sensitivity, willingness to pay distribution |
| External Factors | Competition, seasonality, market trends? | Industry benchmarks, competitor activity |

### Analysis Workflow

```
                    ┌─────────────────┐
                    │  Trend Analysis │
                    │  (YoY/MoM/DoD)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ User Quality│  │   Product   │  │   Pricing   │
    │   Analysis  │  │  Experience │  │   Strategy  │
    └─────────────┘  └─────────────┘  └─────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │   Root Cause    │
                    │   Summary +     │
                    │ Recommendations │
                    └─────────────────┘
```

---

## Dimension 1: User Quality Analysis

### Key Metrics

| Metric | Healthy Range | Warning | Critical |
|--------|---------------|---------|----------|
| First Purchase Rate | 5-8% | 3-5% | <3% |
| D1 Retention | >40% | 30-40% | <30% |
| Median Time to First Purchase | <48h | 48-72h | >72h |
| Paying User D1 Retention | >60% | 50-60% | <50% |

### CLI Queries

```bash
# User quality by registration source
ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type event \
  --definition '{"time_range":{"mode":"custom","start_time":"<start_date> 00:00:00","end_time":"<end_date> 23:59:59"},"time_particle_size":"day","metrics":[{"event":"first_purchase","aggregation":"user_count"},{"event":"user_register","aggregation":"user_count"}],"groups":[{"field":{"name":"channel","type":"user_property"}}]}' \
  --format json
```

The names are examples. Use compiler candidates or user-confirmed names; do not
send raw QP or frontend DTOs.

### Diagnostic Questions

1. Is the drop concentrated in specific channels?
2. Are organic vs paid user ratios changing?
3. Are there quality issues from specific acquisition sources?

---

## Dimension 2: Product Experience Analysis

### Key Metrics

| Metric | Healthy Range | Warning | Critical |
|--------|---------------|---------|----------|
| D1 Retention | >40% | 30-40% | <30% |
| D3 Retention | >25% | 20-25% | <20% |
| Paying User D1 Retention | >60% | 50-60% | <50% |
| Avg. Game Time Before First Purchase | >60min | 30-60min | <30min |

### Diagnostic Questions

1. Is retention declining, suggesting engagement issues?
2. Are users reaching the first pay trigger point?
3. Is there a gameplay progression bottleneck?

---

## Dimension 3: Pricing Strategy Analysis

### Price Sensitivity by User Segment

| Segment | Recommended Price Range | Strategy |
|---------|------------------------|----------|
| Low Spender | $0.99-4.99 | Entry-level packages |
| Mid Spender | $4.99-14.99 | Value packages |
| High Spender | $14.99+ | Premium packages |

### Diagnostic Questions

1. Is the first purchase price point too high?
2. Is the package value proposition clear?
3. Are there competitor pricing pressures?

---

## Dimension 4: External Factors

### Factors to Check

1. **Seasonality**: Chinese New Year, National Day, etc.
2. **Competition**: Major game releases, competitor promotions
3. **Market Trends**: Industry-wide payment behavior changes
4. **Regulatory**: Gaming time restrictions, payment regulations

### Industry Benchmarks

| Game Type | First Purchase Rate | First Purchase ARPU |
|-----------|-------------------|---------------------|
| RPG | 4-6% | $4.99-7.99 |
| SLG | 6-8% | $7.99-12.99 |
| MOBA | 2-3% | $2.99-4.99 |
| Casual | 5-8% | $2.49-3.99 |
| Card/Puzzle | 8-12% | $2.99-5.99 |

---

## Recommendations Framework

### For User Quality Issues

| Problem | Recommendation | Priority |
|---------|---------------|----------|
| Channel quality decline | Audit high-volume low-quality channels | High |
| Organic user drop | Improve ASO and organic acquisition | Medium |
| Bot/traffic issues | Strengthen anti-cheat verification | High |

### For Product Experience Issues

| Problem | Recommendation | Priority |
|---------|---------------|----------|
| Low early retention | Optimize onboarding flow | High |
| Progression bottleneck | Review difficulty curve | Medium |
| Unclear value prop | Improve paywall UI/UX | High |

### For Pricing Strategy Issues

| Problem | Recommendation | Priority |
|---------|---------------|----------|
| Price too high | Introduce lower tier options | High |
| Poor value perception | Redesign package contents | Medium |
| Competitive pressure | Competitive price analysis | Medium |

### For External Factors

| Problem | Recommendation | Priority |
|---------|---------------|----------|
| Seasonality | Plan seasonal promotions | Low |
| Competition | Differentiate value proposition | Medium |
| Regulatory | Ensure compliance, adapt pricing | High |

---

## Report Template

```markdown
## Diagnostic Report: First Purchase Rate Analysis

### Basic Information
- Analysis Period: [start_date] to [end_date]
- Game Type: [game_type]
- New Users: [N]
- First-Time Payers: [N]
- **First Purchase Rate: [X.X%]** ← Highlight this

### Key Findings
[3-5 bullet points, most important first]

### Root Cause Analysis
| Dimension | Status | Description |
|-----------|--------|-------------|
| User Quality | [Normal/Anomalous] | [Details] |
| Product Experience | [Normal/Anomalous] | [Details] |
| Pricing Strategy | [Normal/Anomalous] | [Details] |
| External Factors | [Normal/Anomalous] | [Details] |

### Recommendations
1. **[High Priority]** [Specific recommendation]
2. **[Medium Priority]** [Specific recommendation]
3. **[Low Priority]** [Specific recommendation]

### Next Steps
- [ ] [Action item 1]
- [ ] [Action item 2]
- [ ] [Action item 3]
```

---

## Phase 3 Closing Guidance

```
Phase 3 root cause analysis complete.

Would you like to:
- Dive deeper into a specific dimension?
- Create a detailed optimization plan?
- Set up follow-up monitoring metrics?
- End this analysis session?
```
