---
name: journey-node-builder
description: Receives intent JSON output from journey-intent-parser, calls query_cluster_qp_skill to generate behavior event conditions/segment qp, calls query_channel_list to query push channel list and intelligently matches the most suitable channel ID, generates complete request body (nodeList + edgeList) for ThinkingData journey canvas, and finally creates the journey canvas via save_flow. Triggered when user completes intent parsing and needs to generate canvas node structure.
---

# Journey Node Builder

Converts intent JSON into ThinkingData journey canvas frontend request body, outputs complete `nodeList` + `edgeList`, and completes canvas creation via `save_flow`.

Execution flow overview:

1. Confirm projectId and read intent JSON
2. Call **`query_cluster_qp_skill`** tool to get cluster qp skill, assemble qp based on user intent and skill
3. Call **`query_channel_list`** tool to get all push channels under the project, intelligently match the most suitable channel ID based on `channel_name` in intent JSON
4. Generate IDs → Apply templates → Build edgeList → Self-check
5. Call **`save_flow`** to create journey canvas

---

## Top-level Output Structure

```json
{
  "flowName": "<flow_name>",
  "flowDesc": "<description or empty string>",
  "groupId": 0,
  "tzOffset": "<get from system server timezone, e.g., UTC+8 fill 8>",
  "nodeList": [],
  "edgeList": [],
  "completionIndicators": [],
  "versionType": 1,
  "projectId": "$projectId"
}
```

> This structure is submitted directly to `save_flow` in step 8, not output to user.
> Only output complete JSON for debugging when creation fails.
>
> ⚠️ **Required Fields Checklist (confirm each item when building request body; missing any will cause `save_flow` to fail):**
>
> | Field                  | Required | Default                                                                         |
> | ---------------------- | -------- | ------------------------------------------------------------------------------- |
> | `flowName`             | ✅       | From intent JSON `flow_name`                                                    |
> | `groupId`              | ✅       | `0`                                                                             |
> | `tzOffset`             | ✅       | Get from system server timezone (UTC+8 fill `8`), use user value when specified |
> | `nodeList`             | ✅       | Generated in step 5                                                             |
> | `edgeList`             | ✅       | Generated in step 6                                                             |
> | `completionIndicators` | ✅       | `[]`                                                                            |
> | `versionType`          | ✅       | `1` (fixed value)                                                               |
> | `projectId`            | ✅       | From user specification, must ask if not specified                              |
>
> `$projectId` resolution rules (by priority):
>
> 1. Project ID explicitly specified by user in current conversation (e.g., "create in project 1", "projectId is 5")
> 2. If not mentioned in context, **must ask user**: "Which project do you want to create this journey in? Please tell me the project name or project ID."
> 3. After obtaining projectId, use the same value for subsequent `query_channel_list` and `save_flow`

---

## ID Generation Rules

All IDs (nodeId, branchId, edgeId, meetBranchId, notMeetBranchId) are **random numeric strings**, allowing `_`, globally unique and must not be reused.

```
Format: [0-9_]{8}
Valid examples: 0003_11310878101  0003_901127955  0003_107105105115  0003_1009712166
```

---

## Node Templates (nodeList)

---

### 1. repeat_trigger — Scheduled Recurring Entry

```json
{
  "id": "<nodeId>",
  "name": "<segment description>",
  "type": "repeat_trigger",
  "config": {
    "targetUserType": 1,
    "startDate": "<YYYY-MM-DD>",
    "endDate": "<YYYY-MM-DD>",
    "flowEndDate": "<YYYY-MM-DD HH:mm>",
    "crontab": "0 00 09 * * ?",
    "entryControlLimits": { "enableMultEntry": false, "disableConcurrentEntry": false },
    "targetClusterName": null,
    "clusterPredictCount": null,
    "clusterPredictTime": "<current time YYYY-MM-DD HH:mm:ss>",
    "targetClusterQp": "<JSON serialized string of qp object>"
  }
}
```

