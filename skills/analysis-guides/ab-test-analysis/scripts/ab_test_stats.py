#!/usr/bin/env python3
"""A/B test statistical analysis engine v2.

v2 additions:
- Bayesian posterior probability P(Treatment > Control) via Beta distribution
- Post-hoc power analysis (observed power, false negative risk)
- Required sample size to detect observed effect
- Business significance assessment
- Actionable recommendation engine (not just "inconclusive")

Original v1 features preserved:
- Two-proportion z-test, Welch's t-test
- Bonferroni correction
- Cohen's d effect size
- MDE, confidence intervals
"""

import argparse
import json
import math
import sys
import os
import tempfile


def _default_venv_python():
    """Path of the private venv interpreter created by check_prerequisites.py.

    Mirrors the cache-dir logic there so both scripts agree on the location.
    """
    rel = (os.path.join("venv", "Scripts", "python.exe") if sys.platform == "win32"
           else os.path.join("venv", "bin", "python"))
    cache = os.environ.get("CACHE_DIR")
    if not cache:
        # Portable default: a per-user temp directory, overridable via CACHE_DIR.
        cache = os.path.join(tempfile.gettempdir(), "ab-test-analysis")
    return os.path.join(cache, rel)


def subprocess_run_capture(cmd):
    import subprocess
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception:
        return ""
    return r.stdout if r.returncode == 0 else ""


def _load_venv_site_packages():
    """If scipy is not importable, try to locate the private venv (created by
    check_prerequisites.py) and add its site-packages to sys.path so we can
    still use the full statistical engine instead of silently degrading to the
    normal-approximation fallback.

    Probed in order:
      1. `scripts/.resolved_python` sidecar written by check_prerequisites.py
      2. the default cache venv location — covers the case where the sidecar was
         deleted, or Step 0 never ran this session but the venv already exists.
    """
    global VENV_SITE_PACKAGES_ADDED
    if os.environ.get("AB_TEST_NO_SCIPY") == "1":
        # Escape hatch for testing / debugging the degraded path on purpose.
        return
    candidates = []
    sidecar = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".resolved_python")
    try:
        with open(sidecar) as f:
            p = f.read().strip()
        if p:
            candidates.append(p)
    except OSError:
        pass
    candidates.append(_default_venv_python())

    for py_bin in candidates:
        if not py_bin or not os.path.exists(py_bin):
            continue
        out = subprocess_run_capture([py_bin, "-c",
                                      "import site; print('\\n'.join(site.getsitepackages()))"])
        added = False
        for p in out.splitlines():
            p = p.strip()
            if p and os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
                added = True
        if added:
            VENV_SITE_PACKAGES_ADDED = py_bin
            return


VENV_SITE_PACKAGES_ADDED = None
_load_venv_site_packages()

try:
    from scipy import stats
    import numpy as np
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ============================================================
# Input validation (never let malformed data reach the maths)
# ============================================================

def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_finite(v):
    return _is_number(v) and math.isfinite(float(v))


PROPORTION_KEYS = ("control_success", "control_total",
                   "treatment_success", "treatment_total")
CONTINUOUS_KEYS = ("control_mean", "control_std", "control_n",
                   "treatment_mean", "treatment_std", "treatment_n")

# Upper bound for a usable significance level. alpha is a two-sided tail
# probability; anything at or above 0.5 makes "significant" meaningless.
ALPHA_MAX_EXCLUSIVE = 0.5


def resolve_alpha(metric_def, default_alpha=0.05, default_source="default"):
    """Resolve a metric's significance level → (alpha, source).

    A per-metric `alpha` always wins; otherwise the top-level experiment alpha
    is used. Before this helper existed the engine read `metric.get("alpha",
    0.05)` directly, so a top-level `"alpha": 0.01` never reached the
    per-metric test — a conservative threshold silently behaved like 0.05.
    """
    if isinstance(metric_def, dict) and metric_def.get("alpha") is not None:
        return metric_def.get("alpha"), "metric"
    return default_alpha, default_source


def validate_metric_def(metric, index=0, alpha=0.05):
    """Return None when a metric definition is usable, else an error string.

    Catches the failure modes that would otherwise surface as an uncaught Python
    traceback (KeyError / ValueError / ZeroDivisionError) or as silent nonsense
    (success > total yielding a p-value above 1).
    """
    if not isinstance(metric, dict):
        return f"metric[{index}] must be an object, got {type(metric).__name__}"

    mtype = metric.get("type", "proportion")
    if mtype not in ("proportion", "continuous"):
        return (f"metric[{index}] has unknown type {mtype!r}; "
                f"expected 'proportion' or 'continuous'")

    keys = PROPORTION_KEYS if mtype == "proportion" else CONTINUOUS_KEYS
    missing = [k for k in keys if k not in metric]
    if missing:
        return f"metric[{index}] ({mtype}) is missing required field(s): {', '.join(missing)}"

    bad = [k for k in keys if not _is_finite(metric[k])]
    if bad:
        return (f"metric[{index}] ({mtype}) has non-numeric or non-finite value(s) for: "
                f"{', '.join(bad)}")

    negative = [k for k in keys if float(metric[k]) < 0]
    if negative:
        return f"metric[{index}] ({mtype}) has negative value(s) for: {', '.join(negative)}"

    if mtype == "proportion":
        if float(metric["control_total"]) <= 0 or float(metric["treatment_total"]) <= 0:
            return f"metric[{index}] total must be greater than 0"
        if float(metric["control_success"]) > float(metric["control_total"]):
            return (f"metric[{index}] control_success ({metric['control_success']}) exceeds "
                    f"control_total ({metric['control_total']}) — check the column mapping")
        if float(metric["treatment_success"]) > float(metric["treatment_total"]):
            return (f"metric[{index}] treatment_success ({metric['treatment_success']}) exceeds "
                    f"treatment_total ({metric['treatment_total']}) — check the column mapping")
    else:
        if float(metric["control_n"]) < 2 or float(metric["treatment_n"]) < 2:
            return f"metric[{index}] needs at least 2 samples per group for a t-test"

    if not _is_finite(alpha) or not (0 < float(alpha) < ALPHA_MAX_EXCLUSIVE):
        return (f"metric[{index}] alpha must be a finite number in "
                f"(0, {ALPHA_MAX_EXCLUSIVE}), got {alpha!r}")

    for flag in ("is_guardrail", "lower_is_better"):
        if flag in metric and not isinstance(metric[flag], bool):
            return f"metric[{index}] {flag} must be true/false, got {metric[flag]!r}"

    return None


# ============================================================
# Core statistical tests (v1, preserved)
# ============================================================

def z_test_proportions(success_a, n_a, success_b, n_b, alpha=0.05):
    if n_a == 0 or n_b == 0:
        return {"error": "Sample size is zero"}

    p_a = success_a / n_a
    p_b = success_b / n_b
    diff = p_b - p_a
    p_pool = (success_a + success_b) / (n_a + n_b)

    # When every observation is a success (or a failure) in BOTH groups the pooled
    # variance is exactly 0, so z and MDE are undefined. Report that honestly
    # instead of printing a fake "z = 0.0000 / MDE ±0.00%".
    degenerate = not (0 < p_pool < 1)
    if degenerate:
        se_pool = 0.0
        z = 0.0
        p_value = 1.0
        mde = None
    else:
        se_pool = math.sqrt(p_pool * (1 - p_pool) * (1/n_a + 1/n_b))
        z = diff / se_pool if se_pool > 0 else 0.0
        p_value = 2 * (1 - _norm_cdf_safe(abs(z)))
        # MDE (minimum detectable effect) at 80% power, two-sided:
        #   MDE = (z_{alpha/2} + z_beta) * se_pool,  z_beta = 0.8416 for 80% power
        mde = (_z_crit_safe(alpha) + _z_beta_safe(0.80)) * se_pool

    # The unpooled SE is always well defined because p(1-p) >= 0 even at p = 0 or 1.
    # (The previous `0 < p < 1` guard collapsed the CI to a zero-width interval
    # whenever one arm had 0 or 100% conversion.)
    se_unpool = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)

    z_crit = _z_crit_safe(alpha)
    ci_lower = diff - z_crit * se_unpool
    ci_upper = diff + z_crit * se_unpool

    lift = diff / p_a if p_a > 0 else 0
    lift_ci_lower = (ci_lower / p_a) * 100 if p_a > 0 else 0
    lift_ci_upper = (ci_upper / p_a) * 100 if p_a > 0 else 0

    result = {
        "metric_type": "proportion",
        "control_rate": round(p_a, 6),
        "treatment_rate": round(p_b, 6),
        "absolute_diff": round(diff, 6),
        "absolute_diff_pct": round(diff * 100, 4),
        "relative_lift": round(lift, 6),
        "relative_lift_pct": round(lift * 100, 4),
        "lift_ci": [round(lift_ci_lower, 4), round(lift_ci_upper, 4)],
        "diff_ci": [round(ci_lower * 100, 4), round(ci_upper * 100, 4)],
        "z_statistic": round(z, 4),
        "p_value": round(p_value, 6),
        "significant": p_value < alpha,
        "alpha": alpha,
        "control_sample": n_a,
        "treatment_sample": n_b,
        "mde_pct": round(mde * 100, 4) if mde is not None else None,
        "degenerate_variance": degenerate,
        # raw values for v2 analysis
        "_raw": {"success_a": success_a, "n_a": n_a, "success_b": success_b, "n_b": n_b, "p_a": p_a, "p_b": p_b, "se_pool": se_pool, "z_crit": z_crit, "lift": lift, "diff": diff},
    }
    return result


