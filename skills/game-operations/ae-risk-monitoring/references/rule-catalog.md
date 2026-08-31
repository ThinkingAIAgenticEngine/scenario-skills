# Rule catalog

Use these defaults only as calibration starting points. Backtest against the project's traffic distribution before activation.

## `ip_account_burst`

Purpose: detect account farms, credential stuffing, studio activity, scripted registrations, or shared credentials.

Formula for each rolling window and IP/device:

```text
distinct_accounts = count(distinct account_id)
trigger = distinct_accounts >= threshold
```

Starter configuration:

| Parameter | Starter value |
| --- | --- |
| Window | 5 minutes |
| Warning | ≥10 distinct accounts per IP |
| Critical | ≥25 distinct accounts per IP, or ≥10 accounts across ≥3 devices |
| Cooldown | 30 minutes per project + IP + event type |

False-positive guards:

- Separate registration and login alerts.
- Exclude verified office, QA, customer-service, NAT gateway, load-test, and partner IP allowlists.
- Add device count, failure rate, channel, country, account age, or captcha result where available.
- Alert on distinct accounts, not raw event count.
- Require successful events for account-farm monitoring; monitor failures separately for credential attacks.

## `login_silence_or_drop`

Purpose: detect login service outages, severe release regressions, tracking failures, or regional/channel incidents.

Use comparable buckets by weekday and time-of-day when traffic has seasonality. A simple rolling form is:

```text
baseline = median(previous N comparable window counts)
drop_ratio = 1 - current / max(baseline, 1)
trigger = baseline >= absolute_floor and (current = 0 or drop_ratio >= threshold)
```

Starter configuration:

| Parameter | Starter value |
| --- | --- |
| Window | 5 minutes |
| Baseline | median of previous 12 comparable windows; prefer same weekday/time over 4 weeks for production |
| Absolute floor | baseline ≥20 logins per window |
| Warning | current ≤30% of baseline for 2 consecutive windows |
| Critical | current = 0 for 2 windows while heartbeat data is fresh |
| Cooldown | 20 minutes per project + region/channel |

Classification guard:

- If login is zero but other heartbeat events are fresh, classify as likely login/business outage.
- If all monitored events or ingestion are stale beyond the lateness allowance, classify as `DATA_PIPELINE_SUSPECTED`.
- Suppress low-traffic nighttime alerts unless a comparable baseline is high enough.

## `withdrawal_activity`

Purpose: notify operations or risk teams of cash-out activity and escalate unusual amounts or velocity.

Starter configuration:

| Condition | Severity |
| --- | --- |
| Any successful withdrawal | WARNING |
| Amount ≥ configured high-value threshold | CRITICAL |
| Same account ≥3 successful withdrawals in 10 minutes | CRITICAL |
| Same IP/device withdraws from ≥3 accounts in 10 minutes | CRITICAL |
| Failed/pending withdrawal | Separate operational rule, not a successful cash-out notification |

Required controls:

- Confirm currency and normalized amount before comparing thresholds.
- Filter on the verified successful status.
- Deduplicate by immutable transaction/order ID when available.
- Mask account, IP/device, bank, and payment details.
- Never freeze, reject, or reverse a withdrawal automatically from this Skill.

## Severity and notification policy

| Severity | Delivery suggestion | Response target |
| --- | --- | --- |
| INFO | digest only | next business review |
| WARNING | operations/risk group | investigate within 15 minutes |
| CRITICAL | group + on-call escalation | acknowledge within 5 minutes |
| DATA_PIPELINE_SUSPECTED | data/engineering owner | verify ingestion before business action |

Track acknowledgement and closure in the external messaging or incident workflow. Do not infer that delivery equals acknowledgement.
