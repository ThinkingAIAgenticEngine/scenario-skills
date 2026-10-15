# Judgment Parameters (Universal Edition)

> **Sole policy authority for every numeric threshold and confidence tier in this skill.** Runtime scripts mirror these values as executable constants and must be updated together with this table; this file wins if they ever differ.

> **【MUST·threshold single-source rule】** SKILL.md and other narrative references may reference threshold names (e.g., "dual threshold", "SUBGROUP_DEFECT_THRESHOLD") but MUST NOT repeat their numeric values. Executable scripts may encode the values only to implement this table and must not redefine their semantics. When adding or changing a threshold, update this table first, then keep runtime constants aligned.

---

## 1. Thresholds (numeric judgment parameters)

| Parameter | Value | Use |
|------|-----|------|
| INFLECTION_ABS_THRESHOLD | 0.3 pp | threshold A absolute change |
| INFLECTION_REL_RATIO | 0.015 (1.5%) | threshold A relative base-rate ratio |
| INFLECTION_CUM_THRESHOLD | 0.5 pp | threshold B cumulative same-direction change |
| INFLECTION_CUM_MIN_DAYS | 3 days | threshold B min consecutive same-direction days |
| TREND_INFLECTION_PP | 0.5 pp | shape judgment: weekly decline/rise ≥0.5pp to judge A/C inflection |
| DAU_CONSECUTIVE_DECLINE_DAYS | 4 days | DAU consecutive-decline judgment days |
| DAU_FLUCT_THRESHOLD | 5.0% | DAU fluctuation magnitude threshold |
| **TREND_ABNORMAL_THRESHOLD (anomaly judgment)** | **reuse trend-inflection dual threshold: day-over-day change ≥ max(0.3pp, first-day penetration × 1.5%), or consecutive ≥3 days same-direction with cumulative ≥0.5pp** | **Part 4 step 1's sole standard for "anomaly judgment", uniform across all dimensions, no per-dimension exception**. Judgment object is "each group's intra-group penetration within a dimension, its time trend over the full N-day series", not between-group difference, not first/last difference. Missing or flat days break a consecutive run |
| SUBGROUP_DEFECT_THRESHOLD | max(2.0 pp, group mean × 10%) | single subgroup below mean judged anomalous (Part 4 step 2b "single-subgroup problem"); relative + absolute dual threshold, avoiding fixed 2pp misfiring in low/high penetration scenarios. A single group falling alone is more dangerous than all falling together, so the threshold is not relaxed |
| SUSPECT_DEVIATION_THRESHOLD | 2.0 pp | Part 3 suspect-bucket deviation: a single group underperforming aggregate penetration by ≥2pp → suspect bucket (candidate for Part 4 drill-down); fixed absolute value, not floating with magnitude |
| VERSION_DEFECT_THRESHOLD | 2.0 pp | version / intra-group penetration significant-difference threshold (≥2pp = significant); qualitative use, fixed value, not floating with magnitude |
| NULL_RATE_DELTA_THRESHOLD | 3.0 pp | entry-source null-rate first/last-day change threshold (≥3pp = tracking anomaly) |
| NEW_USER_DAYS | same day (0 days) | new-user definition: **registration day** (`{new_user_field} = $part_date`), not "registered within last N days" |
| TREND_ACCEL_RATIO | 1.5× | trend acceleration: incremental analysis key-metric change magnitude ≥ 1.5× previous window triggers forced re-verification |
| NET_TREND_DISPLACEMENT | 0.5 pp | dim_analyzer.py auxiliary net-trend hint: first-half vs second-half mean displacement must be ≥0.5pp (Part 4 step 1a mechanical context) |
| NET_TREND_NOISE_RATIO | 2× | dim_analyzer.py auxiliary net-trend hint: the displacement must also be ≥2× the day-over-day noise σ (filters random-walk); the hint does not replace the dual-threshold result or the main agent's daily-series shape judgment |
| **SAMPLE_CONFIDENCE_TIERS** | **n≥1000 High / 500≤n<1000 Medium / 100≤n<500 Low / n<100 Very Low** | **sub-dimension group's intra-group penetration sample-size confidence tiers** (see §2 below). Used to label "how credible this intra-group rate judgment is"; Very Low groups are not rated, listed as data only. Note the relationship with `--min-dau 200`: <200 hard-excluded as noise, 200-500 kept but labeled Low |

> **Key metric definition**: the "key metric" in `TREND_ACCEL_RATIO` = the **suspect-dimension metric** that entered root-cause attribution (Part 4/5) in the prior round (e.g., new-user penetration, some entry-source penetration), **NOT the aggregate penetration**. A flat aggregate does not mean no acceleration.

Threshold A actual value = max(0.3pp, base_rate × 1.5%), base_rate = the time window's first-day penetration.

