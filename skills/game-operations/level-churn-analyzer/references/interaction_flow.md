## Interaction Flow (Follow this order)

**Step 1 - Define Analysis Parameters**

Collect and validate the following information:

**1. Game Type** (Card/RPG/SLG/Casual/Match-3/Runner/etc.) - Affects recommendation specificity
- Validation: Select from predefined list or specify "Other"

**2. Level Type** (Main/Challenge/Event)
- Validation: One of these three options, or custom user-defined type

**3. Level Range** (e.g., 1-30, "all", or custom level ID list)
- Supported formats:
  - `"all"` → Analyze all levels (max 200, auto-sampling if exceeded)
  - `"X-Y"` (e.g., 1-30) → Numeric range, validate X and Y are positive integers with X < Y
  - Level ID list (e.g., `"level_1,level_2,level_3"`) → Comma-separated level IDs
  - Mixed format (e.g., `"1,2,3,level_A,level_B"`) → Supports both numeric and string level IDs
- Validation logic:
  - If `"all"` → Accept, but warn if >200 levels (will use representative sampling)
  - If range format (contains "-") → Validate: 1 ≤ start < end ≤ 10000, reject negatives
  - If list format (contains ",") → Validate each level ID is non-empty, max 50 IDs
  - Otherwise → Prompt: "Please use format: X-Y (e.g., 1-30), 'all', or level ID list (e.g., level_1,level_2)"
- Production limits:
  - Max range span: 10,000 levels
  - Max list items: 50 level IDs
  - "all" auto-sampling threshold: 200 levels

**4. User Segment** (All users/New users/Silent users/Paid users/Custom)
- Supported formats:
  - **Predefined**: All users, New users, Silent users, Paid users, Highly active users, Churn-risk users
  - **Custom**: Any user-defined condition, e.g.:
    - "Users registered within 7 days"
    - "Paid users with VIP level 3+"
    - "Users with 5+ consecutive login days"
    - "Users with payment activity in last 30 days"
    - "Users currently at levels 10-20"
- Handling:
  - If matches predefined → Use corresponding filter conditions
  - If custom description → Confirm with user, convert to user attribute filters
  - If uncertain → Ask: "Please describe the segment conditions (registration time, payment status, activity level, etc.)"

**5. Churn Definition** (Days of inactivity to count as churn, default: 3)
- Validation: Positive integer, range 1-30 days
- Invalid input → Prompt: "Please enter a number between 1-30. Default is 3 days."

**6. Time Range** (e.g., last 7 days, last 30 days)
- Validation: Supports "last X days" or date range "YYYY-MM-DD to YYYY-MM-DD"
- Invalid input → Show examples and ask again

**7. Project ID**
- Validation: Positive integer
- Invalid input → Prompt: "Project ID should be a number, please confirm"

**Input Validation Failure Template:**
```
⚠️ Parameter Format Error

Error field: {parameter_name}
Input value: {user_input}
Reason: {specific_reason}

Correct format examples:
- Level range: "1-30" or "all" or "level_1,level_2,level_3"
  ⚠️ Limits: max span 10,000; max 50 IDs in list; "all" auto-samples if >200 levels
- User segment: "All users" or "New users" or "Users registered within 7 days"
- Churn definition: Number 1-30 (e.g., 3)
- Time range: "Last 30 days" or "2026-03-01 to "2026-04-01"
- Project ID: Positive number (e.g., 123)

Common errors:
- Negative numbers: Use positive integers only
- Invalid range: Ensure start < end (e.g., "1-100", not "100-1")
- Range too large: Maximum span is 10,000 levels
- List too long: Maximum 50 level IDs

Please re-enter:
```

**Step 2 - Event Confirmation & Data Validation**

After confirming parameters, execute analysis with data validation:

**2.1 Level Event Confirmation**

Use `list_events` to query all events, **MUST follow this process**:

1. **Keyword Matching**: Search for events containing these keywords (case-insensitive):
   - level, stage, mission, game, round, chapter, map, dungeon
   - start, begin, enter, play, attempt

