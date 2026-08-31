---
name: rfm-segmentation
description: "Build end-to-end RFM user segmentation on real AE/TE transaction data: resolve the person-level analysis entity, define universe/window/transaction caliber, compute and score R/F/M, validate segment quality, create AE tags only after confirmation, create per-segment user clusters for activation only after confirmation, and recommend segment-specific operations. Use for RFM analysis, user value tiering, high-value/lapsed payer identification, R/F/M scoring, or RFM-based LTV/retention/campaign analysis. Not for direct LTV forecasting or non-RFM segmentation."
version: "3.24"
---

# RFM Segmentation

## 1. Purpose and guarantees

| Item | Requirement |
| --- | --- |
| Primary purpose | Run production-grade person-level RFM (Recency / Frequency / Monetary) segmentation on ThinkingData AE/TE data. |
| Data source | Use real project metadata and `ae-cli`; never invent event/property names. |
| Population integrity | Never silently change the analysis population. |
| Default unit | One row = one real person/customer, unless the user explicitly requests another business entity. |
| Operationalization | AE tag and user-cluster creation are opt-in and require explicit confirmation. |
| Final result | Render a deterministic user-facing business result using the mandatory output contract. |

## 2. Core principles

| # | Principle |
| --- | --- |
| 1 | **Resolve the business person before the technical field.** RFM normally evaluates a person/customer, not an arbitrary event identity. |
| 2 | **Default technical subject = `#user_id`.** Use `#user_id` unless the business model requires a different entity. Do not assume `#account_id` is universally equivalent for the intended RFM population; use it only when its semantics and coverage are appropriate for the chosen business entity. |
| 3 | **MMO exception (gated).** In single-account-multi-character games, the tracked TE identity may be role-granular while the business needs real-account/player-level RFM. Apply this exception only when (a) project metadata contains a separately reported stable real-player/account field with verified payment-event coverage, OR (b) the user explicitly confirms the project is single-account-multi-character. Do not use `#user_id`↔`#account_id` mapping or `#device_id` mapping alone to infer business entity granularity. When uncertain, present person-level vs role-level options and let the user choose. Never silently fall back to a role identifier for person-level RFM. |
| 4 | **Non-MMO default.** For other games, e-commerce, SaaS, and other businesses, start from `#user_id`. Use `#account_id` or a verified custom stable person field only when metadata/business semantics show that it represents the intended analysis entity with acceptable coverage. |
| 5 | **Caliber before scoring.** Universe, entity, transaction caliber, and window outrank threshold/scoring choices. |
| 6 | **Exactly-once segmentation.** Every member of the chosen universe must receive exactly one RFM segment. Activation may target only selected segments. |
| 7 | **Writes are opt-in.** Never create or delete AE tags or user clusters without the required user confirmation. |
| 8 | **Shared namespace.** AE tag and user-cluster names share one project-scoped namespace. A `tag_name` and `cluster_name` cannot reuse the same key; the second write is rejected with `DUPLICATEKEY`. The RFM tag is one multi-value tag `rfm_segment` whose `tag_value` enumerates the lifecycle segments; keep this tag key stable and use `rfm_<segment>_cluster` for per-segment activation cohorts (for example `rfm_at_risk_cluster`, filtering `tag_value='at_risk'`). |

## 3. Required references and assets

### 3.1 Mandatory before any final user-facing result

| Resource | Purpose |
| --- | --- |
| [`references/output_format.md`](references/output_format.md) | Final output contract |
| [`assets/output_contract.yaml`](assets/output_contract.yaml) | Language-neutral section/table schema |

These two resources are mandatory; they are never "load only when needed".

### 3.2 Load by workflow stage

