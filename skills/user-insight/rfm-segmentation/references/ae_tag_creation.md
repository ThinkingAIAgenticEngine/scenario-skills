# AE Tag Creation

> Canonical Stage 8 guidance. Use ae-analysis tool references as the command/schema authority.

## 0. Single multi-value tag model

The RFM segment tag is **one platform tag with multiple values**, not one tag per segment.

```text
tag_name:  rfm_segment
display:   RFM-Segment
tag_value: champions | lost_high_value | loyal | potential | promising | hibernating | at_risk
```

Every universe member receives exactly one `tag_value` equal to their lifecycle segment key. Activation cohorts are produced as **per-segment user clusters** that reference this tag value (see `references/cluster_creation.md`); they are not separate tags.

Rationale:

- one scan of the event table per refresh instead of N;
- one source of truth for entity / universe / scoring / threshold fidelity;
- per-segment activation still available via clusters that filter `tag_value = '<segment_key>'`.

## 1. Confirmation gate

Before any tag write, show all of the following:

- [ ] Project ID/name
- [ ] `business_entity`
- [ ] Exact `subject_field`
- [ ] Eligibility lookback
- [ ] Scoring window
- [ ] Reference timestamp
- [ ] Payment / refund / F / M caliber
- [ ] Scoring method
- [ ] Per-metric `requested_bands` / `effective_bands` and runtime `band_profile`
- [ ] Final boundaries
- [ ] Segment-priority mapping
- [ ] Single `tag_name` / `tag_display_name` and the exhaustive `tag_value` enumeration
- [ ] Estimated **per-value** counts
- [ ] Exact stable platform tag name / display name from `assets/rfm_tag_names.yaml`

**Write gate**

Proceed only after explicit user approval.

## 2. Stable naming

### 2.1 Source of truth

Read:

```text
assets/rfm_tag_names.yaml
```

Use its single stable:

- `tag_name` (`rfm_segment`);
- `tag_display_name` (`RFM-Segment`);
- `tag_value` enumeration (the lifecycle segment keys).

### 2.2 Naming rules

- Always create exactly one RFM tag per project: `rfm_segment`.
- Do not create per-segment tags (`rfm_champions`, `rfm_at_risk`, …). They are obsolete.
- Do not localize the platform `tag_display_name` per conversation.
- Do not append run dates unless the user explicitly requests a frozen snapshot cohort.
- Keep `tag_value` equal to the stable lifecycle keys; never put localized text in `tag_value`.

### 2.3 Shared namespace with user clusters

AE tags and user clusters share a single project-scoped namespace.

| Condition | Result / action |
| --- | --- |
| `tag_name` reuses an existing `cluster_name` | Platform rejects the second write |
| `cluster_name` reuses an existing `tag_name` | Platform rejects the second write |
| Per-segment activation needed | Create a cluster keyed `rfm_<segment>_cluster` that references `tag_value = '<segment_key>'` |

Platform error:

```text
DUPLICATEKEY: "Unable to save name, [<name>] already exists."
```

Canonical pairing:

```text
tag:     rfm_segment                      (single multi-value tag)
cluster: rfm_at_risk_cluster              (activation cohort; filters tag_value='at_risk')
```

The bare tag key is the shared `rfm_segment`; per-segment keys live only as `tag_value`s and as the `rfm_<segment>_cluster` suffix.

If a legacy per-segment tag (`rfm_champions`, `rfm_at_risk`, …) or same-name cluster already occupies the key, report the namespace conflict and ask before renaming/replacing anything. Do not silently mutate an existing tag or cluster.

Localized display names may coincide; the namespace restriction applies to keys.

## 3. Definition fidelity

The platform tag definition must reproduce the analysis exactly and emit `tag_value` for every universe member.

### Required equivalence checklist

- [ ] Same person-level subject field
- [ ] Same universe / eligibility logic
- [ ] Same scoring window
- [ ] Same reference-timestamp semantics
- [ ] Same currency / filter / dedup rules
- [ ] Same refund-recognition mode
- [ ] Same F mode
- [ ] Same `M_scoring` treatment
- [ ] Same per-metric requested/effective band profile and tie-adjustment logic
- [ ] Same raw-score → semantic-level mapping
- [ ] Same thresholds / boundaries
- [ ] Same segment-priority mapping
- [ ] Emits `tag_value` = the lifecycle segment key for every universe member (exactly one value per user; lapsed users retain their lifecycle segment, never dropped)

**Prohibited**

- Never use a simplified single-window SQL that drops historical lapsed users.
- Never split the model into per-segment tags.

## 4. Definition type

