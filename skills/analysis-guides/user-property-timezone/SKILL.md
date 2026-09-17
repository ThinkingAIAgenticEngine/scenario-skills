---
name: "user-property-timezone"
description: "Use when a time-valued user property must follow the selected analysis timezone. Diagnose datetime or Unix-timestamp sources and create a reusable virtual event property."
---

# User Property Timezone Handling Solution

## Background

In ThinkingEngine, user properties do not have a timezone field. When user properties store time-related data (registration time, last login time, etc.), they cannot dynamically adjust the timezone display based on the event's timezone as event properties do. This Skill analyzes the specific scenario and provides a targeted solution.

## Decision Matrix

Use this table to pick the right solution at a glance. Details for each solution and the diagnosis flow follow.

| Field type | Solution | Formula (see Step 4) |
|---|---|---|
| datetime + user local time with confirmed matching event offset | **Solution 1** | Direct mapping |
| datetime + timezone field reported | **Solution 2-A** | datetime + timezone field |
| datetime + fixed timezone reporting | **Solution 2-A** | datetime + fixed timezone |
| number (Unix timestamp) | **Solution 2-B** | Timestamp formula after unit and conversion-baseline checks |

> **Key rule for numeric timestamps:** A confirmed Unix timestamp needs no source-timezone question. Confirm seconds versus milliseconds and calibrate `from_unixtime` before choosing the formula.

## Overview of Solutions

### Solution 1: User Local Time → Direct Virtual Event Property Mapping

**Applicable conditions:** A **datetime type** user property stores client local time, and the confirmed reporting rule guarantees its source offset matches each relevant event's reporting offset. Check representative event offsets before direct mapping. If this rule cannot be confirmed, use a known source offset or stop.

**Only for datetime.**

---

### Solution 2: Timezone Conversion → Virtual Event Property with Timezone Adjustment

**Applicable conditions:** A time field already exists in user properties, but viewing requires timezone conversion.

- **Case A: datetime type** — apply offset directly on the datetime value. Requires knowing the timezone source (per-user offset field, or fixed timezone).
- **Case B: numeric Unix timestamp type** — confirm seconds or milliseconds, then use the calibrated timestamp formula. No source-timezone question is needed.

**Formula variables:**
- `#zone_offset`: the event's reported UTC offset, not the selected query timezone; confirm the field and representative values in the project
- `fixed_timezone`: the timezone offset value used during data reporting (datetime only)
- `("#zone_offset" - X) * 60`: difference in minutes between the event reporting offset and the source value's offset (datetime only)
- `("#zone_offset" - <conversion_offset>) * 3600`: for Unix timestamps, adjusts from the verified `from_unixtime` rendering offset to the event reporting offset; never assume a universal UTC+8 baseline

**Pros:** Dynamic conversion, no tracking change.

---

## Scenario Diagnosis and Recommendation Flow

### Step 1: Auto-Discovery of Metadata

**The agent MUST search metadata automatically before asking the user anything.**

```bash
ae-cli analysis-meta property list --project-id <Project_ID> --scope user
```

Use `ae-cli` for product data and asset operations. Use the available user-question tool for the `AskUserQuestion` prompts below.

**Identify:**
1. **Target time field candidates** matching the user's description (check both `prop_name` and `prop_desc`)
2. **Timezone-related fields** (only needed for datetime branch): names like `timezone_offset`, `timezone`, `utc_offset`, `tz_offset`, or fields with `is_zone_offset_prop: true`; confirm units, sign, and that the offset describes the time when the source value was recorded
3. **Data type** (`select_type`) of each candidate: `datetime` or `number`

> The data type determines the branch: `datetime` → Step 3-A; confirmed Unix-timestamp `number` → Step 3-B. Confirm the event offset field and representative values before using `#zone_offset`; stop if no valid event offset is available.

### Step 2: Confirm Target Field with User

- **No time field found** → Tell the user no time-related user property was found and stop. Do NOT propose alternatives.
- **Exactly one matching field** → Confirm briefly in text and proceed to Step 3-A or 3-B. Do NOT ask the user to pick.
- **Multiple candidate fields** → Use `AskUserQuestion`:
  ```
  AskUserQuestion({
    questions: [{
      question: "Which user property corresponds to 'XXX'?",
      header: "Target Field",
      options: [
        { label: "FIELD_A", description: "datetime type" },
        { label: "FIELD_B", description: "number type" },
        { label: "Other property", description: "Please specify the property name" }
      ]
    }]
  })
  ```

