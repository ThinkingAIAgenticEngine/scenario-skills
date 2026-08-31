# Step 08: Publish Report (Optional)

## Objective

Publish the final report to Feishu Docs or Knowledge Base.

## Input / Output

Input: `{{workspace_dir}}/final_report.md`
Output: Feishu document link

### 8.0 Ask Publish Method

```
1. 📄 Feishu Knowledge Base (recommended)
2. 📁 Feishu Cloud Space
3. 💬 Feishu Group Chat
4. ⏭️ Skip, local only
```

### 8.1 Publish to Knowledge Base

Create doc with title: `IAA Postmortem Report_{{project.game_name}}_{{window.end}}`. Write report content.

### 8.2 Publish to Cloud Space

Same as 8.1.

### 8.3 Group Chat

Send summary + doc link:

```
📊 IAA Postmortem Report Generated
**{{project.game_name}} {{project.version}}**
D2: {{d2}}% | D3: {{d3}}% | D7: {{d7}}%
Rating: {{rating}}
Issue: {{one_line_problem}}
📄 [Full Report]({{doc_url}})
```

### 8.4 Complete

```
✅ Report Published
Link: {{url}}
Local: {{workspace_dir}}/final_report.md
```

## Status Output

- `STEP_SUCCESS` — Published
- `STEP_ERROR` — Failed but local saved
