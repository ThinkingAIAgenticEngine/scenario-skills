-- Trino template; see references/sql-design.md for parameters and dependencies.
WITH previous AS (
 SELECT user_id,total_amount,event_count FROM {{STATE_TABLE}}
 WHERE stat_date=CAST(date_add('day',-1,DATE '${bd}') AS VARCHAR)
), daily AS (
 SELECT user_id,daily_amount,event_count FROM {{DAILY_TABLE}}
 WHERE stat_date='${bd}'
), expected AS (
 SELECT COALESCE(p.user_id,d.user_id) AS user_id,
 CASE WHEN p.total_amount IS NULL AND d.daily_amount IS NULL THEN NULL
 ELSE COALESCE(p.total_amount,0)+COALESCE(d.daily_amount,0) END AS total_amount,
 COALESCE(p.event_count,0)+COALESCE(d.event_count,0) AS event_count
 FROM previous p FULL OUTER JOIN daily d ON p.user_id=d.user_id
), actual AS (
 SELECT user_id,total_amount,event_count FROM {{STATE_TABLE}} WHERE stat_date='${bd}'
)
SELECT 1/IF(DATE '${bd}'<CAST(CURRENT_TIMESTAMP AT TIME ZONE '${tag_tz_name}' AS DATE)
 AND (SELECT COUNT(*)>0 AND COUNT(*)=COUNT(DISTINCT user_id)
      AND COALESCE(COUNT_IF(user_id IS NULL),0)=0 FROM actual)
 AND COALESCE(COUNT_IF(e.user_id IS NULL OR a.user_id IS NULL
     OR e.total_amount IS DISTINCT FROM a.total_amount
     OR e.event_count IS DISTINCT FROM a.event_count),0)=0,1,0) AS valid_cumulative
FROM expected e FULL OUTER JOIN actual a ON e.user_id=a.user_id LIMIT 1;
