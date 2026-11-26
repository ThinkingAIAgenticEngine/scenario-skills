-- Trino template; see references/sql-design.md for parameters and dependencies.
WITH accepted AS (
 SELECT COUNT(*) AS receipt_count, MAX(user_count) AS user_count
 FROM {{ACCEPTANCE_TABLE}}
 WHERE stat_date=CAST(date_add('day',-1,DATE '${bd}') AS VARCHAR)
)
SELECT 1/IF(DATE '${bd}'<CAST(CURRENT_TIMESTAMP AT TIME ZONE '${tag_tz_name}' AS DATE)
 AND COUNT(*)>0 AND COUNT(*)=COUNT(DISTINCT user_id)
 AND (SELECT receipt_count=1 AND user_count IS NOT NULL FROM accepted)
 AND COUNT(*)=(SELECT user_count FROM accepted)
 AND COALESCE(COUNT_IF(user_id IS NULL),0)=0
 AND COALESCE(COUNT_IF(event_count<=0 OR event_count IS NULL),0)=0,1,0) AS valid_previous
FROM {{STATE_TABLE}}
WHERE stat_date=CAST(date_add('day',-1,DATE '${bd}') AS VARCHAR) LIMIT 1;
