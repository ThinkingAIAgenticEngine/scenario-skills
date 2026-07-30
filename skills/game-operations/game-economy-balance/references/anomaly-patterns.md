# Economy System Anomaly Pattern Recognition Rules

> **Core Principle**: Anomaly recognition must be based on quantitative rules; do not rely on intuition alone. Every anomaly determination must be backed by specific data.

---

## I. Anomaly Type Classification

### 1.1 Four Major Anomaly Types

| Anomaly Type | Definition | Core Harm |
|---------|------|---------|
| **Studio** | Organized bulk control of multiple accounts to farm resources | Large resource volumes flow into the black market, disrupting the normal economic order. |
| **Cheat / Script** | Using automated tools in place of manual operation | Resource acquisition efficiency far exceeds normal players; anomalous production. |
| **Exploit Abuse** | Using game bugs to acquire resources beyond design expectations | Sudden resource surges can instantly break economy balance. |
| **Anomalous Trade (RMT)** | Transferring resources at prices far below market value, linked to real-currency trade | Resources flow from legal channels to the black market; currency devaluation. |

---

## II. Studio Recognition Rules

### 2.1 Multi-Account Features

| Feature Dimension | Recognition Rule | Threshold | Data Source |
|---------|---------|------|---------|
| Same-IP Account Count | Active accounts under the same IP address | ≥5 | generate-sql (grouped by IP) |
| Same-DID Account Count | Active accounts under the same device ID | ≥3 | generate-sql (grouped by DID) |
| Registration Time Concentration | Registration-time distribution of accounts under the same IP | ≥3 registered within 24h | User property + registration time |
| Behavior Sync | Behavior-time distribution of accounts under the same IP | Behavior trigger times highly synchronized (multiple accounts triggered within the same minute) | Event timestamp analysis |

### 2.2 Farming Behavior Features

| Feature Dimension | Recognition Rule | Threshold | Notes |
|---------|---------|------|------|
| Daily Production | Per-account daily average resource production | >Server-wide P90 × 2 | Studio-account production far exceeds normal. |
| Production Concentration | Per-account production source-point distribution | 90%+ of production concentrated on 1~2 source points | Studios only farm the most efficient points. |
| Very Low Consumption | Per-account daily average consumption/production ratio | <0.1 | Studio accounts barely consume; pure production. |
| Behavior Repetition | Repetition rate of the same operation sequence | >80% | Repeats the same behavior sequence daily. |
| Trade Outflow | Resource transfer destination | Large resource volumes transferred at low prices to fixed accounts | Resources flow to "buyer accounts." |

### 2.3 Studio Determination Flow

```
Step 1: Identify high-production accounts (daily production > P90 × 2)
Step 2: Check whether they belong to a same-IP/DID cluster
  → Yes: Tag as a studio cluster
  → No: Go to Step 3
Step 3: Check production-concentration and very-low-consumption features
  → Production concentration >90% AND consumption/production <0.1: Tag as suspected studio
  → No: Go to Step 4 (cheat detection)
```

---

## III. Cheat / Script Recognition Rules

### 3.1 Automated Behavior Features

| Feature Dimension | Recognition Rule | Threshold | Notes |
|---------|---------|------|------|
| Quest Completion Frequency | Daily average completion count of the same quest/level | >50 times/day | Normal players <20 times/day. |
| Operation Interval | Time interval between two operations | <3 seconds and highly regular | Automated scripts have fixed operation intervals. |
| Daily Online Duration | Per-account daily average online duration | >12 hours | Normal players average 2~4 hours/day. |
| Operation Consistency | Execution path of the same operation is identical | Each operation step is 100% identical | Script execution paths have no randomness. |
| Reaction Time | Response time after an event is triggered | <0.5 seconds | A reaction speed impossible for human players. |

### 3.2 Cheat Determination Flow

```
Step 1: Identify high-frequency-operation accounts (daily quest completion >50 OR daily online >12h)
Step 2: Check operation-interval regularity
  → Interval <3 seconds and variance is tiny: Tag as cheat
  → No: Go to Step 3
Step 3: Check the difference in production source points vs. normal players
  → Production-only no consumption (consumption/production <0.2) OR production concentrated on script-farmable points: Tag as suspected cheat
```

---

## IV. Exploit-Abuse Recognition Rules

### 4.1 Sudden-Anomaly Features

