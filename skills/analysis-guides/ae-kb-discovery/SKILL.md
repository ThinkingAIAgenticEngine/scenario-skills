---
name: ae-kb-discovery
description: >
  Discover and read AE/TE/ThinkingEngine knowledge bases accessible to the current user through read-only operations. Use when the user explicitly asks to search knowledge bases, internal documentation, or company materials. Also use when a task requires internal facts or business context, including product design and rules, events, campaign or operations calendars, release and iteration records, workflows, policies, and terminology; use it as well when this context is needed to explain data analysis results, anomalies, or trends and form evidence-backed conclusions. Do not use if the user explicitly asks not to access knowledge bases.
---

# Knowledge Base Discovery

Treat knowledge bases as an optional source of internal facts and business context. Keep the user's original goal unchanged; knowledge base retrieval is a supporting workflow, not the task itself.

## Decide Whether to Use This Skill

Use this skill when:

- The user explicitly asks to search a knowledge base, internal documentation, or company materials.
- The task requires organization-specific facts or context, such as product design and rules, events, campaign or operations calendars, release and iteration records, workflows, policies, or terminology.
- Internal context is needed to explain data analysis results, anomalies, or trends and form evidence-backed conclusions.
- The knowledge base context currently available does not cover the question, and discovering other accessible sources has clear value.

Do not use this skill when:

- The user explicitly asks not to use knowledge bases.
- The task only requires querying real-time state or performing an operation and does not need document context.
- General knowledge is sufficient for a reliable answer and internal evidence would not materially improve it.

## Read-Only Retrieval Workflow

### 1. Get the List of Accessible Knowledge Bases

First, get the lightweight list of knowledge bases accessible to the current user:

```bash
ae-cli kb +list
```

Use the exact `scope` and knowledge base name returned by the command, together with available metadata such as description, tags, language, and `bindings`. A binding identifies an associated context through `targetType`, `targetId`, and optional `targetName`. Do not guess a name, scope, or binding. Treat metadata returned by `+list` only as input for candidate selection, not as evidence from knowledge base content.

If `+list` is unavailable or fails, do not guess which knowledge bases exist. If the user explicitly requested a knowledge base search, explain that discovery cannot currently be completed. Otherwise, return to the original task and reassess the capabilities currently available.

### 2. Rank Candidate Knowledge Bases

Rank candidates in this order:

1. Prefer a knowledge base explicitly named by the user. Use the exact name and scope returned by `+list`, regardless of whether it has a matching binding.
2. Prefer candidates whose bindings exactly match the current session context. Match `targetType: project` against the current analysis project ID, `targetType: space` against the current community space ID, and `targetType: dwSpace` against the current digital workspace code.
3. For the remaining candidates, compare the user's request with the knowledge base name, description, and tags. Use language only as a preference between candidates with similar relevance; language alone does not establish relevance.

Compare `targetId` with the corresponding current ID or code first. Use `targetName` only as a secondary signal when an ID or code is unavailable; do not replace a conflicting ID match with a name match. A candidate with no bindings or no current-context match remains eligible for semantic ranking. A binding to another project or space lowers implicit priority but does not exclude the candidate, and an explicit user choice still takes precedence.

Select one preferred knowledge base by default. When several candidates are highly relevant, retain no more than three and try them one at a time in priority order. Do not read the indexes of all candidates in advance. A binding, name, description, tag, or language match only indicates that a knowledge base is worth searching; it does not prove a content match, grant access, or count as knowledge base evidence.

### 3. Read the Preferred Knowledge Base Index

Read the index only for the current preferred knowledge base. Specify exactly one knowledge base:

```bash
ae-cli kb +index --sources '[{"scope":"<exact scope>","name":"<exact knowledge base name>"}]'
```

Use the returned navigation information to decide whether the knowledge base is worth searching further and to identify potentially relevant page topics and keywords. Do not omit `--sources`, and do not pass multiple knowledge bases at once. If the index is clearly unrelated to the user's question, switch to the next candidate instead of continuing to search the current knowledge base.

### 4. Locate Relevant Pages

Search the current knowledge base using high-information keywords:

```bash
ae-cli kb +grep --query "<keywords>" --sources '[{"scope":"<exact scope>","name":"<exact knowledge base name>"}]' --top-k 10
```

After inspecting the first search result, adjust the query at most once. Do not repeatedly rewrite the query or loop over searches within the same candidate knowledge base.

### 5. Read Supporting Evidence

