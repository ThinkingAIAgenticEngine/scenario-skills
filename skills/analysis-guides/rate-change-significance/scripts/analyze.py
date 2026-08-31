#!/usr/bin/env python3
"""Rate-change significance calculator for the rate-change-significance skill.

Reads a JSON job describing the data and chosen test path, computes statistics,
writes a JSON result file, and prints a short summary to stdout. Pure stdlib.

Behavior notes:
  - decide_test() is cohort_design-aware. Paired jobs (cohort_design="paired"
    OR a mcnemar={a,b,c,d} block present) auto-route to McNemar; no need to pass
    test="mcnemar" explicitly (you still can).
  - Fisher fallback requires no re-invoke round-trip. When any expected cell
    < 5, the script auto-builds the 2x2 cells from group_A/group_B and runs
    fisher_exact directly.
  - mcnemar() returns marginal_p_A, marginal_p_B, observed_diff, ci_95
    (paired Edwards form), relative_uplift, cohen_h + label, so the report
    template's Part 3 / Part 6 can be filled for paired design.
  - SRM decision logic lives in the script. Pass cohort_design, overlap.rate,
    design_type, period_lengths and the script returns srm_decision
    (proceed | proceed_with_warning | hard_reject | skip) with a reason. The
    agent no longer executes the SRM if/else tree in prompt space.
  - expected_ratio auto-derived from period_lengths when design_type="pre_post"
    and expected_ratio is not explicitly set.
  - When overlap.rate >= 0.30 and cohort_design != "paired", the output
    includes a structured `recommended_rerun: "paired"` field (machine-readable)
    in addition to the existing human-readable `warnings` string. The agent can read this to decide whether to auto-trigger a Part 3b paired run.

Job schema (backward compatible; new fields optional):

{
  "scenario": "retention | repurchase | conversion | churn | renewal | custom",
  "cohort_event": "<event>",
  "outcome_event": "<event>",
  "window_N": <int>,
  "window_mode": "exact_day | within_window",
  "cohort_design": "first_occurrence | period_active | paired",
  "design_type": "pre_post | concurrent_ab",                       # default pre_post
  "period_lengths": [<days_A>, <days_B>],                          # for expected_ratio auto-calc
  "group_A": {"label": "...", "time_range": "...", "n": <int>, "outcome": <int>},
  "group_B": {"label": "...", "time_range": "...", "n": <int>, "outcome": <int>},
  "overlap": {"count": <int>, "rate": <float 0..1>},
  "test": "auto | z_independent | mcnemar | fisher_exact",  # fisher_exact is independent-samples only
  "expected_ratio": <float 0..1, optional>,                        # auto-derived if absent + pre_post + period_lengths
  "mcnemar": {"a": <int>, "b": <int>, "c": <int>, "d": <int>},     # paired cells
  "fisher": {"a": <int>, "b": <int>, "c": <int>, "d": <int>},      # optional independent 2x2; auto-built from group_A/B if absent
  "output_path": "<path>"
}
"""
import argparse, json, math, sys




