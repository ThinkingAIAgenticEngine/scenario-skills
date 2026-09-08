# Feishu Sheet Contract

Read this reference when resolving and normalizing the source spreadsheet.

## Required Logical Fields

| Logical field | Default header | Requirement |
|---|---|---|
| Account | `account` | Non-empty AE/TE-supported unique login identifier |
| Platform | `platform` | Non-empty exact event-property value; preserve case and text |
| Data permission | `data_permission` | Non-empty project-scoped permission display name |

Different headers are allowed only after an explicit mapping is recorded. Do not infer a column from its position alone.

## Snapshot Evidence

Record:

- Feishu file token or URL.
- Worksheet ID and title.
- Exact range.
- Read timestamp and acting identity when available.
- Raw row count, normalized row count, and ignored blank-tail count.
- SHA-256 hash of the normalized CSV bytes.

The normalized CSV must use UTF-8, a header row, Unix newlines, and rows sorted by account, data permission, and platform before hashing.

## Normalization Rules

- Trim surrounding whitespace from account and data-permission names.
- Preserve the exact platform value after removing only accidental surrounding whitespace.
- Preserve account case unless the AE/TE identity API explicitly returns a canonical case-insensitive identifier. Record both source and canonical forms when they differ.
- Ignore completely blank trailing rows.
- Do not evaluate a displayed formula as permission data unless the spreadsheet API returns its resolved cell value.
- Do not silently exclude hidden or filtered rows. The exact source range controls inclusion.
- Collapse byte-identical duplicate rows and report their source row numbers.

## Conflict Rules

Block planning when:

- Any required logical field is empty.
- One data-permission name maps to multiple platform values.
- The same account and data-permission name map to multiple platform values.
- One account identifier resolves to multiple AE/TE users.
- A source account is not a valid candidate for the target project.
- The same account has incompatible instructions after normalization.

Multiple rows for one account are otherwise valid and mean that the account requires the union of the listed data permissions.

## Unknown Platform Values

Compare each exact source platform value with live candidates from the target project.

- Known value: continue.
- Unknown value: mark `BLOCKED_UNKNOWN_PLATFORM` and show similar candidates only as suggestions.
- Explicit override: allowed only after the user approves the exact original value in a later message. Record the override in the plan.

Never automatically replace an unknown value with a similar candidate.

## Sensitive Data

Use account identifiers only for resolution, planning, and source-aligned results. Do not return unrelated project members or copy the full member directory into artifacts. Never store authentication credentials in the normalized CSV.
