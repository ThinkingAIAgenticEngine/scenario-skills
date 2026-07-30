---
name: community-analyzing-theme-comment
description: Perform deep analysis of a topic’s comment section and generate a structured analytical report. Use this skill when users need an in-depth comment analysis for a specific topic (post or video).

metadata:
  author: Uni
  team: product
  version: "1.0.0"
  created: "2026-03-12"
  updated: "2026-03-12"
  space: commercial
  category: drafts
  status: draft
  tags:
    - community
    - comments
    - deep-analysis
  dependencies:
    - community-mcp-content
  compatible-tools:
    - claude-code
  commercial:
    target-persona: Operations or analyst
    value-proposition: High
    pricing-tier: M1
    requires-mcp: apollo-mcp
    demo-scenario: Direct use
---

# Skill: analyzing-theme-comment (deep comment analysis)

## Overview

This skill performs deep analysis of comment threads for a specified post or video in the game community, following a structured flow to produce a report covering trends, viewpoint distribution, and synthesis.

## Prerequisites

- **MCP:** community-mcp-content (community content MCP)
- **gameId:** Must be explicit
- **Channel:** Know which channel hosts the target post/video

## When to use

- Sentiment in a hot post’s comments
- Audience feedback after a video drop
- Viewpoint distribution for a specific topic
- Evaluating content performance and player mood

---

## Execution flow

### Step 1: Identify the target post or video

#### 1.1 Check whether the user specified a target

Confirm the user provided:

- Post/video UUID
- `channelId`
- Resource type: post (`0`) or video (`1`)

**If yes, go to Step 2.**

#### 1.2 Search when no target is given

Use community-mcp-content `search_posts`:

**Payload:**

```json
{
  "gameId": "<game ID>",
  "startTime": "<start>",
  "endTime": "<end>",
  "searchWord": "<keyword>",
  "channelIdList": [<channel IDs>],
  "resourceType": [0, 1],
  "pagerHeader": {
    "pageNum": 1,
    "pageSize": 20,
    "orderBy": 4
  }
}
```

**Parameters:**

| Field         | Required | Notes                     |
| ------------- | -------- | ------------------------- |
| gameId        | Yes      | Game ID                   |
| startTime     | Yes      | Lower bound, `yyyy-MM-dd` |
| endTime       | Yes      | Upper bound, `yyyy-MM-dd` |
| searchWord    | No       | Keyword                   |
| channelIdList | No       | Channel filter            |
| resourceType  | No       | `0` post, `1` video       |
| orderBy       | No       | `4` = hotness desc        |

**Channel reference:**

| channelId | Name     |
| --------- | -------- |
| 1         | TapTap   |
| 2         | BiliBili |
| 3         | Douyin   |
| 5         | Weibo    |
| 7         | RedNote  |
| 8         | HeyBox   |
| 9         | Douyu    |
| 11        | Tieba    |
| 17        | Nga      |

**Logic:**

1. Search by keyword or hot topic
2. Sort by heat; surface top items
3. Have the user pick a target
4. Capture UUID and channelId

---

### Step 2: Fetch comments

#### 2.1 Post/video detail

Use `get_post_detail`:

```json
{
  "gameId": "<game ID>",
  "channelId": "<channel ID>",
  "uuid": "<content UUID>",
  "resourceType": <0 post, 1 video>,
  "replyPagerHeader": {
    "pageNum": 1,
    "pageSize": 100,
    "orderBy": 0
  }
}
```

| Field            | Required | Notes               |
| ---------------- | -------- | ------------------- |
| gameId           | Yes      | Game ID             |
| channelId        | Yes      | Channel ID          |
| uuid             | Yes      | Content UUID        |
| resourceType     | Yes      | `0` post, `1` video |
| replyPagerHeader | No       | Comment paging      |

#### 2.2 Paginate to completeness

1. First page (pageSize ~100)
2. If `hasMore`, fetch next page
3. Repeat until complete

**Filter out low-value replies:**

- Spam / duplicates / flood
- Emoji-only or symbol-only (“???”, “!!!”)
- Fewer than 3 meaningful characters
- System/automated official messages

**Record:**

- Total vs. valid comment counts
- Time span
- Channel distribution if applicable

---

### Step 3: Deep analysis

#### 3.1 Trend

**3.1.1 Time distribution (daily)**

| Date       | Comments | Cumulative |
| ---------- | -------- | ---------- |
| 2026-03-10 | 150      | 150        |
| …          | …        | …          |

**3.1.2 Sentiment by day**

| Date       | Positive | Neutral | Negative |
| ---------- | -------- | ------- | -------- |
| 2026-03-10 | 0.45     | 0.35    | 0.20     |
| …          | …        | …       | …        |

---

#### 3.2 Viewpoints

**3.2.1 Method**

1. Cluster themes from valid text
2. Surface recurring keywords/phrases
3. Merge near-duplicates
4. Split positive vs. negative stances

**3.2.2 Viewpoint object**

| Field       | Description                     |
| ----------- | ------------------------------- |
| Title       | Short label (~20 chars)         |
| Description | ~100 chars                      |
| Match count | Comments aligned with this view |
| Examples    | Up to 10 representative quotes  |

**3.2.3 Opposing views**

- Allow clear pro/con on the same subject
- Do not merge contradictions; list separately

**Example:**

**Positive viewpoint 1**

- **Title:** Roguelike mode praised
- **Description:** Players like the new roguelike loop for variety and replay value.
- **Matches:** 45
- **Quotes:** …

**Negative viewpoint 1**

- **Title:** Daily grind frustration
- **Description:** Some players say dailies take too long and mats are too scarce for low spenders.
- **Matches:** 38
- **Quotes:** …

---

#### 3.3 Synthesis

**3.3.1 Volume summary**

- Total vs. valid counts
- Overall sentiment mix
- Peaks and likely drivers
- Optional benchmark vs. similar content

**3.3.2 Viewpoint synthesis**

- Dominant positive themes and reach
- Dominant negative themes and reach
- Conflict axes
- Core asks from players

**3.3.3 Ecosystem**

- Tone: harmonious / polarized / neutral
- Alignment with OP/video
- Audience segments and risks/opportunities

---

## Output format

```
# Themed Comment Deep-Dive Report

## 1. Basics
- Title: [title]
- Channel: [name]
- Published: [time]
- Analysis window: [start] – [end]
- Valid comments: [X]

## 2. Trends
### 2.1 Time series
[table or narrative]
### 2.2 Sentiment mix
[table or narrative]

## 3. Viewpoints
### 3.1 Positive
[…]
### 3.2 Negative
[…]

## 4. Summary
### 4.1 Volume
### 4.2 Viewpoints
### 4.3 Ecosystem & recommendations
```

---

## Notes

1. **Completeness:** Paginate until all comments are retrieved.
2. **Quality:** Strictly filter spam/noise.
3. **Objectivity:** Ground clusters in actual text.
4. **Opposition:** Preserve real splits in opinion.
5. **Representative quotes:** Weight typicality, engagement, recency.

---

## Error handling

| Situation                    | Action                                      |
| ---------------------------- | ------------------------------------------- |
| Invalid gameId               | Ask user to verify                          |
| Missing post/video           | Verify UUID                                 |
| Fetch failure                | Retry; check connectivity                   |
| Fewer than 10 valid comments | Warn sample is thin; suggest another target |
| Invalid channelId            | Show channel list                           |

---

## Tool dependencies

| Tool                 | Role              |
| -------------------- | ----------------- |
| search_posts         | Find posts/videos |
| get_post_detail      | Detail + comments |
| get_comments_summary | Optional assist   |

---
