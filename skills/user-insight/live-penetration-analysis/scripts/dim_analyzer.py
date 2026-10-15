#!/usr/bin/env python3
"""
Dimension / cross drill-down analyzer — reads ae-cli-persisted dimension JSON,
computes intra-group penetration daily series + dual-threshold anomaly judgment.
Solves the pain points: hand-written group3/group4 parsing, OS case normalization,
version DAU filtering, dual-threshold anomaly judgment — repeatedly written and
repeatedly error-prone during dimension breakdown / cross drill-down.

Usage (three modes):

1) Aggregate analysis (Part 1): read three series JSON ({date: uv})
   python3 dim_analyzer.py overview enter.json bhv.json dau.json

2) Single-dimension breakdown (Part 3, two things each as a file group):
   python3 dim_analyzer.py dim \
       --enter enter_os.json --bhv bhv_os.json --dau dau_os.json \
       --name "OS" --os-normalize
   # output: each dimension value's intra-group penetration first/last/Δ/mean + dual-threshold anomaly mark
   # --os-normalize: case normalization (for primary-event uppercase / DAU lowercase join failure)

3) Cross drill-down (Part 4, suspect dimension × secondary dimension, SQL returns 3 dims [date, dim1, dim2, uv]):
   python3 dim_analyzer.py cross \
       --enter x_neworg_enter.json --dau x_neworg_dau.json \
       --dim1 new --name "new-user × organic/paid" \
       --min-dau 500 --top 10
   # take the dim1=='new' subset, split by dim2 to compute intra-group rate, filter low-volume groups by DAU

Common params:
   --min-dau N      skip days where a group's single-day denominator < N (version noise, default 0)
   --top N          only show TOP N groups by DAU total (version dimension, default all)
   --mindim2-dau N  skip dim2 groups whose 30-day DAU total < N (default 0)
   --os-normalize   lower() normalize dim2 values (required for OS cross drill-down)
   --summary-only   only emit conclusion lines (first/last/Δ/mean/low/anomaly mark), no daily series
                    — use for daily anomaly judgment to save tokens; remove to re-run for daily detail

Dual threshold (implemented from judgment-parameters.md, the sole authority):
   threshold A: day-over-day |Δ| >= max(0.3pp, first-day rate×1.5%); threshold B: consecutive ≥3 days same-direction cumulative ≥0.5pp

Anomaly verdict = threshold A OR threshold B. Significant NET trend is a hint:
   first-half vs second-half mean displacement ≥0.5pp AND ≥2× day-over-day noise σ.
   It helps the main agent distinguish sustained movement from isolated swings, but does not
   replace the authoritative dual-threshold anomaly verdict.
"""

import json
import sys
import statistics

INFLECTION_ABS_THRESHOLD = 0.3
INFLECTION_REL_RATIO = 0.015
INFLECTION_CUM_THRESHOLD = 0.5
INFLECTION_CUM_MIN_DAYS = 3


def load(path):
    """Read ae-cli persisted JSON, tolerant of ae-cli log prefix (find '{')"""
    import os
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"File not found: {path}\n"
            f"  → Run ae_query.sh first to generate it, e.g.:\n"
            f"    ./ae_query.sh sql {path} <<'SQL' ... SQL"
        )
    raw = open(path).read()
    if not raw.strip():
        raise ValueError(f"File is empty: {path} — ae-cli query may have failed. Check the .stderr.log file.")
    i = raw.find('{')
    if i < 0:
        raise ValueError(f"{path} contains no valid JSON (no '{{' found). First 200 chars: {raw[:200]}")
    try:
        data = json.loads(raw[i:])
    except json.JSONDecodeError as e:
        raise ValueError(f"{path} JSON parse error: {e}. First 200 chars after '{{': {raw[i:i+200]}")
    if 'data' not in data:
        raise ValueError(f"{path} has no 'data' key. Keys found: {list(data.keys())}. ae-cli may have returned an error.")
    rows = data.get('data', {}).get('rows', [])
    if not rows:
        raise ValueError(f"{path} has empty data.rows. ae-cli returned ok={data.get('ok')} but no rows.")
    return rows


