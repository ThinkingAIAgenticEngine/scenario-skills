# Delivery Mechanisms and Message Forms: Probing, Test Delivery, and Reference Implementations

Delivery on the automation path = two mechanism classes, selected via **BUILD-phase probing + first-run test delivery**. Message form = the **template system**: built-in templates work out of the box; custom templates carry exploration results.

**Quick view of form × channel test status** (detailed capabilities in each section; untested combinations are probed on the spot per the "form-probing methodology". **This table is only a snapshot of historical tests in the demo environment and represents no commitment for any customer environment — combination feasibility is decided by the BUILD-phase test delivery of the final form**):

| Channel | Text | Rich text | Card | File |
|---|---|---|---|---|
| Feishu lark-cli (im_cli) | ✅ | ✅ | ✅ | ✅ |
| Feishu webhook | ✅ | — | ✅ (2.0) | Not implemented (goes via im_cli) |
| WeCom webhook | ✅ | — | Untested | ✅ (upload_media) |
| DingTalk webhook | ✅ (keyword filtering must be handled, see section 6) | — | Untested | Untested |
| custom webhook | ✅ | — | — | — |

> **Message size limits (state only what is known right now; do not hard-code them as constants)**: the values in this table are a **snapshot of tests at the time / official documentation**, and channel-side upgrades can change them at any time — during the BUILD phase, **actual tests are authoritative** (test-deliver a sample at real magnitude close to `preview_rows`; exceeding a limit exposes itself as a channel error). This table is for pre-assessment only, not as a validation basis. Known: WeCom webhook text content upper limit is about 2048 bytes (per official documentation; therefore the default `max_message_kb` of 8KB is **naturally too large** for WeCom text — for WeCom text tasks, reduce preview_rows or cut rows during the BUILD phase; hitting the limit is a deterministic failure with no retry); other channels' size limits are **untested** — do not preset conclusions. The script-side size guardrail (max_message_kb) is a message-side self-constraint and a separate matter from the channel's real limit — passing the guardrail can still be rejected by the channel. Combined operations for WeCom text tasks: **reduce `message.preview_rows` (fewer preview rows)** as the primary lever, `max_message_kb` as the secondary (the guardrail only governs text/rich text; it cannot control the channel's own hard limit).

> **Positioning statement**: every "verified implementation" in this document is a **reference and example, not the sole standard**. During the BUILD phase the LLM can (and should) probe uncovered channel × form combinations on the spot — test-deliver a sample → read the error → iterate → user acceptance. That is precisely the Agent's capability; this document's value is the pitfalls already hit and the shortcuts already verified, not the boundary.

## 1. Two Mechanism Classes

| Mechanism | Form | Description |
|---|---|---|
| **im_cli** (IM CLI direct send) | A channel CLI installed in the sandbox, sending directly as the identity the CLI is bound to | Feishu lark-cli works zero-config (all forms verified); **other channel CLIs attach via command templates** (`send_template`/`send_file_template`/`success` judgment; BUILD-phase probe → test-deliver → lock, see the "Command Templates" section) — text/rich-text/file capability is decided by test-delivery measurement; cards only via lark-cli default form / Feishu webhook |
| **webhook** (group robot) | A group-robot webhook URL provided by the user, HTTP POST | Text is reliable; file capability depends on channel (WeCom verified: upload_media two-step delivery), untested channels get a BUILD-phase test. **webhook file delivery currently implements only the wecom path** — file needs on other channels go through the im_cli mechanism |

For any untested channel, **do not draw negative conclusions**; this document states only verified facts — everything else is decided by BUILD-phase measurement.

## 2. BUILD-Phase Probing + Test-Delivery Flow (SKILL.md Step 4)

1. Ask the user for the delivery target (group / individual / mailbox — mailbox goes straight to the analysis-board push path); **resolving target group → chat_id** (required for im_cli): `lark-cli im +chat-search --query <group name>` (search groups by name to get chat_id; both verified usable) or `lark-cli im +chat-list` (list the sessions of the current identity); **for an individual recipient, read the login identity first** (im_cli): use only the CLI's public identity surfaces (`auth status`, or `im +chat-list` p2p sessions when the account name is not returned directly). Never read, decode, print, or persist the home login-state token — once the identity is read, confirm with the user "the current login identity is <name>; is sending from this account OK?" to lock it, **do not first ask the user for name/email**; only ask if the login identity is unreadable or mismatches the user
2. **Probe** available mechanisms:
   - im_cli: check whether that channel's CLI exists in the sandbox (`which lark-cli` / `--version`) + check `auth status` (OAuth identity and validity; tokenStatus `needs_refresh` needs no handling — the CLI auto-refreshes at send time; verified usable in the demo environment). **CLI absent ≠ this path is impossible — it is "not installed right now", not "no capability"**: do not silently degrade, do not phrase "not installed" as "not available" — honestly lay out the two live paths for the user (rewrite the sample script as needed, keep the semantics) —
     > "The sandbox currently does not have the <channel> CLI installed, so direct sending as your own identity is unavailable right now. Two paths:
     > 1. **The CLI can be installed by yourself** (user-level install; this sandbox needs no admin rights) — you can check whether a CLI exists for <channel>; after installing it, tell me, and I will re-probe + test-deliver to verify, then it can send directly as your identity (all forms including files/cards, and reusable by the same workspace at RUN time — install once, effective long-term). If you want, I can also first try installing it for you (and call on you only if the install fails);
     > 2. If you prefer not to bother, what is usable right now is the group-robot webhook (<report that channel's verified capabilities honestly>), or the platform's analysis-board push channel."
     When the user chooses to install the CLI and comes back after installing → re-run the probe + test-delivery flow, then lock the mechanism (do not assume installed = usable — the test delivery decides)
   - webhook: ask the user for the group-robot URL, **and at the same time state the sending identity** — "messages on this channel are sent as the group robot and appear in the group as from the robot; to send as yourself you need the CLI path"; **identify the kind by the URL domain** (qyapi.weixin.qq.com→wecom / open.feishu.cn→feishu / oapi.dingtalk.com→dingtalk; anything else custom_webhook), and after identifying, **refresh the echo** (update template A's delivery row to the actual channel + identity, then re-confirm)
3. **Test-deliver**: send an identifiable sample in the **final form (template)** to the real target — text for text-type, card for card-type, file tasks include the file; **sample magnitude close to the real RUN scale** (rows segments at a row count close to `preview_rows` — a small sample passing does not mean the full-size message passes the channel's size limit; hard limits like WeCom text 2048B only surface at real magnitude); the primary mechanism must pass the test delivery (`form_ok=true`) before locking. **The test delivery shares the same source as the final form**: early link probing may send test copy, but the final test-delivery content must use the same template as the RUN-phase first push (including the statistical-window row) — what the user sees in the test delivery is the final form; the delivery script explicitly states "this is the final form" — never present two kinds of content ("probe version" vs "production version") and make the user guess which counts
4. User confirms receipt and correct form → mechanism + parameters are written into `spec.delivery.mechanisms`
5. Backup mechanisms are test-delivered likewise (degradation semantics are acceptable when form capability is insufficient, see R5: `form_ok=false` → degrade to plain text + WARNING); cross-channel backup (e.g. "if Feishu fails, send via WeCom") requires the primary and backup mechanisms to share the same `mechanisms[].group` — cross-channel mechanisms without a group become broadcast double-sends at RUN time
6. **The webhook URL appears in plaintext in automation trigger records** — remind the user before creation to confirm it is OK to expose

## 3. BUILD-Phase Form-Probing Methodology (for forms outside the exploration menu)

When a form cannot be satisfied by built-in templates, or a form on an untested channel, explore per this method (a live case of this methodology: the five-round A-to-E iteration of the Feishu card table, at the end of "Card Reference Implementations"):

1. **Send a probe first**: send a minimal invalid structure to the target channel and read the field requirements from the returned ErrMsg (webhook validation failures **do not enter the group** — zero-noise iteration; ErrMsg points out the ErrPath and missing fields, e.g. `table columns is empty`, `unknown property: data_key`)
2. **Minimal valid structure**: fill in fields one by one per the errors until the channel returns success
3. **Real-sample acceptance**: send real-magnitude data (e.g. 100 rows) to a test target, **user confirms the rendering** — server-side validation passing ≠ client-side rendering working (the VChart lesson: a mixed implementation passed validation but the client showed "chart failed to load")
4. **Finalize and lock the template**: the accepted structure is inlined into the spec as a custom template (`message.template`), with placeholders replacing data positions

Note: mechanism facts discovered through exploration (new component structures, new pitfalls) are worth writing back into this skill's reference implementations — that is how this document's reference implementations grew.

## 3.5. Command Templates (im_cli custom channel-CLI attachment)

Channel CLIs for non-lark forms (DingTalk/WeCom/Slack dedicated CLIs, etc.) attach via `mechanisms[].send_template` — the adapter is data locked into the spec at BUILD time, not a code branch. `tool` must be a bare executable name ending in `-cli`, and every command template must begin with the exact `{tool}` argv element; paths, shells, interpreters, and alternate executables are rejected:

```json
{"mechanism": "im_cli", "tool": "dingtalk-cli",
 "target": {"type": "chat", "id": "xxx"},
 "send_template":  ["{tool}", "send", "--conversation-id", "{target_id}", "--text", "{text}"],
 "send_file_template": ["{tool}", "upload", "--chat", "{target_id}", "--path", "{file}", "--name", "{display_name}"],
 "success": {"type": "stdout_json", "field": "errcode", "value": 0}}
```

- **argv-array hard rule (shell strings forbidden)**: one element per argument, the whole `{text}` message occupies one element (safe with spaces/newlines), no shell concatenation; the string form is rejected outright by static validation
- **Closed placeholder vocabulary**: `{tool}`/`{target_id}`/`{target_type}` (shared by both templates) + `{text}` (text template only); the file template has no `{text}` and adds `{file}`/`{display_name}` beyond the three shared words — unknown tokens are rejected (including near-miss typos like `{Text}`/`{text2}`); JSON-argument writing (e.g. `"--payload", '{"content":"{text}"}'`) is legal — placeholders are replaced inside the element, and `{xxx}` in the message body is not expanded a second time (single-pass replacement; the replacement output is not rescanned)
- **success judgment** (consumed with send_template or send_file_template; appearing alone with neither configured → invalid config): default `{"type": "exit_code", "value": 0}` (value defaults to 0); if the CLI output has an envelope (e.g. JSON `errcode`), lock the `stdout_json` type (exit code 0 + field equals value counts as success — some CLIs exit 0 even on failure, with the error only in the output; **both field and value are required** — with value omitted, a missing field in CLI output would be misjudged as success; the value type must match the CLI output field, number for number, string for string); timeouts are classified as network-type retries
- **BUILD-phase flow**: `<CLI> --help` to read the argument shape (first determine how to get the target id — most channel CLIs have a list or search subcommand for groups/conversations/users; use it to obtain the real id and fill `target.id`, then map the argument names from `--help` into template elements) → draft the template → test-deliver one → read the output to identify the envelope (lock success) → user acceptance of receipt → lock into the spec. This "test-deliver → read result → iterate → accept" is isomorphic to the form-probing methodology
- **Cards unsupported**: card messages have no cross-CLI generic expression — card tasks configured with a pure-template mechanism are rejected by static validation; rich text and text share the same template (what the channel renders it into is adjudicated by test delivery + user acceptance)
- An im_cli without a configured template still invokes with lark-cli argument shapes (lark-cli is zero-config; tool not lark-cli and no template → static WARN flagging the omission)

## 4. Built-in Template Library (factory references for the five forms, referenced by `message.template` name; the fifth form = one of the first 4 templates + the `content.file` section combined, no independent template name)

| Reference name | Form | Structure | Best for |
|---|---|---|---|
| `builtin:plain` | Plain text | Conditional assembly of title / value segments / rows segments / file block | Form 1 single-day metrics; fallback on all channels |
| `builtin:rich` | Rich text | Same structure as plain, sent with lark-cli `--markdown` | Form 1 when bold separators are needed (im_cli only — webhook channels are not blocked by the script; markdown symbols go into the text as-is; check it yourself during the BUILD phase) |
| `builtin:card_chart` | Chart card | Card 2.0: header + chart (VChart; `queries[].chart` selects line/bar, default line) + summary markdown | Form 2 multi-day / multi-group metrics |
| `builtin:card_table` | Table card | Card 2.0: header + table component (display_name header) | Form 3 TopN / leaderboards ≤100 rows |

(An analysis report is not a value of `message.template` — report scenarios are expressed by `content.kind=report` and go through the report pipeline; unknown names with the `builtin:` prefix are rejected by the script with exit code 2.)

- Form 4 (full detail rows + attachment) = `builtin:plain` or `builtin:card_table` + `content.file` (message contains "X rows total + summary (optional summary) + preview" + CSV attachment; the attachment is an independent file message)
- **Row-set cell values pass through verbatim**: cells in card tables / plain-text table pastes / HTML data tables get no thousands separators — phone numbers / order numbers / IDs stay copyable and identical to the CSV attachment; thousands separators apply only to value-segment numbers and `{{agg.*}}` aggregated values. The CSV attachment prefixes `'` to values starting with `=` `+` `-` `@` that **do not parse as numbers** (formula-injection protection — numeric values such as negative numbers are not prefixed, keeping them summable numbers in Excel)
- Placeholder consumption of built-in templates follows the "Placeholder Vocabulary" (push-spec-schema.md); the customization path = copy a built-in skeleton, rework it, then **inline** it (a string equal to a built-in name is always parsed as the built-in — a same-name "override" does not take effect)
- **A card with an empty data segment renders no corresponding component**: a 0-row rows query places only `**{label}**: no data this period` in markdown at that segment position (sensible degradation — no empty chart/table component is rendered); a value segment with 0 columns shows `-`
- Row sets over 100 rows: preview truncated to `preview_rows` (default 100) + "X rows total" annotation; card table components over 100 rows are unverified — measure during the BUILD phase or just go with the file path

## 5. Card Reference Implementations (Feishu, verified)

### Card 2.0 Skeleton

```json
{
  "schema": "2.0",
  "config": {},
  "header": {"title": {"tag": "plain_text", "content": "[Daily Report] {{task_name}} {{window_range}}"}},
  "body": {"direction": "vertical", "elements": [ ... ]}
}
```

- **v1 cards (top-level elements) are deprecated**: markdown pipe tables do not render in v1 (raw pipe-character text); 2.0 has fuller capabilities
- 2.0 does **not** support the `note` tag (use a markdown element instead); passing `config.update_multi` as false is rejected (300302)

### table Component (form 3)

```json
{"tag": "table",
 "columns": [{"name": "rank", "display_name": "Rank"}, {"name": "level", "display_name": "Level"}],
 "rows": "{{q.leaderboard.rows}}"}
```

- `columns[].name` = data key (matching the rows dict keys); `display_name` = header text (**omitting it means no header**)
- `rows` = list of rows, each a "column-name → value" dict — the placeholder `{{q.<label>.rows}}` produces exactly this structure
- Verified: 100 rows (~5.4KB card) renders fine and is scrollable

### chart Component (form 2, VChart spec — not ECharts)

```json
{"tag": "chart",
 "chart_spec": {
   "type": "line",
   "data": [{"id": "core", "values": "{{q.last_7_days.long}}"}],
   "xField": "date", "yField": "value", "seriesField": "metric",
   "legends": {"visible": true, "orient": "top"}
 }}
```

- `data[].values` must be a **long table** (one record per point) — the placeholder `{{q.<label>.long}}` converts the wide table (each row "date,metricA,metricB") into a `date/metric/value` long table; `seriesField` points at the metric-name field, automatically splitting multiple lines + legend
- **Pitfall table (all verified)**: ECharts writing (`xAxis.data`/`series[].data` arrays) → rejected by validation, or "validation passes but the client fails to load the chart"; `tooltip.trigger` only click/hover/none; mixed writing (root type + ECharts axes) passes server-side leniently but fails client-side rendering
- Debugging method: **the webhook's ErrMsg is a schema probe** (see "Form-Probing Methodology")

### markdown Component

```json
{"tag": "markdown", "content": "**Yesterday recharge**: count {{agg.payment_count}} / amount {{agg.total_payment_amount}}"}
```

- The 2.0 markdown component **supports pipe tables** (v1's div + lark_md does not — the A/B sample records raw pipe-character text); the table component is still recommended (structured pass-through, no pipe-string assembly)

### Exploration Record (the source of this section's reference implementations; a live case of the methodology)

A/B (v1 lark_md; v1 markdown component pipe tables) → no rendering; C (2.0 + markdown component) → real table with header; D (2.0 + table component) → real table without header; E (+display_name) → real table with header, **finalized**. Each step advanced via "send sample → see what the user received → read errors → fix structure" — none of it came from pre-written documentation.

## 6. Verified Facts Table (measured in the demo environment)

### Feishu · lark-cli (im_cli, verified)

- Sandbox `~/.local/bin/lark-cli` (demo-environment example), OAuth user identity (scope `im:message.send_as_user`); the token has expiry/refresh mechanics
- Send command: `lark-cli im +messages-send`, `--chat-id oc_xxx` (group) or `--user-id ou_xxx` (individual), `--as user` (this skill always sends as the user identity — the sending identity follows the mechanism, not a separate config)
- **All forms pass** (p2p direct send verified):
  - Plain text: `--text "..."`
  - Rich text (recommended): `--markdown "..."` (the CLI auto-converts to Feishu post; bold/links work, no tag restrictions triggered)
  - Card: `--content '<card JSON>' --msg-type interactive` (content passes the card JSON body directly; 2.0 skeleton same as webhook)
  - File: `--file <local path>` (auto-upload; txt/csv/html all fine)
- Note: `--file/--image` local paths must be cwd-relative (the CLI rejects absolute paths and `..`)
- **A single Feishu message cannot carry both body and file** — a file task = a text message + a file message, two messages (normal behavior; explain to the user)

### Feishu · webhook (verified)

- Group-robot URL `https://open.feishu.cn/open-apis/bot/v2/hook/<key>`, POST JSON
- Text: `{"msg_type":"text","content":{"text":…}}`; card: `{"msg_type":"interactive","card":<2.0 skeleton>}`
- Card chart/table/markdown components as in the previous section; **file delivery unverified** — file needs go via im_cli or the WeCom webhook
- Validation failures return an ErrMsg (with ErrPath), **not entering the group** — a natural probe

### WeCom · webhook (verified)

- Text: `{"msgtype":"text","text":{"content":…}}` (no keyword requirement)
- File (two steps): ① `POST .../webhook/upload_media?key=<key>&type=file` (multipart) to get media_id ② POST the main URL `{"msgtype":"file","file":{"media_id":…}}`
- Card capability untested — probe during the BUILD phase (no fixed conclusion)

### DingTalk · webhook (text verified usable)

- Text payload same shape as WeCom; the custom robot's security setting must be "custom keywords" (the message must contain the keyword); **signature mode is not implemented by the script** — when the user provides a signature webhook, state this honestly and guide them to switch to keyword mode or im_cli
- **Recognizing and handling keyword rejection** (two-case verified record): when the robot has keyword filtering configured, messages without the keyword are rejected; DingTalk's error text (returned in Chinese regardless of the caller's language) is "关键词不匹配；请联系群管理员查看此机器人的关键词，并在发送的信息中包含此关键词" — **the keyword content cannot be probed from outside** (tests tried all common candidate words, none hit; the real word may be an uncommon one like "data daily report"). Handling flow: ① recognize the error signature (the text above) → ② guide the user to group settings → robot → security settings to view the **exact keyword**, or have the user modify the security settings directly (add a word like "daily report") → ③ write the keyword into the push title (e.g. "Data Daily Report: core metrics …") → ④ resend to verify. The first-run test delivery will expose this problem — when a test delivery fails, do not first suspect the pipeline; first check whether the error is about keywords

## 7. RUN-Phase Execution Semantics (authoritative definition in push-spec-schema.md R5)

- Network-type failures retry 3 times with 2/4/8s backoff — **HTTP 429/500/502/503/504 are transient failures** (rate limiting / gateway jitter / upstream overload), classified as network-type and retried likewise; deterministic failures (other non-2xx HTTP / nonzero business code / CLI absent / unparseable return) are not retried
- Degradation happens **within a channel**: a card form that cannot be sent → the same mechanism degrades to a plain-text summary + WARNING (delivery first) — which channel to push is fixed at BUILD time; no cross-channel hopping
- Primary mechanism failure → switch in order to backup mechanisms for the same target (backup mechanisms are configured per the user's explicit need — e.g. "if Feishu fails, send via WeCom"; **cross-channel backup requires both mechanisms to share the same `mechanisms[].group`** — without a group, a Feishu group and a WeCom group are different targets = broadcast double-send; with none configured there is no backup); all failed → exit code 3
- A mechanism with `file_ok=false` is skipped and warned in file-type tasks (do not force a delivery that will most likely fail)
- Channel feasibility = the BUILD-phase measurement flags (form_ok/file_ok); **no hard-coded channel × form matrix is maintained**

## 8. RUN-Sandbox Dependency List (fail-loud expectations)

Each automation RUN trigger opens a fresh sandbox but **shares the same workspace install state as the BUILD phase** (demo-environment measurement: a CLI installed/logged in during the BUILD phase is reusable at RUN time — multiple automations' first runs succeeded + large file deliveries succeeded; for other customer environments, still verify via a RUN test run in the target environment):

| Dependency | Purpose | Behavior when missing |
|---|---|---|
| `ae-cli` | All data fetching / analysis-board queries / timezone reading | die 1 (config paths: `env.ae_cli_path`/`cli`) |
| `python3` | The script itself | automation cannot execute (platform-side issue) |
| `lark-cli` | im_cli mechanism delivery | deterministic failure of that mechanism → exit code 3 (fail-loud, not silent) |
| `curl` | WeCom webhook file delivery (upload_media two steps) | wecom file delivery fails → exit code 3 |

(All are deterministic failures with interpretable exit codes — missing RUN-phase dependencies do not silently swallow messages; when probing available mechanisms during the BUILD phase, if a RUN-sandbox difference is suspected, explain that risk to the user.)
