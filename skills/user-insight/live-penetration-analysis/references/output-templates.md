# Output Artifacts & Templates (Universal Edition)

> Fixed output artifacts and detailed templates pushed down from SKILL.md. Read when the SKILL.md step points here. Judgment thresholds and confidence tiers live in `judgment-parameters.md`; self-check in `validation-checklist.md`.

## 1. Part 3 — All-Dimension Breakdown Status Table (AMA-3)

After Part 3 queries complete, output this table verbatim, filling each cell `✓`/`✗` (copy N/A as-is). Any `✗` (except N/A) → stop and re-query immediately; do NOT enter Part 4, do NOT say "all/every dimension".

| Dimension | Primary event UV | Second event UV | DAU split | Both-event penetration computed | ✓ |
|------|:---:|:---:|:---:|:---:|:---:|
| OS | ☐ | ☐ | ☐ | ☐ | ☐ |
| New/old user | ☐ | ☐ | ☐ | ☐ | ☐ |
| Organic/paid | ☐ | ☐ | ☐ | ☐ | ☐ |
| Channel | ☐ | ☐ | ☐ | ☐ | ☐ |
| App version | ☐ | ☐ | ☐ | ☐ | ☐ |
| Country/region | ☐ | ☐ | ☐ | ☐ | ☐ |
| Entry source - primary | ☐ | N/A | aggregate DAU | N/A | ☐ |
| Entry source - second | N/A | ☐ | aggregate DAU | N/A | ☐ |

## 2. Part 3 — Anomaly-Dimension Judgment Checklist (AMA-2)

At end of Part 3, write all three explicitly as "checked ✓: <one-line explanation>"; missing any → redo immediately.

- ☐ For **each** dimension, used the "trend inflection dual threshold" to judge whether the intra-group rate has time-trend change (not between-group difference, not first/last difference)
- ☐ Produced the "anomaly-dimension candidate list" (dimension names with trend change + each group's intra-group rate trend), non-empty
- ☐ The anomaly-dimension candidate list was fed as Part 4 step 1 input

## 3. Part 4 — Candidate-Combination List (AMA-5)

Before calling AskUserQuestion in step 2a, output within the same reply:
- each line: `<incrementing number>. {suspect dimension} × {remaining dimension}`
- a final fixed line: `total N groups`
- then the MUST phrasing, then AskUserQuestion with `multiSelect: true`, one option per combination line (label = combination name).

Mechanical check: numbered items == N == AskUserQuestion option count, one-to-one mapping.

## 4. Part 6 — Conclusion Fixed Format

Conclusion has five fixed elements: inflection location / root-cause judgment / confirmed caliber / prioritized actions (P0/P1/P2) / remaining to-do.

After each conclusion, append this fixed next-step prompt:

```markdown
---

**📋 Analysis complete — next step options:**

**1. Deep-dive a dimension**
   → e.g., "deep-dive new users", "break down an entry's quick-exit rate", "version × OS cross"

**2. Incremental: shorter/longer window**
   → e.g., "look at last 7 days", "extend to 45 days"

**3. Comparison mode**
   → e.g., "compare before/after update", "this week vs last week"

**4. End analysis**
   → reply "end"

---
```

## 5. Output Spec — Detail Table Template

Each section contains:
1. **Detail data table**: dimension breakdown must include full-window daily data columns, not just first/last comparison.
2. **Fluctuation-pattern description (required)**: 1-2 sentences per dimension table (single-day jump / consecutive rise-fall / V-shape / inverted-U).
3. **Text conclusion**: point out the time-trend pattern ("fell 5 consecutive days then rebounded" rather than "fell 3.4%").

Color conventions (China market): up = red, down = green.

### Do / Don't

❌ Don't (forbidden) — first/last comparison only:
| Dimension | W1 rate | W2 rate | Change |
|------|------|------|------|
| Android | 20.37% | 19.34% | -1.03pp |

✅ Do (required) — full daily data + pattern description:
| Dimension | 08-06 | 08-07 | 08-08 | 08-09 | 08-10 | 08-11 | 08-12 | 08-13 | 08-14 | 08-15 | 08-16 | 08-17 | 08-18 |
|------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| Android | 20.43% | 18.95% | 21.31% | 20.84% | 20.63% | 20.21% | 19.17% | 19.12% | 19.37% | 18.98% | 19.42% | 19.49% | 19.87% |

> **Fluctuation pattern**: 8/11→8/12 single-day drop -1.04pp, fell 4 consecutive days to bottom 18.98% on 8/15, V-shaped rebound from 8/16 but not recovered to W1 level.
