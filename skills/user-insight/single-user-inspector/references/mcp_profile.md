# MCP Tool: User Profile Query

Query user basic profile information

---

## Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | Yes | User unique identifier |

---

## Response Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| user_id | string | User ID | "12345" |
| register_time | string (ISO8601) | Registration time | "2024-01-15T08:30:00Z" |
| last_active_time | string (ISO8601) | Last active time | "2024-03-20T18:45:00Z" |
| last_login_time | string (ISO8601) | Last login time | "2024-03-20T09:00:00Z" |
| level | integer | User level | 45 |
| vip_level | integer | VIP level | 3 |
| total_recharge | integer | Total recharge amount (cents) | 128000 (= $1280) |
| recharge_count | integer | Recharge count | 12 |
| first_recharge_time | string (ISO8601) | First recharge time | "2024-01-20T10:00:00Z" |
| last_recharge_time | string (ISO8601) | Last recharge time | "2024-03-19T14:30:00Z" |
| total_play_time | integer | Total play time (seconds) | 460800 (= 128 hours) |
| status | string | User status | "active" |
| tags | array[string] | User tags | ["High Activity", "Core Player"] |
| device_type | string | Device type | "iOS" |
| channel | string | Channel source | "AppStore" |

---

## Examples

### Request
```json
{
  "user_id": "12345"
}
```

### Response
```json
{
  "user_id": "12345",
  "register_time": "2024-01-15T08:30:00Z",
  "last_active_time": "2024-03-20T18:45:00Z",
  "last_login_time": "2024-03-20T09:00:00Z",
  "level": 45,
  "vip_level": 3,
  "total_recharge": 128000,
  "recharge_count": 12,
  "first_recharge_time": "2024-01-20T10:00:00Z",
  "last_recharge_time": "2024-03-19T14:30:00Z",
  "total_play_time": 460800,
  "status": "active",
  "tags": ["High Activity", "Core Player", "PVE Preference"],
  "device_type": "iOS",
  "channel": "AppStore"
}
```

---

## Error Codes

| Error Code | Description |
|------------|-------------|
| USER_NOT_FOUND | User does not exist |
| INVALID_USER_ID | User ID format error |
