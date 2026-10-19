# Mermaid 科研项目场景配方手册

按使用频率排列。所有示例已过 GitHub 渲染验证写法；生成后务必在目标环境渲染确认。

## 1. timeline——项目进程时间线（handoff 首选）

```mermaid
timeline
    title 项目演进
    2026-09-20 : 第二轮 : MME澄清·jackhmmer收录
    2026-09-20 : 第三轮 : v0.1.1推送GitHub
    2026-09-21 : 第十五轮 : Bizard收编
    2026-10-13 : 第十六轮 : 交付审核防线
```

要点：
- 每行 = `日期 : 事件1 : 事件2 : ...`（可多段，渲染成堆叠卡片）
- **文本内禁英文冒号 `:`**，用全角"："
- 同日期多轮自动归到同一时间点下，天然适配 handoff 多轮同日场景

## 2. gantt——有工期的排期

```mermaid
gantt
    title MC4R VNAR 设计排期
    dateFormat YYYY-MM-DD
    axisFormat %m-%d
    section 计算
    AF3 100-seed 批量预测      :a1, 2026-09-01, 10d
    OpenDDE 对照预测            :a2, after a1, 5d
    双轴四象限筛选              :a3, after a2, 3d
    section 验证
    MD 验证 (Top5×100ns)       :b1, after a3, 14d
    section 交付
    交付包五道防线              :crit, b2, after b1, 1d
```

要点：
- `after a1` 声明依赖；`crit` 红色关键路径；日期必须 `YYYY-MM-DD` 无引号
- 排期图（未来计划）用 gantt，历史回顾用 timeline——勿混

## 3. flowchart LR——pipeline 数据流

```mermaid
flowchart LR
    S1["阶段1 家族鉴定<br/>seq-struct-analysis"] -->|"homologs + 结构近邻"| S2["阶段2 结构获取<br/>structure-prediction-analysis"]
    S2 -->|"model.cif + pLDDT"| S3["阶段3 质量分析<br/>双轴四象限"]
    S3 -->|"A象限候选"| S4["阶段4 MD验证<br/>md-simulation-workflow"]
    S4 -->|"收敛轨迹"| S5["阶段5 结合能<br/>MMGBSA"]
```

要点：
- `LR` 左到右（管线）；`TB` 上到下（层级）
- 边上标签 `-->|"产物"|` 写数据流转契约（= workflow.yaml 的 outputs→inputs）
- `<br/>` 节点内换行；文本含括号必须引号包裹
- **超 12 节点拆 subgraph**：

```mermaid
flowchart TB
    subgraph CALC["计算主线"]
        S1 --> S2 --> S3 --> S4 --> S5
    end
    subgraph CHAIN["科研全链路"]
        R0["构思"] --> R1["设计"] --> W["写作"] --> V["审查"] --> P["展示"]
    end
    CALC -.->|"候选/数据"| CHAIN
```

（`-.->` 虚线 = 弱耦合/可选流转）

## 4. mindmap——知识/方法体系

```mermaid
mindmap
  root((MD 引擎选型))
    AMBER主力
      pmemd.cuda GPU最快
      ff19SB/OPC 现代力场
      QM/MM + CpHMD 生态
    迁移备选
      GROMACS 免费开放
      NAMD 大体系并行
      OpenMM Python脚本化
```

要点：
- 缩进即层级，**不能有连线/标签语法**
- 根节点 `root((文本))`；每层缩进统一（2 或 4 空格，勿混）

## 5. stateDiagram-v2——状态迁移（判定流程）

```mermaid
stateDiagram-v2
    [*] --> 待判定
    待判定 --> A可用 : gate v2 通过
    待判定 --> C待优化 : epi 不足
    待判定 --> D池空 : 无命中
    A可用 --> 交付包 : 五道防线通过
    C待优化 --> A可用 : 重新设计迭代
```

## 6. quadrantChart——双轴候选评估

```mermaid
quadrantChart
    title 候选双轴评估 (ipTM × lb)
    x-axis "低 lb" --> "高 lb"
    y-axis "低 ipTM" --> "高 ipTM"
    quadrant-1 "双引擎A"
    quadrant-2 "AF3优"
    quadrant-3 "池底"
    quadrant-4 "OD优"
    "mc4r_3893": [0.71, 0.82]
    "mc4r_1201": [0.55, 0.61]
```

要点：坐标 [0-1, 0-1]；与双轴四象限分析（structure-prediction-analysis）的语义映射：
quadrant-1 右上 = A（双引擎一致），适合给非技术干系人看的摘要版。

## 7. 渲染环境与导出

| 环境 | 状态 |
|---|---|
| GitHub（README/issue/PR 评论） | 原生渲染，\`\`\`mermaid 代码块即可 |
| Trae / VSCode Markdown 预览 | 装 "Markdown Preview Mermaid Support" 扩展 |
| Typora / Obsidian | 原生支持 |
| 导出 PNG/SVG | `npm i -g @mermaid-js/mermaid-cli && mmdc -i x.md -o x.png -s 2` |

## 8. 通用守则

1. 生成后**必须在目标环境渲染验证**——mermaid 语法错误表现为整图空白而非报错
2. 文本三禁：英文冒号、未引号包裹的括号、行尾反斜杠
3. 图是文档的一部分：进度图内嵌 handoff（PROGRESS-VIZ 区），管线图入 docs/ 并在 README 链接
4. 每次更新 handoff 后重跑生成脚本刷新图（见 SKILL.md 维护约定）
