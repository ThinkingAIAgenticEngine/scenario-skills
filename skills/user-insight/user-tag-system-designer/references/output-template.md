# Output Format Template

> Format reference for full process output content.

---

## First Reply Template (Step 2)

```markdown
📊 **Project metadata analysis completed**:

- 🔍 **Total events**: X items
- 📝 **Total properties**: X items
- 🏢 **Identified industry**: [Industry name] (match rate XX%)
- 🏷️ **Sub-category inferred**: [Category name]
- 💡 **Judgment basis**: Discovered feature data such as `[Event A]`, `[Property B]`.

**The entire tag system consists of 6 layers**:

| Layer | Tag type | Core value |
|-----|---------|---------|
| 1️⃣ User profile & identity | Static profile | User basic characteristics |
| 2️⃣ Active behavior | General | User stickiness |
| 3️⃣ Usage depth | General+Industry | Core function participation |
| 4️⃣ Payment & commercial value | General | User commercial value |
| 5️⃣ **[Industry sub-category] Exclusive** ⭐ | Differentiation core | Customized for you |
| 6️⃣ Lifecycle & comprehensive | Comprehensive | User status management |

👉 **[Next step]**:

If the above industry identification is accurate, how would you like to view the tag solution?
- **A.** Layer-by-layer view (Recommended, start from Layer 1, or specify layer)
- **B.** Directly view core: Layer 5 [Industry] exclusive tags
- **C.** View complete solution (Output all layers at once)

*(If industry identification deviation, please directly tell me the true industry/category)*
```

---

## Single Tag Definition Output Format (Step 3)

> ⚠️ Must strictly follow line formatting, tables must have blank lines before and after.

```markdown
### 3.X [Layer name] Tags

#### 🏷️ 【Tag Chinese name】

* **Business definition**: [Describes what user characteristic, applicable to what analysis or operation scenario]
* **Recommended TE tag type**: `[Condition Tag / Metric Value Tag / First-Last Tag / SQL Tag / ID Tag]`

**⚙️ Calculation logic**:

* **Analysis subject**: `#user_id`
* **Data source**: `[Event name]` or `[User property]`
* **Time range**: `[Last 7 days / Last 30 days / All time etc.]`
* **Filter condition**: `[None / Event property condition]`
* **Specific rule**: `[Sum / Count distinct / Judge whether / Take maximum etc.]`

**📊 Recommended tag value tiering**:

| Tag value | Definition condition | Business meaning |
| :--- | :--- | :--- |
| [Value 1] | [Condition] | [Represents what user] |
| [Value 2] | [Condition] | [Represents what user] |

---

#### 🏷️ 【Next tag name】

... (Repeat above format)

---

### 🚀 Business application scenarios for this layer tags

- **Scenario one [Scenario name]**: [Explain how to use these tags for filtering, tiering or audience targeting]
- **Scenario two [Scenario name]**: [Explain how to combine reports for analysis insight]

### ⚠️ Missing fields and supplement suggestions

- [List key missing events/properties discovered during design, provide tracking supplement suggestions]
- If no missing: Current tracking supports well, no missing supplement suggestions for now.
```

---

## Complete Solution Document Structure (When user selects view all)

```markdown
# [Industry/Category] User Tag System Design Solution

## 1. Project Overview

| Dimension | Content |
|-----|------|
| Project ID | [ID] |
| Industry identification | [Industry name] |
| Sub-category | [Category name] |
| Match basis | [Feature events/properties] |
| Total events | X items |
| Total properties | X items |

## 2. Tag System Architecture Overview

| Layer | Tag count | Type | Core value |
|------|--------|------|---------|
| Basic attributes | X | Static profile | User basic characteristics |
| Active behavior | X | General | User stickiness |
| Usage depth | X | General+Industry | Core function usage |
| Payment & commercial value | X | General | User commercial value |
| [Industry] exclusive | X | Industry differentiation | Industry core insight |
| Lifecycle & comprehensive | X | Comprehensive | User status management |

## 3. Tag Detail Definitions

### 3.1 Basic Attribute Tags
[Output by single tag format]

### 3.2 Active Behavior Tags
[Output by single tag format]

### 3.3 Usage Depth Tags
[Output by single tag format]

### 3.4 Payment & Commercial Value Tags
[Output by single tag format]

### 3.5 [Industry sub-category] Exclusive Tags  ← Key output
[Output by single tag format, richest content]

### 3.6 Lifecycle & Comprehensive Tags
[Output by single tag format]

## 4. Priority Implementation Suggestions

**P0 Immediate implementation**:
- Basic active tags (last 7 days/last 30 days active days, active tiering)
- Payment tiering tags
- [Industry core tags TOP3]

**P1 Second batch implementation**:
- Usage depth tags
- Payment behavior refined tags
- [Industry exclusive tags TOP5]

**P2 Follow-up completion**:
- SQL tags (complex logic)
- Lifecycle comprehensive tags
- Promotion/preference tags

## 5. Business Application Scenarios

### User operation scenarios
| Scenario | Tag combination | Operation action |
|-----|---------|---------|
| Precision targeting | [Combination] | [Action] |
| Churn recall | [Combination] | [Recall strategy] |
| Campaign targeting | [Combination] | [Campaign plan] |

### Data analysis scenarios
- User cohort comparison
- Retention analysis
- Conversion funnel analysis

### Product optimization scenarios
- Feature iteration direction identification
- Core user need mining

## 6. Missing Fields and Supplement Suggestions

| Missing field | Tracking suggestion | Alternative solution |
|---------|---------|---------|
| [Field name] | [Event/property suggestion] | [Existing field alternative] |
```

---

## Guidance Closing Template (Step 4)

> Must be included at each reply end, select based on current state.

### After single layer view

```markdown
👉 **[Next step guidance]**:
Above is Layer [X] tag design. Next would you like:
- View **Layer [X+1]**
- Directly **Summarize complete solution document**
```

### After exclusive layer (Layer 5) view

```markdown
👉 **[Next step guidance]**:
This is the customized industry exclusive tag for you. Do you think:
- Matches business intuition, continue to view **Layer 6 (Lifecycle tags)**
- Needs adjustment, please tell me adjustment direction
```

### After complete solution view

```markdown
👉 **[Next step guidance]**:
Above is the complete tag system solution. Do you need:
- Extract core tag **SQL calculation pseudocode**
- This design session ends here
```

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.