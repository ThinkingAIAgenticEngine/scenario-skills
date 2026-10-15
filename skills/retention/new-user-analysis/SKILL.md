---
name: new-user-analysis
description: Trigger when the user asks to analyze new-user quality, first-day behavior, new-user retention/churn, channel quality for new users, or structural changes in newly acquired users. The Skill first asks the user to confirm the new-user definition (caliber), analysis dimensions, product type, and time range, then validates event/property metadata and sample quality before querying business data. It scores first-day quality (engagement depth, feature adoption, monetization readiness, retention signal), analyzes first-day behavior paths and funnels, attributes D1/D3/D7 retention to first-day behaviors and acquisition channels, and diagnoses structural mutations in the new-user mix. Use ae-cli event/path/retention/funnel/sql models and deliver Markdown or HTML reports depending on analysis depth. Do not trigger for existing-user retention/churn or requests to create a new/old user classification property.
---

# New User Analysis (新用户分析)

> **One-line positioning**: Lock down the "new user" definition with the user, then deliver the right depth of analysis — from a quick cohort check to a full structural-mutation diagnosis.
> **Data source**: ThinkingData via ae-cli (event / path / retention / funnel / sql models; SQL is verified for cross-event time alignment — see `references/data-validation.md` §4.3.5).
> **Output style**: 结论先行，结构化表格，红黄绿灯标识；语言跟随用户提问语言。

## When to Activate

Trigger phrases: new user definition / caliber / first-day quality / new user cohort / new user structural mutation / new user retention anomaly / channel quality / activation analysis / LTV prediction / behavior sequence / path analysis / first-day funnel.

## Not Applicable (Do NOT Activate)

- Existing-user retention/churn → use a dedicated retention-diagnosis Skill.
- Short-drama retention → use the dedicated short-drama retention Skill.
- Creating or defining a new/old user classification property → use `new-old-user-define`.
- Single-user behavior inspection or individual churn diagnosis → use `single-user-inspector`.

---

## 0. Boundary & Stop Conditions

This Skill handles **new user cohort analysis only**. **STOP** (do not proceed) when:

1. The project has **no identifiable new-user signal** (no register / first-launch / activation event) — the caliber cannot be confirmed.
2. The user needs **existing-user retention**, order-level revenue attribution, or a client-branded report.
3. **Minimum viable data** is missing: one new-user signal event + one identity field (`#account_id` or `#distinct_id`) + `event_time`. Without these, ask the user to confirm the caliber / fix tracking first.

---

## 1. Analysis Levels (choose depth by intent, not always Phase 1→5)

Select the level matching the user's actual question. Every level reuses the shared state machine (§2) and the same phases; higher levels simply go deeper.

| Level | User intent | Deliver | Skip |
|-------|-------------|---------|------|
| **L0** Quick cohort check | "分析过去 7 天新增情况" | Caliber confirm + scale trend + property coverage + D1 | Path, mutation, drill-downs |
| **L1** First-day quality score | "新用户质量怎么样？" | L0 + 4-dimension score + weakest dimension | Behavior path, drill-downs |
| **L2** Behavior sequence | "新增用户为什么流失？" | L1 + Top paths + funnel + entropy | Channel/geo deep-dive |
| **L3** Retention attribution | "哪些首日行为/渠道决定留存？" | L2 + dimension×retention + first-day-behavior×retention lift + cross-dimension low-quality cohort | Structural mutation |
| **L4** Structural mutation | "新增结构是否变了？" | L1/L2 essentials + baseline compare + root-cause + optional drill-down | Running all 3 drill-downs by default |

**Rule**: Always start at the lowest level that answers the question. Escalate only when an anomaly fires or the user asks. A Phase 5 mutation is required context only for L4.

---

### Quick Start (minimum L0 path)

```
ae-cli team +list-projects                        # 找 project_id
# 问用户口径 → 得事件名（如 register）
ae-cli analysis-meta event list --project-id <pid>  # 确认事件存在
# 进入 §2 Gate B → §3 Phase 1，再按层级选 Phase 2/3/4/5
```

> 完整 model JSON 格式与已测字段：`references/data-validation.md` §4.3。

---

## 2. Shared Execution State Machine

