# churn-define | Gotchas (Common Pitfalls)

## Common Pitfalls & Solutions


### 1. Confusion between Last Active User Properties vs Activity Events

**Pitfall:** When searching assets, it's easy to confuse:
- **User property** representing "user's last active time" (asset type is "User Property", from user table, raw reported asset, one value per user)
- **Event** representing "user activity" (asset type is "Event", from event table, raw reported asset, multiple records per user)
- virtual-user-property (divided into virtual user properties and virtual event properties, not raw reported data assets, created by system users with permissions, any account with permissions can create them)

**Correct Approach:**
- Step 2 only searches two types: **user property** representing "user's last active time" + **event** representing "user activity"
- virtual-user-property is created in Step 3, not displayed or mentioned in Step 2
- If virtual-user-property are mixed into search results, they must be silently discarded, not mentioned

**Failure Cases:**
❌ Search found "days since last active" (virtual-user-property), directly showed it to user, causing confusion "why create virtual-user-property", and since any account with permissions can create virtual-user-property, using someone else's virtual-user-property requires extra confirmation of its creation logic and definition, easily deviating from the main flow. So unless user actively mentions it, never mention it to user.

---

### 2. Exception Handling: Failed to Create AE Assets

**Pitfall:** After failing to create virtual-user-property, firstlast-tag, or Property Analysis Model reports, starts trying other methods on its own
- After Step 3 fails to create virtual-user-property "days since last active", starts trying to call other tools or use other tool parameters to create churn user segments or tags
- After Step 3-2 fails to create firstlast-tag to get user's last active time, starts trying to call other tools or use other tool parameters to create churn user segments or tags
- "Churned user churn day distribution" report and other segmentation dimension reports must be [Property Analysis Model] reports, cannot use Event Analysis Model reports or Distribution Analysis Model reports, once report creation fails, cannot try creating other types of reports

**Correct Approach:**
- After creation failure, directly state the facts to user, provide detailed creation steps, recommend user manually try creating, continue to next step after user completes creation

**Failure Cases:**
❌ "Segmentation report creation failed, let me try using Event Analysis Model to analyze churn days"
❌ "virtual-user-property 'days since last active' had a problem, let me use condition tag to identify churned users"


---

### 3. Loose Process Discipline

**Pitfall:** Exposing later step content in advance:
- Step 1 says "I'll create virtual-user-property later"
- Step 2 searching churn definition related data assets mixes in payment, level and other assets unrelated to churn identification
- Step 3 starts discussing segmentation dimensions before confirming churn user identification condition

**Correct Approach:**
- Strictly follow steps in order, don't execute early
- Don't expose internal execution steps (don't say "I'm now executing Step X")
- Each step only outputs that step's content, don't preview next step

**Failure Cases:**
❌ Step 2 outputs: "Found last login property, next I'll create virtual-user-property, then recommend segmentation dimensions..."
❌ User just said "identify churn users", immediately replied "recommend payment value, level, lifecycle segmentation", user is confused


---

### 4. Parameter Auto-fill Trap

**Pitfall:** User has not explicitly confirmed parameters, but model fills them in on its own:
- Project name or Project ID not confirmed with user
- Analysis period uses default value instead of user's actual needs

**Correct Approach:**
- Before creating any asset, must use "Pre-operation Confirmation Template" to list all parameters
- Wait for explicit user confirmation before executing
- Do NOT fill in parameters not explicitly confirmed in context
- If user didn't explicitly say, use default value and mark "default" in confirmation table

**Failure Cases:**
❌ User said "create virtual-user-property", model directly created "days since last active", result was user wanted name "churn days"

---

### 5. Over-judgment of Missing Data

**Pitfall:** Search keyword has no exact match, directly determines "data missing" and ends process:
- Search "last_login_time" not found, says "no last login property"
- Actually user's property is called "last_active_time" or "latest_login"

**Correct Approach:**
- Try several synonyms: `last_active`, `last_login_time`, `last_active_time`, `last_login`, `latest_login`
- When nothing found, proactively confirm with user: "I didn't find last login related property, does your project have one?"
- Cannot determine missing just because keyword doesn't match

**Failure Cases:**
❌ Search "login" not found, directly says "no login event", result was user's event is called "user_login" or "app_start"

---

### 6. Industry Adaptation Deviation

**Pitfall:** Recommended segmentation dimensions don't match product industry characteristics:
- Game type recommends "content contribution" (should recommend "level" "payment value")
- Social type recommends "virtual currency" (should recommend "follower count" "activity level")

**Correct Approach:**
- Must confirm product type and stage in Step 1
- Dynamically recommend segmentation dimensions based on product type
- Segmentation recommendations should include business reasoning (why this dimension is useful for you)

**Failure Cases:**
❌ User said "We're an SLG game", model recommends "content contribution" segmentation

---

### 7. Path Branching Fallback: Assets Don't Fit Preset Paths

**Pitfall:** The three paths in Step 3-1 are preset, actual asset situation may not fully fit any path:
- Has "last active time" property, but data quality is poor (all NULL or default values)
- Has login event, but missing necessary properties like `#event_time`
- User property time and event time definitions are inconsistent

**Correct Approach:**
When assets confirmed by user don't fully fit Path 1/2 conditions, Skill should:
1. Explain current situation: "I see you have [asset X], but its situation is special [explain]"
2. Give options for user to judge:
   - Option A: Try using it, see if it can work
   - Option B: Change to another asset (back to Step 2 to reselect)
   - Option C: First solve data quality issues (end this session)
3. Continue only after user chooses, model does not decide whether to "make it work"

**Failure Cases:**
❌ Asset data quality is poor but model directly uses it, causing incorrect calculation results for subsequently created virtual-user-property
❌ Definitions are inconsistent but model ignores differences and continues execution, causing inaccurate churn identification condition

---

## Test Checklist

Run this checklist when executing skill to check for pitfalls:

- [ ] Did you confirm churn definition with a question?
- [ ] Did Step 2 only show last active properties and activity events, no virtual-user-property mixed in?
- [ ] Did you recommend segmentation dimensions in Step 1? (Should not)
- [ ] Did you list all parameters with confirmation table before creating assets?
- [ ] Did you try several synonyms before determining data missing?
- [ ] Did you expose later step content in advance?
- [ ] Is exception handling consistent?
- [ ] Do segmentation dimension recommendations match product industry characteristics?
