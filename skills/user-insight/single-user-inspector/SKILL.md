---
name: single-user-inspector
description: Queries individual user profiles, tracks behavior events, analyzes payment history, monitors game progress, and diagnoses churn reasons, applicable to game operations, planning, and customer service teams. Use when users need to check a specific user/player, view user details, payment records, game progress, or ask why a user churned.
---

# single-user-inspector

**Single User Inspector** - A skill for game behavior data analysis tool to inspect individual users

## Overview

This skill is used for comprehensive data query and analysis of individual game users, supporting user profile viewing, behavior tracking, economy flow query, game progress query, and churn reason diagnosis. Through natural language interaction, it helps operations, planning, and customer service teams quickly understand individual user situations, identify issues, and formulate intervention strategies.

## Use Cases

- Customer service quickly querying user situations when handling complaints
- Operations staff analyzing churned user reasons
- Planning staff viewing specific user behavior paths
- Monitoring high-value user activity status

## Core Capabilities

| Capability | Description |
|------------|-------------|
| User Profile | View user registration info, level, payment tier, activity status |
| Behavior Tracking | View user behavior events in time series, support event aggregation |
| Economy Flow | View user recharge records, total payments, payment trends |
| Game Progress | View user level, stage progress, achievement completion |
| Churn Diagnosis | Analyze user churn reasons, provide intervention suggestions |

---

## Trigger Conditions

This skill is activated when users ask the following types of questions:

| Trigger Pattern | Examples |
|-----------------|----------|
| User Profile Query | "Check user 12345", "Player 67890 info" |
| Behavior Tracking | "What did XXX do yesterday", "User recent behavior" |
| Economy Flow Query | "How much did user XXX spend", "XXX payment records" |
| Game Progress Query | "What level is XXX", "Player progress" |
| Churn Analysis | "Why did XXX churn", "Why did 12345 stop playing" |
| Login Records | "XXX recent login status", "User 111 online time" |

---

## ae-cli Capabilities

This skill requires the following ae-cli commands (provided by the ae-analysis product skill):

| Capability Type | ae-cli Command | Required Flags |
|-----------------|---------------|----------------|
| User Profile Query | `ae-cli analysis entity-detail run` | `--project-id`, `--definition` (entity="user", cohort filter by the confirmed user identifier field, properties from discovered user properties) |
| Behavior Event Query | `ae-cli analysis event-detail run` | `--project-id`, `--definition` (event name, time_range, filters, properties from discovered event properties) |
| Economy Flow Query | `ae-cli analysis event-detail run` | `--project-id`, `--definition` (payment event name, time_range, user filter, properties from discovered event properties) |
| Game Progress Query | `ae-cli analysis entity-detail run` | `--project-id`, `--definition` (entity="user", cohort filter by the confirmed user identifier field, properties from discovered user properties) |
| Login Session Query | `ae-cli analysis event-detail run` | `--project-id`, `--definition` (login event name, time_range, user filter, properties from discovered event properties) |

### ae-cli Command Conventions

- All commands require `--project-id` to specify the target project.
- All commands require `--definition` (JSON) with the AI-facing contract. Do not pass raw QP or event_view.
- `entity-detail run`: `--definition` must include `entity` ("user"), `cohort` (user_property/tag/cluster filter), and optionally `properties` (user property names to project). User rows always include `#user_id`, `#account_id`, `#distinct_id`.
- `event-detail run`: `--definition` must include `event` (event name), `time_range`, and optionally `filters` and `properties`. Event and property names must be discovered first.
- Build entity cohorts and event filters with the identifier field confirmed for the supplied value. Never treat an opaque player ID as `#user_id` by default.
- Event names and property names must be discovered first via `ae-cli analysis-meta event list` or `ae-cli analysis-meta property list` before using them in queries. Do not guess or assume names.
- For command details, refer to the ae-analysis product skill.

### Execution Prerequisites

Before executing any data query, the following contracts must be confirmed through ae-analysis. **Do not proceed with queries if any contract cannot be confirmed.**

