#!/usr/bin/env python3
"""Validation gate: check ae-cli query output for data quality and cohort integrity.

ae-cli output shape (see references/ae_cli_query_patterns.md):
    {
      "ok": true,
      "data": {
        "title": ["时间", "<group_field>", "<metric1>", "<metric2>", ...],
        "rows": [
          ["<time_range>", "<group_value>", "<metric1_value>", ...],  # all strings
          ...
        ],
        ...
      }
    }

Usage:
    validate_query_output.py <query_output.json> [field_mapping.json]

The optional field_mapping.json supplies the declared `cohort` block, which is
how the denominators are identified. Without it the gate falls back to column
name hints and downgrades the outcome to WARN.

## Why the sample gate only looks at the denominator

The previous version range-checked *every* column whose name looked like a user
count. In a perfectly normal conversion query that means the success column is
checked too, so 10,000 exposed users with 50 conversions in one arm was reported
as "50 users < 100 minimum — insufficient sample" — a false alarm on the
numerator — while a genuinely degenerate 0-conversion arm passed silently,
because zero was excluded from the check. Statistical adequacy is a property of
the **cohort** (the denominator), not of the numerator. This gate now:

  * identifies one denominator column (explicit > hinted)      ERROR if unknown
  * applies the MIN_SAMPLE floor to that column only            ERROR if below
  * requires every numerator cell to be <= its denominator      ERROR if not
  * flags a zero numerator as a degenerate comparison            WARN
  * requires an exposure-cohort declaration when no mapping is given  WARN

Exit codes: 0 = SUCCESS / WARN, 1 = EMPTY / ERROR / FATAL.
"""
import json
import os
import sys

# Columns that hold a rate / average / duration rather than a user count.
RATE_COLUMN_HINTS = (
    "率", "占比", "比例", "百分比", "平均", "均值", "时长", "分数", "得分",
    "rate", "ratio", "pct", "percent", "avg", "mean", "median", "score",
    "duration", "ltv", "arpu", "arppu",
)

# Columns that are almost certainly a numerator (a success/guardrail outcome).
NUMERATOR_HINTS = (
    "成功", "付费", "购买", "下单", "充值", "支付", "注册", "订阅", "转化", "点击",
    "完成", "崩溃", "闪退", "错误", "失败", "超时", "退款", "投诉", "流失", "卸载",
    "留存", "召回", "参与",
    "success", "purchase", "pay", "order", "recharge", "signup", "register",
    "subscribe", "convert", "click", "complete", "crash", "error", "fail",
    "timeout", "refund", "churn", "uninstall", "retention",
)

# Columns that plausibly hold the exposed-cohort size (the denominator).
DENOMINATOR_HINTS = (
    "曝光", "进入实验", "分流", "实验用户", "覆盖", "总用户", "用户数", "人数",
    "去重", "分母", "样本量", "参与用户",
    "exposure", "exposed", "cohort", "users", "user_count", "uv",
)

COHORT_BASIS_EXPECTED = "exposed_users_after_exposure"


def _to_number(val):
    """Convert a metric cell to number; return None if not numeric."""
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        s = val.strip().replace(",", "").replace("%", "")
        if s == "":
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _hits(name, hints):
    n = str(name or "").lower()
    return any(h in n for h in hints)


def _classify_column(col_name):
    """role in ('rate', 'numerator', 'denominator', 'unknown')."""
    if _hits(col_name, RATE_COLUMN_HINTS):
        return "rate"
    if _hits(col_name, NUMERATOR_HINTS):
        return "numerator"
    if _hits(col_name, DENOMINATOR_HINTS):
        return "denominator"
    return "unknown"


def _fatal(msg, check="input"):
    return {"status": "FATAL", "checks": [{"check": check, "status": "FATAL", "message": msg}]}


def _load_cohort(plan_path):
    """Read the declared cohort block, if any. Returns (cohort, note)."""
    if not plan_path:
        return {}, ""
    try:
        with open(plan_path, encoding="utf-8") as f:
            mapping = json.load(f)
    except FileNotFoundError:
        return {}, f"cohort declaration file not found: {plan_path}"
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"cohort declaration unreadable: {exc}"
    if not isinstance(mapping, dict):
        return {}, "cohort declaration is not an object"
    cohort = mapping.get("cohort")
    return (cohort if isinstance(cohort, dict) else {}), ""


