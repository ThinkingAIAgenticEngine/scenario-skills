# MCP Tool: User Sessions Query

Query user login session records

---

## Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | Yes | User unique identifier |
| start_time | string (ISO8601) | No | Query start time |
| end_time | string (ISO8601) | No | Query end time |
| limit | integer | No | Return limit, default 20 |

---

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| sessions | array[Session] | Session list |
| total_online_time | integer | Total online time (seconds) |

### Session Object

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| session_id | string | Session ID | "sess_abc123" |
| login_time | string (ISO8601) | Login time | "2024-03-19T09:23:00Z" |
| logout_time | string (ISO8601) | Logout time | "2024-03-19T09:50:00Z" |
| duration | integer | Online duration (seconds) | 1620 |
| device_type | string | Device type | "iOS" |
| ip | string | IP address | "192.168.1.1" |
| network | string | Network type | "WiFi" |

---

## Examples

### Request
```json
{
  "user_id": "12345",
  "start_time": "2024-03-19T00:00:00Z",
  "end_time": "2024-03-20T00:00:00Z",
  "limit": 10
}
```

### Response
```json
{
  "sessions": [
    {
      "session_id": "sess_001",
      "login_time": "2024-03-19T09:23:00Z",
      "logout_time": "2024-03-19T09:50:00Z",
      "duration": 1620,
      "device_type": "iOS",
      "ip": "192.168.1.100",
      "network": "WiFi"
    }
  ],
  "total_online_time": 1620
}
```
