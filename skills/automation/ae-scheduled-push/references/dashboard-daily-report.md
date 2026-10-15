# Analysis Board push path: dashboard_daily_report capability boundaries (empirically finalized, retested and corrected)

The Analysis Board push path = the platform's built-in board subscription push. **4 capabilities** (use in this order):

```
analysis.dashboard_daily_report.update   Create/update the configuration (upsert+merge, omitted fields remain unchanged)
analysis.dashboard_daily_report.get      Read back the configuration (sensitive values masked) — for two-stage read-back
analysis.dashboard_daily_report.send     Send immediately (returns task_id; send overrides title/content for that single run)
analysis.dashboard_daily_report.send_status  Query delivery progress (per-channel detail)
```

## Empirically verified capability boundary table

| Item | Conclusion (empirical) |
|---|---|
| Channels | **6**: email / dd (DingTalk) / wx (WeCom) / feishu (Feishu) / kim (KIM/custom webhook combined) / slack; each channel takes a URL array (multiple groups) |
| Email recipients | `email_login_users` (platform login names, comma-separated) + `email_new` (arbitrary mailboxes); **by default only project members with a bound mailbox are supported** (the sender must bind a mailbox first in Personal Center → Account Security; external mailboxes require SMTP enabled by the system) |
| Feishu | `feishu_info` = app_id+app_secret+webhook[]; credentials are used to upload screenshots (**confirmed to push screenshots**; text+image content requires the full triple) |
| Frequency | send_date (comma-separated 1..7 days of week) + send_time (**on-the-hour 0~23, comma-separated multi-value supported**, e.g. "09:00,18:00"; read back normalized as "9,18"; 09:30 rejected with INVALID_SEND_TIME, 24:00 rejected) + enable_send. Frequency grid = Monday~Sunday (multi-select) × on-the-hour hours (multi-select); **non-hourly/minute-level frequency goes through the automation path** |
| Expressing "every day" | **Pass an empty string `""` for send_date** → the server normalizes to "1,2,3,4,5,6,7" (empirical) |
| send_date out of range | "0"/"1,8" are **stored as-is with no business validation** (validate also lets them pass) → BUILD must validate a 1~7 whitelist on the client side |
| Day-of-week semantics | 1..7 (1=Monday), same direction as alert; **opposite of the automation path's 0-6 (0=Sunday)** — do not carry values across paths |
| update merge | Empirically holds: pass only send_title and the rest is preserved; incremental modification is safe |
| send channel selection | **Trap 1**: omitting destination fields ≠ reusing saved destinations (empirically returns `daily.error.nochannel`; the capability description says "omission reuses saved destinations", which contradicts the empirical result — trust the empirical result); **Trap 2**: passing `email_new` alone does not select the email channel, `email_login_users` is the email selector (email_new is an additional address); send does not recognize `enable_*` fields |
| Multi-channel concurrency | Works; email succeeded + wx failed → overall `partially_succeeded` + per-channel detail + Chinese localeMsg (RUN-side judgment must check each channel, not just the overall status) |
| State machine | queued → rendering → sending → succeeded / partially_succeeded / failed / canceled; asynchronous ~20-45 seconds |
| Single report | **No entry point**: all three capabilities anchor on a mandatory dashboard_id, a board must be attached (to "push just one report", first create a board to hold it) |
| Placeholders | 4: `$[看板名]$` / `$[日期]$` / `$[昨日日期]$` / `$[看板计算时间]$`; an empty title falls back to `$[Dashboard Title]$` (bilingual forms) |
| CSV attachment | need_csv=true: zip (if <30M and SMTP available) / download link+extraction code (expires in 30 days; when via bot channels, no SMTP, or over 30M) |
| Screenshot width | screen_type: normal / wide (1.5x width, fully displays tables about 15 columns wide) |
| host_url | **Mandatory: pass the public domain** (each deployment uses its own public domain, of the form https://<your-deployment-domain>). If omitted → links inside the email are intranet addresses (v1/ta/..., static_file/...) that recipients cannot open (empirical) |
| Data permissions | Computed under the **board creator's** permissions (the automation path follows the executing identity — the two paths have different permission semantics; cross-path migrated tasks must flag this) |
| Filters | Computed from the board's default filter state; timezone via zone_offset (pass a raw -12~14 number, 5.5 supported; a **different set of semantics** from alert's data_zone_offset=99 sentinel) |
| Daily report config cleanup | No delete capability; update with explicit empty values to disable (enable_send=false + clear each channel — empirically works) |

