---
name: ltv-prediction
description: >
  Predict internet product user lifetime value (LTV) and lifecycle (LT) from
  retention and revenue data. Use when the user asks about LTV, user lifetime
  value, LT, user lifecycle, lifecycle forecast, payback period, retention
  fitting, retention decay, retention curve, channel quality assessment,
  product revenue forecast, user value estimation, or active days forecast —
  for games, tools, social, e-commerce, or any internet product.
---


# LTV & LT Prediction for the Internet Industry

## AI Execution Workflow (Must Read)

When this skill is triggered, execute the following steps in order. DO NOT skip any step.

### Step 1: Confirm the Data Shape and Prediction Target

Confirm with the user or identify from user input:

1. **What is the prediction target?**
   - **LTV** (user lifetime value, revenue) → requires retention + ARPU data
   - **LT** (user lifecycle, average active days) → requires retention data only
   - If the user is unclear, ask

2. **What is the data?** Retention rate series / daily LTV series / retention + ARPU / raw event table / semi-structured data pulled via MCP / user feature table
3. **How many days are available?** This directly determines the safe range of the prediction window (see the table below)
4. **Which day do you need to predict to?** D30 / D60 / D90 / D180 / D365?
5. **Do you have CAC?** Required if payback analysis is needed (LTV only)

> **If the user has no data at all**: Tell the user that at least a D1~D7 retention rate or LTV series is required to make a prediction. You can provide industry benchmark data for similar products to make a rough estimate, but you must note in the report "Based on industry benchmarks, not actual data".

#### Step 1A: Data Acquisition Method

**1A-1. Single-day registration** (e.g., "new users on January 1")
- Calculate the difference between today's date and the registration date = available retention days
  - Example: Today is January 18, registration date is January 1 → D1~D17, 17 days of retention available
  - Example: Today is January 3, registration date is January 1 → only D1~D2, 2 days of retention

**1A-2. Time-range aggregation** (e.g., "all of January", "January 1 to January 15")
- Calculate the number of days N in the registration interval, and the distance from the current date to each date in the registration interval
- Different registration dates produce different numbers of retention days:
  - Example: Today is February 1, analyzing January → earliest 1/1 has D1~D31, latest 1/31 only D1
- **Data acquisition priority**:
  1. Preferentially pull weighted retention rates for each sub-cohort via MCP/API
  2. If no MCP interface is available, fall back to the appendix SQL (weighted retention)
- **Calculate the effective cohort count for each retention point**:
  - For each retention point D_N, count how many sub-cohorts contribute: `effective cohort count = number of dates in the registration interval that are >= N days ago from today`
  - Example: For January, D30 has data only for 1/1 and 1/2 cohorts → effective cohort count = 2
  - Helper function (AI can execute directly to avoid manual calculation errors):

    ```python
    from datetime import date, timedelta

    def calc_effective_cohorts(reg_start, reg_end, today, max_days=90):
        """Return {retention_day: effective_cohort_count}"""
        reg_dates = [reg_start + timedelta(days=i)
                     for i in range((reg_end - reg_start).days + 1)]
        return {n: sum(1 for d in reg_dates if (today - d).days >= n)
                for n in range(1, max_days + 1)}
    ```

- **Safe window correction**:
  - No longer simply determined by the available days of the latest cohort
  - Instead, take the **maximum retention day where the effective cohort count >= 5** as the available data upper bound
  - Example: For January, D15 effective cohort count = 17 (sufficient), D25 effective cohort count = 7 (sufficient), D31 effective cohort count = 1 (insufficient)
    → The reliable data available is only D1~D25; D26+ weighted retention can be computed but are not reliable
- **Annotations in the report**:
  - Effective cohort count for each retention node
  - Data points with D_N effective cohort count < 5 are marked as "low confidence" and excluded from fitting
  - Long-tail data is annotated as "only from early cohorts, survivorship bias exists"

**1A-3. Retention/LTV sequence provided directly** → use directly

**1A-4. Cannot determine** → ask the user

**Forecast window**:
- If the user does not specify a forecast horizon → determine automatically by the safe window (see Step 2)
- If the user specifies forecast days → execute with the specified value; trigger a disclaimer when exceeding the safe window

> **Note**: The AI must obtain the current date via the system (using the `date` command or the `currentDate` field in the context). Do not fabricate it.

### Step 2: Assess Feasibility

**Data volume determines the prediction window.** Based on experimental validation:

| Available Data | Safe Prediction Window | Notes |
|---------------|------------------------|-------|
| < 3 days | **Prediction not recommended** | Too little data; none of the three curves can be reliably fitted; forced forecasting produces very large errors |
| 3–6 days | Next 3–5 days | Barely fittable, but LT estimation has almost no reference value |
| 7 days | Next 7~10 days | Only short-term extrapolation; error ~5% |
| 14 days | Next 14~20 days | Trend starts to become clear |
| 30 days | Next 30~60 days | Curve shape is basically locked |
| 60+ days | Next 365 days | Long-term prediction is possible |

