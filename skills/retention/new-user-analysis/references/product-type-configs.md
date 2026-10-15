# Product Type Configurations

> **Purpose**: Product-specific scoring weights, thresholds, first-day event presets, and the caliber reference table. This file is the **single source of truth** for weights/thresholds/presets — `SKILL.md` only links here, it does not restate these values.
> **Usage**: Load before Phase 1 (caliber options) and Phase 2 (scoring). Match `product_type` from user input to the corresponding section.

---

## 0. Caliber Reference (for explaining options, never for deciding)

Phase 1 always asks the user for the caliber — this table only helps explain the trade-offs.

| Caliber Type | Typical Event | Use Case | Watch Out |
|-------------|--------------|----------|-----------|
| **First-Launch** | ta_app_start / app_open | Channel attribution, install tracking | Reinstalls counted as new; emulators inflate |
| **Register** | register / signup | New-user quality & retention analysis | Guest play not captured; account alts inflate |
| **First-Active** | tutorial_complete / level_1 | Activation-funnel analysis | "Meaningful" definition varies by team |

> Register ⊂ Launch; First-Pay is a business milestone, not a new-user caliber. Do not mix milestones into the definition.

---

## 1. Scoring Weight Matrix

### 1.1 Game (游戏)

| Dimension | Weight | Core Metrics | Healthy | Warning | Critical |
|-----------|--------|-----------|---------|---------|----------|
| Engagement Depth | 25% | Session count, session duration, level progression | ≥3 sessions, ≥10min, reach level 3 | 1-2 sessions, 5-10min, level 1-2 | 0-1 sessions, <5min, tutorial only |
| Feature Adoption | 30% | Tutorial complete, core loop usage, social feature | ≥70% tutorial complete, ≥50% core loop | 40-70% tutorial, 30-50% core loop | <40% tutorial, <30% core loop |
| Monetization Readiness | 25% | Paywall exposure, first purchase intent, ARPU proxy | ≥8% paywall view, ≥3% purchase intent | 4-8% paywall, 1-3% intent | <4% paywall, <1% intent |
| Retention Signal | 20% | D1 retention, next-day session, push opt-in | ≥40% D1, ≥60% push opt-in | 25-40% D1, 40-60% opt-in | <25% D1, <40% opt-in |

**Game-Specific Notes**:
- Core loop = primary gameplay action (e.g., battle, match, level attempt)
- Paywall exposure = any purchase UI view, not necessarily hard paywall
- D1 retention for games is typically 35-45% for healthy titles

### 1.2 E-commerce (电商)

| Dimension | Weight | Core Metrics | Healthy | Warning | Critical |
|-----------|--------|-----------|---------|---------|----------|
| Engagement Depth | 20% | Session count, browse duration, product views | ≥3 sessions, ≥8min, ≥10 product views | 1-2 sessions, 4-8min, 5-10 views | 0-1 sessions, <4min, <5 views |
| Feature Adoption | 20% | Search usage, filter usage, cart interaction | ≥40% use search, ≥30% use filter | 20-40% search, 15-30% filter | <20% search, <15% filter |
| Monetization Readiness | 35% | Add to cart, checkout start, purchase complete | ≥15% add cart, ≥5% checkout, ≥2% purchase | 8-15% cart, 3-5% checkout, 1-2% purchase | <8% cart, <3% checkout, <1% purchase |
| Retention Signal | 25% | D1 retention, wishlist/save, push opt-in | ≥30% D1, ≥20% save item | 20-30% D1, 10-20% save | <20% D1, <10% save |

**E-commerce-Specific Notes**:
- Monetization is the north star — weight is highest (35%)
- "Purchase intent" = add to cart or start checkout, not just browse
- D1 retention for e-commerce is typically 25-35%

### 1.3 Social / Content (社交/内容)

| Dimension | Weight | Core Metrics | Healthy | Warning | Critical |
|-----------|--------|-----------|---------|---------|----------|
| Engagement Depth | 35% | Session count, content consumption time, feed depth | ≥4 sessions, ≥15min, ≥30 content items | 2-3 sessions, 8-15min, 15-30 items | 0-1 sessions, <8min, <15 items |
| Feature Adoption | 25% | Like/comment, follow, share, content creation | ≥50% like, ≥30% follow, ≥10% share | 30-50% like, 15-30% follow, 5-10% share | <30% like, <15% follow, <5% share |
| Monetization Readiness | 15% | Ad exposure, premium feature view, gift/ tip | ≥10% ad click, ≥5% premium view | 5-10% ad, 2-5% premium | <5% ad, <2% premium |
| Retention Signal | 25% | D1 retention, next-day session, notification opt-in | ≥45% D1, ≥70% notif opt-in | 30-45% D1, 50-70% opt-in | <30% D1, <50% opt-in |