## get read-back key/value transformations (read before any field-by-field comparison)

Read-back keys and input keys are **not the same names** — literal comparison will misjudge as "configuration error":

| Input key/value | Read-back key/value |
|---|---|
| `enable_dd` | `enable_d_d` |
| `enable_wx` | `enable_w_x` |
| `send_time: "09:00"` | `send_time: "9"` (leading-zero normalization) |
| `send_date: ""` | `send_date: "1,2,3,4,5,6,7"` |
| `send_time: "09:00,18:00"` | `send_time: "9,18"` |
| URL array fields of channels not enabled | Absent from the read-back (do not treat as lost) |

## BUILD flow (Analysis Board push path)

1. **Precondition checks (page-guided checklist, CLI cannot do these)**: the board exists (if not, guide creation; `analysis.dashboard.create`+`analysis.report.create` can create it on the user's behalf; a single report must be attached to a board); for the email channel check the sender's mailbox binding/SMTP availability; for Feishu text+image check the app triple
2. Assemble the update parameters (**validate each send_date value against the 1~7 whitelist before passing** — the platform stores "0"/"1,8" as-is with no business validation, a misconfiguration silently takes effect, and validate lets it pass too): dashboard_id + send_date (pass "" for every day, or a day-of-week like "2"; pass "09:00,18:00" for multiple time points) + send_time (on the hour) + channel fields + `host_url` (**mandatory**) + zone_offset + need_csv/screen_type + send_title/send_content (placeholders usable). **zone_offset out of range silently falls back** (empirical: values outside the project's available timezone list, e.g. writing 9 when project 2's list is -12/-7/-2/0/5/6/8/12) — the platform raises no error and silently falls back to default UTC+8 (values inside the list are stored as-is); **after writing, you must get and read back to verify the actual value**; if it does not match, guide the user to pick from the available list or ask a project admin to extend the list
3. `capability run analysis.dashboard_daily_report.update` → **immediately `get` to read back and compare field by field** (compare using the transformation mapping above; creation succeeded ≠ configuration is correct; **zone_offset must be compared** — silent fallback of out-of-range values, see step 2)
4. First-run verification: `send` an immediate delivery (title/content can be overridden for that single run with a recognizable marker) → `send_status` poll until a terminal state (for succeeded / partially_succeeded, check each channel) → the user accepts in the group/mailbox
5. Deliver the triple: board name+dashboard_id, read-back comparison conclusion, jump link (`ae-cli config current --jq '.activeHost'` to read the domain dynamically, then concatenate `<activeHost>/#/panel/panel/<project_id>_<dashboard_id>` — use the standard access domain of the current deployment (the activeHost read-back value is that domain); if the read-back host is an intranet address, replace it with the standard access domain of the current deployment)

## Quick reference for common inputs

```bash
# Push to a WeCom group every day at 09:00 (example)
ae-cli capability run analysis.dashboard_daily_report.update --input '{
  "project_id": 2, "dashboard_id": <id>,
  "send_date": "", "send_time": "09:00",
  "enable_wx": true, "wx_url": ["https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."],
  "host_url": "https://<public-domain>", "zone_offset": 8, "enable_send": true
}'

# Email channel (example; login_users is the selector, email_new is an example address)
"enable_email": true, "email_login_users": "<login-name>", "email_new": "user@example.com"

# Send immediately + check status (send does not reuse saved destinations — for multiple channels, explicitly pass all destination fields, see "Trap 1")
ae-cli capability run analysis.dashboard_daily_report.send --input '{"project_id":2,"dashboard_id":<id>,"email_login_users":"...","wx_url":["https://qyapi.weixin.qq.com/..."],"send_title":"Verify"}'
ae-cli capability run analysis.dashboard_daily_report.send_status --input '{"project_id":2,"task_id":<tid>}'
```

> Test asset: empirical testing was done with an empty probe board (daily report config cleaned up and disabled) — when switching to another deployment, retest with an equivalent asset.
