# SQL Patterns and Extraction Contracts

This file is the executable SQL specification. Do not shorten documented templates to “same structure” during maintenance.

## Filter placeholder contract

Two placeholders may appear in templates:

- `<<COHORT_FILTER>>`
- `<<OUTCOME_FILTER>>`

### Injection rules

1. **Omit-when-empty**: if the corresponding filter is absent, remove the entire placeholder line. Do not leave `AND`, `TRUE`, comments, or empty parentheses behind.
2. **Cohort-side aliasing**:
   - inside a cohort-event table scan with no alias, render `AND "<property>" <op> <value>`;
   - if the template explicitly aliases the cohort table, use that alias exactly.
3. **Outcome-side aliasing**:
   - in `logs` CTEs where the event table is unaliased, render `AND "<property>" <op> <value>`;
   - in outcome JOINs aliased as `e`, render `AND e."<property>" <op> <value>`;
   - in outcome JOINs aliased as `l`, render `AND l."<property>" <op> <value>`.
4. Apply `cohort_filter` **before** `min("$part_date")` whenever “first qualifying event” is the cohort definition.
5. `cohort_filter` and `outcome_filter` are independent. Never copy one to the other unless the business meaning explicitly requires it.
6. Quote SQL identifiers; SQL-escape string values. Never splice untrusted raw SQL supplied as a property value.

### Operator rendering

Supported structured operators should be rendered as follows:

- `=` / `!=` / `<` / `<=` / `>` / `>=`: scalar comparison
- `IN`: parenthesized escaped scalar list; reject empty lists
- `LIKE`: escaped string pattern
- `IS NULL` / `IS NOT NULL`: no value operand

If the requested operator cannot be represented safely from structured filter data, stop and ask for a supported structured condition rather than injecting raw SQL.

## Template-selection invariants

- `first_occurrence` → global first qualifying cohort event.
- `period_active` → first qualifying cohort event **within each period**; return A/B overlap.
- `paired` → matched users present in both periods; retain separate A/B cohort dates and return McNemar a/b/c/d.
- `exact_day` and `within_window` must be consistent across headline counts, paired rerun and trend extraction.
- Outcome windows are cohort-relative, not simply period-end + N.

#### Step 2a — Get aggregate counts and per-day trend

##### 2a-1. Retention scenario with one-time cohort event — use retention ad-hoc

For the `retention` scenario with a **one-time** cohort event (e.g., `register`, `first_order`), the retention ad-hoc model is the cleanest source for the per-day trend chart. One-time events have a single global first occurrence, so `first_occurrence` and `period_active` give identical results (overlap is structurally 0). The `paired` design is **not applicable** here — paired requires users active in both periods, but a user's only occurrence of a one-time event cannot fall in two disjoint windows, so `paired_n` would be 0 and Step 3 would reject. Use `first_occurrence` (conventional) or `period_active` for one-time events; do not select `paired`.

For `retention` with a **recurring** cohort event (e.g., `login`) under `period_active` or `paired` design, the retention ad-hoc model computes **first-ever-login retention**, which does NOT match the per-period-active or paired headline rate. Use the **Step 2a-2 SQL path** with the appropriate design variant instead.

Read `ae-analysis/references/ai_models.md` and `ae-analysis/references/adhoc_run.md` before composing the definition. Use AI-facing snake_case only; never pass raw QP.

```bash
cat > /tmp/vrs_rate_<GROUP>.json <<'EOF'
{
  "time_range": {"mode":"custom","start_time":"<START>","end_time":"<END>"},
  "time_particle_size": "day",
  "retention": {
    "initial_event":"<cohort_event>",
    "return_event":"<outcome_event>",
    "unit_num": <N>,
    "stat_type":"retention",
    "rtn_rate_or_num":"num"
  }
}
EOF

ae-cli analysis adhoc run \
  --project-id <project_id> \
  --model-type retention \
  --definition "$(cat /tmp/vrs_rate_<GROUP>.json)" \
  --preview-rows 100
```

Run twice — once for group A's time range, once for group B's. Pass `--zone-offset <hours>` only when the user explicitly specifies a timezone; otherwise **omit it** to use the project's analysis default. Never hardcode `UTC+8`.

> **Parsing the retention ad-hoc response.** The response is a list of rows keyed by cohort date (`$part_date` of the cohort event). Each row carries `initial_users` (the cohort size for that date) and a day-N retained count whose field name is model-version-dependent — look for one of `retained_users`, `retention_num`, `retention_count`, or `rtn_num`. Do **not** assume a single fixed key; iterate the response rows and take whichever of those keys is present and non-null as the retained count for that cohort date. Sum `initial_users` across A's rows → `n_A`; sum the retained counts across A's rows → `r_A`. Repeat for B. For the per-day trend chart (Step 6), use `cohort_date` × `initial_users` (cohort bars) and `cohort_date` × retained count (outcome line). If the response is empty or missing these fields, fall back to the Step 2a-2 SQL path — the retention ad-hoc model is optional, not load-bearing.

