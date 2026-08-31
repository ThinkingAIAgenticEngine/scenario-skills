# Key Metrics Summary Table

## {{project.game_name}} — {{project.version}} Postmortem

**Period**: {{window.start}} ~ {{window.end}} ({{days}} days)

### Core Retention

| Metric | Value | Baseline | Status |
|--------|-------|----------|--------|
| Day 2 Retention | {{d2_retention}}% | >35% | {{d2_status}} |
| Day 3 Retention | {{d3_retention}}% | >20% | {{d3_status}} |
| Day 7 Retention | {{d7_retention}}% | >12% | {{d7_status}} |
| D2→D3 Decay | {{decay_1}}% | <30% | {{decay_1_status}} |
| D3→D7 Decay | {{decay_2}}% | <25% | {{decay_2_status}} |

### Activity

| Metric | Day 1 | Day 2 | Days 3-7 | Status |
|--------|-------|-------|----------|--------|
| Avg Duration (min) | {{duration_d1}} | {{duration_d2}} | {{duration_d3_7}} | {{duration_status}} |
| Avg Levels | {{level_d1}} | {{level_d2}} | {{level_d3_7}} | {{level_status}} |

### Levels

| Metric | Value | Status |
|--------|-------|--------|
| First Level Pass Rate | {{first_level_pass}}% | {{first_level_status}} |
| First <80% | Level {{stuck_80}} | - |
| First <50% | Level {{stuck_50}} | - |

### Ads

| Ad Type | Impression Share | User Share |
|---------|-----------------|------------|
| {{ad_type_1}} | {{ad_share_1}}% | {{ad_user_share_1}}% |
| {{ad_type_2}} | {{ad_share_2}}% | {{ad_user_share_2}}% |
| {{ad_type_3}} | {{ad_share_3}}% | {{ad_user_share_3}}% |

### User Structure

| User Type | Share | D2 |
|-----------|-------|-----|
| Core Users | {{core_share}}% | {{core_d2}}% |
| Squeeze Users | {{squeeze_share}}% | {{squeeze_d2}}% |
| Zero Ad Users | {{zero_ad_share}}% | {{zero_ad_d2}}% |

### Overall Rating

**{{rating}}**

**Most Critical Issue**: {{one_line_problem}}
