# RFM Validation Rules

> Canonical Stage 6 validation. Keep hard correctness checks separate from business diagnostics.

## 1. Hard validation — blocks operationalization

All hard checks must pass.

| # | Hard check | Requirement |
| ---: | --- | --- |
| 1 | Universe coverage | Assigned subjects = eligible-universe subjects |
| 2 | Exactly-once assignment | Each subject has one and only one segment |
| 3 | No null segment | Final mapping contains no null segment |
| 4 | Metric validity | `R>=0` unless future-dated events are explicitly valid; `F>=0`; `M_raw` follows confirmed net/gross rule |
| 5 | Tie preservation | Within each metric, one identical raw value maps to exactly one raw score; no tied value is split to balance band counts |
| 6 | Band-resolution integrity | For each metric: `effective_bands <= requested_bands`; scores are contiguous `1..effective_bands`; every effective band is non-empty; any reduction has an `adjustment_reason` |
| 7 | Scoring direction | Lower R cannot get a worse score solely because of boundary logic; higher F/`M_scoring` cannot get a worse score solely because of boundary logic |
| 8 | Boundary consistency | Implemented operators match `scoring_standards.md` exactly |
| 9 | Revenue reconciliation | Sum of segment `M_raw` equals universe `M_raw` within expected numerical tolerance |
| 10 | Lapsed-user retention | Eligible users with `F=0` remain in the result and are not lost through an inner join / scoring-window-universe bug |
| 11 | Entity integrity | Chosen person-level field has acceptable coverage; MMO must never silently fall back from custom person-level `account_id` to role `#account_id` |
| 12 | Mapping compatibility | Mixed-band profiles route through semantic levels; 5-band-native extension is used only when R/F/M all have `effective_bands=5` and only splits eligible parent cohorts |

**On any hard failure**

Return to the relevant earlier workflow stage.

## 2. Diagnostic expectations — never auto-fail

These are interpretation signals, not correctness gates.

| Diagnostic | Interpretation guidance |
| --- | --- |
| Champions | Tend to have high `M_raw` / F and recent R |
| Lost High-Value | May have higher historical/current mean value than Champions; this can be a legitimate churn-whale pattern |
| At Risk | Tends to be less recent, but average F does not have to be the lowest |
| High Champions share | Can be legitimate in a VIP-heavy product |
| High Hibernating + At Risk share | Can be legitimate in a mature/churn-heavy product |
| Revenue concentration | Does not need to follow an 80/20 pattern |

When distributions are skewed, use medians/quantiles alongside means.

## 3. Segment-quality indicators

Default summary metrics:

- runtime `band_profile` and per-metric requested/effective band counts;
- tie concentration / band-collapse notes when material;
- user count / share;
- total `M_raw` / revenue share;
- median or mean R/F/`M_raw` when useful;
- sub-profile mix when materially heterogeneous;
- zero-window-activity share.

Flag segments that are:

- too small for reliable operations; or
- too broad to be actionable.

## 4. Temporal stability and migration

### 4.1 Terminology

Do **not** call shifted-window testing "bootstrap".

### 4.2 Temporal stability

Temporal stability is **not a default second full RFM run** for every analysis.

Run it only when the user asks, an existing prior snapshot makes it low-cost, or production operationalization warrants the check and query cost is reasonable.

When run:

1. reuse an existing comparable snapshot when possible; otherwise rerun the same fixed methodology on the prior reference date/window;
2. compare:
   - segment-share change;
   - threshold movement, when thresholds are recomputed;
   - key segment revenue-share movement.

For pure methodology stability:

- prefer holding business definitions fixed;
- explicitly state whether thresholds were recomputed or frozen.

### 4.3 Cross-period migration

When per-user snapshots exist, compute:

```text
previous_segment -> current_segment
count / share
```

Highlight meaningful flows such as:

- Champions → Loyal
- Champions → Lost High-Value
- Potential → Champions

### 4.4 When no comparison exists

State:

```text
stability/migration not assessed
```

This is **not** a hard failure.

## 5. GO / NO-GO

| Result | Condition | Operational implication |
| --- | --- | --- |
| **GO** | All hard checks pass; diagnostic anomalies are explained or clearly flagged | Tag/cluster creation may proceed after explicit user confirmation |
| **NO-GO** | Any hard correctness check fails | Do not create tags/clusters |