##### 2a-2. Other scenarios — use SQL for per-day trend

For `repurchase` / `conversion` / `renewal` / `churn` / `custom` scenarios (and optionally for `retention`), use SQL to fetch per-day cohort counts and outcome counts directly. Confirm the event table name via `ae-cli analysis sql-table list --project-id <project_id>`; the standard event table is `hive.ta.v_event_<project_id>`. SQL identifiers `#user_id`, `$part_event`, `$part_date` must be double-quoted.

> **Timezone boundary note.** `"$part_date"` is a **pre-materialized project-local date** column (analysis timezone already baked in at ingestion time). The cohort range `BETWEEN '<A_START>' AND '<A_END>'` is therefore sliced in the project's analysis timezone. Passing `--zone-offset` to the ad-hoc run does **not** re-slice `$part_date` retroactively — it only affects how the platform computes the partition key for new event-time-to-partition mapping, which is irrelevant to a SQL query filtering on the already-stored column. If the user genuinely needs UTC slicing (rare), they must filter on the raw event-time column (e.g. `"$part_date"` is not the right column — use `event_time`/`#event_time` or the equivalent raw timestamp column) and accept that historical partitions are already materialized in project-local dates. For the common case, just rely on the project default and do not pass `--zone-offset`. Never mix timezones within the same run.

Pick the outcome-date semantics to match Step 2b-1 Template 2A (exact-day for `retention` with project exact-day definition, within-window for `repurchase / conversion / churn / renewal / custom` and for `retention` with cumulative-window definition). The paired path uses the same scenario-driven rule — see Step 2b-paired. The exact-day variant is shown; swap the `outcome_by_day` join predicate to `l."$part_date" > c.cohort_date AND l."$part_date" <= date_add('day', <N>, date(c.cohort_date))` for the within-window variant.

**Cohort-date definition depends on design.** The SQL below uses `first_occurrence` semantics (global `min("$part_date")` per user). For `period_active` and `paired` designs with a recurring cohort event, the cohort date must be the **per-period** first occurrence, not the global first — otherwise the trend chart will not match the headline rate. Design variants are listed after the SQL.

```sql
-- first_occurrence variant — spans A and B in one query
WITH user_first_cohort AS (
  SELECT "#user_id", min("$part_date") AS cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
  GROUP BY "#user_id"
),
cohort_by_day AS (
  SELECT cohort_date, count(*) AS cohort_count
  FROM user_first_cohort
  WHERE cohort_date BETWEEN '<A_START>' AND '<B_END>'
  GROUP BY cohort_date
),
outcome_by_day AS (
  SELECT c.cohort_date AS cohort_date,
         count(DISTINCT case when l."#user_id" is not null then c."#user_id" end) AS outcome_count
  FROM user_first_cohort c
  LEFT JOIN hive.ta.v_event_<project_id> l
    ON l."#user_id" = c."#user_id"
    AND l."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: append `AND l."<prop>" <op> <value>` when Step 1 `outcome_filter` is set; omit entirely when not set. Note the `l.` alias prefix on the outcome join.
    AND l."$part_date" = date_format(date_add('day', <N>, date(c.cohort_date)), '%Y-%m-%d')
  WHERE c.cohort_date BETWEEN '<A_START>' AND '<B_END>'
  GROUP BY c.cohort_date
)
SELECT c.cohort_date, c.cohort_count, coalesce(o.outcome_count, 0) AS outcome_count
FROM cohort_by_day c
LEFT JOIN outcome_by_day o ON o.cohort_date = c.cohort_date
ORDER BY c.cohort_date
```

> The `first_occurrence` CTE computes the global first cohort date per user. The `outcome_by_day` CTE groups by `c.cohort_date` (the cohort date, not `target_date`), so each row in the final result aligns the cohort count for day X with the outcome count for users whose cohort date was X.

**period_active variant** — the cohort date is the per-period first occurrence, so the trend SQL must be run **separately for group A and group B**. Replace the `user_first_cohort` CTE definition with `period_A_active` (for group A) or `period_B_active` (for group B), and update the two `FROM user_first_cohort c` references in `cohort_by_day` and `outcome_by_day` to `FROM period_A_active c` (or `period_B_active c`). The column alias remains `cohort_date`, so the rest of the SQL is unchanged.

```sql
-- For group A trend:
period_A_active AS (
  SELECT "#user_id", min("$part_date") AS cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
    AND "$part_date" BETWEEN '<A_START>' AND '<A_END>'
  GROUP BY "#user_id"
)
-- (run again for group B with B_START/B_END; combine the two outputs in the report chart)
```

**paired variant** — same per-period CTEs as `period_active`, but only users present in **both** `period_A_active` and `period_B_active` are kept (INNER JOIN on `#user_id`). Use group A's per-period cohort_date for the A-side trend and group B's for the B-side trend.

Aggregate per-day counts into group A and group B totals for the report's Part 1. **Match the trend chart's semantics to the headline rate's semantics** — if you used Template 2A-window for the test, use the within-window variant here too, otherwise the chart and the Part 1 numbers will disagree.

