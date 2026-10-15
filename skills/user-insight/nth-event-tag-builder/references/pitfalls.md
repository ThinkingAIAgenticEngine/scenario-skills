# Pitfalls & Debugging

Errors the source doc《用户第几次触发xx事件》omits but that an Agent will hit in practice. Debug client reports against this page.

---

## Pitfall 1: guessing or copying an event-table name ⭐ most frequent

**Symptom**: SQL tag save fails with "table not found" or preview is empty.

**Cause**: the SQL used a guessed or copied table name instead of the exact server-authorized event-view `table_ref` for the current project and `tag_cluster` usage.

**Fix**:
1. Run `ae-cli analysis sql-table list -p <project_id> --usage tag_cluster` and select the event-view row.
2. Copy its exact `table_ref` into both `sql-table columns` and `FROM`; write the `id` column inline because event views have no `#vp@` columns.

**Never** hand the client SQL without confirming the table name first.

---

## Pitfall 2: wrong user ID

**Symptom**: counts don't line up per user, or most users show count=1.

**Cause**: didn't confirm which ID to count by; defaulted to `#account_id` but the project may have no account system (`#account_id` empty) or the client wants `#device_id` / `#user_id` / another property.

**Fix**:
- Offer common candidates and ask: "which ID to count by?" — `#account_id` (account) / `#user_id` (user) / `#device_id` (device) / `#distinct_id` (visitor), or let the client type their own (may be any event or user property, e.g. `role_id`, `openid`)
- Once decided, use the same ID in `id` concatenation, SELECT, and PARTITION (3 places)
- If `#account_id` is partially missing on some platforms → warn the client to check coverage, or switch to `#device_id` / `#distinct_id`

---

## Pitfall 3: event enumeration vs counting everything

`$part_event` is the pre-partition field (physical partition, fast filter) — **enumerate target events** (one or more), don't omit WHERE and count everything.

| Condition | Consequence |
|---|---|
| Forgot WHERE `$part_event` | counts all events, slow and mismatched to expectations |
| PARTITION missing `"#event_name"` | multiple events merged into one count, numbering corrupted |

**Fix**:
- Ask the client which event(s) to count
- Standard form: `$part_event in ('a','b')` + `partition by "<userID>","#event_name"` (double grouping, per-event independent numbering)
- Only for the special "merge several events into one count" need, drop `"#event_name"` from PARTITION

---

## Pitfall 4: ascending/descending swapped

| Scenario | Ordering | rnk/rowid=1 is |
|---|---|---|
| Scenario 1 (Nth, since launch) | `asc` | **first occurrence** |
| Scenario 2 (Recent N, last x days) | `desc` | **most recent** |

**Symptom**: filtering "=3" returns obviously wrong behavior (treats the 3rd-from-last as the 3rd).

**Debug**: preview the tag data and check whether the rnk/rowid=1 row is the expected occurrence.

---

## Pitfall 5: lifecycle-days property missing

**Symptom**: Scenario 1 can't find the attribute when grouping by "lifecycle".

**Cause**: "lifecycle days" is a **separate virtual property** (event time − acquisition time), not part of this skill's 4 steps.

**Fix**: guide the client to create the lifecycle-days virtual property first (Feishu doc《常用虚拟属性语句》 docx: doccnAxOTzPagbLayBezN1qkg2d), then come back to group by it.

---

## Pitfall 6: tag refresh policy unclear

| Scenario | Time policy | Client expectation |
|---|---|---|
| Scenario 1 (Nth) | static (since launch) | "Nth" only grows — the 3rd stays the 3rd; but new 4th/5th occurrences keep accumulating |
| Scenario 2 (Recent N) | dynamic (last x days) | "recent N" rolls daily — the last-30-games average you see today may differ tomorrow |

**Symptom**: client sees "last-30-games average" change the next day and thinks data is wrong.

**Fix**: state the refresh policy up front, and write it into the tag remark.

---

