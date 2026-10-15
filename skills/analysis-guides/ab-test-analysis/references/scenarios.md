# Scenario Playbook

Reference for **Step 0b (field alignment)** and **Step 1 (query)**. Locate the row that matches the user's
situation, then start from that scenario's default metric caliber. The defaults below are a *starting
point* for the Step 0b questions — every one of them must still be confirmed with the user, and every
field name must still be verified against the project's real metadata before it is used in a query.

## 1. Industry / business scenarios

| Industry / scenario | Typical role | The user's own words (the pain) | What this skill returns |
|---------------------|--------------|--------------------------------|-------------------------|
| E-commerce / payment conversion — checkout button, order page, coupon threshold redesign | Growth PM, data analyst | "The new checkout page lifted conversion by 0.3pp — is that real, or noise? Do we dare roll it out?" | Proportion z-test on conversion + confidence interval + MDE, with a ship / extend / gradual recommendation |
| E-commerce / AOV and revenue — pricing page, bundling, free-shipping threshold | Business analyst, operations | "Revenue per user is up but the paying rate is down — are we net ahead or behind?" | Joint verdict over several metrics (proportion + continuous), naming which metric the decision actually rests on |
| Gaming / onboarding and monetisation — tutorial, first-purchase pack, event popup | Game ops, producer | "D7 retention dropped — is it the release, or did the new pack scare users off?" | Retention z-test plus guardrail checks, separating "the intended effect" from "the side effect" |
| Gaming / release rollout — a major version opened to 5% of traffic | Publishing / ops lead | "Is the crash rate on the rollout build over the line? Can we widen the rollout?" | Guardrail metric (crash rate / force-quit rate, `lower_is_better: true`) significance verdict |
| Content and social / recommendation strategy — feed ranking, recall strategy, push copy | Recommendation engineer, content ops | "The new ranking lifted time-per-user but D1 retention did not move — is that a win?" | Primary metric plus several guardrails, judged together, to avoid "one metric went up so we won" |
| SaaS / B2B — signup onboarding, trial flow, pricing page | PM, growth lead | "Trial-to-paid improved, but ticket volume went up too — is it worth shipping?" | Conversion test plus a support-ticket-volume guardrail test (`lower_is_better: true`) |
| Paid acquisition / landing page and creative A/B | Acquisition optimizer, growth | "Creative B cut signup cost by 12% — is the sample big enough to trust?" | Small-sample warning + post-hoc MDE, stating plainly that "the sample is insufficient, the conclusion is unusable" |
| Presales / customer conversation — a customer brings their own experiment data | Solutions engineer, presales consultant | "The customer ran an experiment but dare not conclude — can you take a look?" | General two-sample analysis plus a deliverable HTML report the customer can cite directly |

## 2. Role-specific emphasis (decides which part of the report to lead with)

| Role | Cares most about | Read first in the report |
|------|------------------|--------------------------|
| Data analyst | Test method, assumptions, sample size | Statistical methodology + MDE + power analysis |
| Product / operations | Whether the conclusion can be acted on | Verdict banner + per-metric recommendation cards + action plan |
| Business owner | Risk | Guardrail banner + limitations |
| Presales / solutions | Whether the deliverable can be shown to a customer | The full HTML report + data source and caliber |

## 3. Default metric caliber per scenario

The caliber decides how the Step 1 query must be shaped. `scripts/check_query_definition.py` enforces
it before the query is sent — see `references/ae_cli_query_patterns.md` for the templates.

| Scenario | Primary metric | `type` | Caliber |
|----------|----------------|--------|---------|
| Checkout / signup / trial conversion | Conversion rate (success users / exposed users) | `proportion` | Caliber 1 — funnel: step 1 = exposure, step 2 = success + conversion window |
| AOV / revenue per user | Revenue per exposed user | `continuous` | Caliber 2 — one-row-per-exposed-user distribution including zeros; aggregates are descriptive only |
| Retention / churn | D1 / D7 retention | `proportion` or nested `retention` | Caliber 3 — nested `retention` object when the platform models retention natively |
| Release rollout / stability | Crash rate, force-quit rate, ANR rate | `proportion` + `is_guardrail: true` + `lower_is_better: true` | Caliber 1 — the harmful direction is an increase |
| Support load | Ticket volume, refund rate | `proportion` + `is_guardrail: true` | Caliber 1 — per exposed user, not per ticket holder |
| Latency / performance | Response time, load time, stuck rate | `continuous` + `is_guardrail: true` + `lower_is_better: true` | Caliber 2 — user-level exposed-cohort distribution for inference |

## 4. Which questions the scenario forces you to ask

Regardless of scenario, Step 0b must end with these six answers recorded in `field_mapping.json`:

1. Which project? (`project_id`)
2. Which event or user property stores the A/B assignment, and is it `event_property` or `user_property`?
3. Which events measure success, and which measure harm (guardrails)?
4. What is the experiment time range, and which mode (does `recent` include today)?
5. Any global filters (platform, country, channel)?
6. What is the data volume per group — does it clear the 100-per-group floor?

## 5. Scenario-specific pitfalls

| Scenario | Frequent mistake | Consequence |
|----------|------------------|-------------|
| Conversion | Querying success users and exposed users as two independent `user_count` rows | The success row can contain users who were never exposed; conversion rate > 100% |
| Revenue per user | Using `avg` + `stddev` over the purchase event, paired with the paying-user count | That distribution is payers-only, so the mean is ARPPU and n is not the cohort — the t-test answers a different question than the report claims |
| Retention | Using flat top-level `initial_event` / `return_event` | The platform silently ignores the window; the retention definition is no longer what the report says |
| Guardrails | Leaving polarity unset and letting the engine infer it | The harmful direction may be reported as an improvement — always declare `lower_is_better` for the metrics that matter |
| Paid acquisition | Reading a 12% cost drop off a few hundred users | Under-powered experiment; report the MDE and say the conclusion is unusable |
| Presales / customer data | Accepting the customer's own group definition without checking the value domain | Dirty values (null / internal-test groups) dilute the difference and can flip the verdict |