#### Step 2b — User-level data (depends on cohort design)

##### Step 2b-1 — first_occurrence design (SQL mode, recommended)

Use the SQL ad-hoc model to compute `n_A`, `n_B`, and `overlap_count` in a single query. Under the first-occurrence cohort design, `overlap_count` will always be 0 — see Step 4 structural note for why and what to do about it.

**Template 1 — n_A / n_B / overlap:**

```sql
WITH user_first_cohort AS (
  SELECT "#user_id", min("$part_date") AS cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
  GROUP BY "#user_id"
), flagged AS (
  SELECT "#user_id",
    case when cohort_date BETWEEN '<A_START>' AND '<A_END>' then 1 else 0 end as in_A,
    case when cohort_date BETWEEN '<B_START>' AND '<B_END>' then 1 else 0 end as in_B
  FROM user_first_cohort
)
SELECT
  count(case when in_A=1 then 1 end) AS n_A,
  count(case when in_B=1 then 1 end) AS n_B,
  count(case when in_A=1 and in_B=1 then 1 end) AS overlap
FROM flagged
```

Run via `ae-cli analysis adhoc run --project-id <project_id> --model-type sql --definition '{"sql":"<SQL>"}'`. Compute `overlap_rate = overlap / min(n_A, n_B)`.

> **Overlap is structurally 0 under the first-occurrence cohort design.** Because `user_first_cohort` keys on `min("$part_date")`, every user has exactly one cohort_date, and a user's cohort_date cannot fall in both A and B (assuming A and B are disjoint). The Template 1 query is therefore guaranteed to return `overlap = 0` for the first_occurrence design. You may still run Template 1 as a sanity check (it also confirms n_A/n_B), or you may skip straight to Template 2A.
>
> This is **not** true for the `paired` design (Step 2b-paired) — paired design explicitly includes only users in both periods, so overlap is structurally high.

**Template 2A — per-group outcome counts (first_occurrence, independent samples):**

Pick the outcome-date semantics based on the scenario:

- **Exact-day semantics** (`outcome_date = cohort_date + N`): use for **retention** when the project defines day-N retention as exact-day — the business question is "did the user come back on exactly day N". Most retention models count returnees on the precise Nth day.
- **Within-window semantics** (`cohort_date < outcome_date ≤ cohort_date + N`): use for **repurchase / conversion / churn / renewal / custom**, and for **retention** when the project defines day-N retention as cumulative-window. The business question is "did the user perform the outcome action at least once within N days after the cohort event". Exclude `outcome_date = cohort_date` itself for non-retention scenarios, because the cohort event on the same day is usually the same action that triggered cohort entry, not an independent repeat.
- **Same rule for all three cohort designs.** The `first_occurrence`, `period_active`, and `paired` paths use the same scenario-driven window rule. The paired path does NOT hardcode within-window — it inherits the project's retention definition so all three designs test the same quantity and remain comparable.

**Template 2A-exact (exact-day, retention first_occurrence default):**

```sql
WITH user_first_cohort AS (
  SELECT "#user_id", min("$part_date") AS cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
  GROUP BY "#user_id"
), regs AS (
  SELECT "#user_id", cohort_date
  FROM user_first_cohort
  WHERE cohort_date BETWEEN '<A_START>' AND '<B_END>'
), logs AS (
  SELECT DISTINCT "#user_id", "$part_date" AS outcome_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<outcome_event>'
  -- <<OUTCOME_FILTER>> optional: append `AND "<prop>" <op> <value>` when Step 1 `outcome_filter` is set; omit entirely when not set
    AND "$part_date" BETWEEN '<A_START>' AND '<B_END + N days>'
)
SELECT
  count(DISTINCT case when r.cohort_date BETWEEN '<A_START>' AND '<A_END>' then r."#user_id" end) AS n_A,
  count(DISTINCT case when r.cohort_date BETWEEN '<B_START>' AND '<B_END>' then r."#user_id" end) AS n_B,
  count(DISTINCT case when r.cohort_date BETWEEN '<A_START>' AND '<A_END>'
      AND l.outcome_date = date_format(date_add('day', <N>, date(r.cohort_date)), '%Y-%m-%d')
      then r."#user_id" end) AS outcome_A,
  count(DISTINCT case when r.cohort_date BETWEEN '<B_START>' AND '<B_END>'
      AND l.outcome_date = date_format(date_add('day', <N>, date(r.cohort_date)), '%Y-%m-%d')
      then r."#user_id" end) AS outcome_B
FROM regs r
LEFT JOIN logs l ON r."#user_id" = l."#user_id"
```

**Template 2A-window (within-window, default for repurchase / conversion / churn / renewal / custom):**

