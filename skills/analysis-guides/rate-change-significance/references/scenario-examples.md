# Scenario examples and SQL templates

> Note: The scenarios in this file are illustrative examples only. They do not override the cohort selection rules defined in `scenario-selection.md`. Always follow explicit user requirements and business context first.


This reference contains worked examples. Load only when a concrete business scenario example is needed.

## 3. Worked scenarios

### Scenario A — New user next-day retention (first_occurrence)

**User input**:
> "We released on Aug 1 and want to see whether new-user next-day retention changed significantly. Period A: users who registered in Jul 25-31. Period B: users who registered in Aug 2-8."

**Resolution path**:
- Phrasing "new users registered" → `first_occurrence`
- Scenario: cohort=register, outcome=login → `retention`
- Project retention definition: assume exact-day → exact-day window
- Template: **2A-exact**
- Test: **independent Z** (overlap structurally 0)

**SQL (Template 2A-exact)**:
```sql
WITH user_first_cohort AS (
  SELECT "#user_id", min("$part_date") AS cohort_date
  FROM hive.ta.v_event_7
  WHERE "$part_event" = 'register'
  GROUP BY "#user_id"
), regs AS (
  SELECT "#user_id", cohort_date
  FROM user_first_cohort
  WHERE cohort_date BETWEEN '2026-07-25' AND '2026-08-08'
), logs AS (
  SELECT DISTINCT "#user_id", "$part_date" AS outcome_date
  FROM hive.ta.v_event_7
  WHERE "$part_event" = 'login'
    AND "$part_date" BETWEEN '2026-07-25' AND '2026-08-09'
)
SELECT
  count(DISTINCT case when r.cohort_date BETWEEN '2026-07-25' AND '2026-07-31' then r."#user_id" end) AS n_A,
  count(DISTINCT case when r.cohort_date BETWEEN '2026-08-02' AND '2026-08-08' then r."#user_id" end) AS n_B,
  count(DISTINCT case when r.cohort_date BETWEEN '2026-07-25' AND '2026-07-31'
      AND l.outcome_date = date_format(date_add('day', 1, date(r.cohort_date)), '%Y-%m-%d')
      then r."#user_id" end) AS outcome_A,
  count(DISTINCT case when r.cohort_date BETWEEN '2026-08-02' AND '2026-08-08'
      AND l.outcome_date = date_format(date_add('day', 1, date(r.cohort_date)), '%Y-%m-%d')
      then r."#user_id" end) AS outcome_B
FROM regs r
LEFT JOIN logs l ON r."#user_id" = l."#user_id"
```

---

### Scenario B — Active users next-day retention (period_active)

**User input**:
> "We released on Aug 1 and want to see whether active users' next-day retention changed before vs after. Period A: users who logged in during Jul 25-31. Period B: users who logged in during Aug 2-8. Check whether they logged in again the next day."

**Resolution path**:
- Phrasing "active users who logged in" → `period_active` (NOT paired — "active users" means users active in this period, not necessarily both)
- Scenario: cohort=login, outcome=login → `retention`
- Project retention definition: assume exact-day → exact-day window
- Template: **2C-period-active-exact**
- Test: **independent Z** (report overlap rate; warn if ≥ 30%)

**SQL (Template 2C-period-active-exact)**:
```sql
WITH period_A_active AS (
  SELECT "#user_id", min("$part_date") AS a_cohort_date
  FROM hive.ta.v_event_7
  WHERE "$part_event" = 'login'
    AND "$part_date" BETWEEN '2026-07-25' AND '2026-07-31'
  GROUP BY "#user_id"
),
period_B_active AS (
  SELECT "#user_id", min("$part_date") AS b_cohort_date
  FROM hive.ta.v_event_7
  WHERE "$part_event" = 'login'
    AND "$part_date" BETWEEN '2026-08-02' AND '2026-08-08'
  GROUP BY "#user_id"
),
outcome_A AS (
  SELECT DISTINCT pa."#user_id", 1 AS flag_A
  FROM period_A_active pa
  JOIN hive.ta.v_event_7 e
    ON e."#user_id" = pa."#user_id"
    AND e."$part_event" = 'login'
    AND e."$part_date" = date_format(date_add('day', 1, date(pa.a_cohort_date)), '%Y-%m-%d')
),
outcome_B AS (
  SELECT DISTINCT pb."#user_id", 1 AS flag_B
  FROM period_B_active pb
  JOIN hive.ta.v_event_7 e
    ON e."#user_id" = pb."#user_id"
    AND e."$part_event" = 'login'
    AND e."$part_date" = date_format(date_add('day', 1, date(pb.b_cohort_date)), '%Y-%m-%d')
)
SELECT
  (SELECT count(*) FROM period_A_active) AS n_A,
  (SELECT count(*) FROM period_B_active) AS n_B,
  (SELECT count(*) FROM outcome_A) AS outcome_A_count,
  (SELECT count(*) FROM outcome_B) AS outcome_B_count,
  (SELECT count(*) FROM period_A_active pa
   INNER JOIN period_B_active pb ON pa."#user_id" = pb."#user_id") AS overlap
```