Every level runs through these four gates in order. Do not skip gates.

**Terminology anchor (D0 / 首日 / first-day are the SAME thing — the register day):** `D0` = `首日` = `first-day` = the new user's registration day itself. `D1` = the calendar day AFTER registration (next-day return). `D3`/`D7` = 3 / 7 days after registration. All three terms — D0 (English date shorthand), 首日 (Chinese), first-day (English) — refer to the same register-day behavior window and MUST be treated as interchangeable. Never confuse 首日 (D0) with D1 (次日).

```
Confirm  →  Validate  →  Analyze  →  Verify
 口径/维度/类型/周期  事件/身份/样本   按层级执行     对账/结论/复查窗口
```

**Hard stop before any business-data query**: the Analyze gate (Gate C) may NOT run until BOTH the new-user caliber (Gate A) AND the analysis dimensions (Gate A) have been explicitly confirmed by the user, AND Gate B has verified both the event AND user property tables. Running a business-data query on an unconfirmed caliber or unconfirmed dimensions is a violation.

### Gate A — Confirm (确认口径、维度、产品类型、周期)

- **Project ID**, **product type** (Game / E-commerce / Social-Content / SaaS-Tool / Utility / Other), **time range** — all required.
- **New user caliber — ALWAYS ask, never auto-arbitrate.** This is a business decision owned by the user. Present options:

  > 你们团队当前怎么定义「新用户」？常见选项：① 首次启动（ta_app_start / app_open）② 注册（register / signup）③ 首次激活（tutorial_complete / level_1）④ 其他（请描述事件名或口径）

- **Analysis dimensions — ALWAYS ask, never auto-arbitrate.** Before querying, list the candidate dimensions you found in metadata and let the user pick which to analyze. Never silently decide which dimensions to cover, and never claim "no such dimension exists" before you have checked BOTH the event-property table AND the user-property table (see Gate B). Typical dimensions: channel, region/country (often a user property like `channel@country` or `#vp@region`), device/os, server/区服, traffic source (ad/media_source/campaign), monetization (payment/purchase/paywall). Present them and ask which to include; do not assume region is unavailable just because it is absent from the register event.

- Use the user's event name **verbatim** for all downstream phases. If the user defers, default suggestion is **register**, but do not impose it.
- **L3 (retention attribution)**: also collect the **retention windows** (D1 / D3 / D7 — default all three) and the **return event** for retention (default `login`, confirm with the user). Lift thresholds live in `references/retention-attribution.md` §1, not here.
- **L4 only**: also collect **baseline period** and **comparison period**. Default if skipped: baseline = 4-week average from 2 months ago; comparison = last 7 days.

> Caliber reference table (for explaining options, never for deciding): see `references/product-type-configs.md` §0. Note: Register ⊂ Launch; First-Pay is a business milestone, not a caliber.

### Gate B — Validate (事件、身份、样本、可用维度)

After the caliber is fixed, verify it is queryable (to catch tracking gaps, not to decide the caliber):

1. Confirm the event exists: `ae-cli analysis-meta event list --project-id <pid>`.
2. Check identity + key-property coverage: `#account_id` / `#distinct_id`, `channel`, `device_model`, `region`.
3. **Check BOTH property tables before concluding any dimension is missing.** A dimension absent from the register event may live in the user-property table. Query the user table explicitly: `ae-cli analysis-meta property list --project-id <pid> --table-type user`. Only after checking **both** `event` and `user` tables can you state "dimension X unavailable". Never conclude from a single event's props alone.
4. Run low-sample + synthetic-data checks.

**Low-sample tier (single source of truth: `references/data-validation.md` §3.1)** — 3 tiers, always apply before scoring.

**First-day isolation check (hard gate for L1/L2 scores)**: confirm the numerator is the **new user cohort's register-day (D0/首日) behavior**, not blended with returning users. If a metric cannot be isolated to new users, do **not** issue a full composite score — output "available-dimension score + unscorable reason" instead.

### Gate C — Analyze (按层级执行)

Run only the phases required by the chosen level (phase minimal steps in §3). Load the reference file for each phase **before** executing (Reference Router in §4).

### Gate D — Verify (对账、结论、复查窗口)

