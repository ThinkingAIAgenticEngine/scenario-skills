# Agent Detection and Creation

Before Step 4B of the configuration phase ("Create the Scheduled Task"), an execution Agent bound to this Skill must exist.

---

## Why a Dedicated Agent Is Required

When a scheduled task fires, an Agent with the metric-alert skill preloaded is needed to execute the script. A generic Agent does not load the skill by default and cannot execute it correctly.

---

## Detection Flow

### 1. List existing Agents and check skillIds one by one

```bash
ae-cli agent +list-agents --format json
```

The returned JSON envelope is `{"ok": true, "data": {"agents": [...]}}`; each entry in the `agents` array contains `id`, `name`, `scope`, `description`, `model` (the list result does **not** include `skillIds`). Query each candidate Agent individually for details:

```bash
ae-cli agent +get-agent --id <agent-id> --format json
```

The fields returned by `+get-agent` include `skillIds`; find an Agent whose `skillIds` contains this Skill's ID.

### 2. On a match: ask the user whether to reuse it

Once found, report to the user:

> Found an Agent bound to the metric-alert skill: "Execution Assistant" (scope: personal). Do you want to reuse this Agent as the execution Agent for this scheduled task?

After the user confirms, fill that Agent's ID into `--agent-id`.

### 3. On no match: create a new Agent

```bash
ae-cli agent +create-agent \
  --name "metric-alert Execution Assistant" \
  --description "Execution Agent for the metric-alert skill; mechanically executes the alert script when a scheduled task fires" \
  --instructions "You are the execution Agent for the metric-alert skill. When a scheduled task fires, only execute the instructions in the message; do not reason, do not ask follow-up questions, do not modify parameters, do not mock. When the script exits non-zero, output the error and stop." \
  --skill-ids '["<this skill id>"]' \
  --scope personal
```

After creation, explain to the user:

> The Agent just created has personal scope and is only available to you. For company-wide reuse, a root user must create a company-scope Agent.

---

## Creating the Scheduled Task

Once you have the `agent_id`:

```bash
ae-cli agent +create-automation \
  --name "<task_name>" \
  --schedule-kind <hourly|daily|weekly|monthly> \
  --minute <0-59> \
  --time <HH:MM> \
  --weekday <0-6> \
  --day-of-month <1-28> \
  --message "<message template>" \
  --agent-id <agent_id> \
  --reuse-conversation true \
  --enabled true
```

**`--reuse-conversation` must be explicitly set to `true`**: this parameter controls whether subsequent executions reuse the same conversation. The platform default is `false` (each trigger starts a new conversation), which is the opposite of what this skill requires - the alert rule's historical context (trial-run conclusions, confirmed reporting definitions) needs to carry over; omitting the parameter will persist it as `false`. Pass `false` only when the user explicitly requests that each execution be isolated in its own conversation.

**Parameter mapping**:

| Alert Rule Field | CLI Parameter | Description |
|------------------|---------------|-------------|
| `schedule.freq=hourly` | `--schedule-kind hourly --minute <n>` | At minute n of every hour |
| `schedule.freq=daily` | `--schedule-kind daily --time <HH:MM>` | Every day at HH:MM |
| `schedule.freq=weekly` | `--schedule-kind weekly --weekday <n> --time <HH:MM>` | On day n of every week at HH:MM (n is 0-6, **0=Sunday**, consistent with `schedule.day_of_week`) |
| `schedule.freq=monthly` | `--schedule-kind monthly --day-of-month <n> --time <HH:MM>` | On day n of every month at HH:MM (n is 1-28, consistent with `schedule.day_of_month`) |

**Note**: `--time` is interpreted in the server time zone; the conversion method and the paired time-zone echo script are described in "Scheduling Time Conversion" in [`timezone-guide.md`](timezone-guide.md).

**Recommended `--minute` is `05` or `10`, not 0**: the right edge of the window lands on the hour; data for the top of the hour often has a few minutes of loading latency, so `--minute 0` would read an incomplete hour. The only allowed values are multiples of 5 (`05`, `10`, `15`...`55`; the UI does not offer values like `06`, `07`). Pair the window and schedule frequency according to the recommended combinations (`natural_hour`+hourly, `natural_day`+daily, `natural_week`+weekly, `today_to_now`+hourly; see the combination table in "window sub-items" in [`rule-schema.md`](rule-schema.md)). When `today_to_now` is paired with hourly, the 00:00-00:59 trigger reports the full previous day - there is no complete hour yet for the current day, which is expected behavior.