```sql
WITH user_first_cohort AS (
  SELECT "#user_id", min("$part_date") AS cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
  GROUP BY "#user_id"
), regs AS (
  SELECT "#user_id", cohort_date
  FROM user_first_cohort
  WHERE cohort_date BETWEEN '<A_START>' AND '<B_END>'
), logs AS (
  SELECT DISTINCT "#user_id", "$part_date" AS outcome_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<outcome_event>'
  -- <<OUTCOME_FILTER>> optional: append `AND "<prop>" <op> <value>` when Step 1 `outcome_filter` is set; omit entirely when not set
    AND "$part_date" BETWEEN '<A_START>' AND '<B_END + N days>'
)
SELECT
  count(DISTINCT case when r.cohort_date BETWEEN '<A_START>' AND '<A_END>' then r."#user_id" end) AS n_A,
  count(DISTINCT case when r.cohort_date BETWEEN '<B_START>' AND '<B_END>' then r."#user_id" end) AS n_B,
  count(DISTINCT case when r.cohort_date BETWEEN '<A_START>' AND '<A_END>'
      AND l.outcome_date > r.cohort_date
      AND l.outcome_date <= date_format(date_add('day', <N>, date(r.cohort_date)), '%Y-%m-%d')
      then r."#user_id" end) AS outcome_A,
  count(DISTINCT case when r.cohort_date BETWEEN '<B_START>' AND '<B_END>'
      AND l.outcome_date > r.cohort_date
      AND l.outcome_date <= date_format(date_add('day', <N>, date(r.cohort_date)), '%Y-%m-%d')
      then r."#user_id" end) AS outcome_B
FROM regs r
LEFT JOIN logs l ON r."#user_id" = l."#user_id"
```

> **Note on the cohort event for repurchase / renewal first_occurrence.** When the cohort event and outcome event are the same action type (e.g., repurchase scenario with cohort = `first_order`, outcome = `purchase`; or renewal scenario with cohort = `subscribe`, outcome = `renew` when the project tracks renewal as a second `subscribe` event), the `user_first_cohort` CTE keyed on `min("$part_date")` already isolates the *first* occurrence as cohort_date. The within-window predicate `l.outcome_date > r.cohort_date` then naturally excludes that same first occurrence, so any later `purchase` (or `renew`/second `subscribe`) within N days counts as the outcome. No extra filter is needed.

**Choosing the variant at runtime:** check the scenario preset and the project's retention definition. For `retention` with exact-day definition → 2A-exact (or 2B-paired-exact for paired, or 2C-period-active-exact for period_active). For `repurchase / conversion / churn / renewal / custom` → 2A-window by default (or 2B-paired-window / 2C-period-active-window for the other designs). For `retention` with cumulative-window definition → 2A-window (or the equivalent window variant for the other designs). **The cohort design does not change the window rule** — first_occurrence, period_active, and paired all use the same scenario-driven choice. If the choice is ambiguous, run both variants in the same SQL (add a second pair of `count(DISTINCT CASE WHEN ...)` columns with the other predicate) and compare; if the rates differ materially, surface both to the user and ask which matches the team's definition before testing.

**SQL mode failure triggers:** if the SQL capability is not found, the table name is unknown after `sql-table list`, or the query returns `PARAMETER_ERROR` / `QUERY_FAILED`, fall through to Step 2b-3 (aggregate-rate mode) for all designs. For paired design with SQL failure, aggregate-rate mode cannot produce McNemar cells (no user-level data) — inform the user that paired McNemar is not possible and suggest CSV upload. For period_active with SQL failure, aggregate-rate mode is fine for the independent Z-test, just loses the overlap diagnostic.

##### Step 2b-period_active — period_active design (SQL mode, computes n/outcome/overlap)

When `cohort_design = "period_active"`, use this template to compute per-group cohort counts, outcome counts, and the cross-period overlap in a single SQL query. The structure is similar to 2B-paired but WITHOUT the INNER JOIN — A-period and B-period samples are kept separate so the independent Z-test can use them directly.

**Key design choice: per-period first occurrence (not global first).** Each user's per-period cohort date is the user's **first** occurrence of the cohort event **within that period** (per-user, per-period `min("$part_date")`). This is what makes period_active differ from first_occurrence: a user whose global first occurrence was in June but who visited again in period A still gets an A-period cohort date.

**Template 2C-period-active-window (within-window, default for repurchase / conversion / churn / renewal / custom; also for retention with cumulative-window definition):**

