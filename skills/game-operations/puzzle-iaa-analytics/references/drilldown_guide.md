# User Drilldown Operations Guide

> Drilldown semantics at the **analysis intent** level — "what to do," not "which tool."
> Tool invocation patterns: see `adapters/ae-cli.md` (only when ae-cli is present).

---

## Core Principles

- All parameters MUST come from actual analysis results — never guess
- User IDs MUST come from drilldown results — never guess
- Always get user list first, then individual event sequences

---

## 1. Getting User Lists from Analysis Results

### General Semantics

- **Input**: A data point in a completed analysis result
- **Operation**: Expand to get the specific user list
- **Parameters**: source analysis type (event/retention/funnel), target date, group dimension, retention days/lost side, funnel step/churned side

### Event Analysis Drilldown
- Target date format matches source analysis granularity
- Group values from source analysis results

### Retention Analysis Drilldown
- Specify retention days (1=D1, 7=D7)
- Option: retained or lost users

### Funnel Analysis Drilldown
- Specify step number (from 1)
- Option: converted or churned users

---

## 2. Querying Individual User Event Sequences

- **Input**: User ID (from drilldown) + event scope + date range
- **Operation**: All behavior records for that user on specified dates, sorted by time
- **Parameters**: user ID, event name list, discrete dates (NOT range), time granularity

---

## 3. Standard Drilldown Flows

### Churned User Behavior Trace
```
1. Run churn retention → get data points
2. Drilldown churned user list (lost side)
3. Sample 30-50 users
4. Query each user's last-session level and ad behaviors
5. Aggregate: stuck levels, ad-then-fail rate, frustration exit rate
```

### High-Value User Behavior Analysis
```
1. Run event analysis → get target group data
2. Drilldown user list
3. Sample users
4. Compare behaviors across segments
```

---

## 4. Error Handling

| Scenario | Handling |
|----------|----------|
| Drilldown returns empty | Mark STEP_EMPTY |
| Individual query empty | Skip, continue |
| Sample >50 | Take first 50, note scope |
| Timeout | Reduce sample or date range |
