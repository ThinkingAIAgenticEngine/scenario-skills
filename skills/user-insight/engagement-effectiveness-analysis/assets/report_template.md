# Analysis Report Template

Deliverable 2 of 2, produced by `scripts/generate_report.py`.

**Purpose: explain how the campaign performed and what to do next.** Written for
a business reader, not an analyst. Conclusions first, evidence second, actions
last.

The report is generated from `analysis.json`; the template below documents the
contract so the generator can be changed without losing a section.

## Header block

```
> **数据来源模式**：mode A: Engage native  |  mode B: third-party event recovery
> **策略与回收事件**：<name> (object id `<id>`) ｜ recovery events: `<event>` (window <n><unit>)
> **触达渠道**：<channel> ｜ **触发时间**：<time> (<timezone>) ｜ **触发规则**：<crontab in plain words>
> **数据范围**：<start> ~ <end> (<n> days) ｜ **生成时间**：<timestamp>
> **配套明细**：`<workbook filename>` (7 sheets, per-day / per-instance / raw)
```

The source-mode line is mandatory. A reader must be able to tell whether the
numbers came from the platform's own definitions or from a reconstructed event
chain, because the two are not equally precise.

`触发时间` falls back to the campaign's `startDate` when the platform left
`triggerTime` empty (a common case for crontab-driven campaigns). The timezone
and the marker share one pair of parentheses - `<time>（<timezone>，任务起始日）`
- so the line never reads `<time>（任务起始日）（UTC+8）`. Without the marker the
workbook and the report would disagree about the same campaign. The `触发规则`
segment is emitted only when the platform supplied a cron expression.

## Confidence statement

Rendered directly under the header, before any finding:

```
> **置信度声明**：this analysis carries the following degradations …
> | degradation | impact | precision loss |
```

Every degradation recorded in `analysis.json` appears here. The precision figures
are estimates and are labelled as such. **Suppressing this block is not an
option** - a conclusion drawn from a degraded measurement must say so on the same
page as the conclusion.

## Field caveats

Rendered directly after the confidence statement, whenever
`analysis.json.field_caveats` is non-empty:

```
> 📐 **口径提示**：the following fields carry different definitions in different
> platform interfaces; all values are reported as returned.
> - **<field>**：<interface A> = <value>；<interface B> = <value>。<why it differs>
```

A degradation says *a measurement is weaker than it looks*; a caveat says *two
correct numbers are not comparable*. Both are silent failures - nothing errors
out, the reader just concludes something wrong - so both must be stated on the
page rather than left for the reader to notice.

## The six sections

### 一、结论先行
One verdict line, then three core findings, then the recommended actions.

```
**效果判定**：effective / ineffective / needs observation / not evaluable
```

The verdict is followed by a one-line reason. `not evaluable` is a legitimate
verdict and must be used rather than inventing a weak conclusion when the chain
broke.

The three findings are ranked, and when there are no problems the findings
describe what went right with the numbers that show it - never "no anomalies
found" as the only content.

### 二、效果总览
2.1 the funnel table: stage, users, stage conversion, cumulative conversion, drop
count, drop rate, note. An unmeasurable stage is shown with a note explaining
that it was not measured.
2.2 benchmark comparison: rate, actual, benchmark, red/amber/green flag, advice.

### 三、归因分析
Why the result is what it is - audience, content, timing, frequency or channel.
Separates what the data supports from what it merely suggests.

### 四、问题定位
Prioritised issues, each with priority, severity, category, title, detail, and
the sheet that evidences it. Priority order:
`broken data chain > benchmark miss > experiment inconclusive > content/timing > segment mismatch`.
A problem already reported as a bleed point or a data break is not repeated
under a second category.

### 五、优化建议
One entry per issue: action, detail, and **expected impact**. A recommendation
without a stated expected impact is not actionable and should not be emitted.

### 六、验证方案
How to confirm the fix worked: method, the indicators to compare with their
baseline and target, and the execution steps. When no baseline could be
established, the section says so explicitly instead of presenting an empty table.

## Hard requirements

| Requirement | Reason |
|---|---|
| every conclusion cites its workbook sheet | the business reader must be able to verify a claim without asking |
| confidence statement present whenever degradations exist | degraded precision must never be presented as measured fact |
| source mode stated in the header | the two modes are not equally precise |
| no "anomalous 100% drop" language for missing data | missing data is reported as not returned, never as churn |
| no credentials, internal IPs or absolute home paths | the report is delivered outside the company |

## Naming

```
output/{strategy_name}_效果分析报告_{YYYYMMDD}.md
```

Optional: convert to docx or PDF through `tencent-docx`. No cloud delivery is
performed by this skill - the two local artifacts are the deliverable.
