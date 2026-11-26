-- Trino template; see references/sql-design.md for parameters and dependencies.
INSERT INTO {{STATE_TABLE}}
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
)
SELECT user_id,total_amount,event_count,'${bd}'
FROM expected WHERE DATE '${bd}'<CAST(CURRENT_TIMESTAMP AT TIME ZONE '${tag_tz_name}' AS DATE);