## Pitfall 7: timezone unconfirmed

**Symptom**: client reads "last 30 days" in Beijing time but the sliced boundary is off by hours/a day; or `user-tag get` shows `cluster_zone_offset=99`.

**Cause**: the window (`recent_day`, `start_time`) day-slicing depends on timezone. Without specifying one, `cluster_zone_offset` falls to `99` (unbound sentinel) and slices by raw `#event_time`, not aligned to the project default natural day. **Also**: an Agent that silently adopts `default_time_zone_offset` without asking has assumed — not confirmed — the timezone. The default is only a suggestion, not the client's choice.

**Fix**:
1. Check project timezone first: `ae-cli project timezone get -p <project_id>` → note BOTH `default_time_zone_offset` (e.g. 8 = UTC+8) AND `available_time_zones` (the list the project actually allows, e.g. `[-12, -7, -2, 0, 5, 6, 8, 12]`)
2. **List `available_time_zones` to the user and ask which offset to slice by.** Do NOT default silently — a cross-timezone business may need a different offset, and the wrong one shifts the day-slice boundary (counts land on the wrong "day"). **Enumerate every value in `available_time_zones` as its own option** (e.g. `[-12, 8, 0, 5, 6, 12, -2, -7]` → `UTC-12 / UTC+8 / UTC+0 / UTC+5 / UTC+6 / UTC+12 / UTC-2 / UTC-7`), each labeled `UTC±n` (or the equivalent named zone). **Do NOT collapse to a "+8 / other" binary choice and do NOT add an "other" catch-all** — that forces the user to re-type a value you already retrieved, which is exactly the friction this step exists to remove. Mark `default_time_zone_offset` with a "(project default)" tag instead of auto-selecting it.
3. Specify timezone at creation:
   - ae-cli: `--zone-offset 8` (or the relevant offset)
   - definition params: `use_timezone: true` (with SQL using the `#zone_offset` column)
4. If already built with the wrong timezone, `user-tag update` to fix and recompute

**Note**: `timezone: 99` is the "unspecified" special entry in the project timezone list (`default:false`). It is not a real timezone — seeing `cluster_zone_offset=99` means the tag has no timezone bound.

---

## Pitfall 8: didn't check for an existing entity before building

**Symptom**: duplicated a pile of functionally identical virtual properties/entities, cluttering project metadata.

**Cause**: didn't check whether a "userID + event name + event time" concatenation entity already exists.

**Fix**:
- Before Step 1, `ae-cli project entity list -p <project_id>` to look for a "user+event+time" entity bound to a concatenation virtual property (`#vp@xxx`)
- Usable entity exists → skip Step 1+2, take its `entity_id` to Step 3
- Only a "account+event time" legacy entity (missing the event-name dimension) is NOT reusable — build the full triple

**What counts as usable**: the entity must contain all three dimensions — user ID + event name + event time. In practice, project 2 had several legacy entities (`#vp@event_time_111` "account+event time", `#vp@id_time` "account ID + event time concat", etc.), all two-part "account+event time" missing `#event_name`, so none could be reused and a fresh triple entity (entity_id 87073) had to be built.

---

## Pitfall 9: "自某日至今" must use `recent_day: "<date> 00:00:00@@0"` — NOT `end_time: "today"` or a far-future end

**Symptom**: `user-tag create/update` returns `CAPABILITY_EXECUTION_FAILED` when using `end_time: "today"` (or `start_time` alone). It passes `--validate` but the backend rejects it at execution.

**Cause**: the SQL-tag `params` item for `type=part_date` has no `start_to_today`/`today` field. "自某日至今" is expressed by the anchored `recent_day` encoding, which the UI persists as `"<date> 00:00:00@@0"` (e.g. `"2026/09/10 00:00:00@@0"`). `@@0` = includes today (end rolls daily), `@@1` = up to yesterday.

