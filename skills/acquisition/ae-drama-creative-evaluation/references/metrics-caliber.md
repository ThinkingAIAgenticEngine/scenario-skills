# Metric Calibers, Observation Windows, and Retrieval Rules Verified in Practice (Skill Steps 5/7)

## Core Metric Definitions

| Metric | Definition |
|---|---|
| CTR | clicks / impressions |
| Click-to-activation rate | attributed activations / clicks |
| CPI | ad spend / attributed activations |
| Registration rate | successfully registered users / attributed activated users |
| First-purchase rate | first-time paying users / corresponding cohort users |
| ROAS | attributed revenue / ad spend (**must not be calculated** without real spend; simulated fields are forbidden) |
| ROI | (revenue or gross profit - input) / input; calculate only when content cost, channel revenue share, and payment fees are available |
| LTV | per-user cumulative revenue of a specified cohort within a fixed maturity window; must label D0/D1/D3/D7/L30 |
| Comprehensive revenue | IAP revenue + subscription revenue + IAA ad revenue |
| D0 | do not call it retention; use terms such as "same-day activity depth, same-day viewing, same-day payment" |

## Default Observation Windows

- Pre-funnel metrics: observe by hour/day;
- Activation, registration, content conversion: T+0, T+1;
- Revenue and ROAS: D0/D1/D3/D7, add L30 when business allows;
- Retention: D1/D3/D7, draw conclusions only after the observation period matures;
- Creative lifecycle: align by days-since-launch, do not compare only by natural calendar date.

**Maturity rule**: D7 metrics count only cohorts where "activation date <= analysis date - 7"; the attribution data start point determines the maximum usable window (e.g., if data starts from 8/28, L30 does not hold). Different maturity windows must not be mixed; immature cohorts are labeled "under observation".

## ae-cli Retrieval Rules Verified in Practice (validated on real projects; must read before retrieval)

### Metadata stage
1. **Complete metadata export**: use `analysis-meta event export` / `analysis-meta property export` when all accessible metadata is required (already wrapped in scripts/metadata_scan.sh). Do not rebuild a complete export by repeatedly paging list commands.
2. **Event list cross-validation**: preset events (`ta_app_install`, `ta_app_start`, etc.) and some custom events may not appear in the metadata export; use SQL `select "#event_name", count(*) from <authorized event table> where "$part_date"='<yesterday>' group by 1` as the tested source of truth.
3. **Data freshness**: metadata `last_day_count` may lag (shows 0 but data actually exists); validate with queries over the last 7 days.
4. **Attribution layer probe**: post-activation behavior events usually do not carry media_source/campaign/ad_id; check whether the preset activation event (e.g., `ta_app_install`) carries them; also check whether the user property table (v_user_<PID>) persists attribution fields.
5. **Channel dual-field discrimination**: `channel` usually refers to the package distribution channel (app store), while `media_source` is the ad media channel; do not mix them up.

### Field semantic verification (must test; forbidden to interpret names literally)
6. **Boolean field truth type**: first `group by` to see the actual type. Boolean columns use `is_xxx = true` (write `is_xxx=true` in SQL), string columns use `= 'true'`; mixing them directly errors out.
7. **Synonym field discrimination**: registration success may be `is_register` rather than `is_success` (tested: RegisterResult only has is_register); defer to group-by test results.
8. **Failed orders carrying amounts**: recharge-result failed orders (is_success=false) often also carry the amount field; without filtering, revenue can be inflated by dozens of times - **revenue must be filtered by success status**.
9. **Multi-event revenue mounting**: `ad_income` is often mounted on entry-click/impression/click/play-complete multiple events simultaneously with duplicated values - **bill on a single event only** (default to the play-complete event, e.g., AdComplete); summing across events inevitably double-counts.
10. **Virtual property risk**: for properties starting with `#vp@`, first query `vir_prop_column_rule` via `metadata.property.get` - if the rule contains `random()`, it is simulated data and **forbidden for any conclusion**; virtual properties cannot be used as physical columns in SQL models.
11. **Cost field**: when no real spend/cost field is found, label ROAS "unavailable"; do not fill with simulated values.

### SQL authoring
12. **`$part_date` is varchar**: use string comparison (e.g., `"$part_date" >= '<yyyy-MM-dd>'`), do not compare directly against date literals.
13. **Authorized table reference**: first use `analysis sql-table list --project-id <PROJECT_ID> --usage analysis`, then copy its exact `table_ref`; never guess `v_event_<PROJECT_ID>` or another physical table name.
14. **Large quoted SQL**: write to a securely generated temporary JSON file and pass with `--definition "$(cat file)"` to avoid shell-escaping breaking the query.
15. **Multiple-activation check**: before defining a cohort, verify `count(*)` vs `count(distinct "#user_id")`; de-duplicate to the earliest observed activation and its attribution before joining later events. The bundled SQL templates do this with `row_number()` over `"#event_time"`.
16. ae-cli `--jq` operates on the `data` layer inside the envelope. Event list rows are under `.items[]`; property list rows are under `.properties[]`.
17. Quote system fields: `"#user_id"`, `"#event_name"`, `"#event_time"`, `"$part_date"`; first run a small-window query to verify fields and calibers, then expand; on `No property matched`, go back to metadata to confirm which event the property is mounted on.

### adhoc event analysis model (--model-type event) definition structure
- `metrics` is an array of objects: `[{"event":"<event name>","aggregation":"total_count"}]`; total-count aggregation uses `total_count`; property sum uses `"aggregation":"sum","property":"<property name>"`;
- Time: `"time_range":{"mode":"recent|previous|custom",...}` (previous excludes today; custom uses `start_time`/`end_time`, format yyyy-MM-dd);
- Grouping: `"groups":[{"field":{"name":"<property name>"}}]`; granularity: `"time_particle_size":"total|day|hour|week|month"`;
- Different model_type structures are entirely different. Follow the matching command/model reference; inspect `analysis.adhoc.run` only when a concrete schema mismatch remains unresolved.

## Sample Threshold

Do not arbitrarily apply a fixed industry threshold when the user has not provided one; recommend based on the project distribution, and at minimum check impressions, clicks, activations, paying users, spend, and maturity days simultaneously. Reference practice: creative-level >=300 activations can be judged; creative x channel cells <100 are only "directional signals". Do not output definite scale-up/pause conclusions when the sample is insufficient.
