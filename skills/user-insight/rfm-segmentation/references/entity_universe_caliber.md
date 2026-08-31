# Entity, Universe, Window, and Transaction Caliber

> Canonical rules for Stage 1–2.

## 1. Person-level entity resolution

### 1.1 Principle

RFM normally evaluates one **person/customer**. Keep these two concepts separate:

| Concept | Meaning |
| --- | --- |
| `business_entity` | What one row represents in business terms |
| `subject_field` | The actual TE event/property field used to identify that entity |

### 1.2 Default identity rule

| Scenario | Subject rule |
| --- | --- |
| Default | Start from TE `#user_id` as the technical user identifier. |
| `#account_id` usage | Use only when its business semantics and coverage match the intended RFM entity. Do not assume it is universally interchangeable with `#user_id` for every population/objective. |
| Custom person/account field | Use when the business model defines a stable entity above or different from the default TE user identity and payment-event coverage is acceptable. |
| Explicit role-level objective | Role/character ID may be used as the RFM subject. |

### 1.3 MMO binding rule — single-account, multi-character

MMO projects may have one real-world account controlling multiple roles/characters. In this model:

- TE `#account_id` typically stores **role/character ID**, not the real account ID.
- TE `#user_id` is therefore also **role-granular**.

**For account-level RFM**

1. Do **not** use TE `#account_id` or `#user_id`.
2. Find the customer's separately reported real-player/account field:
   - commonly custom `account_id`;
   - or an equivalent stable account property.
3. Verify the field exists on the successful-payment event.
4. Quantify its coverage.
5. Use that field as `subject_field`.

**For role-level RFM**

- Use TE `#account_id` / `#user_id` only when the user explicitly requests role/character value analysis.

**If no person-level field exists**

1. Report the limitation.
2. Ask whether role-level analysis is acceptable.
3. Never silently merge roles with an unverified field.

### 1.4 Identity record

Record these runtime values:

```yaml
business_entity: real_player | customer | account | role | custom
subject_field: <real TE field>
identity_semantics: <what one value means — account vs role vs customer>
coverage_on_payment_event: <percent>
```

## 2. Universe types

**Default recommendation for classic customer-value RFM:** `payer_based` — but it is **not** an auto-selected default.

| Universe type | Definition | Guidance |
| --- | --- | --- |
| `payer_based` | At least one valid paid order in eligibility lookback | Recommended for customer-value RFM |
| `activity_based` | Defined active population, including F/M=0 users when required | Use only when business objective requires an active-population view |
| `account_based` | Registered/subscribed accounts meeting a specified status rule | Suitable for account/subscription populations |
| `custom_cohort` | User-provided audience rule | Use exactly the confirmed cohort definition |

**Rules**

- Always state the universe type.
- Require explicit user confirmation of the universe unless the user's request already defines it unambiguously.
- Do not infer “historical payers” merely because the task says “RFM”.
- Do not label `activity_based` or `account_based` segmentation as "payer RFM" without qualification.
- Keep universe eligibility separate from the scoring window so eligible lapsed users remain in the result.

## 3. Eligibility lookback, scoring window, and reference timestamp

Keep the three concepts separate:

| Time concept | Purpose |
| --- | --- |
| Eligibility lookback | Determines who qualifies and where R searches for the latest valid order |
| Scoring window | Measures F and M |
| Reference timestamp | Anchor for R; normally the scoring-window end |

### 3.0 Mandatory Stage-1 calibration gate

Universe and time calibers are **user-confirmed business choices**, not agent-silent defaults.

1. Before computing R/F/M, batch the unresolved Stage-1 choices into one interaction: universe, eligibility lookback, scoring window, reference timestamp, and any refund/F-semantic choices that require business judgment.
2. Ground recommendations in discovered project facts — payment-event date range (`min`/`max $part_date`), payer scale, and lifecycle signals — never hardcode by industry.
3. Offer a short recommendation list (for example 14 / 28 / 30 / 60 days or a lifecycle-aligned span), each with an impact note, and allow custom input.
4. State eligibility lookback and reference timestamp in the same round because they anchor with the scoring window under closed-day alignment.
5. Reuse any universe/time choice already stated unambiguously by the user; do not ask twice.
6. Ambiguous wording such as “最近” / “recently” is not explicit.
7. Proceed only when every required caliber is resolved.

### 3.1 Reference timestamp default

Default to:

```text
T-1 23:59:59 in the project timezone
```

Do **not** default to "now" or current-day end.

**Reason**

A same-day cutoff reads a live, still-ingesting partition. That causes minute-to-minute drift in:

- user counts;
- R;
- F;
- M;
- reconciliation;
- tag-refresh consistency.

### 3.2 Closed-day alignment

Keep these aligned to the same closed day:

- eligibility `$part_date` upper bound;
- scoring-window upper bound;
- R `date_diff` reference.

For date arithmetic/reference expressions, a SQL date literal may be used when needed, for example:

```sql
date '2026-08-25'
```

This does **not** apply to the event partition predicate: `"$part_date"` is varchar and must be compared with string literals such as `'2026-08-25'`.

### 3.3 Opt-in fresh slice

Use "as of today / now" only when:

- the business explicitly needs the freshest activation slice; and
- the user accepts data drift.

### 3.4 Eligibility recommendation

