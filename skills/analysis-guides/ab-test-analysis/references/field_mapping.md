# Field Mapping & Value-Domain Validation

Reference for **Step 0b (Field Alignment)** of `ab-test-analysis`.

A two-group A/B analysis needs exactly four fields to be right. Everything else — the z-test, the
confidence interval, the Bayesian posterior — is downstream of them, so a field mismatch produces a
confident, well-formatted, **wrong** conclusion. This document is the checklist that prevents that.

Related: SKILL.md → "字段核对与映射（Step 0b）"; `scripts/check_field_mapping.py` (the gate);
`references/ae_cli_query_patterns.md` (how the fields enter a query).

---

## 1. Required field inventory

| # | Role | Key in `field_mapping.json` | Required | Type | Why it matters |
|---|------|----------------------------|----------|------|----------------|
| 1 | Group / variant field | `variant_field` | YES | `event_property` \| `user_property` | Splits the population into the two arms. Wrong field → the "experiment" is actually a channel/city split |
| 2 | Group field type | `variant_field_type` | YES | enum | Decides `groups[].field.type` in the ae-cli query. Wrong → 1 group or empty `rows` |
| 3 | Control value | `control_value` | YES | string | Must be the *actual stored value*, not the word "control" |
| 4 | Treatment value | `treatment_value` | YES | string | Same; must differ from control |
| 5 | Exposure event | `exposure_event` | YES | event name | The denominator ("entered the experiment"). Usually the single biggest source of error |
| 6 | Success event(s) | `success_events` | YES (≥1) | event name list | The numerator |
| 7 | Guardrail event(s) | `guardrail_events` | optional | event name list | Metrics that must not regress |
| 8 | Excluded values | `excluded_values` | YES (may be `[]`) | string list | Dirty domain values that must not be counted as an arm |
| 9 | Observed domain | `observed_domain` | recommended | string list | What the field actually contains, **after** exclusions. Gate checks it equals the 2 mapped values |
| 10 | Observed counts | `observed_counts` | recommended | `{value: int}` | Per-arm user counts. Enables the sample-balance check |
| 11 | Alias resolution log | `field_aliases_resolved` | recommended | `{role: field}` | Makes the mapping auditable when the user disputes the conclusion |
| 12 | Project id | `project_id` | YES | int | Ties the mapping to one project — never reuse across projects |
| 13 | Cohort contract | `cohort` | **YES** | object | Declares that the numerator is restricted to the exposed cohort and that success came *after* exposure. See §5.1 |
| 14 | Metric declarations | `metrics` | recommended | object list | Declares how each tested metric is derived (proportion numerator column, or the per-user basis for a continuous metric). See §5.2 |

> **Never invent a field name.** Every name in this file must come from either the user or the
> project metadata. A guessed name does not error out; it returns empty data, which is then
> misread as "the experiment had no traffic".

---

## 2. Alias resolution

Users describe fields in business language ("分流字段", "曝光埋点", "the group column"). Resolve to a
candidate standard name **before** checking existence.

### 2.1 Group / variant field

| Alias | Notes |
|-------|-------|
| `ab_group`, `abtest_group`, `ab_test_group`, `$abtest_group` | Most common; TE/AE auto-instrumentation uses the `$`-prefixed form |
| `experiment_group`, `$experiment_group`, `experiment_variant`, `$experiment_variant` | Experiment-platform naming |
| `variant`, `variant_id`, `variation`, `version_group` | Common in third-party tooling |
| `group`, `group_id`, `bucket`, `bucket_id` | Generic; **high collision risk** (may be a user tier, not an experiment) |
| `test_group`, `traffic_group`, `strategy_group`, `policy_group` | Strategy/comparison framing |
| `分流`, `分组`, `实验组`, `对照组`, `版本` (as a *field name*) | Chinese field names do occur — match exactly, they are legal |

**Collision warning.** `group`, `bucket`, `version` frequently mean something else in the project
(membership tier, pay level, app version). If a candidate matches one of these generic names, ask the
user to confirm the semantic before using it — a pay-tier split will produce a beautiful, meaningful,
and completely irrelevant result.