**Report Part 2 must include**: overlap rate + independence-violation level (low/moderate/high). If overlap ≥ 30%, recommend rerunning with `cohort_design=paired`.

---

### Scenario C — Old users next-day retention (paired)

**User input**:
> "We want to see whether old users who logged in during both periods had a change in next-day retention before vs after the release."

**Resolution path**:
- Phrasing "old users who logged in during both periods" → `paired`
- Scenario: cohort=login, outcome=login → `retention`
- Project retention definition: assume exact-day → exact-day window
- Template: **2B-paired-exact**
- Test: **McNemar**

**SQL (Template 2B-paired-exact)**:
```sql
WITH active_A AS (
  SELECT "#user_id", min("$part_date") AS a_cohort_date
  FROM hive.ta.v_event_7
  WHERE "$part_event" = 'login'
    AND "$part_date" BETWEEN '2026-07-25' AND '2026-07-31'
  GROUP BY "#user_id"
),
active_B AS (
  SELECT "#user_id", min("$part_date") AS b_cohort_date
  FROM hive.ta.v_event_7
  WHERE "$part_event" = 'login'
    AND "$part_date" BETWEEN '2026-08-02' AND '2026-08-08'
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
  JOIN hive.ta.v_event_7 e
    ON e."#user_id" = p."#user_id"
    AND e."$part_event" = 'login'
    AND e."$part_date" = date_format(date_add('day', 1, date(p.a_cohort_date)), '%Y-%m-%d')
),
outcome_B AS (
  SELECT DISTINCT p."#user_id", 1 AS flag_B
  FROM paired p
  JOIN hive.ta.v_event_7 e
    ON e."#user_id" = p."#user_id"
    AND e."$part_event" = 'login'
    AND e."$part_date" = date_format(date_add('day', 1, date(p.b_cohort_date)), '%Y-%m-%d')
)
SELECT
  count(case when oa.flag_A=1 AND ob.flag_B=1 then 1 end) AS a,
  count(case when oa.flag_A=1 AND ob.flag_B IS NULL then 1 end) AS b,
  count(case when oa.flag_A IS NULL AND ob.flag_B=1 then 1 end) AS c,
  count(case when oa.flag_A IS NULL AND ob.flag_B IS NULL then 1 end) AS d,
  count(*) AS paired_n
FROM paired p
LEFT JOIN outcome_A oa ON oa."#user_id" = p."#user_id"
LEFT JOIN outcome_B ob ON ob."#user_id" = p."#user_id"
```

**Report Part 5 must include**: survivorship caveat — paired sample reflects only consistently-active users; new users and churned users are excluded.

---

### Scenario D — All visitors 1-day conversion (period_active) — THE classic case

**User input**:
> "The homepage was redesigned in August. We want to see whether the 1-day conversion rate of all visitors changed before vs after. Period A: visitors during Jul 25-31. Period B: visitors during Aug 2-8. Check whether they placed an order within 1 day."

**Resolution path**:
- Phrasing "all visitors" + recurring cohort event (page_view) → `period_active` (NOT first_occurrence, NOT paired)
- Scenario: cohort=page_view, outcome=place_order → `conversion`
- Window: conversion → within-window
- Template: **2C-period-active-window**
- Test: **independent Z** (report overlap rate; warn if ≥ 30%)

**Why not first_occurrence?** first_occurrence with cohort=page_view only counts users whose **first-ever** page_view was in this period — it excludes all returning visitors, which is not what "all visitors" means.

**Why not paired?** paired would INNER JOIN to keep only visitors who came in BOTH periods — it excludes new visitors and churned visitors, changing the business question to "old visitors before vs after".

