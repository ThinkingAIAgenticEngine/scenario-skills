---
name: example-new-user-icebreaker
description: New user icebreaker payment reference case. event_trigger registration event entry + webhook_push instant gift + event_split_flow time-gradient split (with fallback branch). Demonstrates complete usage of multi-branch NOT event detection and fallback branchType:2.
---

# Case: New User Icebreaker Payment

## Scenario Description

> **Flow Goal**: Maximize first-order conversion rate for newly registered users through a tiered incentive strategy.
>
> **Core Strategy**:
>
> 1. **First-order warm-up**: Immediately send "Newbie Gift Pack" after user registration to lower first-time decision threshold
> 2. **Tiered stimulation**: At 15 minutes, 30 minutes, 60 minutes, and 1 day after registration, push progressively stronger payment guidance benefits to users who still haven't paid
> 3. **Conversion reward**: Users who complete first payment within 1 day (fallback branch) automatically receive additional first-order reward to complete conversion loop

---

## User Input

> Create a new user icebreaker payment flow: immediately send a newbie gift pack after user registration, then check payment status at four time points: 15 minutes, 30 minutes, 60 minutes, and 1 day. For users who haven't paid, push payment guidance, popup gift, popup gift, and special offer gift respectively. Users who have paid within 1 day (fallback) receive first-order reward, then each path ends.

---

## Flow Topology

```
event_trigger (Registration event)
  └── webhook_push (Newbie gift pack)
        └── event_split_flow (Unpaid tiered split)
              ├─ b1: 15min unpaid → webhook_push (Payment guidance) → exit
              ├─ b2: 30min unpaid → webhook_push (Popup gift) → exit
              ├─ b3: 60min unpaid → webhook_push (Popup gift) → exit
              ├─ b4: 1day unpaid  → webhook_push (Special offer) → exit
              └─ b5: Fallback (paid) → webhook_push (First-order reward) → exit
```

---

## Key Node Types

| Node            | type               | Description                                                                               |
| --------------- | ------------------ | ----------------------------------------------------------------------------------------- |
| Entry           | `event_trigger`    | Event-triggered, user enters upon registration, no schedule                               |
| Instant action  | `webhook_push`     | Immediately send newbie gift pack after registration                                      |
| Split           | `event_split_flow` | Check behavior by time gradient, `eventTriggerType: -1` (NOT event) means "did not occur" |
| Fallback branch | branchType: 2      | No triggerRule, captures all users not falling into first 4 branches (i.e., already paid) |
| Deliver         | `webhook_push`     | Differentiated gifts for each branch                                                      |
| End             | `exit_flow`        | Path terminus                                                                             |

> **event_split_flow Key Rules**:
>
> - "Unpaid" branches use `eventTriggerType: -1` (NOT event), different from default `0` (AT event)
> - Fallback branch `branchType: 2`, **no triggerRule**
> - Time units: `delayTimeSymbol` is `"minute"` or `"day"`

---

## Intent Parsing (Intent JSON)

**Inference Process:**

| Field                 | Basis                                             | Result                         |
| --------------------- | ------------------------------------------------- | ------------------------------ |
| `flow_type`           | "New user" registration trigger                   | `NEW_USER_ACTIVATE`            |
| `entry.type`          | "Immediately after registration" → Event trigger  | `event_trigger`                |
| `entry.trigger_event` | Auto-inferred                                     | `register`                     |
| n1                    | "Immediately send a newbie gift pack"             | `webhook_push`                 |
| n2                    | "Check payment at 15/30/60min, 1day" + "fallback" | `event_split_flow`, 5 branches |
| n3~n12                | Actions and ends for each branch                  | `webhook_push` + `exit_flow`   |

