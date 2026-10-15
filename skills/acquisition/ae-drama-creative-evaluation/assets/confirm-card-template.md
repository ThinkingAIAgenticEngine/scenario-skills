# Data Feasibility Evaluation Confirmation Card (Template)

> Usage rule: mandatory in Skill Step 4. All field names must be real field names confirmed by metadata / tested queries; guessing names is forbidden. After presenting, **stop and wait for user confirmation**, and proceed to formal data retrieval only after confirmation or correction.

## (1) Layer-by-layer field check result (hit vs missing)

| Data Layer | Hit Fields (real field names) | Missing Fields | Supportable Conclusions |
|---|---|---|---|
| Ad platform aggregation layer | <e.g., none / impression event xxx> | <impressions/clicks/spend/frequency...> | <whether CTR/cost/fatigue can be evaluated> |
| Attribution layer | <e.g., ta_app_install carrying media_source/campaign/ad_id; user property xxx> | <click_id/attribution window/first-last source...> | <whether post-activation behavior can be attributed to creatives> |
| Product behavior layer | <registration/play/payment/retention events and success-status fields> | <...> | <...> |
| IAA monetization layer | <ad-complete event + revenue field + platform/ad placement> | <settlement caliber...> | <...> |
| Creative dimension-table layer | <creative tag dimension table> | <genre/hook/actor/template...> | <...> |

## (2) Evaluation standard and grading

- Level A | Full closed loop: ad aggregation + attribution + product behavior + revenue can all be linked
- Level B | Post-activation closed loop: has attribution and product behavior, no complete impressions/clicks/spend
- Level C | Product conversion analysis: only product behavior, no reliable creative attribution
- Level D | Not analyzable: key events / creative ID / revenue fields missing

**This grading: <_ level>**; grading basis: <why>; key field to upgrade/downgrade: <which field is missing>.

## (3) Analyzable vs non-analyzable scope

- This time we can reliably answer: <...>
- This time we cannot reliably answer: <...>
- Fixed statement: This analysis is limited by [missing data/fields]. We can currently complete [analyzable scope], and cannot reliably answer [non-analyzable questions]. It is recommended to supplement [specific data] before upgrading the conclusion.

## (4) High-frequency issue verification

| # | Check Item | Result (pass/missing/to confirm) |
|---|---|---|
| 1 | Platform creative ID -> enterprise creative ID mapping | |
| 2 | Post-activation events carrying source / user property persistence | |
| 3 | First/last/per-interaction attribution distinction | |
| 4 | Currency/refund/revenue-share unification (including failed-order amount check) | |
| 5 | D1/D3/D7/L30 window coverage | |
| 6 | Creative launch date vs data start point | |
| 7 | Platform-reported activation vs real activation discrepancy | |
| 8 | IAA estimated/settlement caliber | |

## 3 questions awaiting user confirmation

1. Is the field mapping accurate? (creative=< >, channel=< >, activation=< >, payment=< >, IAA revenue=< >, retention=< >)
2. Do you accept the <_> level grading?
3. Are there missing fields, existing reports, or established calibers to include? What is the primary decision question (cross-evaluation / single-creative diagnosis / channel fit / lifecycle / system building)?