**When data is insufficient (< 7 days)**:
- Fitting can still be attempted, but the report must clearly annotate:
  - `WARNING: Severely insufficient data: only D1~D{actual_days}, {actual_days} days of retention; forecast deviation is very large`
  - `This result has no business reference value; it is recommended to accumulate at least 7 days of data before evaluation`
- If < 3 days, prioritize advising the user to wait for more data instead of forcing output

> If the user asks to predict far beyond the safe window, you **must warn first**: "You only have X days of data; the safe prediction range is Y days. Beyond that, the deviation will be large. Do you want to continue?"

### Step 3: Check Whether a Mature Cohort Can Be Borrowed

**When the new cohort has insufficient data but an earlier mature cohort exists, you can borrow its decay rate.**

1. Check whether an earlier registration cohort exists (e.g., the new cohort only has 7 days, but there is an older cohort with 30+ days)
2. Check version consistency: if the user provides raw data, query the `app_version` field (see the version check in the "Borrow Decay Rate" section below)
3. Versions are consistent → you can use the decay rate b of the old cohort to help predict the new cohort
4. Versions are inconsistent or cannot be confirmed → only use the new cohort's own data and flag the risk

### Step 4: Execute the Fit

1. Extract user data into arrays (`x_data` = days, `y_data` = values)
2. Run all three functions (power / log / exponential) and compare R²
3. If R² < 0.7 for all functions: try segmented fitting; if that still fails → tell the user the data quality is insufficient
4. Extrapolate using the best function

### Step 5: Output the Report

Use the report template below. The key is to fill in the numbers. **The report must end with a disclaimer.**

---

## I. Path A: Direct Fitting Prediction (Primary Method)

**Core formulas**:

| Target | Formula | Data Required |
|--------|---------|---------------|
| **LTV** | `LTV = Σ R(i) × ARPU(i)` | Retention + ARPU |
| **LT** | `LT = Σ R(i)` (cumulative from D1 until retention < 0.5% or a specified upper bound) | Retention only |

- **R(i)**: retention rate on day i
- **ARPU(i)**: per-active-user payment on day i (LTV only)
- **LT is the retention-only half of LTV**: LTV = LT × ARPU

> Use this path when the user provides ready-made retention/LTV series.
> **If the user only has a raw event table or needs to pull data via MCP (Path B)**: extract the data first, then return to this path. Use the SQL in Appendix A for raw event tables; for MCP, call the query tools provided by the platform to pull retention/LTV metrics, parse them, and then use them.
> **If the user provides multiple cohorts/channels at once**: fit each channel separately and produce a separate report. If different cohorts belong to the same version, you can borrow the decay rate (see Section II), but a and ARPU are computed independently for each cohort.

### Step 1: Parse User Input

Users may provide data in various forms. Parse it into two arrays: `[days]` and `[values]`:

- **Directly pasted series of numbers**: `0.45, 0.32, 0.28...` → assume incrementing starting from D1
- **Table with day labels**: `D1=0.45, D2=0.32...` → extract key-value pairs
- **Daily incremental LTV**: use directly as y_data
- **Cumulative LTV**: derive daily increments via `ltv[i] - ltv[i-1]`, then fit
- **Retention + ARPU provided separately**: fit retention first, then multiply back by the ARPU mean
- **Retention only (LT target)**: use retention rates directly as y_data

> **When daily new users are too few**: if daily new users < 100 cause retention rate fluctuation, guide the user to use weighted retention instead of simple daily averages (weighted retention SQL is in Appendix A). If the user-provided data is already weighted, use it directly.

### Step 2: Function Fitting

Run all three functions and automatically select the one with the highest R²:

| Function | Formula | Shape | Applicable |
|----------|---------|-------|------------|
| **Power** | `y = a × x^b` | Fast early, flattens mid-to-late | Most products (games, social, content); **preferred** |
| **Logarithmic** | `y = a + b × ln(x)` | Decays faster than power | Products with clear mid-term decay |
| **Exponential** | `y = a × e^(b×x)` | Rapid decay to 0 throughout | Pure tool-type products |

```python
import numpy as np
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score

# === Input: user-provided data ===
x_data = np.array([1, 2, 3, ...])      # days
y_data = np.array([0.45, 0.32, ...])   # retention rate or daily incremental LTV

def power_func(x, a, b): return a * np.power(x, b)
def log_func(x, a, b):   return a + b * np.log(x)
def exp_func(x, a, b):   return a * np.exp(b * x)

models = {}
for name, func, bounds in [
    ('power', power_func, ([0, -2], [2, 0])),
    ('log', log_func, ([-np.inf, -np.inf], [np.inf, np.inf])),
    ('exp', exp_func, ([0, -0.5], [2, 0])),
]:
    try:
        popt, _ = curve_fit(func, x_data, y_data, bounds=bounds, maxfev=10000)
        r2 = r2_score(y_data, func(x_data, *popt))
        models[name] = (r2, func, popt)
    except:
        pass  # skip if it does not converge

if not models:
    # none of the functions converge → data has issues
    raise Exception("None of the functions converged. Check data quality (negative values, missing values, or too few days).")

best_name = max(models, key=lambda k: models[k][0])
best_r2, best_func, best_params = models[best_name]
```

**Fitting quality assessment**:

| R² | Rating | Action |
|----|--------|--------|
| ≥ 0.95 | Excellent | Use directly |
| 0.85~0.95 | Good | Usable |
| 0.70~0.85 | Fair | Usable; note in the report "fitting accuracy is fair" |
| < 0.70 | Poor | Try segmented fitting (Step 3); if that still fails, tell the user the data quality is insufficient for prediction |

### Step 3: Segmented Fitting (attempt when R² < 0.7)

```python
# Detect the changepoint: the position with the largest absolute second-order difference
diff2 = np.abs(np.diff(y_data, n=2))

# Exclude 2 points at both ends (to avoid boundary effects), and the changepoint
# cannot be too early or too late
valid_range = slice(2, len(diff2) - 2)
if len(diff2[valid_range]) > 0:
    changepoint = np.argmax(diff2[valid_range]) + valid_range.start + 1
else:
    changepoint = 0

# Segment length validation: piecewise is meaningless if any segment has fewer than 5 points
min_seg_len = 5
if changepoint < min_seg_len or changepoint > len(y_data) - min_seg_len:
    changepoint = 0

if changepoint > 0 and best_r2 < 0.7:
    # Fit the segment before the changepoint and the segment after, each with a power function
    popt1, _ = curve_fit(power_func, x_data[:changepoint], y_data[:changepoint],
                         bounds=([0, -2], [2, 0]), maxfev=10000)
    popt2, _ = curve_fit(power_func, x_data[changepoint:], y_data[changepoint:],
                         bounds=([0, -2], [2, 0]), maxfev=10000)

    # Build a piecewise function so subsequent calculations can use it directly
    def piecewise_func(x, a1, b1, a2, b2):
        x_arr = np.asarray(x, dtype=float)
        return np.where(x_arr <= changepoint,
                        a1 * np.power(x_arr, b1),
                        a2 * np.power(x_arr, b2))

    best_func = piecewise_func
    best_params = (*popt1, *popt2)
```

### Step 4A: Extrapolation (LTV)

```python
def extrapolate(x_data, y_data, best_func, best_params, target_days=365):
    """Extrapolate to target_days. Use actual values for existing data, fitted values thereafter."""
    days = np.arange(1, target_days + 1)
    actual_len = len(y_data)
    predicted = np.zeros(target_days)
    predicted[:actual_len] = y_data
    for i in range(actual_len, target_days):
        predicted[i] = max(0, best_func(i + 1, *best_params))
    cumulative = np.cumsum(predicted)
    return {
        'D30': cumulative[29], 'D60': cumulative[59],
        'D90': cumulative[89], 'D180': cumulative[179],
        'D365': cumulative[364],
        'daily': predicted, 'cumulative': cumulative,
    }

result = extrapolate(x_data, y_data, best_func, best_params, target_days=365)

# Default outputs D30/D60/D90/D180/D365. For custom milestones such as D10/D20,
# take directly from cumulative: result['cumulative'][9] → D10
```

> If the user provides retention rates: `daily incremental LTV = R(i) × ARPU(i)`, where ARPU is obtained as described in Section III.

### Step 4B: Calculate LT

```python
def safe_max_days(actual_len):
    """Automatically determine the safe forecast window upper bound based on available data volume"""
    if actual_len >= 60:
        return 730
    elif actual_len >= 30:
        return actual_len + 60
    elif actual_len >= 14:
        return actual_len + 20
    elif actual_len >= 7:
        return actual_len + 10
    elif actual_len >= 3:
        return actual_len + 5    # 3-6 days, extrapolate only 3-5 days
    else:
        return actual_len + 3    # <3 days, extreme caution

def data_status(actual_len):
    """Return a data sufficiency label for report annotation"""
    if actual_len < 3:
        return ("severely insufficient", f"WARNING: Severely insufficient data: only {actual_len} days of retention; the fitting result has almost no reference value; recommend waiting for more data")
    elif actual_len < 7:
        return ("insufficient", f"WARNING: Insufficient data: only {actual_len} days of retention; forecast deviation is very large and has no business reference value; recommend accumulating at least 7 days of data")
    elif actual_len < 14:
        return ("limited", "")
    elif actual_len < 30:
        return ("fair", "")
    else:
        return ("sufficient", "")

def calc_lt(x_data, y_data, best_func, best_params, max_days=None):
    """Calculate lifecycle = area under the retention curve.
    max_days is automatically determined by the safe window by default; the user can force a longer window (triggers a disclaimer)."""
    actual_len = len(y_data)
    safe_days = safe_max_days(actual_len)
    status_label, status_warning = data_status(actual_len)

    if max_days is None:
        max_days = safe_days
        overridden = False
    else:
        overridden = max_days > safe_days

    days = np.arange(1, max_days + 1)
    retention = np.zeros(max_days)
    retention[:actual_len] = y_data
    for i in range(actual_len, max_days):
        retention[i] = max(0, best_func(i + 1, *best_params))
    # Truncate: stop accumulating when retention rate < 0.5%
    mask = retention >= 0.005
    lt = retention[mask].sum()
    # Rough algorithm reference: only valid when retention approximates geometric decay (R(n) ≈ D1^n)
    # real products are mostly power-law decay, with errors up to 30%+
    lt_rough = 1 / (1 - y_data[0]) if y_data[0] < 1 else None

    # Return a warning when the safe window is exceeded
    warning = None
    if overridden:
        warning = (f"WARNING: The forecast window of {max_days} days exceeds the safe range (recommended <= {safe_days} days). "
                   f"The actual LT may deviate significantly; the result is for reference only and should not be used as a basis for business decisions.")

    return lt, lt_rough, max_days, safe_days, overridden, warning, status_label, status_warning, retention

lt_precise, lt_rough, max_days, safe_days, overridden, warning, status_label, status_warning, retention = calc_lt(x_data, y_data, best_func, best_params)

# Force-append a disclaimer when the safe window is exceeded
if overridden:
    print(warning)
    print(f"Safe forecast window: <= {safe_max_days(len(y_data))} days | Actual extrapolated to: {max_days} days")

# Output precise LT by default. When the user wants intermediate nodes like D10/D20,
# take them from the cumulative retention: cumulative active days for the first N days = sum(retention[:N])
```