1. **Project contract**: `--project-id` is available and the project exists in ae-analysis.
2. **User identifier contract**: Confirm what kind of value the user supplied, then verify the matching project field (e.g. `#user_id`, `#account_id`, `#distinct_id`, or a project user property) via `ae-cli analysis-meta property list --scope user`. If the identifier field is unknown or ambiguous, ask the user to specify it.
3. **Event and property contract**: Event names and their property names used in the query scenario (e.g. payment events, login events, battle events) are confirmed via `ae-cli analysis-meta event list` and `ae-cli analysis-meta property list`. Do not guess event names or property names.

**Failure closure when contracts cannot be confirmed**:

- If ae-analysis returns "capability not found" or "not implemented" for a required command → report the capability gap and do not fabricate query results.
- If the project does not exist or the user cannot provide a valid `project-id` → ask the user to provide it; do not guess or use a default.
- If event or property names cannot be confirmed for the target project → ask the user to specify the correct names; do not assume names from other projects or generic examples.

---

## Execution Flow

```
User Input
    ↓
[Step 1: Intent Recognition] → Determine query type
    ↓
[Step 2: Parameter Extraction] → Extract user_id, time range
    ↓
[Step 2.5: Contract Verification] → Confirm project, user identifier, event/property contracts via ae-analysis
    ↓                                  (If any contract cannot be confirmed → failure closure, do not proceed)
[Step 3: ae-cli Query] → Call corresponding ae-cli commands
    ↓
[Step 4: Business Processing] → Aggregate, analyze, calculate derived metrics
    ↓
[Step 5: Result Output] → Format as human-readable report
```

---

## Step 1: Intent Recognition

### Recognition Rules

Determine query intent based on keyword matching:

```
IF text contains ["what did", "behavior", "events", "trace", "log", "history", "actions"]
   → Intent = "behavior_trace"

ELSE IF text contains ["spent", "money", "payment", "consumption", "purchase", "economy", "recharge", "paid"]
   → Intent = "economy_query"

ELSE IF text contains ["level", "progress", "stage", "achievement", "progress", "rank"]
   → Intent = "progress_query"

ELSE IF text contains ["churn", "why", "stop playing", "quit", "inactive"]
   → Intent = "churn_analysis"

ELSE IF text contains ["login", "online", "session", "active time", "last seen"]
   → Intent = "session_query"

ELSE
   → Intent = "profile_query" (default)
```

### Intent Priority

When multiple intents are matched, select based on the following priority:

```
churn_analysis > economy_query > behavior_trace > progress_query > session_query > profile_query
```

Example:
- Input: "Why did user 123 churn and how much did they spend"
- Match: churn_analysis + economy_query
- Select: churn_analysis (higher priority)

---

## Step 2: Parameter Extraction

### 2.1 User ID Extraction

Match in the following regex order, return the first successful match:

| Priority | Regex Pattern | Description |
|----------|---------------|-------------|
| 1 | `user\s*[:]?\s*(\d+)` | "user 12345" |
| 2 | `player\s*[:]?\s*(\d+)` | "player 12345" |
| 3 | `(?:uid|UID|user.?id)\s*[:]?\s*(\d+)` | "UID: 12345" |
| 4 | `#(\d{5,})` | "#12345" |
| 5 | `\b(\d{6,})\b` | 6+ digit number |

**When user ID is not matched:**
Return prompt: "❌ Please provide a user ID, e.g., 'Check user 12345'"

### 2.2 Time Range Parsing

Parse time range based on keywords:

| Keyword | Parsed Result |
|---------|---------------|
| "yesterday" | start=yesterday 00:00, end=today 00:00, label="yesterday" |
| "today" | start=today 00:00, end=now, label="today" |
| "last N days" | start=now-N days, end=now, label="last N days" |
| "last week" | Last Monday to Sunday |
| "last month" | Full previous month |
| No match | start=now-7 days, end=now, label="last 7 days" |

---

