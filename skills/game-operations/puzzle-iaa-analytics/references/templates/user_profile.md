# Core User Profile

> Based on data-driven interval analysis (Step 06).

## User Tiers

| Type | Definition | Share | D2 | D7 | IPU |
|------|-----------|-------|-----|-----|-----|
| Core | Ads {{ad_min}}-{{ad_max}}× ∩ Levels {{level_min}}-{{level_max}}/D1 | {{core_pct}}% | {{core_d2}}% | {{core_d7}}% | {{core_ipu}}% |
| Squeeze | Ads >{{ad_knee}}× ∩ D7<{{d7_threshold}}% | {{squeeze_pct}}% | {{squeeze_d2}}% | {{squeeze_d7}}% | {{squeeze_ipu}}% |
| Pure Content | Zero ads ∩ High retention | {{content_pct}}% | {{content_d2}}% | {{content_d7}}% | 0% |
| Silent Churn | D1 low + D2 churned | {{silent_pct}}% | - | - | 0% |

## Core User Profile

- Ads: {{core_ad_min}}-{{core_ad_max}}×/day. Levels: {{core_level_min}}-{{core_level_max}}/D1
- Ad scenes: {{core_ad_scene_1}}, {{core_ad_scene_2}}
- Duration: {{core_duration}} min/day
- D2: {{core_d2}}% / D3: {{core_d3}}% / D7: {{core_d7}}%
- IPU Contribution: {{core_ipu_share}}% of revenue, {{core_user_share}}% of users
- IPU Efficiency: {{core_efficiency}}x

## Squeeze User Profile

- Ads: >{{ad_knee}}×/day. Scene: {{squeeze_ad_scene}} (mostly punitive)
- Frustration rate: {{frustration_rate}}%
- Path: Fail → Ad → Still fail → Churn
- {{If IPU contribution >40%, warn unhealthy structure}}

## Revenue Health

| Metric | Value | Healthy | Status |
|--------|-------|---------|--------|
| Core IPU Contribution | {{core_ipu_pct}}% | >50% | {{core_ipu_status}} |
| Squeeze IPU Contribution | {{squeeze_ipu_pct}}% | <30% | {{squeeze_ipu_status}} |
| Concentration (Top 10%) | {{concentration}}% | <50% | {{concentration_status}} |

### Diagnosis
{{If core>50%}}: Healthy — core users are the pillar.
{{If squeeze>40%}}: ⚠️ Revenue over-dependent on high-churn users.
{{If pure content>50%}}: Under-penetration — add non-intrusive ad placements.
