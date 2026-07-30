# MCP Tool: User Progress Query

Query user game progress data

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
| level | integer | Current level | 45 |
| exp | integer | Current EXP | 12500 |
| exp_to_next | integer | EXP needed to level up | 3500 |
| chapter | integer | Current chapter | 12 |
| stage | integer | Current stage | 5 |
| max_stage_cleared | string | Max stage cleared | "11-10" |
| achievements | array[Achievement] | Achievement list | See below |
| stats | object | Statistics | See below |

### Achievement Object

| Field | Type | Description |
|-------|------|-------------|
| id | string | Achievement ID |
| name | string | Achievement name |
| completed_at | string (ISO8601) | Completion time |

### Stats Object

| Field | Type | Description |
|-------|------|-------------|
| total_battles | integer | Total battles |
| total_wins | integer | Total wins |
| win_rate | float | Win rate |
| total_play_time | integer | Total play time (seconds) |

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
  "level": 45,
  "exp": 12500,
  "exp_to_next": 3500,
  "chapter": 12,
  "stage": 5,
  "max_stage_cleared": "11-10",
  "achievements": [
    {
      "id": "first_win",
      "name": "First Victory",
      "completed_at": "2024-01-16T10:00:00Z"
    }
  ],
  "stats": {
    "total_battles": 328,
    "total_wins": 256,
    "win_rate": 0.78,
    "total_play_time": 460800
  }
}
```
