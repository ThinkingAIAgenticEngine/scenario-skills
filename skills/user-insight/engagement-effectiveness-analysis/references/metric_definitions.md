# Metric Definitions and Stage Model

Both modes are mapped onto the same six-stage funnel so that a single analysis
pipeline can serve either. Mode B simply starts later in the chain.

## The shared funnel

| # | Metric key | Stage | Definition | Mode A | Mode B |
|---|---|---|---|:---:|:---:|
| 1 | `plan` | target audience | size of the audience the campaign was aimed at | native | derived |
| 2 | `actualTrigger` | flow entry | users who actually entered the campaign flow | native | n/a |
| 3 | `trigger` | dispatch | messages dispatched successfully (platform-side delivery proxy) | native | n/a |
| 4 | `view` | impression | users who actually saw the message | native | from events |
| 5 | `click` | click | users who clicked or opened | native | from events |
| 6 | `main` | conversion | users who completed the goal | native | from events |

Mode A cannot observe stages past `trigger` when the platform has no receipt for
them, and mode B cannot observe stages before its first tracked event. Both
degrade by **truncating** the funnel rather than producing zeros - a zero that
means "not measured" is the most dangerous output this skill can produce.

## Stage-to-stage conversion rates

| Rate | Numerator | Denominator | Benchmark | Alert direction |
|---|---|---|---|:---:|
| 触达率 / reach | `actualTrigger` | `plan` | - | - |
| 发送成功率 / dispatch success | `trigger` | `actualTrigger` | 0.90 | below |
| 曝光率 / impression | `view` | `trigger` | - | - |
| 点击率 / click-through | `click` | `view` | 0.03 | below |
| 转化率 / conversion | `main` | `click` | - | - |

A rate is only computed when both sides are measurable. If the denominator is
unavailable the rate is `null`, and any rate that used a substituted denominator
is flagged `degraded` so the report can say so.

### Click-through with a degraded denominator

When `view` is not available, `click / trigger` is used instead. This
overstates the true CTR because it counts users who never saw the message. The
report states the substitution; the workbook records both the declared and the
used denominator.

## Which stage counts as "dispatch success"

`trigger` is the platform's own count of messages that left successfully. It is
used as the delivery proxy because true delivery receipts are frequently not
available. In the sandbox, task `0822` reports `actualTrigger = 13339` and
`trigger = 10676`, i.e. 80.0% dispatch success against a 90% benchmark - a real
finding, and the correct top bleed point.

## Attribution windows

| Source | Where the window lives |
|---|---|
| Mode A | `completionIndicatorDef` on the task (`touch_cycle_num` + unit) |
| Mode B | the funnel `window` field -> `windows_gap_ms` / `windows_gap_tu` in the QP |

Common values are 24 hours for a click-through goal and 5 days for a purchase
goal. Always report which window was used: a conversion rate without its
attribution window is not interpretable.

## Metrics that are explicitly out of scope

| Metric | Why it is not here |
|---|---|
| unsubscribe rate | the benchmark exists, but neither mode returns it from a report call; it requires a separate event query |
| revenue / ARPU | requires a revenue model this skill does not own |
| long-term retention | the retention builder can produce it, but trend attribution needs a cohort design beyond a single campaign review |