### Step 5: Payback Period (LTV only)

**CAC acquisition priority**:

1. Provided directly by the user → use it
2. Not provided but MCP can query cost data → try to pull the spend for the corresponding date/channel via MCP, then divide by the number of new users
3. MCP cannot find it either → ask the user; if the user genuinely does not know, skip payback analysis and only output the LTV estimate

```python
def calc_payback(ltv_daily, cac):
    cumulative = np.cumsum(ltv_daily)
    idx = np.searchsorted(cumulative, cac)
    if idx >= len(cumulative):
        return None
    return idx + 1

# cac source: see the priority above
payback_days = calc_payback(result['daily'], cac)

# Only display the data; do not make subjective judgments.
# Payback expectations vary drastically across categories (hyper-casual 3 days, SLG 180 days). Leave the judgment to the user.
if payback_days is None:
    payback_status = f'Cannot recover cost within the prediction window (D{target_days})'
else:
    payback_status = f'Payback in approximately {payback_days} days'
```

---

## II. Borrowing the Decay Rate of a Mature Cohort (Advanced Path A Technique)

> Use this technique to extend the prediction range when the new cohort has less data than the safe window but a mature cohort of the same version exists. The essence is to use the decay rate of the mature cohort to assist the long-term extrapolation of the new cohort.

### Core Principle

The two parameters of the power function `y = a × x^b` have a clear division of labor:

| Parameter | Meaning | Determined by | Shareable across cohorts? |
|-----------|---------|----------------|---------------------------|
| **a** | Height/level of retention | This cohort's user quality (channel, creative, acquired audience) | Not shareable; differs per cohort |
| **b** | Rate/shape of decay | The product's own stickiness (version, gameplay, operation rhythm) | **Shareable for the same product in the same period** |

When the new cohort only has short-term data (e.g., 7 days) but a mature cohort of the same version exists (e.g., 38 days), you can:

1. Fit a reliable decay rate **b** from the mature cohort
2. Fix b for the new cohort and use only its short-term data to fit its own level **a**
3. Extrapolate long-term with `a(new) + b(borrowed)`

Experimental validation: the borrowed-b scheme yields long-term prediction errors far smaller than fitting only the short-term data itself.

### Step 1: Check Version Consistency

**If the user provides a raw event table or MCP is queryable**:

```sql
-- First check whether the app_version field exists, and list the user counts per version
SELECT
    "#app_version" AS version,
    COUNT(DISTINCT "#user_id") AS users,
    MIN("$part_date") AS first_seen,
    MAX("$part_date") AS last_seen
FROM v_event_231
WHERE "$part_event" = 'register'
    AND "$part_date" BETWEEN '2026-01-01' AND '2026-02-07'
GROUP BY "#app_version"
ORDER BY first_seen;
```

| Query Result | Judgment |
|--------------|----------|
| Only 1 version | Can borrow |
| Multiple versions, but the target cohort and the mature cohort are in the same version | Same version → can borrow |
| Multiple versions, with the target cohort and the mature cohort crossing versions | Cannot borrow; product stickiness may have changed |
| No `app_version` field | Ask the user: "Was there any version release or major update during this period?" |

**If the user directly provides ready-made data**:

Ask the user to confirm:
- "Between the mature cohort (Month-Day) and the target cohort (Month-Day), was there any version release, major campaign, or operational strategy change?"
- No → can borrow
- Yes → cannot borrow

### Step 2: Execute the Borrowing

