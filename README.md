# ThinkingData Scenario Skills

Install approved ThinkingData scenario Skills for your coding agent.

## Interactive installation

The installer groups Skills by business category. Use Space to select a
whole category or individual Skills, then confirm the installation.

```bash
npx skills@latest add ThinkingAIAgenticEngine/scenario-skills
```

Install the latest release for a specific cluster line:

```bash
npx skills@latest add ThinkingAIAgenticEngine/scenario-skills#release/6.1
```

List available Skills without installing:

```bash
npx skills@latest add ThinkingAIAgenticEngine/scenario-skills --list
```

Install only the selected Skills:

```bash
npx skills@latest add ThinkingAIAgenticEngine/scenario-skills \
  --skill <skill-name> [another-skill-name...]
```

Do not pass `-y` or `--all` when you want the interactive category picker.
Automation must pass `--skill` explicitly to avoid installing every Skill.

See [README.zh-CN.md](./README.zh-CN.md) for Chinese instructions.