> **`crontab` parsing rules** (extract time and period from `entry.schedule`):
>
> | Type    | Input Example                | crontab Output              |
> | ------- | ---------------------------- | --------------------------- |
> | Daily   | `"daily 09:00"`              | `"0 00 09 * * ?"`           |
> | Weekly  | `"weekly Tue,Wed,Fri 09:00"` | `"0 00 09 ? * TUE,WED,FRI"` |
> | Monthly | `"monthly 4,11,31 09:00"`    | `"0 00 09 4,11,31 * ?"`     |
>
> **Day-of-week mapping**: Mon→MON, Tue→TUE, Wed→WED, Thu→THU, Fri→FRI, Sat→SAT, Sun→SUN
>
> ⚠️ **Day-of-week field must use English abbreviations (MON/TUE/WED/THU/FRI/SAT/SUN), numbers are prohibited.** Numbers in crontab are for day-of-month; using numbers for day-of-week will cause frontend to display undefined.
>
> Default to `"0 00 09 * * ?"` when unable to parse. `flowEndDate` is a few days later than `endDate`.

---

### 2. event_trigger — Event-triggered Entry

```json
{
  "id": "<nodeId>",
  "name": "<segment description, use trigger_event name when no audience>",
  "type": "event_trigger",
  "config": {
    "triggerType": 3,
    "targetUserType": "<segment=null→3, otherwise→1>",
    "realtime": "<segment=null→1, otherwise→0>",
    "clusterRefresh": "<segment=null→null, otherwise→12>",
    "clusterRefreshTime": null,
    "startDate": "<YYYY-MM-DD HH:mm>",
    "endDate": "<YYYY-MM-DD HH:mm>",
    "flowEndDate": "<endDate+N days HH:mm>",
    "clusterPredictCount": null,
    "clusterPredictTime": "<segment=null→'', otherwise→current time YYYY-MM-DD HH:mm:ss>",
    "triggerRule": [
      {
        "periodStart": "<startDate>",
        "periodEnd": "<endDate>",
        "periodTimeSymbol": "TS02",
        "dayStartTime": null,
        "startDay": null,
        "eventTriggerType": 0,
        "zoneoffset": 8,
        "events": [
          /* eventCondition field mapping, see step 2 */
        ]
      }
    ],
    "entryControlLimits": { "enableMultEntry": false, "disableConcurrentEntry": false },
    "targetClusterQp": "<segment=null→null, otherwise→JSON serialized string of qp object>"
  }
}
```

---

### 3. event_split_flow — Behavior Split

```json
{
  "id": "<nodeId>",
  "name": "<n>",
  "type": "event_split_flow",
  "config": {
    "splitFlowType": "<1=enter by priority|2=enter when condition met>",
    "branchList": [
      {
        "branchId": "<branchId>",
        "branchName": "<label>",
        "branchType": 1,
        "triggerRule": [
          {
            "delayTimeSymbol": "<minute|hour|day>",
            "delayTime": "<number>",
            "eventTriggerType": "<0=occurred|−1=not occurred>",
            "zoneoffset": 8,
            "events": [
              /* eventCondition field mapping, see step 2 */
            ]
          }
        ]
      }
    ]
  }
}
```

> **`splitFlowType` split mode**:
>
> - `1` (default) — **Enter by priority**: User enters only the first branch that meets condition, branches have priority order
> - `2` — **Enter when condition met**: When user meets multiple branch conditions, enters multiple branches simultaneously
>
> ⚠️ **`splitFlowType: 2` topology constraint**: Branches **must not merge to the same downstream node**, each branch must execute independently until its own `exit_flow` end node. When building edgeList, ensure downstream paths of different branches are completely independent and do not intersect.
>
> `time_limit` parsing: `"15m"→15,minute`; `"1h"→1,hour`; `"1d"→1,day`.
> Fallback branch: `branchType:2`, only needs `branchId` and `branchType` two fields, **does not contain** `triggerRule`, `branchName`, `realtime`, `clusterRefresh`, `targetClusterQp` and other attributes.
> "Not paid/not logged in" condition uses `eventTriggerType:-1`; "paid/logged in" uses `0`.

---

### 4. feature_split_flow — Attribute Split