**Social/Content-Specific Notes**:
- Engagement depth is king — time spent = ad inventory
- Content creation (even simple like/comment) is a strong retention signal
- D1 retention for social apps is typically 40-50%

### 1.4 SaaS / Tool (SaaS/工具)

| Dimension | Weight | Core Metrics | Healthy | Warning | Critical |
|-----------|--------|-----------|---------|---------|----------|
| Engagement Depth | 25% | Session count, feature usage time, task completion | ≥3 sessions, ≥12min, ≥2 tasks completed | 1-2 sessions, 6-12min, 1 task | 0-1 sessions, <6min, 0 tasks |
| Feature Adoption | 35% | Onboarding complete, core feature use, integration setup | ≥80% onboarding, ≥60% core feature | 50-80% onboarding, 40-60% core | <50% onboarding, <40% core |
| Monetization Readiness | 20% | Premium feature view, trial start, upgrade click | ≥15% premium view, ≥5% trial start | 8-15% premium, 3-5% trial | <8% premium, <3% trial |
| Retention Signal | 20% | D1 retention, next-day task, email/ push opt-in | ≥50% D1, ≥80% email opt-in | 35-50% D1, 60-80% opt-in | <35% D1, <60% opt-in |

**SaaS/Tool-Specific Notes**:
- Feature activation is the strongest predictor of conversion — weight highest (35%)
- "Task completion" = user achieved the core value proposition (e.g., created a document, sent an invoice)
- D1 retention for SaaS is typically 45-55% (higher than consumer)

### 1.5 Utility (工具)

| Dimension | Weight | Core Metrics | Healthy | Warning | Critical |
|-----------|--------|-----------|---------|---------|----------|
| Engagement Depth | 30% | Session count, core action count, session duration | ≥4 sessions, ≥5 core actions, ≥6min | 2-3 sessions, 3-5 actions, 3-6min | 0-1 sessions, <3 actions, <3min |
| Feature Adoption | 30% | Permission grant, core action 1, core action 2, settings | ≥70% permission, ≥50% action 1 | 40-70% permission, 30-50% action | <40% permission, <30% action |
| Monetization Readiness | 15% | Premium feature view, ad exposure, upgrade click | ≥10% premium view, ≥3% upgrade | 5-10% premium, 1-3% upgrade | <5% premium, <1% upgrade |
| Retention Signal | 25% | D1 retention, next-day action, widget/ shortcut | ≥40% D1, ≥30% widget add | 25-40% D1, 15-30% widget | <25% D1, <15% widget |

**Utility-Specific Notes**:
- Task completion > exploration — users come with a specific goal
- Permission grant is a critical early milestone (camera, location, notifications)
- D1 retention for utility apps is typically 35-45%

---

## 2. First-Day Event Presets

### 2.1 Game

| Step | Event Name Variants | Description |
|------|-------------------|-------------|
| 1 | `launch`, `app_open`, `first_open` | App first opened |
| 2 | `tutorial_start`, `ftue_start`, `onboarding_start` | Tutorial/FTUE started |
| 3 | `tutorial_complete`, `ftue_complete`, `onboarding_complete` | Tutorial completed |
| 4 | `level_1_start`, `stage_1`, `battle_1`, `match_1` | First core gameplay action |
| 5 | `level_1_complete`, `stage_1_win`, `first_win` | First win/ completion |
| 6 | `level_3_start`, `stage_3`, `unlock_feature` | Reach level 3 or unlock 2nd feature |
| 7 | `paywall_view`, `shop_open`, `iap_show` | Purchase UI viewed |
| 8 | `purchase`, `first_iap`, `payment_complete` | First purchase completed |

**Game Event Notes**:
- If no tutorial: skip steps 2-3, start from level_1
- "Core loop" = repeat action (e.g., battle→reward→upgrade→battle)

### 2.2 E-commerce

| Step | Event Name Variants | Description |
|------|-------------------|-------------|
| 1 | `launch`, `app_open`, `first_open` | App first opened |
| 2 | `browse`, `category_view`, `feed_view` | Browse products/feed |
| 3 | `search`, `search_submit`, `query` | Use search |
| 4 | `product_view`, `item_view`, `detail_view` | View product detail |
| 5 | `add_cart`, `cart_add`, `add_to_bag` | Add to cart |
| 6 | `checkout_start`, `begin_checkout`, `order_start` | Start checkout |
| 7 | `purchase`, `payment_complete`, `order_success` | Complete purchase |
| 8 | `wishlist_add`, `save_item`, `favorite` | Save for later |

