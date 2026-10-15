#!/usr/bin/env python3
"""Generate comprehensive HTML analysis report v2.

v2 additions:
- Bayesian posterior probability section per metric
- Post-hoc power analysis section per metric
- Business significance assessment per metric
- Actionable recommendation card per metric (ship/extend/abandon/gradual)
- Overall recommendation with closed-loop next actions
- "Not significant" is no longer a dead end — always gives actionable guidance

Sections:
1. Executive Summary — verdict + overall recommendation
2. Experiment Design
3. Group Analysis
4. Metric-by-Metric Analysis (with Bayesian + Power + Business + Recommendation)
5. Guardrail Analysis
6. Statistical Methodology
7. Limitations
8. Action Plan & Closed-Loop — what to do next, and what happens after
"""
import argparse
import html
import json
import os
import sys
from datetime import datetime


def _e(value):
    """Escape a value for safe interpolation into HTML text or attributes.

    Every string that originates from the experiment data (experiment name,
    metric name, hypothesis, project name, recommendation text ...) must go
    through this — a metric literally named `A < B` would otherwise break the
    layout, and a crafted name could inject markup into a customer-facing report.
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _num(value, spec=".2f", default="N/A"):
    """Format a number, tolerating None / non-numeric input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return format(value, spec)


def _p_val(val):
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return "N/A"
    return f"{val:.4f}" if val >= 0.0001 else f"{val:.2e}"


def _fail(message):
    """Print a machine-readable fatal payload and exit non-zero."""
    print(json.dumps({"status": "FATAL", "check": "report_input", "error": message},
                     ensure_ascii=False, indent=2))
    sys.exit(1)


def _favourable(metric):
    """+1 when the movement is desirable, -1 when harmful, 0 when no movement.

    Mirrors `ab_test_stats._favourable` (deliberately duplicated so report
    generation stays a standalone script that never imports the stats engine).
    `lower_is_better` flips the reading: for crash rate / response time a DROP
    is the good outcome, so a negative lift must not be rendered as a loss.
    """
    diff = metric.get("absolute_diff", 0) or 0
    if isinstance(diff, bool) or not isinstance(diff, (int, float)) or diff != diff:
        return 0
    if diff == 0:
        return 0
    gain = -1 if metric.get("lower_is_better") else 1
    return gain if diff > 0 else -gain


def _decision_sig(metric):
    """The significance flag that every conclusion must read.

    After multiple-comparison correction the *decision* flag is
    `decision_significant` (p against the corrected alpha). The raw
    `significant` flag (p against the uncorrected alpha) is only kept for
    disclosure — "significant before correction". Each conclusion in the
    report must honour the corrected flag, otherwise a run where every
    metric dies under correction could still be rendered as a win.
    """
    if not isinstance(metric, dict):
        return False
    if "decision_significant" in metric:
        return bool(metric.get("decision_significant"))
    return bool(metric.get("significant"))


def _raw_sig(metric):
    """Significance against the uncorrected alpha (disclosure only)."""
    if not isinstance(metric, dict):
        return False
    return bool(metric.get("significant"))


def _fmt_alpha(value, default="0.05"):
    """Render an alpha without trailing noise (0.05, 0.0125 ...)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value == 0:
        return "0"
    return f"{value:.4g}"


def _mc_block(results):
    """The engine's multiple-comparison block, defensively normalized."""
    mc = results.get("multiple_comparison")
    return mc if isinstance(mc, dict) else {}


def _polarity_note(metric):
    """Short HTML suffix telling the reader which direction is good."""
    if not metric.get("lower_is_better"):
        return ""
    return '<span class="tag-lower-better">越低越好</span>'


