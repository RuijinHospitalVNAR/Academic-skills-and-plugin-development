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


## 6. 实验交接包审核防线 (2026-10-13 固化, GPCR/VNAR 项目实战教训)

**背景**: 计算辛苦做完, 交付包拿错结果 = 全功尽弃。实战中连环抓出: 手抄象限笔误 (2 条候选 AF3 标签错)、fasta 计数把注释行算入 (报 20 实为 19)、交付集漏 4 条新晋 A、代表结构是断软链、新晋候选漏能量。**交付前必须过五道程序化防线, 全部脚本化, 禁止人工目检代替**:

1. **序列层**: fasta 逐条对**设计输入 json 原文** (binder 序列源头) 比对, 不对任何中间汇总文件; 同时查重复 ID/重复序列。
2. **标签层**: 象限/lb/iptm 必须**程序化直出自权威 dualaxis CSV**, 禁止手抄转写进 fasta/报告 (笔误根因); 报告与 CSV 交叉一致性抽查, **内部矛盾 = 笔误信号** (如报告两处对同一候选描述冲突)。
3. **结构层**: 交付结构内 binder 链序列 == fasta 序列逐条验证; 交付前 `ls -L` 检查全部软链实体化 (**指向远端机器的软链必断**, 从远端 scp 拉实体: `ssh -p <REMOTE_PORT> -i <DEPLOY_KEY_PATH> user@<REMOTE_HOST>`, 真实地址见本地 handoff)。
4. **覆盖层**: ①分析版本一致性 — gate/阈值变更后核对**所有批次同版本重跑** (boltzgen 批漏 v2 致 3893 lb 低报 0.29 的教训); ②交付集 vs 引擎全集比对 (OD-A 总数 = fasta 收录数); ③fasta 计数用 `line.startswith('>')` 勿用 `count('>')` (注释里的 '>' 会算入)。
5. **能量层**: 新晋候选**立即补能量** (同协议 FastRelax+InterfaceAnalyzer / prime_mmgbsa), 不留 "待补" 尾巴; 主表合并后 rank 全量重排; 命名双前缀归一化必须用 `'mc4r_'+m.split('mc4r_')[-1]` 防 mc2r 混入; Schrodinger out.csv 数值在第 2 行 (DictReader[0])。

**交付包标准结构** (人工审核友好): `{项目}/shortlist_structures/` 下 = `candidates.fasta` (统一 header: ID + 组名 + 各引擎象限(lb,iptm) + len + dG+rank + mMG + 注记, **排序=实验优先级**) + `od_rep/`+`af3_rep/` (与 fasta 一一对应, 平铺命名 `{cand}.cif`) + `relaxed_pdb/`; 全指标 markdown 总表入 handoff (档位/骨架/双引擎/双能量/口袋特征)。
**建议节奏**: 设计→筛选周期收官时, 交付包生成→五道防线→人工核验 三段式; 防线脚本化后每次 <10 min。

## 7. GPCR 功能性 binder 筛选级联 Pipeline v3 (2026-10-18 对照实验校准后定稿)

**适用**: 设计 GPCR 激动剂/拮抗剂 binder 的全链路筛选。核心原则: **效价 (激活/抑制) 判定与亲和力判定分轨** — 亲和看双轴置信, 效价看三元 Gs 偶联, 模板回声用消融排除。详见 structure-prediction-analysis §8。

### 7.1 级联结构 (计算量从小到大, 废候选早出局)

| 阶段 | 体系 | 引擎/seeds | gate |
|---|---|---|---|
| S0 生成 | **二元** (binder+受体) | boltzgen/AnewOmni | — (三元生成归因混淆+成本 1.6×, 禁) |
| S0.5 triage | 二元 | **OD 单引擎** (Ab/Ag 微调强), 5 seeds 起步 | OD-lb ipTM<0.4 弃; 0.4-0.65 触发 25 seeds 复核 |
| S1 双轴 | 二元 | AF3+OD 各 100 seeds | 姿态 dominant + gate v2 |
| S2 sanity | 二元 | — | 能量伪影只 flag 不排序 (dG>+20 REU); binder↔Gs 冲突预检 |
| S3 三元效能 | 5 链 (+Gα/Gβ/Gγ) | **50 seeds × 1 sample = 50 个独立样本** (同 seed 内 diffusion samples 输出基本一致、非独立, 2026-11 实证, 对齐结构技能 §2.1 `--num_diffusion_samples=1` 原则; 与天然激动剂基准同 N) | **gate = 相对联合组装占比** (pair(A-B)≥AB阈值 且 pair(R-Gα)≥0.5; AB阈值由 decoy 面板 95 分位定标, 见 7.2; BC-only=伪影, 0071 实证 binder 漂离 20Å 且 seed 聚集)；候选点估计落入基准 CI → 自动升 100 seeds |
| S3.5 消融探查（可选） | 二元仅非活性模板 | 25 seeds | **单向 assay**：通过=强内在激活证据；失败不结论（α-MSH 也坍缩 0/125） |
| S4 能量+交接 | — | pyro + 静态 MM/GBSA (单结构能量, 无 MD 轨迹) | 五道审核防线 (§6) |

