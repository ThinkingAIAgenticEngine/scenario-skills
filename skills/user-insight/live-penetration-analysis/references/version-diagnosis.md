# Version-Difference Diagnosis (Universal Edition)

> Read this file when SKILL.md Part 4 locates "version" as a suspect dimension, or the trend shape points to "version handover".
> Purpose: distinguish "structural migration" (share change, not a defect) from "version defect" (new version's entry experience itself abnormal).

## Trigger Condition

Part 3 lists "version" as a suspect dimension, or Part 4 cross drill-down confirms the change is version-related, or the trend shape points to "version handover". At this point **do NOT directly output "version migration is normal"**; you MUST complete the following diagnosis before entering Part 5 judgment.

**Timing location**: this part deepens Part 4's "version × new/old / OS" drill-down — Part 4's table only answers the coarse "is the version a new-user problem or an overall problem"; this part answers "is the version itself broken, and where".

## Step Zero (highest priority): Same-Cohort Before/After Upgrade Comparison — rule out selection bias

Same-period new vs old version comparison has a fatal trap: **users who upgraded to the new version may themselves be a low-entry population** (early adopters / silently force-upgraded inactive users), so "new version penetration low" may reflect "these people were always like this" rather than the version being broken. You MUST falsify this with the **same cohort's before/after upgrade** entry-rate comparison:

- Anchor users who "upgraded from old to new version" (via user table `#app_version` change, or upgrade event / upgrade timestamp), compare their **7 days before upgrade vs 7 days after upgrade** entry rate.
- If the same cohort's entry rate drops significantly (≥ 2pp) after upgrade → version defect ironclad evidence, locate directly, no need for between-group comparison.
- If the same cohort's entry rate is unchanged after upgrade, and it is only "low-entry population got upgraded, high-entry population hasn't yet" structural change → this is the true structural migration.

SQL template: `references/query-templates.md` "Version-difference diagnosis queries" step zero.

## Step One: Falsify Migration (intra-group rate comparison)

Compare the new version's vs same-period old version's **intra-group penetration** (fallback when step zero is unqueryable). **Note: intra-group rate comparison has three directions; it can only land on one; do NOT mistake "between-group difference" for "time-trend fluctuation" (see SKILL.md trend-shape judgment).**

- If new version intra-group penetration ≈ same-period old version intra-group penetration (difference < 2pp), AND aggregate decline fully explained by new-version DAU share rise → **pure structural migration**, attributable to type 4b/5, conclusion holds.
- If new version intra-group penetration significantly below same-period old version intra-group baseline (≥ 2pp), the new-version users came in but **entry willingness/ability systematically lower** → **version defect**, enter step two.
- **If new version intra-group penetration is above same-period old version (≥ 2pp), this is the normal "layered upgrade / early-bird effect", not a defect.** Highly active, high-entry-willingness users upgrade first; those lingering on old version are low-activity long-tail, so the new version's rate is naturally higher than the old. This direction **does not need step-two defect digging**; state factually "new version intra-group rate above old version, layered upgrade". **Especially when the aggregate itself has no inflection (shape B), version between-group difference is not "fluctuation" regardless of direction, and does not trigger defect judgment.**

## Key Criterion: first judge whether the aggregate has fluctuation, then decide whether to do version diagnosis

**This is the highest pre-judgment; missing it causes forcing the version-defect framework in a "no fluctuation" scenario and repeatedly changing conclusions.**

1. If the aggregate penetration has **no inflection** (shape B), and each dimension's intra-group rate also has no time-trend change → the conclusion is "no fluctuation". Here **version diagnosis can be entirely skipped**; version between-group difference (whether new version above or below old) is a cross-section feature, listed factually in the detail table, no attribution needed.
2. Only when the aggregate penetration **has an inflection** (down or up), AND version is located as a "suspect dimension", do you run version diagnosis to distinguish "structural migration vs version defect".

## Step Two: Locate In-Version Abnormal Subgroup

Split the new version by the following sub-dimensions, find "exclusive anomaly" (only appears in a subgroup, does not exist in the same subgroup on the old version):

| Sub-dimension | Split field | Judgment point |
|--------|---------|---------|
| Entry source - primary | product config `enter_source_field` | new version's some entry penetration plunges → that entry changed/broken in new version |
| Entry source - second | product config `enter_source_vp` (event model) | same as above, cross-validate |
| OS | `#os` | new version abnormal on only Android or iOS → device-side compatibility issue |
| New/old user | join user table product config `new_user_field` | new version abnormal only for new users → onboarding flow; only for old users → upgrade experience regression |

## Step Three: Judgment Output

- Hit "exclusive abnormal subgroup" → root cause is **that subgroup's problem in the new version** (e.g., new version's some entry broken, some device crash rate high), output factually, do NOT blanket-attribute to "migration".
- No subgroup anomaly hit, each group's intra-group rate uniformly low → root cause is **new version overall entry-experience regression**, suggest regression test / gray rollout rollback.
- Both groups' intra-group rates normal, only share changed → the true "structural migration", only then may you conclude type 4b/5.

## Key Requirements

1. Control-group priority: **prefer "same-cohort before/after upgrade comparison" (step zero, ruling out selection bias)**; when unqueryable, use "same-period old version" intra-group rate comparison (step one). Do NOT use historical-period old version comparison (historical-period aggregate environment differs, not comparable).
2. SQL/event templates: `references/query-templates.md` "Version-difference diagnosis queries" (incl. same-cohort comparison, version × entry-source/OS/new-old SQL).
3. All event names / field names read from product config; do NOT hardcode.