```json
{
  "id": "<nodeId>",
  "name": "<n>",
  "type": "feature_split_flow",
  "config": {
    "splitFlowType": "<1=enter by priority|2=enter when condition met>",
    "branchList": [
      {
        "branchId": "<branchId>",
        "branchName": "<label>",
        "branchType": 1,
        "realtime": 0,
        "clusterRefresh": 12,
        "clusterPredictCount": null,
        "clusterPredictTime": "<current time YYYY-MM-DD HH:mm:ss>",
        "targetClusterQp": "<JSON serialized string of qp object>"
      }
    ]
  }
}
```

> `splitFlowType` rules and topology constraints same as `event_split_flow`.
> Fallback branch (`branchType: 2`) only needs `branchId` and `branchType` two fields, **does not contain** `branchName`, `realtime`, `clusterRefresh`, `targetClusterQp` and other attributes.

---

### 5. ab_split_flow — A/B Test Split

```json
{
  "id": "<nodeId>",
  "name": "A/B Split",
  "type": "ab_split_flow",
  "config": {
    "branchList": [
      {
        "branchId": "<branchId>",
        "branchName": "Control Group",
        "branchType": 1,
        "order": 1,
        "percentageInExperiment": 34
      },
      {
        "branchId": "<branchId>",
        "branchName": "Experiment A",
        "branchType": 2,
        "order": 2,
        "percentageInExperiment": 33
      },
      {
        "branchId": "<branchId>",
        "branchName": "Experiment B",
        "branchType": 2,
        "order": "3",
        "percentageInExperiment": 33
      }
    ],
    "indicatorsDef": [
      {
        "indicatorsUuid": "<8-digit random id>",
        "name": "Metric 1",
        "desc": "",
        "completionIndicatorType": 0,
        "touch_cycle_num": 1,
        "touch_cycle_num_unit": "day",
        "event": {
          "key": "<8-digit random id>",
          "eventName": "payment_initiation",
          "eventDesc": "Initiate Payment",
          "eventType": "event",
          "op": "gt",
          "uceCalcuSymbol": "C03",
          "count": 0,
          "num": "0",
          "relation": 1
          /* fixed event fields */
        }
      }
    ],
    "activateIndicatorsDef": null
  }
}
```

> `order`: Fill numbers for 1st and 2nd, fill **string** for 3rd onwards (`"3"`, `"4"`…). When percentage not specified, distribute evenly (3 groups: 34/33/33).

---

### 6. event_judge — Behavior Decision

```json
{
  "id": "<nodeId>",
  "name": "<n>",
  "type": "event_judge",
  "config": {
    "transferType": 1,
    "meetBranchId": "<meetId>",
    "notMeetBranchId": "<notMeetId>",
    "triggerRule": [
      {
        "delayTimeSymbol": "<minute|hour|day>",
        "delayTime": "<number>",
        "eventTriggerType": 0,
        "zoneoffset": 8,
        "events": [
          /* eventCondition field mapping, see step 2 */
        ]
      }
    ]
  }
}
```

> `wait_time` parsing same as time_limit; default to `30, "minute"` when no wait_time.

---

### 7. feature_judge — Attribute Decision

```json
{
  "id": "<nodeId>",
  "name": "<n>",
  "type": "feature_judge",
  "config": {
    "transferType": 1,
    "meetBranchId": "<meetId>",
    "notMeetBranchId": "<notMeetId>",
    "clusterPredictCount": null,
    "clusterPredictTime": "",
    "targetClusterQp": "<JSON serialized string of qp object>"
  }
}
```

---

### 8. webhook_push / message_push — Push Delivery

```json
{
  "id": "<nodeId>",
  "name": "<n>",
  "type": "<webhook_push|message_push>",
  "config": {
    "channelId": "$channelMap[channel_name].channelId",
    "channelType": "$channelMap[channel_name].channelType",
    "enableChannelTouchLimits": false,
    "isOccasionUp": false,
    "contentList": [
      {
        "pushLanguageCode": "default",
        "content": [
          {
            "name": "<paramsList[i].keyName>",
            "type": "<paramsList[i].type>",
            "value": "<fill intent content into best matching field, fill empty string for others>",
            "key": "<paramsList[i].key>",
            "required": "<paramsList[i].required>",
            "config": "<only add when type=TEXT, see explanation below>"
          }
        ]
      }
    ],
    "processType": 1
  }
}
```

