---
name: journey-intent-parser
description: Parses natural language descriptions of ThinkingData journey canvas into structured intent JSON for downstream node orchestration. Triggered when users mention "generate journey", "create journey", "build a campaign", "new user onboarding", "churn recall", "time-based split", "scheduled push", etc. Output serves as input for `references/journey-node-builder`.
---

# Journey Intent Parser

Converts user natural language into structured intent JSON for journey canvas, consumed by `references/journey-node-builder`.
Output is a **directed graph structure**: `nodes[]` declares nodes, `edges[]` explicitly expresses connections.
Does not involve any backend fields, channelId, or channel configuration.

---

## Interaction Flow (must follow steps in order)

### Conversational Tone Guidelines

Every round of dialogue with the user should embody these principles:

- **Acknowledge first, then ask**: After receiving user input, acknowledge or affirm with one sentence before asking the next question. Don't just throw questions like filling out a form.
  - Example: "Got it, you want to recall recently churned users—that's a clear goal. Now, which channel do you plan to use to reach them?"
- **Show business understanding**: When asking follow-ups, demonstrate understanding of the user's business scenario so they feel you're helping them design, not just collecting information.
  - Example: "For churn recall, timing is critical—just want to confirm, are you planning to use Push or WeChat Subscription to reach users?"
- **Natural tone, no lists**: Use conversational language, not numbered lists or "please provide item X" style questions.
- **Positive closure**: After each confirmation, use brief phrases like "Got it, noted" or "Perfect" to give positive feedback before moving to the next step.

---

### Step 1: Collect Required Information

Before generating any JSON or preview, you must confirm the following 4 required pieces of information through conversation. **Do not generate JSON if any item is missing; do not assume or fill in values yourself.**

| #   | Required Info         | Description                         | Criteria for "Provided"                                                                          |
| --- | --------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1   | **Business Scenario** | Core objective type of this journey | User clearly described the scenario (churn recall / new user activation / paid conversion, etc.) |
| 2   | **Target Audience**   | Which users can enter this journey  | User specified entry conditions (e.g., "not logged in for 14 days" / "registered today")         |
| 3   | **Channel**           | Channel for pushing to users        | User clearly stated the push channel (Push / WeChat Subscription / SMS / Webhook, etc.)          |
| 4   | **Split Conditions**  | Whether users need to be grouped    | User explicitly stated "need grouping + grouping dimension" or "no grouping needed"              |

#### Follow-up Rules

1. Check current context to identify all **missing required information**
2. If missing: first briefly acknowledge what the user has provided in natural language, then **guide progressively, asking one piece of information at a time** (no JSON output, no preview)
3. After receiving user's answer, acknowledge it first, then recheck—if still missing items, continue asking for remaining ones
4. After all 4 items are confirmed, provide a brief summary (e.g., "Great, we have all the info. Let me outline this journey for you"), then **always proceed to Step 2** to show journey summary + text diagram

#### Example Follow-up Tone

- Upon first receiving user description: "Sounds like you want to build a [scenario] campaign—clear objective! Let me help you set it up. Just want to confirm one thing first..."
- Mid-conversation follow-up: "Understood, [restate what user just said]. Now regarding [next missing info], have you decided..."
- Final confirmation: "Perfect, one last quick question—[ask], and once confirmed I can generate the complete journey preview for you."

#### Prohibited Actions

- ❌ Do not auto-infer channel based on scenario type (e.g., "churn recall so use Push")
- ❌ Do not design split logic or add split tiers when user hasn't specified
- ❌ Do not output JSON or journey preview when required info is incomplete
- ❌ Do not ask for non-essential info like start/end dates or push copy (before required info is complete)
- ❌ Do not throw multiple questions at once in a numbered list

---

### Step 2: Show Journey Preview

**Output Format:**

```
📋 Journey Summary
- Business Scenario: xxx
- Target Audience: xxx
- Channel: xxx
- Split Conditions: Yes (split by xxx) / No

🗺️ Mermaid Flowchart
[Insert Mermaid diagram here]
```

After the preview, ask for confirmation in a warm, inviting tone, such as:

- "Does this journey look good to you? Feel free to let me know if you'd like to adjust anything~"
- "How does this design look? If you want to change the node sequence or split logic, just tell me and we'll adjust."

Do not use stiff, formulaic expressions like "Does the above journey meet your expectations?"

---

### Step 3: Generate Intent Recognition JSON

After information is confirmed, generate the intent JSON internally and pass it directly to `references/journey-node-builder` for consumption. **Do not show JSON content to the user**. Generation rules:

- All enum values are in the quick reference table below; do not invent your own
- Assign `nid` / `bid` sequentially (n1/n2/n3…, b1/b2/b3…), globally unique
- All action nodes' `channel_name` must be filled (from Step 1 confirmed channel, cannot be null)

---

## Output Schema