| Stage / need | Resource |
| --- | --- |
| Entity, universe, windows, refunds | [`references/entity_universe_caliber.md`](references/entity_universe_caliber.md) |
| Per-metric scoring resolution, mixed-band/ties, M handling, segment mapping | [`references/scoring_standards.md`](references/scoring_standards.md) |
| Quality, stability, migration | [`references/validation_rules.md`](references/validation_rules.md) |
| AE tag creation / refresh | [`references/ae_tag_creation.md`](references/ae_tag_creation.md) |
| Per-segment user-cluster creation | [`references/cluster_creation.md`](references/cluster_creation.md) |
| Per-segment operational strategy (dynamic, project-grounded) | [`references/dynamic_strategy.md`](references/dynamic_strategy.md) |
| Industry strategy fallback / guardrail | [`references/strategy_profiles.md`](references/strategy_profiles.md) |

### 3.3 Supporting files

- `assets/rfm_tag_names.yaml`
  - Stable platform tag names and display names.
- `scripts/validate_segments.py`
  - Deterministic file-level spot-check only.
  - Covers: null/empty subject, duplicate subject, invalid R/F, missing/invalid scores, illegal lifecycle segment keys, same-value-same-band violations, score contiguity/range, optional effective-band consistency, and basic score-direction monotonicity.
  - Does **not** cover: universe coverage against an external universe source, requested-band intent, exact threshold/operator reproduction, revenue lineage, lapsed-user retention against an external universe, or entity-semantic correctness.
  - Those hard checks must still be executed in the analysis pipeline per `references/validation_rules.md` §1.

## 4. AE/TE and `ae-cli` routing

Use the **ae-analysis** skill as the command/schema authority. Follow its project gate, metadata resolution, host compatibility, partial-result, request-id, and risk rules.

| Task | Typical route |
| --- | --- |
| Project discovery | `ae-cli project info list` |
| Event/property discovery | `ae-cli analysis-meta event list\|get` |
| Aggregate / SQL exploration | `ae-cli analysis adhoc run\|export --model-type sql` |
| Row sampling | `ae-cli analysis event-detail run\|export` |
| Tag definitions / refresh / members | `ae-cli analysis user-tag ...` |
| User clusters / refresh / members | `ae-cli analysis user-cluster ...` |
| Authorized SQL tag/cluster tables | `ae-cli analysis sql-table list\|columns --usage tag_cluster` |

**Metadata rule**

Every payment event, refund event, amount field, currency field, order ID, and subject field must come from real project metadata.

- If metadata is clear → use it.
- If multiple candidates are plausible → present candidates and ask.
- Never guess.

## 5. Workflow

### Stage 0 — Project gate

**Actions**

1. **Runtime-selected project first.** If the host/conversation runtime exposes an already-selected project (`currentProject`, `project_id` in runtime context, or a project the user has just picked in this conversation), treat it as locked and do **not** re-ask the user to choose.
2. Otherwise reuse an already selected/default project when exactly one is available from `ae-cli project info list`.
3. Only when no project can be resolved from (1) or (2), list accessible projects and ask the user to choose.
4. Lock `project_id` for the run and record it in `analysis_caliber`.

**Restart condition**

- If the project changes, restart the workflow.

---

### Stage 1 — Resolve entity, universe, windows, and transaction caliber

**Load:** `references/entity_universe_caliber.md`

#### 1.1 Resolve the business entity before the field

**Goal:** one row = one real person/customer.

| Scenario | Default subject rule |
| --- | --- |
| General | Start from `#user_id`. Use `#account_id` only when its business semantics and coverage fit the intended person/account entity. |
| MMO single-account-multi-character | Apply only when (a) metadata contains a separately reported stable real-player/account field with verified payment-event coverage, OR (b) the user confirms the project is single-account-multi-character. Then use that verified field for account/player-level RFM. Do not infer the pattern from `#user_id`↔`#account_id` or `#device_id` mapping alone. |
| Other games / e-commerce / SaaS / other | Use `#user_id` by default. Use `#account_id` or a verified custom stable person field only when the business explicitly distinguishes that entity and coverage is acceptable. |
| Explicit role/character analysis | Role/character may be the subject. |

**If MMO has no person-level field**

1. Report the limitation.
2. Do not silently substitute role `#account_id` / `#user_id`.
3. Ask whether role-level RFM is acceptable.