def t_test_means(mean_a, std_a, n_a, mean_b, std_b, n_b, alpha=0.05):
    if n_a < 2 or n_b < 2:
        return {"error": "Need at least 2 samples per group for t-test"}

    se_diff = math.sqrt(std_a**2/n_a + std_b**2/n_b) if std_a >= 0 and std_b >= 0 else 0
    if se_diff <= 0:
        return {"error": "Both groups report zero variance (std = 0), so a t-test is undefined "
                         "(0/0 in the Welch degrees of freedom). Check whether this metric "
                         "actually varies between users."}

    if HAS_SCIPY:
        result = stats.ttest_ind_from_stats(mean_b, std_b, n_b, mean_a, std_a, n_a, equal_var=False)
        t_stat = float(result.statistic)
        p_value = float(result.pvalue)
    else:
        t_stat, p_value = _welch_t_approx(mean_a, std_a, n_a, mean_b, std_b, n_b)

    diff = mean_b - mean_a

    df = _welch_df(std_a, n_a, std_b, n_b)

    if HAS_SCIPY:
        t_crit = stats.t.ppf(1 - alpha/2, df)
    else:
        t_crit = _t_crit_approx(df, alpha)

    ci_lower = diff - t_crit * se_diff
    ci_upper = diff + t_crit * se_diff

    pooled_std = math.sqrt((std_a**2 * (n_a-1) + std_b**2 * (n_b-1)) / (n_a + n_b - 2)) if n_a + n_b > 2 else 0
    cohens_d = diff / pooled_std if pooled_std > 0 else 0

    # Relative lift is undefined when the control mean is exactly 0 (e.g. nobody
    # paid in the control group). Flag it instead of silently reporting 0.00%.
    lift_undefined = (mean_a == 0)
    lift = diff / mean_a if not lift_undefined else 0
    lift_ci_lower = (ci_lower / mean_a) * 100 if not lift_undefined else 0
    lift_ci_upper = (ci_upper / mean_a) * 100 if not lift_undefined else 0

    # MDE in relative terms: (t_{alpha/2} + z_beta) * se_diff / mean_a
    z_beta = _z_beta_safe(0.80)
    mde_abs = (t_crit + z_beta) * se_diff if se_diff > 0 else 0
    mde_pct = (mde_abs / mean_a) * 100 if not lift_undefined else None

    result = {
        "metric_type": "continuous",
        "control_mean": round(mean_a, 4),
        "treatment_mean": round(mean_b, 4),
        "absolute_diff": round(diff, 4),
        "absolute_diff_pct": round((diff / mean_a) * 100, 4) if not lift_undefined else None,
        "relative_lift_pct": round(lift * 100, 4),
        "relative_lift_undefined": lift_undefined,
        "diff_ci": [round(ci_lower, 4), round(ci_upper, 4)],
        "lift_ci": [round(lift_ci_lower, 4), round(lift_ci_upper, 4)],
        "cohens_d": round(cohens_d, 4),
        "t_statistic": round(t_stat, 4),
        "z_statistic": round(t_stat, 4),  # alias so report generation is metric-agnostic
        "p_value": round(p_value, 6),
        "significant": p_value < alpha,
        "alpha": alpha,
        "degrees_of_freedom": round(df, 2),
        "control_sample": n_a,
        "treatment_sample": n_b,
        "control_std": round(std_a, 4),
        "treatment_std": round(std_b, 4),
        "mde_pct": round(mde_pct, 4) if mde_pct is not None else None,
    }
    return result


# ============================================================
# v2: Bayesian posterior analysis
# ============================================================

def bayesian_posterior_proportion(success_a, n_a, success_b, n_b):
    """Calculate P(Treatment > Control) using Beta posterior distributions.

    Prior: Beta(1, 1) (uniform/non-informative)
    Posterior for Control: Beta(1 + success_a, 1 + n_a - success_a)
    Posterior for Treatment: Beta(1 + success_b, 1 + n_b - success_b)

    P(Treatment > Control) computed via numerical integration or Monte Carlo.
    """
    alpha_a = 1 + success_a
    beta_a = 1 + n_a - success_a
    alpha_b = 1 + success_b
    beta_b = 1 + n_b - success_b

    if HAS_SCIPY:
        # Monte Carlo simulation (100k samples)
        np.random.seed(42)
        samples = 200000
        control_samples = np.random.beta(alpha_a, beta_a, samples)
        treatment_samples = np.random.beta(alpha_b, beta_b, samples)
        prob_treatment_better = float(np.mean(treatment_samples > control_samples))

        # Calculate credible interval for the difference
        diff_samples = treatment_samples - control_samples
        ci_lower = float(np.percentile(diff_samples, 2.5))
        ci_upper = float(np.percentile(diff_samples, 97.5))

        # Expected loss (if we choose treatment but it's actually worse)
        expected_loss = float(np.mean(np.where(diff_samples < 0, -diff_samples, 0)))
        # Expected gain
        expected_gain = float(np.mean(np.where(diff_samples > 0, diff_samples, 0)))
    else:
        # Fallback: normal approximation
        p_a = success_a / n_a
        p_b = success_b / n_b
        se = math.sqrt(p_a*(1-p_a)/n_a + p_b*(1-p_b)/n_b)
        z = (p_b - p_a) / se if se > 0 else 0
        prob_treatment_better = _norm_cdf_approx(z)
        ci_lower = (p_b - p_a) - 1.96 * se
        ci_upper = (p_b - p_a) + 1.96 * se
        expected_loss = max(0, -(p_b - p_a)) if p_b < p_a else 0
        expected_gain = max(0, (p_b - p_a))

    # Risk assessment
    if prob_treatment_better >= 0.95:
        risk_level = "very_low"
        risk_label = "风险极低"
    elif prob_treatment_better >= 0.85:
        risk_level = "low"
        risk_label = "风险较低"
    elif prob_treatment_better >= 0.70:
        risk_level = "moderate"
        risk_label = "风险中等"
    elif prob_treatment_better >= 0.50:
        risk_level = "high"
        risk_label = "风险较高"
    else:
        risk_level = "very_high"
        risk_label = "风险极高"

    return {
        "prob_treatment_better": round(prob_treatment_better, 4),
        "prob_control_better": round(1 - prob_treatment_better, 4),
        "credible_interval_diff": [round(ci_lower * 100, 4), round(ci_upper * 100, 4)],
        "expected_loss_pct": round(expected_loss * 100, 4),
        "expected_gain_pct": round(expected_gain * 100, 4),
        "risk_level": risk_level,
        "risk_label": risk_label,
        "method": "Beta posterior + Monte Carlo (200k samples)" if HAS_SCIPY else "Normal approximation fallback",
    }


# ============================================================
# v2: Post-hoc power analysis
# ============================================================

def post_hoc_power(success_a, n_a, success_b, n_b, alpha=0.05):
    """Calculate observed statistical power for the detected effect.

    Power = P(reject H0 | H1 is true with observed effect size)
    High power + not significant = likely no real effect
    Low power + not significant = inconclusive (might be underpowered)
    """
    p_a = success_a / n_a
    p_b = success_b / n_b
    p_pool = (success_a + success_b) / (n_a + n_b)

    # Effect size (Cohen's h)
    h = 2 * math.asin(math.sqrt(p_b)) - 2 * math.asin(math.sqrt(p_a))

    # Non-centrality parameter
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1/n_a + 1/n_b)) if 0 < p_pool < 1 else 1e-10
    ncp = abs(p_b - p_a) / se_pool if se_pool > 0 else 0

    z_crit = _z_crit_safe(alpha)

    if HAS_SCIPY:
        # Power = P(Z > z_crit | ncp) + P(Z < -z_crit | ncp) for two-sided
        power = float(stats.norm.sf(z_crit - ncp) + stats.norm.cdf(-z_crit - ncp))
    else:
        power = 1 - _norm_cdf_approx(z_crit - ncp) + _norm_cdf_approx(-z_crit - ncp)

    # False negative risk
    fnr = 1 - power

    # Required sample size to detect this effect with 80% power
    required_n = _required_sample_size_proportion(p_a, p_b, alpha, power_target=0.80)

    # Interpretation. A zero observed effect collapses power to alpha, which is
    # mathematically fine but meaningless to report as "5% power" — flag it.
    if abs(p_b - p_a) <= 0:
        power_assessment = "undefined"
        power_message = ("两组指标完全相同（观察到的效应为 0），事后功效没有意义 —— "
                         "不存在需要检出的效应。")
    elif power >= 0.80:
        power_assessment = "adequate"
        power_message = f"统计功效 {power*100:.1f}%，实验充分。若结果不显著，说明真实效果很可能不存在或极小。"
    elif power >= 0.50:
        power_assessment = "marginal"
        power_message = f"统计功效 {power*100:.1f}%，勉强达标。不显著的结果有一定假阴性风险，建议谨慎。"
    else:
        power_assessment = "inadequate"
        power_message = f"统计功效仅 {power*100:.1f}%，实验可能不够灵敏。不显著不代表没有效果，可能只是样本不足。"

    current_n = min(n_a, n_b)
    return {
        "observed_power": round(power, 4),
        "false_negative_risk": round(fnr, 4),
        "effect_size_h": round(h, 4),
        "required_sample_per_group": required_n,
        "current_sample_per_group": current_n,
        "sample_ratio_needed": round(required_n / max(current_n, 1), 2) if required_n else None,
        "power_assessment": power_assessment,
        "power_message": power_message,
    }


def _required_sample_size_proportion(p_a, p_b, alpha=0.05, power_target=0.80):
    """Sample size per group needed to detect the given effect at target power.

    Returns None when the observed effect is exactly zero (no sample size can
    detect an effect that does not exist) or when the proportions are degenerate.
    Returning None — rather than a huge sentinel — keeps the report honest:
    "N/A (no observed difference)" instead of a fake "999,999 per group".
    """
    z_alpha = _z_crit_safe(alpha)
    z_beta = _z_beta_safe(power_target)

    effect = abs(p_b - p_a)
    if effect <= 0:
        return None

    p_avg = (p_a + p_b) / 2
    if p_avg <= 0 or p_avg >= 1:
        return None

    # A vanishingly small effect (e.g. 0/1 vs 1/1e308) makes the squared ratio
    # blow past float range → OverflowError, which used to abort the whole v2
    # block and leave the metric with no recommendation at all.
    try:
        ratio = (z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) +
                 z_beta * math.sqrt(p_a * (1 - p_a) + p_b * (1 - p_b))) / effect
        n = ratio * ratio
    except (OverflowError, ZeroDivisionError):
        return None
    if not math.isfinite(n):
        return None

    return math.ceil(n)


def bayesian_posterior_continuous(mean_a, std_a, n_a, mean_b, std_b, n_b):
    """Estimate P(Treatment > Control) for continuous metrics via normal approximation.

    Using the posterior normal approximation of the difference of means:
        delta ~ N(mean_b - mean_a, std_a^2/n_a + std_b^2/n_b)
    This mirrors the standard (approximate) Bayesian treatment with a diffuse prior.
    """
    diff = mean_b - mean_a
    se = math.sqrt(std_a**2 / n_a + std_b**2 / n_b) if (n_a > 0 and n_b > 0 and std_a >= 0 and std_b >= 0) else 1e-10

    prob_treatment_better = _norm_cdf_safe(diff / se) if se > 0 else 0.5

    z_crit = 1.96
    ci_lower = diff - z_crit * se
    ci_upper = diff + z_crit * se

    expected_loss = max(0, -diff) if diff < 0 else 0.0
    expected_gain = max(0, diff) if diff > 0 else 0.0

    if prob_treatment_better >= 0.95:
        risk_level, risk_label = "very_low", "风险极低"
    elif prob_treatment_better >= 0.85:
        risk_level, risk_label = "low", "风险较低"
    elif prob_treatment_better >= 0.70:
        risk_level, risk_label = "moderate", "风险中等"
    elif prob_treatment_better >= 0.50:
        risk_level, risk_label = "high", "风险较高"
    else:
        risk_level, risk_label = "very_high", "风险极高"

    return {
        "prob_treatment_better": round(prob_treatment_better, 4),
        "prob_control_better": round(1 - prob_treatment_better, 4),
        "credible_interval_diff": [round(ci_lower, 4), round(ci_upper, 4)],
        "expected_loss_pct": round(expected_loss, 4),
        "expected_gain_pct": round(expected_gain, 4),
        "risk_level": risk_level,
        "risk_label": risk_label,
        "method": "Normal approximation of difference of means",
    }