def validate_input_payload(payload):
    """Validate structural input fields before statistical routing.

    Independent jobs need group_A/group_B. Paired jobs require matched McNemar
    cells. Count fields are strict non-negative integers; no silent truncation.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if payload.get("schema_version", "1.0") != "1.0":
        raise ValueError("Unsupported schema_version")

    cohort_design = payload.get("cohort_design")
    test = payload.get("test", "auto")
    has_mcnemar = isinstance(payload.get("mcnemar"), dict)

    if cohort_design == "paired" and test == "fisher_exact":
        raise ValueError("Fisher exact is not valid for matched paired outcomes; use McNemar/exact McNemar")

    pure_paired = cohort_design == "paired" and has_mcnemar
    has_fisher = isinstance(payload.get("fisher"), dict)
    pure_fisher = test == "fisher_exact" and has_fisher and not has_mcnemar and cohort_design != "paired"
    if not pure_paired and not pure_fisher:
        for key in ("group_A", "group_B"):
            if key not in payload:
                raise ValueError(f"Missing required field: {key}")
            if not isinstance(payload[key], dict):
                raise ValueError(f"{key} must be an object")
            group = payload[key]
            for field in ("n", "outcome"):
                if field not in group:
                    raise ValueError(f"Missing required field: {key}.{field}")
                val = group[field]
                if isinstance(val, bool) or not isinstance(val, (int, float)) or int(val) != val:
                    raise ValueError(f"{key}.{field} must be a non-negative integer")
            n = int(group["n"]); outcome = int(group["outcome"])
            if n < 0:
                raise ValueError(f"{key}.n must be non-negative")
            if outcome < 0:
                raise ValueError(f"{key}.outcome must be non-negative")
            if outcome > n:
                raise ValueError(f"{key}.outcome cannot exceed n")

    for block_name in ("mcnemar", "fisher"):
        block = payload.get(block_name)
        if block is not None:
            if not isinstance(block, dict):
                raise ValueError(f"{block_name} must be an object")
            for cell in ("a", "b", "c", "d"):
                if cell not in block:
                    raise ValueError(f"Missing required field: {block_name}.{cell}")
                val = block[cell]
                if isinstance(val, bool) or not isinstance(val, (int, float)) or int(val) != val or val < 0:
                    raise ValueError(f"{block_name}.{cell} must be a non-negative integer")
    if cohort_design == "paired" and payload.get("fisher") is not None:
        raise ValueError("paired jobs must not supply fisher cells; use mcnemar={a,b,c,d}")

    overlap = payload.get("overlap")
    if overlap is not None:
        if not isinstance(overlap, dict):
            raise ValueError("overlap must be an object")
        if "count" in overlap and overlap["count"] is not None:
            val = overlap["count"]
            if isinstance(val, bool) or not isinstance(val, (int, float)) or int(val) != val or val < 0:
                raise ValueError("overlap.count must be a non-negative integer")
        if "rate" in overlap and overlap["rate"] is not None:
            rate = float(overlap["rate"])
            if not (0.0 <= rate <= 1.0):
                raise ValueError("overlap.rate must be between 0 and 1")

    expected_ratio = payload.get("expected_ratio")
    if expected_ratio is not None:
        if isinstance(expected_ratio, bool) or not isinstance(expected_ratio, (int, float)):
            raise ValueError("expected_ratio must be numeric")
        if not (0.0 < float(expected_ratio) < 1.0):
            raise ValueError("expected_ratio must be strictly between 0 and 1")

    pl = payload.get("period_lengths")
    if pl is not None:
        if not isinstance(pl, (list, tuple)) or len(pl) != 2:
            raise ValueError("period_lengths must contain exactly two positive integers")
        for v in pl:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or int(v) != v or v <= 0:
                raise ValueError("period_lengths must contain exactly two positive integers")
    return True


def _normalized_overlap(job):
    """Return overlap dict; derive and cross-check rate=count/min(n_A,n_B)."""
    overlap = dict(job.get("overlap") or {})
    gA = job.get("group_A") or {}
    gB = job.get("group_B") or {}
    count = overlap.get("count")
    supplied_rate = overlap.get("rate")
    if count is not None and gA.get("n") is not None and gB.get("n") is not None:
        max_overlap = min(int(gA["n"]), int(gB["n"]))
        if int(count) > max_overlap:
            raise ValueError("overlap.count cannot exceed min(group_A.n, group_B.n)")
        derived = (float(count) / max_overlap) if max_overlap > 0 else 0.0
        if supplied_rate is not None and not math.isclose(float(supplied_rate), derived, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(
                "overlap.rate is inconsistent with overlap.count/min(group_A.n, group_B.n): "
                f"supplied={float(supplied_rate):.12g}, derived={derived:.12g}"
            )
        overlap["rate"] = derived
        overlap["count"] = int(count)
    elif supplied_rate is not None:
        overlap["rate"] = float(supplied_rate)
    return overlap


def _rate_boundary(g):
    n = int(g.get("n", 0)); r = int(g.get("outcome", 0))
    if n <= 0:
        return None
    if r == 0:
        return 0
    if r == n:
        return 1
    return None


def sample_quality_gate(job, overlap):
    """Return {blocked, reason, warnings} for the skill's pre-test quality gate."""
    cohort_design = job.get("cohort_design")
    warnings = []
    if cohort_design == "paired" or job.get("mcnemar") is not None:
        cells = job.get("mcnemar")
        if cells is None:
            return {"blocked": True, "reason": "paired analysis requires mcnemar={a,b,c,d} matched-pair cells", "warnings": warnings}
        paired_n = sum(int(cells[k]) for k in ("a", "b", "c", "d"))
        if paired_n < 30:
            warnings.append(f"paired_n={paired_n} < 30: small matched sample; exact McNemar handles sparse discordant pairs, but uncertainty may be large")
        if int(cells["b"]) + int(cells["c"]) == 0:
            return {"blocked": True, "reason": "b+c=0; no discordant pairs, so there is no within-user change to test", "warnings": warnings}
        ctx = job.get("paired_context") or {}
        if ctx.get("n_A_active") and ctx.get("n_B_active"):
            denom = min(int(ctx["n_A_active"]), int(ctx["n_B_active"]))
            if denom > 0:
                share = paired_n / denom
                if share < 0.30:
                    warnings.append(
                        "paired sample is <30% of the smaller period-active population; result describes a narrow consistently-active subset"
                    )
        return {"blocked": False, "reason": None, "warnings": warnings}

    gA = job.get("group_A") or {}; gB = job.get("group_B") or {}
    # Pure Fisher (cells passed directly, no group_A/group_B)
    fisher_cells = job.get("fisher")
    if fisher_cells is not None and not (gA.get("n") and gB.get("n")):
        total = sum(int(fisher_cells[k]) for k in ("a", "b", "c", "d"))
        if total <= 0:
            return {"blocked": True, "reason": "fisher cells sum to 0; nothing to test", "warnings": warnings}
        if total < 30:
            warnings.append(f"fisher 2x2 total={total} < 30: small sample; Fisher exact remains valid for sparse tables, but uncertainty may be large")
        return {"blocked": False, "reason": None, "warnings": warnings}

    n_A = int(gA.get("n", 0)); n_B = int(gB.get("n", 0))
    if n_A <= 0 or n_B <= 0:
        return {"blocked": True, "reason": f"both groups require n>0; got n_A={n_A}, n_B={n_B}", "warnings": warnings}
    if n_A < 30 or n_B < 30:
        warnings.append(f"small sample: n_A={n_A}, n_B={n_B}; do not use n>=30 as a mathematical validity rule — Fisher exact remains valid when sparse")
    bA = _rate_boundary(gA); bB = _rate_boundary(gB)
    if bA is not None and bB is not None and bA == bB:
        warnings.append("both groups have the same boundary rate; observed rate difference is exactly 0 and Fisher exact will return no evidence of a difference")
    elif bA is not None and bB is not None:
        warnings.append("groups have opposite boundary rates; use Fisher exact rather than Z-test")

    rate = float((overlap or {}).get("rate", 0.0) or 0.0)
    if job.get("cohort_design") == "period_active":
        if rate < 0.10:
            warnings.append("overlap <10%: groups are nearly independent")
        elif rate < 0.30:
            warnings.append("overlap 10%-<30%: moderate dependence; disclose the approximation")
        else:
            warnings.append("overlap >=30%: independence is materially violated; keep period-level primary view and add paired sensitivity analysis when possible")
    return {"blocked": False, "reason": None, "warnings": warnings}

