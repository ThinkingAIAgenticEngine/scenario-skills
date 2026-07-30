# Industry Category Identification Dictionary

> Used for Step 2: Identify customer's industry and sub-category based on tracking metadata.

---

## Identification Logic

1. Calculate industry category match rate, select highest match (≥25% considered matched)
2. Within matched industry, perform secondary matching on sub-category keywords
3. Sub-category directly determines Layer 5 [Industry Exclusive Tags] content
4. Cannot identify sub-category → Output industry category general exclusive tags
5. Cannot identify industry → Mark as [General Industry], output basic version tag system

---

## Industry Category Identification Keywords

| Industry | Event keywords | Property keywords |
|------|-----------|-----------|
| Gaming | login, level_up, battle, quest, gacha, recharge, role_create, dungeon, pvp | level, exp, gold, diamond, vip_level, server_id, combat_power |
| E-commerce | view_product, add_cart, place_order, pay, refund, search, collect, review | product_id, category, price, sku, cart_value, order_amount |
| Finance | apply_loan, invest, withdraw, transfer, kyc, risk_assess, repay, portfolio | amount, balance, credit_score, risk_level, product_type, interest_rate |
| Education | course_view, lesson_complete, exam, homework, enroll, replay, note, assignment | course_id, grade, score, study_time, teacher_id, subject |
| Social/Content | post, comment, like, share, follow, message, live, publish, subscribe | content_type, follower_count, topic, feed_type, interaction_count |
| Travel/Local Life | search_poi, book_ride, arrive, order_food, reserve, scan_bike, check_in | poi_id, distance, city, eta, price, rating, category |
| Health/Medical | record_health, consult_doctor, book_appointment, view_report, track, remind | symptom, metric_type, doctor_id, department, health_score |
| Enterprise SaaS | create_project, invite_member, export, api_call, workflow, permission, billing | workspace_id, plan, member_count, feature, module, usage_quota |
| Media/Entertainment | play_video, pause, seek, finish, subscribe, recommend_click, search, download | content_id, duration, genre, resolution, vip_type, play_position |
| Tool/Efficiency | create_file, edit, export, sync, share, template_use, ai_generate | file_type, feature, template_id, output_format, frequency |

---

## Sub-category Identification

Further distinguish within industry category confirmation.

### 🎮 Gaming Sub-categories

| Category | Feature keywords | Exclusive tag focus |
|-----|-----------|-------------|
| MMO/RPG | server_id, guild, role, quest, world_boss | Character profession, guild activity, equipment enhancement depth |
| Card/Idle | card_id, deck, gacha, auto_battle | Gacha count, deck diversity, idle duration preference |
| Casual/Match-3 | level_id, life, booster, daily_challenge | Level progress, item usage, completion speed tiering |
| Strategy/SLG | city_id, alliance, troop, resource_type | Alliance activity, resource collection efficiency, diplomatic behavior |
| Arena/FPS | match_id, rank, kill, team | Rank range, win rate, team preference, frequently used hero/weapon |
| Board/Fishing/Slots | bet, jackpot, spin, multiplier | Bet volatility, coin level, consecutive win/loss state |
| Anime/Open World | explore, achievement, character, skin | Map exploration rate, hidden achievement, character preference |

### 🛍️ E-commerce Sub-categories

| Category | Feature keywords | Exclusive tag focus |
|-----|-----------|-------------|
| General E-commerce | Multi-category, search driven | Cross-category purchase, discount-sensitive, coupon usage rate |
| Vertical E-commerce (Fashion/Beauty) | brand, style, size | Style preference, brand loyalty, seasonal purchase pattern |
| Live/Social E-commerce | live_id, kol_id, flash_sale, group_buy | Live purchase ratio, frequent streamer preference, group buy participation rate |
| Cross-border E-commerce | country, currency, customs | Country preference, cross-border shopping frequency |
| B2B Procurement | company_id, bulk_order, quote | Bulk purchase habit, approval process participation |

### 💰 Finance Sub-categories

