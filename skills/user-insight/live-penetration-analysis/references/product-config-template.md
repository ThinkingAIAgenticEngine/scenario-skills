# Product Config Template

> This file is the **required pre-config** for live-penetration analysis (universal edition). Before the first analysis of any product, you MUST fill the table below and persist as `product-config-<product-name>.md` (e.g., `product-config-myapp.md`).
> **Running analysis without config = violation. Guessing event names = violation.**
> **Fill reference**: `references/product-config-example.md` is a filled real example (LesPark); follow its structure to fill, but it is an **example, not default** — do NOT copy field names.

---

## Product Info

| Config item | Value | Note |
|--------|-----|------|
| `product_name` | | product name (e.g., "some live app") |
| `project_id` | | ae-cli project ID (number) |
| `event_table` | | event table (Trino/Hive full path, e.g., `hive.ta.v_event_<id>`) |
| `user_table` | | user table (e.g., `hive.ta.v_user_<id>`) |
| `tz` | UTC+8 | timezone (default UTC+8) |

---

## DAU & Entry Events

| Config item | Value | Note |
|--------|-----|------|
| `dau_event` | | DAU-caliber event name (e.g., `app_start` / `daily_login`). **Do NOT use all-event distinct (DAU inflated & volatile)** |
| `enter_event` | | entry event name (primary, e.g., `room_enter` / `live_enter`) |
| `enter_event_filter` | | entry event filter (e.g., `beh_type='click'`), empty if none |
| `enter_event_2` | | second entry event name (optional, for dual-event cross-validation, e.g., `live_behavior`) |
| `enter_event_2_filter` | | second entry event filter |

---

## Entry-Source Fields

| Config item | Value | Note |
|--------|-----|------|
| `enter_source_field` | | entry-source field (event-level property, primary event, e.g., `enter_from` / `entry_source` / `enter_scene`) |
| `enter_source_field_2` | | second entry-source field (primary event, optional, e.g., when `live_entry` and `enter_scene` coexist) |
| `enter_source_vp` | | entry-source virtual property (event model, second event, optional, e.g., `#vp@entry_page` / `#vp@content_pos`) |
| `enter_source_vp_2` | | second entry-source virtual property (optional) |

---

## User-Dimension Fields

| Config item | Value | Note |
|--------|-----|------|
| `new_user_field` | | new/old user judgment field (user table, e.g., `register_time` / `first_visit_date`). New user = registration day (`{field} = $part_date`), not "registered within N days" |
| `organic_field` | | organic/paid virtual property (event model, e.g., `#vp@is_organic`) |
| `channel_field` | | channel virtual property (event model, e.g., `#vp@attr_channel`) |
| `locale_field` | | country/region field (user table, e.g., `locale` / `country`) |
| `host_field` | | streamer flag field (user table, e.g., `is_host` / `is_anchor`) |

---

## Funnel & Supply-Side Events (optional; skip corresponding segment if empty)

| Config item | Value | Note |
|--------|-----|------|
| `exposure_event` | | live exposure event name (e.g., `live_expose`). Empty → funnel skips exposure segment |
| `exposure_scene_field` | | exposure event's scene/entry field (e.g., `scene` / `position`) |
| `live_start_event` | | streaming-start event name (e.g., `live_start`). Empty → supply-side analysis skips |
| `live_end_event` | | streaming-end event name (e.g., `live_end`) |
| `live_duration_field` | | streaming-end event's duration field (e.g., `live_duration`) |
| `stay_duration_field` | | entry event's stay-duration field (e.g., `stay_duration`). Empty → quick-exit/avg-time skip |
| `room_id_field` | | room id field (e.g., `room_id` / `live_room_id`) |
| `interaction_events` | | interaction event list (e.g., `room_comment,room_gift,mic_take,emotion_send`), comma-separated |

---

## Caliber Notes (product-specific traps)

> Record the product's specific caliber traps here for future analysis. Examples:
>
> - OS case inconsistency: primary event `#os` is uppercase (`Android`/`iOS`), DAU event is lowercase (`android`/`ios`); cross drill-down must `LOWER()` normalize
> - Entry-source field null-rate chronically 45%~55%; high null-rate ≠ skip breakdown — non-null part still supports entry distribution (declare coverage caveat)
> - Version number is `x.x.xx` three-segment (e.g., `9.7.46`), patch versions can be 100+; **do NOT SUBSTR-truncate to aggregate major version**
> - `{new_user_field}` is `timestamp(3)`, `$part_date` is `varchar`; compare with `cast(x as date)` to unify

```
(fill product-specific traps here)
```

---

## Fill Checklist

- [ ] **Project ID confirmed with user** (if not provided, ask first; do NOT self-list and default a project)
- [ ] **Time range confirmed with user**
- [ ] `project_id` / `event_table` / `user_table` filled
- [ ] `dau_event` / `enter_event` filled, and confirmed as "DAU caliber" not "all events"
- [ ] `enter_source_field` filled (or confirmed the product has no entry-source field, funnel skips entry analysis)
- [ ] `new_user_field` filled, and field type confirmed (timestamp / varchar)
- [ ] `organic_field` / `channel_field` filled (or confirmed the product has no virtual property, use SQL CASE WHEN fallback)
- [ ] Funnel & supply-side events filled (or confirmed skipping the corresponding segment)
- [ ] Caliber notes filled with product-specific traps (if any)