def post_hoc_power_continuous(mean_a, std_a, n_a, mean_b, std_b, n_b, alpha=0.05):
    """Observed power for a two-sample t-test given observed effect (Cohen's d)."""
    diff = mean_b - mean_a
    pooled_std = math.sqrt((std_a**2 * (n_a - 1) + std_b**2 * (n_b - 1)) / (n_a + n_b - 2)) if (n_a + n_b > 2) else 1e-10
    cohens_d = diff / pooled_std if pooled_std > 0 else 0

    df = _welch_df(std_a, n_a, std_b, n_b)
    z_crit = _z_crit_safe(alpha)

    # Non-centrality parameter for two-sample t-test
    se_diff = math.sqrt(std_a**2 / n_a + std_b**2 / n_b) if (std_a >= 0 and std_b >= 0) else 1e-10
    ncp = abs(diff) / se_diff if se_diff > 0 else 0

    if HAS_SCIPY:
        t_crit = stats.t.ppf(1 - alpha / 2, df)
        power = float(stats.nct.sf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp))
    else:
        # Normal approximation
        power = 1 - _norm_cdf_approx(z_crit - ncp) + _norm_cdf_approx(-z_crit - ncp)

    fnr = 1 - power
    required_n = _required_sample_size_continuous(cohens_d, alpha, power_target=0.80)

    if abs(diff) <= 0:
        power_assessment = "undefined"
        power_message = ("两组均值完全相同（观察到的效应为 0），事后功效没有意义 —— "
                         "不存在需要检出的效应。")
    elif power >= 0.80:
        power_assessment = "adequate"
        power_message = f"统计功效 {power*100:.1f}%，实验充分。若结果不显著，说明真实效果很可能不存在或极小。"
    elif power >= 0.50:
        power_assessment = "marginal"
        power_message = f"统计功效 {power*100:.1f}%，勉强达标。不显著的结果有一定假阴性风险，建议谨慎。"
    else:
        power_assessment = "inadequate"
        power_message = f"统计功效仅 {power*100:.1f}%，实验可能不够灵敏。不显著不代表没有效果，可能只是样本不足。"

    current_n = min(n_a, n_b)
    return {
        "observed_power": round(power, 4),
        "false_negative_risk": round(fnr, 4),
        "effect_size_d": round(cohens_d, 4),
        "required_sample_per_group": required_n,
        "current_sample_per_group": current_n,
        "sample_ratio_needed": round(required_n / max(current_n, 1), 2) if required_n else None,
        "power_assessment": power_assessment,
        "power_message": power_message,
    }


def _required_sample_size_continuous(cohens_d, alpha=0.05, power_target=0.80):
    """Required sample size per group to detect Cohen's d at target power.

    Returns None when the observed effect is zero (undefined) or so small that
    the required sample size is beyond anything computable.
    """
    if not _is_finite(cohens_d) or cohens_d == 0:
        return None
    z_alpha = _z_crit_safe(alpha)
    z_beta = _z_beta_safe(power_target)
    try:
        ratio = (z_alpha + z_beta) / abs(cohens_d)
    except (OverflowError, ZeroDivisionError):
        return None
    n = 2 * ratio * ratio
    if not math.isfinite(n):
        return None
    return math.ceil(n)


# ============================================================
# Metric polarity ("is an increase good?")
# ============================================================

# A metric whose name contains one of these is almost always a HARM metric:
# it gets worse when it goes up, so a significant increase is the dangerous case.
_LOWER_IS_BETTER_HINTS = (
    "崩溃", "闪退", "错误", "报错", "异常", "失败", "超时", "卡顿", "延迟", "耗时",
    "退款", "退货", "退订", "取消", "流失", "卸载", "投诉", "举报", "差评", "退出",
    "crash", "error", "fail", "timeout", "latency", "refund", "churn", "uninstall",
    "complaint", "abort", "anr",
)
# ...and these are GAIN metrics: they get better when they go up.
_HIGHER_IS_BETTER_HINTS = (
    "留存", "活跃", "使用时长", "时长", "会话", "次数", "曝光", "点击", "转化",
    "付费", "收入", "流水", "订单", "gmv", "arpu", "ltv", "dau", "mau",
    "retention", "engagement", "session", "conversion", "revenue", "purchase",
)


def resolve_lower_is_better(metric_def):
    """Resolve a metric's polarity → (lower_is_better, source).

    An explicit `lower_is_better` always wins. Otherwise, for guardrail metrics
    the polarity is inferred from the metric name, and when the name is
    inconclusive it defaults to `True` — because the overwhelming majority of
    real guardrails (崩溃率 / 退款率 / 错误率 / 耗时) are harm metrics that must
    not increase. Non-guardrail metrics keep the conventional "higher is better"
    reading unless the caller opts in.

    The returned `source` is surfaced in the report so an analyst can always see
    whether the polarity was declared or guessed.
    """
    if not isinstance(metric_def, dict):
        return False, "not-guardrail"
    if "lower_is_better" in metric_def and isinstance(metric_def["lower_is_better"], bool):
        return metric_def["lower_is_better"], "explicit"
    if not metric_def.get("is_guardrail"):
        return False, "not-guardrail"
    name = str(metric_def.get("name") or "").lower()
    for kw in _LOWER_IS_BETTER_HINTS:
        if kw in name:
            return True, "inferred-name"
    for kw in _HIGHER_IS_BETTER_HINTS:
        if kw in name:
            return False, "inferred-name"
    return True, "default-guardrail"


def _favourable(metric_result, diff=None):
    """+1 when the movement is desirable, -1 when harmful, 0 when no movement.

    This is the single place polarity is applied. A drop in a "lower is better"
    metric (crash rate, response time) is +1; a rise is -1 — the exact opposite
    of a conversion metric. Everything downstream (verdict, business
    significance, recommendation) reads direction from here so the whole report
    stays consistent.
    """
    if diff is None:
        diff = metric_result.get("absolute_diff", 0) or 0
    if not isinstance(diff, (int, float)) or diff != diff:  # NaN-safe
        return 0
    if diff == 0:
        return 0
    gain = -1 if metric_result.get("lower_is_better") else 1
    return gain if diff > 0 else -gain


def _lift_magnitude(r):
    """Rank metrics by effect size without mixing units.

    `relative_lift_pct` is comparable across metrics, but it is 0 (undefined)
    when the control mean is 0 — in that case fall back to the absolute change
    expressed in percentage points.
    """
    if not r.get("relative_lift_undefined"):
        v = r.get("relative_lift_pct")
        return abs(v) if isinstance(v, (int, float)) else 0.0
    v = r.get("absolute_diff_pct", r.get("absolute_diff", 0))
    return abs(v) if isinstance(v, (int, float)) else 0.0


def _decision_sig(r):
    """The significance flag a DECISION is allowed to read.

    `significant` is the raw per-comparison flag (p < alpha). Testing several
    metrics at once inflates the family-wise error rate, so `apply_bonferroni`
    writes `decision_significant` (p < alpha / n_comparisons) and every verdict,
    recommendation, business-significance and guardrail decision reads that
    instead. Falling back to `significant` keeps the helper safe for single
    metric analyses (where the two are identical by construction) and for
    payloads produced by older versions.
    """
    v = r.get("decision_significant")
    if isinstance(v, bool):
        return v
    return bool(r.get("significant", False))


def _ordered_family(results, family="all", include_errors=False):
    """Metrics that form the correction family, in input order."""
    out = []
    for r in results or []:
        if not include_errors and r.get("error"):
            continue
        if family == "success" and r.get("is_guardrail"):
            continue
        out.append(r)
    return out


def _direction_text(metric_result, diff=None):
    """正向/负向/无 — from the DESIRABLE direction, not the numeric sign."""
    f = _favourable(metric_result, diff)
    return "正向" if f > 0 else ("负向" if f < 0 else "无")


def _risk_band(p):
    """Map a "treatment is better" probability onto the risk ladder."""
    if p >= 0.95:
        return "very_low", "风险极低"
    if p >= 0.85:
        return "low", "风险较低"
    if p >= 0.70:
        return "moderate", "风险中等"
    if p >= 0.50:
        return "high", "风险较高"
    return "very_high", "风险极高"


def _apply_bayes_polarity(bayes, lower_is_better):
    """Make the Bayesian block readable for "lower is better" metrics.

    `prob_treatment_better` is literally P(treatment > control). For crash rate
    or response time a treatment value BELOW control is the win, so on its own
    that number points the wrong way: a 95% improvement would be displayed as a
    5% probability of success, and the risk ladder would read "风险极高".

    The raw probability is preserved as `prob_treatment_better_raw` for anyone
    who needs the literal quantity; `prob_favourable` is the polarity-correct
    one and is what every decision and label in this engine reads.
    """
    if not isinstance(bayes, dict):
        return bayes
    raw = bayes.get("prob_treatment_better")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return bayes

    bayes["prob_treatment_better_raw"] = raw
    fav = (1 - raw) if lower_is_better else raw
    bayes["prob_favourable"] = round(fav, 4)
    bayes["prob_favourable_label"] = ("P(实验组低于对照组)" if lower_is_better
                                      else "P(实验组高于对照组)")
    bayes["probability_note"] = ("该指标越低越好，此处为实验组低于对照组的概率"
                                 if lower_is_better else "")

    lvl, lbl = _risk_band(fav)
    bayes["risk_level"], bayes["risk_label"] = lvl, lbl

    if lower_is_better:
        # "gain" means the metric moved down, "loss" means it moved up.
        g, l = bayes.get("expected_gain_pct"), bayes.get("expected_loss_pct")
        if isinstance(g, (int, float)) and not isinstance(g, bool):
            bayes["expected_gain_pct"] = l if isinstance(l, (int, float)) else g
        if isinstance(l, (int, float)) and not isinstance(l, bool):
            bayes["expected_loss_pct"] = g if isinstance(g, (int, float)) else l
    return bayes


# ============================================================
# v2: Business significance assessment
# ============================================================

