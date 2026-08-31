# User Cluster (People-Bundle) Creation

> Canonical guidance for creating per-segment user clusters from a completed RFM run. Use ae-analysis tool references as the command/schema authority.

## 1. Concept and relationship to AE tags

| Artifact | Meaning |
| --- | --- |
| AE tag | Per-user value |
| User cluster | Membership cohort: in / out |

### Default operational pattern

1. Create the RFM `segment` tag first:
   - one tag;
   - N values;
   - every universe member receives exactly one value.
2. Create per-segment user clusters only for segment(s) that need activation delivery:
   - CRM;
   - push;
   - EDM;
   - campaign tooling.
3. Define a cluster as:
   - `members where tag value = <segment_key>`.
4. Do not create clusters for every segment by default.

**Preferred practice**

Keep non-activated segments as tag values for analysis. Bundle only the segments queued for activation.

## 2. Confirmation gate

Before any cluster write, show:

- [ ] Project ID/name
- [ ] `business_entity`
- [ ] Exact `subject_field`
- [ ] Universe
- [ ] Scoring window
- [ ] Reference timestamp
- [ ] Refund / F / M caliber
- [ ] Scoring method
- [ ] Per-metric `requested_bands` / `effective_bands` and runtime `band_profile`
- [ ] Final boundaries
- [ ] Segment(s) to bundle
- [ ] Analytical member count per segment
- [ ] Exact `cluster_name`
- [ ] Display name
- [ ] Definition source: tag-value reference vs reproduced SQL

**Write gate**

Proceed only after explicit user approval **per segment**.

Creating clusters the user did not request is a write violation.

## 3. Definition fidelity

A cluster for segment `S` must select exactly the users assigned to `S` in the analysis.

### 3.1 Definition-source priority

| Priority | Source | Use when | Fidelity behavior |
| ---: | --- | --- | --- |
| 1 | Tag-value reference | RFM tag already exists | Cluster = users whose RFM segment tag equals `S`; delegates entity/universe/scoring/threshold fidelity to the tag |
| 2 | Reproduced SQL | No tag exists or tag must not be a dependency | Reproduce the exact Stage 2 query shape, then filter `segment = 'S'` |

### 3.2 Reproduced SQL checklist

When SQL is used, reproduce:

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

**Prohibited**

Never use a simplified single-window SQL that drops historical lapsed users.

### 3.3 Fixed timestamp warning

If SQL embeds a literal reference timestamp:

- refresh alone may not advance it;
- periodic recreation/update may be required.

State this operational limitation explicitly.

## 4. Naming

### 4.1 Cluster key

Use stable, non-localized activation keys with the `_cluster` suffix, e.g.:

```text
rfm_champions_cluster
rfm_lost_high_value_cluster
rfm_at_risk_cluster
```

Do not use the bare tag key as a cluster key.

### 4.2 Display name

- Localize display name according to `output_locale`.
- Reuse one localized display name throughout the run.
- Do not append dates unless the user explicitly requests a frozen snapshot cohort.

### 4.3 Shared namespace with tags

Tags and user clusters share a single project-scoped namespace.

Platform conflict error:

```text
DUPLICATEKEY: "Unable to save name, [<name>] already exists."
```

After a name conflict:

- `user-tag get` may report `USER_TAG_NOT_FOUND`;
- `user-cluster get` may report `USER_CLUSTER_NOT_FOUND`.

The conflict happens at **name-save time**, not resource lookup.

When both artifacts are needed for one segment, use the canonical pairing:

```text
tag:     rfm_segment                       (single multi-value tag; tag_value enumerates segments)
cluster: rfm_at_risk_cluster               (activation cohort; members where tag_value = 'at_risk')
```

The single tag key `rfm_segment` is shared across all segments; per-segment activation cohorts suffix the segment key with `_cluster` and select members by `tag_value`.

Localized display names may coincide.

## 5. Write, compute, and verify

For each requested cluster:

1. Check whether `cluster_name` already exists before the write preview.
2. If absent, request explicit **CREATE** approval.
3. If present, retrieve the existing definition/member semantics, show the proposed delta, and request explicit **UPDATE/REPLACE** approval. A create approval never authorizes mutation.
4. Use a tag-value condition when the validated RFM tag exists; otherwise use fidelity-preserving reproduced SQL.
5. Execute only the confirmed action. Do **not** call `user-cluster refresh`: a definition create/update starts computation automatically.
6. Follow the returned `next_action` and poll `user-cluster get` until the new result is fresh. Use `user-cluster refresh` only for an explicit retry or recomputation of an unchanged definition.
7. Read member counts only after the new computation is complete.
8. Compare platform member count with the analytical segment count under the same snapshot/caliber.
9. **Expected difference = 0** under the same snapshot/definition; investigate any non-zero difference. Use a tolerance only for a documented timing/backfill/rolling-refresh reason.

### 5.1 Output after creation / recomputation

Render the conditional `ae_clusters` table using:

- `references/output_format.md` §4;
- `assets/output_contract.yaml`.

Populate:

| Field | Value source |
| --- | --- |
| `cluster_name` | Stable cluster key |
| `cluster_display_name` | Localized display name |
| `analytical_count` | Stage 5 segment count |
| `platform_count` | Refresh/member query |
| `member_difference` | `platform_count - analytical_count` |
| `link` | `analysis-meta asset url-get` when resource ID + supported type are available |

If link generation is skipped because:

- no resource ID exists; or
- URL generation fails;

state that explicitly.

## 6. High-risk actions

Deletion/replacement of an existing cluster is a separate high-risk action and requires its own confirmation.

## 7. Failure handling

| Failure | Required action |
| --- | --- |
| Cluster write rejected | Read structured error and follow ae-analysis metadata resolution; never guess identifiers |
| `meta.partial:true` | Report failures and retry only retryable items |
| Member-count divergence above threshold | Do not silently adjust; re-check definition and report gap + recommendation |