### 2.2 Exposure event

| Alias | Notes |
|-------|-------|
| `experiment_exposure`, `exposure`, `$exposure`, `ab_exposure`, `abtest_exposure` | Correct shape — scoped to the experiment |
| `enter_experiment`, `join_experiment`, `experiment_start` | Also correct shape |
| `$app_start`, `app_launch`, `$pageview`, `session_start` | ⚠️ **Oversized denominator.** Counts users who never entered the experiment; inflates the denominator and shrinks the conversion rate for *both* arms |
| `page_view`, `page_enter` | Acceptable only if the exposure genuinely happened page-level; confirm with the user |

If no dedicated exposure event exists, the skill may fall back to using a success event's
`user_count` as the denominator proxy — but that must be **explicitly stated** in the report
("no dedicated exposure tracking, using success event as proxy"), never silently applied.

### 2.3 Success / guardrail events

| Role | Common event names |
|------|-------------------|
| Conversion / purchase | `purchase`, `payment_success`, `order_paid`, `recharge_success`, `pay_success` |
| Registration / activation | `signup`, `register`, `register_success`, `activate`, `onboarding_complete` |
| Engagement | `level_complete`, `stage_clear`, `task_finish`, `subscribe`, `follow` |
| Clicks | `button_click`, `banner_click`, `cta_click` — **must be scoped to the target element**, a generic click event counts every click on the page |
| Guardrail (harm) | `app_crash`, `crash`, `error`, `exception`, `payment_fail`, `refund`, `complaint`, `uninstall` |
| Guardrail (drop) | `app_start`, `session_start` (traffic), `dau`-style activity events |

Event names are **case- and delimiter-sensitive** in most trackers (`pay_success` ≠ `PaySuccess`).
Copy from metadata, never retype from the conversation.

### 2.4 Resolving the value labels

The stored group values are rarely `control` / `treatment`. Observed patterns:

| Stored form | Example | Mapping rule |
|-------------|---------|--------------|
| Words | `control` / `treatment`, `A` / `B`, `baseline` / `variant` | Map A-ish → control, B-ish → treatment |
| Numeric | `0` / `1`, `1` / `2` | Convention: the lower number is control when the user confirms; state it explicitly |
| Chinese | `对照组` / `实验组` | Direct map |
| Prefixed | `ab_control` / `ab_treatment`, `exp_A` / `exp_B` | Strip prefix, then map |
| Opaque ids | `1001` / `1002` | **Ask the user** which is control — never guess from ordering |

**Row order is never a mapping signal.** ae-cli does not guarantee row ordering; always read the
group column value out of `rows[i][1]`.

---

## 3. Value-domain validation rules

Rules 1–10 below are enforced by `scripts/check_field_mapping.py`. Rule 11 is checked after the query
by `scripts/validate_query_output.py`, and the query *shape* that makes them satisfiable is checked
before the query by `scripts/check_query_definition.py`.

| # | Rule | Severity | Rationale |
|---|------|----------|-----------|
| 1 | Exactly **2 valid groups** after exclusions | FATAL | This skill analyses two-group tests only (multi-arm → Boundary Statement §5) |
| 2 | Null-like values excluded: `""`, `null`, `NULL`, `undefined`, `-1`, `none`, `n/a`, `--` | FATAL if they remain in `observed_domain` | These are "never entered the experiment"; counting them as an arm dilutes the effect and biases both arms |
| 3 | Internal / test groups excluded: `test`, `inner`, `internal`, `debug`, `whitelist`, `白名单`, `内部`, `内部测试`, `灰度测试`, `压测`, `staff`, `qa` | ERROR if present | Internal traffic behaves differently and inflates one arm |
| 4 | `control_value ≠ treatment_value`, both non-empty | FATAL | Otherwise both arms are the same arm |
| 5 | Both mapped values ∈ `observed_domain` | FATAL | Prevents mapping to a value the field never takes (a typo looks exactly like this) |
| 6 | Sample balance: `min(n) / max(n) ≥ min_group_ratio` (default **0.20**) | ERROR (WARN if exactly at the ratio) | A 1:10 split is not a 1:1 experiment — either dirty values or a broken assignment |
| 7 | `exposure_event ∉ success_events`, `exposure_event ∉ guardrail_events` | WARN | Prevents an accidental self-comparison (conversion rate of 100% by construction) |
| 8 | `cohort.basis == "exposed_users_after_exposure"` | ERROR | The numerator must be exposed users who converted afterwards. Any other basis means the ratio is not a conversion rate |
| 9 | `cohort.order_enforced == true` | ERROR | Declares that the query enforces exposure-before-success (funnel step 1 = exposure). Without it a pre-exposure conversion sits in the numerator although the user was never treated |
| 10 | `cohort.exposure_event` agrees with `exposure_event`; denominator/numerator columns declared | ERROR / WARN | Stops the denominator from drifting away from the declared exposure event, and tells the query gate which returned column is the cohort |
| 11 | `success_users ≤ exposure_users` per arm (post-query) | ERROR | A conversion rate above 100% means the numerator was not restricted to exposed users |