## Steps 3-4: Scenario-Based Business Logic

### Scenario A: User Profile Query (profile_query)

**Trigger Example**: "Check user 12345"

**Execution Logic**:

```
1. Query user entity details: `ae-cli analysis entity-detail run --project-id <pid> --definition '<json>'`
   - definition: entity="user", cohort filter by the confirmed identifier field = "12345"
   - properties: include user properties discovered via `ae-cli analysis-meta property list --scope user`
     (e.g. payment-related, activity-related, registration-related properties — exact names depend on the project)

2. After receiving data, calculate derived metrics using the properties returned by the query.
   Property names below are illustrative — replace with actual project property names:

   a) Payment Tier Calculation (using the project's total payment property):
      IF total_payment == 0 → "⚪ Non-paying User"
      ELIF total_payment < 10000 (cents) → "🟢 Minnow" (<$10)
      ELIF total_payment < 100000 → "🔵 Dolphin" ($10-$100)
      ELIF total_payment < 1000000 → "🟣 Whale" ($100-$1000)
      ELIF total_payment < 10000000 → "🟡 Super Whale" ($1000-$10000)
      ELSE → "💎 Ultra Whale" (>$10000)

   b) Activity Status Calculation (using the project's last activity time property):
      Current time - last_activity_property = days_diff
      IF days_diff < 1 → "🟢 Active Today"
      ELIF days_diff < 3 → "🟡 Recently Active"
      ELIF days_diff < 7 → "🟠 Declining Activity"
      ELSE → "🔴 Churned"

   c) Registration Duration (using the project's registration time property):
      Current time - registration_time_property

3. Format output (see Step 5)
```

---

### Scenario B: Behavior Tracking Query (behavior_trace)

**Trigger Example**: "What did user 12345 do yesterday"

**Execution Logic**:

```
1. Parse time range → { start: "2024-03-19T00:00:00", end: "2024-03-20T00:00:00" }

2. Determine the relevant event set for the requested behavior trace and confirm every event name through analysis metadata. Do not guess event names.

3. Query each confirmed event separately: `ae-cli analysis event-detail run --project-id <pid> --definition '<json>'`
   - definition: one confirmed event name, the parsed time_range, and a filter using the confirmed identifier field
   - use the same time range and user filter for every event query

4. Merge all returned rows and sort the combined sequence by event time before aggregation. A single `event-detail run` covers only one event and must not be presented as the user's complete behavior trace.

5. After receiving the merged event list, perform aggregation:

   a) Sort by time descending

   b) Merge consecutive similar events (merge rules):
      - Same event type
      - Time interval < 5 minutes
      - After merge display: "Event Name (consecutive N times)"

   c) Calculate online duration:
      Last event time - First event time

6. Format output (see Step 5)
```

**Event Emoji Mapping**:

| Event Keyword | Emoji |
|---------------|-------|
| Login | 🎮 |
| Logout | 👋 |
| Battle | ⚔️ |
| Fail | 💀 |
| Win/Pass | 🎉 |
| Purchase/Recharge | 💰 |
| Shop | 🏪 |
| Reward | 🎁 |
| Level Up | ⬆️ |
| Other | 📝 |

---

### Scenario C: Economy Flow Query (economy_query)

**Trigger Example**: "How much did user 12345 spend"

**Execution Logic**:

```
1. Query economy flow: `ae-cli analysis event-detail run --project-id <pid> --definition '<json>'`
   - definition: payment event name from discovered events, time_range, and a filter using the confirmed identifier field

2. After receiving data, calculate using the properties returned by the query:

   a) Total payment = sum of payment amount property (unit from project metadata → convert as needed)

   b) Payment tier (same as Scenario A)

   c) ARPPU = total / count (if count > 0)

   d) Payment trend (if time series data available):
      Last 7 days recharge vs Previous 7 days → Calculate change percentage

3. Format output (see Step 5)
```

---

### Scenario D: Churn Diagnosis Analysis (churn_analysis) ⭐ Core Scenario

