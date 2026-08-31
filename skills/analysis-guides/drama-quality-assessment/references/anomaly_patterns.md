# Common Anomaly Pattern Library

> This document lists common anomaly patterns and their characteristics in short-drama quality analysis, for the Agent to reference during Step 4 diagnosis.
> The Agent should match detected patterns against this library while analyzing data and produce precise diagnostic conclusions.
> **When outputting diagnostic wording to the user, translate it into Chinese (see SKILL.md "Language Convention"); the templates below are written in English.**

---

## 1. Single-Episode Anomaly Patterns

### Pattern 1: Cliff Episode 🔴
**Characteristics:** a single episode's completion rate and retention rate both plummet simultaneously (20%+ lower than adjacent episodes)
**Typical root causes:**
- severe content-quality decline in that episode (dragging plot, padded content)
- technical problems such as video/audio quality
- abnormal episode length (too long or too short)
**Diagnostic wording:** "Episode X shows a cliff-edge drop: completion rate fell XX% versus the previous episode, and inter-episode retention dropped from XX% to XX%, suggesting a content or technical quality issue in this episode."

### Pattern 2: Pacing Collapse Episode 🔴
**Characteristics:** an episode's progress retention curve is abnormally steep, with mass drop-offs at a specific position (25% or 50%)
**Typical root causes:**
- overly draggy opening causing loss at 25%
- broken plot in the middle segment causing loss at 50%
- insufficient dramatic conflict in that episode
**Diagnostic wording:** "Episode X's pacing curve shows a mass drop-off peak at YY%: XX% of users left at that position, suggesting a pacing problem in that segment."

### Pattern 3: Cliffhanger Failure Episode 🟡
**Characteristics:** high completion rate but extremely low episode-end jump rate (< 30%), high cliffhanger failure ratio
**Typical root causes:**
- ending lacks a hook or suspense design
- ending gives a "series finale" feel, making users think they can stop
- the next-episode preview is not attractive enough
**Diagnostic wording:** "Episode X reaches XX% completion but the episode-end jump rate is only XX%; users finish and leave immediately, indicating the ending hook (cliffhanger) failed."

### Pattern 4: Payment Friction Episode 🟡
**Characteristics:** play count drops off a cliff at the paywall, and the payment conversion rate is significantly lower than peers
**Typical root causes:**
- paywall placed too early (not enough free episodes)
- price does not match content value
- friction in the payment experience flow
**Diagnostic wording:** "Episode X is the paywall start: the payment trigger rate is only XX%, and XX% of users who reached this episode chose to leave instead of paying."

---

## 2. Trend Anomaly Patterns

### Pattern 5: Weak Opening 🟡
**Characteristics:** episode 1 metrics are all low (first-episode completion rate < 40%, 1→2 jump rate < 35%)
**Typical root causes:**
- opening is not attractive enough and fails to build expectation within the first 3 seconds
- genre/visual style mismatch with the target audience
- promotional material inconsistent with actual content, causing user disappointment
**Diagnostic wording:** "First-episode performance is below expectations: completion rate is only XX% and XX% of users did not continue watching; consider optimizing the opening and strengthening the first-3-seconds hook."

### Pattern 6: Mid-Series Fatigue 🟠
**Characteristics:** the first 3-5 episodes perform well, but from episode N onward all metrics keep declining
**Typical root causes:**
- plot enters a padding phase or transitional segment too long
- main-line conflict not dense enough
- intervals between payoff points / twists lengthen
**Diagnostic wording:** "This drama shows clear mid-series fatigue: from episode X onward completion and retention keep declining, with dimension scores decreasing episode by episode; consider compressing the middle section or increasing plot-conflict density."

### Pattern 7: Late-Series Collapse 🔴
**Characteristics:** most episodes perform stably, but the last 2-3 episodes see all metrics plummet
**Typical root causes:**
- poor ending handling (a botched finale)
- large gap between the ending and expectations
- dragging pacing before the finale
**Diagnostic wording:** "The finale episodes collapsed: the last X episodes' completion and retention dropped XX% versus the middle section, suggesting the ending failed to meet user expectations."

### Pattern 8: High Open, Low Finish 🟡
**Characteristics:** episode 1 metrics are strong but then keep declining; large gap between the first and last episodes
**Typical root causes:**
- over-promotion in trailers/marketing, actual content cannot sustain it
- opening tries too hard but follow-through is weak
- imprecise audience targeting (attracting non-target users)
**Diagnostic wording:** "This drama trends high-open-low-close: first-episode completion XX% → finale XX%, retention dropped from XX% to XX%; consider strengthening the content quality and plot drive of the middle episodes."

### Pattern 9: Binge Break 🟡
**Characteristics:** low binge median (< 3 episodes), low binge ≥3 episodes ratio (< 30%)
**Typical root causes:**
- inter-episode connections are not tight enough
- single episodes lack the satisfying "watch in one go" feel
- high consumption threshold of episode length
**Diagnostic wording:** "Binge depth is insufficient: only XX% of users watched 3+ episodes in one session, with a binge median of X episodes; consider strengthening inter-episode coherence and cliffhanger design."

---

## 3. Opportunity Signal Patterns

### Pattern 10: Word-of-Mouth Effect 🟢
**Characteristics:** play count grows organically without promotion, and the new-user ratio keeps rising
**Signal meaning:** users proactively share and spread it; word of mouth drives organic growth
**Suggestion:** increase promotion and ride the momentum

### Pattern 11: Payment Sweet Spot 🟢
**Characteristics:** high payment conversion rate (> 25%), high post-payment watch rate (> 80%)
**Signal meaning:** content value is recognized by users; paywall position is reasonable
**Suggestion:** consider deepening monetization, or use it as a benchmark for paid dramas

### Pattern 12: Counter-Trend Upturn 🟢
**Characteristics:** mediocre early performance, but metrics in the latter half keep rising
**Signal meaning:** the content gets better as it goes; word of mouth starts fermenting
**Suggestion:** consider shortening the free-episode count so users reach the exciting part sooner

---

## 4. Diagnosis Priority Ordering

The Agent outputs findings in the following priority order when diagnosing:

1. **🔴 Urgent** (affects business results):
   - Pattern 1 (Cliff Episode), Pattern 7 (Late-Series Collapse), Pattern 4 (Payment Friction Episode)

2. **🟠 Important** (affects user retention):
   - Pattern 6 (Mid-Series Fatigue), Pattern 2 (Pacing Collapse Episode), Pattern 5 (Weak Opening)

3. **🟡 Attention** (affects long-term growth):
   - Pattern 8 (High Open, Low Finish), Pattern 3 (Cliffhanger Failure Episode), Pattern 9 (Binge Break)

4. **🟢 Opportunity** (worth amplifying):
   - Pattern 10 (Word-of-Mouth Effect), Pattern 11 (Payment Sweet Spot), Pattern 12 (Counter-Trend Upturn)
