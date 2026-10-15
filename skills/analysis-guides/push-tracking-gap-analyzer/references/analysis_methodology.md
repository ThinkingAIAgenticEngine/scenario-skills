# Strategy-to-event mapping

Apply this method to every supplied strategy. Example event names below are illustrative, never evidence that a customer's workbook contains them.

## 1. Decompose the strategy

Extract the audience, action, object, time window, frequency threshold, exclusions, intended conversion, and channel. For example, a reminder for users with no second note requires an account-age anchor, a complete set of note creation/import actions, and a count window. A backup reminder requires both eligibility and a verifiable enabled state.

Separate audience selection (`【圈人】`) from conversion attribution (`【效果回收】`). A field may serve both purposes; explain each use. Receipt events measure arrival/click behavior, while a downstream business event measures the intended outcome.

## 2. Search all available evidence

Search event names, display names, descriptions, property names, common/user properties, and documented value domains. Record the exact source event/property and observed enum value. Absence is a conclusion only after a complete source read.

Prefer a direct existing event, then a suitable enum on an existing event, then a qualified proxy. Propose a new event only if existing evidence cannot answer the strategy. For instance, an import source value on a generic creation event may cover imported notes without a separate import event. A tool-selection event is only a proxy for opening an editor; it misses opens without a tool click.

## 3. Reuse naming conventions

For a missing source/duration/result property, search events with the same tag first, then the same module prefix, then the complete plan. Reuse the exact English name, display label, and type when semantics match. Do not invent `click_source` if `source` already has the required meaning. Do not change a numeric source enum into a text field without an explicit design decision.

The checker compares names and types, but it does not infer that differently named properties are equivalent. Search common properties for such equivalents before adding anything.

## 4. Build the review matrix

Use one row per strategy with stable ID, original condition, desired conversion, candidate event/property, evidence, missing fields, status, and limitations. Each strategy may reference several events. Maintain all strategy IDs when consolidating an event shared by multiple strategies.

Classify findings as new event, property patch, already covered, or unresolved. An unknown enum domain or an incomplete strategy is unresolved, not proof of a gap or full coverage.

## 5. Consolidate and validate

- Combine repeated events and merge their strategy references.
- Remove properties already present on the event or in common properties.
- Resolve differing display names/types across all occurrences.
- Assess receipt events `ops_view` and `ops_click` even when the strategy omits them; supplement only missing coverage.
- Compare the union of classified strategy IDs with the original ID set. A sum of category counts can double-count one strategy and hide another.
- Preserve already-covered results in the matrix so the reviewer can see why no development work is needed.

Before review, ensure every proposed event or property has a specific business purpose and every coverage claim has traceable source evidence. Do not copy hypothetical names into the final supplement.