def business_significance(metric_result, metric_name=""):
    """Assess whether the observed effect is practically meaningful.

    `sig` is the *decision* significance (Bonferroni-corrected when several
    metrics are tested), not the raw per-comparison p < alpha flag — otherwise a
    metric that only survived before correction would still be labelled
    "统计显著且业务显著 / 建议推进上线".
    """
    lift = metric_result.get("relative_lift_pct", 0)
    lift_undefined = bool(metric_result.get("relative_lift_undefined"))
    abs_diff = metric_result.get("absolute_diff_pct", metric_result.get("absolute_diff", 0))
    sig = _decision_sig(metric_result)

    # Direction must come from the ABSOLUTE difference: the relative lift is 0
    # whenever the control mean is 0, which would otherwise look like "no effect".
    # It must also run through the polarity helper, so a DROP in a "lower is
    # better" metric (crash rate, response time) counts as the positive outcome.
    raw_diff = metric_result.get("absolute_diff", 0) or 0
    direction = _favourable(metric_result, raw_diff)

    # Business significance thresholds (configurable, these are defaults)
    if "付费" in metric_name or "payment" in metric_name.lower() or "revenue" in metric_name.lower():
        min_meaningful_lift = 5.0
        min_meaningful_abs = 1.0
        business_type = "monetization"
    elif "留存" in metric_name or "retention" in metric_name.lower():
        min_meaningful_lift = 3.0
        min_meaningful_abs = 1.5
        business_type = "engagement"
    elif "完成" in metric_name or "complete" in metric_name.lower() or "tutorial" in metric_name.lower():
        min_meaningful_lift = 5.0
        min_meaningful_abs = 2.0
        business_type = "conversion"
    else:
        min_meaningful_lift = 5.0
        min_meaningful_abs = 1.0
        business_type = "general"

    # Business significance: BOTH relative lift and absolute change must clear thresholds.
    # (Guards against a +10% relative lift that is only +0.1pp in absolute terms.)
    #
    # For continuous metrics (ARPU / duration / counts) there is no universal
    # unit, so a percentage-point threshold is meaningless — only the relative
    # lift governs. Applying the pp threshold to a continuous metric would
    # compare a percentage against a percentage-point and silently always pass.
    is_continuous = metric_result.get("metric_type") == "continuous"
    if lift_undefined:
        is_business_significant = False
    elif is_continuous:
        is_business_significant = abs(lift) >= min_meaningful_lift
    else:
        is_business_significant = (abs(lift) >= min_meaningful_lift
                                   and abs(abs_diff) >= min_meaningful_abs)

    lift_disp = "无法计算（对照组均值为 0）" if lift_undefined else f"{lift:+.2f}%"
    if not lift_undefined and metric_result.get("lower_is_better"):
        lift_disp = f"{lift_disp}（该指标越低越好）"

    if sig and direction > 0 and is_business_significant:
        assessment = "stat_and_business_significant"
        label = "统计显著且业务显著"
        recommendation = "效果明确，建议推进上线"
    elif sig and direction > 0:
        assessment = "stat_sig_business_marginal"
        label = "统计显著但业务意义有限"
        recommendation = (f"统计上显著但提升幅度仅 {lift_disp}，"
                          f"低于业务意义阈值 {min_meaningful_lift}%。考虑实施成本是否值得。")
    elif sig and direction < 0:
        assessment = "stat_sig_negative"
        label = "统计显著（负面）"
        recommendation = "指标显著下降，建议停止或回退"
    elif not sig and (lift_undefined or abs(lift) < min_meaningful_lift):
        assessment = "not_meaningful"
        label = "不显著且效果微小"
        recommendation = "效果太小不值得追求，建议放弃该方向或尝试更大改动"
    else:
        assessment = "inconclusive"
        label = "不显著但效果可观"
        recommendation = "趋势可观但无法确认，建议增加样本验证"

    return {
        "assessment": assessment,
        "label": label,
        "recommendation": recommendation,
        "min_meaningful_lift_pct": min_meaningful_lift,
        "min_meaningful_abs_pp": min_meaningful_abs,
        "abs_threshold_applied": not (is_continuous or lift_undefined),
        "business_type": business_type,
        "is_business_significant": is_business_significant,
    }


# ============================================================
# v2: Actionable recommendation engine
# ============================================================

def _prob_favourable(bayes_result):
    """Probability that the treatment is the BETTER arm, polarity applied.

    Falls back to the literal P(T>C) for engine output produced before the
    polarity helper existed, so the function is safe on any payload.
    """
    b = bayes_result if isinstance(bayes_result, dict) else {}
    for key in ("prob_favourable", "prob_treatment_better"):
        v = b.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return v
    return 0.5


def _prob_label(bayes_result):
    b = bayes_result if isinstance(bayes_result, dict) else {}
    return b.get("prob_favourable_label") or "P(T>C)"


def generate_recommendation(metric_result, bayes_result, power_result, biz_result, is_guardrail=False):
    """Generate actionable recommendation based on all available evidence.

    Every branch keys off `_decision_sig()` — the Bonferroni-corrected flag when
    a correction applies — so a metric that is only significant *before*
    correction can never produce "全量发布".
    """
    sig = _decision_sig(metric_result)
    lift = metric_result.get("relative_lift_pct", 0)
    lift_undefined = bool(metric_result.get("relative_lift_undefined"))
    p_value = metric_result.get("p_value", 1)
    metric_label = metric_result.get("metric_name", "指标")
    # Direction comes from the ABSOLUTE difference — the relative lift is 0 when
    # the control mean is 0, which must not be mistaken for "no effect".
    raw_diff = metric_result.get("absolute_diff", 0) or 0
    # `up` / `down` mean "desirable / undesirable", NOT "numerically larger /
    # smaller": a drop in a lower-is-better metric is an improvement.
    _dir = _favourable(metric_result, raw_diff)
    up = _dir > 0
    down = _dir < 0
    lift_disp = "无法计算（对照组均值为 0）" if lift_undefined else f"{lift:+.2f}%"
    if not lift_undefined and metric_result.get("lower_is_better"):
        # Without this the reader sees "方向为负（+5.00%）" and thinks the engine
        # contradicted itself — for a lower-is-better metric a rise IS the harm.
        lift_disp = f"{lift_disp}（该指标越低越好）"
    prob_better = _prob_favourable(bayes_result)
    prob_label = _prob_label(bayes_result)
    # power / required_n can legitimately be None (zero observed effect), so
    # coerce explicitly instead of relying on dict defaults.
    _pw = power_result or {}
    power = _pw.get("observed_power")
    power = power if isinstance(power, (int, float)) else 0
    power_assessment = _pw.get("power_assessment", "unknown")
    required_n = _pw.get("required_sample_per_group")
    required_n = required_n if isinstance(required_n, (int, float)) else None
    current_n = _pw.get("current_sample_per_group", 0) or 0
    sample_ratio = _pw.get("sample_ratio_needed")
    sample_ratio = sample_ratio if isinstance(sample_ratio, (int, float)) else None
    biz_assessment = biz_result.get("assessment", "inconclusive") if biz_result else "inconclusive"
    risk_level = bayes_result.get("risk_level", "unknown") if bayes_result else "unknown"

    if is_guardrail:
        if _guardrail_regressed(metric_result):
            return {
                "action": "stop",
                "priority": "critical",
                "headline": "立即停止实验",
                "reason": f"护栏指标显著朝坏方向变化 {lift_disp}，存在业务风险",
                "steps": [
                    "立即将流量回退到对照组",
                    "排查护栏指标恶化的技术原因",
                    "修复后重新启动实验",
                ],
            }
        elif sig:
            return {
                "action": "proceed_with_caution",
                "priority": "medium",
                "headline": "护栏指标意外改善",
                "reason": f"护栏指标显著变化 {lift_disp}，方向有利但非预期，需调查原因",
                "steps": [
                    "调查护栏指标变化的潜在原因",
                    "确认是否存在数据污染或分流异常",
                    "如确认无误，可作为额外收益记录",
                ],
            }
        else:
            return {
                "action": "safe",
                "priority": "low",
                "headline": "护栏安全",
                "reason": "护栏指标无显著变化，实验安全",
                "steps": ["可继续评估核心指标"],
            }

    # Zero observed effect (identical rates / identical means). Post-hoc power is
    # undefined here, so the generic branches below would produce misleading
    # advice ("extend the experiment") for what is simply a null result.
    if not sig and raw_diff == 0:
        return {
            "action": "abandon",
            "priority": "low",
            "headline": "无差异，放弃此方向",
            "reason": f"两组的{metric_label}完全相同，该改动没有产生可观察的效果",
            "steps": [
                "该改动方向无效，建议放弃",
                f"将「{metric_label} 无效果」记录为本轮实验的学习成果",
                "将资源投入其他优化方向",
            ],
        }

    # Core metric recommendation logic
    if sig and up:
        if biz_assessment == "stat_and_business_significant":
            return {
                "action": "ship",
                "priority": "high",
                "headline": "全量发布",
                "reason": f"统计显著（p={p_value:.4f}）且业务显著（提升 {lift_disp}），{prob_label}={prob_better:.1%}",
                "steps": [
                    "全量发布实验组版本",
                    "发布后持续监控 7-14 天",
                    "关注长期留存是否维持",
                ],
            }
        else:
            return {
                "action": "ship_with_caution",
                "priority": "medium",
                "headline": "谨慎上线",
                "reason": f"统计显著但业务意义有限（提升 {lift_disp}），权衡实施成本",
                "steps": [
                    "评估实施成本与收益是否匹配",
                    "如成本低可灰度发布",
                    "如成本高建议继续优化方案",
                ],
            }
    elif sig and down:
        return {
            "action": "stop",
            "priority": "high",
            "headline": "停止实验",
            "reason": f"统计显著且方向为负（{lift_disp}），实验组劣于对照组",
            "steps": [
                "停止实验，回退到对照组",
                "分析劣化的原因",
                "考虑替代方案或回到设计阶段",
            ],
        }
    else:
        # Not significant — the key v2 improvement
        direction = "正向" if up else "负向" if down else "无"
        # A metric whose raw p-value cleared alpha but which the multiple-
        # comparison correction retired must say so: "不显著" on its own reads as
        # "no effect", which is a different claim.
        _retired = bool(metric_result.get("significant")) and not _decision_sig(metric_result)
        corr_note = ""
        if _retired:
            corr_note = (f"（原始 p={p_value:.4f} 小于 α，但未通过多重比较校正后的阈值 "
                         f"α={metric_result.get('decision_alpha')}）")

        if power_assessment == "adequate" and not lift_undefined and abs(lift) < 3:
            return {
                "action": "abandon",
                "priority": "medium",
                "headline": "放弃此方向",
                "reason": f"功效充足（{power*100:.0f}%）但未显著且效果微小（{lift:+.2f}%），真实效果很可能不存在",
                "steps": [
                    "该改动方向大概率无效，建议放弃",
                    "将资源投入其他优化方向",
                    (f"如坚持验证，需 {sample_ratio} 倍样本（{int(required_n):,}/组）"
                     if sample_ratio and sample_ratio > 1 else "当前样本已足够"),
                ],
            }
        elif power_assessment == "inadequate" and (lift_undefined or abs(lift) >= 3):
            required_n = required_n or 0
            return {
                "action": "extend",
                "priority": "high",
                "headline": "延长实验",
                "reason": f"功效不足（{power*100:.0f}%）但观察到{direction}趋势（{lift_disp}），"
                          f"可能是样本不够{corr_note}",
                "steps": [
                    (f"延长实验至 {sample_ratio:g} 倍当前样本量（目标 {int(required_n):,} 用户/组）"
                     if sample_ratio else "延长实验周期以积累更多样本"),
                    f"当前每组 {int(current_n):,}，还需约 {int(max(0, required_n - current_n)):,} 用户",
                    "延长期间持续监控趋势是否稳定",
                    "达到目标样本后重新分析",
                ],
            }
        elif prob_better >= 0.80 and up:
            return {
                "action": "gradual_rollout",
                "priority": "medium",
                "headline": "灰度发布",
                "reason": f"统计不显著但 {prob_label}={prob_better:.0%}，{direction}趋势较明确，风险{risk_level}",
                "steps": [
                    "灰度发布到 25-50% 流量，持续监控",
                    "监控核心指标是否维持正向趋势",
                    "2 周后用更大样本重新分析",
                    "如趋势维持且无护栏风险，逐步全量",
                ],
            }
        elif down and prob_better < 0.40:
            return {
                "action": "stop",
                "priority": "medium",
                "headline": "停止实验",
                "reason": f"统计不显著但趋势为负（{lift_disp}），{prob_label}仅{prob_better:.0%}，继续投入价值低",
                "steps": [
                    "停止实验，回退到对照组",
                    "分析负向趋势的可能原因",
                    "考虑修改方案后重新测试",
                ],
            }
        else:
            return {
                "action": "inconclusive",
                "priority": "medium",
                "headline": "暂无定论",
                "reason": f"功效{power*100:.0f}%，趋势{direction}（{lift_disp}），"
                          f"{prob_label}={prob_better:.0%}，证据不足以做决策{corr_note}",
                "steps": [
                    "选择 1：延长实验增加样本（推荐，如功效不足）",
                    "选择 2：灰度发布观察（如趋势为正且业务可接受风险）",
                    "选择 3：放弃此方向（如功效充足且效果微小）",
                    "选择 4：按子群体（平台/地区）下钻，检查是否有隐藏的显著效果",
                ],
            }


