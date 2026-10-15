# Product Config Example (LesPark, project-id=4)

> This is a **filled real example** demonstrating how to fill `product-config-template.md`. Copy this file, rename to `product-config-<your-product>.md`, and replace values with your product's.
> Note: **this is "example reference", not "default"**. Any new product must fill its own config first; do NOT copy this file's field names directly.

---

## Product Info

| Config item | Value | Note |
|--------|-----|------|
| `product_name` | LesPark | |
| `project_id` | 4 | ae-cli `--project-id 4` |
| `event_table` | `hive.ta.v_event_4` | Trino/Hive |
| `user_table` | `hive.ta.v_user_4` | join key `#user_id` |
| `tz` | UTC+8 | |

## DAU & Entry Events

| Config item | Value |
|--------|-----|
| `dau_event` | `Login_Daily` |
| `enter_event` | `Enter_Live` |
| `enter_event_filter` | (empty) |
| `enter_event_2` | `bhv_live` |
| `enter_event_2_filter` | `bhv_type='click'` |

## Entry-Source Fields

| Config item | Value |
|--------|-----|
| `enter_source_field` | `how_inter` (primary event, null-rate chronically 45%~55%) |
| `enter_source_field_2` | (empty) |
| `enter_source_vp` | `#vp@spm2` (second event, SPM-AB segment) |
| `enter_source_vp_2` | `#vp@spm_c` (second event, SPM-C segment) |

## User-Dimension Fields

| Config item | Value |
|--------|-----|
| `new_user_field` | `add_date` (timestamp(3) type, compare needs `cast as date`) |
| `organic_field` | `#vp@total_is_organic` |
| `channel_field` | `#vp@attribution_channel` |
| `locale_field` | `locale` |
| `host_field` | `if_host` |

## Funnel & Supply-Side Events

| Config item | Value |
|--------|-----|
| `exposure_event` | (LesPark no exposure event, funnel skips exposure segment) |
| `exposure_scene_field` | (empty) |
| `live_start_event` | `live_start` |
| `live_end_event` | `live_end` |
| `live_duration_field` | `live_duration` |
| `stay_duration_field` | (LesPark no stay-duration field, quick-exit/avg-time skip) |
| `room_id_field` | `liveroom_id` |
| `interaction_events` | `liveroom_comment,liveroom_send_gift,mic_take,emotion_send` |

## Caliber Notes (LesPark-specific traps)

- OS case inconsistency: `Enter_Live`'s `#os` is uppercase (`Android`/`iOS`/`HarmonyOS`), `bhv_live`/`Login_Daily` are lowercase (`android`/`ios`); cross drill-down must `LOWER()` normalize
- `Enter_Live`'s entry source `how_inter` null-rate chronically 45%~55%; high null-rate ≠ skip breakdown — non-null part still supports entry distribution (declare coverage caveat)
- `Enter_Live` **has no spm field** (event-level spm all null), entry source can only use `how_inter`; `bhv_live` uses `#vp@spm2`/`#vp@spm_c` virtual properties
- Version number `x.x.xx` three-segment (e.g., `9.7.46`), patch versions can be 100+; **do NOT SUBSTR-truncate to aggregate major version**
- `add_date` is `timestamp(3)`, `$part_date` is `varchar`; compare with `cast(x as date)`, do NOT use `date_parse`
