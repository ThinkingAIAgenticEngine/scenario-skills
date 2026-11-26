-- Trino template; see references/sql-design.md for parameters and dependencies.
-- Add native parameter date1 in the UI, choose Yesterday, and save a single target-day range.
-- Verify time-field projections against the target parameter contract and actual preview.
SELECT s.user_id,s.total_amount
FROM (
 SELECT user_id,total_amount,stat_date AS "$part_date",
        CAST(stat_date AS TIMESTAMP) AS "@vpc_tz_#event_time"
 FROM {{STATE_TABLE}}
) s
WHERE ${PartDate:date1};
