#!/usr/bin/env python3
"""Generate and validate a deterministic synthetic PSM fixture."""

import csv
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path


SEED = 275
USER_COUNT = 800
INJECTED_ATT = 8.0


def sigmoid(value):
    return 1.0 / (1.0 + math.exp(-value))


def generate_fixture(path):
    rng = random.Random(SEED)
    rows = []
    for index in range(USER_COUNT):
        level = max(1.0, rng.gauss(30.0, 8.0))
        login_days = min(7.0, max(0.0, rng.gauss(4.0, 1.6)))
        pre_pay = max(0.0, rng.gauss(12.0 + 0.25 * level, 8.0))
        vip = 1.0 if rng.random() < sigmoid(-2.4 + 0.035 * level + 0.018 * pre_pay) else 0.0
        prior_campaigns = float(min(5, int(rng.expovariate(0.8))))
        treatment_probability = sigmoid(
            -2.55
            + 0.030 * level
            + 0.140 * login_days
            + 0.350 * vip
            + 0.130 * prior_campaigns
        )
        treatment = 1 if rng.random() < treatment_probability else 0
        baseline = 6.0 + 0.28 * level + 0.90 * login_days + 0.24 * pre_pay + 1.8 * vip
        outcome = baseline + INJECTED_ATT * treatment + rng.gauss(0.0, 4.0)
        rows.append(
            [
                f"fixture-user-{index + 1:04d}",
                treatment,
                f"{level:.8f}",
                f"{login_days:.8f}",
                f"{pre_pay:.8f}",
                f"{vip:.0f}",
                f"{prior_campaigns:.0f}",
                f"{outcome:.8f}",
            ]
        )
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "user_id",
                "treatment",
                "level",
                "login_days",
                "pre_pay",
                "vip",
                "prior_campaigns",
                "revenue_7d",
            ]
        )
        writer.writerows(rows)


def main():
    script_dir = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="psm-fixture-") as temporary:
        root = Path(temporary)
        input_path = root / "fixture.csv"
        output_dir = root / "output"
        generate_fixture(input_path)
        command = [
            sys.executable,
            str(script_dir / "psm.py"),
            "--input",
            str(input_path),
            "--id-col",
            "user_id",
            "--treatment-col",
            "treatment",
            "--outcome-col",
            "revenue_7d",
            "--covariates",
            "level,login_days,pre_pay,vip,prior_campaigns",
            "--output-dir",
            str(output_dir),
            "--ratio",
            "1",
            "--caliper",
            "0.2",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
        match_rate = report["matching"]["treated_match_rate"]
        max_smd = report["quality"]["max_abs_smd_after"]
        estimated_att = report["effect"]["att"]
        if not report["model"]["converged"]:
            raise AssertionError("fixture model did not converge")
        if match_rate < 0.70:
            raise AssertionError(f"fixture match rate failed: {match_rate:.4f}")
        if max_smd >= 0.10:
            raise AssertionError(f"fixture balance failed: {max_smd:.4f}")
        if abs(estimated_att - INJECTED_ATT) > 2.0:
            raise AssertionError(
                f"fixture ATT {estimated_att:.4f} is too far from injected {INJECTED_ATT:.1f}"
            )

        replacement_dir = root / "replacement-output"
        replacement_command = list(command)
        replacement_command[replacement_command.index("--output-dir") + 1] = str(replacement_dir)
        replacement_command.append("--with-replacement")
        subprocess.run(replacement_command, check=True, capture_output=True, text=True)
        replacement_report = json.loads(
            (replacement_dir / "report.json").read_text(encoding="utf-8")
        )
        if replacement_report["effect"]["ci95_approx"] is not None:
            raise AssertionError("with-replacement confidence interval must be suppressed")
        if not replacement_report["effect"]["uncertainty_note"]:
            raise AssertionError("with-replacement uncertainty note is required")

        missing_path = root / "fixture-high-missingness.csv"
        with open(input_path, newline="", encoding="utf-8") as handle:
            fixture_rows = list(csv.DictReader(handle))
        for row in fixture_rows[:81]:
            row["level"] = ""
        with open(missing_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fixture_rows[0]))
            writer.writeheader()
            writer.writerows(fixture_rows)
        missing_command = list(command)
        missing_command[missing_command.index("--input") + 1] = str(missing_path)
        missing_command[missing_command.index("--output-dir") + 1] = str(root / "missing-output")
        missing_result = subprocess.run(missing_command, capture_output=True, text=True)
        if missing_result.returncode == 0 or "missing-or-invalid rate exceeds" not in missing_result.stderr:
            raise AssertionError("high covariate missingness was not rejected")

        nonconvergent_command = list(command)
        nonconvergent_command[nonconvergent_command.index("--output-dir") + 1] = str(
            root / "nonconvergent-output"
        )
        nonconvergent_command.extend(["--max-iterations", "1"])
        nonconvergent_result = subprocess.run(
            nonconvergent_command, capture_output=True, text=True
        )
        if nonconvergent_result.returncode == 0 or "did not converge" not in nonconvergent_result.stderr:
            raise AssertionError("non-convergent propensity model was not rejected")

        print(
            json.dumps(
                {
                    "seed": SEED,
                    "users": USER_COUNT,
                    "treated": report["input"]["treated"],
                    "controls": report["input"]["control"],
                    "model_converged": report["model"]["converged"],
                    "match_rate": match_rate,
                    "max_abs_smd_after": max_smd,
                    "estimated_att": estimated_att,
                    "injected_att": INJECTED_ATT,
                    "ci95_approx": report["effect"]["ci95_approx"],
                    "replacement_ci_suppressed": True,
                    "missingness_gate_verified": True,
                    "nonconvergence_gate_verified": True,
                    "status": "PASS",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