```python
# 1. Fit the mature cohort → obtain a reliable b
x_mature = np.array([1, 2, ..., 38])  # days of the mature cohort
y_mature = mature_cohort_daily_inc_ltv  # or mature_cohort_retention for LT
popt_mature, _ = curve_fit(power_func, x_mature, y_mature,
                           bounds=([0, -2], [2, 0]), maxfev=10000)
a_mature, b_mature = popt_mature  # b_mature is the reliable decay rate

# Pre-borrowing validation: the power function's own fit must be reliable, otherwise borrowing b is meaningless
r2_mature_power = r2_score(y_mature, power_func(x_mature, *popt_mature))
if r2_mature_power < 0.7:
    raise Exception(f"Mature cohort power function fit R²={r2_mature_power:.3f}; the retention shape may not be power-law decay, borrowing b is not recommended")

# 2. New cohort: fix b = b_mature, fit only a
def power_fixed_b(x, a):
    return a * np.power(x, b_mature)

x_new = np.array([1, 2, ..., 7])  # the new cohort only has 7 days
y_new = new_cohort_daily_inc_ltv  # or new_cohort_retention for LT
popt_new, _ = curve_fit(power_fixed_b, x_new, y_new,
                        bounds=([0], [2]), maxfev=10000)
a_new = popt_new[0]

# 3. Extrapolate: new cohort's a + borrowed b
# --- For LTV ---
pred_borrowed = np.zeros(target_days)
pred_borrowed[:len(y_new)] = y_new  # use actual values for existing data
for i in range(len(y_new), target_days):
    pred_borrowed[i] = max(0, power_func(i + 1, a_new, b_mature))

# --- For LT ---
lt_borrowed, *_ = calc_lt(x_new, y_new,
    lambda x, a: power_func(x, a, b_mature), (a_new,))

# 4. Also run a "self-fit only" version for comparison
popt_self, _ = curve_fit(power_func, x_new, y_new,
                         bounds=([0, -2], [2, 0]), maxfev=10000)
pred_self_only = np.zeros(target_days)
pred_self_only[:len(y_new)] = y_new
for i in range(len(y_new), target_days):
    pred_self_only[i] = max(0, power_func(i + 1, *popt_self))
```

### Step 3: How to Reflect It in the Report

**Do not average.** Self-fit and borrowed-b are based on different assumptions; mixing them is meaningless.

Recommended approach: **label sources by segment + two-column comparison**, so readers can see the basis for each segment of the prediction.

See the "hybrid prediction" variants in the report templates below for the format.

### When to Borrow and When Not to

| Can borrow (b reusable) | Cannot borrow (b not shared) |
|--------------------------|------------------------------|
| Same version, same operation rhythm | After a major version update, product stickiness has changed |
| Same channel, different creatives | Channels differ drastically (e.g., feed vs. incentivized wall) |
| Adjacent cohorts within 1-2 weeks | Months apart, product has iterated multiple times |
| The old cohort's R² ≥ 0.85 is validated | The old cohort's own fit is unreliable |

---

## III. Where Does ARPU Come From (LTV only)

| Situation | Approach |
|-----------|----------|
| Have daily ARPU data | Use directly. For future days, use 90% of the existing mean (conservative estimate) |
| Have payment data but not computed | `ARPU = Payment Rate × ARPPU`; Payment Rate = Paying Users / Active Users; ARPPU = Total Payment / Paying Users |
| No payment data at all | Can only estimate using benchmarks from similar products; the report must note "Estimated based on industry benchmarks, not actual payment data" |

| Business Type | ARPU Reference |
|----------------|-----------------|
| IAP games | ARPDAU of similar games, or industry report median |
| Ad monetization | eCPM × estimated per-user ad impressions |
| Subscription | Monthly subscription price of similar products / 30 |
| E-commerce | Average order value of similar products × Conversion Rate |

---

## IV. Path C: ML Prediction Method (LTV only, Optional)

> **Prerequisite**: user-level feature data (profile + behavior + payment) is available, and individual LTV needs to be predicted. Used for channel quality assessment.

One row per user. Features include: user profile (gender/age/channel/region/device), behavior (active days/login frequency/level), payment (first payment time/cumulative payment amount/count). The target variable is the user's long-term LTV.

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
rf = RandomForestRegressor(n_estimators=200, max_depth=20,
                           min_samples_leaf=2, random_state=42)
rf.fit(X_train, y_train)
y_pred = rf.predict(X_test)
print(f"MAE: {mean_absolute_error(y_test, y_pred):.2f}, R²: {r2_score(y_test, y_pred):.4f}")
```

> The details of the ML method (feature engineering, hyperparameter tuning) are consistent with general modeling practices; expand only when the user specifically asks.

### Curve Fitting vs. ML

|  | Curve Fitting | ML Prediction |
|------|---------------|----------------|
| Data requirement | 30~90 days of retention/LTV series | User-level features + labels |
| Prediction granularity | Cohort average | Individual user |
| Primary use | Revenue estimation, payback judgment | Channel assessment, user segmentation |
| Complexity | Low | High |

---

## V. Anomaly Analysis (Post-Prediction Monitoring)

The prediction targets the normal trend. If actual data persistently deviates from the predicted values, follow this troubleshooting flow:

1. **Drill down by dimension**: split by channel/version/region/user group to locate the anomaly range
2. **Narrow the scope**: lock onto the smallest suspicious group
3. **Find the cause**: commonality analysis (what shared characteristics the anomalous users have) + TGI analysis (propensity of each dimension; TGI > 120 indicates significant concentration)

---

## VI. Report Templates

### Report A: LTV Curve Fitting Results

```markdown
## LTV Estimate — [Product Name / Channel Name]

**Available data**: D1 ~ D{actual_days} | **Extrapolated to**: D{target_days}
**Fitting model**: {best_name}, R² = {best_r2}

### Model Comparison

