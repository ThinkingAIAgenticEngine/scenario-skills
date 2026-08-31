# Common Attribution Chain Templates

> The attribution mindset: start from the anomaly signal found by inspection, **trace the causal chain upward to the root cause, and downward to the impact surface**. Do not stop midway — do not settle for the intermediate conclusion "the warrior got stronger"; chase down to "why is the nurturing bundle conversion rate also dropping" to complete the chain.
>
> Metric IDs (§N) reference `metric_definitions.md`. Investigation steps are described in business semantics; specific query methods are decided by the adapter layer.

---

## Chain 1: Numeric Tuning → Meta Imbalance → Structural Economy Narrowing → Payment Perception Deterioration

**Trigger signal**: Combat HHI↑ (§1) + Economy consumption concentration↑ (§5)

```
┌─────────────────────────────────────────────────────────────────┐
│ Root cause layer                                                │
│ Numeric tuning of a hero/class (damage multiplier↑, skill buff)  │
│ ▼                                                               │
│ Combat layer                                                    │
│ PVP tilts toward tuned heroes → untuned heroes' appearance↓     │
│ → lineup diversity↓ (§1 HHI↑)                                   │
│ ▼                                                               │
│ Economy layer                                                   │
│ Nurturing consumption concentrates on tuned heroes              │
│ → Top N consumption share↑ (§5) → cold-hero nurturing volume↓ (§6)│
│ ▼                                                               │
│ Backpack layer                                                  │
│ Cold-hero materials unconsumed → fragment/currency holding↑     │
│ (§7/§8) → currency real purchasing power↓                        │
│ ▼                                                               │
│ Monetization layer                                              │
│ Nurturing choice space narrows → "don't know who to buy for"    │
│ → conversion↓ (§9) → willingness to pay↓                         │
└─────────────────────────────────────────────────────────────────┘
```

**Investigation steps**:

1. **Confirm root cause layer**: cross-check version update logs and config-change timelines to locate numeric changes
2. **Verify combat layer**: compare §1 HHI trend before/after the change point for an inflection
3. **Verify economy layer**: confirm §5 consumption distribution starts narrowing from the change point
4. **Verify backpack layer**: check §8 cold-material holding curve correlation with the HHI curve
5. **Verify monetization layer**: break down §9 bundle funnel (exposure→click→purchase) stage-by-stage conversion changes

**Investigation/handoff window**: usually 2-4 weeks from signal confirmation to large-scale user perception. Escalate for remediation planning when HHI just crosses 0.25 and consumption concentration just crosses 50%.

---

## Chain 2: Content Pacing Imbalance → Nurturing Outlet Stage Depletion → Existing Currency Devaluation

**Trigger signal**: Average nurtured heroes↓ (§6) + Currency earn/consume ratio↑ (§4)

```
┌─────────────────────────────────────────────────────────────────┐
│ Root cause layer                                                │
│ New hero release interval too long / new heroes too weak to      │
│ enter mainstream lineups                                        │
│ ▼                                                               │
│ Nurturing layer                                                 │
│ Fewer worthwhile targets → nurturing behavior concentrates      │
│ → average nurtured heroes↓ (§6)                                 │
│ ▼                                                               │
│ Economy layer                                                   │
│ Currency issued as usual but consumption outlets narrow          │
│ → earn/consume ratio > 1.1 keeps widening (§4)                  │
│ ▼                                                               │
│ User behavior layer                                             │
│ "Don't know what to do when online" → session length↓           │
│ → social behavior↓ → churn risk↑                                │
└─────────────────────────────────────────────────────────────────┘
```

**Investigation steps**:

1. Compare the first-week nurturing completion rate trend of the 3 most recent new heroes
2. Analyze click-through rate changes on nurturing entries (nurturing guide, upgrade prompts)
3. Check whether the currency issuance side has abnormal event boosts (rule out supply-side interference)
4. Compare retention differences between "nurturing-active users" vs "nurturing-stagnant users" (§6 segmentation)

---

## Chain 3: Equipment/Nurturing Recycle Anomaly → Economy Loop Rupture

**Trigger signal**: Equipment recycle-before-use ratio↑ (§11) + Nurturing material holding abnormal fluctuation (§7)

```
┌─────────────────────────────────────────────────────────────────┐
│ Root cause layer                                                │
│ Equipment/nurturing system changes (new equipment, old equipment │
│ retirement, nurturing cost adjustment)                          │
│ ▼                                                               │
│ Usage layer                                                     │
│ Equipment recycled before first use in bulk → §11 ratio↑        │
│ → recycled materials flood into the economy                     │
│ ▼                                                               │
│ Economy layer                                                   │
│ Recycled materials shock the nurturing currency system          │
│ → earn/consume ratio imbalance (§4) → nurturing inflation/deflation│
│ ▼                                                               │
│ User perception layer                                           │
│ Nurturing "sense of gain" changes → payment value perception    │
│ changes → willingness to pay fluctuates (§9/§10)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Usage Notes

1. The chains above are **templates** — during actual attribution, select the matching chain based on the specific signal found by inspection
2. Each chain's "investigation steps" give concrete metric directions (§N); load the definitions in `metric_definitions.md` as needed during execution
3. If the actual signal matches no preset chain, a new pattern has been discovered — build the attribution chain yourself following the "root cause → transmission → impact" three-stage structure, and consider adding it to the template library