**Record**

- `business_entity`: e.g. `real_player` / `customer` / `account` / `role`
- `subject_field`: exact TE event/property field

#### 1.2 Define and confirm the universe

Universe is a **business caliber**, not an agent-silent default.

| Universe type | Meaning |
| --- | --- |
| `payer_based` | At least one valid paid order in the eligibility lookback |
| `activity_based` | Confirmed active population; F/M may be zero |
| `account_based` | Registered/subscribed accounts meeting a confirmed status rule |
| `custom_cohort` | User-provided or explicitly defined audience |

**Recommendation vs decision**

- For classic customer-value RFM, recommend `payer_based`.
- Do **not** proceed merely because `payer_based` is the recommended default.
- The user must explicitly confirm the universe unless their request already states it unambiguously (for example, “对历史付费用户做 RFM” or an explicit cohort rule).
- Keep universe eligibility separate from the scoring window so historical/lapsed eligible users are retained.

Record:

- `universe_type`;
- exact eligibility rule;
- expected/observed universe size when available.

#### 1.3 Define time windows

Confirm all applicable time calibers before Stage 2:

| Item | Definition |
| --- | --- |
| Eligibility lookback | Who qualifies and where R searches for the latest valid transaction |
| Scoring window | Where F and M are measured |
| Reference timestamp | Anchor for R; default is T-1 23:59:59 in project timezone |
| Refund recognition | Cutoff/mode used to recognize linked refunds |

**Time-range skip exception**

Only when the user's request already explicitly states the relevant time range may that stated range be adopted without re-asking. Partial wording such as “最近” is not explicit.

**Recommendation behavior**

1. Ground the proposal in discovered project facts: payment-event date range, payer scale, and lifecycle signals — never hardcode by industry.
2. Offer a short recommendation set for scoring window and eligibility lookback, plus custom input.
3. Use closed-day alignment by default; state the reference timestamp.
4. Present refund-recognition choice only when refunds exist; otherwise record `gross_only`.

#### 1.4 Discover transaction caliber

Resolve from real metadata and a minimal aggregate probe:

- successful-payment event;
- success condition/status;
- payment amount and unit;
- order/dedup key or confirmed row-count semantics;
- currency and normalization/filter rule;
- refund event/amount/original-order linkage, when applicable;
- F semantics: `attempt_based` or `net_valid`.

**Payment-event candidate heuristic**

1. Pull the event list once via `ae-cli analysis-meta event list`.
2. Use names only for **candidate discovery**, not final semantic confirmation:
   - exact candidates: `payment`, `pay`, `purchase`, `recharge`, `order`, `iap`, `top_up`, `coin_buy`, `diamond_buy`, `cashier`;
   - prefix/suffix candidates: `pay_*`, `*_pay`, `purchase_*`, `*_purchase`, `recharge_*`, `*_recharge`;
   - exclude `ta@*` prefab/template events unless explicitly selected.
3. For the strongest candidate(s), call `analysis-meta event get` and inspect amount/status/order-id fields.
4. Run one aggregate probe for date range, distinct subjects, amount behavior, and success-status behavior.
5. Auto-adopt a payment event only when **one candidate is both unique and semantically verified by metadata/probe**. A name such as `order` alone is never sufficient evidence of successful payment.
6. If semantics remain ambiguous, present the candidate evidence and ask the user to choose.

**F semantics**

- If refunds/returns exist, `attempt_based` vs `net_valid` must be part of the user calibration decision.
- If no refund/return mechanism exists and successful-payment/order dedup semantics are clear, record `attempt_based` explicitly without an extra question.
- Never leave F mode implicit.

#### 1.5 Single Stage-1 calibration gate

Batch unresolved business choices into **one confirmation interaction** before Stage 2. Do not ask them piecemeal unless a later metadata probe reveals a new ambiguity.

The confirmation payload should include:

| Caliber | Agent behavior |
| --- | --- |
| `business_entity` / `subject_field` | Show when ambiguous or non-default |
| `universe_type` + eligibility rule | **Must be user-confirmed unless explicitly stated in the request** |
| eligibility lookback | Confirm/reuse explicit request |
| scoring window | Confirm/reuse explicit request |
| reference timestamp | State together with window |
| payment event + success condition | Auto-adopt only after semantic verification; otherwise confirm |
| `F_mode` | Confirm when refunds/returns make semantics non-trivial |
| refund recognition | Confirm when refunds exist |
| dedup / currency | Confirm only when ambiguous |

**Hard gate:** do not build the R/F/M dataset while any required caliber above remains unresolved.

---

### Stage 2 — Build the R/F/M dataset

#### 2.1 Metric definitions

| Metric | Runtime definition |
| --- | --- |
| `R` | Days from reference timestamp to latest valid transaction inside eligibility lookback; lower is better |
| `F` | Valid order count inside scoring window using confirmed refund/dedup rule |
| `M_raw` | Net paid amount inside scoring window using confirmed refund-recognition rule |
| `M_scoring` | Scoring-only M value after any justified transformation; otherwise `M_scoring = M_raw` |

#### 2.2 Required query shape

**TE table reference**

- Event table: `ta.v_event_{project_id}` (Hive catalog: `hive.ta.v_event_{project_id}`).
- User table: `ta.v_user_{project_id}`.
- `"$part_date"` is a varchar partition column — compare it with string literals (for example `WHERE "$part_date" BETWEEN '2026-07-29' AND '2026-08-27'`), **not** with `date '...'` casts.
- `"$part_event"` is the event-name filter column.
- Always include a `"$part_date"` partition predicate on event-table queries.

1. Construct the eligibility universe.
2. Compute latest valid transaction for R.
3. Build scoring-window payment orders.
4. Apply recognized refunds using the confirmed refund mode/cutoff.
5. Aggregate F and M by subject.
6. LEFT JOIN F/M back to the universe.

**Lapsed-user rule**

For eligible subjects with no scoring-window orders:

```text
F = 0
M_raw = 0
M_scoring = 0
```

Never define the universe from the scoring-window payment query alone.

**Refund rule**

Do not assume the refund query uses the same date range as payment. Follow the confirmed refund-recognition mode.

#### 2.3 Working artifact

Create `./artifacts/rfm_raw_metrics.csv.gz` only when needed for computation.

- It is a working file.
- It is not a user-facing deliverable unless requested.

---

### Stage 3 — Data quality and identity quality

Before scoring, check all items:

- [ ] Subject-field null/empty rate
- [ ] MMO custom person-field coverage on the payment event
- [ ] Duplicate order rate / dedup behavior
- [ ] `refund > payment` anomalies
- [ ] Unmatched refund anomalies
- [ ] Negative/zero net amount behavior
- [ ] Currency consistency
- [ ] R/F/M missingness
- [ ] Impossible R/F/M values
- [ ] Recovered lapsed-user count: eligible users with no scoring-window orders

**MMO missingness rule**

If the custom person-level field has material missingness:

1. quantify the dropped population;
2. quantify the dropped revenue;
3. report the impact before proceeding;
4. do not fall back to role `#account_id` without user approval.

Stage 3 DQ findings and the planned tie-aware band boundaries are surfaced in the final report (`segment_quality` table and `rfm_scoring_rule` table); no separate interim data-health brief is emitted. When an anomaly requires a user decision (caliber must change, severe distribution skew, material field missingness, MMO custom-field missingness), stop and ask before scoring; otherwise proceed directly to Stage 4.

---

### Stage 4 — Choose the scoring design

**Load:** `references/scoring_standards.md`

#### 4.1 Per-metric band resolution

Treat band count as a **metric-level data-resolution outcome**, not a model-wide constraint.

For each of R, F, and `M_scoring` independently:

1. Record `requested_bands` (normally 3 or 5; business thresholds may define another supported count).
2. Inspect distinct values, tie concentration, zero mass, and usable cutoff gaps.
3. Enforce the hard rule **same raw value → same score band**. Never split tied values to balance counts.
4. Derive `effective_bands` after tie-aware cutoff adjustment.
5. If one metric collapses (for example F from 5 to 3), do **not** force R/M to collapse merely for uniformity.
6. Record the runtime `band_profile`, e.g. `R5-F3-M5`, and the reason for every `effective_bands < requested_bands`.

Priority order:

```text
same-value-same-band
  > preserve each metric's usable resolution
  > operational actionability/readability
  > uniform band count
  > equal band population
```

Do not rely on user-count thresholds alone.

#### 4.2 Choose exactly one segmentation mode

1. Rule-based RFM + business thresholds
2. Rule-based RFM + quantile thresholds
3. Data-driven clustering, only when explicitly requested or clearly justified

#### 4.3 Required handling

- [ ] Do not split identical values across bands just to equalize counts.
- [ ] Diagnose M skew.
- [ ] Preserve `M_raw`.
- [ ] Transform/cap only `M_scoring`, and only when justified.
- [ ] Record thresholds or cluster-centre logic.
- [ ] Record the reason for the chosen method.

---

### Stage 5 — Score and segment the full universe

#### Rule-based RFM

1. Score R, F, and `M_scoring` independently using each metric's own tie-aware `effective_bands`.
2. Preserve raw per-metric `R_score/F_score/M_score`, `requested_bands`, `effective_bands`, adjustment reason, and runtime `band_profile`.
3. Convert each raw metric score to `R_level/F_level/M_level` using the effective-band semantic mapping in `references/scoring_standards.md` §2.4.
4. Apply the default lifecycle-oriented mapping to semantic levels unless the business has an approved alternative. Mixed profiles such as `R5-F3-M5` use this same path and require no special approval.
5. The optional 5-band-native extension may run **only when R, F, and M all have `effective_bands=5`** and the business explicitly approves it. It must split users *within* the already assigned default `champions` / `loyal` cohorts; it must not change the other seven lifecycle boundaries.

#### Coverage rule

Every universe member must receive exactly one segment.

#### Diagnostic sub-profiles

Keep optional `sub_profile` diagnostics when useful, e.g.:

- high-frequency / low-value;
- low-frequency / high-value;
- other materially distinct F/M shapes.

These diagnostics prevent broad lifecycle segments from hiding meaningful differences.

#### Working artifact

Create `./artifacts/rfm_segments.csv.gz` only:

- when needed for later joins; or
- when the user requests the user-level file.

---

### Stage 6 — Validate before operationalization

**Load:** `references/validation_rules.md`

#### 6.1 Hard validation

Limit hard gates to mathematical/data consistency, including:

- coverage;
- no overlap / one subject per row;
- same-value-same-band tie preservation;
- requested/effective band-resolution integrity;
- scoring direction and boundary consistency;
- total revenue reconciliation;
- lapsed-user retention;
- entity integrity.

#### 6.2 Diagnostics

Business-shape expectations are diagnostics, not hard gates.

- Explain anomalies.
- Do not manipulate thresholds merely to make business patterns look "normal".

#### 6.3 Stability and migration

Do **not** rerun a prior-period RFM by default for a standard one-shot analysis; that can nearly double query cost.

Assess temporal stability/migration only when one of these is true:

- the user explicitly asks for it;
- an existing prior snapshot makes the check low-cost; or
- production operationalization is requested and the comparison can be completed at reasonable cost without materially delaying the primary result.

Otherwise:

- render the primary validated RFM result first;
- state `stability/migration not assessed`;
- do not mark this as a hard failure.

Never call shifted-window testing "bootstrap".

#### 6.4 Operationalization gate

- Any hard validation failure → block tag/cluster creation and return to the relevant earlier stage.
- Diagnostic anomalies → explain; do not auto-fail.

#### 6.5 Script limitation

`scripts/validate_segments.py` checks only file-level invariants:

- null/empty or duplicate subject;
- invalid R/F/M fields;
- null/non-integer/out-of-range scores;
- lifecycle segment-key validity (or custom mode when explicitly selected);
- same raw metric value mapped to multiple score bands;
- contiguous score coverage and optional `*_effective_bands` consistency;
- basic score-direction monotonicity;
- per-segment summary.

Passing the script does **not** equal passing the full hard validation set.

---

### Stage 7 — Render the user-facing result deterministically

**MUST load**

- `references/output_format.md` — renderer, embedded template, locale and self-check rules
- `assets/output_contract.yaml` — language-neutral result schema and fixed core-table columns
- `references/dynamic_strategy.md` — dynamic per-segment strategy generation grounded in project metadata
- `references/strategy_profiles.md` — fallback / guardrail archetype library

#### 7.1 Rendering sequence

1. Build the language-neutral result object defined in `assets/output_contract.yaml`.
2. Resolve `output_locale` once:
   - explicit user preference;
   - otherwise current request language;
   - otherwise conversation dominant language.
3. Choose exactly one status: `SUCCESS`, `PARTIAL`, or `FAILED`.
4. Fill the matching embedded template in `references/output_format.md`; do not redesign the response structure.
5. Localize only user-facing labels/content. Preserve raw identifiers, acronyms, event/property names, and persistent AE names.
6. Use the fixed core-table column schemas and order from `assets/output_contract.yaml`; data-row count follows the actual result.
7. Put optional R/F/M statistics only in the designated supplementary table; never mutate a core table.
8. Localize each segment display name once and reuse it everywhere in the run.
9. Generate the per-segment `operational_strategy` table dynamically per `references/dynamic_strategy.md`: classify the project archetype from real event/feature evidence, resolve the project-appropriate vocabulary (用户 vs 玩家, real feature nouns), and write objective / actions / KPI grounded in features the project actually has. Use `references/strategy_profiles.md` only as a completeness/direction guardrail or fallback. Do not import foreign archetype vocabulary into a project that lacks those features.
10. Run the mandatory final self-check in `references/output_format.md` and correct any contract violation before sending.

#### 7.2 Output corrections before send

Correct before sending if any of the following occurs:

- mixed user-facing locale;
- missing/reordered required section;
- changed core-table column count/order;
- missing total row in the main segment table;
- inconsistent segment display names;
- fixed row count invented for a dynamic/custom/clustering segmentation.

#### 7.3 Chart rule

Chart output is outside the core contract. Omit by default; add only when explicitly requested or when a reliable host chart surface materially improves readability.

---

### Stage 8 — Optional AE tag creation

**Run only when:** the user explicitly asks to operationalize/create tags.

**Load:** `references/ae_tag_creation.md`

#### 8.1 Pre-write preview

Show:

- project;
- person-level subject field;
- universe;
- scoring window;
- per-metric requested/effective bands and runtime `band_profile`;
- final scoring/segment definitions;
- estimated per-value (segment) counts;
- exact `tag_name` / `tag_display_name` and the exhaustive `tag_value` enumeration (single multi-value tag `rfm_segment`; see `assets/rfm_tag_names.yaml`).

#### 8.2 Confirmation and existing-resource safety

1. Check whether `rfm_segment` already exists before presenting the write action.
2. If it does not exist, require explicit confirmation for **CREATE**.
3. If it exists, treat **UPDATE/REPLACE** as a separate high-risk action: show the existing definition/refresh semantics and the proposed new definition/impact, then require explicit confirmation for the update.
4. Never convert a create approval into update approval implicitly.

#### 8.3 Fidelity rule

The platform tag definition must reproduce the same:

- entity;
- eligibility lookback;
- scoring window;
- refund-recognition rule;
- F rule;
- M scoring rule;
- per-metric `requested_bands` / `effective_bands` / tie-adjustment reasons;
- raw-score → semantic-level mapping;
- thresholds;
- segment mapping.

The tag is a single multi-value SQL tag `rfm_segment` emitting `tag_value` = each universe member's lifecycle segment key (exactly one value per user). Never split the model into per-segment tags. Never replace the real methodology with a simplified one-window SQL that drops lapsed users.