Read only paths actually returned by `+index` or `+grep`:

```bash
ae-cli kb +read --source '{"scope":"<exact scope>","name":"<exact knowledge base name>"}' --path "<returned relative page path>" --offset 1 --limit 200
```

Treat each returned page path as an opaque identifier and copy it character-for-character from the most recent `+index` or `+grep` result. Do not derive a path from a page title, heading, tags, or link text, and do not insert, remove, replace, or normalize any character or separator. For example, pass `concepts/A-B实验.md` exactly as returned; never rewrite it as `concepts/A/B实验.md`. If `+read` reports that the page does not exist, return to the latest result and copy the path again; do not add a `wiki/` prefix or try another path variant unless that exact variant was returned by `+index` or `+grep`.

When more context is needed, adjust the read window according to the returned line numbers. Do not guess paths, and do not treat an unread title or summary as page evidence.

### 6. Synthesize Only When Necessary

Use `+ask` when synthesizing multiple located pages has clear value:

```bash
ae-cli kb +ask --question "<original question>" --sources '[{"scope":"<exact scope>","name":"<exact knowledge base name>"}]'
```

Its natural-language answer does not by itself prove that the knowledge base matched the request. Key conclusions must still map to page content retrieved through `+grep` or `+read`.

## Assess Coverage

- Full coverage: The page content read supports the key conclusions required for the information request or analysis.
- Partial coverage: The page content read provides only background, definitions, or partially relevant facts and cannot independently support the required conclusions.
- No coverage: No suitable candidate knowledge base exists, or `+grep` and `+read` return no content that can support the conclusions.

A candidate returned by `+list`, navigation returned by `+index`, a successful command, a tool call, or a metadata match does not count as a knowledge base hit. Only relevant page content that has actually been read can serve as knowledge base evidence.

## Use Knowledge Base Evidence in Analysis

When using internal context to explain data analysis results, anomalies, or trends:

1. First state what the analysis itself demonstrates, including the metric change, time range, affected entity, and magnitude.
2. Search using the affected entity, metric, time range, campaign or event name, product area, and release or version name.
3. Verify that the retrieved evidence:
   - Applies to the same entity, product area, or business scope.
   - Overlaps with the time range covered by the analysis.
   - Records an event, rule, release, or change that actually took effect.
   - Uses a version and effective date that remained valid during the analysis period.
4. Distinguish planned activities from completed events. A calendar or roadmap does not prove that an activity or release occurred unless the retrieved content confirms execution.
5. Combine analytical facts with retrieved internal evidence and state directly what the evidence supports. Do not list possible causes that lack evidence.
6. Use causal language such as "caused" or "led to" only when the available evidence establishes causality. Otherwise, say that the evidence supports a factor as a key explanation or that the factor is consistent with the observed change.
7. If the evidence is insufficient, state clearly that the cause cannot be determined from the available evidence. Do not fill evidence gaps with speculation.
8. When appropriate, organize the final answer in this order:
   - Conclusion.
   - Analytical evidence.
   - Knowledge base evidence and relevant page paths.
   - Necessary limitations of the evidence.

## Handle Partial or No Coverage

When knowledge base evidence provides only partial coverage, is entirely absent, or retrieval fails:

1. Stop repeating searches against the same candidate knowledge base.
2. If ranked candidates remain, switch to the next candidate. Search no more than three knowledge bases in one task.
3. When all candidates provide no coverage, return to the user's original request instead of remaining in the knowledge base retrieval subtask.
4. Reassess the capabilities currently available and choose the next path that best serves the original task. Do not hard-code a fixed fallback.
5. Retain verified background evidence when useful, but never attribute conclusions drawn from other sources to a knowledge base.
6. Do not report an unsuccessful knowledge base search unless the retrieval failure itself affects the user's decision.

Knowledge base information must not replace required business operations. If the original task also requires real-time data or an action, complete that part through the appropriate available capability.

## Safety Boundaries

- Limit this skill to `+list`, `+index`, `+grep`, `+read`, and `+ask` when synthesis is genuinely necessary. Do not create, upload, compile, or delete knowledge bases.
- Respect existing scope, tenant, and membership permissions. Do not attempt to bypass an inaccessible knowledge base.
- Do not expose internal root paths, access tokens, or raw permission metadata.
- For protected knowledge bases, provide only summaries and synthesized conclusions allowed by the current permissions. Do not export complete source text or extensive verbatim excerpts.
