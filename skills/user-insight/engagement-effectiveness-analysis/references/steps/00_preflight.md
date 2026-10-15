# Step 0: Pre-flight, Mode Detection, Parameters

## Goal

Establish that the machine can actually run the skill, decide whether this campaign
is mode A (native ThinkingData Engage) or mode B (third-party / self-built send),
and freeze the parameters every later step depends on.

Do not skip this step to "save time". Both groups of checks exist because their
failure modes used to surface only *after* the data had already been fetched, which
wastes a full retrieval cycle and produces a misleading error.

## Input

- `project_id` (required)
- Either a native object id (`task_id` / `flow_id` / `config_id`) **or** the
  campaign's recovery event names
- Optional: `click_event`, `anchor_event`, `conversion_event`, time window

## Output

- `tmp/prereq.json` — 10-check gate result, including `context.resolved_python`
- `tmp/mode.json` — resolved mode plus the evidence used to resolve it
- `tmp/params.json` — frozen parameter set for Steps 1-5

## Executor

Orchestrator running scripts. No sub-agent at this step.

## Validation Gate

Three scripts, all must exit 0. Any exit 1 is **FATAL** — stop and report the
failing check rather than continuing.

## Flow

### Sub-step 0.1 — Resolve the interpreter and run the pre-flight gate

A running script cannot switch its own interpreter, so `PY` has to be resolved
**before** any other script is invoked.

```bash
PY=python3; S=<skill_dir>

$PY $S/scripts/check_prerequisites.py --project-id <PID> --workspace <WD> \
      --out tmp/prereq.json
```

Then read `context.resolved_python` from the printed envelope, or from
`tmp/prereq.json`, and use **that** path as `PY` for every later step.

**Decision based on exit code:**

- **IF exit 0** → re-assign `PY` from `context.resolved_python`, proceed to 0.2.
- **IF exit 1** → read the failing check name from the output and report it:

  | Failing check | Meaning | Remedy |
  |---|---|---|
  | `python_version` | interpreter older than 3.8 | install python 3.8+ |
  | `ae_cli_binary` | no ae-cli on `PATH` | install `@thinkingai/ae-cli`, or set `AE_CLI_PATH` |
  | `ae_cli_compat` | binary drives neither 1.x nor 6.x tree | install a compatible build; the check names one when present |
  | `ae_cli_auth` | not logged in, or no active host | `ae-cli --host <url> auth login` |
  | `openpyxl` | no interpreter can import it and bootstrap is forbidden | re-run without `--no-install` |
  | `project_visible` | target id absent from the active host | check `project_id`, or switch host with `ae-cli config` |
  | `credential_store` | store not writable, or holds no credential for this host | fix ownership, or log in to this host |
  | `output_writable` | `tmp/` / `output/` not creatable under `--workspace` | run from a writable directory or pass `--workspace` |

  Return **FATAL**.

`ae_cli_roundtrip` and `network_reachable` are **ERROR**, not FATAL: they are
advisory probes and a transient network blip should not abort a run that may still
succeed.

`openpyxl` is needed by Step 4 only, and this gate bootstraps it into a private
virtualenv under the user cache directory when no interpreter has it. Pass
`--no-install` to forbid that and receive a plain install command instead.

### Sub-step 0.2 — Resolve the mode

```bash
$PY $S/scripts/detect_mode.py --project-id <PID> \
      [--task-id <TID> | --flow-id <FID> | --config-id <CID>] \
      [--anchor-event <E>] [--click-event <E>] --out tmp/mode.json
```

**Decision based on `mode.json`:**

- **IF `mode = "A"`** → an engagement object id resolved on the platform. Proceed
  to Step 1a (`steps/01_intake.md`).
- **IF `mode = "B"`** → no object id, or the id is not visible on this host. Proceed
  to Step 1b (same file).
- **IF mode cannot be resolved** → **FATAL**. Ask the user for the object id or for
  the recovery event names; do not guess a mode.

### Sub-step 0.3 — Freeze and validate the parameters

```bash
$PY $S/scripts/validate_params.py --project-id <PID> --mode <A|B> \
      [--task-id <TID>] [--click-event <E>] --start-time <S> --end-time <E> \
      --strategy-name "<name>" --out tmp/params.json
```

**Decision based on exit code:**

- **IF exit 0** → parameters frozen. Proceed to Step 1.
- **IF exit 1** → **FATAL**. The window is invalid (inverted, too short, or outside
  retention) or `strategy_name` is missing. Report the specific field.

The minimum viable window is **3 days**; a shorter window cannot support a
day-by-day trend and the run is refused rather than silently degraded.

---

**After completion, proceed to Step 1 (`steps/01_intake.md`).**

## Error Handling Summary

| Scenario | Action | Status |
|---|---|---|
| `check_prerequisites.py` exit 0 | Continue, adopt `resolved_python` as `PY` | SUCCESS |
| `check_prerequisites.py` exit 1 | Report the named check and its remedy, stop | FATAL |
| `ae_cli_roundtrip` or `network_reachable` fails | Report as a warning, continue | WARN |
| `detect_mode.py` cannot resolve a mode | Ask the user, stop | FATAL |
| `validate_params.py` exit 1 | Report the offending field, stop | FATAL |
| Window shorter than 3 days | Refuse the run | FATAL |

## Notes

- Checks fall into two groups on purpose: **remote authority + interpreter** and
  **local permissions**. A read-only credential store produces a 401 partway
  through a long run, so it is checked up front.
- ae-cli stores one credential per host under
  `<home>/.ae-cli/secure-tokens/<host>.enc.json`, with the port separator rewritten
  as `_`. `auth status` only speaks for the *active* host, which is why a project on
  a host this machine never logged into passes auth and then fails at fetch time.
- Discovery prefers the 6.x tree. A version *string* is not evidence of
  compatibility — the command tree is.
- `selftest_gates.py` tests this gate itself against fixtures; run it after editing
  any gate script.