**Trigger Example**: "Why did user 12345 churn"

**Execution Logic**:

```
1. Query user entity details: `ae-cli analysis entity-detail run --project-id <pid> --definition '<json>'`
   - definition: entity="user", cohort filter by the confirmed identifier field = "12345"
   - properties: include activity-related and payment-related properties discovered via `ae-cli analysis-meta property list --scope user`

2. Determine churn status (using the project's last activity time property — exact name from metadata):

   last_active = profile[<project's last activity property name>]
   days_inactive = Current time - last_active

   IF days_inactive < 7:
      Return prompt: "This user has not churned, last active X days ago"
      End flow

   is_churned = true

3. Confirm the event set needed by the enabled churn rules (for example login/logout, battle outcome, payment, progress, and social events when those concepts exist in project metadata). Query each confirmed event separately with `ae-cli analysis event-detail run --project-id <pid> --definition '<json>'`, using the same time range around last activity and a filter on the confirmed identifier field. Merge and sort all returned rows before applying any churn rule. Skip rules whose required events or properties cannot be confirmed; never substitute example names.

4. Execute churn reason identification algorithm:

   ┌─────────────────────────────────────────────────────┐
   │ Rule 1: Consecutive Failures Detection              │
   │ --------------------------------------------------- │
   │ Scan event list, count consecutive battle_fail events│
   │ IF consecutive failures >= 5:                        │
   │    Reason = {                                        │
   │        type: "consecutive_failures",                │
   │        name: "Consecutive Failures",                │
   │        detail: "Experienced X consecutive losses, strong frustration",│
   │        severity: X >= 8 ? "high" : "medium",        │
   │        confidence: 30                                │
   │    }                                                 │
   └─────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────┐
   │ Rule 2: Paid Frustration Detection                  │
   │ --------------------------------------------------- │
   │ Find pattern: purchase event → shortly after battle_fail│
   │ IF paid but still failed:                            │
   │    Reason = {                                        │
   │        type: "paid_frustration",                    │
   │        name: "Paid Frustration",                    │
   │        detail: "Paid for items but still failed, payment experience damaged",│
   │        severity: "high",                            │
   │        confidence: 25                                │
   │    }                                                 │
   └─────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────┐
   │ Rule 3: Progress Blocked Detection                  │
   │ --------------------------------------------------- │
   │ Count battle_fail times for same stage_id          │
   │ IF same stage failed >= 3 times:                     │
   │    Reason = {                                        │
   │        type: "progress_blocked",                    │
   │        name: "Progress Blocked",                    │
   │        detail: "Repeatedly failed at stage X, progress blocked",│
   │        severity: "medium",                          │
   │        confidence: 20                                │
   │    }                                                 │
   └─────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────┐
   │ Rule 4: Abnormal Exit Detection                     │
   │ --------------------------------------------------- │
   │ IF last event is not logout and no subsequent events:│
   │    Reason = {                                        │
   │        type: "abnormal_exit",                       │
   │        name: "Abnormal Exit",                       │
   │        detail: "Suspected rage quit or game crash", │
   │        severity: "medium",                          │
   │        confidence: 15                                │
   │    }                                                 │
   └─────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────┐
   │ Rule 5: Social Disconnection Detection              │
   │ --------------------------------------------------- │
   │ Check if social events decreased suddenly          │
   │ IF guild/friend events dropped significantly:        │
   │    Reason = {                                        │
   │        type: "social_disconnection",                │
   │        name: "Social Disconnection",                │
   │        detail: "Social connections weakened",       │
   │        severity: "medium",                          │
   │        confidence: 18                                │
   │    }                                                 │
   └─────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────┐
   │ Rule 6: Content Exhaustion Detection                │
   │ --------------------------------------------------- │
   │ Check if main story completed with no new content  │
   │ IF no new content available:                         │
   │    Reason = {                                        │
   │        type: "content_exhaustion",                  │
   │        name: "Content Exhaustion",                  │
   │        detail: "Main story completed, no new content",│
   │        severity: "low",                             │
   │        confidence: 12                                │
   │    }                                                 │
   └─────────────────────────────────────────────────────┘

5. Summarize diagnosis results:

   total_confidence = SUM(all reasons.confidence)
   primary_reason = Reason with highest confidence

   Result = {
       is_churned: true,
       days_inactive: days_inactive,
       last_active_time: last_active,
       confidence: MIN(total_confidence, 100),
       primary_reason: primary_reason,
       all_reasons: [All identified reasons],
       last_events: [Last 10 events]
   }

6. Format output (see Step 5)
```

