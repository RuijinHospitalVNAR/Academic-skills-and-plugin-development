---
name: project-viz
description: >
  项目进程可视化与 pipeline 示意图生成（Mermaid）。Use when 用户要看项目进度图/进程时间线、
  handoff 可视化（把文字交接记录变成 timeline/gantt）、把复杂 pipeline/workflow 画成流程图或
  思维导图、复盘项目演进、或要求 mermaid/gantt/flowchart/mindmap/时序图。关键词：进度图、
  进程可视化、项目进度、里程碑、时间线、思维导图、流程图、示意图、pipeline 图、工作流图、
  mermaid、gantt、handoff 可视化、progress visualization、project timeline。
  边界（蛋白药物设计插件内置版）：本技能只管**项目管理类**图（进程/管线/架构）；
  科研数据图表（volcano/KM/ heatmap 等）走 bizard；论文出版级图形走 nature-figure；
  MD 轨迹分析图走 md-simulation-workflow。
---

# 项目进程与 Pipeline 可视化 (Project & Pipeline Visualization)

解决两个长期痛点：① handoff 全是文字，项目跨多轮对话后进程没有一眼可读的进度图；
② 复杂 pipeline（如本插件 11 阶段工作流）纯文字描述，理解和记忆成本高。

**技术选型：Mermaid**——纯文本写进 markdown，GitHub 原生渲染、Trae/VSCode Markdown 预览
（装 Mermaid 插件）即可看图，无二进制、可版本管理、AI 可自动生成与维护。

## 0. 何时使用

- 项目 handoff 更新后刷新**进程时间线**（timeline/gantt）
- 复杂 pipeline / workflow.yaml 需要一图看懂数据流转（flowchart）
- 方法论/决策树/知识结构需要**思维导图**（mindmap）
- 周期回顾（periodic-review）需要里程碑可视化
- 给合作者/导师讲清"这个项目做到哪了、整体架构是什么"

## 1. 两个标准入口（脚本零依赖，python3 直跑）

| 任务 | 命令 | 输出 |
|---|---|---|
| handoff → 进度时间线 | `python3 scripts/handoff_gantt.py <handoff.md>` | mermaid timeline（按日期分组的多轮事件） |
| workflow.yaml → 管线图 | `python3 scripts/workflow_flow.py <workflow.yaml>` | mermaid flowchart LR（阶段→skill→数据流） |

两个脚本都支持 `--inplace` 把图插入/刷新到 markdown 的 `<!-- PROGRESS-VIZ -->` 标记区
（已存在则替换，不存在则插在首个二级标题后）。

**自动刷新（推荐）**：`scripts/auto_refresh.py` — 核对 handoff 轮次数与图内事件数，
不一致自动刷新。已接入 git 钩子（本仓库 `.git/hooks/`）：
- **post-commit**：每次提交后自动核对刷新仓库内全部 handoff*.md 进度图（本地文件，不入库）
- **pre-commit**：workflow.yaml 有暂存变更时自动重生成 docs/pipeline-viz.md 并追加暂存
- 其他仓库安装：把上述两段钩子脚本（见 SKILL.md 同目录 `auto_refresh.py` docstring）接入目标仓库 `.git/hooks/`
- 设计原则：图表同步失败**只告警不阻塞**；安全门禁（secret-scan）永远第一道

**维护约定（长期规则）**：handoff 更新后无需手动跑命令——下一次 commit 时钩子自动同步；
急用时也可手动 `python3 scripts/auto_refresh.py --repo <repo>`。图是 handoff 的一部分，不是额外产物。

## 2. Mermaid 配方速查

详细配方与坑：[references/mermaid-cookbook.md](references/mermaid-cookbook.md)

| 场景 | 图型 | 一句话选型 |
|---|---|---|
| 项目多轮演进 | `timeline` | 离散事件流（handoff 轮次天然适配） |
| 有工期的排期 | `gantt` | 需要条形区间/依赖/今日线时 |
| pipeline 数据流 | `flowchart LR` | 节点=阶段，边=产物传递 |
| 分层架构/决策 | `flowchart TB` + subgraph | 分组归块 |
| 知识/方法体系 | `mindmap` | 发散结构无连线语义 |
| 状态机（如四象限判定） | `stateDiagram-v2` | 状态+迁移 |
| 候选优先级评估 | `quadrantChart` | 双轴散点（如 ipTM×lb 筛候选） |

## 3. 高频坑速查

| 坑 | 规则 |
|---|---|
| 文本含特殊字符 | 节点文本一律用引号包裹 `A["文本(x)"]`；`()`裸写部分渲染器报错 |
| 英文冒号断行 | timeline/任何文本内**不能出现英文 `:`**，中文全角"："安全 |
| timeline 不渲染 | GitHub 需 mermaid ≥v10（已满足）；本地 VSCode 需更新 Mermaid 插件 |
| gantt 日期格式 | 必须 `dateFormat YYYY-MM-DD` 且日期无引号 |
| 图太密 | flowchart 超 ~12 节点就拆 subgraph；timeline 单日期事件 >6 条合并描述 |
| 渲染验证 | 生成后必须在目标渲染环境（GitHub/IDE 预览）确认一次再交付；mermaid 语法错会整图空白 |

## 4. 产出清单

```text
viz/
├── progress-timeline     # 或内嵌 handoff 的 PROGRESS-VIZ 区
├── pipeline-flow.md      # workflow.yaml 生成的管线图（入 docs/ 或 README 引用）
└── *.md                  # 各类按需图（mindmap/state/quadrant）
```

导出位图（汇报用）：`mmdc -i in.md -o out.png -s 2`（mermaid-cli；无则用 IDE 预览截图）。
