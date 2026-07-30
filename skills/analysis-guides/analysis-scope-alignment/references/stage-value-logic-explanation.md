# Stage Value Logic Explanation

Stage values are a summary of retention situation over a period of time, helping you quickly understand data performance. This chapter explains the calculation logic of stage values. You can view the corresponding calculation logic based on the definition of analysis metrics.

## Logic of Preset Analysis Metrics

Regardless of whether simultaneous display is enabled, the retention analysis model calculates the following preset analysis metrics. The corresponding stage value calculation logic is as follows:

| Analysis Metric | Default Calculation Logic | Optional Calculation Logic |
|-----------------|--------------------------|---------------------------|
| Initial Event Users | Stage Sum, i.e., simple sum of data from each date | Stage Average, i.e., arithmetic average, Stage Sum / Time Range |
| Retained Users | Stage Sum, i.e., simple sum of data from each date | Stage Average, i.e., arithmetic average, Stage Sum / Time Range |
| Retention Rate | Weighted Average, i.e., simple sum of retained users / simple sum of initial event users | Stage Average, i.e., arithmetic average, Stage Sum / Time Range |
| Churned Users | Stage Sum, i.e., simple sum of data from each date | Stage Average, i.e., arithmetic average, Stage Sum / Time Range |
| Churn Rate | Weighted Average, i.e., simple sum of churned users / simple sum of initial event users | - |

## Logic of Simultaneous Display Metrics

For simultaneous display metrics with different definitions, stage values use different default calculation logic to fit actual business scenarios.

### Simultaneous Display Metrics with Only Returning User Metrics

| Returning Metric Setting Method | Default Calculation Logic | Optional Calculation Logic |
|--------------------------------|--------------------------|---------------------------|
| Formula, or non-formula and not using per-user calculation method | Stage average of returning user metrics for each date | Stage Sum, i.e., simple sum of values from each date |
| Per-user calculation method (e.g., Average per User, Average Value, Period Cumulative Average per User) | Weighted Average | Stage Sum, i.e., simple sum of per-user values from each date |
| | | Stage Average, i.e., simple sum of per-user values from each date, then arithmetic average |
| | | For example, stage value of Average Count = (D1 total count + D2 total count + ...) / (D1 users + D2 users + ...) |

### Initial Date Metrics

Stage values for initial date metrics default to Stage Average, with optional Stage Sum.

### Simultaneous Display Metrics Containing Initial Date Metrics

| Metric Calculation Setting Method | Default Calculation Logic | Optional Calculation Logic |
|----------------------------------|--------------------------|---------------------------|
| Arithmetic operations between returning user metrics and initial date metrics are addition, subtraction, multiplication | Stage Average | Stage Sum, i.e., simple sum of simultaneous display metric values from each date |
| | | Weighted Average, equivalent to arithmetic average under this condition |
| Arithmetic operation is division | Weighted Average | Stage Sum, i.e., simple sum of simultaneous display metric values from each date |
| | | Stage Average, i.e., simple sum of simultaneous display metric values from each date, then arithmetic average |
| | | i.e., sum of returning user metrics from each date / sum of initial date metrics from each date |

## Impact of Incomplete Data on Stage Values

Stage value calculation excludes incomplete data and only calculates based on complete data. You can choose "Hide Incomplete Data" to avoid misunderstandings.

For example, if you view the stage value of next-day retention rate for February 1-5 on February 6, since February 6 (the next day of February 5) has not ended yet, the stage value equals the weighted average of retention rates for February 1-4. The initial event users and next-day retained users for February 5 will not be included in the stage value calculation.