2. **Multi-Event Confirmation Logic**:

   - **If 0 matching events found**:
     ```
     ⚠️ No level-related events found

     Please tell me the event name used to track level starts in your project, for example:
     - level_start / level_enter / level_play
     - game_start / mission_begin / round_start
     - Or other custom event names
     ```

   - **If 1 matching event found**:
     ```
     📋 Detected the following level event: {event_name}
     Use this event for analysis?
     - Yes → Continue analysis
     - No → Please provide the correct event name: ________
     ```

   - **If multiple matching events found (MUST list options for user confirmation)**:
     ```
     📋 Multiple possible level events detected. Please confirm which one to use:

     | No. | Event Name | Event Description | Pattern |
     |-----|------------|-------------------|---------|
     | 1 | level_start | Level start | Most common |
     | 2 | game_level | Game level | Alternative |
     | 3 | mission_begin | Mission begin | Mission-based |
     | 4 | dungeon_enter | Dungeon enter | Dungeon/RPG |

     Please enter the number or event name to select: ________
     (To use another event, please enter the event name directly)
     ```

3. **After event confirmation**: Record the user-selected event name and use it consistently for subsequent analysis

**2.2 Data Availability Check**

After event confirmation, continue checking:
- Check if data exists in the time range
- Validate data quality (sample size, latency)

**Sample Size Validation with Confidence Assessment:**

Unified adaptive template:
```
📊 Sample Size Assessment

Total challenging users: {n}
Churned users: {churned}
Confidence Level: {High/Medium/Low/Very Low}
Margin of Error: {margin}%

{IF n < 100}
⚠️ Insufficient Sample Size
Current sample ({n} users) is below minimum threshold.
Results may be unreliable. Recommended actions:
1. Expand time range (e.g., last 60 days instead of 30)
2. Broaden user segment (e.g., "All users" instead of "New users")
3. Continue with caution: severity will be downgraded one level

How would you like to proceed?
- [ ] Expand time range
- [ ] Adjust user segment
- [ ] Continue with downgraded severity
{ELSE IF n < 500}
⚠️ Limited Sample Size
Current sample: {n} users (Low confidence: ±5-10% margin)
Severity classifications include confidence intervals.
P0/P1 boundary cases will be flagged for verification.

Continue with confidence warnings? (Yes/No)
{ELSE IF n < 1000}
ℹ️ Adequate Sample Size
Current sample: {n} users (Medium confidence: ±3-5% margin)
Boundary cases will be flagged. Proceeding with standard analysis.
{ELSE}
✓ Excellent Sample Size
Current sample: {n} users (High confidence: ±2-3% margin)
Proceeding with standard analysis.
{END}
```

Confidence tier reference:
- n ≥ 1000: High confidence (±2-3% margin)
- 500 ≤ n < 1000: Medium confidence (±3-5% margin)
- 100 ≤ n < 500: Low confidence (±5-10% margin)
- n < 100: Very Low confidence (±10%+ margin)

**2.3 Error Handling**

If data is abnormal, use this template:

```
⚠️ Data Anomaly - Cannot Complete Analysis

Possible causes:
- No data in time range → Suggest expanding time range
- Insufficient sample size → Current: {X} users, recommend 100+ users
- Event properties missing → Cannot perform deep analysis

Please confirm or adjust parameters and retry.
```

**Sample Size Confidence Warning (Inline):**

When displaying results with confidence considerations, add inline markers:
```
📊 Chokepoint Analysis Results (with confidence)

| Level | Severity | Users | 95% CI | Status |
|-------|----------|-------|--------|--------|
| 32 | 🔴 P0 | 2,847 | 12.1%-15.7% | High ✓ |
| 28 | 🟠 P1 | 892 | 8.9%-13.5% | Medium |
| 15 | 🟡 P2 | 234 | 4.2%-8.8% | Low ⚠️ |

⚠️ Level 28: Near P0 boundary with medium confidence — verify before prioritizing
⚠️ Level 15: Low confidence — consider expanding sample before acting
```

Note: Confidence warnings are now integrated into the unified sample size template above.

**Step 3 - Output Diagnostic Report**