def validate(input_file, plan_path=None):
    # ---- 1. read + parse (never let a traceback escape) -------------------
    try:
        with open(input_file, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return _fatal(f"Input file not found: {input_file}", "file_readable")
    except OSError as exc:
        return _fatal(f"Cannot read input file: {exc}", "file_readable")

    if not raw.strip():
        return _fatal("Query output file is empty (0 bytes). ae-cli produced no output.",
                      "file_not_empty")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _fatal(f"Query output is not valid JSON: {exc}. First 120 chars: {raw[:120]!r}",
                      "json_parse")

    checks = []
    cohort, cohort_note = _load_cohort(plan_path)

    # ---- 2. top-level shape ----------------------------------------------
    if not isinstance(data, dict) or not data:
        return _fatal(f"Expected a JSON object at top level, got {type(data).__name__}. "
                      f"Check that ae-cli was invoked with --format json.", "top_level_shape")

    if not data.get("ok", False):
        err = data.get("error")
        detail = err.get("message") if isinstance(err, dict) else err
        return _fatal(f"ae-cli returned ok=false: {detail or 'unknown error'}", "ae_cli_ok")

    result_data = data.get("data")
    if not isinstance(result_data, dict):
        return _fatal(f"`data` must be an object with `title`/`rows`, got "
                      f"{type(result_data).__name__}. ae-cli response shape changed?", "data_shape")

    rows = result_data.get("rows")
    columns = result_data.get("title")

    if rows is None:
        checks.append({"check": "has_data", "status": "EMPTY",
                       "message": "ae-cli returned no `rows` key. Check time range and event names."})
        return {"status": "EMPTY", "checks": checks}
    if not isinstance(rows, list):
        return _fatal(f"`data.rows` must be an array, got {type(rows).__name__}.", "rows_shape")
    if not rows:
        return {"status": "EMPTY", "checks": [{
            "check": "has_data", "status": "EMPTY",
            "message": "ae-cli returned no data rows. Check time range and event names."}]}

    if columns is None:
        columns = []
    if not isinstance(columns, list):
        checks.append({"check": "columns_shape", "status": "ERROR",
                       "message": f"`data.title` must be an array, got {type(columns).__name__}; "
                                  f"column names will be generic."})
        columns = []

    # ---- 3. row shape -----------------------------------------------------
    group_values = []
    malformed = 0
    max_cols = 0
    for i, row in enumerate(rows):
        if not isinstance(row, list):
            checks.append({"check": f"row_shape_{i}", "status": "ERROR",
                           "message": f"Row {i} is malformed: expected [time, group, metric...], "
                                      f"got {type(row).__name__} ({str(row)[:60]!r})"})
            malformed += 1
            continue
        max_cols = max(max_cols, len(row))
        if len(row) < 2:
            checks.append({"check": f"row_shape_{i}", "status": "ERROR",
                           "message": f"Row {i} has only {len(row)} column(s); expected at least "
                                      f"[time, group]."})
            malformed += 1
            continue
        group_values.append(row[1])

    if max_cols < 3:
        checks.append({"check": "metric_columns", "status": "ERROR",
                       "message": f"Rows carry only {max_cols} column(s) — no metric values found. "
                                  f"Add at least one metric (e.g. 用户数 / 付费用户数) to the ae-cli query."})
    else:
        checks.append({"check": "metric_columns", "status": "PASS",
                       "message": f"Rows carry {max_cols} columns ({max_cols - 2} metric column(s))."})

    # ---- 4. variant groups ------------------------------------------------
    detected_groups = sorted({str(g) for g in group_values if g is not None and str(g) != ""})
    if len(detected_groups) < 2:
        checks.append({"check": "variant_groups", "status": "ERROR",
                       "message": f"Expected >= 2 distinct variant groups, got "
                                  f"{len(detected_groups)} ({detected_groups}). "
                                  f"Check variant property name and whether the experiment has been running."})
    elif len(detected_groups) > 2:
        checks.append({"check": "variant_groups", "status": "ERROR",
                       "message": f"Found {len(detected_groups)} variant groups: {detected_groups}. "
                                  f"This skill only analyses two-group A/B tests — either filter to two "
                                  f"groups or use a multi-variant tool."})
    else:
        checks.append({"check": "variant_groups", "status": "PASS",
                       "message": f"Found 2 variant groups: {detected_groups}"})

    # ---- 5. cohort declaration --------------------------------------------
    declared_denominator = str(cohort.get("denominator_column") or "").strip()
    declared_basis = str(cohort.get("basis") or "").strip()
    metric_columns = columns[2:] if len(columns) > 2 else []

    if cohort_note:
        checks.append({"check": "cohort_declaration_readable", "status": "WARN",
                       "message": f"{cohort_note} — falling back to column-name heuristics."})

    if declared_basis:
        if declared_basis != COHORT_BASIS_EXPECTED:
            checks.append({"check": "cohort_basis", "status": "ERROR",
                           "message": f"cohort.basis = {declared_basis!r} is not "
                                      f"{COHORT_BASIS_EXPECTED!r}. The numerator must be users who were "
                                      f"exposed AND converted after exposure — a success count over a "
                                      f"denominator that is not the exposed cohort is not a "
                                      f"conversion rate."})
        else:
            checks.append({"check": "cohort_basis", "status": "PASS",
                           "message": f"cohort.basis = {COHORT_BASIS_EXPECTED}"})
    elif cohort:
        # A cohort block WAS supplied but incomplete — that is a broken
        # declaration, not a missing one, and must block.
        checks.append({"check": "cohort_basis", "status": "ERROR",
                       "message": f"A `cohort` block was supplied without `basis`. Add "
                                  f"\"basis\": \"{COHORT_BASIS_EXPECTED}\" — without it the gate cannot "
                                  f"tell whether the numerator is restricted to the exposed cohort. "
                                  f"An incomplete declaration is more dangerous than none, because the "
                                  f"query looks validated."})
    else:
        checks.append({"check": "cohort_basis", "status": "WARN",
                       "message": "No cohort declaration supplied. Pass field_mapping.json as the "
                                  "second argument with a `cohort` block naming the denominator column, "
                                  "so the gate knows which column is the exposed cohort instead of "
                                  "guessing from column names."})

    # ---- 6. denominator identification ------------------------------------
    roles = {}
    for j, name in enumerate(metric_columns, start=2):
        roles[j] = _classify_column(name)

    denominator_idx = None
    if declared_denominator:
        for j, name in enumerate(metric_columns, start=2):
            if str(name).strip() == declared_denominator:
                denominator_idx = j
                break
        if denominator_idx is None:
            checks.append({"check": "denominator_column", "status": "ERROR",
                           "message": f"cohort.denominator_column = {declared_denominator!r} is not "
                                      f"among the returned metric columns {metric_columns}. The query "
                                      f"and the declaration have drifted apart."})
        else:
            checks.append({"check": "denominator_column", "status": "PASS",
                           "message": f"Denominator column (exposed cohort) = {declared_denominator!r}"})
    else:
        candidates = [j for j, role in roles.items() if role == "denominator"]
        if len(candidates) == 1:
            denominator_idx = candidates[0]
            checks.append({"check": "denominator_column", "status": "WARN",
                           "message": f"Denominator inferred from the column name: "
                                      f"{columns[denominator_idx]!r}. Confirm it is the EXPOSED cohort "
                                      f"(not all active users) — declare it in field_mapping.json "
                                      f"cohort.denominator_column to make this explicit."})
        elif len(candidates) > 1:
            checks.append({"check": "denominator_column", "status": "ERROR",
                           "message": f"{len(candidates)} columns look like a user count "
                                      f"({[columns[j] for j in candidates]}) — the gate cannot tell "
                                      f"which one is the exposed cohort, and picking the wrong one is "
                                      f"exactly how a numerator (e.g. 付费用户数) gets mistaken for the "
                                      f"sample size. Declare cohort.denominator_column in "
                                      f"field_mapping.json."})
        else:
            checks.append({"check": "denominator_column", "status": "ERROR",
                           "message": f"No user-count denominator column found in {metric_columns}. "
                                      f"A two-proportion z-test needs counts, not a pre-computed rate: "
                                      f"the query must return the exposed-cohort size and the success "
                                      f"count per arm. Re-query with 用户数 alongside 成功数."})

    # ---- 7. sample size (denominator ONLY) + numerator integrity ----------
    MIN_SAMPLE = int(os.environ.get("MIN_SAMPLE", 100))
    denom_by_group = {}
    denom_invalid = []

    if denominator_idx is not None:
        for i, row in enumerate(rows):
            if not isinstance(row, list) or len(row) <= denominator_idx:
                continue
            num = _to_number(row[denominator_idx])
            group = str(row[1]) if len(row) > 1 else f"row{i}"
            if num is None or num < 0:
                denom_invalid.append(f"{group}={row[denominator_idx]!r}")
                continue
            denom_by_group[group] = num

        if denom_invalid:
            checks.append({"check": "denominator_values", "status": "ERROR",
                           "message": f"Denominator column {columns[denominator_idx]!r} has "
                                      f"non-numeric or negative value(s): {denom_invalid}. The exposed "
                                      f"cohort size must be a non-negative number per arm."})
        elif denom_by_group:
            small = {g: int(n) for g, n in denom_by_group.items() if 0 < n < MIN_SAMPLE}
            zero = [g for g, n in denom_by_group.items() if n == 0]
            if zero:
                checks.append({"check": "sample_size", "status": "ERROR",
                               "message": f"Exposed cohort is 0 in {zero} — nothing to compare. "
                                          f"Check the exposure event and the time range."})
            elif small:
                checks.append({"check": "sample_size", "status": "ERROR",
                               "message": f"Exposed cohort below the {MIN_SAMPLE}-user minimum: {small}. "
                                          f"Insufficient for any statistical conclusion — extend the "
                                          f"experiment or widen the time range."})
            else:
                checks.append({"check": "sample_size", "status": "PASS",
                               "message": f"Exposed cohort per arm: "
                                          f"{ {g: int(n) for g, n in denom_by_group.items()} } "
                                          f"— all >= {MIN_SAMPLE}."})

    # numerator ⊆ denominator, and degenerate numerators
    if denominator_idx is not None and denom_by_group:
        for i, row in enumerate(rows):
            if not isinstance(row, list):
                continue
            group = str(row[1]) if len(row) > 1 else f"row{i}"
            denom = denom_by_group.get(group)
            if denom is None:
                continue
            for j, role in roles.items():
                if role not in ("numerator", "unknown"):
                    continue
                if j >= len(row):
                    continue
                col_name = columns[j] if j < len(columns) else f"col_{j}"
                num = _to_number(row[j])
                if num is None:
                    checks.append({"check": f"numerator_value_row{i}_col{j}", "status": "WARN",
                                   "message": f"{col_name} is {row[j]!r} for {group} — treated as "
                                              f"missing. A blank numerator silently becomes 0 conversions "
                                              f"if you coerce it; confirm the event has no data."})
                    continue
                if num < 0:
                    checks.append({"check": f"numerator_negative_row{i}_col{j}", "status": "ERROR",
                                   "message": f"{col_name} is negative ({num}) for {group}."})
                elif num > denom:
                    checks.append({"check": f"numerator_subset_row{i}_col{j}", "status": "ERROR",
                                   "message": f"{col_name} = {int(num)} exceeds the denominator "
                                              f"{columns[denominator_idx]!r} = {int(denom)} for {group}. "
                                              f"The success users are not a subset of the exposed cohort "
                                              f"— the query counts success over ALL users, or without "
                                              f"enforcing exposure-before-success. Use the funnel model "
                                              f"(see references/ae_cli_query_patterns.md Scenario A)."})
        # zero numerator = degenerate variance, not a sample-size problem
        zeros = []
        for j, role in roles.items():
            if role not in ("numerator", "unknown"):
                continue
            col_name = columns[j] if j < len(columns) else f"col_{j}"
            vals = [_to_number(r[j]) for r in rows if isinstance(r, list) and len(r) > j]
            vals = [v for v in vals if v is not None]
            if vals and any(v == 0 for v in vals):
                zeros.append(col_name)
        if zeros:
            checks.append({"check": "degenerate_numerator", "status": "WARN",
                           "message": f"{zeros} are 0 in at least one arm. That is not a sample-size "
                                      f"problem — an arm with zero successes contributes no variance, "
                                      f"so the effect estimate on that arm is degenerate and the "
                                      f"p-value deserves to be read with care. Zeroing a MISSING cell "
                                      f"is also the most common silent data bug: confirm the event "
                                      f"really did not fire inside the experiment window."})

    # ---- 8. aggregate ------------------------------------------------------
    fatals = [c for c in checks if c["status"] == "FATAL"]
    errors = [c for c in checks if c["status"] == "ERROR"]
    empties = [c for c in checks if c["status"] == "EMPTY"]
    warns = [c for c in checks if c["status"] == "WARN"]

    if fatals:
        final_status = "FATAL"
    elif errors:
        final_status = "ERROR"
    elif empties:
        final_status = "EMPTY"
    elif warns:
        final_status = "WARN"
    else:
        final_status = "SUCCESS"

    return {
        "status": final_status,
        "checks": checks,
        # Consumed by the orchestrator when assembling analysis_input.json:
        # group order is NOT guaranteed, so map these labels to control/treatment.
        "detected_groups": detected_groups,
        "metric_columns": metric_columns,
        # The denominator the gate actually used, so the orchestrator assembles
        # control_total/treatment_total from the right column.
        "denominator_column": (columns[denominator_idx]
                               if denominator_idx is not None and denominator_idx < len(columns)
                               else None),
        "cohort_basis": declared_basis or None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"status": "FATAL", "checks": [
            {"check": "usage", "status": "FATAL",
             "message": "Usage: python validate_query_output.py <query_output.json> "
                        "[field_mapping.json]"}
        ]}, ensure_ascii=False, indent=2))
        sys.exit(1)

    result = validate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] in ("FATAL", "ERROR", "EMPTY"):
        sys.exit(1)
    sys.exit(0)