| Model | Formula | R² |
|-------|---------|-----|
| {each fitted model listed} | {formula} | {r2} |

### LTV Estimate

| Milestone | Cumulative LTV |
|-----------|----------------|
| D30 | {D30} |
| D60 | {D60} |
| D90 | {D90} |
| D180 | {D180} |
| D365 | **{D365}** |

> For custom milestones (e.g., D10/D20) requested by the user, take the value for the corresponding day from the `cumulative` array and replace the milestone column above.

### Payback Analysis

| Metric | Value |
|--------|-------|
| CAC | {cac} |
| Predicted-end LTV / CAC | {ratio} |
| Estimated payback days | {days} days / Cannot recover |

### Daily LTV Detail (output when requested by the user)

Use this table when the user has multiple registration cohorts and needs a per-day LTV detail. **Append `*` after predicted values; each cohort's boundary is judged independently**:

| Registration Date | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | ... |
|-------------------|----|----|----|----|----|----|----|----|----|-----|
| 2026-02-01 | 0.33 | 0.61 | 0.85 | 1.04 | 1.24 | 1.44 | 1.61 | 1.79 | 1.95* | ... |
| 2026-02-07 | 0.38 | 0.67 | 0.93* | 1.17* | 1.39* | 1.61* | 1.81* | 2.00* | 2.18* | ... |

> The boundary for each row depends on how many days of actual data that cohort has up to now. 02-01 has 8 days of actual data → add `*` from D9; 02-07 only has 2 days → add `*` from D3.

### Conclusions and Recommendations

1. {Data volume assessment} — extrapolated from {actual_days} days of data to {target_days} days; the safe prediction window is {safe_window} days
2. {Key finding} — LTV/CAC = {ratio}; {payback description}
3. {Recommendations}

### ⚠️ Disclaimer

This prediction is based on fitting and extrapolating historical data. The following factors may cause actual values to deviate significantly from the predicted values and are outside the model's prediction scope:

- **High Spenders**: the sudden appearance of individual high-paying users (whales) will significantly push up the actual LTV
- **Version updates**: major feature releases and content updates may change user retention and payment behavior
- **Operational activities**: limited-time events, promotions, seasons, and other short-term stimuli
- **External events**: competitor launches, policy changes, holiday effects, public opinion events
- **Channel changes**: adjustments to the acquisition strategy that change user composition

> **LTV is an estimate, not a promise.** It is recommended to refit and calibrate monthly, and to continuously correct against actual data.
```

### Report A-2: Hybrid Prediction (New cohort has insufficient data, borrowing the mature cohort's decay rate)

```markdown
## LTV Estimate — [Target Cohort] (Borrowing Mature Cohort Decay Rate)

**Target cohort**: {target_cohort} (registration date) | **Available data**: D1 ~ D{target_days}
**Mature cohort**: {mature_cohort} (registration date) | **Available data**: D1 ~ D{mature_days}
**Version consistency**: ✅ Same version ({version}) / ⚠️ Cannot confirm; based on user confirmation of no major changes

### Prediction Method

| Prediction Interval | Method | Basis |
|---------------------|--------|-------|
| D{target_days+1} ~ D{safe_window} | Fit on the target cohort's own data | Within the safe window, its own pattern is reliable |
| D{safe_window+1} ~ D{target_days_predict} | Borrow the mature cohort's decay rate b={b_mature} | Same version shares product stickiness; only fit the level parameter a of the target cohort |

### Fitting Details

| Cohort | Data Volume | Model | a | b | R² |
|--------|-------------|-------|---|---|-----|
| {mature_cohort} | D1~D{mature_days} | Power | {a_mature} | **{b_mature}** | {r2_mature} |
| {target_cohort} (borrowed b) | D1~D{target_days} | Power (b fixed) | {a_target} | {b_mature} (borrowed) | {r2_target} |
| {target_cohort} (self-fit) | D1~D{target_days} | {self_model} | {a_self} | {b_self} | {r2_self} |

### LTV Estimate

| Milestone | Recommended (borrowed b) | [Reference] self-fit only |
|-----------|--------------------------|---------------------------|
| D14 | {borrowed_d14} | {self_d14} |
| D21 | {borrowed_d21} | {self_d21} |
| D30 | **{borrowed_d30}** | {self_d30} |

> Append `*` to predicted values. The recommended value adopts the scheme that borrows the mature cohort's decay rate.

### Payback Analysis

| Metric | Value |
|--------|-------|
| CAC | {cac} |
| Predicted-end LTV / CAC | {ratio} |
| Estimated payback days | {days} days / Cannot recover |

### Conclusions

1. D{target_days+1}~D{safe_window} is based on the target cohort's own pattern (within the safe window)
2. D{safe_window+1}~D{target_days_predict} borrows the decay rate b={b_mature} of the {mature_cohort} cohort (same version, same operation cycle; product stickiness is shareable)
3. Recommended LTV(D30) = **{borrowed_d30}**

### ⚠️ Disclaimer
(Same as Report A)
```

### Report A-LT: LT Forecast Results

```markdown
## LT Estimate — [Product Name / Channel Name]

