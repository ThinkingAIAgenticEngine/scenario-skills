---
name: analysis-scope-alignment
description: Aligns and explains analytical scope for dashboards, reports, queries, SQL, tags, cohorts, virtual attributes, dimension-table attributes, and related analysis objects. Use when users ask about the scope, definition, or coverage of any of these analysis objects.
---

# analysis-scope-alignment

Use this skill to align and explain analytical scope for existing analysis objects.

## Reference structure

This skill contains both Chinese and English reference materials.

Use:
- `references/skill-main-zh.md`
- `references/skill-main-en.md`
- `references/scope-definition-guide-zh.md`
- `references/scope-definition-guide-en.md`

## Reference responsibilities

- `references/skill-main-zh.md` and `references/skill-main-en.md`
  - contain the main capability specification, workflow, I/O contract, and rules & boundaries

- `references/scope-definition-guide-zh.md` and `references/scope-definition-guide-en.md`
  - contain the detailed guide for layered scope explanation, SQL parsing, usage-layer explanation, definition-layer drill-down, and reference mapping

## Language handling

The Chinese and English files are not separate skills and should not be treated as mutually exclusive routing targets.

They exist as bilingual reference materials for the same skill.

Execution requirements:
- understand and apply the skill by consulting both Chinese and English reference materials when helpful
- answer in the user's current language
- if the user uses a third language, still rely on the bilingual reference materials and respond in the user's language

## Shared references

Use the product reference files in `references/` for:
- definition-layer explanation
- rule validation
- boundary-condition clarification
- product-behavior reference

## Default operating order

1. Identify the analysis object first
2. Determine whether the user needs current-implementation alignment only or deeper definition-layer drill-down
3. Explain the current implementation scope first
4. Confirm whether the current explanation matches the user's intended business scope
5. Drill down only when needed
6. Produce reusable scope-alignment output for downstream work

## Core execution rules

- identify the analysis object before giving any high-confidence final scope conclusion
- prefer customer-provided SQL or object information first
- if information is insufficient, first provide the currently confirmable scope explanation
- request additional information only when it is necessary for higher-confidence judgment
- if customer information is still insufficient, use available system context or tools when applicable
- explain current implementation scope before drilling into definition-layer semantics
- clearly distinguish:
  - confirmed
  - not used in current implementation
  - cannot yet be confirmed
- explicitly mark inference or pending confirmation when evidence is incomplete
- do not treat customer expectation as implementation fact
- do not treat the current usage of a tag, cohort, virtual attribute, or dimension-table attribute as the definition of that object itself
- after each round of scope explanation, explicitly confirm whether the explanation matches the user's intended business scope
- if the current scope does not match expectation, provide recommended scope options instead of only asking the user what they want
- do not modify any underlying database data
- the final scope-alignment output should be reusable for downstream analysis, sql rewriting, report generation, or result review