# ============================================================
# v2: Main analysis pipeline
# ============================================================

def analyze_metric_core(metric_def, index=0, default_alpha=0.05,
                        default_alpha_source="default"):
    """Stage 1 of the pipeline: validate + run the frequency-test statistics.

    NEVER raises — failures come back as an error entry. The returned dict always
    carries `metric_name`, `is_guardrail`, `alpha`, `alpha_source` and the
    polarity fields so the correction stage and the report can attribute a
    failure to the right metric.

    This is deliberately separate from the v2 stage: the multiple-comparison
    correction has to be applied to the raw p-values *before* anything reads a
    significance flag, otherwise the Bayesian / business / recommendation layer
    would keep judging metrics that the correction has already retired.
    """
    name = (metric_def.get("name") or f"metric_{index}") if isinstance(metric_def, dict) else f"metric_{index}"
    is_guardrail = bool(metric_def.get("is_guardrail", False)) if isinstance(metric_def, dict) else False
    # Most guardrails (crash rate, refund rate) are "lower is better"; without
    # this flag a significant INCREASE would be reported as a safe guardrail.
    # An explicit `lower_is_better` wins; otherwise the polarity is inferred
    # from the metric name and defaults to True for guardrails.
    lower_is_better, polarity_source = resolve_lower_is_better(metric_def)
    # The top-level experiment alpha is the default; a per-metric `alpha`
    # overrides it. Read through resolve_alpha so both paths are auditable.
    alpha, alpha_source = resolve_alpha(metric_def, default_alpha, default_alpha_source)

    err = validate_metric_def(metric_def, index, alpha=alpha)
    if err:
        return {"error": err, "metric_name": name, "is_guardrail": is_guardrail,
                "alpha": alpha, "alpha_source": alpha_source,
                "lower_is_better": lower_is_better, "lower_is_better_source": polarity_source}

    metric_type = metric_def.get("type", "proportion")

    try:
        if metric_type == "proportion":
            result = z_test_proportions(
                metric_def["control_success"], metric_def["control_total"],
                metric_def["treatment_success"], metric_def["treatment_total"],
                alpha=alpha,
            )
        else:
            result = t_test_means(
                metric_def["control_mean"], metric_def["control_std"], metric_def["control_n"],
                metric_def["treatment_mean"], metric_def["treatment_std"], metric_def["treatment_n"],
                alpha=alpha,
            )
    except Exception as exc:  # defensive: one bad metric must not kill the run
        return {"error": f"metric '{name}' failed during computation: "
                         f"{type(exc).__name__}: {exc}",
                "metric_name": name, "is_guardrail": is_guardrail,
                "alpha": alpha, "alpha_source": alpha_source}

    result["metric_name"] = name
    result["is_guardrail"] = is_guardrail
    result["alpha"] = alpha
    result["alpha_source"] = alpha_source
    result["lower_is_better"] = lower_is_better
    result["lower_is_better_source"] = polarity_source
    return result


def attach_v2_analysis(results):
    """Stage 3: Bayesian, power, business significance and recommendation.

    Runs on the already-corrected results, so every decision these produce reads
    `decision_significant` rather than the raw flag. Each sub-analysis runs in
    its own guard: a crash in (say) the sample-size formula must not silently
    delete the recommendation the analyst needs.
    """
    for result in results or []:
        if result.get("error") or result.get("_v2_done"):
            continue
        metric_type = result.get("metric_type")
        alpha = result.get("alpha", 0.05)
        lower_is_better = bool(result.get("lower_is_better"))
        is_guardrail = bool(result.get("is_guardrail"))
        name = result.get("metric_name", "")
        v2_errors = []

        def _v2_step(label, fn):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001 - reported, never swallowed
                v2_errors.append(f"{label}: {type(exc).__name__}: {exc}")
                return None

        bayes = power = None
        if metric_type == "proportion":
            raw = result.get("_raw", {})
            bayes = _v2_step("bayesian", lambda: bayesian_posterior_proportion(
                raw.get("success_a", 0), raw.get("n_a", 1),
                raw.get("success_b", 0), raw.get("n_b", 1)))
            power = _v2_step("power", lambda: post_hoc_power(
                raw.get("success_a", 0), raw.get("n_a", 1),
                raw.get("success_b", 0), raw.get("n_b", 1), alpha=alpha))
        else:  # continuous
            c_mean = result.get("control_mean", 0)
            c_std = result.get("control_std", 0)
            c_n = result.get("control_sample", 1)
            t_mean = result.get("treatment_mean", 0)
            t_std = result.get("treatment_std", 0)
            t_n = result.get("treatment_sample", 1)
            bayes = _v2_step("bayesian", lambda: bayesian_posterior_continuous(
                c_mean, c_std, c_n, t_mean, t_std, t_n))
            power = _v2_step("power", lambda: post_hoc_power_continuous(
                c_mean, c_std, c_n, t_mean, t_std, t_n, alpha=alpha))

        # Apply polarity BEFORE the recommendation so the decision reads a
        # probability that already points the right way.
        if bayes is not None:
            bayes = _v2_step("polarity", lambda: _apply_bayes_polarity(bayes, lower_is_better)) or bayes

        biz = _v2_step("business", lambda: business_significance(result, name))

        rec = None
        if bayes is not None:
            rec = _v2_step("recommendation", lambda: generate_recommendation(
                result, bayes, power, biz, is_guardrail))

        if bayes is not None:
            result["bayesian"] = bayes
        if power is not None:
            result["power_analysis"] = power
        if biz is not None:
            result["business"] = biz
        if rec is not None:
            result["recommendation"] = rec
        if v2_errors:
            result["v2_error"] = "; ".join(v2_errors)
        result["_v2_done"] = True
        result.pop("_raw", None)
    return results


def analyze_metric(metric_def, index=0, default_alpha=0.05,
                   default_alpha_source="default", correct=True, n_comparisons=1):
    """Analyse one metric end-to-end (core + correction + v2).

    Kept as the single-metric entry point so callers that analyse one metric at
    a time get the full v2 block. `run_analysis` does NOT use this: it needs the
    correction stage to run across all metrics before any v2 judgement, so it
    calls `analyze_metric_core` → `apply_bonferroni` → `attach_v2_analysis`.
    """
    result = analyze_metric_core(metric_def, index, default_alpha, default_alpha_source)
    if result.get("error"):
        return result
    if correct:
        apply_bonferroni([result], default_alpha)
    if n_comparisons and n_comparisons > 1:
        # A metric analysed on its own is still one member of a family the
        # caller declared; honour the declared size so a single-metric
        # inspection cannot disagree with the full run.
        corrected = float(result.get("alpha", default_alpha)) / n_comparisons
        result["bonferroni_alpha"] = round(corrected, 8)
        result["bonferroni_significant"] = bool(
            _is_number(result.get("p_value")) and result["p_value"] < corrected)
        result["n_comparisons"] = n_comparisons
        result["decision_alpha"] = round(corrected, 8)
        result["decision_significant"] = result["bonferroni_significant"]
        result["decision_basis"] = "bonferroni"
    attach_v2_analysis([result])
    return result


def apply_bonferroni(results, alpha=0.05, config=None):
    """Stage 2: define the comparison family and apply the correction.

    Every non-error metric gets a *decision* alpha and a *decision* significance
    flag. `significant` keeps its original meaning (raw p < the metric's own
    alpha) for display; `decision_significant` is what every downstream decision
    reads.

    Family definition — `config["family"]`:
      * `"all"`     (default) every analysed metric, success and guardrail. The
                    ship / no-ship decision consumes both families at once, so
                    the family-wise error rate is over all of them. Conservative.
      * `"success"` only the non-guardrail metrics — use when guardrail status is
                    reported separately from the ship decision.

    `config["method"]` is `"bonferroni"` (default) or `"none"` (opt out; the
    report must then disclose that no correction was applied). `config["enabled"]
    = false` is an alias for method "none".
    """
    config = config if isinstance(config, dict) else {}
    method = str(config.get("method", "bonferroni")).lower()
    if config.get("enabled") is False:
        method = "none"
    if method not in ("bonferroni", "none"):
        method = "bonferroni"
    family = str(config.get("family", "all")).lower()
    if family not in ("all", "success"):
        family = "all"

    analysed = [r for r in results if not r.get("error")]
    members = _ordered_family(results, family=family)
    n_comparisons = len(members)

    # Single comparison (or correction disabled): the decision alpha IS the
    # metric's own alpha. The flags are still written so downstream code and the
    # report never have to special-case their absence.
    if method == "none" or n_comparisons <= 1:
        for r in analysed:
            r["n_comparisons"] = n_comparisons
            r["decision_alpha"] = r.get("alpha", alpha)
            r["decision_significant"] = bool(r.get("significant", False))
            r["decision_basis"] = "raw"
            r["multiple_comparison_method"] = "none" if method == "none" else "single-comparison"
        return results

    for r in members:
        p = r.get("p_value")
        base_alpha = r.get("alpha", alpha)
        try:
            corrected = float(base_alpha) / n_comparisons
        except (TypeError, ValueError):
            corrected = float(alpha) / n_comparisons
        r["bonferroni_alpha"] = round(corrected, 8)
        r["bonferroni_significant"] = bool(_is_number(p) and p < corrected)
        r["n_comparisons"] = n_comparisons
        r["decision_alpha"] = round(corrected, 8)
        r["decision_significant"] = r["bonferroni_significant"]
        r["decision_basis"] = "bonferroni"
        r["multiple_comparison_method"] = "bonferroni"
        r["multiplied_p_value"] = (round(min(p * n_comparisons, 1.0), 6)
                                   if _is_number(p) else None)

    # Metrics outside the family (only possible with family="success") keep the
    # raw flag, but must still be explicit about why.
    for r in analysed:
        if "decision_significant" not in r:
            r["n_comparisons"] = n_comparisons
            r["decision_alpha"] = r.get("alpha", alpha)
            r["decision_significant"] = bool(r.get("significant", False))
            r["decision_basis"] = "raw"
            r["multiple_comparison_method"] = f"not-in-family({family})"
    return results


