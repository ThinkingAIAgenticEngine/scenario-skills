# Optional AE/TE Adapter

Read this file only when the user explicitly requests AE/TE data access or write-back. The matching algorithm and evidence contract remain platform-independent.

## Safety and Routing

1. Use the installed AE analysis capability and its current command schema; do not rely on remembered CLI flags.
2. Check authentication and list accessible projects before selecting data.
3. Reuse an explicitly named project. If the name is ambiguous, show matching projects and ask the user to select one.
4. Resolve real events, properties, entities, timezones, and identity fields from project metadata. Never invent names.
5. Prefer existing saved reports or analysis assets when they reproduce the required user-level fields. Use ad-hoc analysis only when needed.
6. Keep all discovery and extraction read-only.

If authentication is unavailable, stop AE/TE access and offer the platform-independent CSV route. Never request, print, or store an authentication token.

## Extraction Contract

Before running a query, show a compact mapping:

| PSM concept | Resolved AE/TE source |
|---|---|
| Eligible user | Entity and inclusion rule |
| Treatment | Event or property and binary rule |
| Index time | Event time or shared intervention time |
| Covariates | Pre-period events, properties, and aggregations |
| Outcome | Post-period event or property and aggregation |
| Timezone | Project timezone used for every boundary |

Require approval if this mapping materially changes the user's stated population or outcome.

Build one row per user and conform to `data-contract.md`. For large results, use the current AE/TE export path instead of assuming the first response page is complete. Verify:

- exported rows equal the expected result rows;
- unique users equal exported rows;
- both treatment values are present;
- covariate and outcome windows do not overlap;
- the timezone is preserved;
- the export can be parsed as UTF-8 CSV.

Record the project identifier, query or asset identifier, execution request identifier when available, extraction time, and user count in the analysis log so the result can be reproduced.

## Output Interpretation

AE/TE is the data source, not the matching engine. Run `scripts/psm.py` on the extracted user-level dataset and apply the same validation gates used for every other source. Do not weaken overlap or balance thresholds because the source is AE/TE.

## Optional Write-Back

Write-back is a separate, state-changing action. Perform it only after the user explicitly requests it and confirms:

- project and destination asset type;
- asset name and description;
- input identifier field and matched-user count;
- create versus overwrite behavior;
- permission and rollback expectations.

Show a preview first. If the platform cannot reproduce or import the exact externally matched users, preserve `matched_pairs.csv` and `scored_users.csv` and state that write-back was not performed.
