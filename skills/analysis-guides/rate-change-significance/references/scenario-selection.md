# Cohort Design Selection

Use this reference to decide **which population the user wants compared**. Cohort design and statistical test are related but are not the same decision.

## Three designs

| Design | Cohort definition | Expected A/B overlap | Business question |
|---|---|---:|---|
| `first_occurrence` | user's first-ever qualifying cohort event; one global cohort date per user | 0 for disjoint periods | newcomers / first-occurrence cohorts |
| `period_active` | users who perform the cohort event in each period; per-period first occurrence is the cohort date | possible | all users active in each period |
| `paired` | users observed in both periods; per-period cohort date on the same matched users | structural/high | within-user change among the same users |

For one-time events (`register`, true `first_order`, install, first subscribe), `first_occurrence` and `period_active` are effectively equivalent across disjoint periods. `paired` is structurally impossible for the one-time cohort event itself.

For recurring events (`login`, `page_view`, ordinary `purchase`, repeated subscription activity), the three designs answer different questions.

## Priority and ambiguity

Explicit user wording overrides scenario defaults. **Match on the semantic concept, not on specific words** — users may phrase the same concept in any language (Chinese, English, Japanese, Korean, French, …). The examples below illustrate the concept; they are NOT an exhaustive trigger list. Any phrasing expressing the same concept in any language triggers the same routing. When unsure whether the user's phrasing expresses a concept, ASK rather than guess.

- **First-time / newly-acquired entry** semantics (e.g. EN "new users / first order", 中文 "新用户 / 首单 / 首次", JP "新規 / 初回", KR "신규 / 첫") → usually `first_occurrence`.
- **Full active population this period, without "same users / both periods"** semantics (e.g. EN "all visitors / active users / all buyers this period", 中文 "所有访客 / 活跃用户 / 本期所有购买者", JP "すべての訪問者 / アクティブユーザー", KR "전체 방문자 / 활성 사용자") → usually `period_active`. Bare "subscribers" for renewal/churn also defaults here.
- **Same users observed in both periods** semantics (e.g. EN "same users / users in both periods / existing subscribers in both periods", 中文 "同一批用户 / 两期都活跃 / 两期都在的老用户", JP "両期間の同一ユーザー / 両期間に在籍する既存ユーザー", KR "양 기간 동일 사용자 / 양 기간 모두 활성 기존 사용자") → `paired`.
- **Existing/old-user status ALONE** is an eligibility definition, NOT a paired-design trigger (e.g. EN "existing users", 中文 "老用户", JP "既存ユーザー", KR "기존 사용자"). Default ordinary period comparison to `period_active`; choose `paired` only when the user's phrasing explicitly means the same users are observed in both periods.
- Bare population term ("users / visitors / subscribers" in any language) WITHOUT "same users / both periods" semantics is ambiguous.

Do not use `paired` merely because the user's phrasing expresses "active users". "Active users" normally means `period_active` unless the phrasing explicitly conveys "the same users are present in both periods".

## Old-user retention semantics

For retention questions about **existing/old-user retention** (any language — e.g. EN "existing users", 中文 "老用户", JP "既存ユーザー", KR "기존 사용자"), separate *eligibility* from *statistical design*.

### Ordinary A-period vs B-period old-user retention

Use `period_active` by default. Define eligibility separately in each period:

- A eligible old users: `registration_time < A_START`
- B eligible old users: `registration_time < B_START`
- Within each eligible set, cohort entry is the qualifying **activity/cohort anchor in that period**; old-user D7/D30 retention means return activity after that anchor, **not registration-based D7/D30**.
- Build A and B cohorts independently, then compute their user overlap. High overlap can trigger a paired sensitivity view, but does not redefine the primary period-level estimand.

This intentionally allows users who registered during A but before B to become **B-period old users**. Do not incorrectly freeze both periods at `registration_time < A_START` for the ordinary period comparison.

### Same old users before/after

Use `paired` only when the user's phrasing expresses **same old users observed in both periods** semantics (e.g. EN "same old users before and after", 中文 "同一批老用户 / 两期都在的老用户", JP "両期間の同一の既存ユーザー", KR "양 기간 동일한 기존 사용자"). Freeze eligibility at the earlier boundary:

- paired eligible users: `registration_time < A_START`
- require matched A/B observations for the same user IDs
- compare per-user outcomes with McNemar (exact McNemar/binomial when discordant counts are small)

Do **not** use `registration_time < B_START` for the paired cohort, because that would admit users who were not old users at the A-period baseline.

## Scenario presets

| Scenario | Typical cohort → outcome | Default design | Important business context |
|---|---|---|---|
| retention | register/login → login | first-occurrence for new users; period-active for active users | pair with longer-term retention/payment/LTV |
| repurchase | first_order/purchase → purchase | first-occurrence for first buyers; period-active for all buyers | AOV, repurchase cycle, LTV, cohort mix |
| conversion | exposure/page_view → convert/payment | period-active for all visitors; first-occurrence for new visitors | funnel balance and segment mix |
| renewal | subscribe/eligible subscriber → renew | period-active | tier mix, LTV/churn; paired excludes new/churned users |
| churn | active subscriber → cancel/unsubscribe | period-active | contract/tier mix, renewal/win-back |
| custom | user-specified | infer from wording/event semantics | user-supplied context |

Scenario defaults are fallbacks only. Never infer `first_occurrence` simply because the scenario is retention.

## One-time-event + paired deadlock

If the cohort event is truly one-time and the user asks for the same users in both disjoint periods, a paired cohort on that event has `paired_n=0` by construction. Explain that the literal paired design is impossible for that cohort event and use the nearest meaningful design only if it preserves the user's intent; otherwise ask for a recurring eligibility/activity event that can define the same-user population.

## Design-selection invariants

- `first_occurrence`: global first qualifying cohort date; disjoint A/B periods imply overlap=0.
- `period_active`: per-period first qualifying cohort date; always compute A/B user overlap when user IDs are available.
- `paired`: same user IDs in both periods; requires two outcome flags per matched user or equivalent a/b/c/d cells.
- Cohort design does not by itself decide Z vs Fisher; independent designs still need cell-count/boundary checks.
