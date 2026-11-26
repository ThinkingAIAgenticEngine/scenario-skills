-- Trino template; see references/sql-design.md for parameters and dependencies.
WITH source_rows AS (
 SELECT {{USER_ID}} AS user_id,{{AMOUNT}} AS amount,
        {{BUSINESS_TIME_EXPR}} AS business_time
 FROM {{EVENT_TABLE}}
 WHERE {{PART_DATE}} BETWEEN
       CAST(date_add('day',-{{SCAN_BACK_DAYS}},DATE '${bd}') AS VARCHAR)
       AND CAST(date_add('day',{{SCAN_FORWARD_DAYS}},DATE '${bd}') AS VARCHAR)
 AND {{EVENT_NAME}} IN ({{TARGET_EVENT_LITERALS}})
), expected_daily AS (
 SELECT user_id,SUM(amount) AS daily_amount,COUNT(*) AS event_count
 FROM source_rows
 WHERE business_time>=CAST(DATE '${bd}' AS TIMESTAMP)
 AND business_time<CAST(date_add('day',1,DATE '${bd}') AS TIMESTAMP)
 GROUP BY 1
), actual AS (
 SELECT user_id,daily_amount,event_count FROM {{DAILY_TABLE}} WHERE stat_date='${bd}'
)
SELECT 1/IF(DATE '${bd}'<CAST(CURRENT_TIMESTAMP AT TIME ZONE '${tag_tz_name}' AS DATE)
 AND (SELECT COUNT(*)=COUNT(DISTINCT user_id)
      AND COALESCE(COUNT_IF(user_id IS NULL),0)=0
      AND COALESCE(COUNT_IF(event_count<=0 OR event_count IS NULL),0)=0 FROM actual)
 AND COALESCE(COUNT_IF(e.user_id IS NULL OR a.user_id IS NULL
     OR e.daily_amount IS DISTINCT FROM a.daily_amount
     OR e.event_count IS DISTINCT FROM a.event_count),0)=0,1,0) AS valid_daily
FROM expected_daily e FULL OUTER JOIN actual a ON e.user_id=a.user_id LIMIT 1;
