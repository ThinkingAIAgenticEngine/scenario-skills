# Cohort Retention Deep Dive - Recommendation Library

Recommendation mapping from diagnosis to action. Every recommendation must name a specific segment, behavior, and expected direction; never output vague advice.

## Universal: Problem Type -> Action

| Problem type | Quick fix | System fix |
|--------------|-----------|------------|
| Low-fit acquisition (across-cohort drop) | Pause low-quality channels, tighten targeting | Re-define channel quality scoring, review creatives |
| Onboarding friction (low D1 everywhere) | Shorten tutorial, add skip | Rebuild tutorial as steps with completion events |
| Scheduled churn at day N | Push/notification at N-1, restore stamina/ticket | Move the paywall/beat later or add a mid-beat reward |
| Under-nudged Aha moment (high lift, low coverage) | Surface the behavior in tutorial and daily quests | Make the behavior a first-session goal |
| Weak engagement loop (gradual decay) | Add daily quests / streaks / content cadence | Introduce a core loop with a return hook |
| Segment-specific drop | Segment-targeted campaign or support | Fix the segment-specific flow (version bug, geo pricing) |

## Vertical-Specific Quick Reference

### Games

| Problem | Recommendation |
|---------|---------------|
| D1 low | Reduce forced tutorial length; guarantee a win in the first session |
| Cliff at stamina day | Add a free stamina window; move the first stamina gate later |
| Cliff at level ramp | Smooth the difficulty curve; add checkpoints |
| Low D7 in mid-core | Add daily quests and a 7-day login calendar |
| Aha moment = first add-friend | Nudge friend-adding at the end of session 1 |

### Apps

| Problem | Recommendation |
|---------|---------------|
| D1 low | Trim the permission/onboarding wall; show value in 30 seconds |
| Cliff at paywall | Extend free trial; show preview of locked value |
| Gradual decay | Add push-driven re-engagement with personalization |
| Aha moment = first completed task | Make task completion the onboarding goal |

### E-commerce

| Problem | Recommendation |
|---------|---------------|
| D7 return low | Retarget with cart/browse history; send price-drop alerts |
| Cliff after first order | Add a second-order coupon with a short expiry |
| Aha moment = first search-to-order | Improve search and recommendation ranking |

### Content

| Problem | Recommendation |
|---------|---------------|
| D1 low | Auto-play the next episode; show personalized picks immediately |
| Cliff at trial end | Extend trial or offer a discounted first subscription |
| Gradual decay | Release cadence + follow/notification of updates |
| Aha moment = first saved item | Nudge saving/bookmarking early |

## Validation Note

All recommendations are hypotheses until validated. Route the chosen lever to `ae-experiment-design` for sample-size, MDE, and experiment structure before implementation.