def load_series(path):
    """Single series {date: int}"""
    return {r[0]: int(r[1]) for r in load(path)}


def group2(path):
    """[date, dim, uv] -> {date: {dim: uv}}"""
    out = {}
    for r in load(path):
        out.setdefault(r[0], {})[r[1]] = int(r[2])
    return out


def group3(path):
    """[date, dim1, dim2, uv] -> {(date,dim1): {dim2: uv}}"""
    out = {}
    for r in load(path):
        out.setdefault((r[0], str(r[1])), {})[str(r[2])] = out.setdefault((r[0], str(r[1])), {}).get(str(r[2]), 0) + int(r[3])
    return out


def pen(n, d):
    return n / d * 100 if d > 0 else None


def dual_threshold_flag(series):
    """Return the day-by-day boolean list of threshold-A triggers"""
    first = next((x for x in series if x is not None), None)
    if first is None:
        return [False] * max(0, len(series) - 1)
    threshold = max(INFLECTION_ABS_THRESHOLD, first * INFLECTION_REL_RATIO)
    flags = []
    for i in range(1, len(series)):
        cur, prev = series[i], series[i - 1]
        if cur is None or prev is None:
            flags.append(False)
            continue
        flags.append(abs(cur - prev) >= threshold)
    return flags


def cum_check(series):
    """Whether any uninterrupted same-direction run hits threshold B.

    Missing or flat days break the run. In particular, missing dates must never
    be compressed away and treated as consecutive observations.
    """
    sign = None
    acc = 0.0
    cnt = 0
    for i in range(1, len(series)):
        prev, cur = series[i - 1], series[i]
        if prev is None or cur is None or cur == prev:
            sign, acc, cnt = None, 0.0, 0
            continue
        delta = cur - prev
        move_sign = 1 if delta > 0 else -1
        if move_sign != sign:
            sign, acc, cnt = move_sign, delta, 1
        else:
            acc += delta
            cnt += 1
        if cnt >= INFLECTION_CUM_MIN_DAYS and abs(acc) >= INFLECTION_CUM_THRESHOLD:
            return True
    return False


def trend_test(valid):
    """Net-trend significance: first-half vs second-half mean displacement vs
    day-over-day noise σ. A random-walk noise series produces day-over-day swings
    but a near-zero net displacement between halves; a genuine trend produces a
    large, coherent net displacement that exceeds the noise band. This auxiliary
    hint does not replace the dual-threshold anomaly mark."""
    n = len(valid)
    if n < 6:
        return 0.0, 0.0  # too short to separate trend from noise
    half = n // 2
    first = sum(valid[:half]) / half
    second = sum(valid[half:]) / (n - half)
    net = second - first
    dod = [valid[i] - valid[i - 1] for i in range(1, n)]
    sigma = statistics.pstdev(dod) if len(dod) >= 2 else 0.0
    return net, sigma


def judge(series):
    """For one daily penetration series, output first/last/Δ/mean/low + anomaly mark.

    Anomaly follows the authoritative dual threshold: threshold A OR threshold B.
    The net-trend calculation remains a separate mechanical hint for the main
    agent's full-series shape judgment."""
    valid = [x for x in series if x is not None]
    if len(valid) < 2:
        return None  # not enough non-None data points to judge; caller should skip this group
    s, e = valid[0], valid[-1]
    mean = sum(valid) / len(valid)
    flags = dual_threshold_flag(series)
    nflag = sum(flags)
    cum = cum_check(series)
    net, sigma = trend_test(valid)
    net_hint = abs(net) >= INFLECTION_CUM_THRESHOLD and (sigma == 0.0 or abs(net) >= 2 * sigma)
    abnormal = nflag > 0 or cum
    return dict(s=s, e=e, delta=e - s, mean=mean, low=min(valid),
                nflag=nflag, cum=cum, abnormal=abnormal,
                net_hint=net_hint, net=net, sigma=sigma, seq=series)


