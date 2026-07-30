# Economy System Balance Threshold Configuration

> **Core Principle**: Different game categories have different economy system design logics. The reasonable range and alert thresholds for the production-consumption ratio must be differentiated by category; do not apply a one-size-fits-all value.

---

## I. Production-Consumption Ratio Reasonable Range

### 1.1 Default Configuration by Category

| Game Category | Reasonable Range | Over-Production Threshold | Over-Consumption Threshold | Design Rationale |
|---------|-------------|-----------|-----------|---------|
| **MMO** | 0.95 ~ 1.05 | >1.10 | <0.90 | MMO economy systems are the most complex, involving player-to-player trading and real-currency exchange. The tolerance range is the narrowest; any ratio deviation may trigger exchange-rate fluctuations. |
| **SLG (Strategy Games)** | 0.90 ~ 1.10 | >1.15 | <0.85 | SLG has large resource consumption (build/train/war), and war consumption is unpredictable, so the tolerance range is wider. |
| **Card / Anime** | 0.90 ~ 1.00 | >1.05 | <0.85 | Card games have few resource production channels, and consumption is concentrated on gacha/progression; even slightly higher production may devalue gacha. |
| **Casual / Puzzle** | 0.95 ~ 1.05 | >1.10 | <0.90 | Casual games have a small economy; even a tiny production-consumption deviation may unbalance the experience. |
| **Competitive / MOBA** | 0.95 ~ 1.05 | >1.10 | <0.90 | Competitive games have simpler resource systems, mostly skins/items; the tolerance range is narrow. |
| **Generic / Unknown Category** | 0.90 ~ 1.10 | >1.15 | <0.85 | Use a wide range for unknown categories to avoid misjudgment. |

### 1.2 User-Defined Thresholds

When the user is not satisfied with the category default thresholds, customization is supported. Customization method:

```
Please confirm the following threshold configuration (currently MMO defaults):
- Reasonable production-consumption range: 0.95 ~ 1.05
- Over-production threshold: >1.10
- Over-consumption threshold: <0.90

To adjust, please provide:
1. Custom reasonable range (e.g., 0.93~1.07)
2. Custom over-production threshold (e.g., >1.12)
3. Custom over-consumption threshold (e.g., <0.88)
```

---

## II. Alert Trigger Thresholds

### 2.1 Total-Volume Alert

| Game Category | Single-Day Acquisition Total Alert | Calculation | Notes |
|---------|---------------|---------|------|
| MMO | >Previous 7-day average × 3 | Current-day total acquisition / Recent 7-day daily average | MMO economy is large; ×3 is a significant anomaly. |
| SLG | >Previous 7-day average × 2.5 | Same as above | SLG war consumption fluctuates widely; threshold slightly lower. |
| Card | Single item 24h acquisition > 100 | Absolute value of current-day acquisition total | Card economy is small; use absolute-value threshold. |
| Casual | >Previous 7-day average × 3 | Same as MMO | Casual economy is small but fluctuates less. |
| Generic | >Previous 7-day average × 3 | Same as above | Generic default. |

### 2.2 Frequency Alert

| Monitoring Dimension | Default Threshold | Applicable Categories | Notes |
|---------|---------|---------|------|
| Per-User Daily Acquisition Count | >Server-wide average × 5 | All categories | Acquisition frequency anomaly. |
| Per-User Hourly Acquisition Rate | >Server-wide P95 × 2 | All categories | Anomalous acquisition speed within an hour window. |
| Daily Completion Count of Same Quest | >50 times/day | All categories | Normal players complete the same quest <20 times/day. |
| Account Count under Same IP/DID | ≥5 | MMO/SLG | Studio multi-account feature. |

### 2.3 Payment Contradiction Alert

| Monitoring Dimension | Alert Threshold | Notes |
|---------|---------|------|
| Non-Spender Per-User Production / Paying User Per-User Production | >1.5 | Non-Spender production far exceeds Paying Users; highly suspicious. |
| Non-Spender Production Share / Non-Spender User Share | >2 | A small number of Non-Spenders contribute a large share of production. |

---

## III. Concentration Thresholds

### 3.1 Production Concentration

| Concentration Range | Health Assessment | Meaning |
|----------|---------|------|
| <40% | Healthy | Production sources are dispersed; impact of a single anomalous source point is limited. |
| 40%~60% | Normal | Moderately concentrated; main production channels are clear. |
| >60% | Risk | Over-concentrated; a TOP3 source-point anomaly will heavily affect total production. |

### 3.2 Consumption Concentration

Same thresholds as Production Concentration.

---

## IV. Hoarding Rate Thresholds

| Hoarding Rate Range | Health Assessment | Meaning |
|----------|---------|------|
| <5% | Healthy | Very few users hoard large resource volumes. |
| 5%~15% | Normal | A certain proportion of users have resource reserves. |
| >15% | Risk | Many users hoard; inflation or hoarding strategy may exist. |

**Hoarding Threshold Setting Methods**:
- Default: Server-wide balance P90 percentile.
- Custom: User specifies a concrete value (e.g., "gold balance > 1,000,000 counts as hoarding").

---

## V. Inflation / Deflation Severity Grading

| Level | Production-Consumption Ratio Deviation | Description | Response Requirement |
|------|----------|------|---------|
| **Normal** | Within reasonable range | Dynamic production-consumption balance | Daily monitoring suffices. |
| **Mild Deviation** | Outside reasonable range within ±0.05 | Slight inflation/deflation tendency | Watch the trend; review after 7 days. |
| **Moderate Deviation** | Outside reasonable range by ±0.05~0.15 | Clear inflation/deflation | Intervention needed; adjust within 1~2 weeks. |
| **Severe Deviation** | Outside reasonable range by ±0.15 or more | Severe inflation/deflation | Urgent intervention; act immediately. |
| **Extreme Anomaly** | Outside reasonable range by ±0.30 or more | Economy system on the verge of collapse | Top priority; full investigation + emergency fix. |

### Response Time Requirements

| Severity | First Response Time | Intervention Launch Time | Effect Evaluation Cycle |
|-------|------------|------------|------------|
| Mild | Within 24h | 1~2 weeks | 7 days post-intervention |
| Moderate | Within 12h | 3~7 days | 3 days post-intervention |
| Severe | Within 4h | 1~3 days | Next day post-intervention |
| Extreme | Immediately | Same day | Continuous monitoring until return |

---

## VI. Category Identification Keyword Mapping

Used to auto-identify the game category from event names:

| Category | Keywords | Typical Events |
|------|-------|---------|
| MMO | login, guild, raid, dungeon, craft, trade, auction | Guild War, Dungeon, Auction House Trade, Gear Crafting |
| SLG | build, train, attack, alliance, march, siege | Build, Train, Attack, Alliance, March |
| Card / Anime | gacha, draw, summon, hero, card, level_up, star_up | Gacha, Summon, Hero Upgrade, Star Up |
| Casual | puzzle, match, clear, level, combo | Match, Level Clear, Combo |
| Competitive / MOBA | battle, match, rank, hero_pick, ban | Battle, Match, Rank, Hero Pick, Hero Ban |

**Identification Rules**:
1. Iterate the project event name list; match keywords.
2. Compute match score = (matched keyword count / total keywords for that category) × 100%.
3. Select the highest-scoring category (≥25% counts as a match).
4. Confidence ≥60%: High confidence; confirm directly.
5. Confidence 25%~60%: Requires user confirmation.
6. Confidence <25%: Mark as Generic category; ask the user.