For payer RFM:

1. Prefer all-time eligibility when feasible.
2. Otherwise use a confirmed long capped lookback.
3. Never let a short scoring window silently remove older historical payers.

### 3.5 Late-backfill caveat

T-1 may still be unstable when the project backfills yesterday's partition after midnight due to:

- delayed SDK retries;
- ETL corrections;
- timezone carryover.

For known backfill lag:

- shift the cutoff to T-2; or
- require an ingestion-completed checkpoint.

State the chosen cutoff and its closed-ness assumption in the analysis caliber.

### 3.6 Eligible subject with no scoring-window order

```text
F = 0
M_raw = 0
M_scoring = 0
R = days since latest valid eligibility-window order
```

## 4. Valid transaction and F semantics

### 4.1 Payment event

Confirm the successful-payment event and conditions from real project metadata.

**Candidate heuristic (fast path)**

Match the project event list against this name set before asking the user:

- exact: `payment`, `pay`, `purchase`, `recharge`, `order`, `iap`, `top_up`, `coin_buy`, `diamond_buy`, `cashier`;
- prefix / suffix: `pay_*`, `*_pay`, `purchase_*`, `*_purchase`, `recharge_*`, `*_recharge`;
- exclude prefab / template events starting with `ta@` unless the user explicitly selects one.

Decision rule:

- Event names are discovery hints only; a name such as `order` is not proof of successful payment.
- For the strongest candidate(s), inspect event metadata and run one aggregate probe for date range, distinct subjects, amount behavior, and success-status behavior.
- Auto-adopt only when exactly one candidate is both unique **and semantically verified** by metadata/probe.
- 0 candidates or unresolved semantics → ask the user and present the closest evidence-backed candidates.
- 2 or more plausible verified candidates → present `event_desc` / recent volume / relevant amount-status fields and ask the user to pick.

### 4.2 F modes

| Mode | Definition | Use when |
| --- | --- | --- |
| `attempt_based` | Every deduplicated successful payment order counts, even if later fully refunded | Business wants successful payment attempts/transactions as loyalty frequency |
| `net_valid` | An order counts only when recognized net amount > 0 | Returns/refunds should reverse purchase frequency |

Never leave F mode implicit.

- When refunds/returns exist, include `attempt_based` vs `net_valid` in the Stage-1 user confirmation.
- When no refund/return mechanism exists and successful-payment/dedup semantics are unambiguous, record `attempt_based` explicitly without a separate question.

### 4.3 R transaction-validity semantics

By default, align R with the chosen effective-transaction semantics:

| F / transaction mode | R behavior |
| --- | --- |
| `net_valid` | A fully refunded order whose recognized net amount <= 0 does **not** refresh R |
| `attempt_based` | A deduplicated successful payment may refresh R even if later refunded, when that is the confirmed business definition |

If R intentionally uses different semantics from F:

- document the override explicitly;
- never leave R validity ambiguous.

## 5. Refund recognition

Payment window and refund-recognition window are different concepts.

### 5.1 Supported modes

| Mode | Rule | Recommended use |
| --- | --- | --- |
| `as_of_analysis` | For scoring-window payments, deduct all linked refunds known up to the analysis/reference cutoff, including refunds after scoring-window end | Recommended default for current-state customer value |
| `in_period` | Deduct only refunds whose refund event also falls inside the scoring window | Period-accounting / event-period semantics |
| `historical_cutoff` | Deduct only refunds that would have been known at the historical evaluation timestamp | Historical backtest; avoids future leakage |

**Example — `as_of_analysis`**

```text
Payment: Jun 28
Refund: Jul 3
Analysis: Aug 25
Result: recognize the refund for the Jun-window payment
```

### 5.2 Refund runtime record

```yaml
refund_mode: gross_only | net
refund_recognition: as_of_analysis | in_period | historical_cutoff
refund_cutoff: <timestamp/date>
```

### 5.3 Linkage rule

- Refunds should link to the original order when using order-level netting.
- Unlinked refunds require an explicit approximation or exclusion rule.

## 6. Currency and amount units

Before calculation:

- inspect real values;
- confirm whether amount is:
  - yuan/dollars;
  - cents/minor units;
  - virtual currency;
  - another measure.

For multi-currency projects, choose one:

1. normalize with an approved FX source/rule;
2. restrict to a confirmed currency.

Apply the same currency rule to:

- universe qualification;
- R;
- F;
- M.

## 7. Required SQL shape

**TE table reference**

- Event table: `ta.v_event_{project_id}` (Hive catalog: `hive.ta.v_event_{project_id}`).
- User table: `ta.v_user_{project_id}`.
- `"$part_date"` is a varchar partition column — compare it with string literals (for example `WHERE "$part_date" BETWEEN '2026-07-29' AND '2026-08-27'`), **not** with `date '...'` casts.
- `"$part_event"` is the event-name filter column.
- Always include a `"$part_date"` partition predicate on event-table queries.

Build the dataset in this order:

1. eligible subjects + latest valid payment across eligibility lookback;
2. scoring-window payment orders;
3. recognized refunds according to refund mode/cutoff;
4. order-level `net_amt`;
5. subject-level F/M aggregation;
6. LEFT JOIN back to eligible subjects.

**Prohibited**

Do not reuse a scoring-window-only payment CTE as the universe.