Before delivering, run the validation gate in `references/drilldown-dimensions.md` §5 (trend-tail alignment, split-sum reconciliation, share-denominator sanity, no hardcoded column names). For every recommended action, specify a re-check window (e.g., "re-run Phase 2 in 14 days and compare D1"). Record the caliber + baseline in every report for cross-run traceability.

### Gate E — Hand Back to User (结论交付后，给选项让用户选)

**After the analysis conclusion is delivered, STOP and hand control back to the user.** Do NOT auto-run the next phase, and do NOT auto-generate a report file. Present the conclusion inline, then explicitly offer the next-step options and let the user choose. This applies at every level — after L0, after L1, and so on. The user owns the escalation decision; the agent only recommends.

1. **Report output is opt-in, never automatic.** HTML/Markdown report files are produced ONLY after the user explicitly asks (e.g. "输出报告" / "生成报告" / "导出"). Until then, deliver conclusions inline in the chat. Do NOT call `present_files` or write to `outputs/` on your own initiative.
2. **Disclose what was NOT analyzed.** In the same next-step menu, explicitly list what a deeper level can still add (e.g. "D3/D7 留存（需足够观察窗口）、渠道×留存交叉、首日行为路径"). Never let the user assume D1 was the whole picture — surface the un-analysed dimensions so the escalation choice is informed.
3. **Present next-step options and wait.** After the inline conclusion, end with a short menu of concrete, level-appropriate options (e.g. "① 补 D3/D7 留存 ② 深挖渠道×留存 ③ 输出 HTML 报告 ④ 结束"), and wait for the user to pick. Do not chain into the next phase autonomously.

---

## 3. Phase Minimal Steps

Four phases (reused by all levels). Each phase = the minimum executable steps; details live in references.

### Phase 1 — Caliber Confirmation
1. Collect required info (Gate A).
2. Ask for the caliber (mandatory).
3. Ask which analysis dimensions to cover (mandatory) — present the candidate dimensions discovered from BOTH property tables, let the user pick, never auto-arbitrate.
4. Verify data quality of the chosen caliber and dimensions (Gate B).
5. Output: confirmed caliber (verbatim) + confirmed dimensions + data-quality notes (e.g., "channel missing for 65% of users"). **No comparison table** — the caliber is a stated fact, not a computed recommendation.

### Phase 2 — First-Day Quality Scoring
1. Query first-day behavior: session count/duration, feature usage, monetization signals, retention markers.
2. Compute 4-dimension scores (Engagement Depth / Feature Adoption / Monetization Readiness / Retention Signal) using product-specific weights from `references/product-type-configs.md`.
3. **Confirm the monetization-readiness caliber before scoring.** "Readiness" is the readiness event (paywall_view / shop_open / purchase), NOT the actual-payment outcome (payment). If no paywall/readiness event exists, ask the user which event to use as the intent proxy — do not silently substitute `payment`.
4. Weighted composite + benchmark compare (`references/industry-benchmarks.md`).
5. Output score dashboard + weakest dimension + top 3 opportunities.

> **Verified model reference**: retention uses `--model-type retention`; feature adoption uses `--model-type event` + `metrics`. See `references/data-validation.md` §4.3 for exact JSON.

### Phase 3 — First-Day Behavior Sequence
1. **Auto-discover** first-day Top-15 events by coverage → **user confirms** 5–8 key events (preset fallback in `references/product-type-configs.md` §2).
2. Extract per-user first-day paths (`--model-type path`; `source_event` must be in `included_events`).
3. Path distribution: group identical paths, Top 10, flag bounce (len=1) and len>8.
4. Funnel drop-off: define steps as **strict-funnel** (forced dependency) or **guided-journey** (skippable; use key-node reach rates). A >40% single-step drop is a red flag. Funnel window semantics are still unverified → prefer event-model fallback (see `data-validation.md` §4.3.6).
5. Action entropy: `H = -Σ(p_i·log2(p_i))`, normalized `H/log2(N)`. Interpretation (robotic/focused/exploratory/chaotic) + product-type relativity in `references/path-analysis-guide.md` §2.
6. Output paths + funnel + entropy + key insight.

### Phase 4 — Retention Attribution (留存归因，L3 专属)

