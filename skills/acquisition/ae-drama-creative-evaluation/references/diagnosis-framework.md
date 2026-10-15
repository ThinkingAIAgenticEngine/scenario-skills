# Three-stage Diagnosis, Evidence Strength, and Business Classification (Skill Step 8)

## Three-stage Diagnosis Framework

Diagnose first, then classify. Do not rank solely by a single score.

| Diagnosis Layer | Typical Signal | Priority Explanation |
|---|---|---|
| Poor attraction efficiency | Shallow play, low CTR, while other creatives under the same conditions are normal | Insufficient creativity, opening, hook, cover, copywriting, or channel fit |
| Poor acquisition efficiency | High CTR but low activation/registration | Clickbait, mis-clicks/abnormal traffic, landing page, store page, attribution loss |
| Poor value efficiency | Normal activation/registration but low viewing/payment/retention | Mismatch between creative promise and content, target drama reach, insufficient plot or payment conversion |
| Normal pre-funnel but good post-funnel | CTR unremarkable but high LTV/ROAS | Precision-screening creative; should not be eliminated just because CTR is low |

Under Level B data (no ad pre-funnel), the attraction efficiency layer must be explicitly labeled "not evaluable". Only activation volume may be used as a creative volume proxy, and the limitation of that proxy must be explained (stable activation volume may simply be the result of a constant budget).

## Diagnostic Points (supplemented from practice)

- **Post-registration catch-up**: for creatives with low D0 registration rate, check whether D7 cumulative registration rate catches up - if the catch-up is significant, the D0 gap does not equal acquisition loss.
- **Viewing depth is a divider**: low payment but viewing depth (per-user episodes/duration) on par with other creatives -> leans toward "audience willingness to pay / payment-point reach" issue; viewing depth dropping in tandem -> leans toward "creative promise inconsistent with content".
- **Payment structure check**: break down the order structure of each creative by payment item (payment_name). When a specific tier (e.g., large gift pack) is 0 for a creative, first investigate the reach pipeline (recharge popup exposure coverage) rather than jumping to an audience conclusion.
- **Creative x channel fit vs channel quality**: large LTV differences across creatives on the same channel -> supports the "fit" explanation; the same creative performing poorly across all channels simultaneously -> supports the "creative/audience" explanation.

## Evidence Strength Labeling

Use "evidence strength", not the statistical term "confidence":

- **High**: consistent same-condition controls, mature samples, multiple mutually corroborating metrics, few confounders;
- **Medium**: reasonable evidence exists, but channel, audience, time-period, or product factors still confound;
- **Low**: insufficient samples (e.g., cell <100 activations), incomplete caliber, or only a single metric anomaly; requires experiments or additional data.

## Business Classification Matrix

| Type | Pre-funnel | Post-funnel | Action |
|---|---|---|---|
| Viral high-value | High | High | Continue scaling up, decompose and reuse creative elements |
| Viral low-value | High | Low | First check acquisition and conversion, do not directly blame the creative |
| Low-volume high-value | Average/low | High | Optimize cover and opening, retain precise value |
| Low-volume low-value | Low | Low | Pause or redo after reaching the threshold |

## Early Prediction Limitations

T+0/T+1 can only serve as predictive metrics. The correlation and stability between early behavior and D7 ROAS/LTV must first be validated against historically mature creatives before forming a prediction score; unvalidated early behavior must not be treated directly as final quality.

## Pre-submission Self-check List

- [ ] Did I misstate comprehensive placement performance as pure creative quality?
- [ ] Did I look only at CTR and miss activation, viewing, payment, retention, and revenue?
- [ ] Did I treat ad-platform aggregated impressions/clicks as user-level event funnel?
- [ ] Did I unify platform creative ID with enterprise creative ID?
- [ ] Did I consider first source, recent source, and per-interaction attribution events simultaneously?
- [ ] Did I distinguish ROAS from ROI, and label the maturity window?
- [ ] Did I misplace CPI as a long-term value metric?
- [ ] Did I add IAA ad revenue and catch-up delay?
- [ ] Did I control confounders such as channel, audience, time period, bidding, and lifecycle?
- [ ] Did I check minimum sample size and cohort maturity?
- [ ] Did I mistake T+0 prediction score for the final result?
- [ ] Did I label evidence strength for root causes and explain items to verify?
- [ ] Before ae-cli queries, did I prioritize reusing and verifying existing report calibers?
- [ ] When fields or data are insufficient, did I clearly state the downgraded scope instead of forcing through?
- [ ] Did I stop to present the confirmation card after feasibility evaluation, and wait for user confirmation of fields and level before continuing data retrieval?
- [ ] Were the success-status filter conditions for registration/payment/ad revenue tested and verified?
