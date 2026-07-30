# Economy System Intervention Strategy Template Library

> **Core Principle**: Intervention strategies must have quantified parameters. Do not just say "reduce production" without specifying by how much. All strategies must compute the expected contribution to ensure the combination covers the required adjustment.

---

## I. Over-Production (Inflation Tendency) Intervention Strategies

### 1.1 Production-Reduction Strategies

#### Strategy A: Slightly Lower Production RNG Range

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Decrease Rate | 5%~15% | Too large a decrease may affect player experience; recommend 2~3 gradual steps. |
| Affected Source Points | Top 1~2 source points by production share | Target main production sources; avoid across-the-board production cuts. |
| Implementation Cycle | 2~4 weeks of gradual adjustment | After each adjustment, observe 7 days of data before deciding whether to continue. |
| Rollback Condition | Payment Rate down >5% or Retention down >3% | Immediately roll back to pre-adjustment parameters. |

**Expected Effect**: Production total down 5%~15%.

**Risk Notes**:
- Players may perceive "fewer rewards," reducing satisfaction.
- Recommendation: Launch in sync with a consumption-discount event to divert player attention.

---

#### Strategy B: Shrink Daily Production

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Shrink Rate | 10%~20% | Shrink daily-quest rewards / sign-in rewards. |
| Shrink Scope | Non-core production channels | Do not shrink payment-channel production; avoid impacting the payment experience. |
| Implementation Method | Adjust the quest reward config table | One-time adjustment; observe 7 days of data. |
| Player Notification | Recommend NOT notifying directly | Minor daily-reward tweaks usually do not need an announcement. |

**Expected Effect**: Production total down 10%~20%.

**Risk Notes**:
- Daily-quest completion rate may drop (reduced rewards lower motivation).
- Recommendation: While shrinking daily rewards, add non-resource rewards such as experience/reputation to compensate.

---

#### Strategy C: Limit Farming Count / Frequency

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Limit Method | Daily acquisition count cap | Set a per-source-point daily acquisition cap. |
| Cap Value | Set based on normal-user P90 | Does not affect normal players; only limits anomalous farming. |
| Applicable Scope | Suspicious source points first | Set caps on anomalous source points first, then expand gradually. |
| Effect on Studios | Significant | Studios rely on high-frequency farming; count limits hit them directly. |

**Expected Effect**: Production total decrease depends on the anomalous-user contribution share (if anomalous users account for 20%, production can drop 20%).

**Risk Notes**:
- Normal players may occasionally exceed the cap and be limited.
- Recommendation: Set the cap value above P95 so only a tiny fraction of players are affected.

---

### 1.2 Consumption-Boost Strategies

#### Strategy D: Consumption-Promo Event (Discount / Rebate)

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Event Type | Enhance discount / Repair discount / Consumption rebate | Choose the event type with the lowest current consumption. |
| Discount Rate | 20%~50% | E.g., Enhance 20% off, Repair 50% off. |
| Event Duration | 3~7 days | Too short has limited effect; too long may overdraw subsequent consumption. |
| Rebate Method | Spend N, rebate M% | E.g., "Enhance spend rebates 20% of materials." |
| Event Cadence | Once every 2~3 weeks | Not too frequent; avoid consumption fatigue. |

**Expected Effect**: Consumption up 10%~30% (during the event).

**Risk Notes**:
- Consumption may drop back after the event ends (retaliatory hoarding).
- Recommendation: Continuously observe 7 days of consumption data post-event; fine-tune production if needed.

---

#### Strategy E: Add New Consumption Channels

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Channel Type | New gear advancement / new progression line / appearance system | Sustained consumption, not one-time. |
| Consumption Target | Daily consumption = current gap | Design the consumption to exactly fill the production-consumption gap. |
| Launch Method | Release in sync with a version update | Player acceptance is higher when accompanying new content. |
| Consumption Gradient | Low → Mid → High tiered | Low Spenders consume less / High Spenders more; balance across tiers. |