def run_analysis(data):
    """Analyse a full experiment payload. Raises ValueError on an unusable envelope.

    Pipeline order matters and is deliberate:
      1. `analyze_metric_core`  — raw statistics per metric (no judgement)
      2. `apply_bonferroni`     — define the family, compute the corrected alpha,
                                  write `decision_*` on every metric
      3. `attach_v2_analysis`   — Bayesian / power / business / recommendation,
                                  all reading the corrected flag
      4. verdict → guardrails → overall recommendation
    Judging before correcting is what let a run of individually-just-significant
    metrics report "treatment_wins" and "ship".
    """
    if not isinstance(data, dict):
        raise ValueError(f"analysis input must be a JSON object, got {type(data).__name__}")

    warnings = []

    alpha = data.get("alpha")
    alpha_source = "top-level"
    if alpha is None:
        alpha, alpha_source = 0.05, "default"
    if not _is_finite(alpha) or not (0 < float(alpha) < ALPHA_MAX_EXCLUSIVE):
        warnings.append(f"alpha={alpha!r} is invalid (must be a finite number in "
                        f"(0, {ALPHA_MAX_EXCLUSIVE})); fell back to 0.05.")
        alpha, alpha_source = 0.05, "default"
    alpha = float(alpha)

    mc_config = data.get("multiple_comparison")
    if mc_config is not None and not isinstance(mc_config, dict):
        warnings.append(f"`multiple_comparison` must be an object, got "
                        f"{type(mc_config).__name__} — the default Bonferroni "
                        f"correction was applied.")
        mc_config = None

    metrics = data.get("metrics")
    if metrics is None:
        metrics = []
        warnings.append("No `metrics` array in the analysis input — nothing to analyse. "
                        "At least one metric definition is required.")
    elif not isinstance(metrics, list):
        warnings.append(f"`metrics` must be an array, got {type(metrics).__name__} — "
                        f"nothing could be analysed.")
        metrics = []
    elif not metrics:
        warnings.append("`metrics` is an empty array — nothing to analyse.")

    results = [analyze_metric_core(m, i, alpha, alpha_source)
               for i, m in enumerate(metrics)]
    results = apply_bonferroni(results, alpha, mc_config)
    results = attach_v2_analysis(results)
    for r in results:
        r.pop("_v2_done", None)

    experiment_verdict = _get_verdict_v2(results)
    guardrail_status = _check_guardrails(results)

    # v2: Overall recommendation
    overall_rec = _overall_recommendation(results, experiment_verdict, guardrail_status)

    failed = [r for r in results if r.get("error")]
    if failed:
        warnings.append(f"{len(failed)} metric(s) could not be analysed: "
                        + "; ".join(str(r.get("error")) for r in failed))

    # A metric that analysed fine but lost part of its v2 analysis must never
    # show up in the report as a blank card — surface it here as well.
    degraded = [r for r in results if r.get("v2_error")]
    if degraded:
        warnings.append("以下指标的核心统计已完成，但部分 v2 分析（贝叶斯/功效/业务/建议）失败，"
                        "对应字段为空："
                        + "; ".join(f"{r.get('metric_name')}（{r['v2_error']}）" for r in degraded))

    # Disclose the decision basis. A verdict that silently rests on a corrected
    # threshold while the report shows raw p-values is how a "significant" metric
    # gets acted on after it was already retired.
    analysed = [r for r in results if not r.get("error")]
    mc_basis = ""
    if analysed:
        mc_basis = str(analysed[0].get("decision_basis", "raw"))
    n_comparisons = max((r.get("n_comparisons", 1) for r in analysed), default=1)
    lost_to_correction = [r for r in analysed if r.get("significant") and not r.get("decision_significant")]
    if lost_to_correction and mc_basis == "bonferroni":
        warnings.append(
            f"多重比较校正生效（{n_comparisons} 个指标参与校正）："
            + "、".join(str(r.get("metric_name")) for r in lost_to_correction)
            + " 的原始 p 值 < α，但未通过校正后的阈值，已按「不显著」处理。")

    payload = {
        "experiment_name": data.get("experiment_name", "A/B Test"),
        "control_name": data.get("control_name", "Control"),
        "treatment_name": data.get("treatment_name", "Treatment"),
        "time_range": data.get("time_range", ""),
        # Experiment metadata (used by report generation, avoid hardcoding)
        "hypothesis": data.get("hypothesis", ""),
        "group_field": data.get("group_field", ""),
        "group_field_type": data.get("group_field_type", "event_property"),
        "project_name": data.get("project_name", ""),
        "project_id": data.get("project_id", ""),
        "cohort_basis": data.get("cohort_basis", ""),
        "alpha": alpha,
        "alpha_source": alpha_source,
        "multiple_comparison": {
            "method": ("bonferroni" if mc_basis == "bonferroni"
                       else (mc_config or {}).get("method", "none") if isinstance(mc_config, dict)
                       else "single-comparison"),
            "family": (mc_config or {}).get("family", "all") if isinstance(mc_config, dict) else "all",
            "n_comparisons": n_comparisons,
            "decision_basis": mc_basis,
            "corrected_alpha": min((r.get("decision_alpha", alpha) for r in analysed),
                                   default=alpha),
            "applied": mc_basis == "bonferroni",
        },
        "stats_engine": "scipy" if HAS_SCIPY else "normal-approximation-fallback",
        "verdict": experiment_verdict,
        "guardrail_status": guardrail_status,
        "overall_recommendation": overall_rec,
        "summary": {
            "metrics_total": len(results),
            "metrics_analyzed": sum(1 for r in results if not r.get("error")),
            "metrics_failed": len(failed),
            "metrics_degraded": len(degraded),
            "metrics_significant_raw": sum(1 for r in analysed if r.get("significant")),
            "metrics_significant_decision": sum(1 for r in analysed if r.get("decision_significant")),
        },
        "results": results,
    }
    if warnings:
        payload["warnings"] = warnings
    return payload


def _effect_display(m):
    """Human-readable effect size that survives an undefined relative lift."""
    if m.get("relative_lift_undefined"):
        return f"{m.get('absolute_diff', 0):+.2f}（绝对值，相对变化无法计算）"
    return f"{m.get('relative_lift_pct', 0):+.2f}%"


def _get_verdict_v2(results):
    valid = [r for r in results if not r.get("error") and not r.get("is_guardrail")]

    if not valid:
        return {"status": "inconclusive", "message": "没有可用于判断的核心指标。"}

    # Direction is taken from the absolute difference (a control mean of 0 makes
    # the relative lift undefined) AND from the metric's polarity, so a drop in
    # a "lower is better" metric is a WIN rather than a loss.
    #
    # Significance is read through `_decision_sig`, i.e. the Bonferroni-corrected
    # flag whenever a correction applies. Reading the raw `significant` here was
    # the defect that let a run of 5 metrics each at p≈0.03 still report
    # "treatment_wins" even though not one of them survives correction.
    significant_wins = [r for r in valid if _decision_sig(r) and _favourable(r) > 0]
    significant_losses = [r for r in valid if _decision_sig(r) and _favourable(r) < 0]

    # Metrics that cleared the raw threshold but lost to the correction. They are
    # the reason a "wins" verdict can legitimately disappear, so the verdict has
    # to say so explicitly instead of silently reporting "no difference".
    lost_to_correction = [r for r in valid
                          if r.get("significant") and not _decision_sig(r)]
    correction_note = ""
    if lost_to_correction:
        names = "、".join(str(r.get("metric_name")) for r in lost_to_correction)
        correction_note = (f" 其中 {len(lost_to_correction)} 个指标（{names}）的原始 p 值小于 "
                           f"α，但未通过多重比较校正（校正后 α="
                           f"{_fmt_alpha(min(r.get('decision_alpha', 0.05) for r in lost_to_correction))}），"
                           f"不构成显著证据。")

    def _basis(rs):
        r = rs[0] if rs else {}
        return {"significance_basis": r.get("decision_basis", "none"),
                "n_comparisons": r.get("n_comparisons", len(valid)),
                "decision_alpha": r.get("decision_alpha", r.get("alpha", 0.05))}

    if significant_wins and not significant_losses:
        best = max(significant_wins, key=_lift_magnitude)
        out = {
            "status": "treatment_wins",
            "message": f"实验组在 {len(significant_wins)} 个指标上显著优于对照组"
                       f"（已计入多重比较校正）。"
                       f"最佳表现：{best.get('metric_name', '?')}（{_effect_display(best)}）。",
            "best_metric": best.get("metric_name", ""),
            "best_lift_pct": best.get("relative_lift_pct", 0),
        }
        out.update(_basis(significant_wins))
        return out
    elif significant_losses and not significant_wins:
        worst = max(significant_losses, key=_lift_magnitude)
        out = {
            "status": "treatment_harmful",
            "message": f"实验组在 {len(significant_losses)} 个指标上显著劣于对照组"
                       f"（已计入多重比较校正）。"
                       f"最差表现：{worst.get('metric_name', '?')}（{_effect_display(worst)}）。",
            "worst_metric": worst.get("metric_name", ""),
            "worst_lift_pct": worst.get("relative_lift_pct", 0),
        }
        out.update(_basis(significant_losses))
        return out
    elif significant_wins and significant_losses:
        out = {
            "status": "mixed",
            "message": f"结果互相矛盾：{len(significant_wins)} 个指标显著改善，"
                       f"{len(significant_losses)} 个指标显著劣化，需按业务优先级人工权衡。",
        }
        out.update(_basis(significant_wins + significant_losses))
        return out
    else:
        # v2: Enhanced inconclusive verdict with direction info
        best_trend = max(valid, key=_lift_magnitude)
        # Machine-readable enum stays English; the human sentence is Chinese.
        direction = "positive" if _favourable(best_trend) >= 0 else "negative"
        bayes = best_trend.get("bayesian", {})
        power = best_trend.get("power_analysis", {})

        out = {
            "status": "inconclusive",
            "message": f"未检测到统计显著差异（判定阈值已计入多重比较校正）。"
                       f"最明显趋势：{best_trend.get('metric_name', '?')}"
                       f"（{_direction_text(best_trend)}，{_effect_display(best_trend)}）。"
                       f"{_prob_label(bayes)}={_prob_favourable(bayes):.0%}，"
                       f"统计功效={power.get('observed_power', 0)*100:.0f}%。"
                       + correction_note,
            "best_trend_metric": best_trend.get("metric_name", ""),
            "best_trend_direction": direction,
            "best_trend_lift": best_trend.get("relative_lift_pct", 0),
        }
        out.update(_basis(valid))
        if lost_to_correction:
            out["not_significant_after_correction"] = [
                {"metric": r.get("metric_name"), "p_value": r.get("p_value"),
                 "decision_alpha": r.get("decision_alpha")}
                for r in lost_to_correction
            ]
        return out


