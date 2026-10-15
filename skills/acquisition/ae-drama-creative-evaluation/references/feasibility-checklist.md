# Data Feasibility Check and Grading Standard (Skill Step 4)

## Five-layer Check Table

Event names and property names vary by project, and must be confirmed from metadata and tested queries. **Do not assume they are necessarily named `register`/`pay`/`creative_id`**.

| Data Layer | Must-check Content | Supportable Conclusions |
|---|---|---|
| Ad platform aggregation layer | Date, channel, campaign, ad group, ad/creative/creative ID, impressions, plays, clicks, spend, frequency | Creative appeal, cost, fatigue trend |
| Attribution layer | Activation/attribution events (commonly the preset event `ta_app_install`), unified creative ID, channel/campaign/ad group, click_id, attribution time, attribution model/window, first/recent source | Attribute post-activation users to creatives, analyze sourced-user quality |
| Product behavior layer | Activation, registration, target drama reached, play, key plot, payment point, order, payment, subscription, retention events | Product conversion, content consumption, payment and retention |
| IAA monetization layer | Ad request/impression/completion, ad placement, ad type, estimated or settled revenue, currency | Ad ARPU, ad LTV, comprehensive ROAS |
| Creative dimension-table layer | Enterprise unified creative ID, platform creative ID, version, drama title, genre, hook, actor, template, duration, batch, launch time | Tag patterns, cross-platform reuse, version derivation relationship |

Note: preset events (`ta_app_install`/`ta_app_start`, etc.) and unregistered custom events **may not appear in the metadata export**, and must be cross-validated against the exact authorized event `table_ref` with SQL `select "#event_name", count(*) ... group by 1`.

## Grading Standard

- **Level A | Full closed loop**: ad aggregation + attribution + product behavior + revenue can all be linked. Can do comprehensive creative evaluation, three-stage diagnosis, and ROAS/LTV.
- **Level B | Post-activation closed loop**: has attribution and product behavior, but no complete impressions/clicks/spend. Can evaluate sourced-user quality, cannot fully evaluate creative appeal and ROAS.
- **Level C | Product conversion analysis**: only product behavior, no reliable creative attribution. Can only analyze content and payment conversion, cannot draw creative conclusions.
- **Level D | Not analyzable**: key events, creative ID, or revenue fields missing. Stop forcing through, output a gap list and data-supplementation recommendations.

When grading, must state: why this level, and which field is missing to upgrade/downgrade.

## 8 High-frequency Issue Verification

1. Whether platform creative ID can map to enterprise unified creative ID;
2. Whether post-activation events continuously carry the source, or can be linked via first-source user properties;
3. Whether first source, recent source, and per-interaction attribution events are all retained;
4. Whether revenue currency, refunds, taxes, and channel revenue share are unified (also check whether failed orders carry amounts);
5. Whether the data window covers D1/D3/D7/L30 maturity period (attribution data start point determines the maximum usable window);
6. Whether there is data both before and after the creative launch, and whether the project data start point is mistaken for the creative launch date;
7. Whether there is a significant discrepancy between platform-reported activations and Shushu real activations;
8. Whether IAA uses estimated or settled revenue, and whether there is catch-up delay.

Label each item as [pass / missing / to confirm].

## Fixed Statement for Missing Fields

> This analysis is limited by [missing data/fields]. We can currently complete [analyzable scope], and cannot reliably answer [non-analyzable questions]. It is recommended to supplement [specific data] before upgrading the conclusion.

## Confirmation Gate (mandatory process)

After completing field checks and grading, **must first present the full evaluation result to the user and wait for confirmation before data retrieval**. Present using assets/confirm-card-template.md, which contains four parts:
1. Layer-by-layer field check result (hit vs missing; fields must be real field names confirmed by metadata/tested queries);
2. Restated evaluation standard and this grading basis;
3. Analyzable vs non-analyzable scope;
4. 8 high-frequency issue verification results.

Confirmation method: prefer the AskUserQuestion tool when available, otherwise ask in text. At minimum cover:
1. Whether the field mapping is accurate - especially key fields such as creative ID, revenue, cost, channel, genre;
2. Whether the feasibility level is accepted;
3. Whether there are missing fields, existing reports, or established calibers to include.

When the user corrects fields, go back to Step 3 to re-verify metadata, then re-present the confirmation card.
