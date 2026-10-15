# HTML Report Output Spec (Universal Edition)

> Trigger: when the user explicitly asks "output report / generate report / generate html report", read this file to generate an HTML report.
> If the user did not ask for a report, output text/Markdown conclusions per SKILL.md "Output Spec" by default; do NOT generate HTML.

When the user asks for a report, generate a **self-contained HTML file** (single file, inline CSS, no external dependencies), write it to the analysis working directory, present via `present_files`. Fixed three-layer structure:

1. **Conclusion first (top)**:
   - "Conclusion summary": the core root cause in one sentence (qualitative type + primary driver dimension + key numbers)
   - "Three conclusions": type-1-5 judgment result + exclusions, using tags (root-cause red tag / normal green tag / suggestion blue tag)
   - "Action recommendations": P0/P1/P2 prioritized

2. **Block report (middle, each block = detail table + that table's analysis conclusion)**: for every table of data queried, make an independent "card":
   - Card title (e.g., "Part 2: New/Old User Dimension (primary driver)")
   - **"This report's conclusion" callout box** (right after the title, give that table's judgment conclusion first)
   - Full daily detail table (N date columns, not first/last summary)

> **【MUST·cards must be grouped and ordered by Part layer, do NOT shuffle】**
> All cards in the block report must be **strictly grouped by SKILL.md analysis-workflow Part layers**, separated by prominent layer headers, order not reversible, not interleaved:
>   1. **Part 1 (aggregate trend)**: aggregate series card first, as baseline.
>   2. **Part 3 (multi-dimension breakdown, all dimensions on)**: OS, new/old user, organic/paid, channel, app version, country/region, entry-source (all product-config splits) **all** in sequence. **App version, entry source etc. are Part 3 components; do NOT move them after Part 4 cross drill-down**.
>   3. **Part 4 (cross drill-down)**: only cross drill-down cards (suspect dimension × remaining dimensions) + residual-signal-check card.
>   4. **Part 5 (supply side / environment layer / root-cause library)**: if the product configured supply-side events, supply-side cards go here.
> Within the Part 3 card group, the primary-driver dimension is highlighted (hl), but **still ordered within Part 3's dimension-breakdown sequence**, not detached from its Part. Judgment method: after generating the report, ask "is this card Part 1, Part 3, Part 4, or Part 5 content?", ensure each card lands in the correct Part group.

3. **Comprehensive conclusion (bottom)**: inflection location + primary driver + exclusions + action recommendations + caliber memo (incl. product-config summary)

**HTML technical spec**:
- Single file, `<style>` inline; light theme (white background, dark text), CSS variables for unified colors
- Up red / down green: `.down` (down / penetration down) = green `#2e7d32`, `.up` (up) = red `#d32f2f` (China market convention)
- Tables daily, right-aligned numbers, first-column date left-aligned; zebra stripes for readability
- "This report's conclusion" uses a prominent background callout (e.g., yellow `#fff8e1`), root-cause highlight bar uses pink `#fce4ec`
- Report cards separated by white card + rounded corners + thin border

**Report conclusion-layer echo**: top conclusion summary → each block's "this report's conclusion" → bottom comprehensive conclusion, forming a "conclusion → evidence → conclusion" loop; numbers must be consistent (the same number consistent across all three places), do NOT drift caliber (top says -6pp, block writes -5pp).