```sql
WITH period_A_active AS (
  -- Users who performed the cohort event at least once in period A (per-user first occurrence in A)
  SELECT "#user_id", min("$part_date") AS a_cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
    AND "$part_date" BETWEEN '<A_START>' AND '<A_END>'
  GROUP BY "#user_id"
),
period_B_active AS (
  -- Users who performed the cohort event at least once in period B (per-user first occurrence in B)
  SELECT "#user_id", min("$part_date") AS b_cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
    AND "$part_date" BETWEEN '<B_START>' AND '<B_END>'
  GROUP BY "#user_id"
),
outcome_A AS (
  -- Whether each A-period user performed the outcome within N days after their A-period cohort date
  SELECT DISTINCT pa."#user_id", 1 AS flag_A
  FROM period_A_active pa
  JOIN hive.ta.v_event_<project_id> e
    ON e."#user_id" = pa."#user_id"
    AND e."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: append `AND e."<prop>" <op> <value>` when Step 1 `outcome_filter` is set; omit entirely when not set. Note the `e.` alias prefix on the outcome join.
    AND e."$part_date" > pa.a_cohort_date
    AND e."$part_date" <= date_format(date_add('day', <N>, date(pa.a_cohort_date)), '%Y-%m-%d')
),
outcome_B AS (
  SELECT DISTINCT pb."#user_id", 1 AS flag_B
  FROM period_B_active pb
  JOIN hive.ta.v_event_<project_id> e
    ON e."#user_id" = pb."#user_id"
    AND e."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: append `AND e."<prop>" <op> <value>` when Step 1 `outcome_filter` is set; omit entirely when not set. Note the `e.` alias prefix on the outcome join.
    AND e."$part_date" > pb.b_cohort_date
    AND e."$part_date" <= date_format(date_add('day', <N>, date(pb.b_cohort_date)), '%Y-%m-%d')
)
SELECT
  (SELECT count(*) FROM period_A_active) AS n_A,
  (SELECT count(*) FROM period_B_active) AS n_B,
  (SELECT count(*) FROM outcome_A) AS outcome_A_count,
  (SELECT count(*) FROM outcome_B) AS outcome_B_count,
  -- Overlap diagnostic: users active in BOTH periods (these are the same users counted in both groups)
  (SELECT count(*) FROM period_A_active pa
   INNER JOIN period_B_active pb ON pa."#user_id" = pb."#user_id") AS overlap
```

**Template 2C-period-active-exact (exact-day, for retention with project exact-day definition):**

```sql
WITH period_A_active AS (
  SELECT "#user_id", min("$part_date") AS a_cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: render `AND "<prop>" <op> <value>` here; omit this line when empty
    AND "$part_date" BETWEEN '<A_START>' AND '<A_END>'
  GROUP BY "#user_id"
),
period_B_active AS (
  SELECT "#user_id", min("$part_date") AS b_cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: render `AND "<prop>" <op> <value>` here; omit this line when empty
    AND "$part_date" BETWEEN '<B_START>' AND '<B_END>'
  GROUP BY "#user_id"
),
outcome_A AS (
  SELECT DISTINCT pa."#user_id", 1 AS flag_A
  FROM period_A_active pa
  JOIN hive.ta.v_event_<project_id> e
    ON e."#user_id" = pa."#user_id"
    AND e."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: render `AND e."<prop>" <op> <value>` here; omit this line when empty
    AND e."$part_date" = date_format(date_add('day', <N>, date(pa.a_cohort_date)), '%Y-%m-%d')
),
outcome_B AS (
  SELECT DISTINCT pb."#user_id", 1 AS flag_B
  FROM period_B_active pb
  JOIN hive.ta.v_event_<project_id> e
    ON e."#user_id" = pb."#user_id"
    AND e."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: render `AND e."<prop>" <op> <value>` here; omit this line when empty
    AND e."$part_date" = date_format(date_add('day', <N>, date(pb.b_cohort_date)), '%Y-%m-%d')
)
SELECT
  (SELECT count(*) FROM period_A_active) AS n_A,
  (SELECT count(*) FROM period_B_active) AS n_B,
  (SELECT count(*) FROM outcome_A) AS outcome_A_count,
  (SELECT count(*) FROM outcome_B) AS outcome_B_count,
  (SELECT count(*) FROM period_A_active pa
   INNER JOIN period_B_active pb ON pa."#user_id" = pb."#user_id") AS overlap
```

Run via `ae-cli analysis adhoc run --project-id <project_id> --model-type sql --definition '{"sql":"<SQL>"}'`.

> **Why no INNER JOIN.** Unlike 2B-paired which restricts to users in both periods, period_active keeps A-period and B-period samples separate. The independent Z-test treats them as two (potentially overlapping) groups. The `overlap` column is for diagnostic only — it tells you how much the independence assumption is violated.
>
> **How to interpret `overlap`.** Compute `overlap_rate = overlap / min(n_A, n_B)`. In the report's Part 2:
> - `overlap_rate < 10%` → "groups are nearly independent; independent Z-test is appropriate"
> - `10% ≤ overlap_rate < 30%` → "moderate overlap; independence assumption approximately holds"
> - `overlap_rate ≥ 30%` → "high overlap; independence is materially violated — consider rerunning with `cohort_design=paired` for a precise McNemar test on the same users"
>
> **When period_active is equivalent to first_occurrence.** For one-time cohort events (`register`, `first_order`, first `subscribe`), every user has exactly one occurrence globally, so per-period first = global first, and overlap is structurally 0. In this case period_active and first_occurrence give identical results — use either, but `first_occurrence` is the conventional label.
>
> **Cohort event and outcome event can be the same action.** For retention with cohort=`login` and outcome=`login` under period_active, the per-user first login in period A is the cohort date; the within-window predicate `e."$part_date" > pa.a_cohort_date` excludes that first login itself, so any later login within N days counts as the outcome. No extra filter is needed.
>
> **When cohort and outcome are the same event AND the business wants the same sub-type on both sides** (e.g. "first **diamond** purchase → **diamond** repurchase"), set BOTH `cohort_filter` and `outcome_filter` to the same value — `cohort_filter` filters the cohort-side `min` (so first-ever is first-ever-of-that-subtype), and `outcome_filter` filters the outcome join (so only same-subtype later occurrences count). When the business wants "first X → any Y" (e.g. "first diamond purchase → any repurchase"), set `cohort_filter` only and leave `outcome_filter` empty. The two parameters are independent — never assume they share a value without an explicit user statement.