---

### Scenario E: Multi-User Comparison (multi_user_comparison)

**Trigger Example**: "Compare user 123 and 456 payment"

**Execution Logic**:

```
1. Extract multiple user IDs:
   - Parse all user IDs from input
   - Limit to max_users_per_batch (default 10)

2. For each user, call relevant ae-cli commands with `--project-id` and `--definition` in parallel

3. Aggregate and compare data:
   - Create comparison table
   - Highlight differences
   - Identify patterns

4. Format comparison output
```

---

## Step 5: Result Formatting Output

### General Formatting Rules

1. **Separator**: Use `━━━━━━━━━━━━━━━` as block separator
2. **Title**: Use `[Title]` format
3. **Emoji**: Add status emoji before key information
4. **Relative Time**: Prefer relative time ("3 days ago") over absolute time
5. **Currency**: Cents → Dollars, 2 decimal places, large amounts use K/M notation

### Scenario A Output Format (User Profile)

```
━━━━━━━━━━━━━━━━━━━━━━━
User {user_id} Profile
━━━━━━━━━━━━━━━━━━━━━━━

[Basic Info]
• Registration: 2024-01-15 (65 days ago)
• Last Active: 3 days ago
• Status: 🟢 Active Today

[Game Data]
• Current Level: 45
• VIP Level: VIP3
• Online Time: 128 hours

[Payment Info]
• Total Spent: $128.00 (12 transactions)
• Payment Tier: 🔵 Dolphin
• Monthly Average: $42.60

[User Tags]
High Activity | Core Player | Social | PVE Preference

━━━━━━━━━━━━━━━━━━━━━━━
```

### Scenario B Output Format (Behavior Tracking)

```
━━━━━━━━━━━━━━━━━━━━━━━
User {user_id} {time_label} Activity
━━━━━━━━━━━━━━━━━━━━━━━

09:23  🎮 Login
09:25  ⚔️ Enter Stage 12-5
09:30  💀 Stage Failed (3 consecutive)
       └─ Last attempt used revive item but still failed
09:35  🏪 Enter Shop
09:38  💰 Purchase Stamina Pack ($0.99)
09:40  ⚔️ Retry Stage 12-5
       └─ 🎉 Success! Reward: Gold x1000
09:45  🎁 Claim Reward
09:50  👋 Logout

━━━━━━━━━━━━━━━━━━━━━━━
📊 Total {N} events, Online time {XX} minutes
```

### Scenario C Output Format (Economy Flow)

```
━━━━━━━━━━━━━━━━━━━━━━━
User {user_id} Payment Records
━━━━━━━━━━━━━━━━━━━━━━━

[Payment Overview]
• Total Spent: $128.00 (12 transactions)
• Payment Tier: 🔵 Dolphin
• ARPPU: $10.67/transaction
• First Payment: 2024-01-20
• Last Payment: 3 days ago

[Recent Payments]
┌────────────┬─────────────┬────────┐
│ Time       │ Item        │ Amount │
├────────────┼─────────────┼────────┤
│ 3 days ago │ Stamina Pack│ $0.99  │
│ 7 days ago │ Monthly Card│ $4.99  │
│ 12 days ago│ Limited Pack│ $19.99 │
└────────────┴─────────────┴────────┘

━━━━━━━━━━━━━━━━━━━━━━━
```

### Scenario D Output Format (Churn Diagnosis) ⭐

