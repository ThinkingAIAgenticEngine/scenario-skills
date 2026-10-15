# Comparison Mode (Universal Edition)

> Read when the user mentions "before/after update", "event effect", "this week vs last week", "did the redesign improve". Only the trigger gate lives in SKILL.md "Quick Reference"; the full procedure lives here.

When the user enters comparison mode:

1. **Collect two periods**: Period A (baseline, e.g., 14 days before update) + Period B (comparison, e.g., 14 days after update). Keep all other parameters (product config, granularity, dimensions) identical.
2. **Fairness validation**: the two periods should be equal length; non-overlapping; B after A (chronological); each excludes the current partial day.
3. **Execute**: run Part 1-5 for A and B separately, same parameters and caliber, then compare the two periods' root-cause differences using the same inflection/anomaly thresholds — focus on "did penetration change significantly across the update, which dimension the change concentrated in, and whether it was caused by the update/event".
4. **Output**: A vs B penetration first/last values + primary driver dimension difference + root-cause comparison, noting "whether the change is attributable to the update/event" (correlation ≠ causation).
