-- Trino template; see references/sql-design.md for parameters and dependencies.
INSERT INTO {{STATE_TABLE}}
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
)
SELECT user_id,total_amount,event_count,'${bd}'
FROM expected WHERE DATE '${bd}'<CAST(CURRENT_TIMESTAMP AT TIME ZONE '${tag_tz_name}' AS DATE);