**SQL (Template 2C-period-active-window)**:
```sql
WITH period_A_active AS (
  SELECT "#user_id", min("$part_date") AS a_cohort_date
  FROM hive.ta.v_event_7
  WHERE "$part_event" = 'page_view'
    AND "$part_date" BETWEEN '2026-07-25' AND '2026-07-31'
  GROUP BY "#user_id"
),
period_B_active AS (
  SELECT "#user_id", min("$part_date") AS b_cohort_date
  FROM hive.ta.v_event_7
  WHERE "$part_event" = 'page_view'
    AND "$part_date" BETWEEN '2026-08-02' AND '2026-08-08'
  GROUP BY "#user_id"
),
outcome_A AS (
  SELECT DISTINCT pa."#user_id", 1 AS flag_A
  FROM period_A_active pa
  JOIN hive.ta.v_event_7 e
    ON e."#user_id" = pa."#user_id"
    AND e."$part_event" = 'place_order'
    AND e."$part_date" > pa.a_cohort_date
    AND e."$part_date" <= date_format(date_add('day', 1, date(pa.a_cohort_date)), '%Y-%m-%d')
),
outcome_B AS (
  SELECT DISTINCT pb."#user_id", 1 AS flag_B
  FROM period_B_active pb
  JOIN hive.ta.v_event_7 e
    ON e."#user_id" = pb."#user_id"
    AND e."$part_event" = 'place_order'
    AND e."$part_date" > pb.b_cohort_date
    AND e."$part_date" <= date_format(date_add('day', 1, date(pb.b_cohort_date)), '%Y-%m-%d')
)
SELECT
  (SELECT count(*) FROM period_A_active) AS n_A,
  (SELECT count(*) FROM period_B_active) AS n_B,
  (SELECT count(*) FROM outcome_A) AS outcome_A_count,
  (SELECT count(*) FROM outcome_B) AS outcome_B_count,
  (SELECT count(*) FROM period_A_active pa
   INNER JOIN period_B_active pb ON pa."#user_id" = pb."#user_id") AS overlap
```

---

### Scenario E — First-order users 7-day repurchase (first_occurrence)

**User input**:
> "A promotion started on Aug 1. We want to see whether the 7-day repurchase rate of new first-order users changed before vs after. Period A: users who placed their first order in July. Period B: users who placed their first order in August."

**Resolution path**:
- Phrasing "new first-order" + one-time event (first_order) → `first_occurrence`
- Scenario: cohort=first_order, outcome=purchase → `repurchase`
- Window: repurchase → within-window
- Template: **2A-window**
- Test: **independent Z**

(Same SQL structure as Scenario A, but with cohort=first_order, outcome=purchase, N=7, and within-window predicate.)

---

### Scenario F — All buyers this period 7-day repurchase (period_active)

**User input**:
> "We want to see whether the 7-day repurchase rate of all buyers this period changed before vs after. Period A: all users who purchased in July. Period B: all users who purchased in August."

**Resolution path**:
- Phrasing "all buyers this period" + recurring event (purchase) → `period_active`
- Scenario: cohort=purchase, outcome=purchase → `repurchase`
- Window: repurchase → within-window
- Template: **2C-period-active-window**
- Test: **independent Z** (report overlap rate)

**Note**: cohort event and outcome event are the same (purchase). Per-user per-period first occurrence is the cohort date; the within-window predicate `e."$part_date" > pa.a_cohort_date` excludes that first purchase, so any later purchase within N days counts as the outcome.

---

### Scenario G — Old subscribers' renewal rate (paired)

**User input**:
> "We want to see whether the 30-day renewal rate of old subscribers (subscribed in both periods) changed before vs after."

**Resolution path**:
- Phrasing "old subscribers subscribed in both periods" → `paired`
- Scenario: cohort=subscribe, outcome=renew → `renewal`
- Window: renewal → within-window
- Template: **2B-paired-window**
- Test: **McNemar**

---

### Scenario H — New subscribers' renewal rate (first_occurrence)

**User input**:
> "We want to see whether the 30-day renewal rate of new subscribers (first subscribed this period) changed before vs after."

**Resolution path**:
- Phrasing "new subscribers / first subscribed" → `first_occurrence`
- Scenario: cohort=subscribe, outcome=renew → `renewal`
- Window: renewal → within-window
- Template: **2A-window**
- Test: **independent Z**

**Note**: Even though renewal scenario default is `period_active`, the user's explicit "new subscribers / first subscribed" phrasing overrides to `first_occurrence`.

---

### Scenario I — All current subscribers' renewal rate (period_active, the renewal default)

**User input**:
> "We want to see whether the 30-day renewal rate of subscribers changed before vs after. Period A: all subscribers in July. Period B: all subscribers in August."

**Resolution path**:
- Phrasing "subscribers" (no "new" or "old" qualifier) + scenario default → `period_active` (renewal scenario default)
- Scenario: cohort=subscribe, outcome=renew → `renewal`
- Window: renewal → within-window
- Template: **2C-period-active-window**
- Test: **independent Z** (report overlap rate — for subscribers, overlap will likely be very high since most subscribers stay subscribed; consider recommending `paired` if overlap ≥ 30%)

## 4. Decision tree (use when phrasing is ambiguous)

