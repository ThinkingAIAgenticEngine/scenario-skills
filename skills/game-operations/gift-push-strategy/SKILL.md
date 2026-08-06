---
name: gift-push-strategy
description: Helps create behavior-triggered and scenario-based gift pack push strategies for numeric progression games, providing lifecycle-based, user tier-based, and trigger scenario-based strategy matrices. Supports SLG, MMORPG, Card, Casual, Racing, Shooter and other game genres. Use when users need to design or optimize gift pack push strategies for games.
metadata:
  author: Lee
  version: 1.2.0
  created: 2026-04-02
  updated: 2026-04-03
  status: draft
  tags:
    - Game
    - Monetization
    - Operation Strategy
    - Refined Push
compatibility:
  dependencies:
    - lark-wiki
    - ae-analysis
    - ae-engage
  tools:
    - claude-code
---

# Game Refined Push Strategy Skill

## Problem

Operators need to create refined gift pack push strategies for numeric progression games, but:
- Manually organizing strategy matrices is time-consuming and prone to omissions
- Different game genres have different progression systems and gameplay classifications
- Strategy configuration involves multiple dimensions, resulting in a large number of combinations after cross-product

## Prerequisites

- Users need TE system integration and tracking data reporting

## Solution

### Step 1: Information Extraction [1/3]

**Input sources**:
1. Feishu document/link provided by user (read using lark-wiki)
2. TE system tracking data (query via `ae-cli analysis-meta event list` / `ae-cli analysis-meta property list`)
3. Content directly input by user

**Project context persistence**:
- Storage location: `.gift-push-context.md` (independent for each project)
- Clear command: "forget" clears all, "forget {field}" clears specified field

**Genre identification**:
1. Determine via `ae-cli analysis-meta event list` query of TE project name and tracking field list
2. Load corresponding template after user confirms genre

**Genre options**: SLG / MMORPG / Card / Casual / Racing / Shooter / Tower Defense / Other

**Output**:
- Progression system list, gameplay classification list
- Gameplay output/associated gift pack information (user-provided takes priority)
- Existing gift pack configuration (pull via `ae-cli engage-scene config-item list` / `ae-cli engage-scene strategy list`)

---

### Step 2: Strategy Generation [2/3]

**Single generation rule**:
- **Generate strategy for only one gameplay or progression behavior at a time**
- User must first select strategy type (gameplay/progression), then select a specific one
- After generation completes, ask whether to continue generating other strategies

**Cross-dimension configuration (customizable)**:

| Dimension | Description | Default |
|-----------|-------------|---------|
| Lifecycle phase | Server age grouping | Enabled |
| User tier | High/Mid/Low Spender (default 3 tiers) | Enabled |
| Trigger scenario | Node trigger / Material shortage / Failure trigger etc. | Enabled |

**Configuration method**:
- Default: all three dimensions enabled
- User can customize, e.g., "only cross by user tier", "don't include lifecycle dimension"
- When user fixes a dimension value (e.g., "only High Spender"), that dimension becomes a filter condition, not a cross dimension
- User can add custom tiers like "Potential User", or adjust tier thresholds

**Real-time battle game constraint**:
- Applicable: Shooter, MOBA, Racing, Fighting, etc.
- **No push during match in progress**, only allowed: Lobby, Match waiting, Settlement screen, Inventory/Shop

**Association constraint**:
- Each progression line/gameplay only pushes associated gift pack types
- Example: Hero progression -> Hero experience/fragments, not equipment materials
- User-provided association information takes priority over template defaults