```
━━━━━━━━━━━━━━━━━━━━━━━
User {user_id} Churn Diagnosis Report
━━━━━━━━━━━━━━━━━━━━━━━

[Churn Status]
• Status: 🔴 Churned (12 days inactive)
• Last Active: 2024-03-08 20:46
• Inactive Duration: 12 days
• Diagnosis Confidence: 85%

━━━━━━━━━━━━━━━━━━━━━━━
[Primary Churn Reason]
⚠️ Consecutive Failures (Severity: High)
   └─ Experienced 5 consecutive losses, strong frustration

[Behavior Before Churn]
📅 2024-03-08 Timeline:

20:10  Enter Ranked Match
20:15  ❌ Ranked Match Failed (Game 1)
20:22  ❌ Ranked Match Failed (Game 2)
20:30  ❌ Ranked Match Failed (Game 3)
20:35  💰 Purchase Protection Card ($1.99)
20:40  ❌ Ranked Match Failed (Game 4, protection used)
20:45  ❌ Ranked Match Failed (Game 5)
20:46  💥 Force Quit Game (abnormal exit)

━━━━━━━━━━━━━━━━━━━━━━━
[Contributing Factors]
💸 Paid Frustration: Paid for protection but still failed
🚪 Abnormal Exit: Suspected rage quit or crash

[Diagnosis Conclusion]
This user experienced consecutive losses in ranked matches,
paid for protection items trying to recover,
but continued to fail causing strong frustration,
ultimately exited the game abnormally.
Typical "paid but still frustrated" churn pattern.

━━━━━━━━━━━━━━━━━━━━━━━
[Intervention Suggestions]
1️⃣ Return Package: Push return package with protection cards + consolation rewards
2️⃣ Rank Protection: Optimize rank protection mechanism after consecutive losses
3️⃣ Difficulty Adjustment: Temporarily lower match difficulty for losing streak users
4️⃣ Emotional Support: Send message acknowledging matchmaking issues

━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Error Handling

Handling strategies when ae-cli query fails:

### 1. User Not Found
```
Input: "Check user 99999"
Output: "❌ User 99999 not found, please check if user ID is correct"
```

### 2. Query Timeout
```
Input: "Check all history for user 12345"
Process: Limit query time range, return last 7 days data
Output: "⚠️ Query timeout, returning last 7 days data. For more history, please specify time range"
```

### 3. Partial Data Missing
```
Scenario: Can query user profile but not behavior events
Output: "✓ User profile query successful, but no behavior records in this time period"
```

### 4. ae-cli Command Unavailable
```
Output: "❌ Data service temporarily unavailable, please try again later"
```

---

## Data Privacy & Security

### Sensitive Data Processing

The following sensitive fields will be automatically masked:

| Field Type | Masking Method | Example |
|------------|----------------|---------|
| Phone | Hide middle 4 digits | 138****8888 |
| Device ID | Show first 8 chars | abc12345... |
| IP Address | Hide last 2 segments | 192.168.x.x |
| Email | Hide username | ***@qq.com |
| Real Name | Show surname only | Zhang** |

### Usage Guidelines

⚠️ **When using this skill, please follow these guidelines:**

1. **Access Control**: Only query user data you have permission to access
2. **Purpose**: Queries must have legitimate business purposes (customer service, operations, analysis)
3. **Data Confidentiality**: Do not leak query results to unrelated third parties
4. **Audit Logging**: All query operations are recorded in audit logs

---

## Configuration

| Config Item | Description | Default |
|-------------|-------------|---------|
| `churn_config.inactive_days` | Days inactive to be considered churned | 7 |
| `payment_tiers` | Payment tier boundaries (in cents) | free: 0, minnow: 1, dolphin: 10000, whale: 100000, super_whale: 1000000, ultra_whale: 10000000 |
| `limits.max_users_per_batch` | Max users for batch query | 10 |
| `limits.max_events_per_query` | Max events per query | 500 |

---

## Reference Documents

- ae-analysis skill commands (see ae-analysis product skill references)
