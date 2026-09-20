---
name: protein-design-workflow
description: 蛋白质药物设计端到端工作流编排器。Use when 用户提出跨阶段的蛋白质药物设计任务（如"从序列到 MD 验证的完整分析"、"把这个蛋白的家族、结构、动力学、结合能一起做"）、要确定某任务应该调用哪个技能与什么顺序、要规划多阶段项目的时间线与算力、或需要在本插件中接入新技能/新引擎/新分析工具时。它是本插件的路由层与扩展入口，自身不执行具体计算。关键词：工作流、pipeline、完整流程、任务编排、算力规划、接入新技能、扩展插件。
---

# 蛋白药物设计工作流编排 (Workflow Orchestrator)

本技能是路由层：把用户需求映射到本插件的三个执行技能，管理阶段间的数据契约与算力排期。配置声明见插件根目录 [workflow.yaml](../../workflow.yaml)。

## 1. 主流水线（五阶段数据流）

```text
[1] family-identification   seq-struct-analysis      输入: FASTA
        │ 输出: 家族归属 + 同源簇 + 结构锚点
        v
[2] structure-acquisition   structure-prediction-analysis
        │ 输出: model.cif + 置信度 (AF3 100-seed 批量 / 单结构)
        v
[3] structure-analysis      structure-prediction-analysis
        │ 输出: 四象限判定 + 口袋/epitope 几何
        v
[4] md-validation           md-simulation-workflow
        │ 输入: 阶段2/3 结构 + 可选配体 + 质子化态
        │ 输出: prmtop(三道守卫过) + 轨迹 + 稳定性/收敛判定
        v
[5] binding-energy          md-simulation-workflow
          输出: ΔG_bind ± 块平均SEM + 残基分解 (+可选 CpHMD/QM/MM 深化)
```

**数据契约**：每阶段的 inputs/outputs 在 workflow.yaml `stages` 中声明；上游产物即下游输入，格式以各技能 SKILL.md 的"产出清单"为准。

## 2. 任务路由规则

| 用户意图特征 | 路由 |
|---|---|
| 只给序列，问"这是什么/像谁" | 阶段 1 单跑 |
| 有结构/序列，要 AF3 预测或批量筛选 binder | 阶段 2-3 |
| 已有复合物结构，要动力学稳定性/结合模式验证 | 阶段 4（可跳过 2-3） |
| 要 ΔG 定量、排名、残基贡献 | 阶段 4→5 |
| 全新蛋白从零到机制 | 1→2→3→4→5 全链 |
| 阶段 4/5 出现崩溃/伪影/收敛问题 | md-simulation-workflow 的坑清单（§5 + analysis-and-pitfalls.md） |

## 3. 算力排期参考（实证基线）

| 任务 | 资源 | 实测 |
|---|---|---|
| AF3 100-seed 单候选 | 1×3090 | 2.5-5h（featurization ~10s/seed + XLA 编译缓存复用） |
| AF3 批量 N 候选 | 7×3090 round-robin | 151 候选 ≈ 2.5-4.5 天 |
| OpenDDE 单候选 100 seed (bf16) | 1×3090 | ~54s/seed，单 job ~91min |
| MD 100ns（~3 万原子） | 1×3090 | 100-200 ns/day |
| MD 500ns×48 体系批量 | 7×3090 | ~4 天（22 脚本调度 + 断点续跑） |
| MM/GBSA 末20ns×100帧 | CPU | ~2 min/体系 |
| MM/PBSA 同采样 | CPU | 15-25 min/体系（慢一个量级） |
| CpHMD 固定 pH 5ns/点 | 1×3090 | 35-48 min/点 |
| QM/MM RC 扫描（34 窗） | CPU 串行 | ~10-15 h（过夜） |

排期原则：GPU 批量用 round-robin 每卡单进程 + UUID 绑卡；共享集群先巡检占用（本机历史：GPU5 为 MD 专用勿占）；长任务 setsid nohup + 终结标记监控。

## 4. 扩展接口（如何接入新工具/新技能）

**接入新执行技能**（如 FEP、Markov 状态模型）：
1. 复制 `templates/skill-template/` → `skills/<新技能名>/`，按模板写 SKILL.md（frontmatter 规范：name+description，description 只写触发条件）；
2. 在 `workflow.yaml` 的 `stages` 注册新阶段或挂到既有阶段的 `skill_alternatives`；
3. 在 plugin.json 的 keywords 补触发词；
4. 数据契约：声明 inputs/outputs，尽量复用既有产物格式（prmtop/nc、model.cif、FASTA）。

**接入新引擎**（如 GROMACS 作为阶段 4 备选）：
- 在 md-simulation-workflow/references/md-engine-comparison.md 注册引擎档位与迁移注意；
- 编排层无需改代码——路由按 skill_alternatives 降级。

**质量门禁（所有新技能共用约定，已写入 workflow.yaml conventions）**：
- 官方工具优先；手写脚本先与官方输出比对确认无 bug 再运行；
- 完成判定认终结标记，不信文件存在性；改算法/续跑必失效全部缓存；
- 所有参数标实证来源，未实证项标 ⚠️；每项目独立 handoff.md。

## 5. 阶段间检查点（防错传递）

- 1→2：FASTA 清洁（无 */小写混杂）；家族结论已写入 VERDICT.md。
- 2→3：置信度文件齐备；AF3 输出布局与后处理 `--layout` 参数匹配。
- 3→4：进入 MD 的结构已过质量判定（预测结构 pLDDT/四象限合格）；质子化态有依据（PROPKA 或文献）。
- 4→5：生产轨迹**收敛判定通过**（双判据）；未收敛不排能量计算（否则段间 SD 淹没排名）。
- 5→输出：报告口径统一（末 100ns 窗 + 块平均 SEM + 双口径排名稳健性声明）。