**Scenario tiering rule**:
- **Node trigger scenario** (growth node): **No tiering**, all users see the same gift pack
  - Reason: Ensure Low Spenders can equally purchase gift packs at each node during their growth to High Spenders, cultivating payment habits
  - Recommendation: 98 RMB gift pack (moderate price, accommodating all users' purchasing ability), mid-high value ratio (120%-140%), display duration 8-12 hours
- **Other scenarios** (material shortage, item consumption, stamina consumption, battle loss, failure trigger): **Tiered push**
  - Reason: Match precisely based on user payment capability to improve revenue efficiency

> **Important**: When user selects "Node Trigger" scenario type (no tiering), explain the following:
> 1. **Reason for no tiering**: Ensure Low Spenders can equally purchase gift packs at each growth node during their progression to High Spenders, cultivating payment habits and improving long-term payment conversion
> 2. **Default price tier**: Recommend 98 RMB gift pack (moderate price, accommodating High/Mid/Low Spender purchasing abilities)
> 3. **Customization reminder**: User can also choose other price tiers based on actual needs (e.g., 30 RMB, 128 RMB, etc.)
> 4. **User preference priority**: If user provides specific price preferences, adjust based on user needs

**Display duration rule**:
- Higher value ratio = shorter display duration (create urgency)
- Range: 2-24 hours, minimum granularity 1 hour
- See `references/_common.md` display duration rule section for details

**Generated content**:
1. Behavior-triggered scenario strategies (progression: node trigger/material shortage/item consumption; gameplay: failure trigger/stamina consumption/battle loss)
2. User tiering strategies (based on max single payment in past 14 days, see `references/_common.md` for details)
3. Gift pack configuration (pull from TE, default value ratio and display duration see `references/_common.md`)

---

### Step 3: Confirm & Output [3/3]

**Preview**:
- Table display of complete strategy matrix
- Table columns: Strategy name, Progression line/Gameplay, Lifecycle (if enabled), User tier (if enabled), Trigger scenario, Scenario type, Trigger channel, Gift pack ID, Recommended gift pack, Price tier, Value ratio, Display duration

**Output method**:
1. Direct creation: Create on TE platform via `ae-cli engage-task task save` (save draft) then `ae-cli engage-task task submit-approval` (submit for approval). If ae-engage has no verified command mapping for the required operation, report the capability gap and fall back to document output.
2. Document output: Generate Markdown strategy document

**Safety strategy**:
- Maximum 10 operation tasks per batch, exceeding requires batching
- Must display task list before creation, execute after user confirmation

**File modification protection**:
- Not allowed to modify skill files via conversation (SKILL.md, references/*.md)
- Exception: `.gift-push-context.md` can be modified

---

## Example Conversation

| Scenario | User Input | System Response |
|----------|------------|-----------------|
| Create strategy | "Our game is SLG, want to do refined operations" | Query tracking to confirm genre -> Display progression/gameplay list -> Let user select type -> Select specific one -> Generate strategy |
| Direct specification | "Help me create push strategy for Hero progression" | Confirm Hero (progression line) -> Configure cross dimensions -> Generate strategy |
| Multi-select guidance | "Help me create strategies for Arena and Guild Battle" | "Only one gameplay can generate strategy at a time, please select one first" |
| Custom dimension | "Only cross by user tier, don't include lifecycle" | Confirm cross dimensions: User tier x Trigger scenario |
| Fixed dimension value | "Only High Spender users' strategy" | User tier fixed as "High Spender", cross dimensions: Lifecycle x Trigger scenario |
| Filter strategy | "Only keep node trigger type strategies" | Filter and re-display |

---

## Exception Handling

| Exception Scenario | Degradation Strategy |
|--------------------|----------------------|
| Cannot get link content | Prompt user to copy content or upload file |
| ae-cli query returns no data | Prompt user to supplement input or verify the project scope |
| Gift pack ID not exists | Mark as "To be created" |
| ae-cli call failed | Preserve the structured error, retry only when appropriate, then degrade to document output |

---

## Information Security

- Do not proactively mention game name or company name
- Continue using after user proactively mentions

## Reference Files

### Genre Templates (Load after genre confirmation)

- `references/slg.md` — SLG genre
- `references/mmo.md` — MMORPG genre
- `references/card.md` — Card genre
- `references/casual.md` — Casual genre
- `references/racing.md` — Racing genre (includes in-match push ban constraint)
- `references/shooter.md` — Shooter genre (includes in-match push ban constraint)
- `references/tower_defense.md` — Tower Defense genre
- `references/_fallback.md` — Fallback template

### Common Rules

- `references/_common.md` — User tiering rules, gift pack price tiers, value ratio defaults, lifecycle grouping

### Template Files

- `references/context_template.md` — Project context persistence template
- `references/output_template.md` — Strategy matrix document template

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