```json
{
  "flow_type": "<string>",
  "flow_name": "<string>",

  "entry": {
    "type": "<event_trigger|repeat_trigger>",
    "trigger_event": "<string|null>",
    "schedule": "<string|null>",
    "segment": "<string>",
    "start_date": "<YYYY-MM-DD|null>",
    "end_date": "<YYYY-MM-DD|null>"
  },

  "nodes": [
    /* see node structure */
  ],
  "edges": [
    /* see edges rules */
  ]
}
```

> **`trigger_event` field processing rules**:
> User's natural language input needs to be processed into conditional expressions, format varies by condition type:
>
> **Count condition**: "Complete [X] event" → `"Number of times [X] event completed is greater than or equal to [N]"`
>
> - Example: User says "complete registration event" → `"Number of times registration event completed is greater than or equal to 1"`
> - Example: User says "complete payment twice" → `"Number of times payment event completed is greater than or equal to 2"`
> - Default operator is "greater than or equal to", default count is "1"
>
> **Cumulative attribute condition**: "[X]'s [attribute] greater than [Y]" → `"Sum of [attribute] for [X] is greater than [Y]"`
>
> - Example: User says "payment amount greater than 100" → `"Sum of payment amount is greater than 100"`

---

## nodes — Node Structure

Each node must have a unique `nid` (n1, n2, n3…), **does not contain branch_of field** (all connections are expressed in edges).

### Split Node

```json
{
  "nid": "n2",
  "node_type": "split",
  "type": "<event_split_flow|feature_split_flow|ab_split_flow>",
  "name": "<string|null>",
  "dimension": "<string|null>",
  "split_flow_type": "<1|2>",
  "branches": [
    {
      "bid": "b1",
      "label": "<string>",
      "condition": "<string|null>",
      "time_limit": "<string|null>",
      "percentage": "<number|null>"
    }
  ]
}
```

> **branch `condition` field**:
>
> `event_split_flow` branches: Natural language description of wait condition and result, e.g., `"Complete payment within 15 minutes"`, `"Not logged in within 1 hour"`
>
> `feature_split_flow` branches: Natural language description of attribute conditions, e.g., `"VIP level is gold or above"`, `"Cumulative payment amount greater than 500"`, `"Has purchase behavior in past 7 days"`
>
> `ab_split_flow` branches have no condition, only use `percentage`.
> Fallback branch `condition` is filled with `null`.