def fmt(r, label, tot=None, summary_only=False):
    tot_s = f" DAU total {tot:>7}" if tot is not None else ""
    mark = " ★anomaly" if r['abnormal'] else ""
    net_mark = " hint" if r['net_hint'] else ""
    net_s = f" net {r['net']:+5.2f}pp σ{r['sigma']:.2f}{net_mark}"
    line = (f"  [{label:>22}]{tot_s} {r['s']:5.2f}%→{r['e']:5.2f}% "
            f"Δ{r['delta']:+5.2f}pp mean {r['mean']:5.2f}% low {r['low']:5.2f}%"
            f"{net_s} "
            f"swing {r['nflag']}x sustained-run {'yes' if r['cum'] else 'no'}{mark}")
    if summary_only:
        return line   # only conclusion line, no daily series (save tokens; remove --summary-only for detail)
    seq = ' '.join("NA" if x is None else f"{x:.1f}" for x in r['seq'])
    return line + f"\n      daily: {seq}"


def cmd_overview(argv):
    enter = load_series(argv[0])
    bhv = load_series(argv[1])
    dau = load_series(argv[2])
    dates = sorted(set(enter) | set(bhv) | set(dau))
    print("=== aggregate trend ===")
    print(f"{'date':<12}{'enter_uv':>9}{'bhv_uv':>8}{'DAU':>8}{'enter%':>9}{'bhv%':>8}")
    for d in dates:
        enter_uv = enter.get(d, 0)
        bhv_uv = bhv.get(d, 0)
        dau_uv = dau.get(d, 0)
        enter_pen = pen(enter_uv, dau_uv)
        bhv_pen = pen(bhv_uv, dau_uv)
        enter_pen_s = "NA" if enter_pen is None else f"{enter_pen:.2f}%"
        bhv_pen_s = "NA" if bhv_pen is None else f"{bhv_pen:.2f}%"
        print(f"{d:<12}{enter_uv:>9}{bhv_uv:>8}{dau_uv:>8}"
              f"{enter_pen_s:>9}{bhv_pen_s:>8}")
    valid_dates = [d for d in dates if dau.get(d, 0) > 0]
    if not valid_dates:
        raise ValueError("DAU series has no date with a positive denominator")
    s, e = valid_dates[0], valid_dates[-1]
    enter_s, enter_e = enter.get(s, 0) / dau[s], enter.get(e, 0) / dau[e]
    bhv_s, bhv_e = bhv.get(s, 0) / dau[s], bhv.get(e, 0) / dau[e]
    print(f"\nEnter {enter_s*100:.2f}%→{enter_e*100:.2f}% "
          f"({(enter_e-enter_s)*100:+.2f}pp)")
    print(f"bhv {bhv_s*100:.2f}%→{bhv_e*100:.2f}% "
          f"({(bhv_e-bhv_s)*100:+.2f}pp)")
    print(f"DAU {dau[s]}→{dau[e]} ({(dau[e]-dau[s])/dau[s]*100:+.2f}%)")


def cmd_dim(argv, opts):
    enter = group2(opts['enter'])
    bhv = group2(opts['bhv']) if opts.get('bhv') else None
    dau = group2(opts['dau'])
    # Include denominator-only dates: an absent numerator row means zero entries,
    # not a date that may be silently removed from the trend.
    dates = sorted(set(enter) | set(dau))
    normalize = opts.get('os_normalize')

    def norm(v):
        return str(v).lower() if normalize else str(v)

    # merge dim values (numerator/denominator may differ in case; aggregate after norm)
    dims_e = {}
    for d in dates:
        for v, uv in enter.get(d, {}).items():
            dims_e.setdefault(d, {})[norm(v)] = dims_e.setdefault(d, {}).get(norm(v), 0) + uv
    dims_d = {}
    for d in dates:
        for v, uv in dau.get(d, {}).items():
            dims_d.setdefault(d, {})[norm(v)] = dims_d.setdefault(d, {}).get(norm(v), 0) + uv

    print(f"=== dimension {opts['name']} ===")
    dims = set()
    for d in dates:
        dims |= set(dims_e.get(d, {}).keys()) | set(dims_d.get(d, {}).keys())
    tot = {k: sum(dims_d.get(d, {}).get(k, 0) for d in dates) for k in dims}
    order = sorted(dims, key=lambda k: -tot.get(k, 0))
    if opts.get('top'):
        order = order[:opts['top']]
    min_dau = opts.get('min_dau', 0)
    for k in order:
        if k in ('none', ''):
            continue
        if opts.get('mindim2_dau', 0) and tot.get(k, 0) < opts['mindim2_dau']:
            continue
        # skip days where daily denominator < min_dau (early version rollout with a handful of users
        # makes penetration noise, computing fake >100% values)
        series = []
        for d in dates:
            ndv = dims_d.get(d, {}).get(k, 0)
            if min_dau and ndv < min_dau:
                series.append(None)
            else:
                series.append(pen(dims_e.get(d, {}).get(k, 0), ndv))
        r = judge(series)
        if r is None:
            continue
        print(fmt(r, k, tot.get(k, 0), summary_only=opts.get('summary_only')))


