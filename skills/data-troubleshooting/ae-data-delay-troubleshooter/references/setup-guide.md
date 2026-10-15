# Minimal setup

Requirements:

- Python 3.10 or later;
- `ae-cli` available on `PATH`;
- an authenticated AE session.

Verify once:

```bash
python3 --version
ae-cli --version
ae-cli auth status
python3 scripts/check_ingestion_delay.py --help
python3 scripts/render_report.py --self-test
python3 scripts/validate_output.py --self-test
```

If authentication is missing, run `ae-cli auth login`. The diagnosis skill has no publishing dependency and does not manage credentials.