#### 8.4 Post-write verification

1. Execute only the confirmed create/update action. A definition create/update starts computation automatically; do **not** call `user-tag refresh` afterward.
2. Follow the returned `next_action` and poll `user-tag get` until the new result is fresh before reading counts. Use `user-tag refresh` only for an explicit retry or recomputation of an unchanged definition.
3. Compare platform per-value counts (`tag_value` distribution) with analytical segment counts using the same snapshot/caliber.
4. Under the same snapshot/caliber, the expected count difference is `0`; investigate **any** difference rather than accepting a default percentage tolerance.
5. A non-zero tolerance is allowed only when a known timing/backfill/rolling-refresh difference is explicitly documented.

---

### Stage 9 — Optional user-cluster creation

**Run only when:** the user explicitly asks to deliver/bundle one or more RFM segments as activation cohorts.

**Load:** `references/cluster_creation.md`

#### 9.1 Default operational pattern

1. Create the RFM segment tag first.
2. Create user clusters only for segments queued for activation.
3. Do not bundle every segment by default.

#### 9.2 Pre-write preview

For each requested cluster, show:

- project;
- person-level subject field;
- universe;
- scoring window;
- transaction caliber;
- per-metric requested/effective bands and runtime `band_profile`;
- segment and analytical member count;
- `cluster_name`;
- localized display name;
- definition source: tag-value reference vs reproduced SQL.

#### 9.3 Confirmation and existing-resource safety

For each requested cluster, check whether the key already exists.

- New key → require explicit **CREATE** confirmation.
- Existing key → show the existing definition/member semantics and proposed change, then require separate **UPDATE/REPLACE** confirmation.
- Never treat a prior create approval as permission to mutate an existing cluster.

#### 9.4 Fidelity rule

The cluster definition must reproduce the same:

- entity;
- eligibility;
- scoring window;
- refund/F/M rules;
- per-metric `requested_bands` / `effective_bands` / tie-adjustment reasons;
- raw-score → semantic-level mapping;
- thresholds;
- segment mapping.

Never use a simplified one-window SQL that drops lapsed users.

#### 9.5 Post-write verification

1. Execute only the confirmed create/update action. A definition create/update starts computation automatically; do **not** call `user-cluster refresh` afterward.
2. Follow the returned `next_action` and poll `user-cluster get` until the new result is fresh before reading member counts. Use `user-cluster refresh` only for an explicit retry or recomputation of an unchanged definition.
3. Compare platform member counts with analytical segment counts under the same snapshot/caliber.
4. Expected difference is `0`; investigate any non-zero difference unless a documented timing/backfill/rolling-refresh reason justifies an explicit tolerance.

---

### Stage 10 — Downstream analysis

Supported follow-up by RFM segment:

- LTV;
- retention;
- campaign/event conversion;
- cross-period migration;
- segment-level revenue trends;
- segment-level activity trends.

For every follow-up, state:

- project;
- time window;
- metric definition;
- baseline.

Separate observed evidence from causal inference.

## 6. Failure handling

| Failure / condition | Required action |
| --- | --- |
| No accessible project | Stop and report access gap |
| No valid payment event | Stop; do not fabricate a proxy |
| MMO has no person-level entity | Report limitation; ask whether role-level analysis is acceptable |
| Zero eligible users | Report the universe/caliber causing it |
| Quantile cutoffs collapse because of ties / zero mass | Reduce only the affected metric's `effective_bands`, preserve same-value-same-band, record the adjustment, and keep other metrics at their supported resolution; use business thresholds when the remaining resolution is not actionable |
| Tag or cluster write rejected | Read structured error and follow metadata resolution; never guess identifiers |
| `meta.partial:true` | Report failures and retry only retryable items |

## 7. Output policy

- Normal deliverable = deterministic structured inline business result defined jointly by:
  - `references/output_format.md`
  - `assets/output_contract.yaml`
- Working files under `./artifacts/` are not linked unless requested.
- Never return only raw SQL.
- Never return only a model/execution log.
