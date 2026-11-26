-- Trino template; see references/sql-design.md for parameters and dependencies.
CREATE TABLE {{STATE_TABLE}} (
 user_id {{USER_ID_TYPE}}, total_amount {{AMOUNT_TYPE}},
 event_count BIGINT, stat_date VARCHAR
) WITH (format='ORC',partitioned_by=ARRAY['stat_date']);