Answer "which dimensions and which first-day behaviors drive retention" — the highest-value extension beyond pure cohort description.

1. **Confirm retention windows & lift thresholds** (Gate A, mandatory): which retention labels to use (D1 / D3 / D7 — default all three), and the lift thresholds. Default thresholds (single source of truth: `references/retention-attribution.md` §1): critical ≥ +10pt, effective +5~+10pt, weak <+5pt, negative <0.
2. **Dimension × retention**: split the new-user cohort by each confirmed dimension (channel / region / serverid / traffic source), compute D1/D3/D7 retention per segment. Identify high-retention and low-retention segments; flag "high-scale + low-retention" segments (the highest-priority problem).
3. **First-day behavior × retention lift**: for each key first-day behavior, split users into "did X on D0 (首日, register day)" vs "did NOT do X on D0", compute retention for both groups, output the lift (absolute pt as primary, relative as secondary). Method + thresholds in `references/retention-attribution.md` §2.
   - **Key behaviors MUST come from the user, never self-selected.** The behavior list flows from Phase 3's auto-discovered Top-15 + user confirmation. **If the user jumped straight to L3 without running Phase 3 (no confirmed key-behavior list exists yet), you MUST first run the first-day behavior-coverage discovery (§Phase 3 step 1 auto-discover), present the full penetration-rate table to the user, and ask which behaviors to run lift on. Do NOT pick behaviors yourself — even 2–3 "obvious" ones like draw_card or battle_start.**
4. **Cross-dimension localization** (only when a low-retention cohort fires or user asks): minimal two-way cross (dimension × dimension, dimension × key-behavior) to localize the specific low-retention population. Templates in `references/retention-attribution.md` §3.
5. Output: retention-attribution dashboard (key behaviors ranked by lift + low-retention dimensions + cross localization) + one-line root cause + recommended focus. Every "key behavior" must carry a sample-size flag per `references/retention-attribution.md` §1.

### Phase 5 — Structural Mutation Diagnosis
1. Define baseline vs comparison windows (Gate A).
2. Run 6 detection methods (channel mix / device-region / behavioral / value / traffic source / geo concentration) — thresholds in `references/industry-benchmarks.md` §8.
3. For each fired mutation, apply the matching `references/root-cause-rules.md` rule (Trigger → Hypotheses → Validate → Action). **Never present a mutation without at least one validation step.**
4. Optional drill-down (**only when a mutation fires or user asks**): organic-vs-paid / geo Top10 / channel ranking — `references/drilldown-dimensions.md` §1–3. Confirm field placeholders (`{traffic_source}` / `{region}` / `{channel}`) with the user first.
5. Run Gate D validation, then output mutation dashboard + root-cause + owner + next check date.

---

## 4. Reference Router (load before each phase)

| When | Load |
|------|------|
| Any ae-cli command, auth, model JSON, low-sample tiers, error recovery | `references/data-validation.md` |
| Phase 1 caliber options + Phase 2 weights/thresholds + Phase 3 event presets | `references/product-type-configs.md` |
| Phase 2 benchmark values | `references/industry-benchmarks.md` |
| Phase 3 path/entropy/funnel methodology | `references/path-analysis-guide.md` |
| Phase 4 retention-attribution methodology + lift thresholds + cross templates | `references/retention-attribution.md` |
| Phase 5 mutation thresholds + root-cause rules | `references/industry-benchmarks.md` §8 + `references/root-cause-rules.md` |
| Phase 5 drill-downs + tiered thresholds + validation gate | `references/drilldown-dimensions.md` |
| Report templates | `references/report-templates.md` |
| SQL (verified for cross-event time alignment) | `references/sql-templates.md` |

---

## 5. Degradation Strategy

When data falls short, degrade instead of failing. Full matrix in `references/data-validation.md` §7. Headline rules:

- No `register` → proxy with `first_launch` / `app_open` (over-counts ~15-25%)
- No `payment` → proxy with `paywall_view` / `store_open` as monetization-readiness
- No tutorial/feature events → drop Feature Adoption, renormalize to remaining 3 dimensions
- Low sample (<50/day) → aggregate to monthly, suppress daily scores

---

## 6. Execution Rules (non-negotiable)