### Step 3-A: Diagnose datetime Type Fields

Present a single `AskUserQuestion` with three options:

```
AskUserQuestion({
  questions: [{
    question: "The 'XXX' field is datetime type. How should the timezone be determined?",
    header: "Timezone",
    options: [
      { label: "User local time", description: "Use direct mapping only if the source offset matches each event reporting offset" },
      { label: "Timezone field reported in user properties", description: "A timezone offset field has been reported, I'll select which one" },
      { label: "Reported in a fixed timezone", description: "All data is stored in a uniform timezone (e.g., server UTC+8) and needs conversion" }
    ]
  }]
})
```

**Routing:**
- **User local time** → Confirm the reporting rule guarantees the source offset matches each relevant event offset and sanity-check representative events; then use Solution 1. Otherwise obtain a reliable source offset or stop.
- **Timezone field reported** → Ask which field (see *Shared follow-up: pick timezone field* below) → Solution 2-A timezone-field formula.
- **Fixed timezone** → Ask which offset (see *Shared follow-up: pick fixed offset* below) → Solution 2-A fixed-timezone formula.

### Step 3-B: Diagnose number / timestamp Type Fields

Do not ask the user for a source timezone for a confirmed Unix timestamp. Confirm whether its unit is seconds or milliseconds. Calibrate `from_unixtime` with Unix second `1704067200` (= 2024-01-01 00:00:00 UTC):

```bash
ae-cli analysis adhoc run --project-id <Project_ID> --model-type sql --definition '{"sql":"SELECT from_unixtime(1704067200) AS rendered_time"}' --zone-offset 0 --preview-rows 1
ae-cli analysis adhoc run --project-id <Project_ID> --model-type sql --definition '{"sql":"SELECT from_unixtime(1704067200) AS rendered_time"}' --zone-offset 8 --preview-rows 1
```

The returned wall time minus 2024-01-01 00:00:00 UTC gives `<conversion_offset>` in hours. Continue only if both runs give the same unambiguous offset; otherwise stop instead of guessing `8`. Normalize milliseconds to seconds only when that unit is confirmed, then proceed to Step 4.

### Shared follow-up: pick timezone field (datetime only)

If Step 1 found timezone-related fields (e.g., `timezone_offset`, `user_offset`), present them as options; otherwise let the user type the field name:

```
AskUserQuestion({
  questions: [{
    question: "Which user property is the timezone offset field?",
    header: "Timezone Field",
    options: [
      { label: "FIELD_TZ_1", description: "number type" },
      { label: "FIELD_TZ_2", description: "number type" },
      { label: "Other", description: "Please specify the timezone field name" }
    ]
  }]
})
```

### Shared follow-up: pick fixed offset (datetime only)

```
AskUserQuestion({
  questions: [{
    question: "Which fixed timezone is the data reported in?",
    header: "Fixed Timezone",
    options: [
      { label: "UTC+8", description: "Beijing time / East 8, offset = 8" },
      { label: "UTC+0", description: "Coordinated Universal Time, offset = 0" },
      { label: "Other", description: "Please specify the timezone offset value" }
    ]
  }]
})
```

### Step 4: Create the Virtual Event Property

**Once the scenario and formula are determined, show the proposed virtual property name and SQL, obtain confirmation to create it, then execute the creation; do not stop at advice alone.**

**Formula mapping (authoritative source):**

| Scenario | Formula |
|----------|---------|
| datetime + user local time | `ta_u."field_name"` |
| datetime + timezone field | `date_add('minute', cast(("#zone_offset" - ta_u."timezone_field_name") * 60 as integer), ta_u."field_name")` |
| datetime + fixed timezone | `date_add('minute', cast(("#zone_offset" - fixed_timezone) * 60 as integer), ta_u."field_name")` |
| confirmed Unix timestamp | `from_unixtime(<epoch_seconds> + ("#zone_offset" - <conversion_offset>) * 3600)`; `<epoch_seconds>` is `ta_u."timestamp_field"` for seconds or `ta_u."timestamp_field" / 1000.0` for confirmed milliseconds |

