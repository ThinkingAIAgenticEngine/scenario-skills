-- Trino template; see references/sql-design.md for parameters and dependencies.
CREATE TABLE {{DAILY_TABLE}} (
 user_id {{USER_ID_TYPE}}, daily_amount {{AMOUNT_TYPE}},
 event_count BIGINT, stat_date VARCHAR
) WITH (format='ORC',partitioned_by=ARRAY['stat_date']);
