# Step 0 - Pre-flight Check

> Procedure file for **Step 0** in `SKILL.md`.
> Deep command-level runbook with expected output: `references/steps.md`, section "Step 0".

## Goal

Prove the environment can run the pipeline **before** any query is sent: `ae-cli` is installed and
signed in, the parameter set is complete, and an interpreter with `scipy` is available (or the
normal-approximation fallback is knowingly accepted).

## Input

| Source | Content |
|--------|---------|
| Command line | No positional arguments; both scripts of this step are self-checking entry points |
| User | `project_id`, `variant_property`, `success_events`, `time_range`, and optionally `guardrail_events`, `filters` |
| Environment | `ae-cli` present on `PATH` and signed in; Python >= 3.9 |

This step reads no intermediate artifact. `{ws}/tmp/` may not exist yet.

## Output

- stdout: `check_prerequisites.py` prints `{"status": ..., "checks": [...]}`
- stdout: `validate_params.py` prints a result of the same shape
- Side effect: `scripts/.resolved_python` - the path of an interpreter that can import `scipy`,
  written for the later steps to reuse

## Executor

Orchestrator. Run the two scripts directly; no sub-agent is involved.

## Validation Gate

```bash
python scripts/check_prerequisites.py

python scripts/validate_params.py \
  --project-id {project_id} \
  --variant-property {variant_property} \
  --success-events {success_events} \
  --time-range {time_range} \
  [--guardrail-events {guardrail_events}] \
  [--filters {filters}]
```

Both commands must exit `0`. `SUCCESS` and `WARN` both exit `0`; only `FATAL` exits `1`.

## Failure Handling

| Situation | Status | Action |
|-----------|--------|--------|
| `ae-cli` missing or not signed in | FATAL | Stop. Give the sign-in command; restart from this step once the user has finished |
| A required parameter is missing | FATAL | Stop. Ask **only for the missing items**; never re-ask for what was already supplied |
| `scipy` missing | WARN | The script installs it into a private venv automatically; if that fails, record the degradation to the normal approximation |
| Python version < 3.9 | FATAL | Stop and state the version requirement |
| The script itself raises (non-zero exit plus traceback) | FATAL | Stop and hand the traceback to the user verbatim; do not modify the environment on your own |

## Flow

1. Check sign-in first: `IF ae-cli is ready -> continue; ELSE -> FATAL, stop` (nothing downstream can
   work without it).
2. Check parameters: `IF all 6 items are present -> continue; ELSE -> FATAL and ask for the missing ones`.
3. Resolve the interpreter: `IF scipy is importable -> continue; ELSE -> create the private venv and install`.
4. Record `scripts/.resolved_python` so the Step 2 engine can reuse it.
5. `IF both gates exit 0 -> proceed to Step 0b`; `IF either exits 1 -> stop this run` and report every
   `checks[]` entry whose `status` is `FATAL`.

## Error Handling Summary

| Gate | Exit code | Status | May we continue? |
|------|-----------|--------|------------------|
| `check_prerequisites.py` | `0` | SUCCESS / WARN | Yes (a WARN must be relayed to the user) |
| `check_prerequisites.py` | `1` | FATAL | No |
| `validate_params.py` | `0` | SUCCESS | Yes |
| `validate_params.py` | `1` | FATAL | No |

## Notes

- This step does **not** verify field existence. That is Step 0b's job. Here we only prove that the
  environment runs and that no parameter is missing.
- The private venv's cache root can be pinned at run time with the `CACHE_DIR` environment variable.
  With no override a per-user temporary directory is used, which the OS may reclaim; the venv is then
  rebuilt on the next run.
- Never install dependencies into the global interpreter. It pollutes the user's environment and makes
  `.resolved_python` meaningless.
