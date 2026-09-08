# ThinkingAI 场景 Skills

为 Coding Agent 安装已经准出的 ThinkingAI 场景 Skill。

## 交互式安装

安装器会按照业务分类展示 Skill。使用空格选择整个分类或分类中的
部分 Skill，确认后再选择安装目标和安装范围。

```bash
npx skills@latest add ThinkingAIAgenticEngine/scenario-skills
```

安装指定集群版本线的最新内容：

```bash
npx skills@latest add "ThinkingAIAgenticEngine/scenario-skills#release/6.1"
```

只查看可安装的 Skill：

```bash
npx skills@latest add ThinkingAIAgenticEngine/scenario-skills --list
```

非交互式安装指定 Skill：

```bash
npx skills@latest add ThinkingAIAgenticEngine/scenario-skills \
  --skill <skill-name> [another-skill-name...]
```

需要分类选择时不要传 `-y` 或 `--all`。自动化安装必须显式传入
`--skill`，避免一次安装全部场景 Skill。
