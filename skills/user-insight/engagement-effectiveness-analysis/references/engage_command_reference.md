# Mode A - Engage Command Reference

All commands are run through `ae-cli` and accept `--project_id` (`-p`).
Every call is internally suffixed with `--no-update-check`.

Binary discovery (implemented in `scripts/_env.py`, surfaced via `scripts/_ae.py`).
The order is deliberately generic - this skill runs on other people's machines, so
no single install path may be privileged:
1. an explicit path argument (`--ae-cli`), when the caller supplies one
2. `$AE_CLI_PATH` / `$AE_CLI`, when set to an existing file
3. the first `ae-cli` on `PATH`
4. a scan of conventional prefixes, with version directories left as wildcards:
   the agent-managed Node root (`<node-root>/*/node_modules/.bin/`),
   `~/.nvm/versions/node/*/bin/`, `~/.volta/bin/`, `~/.local/bin/`,
   `~/.npm-global/bin/`, `~/node_modules/.bin/`,
   `/usr/local/bin/`, `/opt/homebrew/bin/`, and on Windows `%APPDATA%\npm\`
   (`.cmd` / `.exe` suffixes are probed as well)

When nothing is found the error lists every location that was searched and names
`$AE_CLI_PATH`, so the fix is a one-liner rather than a guessing game.

## Parameter rules (verified against the sandbox)

| Parameter | Accepted values | Notes |
|---|---|---|
| date format | `yyyy-MM-dd` | `20260701` and any datetime form are rejected |
| `--flow_uuid` | `<flowId>_<suffix>` | `--flow_id` raises a NullPointerException |
| `--data_dim_type` | `uv`, `pv` | canvas reports only |
| `--detail_type` | `time`, `instance`, `instance_daily` | `instance_daily` also needs `--task_instance_id` |
| `--report_type` | `overview`, `detail` | experiment report only |
| `--req` | JSON string | e.g. `{"pageNum":1,"pageSize":200}` |

## Object discovery

### `engage +task_list`
```bash
ae-cli engage +task_list -p <PID> --req '{"pageNum":1,"pageSize":200}'
```
Returns `data.operationTaskDTOS[]`. The fields that matter for routing:

| Field | Meaning |
|---|---|
| `taskId` / `taskName` | identity |
| `hasPushRecord` | the task actually sent something - the first filter to apply |
| `hasPushData` | effect data exists |
| `channelName` / `channelType` | channel |
| `statusName` | `已结束` / `执行中` / ... |
| `triggerTime`, `tzOffset` | send time and timezone |
| `completionIndicatorDef` | **JSON string** holding the conversion indicator definition: event name, attribution window (`touch_cycle_num` + unit), condition |
| `expConfig` | JSON string with `enableExp`, `expType`, `expStatus`, `expStartTime`, `expEndTime` |
| `metricMap` | conversion metrics; frequently empty even on real tasks |

> The page size maximum is 200. Paginate rather than assuming one call covers the project.

### `engage +flow_list`
```bash
ae-cli engage +flow_list -p <PID>
```
Returns `data[]` with `flowId`, `flowUuid`, `flowName`, `status`, `entryStartTime`,
`entryEndTime`, `hasData`.

### `engage +flow_detail`
```bash
ae-cli engage +flow_detail -p <PID> --flow_uuid <UUID>
```
`hasData` in this response is the cheapest way to filter out canvases with no
execution records before spending calls on their reports.

## Effect metrics

### `engage +task_data_overview`
```bash
ae-cli engage +task_data_overview -p <PID> --task_id <TID>
```
**Returns synchronously** (`resultGenerateTime` is populated; no polling needed).
Shape: `data.dataList[{key,value}]`.

| key | Stage |
|---|---|
| `plan` | targeted audience size |
| `actualTrigger` | users who entered the flow |
| `trigger` | messages dispatched successfully (platform-side delivery proxy) |
| `view` | users who actually saw the message |
| `click` | users who clicked or opened |
| `main` | users who completed the conversion goal |

### `engage +task_data_detail`
```bash
ae-cli engage +task_data_detail -p <PID> --task_id <TID> \
  --detail_type time --start_time 2024-02-01 --end_time 2024-12-31
```
Returns an ECharts-style payload: `data.data = {x: [...], y: [{metric: [{values: [...]}]}], z: [...], xtag: ...}`.

* `detail_type=time` - `x` is a date list whose **first element is the summary
  label** (`Overview` / `Total`); `y` holds one series per metric.
  The analysis stage separates that summary row out; do not treat it as a date.
* `detail_type=instance` - `z` carries `task_instance_id` values such as
  `0822_2024-02-26`. Those ids are the input to `instance_daily`.
* `detail_type=instance_daily` - per-day tracking after a single send; requires
  `--task_instance_id`.

### `engage +task_experiment_report`
```bash
ae-cli engage +task_experiment_report -p <PID> --task_id <TID> --report_type overview \
  --start_time <S> --end_time <E>
```
Returns per-group rows with `expGroupName`, `expGroupType` (**1 = control, 2 = experiment**),
`successUserNum`, `liftRate`, `confidenceIntervalFloor`, `confidenceIntervalCeil`,
`significanceLevel`, `win`.

> Lift and significance come from the platform. Do not recompute them; a locally
> computed p-value would silently disagree with what the customer sees in the UI.

## Canvas metrics

```bash
ae-cli engage +flow_node_overview_report -p <PID> --flow_uuid <UUID> \
  --start_time <S> --end_time <E> [--data_dim_type uv|pv]
ae-cli engage +flow_node_detail_report  -p <PID> --flow_uuid <UUID> --node_uuid <NID> ...
ae-cli engage +flow_process_report      -p <PID> --flow_uuid <UUID> --report_type <overview|detail> ...
ae-cli engage +flow_ab_split_node_report ...
```

A `dataList: null` response is **not a call error**. In the sandbox, canvases
with `hasData=true` still return null node reports: the records were never
generated. Distinguish this from a parameter mistake before debugging.

## Configuration item metrics

```bash
ae-cli engage +config_item_list -p <PID>
ae-cli engage +config_item_trigger_report -p <PID> --config_id <CID> --start_time <S> --end_time <E>
```
`+config_item_strategy_comparison` provides cross-strategy comparison.
`+config_item_trigger_report` returns `targetUserTotalNum`, `userTotalNum`
and `detail[].x`.

## Permission

Engage queries are scoped to projects visible to the authenticated account.
`analysis_common +list_projects` returns the full accessible set (301 projects
in the sandbox) and is the cheapest way to confirm a `project_id` is valid
before running any report.