> **`split_flow_type`** (only used by `event_split_flow` / `feature_split_flow`, `ab_split_flow` doesn't need this field):
>
> - `1` (default) — Enter by priority: user only enters the first branch that meets the condition
> - `2` — Enter when condition is met: when user meets multiple branch conditions, enters multiple branches simultaneously
>
> Set to `2` when user says "enter when condition is met", "enter multiple branches simultaneously", "not mutually exclusive"; default to `1` when not mentioned.

### Judge Node (fixed to produce meet / not_meet two paths)

```json
{
  "nid": "n3",
  "node_type": "judge",
  "type": "<event_judge|feature_judge>",
  "name": "<string|null>",
  "event": "<string|null>",
  "condition": "<string|null>",
  "wait_time": "<string|null>",
  "branches": [
    { "bid": "meet", "label": "Met" },
    { "bid": "not_meet", "label": "Not Met" }
  ]
}
```

> - `event_judge` uses `event` field, fill with natural language description of wait condition and detection behavior, e.g., `"Wait 30 minutes then check if payment completed"`, `"Wait 1 hour to see if logged in"`
> - `feature_judge` uses `condition` field, fill with natural language description of user attribute conditions, e.g., `"Is VIP user"`, `"Cumulative payment amount greater than 1000"`
> - Judge node's `branches` are fixed as the above two items, always like this, no need to extract from user description.

### Action Node

```json
{
  "nid": "n4",
  "node_type": "action",
  "type": "<webhook_push|message_push|wechat_push>",
  "name": "<string|null>",
  "content": "<string|null>",
  "channel_name": "<string>",
  "languages": ["<pushLanguageCode>"]
}
```

> **`languages` multilingual field**:
>
> - Default (not filled or `["default"]`): Generate copy in default language only
> - When user specifies multiple languages (e.g., "translate to German, Portuguese, Japanese"), fill in corresponding language codes: `["default", "de", "pt", "ja"]`
> - `"default"` is always included as the first item in the list, representing the default language
> - Common language codes: `zh`(Chinese) / `en`(English) / `ja`(Japanese) / `ko`(Korean) / `de`(German) / `fr`(French) / `pt`(Portuguese) / `es`(Spanish) / `ru`(Russian) / `ar`(Arabic)
> - Omit this field or fill `null` when user doesn't mention multilingual requirements

### Wait Node

```json
{
  "nid": "n5",
  "node_type": "wait",
  "type": "time_control",
  "name": "<string|null>",
  "duration": "<string|null>"
}
```

### End Node (automatically appended at the end of each path)

```json
{
  "nid": "n6",
  "node_type": "end",
  "type": "exit_flow"
}
```

---

## edges — Connection Rules

```json
{ "from": "<nid|'entry'>", "to": "<nid>", "via": "<bid|null>" }
```

- `from`: Source node nid, fixed as `"entry"` for entry node
- `to`: Target node nid
- `via`: Fill `null` for normal connections; fill corresponding `bid` for split/judge node exits

### Outbound Edge Rules for Each Node Type

| Node Type             | Outbound Edges | via Value                                          |
| --------------------- | -------------- | -------------------------------------------------- |
| entry / action / wait | 1              | `null`                                             |
| split (N branches)    | N              | Fill corresponding `bid` for each edge (b1/b2/b3…) |
| judge                 | 2              | `"meet"` and `"not_meet"`                          |
| end                   | 0              | —                                                  |

### ⚠️ Key Constraints

1. **Every path must end with an end node**, end nodes have no outbound edges
2. **Every branch exit of split/judge must have a corresponding edge**, no dangling branches allowed
3. **The `via` in edge must be a bid that exists in that node's branches**, cannot reference bids from other nodes

---

## Enum Values Quick Reference

**flow_type**
`NEW_USER_ACTIVATE` / `CHURN_RECALL` / `PAID_CONVERT` / `ACTIVE_BOOST` / `PUSH_NOTIFY` / `HOLIDAY_CAMPAIGN` / `CUSTOM`

**entry.type**
`event_trigger` (default) / `repeat_trigger` (includes "daily/scheduled/periodic/weekly/planned/recurring") / `single_trigger` (includes "execute once/single/one-time scheduled")

**entry.schedule format** (required for `repeat_trigger`, format examples)

- Daily: `"Daily at 09:00"`, `"Daily at 20:00"`
- Weekly: `"Every Tuesday, Wednesday, Friday at 09:00"`
- Monthly: `"Monthly on 4th, 11th, 31st at 09:00"`

**entry.segment semantics**

- `repeat_trigger`: Always has target audience, `segment` describes filtering conditions (e.g., "users who haven't logged in for 14 days")
- `single_trigger`: Always has target audience, `segment` describes filtering conditions, executes only once
- `event_trigger`:
  - `segment: null` → Enter as long as behavior condition is met (no audience filtering, targetUserType: 3)
  - `segment: "<description>"` → Both behavior condition + audience filtering (targetUserType: 1)

**split vs judge selection rules**

> Core distinction: **Number of branches** determines whether to use split or judge.
>
> - Only "yes/no" two paths → **judge**
> - ≥3 paths (including fallback) → **split**

**judge type** (fixed 2 paths: meet / not meet)

- `event_judge` — Wait for a period, judge whether a behavior occurred ("whether payment completed within 15 minutes", "wait 1 hour to see if logged in")
- `feature_judge` — Judge whether user attributes meet conditions ("is paying user", "belongs to certain group"), no waiting

**split type** (≥3 paths, including fallback branch)

- `event_split_flow` — Split by behavior/time **gradient**, different time windows go to different paths ("15min unpaid→reminder, 1hr unpaid→coupon, 24hr unpaid→abandon")
- `feature_split_flow` — Split by user attributes to multiple branches ("split by level: bronze/silver/gold each go different paths")
- `ab_split_flow` — A/B experiment split (includes "AB test/experiment/control group/percentage")

**action type**

- `webhook_push` — Custom channel, Webhook, gift pack, popup, email, SMS
- `message_push` — Message push, Push, FCM, Apns, JPush
- `wechat_push` — WeChat subscription message

**split_dimension**
Used to quickly identify split dimension type, allows custom description. Common values reference:
`PAY_TIME_GRADIENT` / `LOGIN_TIME_GRADIENT` / `PAY_STATUS` / `APP_PACKAGE` / `USER_LEVEL` / `DEVICE_TYPE` / `CUSTOM_CLUSTER` or any custom description

---

## ⚠️ Key Distinction: time_control vs event_judge

- "Wait 30 minutes then send" → `time_control` (pure delay, single output, no branches)
- "Wait 30 minutes to see if payment occurred" → `event_judge` (delay + detection, outputs meet / not_meet two paths)

---

## nid / bid Allocation Method

Generation order: From entry downward, traverse the flow in **depth-first, left-to-right** order, sequentially allocate n1, n2, n3…

Judge nodes' bid are fixed as `meet` / `not_meet`, do not participate in b sequence allocation.
Split nodes' bid are allocated in branch order as b1, b2, b3…, **each split node independently starts counting from b1**, not accumulated across nodes.

Example: Two split nodes, each with branches starting from b1:

```
split n2: b1="15m", b2="30m", b3="fallback"
split n5: b1="experiment group A", b2="experiment group B"   ← Each independent, not b4/b5
```

---

## Reference Examples

See `references/` directory, load as needed:

| File                              | Load Condition                                             |
| --------------------------------- | ---------------------------------------------------------- |
| `references/new_user_activate.md` | User mentions "new user", "onboarding", "newly registered" |
| `references/churn_recall.md`      | User mentions "churn", "recall", "reactivation"            |