1. **Data authenticity**: every metric from real ae-cli queries — no fabrication, no placeholder values.
2. **Confirm caliber AND dimensions before querying**: never run a business-data query, never claim "no such dimension", and never score before the user has confirmed (a) the new-user caliber AND (b) the analysis dimensions. Metadata-only discovery (event list / property list) is allowed before confirmation; business-data queries (event/path/retention/funnel models) are NOT.
3. **Check both property tables**: a dimension must be declared "unavailable" only after checking BOTH the event-property table and the user-property table (`analysis-meta property list --table-type user`). Never conclude from one event's props.
4. **Single source of truth**: sample rules → `data-validation.md`; weights/thresholds → `product-type-configs.md`; mutation thresholds → `industry-benchmarks.md` §8; drill-down thresholds → `drilldown-dimensions.md` §4. Do not restate values in this file.
5. **Progressive escalation**: start at the lowest level that answers the question; escalate only on anomaly or request.
6. **First-day isolation**: unscorable metrics → no composite score, report the gap.
7. **Output format by level**: L0/L1 = Markdown; L2/L3/L4 = HTML (Chart.js) only when multi-period trends or multi-dimension structures are shown; otherwise Markdown. Save self-contained files to `outputs/`.
8. **Report file is opt-in**: deliver conclusions inline by default; only generate the HTML/Markdown report file (and `present_files` it) after the user explicitly asks for a report. Never auto-emit a report.
9. **Hand back control**: after each level's inline conclusion, present next-step options and wait for the user to choose — never auto-escalate to the next phase or auto-generate a report.
10. **Language**: follow the user's language; bilingual labels when Chinese.
11. **Error recovery**: on ae-cli error, consult `references/data-validation.md` §5 immediately (need_clarification / PROJECT_TZ_DISABLED / INVALID_CAPABILITY_INPUT / AI_QP_COMPILE_FAILED / has_more / CAPABILITY_PERMISSION_DENIED / QUERY_TIMEOUT / missing-$part_date-predicate).
12. **Never self-select the caliber, dimensions, or key-behavior list** — all three are user-owned decisions (see Phase 4 step 3 for the jump-straight-to-L3 handling).

---

## 7. File Index

| File | Purpose |
|------|---------|
| `references/data-validation.md` | ae-cli commands, model JSON formats (verified), low-sample tiers, error recovery, degradation |
| `references/product-type-configs.md` | Caliber reference, product weights/thresholds, event presets, composite anchors |
| `references/industry-benchmarks.md` | Benchmark values (D1/session/feature/monetization) + mutation thresholds |
| `references/path-analysis-guide.md` | Path/entropy/funnel methodology + product-type relativity |
| `references/retention-attribution.md` | Phase 4 retention-attribution methodology: D1/D3/D7 lift thresholds, behavior×retention split method, cross-dimension templates |
| `references/root-cause-rules.md` | 6 mutation rules: Trigger → Hypotheses → Validate → Action |
| `references/drilldown-dimensions.md` | Organic/paid, geo Top10, channel ranking + tiered thresholds + validation gate |
| `references/report-templates.md` | Report templates (Markdown L0/L1, HTML L2/L3/L4) |
| `references/sql-templates.md` | SQL templates — verified; table/column naming per `data-validation.md` §4.3.5 |

---

## 8. FAQ

**Team already has a fixed definition?** Use it verbatim. Phase 1 is confirmation, not arbitration — just validate data quality and document the definition.

**First-day data incomplete?** Label affected dimensions "data unavailable"; score with available dimensions only; flag the gap.

**Multiple product lines in one project?** Run separate analyses per product line via a `product_line` filter; never mix cohorts.

**Behavior sequences too diverse (no dominant path)?** High entropy is itself a finding. Segment by channel/device; if still high, investigate UI confusion or tracking errors.

**Mutations detected but nothing external explains them?** Escalate to fraud investigation; label "unexplained anomaly — investigate manually."

**<50 new users/day?** Monthly aggregation only; suppress daily scores; consider extending the window for sample size.

**User jumped straight to L3/L4 without a confirmed key-behavior list?** See Phase 4 step 3 — do NOT self-select behaviors; run the discovery query and ask the user first.
