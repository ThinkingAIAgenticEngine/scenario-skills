-- Trino template; see references/sql-design.md for parameters and dependencies.
WITH source_rows AS (
 SELECT {{USER_ID}} AS user_id,{{AMOUNT}} AS amount,
        {{BUSINESS_TIME_EXPR}} AS business_time
 FROM {{EVENT_TABLE}}
 WHERE {{PART_DATE}} BETWEEN '{{HISTORY_PART_START}}'
       AND CAST(date_add('day',{{SCAN_FORWARD_DAYS}},DATE '${bd}') AS VARCHAR)
 AND {{EVENT_NAME}} IN ({{TARGET_EVENT_LITERALS}})
), expected AS (
 SELECT user_id,SUM(amount) AS total_amount,COUNT(*) AS event_count
 FROM source_rows
 WHERE business_time>=TIMESTAMP '{{HISTORY_START_TS}}'
 AND business_time<CAST(date_add('day',1,DATE '${bd}') AS TIMESTAMP)
 GROUP BY 1
), actual AS (
 SELECT user_id,total_amount,event_count FROM {{STATE_TABLE}} WHERE stat_date='${bd}'
)
SELECT COUNT(e.user_id) AS expected_users,COUNT(a.user_id) AS actual_users,
 (SELECT COUNT(*)-COUNT(DISTINCT user_id) FROM actual) AS duplicate_users,
 COALESCE(COUNT_IF(e.user_id IS NULL),0) AS extra_users,
 COALESCE(COUNT_IF(a.user_id IS NULL),0) AS missing_users,
 COALESCE(COUNT_IF(e.total_amount IS DISTINCT FROM a.total_amount),0) AS amount_differences,
 COALESCE(COUNT_IF(e.event_count IS DISTINCT FROM a.event_count),0) AS count_differences,
 SUM(e.total_amount) AS expected_amount,SUM(a.total_amount) AS actual_amount
FROM expected e FULL OUTER JOIN actual a ON e.user_id=a.user_id LIMIT 1;
