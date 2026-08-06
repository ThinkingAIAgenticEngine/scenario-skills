---
name: example-churn-recall
description: Churn recall reference case. repeat_trigger scheduled entry + feature_judge split by payment status + webhook_push differentiated channel delivery. Demonstrates end-to-end transformation from user input → intent JSON → complete canvas request body.
---

# Case: Churn Recall

## Scenario Description

> **Flow Goal**: Re-engage dormant users at low cost to improve overall activity.
>
> **Core Strategy**: Filter users who haven't logged in for the last 14 days, segment them by user value (payment status), and match different recall channels:
>
> - **High-priority recall (paid users)**: Use SMS channel for high delivery rate to ensure recall opportunities for high-value users
> - **Regular delivery (non-paid users)**: Use PUSH channel for low-cost coverage of large-scale dormant users

---

## User Input

> Create a churn recall flow: run every day at 8 PM for users who haven't logged in for the last 14 days. After entering the flow, first check if the user has ever paid. Paid users go through SMS channel recall, non-paid users go through Push message recall, then each path ends.

---

## Flow Topology

```
repeat_trigger (Daily 20:00 · Users inactive for last 14 days)
  └── feature_judge (Has paid?)
        ├─ meet     → webhook_push (SMS recall) → exit
        └─ not_meet → webhook_push (Push recall) → exit
```

---

## Key Node Types

| Node    | type             | Description                                                                                  |
| ------- | ---------------- | -------------------------------------------------------------------------------------------- |
| Entry   | `repeat_trigger` | Daily scheduled execution, crontab defines frequency                                         |
| Split   | `feature_judge`  | Checks user **property** (e.g., payment status), no wait window, fixed outputs meet/not_meet |
| Deliver | `webhook_push`   | Configure SMS/Push channels separately                                                       |
| End     | `exit_flow`      | Path terminus                                                                                |

---

## Intent Parsing (Intent JSON)

**Inference Process:**

| Field                 | Basis                                                                | Result                              |
| --------------------- | -------------------------------------------------------------------- | ----------------------------------- |
| `flow_type`           | "Churn recall"                                                       | `CHURN_RECALL`                      |
| `entry.type`          | "Every day at 8 PM"                                                  | `repeat_trigger`                    |
| `entry.schedule`      | "Every day at 8 PM"                                                  | `"Daily 20:00"`                     |
| `entry.trigger_event` | CHURN_RECALL auto-inferred                                           | `login`                             |
| n1                    | "First check if user has paid" → Check user property, no wait window | `feature_judge`                     |
| n2                    | "Paid users go through SMS channel" → Webhook/SMS                    | `webhook_push`, channel_name="SMS"  |
| n3                    | Path terminus                                                        | `exit_flow`                         |
| n4                    | "Non-paid users go through Push message"                             | `webhook_push`, channel_name="Push" |
| n5                    | Path terminus                                                        | `exit_flow`                         |

```json
{
  "flow_type": "CHURN_RECALL",
  "flow_name": "Churn Recall",

  "entry": {
    "type": "repeat_trigger",
    "trigger_event": { "event": "login" },
    "schedule": "Daily 20:00",
    "segment": "Users inactive for last 14 days",
    "start_date": null,
    "end_date": null
  },

  "nodes": [
    {
      "nid": "n1",
      "node_type": "judge",
      "type": "feature_judge",
      "name": "Has Paid",
      "event": null,
      "condition": { "property": "pay_status", "op": "=", "value": "paid" },
      "wait_time": null,
      "branches": [
        { "bid": "meet", "label": "Meet" },
        { "bid": "not_meet", "label": "Not Meet" }
      ]
    },
    {
      "nid": "n2",
      "node_type": "action",
      "type": "webhook_push",
      "name": "SMS Recall",
      "content": "Your exclusive comeback gift pack has arrived, click to view",
      "channel_name": "SMS Channel"
    },
    { "nid": "n3", "node_type": "end", "type": "exit_flow" },
    {
      "nid": "n4",
      "node_type": "action",
      "type": "webhook_push",
      "name": "Push Message Recall",
      "content": "${user.nickname}, we miss you! Your exclusive comeback bonus has arrived, open the app to view",
      "channel_name": "Push Channel"
    },
    { "nid": "n5", "node_type": "end", "type": "exit_flow" }
  ],

  "edges": [
    { "from": "entry", "to": "n1", "via": null },
    { "from": "n1", "to": "n2", "via": "meet" },
    { "from": "n2", "to": "n3", "via": null },
    { "from": "n1", "to": "n4", "via": "not_meet" },
    { "from": "n4", "to": "n5", "via": null }
  ],

  "confidence": 0.85,
  "missing_fields": ["entry.start_date", "entry.end_date"],
  "clarify_questions": [
    "Please confirm flow start and end dates (reference: 2026-03-14 ~ 2026-08-31)"
  ]
}
```