def cmd_cross(argv, opts):
    enter = group3(opts['enter'])
    dau = group3(opts['dau'])
    dim1 = opts.get('dim1', 'new')
    # extract all dates from enter (matching dim1)
    all_dates = set()
    for (d, d1) in enter:
        if d1 == dim1:
            all_dates.add(d)
    for (d, d1) in dau:
        if d1 == dim1:
            all_dates.add(d)
    dates = sorted(all_dates)
    normalize = opts.get('os_normalize')

    def norm(v):
        return str(v).lower() if normalize else str(v)

    # merge dim2
    ent = {}
    for (d, d1), m in enter.items():
        if d1 != dim1:
            continue
        for k, uv in m.items():
            ent[(d, norm(k))] = ent.get((d, norm(k)), 0) + uv
    ded = {}
    for (d, d1), m in dau.items():
        if d1 != dim1:
            continue
        for k, uv in m.items():
            ded[(d, norm(k))] = ded.get((d, norm(k)), 0) + uv

    dims = set(kk for (d, kk) in ent) | set(kk for (d, kk) in ded)
    tot = {}
    for (d, k), v in ded.items():
        tot[k] = tot.get(k, 0) + v

    print(f"=== cross drill-down {opts['name']} (dim1={dim1}) ===")
    order = sorted(dims, key=lambda k: -tot.get(k, 0))
    if opts.get('top'):
        order = order[:opts['top']]
    min_dau = opts.get('min_dau', 0)
    for k in order:
        if k in ('none', ''):
            continue
        if tot.get(k, 0) < opts.get('mindim2_dau', 0):
            continue
        # skip days where daily denominator < min_dau (same as dim mode, prevent >100% fake values in early rollout)
        series = []
        for d in dates:
            ndv = ded.get((d, k), 0)
            if min_dau and ndv < min_dau:
                series.append(None)
            else:
                series.append(pen(ent.get((d, k), 0), ndv))
        r = judge(series)
        if r is None:
            continue
        print(fmt(r, k, tot.get(k, 0), summary_only=opts.get('summary_only')))


def parse_opts(argv):
    opts = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--name':
            opts['name'] = argv[i + 1]; i += 2
        elif a == '--enter':
            opts['enter'] = argv[i + 1]; i += 2
        elif a == '--bhv':
            opts['bhv'] = argv[i + 1]; i += 2
        elif a == '--dau':
            opts['dau'] = argv[i + 1]; i += 2
        elif a == '--dim1':
            opts['dim1'] = argv[i + 1]; i += 2
        elif a == '--min-dau':
            opts['min_dau'] = int(argv[i + 1]); i += 2
        elif a == '--top':
            opts['top'] = int(argv[i + 1]); i += 2
        elif a == '--mindim2-dau':
            opts['mindim2_dau'] = int(argv[i + 1]); i += 2
        elif a == '--os-normalize':
            opts['os_normalize'] = True; i += 1
        elif a == '--summary-only':
            opts['summary_only'] = True; i += 1
        else:
            i += 1
    return opts


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    mode = sys.argv[1]
    rest = sys.argv[2:]
    try:
        if mode == 'overview':
            cmd_overview(rest)
        elif mode == 'dim':
            cmd_dim(rest, parse_opts(rest))
        elif mode == 'cross':
            cmd_cross(rest, parse_opts(rest))
        else:
            print(__doc__)
    except (FileNotFoundError, ValueError) as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