##### Step 2b-paired — paired design (SQL mode, computes a/b/c/d directly)

When `cohort_design = "paired"`, use this template family to compute the four McNemar discordance cells in a single SQL query. No CSV required.

**Key design choice: per-user cohort-relative windows.** Each user's per-period cohort date is the user's **first** occurrence of the cohort event **within that period** (per-user, per-period `min("$part_date")`). The outcome window is then relative to that user's per-period cohort date — not to the period start/end. This makes the paired path test the **same quantity** as the first_occurrence path, so the two designs remain comparable.

**Window variant follows the same scenario rule as first_occurrence.** Pick the variant per the "Choosing the variant at runtime" rule in Step 2b-1: exact-day for retention with project exact-day definition; within-window for repurchase / conversion / churn / renewal / custom, and for retention with cumulative-window definition. Do NOT hardcode within-window for paired — it would diverge from the first_occurrence path's definition.

**Template 2B-paired-window (within-window, default for repurchase / conversion / churn / renewal / custom; also for retention with cumulative-window definition):**

```sql
WITH active_A AS (
  -- Per-user first cohort event date in period A
  SELECT "#user_id", min("$part_date") AS a_cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
    AND "$part_date" BETWEEN '<A_START>' AND '<A_END>'
  GROUP BY "#user_id"
),
active_B AS (
  -- Per-user first cohort event date in period B
  SELECT "#user_id", min("$part_date") AS b_cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: append `AND "<prop>" <op> <value>` here when Step 1 `cohort_filter` is set (e.g. AND "status" = 'success'); omit the line entirely when not set
    AND "$part_date" BETWEEN '<B_START>' AND '<B_END>'
  GROUP BY "#user_id"
),
paired AS (
  -- Users observed in BOTH periods — the paired sample
  SELECT a."#user_id", a.a_cohort_date, b.b_cohort_date
  FROM active_A a
  INNER JOIN active_B b ON a."#user_id" = b."#user_id"
),
outcome_A AS (
  -- Whether each paired user performed the outcome within N days after their A-period cohort date
  SELECT DISTINCT p."#user_id", 1 AS flag_A
  FROM paired p
  JOIN hive.ta.v_event_<project_id> e
    ON e."#user_id" = p."#user_id"
    AND e."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: append `AND e."<prop>" <op> <value>` when Step 1 `outcome_filter` is set; omit entirely when not set. Note the `e.` alias prefix on the outcome join.
    AND e."$part_date" > p.a_cohort_date
    AND e."$part_date" <= date_format(date_add('day', <N>, date(p.a_cohort_date)), '%Y-%m-%d')
),
outcome_B AS (
  -- Whether each paired user performed the outcome within N days after their B-period cohort date
  SELECT DISTINCT p."#user_id", 1 AS flag_B
  FROM paired p
  JOIN hive.ta.v_event_<project_id> e
    ON e."#user_id" = p."#user_id"
    AND e."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: append `AND e."<prop>" <op> <value>` when Step 1 `outcome_filter` is set; omit entirely when not set. Note the `e.` alias prefix on the outcome join.
    AND e."$part_date" > p.b_cohort_date
    AND e."$part_date" <= date_format(date_add('day', <N>, date(p.b_cohort_date)), '%Y-%m-%d')
)
SELECT
  count(case when oa.flag_A=1 AND ob.flag_B=1 then 1 end) AS a,            -- both periods: outcome happened
  count(case when oa.flag_A=1 AND ob.flag_B IS NULL then 1 end) AS b,     -- A only: outcome in A, not in B
  count(case when oa.flag_A IS NULL AND ob.flag_B=1 then 1 end) AS c,     -- B only: outcome in B, not in A
  count(case when oa.flag_A IS NULL AND ob.flag_B IS NULL then 1 end) AS d, -- neither
  count(*) AS paired_n,
  (SELECT count(*) FROM active_A) AS n_A_active,   -- per-period active count for A (for the Step 3 paired_share < 30% representativeness check)
  (SELECT count(*) FROM active_B) AS n_B_active    -- per-period active count for B (for the Step 3 paired_share < 30% representativeness check)
FROM paired p
LEFT JOIN outcome_A oa ON oa."#user_id" = p."#user_id"
LEFT JOIN outcome_B ob ON ob."#user_id" = p."#user_id"
```

**Template 2B-paired-exact (exact-day, for retention with project exact-day definition):**

