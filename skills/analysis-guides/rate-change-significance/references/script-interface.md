# analyze.py Interface

Use `scripts/analyze.py` rather than hand-calculating inferential statistics.

## Independent / period-active job

```json
{
  "schema_version": "1.0",
  "scenario": "retention",
  "cohort_event": "login",
  "outcome_event": "login",
  "window_N": 1,
  "window_mode": "exact_day",
  "cohort_design": "period_active",
  "design_type": "pre_post",
  "period_lengths": [7, 7],
  "group_A": {"label": "A", "n": 1000, "outcome": 300},
  "group_B": {"label": "B", "n": 1100, "outcome": 350},
  "overlap": {"count": 500},
  "test": "auto"
}
```

If overlap `rate` is omitted but `count` + both group sizes are present, the script derives `rate = count / min(n_A,n_B)`.

## Paired job

```json
{
  "schema_version": "1.0",
  "scenario": "conversion",
  "cohort_design": "paired",
  "design_type": "pre_post",
  "test": "auto",
  "mcnemar": {"a": 400, "b": 60, "c": 90, "d": 450},
  "paired_context": {"n_A_active": 1400, "n_B_active": 1500}
}
```

`group_A`/`group_B` are optional for a pure paired job.

## Run

```bash
python3 scripts/analyze.py --input job.json --output stats.json
```

Read the JSON result, not stdout, for downstream logic.

Important fields:
- `analysis_status`: `ok` or `blocked`
- `blocked_reason` when blocked
- `test`
- `p_value`, CI/effect fields when a test runs
- `overlap`
- `warnings`
- `recommended_rerun`
- `srm`, `srm_decision`
- paired `n_discordant` and `discordant_pairs_needed_for_80pct`
- independent `mdd_80pct_power`, `n_needed_per_group`, `extra_needed_per_group`

Do not format `null` power/sample-size fields as numeric values.

## Full schema template

Every accepted field, annotated:

```json
{
  "schema_version": "1.0",
  "scenario": "retention | repurchase | conversion | churn | renewal | custom",
  "cohort_event": "<event>",
  "outcome_event": "<event>",
  "window_N": <int>,
  "window_mode": "exact_day | within_window",
  "cohort_design": "first_occurrence | period_active | paired",
  "design_type": "pre_post | concurrent_ab",
  "period_lengths": [<days_A>, <days_B>],
  "group_A": {"label": "...", "time_range": "...", "n": <int>, "outcome": <int>},
  "group_B": {"label": "...", "time_range": "...", "n": <int>, "outcome": <int>},
  "overlap": {"count": <int>, "rate": <float 0..1>},
  "test": "auto | z_independent | mcnemar | fisher_exact",
  "expected_ratio": "<float 0..1, optional — auto-derived from period_lengths when design_type=pre_post; explicit value wins>",
  "paired_context": {"n_A_active": <int>, "n_B_active": <int>},
  "mcnemar": {"a": <int>, "b": <int>, "c": <int>, "d": <int>},
  "fisher": {"a": <int>, "b": <int>, "c": <int>, "d": <int>},
  "output_path": "./artifacts/rate-change-significance/stats.json"
}
```

Field semantics:

- `cohort_design` is consumed by `decide_test()`: paired jobs auto-route to McNemar without `test:"mcnemar"`. `design_type` + `period_lengths` drive `expected_ratio` auto-resolution and the SRM proceed/reject decision.
- `group_A`/`group_B` are required for independent (Z/Fisher) jobs; optional for pure paired jobs that supply `mcnemar` cells.
- `overlap.rate` is auto-derived from `count / min(n_A, n_B)` when only `count` is supplied.
- `paired_context` is optional context for paired jobs; `n_A_active`/`n_B_active` are per-period active cohort counts (the paired sample is a subset). Used for the survivorship caveat in Part 5.
- `expected_ratio` must be strictly between 0 and 1. Auto-resolution precedence: explicit value wins; else `days_A / (days_A + days_B)` when `design_type=pre_post` and `period_lengths` is set; else `0.5`.
- `test:"auto"` is safe for all three designs — the script routes automatically.

## Minimal job variants

For McNemar (paired, from SQL or CSV — `group_A`/`group_B`/`overlap` not required):

```json
{
  "schema_version": "1.0",
  "cohort_design": "paired",
  "test": "auto",
  "mcnemar": {"a": <int>, "b": <int>, "c": <int>, "d": <int>}
}
```

For Fisher's exact (small expected cell fallback — cells auto-built from `group_A`/`group_B` if `fisher` block is omitted):

```json
{
  "schema_version": "1.0",
  "test": "fisher_exact",
  "fisher": {"a": <int>, "b": <int>, "c": <int>, "d": <int>}
}
```

## Null and Infinity handling

The script never emits a bare `Infinity` token. Always check for `null` before formatting these fields in the report:

- `relative_uplift` is `null` when `p_A = 0` (division by zero).
- `n_needed_per_group` and `extra_needed_per_group` are `null` when the observed difference is exactly 0 (no effect to detect).
- `mdd_80pct_power` and `n_needed_per_group` are `null` for McNemar (paired power depends on discordant-pair structure — use `discordant_pairs_needed_for_80pct` instead).
- `discordant_pairs_needed_for_80pct` is `null` when `ψ = 0` (i.e. `b = c`, no observed asymmetry).
- `odds_ratio` (Fisher) is **B vs A** and can be `null` when a finite ratio is undefined because of zero denominator cells; read `odds_ratio_direction="B_vs_A"`.
- `ci_95` (Fisher) is always `null` — Fisher's exact does not produce a CI via the hypergeometric test; use `odds_ratio + p_value` for inference.
- `srm_decision` is `{"decision":"skip","reason":"..."}` for paired design (no traffic split to test).

## Test auto-selection (`decide_test`)

When `test == "auto"`, routing precedence:

1. `cohort_design == "paired"` OR a `mcnemar={a,b,c,d}` block is present → **McNemar**. If `cohort_design=paired` but no `mcnemar` block is provided, the script returns an error — paired McNemar requires the four discordance cells.
2. If either independent group is at rate 0 or 1 (boundary rate) → **Fisher exact**. Same-boundary pairs have observed diff 0; opposite-boundary pairs remain valid Fisher cases.
3. Any expected 2×2 cell < 5 → **Fisher exact**, with cells auto-built from `group_A`/`group_B` for independent designs (`a=r_A, b=n_A-r_A, c=r_B, d=n_B-r_B`). No re-invoke round-trip.
4. Otherwise → **two-proportion Z-test** (independent).

You may explicitly request a compatible independent test, but `fisher_exact` is never valid for paired matched outcomes. Prefer `test:"auto"`; paired jobs route to McNemar automatically.