> **【MUST·worked example, anti-unit-confusion】** `base_rate` uses the **percentage number** (e.g., `24.06`, not decimal `0.2406`) multiplied directly by `0.015`.
> Example: first-day penetration 24.06% → threshold A = max(0.3, 24.06 × 0.015) = max(0.3, 0.361) = **0.361pp** (not 0.36pp×100, let alone 36pp).
> First-day penetration 20.09% → threshold A = max(0.3, 20.09 × 0.015) = max(0.3, 0.301) = **0.301pp**.
> To judge whether a single-day change triggers threshold A: `|day-over-day change| ≥ threshold A`. If the first-day rate base is small (e.g., 2%), 0.3pp is the floor absolute threshold.

---

## 2. Confidence Tiers & Root-Cause Confidence Labeling

### 2.1 Sample-Size Confidence Tiers (data solidity)

**Applies to**: any **sub-dimension group's intra-group penetration** (e.g., a country, a version, an entry, a cross drill-down sub-combination). Aggregate penetration's denominator (DAU) is usually tens of thousands to millions, almost always High, no tiering needed; what really needs tiering is the **sub-group's intra-group rate judgment**.

> **Relationship with the existing "single-day denominator <200 = exclude as noise" rule**: `--min-dau 200` is the "this group is too small, exclude as noise" hard gate; this tiering is the "group is big enough but not yet fully credible" soft confidence label. They stack: <200 excluded directly, 200-500 kept but labeled Low, ≥1000 safe to use.

| Sample size (group denominator DAU, window total) | Confidence | Error margin | Handling |
|-----------------------------------|--------|---------|------|
| n ≥ 1000 | High | ±2-3% | use normally, directly supports conclusion |
| 500 ≤ n < 1000 | Medium | ±3-5% | downgrade one tier for borderline values, label "suggest re-verify" |
| 100 ≤ n < 500 | Low | ±5-10% | downgrade one tier, label "pending larger sample" |
| n < 100 | Very Low | ±10%+ | **not rated**, list data only, no conclusion; extend window or merge groups |

#### 95% Confidence Interval Formula

```
95% CI for penetration = p ± 1.96 × √(p(1-p)/n)

where p = observed penetration (proportion, e.g., 0.24 = 24%)
      n = that group's denominator (distinct user count)
```

> Note: `p` uses **proportion** (0~1 decimal), not percentage. Example: penetration 24.06%, n=2847 → CI = 0.2406 ± 1.96×√(0.2406×0.7594/2847) = 0.2406 ± 0.0157 → **22.5%~25.6%**.

#### Inflection/Trend Judgment Confidence Linkage

An "inflection/trend change" conclusion's credibility depends on the **smallest sample group supporting it**:

- Aggregate inflection (DAU ~100k) → High, judge directly
- A dimension's intra-group rate inflection → rated by that group's sample size; anomalies judged on Low/Very Low groups must be labeled "low confidence, pending verification", not used directly as root cause
- Cross drill-down sub-combination (e.g., "new user × some country") → smallest denominator, most likely Very Low, **must label confidence**

#### Display Format

```
🔴 New-user penetration -6.17pp (24.06%→21.19%)
   95% CI: first day 22.5%-25.6% / last day 19.8%-22.6%
   Sample: n=2847 → high confidence ✓
   Judgment: anomaly holds (2.6× beyond aggregate -2.34pp)

🟡 Some small country penetration -5.20pp
   Sample: n=342 → low confidence ⚠️
   Judgment: suspected anomaly, pending window extension or country merge before root cause
```

### 2.2 Root-Cause Confidence Labeling (attribution solidity)

Root-cause conclusion confidence is jointly determined by **evidence strength** + **sample size**. Even when the evidence chain fully hits (satisfying HARD RULE #18), confidence is not a constant 100% — "barely all hit" vs "all strongly hit" are different.

| Confidence | Criterion | Handling |
|--------|------|------|
| **High** | evidence chain fully hit + each evidence **significantly over threshold** (e.g., entry-rate drop is 2×+ the threshold) + supporting sample groups all High confidence | directly as primary root cause, give P0 action |
| **Medium** | evidence chain fully hit, but some evidence **just over threshold** (borderline hit) or supporting groups Medium sample | as primary root cause, but label "suggest A/B or supplementary verification" |
| **Low** | evidence chain hit but supporting groups Low confidence, or **alternative explanation not ruled out** (e.g., supply shrinking and product-traffic downgrade both possible) | as hypothesis only, label "needs further verification", not into P0 |

#### Composite Root-Cause Label Format

```
Root cause: supply shrinking [High] + algorithm match failure [Medium]
- supply shrinking High: online rooms -18%, prime-time streaming -22%, active streamers -15%, all far over threshold, entry rate flat (+0.1pp), supporting samples DAU all >100k
- algorithm match failure Medium: exposure→entry conversion -1.2pp, only slightly over threshold, and exposure data is approximate caliber, pending click-event supplement for re-verify
```

#### Relationship with the Root-Cause Library

`indicators.md` "high-frequency root-cause library" still governs "**whether to judge**" (evidence chain none missing); this section's confidence labeling governs "**how hard after judging**". Two-step order: first evidence-chain establish the root cause → then rate confidence per this section.