```sql
WITH active_A AS (
  SELECT "#user_id", min("$part_date") AS a_cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: render `AND "<prop>" <op> <value>` here; omit this line when empty
    AND "$part_date" BETWEEN '<A_START>' AND '<A_END>'
  GROUP BY "#user_id"
),
active_B AS (
  SELECT "#user_id", min("$part_date") AS b_cohort_date
  FROM hive.ta.v_event_<project_id>
  WHERE "$part_event" = '<cohort_event>'
  -- <<COHORT_FILTER>> optional: render `AND "<prop>" <op> <value>` here; omit this line when empty
    AND "$part_date" BETWEEN '<B_START>' AND '<B_END>'
  GROUP BY "#user_id"
),
paired AS (
  SELECT a."#user_id", a.a_cohort_date, b.b_cohort_date
  FROM active_A a
  INNER JOIN active_B b ON a."#user_id" = b."#user_id"
),
outcome_A AS (
  SELECT DISTINCT p."#user_id", 1 AS flag_A
  FROM paired p
  JOIN hive.ta.v_event_<project_id> e
    ON e."#user_id" = p."#user_id"
    AND e."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: render `AND e."<prop>" <op> <value>` here; omit this line when empty
    AND e."$part_date" = date_format(date_add('day', <N>, date(p.a_cohort_date)), '%Y-%m-%d')
),
outcome_B AS (
  SELECT DISTINCT p."#user_id", 1 AS flag_B
  FROM paired p
  JOIN hive.ta.v_event_<project_id> e
    ON e."#user_id" = p."#user_id"
    AND e."$part_event" = '<outcome_event>'
    -- <<OUTCOME_FILTER>> optional: render `AND e."<prop>" <op> <value>` here; omit this line when empty
    AND e."$part_date" = date_format(date_add('day', <N>, date(p.b_cohort_date)), '%Y-%m-%d')
)
SELECT
  count(case when oa.flag_A=1 AND ob.flag_B=1 then 1 end) AS a,
  count(case when oa.flag_A=1 AND ob.flag_B IS NULL then 1 end) AS b,
  count(case when oa.flag_A IS NULL AND ob.flag_B=1 then 1 end) AS c,
  count(case when oa.flag_A IS NULL AND ob.flag_B IS NULL then 1 end) AS d,
  count(*) AS paired_n,
  (SELECT count(*) FROM active_A) AS n_A_active,
  (SELECT count(*) FROM active_B) AS n_B_active
FROM paired p
LEFT JOIN outcome_A oa ON oa."#user_id" = p."#user_id"
LEFT JOIN outcome_B ob ON ob."#user_id" = p."#user_id"
```

Run via `ae-cli analysis adhoc run --project-id <project_id> --model-type sql --definition '{"sql":"<SQL>"}'`.

> **Why per-user cohort-relative windows, not period-relative.** Using period-level windows (e.g., `e."$part_date" BETWEEN '<A_START>' AND date_add('day', <N>, date('<A_END>'))`) would test "did the user perform the outcome anywhere in the A-period-plus-N-days", which is a different quantity than the first_occurrence path's "outcome within N days of the user's cohort date". The two designs would not be comparable. The per-user cohort-relative window aligns the paired path with the first_occurrence path so the same business metric is being tested under both designs.
>
> **Cohort event and outcome event can be the same action.** For renewal scenarios (cohort = `subscribe`, outcome = `renew`), the per-user `min("$part_date")` in `active_A` picks the user's first subscribe event in period A as their A-period cohort date. The outcome CTE joins on `"$part_event" = '<outcome_event>'` (i.e., `renew`), and the within-window predicate `e."$part_date" > p.a_cohort_date` ensures the outcome event occurs after the cohort subscribe. So any `renew` event within N days of the cohort subscribe counts as the outcome — no extra filter is needed. (If your project tracks renewal as a second `subscribe` event rather than a separate `renew` event, set `outcome_event=subscribe` and the same exclusion logic applies.) For the exact-day variant, the same-day exclusion is automatic because `a_cohort_date + N` ≠ `a_cohort_date`.
>
> **paired_n is the sample size for McNemar.** McNemar uses `a + b + c + d = paired_n`. The test only depends on discordance cells `b` and `c`. Step 3 surfaces `paired_n < 30` and per-group `n < 30` as precision warnings, not hard blocks (Fisher exact and exact McNemar remain valid for sparse tables); only structurally unusable inputs (n=0, invalid counts, b+c=0) block.
>
> **Window variant rule matches first_occurrence.** If the user's project uses exact-day retention, run 2B-paired-exact for the retention scenario. If the project uses cumulative-window retention (or the scenario is repurchase/conversion/renewal/custom), run 2B-paired-window. The choice is the same as for Template 2A in Step 2b-1 — do not pick a different variant just because the design is paired.

##### Step 2b-2 — Drilldown mode (DEPRECATED, skip to 2b-3)