**Expected Effect**: Consumption up 5%~20% (sustained, non-event type).

**Risk Notes**:
- If poorly designed, the new consumption channel may only consume High Spenders' resources; Mid/Low Spenders feel nothing.
- Recommendation: Design gradient consumption so every payment tier has a consumption motive.

---

#### Strategy F: Consumption Guidance (UI / Mechanism Optimization)

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Guidance Method | Red-dot prompt / one-tap enhance / recommended consumption | Optimize UI so players trigger consumption more easily. |
| Applicable Scenario | Players with resource balance but no consumption | Target hoarding users. |
| Implementation Cost | Low | UI tweak; no version update needed. |
| Effect Evaluation | Observe the change in consumption-event trigger rate | Evaluate whether the guidance lifts the consumption rate. |

**Expected Effect**: Consumption up 3%~10% (gentle guidance type).

---

## II. Over-Consumption (Deflation Tendency) Intervention Strategies

### 2.1 Production-Boost Strategies

#### Strategy G: Production-Promo Event (Double / UP)

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Event Type | Level double production / stamina potion giveaway / limited-time drop UP | Pick the channel with currently low production to boost. |
| Increment Multiplier | 1.5~2x | Double production or drop-rate UP. |
| Event Duration | 3~7 days | Same as consumption-promo events. |
| Event Cadence | Once every 2~3 weeks | Same as consumption-promo events. |
| Stamina Companion | Give away stamina potions | Double production needs companion stamina; otherwise player participation is limited. |

**Expected Effect**: Production up 30%~100% (during the event).

**Risk Notes**:
- Production drops back after the event; may cause event-period hoarding.
- Recommendation: Precisely calculate the event-period production increment to avoid over-compensation.

---

#### Strategy H: Direct Resource Injection (Mail / Sign-in)

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Injection Method | Mail distribution / sign-in reward boost | Unconditional resource giveaway. |
| Daily Injection | = Current daily gap | Precisely calculated to exactly fill the gap. |
| Injection Cycle | 7~14 days | Continuous injection until the production-consumption ratio returns to the reasonable range. |
| Tiering Design | High Spenders less / Low Spenders more | During deflation, Low Spenders feel it most; prioritize compensating them. |

**Expected Effect**: Production up 5%~15% (steady increment type).

**Risk Notes**:
- Long-term mail distribution may foster a "wait for mail" habit, reducing self-driven production.
- Recommendation: Taper off after the injection period rather than stopping abruptly.

---

#### Strategy I: Boost Daily Production

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Boost Rate | 10%~20% | Boost daily-quest rewards / base level production. |
| Boost Scope | Low-difficulty levels first | Lower the new-player acquisition difficulty. |
| Implementation Method | Adjust config tables | Sustained adjustment, non-event type. |
| Companion Measure | Lower daily completion conditions | Lower quest completion difficulty to lift the participation rate. |

**Expected Effect**: Production up 10%~20% (sustained).

---

### 2.2 Consumption-Reduction Strategies

#### Strategy J: Consumption-Waiver Event

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Event Type | Free repair / enhance voucher giveaway / consumption waiver | Reduce the burden of daily consumption items. |
| Waiver Rate | 50%~100% | Free repair (100% waiver) or enhance discount (50% waiver). |
| Event Duration | 3~7 days | Same as consumption-promo events. |
| Applicable Scenario | High consumption pressure on players during deflation | Focus on easing Low/Mid Spender consumption pressure. |

**Expected Effect**: Consumption down 10%~30% (during the event).

---

#### Strategy K: Consumption Cap Mechanism

| Parameter | Suggested Value | Notes |
|------|-------|------|
| Cap Method | Daily enhance count cap / repair count cap | Set a daily count cap on consumption behaviors. |
| Cap Value | Normal consumption × 0.7~0.9 | Does not affect normal players' daily consumption. |
| Applicable Scope | High-consumption channels first | Limit channels with excessive consumption. |
| Implementation Method | Config table adjustment | Sustained mechanism. |