def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def chi2_sf_df1(stat):
    """Survival function 1 - CDF for chi-square with df=1."""
    if stat <= 0:
        return 1.0
    return 2 * (1 - norm_cdf(math.sqrt(stat)))


def cohen_h_label(h):
    ah = abs(h)
    if ah < 0.2:
        return "negligible"
    if ah < 0.5:
        return "small"
    if ah < 0.8:
        return "medium"
    return "large"


# ----------------------------------------------------------------------------
# Independent two-proportion Z-test (first_occurrence / period_active)
# ----------------------------------------------------------------------------

def z_independent(n_A, r_A, n_B, r_B):
    if n_A <= 0 or n_B <= 0:
        raise ValueError(
            "z_independent requires n_A > 0 and n_B > 0 (got n_A=%r, n_B=%r); "
            "the calling skill should have rejected this in its Step 3 data-quality "
            "check (n > 0 per group, valid counts)." % (n_A, n_B)
        )
    if not (0 <= r_A <= n_A) or not (0 <= r_B <= n_B):
        raise ValueError(
            "outcome count must be between 0 and n for each group "
            "(got r_A=%r/n_A=%r, r_B=%r/n_B=%r)" % (r_A, n_A, r_B, n_B)
        )
    p_A = r_A / n_A
    p_B = r_B / n_B
    p_pool = (r_A + r_B) / (n_A + n_B)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n_A + 1 / n_B))
    z = (p_B - p_A) / se_pool
    p_value = 2 * (1 - norm_cdf(abs(z)))
    se_ind = math.sqrt(p_A * (1 - p_A) / n_A + p_B * (1 - p_B) / n_B)
    ci_low = (p_B - p_A) - 1.96 * se_ind
    ci_high = (p_B - p_A) + 1.96 * se_ind
    rel_uplift = (p_B - p_A) / p_A if p_A > 0 else None
    cohen_h = 2 * (math.asin(math.sqrt(p_B)) - math.asin(math.sqrt(p_A)))
    z_alpha, z_beta = 1.96, 0.84
    mdd = (z_alpha + z_beta) * math.sqrt(p_pool * (1 - p_pool) * (1 / n_A + 1 / n_B))
    observed_diff = abs(p_B - p_A)
    avg_n = (n_A + n_B) / 2
    if observed_diff > 0:
        n_needed = (
            (
                z_alpha * math.sqrt(2 * p_pool * (1 - p_pool))
                + z_beta * math.sqrt(p_A * (1 - p_A) + p_B * (1 - p_B))
            )
            / observed_diff
        ) ** 2
        extra = max(0, n_needed - avg_n)
    else:
        # observed_diff == 0: infinite sample needed. null, not Infinity token.
        n_needed = None
        extra = None
    return {
        "test": "two_proportion_z_test_independent",
        "p_A": p_A,
        "p_B": p_B,
        "z": z,
        "p_value": p_value,
        "ci_95": [ci_low, ci_high],
        "relative_uplift": rel_uplift,
        "cohen_h": cohen_h,
        "cohen_h_label": cohen_h_label(cohen_h),
        "mdd_80pct_power": mdd,
        "observed_diff": observed_diff,
        "n_needed_per_group": n_needed,
        "extra_needed_per_group": extra,
    }


