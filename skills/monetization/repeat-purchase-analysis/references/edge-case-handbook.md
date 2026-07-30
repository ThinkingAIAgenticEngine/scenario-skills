# Edge Case Handling Handbook

Edge case handling handbook for the main skill to reference.

---

## Data Layer Exceptions

| Scenario | Detection Method | Handling Strategy | Response Template |
|----------|------------------|-------------------|-------------------|
| **No purchase events found** | `list_events` returns no purchase/subscribe/order events | Prompt user to confirm event name; list available events | "⚠️ No purchase-related events detected. Available events: [list]. Please confirm which event represents user purchases." |
| **Insufficient sample size** | Repurchase users < 100 | Warn about reliability; suggest expanding time range | "⚠️ Current sample size (N={count}) is below recommended threshold (N≥100). Conclusions may be unreliable. Consider expanding the time range." |
| **Data latency issues** | Latest data date is T-N (N>2) | Note the delay in report; adjust analysis period | "ℹ️ Data has a {N}-day delay. Analysis covers up to {latest_date}." |
| **Missing key properties** | No amount/product_type fields | Ask for alternative property names | "⚠️ Missing expected properties (amount, product_type). Are there alternative field names I should use?" |
| **No repurchase users** | Retention query returns 0% | Check cycle definition or expand range | "⚠️ No repurchase users detected. This may indicate: (1) Incorrect repurchase cycle, (2) Data quality issues, or (3) Genuine zero repurchase. Please verify." |
| **100% repurchase rate** | All users repurchased | Check for auto-renewal not being tracked | "⚠️ 100% repurchase rate detected. Please verify if auto-renewal events are being properly tracked." |

## Business Layer Exceptions

| Scenario | Detection Method | Handling Strategy | Response Template |
|----------|------------------|-------------------|-------------------|
| **Abnormal spike** | Daily repurchase rate > 90% or 3x average | Check for promotional campaigns or data anomalies | "ℹ️ Detected unusually high repurchase rate on {date} ({rate}%). This may be due to promotional campaigns or data anomalies." |
| **All-time low** | Rate drops to historical minimum | Immediate escalation; deep dive recommended | "🔴 Repurchase rate ({rate}%) is at an all-time low. Immediate attention recommended." |
| **Channel data missing** | Channel field empty/NULL for >50% users | Use available segments; note limitation | "ℹ️ Channel data is missing for {pct}% of users. Channel comparison will be based on available data only." |
| **New user dominant** | New users > 80% of sample | Flag potential sample bias | "ℹ️ New users comprise {pct}% of the sample. This may skew overall repurchase rate. Consider analyzing new vs returning separately." |
| **Single product type** | Only one product type detected | Skip product comparison; note homogeneity | "ℹ️ Only one product type detected ({type}). Product comparison analysis will be skipped." |

## User Interaction Exceptions

| Scenario | Handling Approach |
|----------|-------------------|
| **User provides wrong event name** | Politely confirm: "I couldn't find '{event_name}'. Did you mean '{suggested_event}'?" |
| **User requests unsupported time range** | Explain limitation: "I can analyze data up to {latest_date}. Would you like me to analyze a different period?" |
| **User asks for real-time data** | Clarify: "Analysis is based on processed data (T-1). Real-time metrics are not available through this skill." |
| **User requests data export** | Redirect: "This skill focuses on analysis and insights. For data export, please use the dashboard or contact your data team." |
| **User disagrees with findings** | Acknowledge + investigate: "I understand your concern. Let me verify the data and methodology..." |

## Decision Tree for Common Edge Cases

```
Data Quality Issues
├── No events found
│   └── → List available events → Ask user to confirm
├── Sample < 100
│   └── → Warn + Continue with disclaimer OR Suggest expansion
├── 100% repurchase
│   └── → Check auto-renewal tracking → Flag for verification
└── No repurchase users
    └── → Verify cycle definition → Check data → Expand range

User Requirement Issues
├── Changes business type mid-analysis
│   └── → Acknowledge → Adjust parameters → Offer restart
├── Asks multiple questions
│   └── → Prioritize (P0 > P1 > P2) → Answer most specific first
└── Requests unsupported analysis
    └── → Clarify scope → Suggest appropriate skill/resource

Data Anomalies
├── Abnormal spike (>3x avg)
│   └── → Note in report → Ask about campaigns
└── Historical low
    └── → Flag as 🔴 → Recommend immediate action
```