| Category | Feature keywords | Exclusive tag focus |
|-----|-----------|-------------|
| Consumer Loan/Cash Loan | apply_loan, credit_limit, repay, overdue | Loan count, on-time repayment rate, current debt status |
| Investment/Fund | invest, portfolio, yield, risk_preference | Holding product count, product type preference, fixed investment participation |
| Insurance | policy, premium, claim, renewal | Policy count, category coverage, renewal rate |
| Securities/Stock | trade, position, watchlist, market_data | Trading activity, preferred sector, holding period |
| Digital Wallet/Payment | transfer, top_up, scan_pay, bill | Payment frequency, transfer preference |

### 📚 Education Sub-categories

| Category | Feature keywords | Exclusive tag focus |
|-----|-----------|-------------|
| K12 | grade, subject, homework, exam, parent_view | Grade level, weak subjects, parent-supervised vs autonomous learning |
| Vocational/Certification | certificate, practice_test, study_plan, flashcard | Preparing certificate type, mock test accuracy, check-in continuity |
| Language Learning | vocabulary, pronunciation, speaking_practice, streak | Target language, current level, speaking practice activity, weak skills |
| Higher Education/MOOC | university, credit, peer_review, project | Credit progress, project completion status |
| Hobby Education (Music/Art/Sports) | skill_level, practice_duration, feedback | Practice duration, skill level progression, teacher interaction rate |

### 📱 Social/Content Sub-categories

| Category | Feature keywords | Exclusive tag focus |
|-----|-----------|-------------|
| Short Video Platform | swipe, like, share, live_gift | Content preference topic, completion rate preference, gift frequency |
| Image-text/News Platform | read, collect, follow_topic, comment | Followed topics, read-through rate, comment style |
| Novel Reading | chapter, novel_genre, reading_speed | Genre preference (fantasy/urban), reading speed, update tolerance |
| Creator Platform | publish, follower_growth, monetize | Publish frequency, content quality tiering, follower growth speed |

### 🚗 Travel/Local Life Sub-categories

| Category | Feature keywords | Exclusive tag focus |
|-----|-----------|-------------|
| Ride-hailing | book_ride, car_type, route, eta | Travel frequency, preferred car type, commuter vs non-commuter |
| Food Delivery/Dining | order_food, cuisine, meal_time, coupon | Order frequency, preferred cuisine, order time slot, coupon usage rate |
| Hotel/Travel | book_hotel, destination, trip_type, star | Travel frequency, booking lead time, preferred accommodation grade |

### 🏥 Health/Medical Sub-categories

| Category | Feature keywords | Exclusive tag focus |
|-----|-----------|-------------|
| Health Management App | record_health, goal, reminder, exercise | Monitoring metric type, goal achievement rate, exercise completion rate |
| Internet Healthcare | consult, prescription, follow_up, report | Consultation frequency, preferred department, follow-up rate |

### 🏢 Enterprise SaaS Sub-categories

| Category | Feature keywords | Exclusive tag focus |
|-----|-----------|-------------|
| Collaboration/Project Management | project, task, member, comment | Project creation frequency, task flow activity, invitation activity |
| Marketing SaaS | campaign, channel, report, ab_test | Campaign creation frequency, placement channel count, report view frequency |
| CRM/Sales | lead, deal, contact, pipeline | Sales lead processing, conversion rate |

---

## Match Rate Calculation Method

```
Match rate = (matched keyword count / total keywords for that industry) × 100%

Example:
- Project has 20 events
- 12 match [Gaming] keywords
- Gaming keyword total approximately 15
- Match rate = 12/15 × 100% = 80%
```

**Threshold rules**:
- ≥60%: High confidence, direct confirmation
- 25%-60%: Medium confidence, requires user confirmation
- <25%: Low confidence, mark as general industry or proactively ask user

---

## Language Constraint

**[LANGUAGE CONSTRAINT]**: Generate your response in the EXACT SAME LANGUAGE as the user's input. If user queries in Chinese, respond entirely in Chinese. If user queries in English, respond in English. Do not mix languages unless explicitly translating terms.