# ----------------------------------------------------------------------------
# McNemar matched-pairs test (paired design) — adds marginal CI/effect
# ----------------------------------------------------------------------------

def mcnemar(a, b, c, d):
    n = a + b + c + d
    n_disc = b + c
    if n <= 0:
        raise ValueError("mcnemar requires paired_n = a+b+c+d > 0")
    # Marginal proportions (the per-period rates on the paired subset)
    p_A = (a + b) / n  # A-period outcome rate in the paired sample
    p_B = (a + c) / n  # B-period outcome rate in the paired sample
    observed_diff = p_B - p_A  # = (c - b) / n
    if n_disc == 0:
        return {
            "test": "mcnemar",
            "a": a, "b": b, "c": c, "d": d,
            "paired_n": n,
            "marginal_p_A": p_A,
            "marginal_p_B": p_B,
            "observed_diff": observed_diff,
            "ci_95": [0.0, 0.0],
            "relative_uplift": None,
            "cohen_h": 0.0,
            "cohen_h_label": "negligible",
            "statistic": 0.0,
            "p_value": 1.0,
            "n_discordant": 0,
            "method": "no_discordant_pairs",
            "mdd_80pct_power": None,
            "n_needed_per_group": None,
            "note": "b+c=0; no discordant pairs, McNemar undefined; p-value set to 1.0",
        }
    stat = (abs(b - c) - 1) ** 2 / n_disc
    p_value = chi2_sf_df1(stat)
    method = "chi_square_continuity_correction"
    exact_p = None
    if n_disc < 25:
        method = "exact_binomial"
        k = min(b, c)
        one_side = sum(math.comb(n_disc, i) for i in range(0, k + 1)) * (0.5 ** n_disc)
        exact_p = min(one_side * 2, 1.0)
        p_value = exact_p
    # Paired 95% CI of the marginal difference (Edwards form):
    #   SE_diff = sqrt((b + c) - (c - b)^2 / n) / n
    se_diff = math.sqrt(max(0.0, (b + c) - (c - b) ** 2 / n)) / n
    ci_low = observed_diff - 1.96 * se_diff
    ci_high = observed_diff + 1.96 * se_diff
    rel_uplift = (p_B - p_A) / p_A if p_A > 0 else None
    cohen_h = 2 * (math.asin(math.sqrt(p_B)) - math.asin(math.sqrt(p_A)))
    # McNemar power is structurally different from independent Z — it depends on
    # the discordant-pair ratio, not just n. We do not emit a bare MDD; instead
    # we emit the effective sample size (n_discordant) and a discordant-pairs-
    # needed figure for 80% power to detect the observed discordant asymmetry.
    psi = abs(b - c) / n_disc  # discordant asymmetry, in [0, 1]
    z_alpha, z_beta = 1.96, 0.84
    if psi > 0:
        disc_needed = ((z_alpha + z_beta) / psi) ** 2
    else:
        disc_needed = None
    return {
        "test": "mcnemar",
        "a": a, "b": b, "c": c, "d": d,
        "paired_n": n,
        "marginal_p_A": p_A,
        "marginal_p_B": p_B,
        "observed_diff": observed_diff,
        "ci_95": [ci_low, ci_high],
        "relative_uplift": rel_uplift,
        "cohen_h": cohen_h,
        "cohen_h_label": cohen_h_label(cohen_h),
        "statistic": stat,
        "p_value": p_value,
        "n_discordant": n_disc,
        "method": method,
        "exact_binomial_p": exact_p,
        "mdd_80pct_power": None,
        "discordant_pairs_needed_for_80pct": disc_needed,
        "n_needed_per_group": None,
        "note": "McNemar power depends on discordant-pair structure, not n alone; mdd/n_needed fields are null. Effective sample = n_discordant; discordant_pairs_needed_for_80pct estimates the discordant count required to detect the observed asymmetry at 80% power.",
    }


