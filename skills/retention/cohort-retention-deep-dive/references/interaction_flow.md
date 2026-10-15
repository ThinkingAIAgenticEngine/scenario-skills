# Cohort Retention Deep Dive - Interaction Flow

Complete 6-step workflow. Step 0 is mandatory before any query. Follow steps in order; do not expose later-step content before the current step is confirmed.

## Step 0 - Align the Retention Definition (do this first)

Retention definitions differ per project. Before composing any query, confirm and record all five items below; do not assume defaults.

| # | Item | Ask / confirm | Why it matters |
|---|------|---------------|----------------|
| 1 | Active / return events | Which events count as "active" (any event vs a specific session / app-open / login event), and which count as "returned"? Confirm exact event names. | A wrong active event silently shifts every cohort |
| 2 | Dedup dimension | `#user_id`, `#account_id`, or `#distinct_id`? Which key is the retention denominator? | Different dedup keys give different denominators |
| 3 | Bounded vs unbounded | Does "D7 retention" mean "returned exactly on day 7" (bounded) or "returned on day 7 or later" (unbounded)? | Changes both the level and the curve shape |
| 4 | Day-0 offset | Is D1 the next calendar day after day 0, or day 0 itself? Confirm the +1 offset. | A one-day offset shifts every D{N} |
| 5 | Cohort-entry definition | What starts the cohort: a confirmed initial event, registration, or first active day? | Cohorts differ by entry condition |

If the user quotes a retention figure from an existing dashboard or report, reconcile your computed number against it before diagnosing. A mismatch means the definition is not yet aligned — stop and reconcile (or route to `retention-verification`), do not diagnose on a mismatched metric.

## Step 1 - Define Scope

Collect the following. Ask only what is missing; infer the rest from context where safe.

| Parameter | Options | Default |
|-----------|---------|---------|
| Product type | game / app / e-commerce / content | ask |
| Retention model | generic cohort / active-user | ask |
| Target metrics | D1 / D7 / D30 / custom N-day | D7 (D1+D30 as context) |
| Time range | e.g. "last 30 days" or explicit dates | ask |

If the user's wording already routes elsewhere (numbers don't match, new-user quality/acquisition/first-day attribution, want a metric, define churn, levels, drama, repurchase), hand off per the Boundary Routing table before proceeding.

## Step 2 - Collect Parameters

| Parameter | Notes |
|-----------|-------|
| `project_id` | required; never guess |
| Time range | confirmed start/end for the retention cohort window |
| Churn definition | only if layering needs a churned-user slice (default: 7 days inactive) |

Confirm the project timezone. If unknown, ask or read the project configuration; a wrong timezone corrupts day-0 boundaries.

## Step 3 - Event & Property Discovery

1. Discover the "active/return" event(s) that define retention (session start, app open, login).
2. Discover candidate key-behavior events for Module 4.
3. Discover segment properties for Module 2 (channel, version, device, pay status).
4. Confirm all names with the user before composing queries. Never fabricate event or property names.

## Step 4 - Diagnose

Run Module 1 first, then only the modules required by the user's question. Keep the user informed between modules; do not dump every module at once. After Module 1, tell the user which module is next and why. Do not produce an optimization ranking when no diagnostic module produced a supported candidate.

## Step 5 - Hand Off

Produce the report from `report_template.md`, ending with the standard next-step menu. If the user picks a lever to validate, route to `ae-experiment-design` with the exact breakpoint, segment, and behavior carried over.

## Production Limits

- Report at most 5 segment-effect rows and 5 lever rows; fold the rest into "Other" while preserving totals.
- Do not classify any slice with n < 50.
- Recommend analysis on T-1 or earlier data; flag incomplete "today" cohorts.
