# LTV Prediction - Workflow Phase 1 & 2 (CLI Edition)

## Language Policy

All content in English. Exception: user explicitly requests Chinese.

---

## Phase 1: Prerequisite Check (Interactive Gates)

Execute 3 gates before any analysis. **Stop and ask user if any gate fails.**

### G1: Data Mapping

**Purpose**: Resolve cohort, payment event, and amount property names without guessing.

**Procedure**:

1. Submit the semantic `revenue` or `event` AI-facing definition and inspect
   `meta.resolved`, `meta.warnings`, and structured compiler errors.

2. Only after a clarification/error, run the relevant metadata query:
   ```bash
   ae-cli analysis-meta event list --project-id <id> --format json
   ae-cli analysis-meta property list --project-id <id> --format json
   ae-cli analysis-meta property list --project-id <id> --scope user --format json
   ```

3. Search the returned candidates for payment/purchase/recharge fields.

4. **If no payment event resolves**: Ask user:
   > "What event records successful payments in your project?"
   List candidate events containing keywords like pay, purchase, recharge, charge, buy.

5. **If no amount property resolves**: Ask user:
   > "Which property holds the payment amount?"
   List number-type properties of the found event for selection.

6. **If VIP or RFM tag is unavailable** (for B3): Ask user:
   > "Does your project have VIP level, RFM segmentation, or pay tier tags? If not, B3 (stratified LTV) will use basic pay-tier segmentation instead."

7. Store confirmed names:
   - `PAYMENT_EVENT`: confirmed event display name
   - `COHORT_EVENT`: confirmed registration/acquisition event display name
   - `PAY_AMOUNT_PROP`: confirmed amount property name
   - `VIP_LEVEL_PROP`: confirmed VIP property (if exists)
   - `RFM_TAG`: confirmed RFM tag name (if exists)
   - `PAY_TIER_TAG`: confirmed pay tier tag name (if exists)

**Never proceed without confirmed data mapping.**

### G2: LTV Report Check

**Purpose**: Determine if the project already has LTV reports/dashboards to reuse.

**Procedure**:

1. Search for existing LTV assets:
   ```bash
   ae-cli analysis report list --project-id <id> --queries '["LTV"]'
   ae-cli analysis dashboard list --project-id <id> --queries '["LTV"]' --format json
   ```

2. **If LTV reports exist**: Inform user:
   > "Existing LTV reports found (IDs: X, Y, Z). Should I reuse their data or create fresh ad-hoc queries?"

3. **If no LTV reports**: Proceed with `analysis adhoc run` using an AI-facing definition.

4. **If reports exist but are empty/incomplete**: Fall back to ad-hoc queries.

### G3: Python Environment Check

**Purpose**: Ensure scipy/numpy are available for curve fitting (B2).

**Procedure**:

1. Check availability:
   ```bash
   python3 -c "import numpy; import scipy; print('OK')"
   ```

2. **If import fails**: Ask for approval, then create an isolated environment:
   ```bash
   python3 -m venv "$SKILL_DIR/.venv"
   "$SKILL_DIR/.venv/bin/python" -m pip install -r "$SKILL_DIR/scripts/requirements.txt"
   ```

3. **If installation fails**: Ask user:
   > "Python scipy installation failed. B2 (curve fitting) requires it. Should I proceed with B3 only (no Python dependency)?"

---

## Phase 2: Data Collection

### B2: Cohort LTV Data Collection

**Goal**: Get historical LTV values by day for curve fitting.

**Option A: From existing LTV report** (if G2 found reports):

```bash
# Query report data
ae-cli analysis report-data run --project-id <id> --report-ids '[<LTV_REPORT_ID>]' \
  --start-time "YYYY-MM-DD" --end-time "YYYY-MM-DD"

# Or query from dashboard
ae-cli analysis dashboard-report-data run --project-id <id> --dashboard-id <LTV_DASHBOARD_ID> \
  --start-time "YYYY-MM-DD" --end-time "YYYY-MM-DD"
```

Extract LTV values at day markers (D0, D1, D3, D7, D14, D30) from report data.

**Option B: From ad-hoc query** (if no existing reports):

Use one AI-facing revenue definition to query cohort LTV:

```bash
ae-cli analysis adhoc run \
  --project-id <id> \
  --model-type revenue \
  --definition '{
    "time_range":{"mode":"custom","start_time":"YYYY-MM-DD","end_time":"YYYY-MM-DD"},
    "initial_event":{"event":"<COHORT_EVENT>"},
    "pay_event":{"event":"<PAYMENT_EVENT_DISPLAY_NAME>"},
    "revenue_metric":{"event":"<PAYMENT_EVENT_DISPLAY_NAME>","aggregation":"sum","property":"<PAY_AMOUNT_PROP>"},
    "observation_days":30,
    "selected_metrics":["payAmount","cumPayAmount","ltv"]
  }'
```

Use returned observation-day values to build the cumulative LTV curve. Change
`observation_days` for a longer verified horizon rather than approximating LTV
from unrelated event totals.

**Minimum data points for fitting**: 6 (D0, D1, D3, D7, D14, D30). More points yield better fit.

### B3: Stratified LTV Data Collection

**Goal**: Get per-segment LTV values across RFM, pay-tier, and VIP dimensions.

**RFM Segmentation**:

```bash
# Get RFM tag members and their payment data
ae-cli analysis user-tag list --project-id <id> --queries '["<RFM_TAG>"]'

# Find the tag, then query all returned segments as a group.
ae-cli analysis adhoc run \
  --project-id <id> \
  --model-type revenue \
  --definition '{
    "time_range":{"mode":"custom","start_time":"YYYY-MM-DD","end_time":"YYYY-MM-DD"},
    "initial_event":{"event":"<COHORT_EVENT>"},
    "pay_event":{"event":"<PAYMENT_EVENT_DISPLAY_NAME>"},
    "revenue_metric":{"event":"<PAYMENT_EVENT_DISPLAY_NAME>","aggregation":"sum","property":"<PAY_AMOUNT_PROP>"},
    "observation_days":30,
    "selected_metrics":["payAmount","cumPayAmount","ltv"],
    "groups":[{"field":{"name":"<RFM_TAG>","type":"tag"}}]
  }'
```

**VIP Level Segmentation**:

```bash
# Query per VIP level; use metadata only if compilation needs clarification.

ae-cli analysis adhoc run \
  --project-id <id> \
  --model-type revenue \
  --definition '{
    "time_range":{"mode":"custom","start_time":"YYYY-MM-DD","end_time":"YYYY-MM-DD"},
    "initial_event":{"event":"<COHORT_EVENT>"},
    "pay_event":{"event":"<PAYMENT_EVENT_DISPLAY_NAME>"},
    "revenue_metric":{"event":"<PAYMENT_EVENT_DISPLAY_NAME>","aggregation":"sum","property":"<PAY_AMOUNT_PROP>"},
    "observation_days":30,
    "selected_metrics":["payAmount","cumPayAmount","ltv"],
    "groups":[{"field":{"name":"<VIP_LEVEL_PROP>","type":"user_property"}}]
  }'
```

**Pay-Tier Segmentation** (only when a cumulative-payment user property is
compiler-resolved or explicitly confirmed):

```bash
# Group by the confirmed cumulative-payment user property
ae-cli analysis adhoc run \
  --project-id <id> \
  --model-type revenue \
  --definition '{
    "time_range":{"mode":"custom","start_time":"YYYY-MM-DD","end_time":"YYYY-MM-DD"},
    "initial_event":{"event":"<COHORT_EVENT>"},
    "pay_event":{"event":"<PAYMENT_EVENT_DISPLAY_NAME>"},
    "revenue_metric":{"event":"<PAYMENT_EVENT_DISPLAY_NAME>","aggregation":"sum","property":"<PAY_AMOUNT_PROP>"},
    "observation_days":30,
    "selected_metrics":["payAmount","cumPayAmount","ltv"],
    "groups":[{"field":{"name":"<CONFIRMED_TOTAL_PAY_PROPERTY>","type":"user_property"}}]
  }'
```

Use the confirmed property to classify tiers:
- **Micro payer**: 0 < value <= threshold_1
- **Small payer**: threshold_1 < value <= threshold_2
- **Medium payer**: threshold_2 < value <= threshold_3
- **Large payer**: threshold_3 < value <= threshold_4
- **Whale**: value > threshold_4

Derive thresholds from the observed payer distribution. If no cumulative-payment
property or pay-tier tag exists, skip this dimension and state the data gap;
never invent `total_pay_amount`.