# ----------------------------------------------------------------------------
# Fisher's exact 2x2 (small expected cell fallback)
# ----------------------------------------------------------------------------

def fisher_exact(a, b, c, d):
    n = a + b + c + d
    row1 = a + b
    col1 = a + c

    def pmf(k):
        return math.comb(col1, k) * math.comb(n - col1, row1 - k) / math.comb(n, row1)

    lo = max(0, row1 - (n - col1))
    hi = min(row1, col1)
    observed_pmf = pmf(a)
    two_sided = 0.0
    for k in range(lo, hi + 1):
        p = pmf(k)
        if p <= observed_pmf * (1.0 + 1e-12):
            two_sided += p
    two_sided = min(two_sided, 1.0)
    # marginal rates for Fisher (independent-samples layout):
    # a/b = A success/failure, c/d = B success/failure
    p_A = a / (a + b) if (a + b) > 0 else None
    p_B = c / (c + d) if (c + d) > 0 else None
    observed_diff = abs(p_B - p_A) if (p_A is not None and p_B is not None) else None
    rel_uplift = (p_B - p_A) / p_A if (p_A is not None and p_B is not None and p_A > 0) else None
    cohen_h = (
        2 * (math.asin(math.sqrt(p_B)) - math.asin(math.sqrt(p_A)))
        if (p_A is not None and p_B is not None)
        else None
    )
    return {
        "test": "fisher_exact",
        "a": a, "b": b, "c": c, "d": d,
        "p_value": two_sided,
        "odds_ratio": (b * c) / (a * d) if a > 0 and d > 0 else None,
        "odds_ratio_direction": "B_vs_A",
        "marginal_p_A": p_A,
        "marginal_p_B": p_B,
        "observed_diff": observed_diff,
        "relative_uplift": rel_uplift,
        "cohen_h": cohen_h,
        "cohen_h_label": cohen_h_label(cohen_h) if cohen_h is not None else None,
        "ci_95": None,
        "note": "Fisher's exact does not produce a CI via the hypergeometric test; use odds_ratio (B vs A) + p_value for inference.",
    }


# ----------------------------------------------------------------------------
# Test auto-selection (cohort_design-aware)
# ----------------------------------------------------------------------------

def _build_independent_fisher_cells(gA, gB):
    """Independent-samples 2x2 layout: a=r_A, b=n_A-r_A, c=r_B, d=n_B-r_B."""
    n_A = int(gA.get("n", 0))
    r_A = int(gA.get("outcome", 0))
    n_B = int(gB.get("n", 0))
    r_B = int(gB.get("outcome", 0))
    return {"a": r_A, "b": n_A - r_A, "c": r_B, "d": n_B - r_B}


def _min_expected_cell(gA, gB):
    n_A = int(gA.get("n", 0))
    n_B = int(gB.get("n", 0))
    r_A = int(gA.get("outcome", 0))
    r_B = int(gB.get("outcome", 0))
    total = n_A + n_B
    if total == 0:
        return 0
    expected_A = (r_A + r_B) * n_A / total
    expected_B = (r_A + r_B) * n_B / total
    expected_nonA = (n_A - r_A + n_B - r_B) * n_A / total
    expected_nonB = (n_A - r_A + n_B - r_B) * n_B / total
    return min(expected_A, expected_B, expected_nonA, expected_nonB)


def decide_test(job):
    """Auto-select the inferential test after structural quality gating.

    Precedence:
      1. paired / mcnemar cells -> McNemar
      2. any independent-group boundary rate (0 or 1) -> Fisher
      3. any expected independent 2x2 cell < 5 -> Fisher
      4. otherwise -> independent two-proportion Z

    High period_active overlap does not replace the primary estimand; it adds a
    warning + recommended paired rerun.
    """
    cohort_design = job.get("cohort_design")
    overlap = _normalized_overlap(job)
    rate = float(overlap.get("rate", 0.0) or 0.0)
    gA = job.get("group_A") or {}
    gB = job.get("group_B") or {}
    warnings = []

    mcnemar_block = job.get("mcnemar")
    if cohort_design == "paired" or mcnemar_block is not None:
        if mcnemar_block is None:
            return None, "paired McNemar requires mcnemar={a,b,c,d}", warnings
        return "mcnemar", None, warnings

    if rate >= 0.30:
        warnings.append(
            "overlap_rate=%.4f >= 0.30: independence assumption materially violated. "
            "Keep the period-level independent result as the full-population view, "
            "and run a paired McNemar sensitivity analysis when matched cells are available." % rate
        )

    bA = _rate_boundary(gA); bB = _rate_boundary(gB)
    if bA is not None or bB is not None:
        warnings.append("at least one group has a boundary rate (0 or 1); Fisher's exact used instead of Z-test")
        return "fisher_exact", None, warnings

    if _min_expected_cell(gA, gB) < 5:
        return "fisher_exact", None, warnings
    return "z_independent", None, warnings


