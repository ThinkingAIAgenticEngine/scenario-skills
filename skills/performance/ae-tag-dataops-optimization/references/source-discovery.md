# Source and Dependency Discovery

## Step 1: Establish scope and platform boundaries

Apply the [scope check](../SKILL.md#scope) first. A confirmed cross-source tag or actual input ends this workflow with the prescribed scope response.

| Object | Authoritative location | Evidence |
|---|---|---|
| Original tag and input assets | Original analysis project | Type, ID, saved definition, joins, and date/version semantics |
| Events and properties | Analysis metadata | Machine names, conditions, expressions, and types |
| Source tables and fields | Project SQL catalog and query context | Exact SQL reference, usage, and source mapping |
| Output tables and workflows | Target DataOps space | Environment, partitions, release, and execution status |

Use analysis-platform evidence for original semantics and sources. Use the DataOps catalog to manage processing targets, not to guess source events or definitions.

## Step 2: Resolve actual inputs

1. Read the original tag's type, saved SQL or model, date parameters, time zones, and subject.
2. Follow actual references through tags, cohorts, composite events, virtual events, and properties. Preserve conditions, join keys, versions, and refresh semantics. Track inspected IDs to handle repeated references.
3. In the same analysis project, verify source event/property machine names, types, composition rules, and virtual expressions.
4. Reuse a verified table reference only for the same project and purpose. Otherwise inspect the project's SQL catalog and columns and save the exact returned reference and catalog context.
5. Run a bounded, read-only DataOps check against that identified source. Verify connection mapping, types, and permission. If the two platforms expose different references, translate through a verified mapping and record both sides.

A catalog containing cross-source resources does not prove the tag uses them. Actual SQL and references establish use. Stop once a cross-source input is confirmed.

## Step 3: Use the project SQL catalog

Read `ae-analysis` instructions and current CLI help before calling commands. The catalog pattern is:

```sh
ae-cli analysis sql-table list --project-id <project-id> --usage tag_cluster

ae-cli analysis sql-table columns --project-id <project-id> \
  --table-ref '<exact-reference-returned-by-catalog>' --usage tag_cluster
```

Use `tag_cluster` for tag/cohort SQL; choose other usage contexts from the capability contract. Keep table and column discovery in the same usage context. Copy the returned `sql_reference`, handle server pagination, and verify current-account readability of references from saved SQL.

Event/property metadata explains meaning; the SQL catalog establishes table and field references. Both are needed.

## Step 4: Recover missing access or definitions

If APIs are unsupported or persistently fail after diagnosis, inspect the tag, metadata, or SQL page in the same original analysis project. Follow [setup and troubleshooting](setup-and-troubleshooting.md) for authentication and access. If DataOps cannot read an established source, check its connection, mapping, and permissions.

Ask the user only for a critical definition unavailable through both API and analysis-project page. Continue independent work meanwhile. Before binding `{{EVENT_TABLE}}`, save source, field, and DataOps-readability evidence. Summarize the source-to-output relationship in the customer document and keep detailed mappings in execution records.
