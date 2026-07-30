# LTV Industry Benchmarks Reference

## LTV Benchmarks by Game Type

| Game Type | 7-Day LTV | 30-Day LTV | 90-Day LTV | Notes |
|-----------|-----------|-------------|-------------|-------|
| SLG | $5-$8 | $12-$18 | $22-$38 | High payment depth, long LTV cycle |
| MMO | $6-$9 | $11-$17 | $18-$28 | Rich payment points, social-driven |
| Card | $4.50-$7.50 | $9-$14 | $14-$22 | Gacha-driven, hero progression |
| Casual | $1.20-$2.30 | $2.30-$3.80 | $3-$5.30 | Large user base, ad monetization |
| Board | $7.50-$12 | $15-$23 | $27-$42 | Strong user payment awareness, high LTV |

## LTV Monitoring Alert Thresholds

| Metric | Yellow Flag | Red Flag |
|--------|-----------|---------|
| 7-Day LTV | MoM ↓10% | MoM ↓20% |
| 30-Day LTV | MoM ↓15% | MoM ↓25% |
| Channel LTV | Below benchmark 30% | Below benchmark 50% |

## Healthy LTV Decay Curve

| Day | Cumulative Payment % | Description |
|-----|---------------------|-------------|
| D1 | 30%-40% | Strongest first-day payment willingness |
| D3 | 50%-60% | First 3 days contribute half |
| D7 | 70%-80% | First week contributes most |
| D14 | 85%-90% | Growth slows after 2 weeks |
| D30 | 95%-100% | Near final value |

**Anomalous Decay Signals**:
- D1 proportion too low (<20%): Insufficient first-day payment guidance
- D7 proportion too low (<50%): Mid-term retention/payment design issue
- D30 still high growth: Long-LTV-cycle game characteristic (e.g., SLG)