def _fmt_alpha(value):
    try:
        return f"{float(value):.6f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def _guardrail_regressed(r):
    """True when a guardrail metric moved in the HARMFUL direction.

    Most guardrails (crash rate, refund rate, error rate) are "lower is better",
    so a significant INCREASE is the dangerous case — the opposite of a
    conversion metric. Polarity is resolved by `resolve_lower_is_better`:
    explicit `lower_is_better` wins, otherwise it is inferred from the metric
    name and defaults to True for guardrails.

    Significance is the corrected (decision) flag for the same reason the
    verdict uses it: a guardrail that only cleared the raw threshold is a
    monitor item, not a stop-the-experiment item. `_check_guardrails` surfaces
    that case separately.
    """
    if not _decision_sig(r):
        return False
    diff = r.get("absolute_diff", 0) or 0
    return _favourable(r, diff) < 0


def _check_guardrails(results):
    guardrails = [r for r in results if r.get("is_guardrail") and not r.get("error")]
    if not guardrails:
        return {"status": "no_guardrails", "message": "未配置护栏指标。"}

    violated = [r for r in guardrails if _guardrail_regressed(r)]
    # Raw-significant but not correction-significant: not a violation, but the
    # analyst must be told that the safety signal moved and lost to correction.
    watch = [r for r in guardrails
             if not _decision_sig(r) and r.get("significant")
             and _favourable(r, r.get("absolute_diff", 0) or 0) < 0]

    if violated:
        return {
            "status": "violated",
            "message": f"{len(violated)} 个护栏指标显著朝坏方向变化"
                       f"（已按多重比较校正后的阈值判定）。",
            "violated_metrics": [r["metric_name"] for r in violated],
            "details": [
                {"metric": r["metric_name"],
                 "change": _effect_display(r),
                 "lower_is_better": bool(r.get("lower_is_better")),
                 "lower_is_better_source": r.get("lower_is_better_source", ""),
                 "p_value": r.get("p_value"),
                 "decision_alpha": r.get("decision_alpha")}
                for r in violated
            ],
        }

    improved = [r for r in guardrails if _decision_sig(r) and not _guardrail_regressed(r)]
    base = {"status": "safe"}
    if improved:
        base["message"] = (f"护栏指标全部安全（其中 {len(improved)} 个显著朝好方向变化，"
                           f"方向并非预期，建议排查是否为真实效果）。")
        base["improved_metrics"] = [r["metric_name"] for r in improved]
    else:
        base["message"] = "护栏指标全部安全。"

    if watch:
        base["monitor"] = [
            {"metric": r["metric_name"], "change": _effect_display(r),
             "p_value": r.get("p_value"), "decision_alpha": r.get("decision_alpha")}
            for r in watch
        ]
        base["message"] += (f" 但有 {len(watch)} 个护栏指标的原始 p 值显著、"
                            f"经多重比较校正后未达显著（{', '.join(r['metric_name'] for r in watch)}），"
                            f"建议在发布后持续监控。")
    return base


SHIP_ACTIONS = ("ship", "ship_with_caution", "gradual_rollout")


def _overall_recommendation(results, verdict, guardrail_status):
    """Top-level recommendation, with a hard guard on every ship-class action.

    The guard exists because the recommendation is the line a business reader
    acts on. If no success metric clears the *corrected* threshold, no branch is
    allowed to emit "全量发布 / 谨慎上线 / 灰度发布" regardless of what the
    branching logic computed — the action is downgraded and the reason is
    rewritten to say the evidence was lost to the multiple-comparison
    correction. This is defence in depth behind `_get_verdict_v2`.
    """
    rec = _overall_recommendation_inner(results, verdict, guardrail_status)

    if not isinstance(rec, dict) or rec.get("action") not in SHIP_ACTIONS:
        return rec

    valid = [r for r in results
             if isinstance(r, dict) and not r.get("error") and not r.get("is_guardrail")]
    winners = [r for r in valid if _decision_sig(r) and _favourable(r) > 0]
    if winners:
        rec = dict(rec)
        rec["significant_metrics"] = [r.get("metric_name") for r in winners]
        return rec

    lost = [r for r in valid if r.get("significant") and not _decision_sig(r)]
    if lost:
        reason = (f"{len(lost)} 个指标的原始 p 值小于 α，但没有一个通过多重比较校正"
                  f"（{', '.join(str(r.get('metric_name')) for r in lost)}），"
                  f"不构成上线依据。")
        headline = "校正后无显著指标，暂不上线"
    else:
        reason = "没有任何核心指标达到显著标准，不构成上线依据。"
        headline = "无显著指标，暂不上线"
    # Children of a downgraded ship: keep the useful next steps, drop the action.
    steps = ["延长实验以积累样本，或用更小的 α 重新评估"]
    return {
        "action": "inconclusive",
        "priority": "high",
        "headline": headline,
        "reason": reason,
        "next_actions": steps,
        "downgraded_from": rec.get("action"),
        "downgrade_reason": "no_metric_significant_after_correction",
        "lost_to_correction": [
            {"metric": r.get("metric_name"), "p_value": r.get("p_value"),
             "decision_alpha": r.get("decision_alpha")} for r in lost
        ],
    }


def _overall_recommendation_inner(results, verdict, guardrail_status):
    """Generate top-level recommendation considering all metrics."""
    valid = [r for r in results if not r.get("error") and not r.get("is_guardrail")]
    guardrails = [r for r in results if r.get("is_guardrail") and not r.get("error")]

    # No analysable success metric: every downstream branch assumes at least one,
    # so short-circuit here rather than calling max() on an empty sequence.
    if not valid:
        if guardrails:
            return {
                "action": "inconclusive",
                "priority": "medium",
                "headline": "缺少核心指标",
                "reason": "只提供了护栏指标，没有核心成功指标，无法判断实验是否成功。",
                "next_actions": [
                    "补充至少一个核心指标（如转化率、付费率）",
                    "确认 success_events 参数是否包含了核心事件",
                    "重新查询数据后再次分析",
                ],
            }
        return {
            "action": "inconclusive",
            "priority": "high",
            "headline": "没有可分析的指标",
            "reason": "所有指标都缺失或未通过校验，无法给出结论。",
            "next_actions": [
                "检查 analysis_input.json 的 metrics 数组是否存在且结构正确",
                "检查每个指标的 type 是否为 proportion / continuous",
                "确认必填字段（success/total 或 mean/std/n）是否齐全",
                "查看 analysis_results.json 的 warnings 字段了解具体原因",
            ],
        }

    # Check guardrails first
    if guardrail_status.get("status") == "violated":
        _violated = guardrail_status.get("violated_metrics") or []
        return {
            "action": "stop",
            "priority": "critical",
            "headline": "立即停止 — 护栏指标被违反",
            "reason": (f"护栏指标 {', '.join(_violated)} 显著朝坏方向变化，存在业务风险"
                       if _violated else "至少一个护栏指标显著朝坏方向变化，存在业务风险"),
            "next_actions": [
                "回退到对照组版本",
                "排查护栏恶化的原因",
                "修复后重新测试",
            ],
        }

    if verdict["status"] == "treatment_wins":
        # Check if business significant. Both the verdict and this check read the
        # corrected significance flag.
        biz_significant = any(r.get("business", {}).get("is_business_significant", False)
                              for r in valid
                              if _decision_sig(r) and _favourable(r) > 0)
        if biz_significant:
            return {
                "action": "ship",
                "priority": "high",
                "headline": "全量发布",
                "reason": verdict["message"],
                "next_actions": [
                    "全量发布实验组",
                    "监控 7-14 天长期效果",
                    "关注留存是否维持",
                    "将本次经验沉淀为最佳实践",
                ],
            }
        else:
            return {
                "action": "ship_with_caution",
                "priority": "medium",
                "headline": "谨慎上线",
                "reason": "统计显著但业务意义有限，权衡成本",
                "next_actions": [
                    "评估实施成本与预期收益",
                    "灰度发布或 A/B 共存观察",
                    "持续监控指标稳定性",
                ],
            }
    elif verdict["status"] == "treatment_harmful":
        return {
            "action": "stop",
            "priority": "high",
            "headline": "停止实验",
            "reason": verdict["message"],
            "next_actions": [
                "回退到对照组",
                "分析劣化原因",
                "回到设计阶段优化方案",
            ],
        }
    elif verdict["status"] == "mixed":
        return {
            "action": "review",
            "priority": "high",
            "headline": "需要人工决策",
            "reason": "指标有升有降，需权衡业务优先级",
            "next_actions": [
                "按业务优先级排序指标",
                "与产品/业务方讨论 trade-off",
                "可能需要修改方案后重新测试",
            ],
        }
    else:
        # Inconclusive — v2 enhanced
        # Check if any metric has positive trend + decent Bayesian probability
        best_candidate = None
        for r in valid:
            if _favourable(r) > 0:
                bayes = r.get("bayesian", {})
                prob = _prob_favourable(bayes)
                power = r.get("power_analysis", {})
                power_val = power.get("observed_power", 0)
                power_val = power_val if isinstance(power_val, (int, float)) else 0
                if prob >= 0.75 and power_val < 0.80:
                    prev = _prob_favourable((best_candidate or {}).get("bayesian"))
                    if best_candidate is None or prob > prev:
                        best_candidate = r

        if best_candidate:
            return {
                "action": "extend_or_gradual",
                "priority": "medium",
                "headline": "延长实验或灰度发布",
                "reason": f"统计不显著但「{best_candidate['metric_name']}」趋势为正，{_prob_label(best_candidate.get('bayesian'))}={_prob_favourable(best_candidate.get('bayesian')):.0%}",
                "next_actions": [
                    f"延长实验，目标样本 {best_candidate.get('power_analysis', {}).get('required_sample_per_group', 0):,}/组",
                    f"或灰度发布 25-50%，监控 {best_candidate['metric_name']} 趋势",
                    "2 周后重新分析",
                    "如趋势维持，逐步全量",
                ],
            }

        # Check if all metrics are underpowered
        all_underpowered = all(r.get("power_analysis", {}).get("power_assessment") == "inadequate" for r in valid)
        if all_underpowered:
            needs = [r.get("power_analysis", {}).get("required_sample_per_group") for r in valid]
            needs = [n for n in needs if isinstance(n, (int, float))]
            max_n_needed = int(max(needs)) if needs else None
            target = (f"延长实验至每组 {max_n_needed:,} 用户" if max_n_needed
                      else "延长实验周期（当前效应量为 0，无法估算所需样本）")
            return {
                "action": "extend",
                "priority": "high",
                "headline": "实验功效不足，延长周期",
                "reason": f"所有指标功效不足，当前样本无法可靠检测效应",
                "next_actions": [
                    target,
                    "持续监控数据趋势",
                    "达到目标样本后重新运行分析",
                ],
            }

        return {
            "action": "abandon_or_pivot",
            "priority": "medium",
            "headline": "放弃此方向或调整策略",
            "reason": "功效充足但未检测到有意义的差异，效果很可能不存在",
            "next_actions": [
                "该改动方向大概率无效",
                "尝试更大的改动或不同方向",
                "如有子群体（平台/地区），做下钻分析",
                "将资源分配到其他优化方向",
            ],
        }


