-- Trino template; see references/sql-design.md for parameters and dependencies.
SELECT 1/IF(DATE '${bd}'<CAST(CURRENT_TIMESTAMP AT TIME ZONE '${tag_tz_name}' AS DATE),1,0) AS valid_business_date LIMIT 1;