{status_banner}
**Available Data**: D1 ~ D{actual_days} | **Data Sufficiency**: {status_label} | **Fitting Model**: {best_name}, R² = {best_r2}
**Safe Forecast Window**: <= {safe_days} days | **Actual Extrapolated To**: {max_days} days {overridden_mark}

### Conclusion

1. Within the D1~D{max_days} safe window, cumulative active **{lt_precise} days** (not the complete LT; the retention decay shape beyond {max_days} days is unknown, the actual lifecycle will be higher)
2. D1 retention = {r1}; if D1 improves by 10%, LT typically improves by 15-30%
3. {data_advice}

### ⚠️ Disclaimer

This forecast is based on extrapolation of historical retention data. Factors such as version updates, operational activities, and external events may cause actual values to deviate. **LT is an estimate, not a commitment**; it is recommended to refit and recalibrate monthly.

{overridden_disclaimer}

---

### Retention Curve Fitting

| Model | Formula | R² |
|-------|---------|-----|
| {each_function} | {formula} | {r2} |

> Selected: **{best_name}**

### Cumulative Active Days (D1~D{max_days})

| Method | Value |
|--------|-------|
| Rough algorithm (1/(1-D1)) | {lt_rough} days (for reference only; only valid for geometric decay) |
| Area under curve | **{lt_precise} days** |

> Note: This value is the cumulative active days within the D1~D{max_days} forecast window and **is not equivalent to the complete lifecycle LT**. Retention beyond {max_days} days is unknown; the actual LT will be larger.

### Key Retention Nodes

{cohort_count_header}| Node | Retention Rate | Source |
|------|----------------|--------|
| D1 | {r1} | {r1_source} |
| D7 | {r7} | {r7_source} |
| D14 | {r14} | {r14_source} |
| D30 | {r30} | {r30_source} |

> {cohort_count_note}
```

**Aggregate scenario variable descriptions** (used only for time-range aggregation; leave empty for single-day scenarios):

| Variable | Meaning | Example Fill |
|----------|---------|--------------|
| `{cohort_count_header}` | Shown only in aggregate scenarios: `| Effective Cohort Count |` | `| Effective Cohort Count |` or empty |
| `{r1_source}` ~ `{r30_source}` | Data source label | `Measured (31 cohorts)` / `Forecast` / `Weighted (2 cohorts) WARNING` |
| `{cohort_count_note}` | Cohort note in aggregate scenarios | `D30 only comes from 2 sub-cohorts (1/1, 1/2); survivorship bias exists` or empty |
| `{status_banner}` | Red warning when data is insufficient | Display `> WARNING: Severely insufficient data...` when present; otherwise empty |

**Single-day scenario quick reference** (`{cohort_count_header}`, `{cohort_count_note}` are empty; `{rN_source}` is "Measured" or "Forecast"):

### Report A-LT-2: LT Hybrid Forecast (Borrowed decay rate from mature cohort)

```markdown
## LT Estimate — [Target Cohort] (Borrowed Decay Rate from Mature Cohort)

**Target Cohort**: {target_cohort} | **Available Retention**: D1 ~ D{target_days}
**Mature Cohort**: {mature_cohort} | **Available Retention**: D1 ~ D{mature_days}
**Version Consistency**: PASS same version / WARNING cannot confirm

### Conclusion

1. Within the D1~D{max_days} forecast window, cumulative active **{lt_borrowed} days** (not the complete LT; retention beyond {max_days} days is unknown)

### ⚠️ Disclaimer

This forecast is based on extrapolation of historical retention data and borrows the decay rate b from a mature cohort (assuming product stickiness is consistent within the same version). Factors such as version updates, operational activities, and external events may cause actual values to deviate. **LT is an estimate, not a commitment**; it is recommended to refit and recalibrate monthly.

---

### Cumulative Active Days (D1~D{max_days})

| Method | Recommended Value (Borrowed b) | [Reference] Self-fit Only |
|--------|--------------------------------|---------------------------|
| Cumulative active days | **{lt_borrowed} days** | {lt_self} days |

> The recommended value borrows the decay rate b={b_mature} from {mature_cohort} (product stickiness is shared within the same version)
> Note: This value is the cumulative active days within the forecast window and **is not equivalent to the complete lifecycle LT**.
```

### Report B: ML Prediction Results

```markdown
## User-Level LTV Prediction

**Model**: Random Forest | **Sample size**: {n} | **MAE**: {mae} | **R²**: {r2}

### Channel Aggregation

| Channel | User Count | Predicted per-user LTV | CAC | LTV/CAC | Rating |
|---------|------------|------------------------|-----|---------|--------|
| {channel} | {n} | {ltv} | {cac} | {ratio} | {grade} |

### Top Feature Importance
{ranking}