### 7.2 三元判读标尺 (相对基准 + 非劣效, 2026-10-19 校准)

- **基准 = 靶点实测值, 非普适常数**: MC4R 的 50% (25/50, Clopper-Pearson [0.36, 0.65]) 来自 α-MSH 原生肽 SYSMEHFRWGKPV 50 seeds (历史 10×5 协议实测); GLP-1R 等须用自身天然激动肽同协议同 N 实测 (如 GLP-1(7-36)), **禁止沿用 50%**
- **非劣效检验 (主判据)**: δ=0.20 (允许比天然低 20 个百分点仍判同档); Newcombe 差值 CI (p_cand − p_native) 单侧 95% 下界 ≥ −δ → 激动级 (非劣于天然); 点估计档位仅描述不作判决; 一律报 Clopper-Pearson CI, 禁用 Wald
- **AB 阈值由 decoy 定标**: 2 个不结合靶点的 VHH (无关 VHH 1MEL cAb-Lys3 + CDR 打乱/框架保留版) 各 25 seeds, 取 95 分位作下限; 结果表同报硬联合率 (AB≥0.5) 与软联合率 (AB≥decoy 下限)
- **过散检验**: 报每 seed 联合率 + beta-binomial 过散检验 + ICC; ICC 高 (seed 聚集, 如 0071 全高/全低) → 加 seeds 复测, ICC 低 → 加 seeds 提精度; 点估计落入基准 CI → 自动升 100 seeds
- corr(pair,S1)≈0.4-0.5 + 高/低 pair 样本 TM6 差 ~1Å (跨对照与候选一致) → 构象选择信号真实, pair 承载激活信息
- S1 复合分客观化: 熵权法/CRITIC + simplex 扰动扫描 (Kendall τ) + 帕累托前沿双轨; cAMP≥12 点后切 logistic

### 7.3 红线禁令 (对照实验实证)

1. **混合活性/非活性模板的二元 S1 不得作效价结论** — 受体构象跟随模板组成而非 binder (0094 实证: 4 模板 S1 0.842 → 仅 6W25 模板时 0.324, TM6 9.0Å 全闭); **消融是单向 assay** — α-MSH 天然激动肽也坍缩 (S1 0.308, 0/125), 消融失败不能证伪; 仅"超出肽参照的激活尾巴"可作加分项
2. **多链预测接触数无区分力** — 模型必须摆出所有链 ("Gs 搭上去"是输出假象); 读数用 chain_pair_iptm; 弱偶联体系的 binder-Gs 2-3Å "冲突"是链错位退化, 非真拮抗
3. **三元 S1 只记录不作 gate** (Gs+活性模板把全员压到 0.77-0.80, 基线 0.738)
4. 三元 Gs 链配 MSA (裸序列压低绝对校准; 候选间相对比较不受影响)
5. 肽对照线性化须诚实注记 (丢环化/D-残基 → setmelo/shu 线性版仅差 1 残基, 阴性弱); α-MSH 原生序列是唯一精确标尺; 真肽用 CCD 编码
6. **AB 阈值 0.5 不得默认使用** — 每靶点须用 decoy 面板定标 (7.2); 未定标前只报硬/软双列并注明阈值来源, 不得据此判死候选
7. **小样本不得单独定罪** — 25 samples/5 seeds 量级不足 (0071 消融 3/5 的 Wilson CI ≈ [0.23, 0.88]); 判死/判活一律走非劣效 CI + 过散检验, 必要时先加 seed 复测

**工具链**: build_ternary_inputs.py (5 链 json, 顶层 dict+dialect alphafold3) / ternary_postprocess.py / build_ctrl_inputs.py + ctrl_postprocess.py (对照与消融)。链级模板机制: templates 挂 query 链只约束该链自身构象, 链间摆放靠模型训练先验。

### 7.4 对照面板 (靶点级一次性资产, 非每批成本)

两级分离: **引擎级 QA** (跨靶点, MC4R 战役 2026-10 已定, 结论永久复用): OD 三元挤掉设计蛋白 binder、AF3 pair 有构象选择信号、多链接触数无区分力、消融是单向 assay — 新靶点不重验。**靶点级标尺** (每靶点一次性, ~1-2h): 天然激动肽同 N 定 p_native (MC4R: α-MSH 25/50 = 0.50) + 拮抗肽定地板 + 二元 TM6 基线一次 + **decoy 面板 2×25 seeds** (无关 VHH 1MEL cAb-Lys3 + CDR 打乱/框架保留版) 定 AB 阈值 95 分位; GLP-1R 例: GLP-1(7-36) + exendin(9-39); 基准值禁止跨靶点沿用。**重跑触发仅四项** (日常批次零对照成本): ①引擎/checkpoint 版本 ②seeds 协议 ③MSA 策略 ④模板集/构建体变更。**同型铁律**: 肽对照不能定标蛋白 binder 构象指标; 肽线性化须注记。
