---
name: generate-sql
description: Write Trino SQL statements based on requirements and system data specifications. Triggered only under the following conditions >> 1. When users need SQL code, such as "help me write a SQL", "generate SQL statement", "how to write this SQL", "give me a query statement". 2. When users need to query a list of players meeting certain conditions or query a player's behavior list, used to generate SQL and then initiate query requests through `ae-cli analysis adhoc run` with `--model-type sql`. 3. If the data users need can be obtained through ae-analysis (such as dashboards, reports), prioritize using the ae-analysis skill to complete the full query execution process, do not use this skill
---

# Key Input Parameters

- **project_id**:
  - The project ID to query, obtained from context. If not found, ask the user. Do not guess or randomly generate
  - By default, only one project's query SQL can be generated at a time. If multiple project IDs need to be queried, generate and execute them one by one
- **$part_date**:
  - The date range to query, limiting the query scope based on date partitions
  - If querying data for the date range from 2026-01-01 to 2026-01-07, the generated filter condition fragment example is: "$part_date" between '2026-01-01' and '2026-01-07'
  - Only required for <Event Table>
- **$part_event**:
  - The event range to query. Confirm valid event names by combining context or using `ae-cli analysis-meta event list`. Do not guess or randomly generate
  - If querying a single event 'register', the filter condition fragment example is: "$part_event" in ('register')
  - If querying multiple events like 'login' and 'logout', the filter condition fragment example is: "$part_event" in ('login', 'logout')
  - Only required for <Event Table>

# Main Data Tables in TE System

- <Event Table>
  - Wide table recording player behavior data, named ta.v\_event\_{project_id}, replace the variable in the name with project ID
  - Key field descriptions:
    - #user_id: Unique player identifier in the system, can be used as a join key with <User Table>. Usually not needed in SQL when not performing join queries
    - #distinct_id: Usually records player's device ID, needed when querying player lists or player behavior lists
    - #account_id: Usually records player's account ID, needed when querying player lists or player behavior lists
    - #event_name: Records the name of the event triggered by the player, needed when querying player lists or player behavior lists
    - #event_time: Records the time when the player triggered the event, needed when querying player lists or player behavior lists
    - $part_event: Event name partition, must be used in SQL to ensure query efficiency, can pass single or multiple events as needed
    - $part_date: Event date partition, must be used in SQL to ensure query efficiency, can pass date range as needed. If querying only 1 day of data, the start and end points of the date range are the same
  - Each event has corresponding event properties. Confirm valid event property names and types by combining context or using `ae-cli analysis-meta property list`. Do not guess or randomly generate
    - Related event properties are usually used for displaying fields in results or filtering data
    - Example scenario:
      - When checking the registration channel of a player, usually add after the select statement for display
      - Example: select "#distinct_id", "#account_id", channel
    - Example scenario:
      - When checking players with channel="yaxiaoliang", usually add after the where statement for filtering
      - Example: select "#distinct_id", "#account_id", channel from ta.v_event_1 where 1=1 and "channel" in ( 'yaxiaoliang' )
- <User Table>
  - Wide table recording player basic attributes, named ta.v\_user\_{project_id}, replace the variable in the name with project ID
  - Key field descriptions:
    - #user_id: Unique player identifier in the system, can be used as a join key with <Event Table>. Usually not needed in SQL when not performing join queries
    - #distinct_id: Usually records player's device ID, needed when querying player lists
    - #account_id: Usually records player's account ID, needed when querying player lists
  - The project may have other business-related user properties. Confirm valid event property names and types by combining context or using `ae-cli analysis-meta property list --scope user`. Do not guess or randomly generate
  - If the query scenario requires user property related content, please query and display them together in the SQL

# General SQL Specifications

- By default, SQL should include a limit 100 result quantity restriction at the end
- Query, filter, group by, and alias fields all need to add " before and after the name to avoid TRINO/PRESTO recognition errors
  - Example: select "#user_id", "channel" as "Channel"
  - Example: group by "#account_id", "#distinct_id"
- Notes on "join keys" in join operations (left join, full join, inner join)
  - <Event Table> with <Event Table>
    - Use "#user_id" for joining
    - SQL example: from ta.v_event_8 left join ta.v_event_8 using("#user_id")
    - Common scenarios: Retention analysis (players registered on day T, logged in on T+1), Funnel analysis (proportion of players who completed tutorial step 2 after completing step 1)
  - <Event Table> with <User Table>
    - Use "#user_id" for joining
    - SQL example: from ta.v_event_8 left join ta.v_user_8 using("#user_id")
    - Common scenarios: Join query for "vip_level", "total_pay_amount" and other attributes in <User Table>