### 2.3 Social / Content

| Step | Event Name Variants | Description |
|------|-------------------|-------------|
| 1 | `launch`, `app_open`, `first_open` | App first opened |
| 2 | `feed_view`, `timeline_view`, `home_view` | View content feed |
| 3 | `content_click`, `video_play`, `article_open` | Click/ play content |
| 4 | `like`, `like_post`, `heart`, `upvote` | Like content |
| 5 | `comment`, `reply`, `comment_post` | Comment on content |
| 6 | `follow`, `subscribe`, `friend_add` | Follow user/ channel |
| 7 | `share`, `repost`, `forward` | Share content |
| 8 | `profile_view`, `my_page`, `user_center` | View own profile |

### 2.4 SaaS / Tool

| Step | Event Name Variants | Description |
|------|-------------------|-------------|
| 1 | `launch`, `app_open`, `first_open` | App first opened |
| 2 | `signup`, `register`, `account_create` | Create account |
| 3 | `onboarding_step1`, `setup_start`, `wizard_1` | Onboarding step 1 |
| 4 | `onboarding_complete`, `setup_complete`, `wizard_done` | Onboarding complete |
| 5 | `feature_use`, `core_action`, `task_create` | Use core feature |
| 6 | `integration_setup`, `connect`, `sync_enable` | Setup integration |
| 7 | `invite`, `team_add`, `collaborate` | Invite team member |
| 8 | `upgrade_view`, `premium_view`, `pricing_view` | View upgrade options |

### 2.5 Utility

| Step | Event Name Variants | Description |
|------|-------------------|-------------|
| 1 | `launch`, `app_open`, `first_open` | App first opened |
| 2 | `permission_grant`, `permission_allow`, `auth_success` | Grant key permission |
| 3 | `core_action_1`, `primary_task`, `main_feature` | First core action |
| 4 | `core_action_2`, `secondary_task`, `advanced_feature` | Second core action |
| 5 | `settings_open`, `preference_view`, `config` | Open settings |
| 6 | `widget_add`, `shortcut_create`, `home_screen` | Add widget/ shortcut |
| 7 | `notification_enable`, `push_allow`, `alert_on` | Enable notifications |
| 8 | `upgrade_view`, `premium_view`, `pro_view` | View upgrade options |

---

## 3. Composite Score Interpretation

| Score Range | Label | Action |
|-------------|-------|--------|
| **≥80** | Excellent | Scale acquisition, document best practices |
| **70-79** | Healthy | Maintain current strategy, minor optimizations |
| **60-69** | Acceptable | Identify weakest dimension, run A/B test |
| **50-59** | Warning | Pause low-quality channels, fix onboarding |
| **40-49** | Critical | Halt paid acquisition, emergency product review |
| **<40** | Failure | Full product-market-fit reassessment |

---

## 4. Cross-Product-Type Benchmarks

| Metric | Game | E-commerce | Social | SaaS | Utility |
|--------|------|-----------|--------|------|---------|
| **D1 Retention (Healthy)** | 40% | 30% | 45% | 50% | 40% |
| **D1 Retention (Critical)** | 25% | 20% | 30% | 35% | 25% |
| **Session Count (Healthy)** | 3 | 3 | 4 | 3 | 4 |
| **Feature Adoption (Healthy)** | 70% | 40% | 50% | 80% | 70% |
| **Monetization Ready (Healthy)** | 8% | 15% | 10% | 15% | 10% |

---

## 5. Event Name Mapping Rules

When auto-discovered event names don't match presets:

| Preset Event | Common Variants | Regex Pattern |
|-------------|-----------------|---------------|
| `tutorial_complete` | ftue_done, onboarding_end, guide_finish | `(tutorial|ftue|onboarding|guide).*(complete|done|end|finish)` |
| `level_1_start` | stage_1, battle_start, match_begin, game_play | `(level|stage|battle|match|game).*(1|first|start|begin)` |
| `purchase` | payment, iap, order_complete, transaction | `(purchase|payment|iap|order|transaction).*(complete|success|done)` |
| `add_cart` | cart_add, add_to_bag, basket_add | `(cart|bag|basket).*(add|insert|put)` |
| `search` | query, search_submit, find | `search|query|find|lookup` |
| `like` | heart, upvote, favorite, thumbs_up | `like|heart|upvote|favorite|thumbs` |
| `follow` | subscribe, friend_add, track | `follow|subscribe|friend|track` |
| `signup` | register, account_create, join | `(sign|register|account|join).*(up|create|new)` |

---

*File version: 1.0.0 | Last updated: 2026-09-14*