# ----------------------------------------------------------------------------
# SRM (Sample Ratio Mismatch) — computation + decision
# ----------------------------------------------------------------------------

def srm_check(n_A, n_B, expected_ratio=0.5):
    """Chi-square df=1 with Yates correction. Returns the raw check."""
    total = n_A + n_B
    if total == 0:
        return {"ok": False, "error": "total = 0"}
    e_A = total * expected_ratio
    e_B = total * (1 - expected_ratio)
    if e_A <= 0 or e_B <= 0:
        return {"ok": False, "error": "expected ratio yields zero expected cell"}
    stat = (max(0, abs(n_A - e_A) - 0.5) ** 2) / e_A + (max(0, abs(n_B - e_B) - 0.5) ** 2) / e_B
    p_value = chi2_sf_df1(stat)
    return {
        "ok": True,
        "expected_ratio": expected_ratio,
        "observed_ratio_A": n_A / total,
        "n_A_observed": n_A,
        "n_B_observed": n_B,
        "n_A_expected": e_A,
        "n_B_expected": e_B,
        "statistic": stat,
        "p_value": p_value,
        "srm_detected": p_value < 0.01,
    }


def srm_decision(srm_result, cohort_design, overlap_rate, design_type, marginal_p=0.05):
    """Decide what to do with an SRM result. logic moved here from prompt.

    Returns {decision, reason}:
      - "skip"                : SRM not applicable (paired, or compute failed)
      - "proceed"             : no SRM
      - "proceed_with_warning": SRM fired but design context says it likely
                                reflects organic drift, not a data bug
      - "hard_reject"         : SRM fired in a context where independent
                                allocation is expected (concurrent A/B with
                                first_occurrence and no overlap)
    """
    if not srm_result or not srm_result.get("ok"):
        return {"decision": "skip", "reason": "SRM not computed (n_A/n_B absent or invalid)"}
    if cohort_design == "paired":
        return {"decision": "skip", "reason": "SRM not applicable to paired design (same users in both periods, no traffic split)"}
    detected = srm_result.get("srm_detected", False)
    marginal = srm_result.get("p_value", 1.0) < marginal_p
    if not detected and not marginal:
        return {"decision": "proceed", "reason": "no SRM detected"}
    # SRM fired (strict) or marginal
    level = "detected" if detected else "marginal"
    if cohort_design == "period_active" and overlap_rate > 0:
        return {
            "decision": "proceed_with_warning",
            "reason": "pre/post cohort-size balance diagnostic is %s under period_active with overlap_rate>0; this is not classical randomized-experiment SRM, and shared users violate the allocation-test independence assumption — treat as traffic/composition context" % level,
        }
    if design_type == "concurrent_ab" and detected:
        return {
            "decision": "hard_reject",
            "reason": "concurrent A/B with SRM detected and no overlap; likely data-collection bug (redirect, tracking gap, bot traffic) — investigate before testing",
        }
    # first_occurrence pre/post OR period_active with 0 overlap (one-time event)
    return {
        "decision": "proceed_with_warning",
        "reason": "pre/post cohort-size balance diagnostic is %s; this is not classical randomized-experiment SRM and may reflect organic traffic drift — investigate cohort-size context in Part 1 before interpreting" % level,
    }


# ----------------------------------------------------------------------------
# expected_ratio resolution
# ----------------------------------------------------------------------------

def resolve_expected_ratio(job):
    """auto-derive expected_ratio when not explicitly set.

    Precedence:
      1. explicit expected_ratio in job
      2. design_type=pre_post + period_lengths=[a,b] -> a/(a+b)
      3. default 0.5
    """
    explicit = job.get("expected_ratio")
    if explicit is not None:
        return float(explicit)
    design_type = job.get("design_type", "pre_post")
    if design_type == "pre_post":
        pl = job.get("period_lengths")
        if pl and len(pl) == 2 and (pl[0] + pl[1]) > 0:
            return pl[0] / (pl[0] + pl[1])
    return 0.5