def _lift_magnitude(metric):
    """Rank metrics by effect size without mixing units."""
    if not metric.get("relative_lift_undefined"):
        v = metric.get("relative_lift_pct")
        return abs(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0
    v = metric.get("absolute_diff_pct", metric.get("absolute_diff", 0))
    return abs(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def _prob_favourable(bayes):
    """P(treatment is the better arm), polarity already applied by the engine.

    The engine emits `prob_favourable`; older result files only carry the
    literal P(T>C), which is used as a fallback so the report never hard-fails.
    """
    b = bayes if isinstance(bayes, dict) else {}
    for key in ("prob_favourable", "prob_treatment_better"):
        v = b.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return v
    return 0.5


def _prob_label(bayes):
    b = bayes if isinstance(bayes, dict) else {}
    return b.get("prob_favourable_label") or "P(实验组高于对照组)"


def _verdict_color(status):
    return {
        "treatment_wins": "#16a34a", "treatment_harmful": "#dc2626",
        "mixed": "#f59e0b", "inconclusive": "#6b7280",
    }.get(status, "#6b7280")


def _verdict_label(status):
    return {
        "treatment_wins": "实验组胜出", "treatment_harmful": "实验组有害",
        "mixed": "结果混合", "inconclusive": "无法定论",
    }.get(status, "分析完成")


def _action_color(action):
    return {
        "ship": "#16a34a", "ship_with_caution": "#84cc16",
        "extend": "#3b82f6", "extend_or_gradual": "#3b82f6",
        "gradual_rollout": "#8b5cf6", "stop": "#dc2626",
        "abandon": "#6b7280", "abandon_or_pivot": "#6b7280",
        "review": "#f59e0b", "inconclusive": "#6b7280",
        "safe": "#16a34a", "proceed_with_caution": "#84cc16",
    }.get(action, "#6b7280")


def _risk_color(level):
    return {
        "very_low": "#16a34a", "low": "#84cc16",
        "moderate": "#f59e0b", "high": "#f97316",
        "very_high": "#dc2626",
    }.get(level, "#6b7280")


def _pair(v, default=0.0):
    """Return a 2-tuple of numbers from a list-like value, tolerating junk."""
    def _one(x):
        return x if isinstance(x, (int, float)) and not isinstance(x, bool) else default
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return _one(v[0]), _one(v[1])
    return default, default


def _metric_fields(m):
    """Normalize metric-type-specific fields into a uniform accessor.

    Returns a dict with:
      c_value / t_value   — the headline value (rate 0-1 for proportion, mean for continuous)
      value_suffix        — "%" for proportion, "" for continuous
      c_n / t_n           — sample sizes
      test_stat / test_label — statistic name and value ("z"/"t")
      is_proportion       — bool
    """
    is_proportion = m.get("metric_type") != "continuous"
    if is_proportion:
        return {
            "is_proportion": True,
            "c_value": m.get("control_rate", 0) or 0,
            "t_value": m.get("treatment_rate", 0) or 0,
            "value_suffix": "%",
            "c_n": m.get("control_sample", 0) or 0,
            "t_n": m.get("treatment_sample", 0) or 0,
            "test_stat": m.get("z_statistic", 0) or 0,
            "test_label": "z",
        }
    else:
        return {
            "is_proportion": False,
            "c_value": m.get("control_mean", 0) or 0,
            "t_value": m.get("treatment_mean", 0) or 0,
            "value_suffix": "",
            "c_n": m.get("control_sample", 0) or 0,
            "t_n": m.get("treatment_sample", 0) or 0,
            "test_stat": m.get("t_statistic", m.get("z_statistic", 0)) or 0,
            "test_label": "t",
        }


def _narrative_for_metric(m, control_name, treatment_name):
    name = _e(m.get("metric_name", ""))
    c_name = _e(control_name)
    t_name = _e(treatment_name)
    f = _metric_fields(m)
    c_value = f["c_value"]
    t_value = f["t_value"]
    suffix = f["value_suffix"]
    lift = m.get("relative_lift_pct", 0) or 0
    lift_undefined = bool(m.get("relative_lift_undefined"))
    abs_diff = m.get("absolute_diff_pct")
    if abs_diff is None:
        abs_diff = m.get("absolute_diff")
    p = m.get("p_value")
    sig = _decision_sig(m)
    sig_raw = _raw_sig(m)
    alpha_disp = _fmt_alpha(m.get("decision_alpha", m.get("alpha")))
    dec_basis = str(m.get("decision_basis") or "raw")
    c_n = f["c_n"]
    t_n = f["t_n"]
    test_stat = f["test_stat"]
    test_label = f["test_label"]
    bayes = m.get("bayesian") or {}
    power = m.get("power_analysis") or {}
    biz = m.get("business") or {}
    rec = m.get("recommendation") or {}

    lift_disp = "无法计算（对照组均值为 0）" if lift_undefined else f"{lift:+.2f}%"

    narrative = ""

    # ---- Data performance ----
    if f["is_proportion"]:
        c_success = round(c_value * c_n)
        t_success = round(t_value * t_n)
        narrative += (f"<p><strong>数据表现：</strong>{c_name}的{name}为 "
                      f"<strong>{_num(c_value*100, '.2f')}%</strong>（{c_success:,}/{c_n:,}），")
        narrative += (f"{t_name}为 <strong>{_num(t_value*100, '.2f')}%</strong>"
                      f"（{t_success:,}/{t_n:,}）。")
    else:
        narrative += (f"<p><strong>数据表现：</strong>{c_name}的{name}为 "
                      f"<strong>{_num(c_value)}</strong>（n={c_n:,}），")
        narrative += f"{t_name}为 <strong>{_num(t_value)}</strong>（n={t_n:,}）。"
    narrative += (f"绝对差异 <span class='num-highlight'>{_num(abs_diff, '+.2f')}{suffix}</span>，"
                  f"相对变化 <span class='num-highlight'>{_e(lift_disp)}</span>。</p>")

    # ---- Statistical test ----
    narrative += (f"<p><strong>统计检验：</strong>{test_label} = {_num(test_stat, '.4f')}，"
                  f"p = {_p_val(p)}。")
    if dec_basis == "bonferroni":
        _n_cmp = m.get("n_comparisons")
        _cmp_disp = (f"{int(_n_cmp)} 项比较" if isinstance(_n_cmp, (int, float))
                     and not isinstance(_n_cmp, bool) else "多重比较")
        if sig:
            narrative += (f"p &lt; 校正后 α={alpha_disp}（{_cmp_disp}，Bonferroni 校正），"
                          "差异具有统计显著性，结论可靠。")
        elif sig_raw:
            narrative += (f"p &lt; α={_fmt_alpha(m.get('alpha'))}，但未通过校正后的 "
                          f"α={alpha_disp}（{_cmp_disp}）。校正后差异不再显著，"
                          "存在假阳性风险，不足以支撑上线决策。")
        else:
            narrative += f"p ≥ 校正后 α={alpha_disp}（{_cmp_disp}），差异不具有统计显著性。"
    else:
        if sig:
            narrative += f"p &lt; α={alpha_disp}，差异具有统计显著性。"
        else:
            narrative += f"p ≥ α={alpha_disp}，差异不具有统计显著性。"
    if f["is_proportion"]:
        lo, hi = _pair(m.get("lift_ci"))
        narrative += f"95% CI（相对提升）：[{_num(lo, '+.2f')}%, {_num(hi, '+.2f')}%]。</p>"
    else:
        lo, hi = _pair(m.get("diff_ci"))
        narrative += f"95% CI（绝对差）：[{_num(lo, '+.2f')}, {_num(hi, '+.2f')}]。</p>"

    if m.get("degenerate_variance"):
        narrative += ("<p><strong>注意：</strong>两组的取值全部相同（不是 0% 就是 100%），"
                      "方差为 0，检验统计量与 MDE 无法估计。请核对数据口径。</p>")

    # ---- Bayesian analysis ----
    if bayes:
        prob = _prob_favourable(bayes)
        risk = _e(bayes.get("risk_label", ""))
        prob_note = bayes.get("probability_note") or ""
        note_html = f"（{_e(prob_note)}）" if prob_note else ""
        narrative += (f"<p><strong>贝叶斯分析：</strong>{_e(_prob_label(bayes))} = "
                      f"<strong>{_num(prob*100, '.1f')}%</strong>，风险等级：{risk}。{note_html}")
        if prob >= 0.95:
            narrative += "实验组优于对照组的概率极高，可以自信地推进。"
        elif prob >= 0.80:
            narrative += "实验组更优的可能性较高，但仍存在不确定性。"
        elif prob >= 0.50:
            narrative += "实验组略优，但优势不明显，需要更多数据。"
        else:
            narrative += "对照组可能更优，不建议推进实验组。"
        narrative += (f"预期收益 {_num(bayes.get('expected_gain_pct'), '+.2f')}%，"
                      f"预期损失 {_num(bayes.get('expected_loss_pct'), '+.2f')}%。</p>")

    # ---- Power analysis ----
    if power:
        narrative += (f"<p><strong>功效分析：</strong>统计功效 = "
                      f"<strong>{_num(power.get('observed_power', 0)*100, '.1f')}%</strong>，"
                      f"{_e(power.get('power_message', ''))}</p>")
        pow_val = power.get("observed_power") or 0
        if pow_val < 0.80 and not sig and not lift_undefined:
            req_n = power.get("required_sample_per_group")
            cur_n = power.get("current_sample_per_group", 0) or 0
            ratio = power.get("sample_ratio_needed")
            if isinstance(req_n, (int, float)):
                narrative += (f"<p><strong>所需样本：</strong>要检测到当前效应量，每组需约 "
                              f"<strong>{int(req_n):,}</strong> 用户，当前每组 {int(cur_n):,}，"
                              f"需延长至 <strong>{_num(ratio, '.2f')} 倍</strong>当前样本量。</p>")
            else:
                narrative += (f"<p><strong>所需样本：</strong>当前效应量下无法估算所需样本"
                              f"（观察到的效应为 0）。</p>")

    # ---- Business significance ----
    if biz:
        narrative += (f"<p><strong>业务评估：</strong>{_e(biz.get('label', ''))}。"
                      f"{_e(biz.get('recommendation', ''))}</p>")

    # ---- Recommendation ----
    if rec:
        action = rec.get("action", "")
        headline = rec.get("headline", "")
        reason = rec.get("reason", "")
        color = _action_color(action)
        narrative += f"<div class='rec-card' style='border-color:{color}'>"
        narrative += (f"<div class='rec-header' style='background:{color}10;color:{color}'>"
                      f"{_e(headline)}</div>")
        narrative += f"<p class='rec-reason'>{_e(reason)}</p>"
        steps = rec.get("steps") or []
        if steps:
            narrative += "<ol class='rec-steps'>"
            for s in steps:
                narrative += f"<li>{_e(s)}</li>"
            narrative += "</ol>"
        narrative += "</div>"

    # A metric can analyse cleanly yet lose part of its v2 block. Rendering a
    # blank card without saying why is exactly the kind of silent failure a
    # customer-facing report must never ship.
    if m.get("v2_error"):
        narrative += ("<div class='error-box'><strong>部分分析缺失：</strong>"
                      f"该指标的贝叶斯 / 功效 / 业务 / 建议分析未能完成 —— "
                      f"{_e(m['v2_error'])}</div>")

    return narrative


def generate_html(results):
    verdict = results.get("verdict") or {}
    guardrail = results.get("guardrail_status") or {}
    overall_rec = results.get("overall_recommendation") or {}
    all_metrics = [m for m in (results.get("results") or []) if isinstance(m, dict)]
    exp_name = results.get("experiment_name", "A/B Test")
    control_name = results.get("control_name", "Control")
    treatment_name = results.get("treatment_name", "Treatment")
    time_range = results.get("time_range", "")
    gen_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    warnings = [w for w in (results.get("warnings") or []) if w]
    stats_engine = results.get("stats_engine", "")

    # Experiment metadata (no hardcoding — passed through from analysis input)
    hypothesis = results.get("hypothesis", "")
    group_field = results.get("group_field", "")
    group_field_type = results.get("group_field_type", "event_property")
    project_name = results.get("project_name", "")
    project_id = results.get("project_id", "")
    if project_name and project_id:
        data_source = f"{project_name}（ID={project_id}）"
    else:
        data_source = project_name or (f"ID={project_id}" if project_id else "ae-cli")

    v_color = _verdict_color(verdict.get("status"))
    v_label = _verdict_label(verdict.get("status"))
    o_color = _action_color(overall_rec.get("action", ""))

    # Metrics that failed validation are listed separately instead of being
    # rendered as a bogus "0.00%" card.
    error_metrics = [m for m in all_metrics if m.get("error")]
    metrics = [m for m in all_metrics if not m.get("error")]
    success_metrics = [m for m in metrics if not m.get("is_guardrail")]
    guardrail_metrics = [m for m in metrics if m.get("is_guardrail")]

    # Metrics whose polarity the analyst did NOT declare are guessed from the
    # metric name — say so, so nobody silently trusts a wrong assumption.
    _assumed = [m for m in metrics
                if m.get("lower_is_better_source") in ("inferred-name", "default-guardrail")]
    if _assumed:
        _rows = "".join(
            f"<li>{_e(m.get('metric_name', ''))} → "
            f"{'越低越好' if m.get('lower_is_better') else '越高越好'}"
            f"（{'按名称推断' if m.get('lower_is_better_source') == 'inferred-name' else '护栏默认'}）</li>"
            for m in _assumed)
        polarity_assumptions = (
            "<p style='margin-top:10px'><strong>方向假设（未显式声明，请核对）：</strong></p>"
            f"<ul>{_rows}</ul>")
    else:
        polarity_assumptions = ""

    # Guard against empty metrics list (defensive)
    # The exposure cohort is the denominator for every test. Under the cohort
    # contract all metrics share it, but older payloads may disagree — take the
    # largest so the headline never understates participation.
    total_control = max([m.get("control_sample", 0) or 0 for m in metrics] or [0])
    total_treatment = max([m.get("treatment_sample", 0) or 0 for m in metrics] or [0])

    mc = _mc_block(results)
    mc_method = str(mc.get("method") or "none")
    mc_family = str(mc.get("family") or "all")
    mc_n = mc.get("n_comparisons")
    mc_alpha = mc.get("corrected_alpha")
    decision_basis = str(mc.get("decision_basis") or "raw")
    top_alpha = results.get("alpha")
    cohort_basis = results.get("cohort_basis")

    if decision_basis == "bonferroni" and isinstance(mc_n, (int, float)) and not isinstance(mc_n, bool):
        _mfam = "全部指标（核心+护栏）" if mc_family == "all" else "核心指标"
        _method_line = (f"对{_mfam}共 {int(mc_n)} 项比较做 Bonferroni 校正，"
                        f"判定阈值收紧为 α={_fmt_alpha(mc_alpha)}")
    else:
        _method_line = "未启用多重比较校正（判定阈值 = 顶层 α）"

    # ---- Significance-caliber disclosure: stated before any conclusion ----
    if decision_basis == "bonferroni" and isinstance(mc_n, (int, float)) and not isinstance(mc_n, bool):
        _fam_txt = "全部指标（核心+护栏）" if mc_family == "all" else "核心指标"
        caliber_html = (
            "<p><strong>显著性判定口径：</strong>"
            f"顶层 α={_fmt_alpha(top_alpha)}，对{_fam_txt}共 {int(mc_n)} 项比较做 "
            f"Bonferroni 校正，判定阈值为 <strong>校正后 α={_fmt_alpha(mc_alpha)}</strong>。"
            "本报告所有「显著」结论均以校正后阈值判定；校正前显著但校正后不显著的指标会单独标注。"
            "</p>")
    else:
        caliber_html = (
            "<p><strong>显著性判定口径：</strong>"
            f"未启用多重比较校正（单次比较），判定阈值 α={_fmt_alpha(mc_alpha if isinstance(mc_alpha, (int, float)) and not isinstance(mc_alpha, bool) else top_alpha)}。"
            "</p>")
    if cohort_basis:
        caliber_html += (
            f"<p><strong>数据口径：</strong>{_e(cohort_basis)}——"
            "分子事件必须属于曝光 cohort 且发生在曝光之后，分母为曝光用户数。"
            "</p>")

    # Executive summary
    exec_summary = caliber_html
    exec_summary += f"<p>本次 A/B 测试「{_e(exp_name)}」在 {_e(time_range) or '未指定周期'} 进行，"
    exec_summary += (f"对照组（{_e(control_name)}）和实验组（{_e(treatment_name)}）"
                     f"各 {total_control:,} 名曝光用户参与。</p>")

    if overall_rec:
        exec_summary += f"<div class='overall-rec' style='border-color:{o_color}'>"
        exec_summary += (f"<div class='overall-rec-badge' style='background:{o_color}'>"
                         f"{_e(overall_rec.get('headline', ''))}</div>")
        exec_summary += f"<p>{_e(overall_rec.get('reason', ''))}</p>"
        exec_summary += "</div>"

    if verdict.get("status") == "treatment_wins":
        # "Wins" must be judged by the DESIRABLE direction, not the numeric sign:
        # a drop in a lower-is-better metric is a win. And it must be the
        # *decision* flag — a metric that lost significance under correction
        # cannot carry a win.
        sig_wins = [m for m in success_metrics
                    if _decision_sig(m) and _favourable(m) > 0]
        if sig_wins:
            best = max(sig_wins, key=_lift_magnitude)
            lift_disp = ("无法计算（对照组均值为 0）" if best.get("relative_lift_undefined")
                         else f"{best.get('relative_lift_pct', 0):+.2f}%")
            word = "下降" if best.get("lower_is_better") else "提升"
            exec_summary += (f"<p>核心指标「{_e(best.get('metric_name', ''))}」显著{word} "
                             f"{_e(lift_disp)}{_polarity_note(best)}")
            bayes = best.get("bayesian") or {}
            if bayes:
                exec_summary += (f"，{_e(_prob_label(bayes))}="
                                 f"{_num(_prob_favourable(bayes)*100, '.0f')}%")
            exec_summary += "。</p>"
            if best.get("decision_basis") == "bonferroni":
                exec_summary += (f"<p style='font-size:14px;color:#64748b'>该结论已通过 Bonferroni "
                                 f"多重比较校正（校正后 α="
                                 f"{_fmt_alpha(best.get('decision_alpha'))}）。</p>")
    elif verdict.get("status") == "inconclusive":
        exec_summary += f"<p>{_e(verdict.get('message', ''))}</p>"
        exec_summary += "<p>详见下方逐指标分析和行动建议——即使统计不显著，也能给出基于现有证据的最佳决策。</p>"

    # A run where every metric lost significance under correction must say so
    # in the executive summary — not only bury it in the methodology section.
    _lost = [m for m in metrics if _raw_sig(m) and not _decision_sig(m)]
    if _lost:
        _names = "、".join(f"「{_e(m.get('metric_name', ''))}」" for m in _lost)
        _alphas = [m.get("decision_alpha") for m in _lost
                   if isinstance(m.get("decision_alpha"), (int, float))
                   and not isinstance(m.get("decision_alpha"), bool)]
        _a_disp = _fmt_alpha(min(_alphas)) if _alphas else "校正后阈值"
        exec_summary += (f"<p style='color:#b45309'><strong>多重比较校正提示：</strong>"
                         f"{_names}在校正前显著，但未通过 Bonferroni 校正后的 α={_a_disp}，"
                         f"因此未计入「显著胜出」，不宜据此上线。</p>")

    if overall_rec.get("downgraded_from"):
        exec_summary += (f"<p style='color:#b45309'>总体建议已由 "
                         f"「{_e(overall_rec.get('downgraded_from'))}」下调为「{_e(overall_rec.get('action', ''))}」"
                         f"（原因：{_e(overall_rec.get('downgrade_reason', ''))}）。</p>")

    if guardrail.get("status") == "safe":
        exec_summary += "<p><strong>护栏指标：</strong>全部安全。</p>"
    elif guardrail.get("status") == "violated":
        exec_summary += (f"<p style='color:#dc2626'><strong>护栏告警：</strong>"
                         f"{_e(guardrail.get('message', ''))}</p>")
        # A guardrail can regress by going UP (crash rate) or DOWN (exposure).
        # State the direction explicitly so the reader never has to guess.
        details = [d for d in (guardrail.get("details") or []) if isinstance(d, dict)]
        if details:
            items = "".join(
                f"<li>{_e(d.get('metric', ''))}：{_e(d.get('change', ''))}"
                f"{'（越低越好）' if d.get('lower_is_better') else '（越高越好）'}</li>"
                for d in details)
            exec_summary += f"<ul style='color:#dc2626'>{items}</ul>"

    # Warnings surfaced by the analysis engine (bad input, failed metrics, ...)
    warnings_html = ""
    _deg = [f"「{m.get('metric_name', '')}」部分 v2 分析未完成：{m['v2_error']}"
            for m in metrics if m.get("v2_error")]
    _all_warn = list(warnings) + _deg
    if _all_warn:
        items = "".join(f"<li>{_e(w)}</li>" for w in _all_warn)
        warnings_html = (f"<div class='warn-box'><strong>分析提示</strong>"
                         f"<ul>{items}</ul></div>")

    # Group cards
    group_sections = ""
    for group_label, group_name, is_treatment in [("对照组", control_name, False), ("实验组", treatment_name, True)]:
        group_sections += (f"<div class='group-card'><h3>{group_label}：{_e(group_name)}</h3>"
                           f"<div class='group-metrics'>")
        if not metrics:
            group_sections += "<div class='group-metric'><span class='gm-label'>无可用指标</span></div>"
        for m in metrics:
            f = _metric_fields(m)
            value = f["t_value"] if is_treatment else f["c_value"]
            n = f["t_n"] if is_treatment else f["c_n"]
            name = _e(m.get("metric_name", ""))
            is_g = m.get("is_guardrail", False)
            tag = '<span class="tag-guardrail">护栏</span>' if is_g else '<span class="tag-success">核心</span>'
            group_sections += f"<div class='group-metric'><span class='gm-label'>{name} {tag}</span>"
            if f["is_proportion"]:
                group_sections += f"<span class='gm-value'>{_num(value*100, '.2f')}%</span>"
                success = round(value * n)
                group_sections += f"<span class='gm-detail'>{success:,} / {n:,}</span></div>"
            else:
                group_sections += f"<span class='gm-value'>{_num(value)}</span>"
                group_sections += f"<span class='gm-detail'>n = {n:,}</span></div>"
        group_sections += "</div></div>"

    # Metric sections
    metric_sections = ""
    for i, m in enumerate(metrics, 1):
        rec = m.get("recommendation") or {}
        action = rec.get("action", "")
        headline = _e(rec.get("headline") or ("分析降级" if m.get("v2_error") else "—"))
        rec_color = _action_color(action)

        bayes = m.get("bayesian") or {}
        power = m.get("power_analysis") or {}

        f = _metric_fields(m)
        c_value = f["c_value"]
        t_value = f["t_value"]
        c_n = f["c_n"]
        t_n = f["t_n"]
        is_proportion = f["is_proportion"]
        test_label = f["test_label"]
        test_stat = f["test_stat"]

        max_value = max(c_value, t_value, 0.001)
        c_bar_h = int(c_value / max_value * 100)
        t_bar_h = int(t_value / max_value * 100)
        if is_proportion:
            c_disp = f"{_num(c_value*100, '.2f')}%"
            t_disp = f"{_num(t_value*100, '.2f')}%"
            abs_disp = f"{_num(m.get('absolute_diff_pct'), '+.2f')}pp"
            lo, hi = _pair(m.get("lift_ci"))
            ci_disp = f"[{_num(lo, '+.2f')}%, {_num(hi, '+.2f')}%]"
        else:
            c_disp = _num(c_value)
            t_disp = _num(t_value)
            abs_disp = _num(m.get("absolute_diff"), "+.2f")
            lo, hi = _pair(m.get("diff_ci"))
            ci_disp = f"[{_num(lo, '+.2f')}, {_num(hi, '+.2f')}]"
        mde_disp = (f"±{_num(m.get('mde_pct'), '.2f')}%"
                    if isinstance(m.get("mde_pct"), (int, float)) else "无法估计")

        if m.get("relative_lift_undefined"):
            lift_disp = "无法计算"
        else:
            lift_disp = f"{m.get('relative_lift_pct', 0):+.2f}%"

        narrative = _narrative_for_metric(m, control_name, treatment_name)

        # Bayesian mini-chart
        bayes_html = ""
        if bayes:
            prob = _prob_favourable(bayes)
            risk_color = _risk_color(bayes.get("risk_level", ""))
            bayes_html = f"""
            <div class="bayes-bar">
                <span class="bayes-label">{_e(_prob_label(bayes))}</span>
                <div class="prob-bar-wrap">
                    <div class="prob-bar" style="width:{min(max(prob*100, 0), 100):.1f}%;background:{risk_color}"></div>
                </div>
                <span class="prob-num">{_num(prob*100, '.1f')}%</span>
                <span class="risk-tag" style="background:{risk_color}20;color:{risk_color}">{_e(bayes.get('risk_label', ''))}</span>
            </div>"""

        # Power mini-chart
        power_html = ""
        if power:
            pow_val = power.get("observed_power") or 0
            pow_color = "#16a34a" if pow_val >= 0.8 else "#f59e0b" if pow_val >= 0.5 else "#dc2626"
            power_html = f"""
            <div class="power-bar">
                <span class="power-label">统计功效</span>
                <div class="prob-bar-wrap">
                    <div class="prob-bar" style="width:{min(max(pow_val*100, 0), 100):.1f}%;background:{pow_color}"></div>
                </div>
                <span class="prob-num">{_num(pow_val*100, '.1f')}%</span>
                <span class="power-tag" style="background:{pow_color}20;color:{pow_color}">{_e(power.get('power_assessment', ''))}</span>
            </div>"""

        req_n = power.get("required_sample_per_group")
        if isinstance(req_n, (int, float)) and not isinstance(req_n, bool):
            req_n_disp = f"{int(req_n):,}"
        else:
            req_n_disp = "无法估计（效应为 0）"

        _is_g = m.get("is_guardrail", False)
        _role_tag = ('<span class="tag-guardrail">护栏</span>' if _is_g
                     else '<span class="tag-success">核心</span>')
        _pol_tag = _polarity_note(m)
        # Correction outcome is stated on the card itself, so a reader skimming
        # the per-metric sections cannot mistake a retired p-value for a win.
        if _decision_sig(m):
            if m.get("decision_basis") == "bonferroni":
                _sig_tag = (f'<span class="tag-sig-yes" title="已通过 Bonferroni 校正">'
                            f'校正后显著 α={_fmt_alpha(m.get("decision_alpha"))}</span>')
            else:
                _sig_tag = '<span class="tag-sig-yes">显著</span>'
        elif _raw_sig(m):
            _sig_tag = (f'<span class="tag-sig-lost" title="校正前显著，校正后不显著">'
                        f'校正后不显著（校正前 p &lt; α）</span>')
        else:
            _sig_tag = '<span class="tag-sig-none">不显著</span>'
        metric_sections += f"""
        <div class="metric-section" id="metric-{i}">
            <div class="metric-header">
                <h3>指标 {i}：{_e(m.get('metric_name', ''))} {_role_tag}{_pol_tag}{_sig_tag}</h3>
                <span class="metric-action-badge" style="background:{rec_color}20;color:{rec_color};border-color:{rec_color}">{headline}</span>
            </div>
            <div class="metric-comparison">
                <div class="bar-comparison">
                    <div class="bar-group">
                        <div class="bar-label">{_e(control_name)}</div>
                        <div class="bar-wrap"><div class="bar bar-control" style="height:{c_bar_h}%"></div></div>
                        <div class="bar-num">{c_disp}</div>
                    </div>
                    <div class="bar-group">
                        <div class="bar-label">{_e(treatment_name)}</div>
                        <div class="bar-wrap"><div class="bar bar-treatment" style="height:{t_bar_h}%"></div></div>
                        <div class="bar-num">{t_disp}</div>
                    </div>
                    <div class="bar-diff">
                        <span class="diff-label">相对变化{'（越低越好）' if m.get('lower_is_better') else ''}</span>
                        <span class="diff-value" style="color:{rec_color}">{_e(lift_disp)}</span>
                    </div>
                </div>
            </div>
            {bayes_html}
            {power_html}
            <div class="metric-narrative">{narrative}</div>
            <div class="metric-stats-grid">
                <div class="stat-cell"><span class="stat-label">对照组样本</span><span class="stat-value">{c_n:,}</span></div>
                <div class="stat-cell"><span class="stat-label">实验组样本</span><span class="stat-value">{t_n:,}</span></div>
                <div class="stat-cell"><span class="stat-label">{test_label} 统计量</span><span class="stat-value">{_num(test_stat, '.4f')}</span></div>
                <div class="stat-cell"><span class="stat-label">p 值</span><span class="stat-value">{_p_val(m.get('p_value'))}</span></div>
                <div class="stat-cell"><span class="stat-label">绝对差异</span><span class="stat-value">{abs_disp}</span></div>
                <div class="stat-cell"><span class="stat-label">95% CI</span><span class="stat-value">{ci_disp}</span></div>
                <div class="stat-cell"><span class="stat-label">MDE</span><span class="stat-value">{mde_disp}</span></div>
                <div class="stat-cell"><span class="stat-label">所需样本/组</span><span class="stat-value">{req_n_disp}</span></div>
            </div>
        </div>"""

    # Metrics that could not be analysed
    error_sections = ""
    if error_metrics:
        rows = "".join(
            f"<li><strong>{_e(m.get('metric_name', '(未命名)'))}</strong>：{_e(m.get('error'))}</li>"
            for m in error_metrics
        )
        error_sections = (f"<div class='error-box'><strong>以下指标未能分析</strong>"
                          f"<ul>{rows}</ul>"
                          f"<p>请核对指标类型（proportion / continuous）与必填字段后重新运行。</p></div>")

    # Action plan & closed-loop
    next_actions = overall_rec.get("next_actions") or []
    action_html = ""
    if next_actions:
        action_html = "<ol class='action-list'>"
        for a in next_actions:
            action_html += f"<li>{_e(a)}</li>"
        action_html += "</ol>"

    # Closed-loop explanation
    closed_loop = """
    <div class="closed-loop">
        <h4>闭环分析</h4>
        <p>本报告不是一次性交付物。根据您选择的行动路径，可以继续分析形成闭环：</p>
        <div class="loop-paths">
            <div class="loop-path">
                <div class="loop-icon">A</div>
                <div class="loop-content">
                    <strong>如果选择「延长实验」</strong>
                    <p>运行更长时间后，再次调用本 skill 分析新数据。系统会自动对比前后趋势，判断效应是否稳定。</p>
                </div>
            </div>
            <div class="loop-path">
                <div class="loop-icon">B</div>
                <div class="loop-content">
                    <strong>如果选择「灰度发布」</strong>
                    <p>灰度 2 周后调用本 skill 分析灰度数据，重点关注留存指标和长期趋势是否维持。</p>
                </div>
            </div>
            <div class="loop-path">
                <div class="loop-icon">C</div>
                <div class="loop-content">
                    <strong>如果选择「子群体下钻」</strong>
                    <p>按平台/地区/用户群体重新查询和分析，本 skill 支持 filter 参数进行分群对比。</p>
                </div>
            </div>
            <div class="loop-path">
                <div class="loop-icon">D</div>
                <div class="loop-content">
                    <strong>如果选择「放弃/调整」</strong>
                    <p>记录本次实验的学习成果（什么无效、为什么），设计新方案后重新启动 A/B 测试。</p>
                </div>
            </div>
        </div>
        <p class="loop-note">无论选择哪条路径，都可以将本报告作为基线，后续分析会参考当前结论进行趋势对比。</p>
    </div>"""

    # Limitations
    limitations = "<ul>"
    total_n = (total_control + total_treatment) if metrics else 0
    limitations += f"<li><strong>样本量：</strong>总计 {total_n:,} 用户。"
    mdes = [m.get("mde_pct") for m in metrics]
    mdes = [v for v in mdes if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if mdes:
        limitations += (f"最小可检测效应 ±{min(mdes):.2f}%。"
                        f"低于此的差异无法可靠检测。</li>")
    else:
        limitations += "当前数据无法估算最小可检测效应（指标取值为 0% 或 100%）。</li>"

    if decision_basis == "bonferroni" and isinstance(mc_n, (int, float)) and not isinstance(mc_n, bool):
        _fam_txt = "全部指标（核心+护栏）" if mc_family == "all" else "核心指标"
        limitations += (f"<li><strong>多重比较：</strong>对{_fam_txt}共 {int(mc_n)} 项比较做了 "
                        f"Bonferroni 校正，判定阈值由 α={_fmt_alpha(top_alpha)} 收紧为 "
                        f"{_fmt_alpha(mc_alpha)}。校正后仍显著的结论更稳健；"
                        f"校正前显著而校正后不显著的指标存在假阳性风险。</li>")
        if _lost:
            limitations += (f"<li><strong>校正后失效：</strong>"
                            f"{len(_lost)} 个指标在校正后不再显著，已在执行摘要中标注。</li>")
    else:
        limitations += ("<li><strong>多重比较：</strong>本次仅单次比较，未做校正。"
                        "若一次性判读多个指标，建议启用 Bonferroni 校正以控制族错误率。</li>")

    limitations += (f"<li><strong>时间窗口：</strong>{_e(time_range) or '未指定'}，"
                    f"可能无法捕获长期效应（新奇效应、留存变化）。</li>")
    limitations += "<li><strong>贝叶斯概率：</strong>「实验组优于对照组」的概率基于无信息先验 Beta(1,1)，结果偏保守，且对「越低越好」的指标会自动取反。如有历史数据可作为先验，概率估计会更准确。</li>"
    if stats_engine and stats_engine != "scipy":
        limitations += ("<li><strong>计算精度：</strong>本次分析运行在无 scipy 的降级模式下"
                        "（正态近似），p 值误差约 1e-3。安装 scipy 后精度更高。</li>")
    limitations += "<li><strong>外部效度：</strong>结论仅适用于当前用户群体和时间段。</li>"
    limitations += "</ul>"

    # Build HTML
    document = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(exp_name)} — A/B 测试分析报告</title>
<style>
:root {{
    --bg:#f8fafc;--card:#fff;--text:#1e293b;--muted:#64748b;
    --border:#e2e8f0;--accent:#3b82f6;--green:#16a34a;--red:#dc2626;
    --amber:#f59e0b;--gray:#6b7280;--dark:#0f172a;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);line-height:1.7}}
.container{{max-width:960px;margin:0 auto;padding:32px 24px}}

.cover{{text-align:center;margin-bottom:40px;padding:40px 32px;background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);border-radius:24px;color:#fff}}
.cover h1{{font-size:32px;margin-bottom:12px}}
.cover .subtitle{{font-size:15px;opacity:0.85;margin-bottom:8px}}
.cover .meta-row{{display:flex;justify-content:center;gap:24px;margin-top:20px;flex-wrap:wrap}}
.cover .meta-item{{font-size:13px;opacity:0.8}}
.cover .meta-item strong{{display:block;font-size:16px;opacity:1;margin-bottom:2px}}

.section{{margin-bottom:32px}}
.section-title{{font-size:20px;font-weight:700;margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid var(--border)}}

.verdict-banner{{border-radius:16px;padding:24px;margin-bottom:24px;border-left:6px solid {v_color};background:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.06)}}
.verdict-banner h2{{color:{v_color};font-size:22px;margin-bottom:8px}}
.verdict-banner p{{color:var(--text);font-size:15px}}

.overall-rec{{border:2px solid;border-radius:12px;padding:16px;margin:16px 0}}
.overall-rec-badge{{display:inline-block;padding:4px 12px;border-radius:20px;font-weight:700;font-size:14px;margin-bottom:8px}}

.exec-summary{{background:#fff;border-radius:16px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:24px}}
.exec-summary p{{margin-bottom:12px;font-size:15px}}
.exec-summary p:last-child{{margin-bottom:0}}

.group-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}}
.group-card{{background:#fff;border-radius:16px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.06)}}
.group-card h3{{font-size:16px;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--border)}}
.group-metrics{{display:flex;flex-direction:column;gap:12px}}
.group-metric{{display:flex;flex-direction:column;gap:2px;padding:8px 12px;border-radius:8px;background:var(--bg)}}
.gm-label{{font-size:13px;color:var(--muted)}}
.gm-value{{font-size:20px;font-weight:700;color:var(--dark)}}
.gm-detail{{font-size:12px;color:var(--muted)}}
.tag-guardrail{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;background:#fef3c7;color:#92400e;margin-left:4px}}
.tag-success{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;background:#dbeafe;color:#1e40af;margin-left:4px}}
.tag-sig-yes{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;background:#dcfce7;color:#166534;margin-left:4px}}
.tag-sig-lost{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;background:#fef3c7;color:#92400e;margin-left:4px}}
.tag-sig-none{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;background:#f1f5f9;color:#64748b;margin-left:4px}}

.metric-section{{background:#fff;border-radius:16px;padding:24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.06)}}
.metric-comparison{{margin-bottom:16px}}
.metric-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}}
.metric-header h3{{font-size:18px}}
.metric-action-badge{{padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600;border:1px solid}}

.bar-comparison{{display:flex;align-items:flex-end;gap:32px;padding:20px;background:var(--bg);border-radius:12px;margin-bottom:16px}}
.bar-group{{display:flex;flex-direction:column;align-items:center;gap:8px;flex:1;max-width:120px}}
.bar-label{{font-size:13px;color:var(--muted)}}
.bar-wrap{{width:60px;height:120px;display:flex;align-items:flex-end;background:#f1f5f9;border-radius:8px;overflow:hidden}}
.bar{{width:100%;border-radius:8px 8px 0 0;transition:height 0.5s}}
.bar-control{{background:#94a3b8}}
.bar-treatment{{background:var(--accent)}}
.bar-num{{font-size:18px;font-weight:700}}
.bar-diff{{display:flex;flex-direction:column;gap:4px;margin-left:auto}}
.diff-label{{font-size:12px;color:var(--muted)}}
.diff-value{{font-size:24px;font-weight:700}}

.bayes-bar,.power-bar{{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--bg);border-radius:8px;margin-bottom:8px}}
.bayes-label,.power-label{{font-size:13px;color:var(--muted);min-width:180px}}
.prob-bar-wrap{{flex:1;height:12px;background:#e2e8f0;border-radius:6px;overflow:hidden}}
.prob-bar{{height:100%;border-radius:6px;transition:width 0.5s}}
.prob-num{{font-size:14px;font-weight:700;min-width:50px}}
.risk-tag,.power-tag{{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}}

.metric-narrative{{margin-bottom:20px}}
.metric-narrative p{{margin-bottom:12px;font-size:15px}}
.metric-narrative p:last-child{{margin-bottom:0}}
.num-highlight{{background:#fef3c7;padding:1px 6px;border-radius:4px;font-weight:600}}

.rec-card{{border:2px solid;border-radius:12px;padding:16px;margin-top:16px}}
.rec-header{{padding:6px 12px;border-radius:8px;font-weight:700;font-size:15px;margin-bottom:8px}}
.rec-reason{{font-size:14px;margin-bottom:8px;color:var(--text)}}
.rec-steps{{padding-left:20px}}
.rec-steps li{{font-size:14px;margin-bottom:6px}}

.metric-stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px;background:var(--bg);border-radius:12px}}
.stat-cell{{display:flex;flex-direction:column;gap:2px}}
.stat-label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px}}
.stat-value{{font-size:14px;font-weight:600;font-variant-numeric:tabular-nums}}
.tag-lower-better{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;background:#e0e7ff;color:#3730a3;margin-left:4px;vertical-align:middle}}
.warn-box,.error-box{{border-radius:12px;padding:16px 20px;margin-bottom:20px;font-size:14px}}
.warn-box{{background:#fffbeb;border-left:5px solid #f59e0b;color:#78350f}}
.error-box{{background:#fef2f2;border-left:5px solid #dc2626;color:#7f1d1d}}
.warn-box strong,.error-box strong{{display:block;margin-bottom:6px}}
.warn-box ul,.error-box ul{{padding-left:20px;margin:0}}
.warn-box li,.error-box li{{margin-bottom:4px;line-height:1.6}}

.method-box,.limits-box{{background:#fff;border-radius:16px;padding:24px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.06)}}
.method-box p{{font-size:14px;margin-bottom:10px}}
.method-box ul{{padding-left:20px}}
.method-box li{{font-size:14px;margin-bottom:6px}}
.limits-box ul{{padding-left:20px}}
.limits-box li{{font-size:14px;margin-bottom:10px}}

.action-box{{background:linear-gradient(135deg,#eff6ff 0%,#f0fdf4 100%);border-radius:16px;padding:24px;margin-bottom:24px}}
.action-box h3{{margin-bottom:16px}}
.action-list{{padding-left:20px}}
.action-list li{{font-size:15px;margin-bottom:12px}}

.closed-loop{{margin-top:24px;padding:20px;background:#fff;border-radius:12px;border:1px solid var(--border)}}
.closed-loop h4{{margin-bottom:12px;font-size:16px}}
.loop-paths{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0}}
.loop-path{{display:flex;gap:12px;padding:12px;background:var(--bg);border-radius:8px}}
.loop-icon{{width:32px;height:32px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}}
.loop-content strong{{display:block;font-size:14px;margin-bottom:4px}}
.loop-content p{{font-size:13px;color:var(--muted)}}
.loop-note{{font-size:13px;color:var(--muted);font-style:italic}}

.footer{{text-align:center;color:var(--muted);font-size:12px;padding:24px;border-top:1px solid var(--border)}}

@media (max-width:640px){{
    .group-grid{{grid-template-columns:1fr}}
    .metric-stats-grid{{grid-template-columns:repeat(2,1fr)}}
    .bar-comparison{{flex-direction:column;align-items:stretch}}
    .loop-paths{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<div class="container">

<div class="cover">
    <h1>{_e(exp_name)}</h1>
    <div class="subtitle">{_e(control_name)} vs {_e(treatment_name)}</div>
    <div class="meta-row">
        <div class="meta-item"><strong>{_e(time_range) or '—'}</strong>实验周期</div>
        <div class="meta-item"><strong>{total_control:,} + {total_treatment:,}</strong>总样本</div>
        <div class="meta-item"><strong>{len(metrics)}</strong>分析指标</div>
        <div class="meta-item"><strong>{gen_date}</strong>报告生成</div>
    </div>
</div>

<div class="verdict-banner">
    <h2>实验结论：{v_label}</h2>
    <p>{_e(verdict.get('message', '分析完成'))}</p>
</div>

{warnings_html}

<div class="section">
    <div class="section-title">一、执行摘要</div>
    <div class="exec-summary">
        {exec_summary}
    </div>
</div>

<div class="section">
    <div class="section-title">二、实验设计</div>
    <div class="method-box">
        <p><strong>实验假设：</strong>{_e(hypothesis) or '未提供（请在分析输入中补充 hypothesis 字段）'}</p>
        <p><strong>分组方式：</strong>通过{'事件属性' if group_field_type == 'event_property' else '用户属性'} <code>{_e(group_field) or '未指定'}</code> 分流，对照组 <code>{_e(control_name)}</code>，实验组 <code>{_e(treatment_name)}</code>。</p>
        <p><strong>核心指标（{len(success_metrics)}个）：</strong></p>
        <ul>{''.join(f'<li>{_e(m.get("metric_name", ""))}{_polarity_note(m)}</li>' for m in success_metrics) or '<li>无</li>'}</ul>
        <p><strong>护栏指标（{len(guardrail_metrics)}个）：</strong></p>
        <ul>{''.join(f'<li>{_e(m.get("metric_name", ""))}{_polarity_note(m)}</li>' for m in guardrail_metrics) if guardrail_metrics else '<li>无</li>'}</ul>
        <p><strong>时间范围：</strong>{_e(time_range) or '未指定'}</p>
        <p><strong>数据来源：</strong>{_e(data_source)}，ae-cli <code>analysis.adhoc.run</code></p>
        {polarity_assumptions}
    </div>
</div>

<div class="section">
    <div class="section-title">三、分组效果总览</div>
    <p style="margin-bottom:16px;font-size:15px">每组各 {total_control:,} 名曝光用户参与实验（曝光 cohort 为统计分母）。</p>
    {error_sections}
    <div class="group-grid">{group_sections}</div>
</div>

<div class="section">
    <div class="section-title">四、逐指标详细分析</div>
    <p style="margin-bottom:16px;font-size:15px">每个指标包含：数据表现、统计检验、贝叶斯概率、功效分析、业务评估和行动建议。即使统计不显著，也能给出基于现有证据的决策指引。</p>
    {metric_sections or "<p style='color:#64748b'>没有可分析的指标。</p>"}
</div>

<div class="section">
    <div class="section-title">五、护栏指标分析</div>
    <div class="method-box" style="border-left:6px solid {'#16a34a' if guardrail.get('status')=='safe' else '#dc2626'}">
        <p><strong>护栏状态：</strong>{'安全' if guardrail.get('status')=='safe' else '告警' if guardrail.get('status')=='violated' else '未配置'}</p>
        <p>{_e(guardrail.get('message', ''))}</p>
    </div>
</div>

<div class="section">
    <div class="section-title">六、统计方法论</div>
    <div class="method-box">
        <p><strong>频率派检验：</strong>比例类指标用双比例 z 检验，连续类指标用 Welch t 检验（双侧）。顶层 α={_fmt_alpha(top_alpha)}；{_method_line}</p>
        <p><strong>显著性判定：</strong>所有结论以<strong>校正后阈值</strong>为准（当前判定基准：{_e(decision_basis)}，阈值 α={_fmt_alpha(mc_alpha if isinstance(mc_alpha, (int, float)) and not isinstance(mc_alpha, bool) else top_alpha)}）。原始 p 值仅用于披露。</p>
        <p><strong>数据口径：</strong>{_e(cohort_basis) if cohort_basis else '曝光 cohort 分母（分子须为曝光后发生的成功事件）'}；比例指标 n = 曝光用户数，连续指标为「每曝光用户均值 × 曝光用户数」，避免只统计付费/活跃子集。</p>
        <p><strong>贝叶斯分析：</strong>Beta(1+success, 1+failure) 后验分布，Monte Carlo 200k 次采样计算「实验组优于对照组」的概率（对标注或推断为「越低越好」的指标自动取反，如崩溃率、响应耗时）。提供概率化决策依据，弥补 p 值无法回答「有多大概率实验组更好」的局限。</p>
        <p><strong>功效分析：</strong>基于观察到的效应量计算事后统计功效（1-β）。功效 ≥ 80% 时不显著意味着效果很可能不存在；功效 &lt; 80% 时不显著可能是样本不足。</p>
        <p><strong>业务显著性：</strong>转化类指标按业务意义阈值（付费≥5%、留存≥3%、转化≥5%）判定；连续型指标（ARPU/时长等）无统一单位，仅用相对提升判定。</p>
        <p><strong>置信区间：</strong>95% CI，包含 0 时与 p ≥ 0.05 一致。</p>
        <p><strong>计算引擎：</strong>{_e(stats_engine) or 'unknown'}</p>
    </div>
</div>

<div class="section">
    <div class="section-title">七、局限性与注意事项</div>
    <div class="limits-box">{limitations}</div>
</div>

<div class="section">
    <div class="section-title">八、行动计划与闭环分析</div>
    <div class="action-box">
        <h3>总体建议：{_e(overall_rec.get('headline', ''))}</h3>
        <p style="margin-bottom:16px">{_e(overall_rec.get('reason', ''))}</p>
        {action_html}
    </div>
    {closed_loop}
</div>

<div class="footer">
    <p>ab-test-analysis skill v2.7.0 · 自动生成</p>
    <p>z检验 · 贝叶斯Beta后验 · 事后功效 · Bonferroni校正 · 业务显著性</p>
    <p>数据来源：{_e(data_source)} · {gen_date}</p>
</div>

</div>
</body>
</html>"""

    return document


def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive A/B test HTML report v2")
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        with open(args.results, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        _fail(f"analysis results not found: {args.results}")
    except OSError as exc:
        _fail(f"cannot read analysis results: {exc}")

    if not raw.strip():
        _fail(f"analysis results file is empty: {args.results}")

    try:
        results = json.loads(raw)
    except json.JSONDecodeError as exc:
        _fail(f"analysis results are not valid JSON: {exc}")

    if not isinstance(results, dict):
        _fail(f"analysis results must be a JSON object, got {type(results).__name__}")

    if not results.get("results"):
        _fail("analysis results contain no metrics — run Step 2 (ab_test_stats.py) first, "
              "or fix the metric definitions it rejected.")

    try:
        document = generate_html(results)
    except Exception as exc:
        _fail(f"report generation failed: {type(exc).__name__}: {exc}")

    out_dir = os.path.dirname(os.path.abspath(args.output))
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(document)
    except OSError as exc:
        _fail(f"cannot write report to {args.output}: {exc}")

    print(f"Report v2 generated: {args.output} ({len(document):,} bytes)")


if __name__ == "__main__":
    main()
