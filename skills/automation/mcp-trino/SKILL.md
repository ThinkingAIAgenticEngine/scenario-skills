---
name: mcp-trino
description: Inspect Trino metadata, table schemas, query plans, EXPLAIN ANALYZE output, and existing query records through the mcp-trino MCP tools. Use when Codex needs to navigate Trino catalogs or schemas, inspect a table before writing or reviewing SQL, analyze a query plan, diagnose a Trino query ID from query-info, or explain the inspection-only limits and query visibility behavior of mcp-trino.
---

# mcp-trino

Use the mcp-trino tools as an inspection surface for Trino. Prefer returned
Trino metadata, plan text, and query-info payloads over generic assumptions.

## Workflow

1. Start from the user's artifact.
   - For a table name or data-location question, discover metadata first.
   - For SQL text, inspect the plan before claiming runtime behavior.
   - For a query ID, inspect the saved query record before rerunning anything.
2. Navigate data with `list_catalogs`, `list_schemas`, and `list_tables`.
3. Inspect table shape with `get_table_schema`. Use `execute_query` with
   `SHOW CREATE`, `SHOW`, `DESCRIBE`, or `DESC` when the helper tools do not
   expose the needed inspection result.
4. Analyze SQL with `explain_query`.
   - Default to plain `EXPLAIN` for static plan questions.
   - Use `type` for `LOGICAL`, `DISTRIBUTED`, `VALIDATE`, or `IO` plan types.
   - Use `format` for `TEXT`, `GRAPHVIZ`, or `JSON` plan output formats.
   - Use `structured: true` with plain `EXPLAIN` when the JSON plan is needed;
     this maps to Trino's `FORMAT JSON`.
   - Use `analyze: true` only when executing the query is acceptable and
     runtime evidence is needed.
   - Add `structured: true` with `analyze: true` when selected runtime
     query-info fields are needed alongside the plan text.
   - If the plan response is paged, continue with `offset: nextOffset` and a
     bounded `limit`; do not ask for an unbounded full plan.
5. Diagnose an existing query ID from query-info.
   - Use `list_query_history` to find recently retained completed, failed, or
     canceled queries; and it is
     coordinator retention, not an audit log.
   - Use `get_query_by_id` when only the recorded SQL text is needed.
   - Use `get_query_detail` when query state, runtime stats, stages, warnings,
     failure details, or session fields matter.
   - For large query-info payloads, read them page by page with `offset` and
     `limit`, or search the returned page for the specific field first.
   - Preserve the distinction between saved runtime evidence and a new
     controlled repro.

## Tool Choice

| Need                                            | Tool                 |
| ----------------------------------------------- | -------------------- |
| Visible catalogs                                | `list_catalogs`      |
| Schemas in a catalog                            | `list_schemas`       |
| Tables and views in a schema                    | `list_tables`        |
| Columns and types                               | `get_table_schema`   |
| `SHOW`, `SHOW CREATE`, or `DESCRIBE` inspection | `execute_query`      |
| Static or runtime plan inspection               | `explain_query`      |
| Recently retained query history                 | `list_query_history` |
| Recorded SQL for a query ID                     | `get_query_by_id`    |
| Raw query-info for a query ID                   | `get_query_detail`   |

## Guardrails

- Treat `execute_query` as inspection-only. It accepts `EXPLAIN`,
  `EXPLAIN ANALYZE`, `SHOW`, `SHOW CREATE`, `DESCRIBE`, and `DESC`; do not try
  general `SELECT`, DML, DDL, or multi-statement SQL through it.
- State whether a conclusion comes from static `EXPLAIN`, runtime
  `EXPLAIN ANALYZE`, or saved query-info.
- Prefer the original query-info record for postmortems when it is available.
  If it is missing or no longer retained, say that before falling back to a
  new `EXPLAIN ANALYZE`.
- Treat `list_query_history` as a recent coordinator-retention view. Do not
  present it as complete historical auditing.
- Remember that `EXPLAIN ANALYZE` executes the supplied query in Trino.
- Query-info tools read `/v1/query/{queryId}` with the configured Trino
  connection identity. Trino authentication and query visibility rules must
  allow that identity to read the query. Do not assume the MCP caller token is
  forwarded to Trino; per-caller visibility requires Trino impersonation and a
  matching Trino access policy.

## Response Shape

- Ground the answer in the artifact the tools returned: table metadata, plan
  text, or query-info fields.
- Call out missing query records, authorization failures, and static-only
  reasoning explicitly.
- Keep SQL rewrites separate from evidence about what Trino already executed.