```
1. Is the cohort event one-time (register, first_order, first subscribe)?
   ├─ YES → Does the user explicitly ask for "newcomers"?
   │       ├─ YES → first_occurrence
   │       └─ NO  → first_occurrence (one-time events: same as period_active; use first_occurrence as the conventional label)
   └─ NO (recurring: page_view, login, purchase, subscribe after first)
       ↓
2. Does the user's phrasing indicate which subset? (Match on the **semantic concept**, not on specific words — users may phrase the same concept in any language: Chinese, English, Japanese, Korean, etc. The English/中文 examples below are illustrations, not an exhaustive trigger list.)
   ├─ **First-time / newly-acquired entry** semantics (e.g. EN "new / first-ever", 中文 "新 / 首次 / 新访客", JP "新規 / 初回", KR "신규 / 첫") → first_occurrence
   ├─ **Full active population this period** semantics (e.g. EN "all / active this period", 中文 "所有 / 全部 / 本期活跃", JP "すべて / 今期アクティブ", KR "전체 / 이번 기간 활성") → period_active
   ├─ **Same users observed in both periods** semantics (e.g. EN "existing in both periods / in both periods", 中文 "老 / 两期都", JP "両期間に在籍", KR "양 기간 모두") → paired
   └─ Unclear (bare "users / visitors" with no population qualifier in any language) → ASK the user via AskUserQuestion:
        "Which subset?"
        - first_occurrence: users whose first-ever cohort event was in this period (newcomers only)
        - period_active: all users who did the cohort event in this period
        - paired: same users who did the cohort event in both periods
```

## 5. Common misclassifications to avoid

| Misclassification | Why it's wrong | What to use instead |
|---|---|---|
| "all visitors" → paired | Excludes new visitors and churned visitors, changes the business question | Use `period_active` |
| "active users" → paired | "active users" usually means active in this period, not both | Use `period_active`; only use `paired` if user says "active in both periods" |
| "all visitors" + cohort=page_view → first_occurrence | Only counts users whose first-ever page_view was in this period — excludes all returning visitors | Use `period_active` |
| "new visitors" → period_active | User explicitly asks about first-ever visitors; period_active includes return visitors | Use `first_occurrence` |
| "existing users" → period_active | "existing users" means users present in both periods — period_active treats A/B as independent groups | Use `paired` |
| "new subscribers" → period_active (because renewal default is period_active) | User explicitly asks about new subscribers — overrides scenario default | Use `first_occurrence` |
| period_active with high overlap (≥30%) without warning | Independence is materially violated; user might be running the wrong test | Always report overlap rate; recommend `paired` if ≥ 30% |
| Using period-level windows in period_active SQL | Tests "outcome anywhere in A period + N days" instead of "outcome within N days of user's cohort date" | Always use per-user cohort-relative windows (per-period `min($part_date)` + relative window predicate) |

## 6. Window variant selection (independent of cohort design)

The window variant (exact-day vs within-window) is decided by the **scenario and project retention definition**, NOT by the cohort design. All three designs use the same window rule for a given scenario so they remain comparable.

| Scenario + project definition | Window variant | Template suffix |
|---|---|---|
| retention + exact-day definition | exact-day | `-exact` |
| retention + cumulative-window definition | within-window | `-window` |
| repurchase / conversion / renewal / churn / custom | within-window | `-window` |

So for `retention` with exact-day project definition:
- first_occurrence → 2A-exact
- period_active → 2C-period-active-exact
- paired → 2B-paired-exact

For `conversion` (always within-window):
- first_occurrence → 2A-window
- period_active → 2C-period-active-window
- paired → 2B-paired-window

## 7. One-page summary table

| Scenario | Cohort event | Outcome event | "new X" question | "all X" question | "existing X / both periods" question |
|---|---|---|---|---|---|
| retention (exact-day) | register (1-time) | login | first_occurrence / 2A-exact | n/a (one-time event — no "all" vs "new" distinction) | n/a |
| retention (exact-day) | login (recurring) | login | first_occurrence / 2A-exact | period_active / 2C-period-active-exact | paired / 2B-paired-exact |
| repurchase | first_order (1-time) | purchase | first_occurrence / 2A-window | n/a | n/a |
| repurchase | purchase (recurring) | purchase | first_occurrence / 2A-window | period_active / 2C-period-active-window | paired / 2B-paired-window |
| conversion | page_view (recurring) | place_order | first_occurrence / 2A-window | period_active / 2C-period-active-window | paired / 2B-paired-window |
| renewal | subscribe (recurring after first) | renew | first_occurrence / 2A-window | period_active / 2C-period-active-window | paired / 2B-paired-window |
| churn | subscribe (active subscription) | cancel_subscribe / unsubscribe | first_occurrence / 2A-window | period_active / 2C-period-active-window | paired / 2B-paired-window |

For one-time cohort events, "new X" and "all X" collapse to the same set (first_occurrence = period_active). The distinction only matters for recurring cohort events.