> **SQL reference syntax:** Always reference user properties with the `ta_u."property_name"` prefix. Writing the property name alone will cause the system to parse it as an event property.

**Create command (ae-cli only):**

```bash
ae-cli analysis-meta virtual-property create \
  --project-id <Project_ID> \
  --property-name "#vp@<Virtual_Property_Name>" \
  --property-desc "<Description>" \
  --table-type event \
  --select-type datetime \
  --sql-expression '<Formula>' \
  --sql-event-relation-type relation_default
```

If creation reports an unresolved user-property dependency, use `--properties` with metadata-backed descriptors for **every** user property referenced by the chosen formula (including the source offset field in the timezone-field branch). Validate the exact dependent-property JSON against the current `ae-analysis` virtual-property create contract; do not assume the source field alone is sufficient.

### Step 5: Post-Creation Verification (MANDATORY)

Do NOT deliver the final answer right after `virtual-property create` returns success. Prove that the new property can be queried and produces the intended time values. Complete all checks below and proceed to the Response Template only when they pass.

**1. Data verification (proves persistence and compilability):** choose a confirmed event and a fixed absolute time window with matching users, then preview event details containing `#vp@<Virtual_Property_Name>`:

```bash
ae-cli analysis event-detail run \
  --project-id <Project_ID> \
  --definition '{"event":"<confirmed_event>","time_range":{"mode":"absolute","start_time":"<start>","end_time":"<end>"},"properties":["#event_time",{"name":"#vp@<Virtual_Property_Name>","type":"event_property"},{"name":"<source_prop>","type":"user_property"}]}' \
  --preview-rows 10
```

Use real event and property names from metadata. Pass criteria: a successful response, at least one matching row, and a non-null virtual property value. Resolve a metadata compile error before continuing; do not assume it proves the asset was not saved.

**2. Timezone behavior spot-check (proves formula correctness):** run the same definition twice with different fixed offsets:

```bash
ae-cli analysis event-detail run --project-id <Project_ID> --definition '<same event-detail definition>' --zone-offset 8 --preview-rows 10
ae-cli analysis event-detail run --project-id <Project_ID> --definition '<same event-detail definition>' --zone-offset 0 --preview-rows 10
```

Match the same identifiable event across both previews (use user ID, event time, and a unique event identifier when available); keep the absolute window wide enough for both offsets. Its virtual datetime must differ by exactly the selected offset difference (8 hours here), in the expected direction. Compare a value with an independently known source instant when available. If the records cannot be matched or the shift is wrong, return to Step 3/Step 4, fix the formula, and re-verify.

**3. User-side acceptance guidance:** in the final answer, tell the user how to self-check: after switching the analysis timezone in the product UI, the values of `#vp@<Virtual_Property_Name>` should shift accordingly (or land on the user's local time, depending on the chosen scenario).

**On failure:** never claim success when any check fails. Classify the error (SQL compile failure → fix the formula; property not resolved → re-create; wrong offset direction → fix the branch), apply the fix, then re-run this step. If temporary assets were created only for verification, delete them afterwards and inform the user.

## Response Template

1. **Scenario confirmation**: One-sentence summary (field name, data type)
2. **Action**: Create the virtual event property
3. **Rationale**: Briefly explain why virtual event properties solve the timezone issue (user properties lack a timezone field; virtual event properties inherit the event's timezone context)
4. **Usage guidance**: Return the created virtual property name, and tell the user which field to use for viewing data. If historical values lack a reliable source offset, say which values could not be converted accurately; do not claim that creating the property repairs them. **Render the final usage guidance as a Markdown blockquote** (using `> ` prefix). Example:

   > In subsequent analysis, please use `#vp@create_timestamp_tz` to view data, which will dynamically adjust time display based on the query timezone.

5. **Verification summary**: one line stating that the Step 5 post-creation checks passed (query returns data; the timezone shift between different `--zone-offset` runs matches the expected offset difference). If any check failed and was not recoverable, report the failure and its cause instead of the usage guidance.

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.
