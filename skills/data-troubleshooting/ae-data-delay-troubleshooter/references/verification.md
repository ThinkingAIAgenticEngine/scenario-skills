# Release verification — 2.8.1

Before publishing, verify:

- frontmatter version is `2.8.1`;
- the release archive contains `SKILL.md` and only the allowed `scripts`, `references`, and optional `assets` directories at its root; local `tests` and `agents` directories are excluded;
- no operating-system metadata, platform-specific local path, environment checker, duplicate dependency manifest, or publishing workflow remains;
- the required user-confirmed threshold changes SQL, report labels, and chart labels;
- SQL normalizes event time from `#zone_offset` to the server offset before upload and end-to-end subtraction;
- the server offset is required and the checker never substitutes UTC+8 or another unconfirmed value;
- null offsets are excluded by default and included only with `--missing-zone-offset`;
- `$part_date` appears in every query, while `$part_event` appears only for event-scoped queries;
- `--output` uses an atomic replace and no documentation recommends `>` for canonical JSON;
- a completed measurement exits 0 even when delayed rows exist;
- the checker emits JSON only and the human-readable report has a single implementation in `render_report.py`;
- `validate_output.py` independently validates the canonical result before rendering and validates the report, summary, and chart before delivery;
- only the current 45-column warehouse measurement schema is accepted;
- `--days` is anchored to an explicit `--end-date`, when provided;
- formal Markdown and YAML files satisfy the publication language-ratio policy;
- Python compilation, renderer and validator self-tests, CLI help, SQL assertions, atomic-output tests, and the local development test suite pass before creating the staged archive.
