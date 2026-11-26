-- Trino template; see references/sql-design.md for parameters and dependencies.
-- Run after date, daily, and prior-state gates; initialization also requires the completed-date gate.
DELETE FROM {{STATE_TABLE}} WHERE stat_date='${bd}';