- TRINO/PRESTO SQL cannot use aliases from the select fields when using group by logic. Must use original field names or calculation logic, or field position numbers
  - **Correct example**: select "#user_id" as "uid", count("channel") as "ya" from v_event_8 group by "#user_id" /\*Use original field name\*/
  - **Correct example**: select "#user_id"+1 as "uid", count("channel") as "ya" from v_event_8 group by "#user_id"+1 /\*Use original calculation logic\*/
  - **Correct example**: select "#user_id"+1 as "uid", count("channel") as "ya" from v_event_8 group by 1 /\*Use field position number\*/
  - **Incorrect example**: select "#user_id" as "uid", count("channel") as "ya" from v_event_8 group by "uid" /\*Error: using alias\*/

# Common Scenarios and Check Templates

```sql
/*Assumption: project id=8, check players registered on 2026-01-01, known registration event=register, event contains channel, device_type, server_id properties
Use case: Based on a certain event, spot check players related to that event
Note: Only retrieves 100 records, adjust limit restriction and re-query to get more data*/
select "#distinct_id", "#account_id", "#event_time", "#event_name", "channel", "device_type", "server_id"
from ta.v_evnet_8 /*Project ID:8*/
where 1=1
and "$part_event" in ('register') /*Event name partition range*/
and "$part_date" between '2026-01-01' and '2026-01-01' /*Event date partition range*/
limit 100
```

```sql
/*Assumption: project id=8, check player (#account_id='yaxiaoliang') register, login, logout behaviors on '2026-01-01'; register and login events contain "channel" property, logout event contains "online_time" property
Use case: For a specific abnormal player, investigate their abnormal event situations within a certain date range. Default result quantity limit is 100, can be adjusted as needed
Note: Only retrieves 100 records, adjust limit restriction and re-query to get more data*/
select "#distinct_id", "#account_id", "#event_time", "#event_name", "channel", "online_time"
from ta.v_evnet_8 /*Project ID:8*/
where 1=1
and "$part_event" in ('register', 'login', 'logout') /*Event name partition range*/
and "$part_date" between '2026-01-01' and '2026-01-01'/*Event date partition range*/
and "#account_id" in ('yaxiaoliang') /*Filter by account ID*/
limit 100
```

```sql
/*Assumption: project id=8, check players who paid on 2026-01-01, also display "accumulated payment amount" from player properties
Known payment event=player_pay, event contains pay_amount (numeric type), item_id (text type)
"Accumulated payment amount" in player properties is acc_pay_amount (numeric type)
Use case: While querying event data, obtain more player-related information from <User Table>
Note: Only retrieves 100 records, adjust limit restriction and re-query to get more data
*/
select tav."#distinct_id", tav."#account_id", tav."#event_time", tav."#event_name", tav."pay_amount", tav."item_id", tau."acc_pay_amount"
from ta.v_evnet_8 tav /*Project ID:8, Event Table*/
left join ta.v_user_8 tau /*Project ID:8, User Table*/
using("#user_id")
where 1=1
and "$part_event" in ('player_pay') /*Event name partition range*/
and "$part_date" between '2026-01-01' and '2026-01-01' /*Event date partition range*/
limit 100
```

```sql
/*Assumption: project id=2, check key event situations for players with channel="suspect_channel" within the range of 2026-03-01 to 2026-03-02
Events include: register, login, activity_attend, player_pay
Calculation results include: player primary key ID info, player account ID info, number of event types triggered by player, total number of events triggered by player, number of times each event was triggered by player (map type)
Display logic: Sort by number of event types triggered by player, display top ten players with the least total quantity
Use case: After locating abnormal players, check if their event behaviors are abnormal. If necessary, can further join with <User Table> for query
Note: Only retrieves 100 records, adjust limit restriction and re-query to get more data
*/
with tbl1 as (
	select "#user_id", "#account_id", "$part_event", count() as "event_count"
	from ta.v_event_2 /*Project ID:2, Event Table*/
	where 1=1
	and "$part_event" in ('register', 'login', 'activity_attend', 'player_pay') /*Event name partition range*/
	and "$part_date" between '2026-03-01' and '2026-03-02' /*Event date partition range*/
	and "channel" in  ('suspect_channel') /*Check scope, currently filtering by channel*/
	group by "#user_id", "#account_id", "$part_event"
)
select
    "#user_id", "#account_id"
    ,count(distinct "$part_event" ) as "event_name_count" /*Number of event types triggered by player, fewer types means more singular behavior and higher abnormality*/
    ,sum("event_count") as "event_sum" /*Total event volume triggered by player*/
    ,map_agg("$part_event", "event_count") as "detail_info" /*Event volume for each event triggered by player, can be used to analyze player behavior concentration*/
from tbl1
group by "#user_id", "#account_id"
order by "event_name_count", "event_sum"
limit 100
```

# Output Format Requirements

- After generating SQL statements, check for syntax errors according to trino/presto engine specifications
- After confirmation, directly output the SQL statement. SQL statements can have corresponding logic comments. No other explanatory content is needed before or after the SQL statement