**Expected Effect**: Consumption down 10%~30% (sustained).

**Risk Notes**:
- Consumption caps may affect the High Spender experience (High Spenders have high consumption demand).
- Recommendation: High Spenders can bypass the cap via payment (payment channels are uncapped), forming a payment-conversion effect.

---

## III. Anomalous-Behavior Crackdown Strategies

### 3.1 Studio Crackdown

| Strategy | Specific Measures | Expected Effect |
|------|---------|---------|
| Ban suspicious accounts | Batch-ban accounts with anomalous production | Directly reduce anomalous production. |
| Restrict same-IP registration | Limit registration count per IP/DID | Prevent studios from bulk-creating accounts. |
| Production decay | Production gradually decays when farming the same level repeatedly | Suppress farming motivation. |
| Trade restriction | Limit large low-price trades / add trade review | Block RMT (real-money trade). |
| Real-name verification | Force high-production users through real-name verification | Increase studio operating costs. |

### 3.2 Cheat Crackdown

| Strategy | Specific Measures | Expected Effect |
|------|---------|---------|
| Anti-cheat detection | Launch an anti-cheat SDK | Auto-detect and block anomalous clients. |
| Behavior feature recognition | Auto-tag anomalous behavior patterns | Automated cheat recognition. |
| CAPTCHA mechanism | Pop up CAPTCHA for high-frequency operations | Block automated scripts. |
| Data validation | Client-server data consistency check | Detect data tampering. |
| Periodic cleanup | Batch-ban cheat accounts weekly | Continuous crackdown. |

### 3.3 Exploit Fix

| Strategy | Specific Measures | Expected Effect |
|------|---------|---------|
| Emergency fix | Immediately fix known exploits | Stop exploit abuse. |
| Data rollback | Roll back data for the exploit time window | Eliminate anomalous production caused by the exploit. |
| Security audit | Full security audit on production logic | Prevent similar exploits. |
| Log tracing | Add detailed logging on production behaviors | Quickly locate future exploits. |

---

## IV. Strategy Combination Principles

### 4.1 Combination Rules

1. **Reduce Production + Boost Consumption**: For over-production, simultaneously cutting production and boosting consumption yields the fastest effect.
2. **Boost Production + Reduce Consumption**: For over-consumption, simultaneously boosting production and cutting consumption yields the fastest effect.
3. **Crack down on anomalies first + then fine-tune**: When anomalous behavior dominates, crack down on anomalies first, then fine-tune based on corrected data.
4. **Gradual adjustment**: Any adjustment should not be one-shot; do it in 2~3 gradual steps.

### 4.2 Combination Verification Formula

```
Required Adjustment = |Current Production-Consumption Ratio - Target Production-Consumption Ratio| × Current Production Total

Combined Strategy Total Contribution = Σ(Each strategy's expected contribution)

Verification: Combined Strategy Total Contribution ≥ Required Adjustment × 1.2 (leave a 20% safety margin)
```

### 4.3 Priority Ranking Principles

| Priority | Selection Criteria |
|-------|---------|
| P0 | Fastest-effect + lowest-risk strategies (e.g., slightly lower RNG, consumption-promo event) |
| P1 | Medium-effect + controllable-risk strategies (e.g., shrink daily production, add consumption channels) |
| P2 | Slow-effect but sustainable strategies (e.g., consumption guidance, daily production adjustment) |
| P3 | High-risk strategies; use only in extreme cases (e.g., consumption caps, large-scale cuts) |

### 4.4 Rollback Plan

Every intervention strategy must come with a rollback plan:
- **Trigger Condition**: Core metrics (Payment Rate, Retention Rate) drop beyond threshold post-intervention.
- **Rollback Method**: Restore the pre-adjustment configuration parameters.
- **Evaluation Cycle**: Evaluate effect 7 days after intervention launch; roll back if it fails to meet the target.
