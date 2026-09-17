# Data Feasibility Check Standard

Detailed operations and criteria for Step 3 (confirm data feasibility). This step is where version comparison is most prone to failure — **you MUST confirm both sides of the comparison window have data before writing queries**.

## Fields That Must Be Confirmed

### 1. Version-number property

Probe commands:
```bash
ae-cli analysis-meta event list --project-id <PID>
ae-cli analysis-meta property list --project-id <PID> --scope event
ae-cli analysis-meta property list --project-id <PID> --scope user
```

Look for fields whose names contain version/app_ver/client_ver/build/app_version (including preset fields like `#app_version`; field names vary by project). Note:
- Check **both** event properties and user properties (user properties may have a "current version" tag)
- Field names vary by project; do not assume it must be `app_version` (e.g. the card game demo uses `#app_version`)
- After finding the field, retrieve its candidate values with `ae-cli analysis filter-value list --project-id <PID> --property-name <FIELD> --table-type <event|user>` (and `--event-name <EVENT>` for an event property). Confirm the target value and baseline value(s) with the user.
- Treat missing/empty/unknown values as a separate data-quality group. Do not fold them into the baseline with a `neq` filter.

**Decision result**:
| Situation | Comparison that can be done |
|------|-----------|
| Has a version-number property | Dual approach (time comparison + updated/not-updated cohort comparison) |
| No version-number property | Time comparison only; the report must state "cohort comparison is not possible" |

### 2. Core behavior events

Whether key events such as login / launch / level / payment are complete. If a corresponding event is missing, the corresponding metric cannot be computed.

### 3. Payment event and amount property (monetization goals only)

Payment event + amount property (e.g. pay_amount). The correct event that the amount property is attached to must be determined (e.g. "online duration" is attached to logout, not login; probing the wrong one yields `No property matched`).

## The Most Critical Pitfall: No Data on Either Side of the Comparison Window

**This is the most frequent failure point.** The "launch date" the user provides may not be the real data boundary. Two common cases:

1. **The project's entire data starts after the "launch date"** → the "pre-launch" window has no data at all, making time comparison impossible.
2. **Tracking started reporting before the feature launched** → data is stable both before and after the "launch date", with no discontinuity found, meaning that day is not the real launch date.

**Mandatory verification** (run this before formal queries to confirm the boundary is reasonable):

```sql
-- Check daily data volume around the boundary day to confirm whether there is a "from nothing" or "obvious jump"
SELECT "$part_date" as d, count(*) as total_events,
       count(distinct CASE WHEN "#event_name"='<target event>' THEN "#user_id" END) as target_uv
FROM <event table>
WHERE "$part_date" >= '<D-7>' AND "$part_date" <= '<D+7>'
GROUP BY "$part_date" ORDER BY d
```

**Judgment**:
- Target event is 0 before the boundary day and appears after it → ✅ boundary holds, comparison is possible
- Target event is stable both before and after → ⚠️ boundary does not hold, it may not be the real launch date; pause and tell the user honestly
- No data at all (including login) before the boundary day → ⛔ that is the entire project's data start point, not the feature launch date

The boundary probe may include D to inspect the launch spike. The formal default comparison excludes D and uses D-7..D-1 versus D+1..D+7.

## Discipline When Fields Are Missing

> Clearly tell the user "this analysis is limited by the missing XX field and can only achieve YY", **do not force it**.

Do not fabricate conclusions just to produce a report. It is better to downgrade the analysis scope (e.g. time comparison only, or retention-difference analysis only) and honestly state the limitations.