### ⚠️ Disclaimer
(Same as above)
```

---

## VII. Quick FAQ

| Question | Answer |
|----------|--------|
| What is the relationship between LT and LTV? | LTV = LT × ARPU. LT is the retention-only half of LTV; LTV adds revenue |
| Minimum days of data? | 30 days to start, 60 days is reliable, 90 days is ideal. 7 days can only predict the next 7~10 days. < 3 days is not recommended |
| New cohort has insufficient data? | Find a mature cohort of the same version and borrow the decay rate b (see Section II) |
| How to decide whether b can be borrowed? | Check the app_version field, or ask the user whether there was a version release/major update during the period |
| Must I split by channel? | Yes. Different channels have very different user quality; mixing them hides problems |
| Daily new users too few? | Use weighted retention to merge multiple days |
| No payment data? | Predict LT (retention only) first. For LTV, estimate ARPU with benchmarks from similar products, and note it in the report |
| Fitting R² < 0.7? | Try segmented fitting; if all functions have poor R², tell the user the data is insufficient or has quality issues |
| None of the models converge? | Check the data: negative values, missing values, or fewer than 5 days |
| Is the rough LT algorithm accurate? | Only applicable to exponential decay products, with errors up to 30%+; not recommended |
| Update frequency? | Refit once a month |
| D1 retention value? | A 10% increase in D1 typically raises LTV by 15~30% |

---

## Appendix A: SQL Extraction Templates (for Path B)

### Retention Matrix

```sql
WITH new_users AS (
    SELECT
        "$part_date" AS reg_date,
        COUNT(DISTINCT "#user_id") AS new_users
    FROM v_event_231
    WHERE "$part_event" = 'register'
        AND "$part_date" BETWEEN '2026-01-01' AND '2026-03-31'
    GROUP BY "$part_date"
),
retention AS (
    SELECT
        n.reg_date,
        DATEDIFF(l."$part_date", n.reg_date) AS day_n,
        COUNT(DISTINCT l."#user_id") AS retained_users
    FROM new_users n
    LEFT JOIN (
        SELECT DISTINCT "#user_id", "$part_date"
        FROM v_event_231
        WHERE "$part_event" = 'login'
            AND "$part_date" BETWEEN '2026-01-01' AND '2026-06-07'
    ) l ON l."#user_id" IN (
        SELECT DISTINCT "#user_id" FROM v_event_231
        WHERE "$part_event" = 'register' AND "$part_date" = n.reg_date
    ) AND l."$part_date" >= n.reg_date
    GROUP BY n.reg_date, day_n
)
SELECT
    reg_date, day_n, retained_users, new_users,
    ROUND(retained_users * 1.0 / new_users, 4) AS retention_rate
FROM retention r
JOIN new_users n USING (reg_date)
WHERE day_n BETWEEN 1 AND 90
ORDER BY reg_date, day_n;
```

### Weighted Retention (Optimized — avoids correlated subqueries)

```sql
WITH reg_users AS (
    SELECT DISTINCT "#user_id", "$part_date" AS reg_date
    FROM v_event_231
    WHERE "$part_event" = 'register'
        AND "$part_date" BETWEEN '2026-01-01' AND '2026-03-31'
),
new_users AS (
    SELECT reg_date, COUNT(DISTINCT "#user_id") AS new_users
    FROM reg_users
    GROUP BY reg_date
),
logins AS (
    SELECT DISTINCT "#user_id", "$part_date"
    FROM v_event_231
    WHERE "$part_event" = 'login'
        AND "$part_date" BETWEEN '2026-01-01' AND '2026-06-07'
),
retention AS (
    SELECT n.reg_date,
        DATEDIFF(l."$part_date", n.reg_date) AS day_n,
        COUNT(DISTINCT l."#user_id") AS retained_users
    FROM new_users n
    JOIN reg_users r ON r.reg_date = n.reg_date
    LEFT JOIN logins l ON l."#user_id" = r."#user_id"
        AND l."$part_date" >= n.reg_date
    GROUP BY n.reg_date, day_n
)
SELECT day_n,
    SUM(retained_users) AS total_retained,
    SUM(new_users) AS total_new,
    ROUND(SUM(retained_users)*1.0/SUM(new_users), 4) AS retention
FROM retention r2 JOIN new_users n USING (reg_date)
WHERE day_n BETWEEN 1 AND 90
GROUP BY day_n ORDER BY day_n;
```

### Daily ARPU

```sql
SELECT
    "$part_date",
    SUM(revenue) / COUNT(DISTINCT "#user_id") AS arpu
FROM v_event_231
WHERE "$part_event" = 'payment'
    AND "$part_date" BETWEEN '2026-01-01' AND '2026-06-07'
GROUP BY "$part_date"
ORDER BY "$part_date";
```

## Appendix B: Required Tracking

| Category | Content |
|----------|---------|
| Events | register (new user), login (active), payment (paid) |
| Event properties | revenue amount, source channel |
| User properties | channel, campaign/adset, region, device |

---

## Skill Boundaries

This skill covers LTV and LT prediction methodology (curve fitting, payback analysis, ML prediction, mature cohort borrowing). For the following scenarios, route to the companion skill:

- **User has a TE project and needs ae-cli automated data retrieval** → `ltv-prediction-cli`
- **User needs stratified LTV by RFM / pay-tier / VIP segments** → `ltv-prediction-cli` (B3 methodology)
- **User needs ae-cli report/dashboard creation for LTV results** → `ltv-prediction-cli`

This skill is preferred when the user directly provides data, needs payback analysis, wants to borrow mature cohort decay rates, or requires ML-based user-level prediction.

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