**Continuous metrics carry two extra rules.** A `continuous` metric must declare
`"basis": "per_user_over_exposed_cohort"` and `"distribution": "user_level"` (ERROR otherwise).
Welch's t-test compares per-user means with a per-user variance, so `mean`, `std` and `n` must all come
from the same one-row-per-exposed-user dataset, including users who contributed 0. Event-model
`avg_per_user` is descriptive only; event-level `avg`/`stddev` is usually a payer-only distribution.

Numeric typing (part of rule 2's spirit, checked when counts are supplied):

- Count fields must be **non-negative integers**. `1.5` users, or a negative count, is a defect.
- Mean / rate fields must be **finite** (`NaN`, `Inf`, `-` are not zero — treating them as 0 silently
  pulls the mean toward zero).
- Placeholder strings (`-`, `--`, `N/A`, `null`) must be recounted as *missing*, not as 0. A missing
  cell coerced to 0 in the numerator is the most common silent bug in this pipeline.

---

## 4. Mismatch symptoms → diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Only 1 group returned | Wrong field name; or a `user_property` queried as `event_property`; or the field is only populated on one arm | Re-resolve aliases; flip `variant_field_type`; check the field's populating event |
| 3+ groups returned | Wrong field (channel / city / tier); or a genuine multi-arm experiment; or dirty values | Confirm the field's semantic; if multi-arm, use a multi-variant tool |
| Both arms nearly identical / effect exactly 0 | Field is populated but unrelated to the experiment (e.g. a constant user attribute) | Verify the field's *values* correlate with the experiment start date |
| Sample ratio severely off | Null-like values counted as an arm; internal test group inflating one arm; broken assignment | Apply rules 2–3 and re-query; if still off, report it as an experiment-configuration risk |
| Exposure ≫ experiment population | Used `$app_start`-style site-wide event as exposure | Switch to a real exposure event, or declare the proxy denominator explicitly |
| Conversion rate > 100% | Success event not scoped to exposed users | Add an exposure restriction to the success-event query (same user must expose *before* converting) |
| Treatment metrics look like the whole product | Filters not applied, or the group filter was dropped when copying the query | Compare the dispatched normalized `definition`; if compilation needs clarification, run the corrected definition once with `--dry-run` and inspect `meta.resolved` / `meta.errors[]` |
| Numbers changed between runs | `recent` includes today (data still landing); `previous` excludes it | Pin an explicit `custom` range; see the time-range mode table in `references/ae_cli_query_patterns.md` |
| Guardrail metric identical in both arms | Guardrail event not actually instrumented, or field missing on that event path | Verify raw counts before concluding "no regression" |
| ARPU far above the product's real ARPU | `avg`/`stddev` taken over the purchase event with `n = paying users` — the payers-only distribution, not the cohort | Supply a user-level distribution with one row per exposed user, including zeros (`--distribution user_level`); use `avg_per_user` only as a descriptive cross-check |
| `n` in the analysis input equals the paying-user count | Same as above; the cohort size was replaced by the numerator count | `n` must be the exposed-cohort size for every metric |
| Retention number does not match the platform report | `initial_event` written at definition level (ignored, so the cohort is everyone) or `stat_type`/`unit_num` left implicit | Move the fields into the nested `retention` object and declare `stat_type` + `unit_num` explicitly |
| Retention "rate" that is actually a user count | `rtn_rate_or_num` in a count form (`R1`/`number`/`count`) | Set it to `R0`/`rate` — a proportion test needs the rate |

---

## 5. Contract and gate

Write the mapping to `{workspace}/tmp/field_mapping.json`:

```json
{
  "project_id": "8888",
  "variant_field": "ab_group",
  "variant_field_type": "event_property",
  "control_value": "control",
  "treatment_value": "treatment",
  "exposure_event": "experiment_exposure",
  "success_events": ["purchase"],
  "guardrail_events": ["app_crash"],
  "excluded_values": ["", "null", "unknown", "test", "内部"],
  "observed_domain": ["control", "treatment"],
  "observed_counts": {"control": 10000, "treatment": 10000},
  "field_aliases_resolved": {
    "分组字段": "ab_group",
    "曝光事件": "experiment_exposure",
    "成功事件": "purchase"
  },
  "cohort": {
    "basis": "exposed_users_after_exposure",
    "exposure_event": "experiment_exposure",
    "order_enforced": true,
    "denominator_column": "曝光用户数",
    "numerator_columns": {"购买转化率": "付费用户数"}
  },
  "metrics": [
    {"name": "购买转化率", "type": "proportion", "numerator_column": "付费用户数"},
    {"name": "人均付费金额", "type": "continuous", "basis": "per_user_over_exposed_cohort",
     "distribution": "user_level"},
    {"name": "崩溃率", "type": "proportion", "is_guardrail": true, "lower_is_better": true,
     "numerator_column": "崩溃用户数"}
  ]
}
```

### 5.1 The `cohort` block

| Key | Required | Meaning |
|-----|----------|---------|
| `basis` | YES | Must be `exposed_users_after_exposure`. It is the statement that the numerator is a subset of the exposed cohort and converted afterwards |
| `order_enforced` | YES | `true` when the query enforces the ordering (funnel step 1 = exposure). `false` or absent is an ERROR |
| `exposure_event` | recommended | Repeated so the denominator cannot drift away from the declared exposure event |
| `denominator_column` | recommended | The exact column name the query returns for the cohort size. `validate_query_output.py` reads it to apply the `MIN_SAMPLE` floor to the denominator — without it the gate has to guess, and it refuses to guess when several columns look like user counts |
| `numerator_columns` | recommended | `{"<metric>": "<returned column>"}`, so the gate can check `numerator ≤ denominator` per row |

### 5.2 The `metrics` block

Declares how each tested metric is derived, which is what lets the gates check the numerator and the
distribution rather than trusting them:

| `type` | Required key | Enforced |
|--------|--------------|----------|
| `proportion` | `numerator_column` (recommended) | Query gate requires the funnel shape with the exposure event as step 1 |
| `continuous` | `basis` = `per_user_over_exposed_cohort`; `distribution` = `user_level` | ERROR unless both are explicit, because neither a payer-only distribution nor an aggregate `avg_per_user` can supply a valid exposed-user Welch input |

Run the gate:

```bash
python scripts/check_field_mapping.py {workspace}/tmp/field_mapping.json
```

- exit `0` → alignment passed, proceed to Step 1
- exit `1` → FATAL/ERROR; the JSON output lists every failed rule with a concrete remediation

Optional flags: `--min-group-ratio 0.2` (sample-balance threshold),
`--allow-extra-groups` (downgrade rule 1 from FATAL to WARN when the extra groups are known-benign
and will be filtered in the query — use sparingly and say so in the report).

The output also carries `resolved_mapping` (a copy of the confirmed mapping, including the `cohort`
and `metrics` blocks) — feed that into Step 1's query and Step 2's `group_field` / `control_name` /
`treatment_name` metadata so the same values are used on both ends. The same file is the second
argument of `validate_query_output.py`, which is how the post-query gate knows which column is the
exposed cohort.
