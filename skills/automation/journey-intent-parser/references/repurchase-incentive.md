---
name: example-repurchase-incentive
description: Repurchase incentive for paid users reference case. repeat_trigger scheduled entry (with audience filtering for yesterday's paid users) + feature_split_flow three-tier split by user value + webhook_push differentiated gifts (with complete contentList config). Demonstrates usage of feature_split_flow and completionIndicators.
---

# Case: Repurchase Incentive for Paid Users

## Scenario Description

> **Flow Goal**: Based on yesterday's paid users' historical value, improve user repurchase rate and order value through differentiated gift strategy.
>
> **Core Strategy**:
>
> 1. **Audience selection**: Target all users who made payments yesterday
> 2. **User segmentation**: After entering the flow, system automatically segments users into high-value, medium-value, and low-value groups based on "historical cumulative payment amount"
> 3. **Differentiated delivery**: For different value tiers, trigger and push personalized gifts that match their level (high-value → premium gift, medium-value → standard gift, low-value → activation gift)

---

## User Input

> Create a repurchase incentive flow for paid users: run every day at 9 AM for users who paid yesterday. After entering the flow, segment users by payment capability into high-value, medium-value, and low-value groups, push different tier popup gifts respectively, then each path ends. Also set a flow goal: initiate payment within 1 day.

---

## Flow Topology

```
repeat_trigger (Daily 09:00 · Yesterday's paid users)
  └── feature_split_flow (Segment by payment capability)
        ├─ High-value users → webhook_push (Premium gift ¥99→¥66) → exit
        ├─ Medium-value users → webhook_push (Standard gift ¥66→¥39) → exit
        └─ Low-value users → webhook_push (Activation gift ¥29→¥9) → exit
```

---

## Key Node Types

| Node      | type                   | Description                                                                                                            |
| --------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Entry     | `repeat_trigger`       | Daily scheduled execution, targetClusterQp contains yesterday's payment filter condition                               |
| Split     | `feature_split_flow`   | Segment by user **property** (payment capability tag) into multiple groups, each group has independent targetClusterQp |
| Deliver   | `webhook_push`         | Contains complete contentList (gift name, item group, original price, discount price)                                  |
| End       | `exit_flow`            | Path terminus                                                                                                          |
| Flow goal | `completionIndicators` | Initiate payment within 1 day counts as conversion success                                                             |

> **feature_split_flow vs feature_judge**:
>
> - `feature_judge`: Bifurcation (meet/not_meet), checks single condition
> - `feature_split_flow`: Multi-branch (N branches), each branch has independent targetClusterQp audience condition

> **feature_split_flow vs event_split_flow**:
>
> - `feature_split_flow`: Split by user **current property**, no time wait, `splitFlowType: 1` for property split
> - `event_split_flow`: Split by **behavior + time window**, has delayTime wait

---

## Intent Parsing (Intent JSON)

**Inference Process:**

| Field            | Basis                                                                   | Result                           |
| ---------------- | ----------------------------------------------------------------------- | -------------------------------- |
| `flow_type`      | "Repurchase incentive for paid users"                                   | `REPURCHASE_INCENTIVE`           |
| `entry.type`     | "Every day at 9 AM"                                                     | `repeat_trigger`                 |
| `entry.schedule` | "Every day at 9 AM"                                                     | `"Daily 09:00"`                  |
| `entry.segment`  | "Users who paid yesterday"                                              | Yesterday's paid users segment   |
| n1               | "Segment by user payment capability into three groups" → Property split | `feature_split_flow`, 3 branches |
| n2               | High-value branch → Premium gift                                        | `webhook_push`                   |
| n3               | Path terminus                                                           | `exit_flow`                      |
| n4               | Medium-value branch → Standard gift                                     | `webhook_push`                   |
| n5               | Path terminus                                                           | `exit_flow`                      |
| n6               | Low-value branch → Activation gift                                      | `webhook_push`                   |
| n7               | Path terminus                                                           | `exit_flow`                      |

```json
{
  "flow_type": "REPURCHASE_INCENTIVE",
  "flow_name": "Repurchase Incentive for Paid Users",

  "entry": {
    "type": "repeat_trigger",
    "trigger_event": { "event": "payment_initiation" },
    "schedule": "Daily 09:00",
    "segment": "Yesterday's paid users",
    "start_date": null,
    "end_date": null
  },

  "nodes": [
    {
      "nid": "n1",
      "node_type": "split",
      "type": "feature_split_flow",
      "name": "Segment by Payment Capability",
      "dimension": "PAY_ABILITY",
      "branches": [
        {
          "bid": "b1",
          "label": "High-value users",
          "condition": { "property": "pay_ability", "op": "=", "value": "high" },
          "percentage": null
        },
        {
          "bid": "b2",
          "label": "Medium-value users",
          "condition": { "property": "pay_ability", "op": "=", "value": "medium" },
          "percentage": null
        },
        {
          "bid": "b3",
          "label": "Low-value users",
          "condition": { "property": "pay_ability", "op": "=", "value": "low" },
          "percentage": null
        }
      ]
    },
    {
      "nid": "n2",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Premium Gift Pack",
      "content": "Limited-time Premium Gift Pack (Item×15+Item×5), Original Price ¥99, Discount Price ¥66",
      "channel_name": "Popup Gift Pack"
    },
    { "nid": "n3", "node_type": "end", "type": "exit_flow" },
    {
      "nid": "n4",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Standard Gift Pack",
      "content": "Limited-time Standard Gift Pack (Item×10+Item×3), Original Price ¥66, Discount Price ¥39",
      "channel_name": "Popup Gift Pack"
    },
    { "nid": "n5", "node_type": "end", "type": "exit_flow" },
    {
      "nid": "n6",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Activation Gift Pack",
      "content": "Limited-time Activation Gift Pack (Item×5+Item×1), Original Price ¥29, Discount Price ¥9",
      "channel_name": "Popup Gift Pack"
    },
    { "nid": "n7", "node_type": "end", "type": "exit_flow" }
  ],

  "edges": [
    { "from": "entry", "to": "n1", "via": null },
    { "from": "n1", "to": "n2", "via": "b1" },
    { "from": "n2", "to": "n3", "via": null },
    { "from": "n1", "to": "n4", "via": "b2" },
    { "from": "n4", "to": "n5", "via": null },
    { "from": "n1", "to": "n6", "via": "b3" },
    { "from": "n6", "to": "n7", "via": null }
  ],

  "confidence": 0.88,
  "missing_fields": [],
  "clarify_questions": []
}
```

---

## Canvas Request Body (canvas-node-builder Output)

**ID Assignment:**

| Node                      | nodeId           | Notes              |
| ------------------------- | ---------------- | ------------------ |
| repeat_trigger            | `0315_100000001` |                    |
| feature_split_flow        | `0315_200000002` |                    |
| b1 branchId               | `0315_300000003` | High-value users   |
| b2 branchId               | `0315_400000004` | Medium-value users |
| b3 branchId               | `0315_500000005` | Low-value users    |
| webhook_push (premium)    | `0315_600000006` |                    |
| exit_flow (1)             | `0315_700000007` |                    |
| webhook_push (standard)   | `0315_800000008` |                    |
| exit_flow (2)             | `0315_900000009` |                    |
| webhook_push (activation) | `0315_A00000010` |                    |
| exit_flow (3)             | `0315_B00000011` |                    |

```json
{
  "flowName": "Repurchase Incentive for Paid Users",
  "flowDesc": "Based on yesterday's paid users' historical value, improve user repurchase rate and order value through differentiated gift strategy",
  "groupId": 0,
  "nodeList": [
    {
      "id": "0315_100000001",
      "name": "Yesterday's Paid Users",
      "type": "repeat_trigger",
      "config": {
        "triggerType": 2,
        "targetUserType": 1,
        "startDate": "2026-03-15",
        "endDate": "2026-08-31",
        "flowEndDate": "2026-09-02 00:00",
        "crontab": "0 00 09 * * ?",
        "entryControlLimits": { "enableMultEntry": false, "disableConcurrentEntry": false },
        "targetClusterName": null,
        "clusterPredictCount": null,
        "clusterPredictTime": "2026-03-15 09:00:00",
        "targetClusterQp": { "totalCFilter": { "relation": "1", "filts": [] } }
      },
      "uiConfig": {}
    },
    {
      "id": "0315_200000002",
      "name": "Segment by Payment Capability",
      "type": "feature_split_flow",
      "config": {
        "splitFlowType": 1,
        "branchList": [
          {
            "branchId": "0315_300000003",
            "branchName": "High-value Users",
            "branchType": 1,
            "realtime": 0,
            "clusterRefresh": 12,
            "clusterPredictCount": null,
            "clusterPredictTime": "2026-03-15 09:00:00",
            "targetClusterQp": { "totalCFilter": { "relation": "1", "filts": [] } }
          },
          {
            "branchId": "0315_400000004",
            "branchName": "Medium-value Users",
            "branchType": 1,
            "realtime": 0,
            "clusterRefresh": 12,
            "clusterPredictCount": null,
            "clusterPredictTime": "2026-03-15 09:00:00",
            "targetClusterQp": { "totalCFilter": { "relation": "1", "filts": [] } }
          },
          {
            "branchId": "0315_500000005",
            "branchName": "Low-value Users",
            "branchType": 1,
            "realtime": 0,
            "clusterRefresh": 12,
            "clusterPredictCount": null,
            "clusterPredictTime": "2026-03-15 09:00:00",
            "targetClusterQp": { "totalCFilter": { "relation": "1", "filts": [] } }
          }
        ]
      },
      "uiConfig": { "dataReady": false }
    },
    {
      "id": "0315_600000006",
      "name": "Premium Gift Pack",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [
          {
            "pushLanguageCode": "default",
            "content": [
              {
                "key": "gift_name",
                "type": "STRING",
                "value": "Limited-time Premium Gift Pack",
                "required": true
              },
              {
                "key": "items",
                "type": "OBJ_ARRAY",
                "value": "[{\"name\":\"Item A\",\"count\":15},{\"name\":\"Item B\",\"count\":5}]",
                "required": true
              },
              { "key": "original_price", "type": "NUM", "value": "99", "required": true },
              { "key": "discount_price", "type": "NUM", "value": "66", "required": true }
            ]
          }
        ],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    { "id": "0315_700000007", "name": "End", "type": "exit_flow", "uiConfig": {} },
    {
      "id": "0315_800000008",
      "name": "Standard Gift Pack",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [
          {
            "pushLanguageCode": "default",
            "content": [
              {
                "key": "gift_name",
                "type": "STRING",
                "value": "Limited-time Standard Gift Pack",
                "required": true
              },
              {
                "key": "items",
                "type": "OBJ_ARRAY",
                "value": "[{\"name\":\"Item A\",\"count\":10},{\"name\":\"Item B\",\"count\":3}]",
                "required": true
              },
              { "key": "original_price", "type": "NUM", "value": "66", "required": true },
              { "key": "discount_price", "type": "NUM", "value": "39", "required": true }
            ]
          }
        ],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    { "id": "0315_900000009", "name": "End", "type": "exit_flow", "uiConfig": {} },
    {
      "id": "0315_A00000010",
      "name": "Activation Gift Pack",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [
          {
            "pushLanguageCode": "default",
            "content": [
              {
                "key": "gift_name",
                "type": "STRING",
                "value": "Limited-time Activation Gift Pack",
                "required": true
              },
              {
                "key": "items",
                "type": "OBJ_ARRAY",
                "value": "[{\"name\":\"Item A\",\"count\":5},{\"name\":\"Item B\",\"count\":1}]",
                "required": true
              },
              { "key": "original_price", "type": "NUM", "value": "29", "required": true },
              { "key": "discount_price", "type": "NUM", "value": "9", "required": true }
            ]
          }
        ],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    { "id": "0315_B00000011", "name": "End", "type": "exit_flow", "uiConfig": {} }
  ],
  "edgeList": [
    { "id": "0315_E01000001", "source": "0315_100000001", "target": "0315_200000002" },
    {
      "id": "0315_E02000002",
      "source": "0315_200000002",
      "target": "0315_600000006",
      "sourceBranchId": "0315_300000003"
    },
    { "id": "0315_E03000003", "source": "0315_600000006", "target": "0315_700000007" },
    {
      "id": "0315_E04000004",
      "source": "0315_200000002",
      "target": "0315_800000008",
      "sourceBranchId": "0315_400000004"
    },
    { "id": "0315_E05000005", "source": "0315_800000008", "target": "0315_900000009" },
    {
      "id": "0315_E06000006",
      "source": "0315_200000002",
      "target": "0315_A00000010",
      "sourceBranchId": "0315_500000005"
    },
    { "id": "0315_E07000007", "source": "0315_A00000010", "target": "0315_B00000011" }
  ],
  "uiConfig": { "direction": "VERTICAL" },
  "completionIndicators": [
    {
      "indicatorsUuid": "0315_GOAL0001",
      "name": "Repurchase Conversion",
      "desc": "",
      "completionIndicatorType": 0,
      "touch_cycle_num": 1,
      "touch_cycle_num_unit": "day",
      "event": {
        "eventName": "payment_initiation",
        "eventDesc": "Initiate Payment",
        "eventType": "event",
        "relation": 1,
        "key": "0315_GOAL_EVT",
        "taPropQuota": {
          "analysis": "A200",
          "analysisDesc": "times",
          "analysisParams": "",
          "quota": "",
          "quotaDesc": ""
        },
        "op": "gt",
        "uceCalcuSymbol": "C03",
        "count": 0,
        "filts": [],
        "num": "0",
        "bubbleInfo": {
          "bubbleType": "super_event",
          "dataStatus": "normal",
          "hasConnected": true,
          "id": 49082
        },
        "isDisPlay": 1,
        "realAvailable": true,
        "withFirst": false,
        "withUpdate": false
      }
    }
  ],
  "versionType": 1,
  "projectId": 61
}
```

---

## Key Differences from Other Cases

| Comparison           | Case 1 (Churn Recall)           | Case 2 (Icebreaker Payment)           | Case 3 (Repurchase Incentive)                |
| -------------------- | ------------------------------- | ------------------------------------- | -------------------------------------------- |
| Entry type           | `repeat_trigger`                | `event_trigger`                       | `repeat_trigger`                             |
| Core split node      | `feature_judge` (bifurcation)   | `event_split_flow` (behavior+time)    | `feature_split_flow` (property multi-branch) |
| Branch logic         | Binary choice by payment status | 4 tiers by unpaid duration + fallback | 3 tiers by payment capability                |
| Audience filter      | Inactive for last 14 days       | None (triggered on registration)      | Yesterday's paid users                       |
| webhook_push content | Empty contentList               | Empty contentList                     | **Complete contentList** (with gift config)  |
| completionIndicators | None                            | None                                  | **Yes** (initiate payment within 1 day)      |