# ----------------------------------------------------------------------------
# Main runner
# ----------------------------------------------------------------------------

def run(job):
    test_requested = job.get("test", "auto")
    cohort_design = job.get("cohort_design")
    design_type = job.get("design_type", "pre_post")
    overlap = _normalized_overlap(job)
    overlap_rate = float(overlap.get("rate", 0.0) or 0.0)

    out = {
        "scenario": job.get("scenario"),
        "cohort_event": job.get("cohort_event"),
        "outcome_event": job.get("outcome_event"),
        "window_N": job.get("window_N"),
        "window_mode": job.get("window_mode"),
        "cohort_design": cohort_design,
        "design_type": design_type,
        "calculator_version": "4.16",
        "schema_version": job.get("schema_version", "1.0"),
        "group_A": job.get("group_A"),
        "group_B": job.get("group_B"),
        "overlap": overlap,
        "analysis_status": "ok",
    }

    gate = sample_quality_gate(job, overlap)
    if gate.get("warnings"):
        out["warnings"] = list(gate["warnings"])
    if gate.get("blocked"):
        out["analysis_status"] = "blocked"
        out["blocked_reason"] = gate.get("reason")
        out["test"] = None
        return out

    warnings = list(out.get("warnings", []))
    test = test_requested
    if test == "auto":
        test, reason, route_warnings = decide_test(job)
        warnings.extend(route_warnings)
        if reason:
            out["analysis_status"] = "blocked"
            out["blocked_reason"] = reason
            out["test"] = None
            if warnings:
                out["warnings"] = warnings
            return out
    # Enforce compatibility even when a caller explicitly requests a test.
    if cohort_design == "paired" and test != "mcnemar":
        out["analysis_status"] = "blocked"
        out["blocked_reason"] = "paired matched outcomes require McNemar; Fisher/Z are independent-sample tests"
        out["test"] = None
        return out
    if cohort_design != "paired" and test == "z_independent":
        gA_check = job.get("group_A") or {}
        gB_check = job.get("group_B") or {}
        if _rate_boundary(gA_check) is not None or _rate_boundary(gB_check) is not None or _min_expected_cell(gA_check, gB_check) < 5:
            out["analysis_status"] = "blocked"
            out["blocked_reason"] = "requested z_independent violates boundary/expected-cell requirements; use test=auto or fisher_exact"
            out["test"] = None
            return out

    out["test"] = test
    if warnings:
        # preserve order while de-duplicating
        out["warnings"] = list(dict.fromkeys(warnings))

    if overlap_rate >= 0.30 and cohort_design != "paired":
        out["recommended_rerun"] = "paired"

    gA = job.get("group_A") or {}
    gB = job.get("group_B") or {}

    # SRM applies to independent allocation/sample-count paths only.
    if test != "mcnemar" and gA and gB and "n" in gA and "n" in gB:
        expected_ratio = resolve_expected_ratio(job)
        srm = srm_check(int(gA["n"]), int(gB["n"]), expected_ratio)
        decision = srm_decision(srm, cohort_design, overlap_rate, design_type)
        out["srm"] = srm
        out["sample_balance_diagnostic"] = "SRM" if design_type == "concurrent_ab" else "pre_post_cohort_size_balance"
        out["srm_decision"] = decision
        if decision.get("decision") == "hard_reject":
            out["analysis_status"] = "blocked"
            out["blocked_reason"] = decision.get("reason")
            return out

    try:
        if test == "z_independent":
            out.update(z_independent(int(gA["n"]), int(gA["outcome"]),
                                     int(gB["n"]), int(gB["outcome"])))
        elif test == "mcnemar":
            cells = job.get("mcnemar") or {}
            out.update(mcnemar(int(cells["a"]), int(cells["b"]),
                               int(cells["c"]), int(cells["d"])))
        elif test == "fisher_exact":
            cells = job.get("fisher")
            if not cells:
                cells = _build_independent_fisher_cells(gA, gB)
                out["fisher_cells_auto_built"] = True
            out.update(fisher_exact(int(cells["a"]), int(cells["b"]),
                                    int(cells["c"]), int(cells["d"])))
        else:
            out["analysis_status"] = "blocked"
            out["blocked_reason"] = "unknown test: %s" % test
            return out
    except (KeyError, ValueError, ZeroDivisionError) as e:
        out["analysis_status"] = "blocked"
        out["blocked_reason"] = "%s failed: %s" % (test, e)
        return out
    return out


