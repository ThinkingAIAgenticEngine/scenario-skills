# Optimization Recommendations Template

## Usage
Generate genre-specific, actionable optimization recommendations based on identified chokepoint types.

## Template

### Universal Optimization Measures

| Problem Type | Recommendation | Expected Impact |
|--------------|----------------|-----------------|
| Excessive difficulty | Reduce enemy HP / Decrease obstacles / Increase time | +10-20% pass rate |
| Beginner chokepoint | Add guidance hints / Simplify controls / Lower early difficulty | +5-10% new user retention |
| Low forgiveness | Add checkpoints / Increase moves / Add forgiveness mechanics | Reduce frustration |
| Excessive cooldown | Push recall after failure / Gift items / Lower retry cost | +15-25% return rate |
| Unclear mechanics | Add tutorial levels / Hint guidance / Mechanic demos | Reduce invalid attempts |

### Genre-Specific Recommendations

| Game Type | Common Chokepoint Causes | Targeted Recommendations |
|-----------|-------------------------|--------------------------|
| **Card** | Enemy counters deck / Insufficient deck strength | Add card acquisition in prior levels; Failure hints for deck building; Trial cards |
| **RPG** | Complex boss mechanics / High power threshold | Reduce boss HP/damage; Add mechanic tutorials; Increase gear drops in prior levels |
| **Match-3/Puzzle** | Move limits / Special obstacle difficulty | Increase move cap; Reduce obstacle spawn rate; Increase special item drops |
| **Runner/Action** | Reaction speed requirements / Obstacle density | Reduce movement speed; Increase obstacle warning time; Add shield/revive mechanics |
| **SLG** | Insufficient resources / High strategy threshold | Increase resource output in prior levels; Simplify win conditions; Add strategy hints |
| **Casual/Sim** | Long wait times / Complex controls | Reduce wait CDs; Simplify operation steps; Add automation features |
| **MOBA/Competitive** | Matchmaking / Control threshold | Optimize newbie match pool; Add control assists; Provide AI practice |
| **Idle/Incremental** | Progress bottlenecks / Number gates | Increase offline earnings; Provide breakthrough items; Lower upgrade requirements |

### Intervention Strategies

**Immediate Intervention (Within 24h of failure):**
- Push level guides / tips
- Gift assist items
- Lower retry cost

**Recall Strategy (3-7 days after churn):**
- Push "Stuck at Level X" reminder
- Offer "Skip" or "Lower Difficulty" option
- Return package with level counter items

**Pre-emptive Optimization (Before entering level):**
- Add resources/items in prior levels
- Add difficulty transition levels
- Early tutorial for key mechanics

## Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `{problem_type}` | Identified problem category | "Excessive difficulty" |
| `{game_type}` | Game genre | "RPG", "Match-3" |
| `{impact_estimate}` | Expected improvement range | "+10-20%" |

## Integration Notes

This template is referenced by:
- `templates/action_recommendations.md` - For specific level recommendations
- SKILL.md - For recommendation library overview

When generating recommendations:
1. Map inferred root cause to Problem Type
2. Select Game Type specific recommendations
3. Choose Intervention Strategy based on urgency
4. Include impact estimates with appropriate disclaimers