```json
{
  "flow_type": "NEW_USER_ACTIVATE",
  "flow_name": "New User Icebreaker Payment Flow",

  "entry": {
    "type": "event_trigger",
    "trigger_event": { "event": "register" },
    "schedule": null,
    "segment": null,
    "start_date": null,
    "end_date": null
  },

  "nodes": [
    {
      "nid": "n1",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Newbie Gift Pack",
      "content": "Newbie gift pack upon registration (Item×1)",
      "channel_name": null
    },
    {
      "nid": "n2",
      "node_type": "split",
      "type": "event_split_flow",
      "name": "Unpaid Tiered Split",
      "dimension": "PAY_TIME_GRADIENT",
      "branches": [
        {
          "bid": "b1",
          "label": "15min unpaid",
          "condition": { "event": "pay", "time_limit": "15m", "occurred": false },
          "time_limit": "15m",
          "percentage": null
        },
        {
          "bid": "b2",
          "label": "30min unpaid",
          "condition": { "event": "pay", "time_limit": "30m", "occurred": false },
          "time_limit": "30m",
          "percentage": null
        },
        {
          "bid": "b3",
          "label": "60min unpaid",
          "condition": { "event": "pay", "time_limit": "60m", "occurred": false },
          "time_limit": "60m",
          "percentage": null
        },
        {
          "bid": "b4",
          "label": "1day unpaid",
          "condition": { "event": "pay", "time_limit": "1d", "occurred": false },
          "time_limit": "1d",
          "percentage": null
        },
        {
          "bid": "b5",
          "label": "Fallback",
          "condition": null,
          "time_limit": null,
          "percentage": null
        }
      ]
    },
    {
      "nid": "n3",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Payment Guidance",
      "content": "Limited-time payment guidance popup",
      "channel_name": null
    },
    { "nid": "n4", "node_type": "end", "type": "exit_flow" },
    {
      "nid": "n5",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Popup Gift Pack (30min)",
      "content": "Popup gift pack (Item×2)",
      "channel_name": null
    },
    { "nid": "n6", "node_type": "end", "type": "exit_flow" },
    {
      "nid": "n7",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Popup Gift Pack (60min)",
      "content": "Popup gift pack (Item×2)",
      "channel_name": null
    },
    { "nid": "n8", "node_type": "end", "type": "exit_flow" },
    {
      "nid": "n9",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Special Offer Gift Pack",
      "content": "1-day special offer gift pack (High-discount Item×3)",
      "channel_name": null
    },
    { "nid": "n10", "node_type": "end", "type": "exit_flow" },
    {
      "nid": "n11",
      "node_type": "action",
      "type": "webhook_push",
      "name": "First-Order Reward",
      "content": "First-order reward (Extra Item×1)",
      "channel_name": null
    },
    { "nid": "n12", "node_type": "end", "type": "exit_flow" }
  ],

  "edges": [
    { "from": "entry", "to": "n1", "via": null },
    { "from": "n1", "to": "n2", "via": null },
    { "from": "n2", "to": "n3", "via": "b1" },
    { "from": "n3", "to": "n4", "via": null },
    { "from": "n2", "to": "n5", "via": "b2" },
    { "from": "n5", "to": "n6", "via": null },
    { "from": "n2", "to": "n7", "via": "b3" },
    { "from": "n7", "to": "n8", "via": null },
    { "from": "n2", "to": "n9", "via": "b4" },
    { "from": "n9", "to": "n10", "via": null },
    { "from": "n2", "to": "n11", "via": "b5" },
    { "from": "n11", "to": "n12", "via": null }
  ],

  "confidence": 0.9,
  "missing_fields": [],
  "clarify_questions": []
}
```

---

## Canvas Request Body (canvas-node-builder Output)

**ID Assignment:**