| Feature Dimension | Recognition Rule | Threshold | Notes |
|---------|---------|------|------|
| Single-Acquisition Amount | Resource amount acquired in a single event | >Normal value × 10 | Exploit causes anomalous single-acquisition volume. |
| 24h Total Acquisition | Total acquisition within 24 hours | >Previous 7-day daily average × 5 | Sudden large surge. |
| Impact Scope | Number of affected users | A few users suddenly high-production | Exploits are usually found and abused by a small group. |
| Time Distribution | Time distribution of anomalous acquisition | Concentrated in early morning or specific windows | Exploit abusers trigger under specific conditions. |
| Acquisition Channel | Trigger condition for resource acquisition | Triggered via non-standard channels | E.g., a normal level but with anomalous acquisition volume. |

### 4.2 Exploit Determination Flow

```
Step 1: Identify surge days (24h acquisition > previous 7-day daily average × 5)
Step 2: Check whether it is a known activity effect
  → A double-production event launched recently: Tag as normal activity effect
  → No: Go to Step 3
Step 3: Check whether single-acquisition amount is anomalous
  → Records exist with single-acquisition amount > normal value × 10: Tag as exploit abuse
  → No: Go to Step 4 (studio/cheat investigation)
Step 4: Check time-distribution anomaly
  → Anomalies concentrated in specific windows (e.g., 2~5 AM): Tag as suspected exploit abuse
```

---

## V. Anomalous-Trade (RMT) Recognition Rules

### 5.1 Anomalous-Trade Features

| Feature Dimension | Recognition Rule | Threshold | Notes |
|---------|---------|------|------|
| Trade Price | Transaction price / market average price | <0.5 | Anomalously low-price resource transfer. |
| Trade Frequency | Trade frequency between two accounts | Same account pair trades ≥3 times/day | Repeatedly transferring between the same pair. |
| Trade Direction | Resource flow direction | One-way flow (A→B, but B→A minimal) | Seller accounts only output to buyer accounts. |
| Associated Behavior | Behavior correlation between buyer and seller | Seller high-production low-consumption + Buyer high-consumption low-production | The studio-production → High-Spender-consumption chain. |
| Trade Scale | Single-trade volume / server-wide daily average trade volume | >1% | A single trade is too large a share of server-wide trade. |

### 5.2 RMT Determination Flow

```
Step 1: Identify anomalous low-price trades (transaction price < market average × 0.5)
Step 2: Check trade direction
  → One-way flow (seller → buyer): Tag as suspected RMT
  → Two-way flow (normal trade): Exclude
Step 3: Check buyer/seller behavior profiles
  → Seller: high-production low-consumption (studio feature) + Buyer: high-consumption (High Spender feature): Confirm the RMT chain
```

---

## VI. Comprehensive Anomaly Diagnosis Matrix

When multiple anomaly features appear simultaneously, use the following matrix for comprehensive determination:

| Feature Combination | Most Likely Type | Recommended Action |
|---------|----------|---------|
| Same-IP multi-account + high-production low-consumption + production concentration | Studio | Ban cluster + IP restriction |
| High-frequency operation + fixed interval + long online | Cheat | Anti-cheat detection + ban |
| Surge day + single-acquisition anomaly + concentrated window | Exploit | Emergency fix + data rollback |
| Anomalous low price + one-way + high-production seller | RMT | Trade restriction + ban seller |
| High-frequency operation + same-IP multi-account | Studio + Cheat | Ban cluster + anti-cheat |
| Surge day + high-frequency operation | Exploit + Cheat | Fix + ban + anti-cheat |

---

## VII. Anomaly Impact Assessment Framework

### 7.1 Anomalous-Production Contribution Calculation

```
Anomalous-User Total Production = Σ(Production of users tagged as anomalous)
Anomalous Contribution Share = Anomalous-User Total Production / Server-Wide Total Production × 100%
Corrected Production-Consumption Ratio = (Server-Wide Total Production - Anomalous-User Total Production) / Server-Wide Total Consumption
```

### 7.2 Impact Severity Grading

| Anomalous Contribution Share | Severity | Response Requirement |
|------------|-------|---------|
| <5% | Minor | Log and monitor; handle in daily routine. |
| 5%~15% | Moderate | Dedicated crackdown; handle within 7 days. |
| 15%~30% | Severe | Emergency crackdown; handle within 3 days. |
| >30% | Extreme | Top priority; handle same day. |

### 7.3 Re-evaluation After Correction

After excluding anomalous users, recompute the production-consumption ratio and determine:
- Corrected ratio returns to the reasonable range → Cracking down on anomalies alone solves the problem.
- Corrected ratio still deviates → Intervention strategy still needed (enter Branch D).