---

## Message Template

When a scheduled task fires, the message field must use the following template verbatim:

**Confirm the webhook with the user first**: `notify.webhook_url` in the alert_rule will appear in plaintext in the message. Remind the user before creation - this URL is visible in the automation's trigger records; confirm that the webhook used is safe to expose in that context.

```
MODE: RUN
Skill: metric-alert (skill id: <fill in the platform ID of this skill as-is when creating the automation; the configuration Agent obtains it from the Skill metadata, not guessed by the execution Agent>)
Instruction: The new session of the automation containing this message is the sole workspace.
1) Read the content of scripts/metric_alert.py from the Skill script assets (command: ae-cli agent +read-skill-script --id <skill id above> --path metric_alert.py --output ./metric_alert.py; the command returns a JSON envelope, and the file written by --output is the script body), then Write it to ./metric_alert.py in the root of this session;
2) Write the alert_rule below verbatim to ./alert_rule.json in the root of this session;
3) If the Skill tool runs in an isolated sub-session: both files above must be written back to the root of this session; do not leave them only in the sub-session;
4) Run ls to confirm that metric_alert.py and alert_rule.json exist in the root of this session;
5) Execute in the root of this session:
  METRIC_ALERT_SPEC=./alert_rule.json python3 ./metric_alert.py
6) The script performs the alert push by itself; manual pushing is forbidden. After execution, verify the push field of ./run_result.json and the script exit code:
  0 = normal exit (alert matched and pushed, or no match and silent)
  1 = evaluation error, or message template rendering failed when an alert matched (see the error field in run_result.json)
  2 = spec file missing
  3 = push failed
  The push field is written when "an alert matched and a push attempt was completed": a successful push contains status/body; a failed push contains error (corresponding to exit code 3; a human decides whether to re-push). Exit code 0 with no push field = not triggered, which is normal.
  On non-zero exit, output stderr and the content of run_result.json, then stop.
Do not rewrite SQL / do not switch projects / do not ask follow-up questions / do not mock.
```

**Handling push failures**: inside the script, only network-layer failures (connection failure, timeout) are retried 3 times with exponential backoff (2s/4s/8s, i.e. the first attempt plus 3 retries for 4 attempts total); HTTP non-2xx (deterministic failure, decided directly by status, no retry) and business-layer rejection (the webhook returns a non-zero business code, including responses missing the business code field) are both judged as failed immediately - in all of the above cases the exit code is 3. The automation will not automatically rerun that evaluation; that alert is lost. After the execution Agent reports the error, a human must inspect the push field of run_result.json and decide whether to re-push.

The `alert_rule` JSON content is appended at the end of the template:

```
alert_rule:
${ALERT_RULE_JSON}
```

---

## The Three Delivery Items

After the scheduled task is created, the delivery must include all **three items**; none can be omitted:

1. **Task completion status**: task name + automation ID
2. **Platform jump link**: first run `ae-cli config current --jq '.activeHost'` to read the access domain of the current deployment (**do not hardcode the domain**; the domain of a customer environment is determined by their deployment), then concatenate the automation detail page: `<activeHost>/agent/automations/<automation_id>`
3. **First-run reminder**: recommend that the user manually trigger the automation once (the platform supports running it immediately) and confirm the first run succeeds - issues such as insufficient quota, misconfigured execution Agent, or wrong script path only surface on a real run; static checks cannot reveal them

```bash
# Read the access domain of the current deployment
ae-cli config current --jq '.activeHost'
# Concatenation example (automation_id comes from the create command's response)
# <activeHost>/agent/automations/<automation_id>
```

---

## Debugging and Probing

To probe ae-cli capabilities, use `--dry-run`:

```bash
ae-cli agent +create-agent --dry-run --name "test" --description "x" --instructions "y" --scope personal
```

Full list of items that can be probed:

- `ae-cli agent +list-agents --help`
- `ae-cli agent +get-agent --help`
- `ae-cli agent +create-agent --help`
- `ae-cli agent +create-automation --help`