def print_summary(r):
    print("=" * 60)
    if r.get("analysis_status") == "blocked":
        print("ANALYSIS BLOCKED: %s" % r.get("blocked_reason", "unspecified reason"))
        if r.get("srm_decision"):
            d = r["srm_decision"]
            print("SRM decision: %s — %s" % (d.get("decision"), d.get("reason")))
        print("=" * 60)
        return
    t = r.get("test")
    if t == "two_proportion_z_test_independent":
        gA = r["group_A"]; gB = r["group_B"]
        print("Group A: n=%d, outcome=%d, rate=%.4f%%" % (gA["n"], gA["outcome"], r["p_A"] * 100))
        print("Group B: n=%d, outcome=%d, rate=%.4f%%" % (gB["n"], gB["outcome"], r["p_B"] * 100))
        print("Z = %.4f, p = %.6f (two-sided)" % (r["z"], r["p_value"]))
        print("95%% CI of diff: [%.4f%%, %.4f%%]" % (r["ci_95"][0] * 100, r["ci_95"][1] * 100))
        if r["relative_uplift"] is None:
            print("Relative uplift: n/a (p_A = 0)")
        else:
            print("Relative uplift: %.2f%%" % (r["relative_uplift"] * 100))
        print("Cohen's h: %.4f (%s)" % (r["cohen_h"], r["cohen_h_label"]))
        print("MDD @80%% power: %.4f pp; observed diff: %.4f pp" %
              (r["mdd_80pct_power"] * 100, r["observed_diff"] * 100))
        if r["n_needed_per_group"] is None:
            print("Sample needed per group @80% power: n/a (observed diff = 0)")
        else:
            print("Sample needed per group @80%% power: %d (extra: %d)" %
                  (math.ceil(r["n_needed_per_group"]), math.ceil(r["extra_needed_per_group"])))
    elif t == "mcnemar":
        print("McNemar cells: a=%d b=%d c=%d d=%d (paired_n=%d)" %
              (r["a"], r["b"], r["c"], r["d"], r["paired_n"]))
        print("Marginal p_A=%.4f%%, p_B=%.4f%%, diff=%.4f%%" %
              (r["marginal_p_A"] * 100, r["marginal_p_B"] * 100, r["observed_diff"] * 100))
        print("Statistic = %.4f, p = %.6f (%s)" % (r["statistic"], r["p_value"], r["method"]))
        print("Discordant pairs (b+c) = %d" % r["n_discordant"])
        print("95%% CI of marginal diff: [%.4f%%, %.4f%%]" %
              (r["ci_95"][0] * 100, r["ci_95"][1] * 100))
        if r["relative_uplift"] is None:
            print("Relative uplift: n/a (marginal p_A = 0)")
        else:
            print("Relative uplift: %.2f%%" % (r["relative_uplift"] * 100))
        print("Cohen's h (marginals): %.4f (%s)" % (r["cohen_h"], r["cohen_h_label"]))
        if r.get("discordant_pairs_needed_for_80pct") is None:
            print("Discordant pairs needed @80% power: n/a (psi=0, no asymmetry to detect)")
        else:
            print("Discordant pairs needed @80%% power (observed asymmetry): %d" %
                  math.ceil(r["discordant_pairs_needed_for_80pct"]))
    elif t == "fisher_exact":
        print("Fisher 2x2: a=%d b=%d c=%d d=%d" % (r["a"], r["b"], r["c"], r["d"]))
        if r["odds_ratio"] is None:
            print("p = %.6f, OR = n/a (a=0 or d=0)" % r["p_value"])
        else:
            print("p = %.6f, OR = %.4f" % (r["p_value"], r["odds_ratio"]))
    # SRM + decision
    if r.get("srm", {}).get("ok"):
        s = r["srm"]
        flag = " *** SRM DETECTED ***" if s["srm_detected"] else ""
        print("SRM: chi2=%.4f, p=%.4f (expected A ratio=%.2f, observed=%.4f)%s" %
              (s["statistic"], s["p_value"], s["expected_ratio"],
               s["observed_ratio_A"], flag))
    if r.get("srm_decision"):
        d = r["srm_decision"]
        print("SRM decision: %s — %s" % (d["decision"], d["reason"]))
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="JSON job file path; reads stdin if omitted")
    ap.add_argument("--output", help="JSON result file path; default stats.json in cwd")
    args = ap.parse_args()

    raw = open(args.input).read() if args.input else sys.stdin.read()
    job = json.loads(raw)
    validate_input_payload(job)
    result = run(job)
    out_path = args.output or job.get("output_path") or "stats.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print_summary(result)
    print("Saved " + out_path)


if __name__ == "__main__":
    main()