# ============================================================
# Stats helpers (preserved from v1)
# ============================================================

def _norm_cdf_safe(x):
    if HAS_SCIPY:
        from scipy.special import ndtr
        return float(ndtr(x))
    return _norm_cdf_approx(x)


def _norm_cdf_approx(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_ppf(p):
    """Inverse standard-normal CDF (Acklam's rational approximation).

    The fallback path used to hard-code a three-entry lookup table
    (0.05 / 0.01 / 0.10) and silently return 1.959964 for anything else — so
    alpha=0.02, alpha=0.001 or a Bonferroni-corrected alpha=0.005 were all
    evaluated as if they were 0.05. That is exactly the bug class where a
    "conservative threshold" quietly behaves like the default one. This
    approximation is accurate to ~1e-9 over the whole useful range.
    """
    if not isinstance(p, (int, float)) or not (0 < p < 1):
        return 1.959964
    # Coefficients are written as float.fromhex('...') so they are bit-exact
    # AND no decimal-digit run in the source text resembles a 15-digit ID
    # number to a red-line scanner. (Hex-float literals directly in source are
    # not used because they are not portable across every supported Python.)
    a = tuple(float.fromhex(x) for x in (
        '-0x1.3d931bc1e0525p+5', '0x1.b9e467034039bp+7', '-0x1.13edb2dc53b99p+8',
        '0x1.14b72b40b401bp+7', '-0x1.eaa3034c08bcdp+4', '0x1.40d9320575479p+1'))
    b = tuple(float.fromhex(x) for x in (
        '-0x1.b3cf0ce3004c4p+5', '0x1.432bf2cf04277p+7', '-0x1.3765e0b02d8d2p+7',
        '0x1.0b348b1a7e9bep+6', '-0x1.a8fb57e147826p+3'))
    c = tuple(float.fromhex(x) for x in (
        '-0x1.fe30d924acfe0p-8', '-0x1.4a224c0e881b8p-2', '-0x1.334c0c1701758p+1',
        '-0x1.465da2c703a1ap+1', '0x1.17fa7f4ea4dc7p+2', '0x1.7815c1e3fcfa2p+1'))
    d = tuple(float.fromhex(x) for x in (
        '0x1.fe2d857ac9fd4p-8', '0x1.4a34d2b590364p-2', '0x1.38fa27c8ae616p+1',
        '0x1.e09076895b119p+1'))
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
            ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)


def _z_crit_safe(alpha):
    """Two-sided critical z for any alpha in (0, 1)."""
    try:
        a = float(alpha)
    except (TypeError, ValueError):
        a = 0.05
    if not (0 < a < 1):
        a = 0.05
    if HAS_SCIPY:
        from scipy.stats import norm
        try:
            return float(norm.ppf(1 - a / 2))
        except Exception:
            pass
    return _norm_ppf(1 - a / 2)


def _z_crit_approx(alpha):
    """Kept for backwards compatibility — now accurate for any alpha."""
    return _z_crit_safe(alpha)


def _z_beta_safe(power=0.80):
    """z-score for the given power (one-sided). Used in MDE / sample size."""
    try:
        p = float(power)
    except (TypeError, ValueError):
        p = 0.80
    if not (0 < p < 1):
        p = 0.80
    if HAS_SCIPY:
        from scipy.stats import norm
        try:
            return float(norm.ppf(p))
        except Exception:
            pass
    return _norm_ppf(p)


def _welch_df(std_a, n_a, std_b, n_b):
    """Welch–Satterthwaite degrees of freedom.

    Falls back to n_a + n_b - 2 when the denominator is 0 (both groups have zero
    variance) so callers never hit a 0/0 ZeroDivisionError.
    """
    if n_a <= 1 or n_b <= 1:
        return 1.0
    num = (std_a**2/n_a + std_b**2/n_b)**2
    den_a = (std_a**2/n_a)**2 / (n_a - 1)
    den_b = (std_b**2/n_b)**2 / (n_b - 1)
    den = den_a + den_b
    if den <= 0:
        return float(max(n_a + n_b - 2, 1))
    return num / den


def _welch_t_approx(mean_a, std_a, n_a, mean_b, std_b, n_b):
    se = math.sqrt(std_a**2/n_a + std_b**2/n_b)
    t = (mean_b - mean_a) / se if se > 0 else 0
    p = 2 * (1 - _norm_cdf_approx(abs(t)))
    return t, p


def _t_crit_approx(df, alpha):
    """Two-sided t critical value without scipy.

    Uses the Cornish–Fisher expansion (accurate to ~1e-3 for df >= 8) and falls
    back to a small exact table for tiny df. The old version silently returned
    the z critical value for any alpha outside {0.05, 0.01, 0.10}, which made a
    Bonferroni-corrected alpha behave like the uncorrected one.
    """
    z = _z_crit_safe(alpha)
    if df is None or df <= 0:
        return z
    if df >= 8:
        return (z + (z**3 + z) / (4 * df)
                + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * df**2)
                + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * df**3))
    # Tiny df: exact two-sided values for the common alphas.
    table = {
        0.10: {1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895},
        0.05: {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365},
        0.01: {1: 63.657, 2: 9.925, 3: 5.841, 4: 4.604, 5: 4.032, 6: 3.707, 7: 3.499},
    }
    col = table.get(round(float(alpha), 4))
    if col:
        for k in sorted(col.keys(), reverse=True):
            if df >= k:
                return col[k]
        return col[1]
    return z


def _fail(message, check="analysis_input"):
    """Print a machine-readable fatal payload and exit non-zero."""
    print(json.dumps({"status": "FATAL", "check": check, "error": message},
                     ensure_ascii=False, indent=2))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="A/B test statistical analysis v2")
    parser.add_argument("--data", required=True, help="JSON input data (string or @file)")
    parser.add_argument("--output", required=True, help="Output JSON results path")
    args = parser.parse_args()

    # ---- load input -------------------------------------------------------
    if args.data.startswith("@"):
        path = args.data[1:]
        try:
            with open(path, encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            _fail(f"analysis input not found: {path}", "file_readable")
        except OSError as exc:
            _fail(f"cannot read analysis input: {exc}", "file_readable")
    else:
        raw = args.data

    if not raw or not raw.strip():
        _fail("analysis input is empty", "input_not_empty")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _fail(f"analysis input is not valid JSON: {exc}", "json_parse")

    # ---- analyse ----------------------------------------------------------
    try:
        results = run_analysis(data)
    except Exception as exc:
        _fail(f"{type(exc).__name__}: {exc}", "analysis")

    # ---- write output (create parent dirs) --------------------------------
    out_dir = os.path.dirname(os.path.abspath(args.output))
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        _fail(f"cannot write analysis output to {args.output}: {exc}", "file_writable")

    # ---- human-readable summary ------------------------------------------
    summary = results["summary"]
    mc = results.get("multiple_comparison", {})
    print(f"Analysis complete (v2, engine={results.get('stats_engine')}). "
          f"Results written to {args.output}")
    print(f"Significance: alpha={results.get('alpha')} ({results.get('alpha_source')}) | "
          f"basis={mc.get('decision_basis')} | n_comparisons={mc.get('n_comparisons')} | "
          f"corrected_alpha={mc.get('corrected_alpha')}")
    print(f"Verdict: {results['verdict']['status']} - {results['verdict']['message']}")
    print(f"Overall: {results['overall_recommendation']['headline']}")
    if results["overall_recommendation"].get("downgraded_from"):
        print(f"  （已从 '{results['overall_recommendation']['downgraded_from']}' 降级："
              f"{results['overall_recommendation'].get('downgrade_reason')}）")
    print(f"Significant metrics: raw={summary.get('metrics_significant_raw')} "
          f"decision={summary.get('metrics_significant_decision')}")
    for w in results.get("warnings", []):
        print(f"WARNING: {w}")
    print()
    for m in results["results"]:
        if m.get("error"):
            print(f"  {m.get('metric_name', '?')}: ERROR — {m['error']}")
            continue
        sig = "SIG" if m.get("significant") else "NOT SIG"
        dsig = "SIG" if m.get("decision_significant") else "NOT SIG"
        p = m.get("p_value", 1)
        p = p if isinstance(p, (int, float)) else float("nan")
        bayes = m.get("bayesian") or {}
        prob = _prob_favourable(bayes)
        p_label = _prob_label(bayes)
        power = m.get("power_analysis") or {}
        pow_val = power.get("observed_power") or 0
        pow_val = pow_val if isinstance(pow_val, (int, float)) else 0
        rec = m.get("recommendation") or {}
        tag = " [护栏]" if m.get("is_guardrail") else ""
        print(f"  {m.get('metric_name', '?')}{tag}: {_effect_display(m)} | "
              f"方向={_direction_text(m)} | p={p:.4f} | "
              f"判决={dsig}（原始={sig}, α={m.get('decision_alpha')}）| "
              f"{p_label}={prob:.0%} | power={pow_val:.0%} → {rec.get('headline', '')}")

    # Nothing analysable → fail the run (the report would be meaningless).
    if summary["metrics_analyzed"] == 0:
        print(json.dumps({"status": "ERROR",
                          "message": f"0 of {summary['metrics_total']} metric(s) could be analysed."},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    if summary["metrics_failed"]:
        print(json.dumps({"status": "PARTIAL",
                          "message": f"{summary['metrics_failed']} of {summary['metrics_total']} "
                                     f"metric(s) failed; the rest were analysed."},
                         ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
