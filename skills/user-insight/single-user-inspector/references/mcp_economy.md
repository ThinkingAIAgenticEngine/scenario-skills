# MCP Tool: User Economy Query

Query user economy transactions (recharge, consumption)

---

## Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | Yes | User unique identifier |
| start_time | string (ISO8601) | No | Query start time, omit for all history |

---

## Response Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| user_id | string | User ID | "12345" |
| total_recharge | integer | Total recharge (cents) | 128000 |
| total_recharge_count | integer | Total recharge count | 12 |
| first_recharge_time | string (ISO8601) | First recharge time | "2024-01-20T10:00:00Z" |
| last_recharge_time | string (ISO8601) | Last recharge time | "2024-03-19T14:30:00Z" |
| total_expense | integer | Total expense (cents) | 86000 |
| currency_balance | integer | Current currency balance | 5200 |
| recent_records | array[Record] | Recent recharge records | See below |

### Record Object

| Field | Type | Description |
|-------|------|-------------|
| time | string (ISO8601) | Transaction time |
| type | string | "recharge" or "expense" |
| amount | integer | Amount (cents) |
| item_name | string | Item name |
| item_id | string | Item ID |
| order_id | string | Order ID |

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
  "total_recharge": 128000,
  "total_recharge_count": 12,
  "first_recharge_time": "2024-01-20T10:00:00Z",
  "last_recharge_time": "2024-03-19T14:30:00Z",
  "total_expense": 86000,
  "currency_balance": 5200,
  "recent_records": [
    {
      "time": "2024-03-19T14:30:00Z",
      "type": "recharge",
      "amount": 600,
      "item_name": "Stamina Pack",
      "item_id": "pack_001",
      "order_id": "P202403191430001"
    },
    {
      "time": "2024-03-15T09:00:00Z",
      "type": "recharge",
      "amount": 3000,
      "item_name": "Monthly Card",
      "item_id": "monthly_card",
      "order_id": "P202403150900001"
    }
  ]
}
```