| Node                              | nodeId           | Notes        |
| --------------------------------- | ---------------- | ------------ |
| event_trigger                     | `0314_110000011` |              |
| webhook_push (newbie gift)        | `0314_120000012` |              |
| event_split_flow                  | `0314_130000013` |              |
| b1 branchId                       | `0314_140000014` | 15min unpaid |
| b2 branchId                       | `0314_150000015` | 30min unpaid |
| b3 branchId                       | `0314_160000016` | 60min unpaid |
| b4 branchId                       | `0314_170000017` | 1day unpaid  |
| b5 branchId (fallback)            | `0314_180000018` | Paid users   |
| webhook_push (payment guidance)   | `0314_190000019` |              |
| exit_flow (1)                     | `0314_200000020` |              |
| webhook_push (popup gift 30min)   | `0314_210000021` |              |
| exit_flow (2)                     | `0314_220000022` |              |
| webhook_push (popup gift 60min)   | `0314_230000023` |              |
| exit_flow (3)                     | `0314_240000024` |              |
| webhook_push (special offer)      | `0314_250000025` |              |
| exit_flow (4)                     | `0314_260000026` |              |
| webhook_push (first-order reward) | `0314_270000027` |              |
| exit_flow (5)                     | `0314_280000028` |              |

```json
{
  "flowName": "New User Icebreaker Payment Flow",
  "flowDesc": "Maximize first-order conversion rate for newly registered users through a tiered incentive strategy",
  "groupId": 0,
  "nodeList": [
    {
      "id": "0314_110000011",
      "name": "Registration Event",
      "type": "event_trigger",
      "config": {
        "triggerType": 1,
        "targetUserType": 1,
        "startDate": "2026-03-14",
        "endDate": "2026-08-31",
        "flowEndDate": "2026-09-02 00:00",
        "entryControlLimits": { "enableMultEntry": false, "disableConcurrentEntry": false },
        "targetClusterName": null,
        "clusterPredictCount": null,
        "clusterPredictTime": "",
        "targetClusterQp": { "totalCFilter": { "relation": "1", "filts": [] } },
        "triggerEvent": {
          "eventName": "register",
          "eventDesc": "Registration",
          "eventType": "event",
          "relation": 1,
          "key": "0314_ENTRY_EVT",
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
            "id": 49001
          },
          "isDisPlay": 1,
          "realAvailable": true,
          "withFirst": false,
          "withUpdate": false
        }
      },
      "uiConfig": {}
    },
    {
      "id": "0314_120000012",
      "name": "Newbie Gift Pack",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    {
      "id": "0314_130000013",
      "name": "Unpaid Tiered Split",
      "type": "event_split_flow",
      "config": {
        "splitFlowType": 2,
        "branchList": [
          {
            "branchId": "0314_140000014",
            "branchName": "15min Unpaid",
            "branchType": 1,
            "triggerRule": {
              "delayTime": 15,
              "delayTimeSymbol": "minute",
              "eventTriggerType": -1,
              "triggerEvent": {
                "eventName": "pay",
                "eventDesc": "Payment",
                "eventType": "event",
                "relation": 1,
                "key": "0314_B1_EVT",
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
                  "id": 49010
                },
                "isDisPlay": 1,
                "realAvailable": true,
                "withFirst": false,
                "withUpdate": false
              }
            }
          },
          {
            "branchId": "0314_150000015",
            "branchName": "30min Unpaid",
            "branchType": 1,
            "triggerRule": {
              "delayTime": 30,
              "delayTimeSymbol": "minute",
              "eventTriggerType": -1,
              "triggerEvent": {
                "eventName": "pay",
                "eventDesc": "Payment",
                "eventType": "event",
                "relation": 1,
                "key": "0314_B2_EVT",
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
                  "id": 49010
                },
                "isDisPlay": 1,
                "realAvailable": true,
                "withFirst": false,
                "withUpdate": false
              }
            }
          },
          {
            "branchId": "0314_160000016",
            "branchName": "60min Unpaid",
            "branchType": 1,
            "triggerRule": {
              "delayTime": 60,
              "delayTimeSymbol": "minute",
              "eventTriggerType": -1,
              "triggerEvent": {
                "eventName": "pay",
                "eventDesc": "Payment",
                "eventType": "event",
                "relation": 1,
                "key": "0314_B3_EVT",
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
                  "id": 49010
                },
                "isDisPlay": 1,
                "realAvailable": true,
                "withFirst": false,
                "withUpdate": false
              }
            }
          },
          {
            "branchId": "0314_170000017",
            "branchName": "1day Unpaid",
            "branchType": 1,
            "triggerRule": {
              "delayTime": 1,
              "delayTimeSymbol": "day",
              "eventTriggerType": -1,
              "triggerEvent": {
                "eventName": "pay",
                "eventDesc": "Payment",
                "eventType": "event",
                "relation": 1,
                "key": "0314_B4_EVT",
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
                  "id": 49010
                },
                "isDisPlay": 1,
                "realAvailable": true,
                "withFirst": false,
                "withUpdate": false
              }
            }
          },
          {
            "branchId": "0314_180000018",
            "branchName": "Fallback",
            "branchType": 2
          }
        ]
      },
      "uiConfig": { "dataReady": false }
    },
    {
      "id": "0314_190000019",
      "name": "Payment Guidance",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    { "id": "0314_200000020", "name": "End", "type": "exit_flow", "uiConfig": {} },
    {
      "id": "0314_210000021",
      "name": "Popup Gift Pack (30min)",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    { "id": "0314_220000022", "name": "End", "type": "exit_flow", "uiConfig": {} },
    {
      "id": "0314_230000023",
      "name": "Popup Gift Pack (60min)",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    { "id": "0314_240000024", "name": "End", "type": "exit_flow", "uiConfig": {} },
    {
      "id": "0314_250000025",
      "name": "Special Offer Gift Pack",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    { "id": "0314_260000026", "name": "End", "type": "exit_flow", "uiConfig": {} },
    {
      "id": "0314_270000027",
      "name": "First-Order Reward",
      "type": "webhook_push",
      "config": {
        "channelId": "",
        "enableChannelTouchLimits": false,
        "isOccasionUp": false,
        "contentList": [],
        "processType": 1
      },
      "uiConfig": { "dataReady": false }
    },
    { "id": "0314_280000028", "name": "End", "type": "exit_flow", "uiConfig": {} }
  ],
  "edgeList": [
    { "id": "0314_E01000001", "source": "0314_110000011", "target": "0314_120000012" },
    { "id": "0314_E02000002", "source": "0314_120000012", "target": "0314_130000013" },
    {
      "id": "0314_E03000003",
      "source": "0314_130000013",
      "target": "0314_190000019",
      "sourceBranchId": "0314_140000014"
    },
    { "id": "0314_E04000004", "source": "0314_190000019", "target": "0314_200000020" },
    {
      "id": "0314_E05000005",
      "source": "0314_130000013",
      "target": "0314_210000021",
      "sourceBranchId": "0314_150000015"
    },
    { "id": "0314_E06000006", "source": "0314_210000021", "target": "0314_220000022" },
    {
      "id": "0314_E07000007",
      "source": "0314_130000013",
      "target": "0314_230000023",
      "sourceBranchId": "0314_160000016"
    },
    { "id": "0314_E08000008", "source": "0314_230000023", "target": "0314_240000024" },
    {
      "id": "0314_E09000009",
      "source": "0314_130000013",
      "target": "0314_250000025",
      "sourceBranchId": "0314_170000017"
    },
    { "id": "0314_E10000010", "source": "0314_250000025", "target": "0314_260000026" },
    {
      "id": "0314_E11000011",
      "source": "0314_130000013",
      "target": "0314_270000027",
      "sourceBranchId": "0314_180000018"
    },
    { "id": "0314_E12000012", "source": "0314_270000027", "target": "0314_280000028" }
  ],
  "uiConfig": { "direction": "VERTICAL" },
  "completionIndicators": [],
  "versionType": 1,
  "projectId": 61
}
```
