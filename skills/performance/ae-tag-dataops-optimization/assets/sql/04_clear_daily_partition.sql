-- Trino template; see references/sql-design.md for parameters and dependencies.
-- After the 03 date check succeeds, run as the pre-statement of the 05 daily-statistics node.
DELETE FROM {{DAILY_TABLE}} WHERE stat_date='${bd}';