### 4.1 Use a SQL tag

The condition/metric tag model cannot express the full R/F/M methodology reliably. Use a `sql` tag that reproduces the **exact Stage-2/Stage-5 pipeline** and emits one `tag_value` per universe member.

Do **not** copy a generic executable SQL example with hardcoded `#user_id`, payment-only aggregation, or raw-score aliases. Generate the SQL from the confirmed runtime caliber.

Required logical shape:

```text
universe
  -> eligible subjects using <subject_field> and confirmed universe rule

payment_orders
  -> confirmed successful-payment semantics
  -> confirmed order dedup key / row semantics

recognized_refunds
  -> original-order linkage
  -> confirmed refund_recognition cutoff/mode

order_netting
  -> payment +/- recognized refund at order level
  -> derive transaction validity for R/F according to confirmed F/R semantics

rfm_metrics
  -> LEFT JOIN aggregated F/M back to universe
  -> preserve lapsed eligible subjects with F=0, M_raw=0
  -> derive R from latest valid eligibility-window transaction
  -> derive M_scoring exactly as analysis

raw_scores
  -> reproduce exact per-metric cutoffs/operators
  -> emit R_score/F_score/M_score on each metric's effective scale

semantic_levels
  -> map raw scores to R_level/F_level/M_level using scoring_standards.md §2.4

segmented
  -> apply the exact first-match lifecycle mapping

final
  -> SELECT <subject_field>, <segment_key> AS tag_value
```

**Mandatory SQL fidelity details**

- Use the runtime `<subject_field>`; never hardcode `#user_id` when another entity was selected.
- Universe must be its own CTE/input and F/M must be LEFT JOINed back to it.
- Refunds must be netted at the confirmed order/linkage grain before F/M aggregation when refund semantics require it.
- Keep `R_score/F_score/M_score` distinct from `R_level/F_level/M_level`; never alias raw scores directly as semantic levels.
- Reproduce mixed-band profiles and tie-safe cutoffs exactly; do not recompute different thresholds inside the tag.
- Quote identifiers according to Trino rules and include valid `$part_date` partition predicates using string literals/placeholders.

### 4.2 Rolling vs fixed timestamp

Prefer a rolling reference timestamp expressed via the SQL engine (`date(current_date) - interval '1' day`) and a `${PartDate:elig}` placeholder with `recent_day` set to the eligibility span. The tag then advances automatically on each refresh.

If the SQL must embed a literal reference timestamp (business-required frozen snapshot), state explicitly that refresh alone will not advance the timestamp and periodic recreation is required.

### 4.3 Before SQL tag creation

1. list authorized `tag_cluster` tables/columns (`--usage tag_cluster`);
2. generate SQL from the same Stage 2 query shape;
3. verify the analytical segment counts are reproduced by the same SQL run as an ad-hoc query;
4. verify reference-timestamp behavior.

`#user_id`, `$part_event`, `$part_date`, and any other Trino identifier containing `#`, `$`, `@`, spaces, or punctuation must be delimited with double quotes. SQL tags support only `${PartDate:name}` placeholders; each placeholder requires one `params` item with `type=part_date` and either `recent_day` or `start_time` plus `end_time`.

## 5. Write, compute, and verify

### 5.1 Existing-resource check and action-specific approval

Before write, look up `rfm_segment`.

- If absent: show the preview and request explicit **CREATE** approval.
- If present: retrieve the existing definition/refresh semantics, show the delta and dependent-cluster impact, and request explicit **UPDATE/REPLACE** approval.
- A create approval never authorizes an update.
- Deletion/replacement remains separately high-risk per §6.

### 5.2 Execute and verify

After the matching action is confirmed:

1. Execute only that confirmed create/update action.
2. Do **not** call `user-tag refresh`: a definition create/update starts computation automatically. Follow the returned `next_action` and poll `user-tag get` until the new result is fresh. Use `user-tag refresh` only for an explicit retry or recomputation of an unchanged definition.
3. Read per-value counts only after the new computation is complete.
4. Compare platform per-value counts with analytical segment counts under the same snapshot/caliber.
5. **Expected difference = 0** under the same snapshot and definition; investigate any non-zero difference.
6. Use a non-zero tolerance only when a documented rolling-refresh, late-backfill, or evaluation-timestamp difference makes exact equality impossible; state that reason and tolerance explicitly.

## 6. High-risk actions

Deletion/replacement of the existing `rfm_segment` tag is a separate high-risk action and requires its own confirmation. Deleting the tag breaks dependent per-segment clusters that reference its `tag_value`; surface this impact before deleting.