> When channel not matched, `contentList` degrades to `[]`, `dataReady` set to `false`.
>
> **Multi-language contentList generation rules:**
>
> When intent JSON action node contains `languages` field, generate independent `contentList[]` entry for each language:
>
> 1. **First entry always `"pushLanguageCode": "default"`**, `value` uses original `content` from intent JSON
> 2. Subsequent entries generated in order of `languages` list, each entry's `pushLanguageCode` fills corresponding language code
> 3. Each language entry's `content[]` structure identical to default (same `key`/`name`/`type`/`required`), only `value` and text in `config` replaced with corresponding language translation
> 4. Translation automatically completed by AI, maintaining original semantics and tone
> 5. For `type=TEXT` parameters, `children[0].text` in `config` field must match translated `value`
>
> **Key Constraints (`config` field for `type=TEXT`):**
>
> | Constraint                 | Description                                                                                  |
> | -------------------------- | -------------------------------------------------------------------------------------------- |
> | **Data Type**              | `config` must be a **JSON string** (not an object/array)                                     |
> | **Fixed Structure**        | Fixed format: `[{"type":"paragraph","children":[{"text":"..."}]}]`                           |
> | **text Value Consistency** | `children[0].text` must exactly match the `value` field                                      |
> | **Applicable Scenario**    | Only parameters with `type=TEXT` need this field; other types (e.g., `STRING`) do not add it |
>
> ⚠️ **Important**: Passing an object/array instead of a JSON string will cause frontend rendering to freeze.

> Example (`languages: ["default", "de", "ja"]`, original content="hi"):
>
> ```json
> "contentList": [
>   { "pushLanguageCode": "default", "content": [{ "key": "content", "type": "TEXT", "value": "hi", "config": "[{\"type\":\"paragraph\",\"children\":[{\"text\":\"hi\"}]}]" }] },
>   { "pushLanguageCode": "de", "content": [{ "key": "content", "type": "TEXT", "value": "Hallo", "config": "[{\"type\":\"paragraph\",\"children\":[{\"text\":\"Hallo\"}]}]" }] },
>   { "pushLanguageCode": "ja", "content": [{ "key": "content", "type": "TEXT", "value": "こんにちは", "config": "[{\"type\":\"paragraph\",\"children\":[{\"text\":\"こんにちは\"}]}]" }] }
> ]
> ```
>
> When no `languages` field or `languages=null`, only generate single `"pushLanguageCode": "default"` entry (backward compatible).

---

### 9. wechat_push — WeChat Subscription Message

```json
{
  "id": "<nodeId>",
  "name": "<n>",
  "type": "wechat_push",
  "config": {
    "channelId": "$channelMap[channel_name]",
    "enableChannelTouchLimits": false,
    "isOccasionUp": false,
    "contentList": [
      {
        "pushLanguageCode": "default",
        "content": [
          {
            "key": "lang",
            "type": "STRING",
            "required": true,
            "paramType": 2,
            "name": "Language",
            "value": "default"
          },
          {
            "key": "page",
            "type": "STRING",
            "required": true,
            "paramType": 2,
            "name": "Jump Page"
          },
          {
            "key": "miniprogramState",
            "type": "STRING",
            "required": true,
            "paramType": 2,
            "name": "Version"
          }
        ]
      }
    ],
    "processType": 1
  }
}
```

---

### 10. time_control — Time Control

```json
{
  "id": "<nodeId>",
  "name": "Time Control",
  "type": "time_control",
  "config": { "controlType": 1, "timeUnit": "<minute|hour|day>", "timeUnitNum": "<number>" }
}
```

> `duration` parsing: `"30 minutes"→minute,30`; `"1 day"→day,1`; `"2 hours"→hour,2`.

---

### 11. exit_flow — End

```json
{ "id": "<nodeId>", "name": "End", "type": "exit_flow" }
```

> Each branch path end must have **independent** exit_flow, different paths do not share.

---

## edgeList Build Rules

Standard edge (no branch):

```json
{ "id": "<8-digit random string>", "source": "<sourceNodeId>", "target": "<targetNodeId>" }
```

With branch outlet:

```json
{
  "id": "<8-digit random string>",
  "source": "<nodeId>",
  "target": "<targetNodeId>",
  "sourceBranchId": "<branchId>"
}
```

| Node Type                                                        | Outgoing Edges   | sourceBranchId Source                         |
| ---------------------------------------------------------------- | ---------------- | --------------------------------------------- |
| `repeat_trigger` / `event_trigger`                               | 1                | None                                          |
| `event_split_flow` / `feature_split_flow` / `ab_split_flow`      | N (1 per branch) | Corresponding `branchList[i].branchId`        |
| `event_judge` / `feature_judge`                                  | 2                | Met→`meetBranchId`; Not met→`notMeetBranchId` |
| `webhook_push` / `message_push` / `wechat_push` / `time_control` | 1                | None                                          |
| `exit_flow`                                                      | 0                | —                                             |

---

## Build Steps

### Step 0: Confirm projectId

Extract user-specified project ID from conversation context. If user hasn't mentioned, ask: "One more quick question—which project do you want to create this journey in? Just tell me the project ID."

After confirmation, inject `$projectId` into top-level structure and use for all subsequent API calls.

---

### Step 1: Read Intent JSON

Read `entry` / `nodes[]` / `flow_name` from intent JSON.

---

### Step 2: Call `query_cluster_qp_skill` to Get Cluster QP and Assemble

**Tool purpose**: Get cluster qp skill, assemble qp based on user intent and skill, generate condition data needed by nodes.

**Field Extraction and Injection Mapping:**

Extract condition text from corresponding fields in intent JSON, call `query_cluster_qp_skill` to generate QP structure, inject into corresponding config parameters by node type.

| Node Type                          | Intent Extraction Field | Injection Field (config)              | Data Source               |
| ---------------------------------- | ----------------------- | ------------------------------------- | ------------------------- |
| `event_trigger`                    | `entry.trigger_event`   | `triggerRule[].events[]`              | qp.eventCondition mapping |
| `event_trigger` (segment ≠ null)   | `entry.segment`         | `targetClusterQp`                     | Full qp structure         |
| `repeat_trigger`                   | `entry.segment`         | `targetClusterQp`                     | Full qp structure         |
| `event_judge`                      | `node.event`            | `triggerRule[].events[]`              | qp.eventCondition mapping |
| `feature_judge`                    | `node.condition`        | `targetClusterQp`                     | Full qp structure         |
| `event_split_flow` (each branch)   | `branch.condition`      | `branchList[].triggerRule[].events[]` | qp.eventCondition mapping |
| `feature_split_flow` (each branch) | `branch.condition`      | `branchList[].targetClusterQp`        | Full qp structure         |

> ⚠️ **Natural Language Parsing**: When calling `query_cluster_qp_skill`, extract key information from natural language:
>
> - Event name: e.g., "completed registration" → `register`, "completed payment" → `payment`
> - Time window: e.g., "within 15 minutes" → `15,minute`, "within 1 hour" → `1,hour`
> - Count/operator: e.g., "completed twice" → `count=2, op=>=`
> - Property conditions: e.g., "VIP level is gold" → extract property/op/value
> - Omitted fields use defaults: `op` defaults to `>=`, `count` defaults to `1`

> ⚠️ When `event_trigger` has no audience (segment = null): `targetClusterQp` fixed to `null`, do not call tool.
>
> ⚠️ **`targetClusterQp` format explanation**: Since node's `config` is JSON, `targetClusterQp` value must be **JSON serialization of qp object** (i.e., `JSON.stringify(qp)`). Example: `"targetClusterQp": "{\"totalCFilter\":{...}}"`

**eventCondition field mapping checklist:**

When data source is `qp.eventCondition mapping`, **only map fields listed in the table below** to `events[]` elements. Fields present in eventCondition but not in the table below must be ignored and not added. If a field in the table below does not exist in eventCondition, use the following default values:

| Field            | When eventCondition Exists                 | Default Value When eventCondition Does Not Exist |
| ---------------- | ------------------------------------------ | ------------------------------------------------ |
| `op`             | Use eventCondition.op                      | `"gte"`                                          |
| `eventDesc`      | Use eventCondition.eventDesc               | Event's description                              |
| `eventName`      | Use eventCondition.eventName               | Event name                                       |
| `eventType`      | Use eventCondition.eventType               | `"event"`                                        |
| `type`           | Use eventCondition.type                    | `"event"`                                        |
| `uceCalcuSymbol` | Use eventCondition.uceCalcuSymbol          | `"C030"`                                         |
| `count`          | Use eventCondition.count                   | `1`                                              |
| `num`            | Use eventCondition.num                     | `"1"`                                            |
| `filts`          | Use eventCondition.filts                   | `[]`                                             |
| `relation`       | Use eventCondition.relation                | `1`                                              |
| `realAvailable`  | Use eventCondition.realAvailable           | `true`                                           |
| `taPropQuota`    | Use eventCondition.taPropQuota             | See default structure below ⚠️                   |
| `key`            | Use eventCondition.key (if present)        | Can be omitted                                   |
| `bubbleInfo`     | Use eventCondition.bubbleInfo (if present) | Can be omitted                                   |
| `isDisPlay`      | Use eventCondition.isDisPlay (if present)  | Can be omitted                                   |
| `withFirst`      | Use eventCondition.withFirst (if present)  | Can be omitted                                   |
| `withUpdate`     | Use eventCondition.withUpdate (if present) | Can be omitted                                   |

````
> ⚠️ taPropQuota must not be empty: When eventCondition exists, taPropQuota must provide a valid structure. If query_cluster_qp_skill does not return valid data, you may use the following default structure:
> ```json
> "taPropQuota": {
>   "quotaDesc": "",
>   "quota": "",
>   "analysis": "A200",
>   "analysisDesc": "Times",
>   "analysisParams": ""
> }
> ```

> ⚠️ When tool unavailable, omit above fields entirely, do not use hardcoded default values.

**When tool available:**
- Traverse all nodes in above table, extract condition descriptions, **deduplicate by condition** then batch call tool
- Save returned results as `$qpMap: { "<condition key>": <qp structure> }`, inject into corresponding fields as needed

**When tool unavailable (skip):**
- `targetClusterQp` 填默认空值（必须是完整标准格式的 JSON 序列化字符串）：
````

"{\"totalCFilter\":{\"relation\":1,\"filts\":[],\"events\":[],\"eventRelation\":1,\"userEventRelation\":1,\"behaviorSeqDefs\":[]},\"totalOutCFilter\":{\"relation\":1,\"filts\":[]}}"