**Fix**:
- **Scenario 1 (cumulative since launch)**: `recent_day: "<launch_date> 00:00:00@@0"` (date uses `/` separators, e.g. `"2022/01/01 00:00:00@@0"`). Fixed start + dynamic end. **Ask the user for the exact start date** — do NOT infer it from the project's earliest data or hardcode an arbitrary date; a wrong start silently truncates the cumulative count.
- **Scenario 2 (recent N)**: `recent_day: "0-30"` (last 30 days incl. today) or `"1-30"` (past 30 days excl. today).
- **Do NOT** use `end_time: "today"` (rejected) or `end_time: "2099-12-31"` (static end that never rolls — silently wrong for "至今").
- Verify the persisted form with `user-tag get`; a correct anchored tag shows `recent_day: "<date> 00:00:00@@0"` and `def_contain_today: true`.

---

## Pitfall 10: `concat` fails on numeric user ID (bigint)

**Symptom**: `user-tag create` fails with `Unexpected parameters (bigint, varchar) for function concat. Expected: concat(varchar)`.

**Cause**: `#user_id` (and some other ID columns) is `bigint`. Trino's `concat`/`||` does not auto-coerce `bigint` + `varchar`, so `"#user_id"||"#event_name"||cast("#event_time" as varchar)` blows up at analysis time.

**This hits in TWO places, and one is silent**:
1. **Step-3 tag SQL** — fails loudly at `user-tag create`.
2. **Step-1 virtual property SQL** — the create call returns `ok: true` immediately, but the backend validates the property's type **asynchronously** (`VirtualSqlPropService.getTypeOfSqlRule`); the raw `bigint` breaks later, and the entity/tag bound to it then fails with a generic `CAPABILITY_EXECUTION_FAILED`. This is the sneakier of the two.

**Fix**: wrap the ID in an explicit cast in the `id`/concatenation column of **both** SQL expressions:
```sql
cast("<userID>" as varchar)||"#event_name"||cast("#event_time" as varchar)
```
`PARTITION BY` keeps the raw `<userID>` (casting there is harmless but unnecessary). Confirm the ID column type via `ae-cli analysis sql-table columns -p <project_id> --table-ref '<event_table_ref>' --usage tag_cluster`, where `<event_table_ref>` is copied from `sql-table list`.

---

## Pitfall 11: existing entity uses a different ID caliber

**Symptom**: tag built on a reused entity returns wrong counts (users split or merged incorrectly).

**Cause**: found a "user+event+time" entity and reused it without checking which ID it was built on. An entity built on `#user_id` cannot serve a `#distinct_id` request (and vice versa).

**Fix**:
- Before reusing, verify the bound virtual property's ID caliber: `ae-cli analysis-meta property get -p <project_id> --table-type event --prop-name '<column_name>'` → read `vir_prop_column_rule`
- If the existing entity's ID differs from the requested ID, do NOT reuse it — build a fresh property + entity for the requested ID
- In practice, entity 87074 was built on `#user_id`; a `#distinct_id` request needed a fresh property+entity, not reuse

---

## Debug flow (when the client says "the numbers are wrong")

```
1. Event `table_ref` copied exactly from `sql-table list --usage tag_cluster`? (Pitfall 1)
2. User ID correct? (Pitfall 2) → switch to the confirmed ID
3. Scenario correct? (Nth vs recent N)
4. Ordering correct? (Pitfall 4) → preview tag, verify rnk/rowid=1
5. Event enumeration correct? (Pitfall 3, missing $part_event?)
6. Time policy correct? (Pitfall 6, static vs dynamic)
7. Timezone correct? (Pitfall 7) → cluster_zone_offset=99 means unbound, re-specify --zone-offset
8. Create failed on concat? (Pitfall 10) → cast "<userID>" as varchar in id column
9. Time param wrong? (Pitfall 9) → "自某日至今"用 `recent_day:"<date> 00:00:00@@0"`，别用 `today` 或远日期
```

Check in order; the first 2 pitfalls account for 80% of issues.
