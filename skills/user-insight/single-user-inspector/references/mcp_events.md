# MCP Tool: User Events Query

Query user behavior event logs

---

## Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | Yes | User unique identifier |
| start_time | string (ISO8601) | Yes | Query start time |
| end_time | string (ISO8601) | Yes | Query end time |
| limit | integer | No | Return limit, default 100, max 500 |
| event_types | array[string] | No | Filter by event types |

---

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| events | array[Event] | Event list |
| total_count | integer | Total event count (may be more than returned) |

### Event Object

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| event_time | string (ISO8601) | Event time | "2024-03-19T09:23:00Z" |
| event_type | string | Event type code | "1001" |
| event_name | string | Event name | "Login" |
| params | object | Event params | See below |

### Common Event Parameters

| Event Type | Parameter Example |
|------------|-------------------|
| Enter Stage | `{ "stage_id": "12-5", "chapter": 12, "stage": 5 }` |
| Battle Result | `{ "stage_id": "12-5", "result": "fail", "duration": 180 }` |
| Purchase Item | `{ "item_id": "5001", "item_name": "Stamina Pack", "amount": 600, "currency": "USD" }` |
| Login | `{ "device_id": "xxx", "ip": "1.2.3.4", "network": "WiFi" }` |

---

## Examples

### Request
```json
{
  "user_id": "12345",
  "start_time": "2024-03-19T00:00:00Z",
  "end_time": "2024-03-20T00:00:00Z",
  "limit": 100
}
```

### Response
```json
{
  "events": [
    {
      "event_time": "2024-03-19T09:23:00Z",
      "event_type": "1001",
      "event_name": "Login",
      "params": {
        "device_id": "abc123",
        "network": "WiFi"
      }
    },
    {
      "event_time": "2024-03-19T09:25:00Z",
      "event_type": "1003",
      "event_name": "Enter Stage",
      "params": {
        "stage_id": "12-5",
        "chapter": 12,
        "stage": 5
      }
    },
    {
      "event_time": "2024-03-19T09:30:00Z",
      "event_type": "1005",
      "event_name": "Battle Failed",
      "params": {
        "stage_id": "12-5",
        "result": "fail"
      }
    }
  ],
  "total_count": 8
}
```