---

## Canvas Request Body (canvas-node-builder Output)

**ID Assignment:**

| Node                | nodeId           | Notes               |
| ------------------- | ---------------- | ------------------- |
| repeat_trigger      | `0314_100000001` |                     |
| feature_judge       | `0314_200000002` |                     |
| meetBranchId        | `0314_300000003` | judge meet exit     |
| notMeetBranchId     | `0314_400000004` | judge not_meet exit |
| webhook_push (SMS)  | `0314_500000005` |                     |
| exit_flow (1)       | `0314_600000006` |                     |
| webhook_push (Push) | `0314_700000007` |                     |
| exit_flow (2)       | `0314_800000008` |                     |

```json
{
  "flowName": "Churn Recall",
  "flowDesc": "Segment high-value and regular churned users by payment status, recall through differentiated SMS and Push channels",
  "groupId": 0,
  "nodeList": [
    {
      "id": "0314_100000001",
      "name": "Users inactive for last 14 days",
      "type": "repeat_trigger",
      "config": {
        "triggerType": 2,
        "targetUserType": 1,
        "startDate": "2026-03-14",
        "endDate": "2026-08-31",
        "flowEndDate": "2026-09-02 00:00",
        "crontab": "0 00 20 * * ?",
        "entryControlLimits": { "enableMultEntry": false, "disableConcurrentEntry": false },
        "targetClusterName": null,
        "clusterPredictCount": null,
        "clusterPredictTime": "",
        "targetClusterQp": {
          "totalCFilter": {
            "filts": [
              {
                "filts": [
                  {
                    "eventCondition": {
                      "op": "gt",
                      "withUpdate": false,
                      "filts": [],
                      "num": "0",
                      "count": 0,
                      "eventType": "event",
                      "withFirst": false,
                      "realAvailable": true,
                      "relation": 1,
                      "eventDesc": "Login",
                      "taPropQuota": {
                        "quotaDesc": "",
                        "quota": "",
                        "analysis": "A200",
                        "analysisDesc": "Times",
                        "analysisParams": ""
                      },
                      "recentDay": "0-14",
                      "eventName": "login",
                      "uceCalcuSymbol": "C00",
                      "startTime": "2026-03-31 00:00:00",
                      "endTime": "2026-04-13 23:59:59",
                      "key": "aN7RHg3e",
                      "isDisPlay": 1
                    },
                    "conditionType": "event"
                  }
                ],
                "relation": "1"
              }
            ],
            "relation": "1"
          }
        }
      },
      "uiConfig": {}
    },
    {
      "id": "0314_200000002",
      "name": "Has Paid",
      "type": "feature_judge",
      "config": {
        "judgeType": 1,
        "meetBranchId": "0314_300000003",
        "notMeetBranchId": "0314_400000004",
        "clusterPredictCount": null,
        "clusterPredictTime": "",
        "targetClusterQp": { "totalCFilter": { "relation": "1", "filts": [] } }
      },
      "uiConfig": { "dataReady": false, "meetBranchPosition": "left" }
    },
    {
      "id": "0314_500000005",
      "name": "SMS Recall",
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
      "id": "0314_600000006",
      "name": "End",
      "type": "exit_flow",
      "uiConfig": {}
    },
    {
      "id": "0314_700000007",
      "name": "Push Message Recall",
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
      "id": "0314_800000008",
      "name": "End",
      "type": "exit_flow",
      "uiConfig": {}
    }
  ],
  "edgeList": [
    { "id": "0314_901000009", "source": "0314_100000001", "target": "0314_200000002" },
    {
      "id": "0314_902000010",
      "source": "0314_200000002",
      "target": "0314_500000005",
      "sourceBranchId": "0314_300000003"
    },
    { "id": "0314_903000011", "source": "0314_500000005", "target": "0314_600000006" },
    {
      "id": "0314_904000012",
      "source": "0314_200000002",
      "target": "0314_700000007",
      "sourceBranchId": "0314_400000004"
    },
    { "id": "0314_905000013", "source": "0314_700000007", "target": "0314_800000008" }
  ],
  "uiConfig": { "direction": "VERTICAL" },
  "completionIndicators": [],
  "versionType": 1,
  "projectId": 61
}
```
