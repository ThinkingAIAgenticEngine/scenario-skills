# Quick Reference & Benchmarks

## Quick Reference Card

### Essential CLI Commands

```bash
# Authentication
ae-cli auth status
ae-cli auth login

# Data exploration
ae-cli analysis-meta event list --project-id <id>
ae-cli analysis-meta property list --project-id <id> --table-type event

# Dashboard operations
ae-cli analysis dashboard list --project-id <id>
ae-cli analysis dashboard get --project-id <id> --dashboard-id <id>
ae-cli analysis dashboard-report-data run --project-id <id> --dashboard-id <id>

# Ad-hoc queries
ae-cli analysis adhoc run --project-id <id> --model-type event --definition '<ai_definition_json>'

# Report & Dashboard creation
ae-cli analysis report create --project-id <id> --report-name "<name>" --model-type <type> --definition '<ai_definition_json>'
ae-cli analysis dashboard create --project-id <id> --dashboard-name "<name>" --initial-report-id <report_id>
```

### Key Formulas

```
First Purchase Rate = First-Time Payers / New Registered Users × 100%
First Purchase ARPU = First Purchase Revenue / First-Time Payers
Funnel Conversion = Next Stage Users / Previous Stage Users × 100%
```

---

## Industry Benchmarks

### First Purchase Rate by Game Type

| Game Type | First Purchase Rate | First Purchase ARPU | Target Range |
|-----------|-------------------|--------------------|--------------|
| RPG | 4-6% | $4.99-7.99 | 3-8% |
| SLG | 6-8% | $7.99-12.99 | 5-10% |
| MOBA | 2-3% | $2.99-4.99 | 1-5% |
| Casual | 5-8% | $2.49-3.99 | 4-10% |
| Card/Puzzle | 8-12% | $2.99-5.99 | 6-15% |

### Key Metric Benchmarks

| Metric | Excellent | Good | Acceptable | At Risk |
|--------|-----------|------|------------|---------|
| First Purchase Rate | >8% | 5-8% | 3-5% | <3% |
| D1 Retention | >50% | 40-50% | 30-40% | <30% |
| Median Time to First Purchase | <24h | 24-48h | 48-72h | >72h |
| Paying User D1 Retention | >70% | 60-70% | 50-60% | <50% |

---

## Internal Best Practices

### User Segmentation Framework

| Segment | Characteristics | First Purchase Strategy |
|---------|----------------|------------------------|
| High Spender (Whale) | High LTV, strong paying ability | Premium packages, exclusive benefits |
| Mid Spender (Dolphin) | Moderate spending | Value packages, clear progression |
| Low Spender (Minnow) | Price sensitive | Entry-level, high perceived value |

### Pricing Strategy Matrix

| User Segment | Price Range | Package Type | Key Features |
|--------------|------------|--------------|---------------|
| New User First Purchase | $0.99-4.99 | Starter Pack | High immediate value |
| Low Spender | $0.99-4.99 | Value Pack | Visible ROI |
| Mid Spender | $4.99-14.99 | Premium Pack | Progression boost |
| High Spender | $14.99+ | Elite Pack | Exclusivity, status |

### First Purchase Package Design Principles

1. **Immediate gratification**: User should feel the value instantly
2. **Clear value proposition**: Show "savings vs regular price"
3. **Limited time offer**: Create urgency with "first time only"
4. **Progression unlock**: Remove gameplay bottlenecks
5. **Social proof**: Show "X users purchased today"

---

## Common Pitfalls

### Data Analysis Pitfalls

| Pitfall | Description | Prevention |
|---------|-------------|------------|
| Definition inconsistency | Different definitions of "first purchase" | Always confirm definition upfront |
| Small sample base | Small user base leads to volatility | Use sufficient sample size |
| Attribution error | Wrongly attributing cause | Consider multiple factors |
| Selection bias | Only looking at paying users | Include non-payers in analysis |

### Pricing Strategy Pitfalls

| Pitfall | Description | Prevention |
|---------|-------------|------------|
| Price too high | First purchase price too high | A/B test price points |
| Unclear value | User doesn't understand value | Clear UI/UX messaging |
| Wrong timing | Paywall shown too early/late | Optimize trigger timing |
| Ignoring competition | Not considering competitor pricing | Regular competitive analysis |

---

## Further Reading

- Game Operations Playbook (Internal Wiki)
- TE Analysis Best Practices (Internal Wiki)
- User Segmentation Framework (Internal Wiki)
- Pricing Strategy Guidelines (Internal Wiki)