```
> ⚠️ `relation` 必须为数字 `1`，**不得写成字符串 `"1"`**。必须包含 `events`、`eventRelation`、`userEventRelation`、`behaviorSeqDefs`、`totalOutCFilter` 字段，缺少任一字段会导致前端解析崩溃。
> ⚠️ 禁止使用旧格式（含 `userCondition` / `conditionType` 字段），该格式前端无法解析。
- `triggerRule[].events[]` use event info from intent JSON, without qp additional fields
- Continue with subsequent steps, do not interrupt flow

---

### Step 3: Call `query_channel_list` to Get Channel ID

**Call method:** Pass in `projectId`, query all available push channels under this project.

**Channel matching logic:**

1. Extract `channel_name` and `type` from all action nodes in intent `nodes[]`, deduplicate to get matching list
2. Call `query_channel_list` to get complete channel list under project
3. For each `channel_name`, match best channel by following priority:
 - **Exact match**: Channel name exactly matches `channel_name`
 - **Semantic match**: Channel name contains keywords from `channel_name` (e.g., `channel_name="Push Channel"` matches channels with "Push" in name)
 - **Type fallback**: Match by action node's `type` field (e.g., `type="webhook_push"` matches `channelType=1` channels)
4. Save matching results as `$channelMap: { "<channel_name>": { channelId, channelType, paramsList } }`

**When channel not matched:**
- Set `dataReady: false` in corresponding action node
- `contentList` degrades to `[]`
- `channelId` / `channelType` fill empty string or 0

**When tool unavailable (skip):**
- All action nodes' `dataReady` set to `false`
- `contentList` all degrade to `[]`
- Continue with subsequent steps, do not interrupt flow

---

### Step 4: Generate Random IDs
Assign unique 8-digit random numeric string for each node/branch/edge.

---

### Step 5: Apply Templates to Generate nodeList
Map intent JSON nodes to corresponding templates one by one, inject qp and channel data.

---

### Step 6: Build edgeList
- Entry node: Connect to first node in `nodes[]` (no sourceBranchId)
- Action / time_control nodes: Connect to next node (no sourceBranchId)
- Split nodes: Each branch edge (sourceBranchId=branchId) connects to first node of `branch_of=that label`
- Judge nodes: Met edge (meetBranchId) connects to first node of `branch_of="met"`; not met edge connects to first node of `branch_of="not met"`
- Each path end: Append independent exit_flow and connect edge (no sourceBranchId)

---

### Step 7: Self-check
Each non-exit_flow node has ≥1 outgoing edge; each path ends with exit_flow; all branchIds are used in edgeList.

1. **Outgoing Edge Completeness**: Each non-`exit_flow` node has ≥1 outgoing edge
2. **Path Completeness**: Each branch path ends with an independent `exit_flow`
3. **Branch ID Consistency** (only applies to split nodes and judge nodes):
 - `event_split_flow` / `feature_split_flow` / `ab_split_flow`: Each `branchId` in `branchList` must have a corresponding outgoing edge in edgeList (with exactly matching `sourceBranchId`)
 - `event_judge` / `feature_judge`: Both `meetBranchId` and `notMeetBranchId` must each have a corresponding outgoing edge in edgeList (with exactly matching `sourceBranchId`)
 - Push nodes (`webhook_push` / `message_push` etc.): `meetBranchId` / `notMeetBranchId` in config only need to appear in edgeList when `processType: 2`; no check needed when `processType: 1`

> ⚠️ **`splitFlowType: 2` additional validation**: When split node's `splitFlowType` is `2`, need to verify downstream paths of each branch are completely independent—edges from different branches must not point to same target node, each branch must have independent `exit_flow`.

---

### Step 8: Call `save_flow` to Create Journey Canvas

**Prerequisite:** Step 7 self-check passed

**Operation:** Submit complete top-level structure to `save_flow`

**Success:** Show creation result to user (canvas name and other info), and **must** output a clickable Markdown link.

⚠️ **Link generation rules (strictly follow):**

1. Use standard Markdown link syntax, **prohibited** to put in code block
2. URL starts with `/#/`, **prohibited** to add `{domain}` or any domain placeholder
3. Replace `flowUuid` returned by `save_flow` and `projectId` used during creation into URL

**Output template (copy directly, only replace two variables):**

```

[View Canvas](/#/hermes/flow/detail?flowUuid=<replace with actual flowUuid>&currentProjectId=<replace with actual projectId>)

```

**Correct example:**
```

[View Canvas](/#/hermes/flow/detail?flowUuid=0006_831135755&currentProjectId=1)

````

**Common errors (prohibited):**
- ❌ `{domain}/#/hermes/flow/...` — Don't add domain placeholder
- ❌ Put link in code block ` ``` ` — Links in code blocks are not clickable
- ❌ Output plain text URL — Must use `[text](URL)` format

**Failure:** Output complete request body JSON for user debugging, and explain failure reason

---

## Reference Examples

| File | Covered Node Types | Key Points |
|------|-------------------|-----------|
| `references/churn-recall.md` | `repeat_trigger` → `feature_judge` → `webhook_push` | Scheduled entry + attribute bifurcation (meet/not_meet) + multi-channel differentiated delivery; shows end-to-end conversion (user input→intent JSON→canvas request body) |
| `references/new-user-icebreaker.md` | `event_trigger` → `webhook_push` → `event_split_flow` | Event-triggered entry (no audience) + tiered time split (`eventTriggerType:-1` NOT event detection) + fallback branch (`branchType:2` no triggerRule) |
| `references/repurchase-incentive.md` | `repeat_trigger` → `feature_split_flow` → `webhook_push` | Scheduled entry with audience `targetClusterQp` + attribute multi-branch split + complete `contentList` config (STRING/OBJ_ARRAY/NUM) + `completionIndicators` journey goal |
````