> **Deprecated.** The retention-model drilldown path is documented-broken on cluster 6.x — it returns `PARAMETER_ERROR / QUERY_FAILED` on both `run` and `export` even when the contract advertises `drilldown_entities`. Do not attempt this path; skip straight to Step 2b-3 (aggregate-rate mode). The 2b-3 aggregate-rate fallback uses the same per-cohort `initial users` / `retained users` counts that the retention ad-hoc model already returns, so no information is lost — only user-level overlap detection (which is structurally 0 under first_occurrence anyway). If a future platform version fixes drilldown, this section can be re-enabled.

##### Step 2b-3 — Aggregate-rate mode (last resort, first_occurrence and period_active)

Use only the per-cohort `initial users` and `retained users` (or `outcome users`) counts from Step 2a. Compute `n_A`, `r_A`, `p_A`, `n_B`, `r_B`, `p_B` directly. Mark the report's Part 2 "Overlap detection unavailable; treated as independent." Do not attempt Step 4 overlap detection.

> **Paired design cannot fall back to aggregate-rate mode.** McNemar requires user-level paired outcomes. If Step 2b-paired SQL fails, inform the user that paired McNemar is not possible without user-level data, and suggest either (a) switching to `first_occurrence` design and running independent Z-test, or (b) uploading a CSV with paired user-level outcomes (Step 2c).
>
> **period_active loses the overlap diagnostic in this mode.** The independent Z-test still runs correctly using `n_A`, `r_A`, `n_B`, `r_B` — but the overlap rate cannot be computed without user-level data, so the Step 3 independence-violation warning (≥30% overlap) is not available. Note this in Part 2.

#### Step 2c — From uploaded CSV/Excel

Parse with pandas; validate the required columns. Three schemas accepted:

**Schema 1 — long format (group + outcome):**
- `user_id`, `group` (`A`/`B`), `outcome` (`0`/`1`)
- For `first_occurrence` design: pass through the standard Step 4 independent Z-test routing.
- For `period_active` design: same independent Z-test flow, but if both `group=A` and `group=B` rows exist for the same `user_id`, also compute `overlap = count(DISTINCT user_id present in both groups)` and `overlap_rate = overlap / min(n_A, n_B)`, then report it in Part 2 and apply the ≥30% independence-violation warning from Step 3.

**Schema 2 — wide format (paired):**
- `user_id`, `group_A_outcome` (`0`/`1`), `group_B_outcome` (`0`/`1`)
- For `paired` design: each row is one user observed in both periods. Compute a/b/c/d locally and pass to `analyze.py` with `test=mcnemar` (see Step 4 routing).

**Schema 3 — pre-computed cohort list:**
- `user_id`, `group` (`A`/`B`) — no `outcome` column.
- Use when the cohort membership cannot be derived from event data (the business "first" depends on an event property the project did NOT bury, so Step 2b SQL cannot isolate it). The user pre-computes the cohort user-id list externally and uploads it. Because the cohort is supplied directly as a user-id list, there is no cohort SQL in Schema 3 — the `cohort_filter` parameter does not apply (it is ignored, not "left empty"). The `outcome_filter` still applies and is injected into the outcome SQL below. The `outcome_event` and observation window N still apply.
- For each group, run a SQL query `SELECT DISTINCT "#user_id" FROM hive.ta.v_event_<project_id> WHERE "#user_id" IN (<uploaded list for that group>) AND "$part_event" = '<outcome_event>' <<OUTCOME_FILTER>> AND "$part_date" BETWEEN <cohort_date> AND <cohort_date + N>` to get r_A / r_B. n_A / n_B = the uploaded list sizes per group. Then run the Step 4 independent Z-test (Schema 3 supports first_occurrence / period_active only; for paired, use Schema 2 which carries both-period outcomes).
- Alternatively, if the user also has the outcome pre-computed, ask them to upload Schema 1 instead (it carries both columns and needs no extra SQL).

Fail fast on missing values. When `user_id` is present and complete, run the appropriate design-specific flow in Step 4. When only aggregate rates are available in the file, apply the Step 2b-3 fallback (first_occurrence and period_active; paired requires user-level data).



## Old-user retention filter contract

For **existing/old-user retention** (any language — e.g. EN "existing-user retention", 中文 "老用户留存", JP "既存ユーザーリテンション", KR "기존 사용자 리텐션"), registration age is a **period-relative eligibility condition** and must be applied before cohort construction.

- Ordinary `period_active` comparison:
  - A branch: `registration_time < A_START`
  - B branch: `registration_time < B_START`
  - Do not reuse one frozen cutoff across both branches.
  - The cohort anchor is qualifying activity in each period; N-day retention is measured from that activity anchor, not from the historical registration date.
- `paired` same-old-users comparison:
  - freeze eligibility at `registration_time < A_START` for both periods;
  - then intersect/match user IDs across A and B and build McNemar cells.

If registration time is a user property rather than an event property, join/read it from the project-supported user table/property source instead of injecting it as an event `<<COHORT_FILTER>>`. The generic placeholder remains for event-level filters; do not fabricate an event alias for a user-profile field.