After data validation, generate structured report:
- Analysis overview (use `templates/overview_section.md`)
- Key chokepoint levels (use `templates/chokepoint_table.md`)
- Top chokepoint details (use `templates/level_details.md`)
- Action recommendations (use `templates/action_recommendations.md`)

**Required Report Ending:**
```markdown
---

**📋 Analysis Complete - Choose Next Step:**

**1. Continue Deep Analysis**
   Common dimensions: Failure reasons / Power differences / Item usage / Behavior paths / User comparison
   → Or analyze by any available attribute
   → Ask: `What attributes are available for analysis?`

**2. Analyze Other Levels**

**3. End Analysis**

---
```

**Step 4 - Guide Deep Analysis (Optional)**

If user chooses "Continue Deep Analysis":

**4.1 Pre-validate Available Properties (MUST)**

⚠️ **Before offering analysis dimensions, first call `list_properties` to check which properties are actually available.**

**Pre-validation Flow:**
1. Call `list_properties` for the confirmed level event
2. Filter available properties by type:
   - String properties → Can analyze: Failure reasons, Behavior paths
   - Number properties → Can analyze: Power differences, Item effectiveness
   - Boolean properties → Can analyze: First-attempt vs repeat comparison
3. **Only offer dimensions that have supporting properties available**

**Example - Properties Available → Filtered Dimensions:**
```
Available properties found:
- fail_reason (Failure reason): string type ✅
- user_power (User power): number type ✅
- items_used (Items used): string type ✅
- retry_count (Retry count): number type ✅
- pre_action (Previous action): string type ❌ (null/empty)

Based on available properties, I can analyze:
1️⃣ Failure reason distribution (fail_reason) ✓
2️⃣ Power vs. pass rate relationship (user_power) ✓
3️⃣ Item usage impact on completion (items_used) ✓
4️⃣ Retry count patterns (retry_count) ✓
5️⃣ Behavior paths — ❌ Not available (pre_action missing data)

Which dimensions would you like to analyze?
```

**Property Unavailable Handling:**
```
⚠️ Property Not Available

The dimension you selected requires `{property_name}`, but this property:
- Is not instrumented in your project, OR
- Has no data in the selected time range, OR
- Is not available for the confirmed level event

Available dimensions based on your data:
[Show only dimensions with available properties]

Would you like to analyze one of these instead?
```

**4.2 Execute Deep Analysis**

After user selects from **validated** available dimensions:
- Dynamically generate report based on selection
- All selected dimensions are guaranteed to have data

**Dynamic Report Generation Rules:**
- User selects 1-2 dimensions → Generate lean version (3-4 sections)
- User selects 3+ dimensions → Generate full version (6-8 sections)
- Unclear selection → Default to core version (5 sections)

**Report Section Priority:**
1. **Core sections** (Required): Analysis overview, Root cause diagnosis, Optimization plan
2. **Extension sections** (Based on dimension selection):
   - Select "Failure reasons" → Include failure reason breakdown
   - Select "Power differences" → Include power distribution analysis
   - Select "Item usage" → Include item effectiveness analysis
   - Select "Behavior paths" → Include path analysis
   - Select "User comparison" → Include segment comparison

```
User asks: What attributes are available for analysis?

Skill:
Let me check the properties for level {X} events...
[Call list_properties]

Available properties found:
- fail_reason (Failure reason): string type
- user_power (User power): number type
- items_used (Items used): string type
- retry_count (Retry count): number type
- pre_action (Previous action): string type

Recommended analysis angles:
1. Failure reason distribution (fail_reason)
2. Power vs. pass rate relationship (user_power)
3. Item usage impact on completion (items_used)
4. Retry count distribution (retry_count)

Which angle would you like to analyze?
```

**Report Output Requirements:**

1. **Must include**: Header overview, Key chokepoint list, Root cause diagnosis, Action recommendations
2. **Recommended visualization**: Level churn rate trend chart, Chokepoint distribution heatmap
3. **Tiered output**: Display by P0/P1/P2 priority levels
4. **Actionable**: All recommendations must be specific and executable
5. **Must include next-step guidance**: Use standard guidance format from Step 3

---

